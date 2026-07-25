#!/usr/bin/env python3
"""Outcome recorder for the agent-docs finish-line validation gate.

Writes evidence markers under each declared validation marker directory so the
Stop gate (stop-finish-line-gate.py) can tell whether every declared validation
contract has passed since code was last edited:

- a session-scoped `session-<hash>/<stem>.dirty` marker, refreshed when a
  non-Markdown file under the repo is edited
  (Write/Edit/MultiEdit/NotebookEdit/apply_patch);
- a session- and product-scoped command marker per declared validation command,
  refreshed only after the completed command exits zero;
- a matching failed-outcome marker containing bounded metadata when the latest
  completed command exits non-zero.

Payloads without a session identifier retain the legacy shared marker names.
Identified repo-local and runtime tombstone state lives in directly addressable
session directories; one repo-scoped runtime lock serializes state transitions.

On PreToolUse, matching validation commands are transparently wrapped with a
tokenized EXIT trap. The trap writes the outcome directly through this script
before the shell exits and preserves the original status, including for
long-running commands completed through a later tool poll. If outcome metadata
cannot persist, the pending attempt remains and the Stop gate fails closed.

The recorder never persists command output. It no-ops outside a git repo, in a
repo that declares no AGENT_DOCS.toml, or when no intent declares a validation
contract. A matching validation is blocked before execution only when its
repo-local pending record or shared runtime tombstone cannot register safely.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from typing import Any

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    TERMINAL_OWNER_MARKER_NAMES,
    acquire_validation_state_lock,
    command_failed_marker,
    command_from,
    command_matches_validation,
    command_ran_marker,
    emit_block,
    file_paths_from_payload,
    git_toplevel,
    normalize_command_separators,
    read_payload,
    session_marker_key,
    strip_heredoc_bodies,
    touch_marker,
    tool_input_dict,
    validation_contracts,
    validation_command_target_key,
    validation_marker_set,
    validation_pending_marker,
    validation_tombstone_dir,
)

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"}
OUTCOME_SCHEMA = "agent-runtime-validation.outcome.v1"
PENDING_SCHEMA = "agent-runtime-validation.pending.v1"
RECOVERY_SCHEMA = "agent-runtime-validation.recovery.v1"
TOMBSTONE_SCHEMA = "agent-runtime-validation.tombstone.v1"
PENDING_MAX_AGE_SECONDS = 24 * 60 * 60
PENDING_MAX_RECORDS = 128
TOMBSTONE_MAX_BYTES = 64 * 1024
DIRTY_SNAPSHOT_MAX_BYTES = 64 * 1024
UNPROVABLE_VALIDATION_REASON = "validation_outcome_unprovable"
ValidationMatch = tuple[dict[str, str], int, str]
SHELL_EVALUATION_SENSITIVE_CHARS = frozenset("$`*?[]{}~<>!#\\\n\r")
SHELL_SYNTAX_WORDS = frozenset(
    {
        "case",
        "coproc",
        "do",
        "done",
        "elif",
        "else",
        "esac",
        "fi",
        "for",
        "function",
        "if",
        "in",
        "select",
        "then",
        "time",
        "until",
        "while",
    }
)
SHELL_ASSIGNMENT_WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\+)?=")


def tool_name(payload: Mapping[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def hook_event(payload: Mapping[str, Any]) -> str:
    for key in ("hook_event_name", "hookEventName"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def tool_use_id(payload: Mapping[str, Any]) -> str:
    for key in ("tool_use_id", "toolUseId"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def under_repo(path: str, repo_root: str) -> bool:
    if not path:
        return False
    absolute = path if os.path.isabs(path) else os.path.join(repo_root, path)
    absolute = os.path.abspath(absolute)
    root = os.path.abspath(repo_root)
    try:
        return os.path.commonpath([absolute, root]) == root
    except ValueError:
        return False


def write_json_marker(
    path: str, body: Mapping[str, Any], *, mtime_ns: int | None = None
) -> bool:
    temporary = ""
    descriptor = -1
    try:
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(body, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        if mtime_ns is not None:
            os.utime(temporary, ns=(mtime_ns, mtime_ns))
        os.replace(temporary, path)
        return True
    except OSError:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            os.unlink(temporary)
        except OSError:
            pass
        return False


def write_empty_marker(path: str, *, mtime_ns: int) -> bool:
    temporary = ""
    descriptor = -1
    try:
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
        )
        os.close(descriptor)
        descriptor = -1
        os.utime(temporary, ns=(mtime_ns, mtime_ns))
        os.replace(temporary, path)
        return True
    except OSError:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            os.unlink(temporary)
        except OSError:
            pass
        return False


def remove_marker(path: str) -> bool:
    try:
        os.unlink(path)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def external_tombstone_path(
    repo_root: str, pending_path: str, *, session_key: str = ""
) -> str:
    digest = hashlib.sha256(pending_path.encode("utf-8")).hexdigest()[:32]
    return os.path.join(
        validation_tombstone_dir(repo_root, session_key),
        f"attempt-{digest}.json",
    )


def tombstone_body(
    recovery: Mapping[str, Any],
    *,
    status: str,
    exit_code: int | None = None,
    event: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": TOMBSTONE_SCHEMA,
        "repo_root": recovery["repo_root"],
        "product": recovery["product"],
        "session_key": recovery.get("session_key") or None,
        "contract_key": recovery["contract_key"],
        "pending": recovery["pending"],
        "dirty": recovery["dirty"],
        "dirty_started_ns": recovery["dirty_started_ns"],
        "attempt_started_ns": recovery["attempt_started_ns"],
        "commands": recovery["commands"],
        "status": status,
        "exit_code": exit_code,
        "event": event,
    }


def write_tombstone(
    recovery: Mapping[str, Any],
    *,
    status: str = "pending",
    exit_code: int | None = None,
    event: str = "",
) -> bool:
    return write_json_marker(
        str(recovery["tombstone"]),
        tombstone_body(
            recovery,
            status=status,
            exit_code=exit_code,
            event=event,
        ),
        mtime_ns=int(recovery["attempt_started_ns"]),
    )


def read_regular_json(path: str) -> dict[str, Any] | None:
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > TOMBSTONE_MAX_BYTES:
            return None
        with os.fdopen(descriptor, encoding="utf-8") as handle:
            descriptor = -1
            loaded = json.load(handle)
    except (OSError, ValueError):
        return None
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
    return loaded if isinstance(loaded, dict) else None


def outcome_targets(raw: Any) -> frozenset[str] | None:
    if not isinstance(raw, list) or not raw:
        return None
    targets: set[str] = set()
    for entry in raw:
        if not isinstance(entry, Mapping):
            return None
        target_key = entry.get("target_key")
        if (
            not isinstance(target_key, str)
            or re.fullmatch(r"[0-9a-f]{64}", target_key) is None
        ):
            return None
        targets.add(target_key)
    return frozenset(targets) if targets else None


def supersede_recovery_tombstones(
    recovery: Mapping[str, Any], *, include_current: bool, include_legacy: bool
) -> None:
    """Remove only logical targets covered by this newer recovery attempt."""
    current_session = recovery.get("session_key") or None
    directories = [os.path.dirname(str(recovery["tombstone"]))]
    if current_session is not None and include_legacy:
        directories.append(validation_tombstone_dir(str(recovery["repo_root"])))
    entries: list[os.DirEntry[str]] = []
    for directory in dict.fromkeys(directories):
        try:
            entries.extend(os.scandir(directory))
        except OSError:
            pass
    current_targets = outcome_targets(recovery["commands"])
    if current_targets is None:
        return
    current_started = int(recovery["attempt_started_ns"])
    for entry in entries:
        if not entry.name.startswith("attempt-") or not entry.name.endswith(".json"):
            continue
        body = read_regular_json(entry.path)
        if body is None or body.get("schema_version") != TOMBSTONE_SCHEMA:
            continue
        started = body.get("attempt_started_ns")
        previous_targets = outcome_targets(body.get("commands"))
        if body.get("repo_root") != recovery["repo_root"]:
            continue
        if body.get("product") != recovery["product"]:
            continue
        previous_session = body.get("session_key")
        active_sessions = {current_session}
        if current_session is None or include_legacy:
            active_sessions.add(None)
        if previous_session not in active_sessions:
            continue
        if body.get("contract_key") != recovery["contract_key"]:
            continue
        if not isinstance(started, int) or isinstance(started, bool):
            continue
        if started > current_started or (started == current_started and not include_current):
            continue
        if previous_targets is None or previous_targets.isdisjoint(current_targets):
            continue
        commands = body.get("commands")
        assert isinstance(commands, list)
        remaining = [
            command
            for command in commands
            if isinstance(command, Mapping)
            and command.get("target_key") not in current_targets
        ]
        if remaining:
            retained = dict(body)
            retained["commands"] = remaining
            write_json_marker(entry.path, retained, mtime_ns=started)
        else:
            remove_marker(entry.path)
    current_directory = os.path.dirname(str(recovery["tombstone"]))
    if current_session is not None:
        try:
            os.rmdir(current_directory)
            os.rmdir(os.path.dirname(current_directory))
        except OSError:
            pass


def prune_superseded_tombstones(recovery: Mapping[str, Any]) -> None:
    """Let the newest registered attempt represent every older active one."""
    supersede_recovery_tombstones(
        recovery, include_current=False, include_legacy=False
    )


def clear_recovery_tombstones(
    recovery: Mapping[str, Any], *, include_legacy: bool
) -> None:
    """Clear this and older attempts after repo-local outcome persistence."""
    supersede_recovery_tombstones(
        recovery, include_current=True, include_legacy=include_legacy
    )


def write_failure(
    path: str, exit_code: int | None, event: str, *, attempt_started_ns: int
) -> bool:
    return write_json_marker(
        path,
        {
            "schema_version": OUTCOME_SCHEMA,
            "status": "failed",
            "exit_code": exit_code,
            "event": event,
            "attempt_started_ns": attempt_started_ns,
        },
        mtime_ns=attempt_started_ns,
    )


def safe_outcome_paths(pending_path: str, entry: Mapping[str, Any]) -> tuple[str, str] | None:
    ran = entry.get("ran")
    failed = entry.get("failed")
    if not isinstance(ran, str) or not isinstance(failed, str):
        return None
    directory = os.path.realpath(os.path.dirname(pending_path))
    if not marker_parent_is(ran, directory) or not marker_parent_is(failed, directory):
        return None
    return ran, failed


def marker_parent_is(path: str, directory: str) -> bool:
    if not os.path.isabs(path) or os.path.basename(path) in {"", ".", ".."}:
        return False
    try:
        return os.path.realpath(os.path.dirname(path)) == directory
    except OSError:
        return False


def recovery_record(
    pending_path: str, raw: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping) or raw.get("schema_version") != RECOVERY_SCHEMA:
        return None
    if raw.get("pending") != pending_path:
        return None
    started = raw.get("attempt_started_ns")
    dirty = raw.get("dirty")
    dirty_started = raw.get("dirty_started_ns")
    commands = raw.get("commands")
    declared_root = raw.get("repo_root")
    product = raw.get("product")
    session_key = raw.get("session_key")
    contract_key = raw.get("contract_key")
    tombstone = raw.get("tombstone")
    if (
        not isinstance(started, int)
        or isinstance(started, bool)
        or started <= 0
        or (
            dirty_started is not None
            and (
                not isinstance(dirty_started, int)
                or isinstance(dirty_started, bool)
                or dirty_started <= 0
                or dirty_started > started
            )
        )
        or not isinstance(dirty, str)
        or not isinstance(declared_root, str)
        or product not in {"codex", "claude", "shared"}
        or (
            session_key is not None
            and (
                not isinstance(session_key, str)
                or re.fullmatch(r"[0-9a-f]{64}", session_key) is None
            )
        )
        or not isinstance(contract_key, str)
        or re.fullmatch(r"[0-9a-f]{64}", contract_key) is None
        or not isinstance(tombstone, str)
        or not isinstance(commands, list)
        or not commands
    ):
        return None

    directory = os.path.realpath(os.path.dirname(pending_path))
    root = os.path.realpath(declared_root)
    try:
        resolved = subprocess.run(
            ["git", "-C", root, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if resolved.returncode != 0 or not resolved.stdout.strip():
        return None
    if os.path.realpath(resolved.stdout.strip()) != root:
        return None
    if tombstone != external_tombstone_path(
        root, pending_path, session_key=session_key or ""
    ):
        return None
    try:
        if os.path.commonpath((root, directory)) != root:
            return None
    except ValueError:
        return None
    if not marker_parent_is(pending_path, directory) or not marker_parent_is(
        dirty, directory
    ):
        return None

    normalized_commands: list[dict[str, str]] = []
    for entry in commands:
        if not isinstance(entry, Mapping):
            return None
        paths = safe_outcome_paths(pending_path, entry)
        if paths is None:
            return None
        target_key = entry.get("target_key")
        if (
            not isinstance(target_key, str)
            or re.fullmatch(r"[0-9a-f]{64}", target_key) is None
        ):
            return None
        ran, failed = paths
        normalized_commands.append(
            {"target_key": target_key, "ran": ran, "failed": failed}
        )
    return {
        "repo_root": root,
        "pending": pending_path,
        "tombstone": tombstone,
        "product": product,
        "session_key": session_key,
        "contract_key": contract_key,
        "attempt_started_ns": started,
        "dirty_started_ns": dirty_started,
        "dirty": dirty,
        "commands": normalized_commands,
    }


def encode_recovery(body: Mapping[str, Any]) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_recovery(encoded: str) -> dict[str, Any] | None:
    try:
        decoded = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
        loaded = json.loads(decoded)
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def open_lock_file(path: str):
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError("validation lock is not a regular file")
        return os.fdopen(descriptor, "a+", encoding="utf-8")
    except Exception:
        os.close(descriptor)
        raise


def acquire_edit_locks(dirty_paths: list[str]) -> list[Any] | None:
    """Acquire every marker-directory lock in stable order to avoid deadlocks."""
    handles: list[Any] = []
    directories = sorted({os.path.dirname(path) for path in dirty_paths})
    try:
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            handle = open_lock_file(
                os.path.join(directory, ".agent-runtime-validation.lock")
            )
            try:
                fcntl.flock(handle, fcntl.LOCK_EX)
            except OSError:
                handle.close()
                raise
            handles.append(handle)
        return handles
    except OSError:
        for handle in reversed(handles):
            handle.close()
        return None


def terminal_markers_for_edit(dirty_paths: list[str]) -> list[str] | None:
    """Return every terminal owner invalidated by a shared edit generation."""
    terminals: list[str] = []
    for directory in sorted({os.path.dirname(path) for path in dirty_paths}):
        try:
            for entry in os.scandir(directory):
                if entry.name in TERMINAL_OWNER_MARKER_NAMES:
                    terminals.append(entry.path)
        except OSError:
            return None
    return terminals


def marker_mtime_ns(path: str) -> int | None:
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    return metadata.st_mtime_ns


def dirty_marker_snapshot(path: str) -> dict[str, Any] | None:
    """Capture enough internal marker state to roll back a blocked edit."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return {"kind": "missing"}
    except OSError:
        return None
    if stat.S_ISLNK(metadata.st_mode):
        try:
            return {"kind": "symlink", "target": os.readlink(path)}
        except OSError:
            return None
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > DIRTY_SNAPSHOT_MAX_BYTES:
        return None
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        current = os.fstat(descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_size > DIRTY_SNAPSHOT_MAX_BYTES
            or current.st_dev != metadata.st_dev
            or current.st_ino != metadata.st_ino
        ):
            return None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            content = handle.read(DIRTY_SNAPSHOT_MAX_BYTES + 1)
        if len(content) > DIRTY_SNAPSHOT_MAX_BYTES:
            return None
        return {
            "kind": "regular",
            "content": content,
            "mode": stat.S_IMODE(current.st_mode),
            "atime_ns": current.st_atime_ns,
            "mtime_ns": current.st_mtime_ns,
        }
    except OSError:
        return None
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def restore_dirty_marker(
    path: str,
    snapshot: Mapping[str, Any],
    *,
    expected_generation_ns: int,
) -> bool:
    try:
        current = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        if snapshot.get("kind") == "missing":
            return True
    except OSError:
        return False
    else:
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_size != 0
            or current.st_mtime_ns != expected_generation_ns
        ):
            # Another writer changed the provisional marker. Never erase that
            # potentially newer edit generation during rollback.
            return True
    kind = snapshot.get("kind")
    if kind == "missing":
        return remove_marker(path)
    temporary = ""
    descriptor = -1
    try:
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".rollback", dir=directory
        )
        if kind == "regular":
            content = snapshot.get("content")
            mode = snapshot.get("mode")
            atime_ns = snapshot.get("atime_ns")
            mtime_ns = snapshot.get("mtime_ns")
            if (
                not isinstance(content, bytes)
                or not isinstance(mode, int)
                or not isinstance(atime_ns, int)
                or not isinstance(mtime_ns, int)
            ):
                raise OSError("invalid dirty marker snapshot")
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(content)
            os.chmod(temporary, mode, follow_symlinks=False)
            os.utime(
                temporary,
                ns=(atime_ns, mtime_ns),
                follow_symlinks=False,
            )
        elif kind == "symlink":
            target = snapshot.get("target")
            if not isinstance(target, str):
                raise OSError("invalid dirty marker symlink snapshot")
            os.close(descriptor)
            descriptor = -1
            os.unlink(temporary)
            temporary = f"{temporary}.link"
            os.symlink(target, temporary)
        else:
            raise OSError("unsupported dirty marker snapshot")
        os.replace(temporary, path)
        return True
    except OSError:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        return False


