#!/usr/bin/env python3
"""PreToolUse hook: remind on unlabeled forge-cli record creation.

Identity routing is environment-owned. A private installation can place an
executable router at the front of PATH, while public runtime-kit workflows keep
using portable forge semantics and ambient provider credentials by default.
This hook deliberately does not interpret shell execution or private identity
profiles.

The reminder covers `forge-cli` commands that create or deliver a labelable
provider record (`pr create`, `pr deliver`, `issue create`) without a `--label`
flag. Labels remain optional: an intentional no-label record can proceed by
prefixing the command with `FORGE_NO_LABELS=1` (or
`AGENT_RUNTIME_FORGE_NO_LABELS=1`).

`forge-cli` is provider-neutral, so `pr create` already covers both GitHub PRs
and GitLab MRs; there is no separate `mr` subcommand to match.
"""

from __future__ import annotations

import os
import sys
from pathlib import PurePosixPath

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    emit_block,
    is_assignment,
    invocation_tokens,
    read_payload,
    simple_commands,
)

REMINDER = (
    "forge-cli is about to create a record without any --label. Consider adding "
    "one or more --label flags so the record carries type / area / state / size "
    "/ workflow for triage and automation (follow forge-label-taxonomy; when the "
    "repo ships manifests/forge-labels.yaml, pick from that catalog). This is a "
    "reminder, not a hard requirement: if this record intentionally needs no "
    "label, re-run with FORGE_NO_LABELS=1 prefixed."
)

LABELABLE_SUBCOMMANDS = frozenset(
    {("pr", "create"), ("pr", "deliver"), ("issue", "create")}
)
LABEL_FLAG = "--label"
LABEL_FLAG_PREFIX = "--label="
HELP_FLAGS = frozenset({"--help", "-h"})
OVERRIDE_ENV_NAMES = ("FORGE_NO_LABELS", "AGENT_RUNTIME_FORGE_NO_LABELS")
TRUTHY_VALUES = {"1", "true", "yes"}

# forge-cli global options that consume the following token as their value, so
# the subcommand scan does not mistake a value for the `pr` / `issue` command.
FORGE_GLOBAL_OPTIONS_WITH_VALUE = {
    "--format",
    "--remote",
    "--provider",
    "--repo",
    "--store-root",
}


def env_override_enabled() -> bool:
    for name in OVERRIDE_ENV_NAMES:
        if os.environ.get(name, "").lower() in TRUTHY_VALUES:
            return True
    return False


def assignment_override_enabled(token: str) -> bool:
    if not is_assignment(token):
        return False
    name, value = token.split("=", 1)
    return name in OVERRIDE_ENV_NAMES and value.strip("\"'").lower() in TRUTHY_VALUES


def simple_command_bypass(tokens: list[str]) -> bool:
    """True when an inline `FORGE_NO_LABELS=1` assignment prefixes the command."""
    index = 0
    while index < len(tokens) and is_assignment(tokens[index]):
        if assignment_override_enabled(tokens[index]):
            return True
        index += 1

    if index >= len(tokens) or PurePosixPath(tokens[index]).name != "env":
        return False

    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return False
        if is_assignment(token):
            if assignment_override_enabled(token):
                return True
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
        return False
    return False


def leading_subcommand(rest: list[str]) -> tuple[str, str] | None:
    """Return the (command, action) pair after `forge-cli`, skipping globals."""
    positionals: list[str] = []
    index = 0
    while index < len(rest) and len(positionals) < 2:
        token = rest[index]
        if token == "--":
            index += 1
            while index < len(rest) and len(positionals) < 2:
                positionals.append(rest[index])
                index += 1
            break
        if token in FORGE_GLOBAL_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        positionals.append(token)
        index += 1
    if len(positionals) >= 2:
        return positionals[0], positionals[1]
    return None


def has_label_flag(rest: list[str]) -> bool:
    return any(
        token == LABEL_FLAG or token.startswith(LABEL_FLAG_PREFIX) for token in rest
    )


def is_help_request(rest: list[str]) -> bool:
    return any(token in HELP_FLAGS for token in rest)


def needs_label_reminder(tokens: list[str]) -> bool:
    invocation = invocation_tokens(tokens)
    if not invocation or PurePosixPath(invocation[0]).name != "forge-cli":
        return False
    rest = invocation[1:]
    if leading_subcommand(rest) not in LABELABLE_SUBCOMMANDS:
        return False
    if is_help_request(rest):
        return False
    return not has_label_flag(rest)


def main() -> int:
    command = command_from(read_payload())
    if not command:
        return ALLOW
    for tokens in simple_commands(command):
        if not tokens:
            continue
        if env_override_enabled() or simple_command_bypass(tokens):
            continue
        if needs_label_reminder(tokens):
            emit_block(REMINDER)
            return ALLOW
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
