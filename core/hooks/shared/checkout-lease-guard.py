#!/usr/bin/env python3
"""Coordinate one agent writer lease per physical Git checkout in enforce mode.

The lease is an opt-in strict coordination layer selected with
``AGENT_SESSION_COORDINATION_MODE=enforce``. Advisory, off, invalid, and absent
mode values never acquire or block on a lease. In enforce mode the guard
recognizes only explicit edit tools and high-confidence shell mutations.
Read-only inspection stays available. Stop performs an audit only: it never
removes a worktree, branch, or lease.
"""

from __future__ import annotations

import fcntl
import functools
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
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
    effective_workdir,
    emit_block,
    invocation_command_position_is_dynamic,
    invocation_is_unresolved_nested,
    invocation_tokens,
    is_managed_cli_home_bin,
    invocation_without_redirections,
    is_assignment,
    is_git_recovery_argv,
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
LEASE_V1_SCHEMA = "agent-runtime.checkout-lease.v1"
LEASE_V2_SCHEMA = "agent-runtime.checkout-lease.v2"
SNAPSHOT_SCHEMA = "agent-runtime.dirty-checkout-snapshot.v1"
CHALLENGE_SCHEMA = "agent-runtime.dirty-checkout-challenge.v1"
ADOPTION_SCHEMA = "agent-runtime.dirty-checkout-adoption.v1"
RECEIPT_SCHEMA = "agent-runtime.dirty-checkout-receipt.v1"
INSTANCE_FILE = ".agent-runtime-checkout-instance"
DEFAULT_TTL_SECONDS = 8 * 60 * 60
MAX_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_LEASE_BYTES = 16 * 1024
GIT_TIMEOUT_SECONDS = 5
DIRTY_SNAPSHOT_TIMEOUT_SECONDS = 35
CHALLENGE_TTL_SECONDS = 5 * 60
MAX_CHALLENGE_FILES = 128
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_SECONDS = 0.05
MAX_RENEWAL_WINDOW_SECONDS = 15 * 60
MAX_REDIRECT_TARGETS = 32
MAX_U64 = (1 << 64) - 1
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
DYNAMIC_ARGUMENT_CHARS = frozenset("$`*?[{(")
LEASE_V2_KEYS = frozenset(
    {
        "schema",
        "session_key",
        "checkout_instance",
        "checkout_root",
        "checkout_git_dir",
        "checkout_root_bytes",
        "checkout_git_dir_bytes",
        "acquired_at",
        "refreshed_at",
        "expires_at",
        "adoption",
    }
)
ADOPTION_KEYS = frozenset(
    {
        "schema",
        "receipt_schema",
        "receipt_id",
        "snapshot_id",
        "authorization_turn_digest",
        "reason_digest",
        "adopted_at",
        "challenge_issued_at",
        "challenge_digest",
    }
)
CHALLENGE_KEYS = frozenset(
    {
        "schema",
        "token_digest",
        "session_key",
        "repository_key",
        "checkout_key",
        "checkout_instance",
        "snapshot_id",
        "head_oid",
        "branch_ref_digest",
        "authorization_turn_digest",
        "issued_at",
        "expires_at",
    }
)
SNAPSHOT_KEYS = frozenset(
    {
        "schema",
        "repository_key",
        "checkout_key",
        "checkout_instance",
        "snapshot_id",
        "head_oid",
        "branch_ref_digest",
        "tracked_entries",
        "untracked_entries",
        "hashed_bytes",
    }
)


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
    # Resolve the command's effective workdir (issue #601 P0-4) so the checkout
    # lease binds to the repository the command really mutates, not the hook
    # process cwd. Direct edits stay target-based via edit_paths / target_checkouts.
    return effective_workdir(payload).resolve(strict=False)


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
            errors="surrogateescape",
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
        if not targets:
            targets = semantic_commit_repo_targets(command, base)
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
    if any(character in subcommand for character in DYNAMIC_ARGUMENT_CHARS):
        return True
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
        "adopt-dirty",
        "lock",
        "move",
        "prune",
        "remove",
        "repair",
        "revoke-dirty",
        "unlock",
    }


def semantic_commit_invocation_mutates(arguments: list[str]) -> bool:
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


def semantic_commit_invocation_repo_target(invocation: list[str]) -> str | None:
    """Return the ``--repo`` value of a mutating ``semantic-commit`` invocation.

    ``None`` means the invocation is not a semantic-commit working-tree mutation
    or carries no explicit ``--repo``. A mutating semantic-commit with no
    ``--repo`` targets the session's current checkout and is deliberately left to
    the ``checkout_from(base)`` fallback in ``target_checkouts``.
    """
    invocation = invocation_without_redirections(invocation)
    if not invocation or os.path.basename(invocation[0]) != "semantic-commit":
        return None
    arguments = invocation[1:]
    if not semantic_commit_invocation_mutates(arguments):
        return None
    _read_only, repo = semantic_commit_invocation_state(arguments)
    return repo or None


def resolve_repo_target(raw: str, base: Path) -> Path:
    try:
        candidate = canonical_path(raw, base)
    except (OSError, RuntimeError) as exc:
        raise MutationScopeError(
            f"repo-scoped commit target could not be resolved: {raw}"
        ) from exc
    if not candidate.exists():
        raise MutationScopeError(
            f"repo-scoped commit target does not exist: {raw}"
        )
    if checkout_from(candidate) is None:
        # A repo-scoped commit target that is not inside any Git checkout fails
        # closed rather than resolving to no checkout: an empty target set skips
        # lease evaluation and admits the command with no lease. The guard must
        # not delegate that safety to whether the external semantic-commit binary
        # happens to refuse a non-repository path.
        raise MutationScopeError(
            f"repo-scoped commit target is not a Git checkout: {raw}"
        )
    return candidate


