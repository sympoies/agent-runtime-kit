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


def child_alive(path):
    if not path.exists():
        return False
    state = subprocess.run(["ps", "-o", "stat=", "-p", path.read_text().strip()],
                           capture_output=True, text=True).stdout.strip()
    return bool(state and not state.startswith("Z"))


def cleanup_group(path):
    if path.exists():
        try:
            os.killpg(int(path.read_text()), signal.SIGKILL)
        except ProcessLookupError:
            pass


class ComputerUseDeadline(unittest.TestCase):
    def test_completed_process_cleans_child_and_preserves_status(self):
        supervisor = ROOT / "tests/runtime-smoke/cases/computer-use/mcp-supervisor.py"
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as directory:
                child_file = pathlib.Path(directory) / "child"
                group_file = pathlib.Path(directory) / "group"
                script = 'echo "$$" >"$1"; sleep 60 & echo "$!" >"$2"; exit "$3"'
                try:
                    result = subprocess.run(["python3", str(supervisor), "bash", "-c", script,
                                             "fixture", str(group_file), str(child_file), str(exit_code)], timeout=4)
                    alive = child_alive(child_file)
                finally:
                    cleanup_group(group_file)
                self.assertTrue(child_file.exists(), "synthetic child never started")
                self.assertEqual(result.returncode, exit_code)
                self.assertFalse(alive, "owned child survived")

    def test_open_stdin_fails_and_cleans_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            child_file = root / "child"
            group_file = root / "group"
            source = DOMAIN.read_text()
            needle = '    input="$(cat)"'
            self.assertEqual(source.count(needle), 1)
            source = source.replace(needle, '    echo "$$" >"$COMPUTER_USE_TEST_GROUP"\n'
                                    '    sleep 60 &\n    echo "$!" >"$COMPUTER_USE_TEST_CHILD"\n' + needle)
            fixture = root / "domain.sh"
            fixture.write_text(source)
            env = os.environ.copy()
            env.update(REPO_ROOT=str(ROOT), SCRIPT_DIR=str(ROOT / "tests/runtime-smoke"),
                       TMP_ROOT=str(root / "tmp"), ARTIFACTS_DIR=str(root / "artifacts"),
                       RESULTS_FILE=str(root / "results"), COMPUTER_USE_TEST_CHILD=str(child_file),
                       COMPUTER_USE_TEST_GROUP=str(group_file), COMPUTER_USE_TEST_DEADLINE="1")
            started = time.monotonic()
            watchdog = False
            with (root / "stderr").open("w+") as stderr:
                proc = subprocess.Popen(["bash", str(fixture)], stdin=subprocess.PIPE,
                                        stdout=subprocess.DEVNULL, stderr=stderr,
                                        start_new_session=True, env=env)
                try:
                    try:
                        proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        watchdog = True
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                    alive = child_alive(child_file)
                finally:
                    cleanup_group(group_file)
                    proc.stdin.close()
                stderr.seek(0)
                diagnostic = stderr.read()
            elapsed = time.monotonic() - started
            self.assertTrue(child_file.exists(), "synthetic MCP child never started")
            self.assertFalse(watchdog, "domain exceeded bounded deadline; outer watchdog fired")
            self.assertLess(elapsed, 5)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("timed out", diagnostic)
            self.assertFalse(alive, "owned MCP child survived")
            self.assertIn("\tfail\t", (root / "results").read_text())


if __name__ == "__main__":
    unittest.main()
