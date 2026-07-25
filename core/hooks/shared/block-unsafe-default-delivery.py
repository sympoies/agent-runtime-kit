#!/usr/bin/env python3
"""PreToolUse hook: keep default-branch delivery on governed routes.

PR delivery remains the default. A maintainer-authorized L0 direct-main change
is authored as one signed commit on a non-default managed worktree and is
delivered through ``forge-cli repo push-default``. A separately authorized L0
local-default task may use ``semantic-commit local-default`` to author one
signed local-only commit in the primary checkout. This hook blocks raw shell
paths that would otherwise bypass either contract.

This is a mechanical guardrail, not a shell sandbox. Provider branch rules and
the forge-cli expected-base/signature/read-back contract remain authoritative.

A blocked verdict names what it resolved and what failed, because an agent that
cannot see the discriminator cannot fix the invocation. ``semantic-commit`` is
classified against the repository it actually commits in: ``--repo`` binds that
target outright, and a literal absolute ``cd`` in the same command resolves it.
Raw Git still fails closed after any shell-context change. Where the target
remains unresolvable, one command may state a reason inline as
``AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER=<reason> semantic-commit ...``; that
admits only the unresolvable class, only for the governed CLI that re-verifies
worktree, branch, expected head, staging, and signing itself, and only for the
command it is written on. A proven default-branch target never waives.
"""

from __future__ import annotations

import fnmatch
import functools
import os
import selectors
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    OPAQUE_NESTED_SHELL_COMMAND,
    OPAQUE_WRAPPER_COMMAND,
    command_from,
    effective_workdir,
    emit_block,
    env_split_expanded_tokens,
    invocation_is_unresolved_nested,
    invocation_tokens,
    is_assignment,
    nested_shell_payload,
    opaque_invocation_candidates,
    read_payload,
    semantic_commit_invocation_effects,
    semantic_commit_invocation_state,
    simple_commands_with_nested_shells,
)

BLOCK_REASON = (
    "Do not author or push an agent change on the default branch through a raw "
    "shell path. PR delivery is the default. When the maintainer explicitly "
    "authorized direct-main delivery in the current task, author one signed "
    "commit in a non-default managed worktree and use `forge-cli repo "
    "push-default` with the expected base and reason file. When local-default "
    "completion was explicitly authorized instead, use the exact governed "
    "`semantic-commit local-default` receipt flow."
)
AMBIGUOUS_PREFIX = "Default-branch delivery target could not be resolved safely."
AMBIGUOUS_REASON = f"{AMBIGUOUS_PREFIX} {BLOCK_REASON}"
# A one-shot waiver is spelled on the command it admits, never exported, so it
# cannot outlive that invocation and stays visible in the transcript. It admits
# only an unresolvable `semantic-commit` target, where the governed CLI still
# re-verifies the worktree, branch, expected head, staging, and signing.
WAIVER_ASSIGNMENT_NAME = "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER"
# Must equal nils-cli's MIN_DELIVERY_WAIVER_LENGTH. A lower value here would
# admit a delivery whose reason the receipt then refuses to record.
MINIMUM_WAIVER_REASON_LENGTH = 12
CONTROL_CHARACTERS = frozenset(
    chr(codepoint)
    for start, stop in ((0x00, 0x20), (0x7F, 0xA0))
    for codepoint in range(start, stop)
)
WAIVER_HINT = (
    "When the target cannot be made resolvable, state a reason of at least "
    f"{MINIMUM_WAIVER_REASON_LENGTH} characters of text on this one command as "
    f"`{WAIVER_ASSIGNMENT_NAME}=<reason> semantic-commit ...`; an exported "
    "variable is not accepted, and the reason is recorded in the receipt as "
    "`data.delivery_waiver`."
)
REPO_HINT = (
    "Pass `--repo <absolute path>` when the target repository is not the tool "
    "workdir; it binds the target without depending on shell state."
)
GOVERNED_CONTEXT_EXECUTABLES = frozenset({"git", "semantic-commit"})
DIRECTORY_EXPANSION_CHARACTERS = "$`*?[]~"
GIT_OPTIONS_WITH_VALUE = frozenset(
    {"-C", "-c", "--config-env", "--exec-path", "--git-dir", "--namespace", "--work-tree"}
)
GIT_OPTIONS_WITH_VALUE_PREFIXES = (
    "--config-env=",
    "--exec-path=",
    "--git-dir=",
    "--namespace=",
    "--work-tree=",
)
GIT_REPOSITORY_CONTEXT_OPTIONS = frozenset(
    {"--git-dir", "--namespace", "--work-tree"}
)
GIT_REPOSITORY_CONTEXT_PREFIXES = (
    "--git-dir=",
    "--namespace=",
    "--work-tree=",
)
GIT_REPOSITORY_CONTEXT_FLAGS = frozenset({"--bare"})
GIT_CONFIG_ENVIRONMENT_NAMES = frozenset(
    {"HOME", "XDG_CONFIG_DIRS", "XDG_CONFIG_HOME"}
)
ENV_CONTEXT_OPTIONS = frozenset(
    {"-C", "-P", "-S", "--chdir", "--path", "--split-string"}
)
ENV_CONTEXT_OPTION_PREFIXES = (
    "--chdir=",
    "--path=",
    "--split-string=",
)
GIT_NON_DELIVERY_COMMANDS_BASELINE = frozenset(
    {
        "add",
        "am",
        "annotate",
        "apply",
        "archive",
        "bisect",
        "blame",
        "branch",
        "bundle",
        "cat-file",
        "checkout",
        "cherry",
        "cherry-pick",
        "clean",
        "clone",
        "commit",
        "config",
        "describe",
        "diff",
        "difftool",
        "fetch",
        "for-each-ref",
        "format-patch",
        "fsck",
        "gc",
        "grep",
        "hash-object",
        "help",
        "init",
        "log",
        "ls-files",
        "ls-remote",
        "ls-tree",
        "maintenance",
        "merge",
        "mergetool",
        "mv",
        "name-rev",
        "notes",
        "pull",
        "range-diff",
        "rebase",
        "reflog",
        "remote",
        "repack",
        "replace",
        "reset",
        "restore",
        "rev-list",
        "rev-parse",
        "revert",
        "rm",
        "shortlog",
        "show",
        "show-ref",
        "sparse-checkout",
        "stash",
        "status",
        "submodule",
        "switch",
        "symbolic-ref",
        "tag",
        "update-index",
        "update-ref",
        "verify-commit",
        "verify-tag",
        "whatchanged",
        "worktree",
    }
)
SHELL_CONTEXT_COMMANDS = frozenset({".", "cd", "popd", "pushd", "source"})
SHELL_BUILTIN_UNWRAP_LIMIT = 8
PUSH_OPTIONS_WITH_VALUE = frozenset(
    {"--exec", "--push-option", "--receive-pack", "--repo", "-o"}
)
PUSH_OPTIONS_WITH_VALUE_PREFIXES = (
    "--exec=",
    "--force-with-lease=",
    "--push-option=",
    "--receive-pack=",
    "--repo=",
    "--signed=",
)
GIT_PROBE_TIMEOUT_SECONDS = 4.0
GIT_PROBE_OUTPUT_LIMIT_BYTES = 1024 * 1024
GIT_PROBE_STATUS_TIMEOUT = "timeout"
GIT_DEFAULT_BRANCH_REWRITE_COMMANDS = frozenset(
    {"cherry-pick", "merge", "reset", "update-ref"}
)
GIT_EXPLICIT_RECOVERY_OPTIONS = frozenset(
    {"--abort", "--continue", "--quit", "--skip"}
)


