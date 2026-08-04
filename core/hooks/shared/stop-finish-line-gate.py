#!/usr/bin/env python3
"""Stop hook: block finishing when code was edited but declared validation has
not run since.

Reads the repo's declared validation contracts (commands + marker) via
agent-docs. Identified hook sessions use directly addressable, opaque
session-scoped dirty, command, and recovery state, so an unrelated read-only
session is not charged for an edit or failure it did not create. Payloads
without a session identifier retain
the legacy shared-marker contract. Shared runtime tombstones keep an attempt
outstanding when its repo-local state becomes unwritable. A waiver requires one
discovered-defect routing review before release; a host suppress env releases
immediately.

This is the finish-line enforcement point (plan [D12]): mechanism-flexible but
never silently skippable. The same shared script is wired into the Stop event
for both Claude and Codex.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import sys
from collections.abc import Iterable
from typing import Any

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    TERMINAL_OWNER_MARKER_NAMES,
    acquire_validation_state_lock,
    command_failed_marker,
    command_ran_marker,
    emit_block,
    git_toplevel,
    read_payload,
    read_validation_waiver,
    routing_review_marker,
    session_marker_key,
    touch_marker,
    validation_command_target_key,
    validation_contracts,
    validation_marker_set,
    validation_tombstone_dir,
)

SUPPRESS_ENVS = (
    "AGENT_RUNTIME_SUPPRESS_FINISH_GATE",
    "AGENT_KIT_SUPPRESS_FINISH_GATE",
    "CLAUDE_KIT_SUPPRESS_FINISH_GATE",
)
WAIVER_ENVS = (
    "AGENT_RUNTIME_VALIDATION_WAIVER",
    "AGENT_KIT_VALIDATION_WAIVER",
    "CLAUDE_KIT_VALIDATION_WAIVER",
)
PENDING_SCHEMA = "agent-runtime-validation.pending.v1"
TOMBSTONE_SCHEMA = "agent-runtime-validation.tombstone.v1"
TOMBSTONE_MAX_BYTES = 64 * 1024
SESSION_PRODUCTS = ("codex", "claude", "shared")
SESSION_COMMAND_STATE_SUFFIX = re.compile(
    r"(?:cmd[0-9]+\.(?:ran|failed\.json)|pending\.[0-9a-f]+\.json|routing-reviewed)"
)


def env_enabled(names: Iterable[str]) -> bool:
    for name in names:
        value = os.environ.get(name, "")
        if value and value != "0":
            return True
    return False


def regular_file_mtime(path: str) -> float | None:
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    return metadata.st_mtime


def session_state_is_active(
    state_session_key: str | None, active_session_key: str
) -> bool:
    """Legacy state remains transitional authority for identified sessions."""
    if active_session_key:
        return state_session_key in {None, active_session_key}
    return state_session_key is None


def completed_state_snapshot(
    states: list[tuple[dict[str, str], bool]],
) -> tuple[tuple[Any, ...], ...] | None:
    """Capture the exact terminal generation that cleanup may retire."""
    directory = states[0][0]["dir"]
    snapshot: list[tuple[Any, ...]] = []
    try:
        try:
            directory_metadata = os.stat(directory, follow_symlinks=False)
        except FileNotFoundError:
            snapshot.append(("session-directory", "missing"))
            entries = []
        else:
            if not stat.S_ISDIR(directory_metadata.st_mode):
                return None
            snapshot.append(
                (
                    "session-directory",
                    "present",
                    directory_metadata.st_mode,
                    directory_metadata.st_dev,
                    directory_metadata.st_ino,
                )
            )
            entries = list(os.scandir(directory))
        for entry in entries:
            if entry.name == ".agent-runtime-validation.lock":
                continue
            metadata = entry.stat(follow_symlinks=False)
            snapshot.append(
                (
                    "session",
                    entry.name,
                    metadata.st_mode,
                    metadata.st_dev,
                    metadata.st_ino,
                    metadata.st_size,
                    metadata.st_mtime_ns,
                )
            )
        legacy_paths = {
            markers["legacy_dirty"]
            for markers, remove_legacy in states
            if remove_legacy
        }
        for path in sorted(legacy_paths):
            try:
                metadata = os.stat(path, follow_symlinks=False)
            except FileNotFoundError:
                snapshot.append(("legacy", path, "missing"))
                continue
            snapshot.append(
                (
                    "legacy",
                    path,
                    metadata.st_mode,
                    metadata.st_dev,
                    metadata.st_ino,
                    metadata.st_size,
                    metadata.st_mtime_ns,
                )
            )
    except OSError:
        return None
    return tuple(sorted(snapshot, key=repr))


def session_command_state_owners(
    entry_name: str, contract_stems: set[str]
) -> set[tuple[str, str]]:
    """Return complete contract/product identities for structured state."""
    owners: set[tuple[str, str]] = set()
    for stem in contract_stems:
        for product in SESSION_PRODUCTS:
            prefix = f"{stem}.{product}."
            if not entry_name.startswith(prefix):
                continue
            suffix = entry_name[len(prefix) :]
            if SESSION_COMMAND_STATE_SUFFIX.fullmatch(suffix):
                owners.add((stem, product))
    return owners


def cleanup_completed_session_state(
    states: list[tuple[dict[str, str], bool]],
    *,
    expected_snapshot: tuple[tuple[Any, ...], ...],
) -> bool:
    """Atomically retire all terminal owners in one session directory."""
    markers = states[0][0]
    if not markers.get("session_key"):
        return True
    directory = markers["dir"]
    lock_path = os.path.join(directory, ".agent-runtime-validation.lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    remove_directory = False
    try:
        created_directory = False
        try:
            os.mkdir(directory, 0o700)
            created_directory = True
        except FileExistsError:
            pass
        directory_metadata = os.stat(directory, follow_symlinks=False)
        if not stat.S_ISDIR(directory_metadata.st_mode):
            return False
        descriptor = os.open(lock_path, flags, 0o600)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return False
        fcntl.flock(descriptor, fcntl.LOCK_EX)

        current_snapshot = completed_state_snapshot(states)
        if current_snapshot is None:
            return False
        missing_directory = ("session-directory", "missing")
        if created_directory and missing_directory in expected_snapshot:
            current_directory = next(
                item
                for item in current_snapshot
                if item[0] == "session-directory"
            )
            expected_snapshot = tuple(
                sorted(
                    (
                        current_directory
                        if item == missing_directory
                        else item
                        for item in expected_snapshot
                    ),
                    key=repr,
                )
            )
        if current_snapshot != expected_snapshot:
            return False

        entries = list(os.scandir(directory))
        dirty_names = {os.path.basename(item[0]["dirty"]) for item in states}
        contract_stems = {item[0]["stem"] for item in states}
        products = {item[0]["product"] for item in states}

        foreign_products: set[str] = set()
        unknown_foreign = False
        for entry in entries:
            if (
                entry.name == ".agent-runtime-validation.lock"
                or entry.name in TERMINAL_OWNER_MARKER_NAMES
                or entry.name in dirty_names
            ):
                continue
            matched_owners = session_command_state_owners(
                entry.name, contract_stems
            )
            if len(matched_owners) != 1:
                unknown_foreign = True
                continue
            _, owner_product = next(iter(matched_owners))
            if owner_product not in products:
                foreign_products.add(owner_product)

        if unknown_foreign or foreign_products:
            for product in products:
                if not touch_marker(
                    os.path.join(directory, f".terminal-{product}")
                ):
                    return False
            dirty_generation = max(
                (
                    regular_file_mtime(item[0]["dirty"]) or 0.0
                    for item in states
                ),
                default=0.0,
            )
            if unknown_foreign or any(
                (
                    regular_file_mtime(
                        os.path.join(directory, f".terminal-{product}")
                    )
                    or 0.0
                )
                < dirty_generation
                for product in foreign_products
            ):
                return True

        for entry in os.scandir(directory):
            if entry.name == ".agent-runtime-validation.lock":
                continue
            entry_metadata = entry.stat(follow_symlinks=False)
            if not (
                stat.S_ISREG(entry_metadata.st_mode)
                or stat.S_ISLNK(entry_metadata.st_mode)
            ):
                return False
            os.unlink(entry.path)
        for legacy_path in {
            item[0]["legacy_dirty"] for item in states if item[1]
        }:
            if os.path.lexists(legacy_path):
                legacy_metadata = os.stat(legacy_path, follow_symlinks=False)
                if not (
                    stat.S_ISREG(legacy_metadata.st_mode)
                    or stat.S_ISLNK(legacy_metadata.st_mode)
                ):
                    return False
                os.unlink(legacy_path)
        remove_directory = True
    except OSError:
        return False
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if remove_directory:
        try:
            os.unlink(lock_path)
            os.rmdir(directory)
        except OSError:
            return False
    return True


def session_namespace_has_state(markers: dict[str, str]) -> bool:
    if os.path.lexists(markers["dirty"]):
        return True
    command_prefix = f"{markers['command_stem']}."
    try:
        return any(
            entry.name.startswith(command_prefix)
            for entry in os.scandir(markers["dir"])
        )
    except OSError:
        return False


def cleanup_failure_reason(repo_root: str) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    return (
        f"Code validation passed in {name}, but the completed session marker "
        "namespace could not be retired safely. Repair the validation marker "
        "directory permissions and retry Stop."
    )


def state_lock_failure_reason(repo_root: str) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    return (
        f"Code validation state for {name} could not be locked safely. Repair "
        "the shared runtime validation-state permissions and retry Stop."
    )


def external_tombstones(
    repo_root: str, active_session_key: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    directories = [validation_tombstone_dir(repo_root)]
    if active_session_key:
        directories.append(
            validation_tombstone_dir(repo_root, active_session_key)
        )
    entries: list[os.DirEntry[str]] = []
    invalid_directories: list[str] = []
    for directory in directories:
        try:
            entries.extend(os.scandir(directory))
        except FileNotFoundError:
            pass
        except OSError:
            invalid_directories.append(directory)
    if invalid_directories:
        return [], invalid_directories

    tombstones: list[dict[str, Any]] = []
    invalid: list[str] = []
    root = os.path.realpath(repo_root)
    for entry in entries:
        if not entry.name.startswith("attempt-") or not entry.name.endswith(".json"):
            continue
        descriptor = -1
        try:
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(entry.path, flags)
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size > TOMBSTONE_MAX_BYTES
            ):
                raise OSError("invalid validation tombstone")
            with os.fdopen(descriptor, encoding="utf-8") as handle:
                descriptor = -1
                body = json.load(handle)
        except (OSError, ValueError):
            invalid.append(entry.path)
            continue
        finally:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if not isinstance(body, dict) or body.get("schema_version") != TOMBSTONE_SCHEMA:
            invalid.append(entry.path)
            continue
        started = body.get("attempt_started_ns")
        dirty_started = body.get("dirty_started_ns")
        product = body.get("product")
        session_key = body.get("session_key")
        contract_key = body.get("contract_key")
        dirty = body.get("dirty")
        commands = body.get("commands")
        status = body.get("status")
        exit_code = body.get("exit_code")
        if (
            body.get("repo_root") != root
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
            or not isinstance(started, int)
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
            or not isinstance(commands, list)
            or not commands
            or status not in {"pending", "completed"}
            or (
                exit_code is not None
                and (
                    not isinstance(exit_code, int)
                    or isinstance(exit_code, bool)
                    or exit_code < 0
                    or exit_code > 255
                )
            )
        ):
            invalid.append(entry.path)
            continue
        normalized_commands: list[dict[str, str]] = []
        for command in commands:
            if not isinstance(command, dict):
                normalized_commands = []
                break
            ran = command.get("ran")
            failed = command.get("failed")
            target_key = command.get("target_key")
            if (
                not isinstance(ran, str)
                or not isinstance(failed, str)
                or not isinstance(target_key, str)
                or re.fullmatch(r"[0-9a-f]{64}", target_key) is None
            ):
                normalized_commands = []
                break
            normalized_commands.append(
                {"target_key": target_key, "ran": ran, "failed": failed}
            )
        if not normalized_commands:
            invalid.append(entry.path)
            continue
        tombstones.append(
            {
                "attempt_started_ns": started,
                "dirty_started_ns": dirty_started,
                "product": product,
                "session_key": session_key,
                "contract_key": contract_key,
                "dirty": dirty,
                "commands": normalized_commands,
                "status": status,
                "exit_code": exit_code,
            }
        )
    return tombstones, invalid


def reason(
    repo_root: str,
    contracts: list[dict[str, Any]],
    outstanding: list[tuple[str, str, bool, int | None]],
) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    full = " && ".join(
        command
        for contract in contracts
        for command in contract.get("commands", [])
        if isinstance(command, str)
    )
    missing = " && ".join(
        f"[{context}] {command}"
        + (
            f" (failed with exit code {exit_code})"
            if failed and exit_code is not None
            else " (failed; exit code unavailable)"
            if failed
            else ""
        )
        for context, command, failed, exit_code in outstanding
    )
    markers = ", ".join(
        str(contract.get("marker", "")).strip()
        for contract in contracts
        if str(contract.get("marker", "")).strip()
    )
    failure_guidance = ""
    if any(failed for _, _, failed, _ in outstanding):
        failure_guidance = (
            "\nDiscovered-defect routing:\n"
            "- Project-owned product, test, or CI defect: classify it as "
            "L1 issue-follow-up in the owning repository.\n"
            "- Agent workflow, skill, hook, CLI, or primitive defect: route it "
            "through heuristic-inbox in agent-runtime-kit.\n"
            "- Fixed in this turn or transient with no reusable lesson: create no "
            "retained artifact. If both owners apply, make the project issue primary "
            "and retain a heuristic case only for a reusable cross-project gap.\n"
            "Do not create a provider issue automatically; L1+ provider mutation "
            "still requires the user's decision."
        )
    return (
        f"Code was edited in {name} but its declared validation has "
        "not passed since the last edit.\n"
        f"Declared validation contract:\n  {full}\n"
        f"Outstanding for this edit generation: {missing}\n"
        "A successful creditable invocation records command outcomes in "
        "validation state (session-scoped when the hook receives a session "
        "identity). After all current outcomes are satisfied, Stop consolidates "
        f"the contract into {markers}, removes completed session state when "
        "present, and releases this gate.\n"
        "Run the outstanding declared command shape before finishing. Submit it "
        "as its own tool call with no preceding shell state, or use an absolute "
        "interpreter when the environment requires one; an `export`, `source`, "
        "or other setup command in the same shell payload can make executable "
        "resolution fail closed.\n"
        "If the shell itself is blocked, the recovery lane is out-of-band and "
        "does not need it: `scripts/validation-recovery.py run --repo <path>` "
        "executes only the declared command shape, and "
        "`scripts/validation-recovery.py waive --repo <path> --reason <text>` "
        "records a structured waiver bound to this edit generation. Setting "
        "AGENT_RUNTIME_VALIDATION_WAIVER=1 with a stated reason remains "
        f"supported.{failure_guidance}"
    )


def failed_outcome(
    path: str, *, dirty_mtime: float, ran_mtime: float | None
) -> tuple[bool, int | None, float]:
    failed_mtime = regular_file_mtime(path)
    if failed_mtime is None:
        return False, None, 0.0
    if failed_mtime < dirty_mtime:
        return False, None, failed_mtime
    if ran_mtime is not None and ran_mtime > failed_mtime:
        return False, None, failed_mtime
    exit_code: int | None = None
    try:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
        raw_code = body.get("exit_code") if isinstance(body, dict) else None
        if isinstance(raw_code, int) and not isinstance(raw_code, bool):
            exit_code = raw_code
    except (OSError, ValueError):
        pass
    return True, exit_code, failed_mtime


def pending_attempt_mtimes(markers: dict[str, str]) -> dict[str, float]:
    stem = markers.get("command_stem") or markers["stem"]
    prefix = f"{stem}.pending."
    latest: dict[str, float] = {}
    try:
        entries = list(os.scandir(markers["dir"]))
    except OSError:
        return latest
    for entry in entries:
        if (
            not entry.name.startswith(prefix)
            or not entry.name.endswith(".json")
            or not entry.is_file(follow_symlinks=False)
        ):
            continue
        try:
            with open(entry.path, encoding="utf-8") as handle:
                body = json.load(handle)
            if not isinstance(body, dict) or body.get("schema_version") != PENDING_SCHEMA:
                continue
            raw_started = body.get("attempt_started_ns")
            started = (
                raw_started / 1_000_000_000
                if isinstance(raw_started, int) and not isinstance(raw_started, bool)
                else entry.stat(follow_symlinks=False).st_mtime
            )
            commands = body.get("commands")
            if not isinstance(commands, list):
                continue
            for command in commands:
                if not isinstance(command, dict):
                    continue
                ran = command.get("ran")
                if isinstance(ran, str):
                    latest[ran] = max(latest.get(ran, 0.0), started)
        except (OSError, ValueError):
            continue
    return latest


def routing_review_reason(repo_root: str, *, persistence_failed: bool = False) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    persistence = (
        " The routing-review marker could not persist, so the waiver remains blocked."
        if persistence_failed
        else ""
    )
    return (
        f"Validation is being waived in {name}; discovered-defect routing review required "
        "before finishing. Classify the unresolved signal and state the evidence, owner, "
        "and route in the next user-facing response:\n"
        "- Project-owned product/test/CI defect -> propose L1 issue-follow-up in the "
        "owning repository and wait for user approval before provider mutation.\n"
        "- Agent workflow/skill/hook/CLI/primitive defect -> heuristic-inbox in "
        "agent-runtime-kit.\n"
        "- Fixed this turn or transient/no reusable lesson -> no retained artifact.\n"
        "If both apply, the project issue is primary; add a heuristic case only for a "
        "reusable cross-project gap. Do not create any provider issue automatically. "
        "This is a one-shot routing prompt; the next Stop honors the waiver only after "
        f"the review marker persists.{persistence}"
    )


def unsafe_marker_reason(
    repo_root: str,
    invalid: list[tuple[str, str]],
) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    details = ", ".join(f"[{context}] {marker}" for context, marker in invalid)
    return (
        f"Code validation in {name} has an unsafe validation marker: {details}. "
        "Each AGENT_DOCS.toml validation marker must be repository-relative and "
        "remain beneath the real repository root through symlink resolution. "
        "No validation evidence was written; fix the contract before finishing."
    )


def unsafe_state_reason(repo_root: str, invalid: list[tuple[str, str]]) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    details = ", ".join(f"[{context}] {path}" for context, path in invalid)
    return (
        f"Code validation in {name} has an unsafe validation state marker: "
        f"{details}. Dirty state must be a non-symlink regular file; no marker "
        "of another type can satisfy or suppress the finish-line gate."
    )


def unsafe_tombstone_reason(repo_root: str, invalid: list[str]) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    return (
        f"Code validation in {name} has unreadable authoritative attempt state: "
        f"{', '.join(invalid)}. Repair or remove the invalid runtime tombstone only "
        "after reviewing the unresolved validation attempt."
    )


def unmatched_tombstone_reason(
    repo_root: str, tombstones: list[dict[str, Any]]
) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    keys = ", ".join(
        sorted({str(item["contract_key"])[:12] for item in tombstones})
    )
    return (
        f"Code validation in {name} has unmatched authoritative attempt state "
        f"for contract key(s) {keys}. The validation contract changed while an "
        "attempt was unresolved; review that attempt before removing its runtime "
        "tombstone."
    )


def unmatched_target_reason(
    repo_root: str,
    unmatched: list[tuple[str, str, set[str]]],
) -> str:
    name = os.path.basename(os.path.abspath(repo_root))
    details = ", ".join(
        f"[{context}] {contract_key[:12]}:"
        + "/".join(sorted(target[:12] for target in targets))
        for context, contract_key, targets in unmatched
    )
    return (
        f"Code validation in {name} has authoritative validation target(s) no "
        f"longer declared by the current contract: {details}. The validation "
        "contract changed while those targets were unresolved; review the old "
        "attempt before removing its runtime tombstone. Re-running a different "
        "current command cannot clear this state."
    )


def main() -> int:
    payload = read_payload()
    active_session_key = session_marker_key(payload)
    if env_enabled(SUPPRESS_ENVS):
        return ALLOW

    repo_root = git_toplevel()
    if not repo_root:
        return ALLOW
    contracts = validation_contracts(repo_root)
    try:
        state_lock = acquire_validation_state_lock(repo_root)
    except OSError:
        emit_block(state_lock_failure_reason(repo_root))
        return ALLOW
    tombstones, invalid_tombstones = external_tombstones(
        repo_root, active_session_key
    )
    raw_product = os.environ.get("AGENT_RUNTIME_PRODUCT", "").strip()
    active_product = (
        raw_product if raw_product in {"codex", "claude"} else "shared"
    )
    active_tombstones = [
        tombstone
        for tombstone in tombstones
        if tombstone["product"] == active_product
        and session_state_is_active(
            tombstone["session_key"], active_session_key
        )
    ]
    if not contracts:
        if invalid_tombstones:
            emit_block(unsafe_tombstone_reason(repo_root, invalid_tombstones))
        elif active_tombstones:
            emit_block(unmatched_tombstone_reason(repo_root, active_tombstones))
        return ALLOW
    tombstones_by_contract: dict[str, list[dict[str, Any]]] = {}
    for tombstone in tombstones:
        if not session_state_is_active(
            tombstone["session_key"], active_session_key
        ):
            continue
        tombstones_by_contract.setdefault(
            tombstone["contract_key"], []
        ).append(tombstone)

    outstanding: list[tuple[str, str, bool, int | None]] = []
    satisfied_markers: list[dict[str, str]] = []
    terminal_markers: list[tuple[dict[str, str], bool]] = []
    routing_signals: list[tuple[dict[str, str], float]] = []
    invalid_markers: list[tuple[str, str]] = []
    invalid_state_markers: list[tuple[str, str]] = []
    unmatched_targets: list[tuple[str, str, set[str]]] = []
    matched_contract_keys: set[str] = set()
    for contract in contracts:
        try:
            markers = validation_marker_set(
                repo_root, contract["marker"], session_key=active_session_key
            )
        except ValueError:
            invalid_markers.append(
                (
                    str(contract.get("context") or "validation"),
                    str(contract.get("marker") or ""),
                )
            )
            continue
        matched_contract_keys.add(markers["contract_key"])
        context = str(contract.get("context") or "validation")
        dirty = markers["dirty"]
        ok_mtime = regular_file_mtime(markers["ok"])
        contract_tombstones = tombstones_by_contract.get(
            markers["contract_key"], []
        )
        if active_session_key and ok_mtime is not None:
            contract_tombstones = [
                tombstone
                for tombstone in contract_tombstones
                if tombstone["session_key"] is not None
                or ok_mtime
                < int(tombstone["attempt_started_ns"]) / 1_000_000_000
            ]
        active_contract_tombstones = [
            tombstone
            for tombstone in contract_tombstones
            if tombstone["product"] == active_product
        ]
        foreign_contract_tombstones = [
            tombstone
            for tombstone in contract_tombstones
            if tombstone["product"] != active_product
        ]
        current_targets = {
            validation_command_target_key(markers, index, declared): (
                index,
                declared,
            )
            for index, declared in enumerate(contract["commands"])
        }
        tombstone_targets = {
            command["target_key"]
            for tombstone in active_contract_tombstones
            for command in tombstone["commands"]
        }
        removed_targets = tombstone_targets.difference(current_targets)
        if removed_targets:
            unmatched_targets.append(
                (context, markers["contract_key"], removed_targets)
            )
            continue

        latest_by_target: dict[str, dict[str, Any]] = {}
        for tombstone in active_contract_tombstones:
            for command in tombstone["commands"]:
                target_key = command["target_key"]
                current = latest_by_target.get(target_key)
                if current is None or int(tombstone["attempt_started_ns"]) > int(
                    current["attempt_started_ns"]
                ):
                    latest_by_target[target_key] = tombstone

        contract_outstanding: list[tuple[str, bool, int | None]] = []
        latest_signal = 0.0
        covered_indices: set[int] = set()
        for target_key, latest in latest_by_target.items():
            index, declared = current_targets[target_key]
            covered_indices.add(index)
            raw_exit = latest.get("exit_code")
            exit_code = raw_exit if isinstance(raw_exit, int) else None
            failed = latest.get("status") == "completed" and exit_code not in {
                None,
                0,
            }
            contract_outstanding.append(
                (declared, failed, exit_code if failed else None)
            )
            latest_signal = max(
                latest_signal,
                int(latest["attempt_started_ns"]) / 1_000_000_000,
            )

        dirty_exists = os.path.lexists(dirty)
        dirty_mtime = regular_file_mtime(dirty) if dirty_exists else None
        if dirty_exists and dirty_mtime is None:
            invalid_state_markers.append(
                (context, dirty)
            )
            continue

        legacy_dirty_mtime = 0.0
        cleanup_legacy_dirty = False
        if active_session_key:
            legacy_dirty = markers["legacy_dirty"]
            legacy_dirty_exists = os.path.lexists(legacy_dirty)
            raw_legacy_dirty_mtime = (
                regular_file_mtime(legacy_dirty) if legacy_dirty_exists else None
            )
            if legacy_dirty_exists and raw_legacy_dirty_mtime is None:
                invalid_state_markers.append((context, legacy_dirty))
                continue
            if raw_legacy_dirty_mtime is not None:
                cleanup_legacy_dirty = True
                if ok_mtime is None or ok_mtime < raw_legacy_dirty_mtime:
                    legacy_dirty_mtime = raw_legacy_dirty_mtime

        validation_signal = max(
            dirty_mtime or 0.0,
            legacy_dirty_mtime,
            max(
                (
                    int(tombstone["dirty_started_ns"]) / 1_000_000_000
                    for tombstone in foreign_contract_tombstones
                    if isinstance(tombstone["dirty_started_ns"], int)
                ),
                default=0.0,
            ),
        )
        latest_signal = max(latest_signal, validation_signal)
        if validation_signal:
            pending_mtimes = pending_attempt_mtimes(markers)
            for index, declared in enumerate(contract["commands"]):
                if index in covered_indices:
                    continue
                ran = command_ran_marker(markers, index)
                ran_mtime = regular_file_mtime(ran)
                failed, exit_code, failed_mtime = failed_outcome(
                    command_failed_marker(markers, index),
                    dirty_mtime=validation_signal,
                    ran_mtime=ran_mtime,
                )
                pending_mtime = pending_mtimes.get(ran, 0.0)
                latest_signal = max(latest_signal, failed_mtime, pending_mtime)
                pending = (
                    pending_mtime >= validation_signal
                    and (ran_mtime is None or pending_mtime > ran_mtime)
                    and (not failed or pending_mtime > failed_mtime)
                )
                if pending:
                    contract_outstanding.append((declared, False, None))
                elif failed:
                    contract_outstanding.append((declared, True, exit_code))
                elif ran_mtime is None or ran_mtime < validation_signal:
                    contract_outstanding.append((declared, False, None))
        if contract_outstanding:
            outstanding.extend(
                (context, command, failed, exit_code)
                for command, failed, exit_code in contract_outstanding
            )
            routing_signals.append((markers, latest_signal))
        elif validation_signal:
            satisfied_markers.append(markers)
        if cleanup_legacy_dirty or session_namespace_has_state(markers):
            terminal_markers.append((markers, cleanup_legacy_dirty))

    if invalid_tombstones:
        emit_block(unsafe_tombstone_reason(repo_root, invalid_tombstones))
        return ALLOW
    if invalid_markers:
        emit_block(unsafe_marker_reason(repo_root, invalid_markers))
        return ALLOW
    unmatched_tombstones = [
        tombstone
        for tombstone in active_tombstones
        if tombstone["contract_key"] not in matched_contract_keys
    ]
    if unmatched_tombstones:
        emit_block(unmatched_tombstone_reason(repo_root, unmatched_tombstones))
        return ALLOW
    if unmatched_targets:
        emit_block(unmatched_target_reason(repo_root, unmatched_targets))
        return ALLOW
    if invalid_state_markers:
        emit_block(unsafe_state_reason(repo_root, invalid_state_markers))
        return ALLOW

    if not outstanding:
        for markers in satisfied_markers:
            touch_marker(markers["ok"])
        grouped_terminal_markers: dict[
            str, list[tuple[dict[str, str], bool]]
        ] = {}
        for markers, remove_legacy_dirty in terminal_markers:
            grouped_terminal_markers.setdefault(markers["dir"], []).append(
                (markers, remove_legacy_dirty)
            )
        cleanup_failed = False
        for states in grouped_terminal_markers.values():
            snapshot = completed_state_snapshot(states)
            if snapshot is None or not cleanup_completed_session_state(
                states, expected_snapshot=snapshot
            ):
                cleanup_failed = True
        if cleanup_failed:
            emit_block(cleanup_failure_reason(repo_root))
        return ALLOW

    # A structured waiver is authorized out-of-band by a controller, so it stays
    # reachable from a session whose `PreToolUse` is failing closed — the exact
    # deadlock in `sympoies/nils-cli#1409`, where the documented environment-
    # variable route required the shell execution the hook was blocking. It is
    # also strictly narrower: each record binds to one contract and its current
    # edit generation, so it cannot leak into a later turn.
    waived_structurally = bool(routing_signals) and all(
        read_validation_waiver(markers, repo_root) is not None
        for markers, _signal in routing_signals
    )
    if waived_structurally or env_enabled(WAIVER_ENVS):
        needs_review = False
        persistence_failed = False
        for markers, signal_mtime in routing_signals:
            reviewed = routing_review_marker(markers)
            reviewed_mtime = regular_file_mtime(reviewed)
            if reviewed_mtime is not None and reviewed_mtime >= signal_mtime:
                continue
            needs_review = True
            if not touch_marker(reviewed):
                persistence_failed = True
        if needs_review:
            emit_block(
                routing_review_reason(
                    repo_root, persistence_failed=persistence_failed
                )
            )
        return ALLOW

    emit_block(reason(repo_root, contracts, outstanding))
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
