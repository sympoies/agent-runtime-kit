#!/usr/bin/env python3
"""PreToolUse hook: block direct git commit invocations.

Agents should use semantic-commit so commit messages, validation, and
dirty-tree handling stay auditable.
"""

from __future__ import annotations

import functools
import re
import subprocess
import sys
from pathlib import PurePosixPath

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    emit_block,
    invocation_is_unresolved_nested,
    invocation_tokens,
    opaque_invocation_candidates,
    opaque_invocation_is_literal_shell_test,
    read_payload,
    simple_commands_with_nested_shells,
)

BLOCK_REASON = "Do not use git commit directly. Use semantic-commit instead."
OPAQUE_REASON = (
    "Command intent could not be resolved safely. Classification: "
    "rule=opaque-executable; operation=dynamic-executable. A shell-expanded "
    "or opaque invocation can change the executable or subcommand; use a "
    "stable command name and literal arguments in a separate tool call."
)
ALIAS_REASON = (
    "Git subcommand dispatch could not be admitted safely. Classification: "
    "rule=git-alias-resolution; operation=dynamic-subcommand. A subcommand "
    "that is not an installed Git command, or an invocation-defined alias, can "
    "resolve through configured or shell aliases to `commit`; use a literal "
    "installed Git command, or use semantic-commit for commit creation."
)

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
GIT_SUBCOMMAND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
GIT_OPTIONS_WITH_VALUE = {
    "-C",
    "-c",
    "--config-env",
    "--exec-path",
    "--git-dir",
    "--namespace",
    "--work-tree",
}
GIT_OPTIONS_WITH_VALUE_PREFIXES = (
    "--config-env=",
    "--exec-path=",
    "--git-dir=",
    "--namespace=",
    "--work-tree=",
)


def basename(token: str) -> str:
    return PurePosixPath(token).name


