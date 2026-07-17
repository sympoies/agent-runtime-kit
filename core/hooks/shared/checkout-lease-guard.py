#!/usr/bin/env python3
"""Coordinate one agent writer lease per physical Git checkout.

The guard deliberately recognizes only explicit edit tools and high-confidence
shell mutations. Read-only inspection stays available. Stop performs an audit
only: it never removes a worktree, branch, or lease.
"""

from __future__ import annotations

import fcntl
import functools
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    OPAQUE_NESTED_SHELL_COMMAND,
    OPAQUE_WRAPPER_COMMAND,
    apply_patch_paths,
    command_from,
    emit_block,
    invocation_command_position_is_dynamic,
    invocation_is_unresolved_nested,
    invocation_tokens,
    invocation_without_redirections,
    nested_shell_payload,
    opaque_invocation_has_unresolved_nested,
    output_redirect_targets,
    patch_text_candidates,
    read_payload,
    semantic_commit_invocation_state,
    session_marker_key,
    simple_commands,
    simple_commands_with_nested_shells,
    tool_input_dict,
)

EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"})
COMMAND_TOOLS = frozenset({"Bash"})
LEASE_SCHEMA = "agent-runtime.checkout-lease.v1"
INSTANCE_FILE = ".agent-runtime-checkout-instance"
DEFAULT_TTL_SECONDS = 8 * 60 * 60
MAX_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_LEASE_BYTES = 16 * 1024
GIT_TIMEOUT_SECONDS = 5
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_SECONDS = 0.05
MAX_RENEWAL_WINDOW_SECONDS = 15 * 60
MAX_REDIRECT_TARGETS = 32
SHELL_REDIRECT_EXPANSION_CHARS = frozenset("$`*?[{(")

MUTATING_EXECUTABLES = frozenset(
    {
        "chmod",
        "chown",
        "cp",
        "install",
        "ln",
        "mkdir",
        "mkfifo",
        "mknod",
        "mv",
        "patch",
        "rm",
        "rmdir",
        "tee",
        "touch",
        "truncate",
    }
)
MUTATING_GIT_SUBCOMMANDS = frozenset(
    {
        "add",
        "am",
        "apply",
        "checkout",
        "cherry-pick",
        "clean",
        "commit",
        "merge",
        "mv",
        "pull",
        "rebase",
        "reset",
        "restore",
        "revert",
        "rm",
        "switch",
        "update-index",
        "update-ref",
    }
)
SHELL_OPERATORS = frozenset({";", "&", "&&", "|", "||"})


@dataclass(frozen=True)
class Checkout:
    root: Path
    git_dir: Path
    common_dir: Path
    primary: bool


class LeaseError(RuntimeError):
    """Raised when lease identity or state cannot be trusted."""


class MutationScopeError(LeaseError):
    """Raised when a shell mutation cannot be bound to a checkout safely."""


class LeaseStatePathError(LeaseError):
    """Raised when the managed checkout-lease state path is unavailable."""