def payload_base(payload: Mapping[str, Any]) -> Path:
    # Resolve the command's effective workdir (issue #601 P0-4) so default-branch
    # delivery is judged against the repository the command really targets, not
    # the hook process cwd.
    return effective_workdir(payload).resolve(strict=False)


class GitProbe:
    """Run all Git discovery for one hook command under one bounded budget."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GIT_PROBE_TIMEOUT_SECONDS,
        output_limit_bytes: int = GIT_PROBE_OUTPUT_LIMIT_BYTES,
        executable: str = "git",
    ) -> None:
        self.deadline = time.monotonic() + max(timeout_seconds, 0.0)
        self.output_limit_bytes = max(output_limit_bytes, 0)
        self.executable = executable
        self._builtin_commands: frozenset[str] | None = None

    @staticmethod
    def _kill_group(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def run_with_status(
        self, cwd: Path, *args: str
    ) -> tuple[subprocess.CompletedProcess[str] | None, str]:
        """Run Git and distinguish a deadline timeout from other failures."""
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            return None, GIT_PROBE_STATUS_TIMEOUT
        command = [self.executable, *args]
        environment = dict(os.environ)
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except (OSError, ValueError):
            return None, "execution"
        assert process.stdout is not None and process.stderr is not None

        selected = selectors.DefaultSelector()
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        selected.register(process.stdout, selectors.EVENT_READ, "stdout")
        selected.register(process.stderr, selectors.EVENT_READ, "stderr")
        total = 0
        failure = ""
        try:
            while selected.get_map():
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    failure = GIT_PROBE_STATUS_TIMEOUT
                    break
                events = selected.select(remaining)
                if not events:
                    failure = GIT_PROBE_STATUS_TIMEOUT
                    break
                for key, _mask in events:
                    try:
                        chunk = os.read(key.fd, 65536)
                    except OSError:
                        failure = "read"
                        break
                    if not chunk:
                        selected.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    total += len(chunk)
                    if total > self.output_limit_bytes:
                        failure = "output-limit"
                        break
                    buffers[key.data].extend(chunk)
                if failure:
                    break
            if failure:
                self._kill_group(process)
                return None, failure
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                self._kill_group(process)
                return None, GIT_PROBE_STATUS_TIMEOUT
            try:
                returncode = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                self._kill_group(process)
                return None, GIT_PROBE_STATUS_TIMEOUT
            return (
                subprocess.CompletedProcess(
                    command,
                    returncode,
                    buffers["stdout"].decode("utf-8", errors="replace"),
                    buffers["stderr"].decode("utf-8", errors="replace"),
                ),
                "",
            )
        finally:
            selected.close()
            for stream in (process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()

    def run(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
        completed, _status = self.run_with_status(cwd, *args)
        return completed

    def builtin_commands(self, cwd: Path) -> frozenset[str]:
        """Return installed builtins plus retained non-delivery helper commands."""
        if self._builtin_commands is None:
            result = self.run(cwd, "--list-cmds=builtins")
            discovered = (
                frozenset(result.stdout.split())
                if result is not None and result.returncode == 0
                else frozenset()
            )
            self._builtin_commands = (
                GIT_NON_DELIVERY_COMMANDS_BASELINE | discovered
            )
        return self._builtin_commands


def git_context(
    arguments: list[str], base: Path
) -> tuple[Path, str, list[str], list[str], bool]:
    cwd = base
    config_arguments: list[str] = []
    context_valid = True
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == "--":
            index += 1
            break
        if token == "-C":
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            path = Path(arguments[index + 1]).expanduser()
            cwd = (path if path.is_absolute() else cwd / path).resolve(strict=False)
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            path = Path(token[2:]).expanduser()
            cwd = (path if path.is_absolute() else cwd / path).resolve(strict=False)
            index += 1
            continue
        if token == "-c":
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            value = arguments[index + 1]
            config_arguments.extend((token, value))
            if delivery_sensitive_config(value):
                context_valid = False
            index += 2
            continue
        if token.startswith("-c") and token != "-c":
            config_arguments.append(token)
            if delivery_sensitive_config(token[2:]):
                context_valid = False
            index += 1
            continue
        if token in {"--config-env"}:
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            value = arguments[index + 1]
            config_arguments.extend((token, value))
            if delivery_sensitive_config(value):
                context_valid = False
            index += 2
            continue
        if token.startswith("--config-env="):
            config_arguments.append(token)
            if delivery_sensitive_config(token.removeprefix("--config-env=")):
                context_valid = False
            index += 1
            continue
        if token in GIT_REPOSITORY_CONTEXT_OPTIONS:
            context_valid = False
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            index += 2
            continue
        if token.startswith(GIT_REPOSITORY_CONTEXT_PREFIXES):
            context_valid = False
            index += 1
            continue
        if token in GIT_REPOSITORY_CONTEXT_FLAGS:
            context_valid = False
            index += 1
            continue
        if token in GIT_OPTIONS_WITH_VALUE:
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            index += 2
            continue
        if token.startswith(GIT_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return cwd, token, arguments[index + 1 :], config_arguments, context_valid
    if index < len(arguments):
        return cwd, arguments[index], arguments[index + 1 :], config_arguments, context_valid
    return cwd, "", [], config_arguments, context_valid


def delivery_sensitive_config(value: str) -> bool:
    """Reject command-local Git config that can retarget a delivery."""
    key = value.split("=", 1)[0].strip().lower()
    if key in {"remote.pushdefault", "push.default", "include.path"}:
        return True
    if key.startswith("includeif.") and key.endswith(".path"):
        return True
    if key.startswith("remote."):
        return key.endswith((".url", ".pushurl", ".push", ".mirror"))
    if key.startswith("branch."):
        return key.endswith((".remote", ".pushremote", ".merge"))
    return key.startswith("url.") and key.endswith(
        (".insteadof", ".pushinsteadof")
    )


def config_environment_variables(arguments: list[str]) -> set[str]:
    """Return environment names referenced by Git ``--config-env`` options."""
    variables: set[str] = set()
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == "--config-env" and index + 1 < len(arguments):
            _name, separator, variable = arguments[index + 1].rpartition("=")
            if separator and variable:
                variables.add(variable)
            index += 2
            continue
        if token.startswith("--config-env="):
            _name, separator, variable = token.removeprefix(
                "--config-env="
            ).rpartition("=")
            if separator and variable:
                variables.add(variable)
        index += 1
    return variables


def command_local_git_environment_is_safe(
    simple_command: list[str], invocation: list[str]
) -> bool:
    """Reject command-local environment that can diverge from Git probes.

    ``semantic-commit`` is covered alongside ``git`` because the same overrides
    move where its commit lands, which would make this guard classify a
    different repository than the one the invocation mutates.
    """
    if not invocation:
        return True
    executable = PurePosixPath(invocation[0]).name
    if executable not in GOVERNED_CONTEXT_EXECUTABLES:
        return True
    referenced = config_environment_variables(invocation[1:])
    command_index = next(
        (
            index
            for index, token in enumerate(simple_command)
            if PurePosixPath(token).name == executable
        ),
        len(simple_command),
    )
    prefix = simple_command[:command_index]
    env_index = next(
        (
            index
            for index, token in enumerate(prefix)
            if PurePosixPath(token).name == "env"
        ),
        -1,
    )
    has_env_wrapper = env_index >= 0
    if has_env_wrapper:
        normalized = env_split_expanded_tokens(simple_command, env_index + 1)
        if (
            OPAQUE_WRAPPER_COMMAND in normalized
            or OPAQUE_NESTED_SHELL_COMMAND in normalized
        ):
            return False
        normalized_command_index = next(
            (
                index
                for index, token in enumerate(normalized)
                if PurePosixPath(token).name == executable
            ),
            len(normalized),
        )
        prefix = [*simple_command[:env_index], *normalized[:normalized_command_index]]

    def sensitive(name: str) -> bool:
        return (
            name.startswith("GIT_")
            or name in GIT_CONFIG_ENVIRONMENT_NAMES
            or name in referenced
        )

    for token in prefix:
        if is_assignment(token) and sensitive(token.split("=", 1)[0]):
            return False
    if not has_env_wrapper:
        return True
    index = 0
    while index < len(prefix):
        token = prefix[index]
        if token in {"-i", "--ignore-environment"}:
            return False
        if token in ENV_CONTEXT_OPTIONS or token.startswith(
            ENV_CONTEXT_OPTION_PREFIXES
        ):
            return False
        if (
            token.startswith("-")
            and not token.startswith("--")
            and any(option in token[1:] for option in "iCPS")
        ):
            return False
        if token in {"-u", "--unset"} and index + 1 < len(prefix):
            if sensitive(prefix[index + 1]):
                return False
            index += 2
            continue
        if token.startswith("--unset=") and sensitive(token.split("=", 1)[1]):
            return False
        if token.startswith("-u") and len(token) > 2 and sensitive(token[2:]):
            return False
        index += 1
    return True


def shell_command_changes_git_context(simple_command: list[str]) -> bool:
    """Whether this command can alter later Git cwd/config interpretation."""
    invocation = invocation_tokens(simple_command)
    executable = ""
    arguments: list[str] = []
    if invocation:
        executable = (
            invocation[0]
            if invocation[0] == "."
            else PurePosixPath(invocation[0]).name
        )
        arguments = invocation[1:]
    for _depth in range(SHELL_BUILTIN_UNWRAP_LIMIT):
        if executable != "builtin":
            break
        if not arguments or "$" in arguments[0] or "`" in arguments[0]:
            return True
        executable = (
            arguments[0]
            if arguments[0] == "."
            else PurePosixPath(arguments[0]).name
        )
        arguments = arguments[1:]
    else:
        if executable == "builtin":
            return True
    if executable in SHELL_CONTEXT_COMMANDS:
        return True
    if not invocation:
        return any(
            is_assignment(token)
            and (
                token.split("=", 1)[0].startswith("GIT_")
                or token.split("=", 1)[0] in GIT_CONFIG_ENVIRONMENT_NAMES
            )
            for token in simple_command
        )
    if executable in {"export", "readonly", "declare", "typeset"}:
        return any(
            is_assignment(token)
            and (
                token.split("=", 1)[0].startswith("GIT_")
                or token.split("=", 1)[0] in GIT_CONFIG_ENVIRONMENT_NAMES
            )
            for token in simple_command
        )
    if executable == "unset":
        return any(
            token.startswith("GIT_") or token in GIT_CONFIG_ENVIRONMENT_NAMES
            for token in arguments
            if not token.startswith("-")
        )
    return False


def literal_directory_target(simple_command: list[str]) -> str | None:
    """Return the literal absolute directory a plain ``cd`` moves to.

    Only an unambiguous destination qualifies. A relative path depends on where
    the sequence started, and expansion, globbing, or `~` hides the target, so
    those keep the fail-closed verdict instead of resolving to a guess.
    """
    invocation = invocation_tokens(simple_command)
    if len(invocation) != 2 or PurePosixPath(invocation[0]).name != "cd":
        return None
    if simple_command[: len(invocation)] != invocation:
        return None
    target = invocation[1]
    if not target.startswith("/"):
        return None
    if any(character in target for character in DIRECTORY_EXPANSION_CHARACTERS):
        return None
    return target


def normalized_waiver_reason(value: str) -> str:
    """Normalize a waiver reason the way the receipt writer measures it.

    Admission and recording must agree on what counts as a stated reason. This
    mirrors ``normalized_delivery_waiver`` in nils-cli's
    ``local_default_receipt``: control characters become spaces and whitespace
    runs collapse, so a reason cannot clear the minimum here through padding
    and then be dropped from the receipt, leaving an admitted delivery with no
    recorded reason. Keep both sides in step, including the minimum length.

    ``CONTROL_CHARACTERS`` is Unicode category Cc, which is exactly what Rust's
    ``char::is_control`` matches, so the two normalizations agree per codepoint.
    """
    return " ".join(
        "".join(
            " " if character in CONTROL_CHARACTERS else character
            for character in value
        ).split()
    )


def command_waiver_reason(simple_command: list[str]) -> str:
    """Return the waiver reason spelled on this command's own prefix."""
    for token in simple_command:
        if not is_assignment(token):
            break
        name, _, value = token.partition("=")
        if name == WAIVER_ASSIGNMENT_NAME:
            return normalized_waiver_reason(value)
    return ""


