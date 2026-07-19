#!/usr/bin/env python3
"""Run Claude mutation gates sequentially before operation admission.

Claude executes sibling hooks for a matching event concurrently.  Admission
must therefore share one command process with every blocker that precedes it;
otherwise a denied tool can still acquire an operation lease and never receive
a PostToolUse outcome.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

SEQUENCES = {
    "Bash": (
        "pre-edit-intent-gate.py",
        "checkout-lease-guard.py",
        "block-direct-git-commit.py",
        "block-unsafe-default-delivery.py",
        "block-direct-git-worktree.py",
        "semantic-commit-body-gate.py",
        "block-claude-coauthor-trailer.py",
        "block-direct-pr-create.py",
        "forge-label-reminder.py",
        "block-direct-python.py",
        "mcp-secret-scan.py",
        "block-project-memory-write.py",
        "memory-write-principle-reminder.py",
        "portable-paths-scan.py",
        "finish-line-record.py",
        "session-coordination-guard.py",
    ),
    "Write": (
        "mcp-secret-scan.py",
        "block-project-memory-write.py",
        "memory-write-principle-reminder.py",
        "agent-scope-lock-guard.py",
        "portable-paths-scan.py",
        "pre-edit-intent-gate.py",
        "checkout-lease-guard.py",
        "finish-line-record.py",
        "session-coordination-guard.py",
    ),
    "Edit": (),
    "NotebookEdit": (),
    "MultiEdit": (
        "block-project-memory-write.py",
        "memory-write-principle-reminder.py",
        "agent-scope-lock-guard.py",
        "pre-edit-intent-gate.py",
        "checkout-lease-guard.py",
        "finish-line-record.py",
        "session-coordination-guard.py",
    ),
}
SEQUENCES["Edit"] = SEQUENCES["Write"]
SEQUENCES["NotebookEdit"] = SEQUENCES["Write"]

DEFAULT_HOOK_TIMEOUT = 10
HOOK_TIMEOUTS = {
    "pre-edit-intent-gate.py": 20,
    "checkout-lease-guard.py": 25,
    "finish-line-record.py": 20,
    "session-coordination-guard.py": 55,
}


def tool_name(payload: Mapping[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def blocked(body: Mapping[str, Any]) -> bool:
    if body.get("decision") == "block":
        return True
    specific = body.get("hookSpecificOutput")
    return isinstance(specific, Mapping) and specific.get("permissionDecision") in {
        "deny",
        "block",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    sequence = SEQUENCES.get(tool_name(payload), ())
    if not sequence:
        return 0

    hook_dir = Path(__file__).resolve().parent
    contexts: list[str] = []
    messages: list[str] = []
    updated_input: dict[str, Any] | None = None
    for name in sequence:
        raw = json.dumps(payload)
        try:
            completed = subprocess.run(
                [str(hook_dir / name)],
                input=raw,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=HOOK_TIMEOUTS.get(name, DEFAULT_HOOK_TIMEOUT),
                env=os.environ.copy(),
            )
        except (OSError, subprocess.SubprocessError):
            completed = None
        if completed is None or completed.returncode != 0:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": "A sequential mutation prerequisite failed; retry after runtime recovery. [reason: prerequisite-hook-unavailable]",
                    }
                )
            )
            return 0
        output = completed.stdout.strip()
        if not output:
            continue
        try:
            body = json.loads(output)
        except json.JSONDecodeError:
            body = None
        if not isinstance(body, dict):
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": "A sequential mutation prerequisite returned an invalid response. [reason: prerequisite-hook-invalid]",
                    }
                )
            )
            return 0
        if blocked(body):
            print(json.dumps(body))
            return 0
        message = body.get("systemMessage")
        if isinstance(message, str) and message:
            messages.append(message)
        specific = body.get("hookSpecificOutput")
        if isinstance(specific, Mapping):
            context = specific.get("additionalContext")
            if isinstance(context, str) and context:
                contexts.append(context)
            candidate = specific.get("updatedInput")
            if isinstance(candidate, Mapping):
                updated_input = dict(candidate)
                payload["tool_input"] = updated_input

    response: dict[str, Any] = {}
    if messages:
        response["systemMessage"] = "\n".join(messages)
    if contexts or updated_input is not None:
        specific = {"hookEventName": "PreToolUse"}
        if contexts:
            specific["additionalContext"] = "\n".join(contexts)
        if updated_input is not None:
            specific["permissionDecision"] = "allow"
            specific["updatedInput"] = updated_input
        response["hookSpecificOutput"] = specific
    if response:
        print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
