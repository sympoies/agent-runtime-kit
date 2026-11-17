#!/usr/bin/env python3
"""Exercise the computer-use MCP fixture with an open input stream."""
import os
import pathlib
import select
import signal
import subprocess
import tempfile
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
                script = 'echo "$$" >"$1"; sleep 300 & echo "$!" >"$2"; exit "$3"'
                try:
                    result = subprocess.run(["python3", str(supervisor), "bash", "-c", script,
                                             "fixture", str(group_file), str(child_file), str(exit_code)], timeout=30)
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
            supervisor = ROOT / "tests/runtime-smoke/cases/computer-use/mcp-supervisor.py"
            supervisor_source = supervisor.read_text()
            launch = "proc = subprocess.Popen(sys.argv[1:], start_new_session=True)"
            self.assertEqual(supervisor_source.count(launch), 1)
            supervisor_source = supervisor_source.replace(
                launch, 'proc = subprocess.Popen(sys.argv[1:], start_new_session=True, '
                        'pass_fds=(int(os.environ["COMPUTER_USE_READY_FD"]),))')
            wait = "        code = proc.wait(timeout=deadline)"
            self.assertEqual(supervisor_source.count(wait), 1)
            # Inject the timeout only after the test observes the child. The
            # production supervisor still owns the timeout and cleanup path.
            supervisor_source = supervisor_source.replace(
                wait, '        os.read(int(os.environ["COMPUTER_USE_TRIGGER_FD"]), 1)\n'
                      '        raise subprocess.TimeoutExpired(proc.args, deadline)')
            test_supervisor = root / "supervisor.py"
            test_supervisor.write_text(supervisor_source)
            source = DOMAIN.read_text()
            needle = '    input="$(cat)"'
            self.assertEqual(source.count(needle), 1)
            source = source.replace(needle, '    echo "$$" >"$COMPUTER_USE_TEST_GROUP"\n'
                                    '    sleep 300 &\n    echo "$!" >"$COMPUTER_USE_TEST_CHILD"\n'
                                    '    printf x >&"$COMPUTER_USE_READY_FD"\n' + needle)
            supervised = ('$REPO_ROOT/tests/runtime-smoke/cases/computer-use/mcp-supervisor.py" '
                          'macos-agent mcp --out-dir "$mcp_out-$profile"')
            self.assertEqual(source.count(supervised), 1)
            source = source.replace(supervised, str(test_supervisor) + '" '
                                    'macos-agent mcp --out-dir "$mcp_out-$profile"')
            fixture = root / "domain.sh"
            fixture.write_text(source)
            ready_read, ready_write = os.pipe()
            trigger_read, trigger_write = os.pipe()
            env = os.environ.copy()
            env.update(REPO_ROOT=str(ROOT), SCRIPT_DIR=str(ROOT / "tests/runtime-smoke"),
                       TMP_ROOT=str(root / "tmp"), ARTIFACTS_DIR=str(root / "artifacts"),
                       RESULTS_FILE=str(root / "results"), COMPUTER_USE_TEST_CHILD=str(child_file),
                       COMPUTER_USE_TEST_GROUP=str(group_file), COMPUTER_USE_READY_FD=str(ready_write),
                       COMPUTER_USE_TRIGGER_FD=str(trigger_read))
            with (root / "stderr").open("w+") as stderr:
                proc = subprocess.Popen(["bash", str(fixture)], stdin=subprocess.PIPE,
                                        stdout=subprocess.DEVNULL, stderr=stderr,
                                        start_new_session=True, env=env,
                                        pass_fds=(ready_write, trigger_read))
                os.close(ready_write)
                os.close(trigger_read)
                try:
                    self.assertTrue(select.select([ready_read], [], [], 60)[0],
                                    "synthetic MCP child never became ready")
                    self.assertEqual(os.read(ready_read, 1), b"x")
                    self.assertTrue(child_file.exists(), "synthetic MCP child never started")
                    self.assertTrue(child_alive(child_file), "synthetic MCP child exited before timeout")
                    self.assertIsNone(proc.poll(), "domain exited before the timeout trigger")
                    os.write(trigger_write, b"x")
                    proc.wait(timeout=60)
                    alive = child_alive(child_file)
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                    cleanup_group(group_file)
                    proc.stdin.close()
                    os.close(ready_read)
                    os.close(trigger_write)
                stderr.seek(0)
                diagnostic = stderr.read()
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("timed out", diagnostic)
            self.assertFalse(alive, "owned MCP child survived")
            self.assertIn("\tfail\t", (root / "results").read_text())


if __name__ == "__main__":
    unittest.main()
