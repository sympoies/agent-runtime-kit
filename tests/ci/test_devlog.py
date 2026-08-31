#!/usr/bin/env python3
"""Owner tests for the repository development-log search helper."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, Optional
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SEARCH = REPO_ROOT / "scripts" / "devlog-search.sh"


class DevlogSearchTests(unittest.TestCase):
    def run_search(
        self, *arguments: str, env: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(SEARCH), *arguments],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_enforces_search_contract(self) -> None:
        missing_term = self.run_search()
        self.assertEqual(missing_term.returncode, 2)
        self.assertIn("usage:", missing_term.stderr)
        self.assertNotIn(str(REPO_ROOT), missing_term.stderr)

        valid_month = self.run_search("PROJECT DEVLOG WORKFLOW", "2026-09")
        self.assertEqual(valid_month.returncode, 0)
        self.assertIn("Project devlog workflow established", valid_month.stdout)

        no_match = self.run_search("definitely-not-a-devlog-entry", "2026-09")
        self.assertEqual(no_match.returncode, 1)
        self.assertIn("no matches", no_match.stderr)

        literal_metacharacter = self.run_search("[", "2026-09")
        self.assertEqual(literal_metacharacter.returncode, 0)
        self.assertNotIn("regular expression", literal_metacharacter.stderr.lower())
        self.assertIn("[Development log policy and template]", literal_metacharacter.stdout)

        missing_month = self.run_search("anything", "2026-04")
        self.assertEqual(missing_month.returncode, 1)
        self.assertIn("no devlog month files", missing_month.stderr)
        self.assertNotIn(str(REPO_ROOT), missing_month.stderr)

        for invalid_month in ("../../README", "2026/09", "2026-9", "2026-13"):
            with self.subTest(invalid_month=invalid_month):
                invalid = self.run_search("current implementation", invalid_month)
                self.assertEqual(invalid.returncode, 2)
                self.assertIn("usage:", invalid.stderr)
                self.assertEqual(invalid.stdout, "")
                self.assertNotIn(str(REPO_ROOT), invalid.stderr)

        extra_argument = self.run_search("workflow", "2026-09", "unexpected")
        self.assertEqual(extra_argument.returncode, 2)
        self.assertIn("usage:", extra_argument.stderr)
        self.assertNotIn(str(REPO_ROOT), extra_argument.stderr)

    def test_uses_portable_grep_arguments(self) -> None:
        system_grep = shutil.which("grep")
        self.assertIsNotNone(system_grep)

        with tempfile.TemporaryDirectory() as temporary_directory:
            shim_directory = Path(temporary_directory)
            shim = shim_directory / "grep"
            shim.write_text(
                "#!/usr/bin/env bash\n"
                "for argument in \"$@\"; do\n"
                "  case \"$argument\" in\n"
                "    --color*) echo 'unsupported GNU grep option' >&2; exit 2 ;;\n"
                "  esac\n"
                "done\n"
                f'exec "{system_grep}" "$@"\n',
                encoding="utf-8",
            )
            shim.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{shim_directory}:{environment['PATH']}"

            result = self.run_search(
                "PROJECT DEVLOG WORKFLOW", "2026-09", env=environment
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Project devlog workflow established", result.stdout)
        self.assertNotIn("unsupported GNU grep option", result.stderr)

    def test_does_not_print_the_machine_local_checkout_path(self) -> None:
        result = self.run_search("runtime")

        self.assertEqual(result.returncode, 0)
        self.assertNotIn(str(REPO_ROOT), result.stdout)
        self.assertNotIn(str(REPO_ROOT), result.stderr)


if __name__ == "__main__":
    unittest.main()