def ensure_recovery_dirty(recovery: Mapping[str, Any]) -> bool:
    dirty = recovery["dirty"]
    started = recovery["dirty_started_ns"]
    if started is None:
        return True
    current = marker_mtime_ns(dirty)
    if current is not None:
        return True
    return write_empty_marker(dirty, mtime_ns=started)


def shared_dirty_generation_ns(
    repo_root: str,
    markers: Mapping[str, str],
) -> int | None:
    """Recover the edit generation without advancing it on validation retries."""
    generations: list[int] = []
    current = marker_mtime_ns(markers["dirty"])
    if current is not None:
        generations.append(current)
    root = os.path.realpath(repo_root)
    current_session = markers.get("session_key") or None
    active_sessions = (
        {None, current_session} if current_session is not None else {None}
    )
    directories = [validation_tombstone_dir(repo_root)]
    if current_session is not None:
        directories.append(
            validation_tombstone_dir(repo_root, current_session)
        )
    entries: list[os.DirEntry[str]] = []
    for directory in directories:
        try:
            entries.extend(os.scandir(directory))
        except OSError:
            pass
    for entry in entries:
        if not entry.name.startswith("attempt-") or not entry.name.endswith(".json"):
            continue
        body = read_regular_json(entry.path)
        if (
            body is None
            or body.get("schema_version") != TOMBSTONE_SCHEMA
            or body.get("repo_root") != root
            or body.get("contract_key") != markers["contract_key"]
            or body.get("session_key") not in active_sessions
        ):
            continue
        attempted = body.get("attempt_started_ns")
        generation = body.get("dirty_started_ns")
        if (
            isinstance(attempted, int)
            and not isinstance(attempted, bool)
            and isinstance(generation, int)
            and not isinstance(generation, bool)
            and 0 < generation <= attempted
        ):
            generations.append(generation)
    return max(generations, default=None)


