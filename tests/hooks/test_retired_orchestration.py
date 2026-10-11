#!/usr/bin/env python3
"""Retired orchestration commands must use ordinary hook admission."""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HOOKS = Path(__file__).resolve().parents[2] / "core/hooks/shared"
sys.path.insert(0, str(HOOKS))
spec = importlib.util.spec_from_file_location("coordination", HOOKS / "session-coordination-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class RetiredOrchestrationTest(unittest.TestCase):
    def test_retired_commands_have_no_preclaim_admission(self):
        # Even a trusted same-release executable cannot mint a bootstrap bypass.
        with (
            mock.patch.object(
                guard.shutil, "which", side_effect=lambda name: "/runtime/" + name
            ),
            mock.patch.object(
                guard, "resolved_trusted_cli",
                side_effect=lambda name: "/runtime/" + name,
            ),
            mock.patch.object(
                guard, "run_cli",
                return_value=subprocess.CompletedProcess([], 0, "1.32.1", ""),
            ),
        ):
            for command in (
                "main-agent self readiness --format json",
                "main-agent bootstrap --idempotency-key retirement-0001 --format json",
                "main-agent worker list --format json",
            ):
                with self.subTest(command=command):
                    self.assertFalse(
                        guard.command_bypasses_admission(
                            command, "/runtime/agent-session", Path("/workspace")
                        )
                    )

if __name__ == "__main__":
    unittest.main()
