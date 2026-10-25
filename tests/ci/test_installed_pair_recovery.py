#!/usr/bin/env python3
"""Installed-pair acceptance must exist and reject unsafe observations."""
import importlib.util
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
        cls.verify = staticmethod(module.verify_observation)

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
