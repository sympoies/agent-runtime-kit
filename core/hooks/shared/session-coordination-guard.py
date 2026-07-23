#!/usr/bin/env python3
"""Advise managed sessions about overlap, with opt-in strict enforcement.

The hook is intentionally bounded and privacy-minimizing. Managed launches that
publish the exact session/capability/state environment receive non-blocking
advice by default. Only ``AGENT_SESSION_COORDINATION_MODE=enforce`` enables the
legacy fail-closed claim and operation admission path. ``off`` and unmanaged
launches stay silent. Public hook output contains only fixed reason codes and
recovery shapes; raw paths, session identities, capabilities, peer summaries,
and CLI error messages never leave this process.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    SHELL_EFFECT_MUTATION,
    SHELL_EFFECT_READ_ONLY,
    SHELL_EFFECT_UNKNOWN,
    apply_patch_paths,
    audited_text_read_invocation,
    classify_shell_effect,
    command_from,
    effective_workdir,
    emit_block,
    invocation_is_opaque,
    invocation_tokens,
    output_redirect_targets,
    patch_text_candidates,
    read_payload,
    simple_commands_with_nested_shells,
    tool_input_dict,
)

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"}
COMMAND_TOOLS = {"Bash"}
SUPPORTED_PRODUCTS = {"codex", "claude"}
COORDINATION_FLOOR = (1, 24, 5)
TIMEOUT_SECONDS = 6.0
HOOK_BUDGET_SECONDS = 50.0
HOOK_DEADLINE: float | None = None
MAX_PENDING_RECORDS = 32
SHELL_CONTROL = frozenset(";&|<>`$(){}#*?[]^~\n\r")
READ_ONLY_GIT = frozenset(
    {
        "rev-parse",
        "rev-list",
        "ls-files",
        "ls-tree",
        "describe",
        "show-ref",
        "for-each-ref",
        "merge-base",
    }
)
READ_ONLY_PROVIDER = frozenset({"view", "list", "status", "checks", "diff"})
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
MUTATING_GIT = frozenset(
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
        "pack-refs",
        "pull",
        "prune",
        "rebase",
        "replace",
        "reset",
        "restore",
        "revert",
        "rm",
        "submodule",
        "switch",
        "update-index",
        "update-ref",
    }
)
PROVIDER_MUTATION_ACTIONS = frozenset(
    {
        "add",
        "archive",
        "cancel",
        "checkout",
        "close",
        "comment",
        "create",
        "delete",
        "deliver",
        "disable",
        "edit",
        "enable",
        "ensure",
        "fork",
        "lock",
        "merge",
        "pin",
        "push-default",
        "ready",
        "rename",
        "reopen",
        "rerun",
        "review",
        "run",
        "sync",
        "transfer",
        "unarchive",
        "unlock",
        "unpin",
        "update",
        "upload",
        "delete-asset",
    }
)
GIT_GLOBAL_VALUE_OPTIONS = frozenset(
    {"-C", "--git-dir", "--work-tree", "--namespace"}
)
GIT_GLOBAL_FLAG_OPTIONS = frozenset(
    {
        "-P",
        "--no-pager",
        "--bare",
        "--no-replace-objects",
        "--literal-pathspecs",
        "--no-literal-pathspecs",
        "--no-optional-locks",
    }
)
SHELL_EXECUTABLES = frozenset({"bash", "dash", "ksh", "sh", "zsh"})
GIT_WRITE_OR_EXEC_FLAGS = frozenset(
    {"-o", "--output", "-O", "--open-files-in-pager"}
)
PROVIDER_VALUE_OPTIONS = frozenset(
    {
        "--format",
        "--remote",
        "--provider",
        "--host",
        "--repo",
        "-R",
        "--store-root",
    }
)
CLAIM_ERROR_CODES = frozenset(
    {
        "claim-not-found",
        "claim-unavailable",
        "claim-expired",
        "session-incarnation-mismatch",
        "capability-invalid",
        "authentication-failed",
    }
)
ADVISORY_CLASSIFICATIONS = frozenset(
    {"potential_conflict", "unknown", "no_known_conflict"}
)
COORDINATION_MODES = frozenset({"advisory", "enforce", "off"})


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
    return "PreToolUse"


def tool_use_id(payload: Mapping[str, Any]) -> str:
    for key in ("tool_use_id", "toolUseId", "call_id", "callId"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def emit_system(message: str) -> None:
    sys.stdout.write(json.dumps({"systemMessage": message}))
    sys.stdout.write("\n")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)\.(\d+)(?:\s|$|\()", text)
    if not match:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    timeout = TIMEOUT_SECONDS
    if HOOK_DEADLINE is not None:
        timeout = min(timeout, HOOK_DEADLINE - time.monotonic())
        if timeout <= 0:
            return None
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=timeout,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def bounded_git_toplevel(cwd: str) -> str | None:
    completed = run_cli(["git", "-C", cwd, "rev-parse", "--show-toplevel"])
    if completed is None or completed.returncode != 0:
        return None
    top = completed.stdout.strip()
    return top or None


def resolved_trusted_cli(name: str) -> str | None:
    candidate = shutil.which(name)
    if not candidate or not os.path.isabs(candidate):
        return None
    lexical = os.path.abspath(candidate)
    resolved = os.path.realpath(candidate)
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return None
    configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "").strip()
    if configured:
        roots = {
            os.path.realpath(item)
            for item in configured.split(os.pathsep)
            if item.strip()
        }
        if os.path.realpath(os.path.dirname(lexical)) in roots:
            return resolved
        return None
    for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
        if os.path.dirname(lexical) == os.path.join(prefix, "bin"):
            cellar = os.path.join(prefix, "Cellar", "nils-cli")
            if resolved == lexical or os.path.commonpath((resolved, cellar)) == cellar:
                return resolved
    if os.path.dirname(lexical) == "/usr/bin" and resolved == lexical:
        return resolved
    return None


def resolved_agent_session() -> str | None:
    return resolved_trusted_cli("agent-session")


def coordination_mode() -> str:
    raw = os.environ.get("AGENT_SESSION_COORDINATION_MODE", "").strip().lower()
    return raw if raw in COORDINATION_MODES else "advisory"


def coordination_capability(executable: str, mode: str = "enforce") -> bool:
    version = run_cli([executable, "--version"])
    if version is None or version.returncode != 0:
        return False
    parsed = parse_version(version.stdout + "\n" + version.stderr)
    if parsed is None or parsed < COORDINATION_FLOOR:
        return False
    help_result = run_cli([executable, "work-context", "--help"])
    if help_result is None or help_result.returncode != 0:
        return False
    required = (
        ("show", "check", "admit", "complete", "reconcile")
        if mode == "enforce"
        else ("advise",)
    )
    return all(command in help_result.stdout for command in required)


def simple_words(command: str) -> list[str] | None:
    quote = ""
    escaped = False
    for character in command:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = ""
            elif quote == '"' and character in "`$":
                return None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character in SHELL_CONTROL:
            return None
    if quote or escaped:
        return None
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return None
    return words or None


def literal_claim_bootstrap_words(command: str) -> list[str] | None:
    """Expand only the two exact quoted variables in the claim recovery shape."""
    current_session = os.environ.get("AGENT_SESSION_ID", "").strip()
    capability_file = os.environ.get("AGENT_SESSION_CAPABILITY_FILE", "").strip()
    if not current_session or not capability_file:
        return None
    replacements = (
        ('"$AGENT_SESSION_ID"', "__AGENT_SESSION_LITERAL_ID_7F3A__", current_session),
        (
            '"$AGENT_SESSION_CAPABILITY_FILE"',
            "__AGENT_SESSION_LITERAL_CAPABILITY_7F3A__",
            capability_file,
        ),
    )
    sanitized = command
    for literal, sentinel, _value in replacements:
        if sanitized.count(literal) != 1 or sentinel in sanitized:
            return None
        sanitized = sanitized.replace(literal, sentinel)
    words = simple_words(sanitized)
    if not words or words[:3] != ["agent-session", "work-context", "claim"]:
        return None
    values = {sentinel: value for _literal, sentinel, value in replacements}
    return [values.get(word, word) for word in words]


def lifecycle_identifier(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value) is not None


def lifecycle_revision(value: str) -> bool:
    if re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is None:
        return False
    return int(value) <= (2**64 - 1)


def lifecycle_idempotency_key(value: str) -> bool:
    return 8 <= len(value) <= 128 and all(
        character.isascii() and character.isprintable() for character in value
    )


def lifecycle_duration(value: str, maximum_seconds: int) -> bool:
    match = re.fullmatch(r"(0|[1-9][0-9]*)([smhd]?)", value)
    if match is None:
        return False
    multiplier = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[
        match.group(2)
    ]
    seconds = int(match.group(1)) * multiplier
    return 0 < seconds <= maximum_seconds


def lifecycle_private_file(
    raw: str, repository: str | None, *, json_file: bool = False
) -> bool:
    if (
        not os.path.isabs(raw)
        or os.path.normpath(raw) != raw
        or os.path.islink(raw)
        or not os.path.isfile(raw)
        or (json_file and not raw.endswith(".json"))
    ):
        return False
    if repository:
        try:
            if os.path.commonpath(
                (os.path.realpath(raw), os.path.realpath(repository))
            ) == os.path.realpath(repository):
                return False
        except ValueError:
            return False
    return True


def projected_lifecycle_invocation(
    words: list[str],
    *,
    session_sentinel: str,
    capability_sentinel: str,
    repository: str | None,
) -> bool:
    """Validate one finite authenticated lifecycle or mailbox command."""
    if words[:1] != ["agent-session"] or words[-2:] != ["--format", "json"]:
        return False

    capability = os.environ.get("AGENT_SESSION_CAPABILITY_FILE", "").strip()
    if not capability or not lifecycle_private_file(capability, repository):
        return False

    if words in (
        [
            "agent-session",
            "work-context",
            "check",
            "--self",
            "--capability-file",
            capability_sentinel,
            "--format",
            "json",
        ],
        [
            "agent-session",
            "work-context",
            "show",
            "--session",
            session_sentinel,
            "--capability-file",
            capability_sentinel,
            "--format",
            "json",
        ],
        [
            "agent-session",
            "broker",
            "status",
            "--session",
            session_sentinel,
            "--capability-file",
            capability_sentinel,
            "--format",
            "json",
        ],
    ):
        return True

    if words[1:3] == ["work-context", "renew"] or words[1:3] == [
        "work-context",
        "release",
    ]:
        return (
            len(words) == 15
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--claim"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9:11] == ["--capability-file", capability_sentinel]
            and words[11] == "--idempotency-key"
            and lifecycle_idempotency_key(words[12])
        )

    if words[1:3] == ["work-context", "admit"]:
        return (
            len(words) == 21
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--claim"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9] == "--targets-file"
            and lifecycle_private_file(words[10], repository, json_file=True)
            and words[11] == "--operation"
            and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", words[12]) is not None
            and words[13] == "--execution-token-file"
            and lifecycle_private_file(words[14], repository)
            and words[15:17] == ["--capability-file", capability_sentinel]
            and words[17] == "--idempotency-key"
            and lifecycle_idempotency_key(words[18])
        )

    if words[1:3] == ["work-context", "complete"]:
        return (
            len(words) == 19
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--lease"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9] == "--execution-token-file"
            and lifecycle_private_file(words[10], repository)
            and words[11] == "--outcome"
            and words[12] in {"pass", "fail"}
            and words[13:15] == ["--capability-file", capability_sentinel]
            and words[15] == "--idempotency-key"
            and lifecycle_idempotency_key(words[16])
        )

    if words[1:3] == ["work-context", "reconcile"]:
        return (
            len(words) == 17
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--lease"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9] == "--proof-file"
            and lifecycle_private_file(words[10], repository, json_file=True)
            and words[11:13] == ["--capability-file", capability_sentinel]
            and words[13] == "--idempotency-key"
            and lifecycle_idempotency_key(words[14])
        )

    if words[1:3] == ["message", "send"]:
        if (
            len(words) < 15
            or words[3:5] != ["--from", session_sentinel]
            or words[5] != "--to"
            or not lifecycle_identifier(words[6])
            or words[7] != "--body-file"
            or not lifecycle_private_file(words[8], repository)
            or words[9:11] != ["--capability-file", capability_sentinel]
            or words[11] != "--idempotency-key"
            or not lifecycle_idempotency_key(words[12])
        ):
            return False
        tail = words[13:-2]
        if tail[:1] == ["--reply-to"]:
            if len(tail) < 2 or not lifecycle_identifier(tail[1]):
                return False
            tail = tail[2:]
        if tail[:1] == ["--expires-in"]:
            if len(tail) < 2 or not lifecycle_duration(tail[1], 7 * 86400):
                return False
            tail = tail[2:]
        return not tail

    if words[1:3] == ["message", "inbox"]:
        if (
            len(words) < 9
            or words[3:5] != ["--session", session_sentinel]
            or words[5:7] != ["--capability-file", capability_sentinel]
        ):
            return False
        tail = words[7:-2]
        if tail[:1] == ["--state"]:
            if len(tail) < 2 or tail[1] not in {
                "unread",
                "read",
                "acknowledged",
                "expired",
            }:
                return False
            tail = tail[2:]
        if tail[:1] == ["--cursor"]:
            if len(tail) < 2 or not lifecycle_identifier(tail[1]):
                return False
            tail = tail[2:]
        if tail[:1] == ["--limit"]:
            if (
                len(tail) < 2
                or re.fullmatch(r"[1-9][0-9]{0,2}", tail[1]) is None
                or int(tail[1]) > 100
            ):
                return False
            tail = tail[2:]
        return not tail

    if words[1:3] == ["message", "show"]:
        return (
            len(words) == 11
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--message"
            and lifecycle_identifier(words[6])
            and words[7:9] == ["--capability-file", capability_sentinel]
        )

    if words[1:3] == ["message", "ack"]:
        return (
            len(words) == 15
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--message"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9:11] == ["--capability-file", capability_sentinel]
            and words[11] == "--idempotency-key"
            and lifecycle_idempotency_key(words[12])
        )

    if words[1:3] == ["message", "reply"]:
        return (
            len(words) == 17
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--message"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9] == "--body-file"
            and lifecycle_private_file(words[10], repository)
            and words[11:13] == ["--capability-file", capability_sentinel]
            and words[13] == "--idempotency-key"
            and lifecycle_idempotency_key(words[14])
        )

    if words[1:3] == ["message", "wait"]:
        return (
            len(words) == 15
            and words[3:5] == ["--session", session_sentinel]
            and words[5] == "--message"
            and lifecycle_identifier(words[6])
            and words[7] == "--if-revision"
            and lifecycle_revision(words[8])
            and words[9] == "--timeout"
            and lifecycle_duration(words[10], 60)
            and words[11:13] == ["--capability-file", capability_sentinel]
        )
    return False


def literal_projected_lifecycle_words(
    command: str, base: Path | None
) -> list[str] | None:
    """Expand only target-owned variables in finite authenticated CLI shapes."""
    current_session = os.environ.get("AGENT_SESSION_ID", "").strip()
    capability_file = os.environ.get("AGENT_SESSION_CAPABILITY_FILE", "").strip()
    if not current_session or not capability_file:
        return None
    session_sentinel = "__AGENT_SESSION_LITERAL_ID_1C4E__"
    capability_sentinel = "__AGENT_SESSION_LITERAL_CAPABILITY_1C4E__"
    if session_sentinel in command or capability_sentinel in command:
        return None
    if command.count('"$AGENT_SESSION_ID"') > 1 or command.count(
        '"$AGENT_SESSION_CAPABILITY_FILE"'
    ) != 1:
        return None
    sanitized = command.replace('"$AGENT_SESSION_ID"', session_sentinel).replace(
        '"$AGENT_SESSION_CAPABILITY_FILE"', capability_sentinel
    )
    words = simple_words(sanitized)
    if not words:
        return None
    repository = bounded_git_toplevel(str(base)) if base is not None else None
    if not projected_lifecycle_invocation(
        words,
        session_sentinel=session_sentinel,
        capability_sentinel=capability_sentinel,
        repository=repository,
    ):
        return None
    values = {
        session_sentinel: current_session,
        capability_sentinel: capability_file,
    }
    return [values.get(word, word) for word in words]


def unwrap_nested_shell(words: list[str]) -> tuple[list[str] | None, bool]:
    current = words
    wrapped = False
    for _ in range(8):
        invocation = invocation_tokens(current, shell_boundary=False)
        if not invocation or invocation_is_opaque(invocation):
            return None, True
        if invocation != current:
            current = invocation
            wrapped = True
            continue
        if not current or os.path.basename(current[0]) not in SHELL_EXECUTABLES:
            return current, wrapped
        script_index: int | None = None
        index = 1
        while index < len(current):
            token = current[index]
            if token == "--":
                break
            if token in {"-O", "+O", "-o", "+o", "--rcfile", "--init-file"}:
                if index + 1 >= len(current):
                    return None, True
                index += 2
                continue
            if token.startswith(("--rcfile=", "--init-file=")):
                index += 1
                continue
            if token == "-c" or (
                token.startswith("-")
                and not token.startswith("--")
                and "c" in token[1:]
            ):
                script_index = index + 1
                break
            if not token.startswith("-"):
                break
            index += 1
        if script_index is None:
            return current, wrapped
        if script_index >= len(current):
            return None, True
        current = simple_words(current[script_index])
        wrapped = True
        if current is None:
            return None, wrapped
    return None, True


def trusted_command(token: str, expected: str) -> bool:
    if os.path.basename(token) != expected:
        return False
    if "/" in token and not os.path.isabs(token):
        return False
    candidate = token if os.path.isabs(token) else shutil.which(token)
    if not candidate:
        return False
    lexical = os.path.abspath(candidate)
    resolved = os.path.realpath(candidate)
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return False
    allowed_roots = {"/usr/bin", "/bin", "/usr/local/bin"}
    configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "").strip()
    allowed_roots.update(
        os.path.realpath(item)
        for item in configured.split(os.pathsep)
        if item.strip()
    )
    lexical_dir = os.path.realpath(os.path.dirname(lexical))
    if lexical_dir in allowed_roots:
        return True
    for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew"):
        if os.path.dirname(lexical) == os.path.join(prefix, "bin"):
            return True
    return False


def git_read_only(args: list[str]) -> bool:
    index = 0
    while index < len(args):
        token = args[index]
        if token in GIT_GLOBAL_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in GIT_GLOBAL_VALUE_OPTIONS):
            index += 1
            continue
        if token in GIT_GLOBAL_FLAG_OPTIONS:
            index += 1
            continue
        if token.startswith("-"):
            return False
        break
    if index >= len(args) or args[index] not in READ_ONLY_GIT:
        return False
    for token in args[index + 1 :]:
        if token == "--":
            break
        if token in GIT_WRITE_OR_EXEC_FLAGS:
            return False
        if any(token.startswith(f"{flag}=") for flag in GIT_WRITE_OR_EXEC_FLAGS):
            return False
        if token.startswith("-O"):
            return False
    return True


def provider_generic_action(words: list[str]) -> tuple[int, str, str] | None:
    index = 1
    while index < len(words):
        token = words[index]
        if token in PROVIDER_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in PROVIDER_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-R") and token != "-R":
            index += 1
            continue
        if token in {"--dry-run", "-h", "--help", "-V", "--version"}:
            index += 1
            continue
        if token.startswith("-"):
            return None
        break
    if index + 1 >= len(words):
        return None
    return index, words[index], words[index + 1]


def provider_group_action(words: list[str]) -> tuple[int, str, str] | None:
    parsed = provider_generic_action(words)
    if parsed is None or parsed[1] not in {"issue", "pr"}:
        return None
    return parsed


def claim_bootstrap_invocation(
    words: list[str], agent_session_executable: str, base: Path | None
) -> bool:
    if words[:3] != [
        "agent-session",
        "work-context",
        "claim",
    ]:
        return False
    candidate = shutil.which(words[0])
    if not candidate or os.path.realpath(candidate) != os.path.realpath(
        agent_session_executable
    ):
        return False
    current_session = os.environ.get("AGENT_SESSION_ID", "").strip()
    capability_file = os.environ.get("AGENT_SESSION_CAPABILITY_FILE", "").strip()
    tail_index = 7
    if words[7:8] == ["--if-revision"]:
        if len(words) != 15 or not lifecycle_revision(words[8]):
            return False
        tail_index = 9
    elif len(words) != 13:
        return False
    if (
        words[3] != "--session"
        or not current_session
        or words[4] != current_session
        or words[5] != "--file"
        or words[tail_index] != "--capability-file"
        or not capability_file
        or words[tail_index + 1] != capability_file
        or words[tail_index + 2] != "--idempotency-key"
        or words[tail_index + 4 :] != ["--format", "json"]
        or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", words[tail_index + 3]
        )
        is None
    ):
        return False
    for raw, require_json in (
        (words[6], True),
        (words[tail_index + 1], False),
    ):
        if (
            not os.path.isabs(raw)
            or os.path.normpath(raw) != raw
            or os.path.islink(raw)
            or not os.path.isfile(raw)
            or (require_json and not raw.endswith(".json"))
        ):
            return False
        if base is not None:
            repository = bounded_git_toplevel(str(base))
            if repository:
                try:
                    if os.path.commonpath(
                        (os.path.realpath(raw), os.path.realpath(repository))
                    ) == os.path.realpath(repository):
                        return False
                except ValueError:
                    return False
    return True


def main_agent_private_packet(raw: str, repository: str | None) -> bool:
    if not lifecycle_private_file(raw, repository, json_file=True):
        return False
    try:
        metadata = os.stat(raw, follow_symlinks=False)
    except OSError:
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
    )


def trusted_main_agent_sibling(agent_session_executable: str) -> str | None:
    """Resolve a same-release ``main-agent`` sibling of ``agent-session``."""
    main_candidate = shutil.which("main-agent")
    session_candidate = shutil.which("agent-session")
    trusted_main = resolved_trusted_cli("main-agent")
    if (
        not main_candidate
        or not session_candidate
        or not trusted_main
        or not os.path.isabs(main_candidate)
        or not os.path.isabs(session_candidate)
    ):
        return None
    if os.path.dirname(os.path.abspath(main_candidate)) != os.path.dirname(
        os.path.abspath(session_candidate)
    ):
        return None
    if os.path.dirname(os.path.realpath(trusted_main)) != os.path.dirname(
        os.path.realpath(agent_session_executable)
    ):
        return None
    if os.path.realpath(session_candidate) != os.path.realpath(
        agent_session_executable
    ):
        return None
    main_version = run_cli([trusted_main, "--version"])
    session_version = run_cli([agent_session_executable, "--version"])
    if (
        main_version is None
        or session_version is None
        or main_version.returncode != 0
        or session_version.returncode != 0
    ):
        return None
    parsed_main = parse_version(main_version.stdout + "\n" + main_version.stderr)
    parsed_session = parse_version(
        session_version.stdout + "\n" + session_version.stderr
    )
    if parsed_main is None or parsed_main != parsed_session:
        return None
    return trusted_main


def main_agent_bypass_invocation(
    words: list[str], agent_session_executable: str, base: Path | None
) -> bool:
    """Validate one finite trusted pre-claim Main Agent command."""
    if words[:1] != ["main-agent"]:
        return False
    candidate = shutil.which(words[0])
    trusted = trusted_main_agent_sibling(agent_session_executable)
    if (
        not candidate
        or not trusted
        or os.path.realpath(candidate) != os.path.realpath(trusted)
    ):
        return False
    if words == ["main-agent", "--version"]:
        return True
    if words in (
        ["main-agent", "self", "show", "--format", "json"],
        ["main-agent", "rehydrate", "--format", "json"],
        ["main-agent", "rehydrate", "--format", "markdown"],
        ["main-agent", "status", "--format", "json"],
        ["main-agent", "worker", "list", "--format", "json"],
    ):
        return True
    if words[:3] == ["main-agent", "worker", "show"]:
        return (
            len(words) == 6
            and lifecycle_identifier(words[3])
            and words[4:] == ["--format", "json"]
        )
    if words[:2] == ["main-agent", "rebind"]:
        return (
            len(words) == 8
            and words[2] == "--if-revision"
            and lifecycle_revision(words[3])
            and words[4] == "--idempotency-key"
            and lifecycle_idempotency_key(words[5])
            and words[6:] == ["--format", "json"]
        )
    if len(words) < 4 or words[:3] != ["main-agent", "init", "--packet-file"]:
        return False
    repository = bounded_git_toplevel(str(base)) if base is not None else None
    if not main_agent_private_packet(words[3], repository):
        return False
    if len(words) == 9:
        return (
            words[4:6] == ["--if-absent", "--idempotency-key"]
            and lifecycle_idempotency_key(words[6])
            and words[7:] == ["--format", "json"]
        )
    return (
        len(words) == 10
        and words[4] == "--if-revision"
        and lifecycle_revision(words[5])
        and words[6] == "--idempotency-key"
        and lifecycle_idempotency_key(words[7])
        and words[8:] == ["--format", "json"]
    )


def invocation_bypasses_admission(
    words: list[str], agent_session_executable: str, base: Path | None = None
) -> bool:
    if "/" in words[0] and not os.path.isabs(words[0]):
        return False
    name = os.path.basename(words[0])
    if name == "main-agent":
        return main_agent_bypass_invocation(words, agent_session_executable, base)
    if name == "agent-session" and len(words) >= 2:
        candidate = shutil.which(words[0]) if "/" not in words[0] else words[0]
        trusted = bool(candidate) and os.path.realpath(candidate) == os.path.realpath(
            agent_session_executable
        )
        if words[1:3] == ["work-context", "claim"]:
            return trusted and claim_bootstrap_invocation(
                words, agent_session_executable, base
            )
        if words[1] == "work-context":
            return trusted and len(words) >= 3 and words[2] in {
                "status",
                "set",
                "clear",
                "advise",
                "acknowledge",
                "--help",
                "help",
            }
        return trusted and words[1] == "activity"
    if name == "agent-docs":
        candidate = words[0] if os.path.isabs(words[0]) else shutil.which(words[0])
        trusted = resolved_trusted_cli("agent-docs")
        return bool(candidate) and bool(trusted) and os.path.realpath(candidate) == trusted and (
            "preflight" in words
            or (
                "session" in words
                and any(item in words for item in ("prepare", "activate", "verify"))
            )
        )
    if audited_text_read_invocation(words):
        return trusted_command(words[0], name)
    if name == "git":
        return trusted_command(words[0], name) and git_read_only(words[1:])
    if name in {"gh", "forge-cli"}:
        if not trusted_command(words[0], name):
            return False
        parsed = provider_group_action(words)
        return bool(parsed and parsed[2] in READ_ONLY_PROVIDER) or any(
            item in {"-h", "--help", "--dry-run"} for item in words[1:]
        )
    return False


def git_mutates(args: list[str]) -> bool:
    index = 0
    while index < len(args):
        token = args[index]
        if token in GIT_GLOBAL_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in GIT_GLOBAL_VALUE_OPTIONS):
            index += 1
            continue
        if token in GIT_GLOBAL_FLAG_OPTIONS:
            index += 1
            continue
        if token.startswith("-"):
            return False
        break
    if index >= len(args):
        return False
    subcommand = args[index]
    action = args[index + 1 :]
    if subcommand in {"push", "fetch"}:
        return "--dry-run" not in action and "-n" not in action
    if subcommand in MUTATING_GIT:
        return True
    if subcommand == "branch":
        if not action:
            return False
        mutation_flags = {
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
        }
        if any(
            token in mutation_flags
            or token.startswith(tuple(f"{flag}=" for flag in mutation_flags))
            for token in action
        ):
            return True
        read_value_flags = {
            "--contains",
            "--no-contains",
            "--merged",
            "--no-merged",
            "--points-at",
            "--format",
            "--sort",
        }
        if any(token in {"-l", "--list"} for token in action):
            return False
        index = 0
        while index < len(action):
            token = action[index]
            if token in read_value_flags:
                index += 2
                continue
            if token.startswith(tuple(f"{flag}=" for flag in read_value_flags)):
                index += 1
                continue
            if token.startswith("-"):
                index += 1
                continue
            return True
        return False
    if subcommand == "tag":
        if not action:
            return False
        if any(
            token
            in {
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
            }
            for token in action
        ):
            return True
        if any(token in {"-l", "--list", "-v", "--verify"} for token in action):
            return False
        read_value_flags = {
            "--contains",
            "--no-contains",
            "--merged",
            "--no-merged",
            "--points-at",
            "--format",
            "--sort",
        }
        index = 0
        while index < len(action):
            token = action[index]
            if token in read_value_flags:
                index += 2
                continue
            if token.startswith(tuple(f"{flag}=" for flag in read_value_flags)):
                index += 1
                continue
            if token.startswith("-"):
                index += 1
                continue
            return True
        return False
    if subcommand == "config":
        if any(
            token
            in {
                "--add",
                "--replace-all",
                "--unset",
                "--unset-all",
                "--remove-section",
                "--rename-section",
            }
            for token in action
        ):
            return True
        positional = [token for token in action if not token.startswith("-")]
        return len(positional) >= 2
    if subcommand == "remote":
        return bool(action) and action[0] not in {"-v", "show", "get-url"}
    if subcommand == "notes":
        return not action or action[0] not in {"list", "show"}
    if subcommand == "stash":
        return not action or action[0] not in {"list", "show"}
    if subcommand == "worktree":
        return bool(action) and action[0] != "list"
    if subcommand == "reflog":
        return bool(action) and action[0] in {"delete", "expire"}
    if subcommand == "symbolic-ref":
        return "--delete" in action or len(
            [token for token in action if not token.startswith("-")]
        ) >= 2
    return False


def provider_api_mutates(words: list[str], group_index: int) -> bool:
    method = ""
    has_input = False
    tail = words[group_index + 1 :]
    index = 0
    while index < len(tail):
        token = tail[index]
        if token in {"-X", "--method"} and index + 1 < len(tail):
            method = tail[index + 1].upper()
            index += 2
            continue
        if token.startswith(("-X", "--method=")):
            method = token.split("=", 1)[1].upper() if "=" in token else token[2:].upper()
        if token in {"-f", "-F", "--field", "--raw-field", "--input"} or token.startswith(
            ("-f", "-F", "--field=", "--raw-field=", "--input=")
        ):
            has_input = True
        index += 1
    if method:
        return method not in {"GET", "HEAD"}
    return has_input


def provider_mutates(words: list[str]) -> bool:
    parsed = provider_generic_action(words)
    if parsed is None:
        return False
    group_index, group, action = parsed
    if group == "api" and os.path.basename(words[0]) == "gh":
        return provider_api_mutates(words, group_index)
    return action in PROVIDER_MUTATION_ACTIONS


def redirect_targets_repository(tokens: list[str], repository_root: Path | None) -> bool:
    for raw_target, _inspectable in output_redirect_targets(tokens):
        if raw_target == os.devnull or any(
            character in raw_target for character in "$`*?[{("
        ):
            continue
        target = Path(raw_target).expanduser()
        if not target.is_absolute():
            return True
        if repository_root is None:
            continue
        try:
            if os.path.commonpath((target.resolve(strict=False), repository_root)) == str(
                repository_root
            ):
                return True
        except (OSError, RuntimeError, ValueError):
            continue
    return False


def invocation_is_recognized_mutation(
    tokens: list[str], repository_root: Path | None
) -> bool:
    if redirect_targets_repository(tokens, repository_root):
        return True
    invocation = invocation_tokens(tokens)
    if not invocation or invocation_is_opaque(invocation):
        return False
    name = os.path.basename(invocation[0])
    arguments = invocation[1:]
    if name in MUTATING_EXECUTABLES:
        return True
    if name == "git":
        return git_mutates(arguments)
    if name in {"gh", "forge-cli"}:
        return provider_mutates(invocation)
    if name == "semantic-commit":
        return bool(arguments) and arguments[0] in {
            "commit",
            "fixup",
            "squash",
            "local-default",
        }
    return name == "git-cli" and len(arguments) >= 2 and (
        arguments[0], arguments[1]
    ) in {
        ("worktree", "add"),
        ("worktree", "remove"),
        ("worktree", "adopt-dirty"),
        ("worktree", "revoke-dirty"),
    }


def has_static_absolute_redirect(command: str) -> bool:
    """Whether a command has an inspectable absolute output redirect."""
    for tokens in simple_commands_with_nested_shells(command):
        for raw_target, _inspectable in output_redirect_targets(tokens):
            if raw_target == os.devnull or any(
                character in raw_target for character in "$`*?[{("
            ):
                continue
            if Path(raw_target).expanduser().is_absolute():
                return True
    return False


def command_effect(
    command: str, agent_session_executable: str, base: Path
):
    def classify(repository_root: Path | None):
        return classify_shell_effect(
            command,
            read_only_invocation=lambda words: invocation_bypasses_admission(
                words, agent_session_executable, base
            ),
            mutation_invocation=lambda tokens: invocation_is_recognized_mutation(
                tokens, repository_root
            ),
        )

    effect = classify(None)
    if effect.kind != SHELL_EFFECT_UNKNOWN or not has_static_absolute_redirect(command):
        return effect
    # Only an absolute redirect needs the repository root to decide whether the
    # write targets this checkout. Ordinary reads and unknown commands avoid a
    # Git subprocess on the default advisory hot path.
    root_raw = bounded_git_toplevel(str(base))
    repository_root = Path(root_raw).resolve() if root_raw else None
    return classify(repository_root)


def command_bypasses_admission(
    command: str, agent_session_executable: str, base: Path | None = None
) -> bool:
    claim_words = literal_claim_bootstrap_words(command)
    if claim_words is not None:
        return invocation_bypasses_admission(
            claim_words, agent_session_executable, base
        )
    lifecycle_words = literal_projected_lifecycle_words(command, base)
    if lifecycle_words is not None:
        candidate = shutil.which(lifecycle_words[0])
        return bool(candidate) and os.path.realpath(candidate) == os.path.realpath(
            agent_session_executable
        )
    if re.search(r"(?<![A-Za-z0-9_.-])main-agent(?:\s|$)", command):
        words = simple_words(command)
        return bool(words) and invocation_bypasses_admission(
            words, agent_session_executable, base
        )
    effect = classify_shell_effect(
        command,
        read_only_invocation=lambda words: invocation_bypasses_admission(
            words, agent_session_executable, base
        ),
    )
    return effect.kind == SHELL_EFFECT_READ_ONLY


def literal_lifecycle_near_miss(command: str) -> bool:
    """Detect raw owner-selecting control-plane commands that missed validation."""
    words = simple_words(command)
    if not words or words[:1] != ["agent-session"] or len(words) < 3:
        return False
    if words[1] == "work-context":
        return words[2] in {
            "show",
            "check",
            "renew",
            "release",
            "admit",
            "complete",
            "reconcile",
        }
    return words[1] in {"broker", "message"}


def nested_paths(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in {"file_path", "path", "filename", "notebook_path"}:
                if isinstance(nested, str) and nested:
                    yield nested
            else:
                yield from nested_paths(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            yield from nested_paths(nested)


def edit_paths(payload: Mapping[str, Any]) -> list[str]:
    paths = list(nested_paths(tool_input_dict(payload)))
    for candidate in patch_text_candidates(payload):
        paths.extend(apply_patch_paths(candidate))
    return list(dict.fromkeys(paths))


def repository_id(root: Path) -> str | None:
    completed = run_cli(["git", "-C", str(root), "remote", "get-url", "origin"])
    if completed is None or completed.returncode != 0:
        return None
    remote = completed.stdout.strip().removesuffix(".git").rstrip("/")
    path = (
        remote.rsplit(":", 1)[-1]
        if ":" in remote and "/" not in remote.split(":", 1)[0]
        else remote
    )
    parts = path.split("/")
    if len(parts) < 2:
        return None
    owner, repository = parts[-2].lower(), parts[-1].lower()
    valid = re.compile(r"^[a-z0-9_.-]{1,100}$")
    if not valid.fullmatch(owner) or not valid.fullmatch(repository):
        return None
    return f"{owner}/{repository}"


def canonical_target_path(
    raw: str,
    base: Path,
    known_root: Path | None = None,
    known_repository: str | None = None,
) -> tuple[dict[str, str], dict[str, str]] | None:
    lexical = Path(raw).expanduser()
    if not lexical.is_absolute():
        lexical = base / lexical
    current = Path(lexical.anchor)
    for component in lexical.parts[1:]:
        current /= component
        try:
            if current.is_symlink():
                return None
        except OSError:
            return None
        if not current.exists():
            break
    path = lexical.resolve(strict=False)
    root: Path | None = None
    repository: str | None = None
    if known_root is not None and known_repository is not None:
        try:
            path.relative_to(known_root)
        except ValueError:
            pass
        else:
            probe = path if path.is_dir() else path.parent
            nested_checkout = False
            while probe != known_root and probe != probe.parent:
                if (probe / ".git").exists():
                    nested_checkout = True
                    break
                probe = probe.parent
            if not nested_checkout:
                root = known_root
                repository = known_repository
    probe = path if path.is_dir() else path.parent
    if root is None or repository is None:
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        root_raw = bounded_git_toplevel(str(probe))
        if not root_raw:
            return None
        root = Path(root_raw).resolve()
        repository = repository_id(root)
        if repository is None:
            return None
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if relative == Path("."):
        target = {"kind": "repository", "repository": repository, "value": "."}
    else:
        target = {
            "kind": "path-exact",
            "repository": repository,
            "value": relative.as_posix(),
        }
    return target, {"repository": repository, "path": str(root)}


def normalized_repository(raw: str) -> str | None:
    value = raw.strip().removesuffix(".git").strip("/").lower()
    if value.startswith(("http://", "https://")):
        value = value.split("/", 3)[-1]
    parts = value.split("/")
    valid = re.compile(r"^[a-z0-9_.-]{1,100}$")
    if len(parts) < 2 or len(parts) > 10 or not all(valid.fullmatch(item) for item in parts):
        return None
    return "/".join(parts)


def option_value(words: list[str], names: frozenset[str]) -> str | None:
    for index, token in enumerate(words):
        if token in names and index + 1 < len(words):
            return words[index + 1]
        for name in names:
            if token.startswith(f"{name}="):
                return token.split("=", 1)[1]
        if "-R" in names and token.startswith("-R") and token != "-R":
            return token[2:]
    return None


def provider_target(
    words: list[str], repository: str
) -> tuple[str, dict[str, Any]] | None:
    if not words or os.path.basename(words[0]) not in {"gh", "forge-cli"}:
        return None
    parsed = provider_group_action(words)
    if parsed is None:
        return None
    group_index, group, action = parsed
    if action in READ_ONLY_PROVIDER:
        return None
    override = option_value(words[1:], frozenset({"--repo", "-R"}))
    effective_repository = normalized_repository(override) if override else repository
    if effective_repository is None:
        return (f"provider-{group}-unresolved", {})
    if action in {"create", "deliver"}:
        return (f"provider-{group}-unresolved", {})
    number = 0
    tail = words[group_index + 2 :]
    for index, value in enumerate(tail):
        if value == "--number" and index + 1 < len(tail):
            candidate = tail[index + 1].lstrip("#")
            if candidate.isdigit():
                number = int(candidate)
                break
    if number == 0 and tail:
        candidate = tail[0].lstrip("#")
        if candidate.isdigit():
            number = int(candidate)
        else:
            url = re.fullmatch(
                r"https?://[^/]+/(.+?)/(?:(issues|pull|merge_requests))/(\d+)(?:/.*)?",
                tail[0],
            )
            if url:
                url_repo = normalized_repository(url.group(1))
                url_kind = "issue" if url.group(2) == "issues" else "pr"
                if url_repo is None or url_kind != group:
                    return (f"provider-{group}-unresolved", {})
                effective_repository = url_repo
                number = int(url.group(3))
    if number <= 0:
        return (f"provider-{group}-unresolved", {})
    return (
        f"provider-{group}",
        {"kind": group, "repository": effective_repository, "number": number},
    )


def explicit_cross_repository(
    words: list[str], base: Path, root: Path
) -> bool:
    candidates: list[str] = []
    for index, token in enumerate(words):
        if token in {"-C", "--git-dir", "--work-tree", "--repo"} and index + 1 < len(words):
            candidates.append(words[index + 1])
        elif token.startswith(("-C=", "--git-dir=", "--work-tree=", "--repo=")):
            candidates.append(token.split("=", 1)[1])
        elif "/" in token and not token.startswith(("-", "http://", "https://")):
            candidates.append(token)
    for raw in candidates:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = base / path
        probe = path if path.is_dir() else path.parent
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        candidate_root = bounded_git_toplevel(str(probe))
        if candidate_root and Path(candidate_root).resolve() != root:
            return True
    return False


def operation_targets(
    payload: Mapping[str, Any], tool: str
) -> tuple[str, dict[str, Any]] | tuple[None, str]:
    base = effective_workdir(payload).resolve(strict=False)
    targets: list[dict[str, str]] = []
    checkouts: list[dict[str, str]] = []
    provider_refs: list[dict[str, Any]] = []
    operation = "edit"
    if tool in EDIT_TOOLS:
        paths = edit_paths(payload)
        if not paths:
            return None, "target-extraction-failed"
        known_root: Path | None = None
        known_repository: str | None = None
        root_raw = bounded_git_toplevel(str(base))
        if root_raw:
            candidate_root = Path(root_raw).resolve()
            candidate_repository = repository_id(candidate_root)
            if candidate_repository is not None:
                known_root = candidate_root
                known_repository = candidate_repository
        for raw in paths:
            resolved = canonical_target_path(
                raw,
                base,
                known_root=known_root,
                known_repository=known_repository,
            )
            if resolved is None:
                return None, "target-boundary-unavailable"
            target, checkout = resolved
            targets.append(target)
            checkouts.append(checkout)
    else:
        root_raw = bounded_git_toplevel(str(base))
        if not root_raw:
            return None, "outside-governed-repository"
        root = Path(root_raw).resolve()
        repository = repository_id(root)
        if repository is None:
            return None, "repository-identity-unavailable"
        words = simple_words(command_from(payload))
        command = command_from(payload)
        provider_in_command = re.search(
            r"(?:^|[\s'\"/])(?:forge-cli|gh)(?=[\s'\";]|$)", command
        )
        if words is None:
            return None, (
                "provider-target-unresolved"
                if provider_in_command
                else "shell-target-unresolved"
            )
        target_words, _ = unwrap_nested_shell(words)
        if target_words is None:
            return None, "shell-target-unresolved"
        if provider_in_command and os.path.basename(words[0]) not in {"gh", "forge-cli"}:
            return None, "provider-target-unresolved"
        if words and os.path.basename(words[0]) not in {"gh", "forge-cli"} and any(
            os.path.basename(item) in {"gh", "forge-cli"} for item in words[1:]
        ):
            return None, "provider-target-unresolved"
        provider = provider_target(words or [], repository)
        if provider is not None:
            operation, provider_ref = provider
            if not provider_ref:
                return None, operation
            provider_refs.append(provider_ref)
        elif words and os.path.basename(words[0]) in {"gh", "forge-cli"}:
            return None, "provider-target-unresolved"
        else:
            if explicit_cross_repository(target_words, base, root):
                return None, "cross-repository-shell-target"
            operation = "shell"
            targets.append({"kind": "repository", "repository": repository, "value": "."})
            checkouts.append({"repository": repository, "path": str(root)})
    checkout_roots: dict[str, str] = {}
    for checkout in checkouts:
        prior = checkout_roots.setdefault(checkout["repository"], checkout["path"])
        if prior != checkout["path"]:
            return None, "multiple-worktrees-one-repository"
    unique_targets = list(
        {json.dumps(item, sort_keys=True): item for item in targets}.values()
    )
    unique_checkouts = [
        {"repository": repository, "path": path}
        for repository, path in checkout_roots.items()
    ]
    return operation, {
        "schema_version": "agent-session.operation-targets.v1",
        "targets": unique_targets,
        "provider_refs": provider_refs,
        "checkouts": unique_checkouts,
    }


def state_root(product: str) -> Path:
    override = os.environ.get("AGENT_RUNTIME_STATE_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    xdg = os.environ.get("XDG_STATE_HOME", "").strip()
    if not xdg:
        xdg = os.path.join(os.path.expanduser("~"), ".local", "state")
    return Path(xdg).expanduser().resolve() / "agent-runtime-kit" / product


def private_namespace(product: str, managed_session: str) -> Path:
    return state_root(product) / "session-coordination" / digest(managed_session)


def ensure_private_dir(path: Path) -> bool:
    try:
        if path.is_symlink():
            return False
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            return False
        path.chmod(0o700)
        return path.is_dir() and stat.S_IMODE(path.stat().st_mode) == 0o700
    except OSError:
        return False


def write_private(path: Path, data: str) -> bool:
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            handle.write(data)
        return True
    except OSError:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        best_effort_unlink(path)
        return False


def best_effort_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def replace_private(path: Path, body: Mapping[str, Any]) -> bool:
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.new")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(body, handle, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
        return True
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def json_body(completed: subprocess.CompletedProcess[str] | None) -> dict[str, Any]:
    if completed is None:
        return {}
    try:
        value = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def result_data(body: Mapping[str, Any]) -> dict[str, Any]:
    data = body.get("data")
    if body.get("ok") is True and isinstance(data, dict):
        return data
    result = body.get("result")
    if body.get("ok") is True and isinstance(result, dict):
        return result
    return {}


def error_code(body: Mapping[str, Any]) -> str:
    error = body.get("error")
    if not isinstance(error, Mapping):
        return "coordination-unavailable"
    code = error.get("code")
    return code if isinstance(code, str) and code else "coordination-unavailable"


def common_cli_args(executable: str, state_dir: str) -> list[str]:
    return [executable, "--state-dir", state_dir]


def claim_recovery_reason(code: str) -> str:
    suffix = (
        "stale or replaced" if "incarnation" in code else "missing or unavailable"
    )
    return (
        f"Managed mutation requires an active work-context claim; the current claim is {suffix}. "
        "Inspect privacy-safe metadata, then run `agent-session work-context claim "
        "--session \"$AGENT_SESSION_ID\" --file <private-context.json> "
        "--capability-file \"$AGENT_SESSION_CAPABILITY_FILE\" "
        "--idempotency-key <unique-key> --format json` and retry. "
        "Do not inspect logs, transcripts, prompt text, or mailbox bodies automatically. "
        f"[reason: {code}]"
    )


def emit_advisory_unavailable(reason: str) -> None:
    emit_system(
        "Session coordination is unavailable, but work remains allowed because "
        "coordination is advisory. Retry `agent-session work-context advise --format "
        f"json` when useful. [reason: {reason}]"
    )


def advisory_pre_tool(
    payload: Mapping[str, Any],
    *,
    executable: str,
    managed_session: str,
    state_dir: str,
    product: str,
) -> int:
    tool = tool_name(payload)
    if tool in COMMAND_TOOLS:
        effect = command_effect(
            command_from(payload), executable, effective_workdir(payload).resolve()
        )
        # Advisory mode reports overlap only for a recognized mutation. Unknown
        # shell effects remain subject to the fail-closed enforce path, but do
        # not create mutation-shaped warning noise in the default mode.
        if effect.kind != SHELL_EFFECT_MUTATION:
            return ALLOW
    args = common_cli_args(executable, state_dir) + ["work-context", "advise"]
    temporary: Path | None = None
    operation, targets_or_reason = operation_targets(payload, tool)
    if operation is not None and isinstance(targets_or_reason, dict):
        namespace = private_namespace(product, managed_session)
        if ensure_private_dir(namespace):
            temporary = namespace / f"advisory-{uuid.uuid4().hex}.targets.json"
            if write_private(
                temporary, json.dumps(targets_or_reason, sort_keys=True) + "\n"
            ):
                args.extend(["--targets-file", str(temporary)])
    args.extend(["--format", "json"])
    try:
        completed = run_cli(args)
    finally:
        if temporary is not None:
            best_effort_unlink(temporary)
    body = json_body(completed)
    advisory = result_data(body)
    if completed is None or completed.returncode != 0 or not advisory:
        emit_advisory_unavailable("coordination-unavailable")
        return ALLOW
    if (
        advisory.get("schema_version")
        != "agent-session.work-context-advisory.v1"
        or advisory.get("managed") is not True
        or not isinstance(advisory.get("available"), bool)
    ):
        emit_advisory_unavailable("advisory-invalid")
        return ALLOW
    if advisory.get("suppressed") is True or advisory.get("severity") == "none":
        return ALLOW
    severity = advisory.get("severity")
    if severity == "warning":
        emit_system(
            "Session coordination advisory: possible overlap with another managed "
            "session. Work remains allowed; coordinate or run `agent-session "
            "work-context acknowledge --for 30m` if the overlap is intentional. "
            "[reason: possible-overlap]"
        )
    elif severity == "info":
        emit_system(
            "Session coordination advisory: another managed session is active in this "
            "repository, but no direct overlap is known. Work remains allowed. "
            "[reason: shared-repository]"
        )
    elif severity == "degraded":
        emit_advisory_unavailable("incomplete-peer-state")
    else:
        emit_advisory_unavailable("advisory-invalid")
    return ALLOW


def acquire_operation_lock(path: Path) -> int | None:
    lock_path = path.with_suffix(".lock")
    try:
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
        if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o600:
            os.close(descriptor)
            return None
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return descriptor
    except OSError:
        return None


def release_operation_lock(descriptor: int | None) -> None:
    if descriptor is None:
        return
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _pre_tool_locked(
    payload: Mapping[str, Any],
    *,
    executable: str,
    managed_session: str,
    capability_file: str,
    state_dir: str,
    product: str,
) -> int:
    tool = tool_name(payload)
    if tool in COMMAND_TOOLS:
        command = command_from(payload)
        if command_bypasses_admission(
            command, executable, effective_workdir(payload).resolve()
        ):
            return ALLOW
        if literal_lifecycle_near_miss(command):
            emit_block(
                "Managed coordination lifecycle commands must use the exact "
                "authenticated current-session shape. "
                "[reason: coordination-lifecycle-untrusted]"
            )
            return ALLOW
    call_id = tool_use_id(payload)
    if not call_id:
        emit_block(
            "Managed mutation admission requires a stable tool-call identity; retry from "
            "a supported managed runtime. [reason: tool-call-identity-unavailable]"
        )
        return ALLOW
    namespace = private_namespace(product, managed_session)
    if not ensure_private_dir(namespace):
        emit_block(
            "Managed mutation admission could not create its private operation state; "
            "repair runtime state permissions and retry. [reason: operation-state-unavailable]"
        )
        return ALLOW
    record_path = namespace / f"{digest(call_id)}.json"
    common = common_cli_args(executable, state_dir)
    if record_path.exists():
        prior = read_record(record_path)
        if prior.get("phase") == "admitting":
            status, code = resume_admission(executable, record_path, prior)
            if status == "active":
                return ALLOW
            emit_block(
                "A prior admission for this tool call remains uncertain; retry the exact "
                f"call or reconcile it. [reason: {code}]"
            )
            return ALLOW
        emit_block(
            "A prior operation for this tool call is still active or uncertain. Complete "
            "or reconcile it before retrying. [reason: operation-pending]"
        )
        return ALLOW
    show = run_cli(
        common
        + [
            "work-context",
            "show",
            "--session",
            managed_session,
            "--capability-file",
            capability_file,
            "--format",
            "json",
        ]
    )
    show_body = json_body(show)
    context = result_data(show_body)
    if show is None or show.returncode != 0 or not context:
        code = error_code(show_body)
        emit_block(
            claim_recovery_reason(
                code if code in CLAIM_ERROR_CODES else "claim-unavailable"
            )
        )
        return ALLOW
    if (
        context.get("schema_version") != "agent-session.work-context.v1"
        or context.get("state") != "active"
        or not isinstance(context.get("claim_id"), str)
        or not isinstance(context.get("revision"), int)
    ):
        emit_block(claim_recovery_reason("claim-invalid"))
        return ALLOW
    target_result = operation_targets(payload, tool)
    operation, targets_or_reason = target_result
    if operation is None:
        emit_block(
            "Managed mutation targets could not be proven as a subset of the active claim. "
            "Use explicit repository-relative edit targets or an explicit repository-scoped "
            f"claim, then retry. [reason: {targets_or_reason}]"
        )
        return ALLOW
    assert isinstance(targets_or_reason, dict)
    check = run_cli(
        common
        + [
            "work-context",
            "check",
            "--self",
            "--capability-file",
            capability_file,
            "--format",
            "json",
        ]
    )
    check_body = json_body(check)
    evaluation = result_data(check_body)
    if check is None or check.returncode != 0 or not evaluation:
        emit_block(
            "Managed mutation conflict evaluation is unavailable; retry after broker/context "
            "recovery. [reason: coordination-unavailable]"
        )
        return ALLOW
    classification = evaluation.get("classification")
    if classification == "conflict":
        emit_block(
            "Managed mutation has a definite peer conflict. Narrow or release the claim, "
            "coordinate through privacy-safe metadata, then retry. "
            "[reason: definite-peer-conflict]"
        )
        return ALLOW
    if classification not in ADVISORY_CLASSIFICATIONS | {"clear"}:
        emit_block(
            "Managed mutation conflict evaluation returned an unsupported state. "
            "[reason: coordination-unavailable]"
        )
        return ALLOW
    operation_key = digest(call_id)
    attempt = uuid.uuid4().hex
    token_path = namespace / f"{operation_key}.{attempt}.token"
    targets_path = namespace / f"{operation_key}.{attempt}.targets.json"
    outcome_path = namespace / f"{operation_key}.{attempt}.outcome"
    execution_token = f"hook-{uuid.uuid4().hex}"
    if not write_private(token_path, execution_token) or not write_private(
        targets_path, json.dumps(targets_or_reason, sort_keys=True) + "\n"
    ):
        token_path.unlink(missing_ok=True)
        targets_path.unlink(missing_ok=True)
        emit_block(
            "Managed mutation proof material could not be persisted privately. "
            "[reason: operation-state-unavailable]"
        )
        return ALLOW
    pending_record = {
        "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
        "phase": "admitting",
        "session": managed_session,
        "capability_file": capability_file,
        "state_dir": state_dir,
        "claim_id": context["claim_id"],
        "claim_revision": context["revision"],
        "operation": operation,
        "token_file": str(token_path),
        "targets_file": str(targets_path),
        "outcome_file": str(outcome_path),
        "outcome": None,
        "admit_idempotency": f"hook-admit-{digest(managed_session + ':' + call_id)[:32]}",
        "complete_idempotency": f"hook-complete-{digest(managed_session + ':' + call_id)[:32]}",
        "classification": classification,
    }
    if not write_private(record_path, json.dumps(pending_record, sort_keys=True) + "\n"):
        token_path.unlink(missing_ok=True)
        targets_path.unlink(missing_ok=True)
        emit_block(
            "Managed mutation admission intent could not be persisted privately. "
            "[reason: operation-state-unavailable]"
        )
        return ALLOW
    status, code = resume_admission(executable, record_path, pending_record)
    if status != "active":
        if code == "claim-conflict":
            reason = "definite peer conflict"
        elif code == "uncovered-mutation-scope":
            reason = "mutation target is not covered by the active claim"
        elif code in {"operation-in-progress", "coordination-unavailable"}:
            reason = "a prior operation is active or uncertain"
        else:
            reason = "operation admission is unavailable"
        emit_block(f"Managed mutation blocked: {reason}. [reason: {code}]")
        return ALLOW
    if isinstance(classification, str) and classification in ADVISORY_CLASSIFICATIONS:
        emit_system(
            "Session coordination advisory: "
            + classification.replace("_", " ")
            + "; operation admission succeeded. Inspect only the smallest privacy-safe "
            "metadata needed if clarification is material."
        )
    return ALLOW


def pre_tool(
    payload: Mapping[str, Any],
    *,
    executable: str,
    managed_session: str,
    capability_file: str,
    state_dir: str,
    product: str,
) -> int:
    tool = tool_name(payload)
    if tool in COMMAND_TOOLS and command_bypasses_admission(
        command_from(payload), executable, effective_workdir(payload).resolve()
    ):
        return ALLOW
    call_id = tool_use_id(payload)
    if not call_id:
        return _pre_tool_locked(
            payload,
            executable=executable,
            managed_session=managed_session,
            capability_file=capability_file,
            state_dir=state_dir,
            product=product,
        )
    namespace = private_namespace(product, managed_session)
    if not ensure_private_dir(namespace):
        emit_block(
            "Managed mutation admission could not create its private operation state; "
            "repair runtime state permissions and retry. [reason: operation-state-unavailable]"
        )
        return ALLOW
    record_path = namespace / f"{digest(call_id)}.json"
    descriptor = acquire_operation_lock(record_path)
    if descriptor is None:
        emit_block(
            "Managed mutation admission could not lock its private operation state. "
            "[reason: operation-state-unavailable]"
        )
        return ALLOW
    try:
        return _pre_tool_locked(
            payload,
            executable=executable,
            managed_session=managed_session,
            capability_file=capability_file,
            state_dir=state_dir,
            product=product,
        )
    finally:
        release_operation_lock(descriptor)


def read_record(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def response_failed(payload: Mapping[str, Any], event: str) -> bool:
    if event == "PostToolUseFailure":
        return True
    response = payload.get("tool_response")
    if not isinstance(response, Mapping):
        return False
    for key in ("exit_code", "exitCode", "status_code", "statusCode"):
        value = response.get(key)
        if isinstance(value, int):
            return value != 0
    return response.get("success") is False or bool(response.get("error"))


def operation_file(path: Path, raw: str, suffix: str) -> Path | None:
    candidate = Path(raw)
    try:
        resolved = candidate.resolve(strict=False)
        if resolved.parent != path.parent.resolve(strict=False):
            return None
    except OSError:
        return None
    expected_prefix = path.stem + "."
    if not candidate.name.startswith(expected_prefix) or not candidate.name.endswith(suffix):
        return None
    return candidate


def retire_record(path: Path, record: Mapping[str, Any]) -> bool:
    retired = path.with_name(path.name + f".{uuid.uuid4().hex}.retired")
    try:
        os.replace(path, retired)
    except OSError:
        return False
    for key, suffix in (
        ("token_file", ".token"),
        ("targets_file", ".targets.json"),
        ("outcome_file", ".outcome"),
    ):
        raw = record.get(key)
        candidate = operation_file(path, raw, suffix) if isinstance(raw, str) else None
        if candidate is not None:
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
    try:
        retired.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def resume_admission(
    executable: str, path: Path, record: dict[str, Any]
) -> tuple[str, str]:
    required_strings = (
        "session",
        "capability_file",
        "state_dir",
        "claim_id",
        "operation",
        "token_file",
        "targets_file",
        "outcome_file",
        "admit_idempotency",
        "complete_idempotency",
    )
    if (
        record.get("schema_version")
        != "agent-runtime-kit.session-coordination-operation.v1"
        or record.get("phase") != "admitting"
        or any(
            not isinstance(record.get(key), str) or not record.get(key)
            for key in required_strings
        )
        or not isinstance(record.get("claim_revision"), int)
    ):
        return "uncertain", "admission-record-invalid"
    token_file = operation_file(path, record["token_file"], ".token")
    targets_file = operation_file(path, record["targets_file"], ".targets.json")
    if (
        token_file is None
        or targets_file is None
        or not token_file.is_file()
        or not targets_file.is_file()
        or token_file.is_symlink()
        or targets_file.is_symlink()
    ):
        return "uncertain", "admission-proof-unavailable"
    admitted = run_cli(
        common_cli_args(executable, record["state_dir"])
        + [
            "work-context",
            "admit",
            "--session",
            record["session"],
            "--claim",
            record["claim_id"],
            "--if-revision",
            str(record["claim_revision"]),
            "--targets-file",
            str(targets_file),
            "--operation",
            record["operation"],
            "--execution-token-file",
            str(token_file),
            "--capability-file",
            record["capability_file"],
            "--idempotency-key",
            record["admit_idempotency"],
            "--format",
            "json",
        ]
    )
    body = json_body(admitted)
    lease = result_data(body)
    if admitted is None or admitted.returncode != 0 or not lease:
        code = error_code(body)
        if code in {
            "claim-conflict",
            "uncovered-mutation-scope",
            "claim-not-found",
            "claim-expired",
            "claim-revision-conflict",
            "session-incarnation-mismatch",
        }:
            retire_record(path, record)
            return "rejected", code
        return "uncertain", code
    if (
        lease.get("schema_version") != "agent-session.operation-lease.v1"
        or not isinstance(lease.get("lease_id"), str)
        or not isinstance(lease.get("revision"), int)
        or lease.get("state") != "active"
    ):
        return "uncertain", "invalid-operation-lease"
    active = dict(record)
    active.update(
        {
            "phase": "active",
            "lease_id": lease["lease_id"],
            "lease_revision": lease["revision"],
        }
    )
    if not replace_private(path, active):
        return "uncertain", "completion-record-unavailable"
    return "active", "admitted"


def operation_outcome(path: Path, record: Mapping[str, Any]) -> str | None:
    outcome = record.get("outcome")
    if isinstance(outcome, str) and outcome in {"pass", "fail"}:
        return outcome
    raw = record.get("outcome_file")
    if not isinstance(raw, str) or not raw:
        return None
    outcome_file = operation_file(path, raw, ".outcome")
    if outcome_file is None:
        return None
    try:
        if outcome_file.is_symlink() or not outcome_file.is_file():
            return None
        value = outcome_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value if value in {"pass", "fail"} else None


def complete_record(executable: str, path: Path, record: dict[str, Any]) -> bool:
    required_strings = (
        "session",
        "capability_file",
        "state_dir",
        "lease_id",
        "token_file",
        "targets_file",
        "outcome_file",
        "complete_idempotency",
    )
    if record.get("schema_version") != "agent-runtime-kit.session-coordination-operation.v1":
        return False
    if any(
        not isinstance(record.get(key), str) or not record.get(key)
        for key in required_strings
    ):
        return False
    revision = record.get("lease_revision")
    if record.get("phase") != "active" or not isinstance(revision, int):
        return False
    token_file = operation_file(path, record["token_file"], ".token")
    targets_file = operation_file(path, record["targets_file"], ".targets.json")
    outcome_file = operation_file(path, record["outcome_file"], ".outcome")
    outcome = operation_outcome(path, record)
    if token_file is None or targets_file is None or outcome_file is None or outcome is None:
        return False
    completed = run_cli(
        common_cli_args(executable, record["state_dir"])
        + [
            "work-context",
            "complete",
            "--session",
            record["session"],
            "--lease",
            record["lease_id"],
            "--if-revision",
            str(revision),
            "--execution-token-file",
            str(token_file),
            "--outcome",
            outcome,
            "--capability-file",
            record["capability_file"],
            "--idempotency-key",
            record["complete_idempotency"],
            "--format",
            "json",
        ]
    )
    body = json_body(completed)
    data = result_data(body)
    if completed is None or completed.returncode != 0 or not data:
        return False
    if data.get("schema_version") != "agent-session.operation-lease.v1":
        return False
    expected_state = "completed" if outcome == "pass" else "failed"
    if data.get("state") != expected_state:
        return False
    return retire_record(path, record)


def _post_tool_locked(
    payload: Mapping[str, Any],
    *,
    executable: str | None,
    managed_session: str,
    product: str,
    event: str,
) -> int:
    call_id = tool_use_id(payload)
    if not call_id:
        return ALLOW
    record_path = private_namespace(product, managed_session) / f"{digest(call_id)}.json"
    if not record_path.is_file():
        return ALLOW
    record = read_record(record_path)
    outcome = "fail" if response_failed(payload, event) else "pass"
    raw_outcome_path = record.get("outcome_file")
    outcome_path = (
        operation_file(record_path, raw_outcome_path, ".outcome")
        if isinstance(raw_outcome_path, str)
        else None
    )
    prior_outcome = operation_outcome(record_path, record)
    if outcome_path is None or (
        prior_outcome is None and not write_private(outcome_path, outcome + "\n")
    ) or (prior_outcome is not None and prior_outcome != outcome):
        emit_system(
            "Session coordination could not persist a trustworthy operation outcome; "
            "further managed mutations fail closed until the exact lease is reconciled."
        )
        return ALLOW
    record["outcome"] = outcome
    if not replace_private(record_path, record):
        emit_system(
            "Session coordination completion is pending; further managed mutations fail "
            "closed until the exact lease is completed or reconciled."
        )
        return ALLOW
    if executable is not None and record.get("phase") == "admitting":
        resume_admission(executable, record_path, record)
        record = read_record(record_path)
        record["outcome"] = outcome
    if executable is None or not complete_record(executable, record_path, record):
        emit_system(
            "Session coordination completion is pending; further managed mutations fail "
            "closed until the exact lease is completed or reconciled."
        )
    return ALLOW


def post_tool(
    payload: Mapping[str, Any],
    *,
    executable: str | None,
    managed_session: str,
    product: str,
    event: str,
) -> int:
    call_id = tool_use_id(payload)
    if not call_id:
        return ALLOW
    record_path = private_namespace(product, managed_session) / f"{digest(call_id)}.json"
    if not record_path.is_file():
        return ALLOW
    descriptor = acquire_operation_lock(record_path)
    if descriptor is None:
        emit_system(
            "Session coordination completion is pending because private operation state "
            "could not be locked."
        )
        return ALLOW
    try:
        return _post_tool_locked(
            payload,
            executable=executable,
            managed_session=managed_session,
            product=product,
            event=event,
        )
    finally:
        release_operation_lock(descriptor)


def stop_audit(executable: str | None, managed_session: str, product: str) -> int:
    namespace = private_namespace(product, managed_session)
    if not namespace.is_dir():
        return ALLOW
    records = list(
        path
        for path in namespace.glob("*.json")
        if not path.name.endswith(".targets.json")
    )
    records.sort(
        key=lambda path: (
            0 if operation_outcome(path, read_record(path)) in {"pass", "fail"} else 1,
            0 if read_record(path).get("phase") == "admitting" else 1,
            path.name,
        )
    )
    pending = len(records) > MAX_PENDING_RECORDS
    for path in records[:MAX_PENDING_RECORDS]:
        descriptor = acquire_operation_lock(path)
        if descriptor is None:
            pending = True
            continue
        try:
            record = read_record(path)
            if executable is not None and record.get("phase") == "admitting":
                resume_admission(executable, path, record)
                record = read_record(path)
            if (
                executable is not None
                and operation_outcome(path, record) in {"pass", "fail"}
                and complete_record(executable, path, record)
            ):
                continue
            pending = True
        finally:
            release_operation_lock(descriptor)
    if pending:
        emit_system(
            "Session coordination retains an unresolved operation proof. Use authenticated "
            "work-context complete/reconcile recovery before another mutation; Stop does not "
            "release or guess the outcome of an active operation."
        )
    return ALLOW


def main() -> int:
    global HOOK_DEADLINE
    HOOK_DEADLINE = time.monotonic() + HOOK_BUDGET_SECONDS
    payload = read_payload()
    event = hook_event(payload)
    product = os.environ.get("AGENT_RUNTIME_PRODUCT", "").strip()
    if product not in SUPPORTED_PRODUCTS:
        return ALLOW
    mode = coordination_mode()
    if mode == "off":
        return ALLOW
    managed_session = os.environ.get("AGENT_SESSION_ID", "").strip()
    capability_file = os.environ.get("AGENT_SESSION_CAPABILITY_FILE", "").strip()
    state_dir = os.environ.get("AGENT_SESSION_STATE_DIR", "").strip()
    if not managed_session and not capability_file:
        return ALLOW
    if not managed_session or not capability_file or not state_dir:
        if mode == "advisory":
            emit_advisory_unavailable("managed-metadata-incomplete")
        else:
            emit_system(
                "Session coordination is unavailable because this launch lacks complete managed "
                "session metadata; no enforcement claim is made."
            )
        return ALLOW
    tool = tool_name(payload)
    if tool not in EDIT_TOOLS | COMMAND_TOOLS and event != "Stop":
        return ALLOW
    if mode == "advisory" and event in {"PostToolUse", "PostToolUseFailure", "Stop"}:
        return ALLOW
    if event in {"PostToolUse", "PostToolUseFailure"}:
        executable = resolved_agent_session()
        if executable is not None and not coordination_capability(executable, mode):
            executable = None
        return post_tool(
            payload,
            executable=executable,
            managed_session=managed_session,
            product=product,
            event=event,
        )
    capability_path = Path(capability_file)
    try:
        capability_mode = stat.S_IMODE(capability_path.stat().st_mode)
    except OSError:
        capability_mode = 0
    if (
        capability_path.is_symlink()
        or not capability_path.is_file()
        or capability_mode != 0o600
    ):
        if mode == "advisory":
            emit_advisory_unavailable("capability-file-invalid")
        else:
            emit_system(
                "Session coordination is unavailable because the managed capability file is "
                "not a private regular file; no enforcement claim is made."
            )
        if event == "Stop":
            return stop_audit(None, managed_session, product)
        return ALLOW
    executable = resolved_agent_session()
    if executable is None or (
        mode == "enforce" and not coordination_capability(executable, mode)
    ):
        if mode == "advisory":
            emit_advisory_unavailable("coordination-surface-unavailable")
        else:
            emit_system(
                "Session coordination is unavailable on this agent-session surface; no "
                "enforcement claim is made. Upgrade to the repository-pinned runtime before "
                "relying on coordination."
            )
        if event == "Stop":
            return stop_audit(None, managed_session, product)
        return ALLOW
    if mode == "advisory":
        return advisory_pre_tool(
            payload,
            executable=executable,
            managed_session=managed_session,
            state_dir=state_dir,
            product=product,
        )
    if event == "Stop":
        return stop_audit(executable, managed_session, product)
    return pre_tool(
        payload,
        executable=executable,
        managed_session=managed_session,
        capability_file=capability_file,
        state_dir=state_dir,
        product=product,
    )


if __name__ == "__main__":
    raise SystemExit(main())
