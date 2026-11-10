#!/usr/bin/env python3
"""Installed-pair acceptance must exist and reject unsafe observations."""
import importlib.util
import contextlib
import io
import json
import shutil
import sys
import os
import tempfile
from unittest.mock import patch
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = ROOT / "scripts/ci/session-coordination-installed-acceptance.py"


class InstalledPairRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENTRYPOINT.is_file():
            raise AssertionError("Installed-pair proof-first recovery remains unproved: acceptance entrypoint absent")
        spec = importlib.util.spec_from_file_location("installed_pair_acceptance", ENTRYPOINT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module
        cls.verify = staticmethod(module.verify_observation)
        cls.resolve_targets = staticmethod(module.resolve_targets)

    def test_selected_pair_and_explicit_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected, poison = root / "selected", root / "poison"
            selected.mkdir()
            poison.mkdir()
            for directory in (selected, poison):
                for name in ("agent-session", "agent-hook"):
                    executable = directory / name
                    executable.write_text("#!/bin/sh\nexit 0\n")
                    executable.chmod(0o755)
            with patch.dict(os.environ, {"PATH": str(poison), "AGENT_SESSION_BIN": str(selected / "agent-session"), "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(selected)}):
                self.assertEqual(self.resolve_targets(), (str(selected / "agent-session"), str(selected / "agent-hook")))
                self.assertEqual(self.resolve_targets("/explicit/session", "/explicit/hook"), ("/explicit/session", "/explicit/hook"))
            with patch.dict(os.environ, {"PATH": str(poison), "AGENT_SESSION_BIN": "", "AGENT_RUNTIME_TRUSTED_CLI_ROOT": ""}):
                self.assertEqual(self.resolve_targets(), (str(poison / "agent-session"), str(poison / "agent-hook")))

    def test_trusted_path_discovery_receipt_is_unselected(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            bindir = home / ".local/nils-cli/bin"
            bindir.mkdir(parents=True)
            hooks = home / "hooks"
            hooks.mkdir()
            for name in ("agent-session", "agent-hook"):
                binary = bindir / name
                binary.write_text(f"#!/bin/sh\necho '{name} 1.2.3 (fixture)'\n")
                binary.chmod(0o755)
            for name in self.module.HOOK_FILES:
                shutil.copyfile(ROOT / "core/hooks/shared" / name, hooks / name)
            base = {"HOME": str(home), "ZDOTDIR": str(home), "PATH": str(bindir),
                    "AGENT_SESSION_BIN": "", "AGENT_RUNTIME_TRUSTED_CLI_ROOT": ""}
            cases = (
                ({}, [], ("unselected-path", "unselected-path")),
                ({"AGENT_SESSION_BIN": str(bindir / "agent-session")}, [], ("selected", "selected")),
                ({"AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(home / "missing") + os.pathsep + str(bindir)}, [], ("selected", "selected")),
                ({}, ["--agent-session-bin", str(bindir / "agent-session"), "--agent-hook-bin", str(bindir / "agent-hook")], ("explicit", "explicit")),
                ({"AGENT_SESSION_BIN": "relative/agent-session"}, [], ("unselected-path", "unselected-path")),
            )
            for extra, flags, expected in cases:
                with self.subTest(extra=extra, flags=flags):
                    output = io.StringIO()
                    with patch.dict(os.environ, {**base, **extra}), patch.object(sys, "argv", [str(ENTRYPOINT), "--installed-hooks", str(hooks), *flags]), \
                         patch.object(self.module, "Fixture") as fixture, contextlib.redirect_stdout(output):
                        fixture.return_value.observe.return_value = {}
                        self.assertEqual(self.resolve_targets(), (str(bindir / "agent-session"), str(bindir / "agent-hook")))
                        self.module.main()
                    self.assertEqual(json.loads(output.getvalue())["target_selection"],
                                     dict(zip(("agent-session", "agent-hook"), expected)))
            (bindir / "agent-hook").unlink()
            with patch.dict(os.environ, {**base, "AGENT_SESSION_BIN": str(bindir / "agent-session")}):
                with self.assertRaisesRegex(AssertionError, "no executable agent-hook sibling"):
                    self.resolve_targets()

    def observation(self, case):
        value = {"case": case, "commands": {"broker prepare-admission-proof": 1, "broker proof": 1},
                 "initial_admit_count": 1, "producer_unchanged": True, "executions": 0,
                 "action": "block", "phase": "admitting", "bundle_preserved": True,
                 "terminal_retired": True, "active_preserved": True, "unrelated_preserved": True}
        if case == "lost-reply":
            value.update(action="allow", phase="active", executions=1,
                         proofs=[{"kind": "admission", "status": "committed", "state": "active"}])
        elif case == "terminal":
            value["proofs"] = [{"kind": "admission", "state": "completed", "outcome": "pass"},
                               {"kind": "operation", "state": "active"}]
        else:
            value["proofs"] = [{"kind": "admission", "status": "unknown"}]
        return value

    def test_real_contract_observation_shapes_pass(self):
        for case in ("lost-reply", "terminal", "unknown"):
            with self.subTest(case=case):
                self.verify(self.observation(case))

    def test_replay_or_missing_proof_is_rejected(self):
        for command, count in (("work-context admit", 1), ("broker proof", 0),
                               ("broker prepare-admission-proof", 0)):
            with self.subTest(command=command):
                value = self.observation("lost-reply")
                value["commands"][command] = count
                with self.assertRaises(AssertionError):
                    self.verify(value)

    def test_terminal_over_deletion_or_execution_is_rejected(self):
        for key, bad in (("active_preserved", False), ("unrelated_preserved", False),
                         ("terminal_retired", False), ("executions", 1)):
            with self.subTest(key=key):
                value = self.observation("terminal")
                value[key] = bad
                with self.assertRaises(AssertionError):
                    self.verify(value)

    def test_unknown_authorization_or_promotion_is_rejected(self):
        for key, bad in (("action", "allow"), ("executions", 1), ("phase", "active"),
                         ("bundle_preserved", False)):
            with self.subTest(key=key):
                value = self.observation("unknown")
                value[key] = bad
                with self.assertRaises(AssertionError):
                    self.verify(value)


if __name__ == "__main__":
    unittest.main()
