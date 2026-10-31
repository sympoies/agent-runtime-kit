#!/usr/bin/env python3
"""Exercise the computer-use MCP fixture with an open input stream."""
import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOMAIN = ROOT / "tests/runtime-smoke/cases/computer-use/run.sh"


class ComputerUseDeadline(unittest.TestCase):
    def test_completed_process_cleans_child_and_preserves_status(self):
        supervisor = ROOT / "tests/runtime-smoke/cases/computer-use/mcp-supervisor.py"
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as directory:
                child_file = pathlib.Path(directory) / "child"
                script = 'sleep 60 & echo "$!" >"$1"; exit "$2"'
                result = subprocess.run(["python3", str(supervisor), "bash", "-c", script,
                                         "fixture", str(child_file), str(exit_code)], timeout=4)
                self.assertEqual(result.returncode, exit_code)
                child = int(child_file.read_text())
                state = subprocess.run(["ps", "-o", "stat=", "-p", str(child)],
                                       capture_output=True, text=True).stdout.strip()
                self.assertTrue(not state or state.startswith("Z"), "owned child survived")

    def test_open_stdin_fails_and_cleans_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            child_file = root / "child"
            source = DOMAIN.read_text()
            needle = '    input="$(cat)"'
            self.assertEqual(source.count(needle), 1)
            source = source.replace(needle, '    sleep 60 &\n    echo "$!" >"$COMPUTER_USE_TEST_CHILD"\n' + needle)
            fixture = root / "domain.sh"
            fixture.write_text(source)
            env = os.environ.copy()
            env.update(REPO_ROOT=str(ROOT), SCRIPT_DIR=str(ROOT / "tests/runtime-smoke"),
                       TMP_ROOT=str(root / "tmp"), ARTIFACTS_DIR=str(root / "artifacts"),
                       RESULTS_FILE=str(root / "results"), COMPUTER_USE_TEST_CHILD=str(child_file),
                       COMPUTER_USE_TEST_DEADLINE="1")
            started = time.monotonic()
            proc = subprocess.Popen(["bash", str(fixture)], stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    start_new_session=True, env=env)
            watchdog = False
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                watchdog = True
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            finally:
                proc.stdin.close()
            elapsed = time.monotonic() - started
            diagnostic = proc.stderr.read().decode(errors="replace")
            proc.stderr.close()
            self.assertTrue(child_file.exists(), "synthetic MCP child never started")
            child = int(child_file.read_text())
            try:
                os.kill(child, 0)
                state = subprocess.run(["ps", "-o", "stat=", "-p", str(child)], capture_output=True, text=True).stdout.strip()
                alive = bool(state and not state.startswith("Z"))
            except ProcessLookupError:
                alive = False
            self.assertFalse(watchdog, "domain exceeded bounded deadline; outer watchdog fired")
            self.assertLess(elapsed, 5)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("timed out", diagnostic)
            self.assertFalse(alive, "owned MCP child survived")
            self.assertIn("\tfail\t", (root / "results").read_text())


if __name__ == "__main__":
    unittest.main()
