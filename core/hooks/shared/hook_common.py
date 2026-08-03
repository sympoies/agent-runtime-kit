"""Shared helpers for product hook scripts.

Hooks should be conservative: if the input payload is missing or has an
unknown shape, allow the tool call and let the normal tool/runtime validation
handle it. Mechanical guardrails should block only when the relevant command
or path is explicit in the payload.

The helpers intentionally fan out across the union of Codex and Claude payload
keys so the hook implementations can stay shared while product activation
stays in `targets/<product>/`.
"""

from __future__ import annotations

import fcntl
import functools
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import stat
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

ALLOW = 0
# Contract stems may begin with `.terminal-`; only these exact filenames are
# reserved for the cross-product terminal handshake.
TERMINAL_OWNER_MARKER_NAMES = frozenset(
    {".terminal-codex", ".terminal-claude", ".terminal-shared"}
)

# The supported per-user managed CLI root (NILS_WRAPPER_INSTALL_PREFIX). It is
# trusted next to the packaged prefixes rather than needing an explicit
# override: on Linux hosts the Homebrew prefix is owner-writable too, so this
# location is no weaker than what these hooks already accept. Binaries here are
# regular files, so callers pair it with a lexical == resolved check, exactly as
# they do for /usr/bin.
MANAGED_CLI_HOME_BIN = os.path.join("~", ".local", "nils-cli", "bin")


def managed_cli_home_bin() -> str:
    return os.path.expanduser(MANAGED_CLI_HOME_BIN)


def is_managed_cli_home_bin(directory: str) -> bool:
    """Whether `directory` is the per-user managed CLI bin, lexical or resolved."""
    home_bin = managed_cli_home_bin()
    if directory == home_bin:
        return True
    try:
        return os.path.realpath(directory) == os.path.realpath(home_bin)
    except OSError:
        return False


def read_payload() -> dict[str, Any]:
    try:
        loaded = json.load(sys.stdin)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def emit_block(reason: str) -> None:
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.stdout.write("\n")


def tool_input_dict(payload: Mapping[str, Any]) -> dict[str, Any]:
    tool_input = payload.get("tool_input", {})
    return dict(tool_input) if isinstance(tool_input, dict) else {}


def command_from(payload: Mapping[str, Any]) -> str:
    tool_input = payload.get("tool_input", {})
    if isinstance(tool_input, dict):
        command = tool_input.get("command", "")
        return command if isinstance(command, str) else str(command)
    return ""


# Workdir keys used across the union of Codex and Claude tool envelopes. A guard
# that resolves the working repository from the hook process cwd alone misgates a
# command whose effective workdir is elsewhere (issue #601 P0-4), so every guard
# resolves the workdir through the shared ``effective_workdir`` below.
WORKDIR_KEYS = frozenset(
    {"cwd", "current_working_directory", "workdir", "working_directory"}
)


def iter_workdir_values(value: Any) -> list[str]:
    """Every non-empty workdir-key string reachable in a nested mapping."""
    values: list[str] = []
    if not isinstance(value, Mapping):
        return values
    for key, nested in value.items():
        if key in WORKDIR_KEYS and isinstance(nested, str) and nested:
            values.append(nested)
        elif isinstance(nested, Mapping):
            values.extend(iter_workdir_values(nested))
    return values


# Bound the transcript read: the workdir lives in the newest event matching the
# call, so a tail read suffices while capping memory and latency now that the
# resolver runs inside the mutation/lease guards on every command.
MAX_TRANSCRIPT_BYTES = 4 * 1024 * 1024
CODEX_EXEC_PRAGMA_RE = re.compile(
    r"\A[ \t]*// @exec:[ \t]*(?P<options>[^\r\n]+)[ \t]*\r?\n"
)
CODEX_CUSTOM_EXEC_PREFIX_RE = re.compile(
    r"\A\s*(?:const\s+(?P<binding>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*)?"
    r"await\s+tools\.exec_command\(\s*"
)
COMMAND_CONTEXT_SOURCES = frozenset(
    {
        "tool-input",
        "matching-transcript-call",
        "payload",
        "session-cwd",
        "managed-session-cwd",
        "process-cwd",
    }
)
MANAGED_SESSION_RECORD_MAX_BYTES = 64 * 1024
MANAGED_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class CommandContext(NamedTuple):
    """Canonical workdir plus its host-observable provenance.

    ``attested`` means the target came from an absolute provider/tool value for
    this call. It is deliberately false for process cwd, relative metadata, and
    a fallback selected after transcript-call matching failed. Consumers can
    therefore retain same-repository compatibility without silently treating a
    process-local fallback as an attested cross-repository target.
    """

    path: Path
    source: str
    attested: bool
    diagnostic: str | None = None


class TranscriptWorkdirResult(NamedTuple):
    value: str | None
    diagnostic: str | None