def invocation_changes_shell_cwd(invocation: list[str]) -> bool:
    invocation = invocation_without_redirections(invocation)
    return bool(invocation) and os.path.basename(invocation[0]) in {
        "cd",
        "popd",
        "pushd",
    }


def invocation_has_cwd_changing_wrapper(tokens: list[str], invocation: list[str]) -> bool:
    """Whether a wrapper retargets a relative operand before the executable."""
    raw = invocation_without_redirections(tokens)
    if not raw or not invocation:
        return False
    target = invocation[0]
    try:
        target_index = raw.index(target)
    except ValueError:
        return True
    prefix = raw[:target_index]
    return any(
        argument in {"-C", "--chdir"} or argument.startswith("--chdir=")
        for argument in prefix
    )


def semantic_commit_repo_targets(command: str, base: Path) -> list[Path]:
    """Resolve an explicit ``semantic-commit --repo <path>`` mutation target.

    A repo-scoped commit must have its lease evaluated on the target
    repository's checkout, not the session's cwd, so coupled cross-repo delivery
    can commit into a second repository's managed worktree (issue #674). This
    mirrors ``managed_worktree_remove_targets``' fail-closed scaffold: the target
    is honored only when the command's mutation scope is statically resolvable
    and the repo-scoped commit is the sole mutating command. Everything after
    target selection — lease ownership, dirty state, in-progress operations, and
    default-branch protection — stays with the existing admission machinery and
    the separate default-delivery guard, so a primary checkout on its default
    branch keeps its branch protection just as it does through the base path.
    """
    commands = parsed_shell_commands(command)
    over_redirect_budget = shell_command_exceeds_redirect_budget(command)
    target_arguments: list[str] = []
    other_mutation = shell_command_has_parenthesized_redirect_word(command)
    cwd_may_have_changed = False
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
        changes_cwd = invocation_changes_shell_cwd(invocation)
        repo = semantic_commit_invocation_repo_target(invocation)
        if repo is None:
            if not over_redirect_budget:
                other_mutation = other_mutation or coresident_command_is_repo_mutation(
                    tokens, base
                )
            cwd_may_have_changed = cwd_may_have_changed or changes_cwd
            continue
        try:
            repo_path = Path(repo).expanduser()
        except (OSError, RuntimeError) as exc:
            raise MutationScopeError(
                f"repo-scoped commit target could not be resolved: {repo}"
            ) from exc
        if not repo_path.is_absolute() and (
            cwd_may_have_changed
            or invocation_has_cwd_changing_wrapper(tokens, invocation)
        ):
            raise MutationScopeError(
                "a relative repo-scoped commit target follows an ambiguous working-directory change"
            )
        if over_redirect_budget:
            raise MutationScopeError(
                "shell redirect target count exceeds the safe inspection limit"
            )
        if command_writes_repo(tokens, base):
            other_mutation = True
        target_arguments.append(repo)
        cwd_may_have_changed = cwd_may_have_changed or changes_cwd
    if len(target_arguments) > 1:
        raise MutationScopeError(
            "exactly one repo-scoped commit is allowed per shell command"
        )
    if target_arguments and other_mutation:
        raise MutationScopeError(
            "a repo-scoped commit must be the sole mutating command"
        )
    if not target_arguments:
        return []
    return [resolve_repo_target(target_arguments[0], base)]


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


def sole_git_recovery_operation(command: str, base: Path) -> bool:
    """True when the command's only mutation is one ``git <op> --abort|--quit``.

    A recovery command restores the checkout to its clean pre-operation state
    and authors no content, so it is the exact escape a stuck mid-operation
    checkout needs. Like the ``sole_managed_worktree_add`` carve-out, the
    admission gate must not refuse its own remediation: ``main()`` short-circuits
    a matched recovery command to ALLOW before the session-identity and lease
    gates, acquiring no lease.

    Narrowness mirrors the worktree-add carve-out exactly — a single recovery op,
    no co-resident repository mutation, no lexer-splitting or over-budget output
    redirect, and no dynamic or unresolved nested shell — so it can never smuggle
    another working-tree write past the gate. ``--continue`` / ``--skip`` advance
    the operation and are not recovery ops (see ``is_git_recovery_argv``).
    """
    commands = parsed_shell_commands(command)
    if shell_command_exceeds_redirect_budget(
        command
    ) or shell_command_has_parenthesized_redirect_word(command):
        return False
    found_recovery = False
    for tokens in commands:
        if invocation_command_position_is_dynamic(tokens):
            return False
        invocation = invocation_tokens(tokens)
        if invocation_is_unresolved_nested(
            invocation
        ) or opaque_invocation_has_unresolved_nested(invocation):
            return False
        if is_git_recovery_argv(invocation):
            if found_recovery or command_writes_repo(tokens, base):
                return False
            found_recovery = True
            continue
        if coresident_command_is_repo_mutation(tokens, base):
            return False
    return found_recovery


