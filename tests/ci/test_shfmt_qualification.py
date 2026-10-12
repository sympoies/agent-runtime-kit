#!/usr/bin/env python3
"""Execute the tracked formatter job with qualified and incompatible binaries."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ShfmtQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        parsed = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e",
             "puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0)), aliases: true))",
             str(ROOT / "lefthook.yml")],
            check=True, capture_output=True, text=True,
        )
        jobs = json.loads(parsed.stdout)["pre-commit"]["jobs"]
        cls.command = next(job["run"] for job in jobs if job["name"] == "shfmt")

    def run_job(self, version: str, status: int = 0) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "shfmt"
            binary.write_text(
                '#!/usr/bin/env bash\n'
                'if [ "${1:-}" = --version ]; then\n'
                '  printf "%s\\n" "$SHFMT_TEST_VERSION"\n'
                '  exit 0\n'
                'fi\n'
                'printf "%s\\n" "$@" > "$SHFMT_TEST_ARGS"\n'
                'exit "$SHFMT_TEST_STATUS"\n',
                encoding="utf-8",
            )
            binary.chmod(0o755)
            arguments = root / "arguments"
            fixture = root / "fixture with spaces.sh"
            content = "#!/bin/sh\necho fixture\n"
            fixture.write_text(content, encoding="utf-8")
            command = self.command.replace("{staged_files}", shlex.quote(str(fixture)))
            result = subprocess.run(
                ["bash", "-c", command], cwd=ROOT,
                env={**os.environ, "PATH": f"{root}{os.pathsep}{os.environ['PATH']}",
                     "SHFMT_TEST_VERSION": version, "SHFMT_TEST_STATUS": str(status),
                     "SHFMT_TEST_ARGS": str(arguments)},
                capture_output=True, text=True,
            )
            self.assertEqual(fixture.read_text(encoding="utf-8"), content)
            argv = arguments.read_text(encoding="utf-8").splitlines() if arguments.exists() else []
            return result, [word if word != str(fixture) else fixture.name for word in argv]

    def test_incompatible_formatter_is_rejected_before_formatting(self) -> None:
        for version in ("v3.8.0", "v3.14.2"):
            with self.subTest(version=version):
                result, argv = self.run_job(version)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("3.14.1", result.stderr)
                self.assertEqual(argv, [], "An unsupported formatter must not run the format pass")

    def test_qualified_formatter_keeps_options_and_file_argument(self) -> None:
        result, argv = self.run_job("v3.14.1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(argv, ["-i", "2", "-ci", "-d", "fixture with spaces.sh"])

    def test_qualified_formatter_failure_stays_a_failure(self) -> None:
        result, argv = self.run_job("v3.14.1", status=3)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(argv, ["-i", "2", "-ci", "-d", "fixture with spaces.sh"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