def git_subcommand(simple_command: list[str]) -> str | None:
    invocation = invocation_tokens(simple_command)
    if not invocation or basename(invocation[0]) != "git":
        return None

    index = 1
    while index < len(invocation):
        token = invocation[index]
        if token == "--":
            return None
        if token in GIT_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            index += 1
            continue
        if token.startswith("-c") and token != "-c":
            index += 1
            continue
        if token.startswith(GIT_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return token
    return None


def token_is_dynamic(token: str) -> bool:
    """Whether shell expansion can change a parsed Git subcommand token."""
    return any(marker in token for marker in "$`*?[]{}()#^~")


def selected_inline_alias(simple_command: list[str]) -> str | None:
    """Return a selected alias defined by this Git invocation, if any."""
    invocation = invocation_tokens(simple_command)
    if not invocation or basename(invocation[0]) != "git":
        return None

    aliases: set[str] = set()
    index = 1
    while index < len(invocation):
        token = invocation[index]
        config: str | None = None
        if token == "-c":
            if index + 1 >= len(invocation):
                return None
            config = invocation[index + 1]
            index += 2
        elif token.startswith("-c") and token != "-c":
            config = token[2:]
            index += 1
        elif token == "--config-env":
            if index + 1 >= len(invocation):
                return None
            config = invocation[index + 1]
            index += 2
        elif token.startswith("--config-env="):
            config = token.removeprefix("--config-env=")
            index += 1
        elif token in GIT_OPTIONS_WITH_VALUE:
            index += 2
        elif token.startswith("-C") and token != "-C":
            index += 1
        elif token.startswith(GIT_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
        elif token.startswith("-") and token != "-":
            index += 1
        else:
            return token if token.lower() in aliases else None

        if config is not None:
            key = config.split("=", 1)[0].lower()
            if key.startswith("alias.") and len(key) > len("alias."):
                aliases.add(key.removeprefix("alias."))
    return None


FALLBACK_BUILTINS = frozenset(
    {
        "add",
        "branch",
        "checkout",
        "clone",
        "commit",
        "config",
        "diff",
        "fetch",
        "grep",
        "init",
        "log",
        "merge",
        "mv",
        "pull",
        "push",
        "rebase",
        "reset",
        "restore",
        "rev-parse",
        "rm",
        "show",
        "status",
        "switch",
        "tag",
        "worktree",
    }
)
# Variables and env options that change where Git finds `git-<name>` programs.
LOOKUP_ENV_NAME_RE = re.compile(r"(?:^|[\s=]|^-u)(?:PATH|GIT_EXEC_PATH)(?:=|\s|$)")
ENV_RESET_TOKENS = {"-", "-i", "--ignore-environment"}
LOOKUP_ENV_NAMES = frozenset({"PATH", "GIT_EXEC_PATH"})
LOOKUP_ASSIGNMENT_RE = re.compile(r"^(?:PATH|GIT_EXEC_PATH)\+?=")
# Shell words that can bind a variable named by a later argument.
VARIABLE_BINDING_WORDS = frozenset(
    {
        "declare",
        "export",
        "for",
        "getopts",
        "local",
        "mapfile",
        "printf",
        "read",
        "readarray",
        "readonly",
        "select",
        "typeset",
        "unset",
    }
)


def list_git_commands(categories: str) -> frozenset[str] | None:
    """Return `git --list-cmds=<categories>` under a bounded probe."""
    try:
        completed = subprocess.run(
            ["git", f"--list-cmds={categories}"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or len(completed.stdout) > 1024 * 1024:
        return None
    return frozenset(completed.stdout.split())


@functools.lru_cache(maxsize=1)
def git_builtin_commands() -> frozenset[str]:
    """Return Git builtins, with a conservative fallback."""
    return FALLBACK_BUILTINS | (list_git_commands("builtins") or frozenset())


@functools.lru_cache(maxsize=1)
def git_installed_commands() -> frozenset[str]:
    """Return builtins plus installed `git-<name>` programs.

    Git dispatches a builtin, then an installed `git-<name>` program (exec-path
    porcelain such as `submodule`, or a PATH extension such as `git-lfs`),
    before it consults aliases, so none of these names can hide an alias while
    the lookup environment matches this probe. Invocation-defined `-c alias.*`
    aliases are rejected separately.
    """
    return git_builtin_commands() | (list_git_commands("main,others") or frozenset())


def tokens_before_git(simple_command: list[str], invocation: list[str]) -> list[str]:
    if invocation and simple_command[-len(invocation) :] == invocation:
        return simple_command[: -len(invocation)]
    for index, token in enumerate(simple_command):
        if basename(token) == "git":
            return simple_command[:index]
    return simple_command


def retargets_program_lookup(simple_command: list[str], invocation: list[str]) -> bool:
    """Whether this command changes PATH or Git's exec-path for the Git call.

    Then an installed `git-<name>` seen by the hook may be absent for Git, which
    falls back to a same-named configured alias.
    """
    prefix = tokens_before_git(simple_command, invocation)
    if any(LOOKUP_ENV_NAME_RE.search(token) for token in prefix):
        return True
    if any(basename(token) == "env" for token in prefix) and any(
        token in ENV_RESET_TOKENS
        or (token.startswith("-") and not token.startswith("--") and "i" in token[1:])
        for token in prefix
    ):
        return True
    for token in invocation[1:]:
        if token == "--exec-path" or token.startswith("--exec-path="):
            return True
        if not token.startswith("-"):
            break
    return False


SOURCING_WORDS = frozenset({"source", "."})
NAMEREF_WORDS = frozenset({"declare", "typeset", "local"})
COMMAND_PREFIX_WORDS = frozenset({"builtin", "command"})


def command_word(tokens: list[str]) -> str | None:
    """Return the shell command word, skipping assignments and builtin/command."""
    index = 0
    while index < len(tokens) and ASSIGNMENT_RE.match(tokens[index]):
        index += 1
    while index < len(tokens) and tokens[index] in COMMAND_PREFIX_WORDS:
        index += 1
        while index < len(tokens) and tokens[index].startswith("-"):
            index += 1
    return tokens[index] if index < len(tokens) else None


def command_retargets_lookup(simple_commands: list[list[str]]) -> bool:
    """Whether any statement of the whole command may change PATH or GIT_EXEC_PATH.

    An earlier `export PATH=...`, `unset PATH`, `for PATH in ...`, or similar
    changes lookup for every later Git call, including across `;`, `&&`, and
    nested shells. A sourced file or a nameref (`declare -n r=PATH`) can do
    the same invisibly. The token check is deliberately conservative.
    """
    for tokens in simple_commands:
        word = command_word(tokens)
        if word in SOURCING_WORDS:
            return True
        if word in NAMEREF_WORDS and any(
            token.startswith("-") and not token.startswith("--") and "n" in token[1:]
            for token in tokens[1:]
        ):
            return True
        if any(LOOKUP_ASSIGNMENT_RE.match(token) for token in tokens):
            return True
        if any(PurePosixPath(token).name in VARIABLE_BINDING_WORDS for token in tokens) and any(
            token in LOOKUP_ENV_NAMES
            or token.lstrip("-").lstrip("v") in LOOKUP_ENV_NAMES
            for token in tokens
        ):
            return True
    return False


def subcommand_block_reason(
    subcommand: str | None,
    simple_command: list[str],
    invocation: list[str],
    *,
    lookup_retargeted: bool = False,
) -> str:
    if subcommand is None:
        return ""
    if subcommand == "commit":
        return BLOCK_REASON
    if token_is_dynamic(subcommand):
        return OPAQUE_REASON
    if not GIT_SUBCOMMAND_RE.fullmatch(subcommand):
        return ""
    if subcommand in git_builtin_commands():
        return ""
    if subcommand not in git_installed_commands():
        return ALIAS_REASON
    if lookup_retargeted or retargets_program_lookup(simple_command, invocation):
        return ALIAS_REASON
    return ""


def git_commit_block_reason(command: str) -> str:
    simple_commands = list(simple_commands_with_nested_shells(command))
    lookup_retargeted = command_retargets_lookup(simple_commands)
    for simple_command in simple_commands:
        if selected_inline_alias(simple_command) is not None:
            return ALIAS_REASON
        invocation = invocation_tokens(simple_command)
        reason = subcommand_block_reason(
            git_subcommand(simple_command),
            simple_command,
            invocation,
            lookup_retargeted=lookup_retargeted,
        )
        if reason:
            return reason
        if invocation_is_unresolved_nested(invocation):
            return OPAQUE_REASON
        if opaque_invocation_is_literal_shell_test(invocation):
            # Test operands are never executed; a substitution among them is
            # already its own simple command in this loop.
            continue
        for candidate in opaque_invocation_candidates(invocation, {"git"}):
            if selected_inline_alias(candidate) is not None:
                return ALIAS_REASON
            reason = subcommand_block_reason(
                git_subcommand(candidate),
                simple_command,
                candidate,
                lookup_retargeted=lookup_retargeted,
            )
            if reason:
                return reason
            if invocation_is_unresolved_nested(candidate):
                return OPAQUE_REASON
    return ""


def main() -> int:
    command = command_from(read_payload())
    reason = git_commit_block_reason(command) if command else ""
    if reason:
        emit_block(reason)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
