#!/usr/bin/env python3
"""Executable contract for the canonical CI gate coverage boundary."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_COVERAGE = """\
ci/all.sh coverage boundary:
- canonical: positions 1-17 run against the active nils-cli surface
- consistency: position 6 proves source/render agreement, not semantic invariants
- provider CI: replays the canonical stack at minimum and validated nils-cli release lanes
- committed-state: position 8 runs convergence; dirty sources stop before position 1
- conditional: host/authenticated product acceptance runs only when affected
"""


class CiGateCoverageTests(unittest.TestCase):
    def run_normal_gate_with_source_state(
        self, *, dirty: bool
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            agent_runtime = temporary_root / "agent-runtime"
            agent_runtime.write_text("#!/bin/sh\nexit 73\n", encoding="utf-8")
            agent_runtime.chmod(0o755)

            git = temporary_root / "git"
            git.write_text(
                """#!/bin/sh
if [ "$1" = status ]; then
  if [ "${CI_GATE_TEST_DIRTY:-0}" = 1 ]; then
    printf ' M synthetic-dirty-source\\n'
  fi
  exit 0
fi
exec "$CI_GATE_TEST_REAL_GIT" "$@"
""",
                encoding="utf-8",
            )
            git.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temporary}{os.pathsep}{env['PATH']}"
            env["CI_GATE_TEST_DIRTY"] = "1" if dirty else "0"
            env["CI_GATE_TEST_REAL_GIT"] = (
                shutil.which("git", path=os.environ["PATH"]) or "git"
            )

            return subprocess.run(
                ["bash", "scripts/ci/all.sh"],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_describe_coverage_reports_the_exact_boundary_without_running_gates(
        self,
    ) -> None:
        source = (ROOT / "scripts/ci/all.sh").read_text(encoding="utf-8")
        marker = 'if [ "${1:-}" = "--describe-coverage" ]; then'
        if marker not in source:
            self.fail("the cheap coverage-description entrypoint is missing")
        result = subprocess.run(
            ["bash", "scripts/ci/all.sh", "--describe-coverage"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED_COVERAGE)
        self.assertEqual(result.stderr, "")

    def test_normal_gate_reports_coverage_before_its_first_gate(self) -> None:
        result = self.run_normal_gate_with_source_state(dirty=False)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith(EXPECTED_COVERAGE), result.stdout)
        self.assertIn("nils-cli version policy failed", result.stderr)

    def test_dirty_source_stops_before_position_one(self) -> None:
        result = self.run_normal_gate_with_source_state(dirty=True)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, EXPECTED_COVERAGE)
        self.assertIn("requires a clean committed source", result.stderr)
        self.assertIn("use focused checks while editing", result.stderr)

    def test_reported_stack_shape_matches_the_executable_gate(self) -> None:
        source = (ROOT / "scripts/ci/all.sh").read_text(encoding="utf-8")
        positions = [
            int(match.group(1))
            for match in re.finditer(r'^banner ([0-9]+) "', source, re.MULTILINE)
        ]
        runtime_smoke_modes = re.findall(
            r"^bash tests/runtime-smoke/run\.sh --mode ([a-z-]+)",
            source,
            re.MULTILINE,
        )
        position_eight_start = source.index('banner 8 "')
        position_nine_start = source.index("# Position 9", position_eight_start)
        position_eight = source[position_eight_start:position_nine_start]
        acceptance_invocations = [
            line.strip()
            for line in position_eight.splitlines()
            if line.strip().endswith(
                "bash scripts/ci/validate-surfaces-manifest.sh --execute-acceptance"
            )
        ]

        ruby = r"""
data = YAML.safe_load(File.read(ARGV.fetch(0)), aliases: false)
entries = data.fetch("surfaces").flat_map do |surface|
  surface.fetch("products").values.flat_map do |product|
    product.fetch("acceptance").map do |entry|
      [entry.fetch("kind"), entry.fetch("command")] if entry.key?("command")
    end.compact
  end
end
puts JSON.generate(entries)
"""
        result = subprocess.run(
            [
                "ruby",
                "-ryaml",
                "-rjson",
                "-e",
                ruby,
                "manifests/surfaces.yaml",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        manifest_acceptance = json.loads(result.stdout)

        self.assertEqual(positions, list(range(1, 18)))
        self.assertEqual(runtime_smoke_modes, ["deterministic"])
        self.assertNotIn("<<", position_eight)
        self.assertNotIn("() {", position_eight)
        self.assertEqual(
            acceptance_invocations,
            [
                'CODEX_HOME="$ACCEPTANCE_CODEX_HOME" '
                "bash scripts/ci/validate-surfaces-manifest.sh --execute-acceptance"
            ],
        )
        self.assertIn(
            ["ci", "bash tests/runtime-smoke/run.sh --mode convergence"],
            manifest_acceptance,
        )

    def test_position_eight_executes_and_gates_the_convergence_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            sentinel = temporary_root / "convergence-executed"
            convergence_command = "bash tests/runtime-smoke/run.sh --mode convergence"
            sentinel_command = (
                f"printf convergence-executed > {shlex.quote(str(sentinel))}; exit 73"
            )
            manifest = temporary_root / "surfaces.yaml"

            ruby = r"""
data = YAML.safe_load(File.read(ARGV.fetch(0)), aliases: false)
target = ARGV.fetch(1)
replacement = ARGV.fetch(2)
target_count = 0
data.fetch("surfaces").each do |surface|
  surface.fetch("products").each_value do |product|
    product.fetch("acceptance").each do |entry|
      next unless entry.key?("command")

      if entry.fetch("command") == target
        entry["command"] = replacement
        target_count += 1
      else
        entry["command"] = "true"
        entry.fetch("success")["exit_status"] = 0
      end
    end
  end
end
abort "expected one convergence command, got #{target_count}" unless target_count == 1
puts YAML.dump(data)
"""
            rewritten = subprocess.run(
                [
                    "ruby",
                    "-ryaml",
                    "-e",
                    ruby,
                    "manifests/surfaces.yaml",
                    convergence_command,
                    sentinel_command,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            manifest.write_text(rewritten.stdout, encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    "scripts/ci/validate-surfaces-manifest.sh",
                    "--execute-acceptance",
                    str(manifest),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                sentinel.read_text(encoding="utf-8"), "convergence-executed"
            )
            self.assertIn("exited 73, expected 0", result.stderr)


if __name__ == "__main__":
    unittest.main()