def resolved_executable_matches(raw: str, name: str, *, managed_cli: bool = False) -> bool:
    """Require the shell spelling to resolve to the hook's trusted executable."""
    candidate = shutil.which(name)
    if not candidate or not os.path.isabs(candidate):
        return False
    if raw == name:
        invoked = candidate
    elif os.path.isabs(raw):
        invoked = raw
    else:
        return False
    try:
        resolved_candidate = os.path.realpath(candidate)
        resolved_invoked = os.path.realpath(invoked)
    except OSError:
        return False
    if (
        resolved_candidate != resolved_invoked
        or not os.path.isfile(resolved_invoked)
        or not os.access(resolved_invoked, os.X_OK)
    ):
        return False
    if not managed_cli:
        return True

    configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "")
    if configured:
        roots = {
            os.path.realpath(item)
            for item in configured.split(os.pathsep)
            if item
        }
        if os.path.realpath(os.path.dirname(candidate)) in roots:
            return True
    for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
        if os.path.dirname(os.path.abspath(candidate)) != os.path.join(prefix, "bin"):
            continue
        if os.path.dirname(resolved_invoked) == os.path.join(prefix, "bin"):
            return True
        cellar = os.path.join(prefix, "Cellar", "nils-cli")
        try:
            return os.path.commonpath((resolved_invoked, cellar)) == cellar
        except ValueError:
            return False
    if os.path.dirname(resolved_invoked) == "/usr/bin":
        return True
    return is_managed_cli_home_bin(os.path.dirname(resolved_invoked))


def invocation_environment_is_stable(tokens: list[str], executable: str) -> bool:
    """Reject command-local executable/config retargeting for narrow carve-outs."""
    raw = invocation_without_redirections(tokens)
    index = 0
    while index < len(raw) and is_assignment(raw[index]):
        name = raw[index].split("=", 1)[0]
        if name in {"HOME", "PATH", "XDG_CONFIG_HOME"} or name.startswith("GIT_"):
            return False
        index += 1
    return index < len(raw) and os.path.basename(raw[index]) == executable


def governed_dirty_transition_details(
    invocation: list[str],
) -> tuple[str, dict[str, str]] | None:
    invocation = invocation_without_redirections(invocation)
    if (
        len(invocation) < 4
        or not resolved_executable_matches(invocation[0], "git-cli", managed_cli=True)
        or invocation[1] != "worktree"
    ):
        return None
    action = invocation[2]
    arguments = invocation[3:]
    required = (
        {"--challenge", "--reason-file"}
        if action == "adopt-dirty"
        else {"--receipt"}
        if action == "revoke-dirty"
        else set()
    )
    if not required:
        return None

    values: dict[str, str] = {}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        name, separator, attached = argument.partition("=")
        if name in required | {"--format"}:
            if name in values:
                return None
            if separator:
                value = attached
                index += 1
            else:
                if index + 1 >= len(arguments):
                    return None
                value = arguments[index + 1]
                index += 2
            if not value:
                return None
            if name == "--format" and value not in {"text", "json"}:
                return None
            values[name] = value
            continue
        return None
    if not required <= values.keys():
        return None
    identifier = values["--challenge"] if action == "adopt-dirty" else values["--receipt"]
    if not lower_hex(identifier, 64):
        return None
    return action, values


def governed_dirty_transition_invocation(invocation: list[str]) -> bool:
    return governed_dirty_transition_details(invocation) is not None


def sole_governed_dirty_transition(
    command: str, base: Path
) -> tuple[str, dict[str, str]] | None:
    """Recognize one exact adopt/revoke command for bound admission."""
    commands = parsed_shell_commands(command)
    if shell_command_exceeds_redirect_budget(
        command
    ) or shell_command_has_parenthesized_redirect_word(command):
        return None
    transition: tuple[str, dict[str, str]] | None = None
    for tokens in commands:
        if invocation_command_position_is_dynamic(tokens):
            return None
        invocation = invocation_without_redirections(invocation_tokens(tokens))
        if invocation_is_unresolved_nested(
            invocation
        ) or opaque_invocation_has_unresolved_nested(invocation):
            return None
        details = governed_dirty_transition_details(invocation)
        if details is not None:
            if (
                transition is not None
                or not invocation_environment_is_stable(tokens, "git-cli")
                or command_writes_repo(tokens, base)
            ):
                return None
            transition = details
            continue
        if coresident_command_is_repo_mutation(tokens, base):
            return None
    return transition


def argument_is_dynamic(argument: str) -> bool:
    return any(character in argument for character in DYNAMIC_ARGUMENT_CHARS)


def checkout_safe_ref_invocation(invocation: list[str]) -> bool:
    invocation = invocation_without_redirections(invocation)
    if (
        len(invocation) < 3
        or not resolved_executable_matches(invocation[0], "git")
    ):
        return False
    subcommand = invocation[1]
    arguments = invocation[2:]
    if subcommand not in {"branch", "tag"} or any(
        argument_is_dynamic(argument) for argument in arguments
    ):
        return False

    if subcommand == "branch":
        mode = arguments[0] if arguments else ""
        if mode in {"-d", "-D", "--delete"}:
            targets = [argument for argument in arguments[1:] if argument != "--"]
            return bool(targets) and all(not target.startswith("-") for target in targets)
        if mode in {"-m", "-M", "--move", "-c", "-C", "--copy"}:
            targets = [argument for argument in arguments[1:] if argument != "--"]
            return 1 <= len(targets) <= 2 and all(
                not target.startswith("-") for target in targets
            )
        return False

    if arguments and arguments[0] in {"-d", "--delete"}:
        targets = [argument for argument in arguments[1:] if argument != "--"]
        return bool(targets) and all(not target.startswith("-") for target in targets)

    positional: list[str] = []
    no_sign = False
    for argument in arguments:
        if argument in {"-f", "--force", "--"}:
            continue
        if argument == "--no-sign":
            no_sign = True
            continue
        if argument.startswith("-"):
            return False
        positional.append(argument)
    return no_sign and 1 <= len(positional) <= 2