def tool_name(payload: Mapping[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def hook_event(payload: Mapping[str, Any]) -> str:
    for key in ("hook_event_name", "hookEventName"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def payload_base(payload: Mapping[str, Any]) -> Path:
    tool_input = tool_input_dict(payload)
    for value in (tool_input.get("workdir"), tool_input.get("cwd"), payload.get("cwd")):
        if isinstance(value, str) and value:
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = Path.cwd() / path
            return path.resolve(strict=False)
    return Path.cwd().resolve(strict=False)


def nested_edit_paths(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in {"file_path", "path", "filename", "notebook_path"}:
                if isinstance(nested, str) and nested:
                    yield nested
            else:
                yield from nested_edit_paths(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            yield from nested_edit_paths(nested)


def edit_paths(payload: Mapping[str, Any]) -> list[str]:
    paths = list(nested_edit_paths(tool_input_dict(payload)))
    for candidate in patch_text_candidates(payload):
        paths.extend(apply_patch_paths(candidate))
    return list(dict.fromkeys(paths))


def canonical_path(raw: str, base: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def existing_ancestor(path: Path) -> Path:
    candidate = path if path.is_dir() else path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    # Admission probes are read-only; optional index refreshes can otherwise
    # expose a transient index.lock that a concurrent admission misclassifies.
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LeaseError(f"git probe failed: {exc}") from exc


def listed_worktree_paths(base: Path) -> list[Path]:
    try:
        completed = subprocess.run(
            ["git-cli", "worktree", "list", "--format", "json"],
            cwd=base,
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MutationScopeError(
            f"managed worktree inventory failed: {exc}"
        ) from exc
    if completed.returncode != 0:
        raise MutationScopeError("managed worktree inventory failed")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MutationScopeError("managed worktree inventory is malformed") from exc
    data = payload.get("data") if isinstance(payload, Mapping) else None
    entries = data.get("entries") if isinstance(data, Mapping) else None
    if not isinstance(entries, list):
        raise MutationScopeError("managed worktree inventory is malformed")
    paths: list[Path] = []
    for entry in entries:
        raw_path = entry.get("path") if isinstance(entry, Mapping) else None
        if not isinstance(raw_path, str) or not raw_path:
            raise MutationScopeError("managed worktree inventory is malformed")
        paths.append(Path(raw_path).resolve(strict=False))
    return paths


def resolve_worktree_remove_target(raw: str, base: Path) -> Path:
    try:
        candidate = canonical_path(raw, base)
    except (OSError, RuntimeError) as exc:
        raise MutationScopeError(
            f"managed worktree target could not be resolved: {raw}"
        ) from exc
    expanded = Path(raw).expanduser()
    slug = (
        expanded.name
        if not expanded.is_absolute() and os.path.sep not in raw
        else ""
    )
    if slug:
        matches = [path for path in listed_worktree_paths(base) if path.name == slug]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise MutationScopeError(f"managed worktree slug is ambiguous: {raw}")
        raise MutationScopeError(
            f"managed worktree slug could not be resolved: {raw}"
        )
    if candidate.exists():
        return candidate
    exact = [path for path in listed_worktree_paths(base) if path == candidate]
    if len(exact) == 1:
        return exact[0]
    raise MutationScopeError(
        f"managed worktree target could not be resolved: {raw}"
    )


def absolute_git_path(raw: str, base: Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def checkout_from(path: Path) -> Checkout | None:
    probe = existing_ancestor(path)
    completed = run_git(probe, "rev-parse", "--show-toplevel")
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    root = Path(completed.stdout.strip()).resolve()

    git_dir_result = run_git(root, "rev-parse", "--absolute-git-dir")
    common_result = run_git(root, "rev-parse", "--git-common-dir")
    if git_dir_result.returncode != 0 or common_result.returncode != 0:
        raise LeaseError("Git checkout identity could not be resolved")
    git_dir = absolute_git_path(git_dir_result.stdout.strip(), root)
    common_dir = absolute_git_path(common_result.stdout.strip(), root)
    return Checkout(
        root=root,
        git_dir=git_dir,
        common_dir=common_dir,
        primary=git_dir == common_dir,
    )


def crosses_nested_checkout_boundary(target: Path, checkout: Checkout) -> bool:
    if target == checkout.root or checkout.root not in target.parents:
        return False
    candidate = existing_ancestor(target)
    while candidate != checkout.root and checkout.root in candidate.parents:
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return True
        candidate = candidate.parent
    return False


def target_checkouts(payload: Mapping[str, Any], tool: str) -> list[Checkout]:
    base = payload_base(payload)
    checkouts: dict[str, Checkout] = {}
    if tool in EDIT_TOOLS:
        base_checkout = checkout_from(base)
        for raw in edit_paths(payload):
            target = canonical_path(raw, base)
            known_checkouts = (
                ([base_checkout] if base_checkout is not None else [])
                + list(checkouts.values())
            )
            enclosing = next(
                (
                    known
                    for known in sorted(
                        known_checkouts,
                        key=lambda item: len(item.root.parts),
                        reverse=True,
                    )
                    if target == known.root or known.root in target.parents
                ),
                None,
            )
            checkout = next(
                (
                    known
                    for known in known_checkouts
                    if target == known.root or known.root in target.parents
                    if not crosses_nested_checkout_boundary(target, known)
                ),
                None,
            )
            if checkout is None:
                checkout = checkout_from(target)
            if checkout is None and enclosing is not None:
                raise LeaseError(
                    "explicit edit target crosses an unresolved nested checkout boundary"
                )
            if checkout is not None:
                checkouts[str(checkout.root)] = checkout
    elif tool in COMMAND_TOOLS:
        command = command_from(payload)
        targets = managed_worktree_remove_targets(command, base)
        if targets:
            for target in targets:
                checkout = checkout_from(target)
                if checkout is not None:
                    checkouts[str(checkout.root)] = checkout
        else:
            checkout = checkout_from(base)
            if checkout is not None:
                checkouts[str(checkout.root)] = checkout
    return [checkouts[key] for key in sorted(checkouts)]


def git_action(arguments: list[str]) -> tuple[str, list[str]]:
    index = 0
    options_with_values = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
    while index < len(arguments):
        token = arguments[index]
        if token == "--":
            index += 1
            break
        if token in options_with_values:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token, arguments[index + 1 :]
    if index < len(arguments):
        return arguments[index], arguments[index + 1 :]
    return "", []


def git_invocation_mutates(arguments: list[str]) -> bool:
    subcommand, action = git_action(arguments)
    if subcommand in MUTATING_GIT_SUBCOMMANDS:
        return True
    if subcommand == "branch":
        if not action:
            return False
        if any(
            flag in action
            for flag in (
                "-d",
                "-D",
                "-m",
                "-M",
                "-c",
                "-C",
                "--delete",
                "--move",
                "--copy",
                "--edit-description",
                "--set-upstream-to",
                "--unset-upstream",
            )
        ):
            return True
        if any(
            flag in action
            for flag in (
                "-a",
                "--all",
                "-l",
                "--list",
                "-r",
                "--remotes",
                "-v",
                "-vv",
                "--verbose",
                "--show-current",
                "--contains",
                "--no-contains",
                "--merged",
                "--no-merged",
                "--points-at",
                "--format",
                "--sort",
                "--column",
                "--no-column",
                "--color",
                "--no-color",
                "--ignore-case",
                "--omit-empty",
            )
        ):
            return False
        if any(
            argument.startswith(
                (
                    "--contains=",
                    "--no-contains=",
                    "--merged=",
                    "--no-merged=",
                    "--points-at=",
                    "--format=",
                    "--sort=",
                    "--column=",
                    "--color=",
                )
            )
            or re.fullmatch(r"-[arv]+", argument) is not None
            for argument in action
        ):
            return False
        return True
    if subcommand == "tag":
        if not action:
            return False
        if any(
            flag in action
            for flag in (
                "-a",
                "-d",
                "-f",
                "-F",
                "-m",
                "-s",
                "-u",
                "--annotate",
                "--delete",
                "--force",
                "--file",
                "--message",
                "--sign",
                "--local-user",
            )
        ):
            return True
        if any(
            flag in action
            for flag in (
                "-l",
                "--list",
                "-n",
                "-v",
                "--verify",
                "--contains",
                "--no-contains",
                "--merged",
                "--no-merged",
                "--points-at",
                "--format",
                "--sort",
                "--column",
                "--no-column",
                "--color",
                "--no-color",
                "--ignore-case",
                "--omit-empty",
            )
        ):
            return False
        if any(
            argument.startswith(
                (
                    "--contains=",
                    "--no-contains=",
                    "--merged=",
                    "--no-merged=",
                    "--points-at=",
                    "--format=",
                    "--sort=",
                    "--column=",
                    "--color=",
                )
            )
            or re.fullmatch(r"-n\d*", argument) is not None
            for argument in action
        ):
            return False
        return True
    if subcommand == "stash":
        return not action or action[0] not in {"list", "show"}
    if subcommand == "bisect":
        return not action or action[0] not in {"log", "terms", "view", "visualize"}
    if subcommand == "worktree":
        return bool(action) and action[0] != "list"
    return False


def git_cli_invocation_mutates(arguments: list[str]) -> bool:
    return len(arguments) >= 2 and arguments[0] == "worktree" and arguments[1] in {
        "add",
        "lock",
        "move",
        "prune",
        "remove",
        "repair",
        "unlock",
    }


def semantic_commit_invocation_mutates(arguments: list[str]) -> bool:
    if not arguments or arguments[0] not in {"commit", "fixup", "squash"}:
        return False
    read_only, _repo = semantic_commit_invocation_state(arguments)
    return not read_only


def is_managed_worktree_remove(invocation: list[str]) -> bool:
    return (
        len(invocation) >= 4
        and os.path.basename(invocation[0]) == "git-cli"
        and invocation[1:3] == ["worktree", "remove"]
    )


def is_managed_worktree_add(invocation: list[str]) -> bool:
    return (
        len(invocation) >= 3
        and os.path.basename(invocation[0]) == "git-cli"
        and invocation[1:3] == ["worktree", "add"]
    )


def worktree_remove_target_argument(invocation: list[str]) -> str:
    # Drop redirections and their operands first: the agent Bash tool wraps every
    # command as `eval '…' < /dev/null && pwd -P >| <cwd>`, so the recursed
    # removal arrives as `git-cli worktree remove <slug> < /dev/null`. Without
    # this, the `< /dev/null` operand is misread as a second removal target.
    invocation = invocation_without_redirections(invocation)
    target = ""
    index = 3
    while index < len(invocation):
        argument = invocation[index]
        if argument == "--":
            index += 1
            while index < len(invocation):
                if target:
                    raise MutationScopeError(
                        "managed worktree removal has multiple targets"
                    )
                target = invocation[index]
                index += 1
            break
        if argument == "--format":
            if index + 1 >= len(invocation):
                raise MutationScopeError(
                    "managed worktree removal --format needs a value"
                )
            index += 2
            continue
        if argument.startswith("--format="):
            index += 1
            continue
        if argument.startswith("-"):
            raise MutationScopeError(
                f"managed worktree removal option is unsupported: {argument}"
            )
        if target:
            raise MutationScopeError(
                "managed worktree removal has multiple targets"
            )
        target = argument
        index += 1
    if not target:
        raise MutationScopeError("managed worktree removal target is missing")
    return target


def executable_invocation_mutates(invocation: list[str]) -> bool:
    """Whether the invoked executable is a working-tree mutation on its own.

    This is the executable-based half of ``simple_command_mutates``, independent
    of any shell redirection. It lets the worktree-removal scope test count a
    redirection as a mutation only when its target actually writes a repository
    (see ``co_command_is_repo_mutation``)."""
    if not invocation:
        return False
    executable = os.path.basename(invocation[0])
    arguments = invocation[1:]
    if executable in {OPAQUE_WRAPPER_COMMAND, OPAQUE_NESTED_SHELL_COMMAND}:
        return True
    if executable in MUTATING_EXECUTABLES:
        return True
    if executable == "git" and git_invocation_mutates(arguments):
        return True
    if executable == "git-cli" and git_cli_invocation_mutates(arguments):
        return True
    if executable == "semantic-commit":
        return semantic_commit_invocation_mutates(arguments)
    if executable in {"sed", "perl", "ruby"} and any(
        argument == "-i" or argument.startswith("-i") or "i" in argument[1:]
        for argument in arguments
        if argument.startswith("-")
    ):
        return True
    if executable == "find" and "-delete" in arguments:
        return True
    return executable == "dd" and any(
        argument.startswith("of=") for argument in arguments
    )


def simple_command_mutates(tokens: list[str], base: Path) -> bool:
    return executable_invocation_mutates(invocation_tokens(tokens)) or command_writes_repo(
        tokens, base
    )


@functools.lru_cache(maxsize=256)
def resolved_target_may_touch_checkout(raw_target: str) -> bool:
    """Whether a canonical absolute target is or may alias a Git checkout.

    Redirect admission needs only a conservative membership decision, not full
    checkout identity. Walking for a .git marker avoids repeated Git subprocess
    probes in the per-command hook hot path. Symlinks are resolved first,
    multiply-linked regular files fail closed, and any untrusted filesystem
    result is treated as a possible checkout write.
    """
    try:
        target = Path(raw_target).expanduser().resolve(strict=False)
        metadata = target.stat()
    except FileNotFoundError:
        metadata = None
        try:
            target = Path(raw_target).expanduser().resolve(strict=False)
        except (OSError, RuntimeError):
            return True
    except (OSError, RuntimeError):
        return True

    if (
        metadata is not None
        and stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink > 1
    ):
        return True

    candidate = (
        target
        if metadata is not None and stat.S_ISDIR(metadata.st_mode)
        else target.parent
    )
    while True:
        try:
            (candidate / ".git").lstat()
        except FileNotFoundError:
            pass
        except OSError:
            return True
        else:
            return True
        if candidate == candidate.parent:
            return False
        candidate = candidate.parent


def redirect_target_is_repo_write(raw_target: str, base: Path) -> bool:
    """Whether an output-redirect target is (or may be) a write into a checkout.

    A redirect to ``/dev/null`` is never a real write, and an **absolute** target
    that resolves outside every Git checkout is not a repository mutation — this
    is what lets the harness command wrapper's ``2>/dev/null`` and
    ``pwd -P >| <cwd-sentinel>`` (both absolute) pass the sole-mutation test.

    A **relative** target is treated as a write: it resolves against the shell's
    live working directory, which an intervening ``cd`` can move into the
    checkout, so a static resolution against ``base`` cannot prove it lands
    outside. Dynamic, pathname-expanded, brace-expanded, and otherwise
    unresolvable targets fail closed for the same reason.
    """
    if any(character in raw_target for character in SHELL_REDIRECT_EXPANSION_CHARS):
        return True
    try:
        expanded = Path(raw_target).expanduser()
    except (OSError, RuntimeError):
        return True
    if not expanded.is_absolute():
        return True
    if expanded == Path(os.devnull):
        return False
    return resolved_target_may_touch_checkout(str(expanded))


def command_writes_repo(tokens: list[str], base: Path) -> bool:
    """Whether any output redirection in a simple command writes a checkout."""
    targets = output_redirect_targets(tokens)
    if len(targets) > MAX_REDIRECT_TARGETS:
        return True
    return any(
        redirect_target_is_repo_write(target, base)
        for target, _inspectable in targets
    )


def coresident_command_is_repo_mutation(tokens: list[str], base: Path) -> bool:
    """Apply the shared mutation policy to a worktree-removal peer command."""
    return simple_command_mutates(tokens, base)


@functools.lru_cache(maxsize=32)
def parsed_shell_commands(command: str) -> tuple[list[str], ...]:
    """Parse one shell command once for all admission decisions."""
    return tuple(simple_commands_with_nested_shells(command))


def source_has_parenthesized_redirect_word(source: str) -> bool:
    """Detect an unquoted ``(`` in an output-redirect word before tokenization.

    The shared best-effort shell lexer treats parentheses as command separators.
    That is correct for subshells, but it discards redirect-word provenance for
    Bash extglob and similar expansion forms before ``output_redirect_targets``
    can fail closed. Scan the raw source narrowly at output redirects so ordinary
    subshell syntax does not turn otherwise read-only commands into mutations.
    """
    quote: str | None = None
    index = 0
    while index < len(source):
        character = source[index]
        if quote == "'":
            if character == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if character == "\\" and index + 1 < len(source):
                index += 2
                continue
            if character == '"':
                quote = None
            index += 1
            continue
        if character == "\\" and index + 1 < len(source):
            index += 2
            continue
        if character in {"'", '"'}:
            quote = character
            index += 1
            continue
        if character != ">":
            index += 1
            continue

        target_index = index + 1
        if target_index < len(source) and source[target_index] in {">", "|"}:
            target_index += 1
        while target_index < len(source) and source[target_index].isspace():
            target_index += 1

        target_quote: str | None = None
        while target_index < len(source):
            target_character = source[target_index]
            if target_quote == "'":
                if target_character == "'":
                    target_quote = None
                target_index += 1
                continue
            if target_quote == '"':
                if target_character == "\\" and target_index + 1 < len(source):
                    target_index += 2
                    continue
                if target_character == '"':
                    target_quote = None
                target_index += 1
                continue
            if target_character == "\\" and target_index + 1 < len(source):
                target_index += 2
                continue
            if target_character in {"'", '"'}:
                target_quote = target_character
                target_index += 1
                continue
            if target_character == "(":
                return True
            if target_character.isspace() or target_character in ";&|<>":
                break
            target_index += 1
        index = max(index + 1, target_index)
    return False


@functools.lru_cache(maxsize=32)
def shell_command_has_parenthesized_redirect_word(command: str) -> bool:
    """Inspect direct and nested shell sources for lexer-splitting redirects."""
    pending = [(command, 0)]
    seen: set[tuple[int, str]] = set()
    while pending:
        source, depth = pending.pop()
        key = (depth, source)
        if key in seen:
            continue
        seen.add(key)
        if source_has_parenthesized_redirect_word(source):
            return True
        if depth >= 5:
            continue
        for tokens in simple_commands(source):
            payload = nested_shell_payload(invocation_tokens(tokens))
            if payload:
                pending.append((payload, depth + 1))
    return False


def redirect_budget_exceeded(commands: Iterable[list[str]]) -> bool:
    redirect_count = 0
    for tokens in commands:
        redirect_count += len(output_redirect_targets(tokens))
        if redirect_count > MAX_REDIRECT_TARGETS:
            return True
    return False


@functools.lru_cache(maxsize=32)
def shell_command_exceeds_redirect_budget(command: str) -> bool:
    return redirect_budget_exceeded(parsed_shell_commands(command))


def managed_worktree_remove_targets(command: str, base: Path) -> list[Path]:
    commands = parsed_shell_commands(command)
    over_redirect_budget = shell_command_exceeds_redirect_budget(command)
    target_arguments: list[str] = []
    other_mutation = shell_command_has_parenthesized_redirect_word(command)
    for tokens in commands:
        if invocation_command_position_is_dynamic(tokens):
            raise MutationScopeError(
                "shell mutation target scope is unresolved and cannot be leased safely"
            )
        invocation = invocation_tokens(tokens)
        if invocation_is_unresolved_nested(
            invocation
        ) or opaque_invocation_has_unresolved_nested(invocation):
            raise MutationScopeError(
                "shell mutation target scope is unresolved and cannot be leased safely"
            )
        if not is_managed_worktree_remove(invocation):
            if not over_redirect_budget:
                other_mutation = other_mutation or coresident_command_is_repo_mutation(
                    tokens, base
                )
            continue
        if over_redirect_budget:
            raise MutationScopeError(
                "shell redirect target count exceeds the safe inspection limit"
            )
        if command_writes_repo(tokens, base):
            other_mutation = True
        target_arguments.append(worktree_remove_target_argument(invocation))
    if len(target_arguments) > 1:
        raise MutationScopeError(
            "exactly one managed worktree removal is allowed per shell command"
        )
    if target_arguments and other_mutation:
        raise MutationScopeError(
            "managed worktree removal must be the sole mutating command"
        )
    if not target_arguments:
        return []
    return [resolve_worktree_remove_target(target_arguments[0], base)]


def high_confidence_shell_mutation(command: str, base: Path | None = None) -> bool:
    resolved_base = base if base is not None else Path.cwd()
    commands = parsed_shell_commands(command)
    if shell_command_exceeds_redirect_budget(
        command
    ) or shell_command_has_parenthesized_redirect_word(command):
        return True
    return any(
        simple_command_mutates(tokens, resolved_base)
        for tokens in commands
    )


def sole_managed_worktree_add(command: str, base: Path) -> bool:
    """True when the command's only mutation is one ``git-cli worktree add``.

    ``git-cli worktree add`` creates a brand-new checkout; it never writes the
    current checkout's working tree, so it needs no lease on the current
    checkout. It is also the exact command ``worktree_guidance()`` tells a
    blocked agent to run, so gating it deadlocks an agent on a non-default
    primary checkout: the recommended escape is refused by the same gate.

    This mirrors only the single-mutation narrowness of the ``worktree remove``
    carve-out: clear it only when it is the sole repository-mutating command, so
    it can never smuggle another working-tree write past the admission gate. Any
    ambiguity — a dynamic command position, an unresolved nested shell, a second
    add, or a co-resident repository write — falls through to normal fail-closed
    gating. Redirect scoping (``command_writes_repo``) matches the removal
    carve-out so the trusted harness command wrapper (``2>/dev/null``,
    ``pwd -P >| <cwd>``) does not defeat it. Unlike ``worktree remove`` (which
    redirects the lease onto the removed checkout and so still requires a
    verifiable session and lease), ``main()`` short-circuits a matched add to
    ALLOW before the session-identity gate and acquires no lease, because add
    takes no lease on the current checkout.
    """
    commands = parsed_shell_commands(command)
    if shell_command_exceeds_redirect_budget(
        command
    ) or shell_command_has_parenthesized_redirect_word(command):
        return False
    found_add = False
    for tokens in commands:
        if invocation_command_position_is_dynamic(tokens):
            return False
        invocation = invocation_tokens(tokens)
        if invocation_is_unresolved_nested(
            invocation
        ) or opaque_invocation_has_unresolved_nested(invocation):
            return False
        if is_managed_worktree_add(invocation):
            if found_add or command_writes_repo(tokens, base):
                return False
            found_add = True
            continue
        if coresident_command_is_repo_mutation(tokens, base):
            return False
    return found_add


def lease_ttl_seconds() -> int:
    raw = os.environ.get("AGENT_RUNTIME_CHECKOUT_LEASE_TTL_SECONDS", "").strip()
    if not raw:
        return DEFAULT_TTL_SECONDS
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_TTL_SECONDS
    return max(60, min(parsed, MAX_TTL_SECONDS))


def state_root() -> Path:
    override = os.environ.get("AGENT_RUNTIME_CHECKOUT_LEASE_STATE_HOME", "").strip()
    if override:
        root = Path(override).expanduser()
    else:
        runtime = os.environ.get("AGENT_RUNTIME_STATE_HOME", "").strip()
        if runtime:
            root = Path(runtime).expanduser() / "checkout-leases"
        else:
            xdg = os.environ.get("XDG_STATE_HOME", "").strip()
            base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "state"
            root = base / "agent-runtime-kit" / "checkout-leases"
    return root.resolve(strict=False)


def private_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise LeaseStatePathError(
            f"checkout lease state directory unavailable: {exc}"
        ) from exc
    if path.is_symlink() or not path.is_dir():
        raise LeaseStatePathError(
            "checkout lease state directory is not a trusted directory"
        )
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise LeaseStatePathError(
            f"checkout lease state permissions failed: {exc}"
        ) from exc


def repository_state_dir(checkout: Checkout, *, create: bool = True) -> Path:
    repo_key = hashlib.sha256(str(checkout.common_dir).encode("utf-8")).hexdigest()
    path = state_root() / repo_key
    if create:
        private_directory(path)
    return path


def checkout_state_dir(checkout: Checkout, *, create: bool = True) -> Path:
    checkout_key = hashlib.sha256(str(checkout.root).encode("utf-8")).hexdigest()
    path = repository_state_dir(checkout, create=create) / checkout_key
    if create:
        private_directory(path)
    return path


def acquire_lock(directory: Path):
    path = directory / "lease.lock"
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise LeaseStatePathError(
            f"checkout lease lock unavailable: {exc}"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LeaseStatePathError(
                "checkout lease lock is not a regular file"
            )
        handle = os.fdopen(descriptor, "a+", encoding="utf-8")
        descriptor = -1
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise LeaseError(
                        "checkout lease lock timed out; another hook may be stalled"
                    ) from exc
                time.sleep(LOCK_POLL_SECONDS)
        return handle
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def read_regular_file(path: Path, *, max_bytes: int) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise LeaseError(f"checkout lease file unavailable: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
            raise LeaseError("checkout lease file is not a bounded regular file")
        return os.read(descriptor, max_bytes + 1).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LeaseError("checkout lease file is not UTF-8") from exc
    finally:
        os.close(descriptor)


def write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise LeaseError("checkout instance sentinel write made no progress")
        offset += written


def read_instance(checkout: Checkout, *, create: bool) -> str:
    path = checkout.git_dir / INSTANCE_FILE
    raw = read_regular_file(path, max_bytes=128).strip()
    if raw:
        if re.fullmatch(r"[0-9a-f]{32}", raw) is None:
            raise LeaseError("checkout instance sentinel is malformed")
        return raw
    if not create:
        return ""

    value = uuid.uuid4().hex
    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{INSTANCE_FILE}-", dir=checkout.git_dir
        )
        os.fchmod(descriptor, 0o600)
        write_all(descriptor, f"{value}\n".encode("ascii"))
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            raw = read_regular_file(path, max_bytes=128).strip()
            if re.fullmatch(r"[0-9a-f]{32}", raw) is None:
                raise LeaseError("checkout instance sentinel is malformed")
            return raw
        directory_fd = os.open(
            checkout.git_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise LeaseError(f"checkout instance sentinel unavailable: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return value


def load_lease(path: Path) -> dict[str, Any] | None:
    try:
        raw = read_regular_file(path, max_bytes=MAX_LEASE_BYTES)
    except LeaseError as exc:
        raise LeaseStatePathError(str(exc)) from exc
    if not raw:
        return None
    try:
        lease = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LeaseStatePathError("checkout lease state is malformed") from exc
    if not isinstance(lease, dict) or lease.get("schema") != LEASE_SCHEMA:
        raise LeaseStatePathError(
            "checkout lease state has an unsupported schema"
        )
    if re.fullmatch(r"[0-9a-f]{64}", str(lease.get("session_key", ""))) is None:
        raise LeaseStatePathError(
            "checkout lease session identity is malformed"
        )
    if re.fullmatch(r"[0-9a-f]{32}", str(lease.get("checkout_instance", ""))) is None:
        raise LeaseStatePathError(
            "checkout lease instance identity is malformed"
        )
    if not isinstance(lease.get("expires_at"), int | float):
        raise LeaseStatePathError("checkout lease expiry is malformed")
    for key in ("checkout_root", "checkout_git_dir"):
        value = lease.get(key)
        if value is not None and (
            not isinstance(value, str) or not value or not Path(value).is_absolute()
        ):
            raise LeaseStatePathError(f"checkout lease {key} is malformed")
    return lease


def write_lease(path: Path, lease: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(lease), sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".lease-", dir=path.parent)
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
        temporary = ""
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise LeaseStatePathError(
            f"checkout lease state write failed: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def checkout_dirty(checkout: Checkout) -> bool:
    result = run_git(
        checkout.root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if result.returncode != 0:
        raise LeaseError("Git dirty-state probe failed")
    return bool(result.stdout)


def git_operation(checkout: Checkout) -> str:
    candidates = (
        ("merge", "MERGE_HEAD"),
        ("cherry-pick", "CHERRY_PICK_HEAD"),
        ("revert", "REVERT_HEAD"),
        ("rebase", "rebase-merge"),
        ("rebase", "rebase-apply"),
        ("sequencer", "sequencer"),
        ("bisect", "BISECT_LOG"),
        ("index update", "index.lock"),
    )
    for name, marker in candidates:
        result = run_git(checkout.root, "rev-parse", "--git-path", marker)
        if result.returncode != 0 or not result.stdout.strip():
            raise LeaseError("Git operation-state probe failed")
        path = absolute_git_path(result.stdout.strip(), checkout.root)
        if path.exists():
            return name
    return ""


def current_branch(checkout: Checkout) -> str:
    result = run_git(checkout.root, "symbolic-ref", "--quiet", "--short", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else ""


def default_branch(checkout: Checkout) -> str:
    result = run_git(
        checkout.root,
        "symbolic-ref",
        "--quiet",
        "--short",
        "refs/remotes/origin/HEAD",
    )
    if result.returncode == 0 and result.stdout.strip():
        remote_ref = result.stdout.strip()
        return remote_ref.split("/", 1)[1] if "/" in remote_ref else remote_ref
    return ""


def new_lease(
    checkout: Checkout,
    session_key: str,
    instance: str,
    *,
    previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    now = int(time.time())
    acquired_at = previous.get("acquired_at") if previous else now
    if not isinstance(acquired_at, int | float):
        acquired_at = now
    return {
        "schema": LEASE_SCHEMA,
        "session_key": session_key,
        "checkout_instance": instance,
        "checkout_root": str(checkout.root),
        "checkout_git_dir": str(checkout.git_dir),
        "acquired_at": acquired_at,
        "refreshed_at": now,
        "expires_at": now + lease_ttl_seconds(),
    }


def worktree_guidance() -> str:
    return (
        "Create an isolated checkout with `git-cli worktree add <slug>`, then move "
        "into it with the harness worktree-entry affordance (for example Claude "
        "Code's `EnterWorktree`) and retry there. A shell `cd` does not change the "
        "checkout this guard evaluates, and a sole `git-cli worktree add` is itself "
        "allowed even from a blocked checkout."
    )


def lease_error_block_reason(error: LeaseError) -> str:
    if isinstance(error, MutationScopeError):
        return (
            "Checkout mutation scope could not be verified and fails closed: "
            f"{error}. Use a concrete executable and, for managed worktree removal, "
            "an explicit target, then retry."
        )
    if isinstance(error, LeaseStatePathError):
        return (
            "Checkout lease state path could not be verified, so repository mutation "
            f"fails closed: {error}. Restore the managed runtime state path, then "
            "retry."
        )
    return (
        "Checkout lease state could not be verified, so repository mutation fails "
        f"closed: {error}."
    )


def renewal_due(lease: Mapping[str, Any], now: float) -> bool:
    window = min(MAX_RENEWAL_WINDOW_SECONDS, max(15, lease_ttl_seconds() // 4))
    return float(lease["expires_at"]) - now <= window


def live_foreign_lease_reason(
    lease: Mapping[str, Any] | None,
    *,
    instance: str,
    session_key: str,
    now: float,
) -> str:
    if (
        lease
        and lease["checkout_instance"] == instance
        and lease["session_key"] != session_key
        and float(lease["expires_at"]) > now
    ):
        return (
            "Checkout mutation is blocked because another agent session owns the "
            f"active checkout lease. {worktree_guidance()}"
        )
    return ""


def checkout_admission_reason(checkout: Checkout) -> str:
    operation = git_operation(checkout)
    if operation:
        return (
            f"Checkout mutation is blocked because a Git operation ({operation}) is "
            f"already in progress without this session's lease. {worktree_guidance()}"
        )
    if checkout_dirty(checkout):
        return (
            "Checkout mutation is blocked because the checkout has unowned changes. "
            f"Preserve those changes and inspect their owner; do not discard them. {worktree_guidance()}"
        )
    if checkout.primary:
        branch = current_branch(checkout)
        expected = default_branch(checkout)
        if not branch or not expected or branch != expected:
            return (
                "The clean primary-checkout direct-edit exception applies only on the "
                f"resolved default branch; current={branch or 'detached'}, "
                f"default={expected or 'unknown'}. {worktree_guidance()}"
            )
    return ""


def acquire_or_refresh(checkout: Checkout, session_key: str) -> str:
    instance = read_instance(checkout, create=True)
    directory = checkout_state_dir(checkout)
    lease_path = directory / "lease.json"
    with acquire_lock(directory):
        lease = load_lease(lease_path)
        now = time.time()
        same_instance = bool(lease and lease["checkout_instance"] == instance)
        if same_instance and lease and lease["session_key"] == session_key:
            if renewal_due(lease, now):
                write_lease(
                    lease_path,
                    new_lease(checkout, session_key, instance, previous=lease),
                )
            return ""
        reason = live_foreign_lease_reason(
            lease, instance=instance, session_key=session_key, now=now
        )
        if reason:
            return reason

    reason = checkout_admission_reason(checkout)
    if reason:
        return reason
    if read_instance(checkout, create=False) != instance:
        raise LeaseError("checkout instance changed during lease admission")

    with acquire_lock(directory):
        lease = load_lease(lease_path)
        now = time.time()
        if (
            lease
            and lease["checkout_instance"] == instance
            and lease["session_key"] == session_key
        ):
            if renewal_due(lease, now):
                write_lease(
                    lease_path,
                    new_lease(checkout, session_key, instance, previous=lease),
                )
            return ""
        reason = live_foreign_lease_reason(
            lease, instance=instance, session_key=session_key, now=now
        )
        if reason:
            return reason
        if read_instance(checkout, create=False) != instance:
            raise LeaseError("checkout instance changed before lease commit")
        write_lease(
            lease_path,
            new_lease(checkout, session_key, instance, previous=None),
        )
    return ""


def prune_removed_checkout_leases(checkout: Checkout) -> int:
    repository_dir = repository_state_dir(checkout, create=False)
    if not repository_dir.is_dir() or repository_dir.is_symlink():
        return 0
    removed = 0
    for directory in repository_dir.iterdir():
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or re.fullmatch(r"[0-9a-f]{64}", directory.name) is None
        ):
            continue
        lease_path = directory / "lease.json"
        try:
            with acquire_lock(directory):
                lease = load_lease(lease_path)
                if lease is None:
                    continue
                root_value = lease.get("checkout_root")
                git_dir_value = lease.get("checkout_git_dir")
                if not isinstance(root_value, str) or not isinstance(git_dir_value, str):
                    continue
                if Path(root_value).exists() or Path(git_dir_value).exists():
                    continue
                lease_path.unlink(missing_ok=True)
                removed += 1
        except (LeaseError, OSError):
            continue
    return removed


def emit_system_message(message: str) -> None:
    sys.stdout.write(json.dumps({"systemMessage": message}))
    sys.stdout.write("\n")


def release_clean_session_leases(
    repository_checkout: Checkout, session_key: str
) -> tuple[int, int, int]:
    repository_dir = repository_state_dir(repository_checkout, create=False)
    if not repository_dir.is_dir() or repository_dir.is_symlink():
        return 0, 0, 0
    released = 0
    retained = 0
    foreign = 0
    for directory in repository_dir.iterdir():
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or re.fullmatch(r"[0-9a-f]{64}", directory.name) is None
        ):
            continue
        lease_path = directory / "lease.json"
        try:
            with acquire_lock(directory):
                lease = load_lease(lease_path)
            if lease is None:
                continue
            if lease["session_key"] != session_key:
                if float(lease["expires_at"]) > time.time():
                    foreign += 1
                continue
            root_value = lease.get("checkout_root")
            git_dir_value = lease.get("checkout_git_dir")
            if not isinstance(root_value, str) or not isinstance(git_dir_value, str):
                retained += 1
                continue
            checkout = checkout_from(Path(root_value))
            if (
                checkout is None
                or checkout.root != Path(root_value).resolve(strict=False)
                or checkout.git_dir != Path(git_dir_value).resolve(strict=False)
                or checkout.common_dir != repository_checkout.common_dir
                or read_instance(checkout, create=False)
                != lease["checkout_instance"]
            ):
                retained += 1
                continue
            if git_operation(checkout) or checkout_dirty(checkout):
                retained += 1
                continue
            with acquire_lock(directory):
                current = load_lease(lease_path)
                if (
                    current
                    and current["checkout_instance"] == lease["checkout_instance"]
                    and current["session_key"] == session_key
                ):
                    lease_path.unlink(missing_ok=True)
                    released += 1
        except (LeaseError, OSError):
            retained += 1
    return released, retained, foreign


def stop_audit(payload: Mapping[str, Any]) -> int:
    session_key = session_marker_key(payload)
    if not session_key:
        return ALLOW
    try:
        checkout = checkout_from(payload_base(payload))
        if checkout is None:
            return ALLOW
        pruned = prune_removed_checkout_leases(checkout)
        released, retained, foreign = release_clean_session_leases(
            checkout, session_key
        )
        details: list[str] = []
        if released:
            details.append(f"released {released} clean same-session lease(s)")
        if retained:
            details.append(f"retained {retained} non-clean or unverifiable lease(s)")
        if foreign:
            details.append(f"observed {foreign} active foreign lease(s)")
        if pruned:
            details.append(f"pruned {pruned} removed-worktree lease record(s)")
        if details:
            emit_system_message(
                "Checkout lease audit "
                + "; ".join(details)
                + ". Stop removed no worktree or branch."
            )
    except LeaseError as exc:
        emit_system_message(f"Checkout lease audit could not verify ownership: {exc}.")
    return ALLOW


def main() -> int:
    payload = read_payload()
    if hook_event(payload) == "Stop":
        return stop_audit(payload)

    tool = tool_name(payload)
    if tool not in EDIT_TOOLS | COMMAND_TOOLS:
        return ALLOW
    if tool in COMMAND_TOOLS:
        command = command_from(payload)
        if not high_confidence_shell_mutation(command, payload_base(payload)):
            return ALLOW
        # `git-cli worktree add` creates a new checkout and is the sanctioned
        # escape the guard recommends; never let the admission gate block its own
        # remediation. Restricted to a sole add with no co-resident repository
        # write so it cannot cover a working-tree mutation. This intentionally
        # short-circuits before the session-identity gate and acquires no lease:
        # add takes no lease on the current checkout.
        if sole_managed_worktree_add(command, payload_base(payload)):
            return ALLOW
    if tool in EDIT_TOOLS and not edit_paths(payload):
        emit_block(
            "Checkout lease enforcement could not resolve an explicit edit target and "
            "fails closed. Retry with an explicit repository path."
        )
        return ALLOW

    session_key = session_marker_key(payload)
    if not session_key:
        emit_block(
            "Repository mutation requires a verifiable agent session identity for the "
            "checkout lease; retry from a supported Codex or Claude session."
        )
        return ALLOW

    try:
        checkouts = target_checkouts(payload, tool)
        if tool in EDIT_TOOLS and len(checkouts) > 1:
            emit_block(
                "One explicit edit spans multiple checkouts, so lease acquisition is "
                "blocked before claiming either checkout. Split the edit by checkout."
            )
            return ALLOW
        for checkout in checkouts:
            reason = acquire_or_refresh(checkout, session_key)
            if reason:
                emit_block(reason)
                return ALLOW
    except LeaseError as exc:
        emit_block(lease_error_block_reason(exc))
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