def record_missing_pending_outcome(
    recovery: Mapping[str, Any], status: int | None, event: str
) -> None:
    started = recovery["attempt_started_ns"]
    ensure_recovery_dirty(recovery)
    for entry in recovery["commands"]:
        ran = entry["ran"]
        failed = entry["failed"]
        latest = max(marker_mtime_ns(ran) or 0, marker_mtime_ns(failed) or 0)
        if latest > started:
            continue
        write_failure(
            failed,
            status if status else None,
            f"{event}-pending-state-missing",
            attempt_started_ns=started,
        )


def record_unlocked_recovery_failure(
    recovery: Mapping[str, Any], status: int | None, event: str
) -> None:
    """Leave a conservative signal when the shared lock itself is unusable."""
    fail_closed = dict(recovery)
    fail_closed["attempt_started_ns"] = max(
        int(recovery["attempt_started_ns"]), time.time_ns()
    )
    record_missing_pending_outcome(
        fail_closed, status, f"{event}-lock-unavailable"
    )


def record_pending_outcome(
    pending_path: str,
    status: int | None,
    event: str,
    raw_recovery: Mapping[str, Any] | None = None,
) -> None:
    recovery = recovery_record(pending_path, raw_recovery)
    if raw_recovery is not None and recovery is None:
        return
    state_lock = None
    if recovery is not None:
        try:
            state_lock = acquire_validation_state_lock(
                str(recovery["repo_root"])
            )
        except OSError:
            return
    if recovery is not None:
        write_tombstone(
            recovery,
            status="completed",
            exit_code=status,
            event=event,
        )
    try:
        os.makedirs(os.path.dirname(pending_path), exist_ok=True)
        lock_path = os.path.join(
            os.path.dirname(pending_path), ".agent-runtime-validation.lock"
        )
        lock_handle = open_lock_file(lock_path)
    except OSError:
        if recovery is not None:
            record_unlocked_recovery_failure(recovery, status, event)
        return
    with lock_handle:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(pending_path, flags)
            with os.fdopen(descriptor, encoding="utf-8") as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode):
                    raise OSError("pending state is not a regular file")
                body = json.load(handle)
        except (OSError, ValueError):
            if recovery is not None:
                record_missing_pending_outcome(recovery, status, event)
            return
        if not isinstance(body, dict) or body.get("schema_version") != PENDING_SCHEMA:
            if recovery is not None:
                record_missing_pending_outcome(recovery, status, event)
            return
        raw_started = body.get("attempt_started_ns")
        raw_entries = body.get("commands")
        if recovery is not None:
            if (
                raw_started != recovery["attempt_started_ns"]
                or raw_entries != recovery["commands"]
            ):
                record_missing_pending_outcome(recovery, status, event)
                return
            attempt_started_ns = int(recovery["attempt_started_ns"])
            entries = recovery["commands"]
        else:
            if isinstance(raw_started, int) and not isinstance(raw_started, bool):
                attempt_started_ns = raw_started
            else:
                try:
                    attempt_started_ns = os.stat(pending_path).st_mtime_ns
                except OSError:
                    return
            entries = raw_entries
        if not isinstance(entries, list):
            if recovery is not None:
                record_missing_pending_outcome(recovery, status, event)
            return
        persisted = recovery is None or ensure_recovery_dirty(recovery)
        valid_entries = 0
        for entry in entries:
            if not isinstance(entry, Mapping):
                persisted = False
                continue
            paths = safe_outcome_paths(pending_path, entry)
            if paths is None:
                persisted = False
                continue
            valid_entries += 1
            ran, failed = paths
            latest = max(
                marker_mtime_ns(ran) or 0,
                marker_mtime_ns(failed) or 0,
            )
            if latest > attempt_started_ns:
                continue
            if status == 0:
                if write_empty_marker(ran, mtime_ns=attempt_started_ns):
                    if not remove_marker(failed):
                        persisted = False
                else:
                    persisted = False
            elif not write_failure(
                failed,
                status,
                event,
                attempt_started_ns=attempt_started_ns,
            ):
                persisted = False
        if persisted and valid_entries and remove_marker(pending_path):
            if recovery is not None:
                clear_recovery_tombstones(
                    recovery, include_legacy=status == 0
                )
            return
        if valid_entries:
            retained = dict(body)
            retained["outcome_persistence_failed"] = True
            retained["last_event"] = event
            write_json_marker(
                pending_path,
                retained,
                mtime_ns=attempt_started_ns,
            )
        elif recovery is not None:
            record_missing_pending_outcome(recovery, status, event)


