#!/usr/bin/env bash
# Project-owned read-back paths for Codex SessionStart, including compaction.
# The project launcher supplies a JSON array; never discover project roles or
# execute project code here. File contents remain outside the hook output.
set -uo pipefail

[[ "${AGENT_RUNTIME_PRODUCT:-}" == "codex" ]] || exit 0
[[ -n "${AGENT_RUNTIME_PROJECT_READBACK_PATHS:-}" ]] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

python3 -c '
import json
import os
from pathlib import Path
import sys

try:
    payload = json.load(sys.stdin)
    paths = json.loads(os.environ["AGENT_RUNTIME_PROJECT_READBACK_PATHS"])
except (ValueError, OSError):
    raise SystemExit(0)
if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
    raise SystemExit(0)
if payload.get("source") not in {"startup", "resume", "clear", "compact"}:
    raise SystemExit(0)
if not isinstance(paths, list):
    raise SystemExit(0)

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
if not existing:
    raise SystemExit(0)
context = "Before continuing, read these project-supplied files:\n" + "\n".join(
    "- " + json.dumps(path, ensure_ascii=False) for path in existing
)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart", "additionalContext": context,
}}))
'
