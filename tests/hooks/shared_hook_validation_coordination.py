"""Shared hook tests: validation coordination."""
from __future__ import annotations

from shared_hook_helpers import (
    Any,
    HOOK_DIR,
    HookTestCase,
    Path,
    REPO_ROOT,
    command_payload,
    concurrent,
    hashlib,
    hook_common,
    importlib,
    inventory_rules,
    inventory_tools,
    json,
    load_claude_hook_fragment,
    load_hook_inventory,
    mock,
    os,
    run_controller,
    run_enforced_hook,
    run_hook,
    shlex,
    stat,
    subprocess,
    tempfile,
    time,
    tomllib,
    write_payload,
)


class ValidationCoordinationTests(HookTestCase):

    def test_managed_sessions_forge_operation_fixtures_without_broker(self) -> None:
        cases = json.loads((REPO_ROOT / "tests/hooks/fixtures/forge-writes.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            broker = Path(tmp) / "agent-session"
            broker.write_text(
                "#!/usr/bin/env python3\nfrom pathlib import Path\n"
                f"Path({str(Path(tmp) / 'broker-called')!r}).touch()\n"
                "raise SystemExit(1)\n"
            )
            broker.chmod(0o755)
            for case in cases:
                with self.subTest(case=case["id"]):
                    code, decision, stderr = run_hook(
                        "block-direct-pr-create.py", command_payload(case["command"]),
                        env={"FORGE_IDENTITY_PRINCIPAL": "",
                             "AGENT_SESSION_ID": "fixture-session",
                             "AGENT_SESSION_RUNTIME_ID": "fixture-runtime",
                             "AGENT_RUNTIME_TRUSTED_CLI_ROOT": tmp,
                             "PATH": tmp + os.pathsep + os.environ["PATH"]},
                    )
                    self.assertEqual(code, 0, stderr)
                    if case["hint"]:
                        self.assert_blocked(decision, case["hint"])
                    else:
                        self.assert_allowed(decision)
            self.assertFalse((Path(tmp) / "broker-called").exists())


    def test_structured_validation_waiver_releases_the_gate_without_a_shell(
        self,
    ) -> None:
        """A blocked session must be able to waive validation out-of-band.

        The env-var route (`AGENT_RUNTIME_VALIDATION_WAIVER`) is unreachable from
        inside a session whose `PreToolUse` is failing closed, because setting it
        requires the shell execution that is blocked. See
        `sympoies/nils-cli#1409`: that made the deadlock unrecoverable from within.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation")

            waived = run_controller(
                ["waive", "--repo", str(repo), "--reason", "bounded infra failure"],
                env=base_env,
            )
            self.assertEqual(waived.returncode, 0, waived.stderr)
            record = json.loads(waived.stdout)
            self.assertEqual(record["ok"], True)
            self.assertEqual(
                record["data"]["schema_version"],
                "agent-runtime-validation.waiver.v1",
            )
            self.assertEqual(record["data"]["reason"], "bounded infra failure")

            # The structured waiver takes the same one-shot routing-review step
            # the env route takes, then releases.
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "routing review required")
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_structured_waiver_reaches_a_managed_session_namespace(self) -> None:
        """The waiver has to land where the *target session's* gate reads.

        The gate namespaces validation state by `sha256(session identity)`, and a
        managed session always has one, so a controller that only wrote the shared
        namespace would put its waiver where that gate never looks — failing
        silently in exactly the deadlock this lane exists for. The other waiver
        tests pass an empty payload, so they only cover the unidentified case.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            managed = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_SESSION_ID": "managed-session",
            }
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=managed,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=managed
            )
            self.assert_blocked(decision, "validation")

            # A shared-namespace waiver must NOT release a session-scoped gate.
            self.assertEqual(
                run_controller(
                    ["waive", "--repo", str(repo), "--reason", "wrong namespace"],
                    env={"AGENT_RUNTIME_DOCS_HOME": str(repo)},
                ).returncode,
                0,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=managed
            )
            self.assert_blocked(decision, "validation")

            # Naming the target session puts the record where that gate reads.
            targeted = run_controller(
                [
                    "waive",
                    "--repo",
                    str(repo),
                    "--reason",
                    "bounded infra failure",
                    "--session",
                    "managed-session",
                ],
                env={"AGENT_RUNTIME_DOCS_HOME": str(repo)},
            )
            self.assertEqual(targeted.returncode, 0, targeted.stderr)
            self.assertNotEqual(
                json.loads(targeted.stdout)["data"]["session_namespace"], "shared"
            )

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=managed
            )
            self.assert_blocked(decision, "routing review required")
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=managed
            )
            self.assert_allowed(decision)


    def test_structured_waiver_inherits_an_ambient_managed_session(self) -> None:
        """A controller invoked inside the managed context needs no argument."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            managed = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_SESSION_ID": "managed-session",
            }
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=managed,
            )
            self.assertEqual(
                run_controller(
                    ["waive", "--repo", str(repo), "--reason", "reviewed"],
                    env=managed,
                ).returncode,
                0,
            )
            for _ in range(2):
                run_hook("stop-finish-line-gate.py", {}, cwd=repo, env=managed)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=managed
            )
            self.assert_allowed(decision)


    def test_structured_validation_waiver_expires_on_the_next_edit(self) -> None:
        """The waiver is bound to the edit generation it was authorized against.

        This is the concrete improvement over the ambient env var, which stays
        true for every later Stop in the process and has already leaked across
        turns in production.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(
                run_controller(
                    ["waive", "--repo", str(repo), "--reason", "reviewed"],
                    env=base_env,
                ).returncode,
                0,
            )
            for _ in range(2):
                run_hook("stop-finish-line-gate.py", {}, cwd=repo, env=base_env)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)

            # A later edit advances the generation, so the waiver no longer
            # applies and validation is outstanding again.
            time.sleep(0.02)
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/other.rs"}},
                cwd=repo,
                env=base_env,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation")


    def test_structured_validation_waiver_requires_a_recorded_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            for arguments in (
                ["waive", "--repo", str(repo)],
                ["waive", "--repo", str(repo), "--reason", "   "],
            ):
                result = run_controller(arguments, env=base_env)
                self.assertNotEqual(
                    result.returncode, 0, f"{arguments} unexpectedly succeeded"
                )


    def test_structured_validation_waiver_is_revocable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(
                run_controller(
                    ["waive", "--repo", str(repo), "--reason", "reviewed"],
                    env=base_env,
                ).returncode,
                0,
            )
            revoked = run_controller(["revoke", "--repo", str(repo)], env=base_env)
            self.assertEqual(revoked.returncode, 0, revoked.stderr)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation")


    def test_typed_validation_run_executes_only_the_declared_command(self) -> None:
        """The recovery lane runs the exact declared command, never a substitute.

        `#1409` asks for a narrowly typed recovery, not a shell escape: the
        blocked session could not re-run its own declared validation because the
        same `PreToolUse` hook kept rejecting Bash.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, commands=("bash scripts/declared.sh",)
            )
            script = repo / "scripts" / "declared.sh"
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text(
                "#!/bin/sh\nprintf 'declared ran\\n' >> \"$PWD/.ran\"\nexit 0\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation")

            result = run_controller(["run", "--repo", str(repo)], env=base_env)
            self.assertEqual(result.returncode, 0, result.stderr)
            body = json.loads(result.stdout)
            self.assertEqual(body["ok"], True)
            self.assertEqual(
                body["data"]["commands"][0]["command"], "bash scripts/declared.sh"
            )
            self.assertEqual(body["data"]["commands"][0]["status"], "passed")
            self.assertEqual(
                (repo / ".ran").read_text(encoding="utf-8"), "declared ran\n"
            )

            # Running the declared command satisfies the gate for real; no
            # waiver is involved.
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_typed_validation_run_reports_a_failing_declared_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, commands=("bash scripts/declared.sh",)
            )
            script = repo / "scripts" / "declared.sh"
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )

            result = run_controller(["run", "--repo", str(repo)], env=base_env)
            self.assertNotEqual(result.returncode, 0)
            # A failing declared command is a failure envelope, so the outcome
            # detail arrives under `error` per the workspace envelope contract.
            body = json.loads(result.stdout)
            self.assertEqual(body["ok"], False)
            self.assertEqual(body["error"]["code"], "declared-validation-failed")
            self.assertEqual(body["error"]["commands"][0]["status"], "failed")
            self.assertEqual(body["error"]["commands"][0]["exit_code"], 3)

            # A failed declared run must not satisfy the gate.
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation")


    def test_typed_validation_status_reports_outstanding_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            clean = run_controller(["status", "--repo", str(repo)], env=base_env)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            body = json.loads(clean.stdout)
            self.assertEqual(body["data"]["outstanding"], False)
            self.assertEqual(
                body["data"]["contracts"][0]["commands"],
                ["bash scripts/ci/all.sh"],
            )
            self.assertEqual(body["data"]["contracts"][0]["waiver"], None)

            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )
            dirty = run_controller(["status", "--repo", str(repo)], env=base_env)
            body = json.loads(dirty.stdout)
            self.assertEqual(body["data"]["outstanding"], True)
            self.assertEqual(
                body["data"]["contracts"][0]["outstanding_commands"],
                ["bash scripts/ci/all.sh"],
            )


    def test_typed_validation_run_refuses_an_undeclared_command(self) -> None:
        """The lane exposes no general shell escape."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            result = run_controller(
                ["run", "--repo", str(repo), "--command", "rm -rf /"],
                env=base_env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("rm -rf /", result.stdout)


    def test_opaque_candidate_scan_has_a_bounded_token_budget(self) -> None:
        invocation = [
            hook_common.OPAQUE_WRAPPER_COMMAND,
            "tool*",
            *(["argument"] * 64_000),
        ]
        started = time.monotonic()
        candidates = hook_common.opaque_invocation_candidates(
            invocation, {"git", "semantic-commit"}
        )
        elapsed = time.monotonic() - started
        self.assertEqual(
            candidates, [[hook_common.OPAQUE_NESTED_SHELL_COMMAND]]
        )
        self.assertLess(elapsed, 0.5)


    def test_opaque_candidate_scan_bounds_work_below_token_ceiling(self) -> None:
        for token_count in (512, 1_024, 4_095, 4_096, 64_000):
            invocation = [
                hook_common.OPAQUE_WRAPPER_COMMAND,
                *(["$argument"] * token_count),
            ]
            started = time.monotonic()
            candidates = hook_common.opaque_invocation_candidates(
                invocation, {"git", "semantic-commit"}
            )
            elapsed = time.monotonic() - started
            with self.subTest(token_count=token_count):
                self.assertIn(
                    [hook_common.OPAQUE_NESTED_SHELL_COMMAND], candidates
                )
                self.assertLessEqual(len(candidates), 32)
                self.assertLess(elapsed, 0.5)


    def test_retired_checkpoint_writes_require_authenticated_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = "managed-session"
            runtime = "runtime-instance"
            state = root / "session-state"
            coordination = state / "sessions" / session / "coordination"
            coordination.mkdir(parents=True)
            for directory in (state, state / "sessions", coordination.parent, coordination):
                directory.chmod(0o700)
            checkpoint = coordination / (
                f"main-agent-checkpoint-{hashlib.sha256(runtime.encode()).hexdigest()}.json"
            )
            checkpoint.write_text("{}\n", encoding="utf-8")
            checkpoint.chmod(0o600)
            capability = root / "capability"
            capability.write_text("fixture-capability\n", encoding="utf-8")
            capability.chmod(0o600)
            bin_dir = root / "bin"
            bin_dir.mkdir(mode=0o700)
            calls = root / "calls.log"
            executable = bin_dir / "agent-session"
            executable.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {shlex.quote(str(calls))}
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.32.1'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\\n' '{{"ok":false,"error":{{"code":"claim-not-found"}}}}'
  exit 1