def record_outcome_cli(argv: list[str]) -> int:
    if len(argv) < 5 or argv[1] != "--record-outcome":
        return 64
    try:
        status = int(argv[2])
    except ValueError:
        return 64
    if status < 0 or status > 255:
        return 64
    pending: list[tuple[str, dict[str, Any] | None]] = []
    cursor = 3
    while cursor + 1 < len(argv) and argv[cursor] == "--pending":
        path = argv[cursor + 1]
        cursor += 2
        recovery = None
        if cursor + 1 < len(argv) and argv[cursor] == "--recovery":
            recovery = decode_recovery(argv[cursor + 1])
            if recovery is None:
                return 64
            cursor += 2
        pending.append((path, recovery))
    if cursor != len(argv) or not pending:
        return 64
    for path, recovery in pending:
        record_pending_outcome(path, status, "wrapped-command", recovery)
    return ALLOW


def validation_matches(
    repo_root: str,
    contracts: list[dict[str, Any]],
    command: str,
    *,
    session_key: str = "",
) -> list[ValidationMatch]:
    matches: list[ValidationMatch] = []
    for contract in contracts:
        try:
            markers = validation_marker_set(
                repo_root, contract["marker"], session_key=session_key
            )
        except ValueError:
            continue
        for index, declared in enumerate(contract["commands"]):
            if command_matches_validation(command, declared):
                matches.append((markers, index, declared))
    return matches


