#!/usr/bin/env python3
"""Coordinate one agent writer lease per physical Git checkout.

The guard deliberately recognizes only explicit edit tools and high-confidence
shell mutations. Read-only inspection stays available. Stop performs an audit
only: it never removes a worktree, branch, or lease.
"""

from __future__ import annotations

import fcntl
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
    opaque_invocation_has_unresolved_nested,
    output_redirect_targets,
    patch_text_candidates,
    read_payload,
    session_marker_key,
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
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
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
        raise LeaseError(f"managed worktree inventory failed: {exc}") from exc
    if completed.returncode != 0:
        raise LeaseError("managed worktree inventory failed")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LeaseError("managed worktree inventory is malformed") from exc
    data = payload.get("data") if isinstance(payload, Mapping) else None
    entries = data.get("entries") if isinstance(data, Mapping) else None
    if not isinstance(entries, list):
        raise LeaseError("managed worktree inventory is malformed")
    paths: list[Path] = []
    for entry in entries:
        raw_path = entry.get("path") if isinstance(entry, Mapping) else None
        if not isinstance(raw_path, str) or not raw_path:
            raise LeaseError("managed worktree inventory is malformed")
        paths.append(Path(raw_path).resolve(strict=False))
    return paths


def resolve_worktree_remove_target(raw: str, base: Path) -> Path:
    candidate = canonical_path(raw, base)
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
            raise LeaseError(f"managed worktree slug is ambiguous: {raw}")
        raise LeaseError(f"managed worktree slug could not be resolved: {raw}")
    if candidate.exists():
        return candidate
    exact = [path for path in listed_worktree_paths(base) if path == candidate]
    if len(exact) == 1:
        return exact[0]
    raise LeaseError(f"managed worktree target could not be resolved: {raw}")


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


def is_managed_worktree_remove(invocation: list[str]) -> bool:
    return (
        len(invocation) >= 4
        and os.path.basename(invocation[0]) == "git-cli"
        and invocation[1:3] == ["worktree", "remove"]
    )


def worktree_remove_target_argument(invocation: list[str]) -> str:
    target = ""
    index = 3
    while index < len(invocation):
        argument = invocation[index]
        if argument == "--":
            index += 1
            while index < len(invocation):
                if target:
                    raise LeaseError("managed worktree removal has multiple targets")
                target = invocation[index]
                index += 1
            break
        if argument == "--format":
            if index + 1 >= len(invocation):
                raise LeaseError("managed worktree removal --format needs a value")
            index += 2
            continue
        if argument.startswith("--format="):
            index += 1
            continue
        if argument.startswith("-"):
            raise LeaseError(
                f"managed worktree removal option is unsupported: {argument}"
            )
        if target:
            raise LeaseError("managed worktree removal has multiple targets")
        target = argument
        index += 1
    if not target:
        raise LeaseError("managed worktree removal target is missing")
    return target


def simple_command_mutates(tokens: list[str]) -> bool:
    if has_output_redirection(tokens):
        return True
    invocation = invocation_tokens(tokens)
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
    if executable == "semantic-commit" and arguments[:1] == ["commit"]:
        return True
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


def managed_worktree_remove_targets(command: str, base: Path) -> list[Path]:
    target_arguments: list[str] = []
    other_mutation = False
    for tokens in simple_commands_with_nested_shells(command):
        if invocation_command_position_is_dynamic(tokens):
            raise LeaseError(
                "shell mutation target scope is unresolved and cannot be leased safely"
            )
        invocation = invocation_tokens(tokens)
        if invocation_is_unresolved_nested(
            invocation
        ) or opaque_invocation_has_unresolved_nested(invocation):
            raise LeaseError(
                "shell mutation target scope is unresolved and cannot be leased safely"
            )
        if not is_managed_worktree_remove(invocation):
            other_mutation = other_mutation or simple_command_mutates(tokens)
            continue
        if has_output_redirection(tokens):
            other_mutation = True
        target_arguments.append(worktree_remove_target_argument(invocation))
    if len(target_arguments) > 1:
        raise LeaseError(
            "exactly one managed worktree removal is allowed per shell command"
        )
    if target_arguments and other_mutation:
        raise LeaseError(
            "managed worktree removal must be the sole mutating command"
        )
    if not target_arguments:
        return []
    return [resolve_worktree_remove_target(target_arguments[0], base)]


def has_output_redirection(tokens: list[str]) -> bool:
    return bool(output_redirect_targets(tokens))


def high_confidence_shell_mutation(command: str) -> bool:
    return any(
        simple_command_mutates(tokens)
        for tokens in simple_commands_with_nested_shells(command)
    )


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
        raise LeaseError(f"checkout lease state directory unavailable: {exc}") from exc
    if path.is_symlink() or not path.is_dir():
        raise LeaseError("checkout lease state directory is not a trusted directory")
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise LeaseError(f"checkout lease state permissions failed: {exc}") from exc


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
        raise LeaseError(f"checkout lease lock unavailable: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LeaseError("checkout lease lock is not a regular file")
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
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        raw = read_regular_file(path, max_bytes=128).strip()
        if re.fullmatch(r"[0-9a-f]{32}", raw) is None:
            raise LeaseError("checkout instance sentinel is malformed")
        return raw
    except OSError as exc:
        raise LeaseError(f"checkout instance sentinel unavailable: {exc}") from exc
    try:
        os.write(descriptor, f"{value}\n".encode("ascii"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return value


def load_lease(path: Path) -> dict[str, Any] | None:
    raw = read_regular_file(path, max_bytes=MAX_LEASE_BYTES)
    if not raw:
        return None
    try:
        lease = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LeaseError("checkout lease state is malformed") from exc
    if not isinstance(lease, dict) or lease.get("schema") != LEASE_SCHEMA:
        raise LeaseError("checkout lease state has an unsupported schema")
    if re.fullmatch(r"[0-9a-f]{64}", str(lease.get("session_key", ""))) is None:
        raise LeaseError("checkout lease session identity is malformed")
    if re.fullmatch(r"[0-9a-f]{32}", str(lease.get("checkout_instance", ""))) is None:
        raise LeaseError("checkout lease instance identity is malformed")
    if not isinstance(lease.get("expires_at"), int | float):
        raise LeaseError("checkout lease expiry is malformed")
    for key in ("checkout_root", "checkout_git_dir"):
        value = lease.get(key)
        if value is not None and (
            not isinstance(value, str) or not value or not Path(value).is_absolute()
        ):
            raise LeaseError(f"checkout lease {key} is malformed")
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
        raise LeaseError(f"checkout lease state write failed: {exc}") from exc
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
    return "Create an isolated checkout with `git-cli worktree add`, then retry there."


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
    if tool in COMMAND_TOOLS and not high_confidence_shell_mutation(command_from(payload)):
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
        emit_block(
            "Checkout lease state could not be verified, so repository mutation fails "
            f"closed: {exc}. Restore the managed runtime state path, then retry."
        )
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
