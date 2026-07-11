#!/usr/bin/env python3
"""UserPromptSubmit hook: remind high-impact skill workflows to retain usage records."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import ALLOW, read_payload


PROMPT_KEYS = ("prompt", "user_prompt", "message", "input")
CONFIG_PATH = Path(__file__).with_name("skill-usage-reminder.skills.json")
MATCH_MODES = {"action_or_explicit", "explicit_only"}


ACTION_HINTS = (
    "use",
    "run",
    "execute",
    "do ",
    "create",
    "open",
    "close",
    "merge",
    "find",
    "fix",
    "deliver",
    "release",
    "publish",
    "review ",
    "scan",
    "implement",
    "migrate",
    "archive",
)


def load_skill_reminders(path: Path = CONFIG_PATH) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text("utf-8"))
    if not isinstance(raw, list):
        raise ValueError("skill usage reminder catalog must be a JSON list")

    reminders: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"catalog entry {index} must be an object")

        skill = item.get("skill")
        aliases = item.get("aliases")
        match_mode = item.get("match_mode")
        tier = item.get("tier")
        reason = item.get("reason")
        record_when = item.get("record_when")

        if not isinstance(skill, str) or not skill:
            raise ValueError(f"catalog entry {index} has invalid skill")
        if skill in seen:
            raise ValueError(f"duplicate skill in reminder catalog: {skill}")
        seen.add(skill)
        if not isinstance(aliases, list) or not aliases or not all(isinstance(alias, str) and alias for alias in aliases):
            raise ValueError(f"catalog entry {skill} has invalid aliases")
        if match_mode not in MATCH_MODES:
            raise ValueError(f"catalog entry {skill} has invalid match_mode")
        if not isinstance(tier, str) or not tier:
            raise ValueError(f"catalog entry {skill} has invalid tier")
        if not isinstance(reason, str) or not reason:
            raise ValueError(f"catalog entry {skill} has invalid reason")
        if not isinstance(record_when, str) or not record_when:
            raise ValueError(f"catalog entry {skill} has invalid record_when")

        reminders.append(
            {
                "skill": skill,
                "aliases": aliases,
                "match_mode": match_mode,
                "tier": tier,
                "reason": reason,
                "record_when": record_when,
            }
        )
    return reminders


def alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9_-]){re.escape(alias.lower())}(?![a-z0-9_-])")


def alias_in_text(text: str, alias: str) -> bool:
    return alias_pattern(alias).search(text) is not None


def strip_aliases(text: str, aliases: Iterable[str]) -> str:
    stripped = text
    for alias in aliases:
        stripped = alias_pattern(alias).sub(" ", stripped)
    return stripped


def alias_is_action_phrase(alias: str) -> bool:
    # An alias counts as an action phrase when it carries an action verb as a
    # whole word -- not only as a leading prefix -- so a CLI-shaped alias whose
    # verb trails the object (e.g. `evidence migrate`) still reads as an action.
    return any(
        re.search(rf"(?<![a-z0-9_-]){re.escape(hint.strip())}(?![a-z0-9_-])", alias)
        for hint in ACTION_HINTS
    )


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_strings(nested)
        return
    if isinstance(value, list | tuple):
        for nested in value:
            yield from _iter_strings(nested)


def prompt_text(payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key in PROMPT_KEYS:
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)

    # Some clients wrap prompt content under nested message arrays. Keep this as
    # a fallback so exact skill links still trigger without depending on shape.
    if not parts:
        parts.extend(_iter_strings(payload))
    return "\n".join(parts)


def explicit_skill_invocation(text: str, skill: str) -> bool:
    return any(
        marker in text
        for marker in (
            f"${skill}",
            f"[${skill}]",
            f"<name>{skill}</name>",
            f"/{skill}/SKILL.md".lower(),
        )
    )


def matched_skills(prompt: str, reminders: Iterable[Mapping[str, Any]] | None = None) -> list[str]:
    if reminders is None:
        reminders = load_skill_reminders()

    text = prompt.lower()
    matches: list[str] = []
    reminder_list = list(reminders)
    all_aliases = tuple(
        str(alias).lower()
        for reminder in reminder_list
        for alias in reminder["aliases"]
    )
    action_text = strip_aliases(text, all_aliases)

    for reminder in reminder_list:
        skill = str(reminder["skill"])
        aliases = tuple(str(alias).lower() for alias in reminder["aliases"])
        explicit = explicit_skill_invocation(text, skill)
        if reminder["match_mode"] == "explicit_only":
            if explicit:
                matches.append(skill)
            continue

        matched_aliases = [alias for alias in aliases if alias_in_text(text, alias)]
        alias_match = bool(matched_aliases)
        actionish = any(hint in action_text for hint in ACTION_HINTS) or any(
            alias_is_action_phrase(alias) for alias in matched_aliases
        )
        if alias_match and (actionish or explicit):
            matches.append(skill)
    return matches


def list_reminders(output_format: str) -> int:
    reminders = load_skill_reminders()
    if output_format == "json":
        sys.stdout.write(json.dumps(reminders, indent=2, ensure_ascii=False))
        sys.stdout.write("\n")
        return ALLOW

    header = "skill\ttier\tmatch_mode\taliases"
    sys.stdout.write(f"{header}\n")
    for reminder in reminders:
        aliases = ", ".join(str(alias) for alias in reminder["aliases"])
        sys.stdout.write(
            f"{reminder['skill']}\t{reminder['tier']}\t{reminder['match_mode']}\t{aliases}\n"
        )
    return ALLOW


def supports_workflow_owners() -> bool:
    if not shutil.which("skill-usage"):
        return False
    try:
        completed = subprocess.run(
            ["skill-usage", "init", "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and "--owner-kind" in completed.stdout


def emit_reminder(skills: list[str]) -> None:
    skill_list = ", ".join(skills)
    product = os.environ.get("AGENT_RUNTIME_PRODUCT", "agent-runtime")
    if supports_workflow_owners():
        record_contract = """retain one outermost skill-usage.record.v2 envelope for the parent outcome workflow (not one record per primitive):
  record_dir="$(agent-out project --topic skill-usage --mkdir)"
  skill-usage init --out "$record_dir" --owner-kind workflow --owner-id "<outermost-outcome>" ...; skill-usage record-validation --out "$record_dir" ...; skill-usage record-outcome --out "$record_dir" ...; skill-usage verify --out "$record_dir" --format json"""
    else:
        record_contract = """retain one compatibility skill-usage.record.v1 envelope for the parent skill workflow:
  record_dir="$(agent-out project --topic skill-usage --mkdir)"
  skill-usage init --out "$record_dir" --skill "<parent-skill>" ...; skill-usage record-validation --out "$record_dir" ...; skill-usage record-outcome --out "$record_dir" ...; skill-usage verify --out "$record_dir" --format json"""
    context = f"""[agent-runtime-kit:{product}] High-impact outcome workflow detected: {skill_list}.