def canonical_shell_word(raw: str) -> str:
    """Normalize harmless quoting without erasing evaluation provenance."""
    try:
        cooked = shlex.split(raw, posix=True)
    except ValueError:
        return raw
    if len(cooked) != 1:
        return raw
    value = cooked[0]
    if (
        value in SHELL_SYNTAX_WORDS
        or SHELL_ASSIGNMENT_WORD.match(value)
        or any(char in SHELL_EVALUATION_SENSITIVE_CHARS for char in value)
    ):
        return raw
    return value


def normalized_shell_tokens(command: str) -> list[tuple[str, str]]:
    """Tokenize while retaining the shell syntax that controls evaluation.

    Ordinary shlex token values erase quote provenance, making a literal quoted
    `'||'` argument indistinguishable from a live `||` operator. The hook grants
    permission to its rewritten input, so authorization keeps raw spelling for
    evaluation-sensitive words, canonicalizes harmless quoting, and types
    unquoted operators explicitly.
    """
    source = normalize_command_separators(
        strip_heredoc_bodies(command.strip())
    )
    tokens: list[tuple[str, str]] = []
    word: list[str] = []
    quote: str | None = None
    index = 0

    def flush_word() -> None:
        if word:
            tokens.append(("word", canonical_shell_word("".join(word))))
            word.clear()

    while index < len(source):
        char = source[index]
        if quote == "'":
            word.append(char)
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            word.append(char)
            if char == "\\" and index + 1 < len(source):
                word.append(source[index + 1])
                index += 2
                continue
            if char == '"':
                quote = None
            index += 1
            continue
        if char == "\\" and index + 1 < len(source):
            word.extend((char, source[index + 1]))
            index += 2
            continue
        if char in {"'", '"'}:
            quote = char
            word.append(char)
            index += 1
            continue
        if char.isspace():
            flush_word()
            index += 1
            continue
        if char in ";&|()":
            flush_word()
            end = index + 1
            while end < len(source) and source[end] in ";&|()":
                end += 1
            tokens.append(("operator", source[index:end]))
            index = end
            continue
        word.append(char)
        index += 1

    if quote is not None:
        return []
    flush_word()
    return tokens


