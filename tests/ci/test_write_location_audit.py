#!/usr/bin/env python3
"""Fixture contract for the write-location audit (#302)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts/ci/write-location-audit.py"


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


class WriteLocationAuditTests(unittest.TestCase):
    def run_audit(
        self, files: dict[str, str], allow: str = ""
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git(root, "init", "-q")
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            git(root, "add", "-A")
            allow_file = root / "allow.toml"
            allow_file.write_text(allow, encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(AUDIT),
                    "--root",
                    str(root),
                    "--allow-file",
                    str(allow_file),
                ],
                capture_output=True,
                text=True,
            )

    def test_new_hard_coded_state_dir_is_blocked(self) -> None:
        result = self.run_audit(
            {
                "scripts/new-tool.sh": 'state="$HOME/.local/state/newtool-1.2/cache"\n',
                "core/policies/runbook.md": "Write fixtures to `/tmp/newtool-rehearsal`.\n",
            }
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("scripts/new-tool.sh:1", result.stdout)
        self.assertIn("~/.local/state/newtool-1.2", result.stdout)
        self.assertIn("tool state", result.stdout)
        self.assertIn("core/policies/runbook.md:1", result.stdout)
        self.assertIn("/tmp/newtool-rehearsal", result.stdout)
        self.assertIn("TMPDIR", result.stdout)

    def test_unknown_agent_home_child_names_the_class_to_use(self) -> None:
        result = self.run_audit(
            {
                "scripts/a.sh": 'out="$AGENT_HOME/rehearsal"\n',
                "scripts/b.sh": 'out="${AGENT_HOME}/out/cargo-target"\n',
            }
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("$AGENT_HOME/rehearsal", result.stdout)
        self.assertIn("$AGENT_HOME/out/cargo-target", result.stdout)
        self.assertIn("core/policies/write-locations.md", result.stdout)

    def test_declared_classes_and_dynamic_paths_pass(self) -> None:
        result = self.run_audit(
            {
                "scripts/ok.sh": "\n".join(
                    [
                        'root="${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit"',
                        'ev="$AGENT_HOME/out/projects/owner__repo/run"',
                        'sc="${AGENT_HOME}/out/scratch/owner__repo/run"',
                        'export CARGO_TARGET_DIR="$AGENT_HOME/build/run/$id"',
                        'tmp="$AGENT_HOME/tmp/$AGENT_SESSION_ID"',
                        'wt="$AGENT_HOME/worktrees/repo-1234/slug"',
                        'f="/tmp/${name}"',
                        'g="$TMPDIR/fixed"',
                        "",
                    ]
                ),
                "tests/fixture.sh": 'x="/tmp/fixture-only"\n',
                "build/codex/out.sh": 'x="~/.local/state/rendered"\n',
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_allowlist_requires_a_reason_and_rejects_stale_entries(self) -> None:
        files = {"docs/setup.md": "Back up to `~/.local/state/legacy-tool/`.\n"}
        allowed = self.run_audit(
            files,
            '[[allow]]\npath = "docs/setup.md"\nliteral = "~/.local/state/legacy-tool"\n'
            'reason = "Pre-contract tool state with its own env override."\n',
        )
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

        unreasoned = self.run_audit(
            files,
            '[[allow]]\npath = "docs/setup.md"\nliteral = "~/.local/state/legacy-tool"\n',
        )
        self.assertEqual(unreasoned.returncode, 2, unreasoned.stdout + unreasoned.stderr)
        self.assertIn("reason", unreasoned.stderr)

        stale = self.run_audit(
            {"docs/setup.md": "Nothing hard-coded here.\n"},
            '[[allow]]\npath = "docs/setup.md"\nliteral = "~/.local/state/legacy-tool"\n'
            'reason = "Pre-contract tool state."\n',
        )
        self.assertEqual(stale.returncode, 1, stale.stdout + stale.stderr)
        self.assertIn("stale allowlist entry", stale.stdout)


if __name__ == "__main__":
    unittest.main()
