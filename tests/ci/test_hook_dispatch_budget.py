#!/usr/bin/env python3
"""PreToolUse dispatch groups must stay inside the agent-hook executable budget.

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
#
# Scope is deliberately PreToolUse tool matchers. The UserPromptSubmit, Stop and
# SessionStart groups carry far fewer executable rules and are nowhere near the
# cap; extend this list if that stops being true. NotebookEdit and apply_patch
# are omitted because a bare probe payload cannot satisfy their provider target
# checks -- and since a non-budget outcome now fails this gate rather than
# passing it, including them would make the gate red for the wrong reason.
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
    # Honor the same override the sibling agent-hook suite uses, so a CI that
    # supplies the binary off-PATH runs this gate instead of skipping it.
    override = os.environ.get("AGENT_HOOK_BIN", "").strip()
    if override:
        return override
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
        self.digest = "sha256:" + hashlib.sha256(policy.read_bytes()).hexdigest()
        self.config = root / "config.toml"
        self.config.write_text(
            'schema_version = "agent-hook.config.v1"\n\n'
            "[policy]\n"
            f'path = "{policy}"\n'
            f'digest = "{self.digest}"\n',
            encoding="utf-8",
        )
        self.state = root / "state"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def dispatch(self, product: str, tool: str, *, config: Path | None = None) -> dict:
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
                str(config or self.config),
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

    def classify(self, envelope: dict) -> str:
        """`ok`, the budget error, or any other outcome -- never silently green.

        A probe that fails before the budget is evaluated proves nothing. If
        such an outcome counted as a pass, this gate would be indistinguishable
        from no gate at exactly the moment it matters.
        """
        if envelope.get("ok") is True:
            return "ok"
        code = (envelope.get("error") or {}).get("code") or "unknown"
        return code

    def test_no_dispatch_group_exceeds_the_executable_budget(self) -> None:
        over: list[str] = []
        unreached: list[str] = []
        for product, tool in PROBES:
            with self.subTest(product=product, tool=tool):
                outcome = self.classify(self.dispatch(product, tool))
                if outcome == BUDGET_ERROR:
                    over.append(f"{product}/{tool}")
                elif outcome != "ok":
                    unreached.append(f"{product}/{tool}={outcome}")

        self.assertEqual(
            unreached,
            [],
            "probe(s) never reached budget evaluation, so this gate proved "
            f"nothing for them: {', '.join(unreached)}.\n"
            "Fix the probe rather than accepting the pass: a non-budget "
            "dispatch error here means the gate is vacuous.",
        )
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

    def test_gate_fails_when_the_probe_cannot_reach_budget_evaluation(self) -> None:
        """A broken probe must be loud, not green.

        Pins the masking bug this gate shipped with: `dispatch` returned valid
        JSON carrying a non-budget error, every probe was counted green, and
        the budget was never evaluated.
        """
        broken = Path(self.tmp.name) / "broken-config.toml"
        broken.write_text(
            self.config.read_text(encoding="utf-8").replace(
                self.digest, "sha256:" + "0" * 64
            ),
            encoding="utf-8",
        )
        outcome = self.classify(self.dispatch("claude", "Bash", config=broken))
        self.assertNotEqual(outcome, "ok")
        self.assertNotEqual(
            outcome,
            BUDGET_ERROR,
            "the corrupted-config probe must fail for its own reason, not the "
            "budget error, or this self-test proves nothing",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