def outcome_status_is_provable(command: str, matches: list[ValidationMatch]) -> bool:
    """Whether the aggregate shell status can safely credit every match.

    A declared command owns its own control-flow semantics. The hook's rewrite
    grants permission to its complete updated input, so every `&&` segment must
    itself be a declared validation command; unrelated preambles or suffixes
    are not rewritten. Additional `;`, `||`, pipeline, background, or grouping
    operators could also mask a failed validation and are not credited unless
    they are part of one exact declared command.
    """
    actual = normalized_shell_tokens(command)
    if not actual:
        return False
    declared: set[tuple[tuple[str, str], ...]] = set()
    for match in matches:
        tokens = tuple(normalized_shell_tokens(match[2]))
        if tokens:
            declared.add(tokens)
    if tuple(actual) in declared:
        return True
    segments: list[tuple[tuple[str, str], ...]] = []
    current: list[tuple[str, str]] = []
    for token in actual:
        if token[0] == "operator":
            if token[1] != "&&" or not current:
                return False
            segments.append(tuple(current))
            current = []
        else:
            current.append(token)
    if not current:
        return False
    segments.append(tuple(current))
    return len(segments) > 1 and all(segment in declared for segment in segments)


def outcome_token(payload: Mapping[str, Any], command: str) -> str:
    identity = tool_use_id(payload)
    if identity:
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return os.urandom(8).hex()


def generated_wrapper_token(command: str) -> str | None:
    match = re.search(
        r"(?m)^(__agent_runtime_validation_report_([0-9a-f]{16}))\(\) \{",
        command,
    )
    if match is None:
        return None
    function, token = match.groups()
    return token if f"trap '{function}' EXIT" in command else None


def unresolved_persistence_entries(
    path: str,
) -> tuple[int, list[dict[str, str]]] | None:
    try:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
    except (OSError, ValueError):
        return None
    if (
        not isinstance(body, dict)
        or body.get("schema_version") != PENDING_SCHEMA
        or body.get("outcome_persistence_failed") is not True
    ):
        return None
    started = body.get("attempt_started_ns")
    commands = body.get("commands")
    if (
        not isinstance(started, int)
        or isinstance(started, bool)
        or not isinstance(commands, list)
    ):
        return None
    unresolved: list[dict[str, str]] = []
    for entry in commands:
        if not isinstance(entry, Mapping):
            continue
        paths = safe_outcome_paths(path, entry)
        if paths is None:
            continue
        ran, failed = paths
        if max(marker_mtime_ns(ran) or 0, marker_mtime_ns(failed) or 0) <= started:
            unresolved.append({"ran": ran, "failed": failed})
    if not unresolved:
        return None
    return started, unresolved


def prune_pending_records(markers: Mapping[str, str]) -> None:
    directory = markers["dir"]
    stem = markers.get("command_stem") or markers["stem"]
    prefix = f"{stem}.pending."
    try:
        entries = [
            entry
            for entry in os.scandir(directory)
            if entry.name.startswith(prefix)
            and entry.name.endswith(".json")
            and entry.is_file(follow_symlinks=False)
        ]
    except OSError:
        return
    records: list[tuple[float, str]] = []
    for entry in entries:
        try:
            records.append((entry.stat(follow_symlinks=False).st_mtime, entry.path))
        except OSError:
            pass
    ordered = sorted(records, reverse=True)
    protected: list[tuple[float, str, int, list[dict[str, str]]]] = []
    ordinary: list[tuple[float, str]] = []
    for mtime, path in ordered:
        persistence = unresolved_persistence_entries(path)
        if persistence is None:
            ordinary.append((mtime, path))
            continue
        started, commands = persistence
        protected.append((mtime, path, started, commands))

    # Equivalent fail-closed blockers must not grow without bound when marker
    # persistence repeatedly fails. Merge every unresolved target into the
    # newest protected record before removing its superseded peers. Using the
    # newest attempt time is conservative: it can extend a block, never release
    # one early.
    if len(protected) > 1:
        selected = max(protected, key=lambda record: (record[2], record[0]))
        commands_by_paths: dict[tuple[str, str], dict[str, str]] = {}
        latest_started = 0
        for _mtime, _path, started, commands in protected:
            latest_started = max(latest_started, started)
            for command in commands:
                commands_by_paths[(command["ran"], command["failed"])] = command
        if write_json_marker(
            selected[1],
            {
                "schema_version": PENDING_SCHEMA,
                "attempt_started_ns": latest_started,
                "commands": list(commands_by_paths.values()),
                "outcome_persistence_failed": True,
                "last_event": "compacted-persistence-failures",
            },
            mtime_ns=latest_started,
        ):
            for _mtime, path, _started, _commands in protected:
                if path != selected[1]:
                    remove_marker(path)
            protected = [
                (latest_started / 1_000_000_000, selected[1], latest_started, [])
            ]

    now = time.time()
    ordinary_capacity = max(
        0,
        PENDING_MAX_RECORDS - 1 - len(protected),
    )
    for position, (mtime, path) in enumerate(ordinary):
        if position >= ordinary_capacity or now - mtime > PENDING_MAX_AGE_SECONDS:
            remove_marker(path)