def sole_checkout_safe_ref_operation(command: str, base: Path) -> bool:
    """Recognize one ref-only mutation without admitting checkout writes."""
    commands = parsed_shell_commands(command)
    if shell_command_exceeds_redirect_budget(
        command
    ) or shell_command_has_parenthesized_redirect_word(command):
        return False
    found_ref_operation = False
    for tokens in commands:
        if invocation_command_position_is_dynamic(tokens):
            return False
        invocation = invocation_without_redirections(invocation_tokens(tokens))
        if invocation_is_unresolved_nested(
            invocation
        ) or opaque_invocation_has_unresolved_nested(invocation):
            return False
        if checkout_safe_ref_invocation(invocation):
            if (
                found_ref_operation
                or not invocation_environment_is_stable(tokens, "git")
                or command_writes_repo(tokens, base)
            ):
                return False
            found_ref_operation = True
            continue
        if coresident_command_is_repo_mutation(tokens, base):
            return False
    return found_ref_operation


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


def path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=False))
    except ValueError:
        return False
    return True


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
    root = state_root()
    if create:
        private_directory(root)
    repo_key = hashlib.sha256(os.fsencode(checkout.common_dir)).hexdigest()
    path = root / repo_key
    if create:
        private_directory(path)
    return path


def checkout_state_dir(checkout: Checkout, *, create: bool = True) -> Path:
    checkout_key = hashlib.sha256(os.fsencode(checkout.root)).hexdigest()
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


