#!/usr/bin/env python3
"""Local/SSH transport helper for nils-cli macos-agent automation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = "agent-runtime-kit.computer-use.macos-desktop.v1"
READY_VALUES = {"ready", "ok", "granted", "allowed"}
PERMISSION_KEYS = ("screen_recording", "accessibility", "automation")


class HelperError(RuntimeError):
    """A user-facing helper error."""


def validate_host(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("SSH host must not be empty")
    if value.startswith("-"):
        raise argparse.ArgumentTypeError("SSH host must not start with '-'")
    if any(char.isspace() or ord(char) < 32 for char in value):
        raise argparse.ArgumentTypeError("SSH host must not contain whitespace or control characters")
    if not re.fullmatch(r"[A-Za-z0-9._@%:+\-\[\]]+", value):
        raise argparse.ArgumentTypeError("SSH host contains unsupported characters")
    return value


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def parse_json(raw: str) -> Any:
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.host: str | None = args.host
        self.out_dir = Path(args.out_dir).expanduser().resolve()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.macos_agent_bin: str = args.macos_agent_bin
        self.connect_timeout: int = args.connect_timeout
        self.transport_timeout: int = args.transport_timeout

    @property
    def transport(self) -> str:
        return "ssh" if self.host else "local"

    def ssh_command(self, remote_command: str) -> list[str]:
        if self.host is None:
            raise HelperError("SSH command requested without --host")
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self.connect_timeout}",
            "--",
            self.host,
            remote_command,
        ]

    def redact_transport_text(self, value: str) -> str:
        if not self.host:
            return value
        candidates = [self.host]
        if "@" in self.host:
            candidates.append(self.host.rsplit("@", 1)[1])
        for candidate in sorted(set(candidates), key=len, reverse=True):
            if candidate:
                value = value.replace(candidate, "<ssh-target>")
        return value

    def subprocess(
        self,
        command: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        binary: bool = False,
    ) -> subprocess.CompletedProcess[Any]:
        try:
            return subprocess.run(
                list(command),
                input=input_bytes if binary else (input_bytes.decode("utf-8") if input_bytes is not None else None),
                capture_output=True,
                check=False,
                text=not binary,
                timeout=self.transport_timeout,
            )
        except FileNotFoundError as error:
            raise HelperError(f"required command not found: {command[0]}") from error
        except subprocess.TimeoutExpired as error:
            raise HelperError(
                f"transport command exceeded {self.transport_timeout}s timeout"
            ) from error

    def run_shell(
        self,
        remote_command: str,
        *,
        input_bytes: bytes | None = None,
        binary: bool = False,
    ) -> subprocess.CompletedProcess[Any]:
        return self.subprocess(
            self.ssh_command(remote_command), input_bytes=input_bytes, binary=binary
        )

    def run_macos_agent(
        self,
        operation: str,
        macos_args: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        artifacts: Sequence[str] = (),
    ) -> tuple[dict[str, Any], int]:
        argv = [
            self.macos_agent_bin,
            "--format",
            "json",
            "--error-format",
            "json",
            *macos_args,
        ]
        if self.host:
            completed = self.run_shell(shlex.join(argv), input_bytes=input_bytes)
        else:
            completed = self.subprocess(argv, input_bytes=input_bytes)

        stdout = self.redact_transport_text(completed.stdout or "")
        stderr = self.redact_transport_text(completed.stderr or "")
        tool_payload = parse_json(stdout)
        error_payload = parse_json(stderr)
        tool_ok = bool(
            completed.returncode == 0
            and isinstance(tool_payload, dict)
            and tool_payload.get("ok", True)
        )
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "ok": tool_ok,
            "operation": operation,
            "transport": self.transport,
            "target": "remote-mac" if self.host else "local-mac",
            "exit_code": completed.returncode,
            "result": tool_payload,
            "artifacts": list(artifacts),
        }
        if stderr.strip():
            payload["error"] = error_payload or {"message": stderr.strip()}
        self.record(payload)
        return payload, completed.returncode

    def record(self, payload: dict[str, Any]) -> None:
        record = dict(payload)
        record["recorded_at_unix_ms"] = int(time.time() * 1000)
        with (self.out_dir / "session.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def remote_artifact_path(self, suffix: str) -> str:
        artifact_id = uuid.uuid4().hex
        script = (
            'root="${AGENT_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}'
            '/out/computer-use"; '
            'umask 077; mkdir -p "$root"; '
            f'printf "%s" "$root/{artifact_id}{suffix}"'
        )
        completed = self.run_shell(script)
        if completed.returncode != 0 or not (completed.stdout or "").strip():
            message = (completed.stderr or "").strip() or "remote artifact path resolution failed"
            raise HelperError(message)
        return completed.stdout.strip()

    def remove_remote(self, path: str) -> None:
        if not self.host:
            return
        self.run_shell(f"rm -f -- {shlex.quote(path)}")


def remainder(values: Sequence[str], label: str) -> list[str]:
    result = list(values)
    if result and result[0] == "--":
        result = result[1:]
    if not result:
        raise HelperError(f"{label} requires arguments after '--'")
    return result


def permission_summary(tool_payload: Any) -> tuple[str, list[dict[str, str]], list[str]]:
    if not isinstance(tool_payload, dict):
        return "unavailable", [], ["macos-agent did not return a JSON preflight envelope"]
    result = tool_payload.get("result")
    if not isinstance(result, dict):
        return "unavailable", [], ["macos-agent preflight result is missing"]
    permissions = result.get("permissions")
    if not isinstance(permissions, dict):
        return "unavailable", [], ["macos-agent permission report is missing"]

    gaps: list[dict[str, str]] = []
    for key in PERMISSION_KEYS:
        raw = permissions.get(key)
        value = str(raw).lower() if raw is not None else "unknown"
        if value not in READY_VALUES:
            gaps.append({"capability": key, "status": value})
    hints = [str(item) for item in permissions.get("hints", []) if str(item).strip()]
    ready = bool(permissions.get("ready", not gaps))
    return ("ready" if ready and not gaps else "degraded"), gaps, hints


def command_preflight(args: argparse.Namespace) -> int:
    runner = Runner(args)
    macos_args = ["preflight"]
    if args.include_probes:
        macos_args.append("--include-probes")
    payload, exit_code = runner.run_macos_agent("preflight", macos_args)
    status, gaps, hints = permission_summary(payload.get("result"))
    payload["status"] = status
    payload["permission_gaps"] = gaps
    payload["hints"] = hints
    write_json(runner.out_dir / "preflight.json", payload)

    pending_path = runner.out_dir / "pending-user-actions.json"
    if gaps:
        write_json(
            pending_path,
            {
                "schema_version": SCHEMA_VERSION,
                "status": "user-action-required",
                "permission_gaps": gaps,
                "hints": hints,
                "instruction": (
                    "Record these gaps, continue with available capabilities, and report "
                    "the unresolved permissions at handoff."
                ),
            },
        )
    elif pending_path.exists():
        pending_path.unlink()
    emit(payload)
    # Capability gaps are data, not a transport failure. Preserve nonzero only
    # when macos-agent itself could not execute.
    return 0 if exit_code == 0 else exit_code


def command_run(args: argparse.Namespace) -> int:
    runner = Runner(args)
    macos_args = remainder(args.macos_args, "run")
    payload, exit_code = runner.run_macos_agent("run", macos_args)
    emit(payload)
    return exit_code


def command_capture(args: argparse.Namespace) -> int:
    runner = Runner(args)
    selectors = list(args.selectors)
    if selectors and selectors[0] == "--":
        selectors = selectors[1:]
    local_path = Path(args.path).expanduser().resolve()
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if not runner.host:
        payload, exit_code = runner.run_macos_agent(
            "capture",
            ["observe", "screenshot", *selectors, "--path", str(local_path)],
            artifacts=[str(local_path)],
        )
        emit(payload)
        return exit_code

    suffix = local_path.suffix if re.fullmatch(r"\.[A-Za-z0-9]+", local_path.suffix) else ".png"
    remote_path = runner.remote_artifact_path(suffix)
    try:
        payload, exit_code = runner.run_macos_agent(
            "capture",
            ["observe", "screenshot", *selectors, "--path", remote_path],
            artifacts=[str(local_path)],
        )
        if exit_code == 0:
            fetched = runner.run_shell(f"cat -- {shlex.quote(remote_path)}", binary=True)
            if fetched.returncode != 0:
                raise HelperError((fetched.stderr or b"").decode("utf-8", errors="replace").strip())
            local_path.write_bytes(fetched.stdout)
            payload["artifacts"] = [str(local_path)]
            payload["artifact_bytes"] = local_path.stat().st_size
        emit(payload)
        return exit_code
    finally:
        runner.remove_remote(remote_path)


def command_scenario(args: argparse.Namespace) -> int:
    runner = Runner(args)
    scenario = Path(args.file).expanduser().resolve()
    if not scenario.is_file():
        raise HelperError(f"scenario file does not exist: {scenario}")

    if not runner.host:
        payload, exit_code = runner.run_macos_agent(
            "scenario", ["scenario", "run", "--file", str(scenario)]
        )
        emit(payload)
        return exit_code

    remote_path = runner.remote_artifact_path(".json")
    try:
        uploaded = runner.run_shell(
            f"umask 077; cat > {shlex.quote(remote_path)}", input_bytes=scenario.read_bytes()
        )
        if uploaded.returncode != 0:
            raise HelperError((uploaded.stderr or "").strip() or "scenario upload failed")
        payload, exit_code = runner.run_macos_agent(
            "scenario", ["scenario", "run", "--file", remote_path]
        )
        emit(payload)
        return exit_code
    finally:
        runner.remove_remote(remote_path)


def add_transport_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", type=validate_host, help="SSH alias or host for a remote Mac")
    parser.add_argument("--out-dir", required=True, help="Local evidence directory")
    parser.add_argument(
        "--macos-agent-bin", default="macos-agent", help="macos-agent executable name or path"
    )
    parser.add_argument("--connect-timeout", type=positive_int, default=8)
    parser.add_argument("--transport-timeout", type=positive_int, default=60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operate a local or SSH-reachable Mac through nils-cli macos-agent."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Record dependencies and permission readiness")
    add_transport_args(preflight)
    preflight.add_argument("--include-probes", action="store_true")
    preflight.set_defaults(func=command_preflight)

    run = subparsers.add_parser("run", help="Run one macos-agent command")
    add_transport_args(run)
    run.add_argument("macos_args", nargs=argparse.REMAINDER)
    run.set_defaults(func=command_run)

    capture = subparsers.add_parser("capture", help="Capture a screenshot and keep it locally")
    add_transport_args(capture)
    capture.add_argument("--path", required=True, help="Local screenshot output path")
    capture.add_argument("selectors", nargs=argparse.REMAINDER)
    capture.set_defaults(func=command_capture)

    scenario = subparsers.add_parser("scenario", help="Run a local scenario file on the target Mac")
    add_transport_args(scenario)
    scenario.add_argument("--file", required=True, help="Local scenario JSON path")
    scenario.set_defaults(func=command_scenario)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except HelperError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