def _custom_exec_arguments(
    event_payload: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Decode one canonical Codex custom-tool exec argument object.

    Current Codex transcripts wrap ``tools.exec_command`` in a small JavaScript
    orchestration input instead of exposing the legacy JSON ``arguments``
    field. Trust only an anchored call whose first argument is strict JSON and
    whose closing parenthesis follows that object. We deliberately do not parse
    JavaScript object literals or search arbitrary source text for a
    ``workdir`` substring: either would let command content impersonate host
    context.
    """
    if (
        event_payload.get("type") != "custom_tool_call"
        or event_payload.get("name") != "exec"
    ):
        return None, "transcript-arguments-missing"
    source = event_payload.get("input")
    if not isinstance(source, str):
        return None, "transcript-custom-input-missing"
    pragma = CODEX_EXEC_PRAGMA_RE.match(source)
    if pragma is not None:
        try:
            pragma_options = json.loads(pragma.group("options"))
        except json.JSONDecodeError:
            return None, "transcript-custom-input-malformed"
        if not isinstance(pragma_options, Mapping):
            return None, "transcript-custom-input-malformed"
        source = source[pragma.end() :]
    elif source.lstrip().startswith("// @exec:"):
        return None, "transcript-custom-input-malformed"
    match = CODEX_CUSTOM_EXEC_PREFIX_RE.match(source)
    if match is None:
        return None, "transcript-custom-input-unrecognized"
    argument_source = source[match.end() :]
    try:
        parsed, end = json.JSONDecoder().raw_decode(argument_source)
    except json.JSONDecodeError:
        return None, "transcript-custom-input-malformed"
    if not isinstance(parsed, Mapping):
        return None, "transcript-custom-input-malformed"
    binding = match.group("binding")
    remainder_pattern = r"\s*\)\s*;?\s*"
    if binding:
        remainder_pattern += (
            rf"(?:text\(\s*{re.escape(binding)}\.output\s*\)\s*;?\s*)?"
        )
    if re.fullmatch(remainder_pattern, argument_source[end:]) is None:
        return None, "transcript-custom-input-ambiguous"
    if not isinstance(parsed.get("cmd"), str):
        return None, "transcript-custom-input-malformed"
    workdir = parsed.get("workdir")
    if workdir is None:
        return {}, None
    if not isinstance(workdir, str) or not workdir:
        return None, "transcript-custom-input-malformed"
    # The exec_command schema owns workdir at the top level. Returning only
    # that field prevents command or metadata content from impersonating host
    # context through the generic recursive envelope reader.
    return {"workdir": workdir}, None


@functools.lru_cache(maxsize=64)
def _transcript_workdir_result(
    transcript_path: str, tool_use_id: str
) -> TranscriptWorkdirResult:
    """Raw workdir and a stable matching diagnostic from a bounded tail read.

    Cached per (path, call id) so repeated guard resolutions in one process read
    the transcript once. Reads only the tail (``MAX_TRANSCRIPT_BYTES``) and fails
    soft on ANY error (missing, unreadable, oversized/OOM, malformed) so a
    hostile or corrupt transcript can never crash a fail-closed guard. The
    public context intentionally collapses these private details to
    ``workdir-attestation-missing``.
    """
    try:
        path = Path(transcript_path).expanduser()
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - MAX_TRANSCRIPT_BYTES)
            handle.seek(start)
            data = handle.read(MAX_TRANSCRIPT_BYTES)
        lines = data.decode("utf-8", errors="replace").splitlines()
        # Drop a leading partial line when the tail started mid-file; the newest
        # matching event we care about is at the end and stays intact.
        if start > 0 and lines:
            lines = lines[1:]
    except Exception:
        return TranscriptWorkdirResult(None, "transcript-unavailable")
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_payload = event.get("payload") if isinstance(event, Mapping) else None
        if not isinstance(event_payload, Mapping):
            continue
        if event_payload.get("call_id") != tool_use_id:
            continue
        arguments = event_payload.get("arguments")
        if isinstance(arguments, str):
            try:
                parsed_arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return TranscriptWorkdirResult(
                    None, "transcript-arguments-malformed"
                )
        else:
            parsed_arguments, diagnostic = _custom_exec_arguments(event_payload)
            if parsed_arguments is None:
                return TranscriptWorkdirResult(None, diagnostic)
        for value in iter_workdir_values(parsed_arguments):
            return TranscriptWorkdirResult(value, None)
        return TranscriptWorkdirResult(None, "transcript-workdir-missing")
    return TranscriptWorkdirResult(None, "transcript-call-mismatch")


def _transcript_workdir_value(transcript_path: str, tool_use_id: str) -> str | None:
    """Compatibility helper returning only the bounded transcript value."""
    return _transcript_workdir_result(transcript_path, tool_use_id).value


def workdir_from_transcript(payload: Mapping[str, Any]) -> Path | None:
    """Workdir from the Codex transcript's exec_command arguments.

    Codex submits a shell command's ``workdir`` in the transcript event whose
    ``call_id`` matches this call's ``tool_use_id`` rather than inline in the
    tool input. Delegates to a cached, bounded, fail-soft reader.
    """
    tool_use_id = payload.get("tool_use_id")
    transcript_path = payload.get("transcript_path")
    if not isinstance(tool_use_id, str) or not isinstance(transcript_path, str):
        return None
    value = _transcript_workdir_value(transcript_path, tool_use_id)
    if value is None:
        return None
    workdir = Path(value).expanduser()
    return workdir if workdir.is_absolute() else Path.cwd() / workdir


def _context_from_value(
    value: str,
    *,
    source: str,
    inherited_diagnostic: str | None = None,
) -> CommandContext:
    expanded = Path(value).expanduser()
    absolute = expanded.is_absolute()
    path = expanded if absolute else Path.cwd() / expanded
    diagnostic = inherited_diagnostic
    if not absolute or diagnostic is not None:
        diagnostic = "workdir-attestation-missing"
    return CommandContext(
        path.resolve(strict=False),
        source,
        absolute and diagnostic is None,
        diagnostic,
    )


def _managed_session_cwd() -> Path | None:
    """Return the authenticated managed-session cwd when it matches this process.

    Claude's Bash hook envelope does not consistently carry a per-call workdir.
    A target-rooted ``agent-session`` launch still has a durable private record,
    runtime incarnation, and process cwd. Treat that exact three-way match as
    host attestation without starting a subprocess or trusting prompt text.
    Malformed, replaced, symlinked, oversized, foreign-owned, or writable state
    fails soft to the ordinary un-attested process-cwd fallback.
    """
    session_id = os.environ.get("AGENT_SESSION_ID", "").strip()
    state_raw = os.environ.get("AGENT_SESSION_STATE_DIR", "").strip()
    runtime_id = os.environ.get("AGENT_SESSION_RUNTIME_ID", "").strip()
    if (
        not MANAGED_SESSION_ID_RE.fullmatch(session_id)
        or not state_raw
        or not runtime_id
    ):
        return None
    state_root = Path(state_raw).expanduser()
    if not state_root.is_absolute():
        return None
    try:
        state_root = state_root.resolve(strict=True)
        session_dir = state_root / "sessions" / session_id
        session_metadata = os.stat(session_dir, follow_symlinks=False)
        if (
            not stat.S_ISDIR(session_metadata.st_mode)
            or session_metadata.st_uid != os.geteuid()
            or session_metadata.st_mode & stat.S_IWOTH
        ):
            return None
        record_path = session_dir / "session.json"
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(record_path, flags)
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or metadata.st_size > MANAGED_SESSION_RECORD_MAX_BYTES
            ):
                return None
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                raw = handle.read(MANAGED_SESSION_RECORD_MAX_BYTES + 1)
        finally:
            os.close(descriptor)
        if len(raw) > MANAGED_SESSION_RECORD_MAX_BYTES:
            return None
        record = json.loads(raw)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(record, Mapping):
        return None
    runtime = record.get("runtime")
    startup = record.get("startup")
    if (
        record.get("id") != session_id
        or not isinstance(runtime, Mapping)
        or runtime.get("launch_id") != runtime_id
        or not isinstance(startup, Mapping)
        or startup.get("state") != "ready"
    ):
        return None
    product = os.environ.get("AGENT_RUNTIME_PRODUCT", "").strip()
    if product and record.get("agent") != product:
        return None
    value = record.get("cwd")
    if not isinstance(value, str) or not value:
        return None
    managed_cwd = Path(value).expanduser()
    if not managed_cwd.is_absolute():
        return None
    try:
        managed_cwd = managed_cwd.resolve(strict=True)
        process_cwd = Path.cwd().resolve(strict=True)
    except OSError:
        return None
    return managed_cwd if managed_cwd == process_cwd else None


def command_context(payload: Mapping[str, Any]) -> CommandContext:
    """Resolve canonical workdir provenance for one provider tool call.

    Fans out across the union of Codex and Claude envelope shapes: explicit
    workdir keys nested anywhere in the tool input, then the Codex transcript
    arguments (referenced by ``call_id``/``tool_use_id``), then non-session
    workdir keys nested elsewhere in the payload, then the top-level session
    ``cwd``, then an authenticated managed-session cwd, and finally process cwd.
    Transcript metadata that cannot be matched prevents an unauthenticated
    payload/session cwd from becoming attested for that call. An independently
    authenticated managed-session record may still attest the same real process
    cwd; this is required for Claude, whose current tool call can reach the hook
    before it is flushed to the transcript. The resolver is pure in-process
    except for bounded transcript/session-record reads; it never starts a
    subprocess.
    """
    tool_input = tool_input_dict(payload)
    for value in iter_workdir_values(tool_input):
        return _context_from_value(value, source="tool-input")

    transcript_diagnostic: str | None = None
    transcript_path = payload.get("transcript_path")
    tool_use_id = payload.get("tool_use_id")
    if isinstance(transcript_path, str) and transcript_path:
        if isinstance(tool_use_id, str) and tool_use_id:
            result = _transcript_workdir_result(transcript_path, tool_use_id)
            if result.value is not None:
                return _context_from_value(
                    result.value, source="matching-transcript-call"
                )
            transcript_diagnostic = result.diagnostic
        else:
            transcript_diagnostic = "transcript-call-id-missing"

    payload_metadata = {
        key: value
        for key, value in payload.items()
        if key not in {"tool_input", "cwd", "transcript_path", "tool_use_id"}
    }
    for value in iter_workdir_values(payload_metadata):
        context = _context_from_value(
            value,
            source="payload",
            inherited_diagnostic=transcript_diagnostic,
        )
        if context.attested:
            return context
        if (managed_cwd := _managed_session_cwd()) == context.path:
            return CommandContext(managed_cwd, "managed-session-cwd", True, None)
        return context
    top_cwd = payload.get("cwd")
    if isinstance(top_cwd, str) and top_cwd:
        context = _context_from_value(
            top_cwd,
            source="session-cwd",
            inherited_diagnostic=transcript_diagnostic,
        )
        if context.attested:
            return context
        if (managed_cwd := _managed_session_cwd()) == context.path:
            return CommandContext(managed_cwd, "managed-session-cwd", True, None)
        return context
    if managed_cwd := _managed_session_cwd():
        return CommandContext(managed_cwd, "managed-session-cwd", True, None)
    return CommandContext(
        Path.cwd().resolve(strict=False),
        "process-cwd",
        False,
        "workdir-attestation-missing",
    )


def effective_workdir(payload: Mapping[str, Any]) -> Path:
    """Compatibility wrapper returning the shared command-context path."""
    return command_context(payload).path


def session_id_from_payload(payload: Mapping[str, Any]) -> str:
    """Return the canonical runtime session identifier for this hook process.

    Managed launches provide a trusted identity through ``AGENT_SESSION_ID``.
    Provider payload ids are fallbacks for otherwise-unmanaged sessions.
    """
    managed_session = os.environ.get("AGENT_SESSION_ID", "").strip()
    if managed_session:
        return managed_session
    for key in ("session_id", "sessionId", "session", "conversation_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def session_marker_key(payload: Mapping[str, Any]) -> str:
    """Hash a hook session identifier for privacy-safe marker names."""
    identity = session_id_from_payload(payload)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest() if identity else ""


def iter_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from iter_text_values(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            yield from iter_text_values(nested)


def patch_text_candidates(payload: Mapping[str, Any]) -> list[str]:
    tool_input = payload.get("tool_input", {})
    if isinstance(tool_input, str):
        return [tool_input]
    if not isinstance(tool_input, dict):
        return []

    candidates: list[str] = []
    for key in ("patch", "input", "content", "diff", "text", "command"):
        value = tool_input.get(key)
        if isinstance(value, str):
            candidates.append(value)

    # Some runtimes wrap the raw patch in nested input structures. Keep this
    # as a fallback after known keys so direct values are tested first.
    for value in iter_text_values(tool_input):
        if value not in candidates:
            candidates.append(value)
    return candidates


def apply_patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    prefixes = (
        "*** Add File: ",
        "*** Update File: ",
        "*** Delete File: ",
        "*** Move to: ",
    )
    for line in patch_text.splitlines():
        for prefix in prefixes:
            if line.startswith(prefix):
                path = line[len(prefix) :].strip()
                if path:
                    paths.append(path)
                break
    return paths


def file_paths_from_payload(payload: Mapping[str, Any]) -> list[str]:
    tool_input = payload.get("tool_input", {})
    paths: list[str] = []
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "filename"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
    for candidate in patch_text_candidates(payload):
        paths.extend(apply_patch_paths(candidate))
    return paths


def is_semantic_commit_commit(command: str) -> bool:
    """True for a mutating semantic-commit authoring invocation.

    Dry-run / validate-only / help / non-commit subcommands are excluded so
    message-content gates only fire on commands that actually write a commit.
    Parse argv before classifying operational flags so option values such as
    a message file named ``-h`` or ``--dry-run`` remain data.
    """
    for simple_command in simple_commands_with_nested_shells(command):
        invocation = invocation_tokens(simple_command)
        candidates = [
            invocation,
            *opaque_invocation_candidates(invocation, {"semantic-commit"}),
        ]
        for candidate in candidates:
            if not candidate or PurePosixPath(candidate[0]).name != "semantic-commit":
                continue
            arguments = candidate[1:]
            authors_commit, _writes_files, _repo = semantic_commit_invocation_effects(
                arguments
            )
            if arguments and arguments[0] in {"commit", "default-branch"} and authors_commit:
                return True
    return False


SEMANTIC_COMMIT_VALUE_OPTIONS = frozenset(
    {
        "--body-bullet",
        "--bullet",
        "--expect-head",
        "--format",
        "--max-header-width",
        "--message",
        "--message-file",
        "--message-out",
        "--receipt-out",
        "--repo",
        "--scope",
        "--subject",
        "--summary",
        "--target",
        "--trailer",
        "--type",
    }
)


def semantic_commit_invocation_effects(
    arguments: list[str],
) -> tuple[bool, bool, str]:
    """Return ``(authors_commit, writes_files, repo)`` for an argv tail.

    Operational flags are recognized only after consuming values for every
    supported value-taking option. This prevents a filename such as ``-h`` or
    ``--dry-run`` from masquerading as an inspection flag. A dry-run or
    validate-only invocation that writes ``--message-out`` needs checkout
    writer admission but does not author a commit. Help exits before work.
    """

    if not arguments or arguments[0] not in {
        "commit",
        "fixup",
        "squash",
        "default-branch",
    }:
        return False, False, ""

    help_requested = False
    dry_run = False
    validate_only = False
    writes_message_out = False
    repo = ""
    index = 1
    while index < len(arguments):
        token = arguments[index]
        if token == "--":
            break
        if token in {"-h", "--help"}:
            help_requested = True
            index += 1
            continue
        if token == "--dry-run":
            dry_run = True
            index += 1
            continue
        if token == "--validate-only":
            validate_only = True
            index += 1
            continue

        option = token.split("=", 1)[0] if token.startswith("--") else token
        if option in SEMANTIC_COMMIT_VALUE_OPTIONS:
            attached = token.startswith("--") and "=" in token
            value = token.split("=", 1)[1] if attached else ""
            if not attached and index + 1 < len(arguments):
                value = arguments[index + 1]
            if option == "--message-out":
                writes_message_out = True
            elif option == "--repo" and value:
                repo = value
            index += 1 if attached else 2
            continue
        if token in {"-m", "-F"}:
            index += 2
            continue
        if (token.startswith("-m") or token.startswith("-F")) and len(token) > 2:
            index += 1
            continue
        index += 1

    if help_requested:
        return False, False, repo
    authors_commit = not dry_run and not validate_only
    writes_files = authors_commit or writes_message_out
    return authors_commit, writes_files, repo


def semantic_commit_invocation_state(arguments: list[str]) -> tuple[bool, str]:
    """Return checkout-admission ``(read_only, repo)`` for an argv tail."""
    _authors_commit, writes_files, repo = semantic_commit_invocation_effects(arguments)
    return not writes_files, repo


def main_agent_capability_recovery_argv(words: list[str]) -> bool:
    """Recognize the finite Main Agent lane retained during capability failure."""

    def revision(value: str) -> bool:
        return (
            re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None
            and int(value) <= (2**64 - 1)
        )

    def idempotency_key(value: str) -> bool:
        return re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value) is not None

    if words == ["main-agent", "--version"]:
        return True
    if words in (
        [
            "main-agent",
            "capabilities",
            "--provider",
            "codex",
            "--format",
            "json",
        ],
        [
            "main-agent",
            "capabilities",
            "--provider",
            "claude",
            "--format",
            "json",
        ],
        ["main-agent", "self", "readiness", "--format", "json"],
        ["main-agent", "self", "show", "--format", "json"],
        ["main-agent", "rehydrate", "--format", "json"],
        ["main-agent", "rehydrate", "--format", "markdown"],
        ["main-agent", "status", "--format", "json"],
    ):
        return True
    if words[:3] == ["main-agent", "self", "recover"]:
        return (
            len(words) == 7
            and words[3] == "--idempotency-key"
            and idempotency_key(words[4])
            and words[5:] == ["--format", "json"]
        )
    if words[:2] == ["main-agent", "rebind"]:
        return (
            len(words) == 8
            and words[2] == "--if-revision"
            and revision(words[3])
            and words[4] == "--idempotency-key"
            and idempotency_key(words[5])
            and words[6:] == ["--format", "json"]
        )
    return False


def normalized_cli_argv(
    words: list[str], executable_name: str
) -> list[str] | None:
    """Rewrite one named pinned absolute CLI argv[0] to its bare name.

    Returns ``None`` when argv[0] is not a usable spelling of the requested
    executable. A relative path containing a separator stays rejected: only a
    bare name or an absolute path may be trust-resolved by the caller.
    """
    if not words:
        return None
    executable = words[0]
    if os.path.basename(executable) != executable_name:
        return None
    if "/" in executable and not os.path.isabs(executable):
        return None
    if executable == executable_name:
        return words
    return [executable_name, *words[1:]]


def normalized_main_agent_argv(words: list[str]) -> list[str] | None:
    """Rewrite a pinned absolute ``main-agent`` argv[0] to its bare name."""
    return normalized_cli_argv(words, "main-agent")


def main_agent_preclaim_argv(words: list[str]) -> bool:
    """Recognize exact trusted Main Agent pre-claim shapes without private files."""

    def identifier(value: str) -> bool:
        return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value) is not None

    def idempotency_key(value: str) -> bool:
        return re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value) is not None

    def wait_duration(value: str) -> bool:
        multiplier = 1
        if value[-1:] in {"s", "m", "h", "d"}:
            multiplier = {
                "s": 1,
                "m": 60,
                "h": 3600,
                "d": 86400,
            }[value[-1]]
            value = value[:-1]
        return value.isdigit() and 1 <= int(value) * multiplier <= 60

    # `main-agent worker start` writes the worker prompt with an absolute
    # `main-agent` path so the worker pins the exact launching build. Compare
    # shapes against the bare name so that pinned form is recognised; callers
    # still resolve and trust-check the real executable separately.
    words = normalized_main_agent_argv(words)
    if words is None:
        return False

    if main_agent_capability_recovery_argv(words):
        return True
    if words == ["main-agent", "worker", "list", "--format", "json"]:
        return True
    if words[:2] == ["main-agent", "bootstrap"]:
        return (
            len(words) == 6
            and words[2] == "--idempotency-key"
            and idempotency_key(words[3])
            and words[4:] == ["--format", "json"]
        )
    if words[:3] in (
        ["main-agent", "worker", "diagnose"],
        ["main-agent", "worker", "supervise"],
    ):
        return (
            len(words) == 6
            and identifier(words[3])
            and words[4:] == ["--format", "json"]
        )
    if words[:3] == ["main-agent", "worker", "wait"]:
        if len(words) not in {8, 10}:
            return False
        if words[3] != "--any" and not identifier(words[3]):
            return False
        if words[4] != "--until" or words[5] not in {
            "submitted",
            "blocked",
            "terminal",
        }:
            return False
        if len(words) == 10:
            return (
                words[6] == "--timeout"
                and wait_duration(words[7])
                and words[8:] == ["--format", "json"]
            )
        return words[6:] == ["--format", "json"]
    if words[:3] == ["main-agent", "worker", "show"]:
        return (
            len(words) == 6
            and identifier(words[3])
            and words[4:] == ["--format", "json"]
        )
    return False


def extract_message(command: str) -> str | None:
    """Best-effort recovery of the commit message from a semantic-commit command.

    Handles `--message`/`-m` passed as a `$(cat <<TAG ...)` HEREDOC, a
    double-quoted string (with common escapes), or a single-quoted string.
    Returns None when no message argument can be parsed.
    """
    heredoc_re = re.compile(
        r"""(?:--message|-m)
            \s+
            ["']?
            \$\(
            \s*cat\s*<<(?P<dash>-)?
            \s*
            (?P<q>['"])?
            (?P<tag>\w+)
            (?P=q)?
            \s*\n
            (?P<body>.*?)
            \n
            (?P<leading>[ \t]*)
            (?P=tag)
            \s*
            \n?
            \s*\)
            ["']?""",
        re.DOTALL | re.VERBOSE,
    )
    match = heredoc_re.search(command)
    if match:
        return match.group("body")

    double_quoted_re = re.compile(r'(?:--message|-m)\s+"((?:\\.|[^"\\])*)"', re.DOTALL)
    match = double_quoted_re.search(command)
    if match:
        return _unescape_double_quoted(match.group(1))

    single_quoted_re = re.compile(r"(?:--message|-m)\s+'([^']*)'", re.DOTALL)
    match = single_quoted_re.search(command)
    if match:
        return match.group(1)

    return None


def _unescape_double_quoted(raw: str) -> str:
    """Undo the common backslash escapes inside a double-quoted shell string."""
    return (
        raw.replace("\\\\", "\x00")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\x00", "\\")
    )


def iter_flag_values(command: str, *flags: str) -> list[str]:
    """Recover every value passed to any of `flags` in a shell command.

    Recognizes `--flag value` and `--flag=value`, where the value is a
    single-quoted string, a double-quoted string (with common escapes), or a
    bare unquoted token. Best-effort guardrail parsing, not a real shell, so
    flag names are matched only when followed by `=` or whitespace.
    """
    values: list[str] = []
    for flag in flags:
        pattern = re.compile(
            re.escape(flag)
            + r"""(?:=|\s+)(?:'(?P<sq>[^']*)'|"(?P<dq>(?:\\.|[^"\\])*)"|(?P<bare>[^\s'"]\S*))"""
        )
        for match in pattern.finditer(command):
            if match.group("sq") is not None:
                values.append(match.group("sq"))
            elif match.group("dq") is not None:
                values.append(_unescape_double_quoted(match.group("dq")))
            elif match.group("bare") is not None:
                values.append(match.group("bare"))
    return values


def read_message_file(command: str, *, max_bytes: int = 65536) -> str | None:
    """Best-effort read of a `--message-file` argument's contents.

    Returns the file text (capped at `max_bytes`) for the first readable
    `--message-file` path, or None when no path parses or can be read.
    """
    for path in iter_flag_values(command, "--message-file"):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                return handle.read(max_bytes)
        except OSError:
            continue
    return None


# --- agent-docs finish-line validation gate helpers ---------------------------
#
# Shared by the PreToolUse recorder (finish-line-record.py) and the Stop gate
# (stop-finish-line-gate.py). The recorder writes evidence markers under each
# declared validation marker directory; the gate reads them to decide whether
# every declared validation contract has run since code was last edited.


def git_toplevel(cwd: str | None = None) -> str | None:
    """Return the git work-tree root for `cwd` (or the process cwd), else None."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if completed.returncode != 0:
        return None
    top = completed.stdout.strip()
    return top or None


GIT_RECOVERY_SUBCOMMANDS = frozenset(
    {"rebase", "merge", "cherry-pick", "revert", "am"}
)
GIT_RECOVERY_FLAGS = frozenset({"--abort", "--quit"})
_GIT_OPTIONS_WITH_VALUES = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
)


def is_git_recovery_argv(argv: list[str]) -> bool:
    """Whether ``argv`` is a single ``git <op> --abort|--quit`` recovery command.

    Recovery commands (`--abort`, `--quit`) restore the pre-operation state and
    author no new content, so both checkout guards admit them even without a
    lease or active project-dev: otherwise a stuck mid-operation checkout cannot
    be aborted to recover in place. ``--continue`` / ``--skip`` advance the
    operation (they author content) and are intentionally excluded. Global
    ``git`` options that take a value (`-C`, `-c`, `--git-dir`, …) are skipped so
    `git -C repo rebase --abort` is still recognized.
    """
    if not argv or os.path.basename(argv[0]) != "git":
        return False
    index = 1
    while index < len(argv):
        token = argv[index]
        if token in _GIT_OPTIONS_WITH_VALUES:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    if index >= len(argv) or argv[index] not in GIT_RECOVERY_SUBCOMMANDS:
        return False
    return any(argument in GIT_RECOVERY_FLAGS for argument in argv[index + 1 :])


def _runtime_cache_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".cache", "agent-runtime-kit")


def _is_runtime_kit_source_checkout(repo_root: str | None) -> bool:
    if not repo_root:
        return False
    required_files = (
        "AGENT_DOCS.toml",
        "AGENT_HOME.md",
        os.path.join("manifests", "skills.yaml"),
        os.path.join("scripts", "sync-runtime-surfaces.sh"),
    )
    required_dirs = (os.path.join("core", "policies"),)
    return all(
        os.path.isfile(os.path.join(repo_root, path)) for path in required_files
    ) and all(os.path.isdir(os.path.join(repo_root, path)) for path in required_dirs)


def _docs_home(repo_root: str | None = None) -> str | None:
    docs_home = os.environ.get("AGENT_RUNTIME_DOCS_HOME") or os.environ.get(
        "AGENT_DOCS_HOME"
    )
    if docs_home:
        return docs_home
    if _is_runtime_kit_source_checkout(repo_root):
        return repo_root
    return None


def _runtime_product() -> str | None:
    product = os.environ.get("AGENT_RUNTIME_PRODUCT", "").strip()
    return product if product in {"codex", "claude"} else None


def validation_tombstone_dir(repo_root: str, session_key: str = "") -> str:
    """Return shared runtime state for fail-closed validation attempts."""
    override = (
        os.environ.get("AGENT_RUNTIME_VALIDATION_STATE_HOME", "").strip()
        or os.environ.get("AGENT_RUNTIME_STATE_HOME", "").strip()
    )
    if override:
        state_root = os.path.realpath(os.path.expanduser(override))
    else:
        xdg_state = os.environ.get("XDG_STATE_HOME", "").strip()
        if not xdg_state:
            xdg_state = os.path.join(os.path.expanduser("~"), ".local", "state")
        state_root = os.path.realpath(
            os.path.join(os.path.expanduser(xdg_state), "agent-runtime-kit")
        )
    repo_key = hashlib.sha256(os.path.realpath(repo_root).encode("utf-8")).hexdigest()
    directory = os.path.join(state_root, "validation-outcomes", repo_key)
    if session_key:
        if re.fullmatch(r"[0-9a-f]{64}", session_key) is None:
            raise ValueError("invalid validation session key")
        directory = os.path.join(
            directory, "sessions", f"session-{session_key}"
        )
    return directory


def acquire_validation_state_lock(repo_root: str):
    """Serialize validation state transitions for one repository."""
    directory = validation_tombstone_dir(repo_root)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, ".agent-runtime-validation.lock")
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError("validation state lock is not a regular file")
        handle = os.fdopen(descriptor, "a+", encoding="utf-8")
        descriptor = -1
        fcntl.flock(handle, fcntl.LOCK_EX)
        return handle
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _agent_docs_base_args(repo_root: str) -> list[str]:
    docs_home = _docs_home(repo_root)
    args = ["agent-docs"]
    if docs_home:
        args += ["--docs-home", docs_home]
    args += ["--project-path", repo_root]
    return args


def _agent_docs_fingerprint() -> str:
    """A cheap identity of the installed ``agent-docs`` binary for cache keying.

    Resolved validation contracts depend on the binary's probed capabilities
    (``--product`` / ``--require-declared-intent`` support), which change across
    CLI upgrades without touching ``AGENT_DOCS.toml``. Folding the resolved
    executable path, size, and mtime into the contract cache key invalidates the
    cache after such an upgrade, so a stale unfiltered fallback contract is not
    served once the host learns to filter by product. Uses only ``which`` plus a
    ``stat`` (no subprocess) so the recorder stays cheap on every tool call;
    returns ``""`` when the binary cannot be resolved.
    """
    executable = shutil.which("agent-docs")
    if not executable:
        return ""
    try:
        stat = os.stat(executable)
    except OSError:
        return executable
    return f"{executable}:{stat.st_size}:{stat.st_mtime_ns}"


def _agent_docs_json(args: list[str]) -> dict[str, Any] | None:
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, check=False, timeout=15
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        data = json.loads(completed.stdout)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _agent_docs_supports_declared_intent_guard(repo_root: str) -> bool:
    try:
        completed = subprocess.run(
            _agent_docs_base_args(repo_root) + ["preflight", "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return (
        completed.returncode == 0
        and "--require-declared-intent" in completed.stdout
    )


def _agent_docs_product_args(repo_root: str) -> list[str]:
    product = _runtime_product()
    if product is None:
        return []
    try:
        completed = subprocess.run(
            _agent_docs_base_args(repo_root) + ["preflight", "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0 or "--product" not in completed.stdout:
        return []
    return ["--product", product]


def _validation_marker_default(context: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", context.strip()).strip(".-")
    if not safe:
        safe = "validation"
    return f".cache/agent-validation/{safe}.ok"


def _contract_from_explain(
    data: dict[str, Any] | None, intent: str
) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    validation = data.get("validation") if isinstance(data, dict) else None
    if not isinstance(validation, dict) or not validation.get("declared"):
        return None
    commands = [
        command
        for command in (validation.get("commands") or [])
        if isinstance(command, str) and command.strip()
    ]
    if not commands:
        return None
    context = validation.get("context") or data.get("intent") or intent
    if not isinstance(context, str) or not context.strip():
        context = intent
    marker = validation.get("marker")
    if not isinstance(marker, str) or not marker.strip():
        marker = _validation_marker_default(context)
    return {"context": context.strip(), "commands": commands, "marker": marker.strip()}


def _declared_intents(repo_root: str) -> list[str]:
    data = _agent_docs_json(
        _agent_docs_base_args(repo_root) + ["list", "--format", "json"]
    )
    raw_intents = data.get("intents") if isinstance(data, dict) else None
    intents: list[str] = []
    if isinstance(raw_intents, list):
        for intent in raw_intents:
            if isinstance(intent, str) and intent.strip() and intent not in intents:
                intents.append(intent.strip())
    return intents or ["project-dev"]


def _resolve_validation_contracts(repo_root: str) -> list[dict[str, Any]]:
    """Resolve every declared validation contract via `agent-docs`."""
    contracts: list[dict[str, Any]] = []
    guard_args = (
        ["--require-declared-intent"]
        if _agent_docs_supports_declared_intent_guard(repo_root)
        else []
    )
    product_args = _agent_docs_product_args(repo_root)
    for intent in _declared_intents(repo_root):
        data = _agent_docs_json(
            _agent_docs_base_args(repo_root)
            + [
                "preflight",
                "--intent",
                intent,
                *guard_args,
                *product_args,
                "--format",
                "json",
            ]
        )
        contract = _contract_from_explain(data, intent)
        if not contract:
            continue
        if any(existing.get("context") == contract["context"] for existing in contracts):
            continue
        contracts.append(contract)
    return contracts


def validation_contracts(repo_root: str) -> list[dict[str, Any]]:
    """The repo's declared validation contracts, or an empty list.

    Returns one ``{"context": "...", "commands": [...], "marker": "..."}``
    record per declared intent whose validation contract contains at least one
    command. The agent-docs result is cached per repo and docs-home, keyed on
    the catalog's mtime, the runtime product, and a fingerprint of the
    ``agent-docs`` binary (so a CLI upgrade that changes product filtering
    invalidates the cache), letting the recorder run on every tool call cheaply.
    """
    catalog = os.path.join(repo_root, "AGENT_DOCS.toml")
    if not os.path.isfile(catalog):
        return []
    try:
        catalog_mtime = os.path.getmtime(catalog)
    except OSError:
        catalog_mtime = 0.0

    docs_home = _docs_home(repo_root)
    product = _runtime_product()
    agent_docs_fingerprint = _agent_docs_fingerprint()
    cache_key = "\0".join(
        [repo_root, docs_home or "", product or "", agent_docs_fingerprint]
    )
    digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()[:16]
    cache_path = os.path.join(_runtime_cache_dir(), f"contract-{digest}.json")
    try:
        with open(cache_path, encoding="utf-8") as handle:
            cached = json.load(handle)
        if (
            isinstance(cached, dict)
            and cached.get("catalog_mtime") == catalog_mtime
            and cached.get("docs_home") == docs_home
            and cached.get("product") == product
            and cached.get("agent_docs_fingerprint") == agent_docs_fingerprint
        ):
            contracts = cached.get("contracts")
            if isinstance(contracts, list):
                return [
                    contract
                    for contract in contracts
                    if isinstance(contract, dict)
                    and isinstance(contract.get("context"), str)
                    and isinstance(contract.get("commands"), list)
                    and isinstance(contract.get("marker"), str)
                ]
    except (OSError, ValueError):
        pass

    contracts = _resolve_validation_contracts(repo_root)
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "catalog_mtime": catalog_mtime,
                    "docs_home": docs_home,
                    "product": product,
                    "agent_docs_fingerprint": agent_docs_fingerprint,
                    "contracts": contracts,
                },
                handle,
            )
    except OSError:
        pass
    return contracts


def project_dev_validation_contract(repo_root: str) -> dict[str, Any] | None:
    """The repo's project-dev validation contract, or None when none applies."""
    for contract in validation_contracts(repo_root):
        if contract.get("context") == "project-dev":
            return contract
    return None


def validation_marker_set(
    repo_root: str, marker: str, *, session_key: str = ""
) -> dict[str, str]:
    """Derive marker file paths for a repo from the contract `marker`.

    Identified sessions receive an opaque session namespace. Within that
    namespace the dirty marker remains shared across products, while command
    outcome markers are also product-scoped. Payloads without a session keep
    the legacy shared paths. Marker paths must be repository-relative and their
    directory must remain beneath the real repository root through every
    existing symlink component. Final marker names are atomically replaced
    rather than followed.
    """
    rel = marker.strip()
    if not rel or os.path.isabs(rel):
        raise ValueError("validation marker must be repository-relative")
    root = os.path.realpath(repo_root)
    raw_target = os.path.join(root, rel)
    lexical_target = os.path.abspath(raw_target)
    if lexical_target == root:
        raise ValueError("validation marker resolves to repository root")
    target_name = os.path.basename(lexical_target)
    if target_name in {"", ".", ".."}:
        raise ValueError("validation marker must name a file")
    resolved_parent = os.path.realpath(os.path.dirname(raw_target))
    resolved_target = os.path.join(resolved_parent, target_name)
    try:
        if os.path.commonpath((root, lexical_target)) != root:
            raise ValueError("validation marker escapes repository")
        if os.path.commonpath((root, resolved_parent)) != root:
            raise ValueError("validation marker directory escapes repository")
        if os.path.commonpath((root, resolved_target)) != root:
            raise ValueError("validation marker target escapes repository")
    except ValueError as error:
        raise ValueError("unsafe validation marker") from error
    stem = os.path.splitext(os.path.basename(resolved_target))[0] or "project-dev"
    abs_dir = os.path.dirname(resolved_target)
    relative_identity = os.path.relpath(lexical_target, root).replace(os.sep, "/")
    contract_key = hashlib.sha256(relative_identity.encode("utf-8")).hexdigest()
    if session_key and re.fullmatch(r"[0-9a-f]{64}", session_key) is None:
        raise ValueError("invalid validation session key")
    product = _runtime_product()
    target_stem = f"{stem}.{product}" if product else stem
    command_stem = target_stem
    marker_dir = abs_dir
    if session_key:
        marker_dir = os.path.join(abs_dir, f"session-{session_key}")
        if os.path.lexists(marker_dir):
            metadata = os.lstat(marker_dir)
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(
                metadata.st_mode
            ):
                raise ValueError("unsafe validation session directory")
            try:
                if os.path.commonpath((root, os.path.realpath(marker_dir))) != root:
                    raise ValueError("validation session directory escapes repository")
            except ValueError as error:
                raise ValueError("unsafe validation session directory") from error
    return {
        "dir": marker_dir,
        "lock_dir": abs_dir,
        "ok": resolved_target,
        "dirty": os.path.join(marker_dir, f"{stem}.dirty"),
        "legacy_dirty": os.path.join(abs_dir, f"{stem}.dirty"),
        "terminal": os.path.join(
            marker_dir, f".terminal-{product or 'shared'}"
        ),
        "stem": stem,
        "command_stem": command_stem,
        "target_stem": target_stem,
        "contract_key": contract_key,
        "product": product or "shared",
        "session_key": session_key,
    }


def command_ran_marker(marker_set: Mapping[str, str], index: int) -> str:
    stem = marker_set.get("command_stem") or marker_set["stem"]
    return os.path.join(marker_set["dir"], f"{stem}.cmd{index}.ran")


def validation_command_target_key(
    marker_set: Mapping[str, str], index: int, declared: str
) -> str:
    """Stable logical identity for one product-scoped declared command."""
    identity = (
        f"{marker_set['contract_key']}\0"
        f"{marker_set.get('target_stem') or marker_set['stem']}\0"
        f"{index}\0{declared.strip()}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def command_failed_marker(marker_set: Mapping[str, str], index: int) -> str:
    stem = marker_set.get("command_stem") or marker_set["stem"]
    return os.path.join(marker_set["dir"], f"{stem}.cmd{index}.failed.json")


def routing_review_marker(marker_set: Mapping[str, str]) -> str:
    stem = marker_set.get("command_stem") or marker_set["stem"]
    return os.path.join(marker_set["dir"], f"{stem}.routing-reviewed")


def validation_pending_marker(
    marker_set: Mapping[str, str], token: str
) -> str:
    stem = marker_set.get("command_stem") or marker_set["stem"]
    return os.path.join(marker_set["dir"], f"{stem}.pending.{token}.json")


VALIDATION_WAIVER_SCHEMA = "agent-runtime-validation.waiver.v1"
VALIDATION_WAIVER_MAX_BYTES = 8 * 1024
VALIDATION_WAIVER_MAX_REASON_CHARS = 500


def validation_waiver_marker(marker_set: Mapping[str, str]) -> str:
    """Path of the structured waiver for one product-scoped contract."""
    stem = marker_set.get("command_stem") or marker_set["stem"]
    return os.path.join(marker_set["dir"], f"{stem}.waiver.json")


def validation_edit_generation(marker_set: Mapping[str, str]) -> int:
    """The contract's current edit generation.

    The dirty marker is re-touched on every recorded edit, so its modification
    time in nanoseconds is an exact, integral generation counter. A waiver binds
    to this value, which is what makes it expire when the next edit lands —
    unlike the ambient `AGENT_RUNTIME_VALIDATION_WAIVER` environment variable,
    which stays true for every later Stop in the process.

    A contract with no dirty marker reports generation ``0``; a waiver recorded
    then still expires as soon as an edit creates the marker.
    """
    try:
        metadata = os.stat(marker_set["dirty"], follow_symlinks=False)
    except OSError:
        return 0
    if not stat.S_ISREG(metadata.st_mode):
        return 0
    return metadata.st_mtime_ns


def read_validation_waiver(
    marker_set: Mapping[str, str], repo_root: str
) -> dict[str, Any] | None:
    """The structured waiver that currently applies, or ``None``.

    Fails closed on every mismatch. A waiver is only honored when it is a small
    private regular file, declares the exact schema, carries a non-empty bounded
    reason, and binds to this repository, contract, product, session, and the
    contract's *current* edit generation.
    """
    path = validation_waiver_marker(marker_set)
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    if metadata.st_size > VALIDATION_WAIVER_MAX_BYTES:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(body, dict):
        return None
    if body.get("schema_version") != VALIDATION_WAIVER_SCHEMA:
        return None
    reason = body.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return None
    if len(reason) > VALIDATION_WAIVER_MAX_REASON_CHARS:
        return None
    if body.get("repository") != os.path.realpath(repo_root):
        return None
    for field in ("contract_key", "target_stem", "product", "session_key"):
        if body.get(field) != marker_set.get(field, ""):
            return None
    generation = body.get("edit_generation_ns")
    if not isinstance(generation, int) or isinstance(generation, bool):
        return None
    if generation != validation_edit_generation(marker_set):
        return None
    return body


SHELL_SEPARATOR_TOKENS = {";", "&&", "||", "|", "(", ")"}
SHELL_CONTROL_PREFIX_TOKENS = frozenset(
    {"!", "if", "then", "elif", "else", "while", "until", "do", "{"}
)
SHELL_CONTROL_TERMINATOR_TOKENS = frozenset({"fi", "done", "}"})
CLOBBER_REDIRECT_MARKER = "__AGENT_CLOBBER_REDIRECT__"

SHELL_EFFECT_READ_ONLY = "read-only"
SHELL_EFFECT_MUTATION = "mutation"
SHELL_EFFECT_UNKNOWN = "unknown"

# Commands with no argument-driven write or command-execution mode. Trust in the
# resolved executable remains a caller-owned decision because the pre-edit and
# coordination hooks have different host boundaries.
AUDITED_READ_ONLY_EXECUTABLES = frozenset(
    {
        "pwd",
        "echo",
        "cat",
        "tac",
        "head",
        "tail",
        "wc",
        "nl",
        "grep",
        "egrep",
        "fgrep",
        "ls",
        "stat",
        "cmp",
        "comm",
        "basename",
        "dirname",
        "realpath",
        "readlink",
        "which",
        "printenv",
        "id",
        "whoami",
        "uname",
        "true",
        "false",
    }
)

PIPELINE_UNQUOTED_CONTROL = frozenset(";&<>`$(){}#*?[]^~\n\r")
PIPELINE_DOUBLE_QUOTED_CONTROL = frozenset("`$")
SED_PRINT_SCRIPT_RE = re.compile(r"^(?:[0-9]+|\$)(?:,(?:[0-9]+|\$))?p$")


class ShellEffect(NamedTuple):
    kind: str
    reason: str


def pipe_only_commands(command: str) -> list[list[str]] | None:
    """Parse one simple command or a pipeline containing only audited `|` edges.

    Any other active shell control, expansion, empty stage, or malformed quoting
    fails closed. Quoted pipes remain ordinary argv content. The returned argv
    stages are syntactic only; callers still own executable trust and per-command
    argument audits.
    """
    if not command.strip():
        return None
    segments: list[str] = []
    current: list[str] = []
    quote = ""
    escaped = False
    index = 0
    while index < len(command):
        character = command[index]
        if quote == "'":
            current.append(character)
            if character == "'":
                quote = ""
            index += 1
            continue
        if escaped:
            current.append(character)
            escaped = False
            index += 1
            continue
        if character == "\\":
            current.append(character)
            escaped = True
            index += 1
            continue
        if quote == '"':
            if character in PIPELINE_DOUBLE_QUOTED_CONTROL:
                return None
            current.append(character)
            if character == '"':
                quote = ""
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            current.append(character)
            index += 1
            continue
        if character == "|":
            if index + 1 < len(command) and command[index + 1] == "|":
                return None
            segment = "".join(current).strip()
            if not segment:
                return None
            segments.append(segment)
            current = []
            index += 1
            continue
        if character in PIPELINE_UNQUOTED_CONTROL:
            return None
        current.append(character)
        index += 1
    if quote or escaped:
        return None
    segment = "".join(current).strip()
    if not segment:
        return None
    segments.append(segment)
    commands: list[list[str]] = []
    for segment in segments:
        try:
            words = shlex.split(segment, posix=True)
        except ValueError:
            return None
        if not words:
            return None
        commands.append(words)
    return commands


def ripgrep_read_only_invocation(arguments: list[str]) -> bool:
    """Admit ripgrep only when every command-execution mode is disabled."""
    no_config = False
    for argument in arguments:
        if argument == "--":
            break
        if argument == "--no-config":
            no_config = True
        if argument in {"--pre", "--hostname-bin", "--search-zip"}:
            return False
        if argument.startswith(("--pre=", "--hostname-bin=")):
            return False
        if (
            argument.startswith("-")
            and not argument.startswith("--")
            and "z" in argument[1:]
        ):
            return False
    return no_config


def sed_print_only_invocation(arguments: list[str]) -> bool:
    """Admit only `sed -n '<literal line range>p' [files...]` reads.

    General sed scripts can write files or execute commands even without `-i`.
    This narrow grammar covers line-range inspection without interpreting sed's
    command language.
    """
    index = 0
    quiet = False
    while index < len(arguments):
        argument = arguments[index]
        if argument in {"-n", "--quiet", "--silent"}:
            quiet = True
            index += 1
            continue
        if argument == "--":
            index += 1
        break
    if not quiet or index >= len(arguments):
        return False
    script = arguments[index]
    index += 1
    if not SED_PRINT_SCRIPT_RE.fullmatch(script):
        return False
    return not any(argument.startswith("-") for argument in arguments[index:])


def audited_text_read_invocation(words: list[str]) -> bool:
    """Whether argv has an audited text-inspection shape, excluding trust."""
    if not words:
        return False
    executable = os.path.basename(words[0])
    arguments = words[1:]
    if executable in AUDITED_READ_ONLY_EXECUTABLES:
        return True
    if executable == "rg":
        return ripgrep_read_only_invocation(arguments)
    if executable == "sed":
        return sed_print_only_invocation(arguments)
    return False


def classify_shell_effect(
    command: str,
    *,
    read_only_invocation: Callable[[list[str]], bool],
    mutation_invocation: Callable[[list[str]], bool] | None = None,
) -> ShellEffect:
    """Classify a shell command without conflating unknown with mutation.

    Read-only admission is deliberately narrower than the best-effort mutation
    scan: every pipe stage must be an audited read. A caller-supplied mutation
    classifier may recognize explicit writes across the broader shared shell
    grammar. Everything else remains unknown so advisory and enforcing callers
    can apply different policies without weakening a fail-closed gate.
    """
    pipeline = pipe_only_commands(command)
    if pipeline is not None and all(read_only_invocation(words) for words in pipeline):
        return ShellEffect(SHELL_EFFECT_READ_ONLY, "audited-read-only")
    if mutation_invocation is not None and any(
        mutation_invocation(tokens)
        for tokens in simple_commands_with_nested_shells(command)
    ):
        return ShellEffect(SHELL_EFFECT_MUTATION, "recognized-mutation")
    return ShellEffect(SHELL_EFFECT_UNKNOWN, "unclassified-shell-effect")


def _shield_clobber_redirects(command: str) -> str:
    """Keep Bash `>|` clobber redirects from being tokenized as pipelines."""
    out: list[str] = []
    quote = None
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if quote == "'":
            out.append(char)
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if char == "\\" and index + 1 < length:
                out.append(char)
                out.append(command[index + 1])
                index += 2
                continue
            out.append(char)
            if char == '"':
                quote = None
            index += 1
            continue
        if char == "\\" and index + 1 < length:
            out.append(char)
            out.append(command[index + 1])
            index += 2
            continue
        if char in {"'", '"'}:
            quote = char
            out.append(char)
            index += 1
            continue
        if command.startswith(">|", index):
            out.append(f">{CLOBBER_REDIRECT_MARKER}")
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def shell_tokens(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(
            _shield_clobber_redirects(command), posix=True, punctuation_chars=";&|()"
        )
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return []


def is_shell_separator(token: str) -> bool:
    return token in SHELL_SEPARATOR_TOKENS or bool(token) and all(
        char in ";&|()" for char in token
    )


def normalize_command_separators(command: str) -> str:
    """Replace unquoted newlines with `;` so multi-line commands split.

    `shell_tokens` runs `shlex` with `whitespace_split`, which treats a newline
    as ordinary whitespace rather than a command boundary. Without this, a
    common multi-line invocation such as::

        cd /repo
        bash scripts/ci/all.sh && bash tests/hooks/run.sh

    collapses `cd` and the next line's command into one simple command whose
    command-position token is `cd`, so the real command is never recognized.

    Single-quoted spans are preserved verbatim. A backslash escapes the
    following character, except a backslash-LF line continuation — which bash
    removes both when unquoted and inside double quotes — so it is dropped
    entirely and the logical line continues without leaving a stray newline
    token (or a split quoted subcommand) that would hide the real command from
    the guards. A backslash-CR is not a continuation in bash, so it is left
    intact (and a following unquoted LF still acts as a separator).
    """
    out: list[str] = []
    quote = None  # active quote char ("'" or '"'), or None when unquoted
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if quote == "'":
            out.append(char)
            if char == "'":
                quote = None
            index += 1
        elif quote == '"':
            if char == "\\" and index + 1 < length:
                nxt = command[index + 1]
                if nxt == "\n":
                    # Bash removes a backslash-LF line continuation inside double
                    # quotes too, so `"com\<newline>mit"` is the word `commit`.
                    # Drop both so a quoted subcommand is not hidden behind an
                    # embedded newline token (guard bypass).
                    index += 2
                    continue
                out.append(char)
                out.append(nxt)
                index += 2
                continue
            out.append(char)
            if char == '"':
                quote = None
            index += 1
        elif char == "\\" and index + 1 < length:
            nxt = command[index + 1]
            if nxt == "\n":
                # Shell line continuation (backslash-LF): removed entirely so the
                # logical line continues without leaving a stray newline token
                # between an executable and its subcommand (`git \<newline> commit`).
                index += 2
            else:
                # Any other escaped char keeps both chars. A lone CR is NOT a
                # continuation in bash (`\<CR>` escapes the CR; a following LF
                # still separates), so dropping it would false-block
                # `git \<CR><LF> commit`, which bash does not run as a commit.
                out.append(char)
                out.append(nxt)
                index += 2
        elif char in ("'", '"'):
            quote = char
            out.append(char)
            index += 1
        elif char in ("\n", "\r"):
            out.append(";")
            index += 1
        else:
            out.append(char)
            index += 1
    return "".join(out)


def _parse_heredoc_delimiter(line: str, index: int) -> tuple[str, int, bool]:
    """Read a here-doc delimiter word starting at ``index``.

    Returns the *unquoted* delimiter (the form bash compares the closing line
    against) and the index just past it. Quotes and backslash escapes around the
    delimiter are stripped, matching bash.
    """
    out: list[str] = []
    quoted = False
    length = len(line)
    while index < length:
        char = line[index]
        if char in (" ", "\t", "<", ">", "|", "&", ";", "(", ")"):
            break
        if char == "$" and index + 1 < length and line[index + 1] in ("'", '"'):
            quoted = True
            quote = line[index + 1]
            index += 2
            while index < length and line[index] != quote:
                if quote == "'" and line[index] == "\\" and index + 1 < length:
                    out.append(line[index + 1])
                    index += 2
                    continue
                out.append(line[index])
                index += 1
            index += 1  # skip closing quote
            continue
        if char in ("'", '"'):
            quoted = True
            quote = char
            index += 1
            while index < length and line[index] != quote:
                out.append(line[index])
                index += 1
            index += 1  # skip closing quote
            continue
        if char == "\\" and index + 1 < length:
            quoted = True
            out.append(line[index + 1])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out), index, quoted


SHELL_HEREDOC_EXECUTORS = {"bash", "sh", "dash", "ksh", "zsh"}


def _starts_shell_comment(line: str, index: int) -> bool:
    return index == 0 or line[index - 1] in " \t;&|()"


def _line_has_unquoted_continuation(line: str) -> bool:
    run = len(line) - len(line.rstrip("\\"))
    if run == 0 or run % 2 == 0:
        return False

    quote: str | None = None
    index = 0
    stop = len(line) - run
    while index < stop:
        char = line[index]
        if quote == "'":
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if char == "\\" and index + 1 < stop:
                index += 2
                continue
            if char == '"':
                quote = None
            index += 1
            continue
        if char == "\\" and index + 1 < stop:
            index += 2
            continue
        if char in ("'", '"'):
            quote = char
        index += 1
    return quote != "'"


def _simple_command_spanning(line: str, op_start: int) -> list[str]:
    """Tokens of the simple command containing the redirection at ``op_start``.

    Unlike a prefix-only scan, this also keeps operands and redirections that
    appear AFTER the here-doc operator, so a trailing script-file operand
    (``bash <<EOF ./script.sh``) or a later input redirection stays visible when
    deciding whether the body is the shell's executed script. Splitting exactly
    at ``op_start`` keeps any fd prefix glued to its operator as one token.
    """
    before: list[str] = []
    for token in shell_tokens(line[:op_start]):
        if is_shell_separator(token):
            before = []
            continue
        before.append(token)
    after: list[str] = []
    for token in shell_tokens(line[op_start:]):
        if is_shell_separator(token):
            break
        after.append(token)
    return before + after


# A token that begins a redirection: optional fd digits then an operator. The
# `&>` / `&>>` arms only fire on raw text; `shell_tokens` (shlex with `&` in
# `punctuation_chars`) splits an `&`-redirection into separate tokens, so a
# tokenized operand never reaches the walk starting with `&`.
_CLOBBER_REDIRECT_RE = re.escape(CLOBBER_REDIRECT_MARKER)
_REDIRECT_TOKEN_RE = re.compile(
    rf"^(?:\d*(?:<<<|<<-?|<>|<&|>{_CLOBBER_REDIRECT_RE}|>>|>&|<|>)|&>>|&>)"
)

# Bash invocation options that always bind the FOLLOWING word as an argument.
# When the next token is instead a redirection or here-doc operator, bash never
# reads it as the argument and aborts with "option requires an argument", so the
# here-doc body is never executed.
_OPTIONS_TAKING_WORD_ARG = {"--init-file", "--rcfile"}

# Bash invocation options that print metadata/help/usage or abort before reading
# stdin. The here-doc body is data for these commands, not script text.
_BASH_EXIT_BEFORE_STDIN_LONG_OPTIONS = {"--version", "--help", "--usage"}

# zsh GNU-style `--option-name` invocation options that are valid AND still read
# and run stdin as the script (verified against zsh 5.9). They only toggle
# startup-file loading. Every OTHER zsh long option is excluded on purpose:
# `--noexec`/`--no-exec` parse but do not run the body, `--version`/`--help`
# exit before stdin, `--emulate <mode>` needs a word argument, and an unknown
# name aborts zsh with "no such option" — crediting any of those would be a
# false validation credit. An unlisted-but-valid option is a safe false
# negative, so keep this allowlist tight.
_ZSH_STDIN_SCRIPT_LONG_OPTIONS = {
    "--rcs",
    "--no-rcs",
    "--globalrcs",
    "--no-globalrcs",
}

# Bash's invocation-level -O/+O is special: with no shopt name, it lists shopt
# state and continues to read stdin. With an unknown shopt name, it aborts before
# executing stdin. Keep this list conservative; an unlisted future shopt option
# becomes a false negative rather than an unsafe gate credit.
_BASH_SHOPT_OPTIONS = {
    "assoc_expand_once",
    "autocd",
    "cdable_vars",
    "cdspell",
    "checkhash",
    "checkjobs",
    "checkwinsize",
    "cmdhist",
    "compat31",
    "compat32",
    "compat40",
    "compat41",
    "compat42",
    "compat43",
    "compat44",
    "complete_fullquote",
    "direxpand",
    "dirspell",
    "dotglob",
    "execfail",
    "expand_aliases",
    "extdebug",
    "extglob",
    "extquote",
    "failglob",
    "force_fignore",
    "globasciiranges",
    "globskipdots",
    "globstar",
    "gnu_errfmt",
    "histappend",
    "histreedit",
    "histverify",
    "hostcomplete",
    "huponexit",
    "inherit_errexit",
    "interactive_comments",
    "lastpipe",
    "lithist",
    "localvar_inherit",
    "localvar_unset",
    "login_shell",
    "mailwarn",
    "no_empty_cmd_completion",
    "nocaseglob",
    "nocasematch",
    "noexpand_translation",
    "nullglob",
    "patsub_replacement",
    "progcomp",
    "progcomp_alias",
    "promptvars",
    "restricted_shell",
    "shift_verbose",
    "sourcepath",
    "varredir_close",
    "xpg_echo",
}
_BASH_SHOPT_OPTION_FLAGS = {"-O", "+O"}


def _bash_exits_before_stdin_long_option(token: str) -> bool:
    """Return true for exact and value-suffixed Bash metadata options."""
    option, _, _ = token.partition("=")
    return option in _BASH_EXIT_BEFORE_STDIN_LONG_OPTIONS


def _redirect_consumes_next(token: str) -> bool:
    """True when a redirection operator token carries no attached target word.

    ``<`` / ``<<`` / ``>`` written with a following space take the next token as
    their target (or here-doc delimiter), so that token must be skipped rather
    than mistaken for a script-file operand.
    """
    match = _REDIRECT_TOKEN_RE.match(token)
    return bool(match) and token[match.end() :] == ""


def _skip_redirections(invocation: list[str], cursor: int) -> int:
    """Return the next token index after any redirections at ``cursor``."""
    while cursor < len(invocation) and _REDIRECT_TOKEN_RE.match(invocation[cursor]):
        cursor += 2 if _redirect_consumes_next(invocation[cursor]) else 1
    return cursor


def invocation_without_redirections(invocation: list[str]) -> list[str]:
    """Return ``invocation`` with redirection operators and their operands removed.

    A simple command's tokens can carry redirections (``2>/dev/null``,
    ``< /dev/null``, ``>| file``) that the shell consumes before the executable
    runs. Callers that inspect an invocation's executable and real arguments —
    for example when selecting a single positional target — must not mistake a
    redirection operand for an argument. Reuses the same redirection grammar as
    ``_skip_redirections``.
    """
    result: list[str] = []
    index = 0
    while index < len(invocation):
        token = invocation[index]
        if _REDIRECT_TOKEN_RE.match(token):
            index += 2 if _redirect_consumes_next(token) else 1
            continue
        result.append(token)
        index += 1
    return result


# A token that begins an stdin/input redirection: optional fd digits then an
# input operator. Output operators (`>`, `>>`, `>&`) are deliberately excluded.
_INPUT_REDIRECT_TOKEN_RE = re.compile(r"^\d*(?:<<<|<<-?|<>|<&|<)")


def _skip_input_redirections(invocation: list[str], cursor: int) -> int:
    """Skip leading stdin/input redirections when locating an option's word arg.

    This skips only input redirections (a real ``<<EOF`` / ``<`` competing for
    the argument slot) so a later word can still bind as the option argument —
    the legitimate ``--rcfile <<EOF arg`` case, where the argument lands after a
    here-doc redirection. It deliberately does NOT skip output-redirect-shaped
    tokens: the caller inspects the resulting slot and refuses to credit when it
    is output-redirect-shaped (``--rcfile >out``), the conservative reading.
    """
    while cursor < len(invocation) and _INPUT_REDIRECT_TOKEN_RE.match(
        invocation[cursor]
    ):
        cursor += 2 if _redirect_consumes_next(invocation[cursor]) else 1
    return cursor


def _stdin_redirect_kind(token: str) -> str | None:
    """Classify how a token redirects stdin (fd 0 or unspecified).

    Returns ``"heredoc"`` for ``<<`` / ``0<<``, ``"override"`` for a here-string
    ``<<<`` or a plain stdin input redirection (``<``, ``0<``, ``<>``) that
    supersedes a here-doc body, or ``None`` for output redirections and explicit
    non-stdin descriptors. (``<&`` / ``>&`` are split by the tokenizer into
    ``<`` / ``>`` plus ``&``, so a tokenized ``<&`` lands on the plain ``<`` arm.)
    """
    match = re.match(r"^(\d*)(<<<|<<-?|<>|<&|<|>>|>&|>)", token)
    if not match:
        return None
    fd, operator = match.group(1), match.group(2)
    if fd not in ("", "0") or operator.startswith(">"):
        return None
    if operator.startswith("<<") and operator != "<<<":
        return "heredoc"
    return "override"


def _heredoc_body_is_executed_by_shell(
    line: str, op_start: int, fd: int | None
) -> bool:
    # A here-doc on an explicit non-stdin descriptor (e.g. `bash -s 3<<EOF`) is
    # data on that fd, never the shell's executed script.
    if fd is not None and fd != 0:
        return False

    invocation = invocation_tokens(_simple_command_spanning(line, op_start))
    if not invocation:
        return False
    executor = PurePosixPath(invocation[0]).name
    if executor not in SHELL_HEREDOC_EXECUTORS:
        return False
    # The `--rcfile`/`--init-file` word-argument options, the `-O`/`+O` shopt
    # flags, and the `+s` stdin-as-script spelling are Bash-specific. A POSIX
    # `sh`/`dash`/`ksh` invocation aborts on (or never honours) them before the
    # here-doc body runs, so crediting them for those executors is a false
    # validation credit. Gate that grammar on an actual ``bash``. `zsh` is the
    # exception for a small allowlist of GNU-style `--option-name` invocation
    # options (the startup-file toggles in `_ZSH_STDIN_SCRIPT_LONG_OPTIONS`) that
    # still run stdin as the script; every other zsh long option is refused
    # below. `ksh` is intentionally folded into the POSIX reject path as the safe
    # (never over-crediting) default; its `--option` spellings are untested here,
    # so add an `is_ksh` branch only with cases that prove a real ksh here-doc
    # script runs.
    is_bash = executor == "bash"
    is_zsh = executor == "zsh"

    # A second stdin here-doc, a here-string, or a plain `< file` input
    # redirection supersedes or competes with this body, so it is no longer
    # reliably the executed script. Bias to "data" (drop): that can only fail to
    # credit a validation, never wrongly credit one. The count includes the
    # here-doc under evaluation, so `> 1` means a second stdin here-doc exists.
    heredocs = 0
    for token in invocation:
        kind = _stdin_redirect_kind(token)
        if kind == "override":
            return False
        if kind == "heredoc":
            heredocs += 1
    if heredocs > 1:
        return False

    forced_stdin_script = False
    noexec = False
    cursor = 1
    past_options = False
    seen_short_option = False
    while cursor < len(invocation):
        token = invocation[cursor]
        if _REDIRECT_TOKEN_RE.match(token):
            cursor = _skip_redirections(invocation, cursor)
            continue
        if past_options:
            break  # operand after `--`: bash runs it as the script file
        if token in {"-c", "--command"}:
            return False
        if token == "--":
            past_options = True
            cursor += 1
            continue
        if token.startswith("--"):
            if is_zsh:
                # zsh accepts GNU-style `--option-name` invocation options, but
                # only some leave stdin as the executed script. Credit just the
                # verified startup-file toggles, and only before any short
                # option: some zsh short options end option processing (`-b`, or
                # a cluster ending in `-` such as `-x-`), after which `--no-rcs`
                # is a script-file operand and the body is its stdin DATA, not the
                # script. Refusing a long option once a short option has been
                # seen avoids enumerating every zsh terminator letter while never
                # over-crediting; an unknown name aborts zsh, `--noexec` parses
                # but does not run, `--version`/`--help` exit, and `--emulate
                # <mode>` takes a word argument, so refusing the rest is also the
                # safe direction.
                if token in _ZSH_STDIN_SCRIPT_LONG_OPTIONS and not seen_short_option:
                    cursor += 1
                    continue
                return False
            # GNU long options are otherwise Bash-only and, even on Bash, are
            # only recognized before any single-character option (Bash manual).
            # For a POSIX sh/dash/ksh executor, or a late long option after a
            # short flag, the shell aborts or treats the token as the script-file
            # operand before the here-doc body runs, so never credit it.
            if not is_bash or seen_short_option:
                return False
            if _bash_exits_before_stdin_long_option(token):
                return False
            if token in _OPTIONS_TAKING_WORD_ARG:
                # The option needs a following word argument. Skip an input
                # redirection (a real `<<EOF` competing for the arg slot) so a
                # later word can still bind (`--rcfile <<EOF -s`). But an
                # output-redirect-shaped candidate is never a safe argument: an
                # unquoted `>out` is a real redirection bash removes, leaving the
                # option argument-less so it aborts, and a quoted `'>out'` is
                # indistinguishable after quote stripping. Refuse both rather
                # than wrongly credit the body. Input redirections were just
                # consumed, so a remaining `_REDIRECT_TOKEN_RE` match here can
                # only be an output redirection.
                arg_cursor = _skip_input_redirections(invocation, cursor + 1)
                if arg_cursor >= len(invocation) or _REDIRECT_TOKEN_RE.match(
                    invocation[arg_cursor]
                ):
                    return False
                cursor = arg_cursor + 1
                continue
            # Any other long option (e.g. `--posix`) is a single unit, never a
            # compact short-flag cluster, so `--posix` must not be read as `-s`.
            cursor += 1
            continue
        if token in _BASH_SHOPT_OPTION_FLAGS:
            if not is_bash:
                return False
            seen_short_option = True
            arg_cursor = _skip_input_redirections(invocation, cursor + 1)
            if arg_cursor >= len(invocation):
                cursor += 1
                continue
            if invocation[arg_cursor] not in _BASH_SHOPT_OPTIONS:
                return False
            cursor = arg_cursor + 1
            continue
        if token.startswith(("-", "+")) and token != "-":
            sign, cluster = token[0], token[1:]
            seen_short_option = True
            if "c" in cluster:
                return False
            if "n" in cluster:
                noexec = sign == "-"
            # `-s` forces stdin-as-script on every POSIX shell; the `+s` spelling
            # only does so on Bash (dash/sh open the operand as a command file),
            # so credit `+s` for an actual bash executor only.
            if "s" in cluster and (sign == "-" or is_bash):
                forced_stdin_script = True
            cursor += 1
            continue
        break  # first non-option operand: bash runs it, the body is its stdin data

    if noexec:
        return False
    if forced_stdin_script:
        return True
    return cursor >= len(invocation)  # no script-file operand -> stdin is the script


def _heredoc_delimiters_on_line(line: str) -> list[tuple[str, bool, bool, bool, int]]:
    """Return here-doc operators on a shell logical line, in order.

    Ignores `<<<` (here-string, which takes a word not a body), a `<<` inside
    single/double quotes, and a `<<` inside arithmetic `$(( ))` / `(( ))` (left
    shift), so those never start spurious body skipping.

    The third tuple member is true when the body is script content executed by a
    shell command such as ``bash <<EOF``. The fourth member records whether the
    delimiter word was quoted, which disables body expansion for inert
    here-docs. The final member is the redirection operator start index.
    """
    result: list[tuple[str, bool, bool, bool, int]] = []
    index = 0
    length = len(line)
    quote: str | None = None
    arith = 0
    while index < length:
        char = line[index]
        if quote is not None:
            if char == "\\" and quote == '"' and index + 1 < length:
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            index += 1
            continue
        if char == "#" and _starts_shell_comment(line, index):
            break
        if char == "\\" and index + 1 < length:
            index += 2
            continue
        if line.startswith("((", index):
            arith += 1
            index += 2
            continue
        if line.startswith("))", index) and arith > 0:
            arith -= 1
            index += 2
            continue
        if line.startswith("<<", index):
            if line.startswith("<<<", index):
                index += 3  # here-string, not a body
                continue
            if arith > 0:
                index += 2  # arithmetic left shift, not a here-doc
                continue
            # An explicit fd prefix (`0<<`, `3<<`) selects which descriptor the
            # body feeds. Leading digits count as an fd only when they form a
            # standalone redirection token, not the tail of a word like `foo2<<`.
            fd_begin = index
            while fd_begin > 0 and line[fd_begin - 1].isdigit():
                fd_begin -= 1
            fd: int | None = None
            op_start = index
            if fd_begin < index and (
                fd_begin == 0 or line[fd_begin - 1] in " \t;&|()<>"
            ):
                fd = int(line[fd_begin:index])
                op_start = fd_begin
            cursor = index + 2
            strip_tabs = False
            if cursor < length and line[cursor] == "-":
                strip_tabs = True
                cursor += 1
            while cursor < length and line[cursor] in (" ", "\t"):
                cursor += 1
            delimiter, cursor, delimiter_quoted = _parse_heredoc_delimiter(
                line, cursor
            )
            if delimiter:
                result.append(
                    (
                        delimiter,
                        strip_tabs,
                        _heredoc_body_is_executed_by_shell(line, op_start, fd),
                        delimiter_quoted,
                        op_start,
                    )
                )
            index = cursor
            continue
        index += 1
    return result


def strip_heredoc_bodies(command: str, *, inert_only: bool = False) -> str:
    """Drop here-doc body (and closing-delimiter) lines from ``command``.

    A here-doc body is data fed to a command, not executed by the shell, so its
    lines must not be parsed as commands. Full stripping is used by the
    validation matcher: erring toward dropping a line is safe there (it can only
    fail to credit a validation, never wrongly credit or unblock one).

    ``inert_only=True`` drops only the bodies that bash treats as pure data with
    no expansion at all: a QUOTED delimiter (``<<'EOF'``) on a command that is
    not a shell executor. Prose in such a body cannot smuggle a command, so
    classifying its lines as commands is a category error, not conservatism —
    it made guards block commit-message and document heredocs whose text merely
    mentioned command-like words. Unquoted-delimiter bodies still expand
    ``$(...)`` and backticks, so they stay visible to the guards, preserving
    the intentional bias toward blocking genuinely ambiguous input; shell
    executor bodies (``bash <<EOF``) remain visible as script text in both
    modes. ``simple_commands`` applies the inert strip unconditionally.
    """
    if "<<" not in command:
        return command
    lines = command.split("\n")
    pending: list[tuple[str, bool, bool, bool, list[str]]] = []
    kept: list[str] = []
    logical_scan_parts: list[str] = []
    logical_raw_lines: list[str] = []

    def close_body(preserve_body: bool, delimiter_quoted: bool, body: list[str]) -> None:
        if preserve_body:
            if body:
                kept.append(
                    strip_heredoc_bodies("\n".join(body), inert_only=inert_only)
                )
            return
        if inert_only and not delimiter_quoted:
            # Expandable body: keep it visible to the guards verbatim.
            kept.extend(body)

    for raw in lines:
        line = raw.rstrip("\r")
        if pending:
            delimiter, strip_tabs, preserve_body, delimiter_quoted, body = pending[0]
            candidate = line.lstrip("\t") if strip_tabs else line
            if candidate == delimiter:
                close_body(preserve_body, delimiter_quoted, body)
                pending.pop(0)  # closing delimiter line: drop it
            else:
                body.append(raw)
            continue

        logical_raw_lines.append(raw)
        if _line_has_unquoted_continuation(line):
            logical_scan_parts.append(line[:-1])
            continue

        logical_scan_parts.append(line)
        logical_line = "".join(logical_scan_parts)
        for (
            delimiter,
            strip_tabs,
            preserve_body,
            delimiter_quoted,
            _op_start,
        ) in _heredoc_delimiters_on_line(logical_line):
            pending.append((delimiter, strip_tabs, preserve_body, delimiter_quoted, []))
        kept.extend(logical_raw_lines)
        logical_scan_parts = []
        logical_raw_lines = []
    kept.extend(logical_raw_lines)
    for _delimiter, _strip_tabs, preserve_body, delimiter_quoted, body in pending:
        close_body(preserve_body, delimiter_quoted, body)
    return "\n".join(kept)


def simple_commands(command: str, *, strip_heredocs: bool = False) -> list[list[str]]:
    # Inert here-doc bodies (quoted delimiter, not shell-executed) are pure
    # data by shell semantics and must never be classified as commands;
    # `strip_heredocs=True` additionally drops expandable bodies for callers
    # that only credit, never block (see strip_heredoc_bodies).
    if strip_heredocs:
        command = strip_heredoc_bodies(command)
    else:
        command = strip_heredoc_bodies(command, inert_only=True)
    commands: list[list[str]] = []
    current: list[str] = []
    for token in shell_tokens(normalize_command_separators(command)):
        if is_shell_separator(token):
            if current:
                commands.append(current)
            current = []
            continue
        current.append(token)
    if current:
        commands.append(current)
    return commands


ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*")


def is_assignment(token: str) -> bool:
    return bool(ASSIGNMENT_RE.match(token))


ENV_OPTIONS_WITH_VALUE = {
    "-u",
    "--unset",
    "-C",
    "--chdir",
    "-P",
    "--path",
    "-S",
    "--split-string",
}
ENV_OPTIONS_WITH_VALUE_PREFIXES = (
    "--unset=",
    "--chdir=",
    "--path=",
    "--split-string=",
)
ENV_OPTIONS_WITHOUT_VALUE = {"-i", "--ignore-environment", "-0", "--null"}
ENV_LONG_OPTION_KINDS = {
    "block-signal": "optional",
    "chdir": "value",
    "debug": "flag",
    "default-signal": "optional",
    "help": "stop",
    "ignore-environment": "flag",
    "ignore-signal": "optional",
    "list-signal-handling": "flag",
    "null": "flag",
    "path": "value",
    "split-string": "split",
    "unset": "value",
    "version": "stop",
}
ENV_SPLIT_WORD_SEPARATORS = frozenset({" ", "\t", "\r", "\n"})


def _unique_long_option(
    token: str, option_kinds: Mapping[str, str]
) -> tuple[str, str, bool] | None:
    name, separator, _value = token[2:].partition("=")
    matches = [option for option in option_kinds if option.startswith(name)]
    if len(matches) != 1:
        return None
    option = matches[0]
    return option, option_kinds[option], bool(separator)


def _unique_long_option_kind(
    token: str, option_kinds: Mapping[str, str]
) -> tuple[str, bool] | None:
    resolved = _unique_long_option(token, option_kinds)
    if resolved is None:
        return None
    _option, kind, attached_value = resolved
    return kind, attached_value


def _env_split_requires_opaque(value: str) -> bool:
    """Detect GNU env split syntax that POSIX shlex cannot model safely."""
    # shell_tokens() cannot retain whether apparent split-string quotes were
    # themselves literal content inside an outer double-quoted shell argument.
    # Expansion syntax that now looks single-quoted may therefore run before
    # env receives the value. Without that provenance, dollars and legacy
    # backtick substitutions are both unresolved.
    if "$" in value or "`" in value:
        return True
    quote = ""
    word_started = False
    index = 0
    while index < len(value):
        character = value[index]
        if quote == "'":
            if character == "'":
                quote = ""
            elif character == "\\" and index + 1 < len(value):
                if value[index + 1] in {"'", "\\"}:
                    return True
            index += 1
            continue
        if quote == '"':
            if character == '"':
                quote = ""
            elif character == "\\":
                return True
            index += 1
            continue
        if character == "'":
            quote = "'"
            word_started = True
            index += 1
            continue
        if character == '"':
            quote = '"'
            word_started = True
            index += 1
            continue
        # GNU env discards an active unquoted comment and can then execute argv
        # appended after the split value. Preserve that hidden scope as opaque.
        if character == "#" and not word_started:
            return True
        if character == "\\" or character in {"\f", "\v"}:
            return True
        if character in ENV_SPLIT_WORD_SEPARATORS:
            word_started = False
            index += 1
            continue
        word_started = True
        index += 1
    return False


def _split_env_string(value: str) -> list[str]:
    # GNU env -S has variable and escape semantics beyond POSIX shlex. Retain
    # an opaque marker whenever syntax could alter token boundaries or hide
    # appended argv from the shared command classifiers.
    if _env_split_requires_opaque(value):
        return _opaque_wrapper_invocation([OPAQUE_NESTED_SHELL_COMMAND])
    try:
        return shlex.split(value, posix=True)
    except ValueError:
        return []


def env_split_expanded_tokens(
    tokens: list[str], index: int = 0, *, depth: int = 0, max_depth: int = 5
) -> list[str]:
    """Normalize a GNU env prefix and expand split strings.

    Option values stay distinct from environment assignments so authorization
    consumers can inspect the normalized prefix without reimplementing GNU
    env's short-cluster and unique-long-option grammar.
    """
    if depth > max_depth:
        return _opaque_wrapper_invocation([OPAQUE_NESTED_SHELL_COMMAND])
    expanded: list[str] = []
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return [*expanded, token, *tokens[index + 1 :]]
        if token == "-":
            expanded.append("-i")
            index += 1
            continue
        if is_assignment(token):
            expanded.append(token)
            index += 1
            continue
        if token.startswith("--"):
            resolved = _unique_long_option(token, ENV_LONG_OPTION_KINDS)
            if resolved is None:
                return [*expanded, *_opaque_wrapper_invocation(tokens[index:])]
            option, kind, attached_value = resolved
            if kind == "stop":
                return (
                    [*expanded, *_opaque_wrapper_invocation(tokens[index:])]
                    if attached_value
                    else expanded
                )
            if kind == "flag":
                if attached_value:
                    return [*expanded, *_opaque_wrapper_invocation(tokens[index:])]
                normalized = {
                    "ignore-environment": "-i",
                    "null": "-0",
                }.get(option, f"--{option}")
                expanded.append(normalized)
                index += 1
                continue
            if kind == "optional":
                expanded.append(token)
                index += 1
                continue
            if attached_value:
                value = token.split("=", 1)[1]
                rest = tokens[index + 1 :]
            elif index + 1 < len(tokens):
                value = tokens[index + 1]
                rest = tokens[index + 2 :]
            else:
                return [*expanded, *_opaque_wrapper_invocation(tokens[index:])]
            if kind == "split":
                return [
                    *expanded,
                    *env_split_expanded_tokens(
                        _split_env_string(value) + rest,
                        0,
                        depth=depth + 1,
                        max_depth=max_depth,
                    ),
                ]
            normalized = {
                "unset": "-u",
                "chdir": "-C",
                "path": "-P",
            }[option]
            expanded.extend((normalized, value))
            tokens = rest
            index = 0
            continue
        if token.startswith("-"):
            cluster = token[1:]
            position = 0
            while position < len(cluster):
                option = cluster[position]
                if option in {"i", "0", "v"}:
                    expanded.append(f"-{option}")
                    position += 1
                    continue
                if option not in {"u", "C", "P", "S"}:
                    return [*expanded, *_opaque_wrapper_invocation(tokens[index:])]
                attached_value = cluster[position + 1 :]
                if attached_value:
                    value = attached_value
                    rest = tokens[index + 1 :]
                elif index + 1 < len(tokens):
                    value = tokens[index + 1]
                    rest = tokens[index + 2 :]
                else:
                    return [*expanded, *_opaque_wrapper_invocation(tokens[index:])]
                if option == "S":
                    return [
                        *expanded,
                        *env_split_expanded_tokens(
                            _split_env_string(value) + rest,
                            0,
                            depth=depth + 1,
                            max_depth=max_depth,
                        ),
                    ]
                expanded.extend((f"-{option}", value))
                tokens = rest
                index = 0
                break
            else:
                index += 1
            continue
        return [*expanded, *tokens[index:]]
    return expanded


def env_target_tokens(
    tokens: list[str], index: int = 0, *, depth: int = 0, max_depth: int = 5
) -> list[str]:
    if depth > max_depth:
        return _opaque_wrapper_invocation([OPAQUE_NESTED_SHELL_COMMAND])
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return tokens[index + 1 :]
        if token == "-":
            index += 1
            continue
        if token.startswith("--"):
            resolved = _unique_long_option_kind(token, ENV_LONG_OPTION_KINDS)
            if resolved is None:
                return _opaque_wrapper_invocation(tokens[index:])
            kind, attached_value = resolved
            if kind == "stop":
                return (
                    _opaque_wrapper_invocation(tokens[index:])
                    if attached_value
                    else []
                )
            if kind == "flag":
                if attached_value:
                    return _opaque_wrapper_invocation(tokens[index:])
                index += 1
                continue
            if kind == "optional":
                index += 1
                continue
            if attached_value:
                value = token.split("=", 1)[1]
                rest = tokens[index + 1 :]
            elif index + 1 < len(tokens):
                value = tokens[index + 1]
                rest = tokens[index + 2 :]
            else:
                return _opaque_wrapper_invocation(tokens[index:])
            if kind == "split":
                return env_target_tokens(
                    _split_env_string(value) + rest,
                    0,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            tokens = rest
            index = 0
            continue
        if is_assignment(token):
            index += 1
            continue
        if token in {"--help", "--version"}:
            return []
        if token in ENV_OPTIONS_WITHOUT_VALUE:
            index += 1
            continue
        if token in ENV_OPTIONS_WITH_VALUE:
            if index + 1 >= len(tokens):
                return []
            if token in {"-S", "--split-string"}:
                split_tokens = _split_env_string(tokens[index + 1])
                return env_target_tokens(
                    split_tokens + tokens[index + 2 :],
                    0,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            index += 2
            continue
        split_prefix = "--split-string="
        if token.startswith(split_prefix):
            split_tokens = _split_env_string(token.removeprefix(split_prefix))
            return env_target_tokens(
                split_tokens + tokens[index + 1 :],
                0,
                depth=depth + 1,
                max_depth=max_depth,
            )
        if any(token.startswith(prefix) for prefix in ENV_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
            continue
        if token.startswith("-") and not token.startswith("--"):
            cluster = token[1:]
            position = 0
            while position < len(cluster):
                option = cluster[position]
                if option in {"i", "0", "v"}:
                    position += 1
                    continue
                if option not in {"u", "C", "P", "S"}:
                    return _opaque_wrapper_invocation(tokens[index:])
                attached_value = cluster[position + 1 :]
                if attached_value:
                    value = attached_value
                    rest = tokens[index + 1 :]
                elif index + 1 < len(tokens):
                    value = tokens[index + 1]
                    rest = tokens[index + 2 :]
                else:
                    return _opaque_wrapper_invocation(tokens[index:])
                if option == "S":
                    return env_target_tokens(
                        _split_env_string(value) + rest,
                        0,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                tokens = rest
                index = 0
                break
            else:
                index += 1
            continue
        return tokens[index:]
    return []


def skip_env_prefix(tokens: list[str], index: int) -> int:
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if is_assignment(token):
            index += 1
            continue
        if token in {"-i", "--ignore-environment", "-0", "--null"}:
            index += 1
            continue
        if token in {"-u", "--unset"}:
            index += 2
            continue
        if token.startswith("--unset="):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return index
    return index


OPAQUE_WRAPPER_COMMAND = "__agent_runtime_opaque_wrapper__"
OPAQUE_NESTED_SHELL_COMMAND = "__agent_runtime_opaque_nested_shell__"


def _opaque_wrapper_invocation(tokens: list[str] | None = None) -> list[str]:
    """Return a conservative marker when wrapper option parsing is ambiguous."""
    return [OPAQUE_WRAPPER_COMMAND, *(tokens or [])]


def invocation_is_opaque(invocation: list[str]) -> bool:
    return bool(invocation) and invocation[0] == OPAQUE_WRAPPER_COMMAND


def invocation_is_unresolved_nested(invocation: list[str]) -> bool:
    return bool(invocation) and invocation[0] == OPAQUE_NESTED_SHELL_COMMAND


def opaque_invocation_candidates(
    invocation: list[str],
    executables: set[str] | frozenset[str],
    *,
    max_depth: int = 4,
) -> list[list[str]]:
    """Return governed command slices retained beneath an opaque wrapper parse."""
    if not invocation_is_opaque(invocation):
        return []
    candidates: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def inspect(tokens: list[str], depth: int) -> None:
        if not tokens or depth > max_depth:
            return
        if invocation_is_unresolved_nested(tokens):
            candidates.append(tokens)
            return
        key = tuple(tokens)
        if key in seen:
            return
        seen.add(key)
        for index, token in enumerate(tokens):
            suffix = tokens[index:]
            if PurePosixPath(token).name in executables:
                candidates.append(suffix)
            parsed = invocation_tokens(suffix, shell_boundary=False)
            if invocation_is_opaque(parsed):
                if depth == max_depth:
                    candidates.append([OPAQUE_NESTED_SHELL_COMMAND])
                    continue
                inspect(parsed[1:], depth + 1)
                continue
            payload = nested_shell_payload(parsed)
            if depth == max_depth:
                if payload:
                    candidates.append([OPAQUE_NESTED_SHELL_COMMAND])
                continue
            if parsed != suffix:
                inspect(parsed, depth + 1)
            if payload:
                for nested in simple_commands_with_nested_shells(
                    payload, max_depth=max_depth - depth - 1
                ):
                    inspect(invocation_tokens(nested), depth + 1)

    inspect(invocation[1:], 0)
    return candidates


def opaque_invocation_has_unresolved_nested(invocation: list[str]) -> bool:
    return any(
        invocation_is_unresolved_nested(candidate)
        for candidate in opaque_invocation_candidates(invocation, set())
    )


def _short_option_cluster_next_index(
    tokens: list[str],
    index: int,
    *,
    flag_options: frozenset[str],
    value_options: frozenset[str],
    stop_options: frozenset[str] = frozenset(),
) -> int | None:
    """Consume one getopt-style short option cluster, including value flags."""
    cluster = tokens[index][1:]
    for position, option in enumerate(cluster):
        if option in stop_options:
            return None
        if option in flag_options:
            continue
        if option not in value_options:
            return -1
        if position + 1 < len(cluster):
            return index + 1
        return index + 2 if index + 1 < len(tokens) else -1
    return index + 1


TIME_LONG_OPTION_KINDS = {
    "append": "flag",
    "format": "value",
    "help": "stop",
    "output": "value",
    "portability": "flag",
    "quiet": "flag",
    "verbose": "flag",
    "version": "stop",
}


def _time_long_option(token: str) -> tuple[str, bool] | None:
    return _unique_long_option_kind(token, TIME_LONG_OPTION_KINDS)


def _time_target_index(tokens: list[str], index: int) -> int | None:
    """Return the command index following shell/GNU ``time`` options."""
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in {"-h", "-V"}:
            return None
        if token.startswith("-") and token != "-" and not token.startswith("--"):
            next_index = _short_option_cluster_next_index(
                tokens,
                index,
                flag_options=frozenset("apqv"),
                value_options=frozenset("fo"),
                stop_options=frozenset("hV"),
            )
            if next_index is None:
                return None
            if next_index >= 0:
                index = next_index
                continue
            return -1
        if token.startswith("--"):
            resolved = _time_long_option(token)
            if resolved is None:
                return -1
            kind, attached_value = resolved
            if kind == "stop":
                return -1 if attached_value else None
            if kind == "flag":
                if attached_value:
                    return -1
                index += 1
                continue
            if attached_value:
                index += 1
                continue
            if index + 1 >= len(tokens):
                return -1
            index += 2
            continue
        return index
    return index


def _command_target_index(tokens: list[str], index: int) -> int | None:
    """Return the command index following POSIX ``command`` options."""
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token.startswith("-") and token != "-":
            flags = token[1:]
            if "v" in flags or "V" in flags:
                return None
            if flags and set(flags) == {"p"}:
                index += 1
                continue
            return -1
        return index
    return index


def _exec_target_index(tokens: list[str], index: int) -> int | None:
    """Return the command index following Bash/POSIX ``exec`` options."""
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in {"-a", "--argv0"}:
            if index + 1 >= len(tokens):
                return -1
            index += 2
            continue
        if token.startswith("--argv0="):
            index += 1
            continue
        if token.startswith("-") and token != "-" and not token.startswith("--"):
            next_index = _short_option_cluster_next_index(
                tokens,
                index,
                flag_options=frozenset("cl"),
                value_options=frozenset("a"),
            )
            if next_index is None:
                return -1
            if next_index >= 0:
                index = next_index
                continue
            return -1
        if token.startswith("--"):
            return -1
        return index
    return index


def _agent_run_exec_target_index(tokens: list[str], index: int) -> int | None:
    """Return the command index following supported ``agent-run exec`` options."""
    index += 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in {"-h", "--help"}:
            return None
        if token in {"--cwd", "--direnv"}:
            if index + 1 >= len(tokens):
                return -1
            index += 2
            continue
        if token.startswith(("--cwd=", "--direnv=")):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            return -1
        return index
    return index


def _invocation_start_index(
    simple_command: list[str], *, shell_boundary: bool = True
) -> int:
    """Skip assignments and shell control words before a command position."""
    index = 0
    while index < len(simple_command):
        token = simple_command[index]
        if is_assignment(token):
            index += 1
            continue
        if shell_boundary and token == "function":
            # Bash accepts `function name { ...; }` without the POSIX `()`
            # separator that otherwise exposes the brace body as a new command.
            index += 2  # declaration keyword plus function name
            if index < len(simple_command) and simple_command[index] == "()":
                index += 1
            if index < len(simple_command) and simple_command[index] == "{":
                index += 1
            continue
        if shell_boundary and token in SHELL_CONTROL_PREFIX_TOKENS:
            index += 1
            continue
        if shell_boundary and token in SHELL_CONTROL_TERMINATOR_TOKENS:
            return len(simple_command)
        break
    return index


def invocation_command_position_is_dynamic(
    simple_command: list[str], *, shell_boundary: bool = True
) -> bool:
    """Whether the shell must expand the executable before it can be known."""
    index = _invocation_start_index(simple_command, shell_boundary=shell_boundary)
    if index >= len(simple_command):
        return False
    token = simple_command[index]
    return "$" in token or "`" in token


def invocation_tokens(
    simple_command: list[str], *, shell_boundary: bool = True
) -> list[str]:
    index = _invocation_start_index(simple_command, shell_boundary=shell_boundary)
    if index >= len(simple_command):
        return []
    if invocation_command_position_is_dynamic(
        simple_command, shell_boundary=shell_boundary
    ):
        return _opaque_wrapper_invocation(simple_command[index:])

    command = PurePosixPath(simple_command[index]).name
    if command == "env":
        return invocation_tokens(
            env_target_tokens(simple_command, index + 1), shell_boundary=False
        )
    if command == "time":
        target_index = _time_target_index(simple_command, index)
        if target_index is None:
            return []
        if target_index < 0:
            return _opaque_wrapper_invocation(simple_command[index + 1 :])
        return invocation_tokens(simple_command[target_index:], shell_boundary=False)
    if command == "command":
        target_index = _command_target_index(simple_command, index)
        if target_index is None:
            return []
        if target_index < 0:
            return _opaque_wrapper_invocation(simple_command[index + 1 :])
        return invocation_tokens(simple_command[target_index:], shell_boundary=False)
    if command == "exec":
        target_index = _exec_target_index(simple_command, index)
        if target_index is None:
            return []
        if target_index < 0:
            return _opaque_wrapper_invocation(simple_command[index + 1 :])
        return invocation_tokens(simple_command[target_index:], shell_boundary=False)

    if index >= len(simple_command):
        return []

    command = PurePosixPath(simple_command[index]).name
    if command == "agent-run" and index + 1 < len(simple_command):
        if simple_command[index + 1] == "exec":
            target_index = _agent_run_exec_target_index(simple_command, index)
            if target_index is None:
                return []
            if target_index < 0:
                return _opaque_wrapper_invocation(simple_command[index + 2 :])
            return invocation_tokens(
                simple_command[target_index:], shell_boundary=False
            )

    return simple_command[index:]


def marker_environment_before_invocation(
    tokens: list[str],
    marker_names: Iterable[str],
    inherited: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return marker variables visible to the final wrapped executable.

    The walk follows the same wrapper target grammar as ``invocation_tokens``
    while preserving ordered assignment, reset, and unset effects. Ambiguous
    wrappers and split-string expansion fail closed by returning no markers.
    """
    names = frozenset(marker_names)
    state = {
        name: value
        for name, value in (inherited or {}).items()
        if name in names
    }

    def apply_assignment(token: str) -> bool:
        if not is_assignment(token):
            return False
        name, value = token.split("=", 1)
        if name in names:
            state[name] = value.strip("\"'")
        return True

    index = 0
    while index < len(tokens) and apply_assignment(tokens[index]):
        index += 1
    if index >= len(tokens):
        return state

    command = PurePosixPath(tokens[index]).name
    if command == "env":
        normalized = env_split_expanded_tokens(tokens[index + 1 :])
        option_mode = True
        env_index = 0
        while env_index < len(normalized):
            token = normalized[env_index]
            if invocation_is_opaque(normalized[env_index:]):
                return {}
            if option_mode and token == "--":
                option_mode = False
                env_index += 1
                continue
            if option_mode and token in {"-i", "--ignore-environment"}:
                state.clear()
                env_index += 1
                continue
            if option_mode and token in {"-u", "--unset"}:
                if env_index + 1 >= len(normalized):
                    return {}
                state.pop(normalized[env_index + 1], None)
                env_index += 2
                continue
            if option_mode and token in {"-C", "--chdir", "-P", "--path"}:
                if env_index + 1 >= len(normalized):
                    return {}
                env_index += 2
                continue
            if option_mode and token.startswith("-") and token != "-":
                env_index += 1
                continue
            if apply_assignment(token):
                env_index += 1
                continue
            return marker_environment_before_invocation(
                normalized[env_index:], names, state
            )
        return state

    target_index: int | None = index
    if command == "time":
        target_index = _time_target_index(tokens, index)
    elif command == "command":
        target_index = _command_target_index(tokens, index)
    elif command == "exec":
        target_index = _exec_target_index(tokens, index)
    elif command == "agent-run" and tokens[index + 1 : index + 2] == ["exec"]:
        target_index = _agent_run_exec_target_index(tokens, index)
    else:
        return state

    if target_index is None:
        return state
    if target_index < 0:
        return {}
    return marker_environment_before_invocation(tokens[target_index:], names, state)


def shell_c_payload(tokens: list[str], index: int = 0) -> str | None:
    """Return the command string passed to a shell ``-c``/``--command`` option."""
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return None
        if token == "-c":
            if index + 1 < len(tokens):
                return tokens[index + 1]
            return None
        if token.startswith("-") and not token.startswith("--") and "c" in token[1:]:
            if index + 1 < len(tokens):
                return tokens[index + 1]
            return None
        index += 1
    return None


def nested_shell_payload(invocation: list[str]) -> str | None:
    """Return nested shell source carried by ``bash -c``/``sh -c`` or ``eval``."""
    if not invocation:
        return None
    command = PurePosixPath(invocation[0]).name
    if command in SHELL_HEREDOC_EXECUTORS:
        return shell_c_payload(invocation, 0)
    if command == "eval" and len(invocation) > 1:
        return " ".join(invocation[1:])
    return None


def simple_commands_with_nested_shells(
    command: str, *, strip_heredocs: bool = False, max_depth: int = 5
) -> list[list[str]]:
    """Return simple commands, recursively descending into shell command strings.

    This intentionally reuses the same best-effort shell grammar as
    ``simple_commands``. If a command-position shell invocation carries a
    ``-c``/``--command`` payload, or the command is ``eval``, the payload is
    parsed as another shell command string so guard hooks inspect equivalent
    wrapper forms of a blocked action.
    """
    commands: list[list[str]] = []
    seen: set[tuple[int, str]] = set()

    def visit(source: str, depth: int) -> None:
        if depth > max_depth:
            return
        key = (depth, source)
        if key in seen:
            return
        seen.add(key)
        for tokens in simple_commands(source, strip_heredocs=strip_heredocs):
            if not tokens:
                continue
            commands.append(tokens)
            payload = nested_shell_payload(invocation_tokens(tokens))
            if payload:
                if depth >= max_depth:
                    commands.append([OPAQUE_NESTED_SHELL_COMMAND])
                else:
                    visit(payload, depth + 1)

    visit(command, 0)
    return commands


def output_redirect_targets(tokens: list[str]) -> list[tuple[str, bool]]:
    """Return output redirection targets and whether stdout content is inspectable."""
    targets: list[tuple[str, bool]] = []
    index = 0
    clobber_op = f">{CLOBBER_REDIRECT_MARKER}"
    while index < len(tokens):
        token = tokens[index]
        if token in {">", ">>", clobber_op}:
            if index + 1 < len(tokens):
                targets.append((tokens[index + 1], True))
            index += 2
            continue
        if token in {"&>", "&>>", f"&{clobber_op}"}:
            if index + 1 < len(tokens):
                targets.append((tokens[index + 1], False))
            index += 2
            continue
        split_fd = re.match(
            rf"^(?P<fd>\d+)(?P<op>>>?|>{_CLOBBER_REDIRECT_RE})$", token
        )
        if split_fd:
            if index + 1 < len(tokens):
                targets.append((tokens[index + 1], split_fd.group("fd") == "1"))
            index += 2
            continue
        combined = re.match(
            rf"^&(?P<op>>>?|>{_CLOBBER_REDIRECT_RE})(?P<path>.+)$", token
        )
        if combined and combined.group("path"):
            targets.append((combined.group("path"), False))
            index += 1
            continue
        clobber = re.match(
            rf"^(?P<fd>\d*)(?P<op>>{_CLOBBER_REDIRECT_RE})(?P<path>.+)$",
            token,
        )
        if clobber and clobber.group("path"):
            targets.append((clobber.group("path"), clobber.group("fd") in {"", "1"}))
            index += 1
            continue
        match = re.match(r"^(?P<fd>\d*)(?P<op>>>?)(?P<path>.+)$", token)
        if match and match.group("path"):
            targets.append((match.group("path"), match.group("fd") in {"", "1"}))
            index += 1
            continue
        index += 1
    return targets


def _stdout_redirect_targets(tokens: list[str]) -> list[str]:
    return [
        target for target, inspectable in output_redirect_targets(tokens) if inspectable
    ]


def _opaque_output_redirect_targets(tokens: list[str]) -> list[str]:
    return [
        target for target, inspectable in output_redirect_targets(tokens) if not inspectable
    ]


def _tee_targets(tokens: list[str]) -> list[str]:
    invocation = invocation_tokens(tokens)
    if not invocation or PurePosixPath(invocation[0]).name != "tee":
        return []
    targets: list[str] = []
    index = 1
    while index < len(invocation):
        token = invocation[index]
        if token == "--":
            targets.extend(invocation[index + 1 :])
            break
        if token in {"-a", "--append", "-i", "--ignore-interrupts"}:
            index += 1
            continue
        if token in {"-p", "--output-error"}:
            index += 1
            continue
        if token.startswith("--output-error="):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        targets.append(token)
        index += 1
    return targets


def bash_write_targets_from_tokens(tokens: list[str]) -> list[str]:
    """Best-effort output paths for a shell simple command."""
    return _stdout_redirect_targets(tokens) + _tee_targets(tokens)


def _absolute_or_expanded_path(path: str) -> bool:
    return path.startswith(("/", "~", "$"))


def _resolve_bash_path(path: str, cwd: str = "") -> str:
    if not cwd or cwd == "." or _absolute_or_expanded_path(path):
        return path
    if path == ".":
        return cwd
    if path.startswith("./"):
        path = path[2:]
    return f"{cwd.rstrip('/')}/{path}"


def _directory_like_target(path: str, known_dirs: set[str] | None = None) -> bool:
    if known_dirs and path in known_dirs:
        return True
    if path in {".", "./", "~", "~/"}:
        return True
    if path.endswith("/"):
        return True
    expanded = os.path.expanduser(path)
    return bool(expanded) and os.path.isdir(expanded)


def _join_directory_target(directory: str, basename: str) -> str:
    if not basename:
        return directory
    if directory in {".", "./"}:
        return f"./{basename}"
    if directory in {"~", "~/"}:
        return f"~/{basename}"
    return f"{directory.rstrip('/')}/{basename}"


def _copy_style_targets_from_invocation(
    invocation: list[str], *, cwd: str = "", known_dirs: set[str] | None = None
) -> list[str]:
    if not invocation:
        return []
    name = PurePosixPath(invocation[0]).name
    if name not in {"cp", "install", "mv"}:
        return []

    positional: list[str] = []
    target_directory: str | None = None
    index = 1
    while index < len(invocation):
        token = invocation[index]
        if token == "--":
            positional.extend(invocation[index + 1 :])
            break
        if token in {"-t", "--target-directory"} and index + 1 < len(invocation):
            target_directory = invocation[index + 1]
            index += 2
            continue
        if token.startswith("--target-directory="):
            target_directory = token.split("=", 1)[1]
            index += 1
            continue
        if token.startswith("-t") and token != "-t":
            target_directory = token[2:]
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        positional.append(token)
        index += 1

    if target_directory is not None:
        sources = positional
        destinations = [target_directory]
    elif len(positional) >= 2:
        sources = positional[:-1]
        destinations = [positional[-1]]
    else:
        return []

    expanded: list[str] = []
    for destination in destinations:
        resolved_destination = _resolve_bash_path(destination, cwd)
        expanded.append(resolved_destination)
        if _directory_like_target(resolved_destination, known_dirs):
            for source in sources:
                basename = PurePosixPath(source.replace("\\", "/")).name
                if basename:
                    expanded.append(_join_directory_target(resolved_destination, basename))
    return expanded


def _mkdir_created_dirs_from_invocation(invocation: list[str], cwd: str = "") -> list[str]:
    if not invocation or PurePosixPath(invocation[0]).name != "mkdir":
        return []
    dirs: list[str] = []
    index = 1
    while index < len(invocation):
        token = invocation[index]
        if token == "--":
            dirs.extend(_resolve_bash_path(path, cwd) for path in invocation[index + 1 :])
            break
        if token in {"-m", "--mode", "-Z", "--context"}:
            index += 2
            continue
        if token.startswith(("--mode=", "--context=")):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        dirs.append(_resolve_bash_path(token, cwd))
        index += 1
    return dirs


def _cd_target_from_invocation(invocation: list[str], cwd: str = "") -> str | None:
    if not invocation or PurePosixPath(invocation[0]).name != "cd":
        return None
    index = 1
    while index < len(invocation) and invocation[index] in {"-L", "-P", "-e"}:
        index += 1
    if index < len(invocation) and invocation[index] == "--":
        index += 1
    if index >= len(invocation):
        return "~"
    target = invocation[index]
    if target == "-":
        return None
    return _resolve_bash_path(target, cwd)


def bash_copy_style_write_targets(command: str) -> list[str]:
    targets: list[str] = []
    known_dirs: set[str] = set()
    cwd = ""
    current: list[str] = []

    def flush(separator: str | None) -> None:
        nonlocal current, cwd
        if not current:
            return
        invocation = invocation_tokens(current)
        targets.extend(
            _copy_style_targets_from_invocation(
                invocation,
                cwd=cwd,
                known_dirs=known_dirs,
            )
        )
        payload = nested_shell_payload(invocation)
        if payload:
            targets.extend(bash_copy_style_write_targets(payload))
        if separator in {";", "&&"}:
            known_dirs.update(_mkdir_created_dirs_from_invocation(invocation, cwd))
            cwd = _cd_target_from_invocation(invocation, cwd) or cwd
        current = []

    for token in shell_tokens(normalize_command_separators(strip_heredoc_bodies(command))):
        if is_shell_separator(token):
            flush(token)
            continue
        current.append(token)
    flush(None)
    return targets


def _tokens_without_redirections(tokens: list[str]) -> list[str]:
    kept: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _REDIRECT_TOKEN_RE.match(token):
            index += 2 if _redirect_consumes_next(token) else 1
            continue
        kept.append(token)
        index += 1
    return kept


def _literal_stdout_from_tokens(tokens: list[str]) -> str:
    invocation = invocation_tokens(_tokens_without_redirections(tokens))
    if not invocation:
        return ""
    command = PurePosixPath(invocation[0]).name
    args = invocation[1:]
    generated_escape_re = r"\\(?:x[0-9A-Fa-f]{1,2}|[0-7]{1,3}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})"
    if command == "echo":
        expands_backslash = False
        while args and re.fullmatch(r"-[neE]+", args[0]):
            for flag in args[0][1:]:
                if flag == "e":
                    expands_backslash = True
                elif flag == "E":
                    expands_backslash = False
            args = args[1:]
        content = " ".join(args)
        if expands_backslash and re.search(generated_escape_re, content):
            return ""
        return "" if re.search(r"[$`]", content) else content
    if command == "printf":
        # Do not approximate printf formatting. Multi-argument printf output is
        # opaque to this parser, so protected writes fail closed instead of
        # scanning a string that differs from the shell's real output.
        if len(args) == 1:
            return "" if re.search(rf"[$`]|{generated_escape_re}", args[0]) else args[0]
        return ""
    return ""


def _record_literal_bash_writes(command: str) -> list[tuple[str, str]]:
    writes: list[tuple[str, str]] = []
    current: list[str] = []
    piped_content: str | None = None
    cwd = ""

    def flush(separator: str | None) -> None:
        nonlocal current, piped_content, cwd
        if not current:
            piped_content = None if separator != "|" else piped_content
            return
        if any(token in {"<<", "<<-"} or token.startswith(("<<", "<<-")) for token in current):
            if separator in {";", "&&"}:
                invocation = invocation_tokens(current)
                cwd = _cd_target_from_invocation(invocation, cwd) or cwd
            current = []
            piped_content = None if separator != "|" else piped_content
            return
        targets = bash_write_targets_from_tokens(current)
        opaque_targets = _opaque_output_redirect_targets(current)
        content = _literal_stdout_from_tokens(current)
        if targets:
            payload = content or piped_content or ""
            writes.extend((_resolve_bash_path(target, cwd), payload) for target in targets)
        if opaque_targets:
            writes.extend((_resolve_bash_path(target, cwd), "") for target in opaque_targets)
        if separator in {";", "&&"}:
            invocation = invocation_tokens(current)
            cwd = _cd_target_from_invocation(invocation, cwd) or cwd
        piped_content = content if separator == "|" else None
        current = []

    for token in shell_tokens(normalize_command_separators(strip_heredoc_bodies(command))):
        if is_shell_separator(token):
            flush(token)
            continue
        current.append(token)
    flush(None)
    return writes


def _record_heredoc_bash_writes(command: str, depth: int) -> list[tuple[str, str]]:
    if "<<" not in command:
        return []
    writes: list[tuple[str, str]] = []
    lines = command.split("\n")
    pending: list[tuple[str, bool, bool, bool, list[str], list[str], list[str]]] = []
    logical_scan_parts: list[str] = []

    def inspected_heredoc_content(
        body_text: str, *, preserve_body: bool, delimiter_quoted: bool
    ) -> str:
        if preserve_body:
            return ""
        if not delimiter_quoted and re.search(r"[$`]", body_text):
            return ""
        return body_text

    for raw in lines:
        line = raw.rstrip("\r")
        if pending:
            (
                delimiter,
                strip_tabs,
                preserve_body,
                delimiter_quoted,
                targets,
                opaque_targets,
                body,
            ) = pending[0]
            candidate = line.lstrip("\t") if strip_tabs else line
            if candidate == delimiter:
                body_text = "\n".join(body)
                if preserve_body:
                    writes.extend(_bash_write_operations(body_text, depth=depth + 1))
                inspected_content = inspected_heredoc_content(
                    body_text,
                    preserve_body=preserve_body,
                    delimiter_quoted=delimiter_quoted,
                )
                for target in targets:
                    writes.append((target, inspected_content))
                for target in opaque_targets:
                    writes.append((target, ""))
                pending.pop(0)
            else:
                body.append(raw)
            continue

        if _line_has_unquoted_continuation(line):
            logical_scan_parts.append(line[:-1])
            continue

        logical_scan_parts.append(line)
        logical_line = "".join(logical_scan_parts)
        for (
            delimiter,
            strip_tabs,
            preserve_body,
            delimiter_quoted,
            op_start,
        ) in _heredoc_delimiters_on_line(logical_line):
            tokens = _simple_command_spanning(logical_line, op_start)
            targets = bash_write_targets_from_tokens(tokens)
            opaque_targets = _opaque_output_redirect_targets(tokens)
            pending.append(
                (
                    delimiter,
                    strip_tabs,
                    preserve_body,
                    delimiter_quoted,
                    targets,
                    opaque_targets,
                    [],
                )
            )
        logical_scan_parts = []
    for (
        _delimiter,
        _strip_tabs,
        preserve_body,
        delimiter_quoted,
        targets,
        opaque_targets,
        body,
    ) in pending:
        body_text = "\n".join(body)
        if preserve_body:
            writes.extend(_bash_write_operations(body_text, depth=depth + 1))
        inspected_content = inspected_heredoc_content(
            body_text,
            preserve_body=preserve_body,
            delimiter_quoted=delimiter_quoted,
        )
        for target in targets:
            writes.append((target, inspected_content))
        for target in opaque_targets:
            writes.append((target, ""))
    return writes


def _bash_write_operations(
    command: str, *, depth: int = 0, max_depth: int = 5
) -> list[tuple[str, str]]:
    if depth > max_depth:
        return []
    writes = _record_heredoc_bash_writes(command, depth)
    writes.extend(_record_literal_bash_writes(command))
    for tokens in simple_commands(command, strip_heredocs=True):
        payload = nested_shell_payload(invocation_tokens(tokens))
        if payload:
            writes.extend(_bash_write_operations(payload, depth=depth + 1))
    return writes


def bash_write_operations(command: str) -> list[tuple[str, str]]:
    """Best-effort ``(path, content)`` pairs for Bash-authored file writes."""
    return _bash_write_operations(command)


def normalize_pathish(token: str) -> str:
    normalized = token
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def token_matches_declared(actual: str, declared: str, *, command_position: bool) -> bool:
    if actual == declared:
        return True
    if command_position and PurePosixPath(actual).name == declared:
        return True
    if "/" in declared:
        expected = normalize_pathish(declared)
        observed = normalize_pathish(actual)
        return observed == expected or observed.endswith(f"/{expected}")
    return False


def invocation_matches_declared(actual_tokens: list[str], declared_tokens: list[str]) -> bool:
    if len(actual_tokens) < len(declared_tokens):
        return False
    for index, declared in enumerate(declared_tokens):
        if not token_matches_declared(
            actual_tokens[index], declared, command_position=(index == 0)
        ):
            return False
    return True


def command_matches_validation(actual: str, declared: str) -> bool:
    """True when a Bash command invokes a declared validation command.

    The check is intentionally shell-segment based, not substring based. A
    command that merely prints or mentions `bash scripts/ci/all.sh` must not
    satisfy the finish-line gate. Known wrappers such as
    `agent-run exec -- bash scripts/ci/all.sh` are unwrapped before matching,
    and here-doc bodies are stripped so a validation command that only appears
    as data fed to another command (e.g. `cat <<EOF ... EOF`) is not credited.

    This is a best-effort static matcher: it cannot evaluate runtime control
    flow, so a validation command inside an uncalled function body or a
    not-taken `if`/loop branch may still be credited. The finish-line gate is
    the agent's own workflow guardrail and is intentionally waivable
    (`AGENT_RUNTIME_VALIDATION_WAIVER`), so this residual is acceptable.
    """
    if not actual or not declared:
        return False
    declared_invocations = [
        invocation_tokens(command)
        for command in simple_commands(declared.strip(), strip_heredocs=True)
    ]
    if not declared_invocations or any(not command for command in declared_invocations):
        return False
    actual_invocations = [
        invocation_tokens(command)
        for command in simple_commands(actual, strip_heredocs=True)
        if command
    ]
    return all(
        any(
            invocation_matches_declared(actual_tokens, declared_tokens)
            for actual_tokens in actual_invocations
        )
        for declared_tokens in declared_invocations
    )


def touch_marker(path: str) -> bool:
    """Atomically create/refresh an empty marker without following a final symlink."""
    temporary = ""
    try:
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.",
            suffix=".tmp",
            dir=directory,
        )
        os.close(descriptor)
        os.replace(temporary, path)
        return True
    except OSError:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        return False
