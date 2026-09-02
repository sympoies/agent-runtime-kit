#!/usr/bin/env python3
"""Every dispatch group must stay inside the agent-hook executable budget.

`agent-hook` caps how many executable capabilities one dispatch may fan out to
(`dispatch-child-budget-exceeded`). The cap is per `(product, event, matcher)`
group, compiled into the released binary, and has no config knob.

This gate exists because that cliff is otherwise invisible until runtime on a
developer's machine: adding one rule to a group already at the cap leaves the
policy valid, the manifests consistent, every unit test green, and the
`sync-runtime-surfaces` dry run clean -- and then every tool call for that
product fails. That is exactly how sympoies/agent-runtime-kit#90 broke Claude's
Bash tool after merge.

It deliberately does NOT reimplement the capability classification. Which
capabilities count as executable is the binary's business and has changed
across releases; a local reimplementation would drift and give false comfort.
Instead it dispatches a probe payload through the installed `agent-hook` and
asserts the budget error does not come back.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "core/policies/agent-hook/runtime-kit-v1.toml"
BUDGET_ERROR = "dispatch-child-budget-exceeded"

# Matchers a real session drives constantly. A group that cannot dispatch here
# is a group whose product is unusable.
PROBES: tuple[tuple[str, str], ...] = (
    ("codex", "Bash"),
    ("codex", "Write"),
    ("codex", "Edit"),
    ("codex", "MultiEdit"),
    ("claude", "Bash"),
    ("claude", "Write"),
    ("claude", "Edit"),
    ("claude", "MultiEdit"),
)


def agent_hook() -> str | None:
    return shutil.which("agent-hook")


class HookDispatchBudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        binary = agent_hook()
        if binary is None:
            self.skipTest("agent-hook is not on PATH")
        self.binary = binary
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        policy = root / "policy.toml"
        policy.write_bytes(POLICY.read_bytes())
        digest = "sha256:" + hashlib.sha256(policy.read_bytes()).hexdigest()
        self.config = root / "config.toml"
        self.config.write_text(
            'schema_version = "agent-hook.config.v1"\n\n'
            "[policy]\n"
            f'path = "{policy}"\n'
            f'digest = "{digest}"\n',
            encoding="utf-8",
        )
        self.state = root / "state"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def dispatch(self, product: str, tool: str) -> dict:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "cwd": str(ROOT),
            "tool_input": {"command": "echo probe", "file_path": "README.md"},
        }
        result = subprocess.run(
            [
                self.binary,
                "--config",
                str(self.config),
                "--state-dir",
                str(self.state),
                "dispatch",
                "--product",
                product,
                "--format",
                "json",
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            env={**os.environ, "AGENT_RUNTIME_KIT_HOOK_PHASE": "budget-probe"},
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(
                f"agent-hook dispatch produced no JSON for {product}/{tool}:\n"
                f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
            )

    def test_no_dispatch_group_exceeds_the_executable_budget(self) -> None:
        over: list[str] = []
        for product, tool in PROBES:
            with self.subTest(product=product, tool=tool):
                envelope = self.dispatch(product, tool)
                code = (envelope.get("error") or {}).get("code")
                if code == BUDGET_ERROR:
                    over.append(f"{product}/{tool}")
        self.assertEqual(
            over,
            [],
            "dispatch group(s) exceed the agent-hook executable-capability "
            f"budget: {', '.join(over)}.\n"
            "A group at the cap cannot take another executable rule. Either "
            "carry the check in a handler already registered on that group "
            "(matching its posture and domain), or remove a rule from it. "
            "Raising the cap is an upstream nils-cli change and costs a child "
            "process on every tool call in that group.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