def waiver_admits(invocation: list[str], reason: str, waiver: str) -> bool:
    """Whether a stated one-shot waiver may admit this blocked invocation."""
    if len(waiver) < MINIMUM_WAIVER_REASON_LENGTH:
        return False
    if not reason.startswith(AMBIGUOUS_PREFIX):
        return False
    return bool(invocation) and PurePosixPath(invocation[0]).name == "semantic-commit"


def unresolved(detail: str) -> str:
    return f"{AMBIGUOUS_REASON} {detail}" if detail else AMBIGUOUS_REASON


def resolve_git_alias(
    probe: GitProbe,
    cwd: Path,
    subcommand: str,
    action: list[str],
    config_arguments: list[str],
) -> tuple[str, list[str]] | None:
    seen: set[str] = set()
    for _depth in range(8):
        # Git aliases cannot override a built-in command. In particular, an
        # alias named `push` must never hide the real push classifier.
        if subcommand == "push":
            return subcommand, action
        alias_name = subcommand.casefold()
        if alias_name in seen:
            return None
        seen.add(alias_name)
        result = probe.run(
            cwd, *config_arguments, "config", "--get", f"alias.{subcommand}"
        )
        if result is None or result.returncode not in {0, 1}:
            return None
        if result.returncode == 1:
            return subcommand, action
        value = result.stdout.rstrip("\n")
        if not value or value.lstrip().startswith("!"):
            return None
        try:
            expanded = shlex.split(value)
        except ValueError:
            return None
        if not expanded or expanded[0].startswith("-"):
            return None
        subcommand, action = expanded[0], [*expanded[1:], *action]
    return None


