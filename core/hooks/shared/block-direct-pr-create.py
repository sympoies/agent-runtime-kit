#!/usr/bin/env python3
"""PreToolUse: guard PR/MR creation and identity-bound raw GitHub writes.

Shared runtime-kit logic accepts the neutral `AGENT_RUNTIME_PR_SKILL` marker.
The value is still an exact-name allow-list, not a broad bypass.
"""

from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

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
    simple_commands_with_nested_shells,
    is_managed_cli_home_bin,
    resolves_within_its_directory,
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
    "Do not run gh pr create directly. Open PRs through the deliver-pr "
    "workflow with `forge-cli pr deliver` (or `forge-cli pr create` for a "
    "create-only record) so the body follows the standard template and the "
    "call is traceable. Skill bypass: prefix the command with "
    "AGENT_RUNTIME_PR_SKILL=<exact allowed skill name>."
)

BLOCK_REASON_MR = (
    "Do not create GitLab MRs directly. Open MRs through the deliver-pr "
    "workflow with `forge-cli pr deliver` (or `forge-cli pr create` for a "
    "create-only record) so the description, branch handling, and "
    "source-branch policy are reviewable. Skill bypass: prefix the command "
    "with AGENT_RUNTIME_PR_SKILL=<exact allowed MR skill name>."
)

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


# This is a shell guard, not an interpreter or credential boundary. Only the
# launch environment and authenticated broker projection establish binding;
# command-local env clearing and the PR-skill marker cannot remove it.
GITHUB_WRITES = {
    "issue": {"create", "new", "develop", "comment", "close", "edit", "reopen", "delete",
              "lock", "unlock", "pin", "unpin", "transfer"},
    "pr": {"create", "new", "comment", "close", "edit", "reopen", "merge", "ready",
           "review", "lock", "unlock", "revert", "update-branch"},
    "release": {"create", "upload", "edit", "delete", "delete-asset"},
    "workflow": {"run", "enable", "disable"},
}
SUPPORTED_WRITES = {
    "issue": {"create", "comment", "close", "edit", "reopen"},
    "pr": {"create", "comment", "close", "edit", "merge", "ready", "review"},
}
MISSING_COMMANDS = "https://github.com/sympoies/nils-cli/issues/2138"


def write_hint(group: str, verb: str = "") -> str:
    if verb in SUPPORTED_WRITES.get(group, set()):
        return f"Use `forge-cli {group} {verb}` through the owning workflow."
    missing = {
        "release": "release", "workflow": "workflow",
        "comment-mutation": "comment edit/delete",
    }.get(group)
    if missing:
        return (
            f"forge-cli has no {missing} command yet ({MISSING_COMMANDS}). "
            "Ask the workflow owner to use an explicitly authorized, identity-aware "
            "delivery path or defer until the typed command is available; do not "
            "fall back to the host's default gh account."
        )
    return (
        "Use the matching typed `forge-cli issue` or `forge-cli pr` command "
        "through the owning workflow. If unavailable, ask the workflow owner "
        f"for an identity-aware path ({MISSING_COMMANDS})."
    )


def api_hint(endpoint: str, method: str) -> str:
    path = urlsplit(endpoint).path.strip("/")
    if "/releases" in path:
        return write_hint("release")
    if "/actions/" in path or path.endswith("/dispatches"):
        return write_hint("workflow")
    if re.search(r"/(?:issues|pulls)/comments/[^/]+$", path):
        return write_hint("comment-mutation")
    if re.search(r"/issues/[^/]+/comments$", path) and method == "POST":
        return write_hint("issue", "comment")
    if re.search(r"/pulls/[^/]+/merge$", path):
        return write_hint("pr", "merge")
    if re.search(r"/pulls/[^/]+/reviews$", path):
        return write_hint("pr", "review")
    if re.search(r"/(issues|pulls)(?:/[^/]+)?$", path):
        group = "pr" if "/pulls" in path else "issue"
        return write_hint(group, "create" if method == "POST" else "edit")
    return write_hint("api")


