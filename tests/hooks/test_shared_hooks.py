#!/usr/bin/env python3
"""Compatibility entrypoint for the shared hook domain suites.

Retain existing SharedHookTests selectors and bounded process sharding. Each
worker still executes serially with its own shared helper runtime state.
Domain files avoid the test_ prefix so discovery collects this aggregate once.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared_hook_agent_memory import AgentMemoryTests
from shared_hook_artifact_routing import ArtifactRoutingTests
from shared_hook_block_hooks import BlockHooksTests
from shared_hook_checkout_lease import CheckoutLeaseTests
from shared_hook_command_guards import CommandGuardsTests
from shared_hook_default_delivery import DefaultDeliveryTests
from shared_hook_dirty_checkout import DirtyCheckoutTests
from shared_hook_finish_line import FinishLineTests
from shared_hook_session_coordination import SessionCoordinationTests
from shared_hook_session_start import SessionStartTests
from shared_hook_validation_coordination import ValidationCoordinationTests


class SharedHookTests(
    AgentMemoryTests,
    ArtifactRoutingTests,
    BlockHooksTests,
    CheckoutLeaseTests,
    CommandGuardsTests,
    DefaultDeliveryTests,
    DirtyCheckoutTests,
    FinishLineTests,
    SessionCoordinationTests,
    SessionStartTests,
    ValidationCoordinationTests,
):
    """Preserve existing public class and method selectors."""


def load_tests(loader, tests, pattern):
    """Imported domain classes must not create duplicate discovery cases."""
    return loader.loadTestsFromTestCase(SharedHookTests)


def _collect_test_names() -> list[str]:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(SharedHookTests)
    names = [test._testMethodName for test in suite]  # type: ignore[attr-defined]
    names.sort()
    return names


def _run_selected_tests(names: list[str], verbosity: int) -> bool:
    suite = unittest.TestSuite(SharedHookTests(name) for name in names)
    return unittest.TextTestRunner(verbosity=verbosity).run(suite).wasSuccessful()


def _default_jobs() -> int:
    # Hook tests are subprocess-bound: each spawns a hook process and blocks on
    # it, so wall-clock scales almost linearly with worker count until cores
    # saturate. Default to the core count, capped so the number of concurrently
    # spawned hook processes stays bounded. Override with HOOKS_TEST_JOBS
    # (HOOKS_TEST_JOBS=1 forces the serial path below).
    return max(1, min(os.cpu_count() or 2, 16))


def _run_parallel(jobs: int) -> int:
    names = _collect_test_names()
    if not names:
        print("test_shared_hooks: no tests discovered", file=sys.stderr)
        return 1
    # Round-robin sharding balances load across workers without needing
    # per-test timings. Each worker runs its shard SERIALLY in its own process,
    # so the per-process execution model — including the module-global
    # TEST_RUNTIME_STATE default state home — is identical to the serial run.
    # Sharding therefore introduces no cross-test races: no two tests ever run
    # concurrently inside a single process, and separate processes never share
    # mutable state (only read-only repo files).
    shards = [names[i::jobs] for i in range(jobs)]
    shards = [shard for shard in shards if shard]
    procs: list[subprocess.Popen[str]] = []
    for shard in shards:
        procs.append(
            subprocess.Popen(
                [sys.executable, __file__, "--tests", ",".join(shard)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        )
    failed = 0
    for proc in procs:
        out, _ = proc.communicate()
        if out:
            sys.stdout.write(out)
            sys.stdout.flush()
        if proc.returncode != 0:
            failed += 1
    if failed:
        print(
            f"test_shared_hooks: {failed}/{len(shards)} parallel shard(s) FAILED",
            file=sys.stderr,
        )
        return 1
    print(
        f"test_shared_hooks: all {len(names)} tests passed "
        f"across {len(shards)} parallel shard(s)"
    )
    return 0


if __name__ == "__main__":
    # Worker mode: run an explicit comma-separated test list serially. This is
    # how _run_parallel invokes each shard; handle it before unittest.main()
    # so the extra argv never reaches (and confuses) its argument parser.
    if "--tests" in sys.argv:
        _tests_idx = sys.argv.index("--tests")
        _selected = [name for name in sys.argv[_tests_idx + 1].split(",") if name]
        sys.exit(0 if _run_selected_tests(_selected, verbosity=1) else 1)

    # Explicit unittest selectors and flags are a focused, serial invocation.
    # The no-argument route retains the faster parallel default.
    if len(sys.argv) > 1:
        unittest.main(verbosity=2)

    _jobs_env = os.environ.get("HOOKS_TEST_JOBS")
    _jobs = int(_jobs_env) if _jobs_env else _default_jobs()
    if _jobs <= 1:
        # Serial escape hatch — exact prior behavior for debugging a failure.
        unittest.main(verbosity=2)
    else:
        sys.exit(_run_parallel(_jobs))