def current_branch(
    probe: GitProbe, cwd: Path, config_arguments: list[str] | None = None
) -> str:
    result = probe.run(
        cwd,
        *(config_arguments or []),
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
    )
    return result.stdout.strip() if result and result.returncode == 0 else ""


def cached_default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str,
    config_arguments: list[str],
) -> str:
    cached = probe.run(
        cwd,
        *config_arguments,
        "symbolic-ref",
        "--quiet",
        "--short",
        f"refs/remotes/{remote}/HEAD",
    )
    if not cached or cached.returncode != 0 or not cached.stdout.strip():
        return ""
    remote_ref = cached.stdout.strip()
    prefix = f"{remote}/"
    return remote_ref[len(prefix) :] if remote_ref.startswith(prefix) else ""


def primary_worktree_branch(
    probe: GitProbe,
    cwd: Path,
    config_arguments: list[str],
) -> str:
    """Return the primary worktree branch from Git's local worktree inventory."""
    worktrees = probe.run(
        cwd,
        *config_arguments,
        "worktree",
        "list",
        "--porcelain",
    )
    if not worktrees or worktrees.returncode != 0:
        return ""
    branch_prefix = "branch refs/heads/"
    for line in worktrees.stdout.splitlines():
        if not line:
            break
        if line.startswith(branch_prefix):
            return line.removeprefix(branch_prefix)
    return ""