def request_parts(args: list[str], *, curl: bool = False) -> tuple[str, list[str], list[str], bool]:
    """Explicit methods override implicit fields regardless of flag order."""
    method = ""
    endpoints: list[str] = []
    fields: list[str] = []
    input_body = False
    upload = False
    read_method = ""
    value_flags = {"-X", "--request" if curl else "--method"}
    upload_flags = {"-T", "--upload-file"} if curl else set()
    field_flags = ({"-d", "--data", "--data-ascii", "--data-raw", "--data-binary", "--data-urlencode",
                    "--json", "-F", "--form", "--form-string"} if curl else
                   {"-f", "-F", "--field", "--raw-field"})
    other_values = ({"-H", "--header", "-o", "--output", "-u", "--user", "--proto-default"} if curl else
                    {"-H", "--header", "--hostname", "--jq", "-q", "--template", "-t",
                     "--cache", "--preview", "-p"})
    i = 0
    while i < len(args):
        token = args[i]
        flag, sep, value = token.partition("=")
        if curl and token in {"-G", "--get", "-I", "--head"}:
            read_method = "HEAD" if token in {"-I", "--head"} else "GET"
        elif flag in value_flags | field_flags | upload_flags | other_values | {"--input", "--url"}:
            if not sep:
                i += 1
                value = args[i] if i < len(args) else ""
            if flag in value_flags:
                method = value.upper()
            elif flag in field_flags:
                fields.append(value)
            elif flag in upload_flags:
                upload = True
            elif flag == "--input":
                input_body = True
            elif flag == "--url":
                endpoints.append(value)
        elif token.startswith("-X") and len(token) > 2:
            method = token[2:].lstrip("=").upper()
        elif curl and token.startswith("-T") and len(token) > 2:
            upload = True
        elif token.startswith(("-d", "-F") if curl else ("-f", "-F")) and len(token) > 2:
            fields.append(token[2:])
        elif not token.startswith("-") and (curl or not endpoints):
            endpoints.append(token)
        i += 1
    implicit_method = "PUT" if upload else read_method or ("POST" if fields or input_body else "GET")
    return method or implicit_method, endpoints, fields, input_body


def graphql_tokens(document: str) -> str | None:
    """Mask strings and comments in one pass; incomplete strings are unverified."""
    tokens: list[str] = []
    i = 0
    while i < len(document):
        if document[i] == "#":
            while i < len(document) and document[i] not in "\r\n":
                i += 1
        elif document[i] == '"':
            block = document.startswith('"""', i)
            i += 3 if block else 1
            while i < len(document):
                if block and document.startswith('\\"""', i):
                    i += 4
                elif block and document.startswith('"""', i):
                    i += 3
                    break
                elif not block and document[i] == '"':
                    i += 1
                    break
                elif not block and document[i] == "\\":
                    i += 2
                elif not block and document[i] in "\r\n":
                    return None
                else:
                    i += 1
            else:
                return None
            tokens.append('""')
        else:
            tokens.append(document[i])
            i += 1
    return "".join(tokens)


def gh_switches(args: list[str]) -> set[str]:
    """Switches outside value slots; a body of '--help' is still a write."""
    values = {"--body", "-b", "--body-file", "-F", "--title", "-t", "--comment", "-c",
              "--reason", "-r", "--assignee", "-a", "--label", "-l", "--milestone", "-m",
              "--project", "-p", "--template", "-T", "--recover", "--name", "--base",
              "--head", "--reviewer", "--subject", "--repo", "-R", "--add-assignee",
              "--remove-assignee", "--add-label", "--remove-label", "--add-project",
              "--remove-project", "--method", "-X", "--field", "-f", "--raw-field",
              "--input", "--header", "-H", "--hostname", "--jq", "-q", "--cache", "--preview"}
    switches: set[str] = set()
    i = 0
    while i < len(args):
        token = args[i]
        flag, sep, _ = token.partition("=")
        if flag in values:
            i += 1 if sep else 2
            continue
        if token.startswith("-"):
            switches.add(flag)
        i += 1
    return switches


def raw_write_hint(tokens: list[str]) -> str | None:
    invocation = invocation_tokens(tokens)
    if not invocation:
        return None
    executable = basename(invocation[0])
    if executable == "gh":
        args = cli_subcommands(tokens, "gh")
        switches = gh_switches(args)
        # Only an unambiguous help-only form is exempt. In a larger argv,
        # '--help' can be data for a value option (e.g. release --notes).
        if len(args) == 3 and args[2] in {"--help", "-h"}:
            return None
        if len(args) >= 2 and args[1] in GITHUB_WRITES.get(args[0], set()):
            if args[:2] == ["issue", "develop"] and "--list" in switches:
                return None
            if args[1] == "comment" and switches & {"--edit-last", "--delete-last"}:
                return write_hint("comment-mutation")
            return write_hint(args[0], "create" if args[1] == "new" else args[1])
        if args[:1] != ["api"]:
            return None
        method, endpoints, fields, input_body = request_parts(args[1:])
        endpoint = endpoints[0] if endpoints else ""
        if urlsplit(endpoint).path.strip("/") == "graphql":
            queries = [field.partition("=")[2] for field in fields if field.startswith("query=")]
            # Inline query documents are reads even though GraphQL uses POST.
            # Files and variable documents cannot be proved read-only here.
            if not input_body and len(queries) == 1:
                query_tokens = graphql_tokens(queries[0])
                if query_tokens is not None:
                    query_tokens = query_tokens.lstrip()
                    if not re.search(r"\bmutation\b", query_tokens) and (
                        query_tokens.startswith("{") or re.match(r"query(?:\s|\(|\{|$)", query_tokens)
                    ):
                        return None
            return write_hint("api")
        if method not in {"GET", "HEAD", "OPTIONS"}:
            return api_hint(endpoint, method)
    elif executable == "curl":
        # --next resets curl's local request options; one transfer's GET must
        # never hide an earlier POST, nor inherit its method into a later read.
        groups: list[list[str]] = [[]]
        for token in invocation[1:]:
            if token in {"--next", "-:"}:
                groups.append([])
            else:
                groups[-1].append(token)
        for group in groups:
            method, endpoints, _, _ = request_parts(group, curl=True)
            if method in {"GET", "HEAD", "OPTIONS"}:
                continue
            for target in endpoints:
                try:
                    parsed = urlsplit(target if "://" in target else "//" + target)
                    if parsed.hostname == "api.github.com":
                        return api_hint(target, method)
                except ValueError:
                    continue
    return None


