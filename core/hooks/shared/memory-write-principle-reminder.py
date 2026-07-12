#!/usr/bin/env python3
"""PreToolUse hook: remind memory-boundary governance on agent-memory writes.

Opt-in and NON-BLOCKING. Off by default; enabled only when the env flag
``AGENT_RUNTIME_MEMORY_WRITE_REMINDER`` is truthy. When enabled and a written
file path is a markdown note in the agent-memory store (or a per-product memory
directory), it injects a short PreToolUse reminder to apply the store's
AGENTS.md Memory Boundaries. It never blocks.
"""

from __future__ import annotations

import json
import os
import re
import sys

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    bash_copy_style_write_targets,
    bash_write_operations,
    command_from,
    file_paths_from_payload,
    read_payload,
)

# Opt-in gate. Off by default; the reminder is emitted only when one of these
# env vars is truthy. Same truthy set the other shared hooks use.
OPT_IN_ENV_NAMES = ("AGENT_RUNTIME_MEMORY_WRITE_REMINDER",)
TRUTHY_VALUES = {"1", "true", "yes"}

# Store-agnostic markdown notes: the agent-memory store (any subdir under
# .config/agent-memory such as global/, agents/, personas/) plus the per-product
# memory directories the block hook also covers. Matches ANY note, not just
# project_*.md.
MEMORY_NOTE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|/)\.claude/projects/[^/]+/memory/[^/]+\.md$"),
    re.compile(r"(?:^|/)\.config/agent-memory/(?:[^/]+/)*[^/]+\.md$"),
    re.compile(r"(?:^|/)\.codex/memories/(?:[^/]+/)*[^/]+\.md$"),
)

REMINDER = (
    "Writing to memory — apply core/policies/memory.md and the store's "
    "AGENTS.md Memory Boundaries. Write only to the active product's untrusted "
    "candidate root; never write curated global memory autonomously. "
    "Store a fact only if it is durable AND project-independent: host/machine "
    "environment, network and tailnet setup, account/workspace conventions, "
    "cross-cutting tooling behavior, and the user's stable preferences and "
    "habits. A single repo's architecture, deploy specifics, build/test loops, "
    "or per-project gotchas belong in that repo's AGENTS.md / DEVELOPMENT.md / "
    "docs/ — memory keeps at most a thin pointer (name + one-line what-it-is + "
    "where its docs live), never the project's internal knowledge. Promotion "
    "requires a reviewed dry-run and explicit user approval. This is a "
    "reminder, not a block."
)


def env_opt_in_enabled() -> bool:
    for name in OPT_IN_ENV_NAMES:
        if os.environ.get(name, "").lower() in TRUTHY_VALUES:
            return True
    return False


def is_memory_note_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("~/"):
        normalized = normalized[2:]
    return any(pattern.search(normalized) for pattern in MEMORY_NOTE_PATTERNS)


def emit_reminder() -> None:
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": REMINDER,
                }
            }
        )
    )
    sys.stdout.write("\n")


def main() -> int:
    # Opt-in gate: silent no-op unless explicitly enabled.
    if not env_opt_in_enabled():
        return ALLOW

    payload = read_payload()
    paths = file_paths_from_payload(payload)
    if str(payload.get("tool_name", "")) == "Bash":
        command = command_from(payload)
        paths.extend(path for path, _content in bash_write_operations(command))
        paths.extend(bash_copy_style_write_targets(command))
    if any(is_memory_note_path(path) for path in paths):
        emit_reminder()
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