def resolve_default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str = "origin",
    config_arguments: list[str] | None = None,
) -> tuple[str, bool]:
    """Resolve an authoritative local default branch without network I/O."""
    if not remote or "/" in remote or ":" in remote:
        return "", False
    git_config = config_arguments or []
    cached = cached_default_branch(probe, cwd, remote, git_config)
    primary = primary_worktree_branch(probe, cwd, git_config)
    if not cached or not primary or cached != primary:
        return "", False
    return cached, False


def default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str = "origin",
    config_arguments: list[str] | None = None,
) -> str:
    expected, cached_timeout = resolve_default_branch(
        probe, cwd, remote, config_arguments
    )
    return "" if cached_timeout else expected


def semantic_commit_repo(
    arguments: list[str], base: Path, base_source: str
) -> tuple[Path, str]:
    """Return the repository this invocation commits in, and how it resolved."""
    _read_only, value = semantic_commit_invocation_state(arguments)
    if value:
        path = Path(value).expanduser()
        resolved = (path if path.is_absolute() else base / path).resolve(strict=False)
        return resolved, "`--repo`"
    return base, base_source


def semantic_commit_block_reason(
    probe: GitProbe, arguments: list[str], base: Path, base_source: str
) -> str:
    """Classify a governed ``semantic-commit`` invocation by its own repository."""
    authors_commit, _writes_files, _repo = semantic_commit_invocation_effects(
        arguments
    )
    if not arguments or not authors_commit:
        return ""
    cwd, source = semantic_commit_repo(arguments, base, base_source)
    location = f"Resolved repository: {cwd} (from {source})."
    if arguments[0] == "local-default":
        rejection = local_default_rejection(probe, arguments, cwd)
        if not rejection:
            return ""
        return unresolved(f"{location} {rejection} {REPO_HINT} {WAIVER_HINT}")
    if arguments[0] not in {"commit", "fixup", "squash"}:
        return ""
    branch = current_branch(probe, cwd)
    expected = default_branch(probe, cwd)
    if not branch or not expected:
        return unresolved(
            f"{location} Its checked-out branch or cached default branch could "
            f"not be read. {REPO_HINT}"
        )
    return BLOCK_REASON if branch == expected else ""


