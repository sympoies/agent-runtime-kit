#!/usr/bin/env python3
"""F6 — hook<->binary argv contract for Main Agent Mode readiness commands.

The two readiness hooks hand-encode a positional-argv allowlist for the
pre-claim Main Agent Mode bootstrap commands:

  - core/hooks/shared/pre-edit-intent-gate.py      (main_agent_readiness_invocation)
  - core/hooks/shared/session-coordination-guard.py (main_agent_bypass_invocation)

Those allowlists are byte-for-byte twins and admit only exact shapes of
`main-agent {self show,self recover,rehydrate,status,bootstrap,worker
list,worker show,worker wait,worker diagnose,worker supervise,rebind,quick,
init}`. The capability-failure subset is separately enumerated so both shared
hooks retain only the proven recovery commands when ordinary hook capability
validation fails. If the binary's clap surface drifts from that allowlist (a renamed or
removed flag, a changed arity), a hook would keep admitting a command the binary
now rejects at parse time — a silent coupling break that only surfaces at
runtime. This test pins the coupling from the binary side: every canonical
admitted shape must be *accepted* (parsed) by the real `main-agent` binary. The
command may still fail afterwards (auth, validation, a missing packet); it must
simply not be rejected as a parse-error / unknown-subcommand.

Gated on the binary being resolvable (MAIN_AGENT_BIN env or `main-agent` on
PATH), mirroring tests/agent-hook/test_executable_contract.py; it skips cleanly
when the binary is absent.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


def resolve_main_agent() -> str | None:
    explicit = os.environ.get("MAIN_AGENT_BIN")
    if explicit:
        return explicit
    return shutil.which("main-agent")


MAIN_AGENT = resolve_main_agent()

# clap error codes that mean the argv itself was rejected (not a later failure).
PARSE_REJECTIONS = frozenset({"parse-error", "unknown-subcommand"})
NEGATIVE_REJECTIONS = PARSE_REJECTIONS | {
    "invalid-orchestration-input",
    "orchestration-store-invalid",
}


def capability_recovery_shapes() -> list[list[str]]:
    """Exact Main Agent shapes retained through capability failure."""
    key = "contract-key-0001"
    return [
        ["--version"],
        ["self", "show", "--format", "json"],
        ["self", "recover", "--idempotency-key", key, "--format", "json"],
        ["rehydrate", "--format", "json"],
        ["rehydrate", "--format", "markdown"],
        ["status", "--format", "json"],
        ["rebind", "--if-revision", "1", "--idempotency-key", key, "--format", "json"],
    ]


def admitted_shapes(packet: str) -> list[list[str]]:
    """Canonical pre-claim shapes admitted by the readiness hook allowlists.

    Keep in lock-step with the two hook allowlists. `packet` is a packet-file
    path; it need not exist because clap parses the string before the command
    reads the file.
    """
    key = "contract-key-0001"
    return [
        *capability_recovery_shapes(),
        ["bootstrap", "--idempotency-key", key, "--format", "json"],
        ["worker", "list", "--format", "json"],
        ["worker", "show", "assignment-contract", "--format", "json"],
        [
            "worker", "wait", "assignment-contract", "--until", "submitted",
            "--timeout", "30s", "--format", "json",
        ],
        [
            "worker", "wait", "--any", "--until", "terminal",
            "--format", "json",
        ],
        [
            "worker", "wait", "assignment-contract", "--until", "blocked",
            "--timeout", "1s", "--format", "json",
        ],
        [
            "worker", "wait", "--any", "--until", "submitted",
            "--timeout", "60s", "--format", "json",
        ],
        [
            "worker", "wait", "assignment-contract", "--until", "terminal",
            "--format", "json",
        ],
        ["worker", "diagnose", "assignment-contract", "--format", "json"],
        ["worker", "supervise", "assignment-contract", "--format", "json"],
        ["quick", "--assignment-file", packet, "--idempotency-key", key, "--format", "json"],
        [
            "quick", "--assignment-file", packet, "--tier", "L0",
            "--idempotency-key", key, "--format", "json",
        ],
        [
            "init", "--packet-file", packet, "--if-absent",
            "--idempotency-key", key, "--format", "json",
        ],
        [
            "init", "--packet-file", packet, "--if-revision", "1",
            "--idempotency-key", key, "--format", "json",
        ],
    ]


def rejected_near_misses(packet: str) -> dict[str, list[str]]:
    """One binary-invalid near miss for every finite hook allowlist family."""
    key = "contract-key-0001"
    return {
        "fixed-read": ["status", "--format", "json", "extra"],
        "worker-show": [
            "worker", "show", "assignment-contract", "--format", "json", "extra",
        ],
        "self-recover": [
            "self", "recover", "--key", key, "--format", "json",
        ],
        "bootstrap": [
            "bootstrap", "--idempotency-key", key, "--bogus", "--format", "json",
        ],
        "idempotency-key": [
            "bootstrap", "--idempotency-key", "bad key!", "--format", "json",
        ],
        "worker-wait": [
            "worker", "wait", "assignment-contract", "--until", "working",
            "--format", "json",
        ],
        "worker-diagnose": [
            "worker", "diagnose", "assignment-contract", "--format", "json", "extra",
        ],
        "worker-supervise": [
            "worker", "supervise", "assignment-contract", "--format", "json", "extra",
        ],
        "rebind": [
            "rebind", "--if-revision", "nope", "--idempotency-key", key,
            "--format", "json",
        ],
        "quick": [
            "quick", "--assignment-file", packet, "--tier", "L9",
            "--idempotency-key", key, "--format", "json",
        ],
        "init": [
            "init", "--packet-file", packet, "--if-revision", "nope",
            "--idempotency-key", key, "--format", "json",
        ],
    }


def error_code(stdout: str) -> str | None:
    """Extract the JSON error code from a `--format json` envelope, if any."""
    lines = [line for line in stdout.strip().splitlines() if line.strip()]
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return error.get("code")
    return None


@unittest.skipUnless(
    MAIN_AGENT,
    "main-agent binary not resolvable (set MAIN_AGENT_BIN or add it to PATH)",
)
class MainAgentArgvContractTest(unittest.TestCase):
    def test_version_flag_is_accepted(self) -> None:
        result = subprocess.run(
            [MAIN_AGENT, "--version"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_admitted_shapes_are_accepted_by_the_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = str(Path(tmp) / "packet.json")
            for shape in admitted_shapes(packet):
                with self.subTest(shape=" ".join(shape)):
                    result = subprocess.run(
                        [MAIN_AGENT, "--state-dir", tmp, *shape],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    code = error_code(result.stdout)
                    self.assertNotIn(
                        code,
                        PARSE_REJECTIONS,
                        "binary rejected a hook-admitted shape at parse time: "
                        f"{shape} -> code={code!r} "
                        f"stdout={result.stdout!r} stderr={result.stderr!r}",
                    )

    def test_capability_failure_recovery_shapes_are_a_strict_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = str(Path(tmp) / "packet.json")
            admitted = {tuple(shape) for shape in admitted_shapes(packet)}
            recovery = {tuple(shape) for shape in capability_recovery_shapes()}
            self.assertTrue(recovery < admitted)
            self.assertNotIn(("worker", "start", "--help"), recovery)

    def test_finite_allowlist_families_have_binary_rejected_near_misses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = str(Path(tmp) / "packet.json")
            for family, shape in rejected_near_misses(packet).items():
                with self.subTest(family=family, shape=" ".join(shape)):
                    result = subprocess.run(
                        [MAIN_AGENT, "--state-dir", tmp, *shape],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertIn(
                        error_code(result.stdout),
                        NEGATIVE_REJECTIONS,
                        "binary unexpectedly accepted a negative hook-family near miss: "
                        f"{family} -> {shape}; stdout={result.stdout!r} "
                        f"stderr={result.stderr!r}",
                    )


if __name__ == "__main__":
    unittest.main()