If this turn actually invokes the skill and performs file edits, tool/API calls, validation, delivery, external lookup, or durable artifact creation, {record_contract}
Keep detailed evidence in typed child records and link them from the envelope. Curate only important unresolved or reusable workflow gaps into heuristic-inbox cases under the shared Heuristic System root. This hook is a reminder only; do not auto-generate or hand-edit records. See the rendered skill-usage skill under the active runtime home."""
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    )
    sys.stdout.write("\n")


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] != "--list":
            sys.stderr.write("usage: skill-usage-reminder.py [--list [--format text|json]]\n")
            return 1
        output_format = "text"
        if len(sys.argv) == 4 and sys.argv[2] == "--format":
            output_format = sys.argv[3]
        elif len(sys.argv) != 2:
            sys.stderr.write("usage: skill-usage-reminder.py [--list [--format text|json]]\n")
            return 1
        if output_format not in {"text", "json"}:
            sys.stderr.write("usage: skill-usage-reminder.py [--list [--format text|json]]\n")
            return 1
        return list_reminders(output_format)

    if (
        os.environ.get("AGENT_RUNTIME_SUPPRESS_SKILL_USAGE_REMINDER") == "1"
        or os.environ.get("AGENT_KIT_SUPPRESS_SKILL_USAGE_REMINDER") == "1"
        or os.environ.get("CLAUDE_KIT_SUPPRESS_SKILL_USAGE_REMINDER") == "1"
    ):
        return ALLOW

    payload = read_payload()
    prompt = prompt_text(payload)
    if not prompt:
        return ALLOW

    try:
        skills = matched_skills(prompt)
    except (OSError, ValueError, json.JSONDecodeError):
        return ALLOW
    if not skills:
        return ALLOW

    emit_reminder(skills)
    return ALLOW


if __name__ == "__main__":
    raise SystemExit(main())