def update_ref_target(arguments: list[str]) -> str | None:
    """Return the single ref target, or None for an ambiguous update-ref shape."""
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"-h", "--help"}:
            return ""
        if token in {"-m", "--message"}:
            index += 2
            continue
        if token.startswith("--message="):
            index += 1
            continue
        if token in {"--create-reflog", "-d", "--delete", "-z"}:
            index += 1
            continue
        if token in {"--stdin", "--no-deref"}:
            return None
        if token.startswith("-"):
            return None
        return token
    return None


def git_default_branch_rewrite_targets_default(
    probe: GitProbe,
    subcommand: str,
    arguments: list[str],
    cwd: Path,
    config_arguments: list[str],
) -> bool | None:
    """Classify raw ref/commit-producing Git paths that could bypass delivery."""
    if subcommand not in GIT_DEFAULT_BRANCH_REWRITE_COMMANDS:
        return False
    if any(argument in GIT_EXPLICIT_RECOVERY_OPTIONS for argument in arguments):
        return False
    if any(argument in {"-h", "--help"} for argument in arguments):
        return False
    if subcommand == "reset":
        if not arguments:
            return False
        if "--" in arguments and arguments.index("--") < len(arguments) - 1:
            return False

    expected = default_branch(probe, cwd, config_arguments=config_arguments)
    if not expected:
        return None

    current = current_branch(probe, cwd, config_arguments)
    if subcommand != "update-ref":
        if not current:
            return None
        return current == expected

    target = update_ref_target(arguments)
    if target is None:
        return None
    if not target:
        return False
    if target in {"HEAD", "@"}:
        if not current:
            return None
        return current == expected
    if target.startswith("refs/heads/"):
        return target.removeprefix("refs/heads/") == expected
    if target.startswith("heads/"):
        return target.removeprefix("heads/") == expected
    if target.startswith("refs/"):
        return False
    return target == expected


def option_value(arguments: list[str], name: str) -> str:
    for index, token in enumerate(arguments):
        if token == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if token.startswith(f"{name}="):
            return token.split("=", 1)[1]
    return ""


def local_default_rejection(
    probe: GitProbe, arguments: list[str], cwd: Path
) -> str:
    """Return why this is not the exact governed local-default shape, else ""."""
    unsupported = next(
        (
            token
            for token in arguments
            if token in {"--amend", "--allow-empty", "--message-only", "--no-edit"}
        ),
        "",
    )
    if unsupported:
        return f"local-default does not support `{unsupported}`."
    expected_branch = option_value(arguments, "--expected-branch")
    expected_head = option_value(arguments, "--expect-head")
    receipt = option_value(arguments, "--receipt-out")
    remote_mode = option_value(arguments, "--remote-mode")
    if not expected_branch:
        return "It carries no `--expected-branch`."
    if len(expected_head) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in expected_head
    ):
        return "Its `--expect-head` is not a full lowercase object id."
    if remote_mode and remote_mode != "local-only":
        return f"Its `--remote-mode {remote_mode}` is not `local-only`."
    receipt_path = Path(receipt).expanduser()
    if not receipt_path.is_absolute() or not receipt_path.parent.exists():
        return (
            "Its `--receipt-out` is not an absolute path with an existing parent."
        )
    try:
        repository = cwd.resolve(strict=True)
        receipt_parent = receipt_path.parent.resolve(strict=True)
    except OSError:
        return "The repository or the receipt directory could not be read."
    if receipt_parent == repository or repository in receipt_parent.parents:
        return (
            "Its `--receipt-out` is inside the repository; allocate the receipt "
            "outside it through `agent-out`."
        )
    head = probe.run(repository, "rev-parse", "--verify", "HEAD")
    git_dir = probe.run(
        repository, "rev-parse", "--path-format=absolute", "--git-dir"
    )
    common_dir = probe.run(
        repository, "rev-parse", "--path-format=absolute", "--git-common-dir"
    )
    if not all(
        result is not None and result.returncode == 0
        for result in (head, git_dir, common_dir)
    ):
        return "The repository did not answer the required Git reads."
    assert head is not None and git_dir is not None and common_dir is not None
    try:
        primary = Path(git_dir.stdout.strip()).resolve(strict=True) == Path(
            common_dir.stdout.strip()
        ).resolve(strict=True)
    except OSError:
        return "The repository's Git directories could not be compared."
    if not primary:
        return "The repository is a linked worktree, not the primary checkout."
    branch = current_branch(probe, repository)
    if branch != expected_branch:
        return (
            f"It is on branch `{branch or 'an unreadable branch'}`, not the "
            f"`--expected-branch {expected_branch}`."
        )
    actual_head = head.stdout.strip()
    if actual_head != expected_head:
        return (
            f"Its HEAD is {actual_head[:12]}, not the `--expect-head` "
            f"{expected_head[:12]}."
        )
    return ""