def lower_hex(value: Any, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch(
        rf"[0-9a-f]{{{length}}}", value
    ) is not None


def unsigned_integer(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= MAX_U64
    )


def strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LeaseStatePathError("checkout lease state has duplicate fields")
        result[key] = value
    return result


def validate_v2_path(raw: Any, text: Any, label: str) -> bytes:
    if (
        not isinstance(raw, str)
        or not raw
        or len(raw) % 2
        or re.fullmatch(r"[0-9a-f]+", raw) is None
    ):
        raise LeaseStatePathError(f"checkout lease {label} bytes are malformed")
    value = bytes.fromhex(raw)
    rendered = value.decode("utf-8", errors="replace")
    if (
        not value
        or b"\0" in value
        or not value.startswith(os.fsencode(os.sep))
        or not isinstance(text, str)
        or text != rendered
        or not Path(text).is_absolute()
    ):
        raise LeaseStatePathError(f"checkout lease {label} identity is malformed")
    return value


def validate_lease_checkout(lease: Mapping[str, Any], checkout: Checkout) -> None:
    schema = lease["schema"]
    if schema == LEASE_V2_SCHEMA:
        expected_root = os.fsencode(checkout.root)
        expected_git_dir = os.fsencode(checkout.git_dir)
        if (
            bytes.fromhex(lease["checkout_root_bytes"]) != expected_root
            or bytes.fromhex(lease["checkout_git_dir_bytes"]) != expected_git_dir
            or lease["checkout_root"]
            != expected_root.decode("utf-8", errors="replace")
            or lease["checkout_git_dir"]
            != expected_git_dir.decode("utf-8", errors="replace")
        ):
            raise LeaseStatePathError(
                "checkout lease native path identity does not match the current checkout"
            )
        return

    for key, expected in (
        ("checkout_root", checkout.root),
        ("checkout_git_dir", checkout.git_dir),
    ):
        value = lease.get(key)
        if value is not None and Path(value).resolve(strict=False) != expected:
            raise LeaseStatePathError(
                f"checkout lease {key} does not match the current checkout"
            )


def load_lease(path: Path, checkout: Checkout | None = None) -> dict[str, Any] | None:
    try:
        raw = read_regular_file(path, max_bytes=MAX_LEASE_BYTES)
    except LeaseError as exc:
        raise LeaseStatePathError(str(exc)) from exc
    if not raw:
        if path.exists() or path.is_symlink():
            raise LeaseStatePathError("checkout lease state is malformed")
        return None
    try:
        lease = json.loads(raw, object_pairs_hook=strict_json_object)
    except (json.JSONDecodeError, LeaseStatePathError) as exc:
        raise LeaseStatePathError("checkout lease state is malformed") from exc
    if not isinstance(lease, dict):
        raise LeaseStatePathError("checkout lease state is malformed")

    schema = lease.get("schema")
    if schema not in {LEASE_V1_SCHEMA, LEASE_V2_SCHEMA}:
        raise LeaseStatePathError(
            "checkout lease state has an unsupported schema"
        )
    if not lower_hex(lease.get("session_key"), 64):
        raise LeaseStatePathError(
            "checkout lease session identity is malformed"
        )
    if not lower_hex(lease.get("checkout_instance"), 32):
        raise LeaseStatePathError(
            "checkout lease instance identity is malformed"
        )

    if schema == LEASE_V1_SCHEMA:
        if not isinstance(lease.get("expires_at"), int | float):
            raise LeaseStatePathError("checkout lease expiry is malformed")
        for key in ("checkout_root", "checkout_git_dir"):
            value = lease.get(key)
            if value is not None and (
                not isinstance(value, str) or not value or not Path(value).is_absolute()
            ):
                raise LeaseStatePathError(f"checkout lease {key} is malformed")
    else:
        if frozenset(lease) != LEASE_V2_KEYS:
            raise LeaseStatePathError("checkout lease v2 fields are malformed")
        timestamps = (
            lease.get("acquired_at"),
            lease.get("refreshed_at"),
            lease.get("expires_at"),
        )
        if not all(unsigned_integer(value) for value in timestamps):
            raise LeaseStatePathError("checkout lease v2 timestamps are malformed")
        acquired_at, refreshed_at, expires_at = timestamps
        if not acquired_at <= refreshed_at <= expires_at:
            raise LeaseStatePathError("checkout lease v2 timestamps are unordered")
        validate_v2_path(
            lease.get("checkout_root_bytes"), lease.get("checkout_root"), "root"
        )
        validate_v2_path(
            lease.get("checkout_git_dir_bytes"),
            lease.get("checkout_git_dir"),
            "Git directory",
        )
        adoption = lease.get("adoption")
        if not isinstance(adoption, dict) or frozenset(adoption) != ADOPTION_KEYS:
            raise LeaseStatePathError("checkout lease adoption fields are malformed")
        if (
            adoption.get("schema") != ADOPTION_SCHEMA
            or adoption.get("receipt_schema") != RECEIPT_SCHEMA
            or not all(
                lower_hex(adoption.get(key), 64)
                for key in (
                    "receipt_id",
                    "snapshot_id",
                    "authorization_turn_digest",
                    "reason_digest",
                    "challenge_digest",
                )
            )
            or not unsigned_integer(adoption.get("adopted_at"))
            or not unsigned_integer(adoption.get("challenge_issued_at"))
            or not adoption["challenge_issued_at"]
            <= adoption["adopted_at"]
            <= refreshed_at
        ):
            raise LeaseStatePathError("checkout lease adoption state is malformed")

    if checkout is not None:
        validate_lease_checkout(lease, checkout)
    return lease


def lease_checkout_paths(
    lease: Mapping[str, Any],
) -> tuple[Path, Path] | None:
    if lease.get("schema") == LEASE_V2_SCHEMA:
        try:
            return (
                Path(os.fsdecode(bytes.fromhex(lease["checkout_root_bytes"]))),
                Path(os.fsdecode(bytes.fromhex(lease["checkout_git_dir_bytes"]))),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LeaseStatePathError(
                "checkout lease native paths are malformed"
            ) from exc

    root_value = lease.get("checkout_root")
    git_dir_value = lease.get("checkout_git_dir")
    if not isinstance(root_value, str) or not isinstance(git_dir_value, str):
        return None
    return Path(root_value), Path(git_dir_value)


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
    if previous and previous.get("schema") == LEASE_V2_SCHEMA:
        refreshed = dict(previous)
        refreshed["refreshed_at"] = now
        refreshed["expires_at"] = now + lease_ttl_seconds()
        return refreshed

    acquired_at = previous.get("acquired_at") if previous else now
    if not isinstance(acquired_at, int | float):
        acquired_at = now
    return {
        "schema": LEASE_V1_SCHEMA,
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
            f"{error}. Use a concrete executable with an explicit target. Resubmit "
            "cross-repository filesystem or index work as a "
            "standalone tool call whose top-level `workdir` is the target checkout. "
            "For staging, run `git add -- <owned-paths>` there, then invoke the "
            "repo-scoped `semantic-commit` separately. Do not retarget with shell `cd`, "
            "raw `git -C`, or nested `agent-run exec --cwd`; use a target-rooted managed "
            "session when the host cannot attest the workdir. Keep a target-aware "
            "managed worktree removal or repo-scoped commit as the command's sole "
            "mutation, then retry."
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
            "already in progress without this session's lease. To recover in place, "
            "a sole `git <op> --abort` (or `--quit`) is always admitted and restores "
            f"a clean state. Otherwise: {worktree_guidance()}"
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


def reference_transaction_hook_enabled(checkout: Checkout) -> bool:
    result = run_git(
        checkout.root,
        "rev-parse",
        "--git-path",
        "hooks/reference-transaction",
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise LeaseError("Git reference-hook probe failed")
    path = absolute_git_path(result.stdout.strip(), checkout.root)
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise LeaseError(f"Git reference-hook probe failed: {exc}") from exc
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError as exc:
        raise LeaseError(f"Git reference-hook probe failed: {exc}") from exc


def checkout_safe_ref_admission(
    checkout: Checkout, session_key: str
) -> tuple[bool, str]:
    """Handle a dirty ref-only operation without minting checkout ownership."""
    if not checkout_dirty(checkout):
        return False, ""

    directory = checkout_state_dir(checkout, create=False)
    lease: dict[str, Any] | None = None
    if directory.exists() or directory.is_symlink():
        if directory.is_symlink() or not directory.is_dir():
            raise LeaseStatePathError(
                "checkout lease state directory is not a trusted directory"
            )
        with acquire_lock(directory):
            lease = load_lease(directory / "lease.json", checkout)
    if lease is not None:
        instance = read_instance(checkout, create=False)
        now = time.time()
        if (
            instance
            and lease["checkout_instance"] == instance
            and lease["session_key"] == session_key
        ):
            return False, ""
        reason = live_foreign_lease_reason(
            lease, instance=instance, session_key=session_key, now=now
        )
        if reason:
            return True, reason
        return True, (
            "Checkout mutation is blocked because the checkout has unowned changes. "
            f"Preserve those changes and inspect their owner; do not discard them. {worktree_guidance()}"
        )

    operation = git_operation(checkout)
    if operation:
        return True, (
            f"Checkout mutation is blocked because a Git operation ({operation}) is "
            f"already in progress without this session's lease. {worktree_guidance()}"
        )
    if reference_transaction_hook_enabled(checkout):
        return True, (
            "The dirty-checkout ref-only exception is blocked because an executable "
            "reference-transaction hook could write checkout content. Disable or remove "
            "the hook before retrying the ref-only operation."
        )
    if checkout.primary:
        branch = current_branch(checkout)
        expected = default_branch(checkout)
        if not branch or not expected or branch != expected:
            return True, (
                "The dirty-checkout ref-only exception applies only on the resolved "
                f"default branch; current={branch or 'detached'}, "
                f"default={expected or 'unknown'}. {worktree_guidance()}"
            )
    return True, ""


def governed_dirty_transition_admission(
    checkout: Checkout,
    session_key: str,
    transition: tuple[str, dict[str, str]],
) -> str:
    """Bind adoption and revocation to their issuing/owning hook session."""
    action, values = transition
    directory = checkout_state_dir(checkout, create=False)
    if directory.is_symlink() or not directory.is_dir():
        return (
            "Dirty-checkout transition is blocked because its private state does not "
            "match this checkout. Request a fresh challenge and retry."
        )

    if action == "adopt-dirty":
        token = values["--challenge"]
        token_digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        challenge_path = directory / "challenges" / f"{token_digest}.json"
        with acquire_lock(directory):
            raw = read_regular_file(challenge_path, max_bytes=MAX_LEASE_BYTES)
        if not raw:
            return (
                "Dirty-checkout adoption is blocked because the challenge is unavailable. "
                "Request a fresh challenge from the issuing agent session."
            )
        try:
            challenge = json.loads(raw, object_pairs_hook=strict_json_object)
        except (json.JSONDecodeError, LeaseStatePathError) as exc:
            raise LeaseStatePathError(
                "dirty-checkout challenge state is malformed"
            ) from exc
        instance = read_instance(checkout, create=False)
        now = int(time.time())
        if (
            not isinstance(challenge, dict)
            or frozenset(challenge) != CHALLENGE_KEYS
            or challenge.get("schema") != CHALLENGE_SCHEMA
            or challenge.get("token_digest") != token_digest
            or not lower_hex(challenge.get("session_key"), 64)
            or not lower_hex(challenge.get("repository_key"), 64)
            or not lower_hex(challenge.get("checkout_key"), 64)
            or not lower_hex(challenge.get("checkout_instance"), 32)
            or not lower_hex(challenge.get("snapshot_id"), 64)
            or not lower_hex(challenge.get("branch_ref_digest"), 64)
            or not lower_hex(challenge.get("authorization_turn_digest"), 64)
            or not unsigned_integer(challenge.get("issued_at"))
            or not unsigned_integer(challenge.get("expires_at"))
            or challenge["issued_at"] > challenge["expires_at"]
            or challenge["expires_at"] < now
            or challenge["repository_key"]
            != hashlib.sha256(os.fsencode(checkout.common_dir)).hexdigest()
            or challenge["checkout_key"]
            != hashlib.sha256(os.fsencode(checkout.root)).hexdigest()
            or not instance
            or challenge["checkout_instance"] != instance
        ):
            return (
                "Dirty-checkout adoption is blocked because the challenge no longer "
                "matches this checkout. Request a fresh challenge and retry."
            )
        if challenge["session_key"] != session_key:
            return (
                "Dirty-checkout adoption requires the issuing agent session; a foreign "
                "session cannot consume this challenge."
            )
        return ""

    with acquire_lock(directory):
        lease = load_lease(directory / "lease.json", checkout)
    adoption = lease.get("adoption") if isinstance(lease, dict) else None
    if (
        not isinstance(lease, dict)
        or lease.get("schema") != LEASE_V2_SCHEMA
        or not isinstance(adoption, dict)
        or adoption.get("receipt_id") != values["--receipt"]
    ):
        return (
            "Dirty-checkout revocation is blocked because the receipt does not match "
            "this checkout's adopted lease."
        )
    if lease["session_key"] != session_key:
        return (
            "Dirty-checkout revocation requires the owning agent session; a foreign "
            "session cannot revoke this lease."
        )
    return ""


def same_session_lease_is_admissible(
    lease: Mapping[str, Any], now: float
) -> bool:
    return lease["schema"] != LEASE_V2_SCHEMA or float(lease["expires_at"]) > now


def acquire_or_refresh(checkout: Checkout, session_key: str) -> str:
    instance = read_instance(checkout, create=True)
    directory = checkout_state_dir(checkout)
    lease_path = directory / "lease.json"
    with acquire_lock(directory):
        lease = load_lease(lease_path, checkout)
        now = time.time()
        same_instance = bool(lease and lease["checkout_instance"] == instance)
        if (
            same_instance
            and lease
            and lease["session_key"] == session_key
            and same_session_lease_is_admissible(lease, now)
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

    reason = checkout_admission_reason(checkout)
    if reason:
        return reason
    if read_instance(checkout, create=False) != instance:
        raise LeaseError("checkout instance changed during lease admission")

    with acquire_lock(directory):
        lease = load_lease(lease_path, checkout)
        now = time.time()
        if (
            lease
            and lease["checkout_instance"] == instance
            and lease["session_key"] == session_key
            and same_session_lease_is_admissible(lease, now)
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
                checkout_paths = lease_checkout_paths(lease)
                if checkout_paths is None:
                    continue
                root_path, git_dir_path = checkout_paths
                if root_path.exists() or git_dir_path.exists():
                    continue
                lease_path.unlink(missing_ok=True)
                removed += 1
        except (LeaseError, OSError):
            continue
    return removed


def dirty_adoption_enabled() -> bool:
    return os.environ.get("AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION") == "1"


def dirty_snapshot(checkout: Checkout) -> dict[str, Any] | None:
    try:
        completed = subprocess.run(
            ["git-cli", "worktree", "dirty-snapshot", "--format=json"],
            cwd=checkout.root,
            capture_output=True,
            text=True,
            check=False,
            timeout=DIRTY_SNAPSHOT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        envelope = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    if (
        not isinstance(envelope, dict)
        or frozenset(envelope) != {"schema_version", "ok", "data"}
        or envelope.get("schema_version")
        != "cli.git-cli.worktree.dirty-snapshot.v1"
        or envelope.get("ok") is not True
        or not isinstance(envelope.get("data"), dict)
    ):
        return None
    snapshot = envelope["data"]
    if frozenset(snapshot) != SNAPSHOT_KEYS:
        return None
    head_oid = snapshot.get("head_oid")
    head_valid = isinstance(head_oid, str) and (
        re.fullmatch(r"[0-9a-f]{40,64}", head_oid) is not None
        or re.fullmatch(r"unborn:[0-9a-f]{64}", head_oid) is not None
    )
    if (
        snapshot.get("schema") != SNAPSHOT_SCHEMA
        or not all(
            lower_hex(snapshot.get(key), length)
            for key, length in (
                ("repository_key", 64),
                ("checkout_key", 64),
                ("checkout_instance", 32),
                ("snapshot_id", 64),
                ("branch_ref_digest", 64),
            )
        )
        or not head_valid
        or not all(
            unsigned_integer(snapshot.get(key))
            for key in ("tracked_entries", "untracked_entries", "hashed_bytes")
        )
        or snapshot["repository_key"]
        != hashlib.sha256(os.fsencode(checkout.common_dir)).hexdigest()
        or snapshot["checkout_key"]
        != hashlib.sha256(os.fsencode(checkout.root)).hexdigest()
    ):
        return None
    return snapshot


def remove_same_session_challenges(
    directory: Path, reason_directory: Path, session_key: str
) -> None:
    entries = list(directory.iterdir())
    if len(entries) > MAX_CHALLENGE_FILES:
        raise LeaseStatePathError("dirty-checkout challenge directory is over budget")
    for path in entries:
        if (
            path.is_symlink()
            or not path.is_file()
            or re.fullmatch(r"[0-9a-f]{64}\.json", path.name) is None
        ):
            raise LeaseStatePathError(
                "dirty-checkout challenge directory contains untrusted state"
            )
        raw = read_regular_file(path, max_bytes=MAX_LEASE_BYTES)
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LeaseStatePathError(
                "dirty-checkout challenge state is malformed"
            ) from exc
        if isinstance(record, dict) and record.get("session_key") == session_key:
            path.unlink()
            (reason_directory / f"{path.stem}.txt").unlink(missing_ok=True)


def write_private_reason_placeholder(directory: Path, token_digest: str) -> Path:
    path = directory / f"{token_digest}.txt"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    directory_fd = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        directory_fd = os.open(
            directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        os.fsync(directory_fd)
    except OSError as exc:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise LeaseStatePathError(
            f"dirty-checkout reason path creation failed: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory_fd >= 0:
            os.close(directory_fd)
    return path


def write_private_challenge(
    directory: Path, challenge: Mapping[str, Any], token_digest: str
) -> None:
    path = directory / f"{token_digest}.json"
    payload = (
        json.dumps(dict(challenge), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        write_all(descriptor, payload)
        os.fsync(descriptor)
    except OSError as exc:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise LeaseStatePathError(
            f"dirty-checkout challenge write failed: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    directory_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def issue_dirty_checkout_challenge(payload: Mapping[str, Any]) -> int:
    if not dirty_adoption_enabled():
        return ALLOW
    session_key = session_marker_key(payload)
    prompt = payload.get("prompt")
    if not session_key or not isinstance(prompt, str) or not prompt:
        return ALLOW
    try:
        checkout = checkout_from(payload_base(payload))
        if checkout is None:
            return ALLOW
        managed_state_root = state_root()
        if path_is_within(managed_state_root, checkout.root):
            return ALLOW
        if not checkout_dirty(checkout) or git_operation(checkout):
            return ALLOW

        directory = checkout_state_dir(checkout, create=False)
        if directory.exists() or directory.is_symlink():
            if directory.is_symlink() or not directory.is_dir():
                return ALLOW
            with acquire_lock(directory):
                lease = load_lease(directory / "lease.json", checkout)
            instance = read_instance(checkout, create=False)
            if (
                lease is not None
                and instance
                and lease["checkout_instance"] == instance
                and float(lease["expires_at"]) > time.time()
            ):
                return ALLOW

        snapshot = dirty_snapshot(checkout)
        if snapshot is None:
            return ALLOW
        if read_instance(checkout, create=False) != snapshot["checkout_instance"]:
            return ALLOW

        directory = checkout_state_dir(checkout)
        challenge_directory = directory / "challenges"
        reason_directory = directory / "reasons"
        private_directory(challenge_directory)
        private_directory(reason_directory)
        token = secrets.token_hex(32)
        token_digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        issued_at = int(time.time())
        challenge = {
            "schema": CHALLENGE_SCHEMA,
            "token_digest": token_digest,
            "session_key": session_key,
            "repository_key": snapshot["repository_key"],
            "checkout_key": snapshot["checkout_key"],
            "checkout_instance": snapshot["checkout_instance"],
            "snapshot_id": snapshot["snapshot_id"],
            "head_oid": snapshot["head_oid"],
            "branch_ref_digest": snapshot["branch_ref_digest"],
            "authorization_turn_digest": hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest(),
            "issued_at": issued_at,
            "expires_at": issued_at + CHALLENGE_TTL_SECONDS,
        }
        with acquire_lock(directory):
            remove_same_session_challenges(
                challenge_directory, reason_directory, session_key
            )
            reason_file = write_private_reason_placeholder(
                reason_directory, token_digest
            )
            try:
                write_private_challenge(
                    challenge_directory, challenge, token_digest
                )
            except (LeaseError, OSError):
                reason_file.unlink(missing_ok=True)
                raise

        context = (
            "This checkout has unowned changes. Remain read-only for Q&A. Before "
            "implementation, ask the user to choose explicit takeover of the exact "
            "warned state or a managed worktree via `git-cli worktree add <slug>`. "
            "After explicit authorization, write a concise reason outside the checkout "
            f"and run `git-cli worktree adopt-dirty --challenge {token} "
            f"--reason-file {shlex.quote(str(reason_file))}`. Keep the challenge out of provider evidence."
        )
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": context,
                    }
                }
            )
            + "\n"
        )
    except (LeaseError, OSError, ValueError):
        # Challenge issuance is advisory only. The mutation gate below remains
        # fail-closed even when the released snapshot primitive is unavailable.
        return ALLOW
    return ALLOW


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
            checkout_paths = lease_checkout_paths(lease)
            if checkout_paths is None:
                retained += 1
                continue
            root_path, git_dir_path = checkout_paths
            checkout = checkout_from(root_path)
            if checkout is not None:
                validate_lease_checkout(lease, checkout)
            if (
                checkout is None
                or checkout.root != root_path.resolve(strict=False)
                or checkout.git_dir != git_dir_path.resolve(strict=False)
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
                current = load_lease(lease_path, checkout)
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
    if os.environ.get("AGENT_SESSION_COORDINATION_MODE", "").strip().lower() != "enforce":
        return ALLOW
    payload = read_payload()
    event = hook_event(payload)
    if event == "Stop":
        return stop_audit(payload)
    if event == "UserPromptSubmit":
        return issue_dirty_checkout_challenge(payload)

    tool = tool_name(payload)
    if tool not in EDIT_TOOLS | COMMAND_TOOLS:
        return ALLOW
    governed_transition: tuple[str, dict[str, str]] | None = None
    checkout_safe_ref = False
    if tool in COMMAND_TOOLS:
        command = command_from(payload)
        base = payload_base(payload)
        if not high_confidence_shell_mutation(command, base):
            return ALLOW
        governed_transition = sole_governed_dirty_transition(command, base)
        checkout_safe_ref = sole_checkout_safe_ref_operation(command, base)
        # `git-cli worktree add` creates a new checkout and is the sanctioned
        # escape the guard recommends; never let the admission gate block its own
        # remediation. Restricted to a sole add with no co-resident repository
        # write so it cannot cover a working-tree mutation. This intentionally
        # short-circuits before the session-identity gate and acquires no lease:
        # add takes no lease on the current checkout.
        if sole_managed_worktree_add(command, payload_base(payload)):
            return ALLOW
        # A sole `git <op> --abort`/`--quit` restores the checkout's clean
        # pre-operation state and authors no content; it is the escape a stuck
        # mid-operation checkout needs, so the admission gate must not refuse it.
        # Like the worktree-add carve-out this short-circuits before the
        # session-identity and lease gates and acquires no lease.
        if sole_git_recovery_operation(command, payload_base(payload)):
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
        if governed_transition:
            if len(checkouts) != 1:
                emit_block(
                    "Dirty-checkout transition target could not be bound to one checkout."
                )
                return ALLOW
            reason = governed_dirty_transition_admission(
                checkouts[0], session_key, governed_transition
            )
            if reason:
                emit_block(reason)
            return ALLOW
        if checkout_safe_ref and checkouts:
            handled_all = True
            for checkout in checkouts:
                handled, reason = checkout_safe_ref_admission(checkout, session_key)
                handled_all = handled_all and handled
                if reason:
                    emit_block(reason)
                    return ALLOW
            if handled_all:
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
