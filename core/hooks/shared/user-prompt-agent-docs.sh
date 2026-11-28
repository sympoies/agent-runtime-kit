#!/usr/bin/env bash
# Project-owned read-back paths for Codex SessionStart, including compaction.
# The project launcher supplies a JSON array; never discover project roles or
# execute project code here. File contents stay outside the hook output, with
# one bounded exception: on compact, the single file named by
# AGENT_RUNTIME_PROJECT_CONTEXT_FILE is injected verbatim when it passes every
# check below; any failed check falls back to the path list alone.
set -uo pipefail

[[ "${AGENT_RUNTIME_PRODUCT:-}" == "codex" ]] || exit 0
[[ -n "${AGENT_RUNTIME_PROJECT_READBACK_PATHS:-}" || -n "${AGENT_RUNTIME_PROJECT_CONTEXT_FILE:-}" ]] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

python3 -c '
import json
import os
from pathlib import Path
import stat
import sys

CONTEXT_FILE_MAX_BYTES = 10240

try:
    payload = json.load(sys.stdin)
except (ValueError, OSError):
    raise SystemExit(0)
if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
    raise SystemExit(0)
if payload.get("source") not in {"startup", "resume", "clear", "compact"}:
    raise SystemExit(0)

try:
    paths = json.loads(os.environ.get("AGENT_RUNTIME_PROJECT_READBACK_PATHS") or "[]")
except ValueError:
    paths = []
if not isinstance(paths, list):
    paths = []

existing = []
for value in paths:
    if not isinstance(value, str):
        continue
    path = Path(value)
    try:
        if path.is_absolute() and path.is_file():
            existing.append(value)
    except (OSError, ValueError):
        continue


def context_file_text():
    # Compact only. Absolute regular file, final component not a symlink,
    # owned by the current user, non-empty, within the size cap, valid UTF-8.
    # Any failure means no injection and no error.
    value = os.environ.get("AGENT_RUNTIME_PROJECT_CONTEXT_FILE", "")
    if payload.get("source") != "compact" or not value or not os.path.isabs(value):
        return ""
    try:
        fd = os.open(value, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except (OSError, ValueError):
        return ""
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or not 0 < info.st_size <= CONTEXT_FILE_MAX_BYTES):
            return ""
        data = b""
        while len(data) <= CONTEXT_FILE_MAX_BYTES:
            chunk = os.read(fd, CONTEXT_FILE_MAX_BYTES + 1 - len(data))
            if not chunk:
                break
            data += chunk
        if len(data) > CONTEXT_FILE_MAX_BYTES:
            return ""
        return data.decode("utf-8").rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return ""
    finally:
        os.close(fd)


card = context_file_text()
parts = []
if existing:
    parts.append("Before continuing, read these project-supplied files:\n" + "\n".join(
        "- " + json.dumps(path, ensure_ascii=False) for path in existing
    ))
if card.strip():
    parts.append(card)
if not parts:
    raise SystemExit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart", "additionalContext": "\n\n".join(parts),
}}))
'
