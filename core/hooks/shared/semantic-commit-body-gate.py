#!/usr/bin/env python3
"""PreToolUse hook: require a body on non-trivial semantic-commit commits."""

from __future__ import annotations

import re
import sys

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    emit_block,
    extract_message,
    is_semantic_commit_commit,
    iter_flag_values,
    read_message_file,
    read_payload,
)

BLOCK_REASON_TEMPLATE = (
    "semantic-commit message is missing a body\n"
    "  subject: {subject}\n"
    "  rule: non-trivial commits need 1-2 bullets explaining why and scope\n"
    "  fix: add a body — `\\n\\n- <reason>` via --message/--message-file,\n"
    "       or pass `--body-bullet <reason>` (a --trailer does not count)\n"
    "  ref: `semantic-commit commit --help`, and commit rules in\n"
    "       `core/policies/git-delivery.md`\n"
    "  escape hatch: add `[no-body]` in the subject if this is truly trivial"
)

TRIVIAL_TYPES = {"chore", "docs", "style", "build"}
TRIVIAL_KEYWORDS = ("bump", "refresh", "regenerate", "pin", "lockfile")


def split_subject_body(message: str) -> tuple[str, list[str]]:
    lines = message.splitlines()
    if not lines:
        return "", []
    subject = lines[0].rstrip()
    rest = lines[1:]
    while rest and not rest[0].strip():
        rest.pop(0)
    body_nonempty = [line for line in rest if line.strip()]
    return subject, body_nonempty


def is_trivial_subject(subject: str) -> bool:
    stripped = subject.strip()
    if not stripped:
        return False
    lower = stripped.lower()

    if "[no-body]" in lower:
        return True

    header_match = re.match(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?:", stripped)
    if header_match:
        commit_type = header_match.group("type")
        scope = (header_match.group("scope") or "").lower()
        if commit_type in TRIVIAL_TYPES:
            return True
        scope_tokens = re.split(r"[\s,/]+", scope)
        if any(token in ("ci", "deps") for token in scope_tokens):
            return True

    subject_words = re.findall(r"[a-z]+", lower)
    return any(keyword in subject_words for keyword in TRIVIAL_KEYWORDS)


def resolve_subject_body(command: str) -> tuple[str, list[str]] | None:
    """Recover (subject, non-empty body lines) from every message source a
    `semantic-commit commit` accepts: `--message`/`-m`, `--message-file`, and
    the structured `--type`/`--scope`/`--subject` + `--body-bullet` form.

    Returns None when no message content parses, so the gate stays out of the
    way of commands whose message it cannot see (e.g. an auto-generated body).
    `--trailer` is intentionally excluded: a trailer is not an explanatory body.
    """
    message = extract_message(command)
    if message is None:
        message = read_message_file(command)
    if message is not None:
        return split_subject_body(message)

    subjects = iter_flag_values(command, "--subject")
    if not subjects:
        return None
    subject = subjects[0].strip()
    types = iter_flag_values(command, "--type")
    if types:
        header = types[0].strip()
        scopes = iter_flag_values(command, "--scope")
        if scopes and scopes[0].strip():
            header += f"({scopes[0].strip()})"
        subject = f"{header}: {subject}"
    body_lines = [line for line in iter_flag_values(command, "--body-bullet") if line.strip()]
    return subject, body_lines


def main() -> int:
    command = command_from(read_payload())
    if not command or not is_semantic_commit_commit(command):
        return ALLOW

    resolved = resolve_subject_body(command)
    if resolved is None:
        return ALLOW

    subject, body_lines = resolved
    if not body_lines and not is_trivial_subject(subject):
        emit_block(BLOCK_REASON_TEMPLATE.format(subject=subject or "<unparsed>"))
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
