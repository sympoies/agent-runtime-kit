#!/usr/bin/env python3
"""Require durable project-dev activation at observable edit boundaries.

Direct-edit targets are canonicalized and checked per repository. Bash is
checked against its working repository only: a pre-tool hook cannot observe
shell-expanded filesystem destinations reliably, so cross-repository shell
mutations must run with the target repository as CWD. Only an explicitly
versioned pre-session ``agent-docs`` release receives compatibility behavior.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    apply_patch_paths,
    command_from,
    emit_block,
    git_toplevel,
    patch_text_candidates,
    read_payload,
    tool_input_dict,
)

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"}
COMMAND_TOOLS = {"Bash"}
SESSION_FLOOR = (1, 21, 17)
SIMPLE_SHELL_CONTROL = re.compile(r"[\r\n;&|<>`$(){}#]")


def tool_name(payload: Mapping[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def session_id(payload: Mapping[str, Any]) -> str:
    for key in ("session_id", "sessionId", "session", "conversation_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def runtime_kit_source_checkout(repo_root: str) -> bool:
    required = (
        "AGENT_DOCS.toml",
        "AGENT_HOME.md",
        os.path.join("manifests", "skills.yaml"),
        os.path.join("scripts", "sync-runtime-surfaces.sh"),
    )
    return all(os.path.isfile(os.path.join(repo_root, path)) for path in required)


def agent_docs_args(repo_root: str, executable: str) -> list[str]:
    args = [executable]
    docs_home = os.environ.get("AGENT_RUNTIME_DOCS_HOME") or os.environ.get(
        "AGENT_DOCS_HOME"
    )
    if not docs_home and runtime_kit_source_checkout(repo_root):
        docs_home = repo_root
    if docs_home:
        args += ["--docs-home", os.path.realpath(docs_home)]
    return args + ["--project-path", repo_root]


def state_home(product: str) -> str:
    override = os.environ.get("AGENT_RUNTIME_STATE_HOME", "").strip()
    if override:
        return os.path.realpath(override)
    product_override = {
        "codex": "CODEX_AGENT_STATE_HOME",
        "claude": "CLAUDE_KIT_STATE_HOME",
    }.get(product, "")
    if product_override:
        value = os.environ.get(product_override, "").strip()
        if value:
            return os.path.realpath(value)
    root = os.environ.get("XDG_STATE_HOME", "").strip()
    if not root:
        root = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.realpath(os.path.join(root, "agent-runtime-kit", product))


def probe_timeout() -> float:
    raw = os.environ.get("AGENT_RUNTIME_AGENT_DOCS_TIMEOUT_SECONDS", "3")
    try:
        return min(max(float(raw), 0.01), 10.0)
    except ValueError:
        return 3.0


def run_probe(args: list[str]) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    try:
        return (
            subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=probe_timeout(),
            ),
            "completed",
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, "crash"


def parsed_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)\.(\d+)(?:\s|$|\()", text)
    if not match:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def session_capability(base_args: list[str]) -> tuple[str, str]:
    completed, outcome = run_probe(base_args + ["session", "--help"])
    if completed is None:
        return "unavailable", f"session-probe-{outcome}"
    if completed.returncode == 0 and "verify" in completed.stdout:
        return "supported", "session-verify-present"

    version_probe, version_outcome = run_probe([base_args[0], "--version"])
    if version_probe is None:
        return "unavailable", f"version-probe-{version_outcome}"
    if version_probe.returncode != 0:
        return "unavailable", "version-probe-nonzero"
    version = parsed_version(version_probe.stdout + "\n" + version_probe.stderr)
    if version is None:
        return "unavailable", "version-probe-malformed"
    if version < SESSION_FLOOR:
        return "legacy", ".".join(str(part) for part in version)
    return "unavailable", "required-session-surface-missing"


def payload_base(payload: Mapping[str, Any]) -> Path:
    tool_input = tool_input_dict(payload)
    for value in (tool_input.get("workdir"), tool_input.get("cwd"), payload.get("cwd")):
        if isinstance(value, str) and value:
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = Path.cwd() / path
            return path.resolve(strict=False)
    return Path.cwd().resolve(strict=False)


def nested_edit_paths(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in {"file_path", "path", "filename", "notebook_path"}:
                if isinstance(nested, str) and nested:
                    yield nested
            else:
                yield from nested_edit_paths(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            yield from nested_edit_paths(nested)


def edit_paths(payload: Mapping[str, Any]) -> list[str]:
    paths = list(nested_edit_paths(tool_input_dict(payload)))
    for candidate in patch_text_candidates(payload):
        paths.extend(apply_patch_paths(candidate))
    return list(dict.fromkeys(paths))


def canonical_path(raw: str, base: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def containing_repo(path: Path) -> str | None:
    probe = path if path.is_dir() else path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return git_toplevel(str(probe))


def simple_shell_words(command: str) -> list[str] | None:
    if not command.strip() or SIMPLE_SHELL_CONTROL.search(command):
        return None
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return None
    return words or None


def resolved_executable(name: str) -> str | None:
    candidate = shutil.which(name)
    if not candidate or not os.path.isabs(candidate):
        return None
    resolved = os.path.realpath(candidate)
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return None
    return resolved


def path_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((os.path.realpath(path), os.path.realpath(root))) == os.path.realpath(root)
    except ValueError:
        return False


def option_pairs(words: list[str]) -> dict[str, list[str]] | None:
    parsed: dict[str, list[str]] = {}
    index = 0
    while index < len(words):
        option = words[index]
        if not option.startswith("--") or index + 1 >= len(words):
            return None
        parsed.setdefault(option, []).append(words[index + 1])
        index += 2
    return parsed


def activation_bootstrap(
    command: str,
    *,
    payload: Mapping[str, Any],
    product: str,
    repos: list[str],
    agent_docs_executable: str,
) -> bool:
    words = simple_shell_words(command)
    if not words or words[0] != agent_docs_executable:
        return False
    try:
        session_index = words.index("session", 1)
    except ValueError:
        return False
    if words[session_index : session_index + 2] != ["session", "activate"]:
        return False

    globals_by_name = option_pairs(words[1:session_index])
    activate_by_name = option_pairs(words[session_index + 2 :])
    if globals_by_name is None or activate_by_name is None:
        return False
    if set(globals_by_name) - {"--docs-home", "--project-path"}:
        return False
    if set(activate_by_name) - {
        "--format",
        "--intent",
        "--product",
        "--session-id",
        "--state-home",
    }:
        return False
    singleton_globals = {"--docs-home", "--project-path"}
    singleton_activate = {"--format", "--product", "--session-id", "--state-home"}
    if any(len(globals_by_name.get(name, [])) > 1 for name in singleton_globals):
        return False
    if any(len(activate_by_name.get(name, [])) > 1 for name in singleton_activate):
        return False

    project_values = globals_by_name.get("--project-path", [])
    session_values = activate_by_name.get("--session-id", [])
    product_values = activate_by_name.get("--product", [])
    state_values = activate_by_name.get("--state-home", [])
    intent_values = activate_by_name.get("--intent", [])
    if not all((project_values, session_values, product_values, state_values, intent_values)):
        return False
    if any(not value.strip() for value in intent_values):
        return False
    if session_values != [session_id(payload)] or product_values != [product]:
        return False
    if os.path.realpath(state_values[0]) != state_home(product):
        return False
    project_path = os.path.realpath(project_values[0])
    if project_path not in repos:
        return False

    expected_docs_home = os.environ.get("AGENT_RUNTIME_DOCS_HOME") or os.environ.get(
        "AGENT_DOCS_HOME"
    )
    if not expected_docs_home and runtime_kit_source_checkout(project_path):
        expected_docs_home = project_path
    docs_values = globals_by_name.get("--docs-home", [])
    if expected_docs_home:
        if not docs_values or os.path.realpath(docs_values[0]) != os.path.realpath(
            expected_docs_home
        ):
            return False
    elif docs_values:
        return False
    format_values = activate_by_name.get("--format", [])
    return not format_values or format_values == ["json"]


def target_repositories(payload: Mapping[str, Any], tool: str) -> list[str]:
    base = payload_base(payload)
    repos: set[str] = set()
    if tool in EDIT_TOOLS:
        paths = edit_paths(payload)
        for raw in paths:
            repo = containing_repo(canonical_path(raw, base))
            if repo:
                repos.add(os.path.realpath(repo))
        if not paths:
            cwd_repo = containing_repo(base)
            if cwd_repo:
                repos.add(os.path.realpath(cwd_repo))
    elif tool in COMMAND_TOOLS:
        cwd_repo = containing_repo(base)
        if cwd_repo:
            repos.add(os.path.realpath(cwd_repo))
    return sorted(
        repo for repo in repos if os.path.isfile(os.path.join(repo, "AGENT_DOCS.toml"))
    )


def verify_intent(
    base_args: list[str], *, current_session: str, product: str
) -> tuple[bool, str]:
    completed, outcome = run_probe(
        base_args
        + [
            "session",
            "verify",
            "--session-id",
            current_session,
            "--product",
            product,
            "--state-home",
            state_home(product),
            "--require-intent",
            "project-dev",
            "--format",
            "json",
        ]
    )
    if completed is None:
        return False, f"intent-verification-{outcome}"
    if completed.returncode == 0:
        try:
            body = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return False, "intent-verification-malformed"
        if (
            not isinstance(body, dict)
            or body.get("schema_version") != "cli.agent-docs.session.verify.v1"
            or body.get("ok") is not True
        ):
            return False, "intent-verification-invalid-response"
        data = body.get("data")
        active_intents = data.get("active_intents") if isinstance(data, dict) else None
        if (
            not isinstance(data, dict)
            or data.get("product") != product
            or not isinstance(active_intents, list)
            or any(not isinstance(intent, str) for intent in active_intents)
            or "project-dev" not in active_intents
            or data.get("verified") is not True
        ):
            return False, "intent-verification-not-verified"
        return True, "verified"
    try:
        body = json.loads(completed.stdout or completed.stderr)
        error = body.get("error") if isinstance(body, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        if isinstance(code, str) and code:
            return False, code
    except (json.JSONDecodeError, TypeError):
        pass
    return False, "intent-not-active-or-stale"


def main() -> int:
    payload = read_payload()
    tool = tool_name(payload)
    if tool not in EDIT_TOOLS | COMMAND_TOOLS:
        return ALLOW
    product = os.environ.get("AGENT_RUNTIME_PRODUCT", "").strip()
    if product not in {"codex", "claude"}:
        return ALLOW

    repos = target_repositories(payload, tool)
    if not repos:
        return ALLOW
    if tool in EDIT_TOOLS and not edit_paths(payload):
        emit_block("Repository edit target extraction failed closed; retry with an explicit path.")
        return ALLOW
    agent_docs_executable = resolved_executable("agent-docs")
    if not agent_docs_executable:
        emit_block(
            "agent-docs capability is unavailable for a supported repository mutation; "
            "restore the governed runtime before retrying."
        )
        return ALLOW
    if tool in COMMAND_TOOLS:
        command = command_from(payload)
        bootstrap_trusted = not any(
            path_within(agent_docs_executable, repo_root) for repo_root in repos
        )
        if bootstrap_trusted and activation_bootstrap(
            command,
            payload=payload,
            product=product,
            repos=repos,
            agent_docs_executable=agent_docs_executable,
        ):
            return ALLOW

    capability, detail = session_capability(
        agent_docs_args(repos[0], agent_docs_executable)
    )
    if capability == "legacy":
        return ALLOW
    if capability != "supported":
        emit_block(
            "agent-docs session capability could not be verified and repository mutation "
            f"fails closed ({detail})."
        )
        return ALLOW

    current_session = session_id(payload)
    if not current_session:
        emit_block(
            "Selective intent enforcement is available, but this mutation payload has no "
            "session id. Retry from a Codex or Claude session with session context."
        )
        return ALLOW

    failures: list[str] = []
    for repo_root in repos:
        verified, code = verify_intent(
            agent_docs_args(repo_root, agent_docs_executable),
            current_session=current_session,
            product=product,
        )
        if not verified:
            failures.append(code)
    if not failures:
        return ALLOW
    emit_block(
        "Activate and read project-dev before mutating the target repository, then retry. "
        "Run agent-docs session activate for the current session/product and agent-docs "
        "preflight --intent project-dev. Shell enforcement is CWD-scoped; run "
        "cross-repository shell mutations with each target repository as CWD. "
        f"Verification code: {failures[0]}."
    )
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
