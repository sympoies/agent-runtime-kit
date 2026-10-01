#!/usr/bin/env python3
"""Host scripts resolve a Python 3.11+ interpreter instead of bare python3.

macOS login shells often resolve `python3` to the system 3.9 interpreter even
when Homebrew Python is installed. These tests stage a PATH whose only
`python3` is an old-interpreter stub and prove that `setup.sh` and
`sync-runtime-surfaces.sh` either find a 3.11+ interpreter or stop before
planning any mutation.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "scripts/lib/runtime-python.sh"
OLD_PYTHON_STUB = """#!/bin/sh
case "${1:-}" in
  --version | -V) echo "Python 3.9.6"; exit 0 ;;
esac
echo "old-python-stub: ModuleNotFoundError: No module named 'tomllib'" >&2
exit 1
"""
MISSING_MESSAGE = "Python 3.11+ is required"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


class RuntimePythonResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.link_host_tools_without_python()
        write_executable(self.bin / "python3", OLD_PYTHON_STUB)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def link_host_tools_without_python(self) -> None:
        """Mirror the host PATH into one directory, minus every python*."""
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory or not os.path.isdir(directory):
                continue
            for entry in sorted(os.listdir(directory)):
                if entry.startswith("python") or (self.bin / entry).exists():
                    continue
                source = Path(directory) / entry
                if not (source.is_file() and os.access(source, os.X_OK)):
                    continue
                if entry == "brew":
                    # brew locates its library from its own path; a symlink
                    # elsewhere breaks that, so forward through a wrapper.
                    write_executable(
                        self.bin / entry, f'#!/bin/sh\nexec "{source}" "$@"\n'
                    )
                else:
                    (self.bin / entry).symlink_to(source)

    def modern_python(self, name: str) -> Path:
        path = self.bin / name
        write_executable(path, f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        return path

    def env(self, **extra: str) -> dict[str, str]:
        env = {
            "PATH": str(self.bin),
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.root / "state"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            # Keep the fixed Homebrew fallbacks out of a hermetic run.
            "AGENT_RUNTIME_PYTHON_FALLBACKS": "",
        }
        env.update(extra)
        return env

    def run_bash(
        self, args: list[str], **extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", *args],
            cwd=ROOT,
            env=self.env(**extra),
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def resolve(self, **extra: str) -> subprocess.CompletedProcess[str]:
        script = f'. "{LIB}" && require_runtime_python && printf "%s\\n" "$RUNTIME_PYTHON"'
        return self.run_bash(["-c", script], **extra)

    def assert_stopped_before_mutation(
        self, result: subprocess.CompletedProcess[str]
    ) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(MISSING_MESSAGE, result.stderr)
        self.assertIn("Python 3.9.6", result.stderr)
        self.assertIn("AGENT_RUNTIME_PYTHON", result.stderr)
        self.assertNotIn("old-python-stub", result.stderr)
        planned = [line for line in result.stdout.splitlines() if line.startswith("+ ")]
        self.assertEqual(planned, [], "no command may be planned before the check")

    def test_setup_stops_before_mutation_with_only_old_python3(self) -> None:
        result = self.run_bash(
            [
                "scripts/setup.sh",
                "--profile",
                "core",
                "--skip-homebrew-install",
                "--skip-cli-tools",
                "--dry-run",
            ]
        )
        self.assert_stopped_before_mutation(result)

    def test_sync_stops_before_mutation_with_only_old_python3(self) -> None:
        result = self.run_bash(
            [
                "scripts/sync-runtime-surfaces.sh",
                "--source-root",
                str(ROOT),
                "--product",
                "claude",
                "--no-pull",
                "--dry-run",
            ]
        )
        self.assert_stopped_before_mutation(result)

    def test_versioned_interpreter_wins_over_old_python3(self) -> None:
        modern = self.modern_python("python3.12")
        result = self.resolve()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(modern))

    def test_new_enough_python3_is_accepted_last(self) -> None:
        modern = self.modern_python("python3")
        result = self.resolve()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(modern))

    def test_fallback_path_is_used_when_shadowed(self) -> None:
        fallback_dir = self.root / "homebrew/bin"
        fallback_dir.mkdir(parents=True)
        fallback = fallback_dir / "python3"
        write_executable(fallback, f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        result = self.resolve(AGENT_RUNTIME_PYTHON_FALLBACKS=str(fallback))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(fallback))

    def test_override_wins_and_must_be_new_enough(self) -> None:
        self.modern_python("python3.12")
        override = self.modern_python("custom-python")
        result = self.resolve(AGENT_RUNTIME_PYTHON=str(override))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(override))

        result = self.resolve(AGENT_RUNTIME_PYTHON=str(self.bin / "python3"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENT_RUNTIME_PYTHON", result.stderr)

    def test_host_scripts_never_call_bare_python3(self) -> None:
        bare = re.compile(r"(?<![\w./-])python3(?![\w.-])")
        for relative in ("scripts/setup.sh", "scripts/sync-runtime-surfaces.sh"):
            for number, line in enumerate(
                (ROOT / relative).read_text(encoding="utf-8").splitlines(), 1
            ):
                stripped = line.strip()
                if stripped.startswith("#") or not bare.search(stripped):
                    continue
                if re.search(r"\bpython3\s+(-|-c\b)", stripped) or stripped.startswith(
                    "require_commands"
                ):
                    self.fail(f"{relative}:{number} invokes bare python3: {stripped}")


if __name__ == "__main__":
    unittest.main()