fi
exit 64
""",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
                "AGENT_SESSION_ID": session,
                "AGENT_SESSION_RUNTIME_ID": runtime,
                "AGENT_SESSION_STATE_DIR": str(state),
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_CHECKPOINT_FILE": str(checkpoint),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            # Match the former exception's exact issued path, private modes,
            # JSON object, and canonical printf shape so it would have bypassed.
            content = '{"ready":true}'
            printf_format = shlex.quote(r"%s\n")
            payloads = (
                write_payload(str(checkpoint), content),
                command_payload(
                    f"printf {printf_format} {shlex.quote(content)} "
                    f"> {shlex.quote(str(checkpoint))}"
                ),
            )
            for payload in payloads:
                with self.subTest(tool=payload["tool_name"]):
                    calls.write_text("", encoding="utf-8")
                    payload.update(
                        session_id="provider-session",
                        tool_use_id=f"checkpoint-{payload['tool_name']}",
                        hook_event_name="PreToolUse",
                    )
                    code, decision, stderr = run_enforced_hook(
                        "session-coordination-guard.py", payload, cwd=root, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "active work-context claim")
                    logged = calls.read_text(encoding="utf-8").splitlines()
                    claim_reads = [line for line in logged if "work-context show" in line]
                    self.assertEqual(len(claim_reads), 1, logged)
                    self.assertIn(f"--session {session}", claim_reads[0])
                    self.assertIn(f"--capability-file {capability}", claim_reads[0])
                    self.assertFalse(any("work-context admit" in line for line in logged))
                    self.assertEqual(checkpoint.read_text(encoding="utf-8"), "{}\n")


    def test_broker_counts_cannot_identify_a_terminal_concurrent_lease(
        self,
    ) -> None:
        """Aggregate active counts cannot prove whether lease A or B is terminal."""
        spec = importlib.util.spec_from_file_location(
            "session_coordination_concurrent_terminal_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        status = {
            "schema_version": "agent-session.coordination-broker.v1",
            "session_id": "managed-session",
            "state": "ready",
            "generation": 1,
            "capability_available": True,
            "heartbeat_fresh": True,
            "claim": {
                "claim_id": "11111111-1111-4111-8111-111111111111",
                "revision": 3,
                "state": "active",
            },
            # This is identical whether A is terminal and B is active or the
            # reverse. No lease-keyed terminal identity is present.
            "operation": {"active": 1, "uncertain": 0},
        }

        common_record = {
            "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
            "phase": "active",
            "session": "managed-session",
            "capability_file": "/private/capability",
            "state_dir": "/private/state",
            "claim_id": status["claim"]["claim_id"],
            "claim_revision": status["claim"]["revision"],
            "session_incarnation": "incarnation-1",
        }
        selectors = []
        for lease_id in ("lease-a", "lease-b"):
            with self.subTest(lease_id=lease_id):
                record = dict(common_record, lease_id=lease_id, lease_revision=1)
                selectors.append(guard.exact_operation_selector(record))

        self.assertEqual(set(status["operation"]), {"active", "uncertain"})
        self.assertEqual(
            [selector["lease_id"] for selector in selectors if selector],
            ["lease-a", "lease-b"],
        )
        self.assertNotEqual(selectors[0], selectors[1])


    def test_stop_uses_one_exact_batch_without_cross_item_poisoning(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_exact_batch_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        session = "managed-session"
        incarnation = "incarnation-1"

        def result(data: dict[str, Any]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps({"ok": True, "data": data}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records: list[Path] = []
            claims = (
                ("lease-a", "claim-a", 3),
                ("lease-b", "claim-b", 4),
                ("lease-claim-conflict", "claim-c", 5),
                ("lease-revision-conflict", "claim-d", 6),
            )
            for lease_id, claim_id, claim_revision in claims:
                path = root / f"{lease_id}.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                            "phase": "active",
                            "session": session,
                            "capability_file": "/private/capability",
                            "state_dir": "/private/state",
                            "claim_id": claim_id,
                            "claim_revision": claim_revision,
                            "lease_id": lease_id,
                            "lease_revision": 1,
                            "session_incarnation": incarnation,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                records.append(path)
            admission_path = root / "admission.json"
            admission_token = root / "admission.attempt.token"
            admission_targets = root / "admission.attempt.targets.json"
            admission_token.write_text("private-token\n", encoding="utf-8")
            admission_token.chmod(0o600)
            admission_targets.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-session.operation-targets.v1",
                        "targets": [],
                        "provider_refs": [],
                        "checkouts": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            admission_targets.chmod(0o600)
            admission_path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                        "phase": "admitting",
                        "session": session,
                        "capability_file": "/private/capability",
                        "state_dir": "/private/state",
                        "claim_id": "claim-admission",
                        "claim_revision": 7,
                        "session_incarnation": incarnation,
                        "operation": "edit",
                        "token_file": str(admission_token),
                        "targets_file": str(admission_targets),
                        "admit_idempotency": "admit-mixed-0001",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            admission_path.chmod(0o600)
            records.append(admission_path)

            calls: list[list[str]] = []
            malformed: list[str | None] = [None]

            def run_cli(
                args: list[str], **_kwargs: Any
            ) -> subprocess.CompletedProcess[str]:
                calls.append(args)
                if args[args.index("broker") + 1] == "status":
                    return result(
                        {
                            "schema_version": "agent-session.coordination-broker.v1",
                            "session_id": session,
                            "state": "ready",
                            "generation": 9,
                            "capability_available": True,
                            "heartbeat_fresh": True,
                            "claim": {
                                "claim_id": "claim-b",
                                "revision": 4,
                                "state": "active",
                            },
                            "operation": {"active": 3, "uncertain": 0},
                        }
                    )
                if args[args.index("broker") + 1] == "prepare-admission-proof":
                    return result(
                        {
                            "schema_version": "agent-session.broker-admission-proof-preparation.v1",
                            "selector": {
                                "kind": "admission",
                                "admit_idempotency_key": "admit-mixed-0001",
                                "claim_id": "claim-admission",
                                "claim_revision": 7,
                                "expected_request_digest": "a" * 64,
                            },
                        }
                    )
                self.assertEqual(args[args.index("broker") + 1], "proof")
                batch_path = Path(args[args.index("--batch-file") + 1])
                batch = json.loads(batch_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    batch["schema_version"],
                    "agent-session.broker-proof-batch.v1",
                )
                self.assertEqual(
                    [selector["kind"] for selector in batch["selectors"]],
                    ["operation", "operation", "operation", "operation", "admission"],
                )
                self.assertEqual(
                    [
                        selector["lease_id"]
                        for selector in batch["selectors"]
                        if selector["kind"] == "operation"
                    ],
                    [lease_id for lease_id, _claim, _revision in claims],
                )
                proof_data = {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": session,
                        "session_incarnation": incarnation,
                        "generation": 9,
                        "proofs": [
                            {
                                "index": 0,
                                "ok": True,
                                "proof": {
                                    "kind": "operation",
                                    "found": True,
                                    "lease_id": "lease-a",
                                    "state": "completed",
                                    "revision": 2,
                                    "outcome": "pass",
                                    "claim": {
                                        "claim_id": "claim-a",
                                        "revision": 3,
                                    },
                                },
                            },
                            {
                                "index": 1,
                                "ok": True,
                                "proof": {
                                    "kind": "operation",
                                    "found": True,
                                    "lease_id": "lease-b",
                                    "state": "active",
                                    "revision": 1,
                                    "outcome": None,
                                    "claim": {
                                        "claim_id": "claim-b",
                                        "revision": 4,
                                    },
                                },
                            },
                            {
                                "index": 2,
                                "ok": False,
                                "error": {
                                    "code": "operation-selector-conflict",
                                    "message": "claim mismatch",
                                },
                            },
                            {
                                "index": 3,
                                "ok": False,
                                "error": {
                                    "code": "operation-revision-conflict",
                                    "message": "revision mismatch",
                                },
                            },
                            {
                                "index": 4,
                                "ok": True,
                                "proof": {
                                    "kind": "admission",
                                    "status": "unknown",
                                    "provenance": "not_retained",
                                    "retained": False,
                                    "lease_id": None,
                                    "state": None,
                                    "revision": None,
                                    "outcome": None,
                                    "claim": None,
                                },
                            },
                        ],
                    }
                if malformed[0] == "generation":
                    proof_data["generation"] = True
                elif malformed[0] == "index":
                    proof_data["proofs"][0]["index"] = False
                elif malformed[0] == "claim_revision":
                    proof_data["proofs"][0]["proof"]["claim"]["revision"] = True
                elif malformed[0] == "unsupported":
                    return subprocess.CompletedProcess(
                        ["agent-session"], 64, stdout="", stderr="unrecognized command"
                    )
                return result(proof_data)

            for malformed_field in (
                "generation",
                "index",
                "claim_revision",
                "unsupported",
            ):
                malformed[0] = malformed_field
                calls.clear()
                with mock.patch.object(guard, "run_cli", side_effect=run_cli):
                    retired = guard.retire_externally_reconciled_records(
                        "/trusted/agent-session", records
                    )
                self.assertEqual(retired, set())
                self.assertTrue(all(path.exists() for path in records))

            malformed[0] = None
            calls.clear()
            with mock.patch.object(guard, "run_cli", side_effect=run_cli):
                retired = guard.retire_externally_reconciled_records(
                    "/trusted/agent-session", records
                )

            self.assertEqual(retired, {records[0]})
            self.assertFalse(records[0].exists())
            for path in records[1:]:
                self.assertTrue(path.exists())
            proof_calls = [args for args in calls if "proof" in args]
            self.assertEqual(len(proof_calls), 1)
            self.assertFalse(list(root.glob("*.broker-proof-batch")))


    def test_stop_preserves_unknown_admission_without_replay(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_unknown_admission_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        session = "managed-session"
        incarnation = "incarnation-1"

        def result(data: dict[str, Any]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps({"ok": True, "data": data}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            runtime_state = Path(tmp) / "runtime-state"
            with mock.patch.dict(
                os.environ,
                {"AGENT_RUNTIME_STATE_HOME": str(runtime_state)},
            ):
                namespace = guard.private_namespace("codex", session)
                namespace.mkdir(parents=True, mode=0o700)
                record_path = namespace / "unknown-admission.json"
                token_path = namespace / "unknown-admission.attempt.token"
                targets_path = namespace / "unknown-admission.attempt.targets.json"
                outcome_path = namespace / "unknown-admission.attempt.outcome"
                token_path.write_text("private-token\n", encoding="utf-8")
                token_path.chmod(0o600)
                targets_path.write_text(
                    json.dumps(
                        {
                            "schema_version": "agent-session.operation-targets.v1",
                            "targets": [],
                            "provider_refs": [],
                            "checkouts": [],
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                targets_path.chmod(0o600)
                record_path.write_text(
                    json.dumps(
                        {
                            "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                            "phase": "admitting",
                            "session": session,
                            "capability_file": "/private/capability",
                            "state_dir": "/private/state",
                            "claim_id": "claim-a",
                            "claim_revision": 3,
                            "session_incarnation": incarnation,
                            "operation": "edit",
                            "token_file": str(token_path),
                            "targets_file": str(targets_path),
                            "outcome_file": str(outcome_path),
                            "outcome": None,
                            "admit_idempotency": "hook-admit-unknown-0001",
                            "complete_idempotency": "hook-complete-unknown-0001",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                record_path.chmod(0o600)
                calls: list[list[str]] = []

                def run_cli(
                    args: list[str], **_kwargs: Any
                ) -> subprocess.CompletedProcess[str]:
                    calls.append(args)
                    if "status" in args:
                        return result(
                            {
                                "schema_version": "agent-session.coordination-broker.v1",
                                "session_id": session,
                                "state": "ready",
                                "generation": 9,
                                "capability_available": True,
                                "heartbeat_fresh": True,
                                "claim": {
                                    "claim_id": "claim-a",
                                    "revision": 3,
                                    "state": "active",
                                },
                                "operation": {"active": 0, "uncertain": 0},
                            }
                        )
                    if "prepare-admission-proof" in args:
                        return result(
                            {
                                "schema_version": "agent-session.broker-admission-proof-preparation.v1",
                                "selector": {
                                    "kind": "admission",
                                    "admit_idempotency_key": "hook-admit-unknown-0001",
                                    "claim_id": "claim-a",
                                    "claim_revision": 3,
                                    "expected_request_digest": "a" * 64,
                                },
                            }
                        )
                    if "proof" in args:
                        return result(
                            {
                                "schema_version": "agent-session.broker-proof.v1",
                                "session_id": session,
                                "session_incarnation": incarnation,
                                "generation": 9,
                                "proofs": [
                                    {
                                        "index": 0,
                                        "ok": True,
                                        "proof": {
                                            "kind": "admission",
                                            "status": "unknown",
                                            "provenance": "not_retained",
                                            "retained": False,
                                            "lease_id": None,
                                            "state": None,
                                            "revision": None,
                                            "outcome": None,
                                            "claim": None,
                                        },
                                    }
                                ],
                            }
                        )
                    self.fail(f"unexpected replay call: {args}")

                with mock.patch.object(guard, "run_cli", side_effect=run_cli):
                    guard.stop_audit(
                        "/trusted/agent-session", session, "codex"
                    )

                self.assertTrue(record_path.exists())
                self.assertTrue(token_path.exists())
                self.assertTrue(targets_path.exists())
                self.assertFalse(
                    any(
                        "work-context" in args and "admit" in args
                        for args in calls
                    )
                )
                self.assertEqual(
                    sum("proof" in args and "broker" in args for args in calls),
                    1,
                )


    def test_exact_admission_receipts_classify_issued_and_terminal(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_committed_admission_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        record = {
            "phase": "admitting",
            "claim_id": "claim-a",
            "claim_revision": 3,
        }
        common = {
            "kind": "admission",
            "status": "committed",
            "lease_id": "lease-a",
            "outcome": None,
            "claim": {"claim_id": "claim-a", "revision": 3},
        }
        self.assertEqual(
            guard.exact_proof_disposition(
                record,
                dict(
                    common,
                    provenance="retained_operation",
                    retained=True,
                    state="active",
                    revision=1,
                ),
            ),
            {
                "disposition": "admitted",
                "lease_id": "lease-a",
                "lease_revision": 1,
            },
        )
        self.assertEqual(
            guard.exact_proof_disposition(
                record,
                dict(
                    common,
                    provenance="historical_receipt",
                    retained=False,
                    state=None,
                    revision=None,
                ),
            ),
            {"disposition": "terminal"},
        )
        self.assertIsNone(
            guard.exact_proof_disposition(
                record,
                dict(
                    common,
                    provenance="retained_operation",
                    retained=True,
                    state="active",
                    revision=True,
                ),
            )
        )
        for uncertain_state in ("completing", "reconcile_pending"):
            with self.subTest(uncertain_state=uncertain_state):
                self.assertIsNone(
                    guard.exact_proof_disposition(
                        record,
                        dict(
                            common,
                            provenance="retained_operation",
                            retained=True,
                            state=uncertain_state,
                            revision=2,
                        ),
                    )
                )
        self.assertIsNone(
            guard.exact_proof_disposition(
                record,
                dict(
                    common,
                    provenance="retained_operation",
                    retained=True,
                    state="active",
                    revision=2,
                    outcome="pass",
                ),
            )
        )


    def test_exact_batch_prioritizes_active_and_caps_admission_preparation(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_bounded_admission_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        session = "managed-session"
        incarnation = "incarnation-1"

        def result(data: dict[str, Any]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps({"ok": True, "data": data}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common = {
                "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                "session": session,
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "claim_id": "claim-a",
                "claim_revision": 1,
                "session_incarnation": incarnation,
            }
            active_path = root / "active.json"
            active = dict(
                common,
                phase="active",
                lease_id="lease-active",
                lease_revision=1,
            )
            snapshots = [(active_path, active)]
            for index in range(guard.MAX_STOP_ADMISSION_PROOF_PREPARATIONS + 5):
                path = root / f"admitting-{index}.json"
                snapshots.append(
                    (
                        path,
                        dict(
                            common,
                            phase="admitting",
                            operation="edit",
                            token_file=str(root / f"admitting-{index}.token"),
                            targets_file=str(
                                root / f"admitting-{index}.targets.json"
                            ),
                            admit_idempotency=f"admit-{index}",
                        ),
                    )
                )

            def run_cli(
                args: list[str], **_kwargs: Any
            ) -> subprocess.CompletedProcess[str]:
                if args[args.index("broker") + 1] == "status":
                    return result(
                        {
                            "schema_version": "agent-session.coordination-broker.v1",
                            "session_id": session,
                            "state": "ready",
                            "generation": 1,
                            "capability_available": True,
                            "heartbeat_fresh": True,
                        }
                    )
                batch_path = Path(args[args.index("--batch-file") + 1])
                batch = json.loads(batch_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    batch["selectors"],
                    [
                        {
                            "kind": "operation",
                            "lease_id": "lease-active",
                            "revision_floor": 1,
                            "claim_id": "claim-a",
                            "claim_revision": 1,
                        }
                    ],
                )
                return result(
                    {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": session,
                        "session_incarnation": incarnation,
                        "generation": 1,
                        "proofs": [
                            {
                                "index": 0,
                                "ok": True,
                                "proof": {
                                    "kind": "operation",
                                    "found": True,
                                    "lease_id": "lease-active",
                                    "state": "completed",
                                    "revision": 1,
                                    "claim": {
                                        "claim_id": "claim-a",
                                        "revision": 1,
                                    },
                                },
                            }
                        ],
                    }
                )

            with mock.patch.object(
                guard, "prepared_admission_selector", return_value=None
            ) as prepare, mock.patch.object(
                guard, "run_cli", side_effect=run_cli
            ):
                evidence = guard.exact_external_reconciliation_evidence(
                    "/trusted/agent-session", snapshots
                )

            self.assertEqual(evidence, {active_path: {"disposition": "terminal"}})
            self.assertEqual(
                prepare.call_count, guard.MAX_STOP_ADMISSION_PROOF_PREPARATIONS
            )


    def test_pretool_exact_admission_recovery_blocks_terminal_and_unknown(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_pretool_recovery_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        session = "managed-session"
        call_id = "recovered-admission-call"
        payload = write_payload("src/example.py", "value = 1\n")
        payload["tool_use_id"] = call_id

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, {"AGENT_RUNTIME_STATE_HOME": tmp}
        ):
            namespace = guard.private_namespace("codex", session)
            namespace.mkdir(parents=True, mode=0o700)
            record_path = namespace / f"{guard.digest(call_id)}.json"
            token_path = namespace / f"{guard.digest(call_id)}.attempt.token"
            targets_path = (
                namespace / f"{guard.digest(call_id)}.attempt.targets.json"
            )
            outcome_path = namespace / f"{guard.digest(call_id)}.attempt.outcome"
            token_path.write_text("private-token\n", encoding="utf-8")
            token_path.chmod(0o600)
            targets_path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-session.operation-targets.v1",
                        "targets": [],
                        "provider_refs": [],
                        "checkouts": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            targets_path.chmod(0o600)
            admitting = {
                "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                "phase": "admitting",
                "session": session,
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "claim_id": "claim-a",
                "claim_revision": 3,
                "session_incarnation": "incarnation-1",
                "operation": "edit",
                "token_file": str(token_path),
                "targets_file": str(targets_path),
                "outcome_file": str(outcome_path),
                "outcome": None,
                "admit_idempotency": "admit-pretool-0001",
                "complete_idempotency": "complete-pretool-0001",
            }
            common_args = {
                "executable": "/trusted/agent-session",
                "managed_session": session,
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "product": "codex",
            }
            scenarios = {
                "active": {
                    "kind": "admission",
                    "status": "committed",
                    "provenance": "retained_operation",
                    "retained": True,
                    "lease_id": "lease-a",
                    "state": "active",
                    "revision": 4,
                    "outcome": None,
                    "claim": {"claim_id": "claim-a", "revision": 3},
                },
                "completing": {
                    "kind": "admission",
                    "status": "committed",
                    "provenance": "retained_operation",
                    "retained": True,
                    "lease_id": "lease-a",
                    "state": "completing",
                    "revision": 5,
                    "outcome": None,
                    "claim": {"claim_id": "claim-a", "revision": 3},
                },
                "reconcile_pending": {
                    "kind": "admission",
                    "status": "committed",
                    "provenance": "retained_operation",
                    "retained": True,
                    "lease_id": "lease-a",
                    "state": "reconcile_pending",
                    "revision": 6,
                    "outcome": None,
                    "claim": {"claim_id": "claim-a", "revision": 3},
                },
                "terminal": {
                    "kind": "admission",
                    "status": "committed",
                    "provenance": "historical_receipt",
                    "retained": False,
                    "lease_id": "lease-a",
                    "state": None,
                    "revision": None,
                    "outcome": None,
                    "claim": {"claim_id": "claim-a", "revision": 3},
                },
                "unknown": {
                    "kind": "admission",
                    "status": "unknown",
                    "provenance": "not_retained",
                    "retained": False,
                    "lease_id": None,
                    "state": None,
                    "revision": None,
                    "outcome": None,
                    "claim": None,
                },
            }

            for scenario in (
                "active",
                "completing",
                "reconcile_pending",
                "terminal",
                "unknown",
                "unsupported",
            ):
                with self.subTest(scenario=scenario):
                    record_path.write_text(
                        json.dumps(admitting) + "\n", encoding="utf-8"
                    )
                    record_path.chmod(0o600)
                    calls: list[list[str]] = []

                    def run_cli(
                        args: list[str], **_kwargs: Any
                    ) -> subprocess.CompletedProcess[str]:
                        calls.append(args)
                        if "admit" in args:
                            # Without the proof surface, recovery replays the
                            # exact admission; a slot-occupied refusal can come
                            # from checks before the replay lookup and stays
                            # uncertain.
                            self.assertEqual(scenario, "unsupported")
                            return subprocess.CompletedProcess(
                                ["agent-session"],
                                1,
                                stdout=json.dumps(
                                    {
                                        "ok": False,
                                        "error": {"code": "coordination-unavailable"},
                                    }
                                ),
                                stderr="",
                            )
                        command = args[args.index("broker") + 1]
                        if command == "--help":
                            listed = "  status\n  reconcile\n"
                            if scenario != "unsupported":
                                listed += "  prepare-admission-proof\n  proof\n"
                            return subprocess.CompletedProcess(
                                ["agent-session"], 0, stdout=listed, stderr=""
                            )
                        if command == "status":
                            data = {
                                "schema_version": "agent-session.coordination-broker.v1",
                                "session_id": session,
                                "state": "ready",
                                "generation": 9,
                                "capability_available": True,
                                "heartbeat_fresh": True,
                            }
                        elif command == "prepare-admission-proof":
                            if scenario == "unsupported":
                                return subprocess.CompletedProcess(
                                    ["agent-session"],
                                    64,
                                    stdout="",
                                    stderr="unrecognized command",
                                )
                            data = {
                                "schema_version": "agent-session.broker-admission-proof-preparation.v1",
                                "selector": {
                                    "kind": "admission",
                                    "admit_idempotency_key": "admit-pretool-0001",
                                    "claim_id": "claim-a",
                                    "claim_revision": 3,
                                    "expected_request_digest": "b" * 64,
                                },
                            }
                        else:
                            self.assertEqual(command, "proof")
                            data = {
                                "schema_version": "agent-session.broker-proof.v1",
                                "session_id": session,
                                "session_incarnation": "incarnation-1",
                                "generation": 9,
                                "proofs": [
                                    {
                                        "index": 0,
                                        "ok": True,
                                        "proof": scenarios[scenario],
                                    }
                                ],
                            }
                        return subprocess.CompletedProcess(
                            ["agent-session"],
                            0,
                            stdout=json.dumps({"ok": True, "data": data}),
                            stderr="",
                        )

                    with mock.patch.object(
                        guard, "run_cli", side_effect=run_cli
                    ), mock.patch.object(guard, "emit_block") as blocked:
                        self.assertEqual(
                            guard._pre_tool_locked(payload, **common_args), 0
                        )

                    recovered = guard.read_record(record_path)
                    if scenario == "active":
                        blocked.assert_not_called()
                        self.assertEqual(recovered["phase"], "active")
                        self.assertEqual(recovered["lease_id"], "lease-a")
                        self.assertEqual(recovered["lease_revision"], 4)
                    else:
                        self.assertEqual(recovered, admitting)
                        expected = (
                            "already terminal"
                            if scenario == "terminal"
                            else "remains uncertain"
                        )
                        self.assertIn(expected, blocked.call_args.args[0])
                    self.assertTrue(token_path.exists())
                    self.assertTrue(targets_path.exists())
                    self.assertEqual(
                        any(
                            "work-context" in args and "admit" in args
                            for args in calls
                        ),
                        scenario == "unsupported",
                    )


    def test_admission_recovery_persistence_failure_is_explicitly_fail_closed(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_admission_persistence_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "operation.json"
            token_path = Path(tmp) / "operation.attempt.token"
            targets_path = Path(tmp) / "operation.attempt.targets.json"
            outcome_path = Path(tmp) / "operation.attempt.outcome"
            token_path.write_text("private-token\n", encoding="utf-8")
            token_path.chmod(0o600)
            targets_path.write_text("{}\n", encoding="utf-8")
            targets_path.chmod(0o600)
            admitting = {
                "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                "phase": "admitting",
                "session": "managed-session",
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "claim_id": "claim-a",
                "claim_revision": 3,
                "session_incarnation": "incarnation-1",
                "operation": "edit",
                "token_file": str(token_path),
                "targets_file": str(targets_path),
                "outcome_file": str(outcome_path),
                "admit_idempotency": "admit-persistence-0001",
                "complete_idempotency": "complete-persistence-0001",
            }
            path.write_text(json.dumps(admitting) + "\n", encoding="utf-8")
            path.chmod(0o600)
            evidence = {
                "disposition": "admitted",
                "lease_id": "lease-a",
                "lease_revision": 4,
            }

            with mock.patch.object(guard, "replace_private", return_value=False):
                self.assertFalse(
                    guard.persist_admitted_record(path, admitting, evidence)
                )

            self.assertEqual(guard.read_record(path), admitting)
            lease_result = subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps(
                    {
                        "ok": True,
                        "data": {
                            "schema_version": "agent-session.operation-lease.v1",
                            "lease_id": "lease-a",
                            "revision": 4,
                            "state": "active",
                        },
                    }
                ),
                stderr="",
            )
            with mock.patch.object(
                guard, "run_cli", return_value=lease_result
            ), mock.patch.object(guard, "replace_private", return_value=False):
                self.assertEqual(
                    guard.submit_admission(
                        "/trusted/agent-session", path, admitting
                    ),
                    ("uncertain", guard.ADMISSION_RECORD_PERSISTENCE_FAILURE),
                )
            with mock.patch.object(
                guard,
                "exact_external_reconciliation_evidence",
                return_value={path: evidence},
            ), mock.patch.object(guard, "replace_private", return_value=False):
                self.assertEqual(
                    guard.recover_admission(
                        "/trusted/agent-session", path, admitting
                    ),
                    ("uncertain", guard.ADMISSION_RECORD_PERSISTENCE_FAILURE),
                )
            with mock.patch.object(
                guard, "next_reconciliation_round", return_value=0
            ), mock.patch.object(
                guard,
                "reserve_reconciliation_groups",
                return_value=[
                    (guard.exact_external_reconciliation_key(admitting), 0)
                ],
            ), mock.patch.object(
                guard,
                "exact_external_reconciliation_evidence",
                return_value={path: evidence},
            ), mock.patch.object(
                guard, "replace_private", return_value=False
            ), mock.patch.object(guard, "emit_system") as emitted:
                self.assertEqual(
                    guard.retire_externally_reconciled_records(
                        "/trusted/agent-session", [path]
                    ),
                    set(),
                )
            self.assertIn("could not be persisted", emitted.call_args.args[0])
            self.assertEqual(guard.read_record(path), admitting)
            self.assertTrue(token_path.exists())
            self.assertTrue(targets_path.exists())


    def test_safe_malformed_reconciliation_cursor_repairs_then_retires(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_failure_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        record = {
            "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
            "phase": "active",
            "session": "managed-session",
            "capability_file": "/private/capability",
            "state_dir": "/private/state",
            "claim_id": "claim-a",
            "claim_revision": 1,
            "session_incarnation": "incarnation-1",
            "lease_id": "lease-a",
            "lease_revision": 1,
        }
        malformed_bodies = (
            "{\n",
            "x" * (64 * 1024 + 1),
            json.dumps({"schema_version": "unsupported.cursor.v9"}) + "\n",
        )
        for malformed in malformed_bodies:
            with self.subTest(size=len(malformed)):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    path = root / "operation.json"
                    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                    path.chmod(0o600)
                    cursor_path = root / ".broker-proof-cursor"
                    cursor_path.write_text(malformed, encoding="utf-8")
                    cursor_path.chmod(0o600)
                    evidence = {path: {"disposition": "terminal"}}

                    with mock.patch.object(
                        guard,
                        "exact_external_reconciliation_evidence",
                        return_value=evidence,
                    ) as exact_proof:
                        self.assertEqual(
                            guard.retire_externally_reconciled_records(
                                "/trusted/agent-session", [path]
                            ),
                            {path},
                        )
                    exact_proof.assert_called_once()
                    self.assertFalse(path.exists())
                    self.assertIsNotNone(
                        guard.read_reconciliation_cursor(cursor_path)
                    )


    def test_reconciliation_cursor_reads_from_validated_descriptor(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_descriptor_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        with tempfile.TemporaryDirectory() as tmp:
            cursor_path = Path(tmp) / ".broker-proof-cursor"
            expected = {
                "schema_version": guard.STOP_RECONCILIATION_CURSOR_SCHEMA,
                "round": 0,
                "groups": {},
            }
            cursor_path.write_text(
                json.dumps(expected) + "\n", encoding="utf-8"
            )
            cursor_path.chmod(0o600)
            with mock.patch.object(
                Path,
                "read_text",
                side_effect=AssertionError("cursor path must not be reopened"),
            ):
                self.assertEqual(
                    guard.read_reconciliation_cursor(cursor_path), expected
                )


    def test_unsafe_reconciliation_cursor_paths_fail_closed(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_unsafe_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        diagnostic = (
            "Session coordination exact-proof recovery remains pending because "
            "its private scheduling cursor could not be safely initialized or "
            "repaired."
        )
        record = {
                "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                "phase": "active",
                "session": "managed-session",
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "claim_id": "claim-a",
                "claim_revision": 1,
                "session_incarnation": "incarnation-1",
                "lease_id": "lease-a",
                "lease_revision": 1,
        }
        for unsafe_kind in (
            "symlink",
            "unsafe-mode",
            "directory",
            "hardlink",
        ):
            with self.subTest(unsafe_kind=unsafe_kind):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    path = root / "operation.json"
                    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                    path.chmod(0o600)
                    cursor_path = root / ".broker-proof-cursor"
                    linked_target: Path | None = None
                    if unsafe_kind == "symlink":
                        target = root / "cursor-target"
                        target.write_text("{\n", encoding="utf-8")
                        target.chmod(0o600)
                        cursor_path.symlink_to(target)
                    elif unsafe_kind == "unsafe-mode":
                        cursor_path.write_text("{\n", encoding="utf-8")
                        cursor_path.chmod(0o644)
                    elif unsafe_kind == "hardlink":
                        linked_target = root / "cursor-target"
                        linked_target.write_text("{\n", encoding="utf-8")
                        linked_target.chmod(0o600)
                        os.link(linked_target, cursor_path)
                    else:
                        cursor_path.mkdir(mode=0o700)
                    original_cursor = (
                        cursor_path.read_bytes()
                        if cursor_path.is_file()
                        else None
                    )
                    with mock.patch.object(
                        guard, "exact_external_reconciliation_evidence"
                    ) as exact_proof, mock.patch.object(
                        guard, "emit_system"
                    ) as emitted:
                        self.assertEqual(
                            guard.retire_externally_reconciled_records(
                                "/trusted/agent-session", [path]
                            ),
                            set(),
                        )
                    exact_proof.assert_not_called()
                    emitted.assert_called_once_with(diagnostic)
                    self.assertEqual(guard.read_record(path), record)
                    if linked_target is not None:
                        assert original_cursor is not None
                        self.assertEqual(cursor_path.read_bytes(), original_cursor)
                        self.assertEqual(linked_target.read_bytes(), original_cursor)


    def test_reconciliation_cursor_persistence_failures_preserve_records(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_persistence_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        record = {
            "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
            "phase": "active",
            "session": "managed-session",
            "capability_file": "/private/capability",
            "state_dir": "/private/state",
            "claim_id": "claim-a",
            "claim_revision": 1,
            "session_incarnation": "incarnation-1",
            "lease_id": "lease-a",
            "lease_revision": 1,
        }
        for cursor_state in ("missing", "malformed"):
            with self.subTest(cursor_state=cursor_state):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    path = root / "operation.json"
                    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                    path.chmod(0o600)
                    cursor_path = root / ".broker-proof-cursor"
                    original_cursor: bytes | None = None
                    persistence_helper = "write_private"
                    if cursor_state == "malformed":
                        cursor_path.write_text("{\n", encoding="utf-8")
                        cursor_path.chmod(0o600)
                        original_cursor = cursor_path.read_bytes()
                        persistence_helper = "replace_private"

                    with mock.patch.object(
                        guard, persistence_helper, return_value=False
                    ), mock.patch.object(
                        guard, "exact_external_reconciliation_evidence"
                    ) as exact_proof, mock.patch.object(
                        guard, "emit_system"
                    ) as emitted:
                        self.assertEqual(
                            guard.retire_externally_reconciled_records(
                                "/trusted/agent-session", [path]
                            ),
                            set(),
                        )
                    exact_proof.assert_not_called()
                    emitted.assert_called_once_with(
                        guard.RECONCILIATION_CURSOR_FAILURE_MESSAGE
                    )
                    self.assertEqual(guard.read_record(path), record)
                    if original_cursor is None:
                        self.assertFalse(cursor_path.exists())
                    else:
                        self.assertEqual(cursor_path.read_bytes(), original_cursor)


    def test_reconciliation_group_reservation_failure_emits_cursor_diagnostic(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_reservation_failure_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        record = {
            "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
            "phase": "active",
            "session": "managed-session",
            "capability_file": "/private/capability",
            "state_dir": "/private/state",
            "claim_id": "claim-a",
            "claim_revision": 1,
            "session_incarnation": "incarnation-1",
            "lease_id": "lease-a",
            "lease_revision": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "operation.json"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            path.chmod(0o600)
            cursor_path = root / ".broker-proof-cursor"
            cursor_path.write_text(
                json.dumps(
                    {
                        "schema_version": guard.STOP_RECONCILIATION_CURSOR_SCHEMA,
                        "round": 0,
                        "groups": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cursor_path.chmod(0o600)
            original_replace = guard.replace_private
            replacement_calls = 0

            def fail_reservation_replace(
                target: Path, body: Mapping[str, Any]
            ) -> bool:
                nonlocal replacement_calls
                replacement_calls += 1
                if replacement_calls == 1:
                    return original_replace(target, body)
                return False

            with mock.patch.object(
                guard,
                "replace_private",
                side_effect=fail_reservation_replace,
            ), mock.patch.object(
                guard, "exact_external_reconciliation_evidence"
            ) as exact_proof, mock.patch.object(
                guard, "emit_system"
            ) as emitted:
                self.assertEqual(
                    guard.retire_externally_reconciled_records(
                        "/trusted/agent-session", [path]
                    ),
                    set(),
                )
            self.assertEqual(replacement_calls, 2)
            exact_proof.assert_not_called()
            emitted.assert_called_once_with(
                guard.RECONCILIATION_CURSOR_FAILURE_MESSAGE
            )
            self.assertEqual(guard.read_record(path), record)


    def test_reconciliation_cursor_serializes_distinct_rounds(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_lock_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "operation.json"
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                rounds = list(
                    pool.map(
                        lambda _index: guard.next_reconciliation_round([path]),
                        range(2),
                    )
                )
            self.assertEqual(sorted(rounds), [0, 1])
            cursor = json.loads(
                (Path(tmp) / ".broker-proof-cursor").read_text(encoding="utf-8")
            )
            self.assertEqual(cursor["round"], 2)

            group_key = (
                "managed-session",
                "/private/capability",
                "/private/state",
                "incarnation-1",
            )
            self.assertEqual(
                guard.reserve_reconciliation_groups(
                    [path],
                    [group_key],
                    round_index=1,
                    record_cycle=1,
                ),
                [(group_key, 1)],
            )
            persisted = (Path(tmp) / ".broker-proof-cursor").read_bytes()
            self.assertIsNone(
                guard.reserve_reconciliation_groups(
                    [path],
                    [group_key],
                    round_index=0,
                    record_cycle=1,
                )
            )
            self.assertEqual(
                (Path(tmp) / ".broker-proof-cursor").read_bytes(), persisted
            )


    def test_bounded_rotation_copies_only_the_selected_window(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_bounded_rotation_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        class SliceTrackingList(list[int]):
            def __init__(self, values: range) -> None:
                super().__init__(values)
                self.copied = 0

            def __getitem__(self, key: object) -> Any:
                result = super().__getitem__(key)
                if isinstance(key, slice):
                    self.copied += len(result)
                return result

        values = SliceTrackingList(range(10_000))
        window = guard.bounded_rotated_window(
            values, 9_990, 128, stride=1
        )
        self.assertEqual(
            window, list(range(9_990, 10_000)) + list(range(118))
        )
        self.assertEqual(values.copied, 128)


    def test_reconciliation_cursor_eviction_keeps_epoch_progress(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_cursor_eviction_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        def group_key(index: int) -> tuple[str, str, str, str]:
            return (
                f"managed-session-{index}",
                f"/private/capability-{index}",
                f"/private/state-{index}",
                f"incarnation-{index}",
            )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "operation.json"
            record_cycle = guard.MAX_STOP_RECONCILIATION_CURSOR_GROUPS + 1
            for round_index in range(record_cycle):
                self.assertEqual(
                    guard.next_reconciliation_round([path]), round_index
                )
                self.assertEqual(
                    guard.reserve_reconciliation_groups(
                        [path],
                        [group_key(round_index)],
                        round_index=round_index,
                        record_cycle=record_cycle,
                    ),
                    [(group_key(round_index), 0)],
                )

            round_index = record_cycle
            self.assertEqual(
                guard.next_reconciliation_round([path]), round_index
            )
            self.assertEqual(
                guard.reserve_reconciliation_groups(
                    [path],
                    [group_key(0)],
                    round_index=round_index,
                    record_cycle=record_cycle,
                ),
                [(group_key(0), 1)],
            )
            cursor = json.loads(
                (Path(tmp) / ".broker-proof-cursor").read_text(encoding="utf-8")
            )
            self.assertLessEqual(
                len(cursor["groups"]),
                guard.MAX_STOP_RECONCILIATION_CURSOR_GROUPS,
            )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "operation.json"
            group_keys = [group_key(index) for index in range(128)]
            selected: set[tuple[str, str, str, str]] = set()
            for round_index in range(64):
                self.assertEqual(
                    guard.next_reconciliation_round([path]), round_index
                )
                reservation = guard.reserve_reconciliation_groups(
                    [path],
                    group_keys,
                    round_index=round_index,
                    record_cycle=129,
                )
                assert reservation is not None
                selected.update(group_key for group_key, _round in reservation)
            self.assertEqual(selected, set(group_keys))


    def test_stop_rotates_past_unknown_admission_window_without_replay(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_admission_rotation_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        session = "managed-session"
        incarnation = "incarnation-1"

        def result(data: dict[str, Any]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps({"ok": True, "data": data}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records: list[Path] = []
            snapshots: dict[Path, dict[str, Any]] = {}
            for index in range(guard.MAX_STOP_ADMISSION_PROOF_PREPARATIONS + 1):
                path = root / f"operation-{index:02d}.json"
                token_path = root / f"operation-{index:02d}.attempt.token"
                targets_path = (
                    root / f"operation-{index:02d}.attempt.targets.json"
                )
                token_path.write_text("private-token\n", encoding="utf-8")
                token_path.chmod(0o600)
                targets_path.write_text("{}\n", encoding="utf-8")
                targets_path.chmod(0o600)
                record = {
                    "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                    "phase": "admitting",
                    "session": session,
                    "capability_file": "/private/capability",
                    "state_dir": "/private/state",
                    "claim_id": "claim-a",
                    "claim_revision": 1,
                    "session_incarnation": incarnation,
                    "operation": "edit",
                    "token_file": str(token_path),
                    "targets_file": str(targets_path),
                    "admit_idempotency": f"admit-{index:02d}",
                }
                path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                path.chmod(0o600)
                records.append(path)
                snapshots[path] = record

            proof_batches: list[list[str]] = []

            def run_cli(
                args: list[str], **_kwargs: Any
            ) -> subprocess.CompletedProcess[str]:
                command = args[args.index("broker") + 1]
                if command == "status":
                    return result(
                        {
                            "schema_version": "agent-session.coordination-broker.v1",
                            "session_id": session,
                            "state": "ready",
                            "generation": 7,
                            "capability_available": True,
                            "heartbeat_fresh": True,
                        }
                    )
                if command == "prepare-admission-proof":
                    admit_key = args[args.index("--admit-idempotency-key") + 1]
                    return result(
                        {
                            "schema_version": "agent-session.broker-admission-proof-preparation.v1",
                            "selector": {
                                "kind": "admission",
                                "admit_idempotency_key": admit_key,
                                "claim_id": "claim-a",
                                "claim_revision": 1,
                                "expected_request_digest": "a" * 64,
                            },
                        }
                    )
                self.assertEqual(command, "proof")
                batch_path = Path(args[args.index("--batch-file") + 1])
                selectors = json.loads(
                    batch_path.read_text(encoding="utf-8")
                )["selectors"]
                keys = [selector["admit_idempotency_key"] for selector in selectors]
                proof_batches.append(keys)
                proofs = []
                for index, key in enumerate(keys):
                    if key == f"admit-{guard.MAX_STOP_ADMISSION_PROOF_PREPARATIONS:02d}":
                        proof = {
                            "kind": "admission",
                            "status": "committed",
                            "provenance": "historical_receipt",
                            "retained": False,
                            "lease_id": "lease-terminal",
                            "state": None,
                            "revision": None,
                            "outcome": None,
                            "claim": {"claim_id": "claim-a", "revision": 1},
                        }
                        proofs.append({"index": index, "ok": True, "proof": proof})
                    else:
                        proofs.append(
                            {
                                "index": index,
                                "ok": False,
                                "error": {"code": "proof-unknown"},
                            }
                        )
                return result(
                    {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": session,
                        "session_incarnation": incarnation,
                        "generation": 7,
                        "proofs": proofs,
                    }
                )

            with mock.patch.object(guard, "run_cli", side_effect=run_cli):
                self.assertEqual(
                    guard.retire_externally_reconciled_records(
                        "/trusted/agent-session", records
                    ),
                    set(),
                )
                retired = guard.retire_externally_reconciled_records(
                    "/trusted/agent-session", records
                )

            terminal_path = records[-1]
            self.assertEqual(retired, {terminal_path})
            self.assertFalse(terminal_path.exists())
            self.assertNotIn("admit-16", proof_batches[0])
            self.assertIn("admit-16", proof_batches[1])
            cursor_path = root / ".broker-proof-cursor"
            self.assertTrue(cursor_path.is_file())
            self.assertEqual(stat.S_IMODE(cursor_path.stat().st_mode), 0o600)
            cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
            self.assertEqual(
                cursor["schema_version"],
                guard.STOP_RECONCILIATION_CURSOR_SCHEMA,
            )
            self.assertEqual(cursor["round"], 2)
            self.assertEqual(len(cursor["groups"]), 1)
            self.assertEqual(
                next(iter(cursor["groups"].values())),
                {
                    "wait": 0,
                    "visits": 2,
                    "last_epoch": 1,
                    "last_wait_epoch": 1,
                    "last_seen": 1,
                },
            )
            for path in records[:-1]:
                self.assertEqual(guard.read_record(path), snapshots[path])


    def test_stop_rotates_reconciliation_groups_to_reach_later_terminal(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_group_rotation_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        def result(data: dict[str, Any]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps({"ok": True, "data": data}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records: list[Path] = []
            snapshots: dict[Path, dict[str, Any]] = {}
            for index in range(3):
                path = root / f"group-{index}.json"
                record = {
                    "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                    "phase": "active",
                    "session": f"managed-session-{index}",
                    "capability_file": f"/private/capability-{index}",
                    "state_dir": f"/private/state-{index}",
                    "claim_id": f"claim-{index}",
                    "claim_revision": 1,
                    "session_incarnation": f"incarnation-{index}",
                    "lease_id": f"lease-{index}",
                    "lease_revision": 1,
                }
                path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                path.chmod(0o600)
                records.append(path)
                snapshots[path] = record

            def scheduling_digest(index: int) -> str:
                group_key = guard.exact_external_reconciliation_key(
                    snapshots[records[index]]
                )
                group_digest = guard.digest(
                    json.dumps(group_key, separators=(",", ":"))
                )
                return group_digest

            terminal_group_index = max(range(1, 3), key=scheduling_digest)
            proved_sessions: list[str] = []

            def run_cli(
                args: list[str], **_kwargs: Any
            ) -> subprocess.CompletedProcess[str]:
                command = args[args.index("broker") + 1]
                session = args[args.index("--session") + 1]
                group_index = int(session.rsplit("-", 1)[1])
                if command == "status":
                    return result(
                        {
                            "schema_version": "agent-session.coordination-broker.v1",
                            "session_id": session,
                            "state": "ready",
                            "generation": 1,
                            "capability_available": True,
                            "heartbeat_fresh": True,
                        }
                    )
                self.assertEqual(command, "proof")
                proved_sessions.append(session)
                return result(
                    {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": session,
                        "session_incarnation": f"incarnation-{group_index}",
                        "generation": 1,
                        "proofs": [
                            {
                                "index": 0,
                                "ok": True,
                                "proof": {
                                    "kind": "operation",
                                    "found": True,
                                    "lease_id": f"lease-{group_index}",
                                    "state": (
                                        "completed"
                                        if group_index == terminal_group_index
                                        else "active"
                                    ),
                                    "revision": 1,
                                    "claim": {
                                        "claim_id": f"claim-{group_index}",
                                        "revision": 1,
                                    },
                                },
                            }
                        ],
                    }
                )

            with mock.patch.object(guard, "run_cli", side_effect=run_cli):
                self.assertEqual(
                    guard.retire_externally_reconciled_records(
                        "/trusted/agent-session", records
                    ),
                    set(),
                )
                retired = guard.retire_externally_reconciled_records(
                    "/trusted/agent-session", records
                )

            self.assertEqual(retired, {records[terminal_group_index]})
            self.assertEqual(
                set(proved_sessions[:2]),
                {
                    f"managed-session-{index}"
                    for index in range(3)
                    if index != terminal_group_index
                },
            )
            self.assertIn(
                f"managed-session-{terminal_group_index}", proved_sessions[2:]
            )
            for index, path in enumerate(records):
                if index != terminal_group_index:
                    self.assertEqual(guard.read_record(path), snapshots[path])


    def test_group_churn_cannot_starve_stable_terminal_record(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_group_churn_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def key(index: int) -> tuple[str, str, str, str]:
                return (
                    f"managed-session-{index}",
                    f"/private/capability-{index}",
                    f"/private/state-{index}",
                    f"incarnation-{index}",
                )

            candidates = list(range(20))
            def scheduling_digest(index: int) -> str:
                group_digest = guard.digest(
                    json.dumps(key(index), separators=(",", ":"))
                )
                return group_digest

            candidates.sort(key=scheduling_digest)
            target_index = candidates[-1]
            churn_indexes = candidates[:4]

            def write_active(index: int) -> tuple[Path, dict[str, Any]]:
                group_key = key(index)
                path = root / f"operation-{index}.json"
                record = {
                    "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                    "phase": "active",
                    "session": group_key[0],
                    "capability_file": group_key[1],
                    "state_dir": group_key[2],
                    "claim_id": f"claim-{index}",
                    "claim_revision": 1,
                    "session_incarnation": group_key[3],
                    "lease_id": f"lease-{index}",
                    "lease_revision": 1,
                }
                path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                path.chmod(0o600)
                return path, record

            target_path, target = write_active(target_index)
            first_churn = [write_active(index) for index in churn_indexes[:2]]
            second_churn = [write_active(index) for index in churn_indexes[2:]]
            proved_sessions: list[str] = []

            def exact_evidence(
                _executable: str,
                snapshots: list[tuple[Path, dict[str, Any]]],
                **_kwargs: Any,
            ) -> dict[Path, dict[str, Any]]:
                proved_sessions.append(snapshots[0][1]["session"])
                if snapshots[0][0] == target_path:
                    return {target_path: {"disposition": "terminal"}}
                return {}

            with mock.patch.object(
                guard,
                "exact_external_reconciliation_evidence",
                side_effect=exact_evidence,
            ):
                first_records = [path for path, _record in first_churn]
                first_records.append(target_path)
                self.assertEqual(
                    guard.retire_externally_reconciled_records(
                        "/trusted/agent-session", first_records
                    ),
                    set(),
                )
                self.assertNotIn(target["session"], proved_sessions)
                second_records = [path for path, _record in second_churn]
                second_records.append(target_path)
                retired = guard.retire_externally_reconciled_records(
                    "/trusted/agent-session", second_records
                )

            self.assertEqual(retired, {target_path})
            self.assertIn(target["session"], proved_sessions)
            self.assertFalse(target_path.exists())
            for path, record in first_churn + second_churn:
                self.assertEqual(guard.read_record(path), record)
            cursor_text = (root / ".broker-proof-cursor").read_text(encoding="utf-8")
            self.assertNotIn("managed-session", cursor_text)
            self.assertNotIn("/private/", cursor_text)


    def test_nested_reconciliation_retires_terminal_beyond_all_caps(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_nested_integration_contract",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        def result(data: dict[str, Any]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                ["agent-session"],
                0,
                stdout=json.dumps({"ok": True, "data": data}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records: list[Path] = []
            snapshots: dict[Path, dict[str, Any]] = {}
            terminal_key = "admit-3-048"
            terminal_path: Path | None = None
            preserved_sidecars: tuple[Path, Path] | None = None
            for record_index in range(64):
                for group_index in range(4):
                    stem = f"operation-{record_index:03d}-{group_index}"
                    path = root / f"{stem}.json"
                    token_path = root / f"{stem}.attempt.token"
                    targets_path = root / f"{stem}.attempt.targets.json"
                    token_path.write_text("private-token\n", encoding="utf-8")
                    token_path.chmod(0o600)
                    targets_path.write_text("{}\n", encoding="utf-8")
                    targets_path.chmod(0o600)
                    admit_key = f"admit-{group_index}-{record_index:03d}"
                    record = {
                        "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                        "phase": "admitting",
                        "session": f"managed-session-{group_index}",
                        "capability_file": f"/private/capability-{group_index}",
                        "state_dir": f"/private/state-{group_index}",
                        "claim_id": f"claim-{group_index}",
                        "claim_revision": 1,
                        "session_incarnation": f"incarnation-{group_index}",
                        "operation": "edit",
                        "token_file": str(token_path),
                        "targets_file": str(targets_path),
                        "admit_idempotency": admit_key,
                    }
                    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                    path.chmod(0o600)
                    records.append(path)
                    snapshots[path] = record
                    if admit_key == terminal_key:
                        terminal_path = path
                    elif preserved_sidecars is None:
                        preserved_sidecars = (token_path, targets_path)

            proof_calls = 0

            def prepared_selector(
                _executable: str, _path: Path, record: dict[str, Any]
            ) -> dict[str, Any]:
                return {
                    "kind": "admission",
                    "admit_idempotency_key": record["admit_idempotency"],
                    "claim_id": record["claim_id"],
                    "claim_revision": 1,
                    "expected_request_digest": "a" * 64,
                }

            def run_cli(
                args: list[str], **_kwargs: Any
            ) -> subprocess.CompletedProcess[str]:
                nonlocal proof_calls
                command = args[args.index("broker") + 1]
                session = args[args.index("--session") + 1]
                group_index = int(session.rsplit("-", 1)[1])
                if command == "status":
                    return result(
                        {
                            "schema_version": "agent-session.coordination-broker.v1",
                            "session_id": session,
                            "state": "ready",
                            "generation": 1,
                            "capability_available": True,
                            "heartbeat_fresh": True,
                        }
                    )
                self.assertEqual(command, "proof")
                proof_calls += 1
                batch_path = Path(args[args.index("--batch-file") + 1])
                selectors = json.loads(batch_path.read_text(encoding="utf-8"))[
                    "selectors"
                ]
                self.assertLessEqual(
                    len(selectors), guard.MAX_STOP_ADMISSION_PROOF_PREPARATIONS
                )
                proofs = []
                for index, selector in enumerate(selectors):
                    key = selector["admit_idempotency_key"]
                    if key != terminal_key:
                        proofs.append({"index": index, "ok": False})
                        continue
                    proofs.append(
                        {
                            "index": index,
                            "ok": True,
                            "proof": {
                                "kind": "admission",
                                "status": "committed",
                                "provenance": "historical_receipt",
                                "retained": False,
                                "lease_id": "lease-terminal",
                                "state": None,
                                "revision": None,
                                "outcome": None,
                                "claim": {
                                    "claim_id": f"claim-{group_index}",
                                    "revision": 1,
                                },
                            },
                        }
                    )
                return result(
                    {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": session,
                        "session_incarnation": f"incarnation-{group_index}",
                        "generation": 1,
                        "proofs": proofs,
                    }
                )

            assert terminal_path is not None and preserved_sidecars is not None
            retired: set[Path] = set()
            with mock.patch.object(
                guard, "prepared_admission_selector", side_effect=prepared_selector
            ), mock.patch.object(guard, "run_cli", side_effect=run_cli):
                for _audit in range(256):
                    before = proof_calls
                    retired.update(
                        guard.retire_externally_reconciled_records(
                            "/trusted/agent-session", records
                        )
                    )
                    self.assertLessEqual(
                        proof_calls - before, guard.MAX_STOP_RECONCILIATION_GROUPS
                    )
                    if terminal_path in retired:
                        break

            self.assertEqual(retired, {terminal_path})
            self.assertFalse(terminal_path.exists())
            for path in records:
                if path != terminal_path:
                    self.assertEqual(guard.read_record(path), snapshots[path])
            self.assertTrue(all(path.exists() for path in preserved_sidecars))


    def test_coordination_capability_is_locked_after_ordinary_rules(self) -> None:
        for product in ("codex", "claude"):
            transactions = inventory_rules(
                product=product,
                event="PreToolUse",
                capability="agent-session.coordination.v1",
            )
            self.assertTrue(transactions, product)
            self.assertTrue(
                all(rule["override_class"] == "locked" for rule in transactions)
            )
            self.assertTrue(
                all(rule["failure_posture"] == "closed" for rule in transactions)
            )
            for transaction in transactions:
                transaction_tools = inventory_tools([transaction])
                ordinary = [
                    rule
                    for rule in inventory_rules(product=product, event="PreToolUse")
                    if rule["capability"]["id"] != "agent-session.coordination.v1"
                    and inventory_tools([rule]) & transaction_tools
                ]
                self.assertTrue(ordinary, transaction["id"])
                self.assertGreater(
                    transaction["priority"],
                    max(rule["priority"] for rule in ordinary),
                )

        self.assertEqual(load_claude_hook_fragment()["hooks"], {})
        self.assertNotIn(
            "command =",
            (
                REPO_ROOT / "targets" / "codex" / "hooks" / "config.block.toml"
            ).read_text(encoding="utf-8"),
        )


    def test_target_hook_fragments_reference_installed_shared_scripts(self) -> None:
        shared_registered_scripts = {
            "agent-scope-lock-guard.py",
            "block-direct-git-commit.py",
            "block-direct-git-worktree.py",
            "block-direct-pr-create.py",
            "block-direct-python.py",
            "block-project-memory-write.py",
            "block-unsafe-default-delivery.py",
            "checkout-lease-guard.py",
            "finish-line-record.py",
            "forge-label-reminder.py",
            "mcp-secret-scan.py",
            "portable-paths-scan.py",
            "semantic-commit-body-gate.py",
            "session-coordination-guard.py",
            "session-start-healthcheck.sh",
            "stop-finish-line-gate.py",
        }
        codex_claude_scripts = {
            "user-prompt-agent-memory.sh",
        }
        for script in shared_registered_scripts | codex_claude_scripts:
            self.assertTrue((HOOK_DIR / script).is_file(), script)
            self.assertTrue(os.access(HOOK_DIR / script, os.X_OK), script)

        codex_block = (REPO_ROOT / "targets" / "codex" / "hooks" / "config.block.toml").read_text(
            encoding="utf-8"
        )
        claude_fragment = (REPO_ROOT / "core" / "hooks" / "claude" / "settings.hooks.jsonc").read_text(
            encoding="utf-8"
        )
        for script in shared_registered_scripts:
            handler = script.rsplit(".", 1)[0]
            rules = (
                inventory_rules(capability="agent-session.coordination.v1")
                if handler == "session-coordination-guard"
                else inventory_rules(handler=handler)
            )
            self.assertTrue(
                rules,
                f"missing policy inventory for {script}",
            )
        for script in codex_claude_scripts:
            handler = script.rsplit(".", 1)[0]
            rules = [
                rule
                for rule in load_hook_inventory()
                if rule["capability"].get("handler_id") == handler
            ]
            self.assertTrue(rules, script)
            self.assertEqual(
                {tuple(rule["products"]) for rule in rules},
                {("codex",), ("claude",)},
            )
        self.assertNotIn("/hooks/", codex_block)
        self.assertNotIn("/hooks/", claude_fragment)


    def test_declared_validation_shape_is_admitted_by_delivery_classifier(
        self,
    ) -> None:
        declared = "bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast"
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, commands=(declared,))
            catalog = tomllib.loads(
                (repo / "VALIDATION.toml").read_text(encoding="utf-8")
            )
            command = catalog["validation"][0]["commands"][0]

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(command),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    'export PATH="$HOME/.cargo/bin:$PATH"; ' + command
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "rule=opaque-shell-resolution")


    def test_opaque_candidates_skip_literal_test_operands(self) -> None:
        # A `[`/`[[` operand is never executed, so its words cannot hide a
        # governed command; a substitution among them is its own command.
        for words in (
            ["[[", '"$p"', "==", "*CLAUDE.md", "]]"],
            ["[", "$a", "=", "$b", "]"],
            ["[[", "$s", "==", "9c2dc137*", "]]"],
        ):
            with self.subTest(words=words):
                self.assertEqual(
                    hook_common.opaque_invocation_candidates(
                        [hook_common.OPAQUE_WRAPPER_COMMAND, *words],
                        {"git", "semantic-commit"},
                    ),
                    [],
                )
        for command in ('[ "$a" = "$b" ] && echo same', '[[ $p == *x ]] || true'):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_raw_deletion_verbs_keep_ordinary_file_and_read_admission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "primary"
            self._init_checkout_lease_repo(primary)
            for mode in ("advisory", "enforce"):
                for command in ("unlink README.md", "shred --remove README.md",
                                "find README.md -delete", "find README.md -exec rm {} +",
                                "find . -print", "find . -name -delete -print",
                                "find . -exec echo -delete {} +",
                                "find . -exec rm README.md +",
                                "find . -fprintf output.txt -delete"):
                    with self.subTest(mode=mode, command=command):
                        payload = self._checkout_lease_payload(
                            "owner", primary, tool_name="Bash", command=command
                        )
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", payload, cwd=primary,
                            env={"AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_allowed(decision)


    def test_raw_rm_literal_variable_file_keeps_ordinary_admission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "primary"
            self._init_checkout_lease_repo(primary)
            for mode in ("", "off", "advisory", "enforce"):
                for command in ('rm README.md', 'ARTIFACT=README.md; rm "$ARTIFACT"'):
                    with self.subTest(mode=mode, command=command):
                        payload = self._checkout_lease_payload("owner", primary, tool_name="Bash", command=command)
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", payload, cwd=primary,
                            env={"AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_allowed(decision)


    def test_coordination_guard_trusts_the_per_user_root_through_a_symlinked_ancestor(
        self,
    ) -> None:
        with self._managed_cli_home_fixture(symlinked_ancestor=True) as (home_bin, _other):
            module = self._load("coord_symlinked_home", "session-coordination-guard.py")
            os.environ["PATH"] = f"{home_bin}{os.pathsep}/usr/bin"
            self.assertIsNotNone(module.resolved_trusted_cli("agent-session"))


    def test_coordination_guard_trusts_the_per_user_root(self) -> None:
        with self._managed_cli_home_fixture() as (home_bin, other_bin):
            module = self._load("coord_home_root", "session-coordination-guard.py")
            os.environ["PATH"] = f"{home_bin}{os.pathsep}/usr/bin"
            self.assertIsNotNone(module.resolved_trusted_cli("agent-session"))
            os.environ["PATH"] = f"{other_bin}{os.pathsep}/usr/bin"
            self.assertIsNone(module.resolved_trusted_cli("agent-session"))