def provider_invocation(tokens: list[str]) -> list[str]:
    """Unwrap common literal process launchers without executing them."""
    invocation = invocation_tokens(tokens)
    for _ in range(5):
        if not invocation:
            break
        wrapper = basename(invocation[0])
        if wrapper not in {"timeout", "gtimeout", "nice", "nohup", "stdbuf"}:
            break
        index = 1
        value_options = {"-s", "--signal", "-k", "--kill-after", "-n", "--adjustment", "-i", "-o", "-e"}
        while index < len(invocation) and invocation[index].startswith("-"):
            option = invocation[index]
            if option == "--":
                index += 1
                break
            index += 2 if option in value_options else 1
        if wrapper in {"timeout", "gtimeout"}:
            index += 1  # duration precedes the launched command
        invocation = invocation_tokens(invocation[index:])
    return invocation


def command_raw_write(command: str, depth: int = 0) -> str | None:
    for tokens in simple_commands_with_nested_shells(command):
        invocation = provider_invocation(tokens)
        hint = raw_write_hint(invocation)
        if hint:
            return hint
        nested = nested_shell_payload(invocation)
        if nested and invocation != invocation_tokens(tokens) and depth < 5:
            hint = command_raw_write(nested, depth + 1)
            if hint:
                return hint
        for candidate in opaque_invocation_candidates(invocation, {"gh", "curl"}):
            hint = raw_write_hint(candidate)
            if hint:
                return hint
    return None


def trusted_broker() -> str | None:
    candidate = shutil.which("agent-session")
    if not candidate or not os.path.isabs(candidate):
        return None
    resolved = os.path.realpath(candidate)
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return None
    directory = os.path.dirname(candidate)
    configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "")
    if configured:
        roots = {os.path.realpath(p) for p in configured.split(os.pathsep) if p}
        return resolved if os.path.realpath(directory) in roots else None
    for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
        cellar = os.path.join(prefix, "Cellar", "nils-cli")
        if directory == os.path.join(prefix, "bin") and (
            resolves_within_its_directory(candidate, resolved)
            or os.path.commonpath((resolved, cellar)) == cellar
        ):
            return resolved
    if (directory == "/usr/bin" or is_managed_cli_home_bin(directory)) and resolves_within_its_directory(candidate, resolved):
        return resolved
    return None


def identity_binding() -> str:
    """bound/unbound/unverified; never read credentials or public board state."""
    if os.environ.get("FORGE_IDENTITY_PRINCIPAL", "").strip():
        return "bound"
    session = os.environ.get("AGENT_SESSION_ID", "").strip()
    incarnation = os.environ.get("AGENT_SESSION_RUNTIME_ID", "").strip()
    if not session or not incarnation:
        return "unbound"
    executable = trusted_broker()
    if not executable:
        return "unverified"
    try:
        result = subprocess.run(
            [executable, "broker", "identity", "--session", session, "--format", "json"],
            capture_output=True, text=True, timeout=2,
        )
        if len(result.stdout) > 65536:
            return "unverified"
        record = json.loads(result.stdout)
        if not isinstance(record, dict):
            return "unverified"
        if result.returncode != 0 or record.get("ok") is not True:
            error = record.get("error", {})
            if isinstance(error, dict) and error.get("code") == "identity_session_binding_missing":
                return "unbound"
            return "unverified"
        data = record.get("data")
        if (record.get("schema_version") == "cli.agent-session.broker-identity.v1"
            and isinstance(data, dict)
            and data.get("schema_version") == "agent-session.forge-binding.v1"
            and data.get("session_id") == session
            and data.get("session_incarnation") == incarnation
            and isinstance(data.get("initiator"), str) and data["initiator"]):
            return "bound"
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return "unverified"


def main() -> int:
    command = command_from(read_payload())
    if not command:
        return ALLOW

    hint = command_raw_write(command)
    if hint:
        binding = identity_binding()
        if binding != "unbound":
            detail = "Identity-bound session" if binding == "bound" else "Session forge binding could not be authenticated"
            emit_block(f"[forge-write: blocked] {detail}: raw GitHub writes are denied. {hint}")
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
