#!/usr/bin/env python3
"""PreToolUse hook: block direct GitHub PR and GitLab MR creation.

Shared runtime-kit logic accepts the neutral `AGENT_RUNTIME_PR_SKILL` marker.
The value is still an exact-name allow-list, not a broad bypass.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path, PurePosixPath

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    emit_block,
    invocation_is_unresolved_nested,
    invocation_tokens,
    marker_environment_before_invocation,
    nested_shell_payload,
    opaque_invocation_candidates,
    read_payload,
    simple_commands,
)

_BUILTIN_PR_SKILLS: frozenset[str] = frozenset(
    {
        "deliver-pr",
        "pr:deliver-pr",
    }
)
_BUILTIN_MR_SKILLS: frozenset[str] = frozenset(
    {
        "deliver-pr",
        "pr:deliver-pr",
    }
)


def _overlay_path() -> Path:
    env_override = os.environ.get("AGENT_RUNTIME_PR_SKILLS_OVERLAY_FILE")
    if env_override:
        return Path(env_override)
    return Path(__file__).resolve().parent.parent / "private" / "pr-skills-overlay.txt"


def _load_overlay_skills() -> frozenset[str]:
    path = _overlay_path()
    if not path.is_file():
        return frozenset()
    extras: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        extras.add(line)
    return frozenset(extras)


_OVERLAY_SKILLS = _load_overlay_skills()
ALLOWED_PR_SKILLS: frozenset[str] = _BUILTIN_PR_SKILLS | _OVERLAY_SKILLS
ALLOWED_MR_SKILLS: frozenset[str] = _BUILTIN_MR_SKILLS | _OVERLAY_SKILLS
MARKER_ENV_NAMES = ("AGENT_RUNTIME_PR_SKILL",)

BLOCK_REASON_PR = (
    "Do not run gh pr create directly. Open PRs through an audited PR workflow "
    "so the body follows the standard template and the call is traceable. "
    "Skill bypass: prefix the command with AGENT_RUNTIME_PR_SKILL=<exact "
    "allowed skill name>."
)

BLOCK_REASON_MR = (
    "Do not create GitLab MRs directly. Use an audited MR workflow so the "
    "description, branch handling, and source-branch policy are reviewable. "
    "Skill bypass: prefix the command with AGENT_RUNTIME_PR_SKILL=<exact "
    "allowed MR skill name>."
)

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*")
CLI_OPTIONS_WITH_VALUE = {"-R", "--repo"}
CLI_OPTIONS_WITH_VALUE_PREFIXES = ("--repo=",)
GLAB_API_METHOD_FLAGS = {"-X", "--method"}
GLAB_API_POST_PARAMETER_FLAGS = {"-F", "--field", "-f", "--raw-field", "--form"}
# Match only the create endpoint itself: the bare path, optionally with a
# single trailing slash, at end-of-path or before a query/fragment. A "/"
# followed by a sub-resource segment must NOT match, or sub-resource POSTs
# (review comments, replies, reviews, reactions, MR notes) are wrongly blocked
# as PR/MR creates (agent-runtime-kit#474). Blocking the trailing-slash form
# (.../pulls/, .../merge_requests/) too is defense-in-depth: GitHub/GitLab 404
# it today, but the guard must not depend on upstream routing strictness.
MR_ENDPOINT_RE = re.compile(r"(?:^|/)merge_requests/?(?:$|[?#])")
PULLS_ENDPOINT_RE = re.compile(r"(?:^|/)repos/[^/\s]+/[^/\s]+/pulls/?(?:$|[?#])")


def basename(token: str) -> str:
    return PurePosixPath(token).name


def is_assignment(token: str) -> bool:
    return bool(ASSIGNMENT_RE.match(token))


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


def cli_command_index(simple_command: list[str], command_name: str) -> int | None:
    invocation = invocation_tokens(simple_command)
    if not invocation:
        return None
    return 0 if basename(invocation[0]) == command_name else None


def skip_cli_global_options(tokens: list[str], index: int) -> int:
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in CLI_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if any(token.startswith(prefix) for prefix in CLI_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
            continue
        if token.startswith("-R") and token != "-R":
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return index
    return index


def cli_subcommands(simple_command: list[str], command_name: str) -> list[str]:
    invocation = invocation_tokens(simple_command)
    if not invocation or basename(invocation[0]) != command_name:
        return []

    index = skip_cli_global_options(invocation, 1)
    return invocation[index:]


def invokes_gh_pr_create(simple_command: list[str]) -> bool:
    args = cli_subcommands(simple_command, "gh")
    return args[:2] == ["pr", "create"]


def api_has_pulls_endpoint(args: list[str]) -> bool:
    return any(PULLS_ENDPOINT_RE.search(token) for token in args)


def invokes_gh_api_pr_create(simple_command: list[str]) -> bool:
    args = cli_subcommands(simple_command, "gh")
    if args[:1] != ["api"]:
        return False
    api_args = args[1:]
    return api_method_is_post(api_args) and api_has_pulls_endpoint(api_args)


def invokes_glab_mr_create(simple_command: list[str]) -> bool:
    args = cli_subcommands(simple_command, "glab")
    return args[:2] == ["mr", "create"]


def api_method_is_post(args: list[str]) -> bool:
    for index, token in enumerate(args):
        upper = token.upper()
        if token in GLAB_API_METHOD_FLAGS and index + 1 < len(args):
            return args[index + 1].upper() == "POST"
        if upper in {"-XPOST", "-X=POST", "--METHOD=POST"}:
            return True
        if upper.startswith("--METHOD="):
            return upper.split("=", 1)[1] == "POST"
        if token in GLAB_API_POST_PARAMETER_FLAGS:
            return True
        if any(token.startswith(f"{flag}=") for flag in GLAB_API_POST_PARAMETER_FLAGS):
            return True
        if token.startswith(("-f", "-F")) and token not in {"-f", "-F"}:
            return True
    return False


def api_has_merge_requests_endpoint(args: list[str]) -> bool:
    return any(MR_ENDPOINT_RE.search(token) for token in args)


def invokes_glab_api_mr_create(simple_command: list[str]) -> bool:
    args = cli_subcommands(simple_command, "glab")
    if args[:1] != ["api"]:
        return False
    api_args = args[1:]
    return api_method_is_post(api_args) and api_has_merge_requests_endpoint(api_args)


def marker_value_before_command(
    simple_command: list[str], command_name: str, marker: str | None = None
) -> str | None:
    invocation = invocation_tokens(simple_command)
    if not invocation or basename(invocation[0]) != command_name:
        return None
    return marker_value_before_invocation(simple_command, marker)


def marker_value_before_invocation(
    tokens: list[str], marker: str | None = None
) -> str | None:
    inherited = {MARKER_ENV_NAMES[0]: marker} if marker is not None else {}
    environment = marker_environment_before_invocation(
        tokens, MARKER_ENV_NAMES, inherited
    )
    return environment.get(MARKER_ENV_NAMES[0])


def command_creates_pr_or_mr(
    command: str,
    *,
    inherited_pr_marker: str | None = None,
    inherited_mr_marker: str | None = None,
    depth: int = 0,
    max_depth: int = 5,
) -> str | None:
    if depth > max_depth:
        return None
    for simple_command in simple_commands(command):
        invocation = invocation_tokens(simple_command)
        for candidate in opaque_invocation_candidates(invocation, {"gh", "glab"}):
            if invocation_is_unresolved_nested(candidate):
                return BLOCK_REASON_PR
            executable = basename(candidate[0])
            if executable == "gh" and (
                invokes_gh_pr_create(candidate) or invokes_gh_api_pr_create(candidate)
            ):
                return BLOCK_REASON_PR
            if executable == "glab" and (
                invokes_glab_mr_create(candidate)
                or invokes_glab_api_mr_create(candidate)
            ):
                return BLOCK_REASON_MR
        pr_marker = marker_value_before_command(
            simple_command, "gh", inherited_pr_marker
        )
        if (
            invokes_gh_pr_create(simple_command)
            or invokes_gh_api_pr_create(simple_command)
        ) and pr_marker not in ALLOWED_PR_SKILLS:
            return BLOCK_REASON_PR
        mr_marker = marker_value_before_command(
            simple_command, "glab", inherited_mr_marker
        )
        if (
            invokes_glab_mr_create(simple_command)
            or invokes_glab_api_mr_create(simple_command)
        ) and mr_marker not in ALLOWED_MR_SKILLS:
            return BLOCK_REASON_MR
        payload = nested_shell_payload(invocation)
        if payload:
            if depth >= max_depth:
                return BLOCK_REASON_PR
            blocked = command_creates_pr_or_mr(
                payload,
                inherited_pr_marker=marker_value_before_invocation(
                    simple_command, inherited_pr_marker
                ),
                inherited_mr_marker=marker_value_before_invocation(
                    simple_command, inherited_mr_marker
                ),
                depth=depth + 1,
                max_depth=max_depth,
            )
            if blocked:
                return blocked
    return None


def main() -> int:
    command = command_from(read_payload())
    if not command:
        return ALLOW

    reason = command_creates_pr_or_mr(command)
    if reason:
        if reason == BLOCK_REASON_PR:
            emit_block(BLOCK_REASON_PR)
        else:
            emit_block(BLOCK_REASON_MR)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
