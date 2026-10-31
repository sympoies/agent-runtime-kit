#!/usr/bin/env python3
"""Bound the synthetic MCP process and clean up its owned process group."""
import os
import signal
import subprocess
import sys

# The ordinary fixture has ample time for local synthetic work. The private
# seam keeps the regression fast; it is not a runtime-smoke interface.
deadline = int(os.environ.get("COMPUTER_USE_TEST_DEADLINE", "30"))
proc = subprocess.Popen(sys.argv[1:], start_new_session=True)
try:
    try:
        code = proc.wait(timeout=deadline)
    except subprocess.TimeoutExpired:
        print("computer-use: synthetic MCP process timed out", file=sys.stderr)
        code = 124
finally:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()
sys.exit(code)