def pending_records(
    repo_root: str, matches: list[ValidationMatch], token: str
) -> tuple[list[dict[str, Any]], bool]:
    grouped: dict[str, tuple[dict[str, str], dict[int, str]]] = {}
    for markers, index, declared in matches:
        key = markers["dir"] + "\0" + markers["command_stem"]
        if key not in grouped:
            grouped[key] = (markers, {})
        grouped[key][1][index] = declared

    attempts: list[dict[str, Any]] = []
    registration_failed = False
    attempt_started_ns = time.time_ns()
    terminal_snapshots: dict[str, dict[str, Any]] = {}
    invalidated_terminals: list[str] = []
    for markers, indexed_commands in grouped.values():
        lock_path = os.path.join(
            markers["dir"], ".agent-runtime-validation.lock"
        )
        try:
            os.makedirs(markers["dir"], exist_ok=True)
            lock_handle = open_lock_file(lock_path)
        except OSError:
            registration_failed = True
            continue
        with lock_handle:
            try:
                fcntl.flock(lock_handle, fcntl.LOCK_EX)
            except OSError:
                registration_failed = True
                continue
            terminal = markers["terminal"]
            if terminal not in terminal_snapshots:
                snapshot = dirty_marker_snapshot(terminal)
                if snapshot is None:
                    registration_failed = True
                    continue
                terminal_snapshots[terminal] = snapshot
                if not remove_marker(terminal):
                    registration_failed = True
                    continue
                if snapshot["kind"] != "missing":
                    invalidated_terminals.append(terminal)
            prune_pending_records(markers)
            path = validation_pending_marker(markers, token)
            commands = [
                {
                    "target_key": validation_command_target_key(
                        markers, index, declared
                    ),
                    "ran": command_ran_marker(markers, index),
                    "failed": command_failed_marker(markers, index),
                }
                for index, declared in sorted(indexed_commands.items())
            ]
            if not write_json_marker(
                path,
                {
                    "schema_version": PENDING_SCHEMA,
                    "attempt_started_ns": attempt_started_ns,
                    "commands": commands,
                },
                mtime_ns=attempt_started_ns,
            ):
                registration_failed = True
                continue
            recovery = {
                "schema_version": RECOVERY_SCHEMA,
                "pending": path,
                "repo_root": os.path.realpath(repo_root),
                "product": markers["product"],
                "session_key": markers.get("session_key") or None,
                "contract_key": markers["contract_key"],
                "dirty": markers["dirty"],
                "dirty_started_ns": shared_dirty_generation_ns(
                    repo_root,
                    markers,
                ),
                "attempt_started_ns": attempt_started_ns,
                "commands": commands,
            }
            recovery["tombstone"] = external_tombstone_path(
                repo_root,
                path,
                session_key=markers.get("session_key") or "",
            )
            if write_tombstone(recovery):
                attempts.append(recovery)
            else:
                remove_marker(path)
                registration_failed = True
    if not registration_failed:
        for attempt in attempts:
            prune_superseded_tombstones(attempt)
    elif invalidated_terminals:
        lock_handles = acquire_edit_locks(invalidated_terminals)
        if lock_handles is not None:
            try:
                for terminal in reversed(invalidated_terminals):
                    restore_dirty_marker(
                        terminal,
                        terminal_snapshots[terminal],
                        expected_generation_ns=attempt_started_ns,
                    )
            finally:
                for handle in reversed(lock_handles):
                    handle.close()
    return attempts, registration_failed


def discard_registered_attempts(attempts: list[dict[str, Any]]) -> None:
    for attempt in attempts:
        remove_marker(str(attempt["pending"]))
        tombstone = str(attempt["tombstone"])
        remove_marker(tombstone)
        if attempt.get("session_key"):
            try:
                os.rmdir(os.path.dirname(tombstone))
                os.rmdir(os.path.dirname(os.path.dirname(tombstone)))
            except OSError:
                pass


def registration_block_reason() -> str:
    return (
        "Validation could not register authoritative outcome state. The command "
        "was not started; repair the repo validation directory, lock, or shared "
        "runtime state and retry."
    )


def edit_registration_block_reason(*, rollback_failed: bool = False) -> str:
    recovery = (
        " Some earlier dirty markers could not be restored, so validation may "
        "remain conservatively required after repair."
        if rollback_failed
        else ""
    )
    return (
        "Code edit could not register validation dirty state. The edit was not "
        "started; repair the validation marker path or directory and retry."
        f"{recovery}"
    )


def wrapped_command(command: str, token: str, pending: list[dict[str, Any]]) -> str:
    function = f"__agent_runtime_validation_report_{token}"
    status = f"__agent_runtime_validation_status_{token}"
    recorder = shlex.quote(os.path.abspath(__file__))
    validation_state_path = str(pending[0]["tombstone"])
    parent_levels = 5 if pending[0].get("session_key") else 3
    for _ in range(parent_levels):
        validation_state_path = os.path.dirname(validation_state_path)
    validation_state_home = shlex.quote(validation_state_path)
    pending_args = " ".join(
        f"--pending {shlex.quote(str(attempt['pending']))} "
        f"--recovery {shlex.quote(encode_recovery(attempt))}"
        for attempt in pending
    )
    return (
        f"{function}() {{\n"
        f"  {status}=$?\n"
        "  trap - EXIT\n"
        "  AGENT_RUNTIME_VALIDATION_STATE_HOME="
        f"{validation_state_home} {recorder} --record-outcome "
        f"\"${{{status}}}\" {pending_args} "
        ">/dev/null 2>&1 || true\n"
        f"  exit \"${{{status}}}\"\n"
        "}\n"
        f"trap '{function}' EXIT\n"
        f"{command}"
    )


