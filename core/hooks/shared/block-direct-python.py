#!/usr/bin/env python3
"""PreToolUse hook: block direct Python invocations in managed Python repos."""

from __future__ import annotations

import os
import re
import shlex
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    effective_workdir,
    emit_block,
    invocation_is_opaque,
    invocation_tokens,
    marker_environment_before_invocation,
    nested_shell_payload,
    normalize_command_separators,
    opaque_invocation_has_unresolved_nested,
    read_payload,
    strip_heredoc_bodies,
)

BYPASS_ENV_NAMES = (
    "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON",
    "AGENT_KIT_ALLOW_SYSTEM_PYTHON",
    "CLAUDE_KIT_ALLOW_SYSTEM_PYTHON",
)
BYPASS_TRUE_VALUES = {"1", "true", "TRUE", "yes", "YES"}

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*")
PYTHON_NAME_RE = re.compile(r"^python(?:3(?:\.\d+)?)?$")
SEPARATOR_TOKENS = {";", "&&", "||", "|", "(", ")"}


@dataclass(frozen=True)
class PythonManager:
    kind: str
    root: Path
    marker: Path
    venv_name: str | None = None


@dataclass(frozen=True)
class PythonInvocation:
    executable: str
    cwd: Path


def process_bypass_environment() -> dict[str, str]:
    return {
        name: value
        for name in BYPASS_ENV_NAMES
        if (value := os.environ.get(name)) is not None
    }


def pyproject_declares_uv(path: Path) -> bool:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            header = line.split("#", 1)[0].strip()
            if header == "[tool.uv]" or header.startswith("[tool.uv."):
                return True
    except OSError:
        return False
    return False


def find_python_manager(start: Path) -> PythonManager | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        uv_lock = directory / "uv.lock"
        if uv_lock.exists():
            return PythonManager("uv", directory, uv_lock)

        pyproject = directory / "pyproject.toml"
        if pyproject.exists() and pyproject_declares_uv(pyproject):
            return PythonManager("uv", directory, pyproject)

        for venv_name in (".venv", "venv"):
            pyvenv_cfg = directory / venv_name / "pyvenv.cfg"
            if pyvenv_cfg.exists():
                return PythonManager("venv", directory, pyvenv_cfg, venv_name)

    return None


def shell_tokens(command: str) -> list[str]:
    # Inert here-doc bodies (quoted delimiter, not shell-executed) are data,
    # not commands; without this strip a body line such as `env python3 ...`
    # inside a commit-message heredoc reads as a direct invocation.
    command = strip_heredoc_bodies(command, inert_only=True)
    # Treat unquoted newlines as command separators so a blocked command on a
    # later physical line (after a `cd` or other preamble) cannot slip past the
    # guard. See hook_common.normalize_command_separators.
    command = normalize_command_separators(command)
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return []


def is_separator(token: str) -> bool:
    return token in SEPARATOR_TOKENS or bool(token) and all(char in ";&|()" for char in token)


def basename(token: str) -> str:
    return PurePosixPath(token).name


def is_assignment(token: str) -> bool:
    return bool(ASSIGNMENT_RE.match(token))


def is_project_venv_python(token: str) -> bool:
    if "/" not in token:
        return False
    parts = PurePosixPath(token).parts
    return len(parts) >= 3 and parts[-2] == "bin" and parts[-3] in {".venv", "venv"}


def is_direct_python_token(token: str) -> bool:
    if is_project_venv_python(token):
        return False
    if not PYTHON_NAME_RE.match(basename(token)):
        return False
    return "/" not in token or token.startswith("/")


def command_python_token(simple_command: list[str]) -> str | None:
    invocation = invocation_tokens(simple_command)
    if not invocation:
        return None
    if invocation_is_opaque(invocation):
        if opaque_invocation_has_unresolved_nested(invocation):
            return "unresolved nested shell"
        return next(
            (token for token in invocation[1:] if is_direct_python_token(token)),
            None,
        )
    return invocation[0] if is_direct_python_token(invocation[0]) else None


def bypass_enabled(environment: Mapping[str, str]) -> bool:
    return any(
        environment.get(name, "") in BYPASS_TRUE_VALUES for name in BYPASS_ENV_NAMES
    )


def cd_target(simple_command: list[str], cwd: Path) -> Path | None:
    index = 0
    while index < len(simple_command) and is_assignment(simple_command[index]):
        index += 1
    if index >= len(simple_command) or basename(simple_command[index]) != "cd":
        return None

    index += 1
    while index < len(simple_command) and simple_command[index] in {"-L", "-P", "-e"}:
        index += 1
    if index < len(simple_command) and simple_command[index] == "--":
        index += 1

    if index >= len(simple_command):
        target = Path.home()
    else:
        raw_target = simple_command[index]
        if raw_target == "-":
            return None
        target = Path(raw_target).expanduser()

    if not target.is_absolute():
        target = cwd / target
    return target


def direct_python_invocation(
    command: str,
    start_cwd: Path,
    *,
    inherited_bypass_environment: Mapping[str, str] | None = None,
    depth: int = 0,
    max_depth: int = 5,
) -> PythonInvocation | None:
    if depth > max_depth:
        return None
    base_environment = (
        dict(inherited_bypass_environment)
        if inherited_bypass_environment is not None
        else process_bypass_environment()
    )
    simple_command: list[str] = []
    current_cwd = start_cwd

    def inspect(simple: list[str], cwd: Path) -> PythonInvocation | None:
        if not simple:
            return None
        command_environment = marker_environment_before_invocation(
            simple, BYPASS_ENV_NAMES, base_environment
        )
        command_bypass = bypass_enabled(command_environment)
        found = command_python_token(simple)
        if found and not command_bypass:
            return PythonInvocation(found, cwd)
        payload = nested_shell_payload(invocation_tokens(simple))
        if payload:
            if depth >= max_depth and not command_bypass:
                return PythonInvocation("unresolved nested shell", cwd)
            return direct_python_invocation(
                payload,
                cwd,
                inherited_bypass_environment=command_environment,
                depth=depth + 1,
                max_depth=max_depth,
            )
        return None

    for token in shell_tokens(command):
        if is_separator(token):
            found = inspect(simple_command, current_cwd)
            if found:
                return found
            if token in {";", "&&"}:
                current_cwd = cd_target(simple_command, current_cwd) or current_cwd
            simple_command = []
            continue
        simple_command.append(token)
    return inspect(simple_command, current_cwd)


def block_reason(executable: str, manager: PythonManager) -> str:
    if manager.kind == "uv":
        fix = "Use `uv run --locked python ...` from this workspace."
        manager_label = "uv"
    else:
        venv_name = manager.venv_name or ".venv"
        fix = f"Use `{venv_name}/bin/python ...` from this workspace."
        manager_label = "a local virtualenv"

    return (
        f"Do not run `{executable}` directly here. This workspace appears to use {manager_label} "
        f"({manager.marker}).\n"
        f"  fix: {fix}\n"
        "  escape hatch: prefix the command with "
        "`AGENT_RUNTIME_ALLOW_"
        "SYSTEM_PYTHON=1` when system Python is intentional."
    )


def main() -> int:
    payload = read_payload()
    command = command_from(payload)
    if not command:
        return ALLOW

    invocation = direct_python_invocation(
        command,
        effective_workdir(payload),
        inherited_bypass_environment=process_bypass_environment(),
    )
    if not invocation:
        return ALLOW

    manager = find_python_manager(invocation.cwd)
    if manager is not None:
        emit_block(block_reason(invocation.executable, manager))
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