def normalized_branch(value: str, current: str) -> str:
    value = value.lstrip("+")
    if value in {"HEAD", "@"}:
        return current
    for prefix in ("refs/heads/", "heads/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def refspec_targets_default(refspec: str, default: str, current: str) -> bool:
    refspec = refspec.lstrip("+")
    # A lone colon is Git's "matching branches" refspec. It can update the
    # default branch alongside every other same-named local/remote branch.
    if refspec == ":":
        return True
    if ":" in refspec:
        source, destination = refspec.split(":", 1)
        target = normalized_branch(destination, current)
    else:
        source = refspec
        target = normalized_branch(source, current)
    if not target and source:
        return False
    if "*" in target:
        return fnmatch.fnmatch(default, target)
    return target == default


def explicit_branch_refspec_target(refspec: str) -> str:
    """Return one exact destination branch that needs no current-branch lookup."""
    value = refspec.lstrip("+")
    if not value or "*" in value or value == ":":
        return ""
    if ":" in value:
        source, destination = value.split(":", 1)
        if not source or not destination:
            return ""
    else:
        destination = value
    if destination in {"HEAD", "@"}:
        return ""
    for prefix in ("refs/heads/", "heads/"):
        if destination.startswith(prefix):
            return destination[len(prefix) :]
    if destination.startswith("refs/") or destination.startswith("tags/"):
        return ""
    return destination


def push_shape(arguments: list[str]) -> tuple[bool, bool, bool, bool, str, list[str]]:
    """Return dry-run, all/mirror, delete, tags-only, remote, and refspecs."""
    dry_run = False
    all_or_mirror = False
    delete = False
    tags_only = False
    repository = ""
    positionals: list[str] = []
    options_done = False
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if not options_done and token == "--":
            options_done = True
            index += 1
            continue
        if not options_done and token.startswith("-") and token != "-":
            if token == "--dry-run":
                dry_run = True
            if token in {"--all", "--mirror"}:
                all_or_mirror = True
            if token == "--tags":
                tags_only = True
            if token == "--delete":
                delete = True
            if token == "--repo" and index + 1 < len(arguments):
                repository = arguments[index + 1]
                index += 2
                continue
            if token.startswith("--repo="):
                repository = token.split("=", 1)[1]
                index += 1
                continue
            if token in PUSH_OPTIONS_WITH_VALUE:
                index += 2
                continue
            if token.startswith(PUSH_OPTIONS_WITH_VALUE_PREFIXES):
                index += 1
                continue
            if not token.startswith("--"):
                cluster = token[1:]
                consumed_next = False
                for position, option in enumerate(cluster):
                    if option == "n":
                        dry_run = True
                    elif option == "d":
                        delete = True
                    elif option == "o":
                        consumed_next = position + 1 == len(cluster)
                        break
                index += 2 if consumed_next and index + 1 < len(arguments) else 1
                continue
            index += 1
            continue
        positionals.append(token)
        index += 1
    if repository:
        return dry_run, all_or_mirror, delete, tags_only, repository, positionals
    if positionals:
        return (
            dry_run,
            all_or_mirror,
            delete,
            tags_only,
            positionals[0],
            positionals[1:],
        )
    return dry_run, all_or_mirror, delete, tags_only, "origin", []


def push_targets_default(
    probe: GitProbe,
    arguments: list[str],
    cwd: Path,
    config_arguments: list[str],
) -> bool | None:
    dry_run, all_or_mirror, delete, tags_only, remote, refspecs = push_shape(arguments)
    if dry_run:
        return False
    if tags_only and not refspecs:
        return False
    default, cached_timeout = resolve_default_branch(
        probe, cwd, remote, config_arguments
    )
    if not default:
        return None
    if cached_timeout:
        if all_or_mirror or delete or tags_only or not refspecs:
            return None
        targets = [explicit_branch_refspec_target(refspec) for refspec in refspecs]
        if any(not target for target in targets):
            return None
        return any(target == default for target in targets)
    if all_or_mirror:
        return True
    current = current_branch(probe, cwd, config_arguments)
    if delete:
        if not refspecs:
            return None
        return any(
            normalized_branch(refspec, current) == default for refspec in refspecs
        )
    if refspecs:
        return any(
            refspec_targets_default(refspec, default, current) for refspec in refspecs
        )
    # With no explicit refspec, Git may select a destination from
    # remote.<name>.push, branch pushRemote/upstream, remote.pushDefault, and
    # push.default. The checked-out branch alone cannot prove the destination
    # is non-default, so require callers to spell out a safe feature refspec.
    return None


def invocation_block_reason(
    probe: GitProbe,
    invocation: list[str],
    base: Path,
    *,
    environment_safe: bool = True,
    target_resolved: bool = True,
    base_source: str = "the tool workdir",
) -> str:
    if not invocation:
        return ""
    executable = PurePosixPath(invocation[0]).name
    if executable == OPAQUE_NESTED_SHELL_COMMAND:
        return AMBIGUOUS_REASON
    if executable == "semantic-commit":
        if not target_resolved:
            return unresolved(
                "Command-local Git context can move where this commit lands, so "
                f"its repository was not classified. {REPO_HINT}"
            )
        return semantic_commit_block_reason(probe, invocation[1:], base, base_source)
    if executable == "git":
        cwd, subcommand, action, config_arguments, context_valid = git_context(
            invocation[1:], base
        )
        if subcommand != "push" and subcommand in probe.builtin_commands(cwd):
            if subcommand in GIT_DEFAULT_BRANCH_REWRITE_COMMANDS:
                if not environment_safe or not context_valid:
                    return AMBIGUOUS_REASON
                target = git_default_branch_rewrite_targets_default(
                    probe, subcommand, action, cwd, config_arguments
                )
                return (
                    BLOCK_REASON
                    if target is True
                    else AMBIGUOUS_REASON
                    if target is None
                    else ""
                )
            return ""
        if subcommand == "push" and push_shape(action)[0]:
            return ""
        if not environment_safe or not context_valid:
            return AMBIGUOUS_REASON
        resolved = resolve_git_alias(
            probe, cwd, subcommand, action, config_arguments
        )
        if resolved is None:
            return AMBIGUOUS_REASON
        subcommand, action = resolved
        if subcommand != "push":
            if subcommand in GIT_DEFAULT_BRANCH_REWRITE_COMMANDS:
                target = git_default_branch_rewrite_targets_default(
                    probe, subcommand, action, cwd, config_arguments
                )
                return (
                    BLOCK_REASON
                    if target is True
                    else AMBIGUOUS_REASON
                    if target is None
                    else ""
                )
            return ""
        if push_shape(action)[0]:
            return ""
        target = push_targets_default(probe, action, cwd, config_arguments)
        return BLOCK_REASON if target is True else AMBIGUOUS_REASON if target is None else ""
    return ""


def candidate_block_reason(
    probe: GitProbe,
    simple_command: list[str],
    cwd: Path,
    candidate: list[str],
    *,
    shell_context_safe: bool,
    directory_resolved: bool,
    base_source: str,
) -> str:
    """Classify one invocation shape of a simple command in its own context."""
    command_safe = command_local_git_environment_is_safe(simple_command, candidate)
    return invocation_block_reason(
        probe,
        candidate,
        cwd,
        environment_safe=command_safe and shell_context_safe,
        target_resolved=command_safe and (shell_context_safe or directory_resolved),
        base_source=base_source,
    )


def command_block_reason(command: str, base: Path) -> str:
    probe = GitProbe()
    shell_context_safe = True
    simple_commands = simple_commands_with_nested_shells(command)
    # A nested shell hides where its own `cd` stops applying, so a resolved
    # directory is only trustworthy across a flat command sequence.
    resolves_directories = not any(
        nested_shell_payload(invocation_tokens(tokens)) for tokens in simple_commands
    )
    directory_resolved = True
    cwd = base
    base_source = "the tool workdir"
    for simple_command in simple_commands:
        invocation = invocation_tokens(simple_command)
        waiver = command_waiver_reason(simple_command)
        classify = functools.partial(
            candidate_block_reason,
            probe,
            simple_command,
            cwd,
            shell_context_safe=shell_context_safe,
            directory_resolved=directory_resolved,
            base_source=base_source,
        )
        reason = classify(invocation)
        if reason and not waiver_admits(invocation, reason, waiver):
            return reason
        if invocation_is_unresolved_nested(invocation):
            return AMBIGUOUS_REASON
        for candidate in opaque_invocation_candidates(
            invocation, {"git", "semantic-commit"}
        ):
            if invocation_is_unresolved_nested(candidate):
                return AMBIGUOUS_REASON
            reason = classify(candidate)
            if reason and not waiver_admits(candidate, reason, waiver):
                return reason
        if not shell_command_changes_git_context(simple_command):
            continue
        # Raw Git keeps failing closed after any context change. Only the
        # governed CLI, which re-verifies its own repository, follows a literal
        # destination this guard can name.
        shell_context_safe = False
        target = (
            literal_directory_target(simple_command) if resolves_directories else None
        )
        if target is not None and Path(target).is_dir():
            cwd = Path(target)
            base_source = "a literal `cd` in the same command"
            continue
        directory_resolved = False
    return ""


def main() -> int:
    payload = read_payload()
    command = command_from(payload)
    if command:
        reason = command_block_reason(command, payload_base(payload))
        if reason:
            emit_block(reason)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