def emit_rewrite(payload: Mapping[str, Any], command: str) -> None:
    updated_input = tool_input_dict(payload)
    updated_input["command"] = command
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": updated_input,
                }
            }
        )
    )
    sys.stdout.write("\n")


def emit_unprovable_validation_advisory() -> None:
    """Explain non-credit without retaining or echoing submitted shell input."""
    message = (
        f"[reason: {UNPROVABLE_VALIDATION_REASON}] Declared validation was "
        "detected, but this shell shape cannot prove its aggregate outcome. "
        "The invocation will run unchanged and will not satisfy the finish-line "
        "gate. Run the declared validation command shape exactly, or move "
        "required toolchain or environment setup into a repository-owned "
        "declared validation wrapper."
    )
    sys.stdout.write(json.dumps({"systemMessage": message}))
    sys.stdout.write("\n")


def main() -> int:
    if len(sys.argv) > 1:
        return record_outcome_cli(sys.argv)

    payload = read_payload()
    active_session_key = session_marker_key(payload)
    tool = tool_name(payload)
    event = hook_event(payload)
    command = command_from(payload) if tool == "Bash" else ""
    if tool == "Bash" and event not in {"", "PreToolUse"}:
        return ALLOW

    repo_root = git_toplevel()
    if not repo_root:
        return ALLOW
    contracts = validation_contracts(repo_root)
    if not contracts:
        return ALLOW

    if tool == "Bash":
        matches = validation_matches(
            repo_root, contracts, command, session_key=active_session_key
        )
        if not matches:
            return ALLOW
        if event == "PreToolUse":
            if generated_wrapper_token(command) is not None:
                return ALLOW
            if not outcome_status_is_provable(command, matches):
                emit_unprovable_validation_advisory()
                return ALLOW
            try:
                state_lock = acquire_validation_state_lock(repo_root)
            except OSError:
                emit_block(registration_block_reason())
                return ALLOW
            token = outcome_token(payload, command)
            pending, registration_failed = pending_records(
                repo_root, matches, token
            )
            if registration_failed:
                discard_registered_attempts(pending)
                emit_block(registration_block_reason())
                return ALLOW
            if pending:
                emit_rewrite(payload, wrapped_command(command, token, pending))
        elif not event:
            # Compatibility for older direct invocations and existing fixtures.
            # Product hook wiring always supplies an explicit event name.
            try:
                state_lock = acquire_validation_state_lock(repo_root)
            except OSError:
                emit_block(registration_block_reason())
                return ALLOW
            for markers, index, _declared in matches:
                touch_marker(command_ran_marker(markers, index))
    elif tool in EDIT_TOOLS:
        for path in file_paths_from_payload(payload):
            if path.endswith(".md"):
                continue
            if under_repo(path, repo_root):
                try:
                    state_lock = acquire_validation_state_lock(repo_root)
                except OSError:
                    emit_block(edit_registration_block_reason())
                    return ALLOW
                dirty_paths: list[str] = []
                for contract in contracts:
                    try:
                        markers = validation_marker_set(
                            repo_root,
                            contract["marker"],
                            session_key=active_session_key,
                        )
                    except ValueError:
                        emit_block(edit_registration_block_reason())
                        return ALLOW
                    if markers["dirty"] not in dirty_paths:
                        dirty_paths.append(markers["dirty"])
                lock_handles = acquire_edit_locks(dirty_paths)
                if lock_handles is None:
                    emit_block(edit_registration_block_reason())
                    return ALLOW
                registration_failed = False
                rollback_failed = False
                try:
                    terminal_paths = terminal_markers_for_edit(dirty_paths)
                    if terminal_paths is None:
                        registration_failed = True
                        terminal_paths = []
                    snapshots: dict[str, dict[str, Any]] = {}
                    if not registration_failed:
                        for dirty in dirty_paths:
                            snapshot = dirty_marker_snapshot(dirty)
                            if snapshot is None:
                                registration_failed = True
                                break
                            snapshots[dirty] = snapshot
                    terminal_snapshots: dict[str, dict[str, Any]] = {}
                    if not registration_failed:
                        for terminal in terminal_paths:
                            snapshot = dirty_marker_snapshot(terminal)
                            if snapshot is None:
                                registration_failed = True
                                break
                            terminal_snapshots[terminal] = snapshot
                    edit_generation_ns = time.time_ns()
                    touched: list[str] = []
                    removed_terminals: list[str] = []
                    if not registration_failed:
                        for dirty in dirty_paths:
                            if write_empty_marker(
                                dirty, mtime_ns=edit_generation_ns
                            ):
                                touched.append(dirty)
                                continue
                            registration_failed = True
                            break
                    if not registration_failed:
                        for terminal in terminal_paths:
                            if remove_marker(terminal):
                                if terminal_snapshots[terminal]["kind"] != "missing":
                                    removed_terminals.append(terminal)
                                continue
                            registration_failed = True
                            break
                    if registration_failed:
                        for terminal in reversed(removed_terminals):
                            if not restore_dirty_marker(
                                terminal,
                                terminal_snapshots[terminal],
                                expected_generation_ns=edit_generation_ns,
                            ):
                                rollback_failed = True
                        for dirty in reversed(touched):
                            if not restore_dirty_marker(
                                dirty,
                                snapshots[dirty],
                                expected_generation_ns=edit_generation_ns,
                            ):
                                rollback_failed = True
                finally:
                    for handle in reversed(lock_handles):
                        handle.close()
                if registration_failed:
                    emit_block(
                        edit_registration_block_reason(
                            rollback_failed=rollback_failed
                        )
                    )
                break

    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
