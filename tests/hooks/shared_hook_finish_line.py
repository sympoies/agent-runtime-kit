"""Shared hook tests: finish line."""
from __future__ import annotations

from shared_hook_helpers import (
    HOOK_DIR,
    HookTestCase,
    Path,
    REPO_ROOT,
    command_event_payload,
    command_payload,
    gate_env,
    hashlib,
    importlib,
    inventory_rules,
    inventory_tools,
    json,
    os,
    run_hook,
    shlex,
    shutil,
    subprocess,
    sys,
    tempfile,
    time,
    write_payload,
)


class FinishLineTests(HookTestCase):

    def test_finish_line_gate_blocks_unvalidated_edit_then_releases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            # No edits yet: the gate allows.
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # A code edit marks the repo dirty.
            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            # The gate now blocks, naming the outstanding validation command.
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")
            assert decision is not None
            reason = str(decision.get("reason", ""))
            self.assertIn("Declared validation contract:", reason)
            self.assertIn("Outstanding for this edit generation:", reason)
            self.assertIn("session-scoped", reason)
            self.assertIn("Stop consolidates", reason)
            self.assertIn("removes completed session state when present", reason)
            self.assertIn("own tool call with no preceding shell state", reason)
            self.assertIn("absolute interpreter", reason)
            self.assertNotIn("Running it records", reason)

            # Running the declared validation records the run.
            self._run_declared_validation(repo, "bash scripts/ci/all.sh", env=env)

            # The gate releases now that validation ran after the edit.
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_finish_line_record_ignores_eventless_validation_payload(self) -> None:
        """Validation credit requires the PreToolUse outcome wrapper.

        A Bash payload without ``hook_event_name`` carries no observed exit
        status, so it must never credit the declared validation. Real provider
        payloads always name their event.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            code, decision, stderr = run_hook(
                "finish-line-record.py",
                command_payload("bash scripts/ci/all.sh"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_gate_names_the_recovery_lane_by_absolute_path(self) -> None:
        # The block text is read inside the repository being validated, which is
        # normally not this one. A bare `scripts/validation-recovery.py` reads as
        # a path in that repository, where it does not exist, so a blocked agent
        # looks in the wrong tree and concludes the lane is unavailable.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            # Pin the kit anchor: the validated repo carries no lane of its own,
            # so without this the assertion would follow whatever docs-home the
            # ambient environment happens to export.
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_DOCS_HOME": str(REPO_ROOT),
            }

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert decision is not None
            reason = str(decision.get("reason", ""))

            lane = REPO_ROOT / "scripts" / "validation-recovery.py"
            self.assertTrue(lane.is_file(), f"missing recovery lane: {lane}")
            self.assertIn(f"{lane} run --repo", reason)
            self.assertIn(f"{lane} waive --repo", reason)
            # The relative spelling must not survive as the named command.
            self.assertNotIn("`scripts/validation-recovery.py", reason)
            # The lane must not be described as a path inside the validated repo.
            self.assertFalse((Path(repo) / "scripts" / "validation-recovery.py").exists())


    def test_finish_line_gate_names_the_lane_from_an_installed_copy(self) -> None:
        # `agent-hook setup` materializes hooks as flat copies under the provider
        # home (`~/.claude/hooks/`), not symlinks into this checkout. Walking up
        # from `__file__` there lands outside the kit entirely, so a location-only
        # resolution silently degrades to the relative spelling in exactly the
        # layout every real session uses. Resolve through the documented
        # docs-home env instead, and prove it from a copy.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            installed = Path(tmp) / "provider-home" / "hooks"
            installed.mkdir(parents=True)
            for name in ("stop-finish-line-gate.py", "hook_common.py"):
                shutil.copy2(REPO_ROOT / "core" / "hooks" / "shared" / name, installed / name)

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env={"AGENT_RUNTIME_DOCS_HOME": str(repo)},
            )
            self.assertEqual(code, 0, stderr)

            # The copy sits four levels below a directory that holds no `scripts/`.
            self.assertFalse((installed.parents[2] / "scripts").exists())

            completed = subprocess.run(
                [sys.executable, str(installed / "stop-finish-line-gate.py")],
                input=json.dumps({}),
                capture_output=True,
                text=True,
                cwd=repo,
                env=gate_env({
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_DOCS_HOME": str(REPO_ROOT),
                }),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            reason = str(json.loads(completed.stdout).get("reason", ""))

            lane = REPO_ROOT / "scripts" / "validation-recovery.py"
            self.assertIn(f"{lane} run --repo", reason)
            self.assertNotIn("`scripts/validation-recovery.py", reason)


    def test_finish_line_dirty_state_is_scoped_per_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }

            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = "editing-session"
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)

            code, read_only_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "read-only-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(read_only_decision)

            code, editing_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "editing-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(editing_decision, "scripts/ci/all.sh")

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=env, session_id="editing-session"
            )

            code, editing_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "editing-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(editing_decision)


    def test_finish_line_completed_session_state_is_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            session_id = "completed-session"

            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)

            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            marker_dir = repo / ".cache" / "agent-validation"
            session_dir = marker_dir / f"session-{session_key}"
            self.assertTrue(session_dir.is_dir())

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
            )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            self.assertFalse(session_dir.exists())


    def test_finish_line_completed_cross_product_session_state_is_cleaned(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            session_id = "cross-product-session"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            marker_dir = repo / ".cache" / "agent-validation"
            session_dir = marker_dir / f"session-{session_key}"

            for product in ("codex", "claude"):
                env = {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_PRODUCT": product,
                }
                edit = write_payload(f"src/{product}.rs", f"fn {product}() {{}}\n")
                edit["session_id"] = session_id
                code, _, stderr = run_hook(
                    "finish-line-record.py", edit, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)

            for product in ("codex", "claude"):
                env = {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_PRODUCT": product,
                }
                self._run_declared_validation(
                    repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
                )

            codex_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=codex_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(session_dir.is_dir())

            claude_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "claude",
            }
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=claude_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertFalse(session_dir.exists())


    def test_finish_line_edit_invalidates_cross_product_terminal_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            session_id = "cross-product-edit-after-terminal"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            session_dir = (
                repo
                / ".cache"
                / "agent-validation"
                / f"session-{session_key}"
            )
            codex_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            claude_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "claude",
            }

            edit = write_payload("src/lib.rs", "fn first() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=codex_env
            )
            self.assertEqual(code, 0, stderr)
            for env in (codex_env, claude_env):
                self._run_declared_validation(
                    repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
                )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=codex_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            codex_terminal = session_dir / ".terminal-codex"
            self.assertTrue(codex_terminal.is_file())

            edit = write_payload("src/lib.rs", "fn second() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=claude_env
            )
            self.assertEqual(code, 0, stderr)
            self.assertFalse(codex_terminal.exists())

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=claude_env, session_id=session_id
            )
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=claude_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(session_dir.is_dir())

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=codex_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=codex_env, session_id=session_id
            )
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=codex_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertFalse(session_dir.exists())


    def test_finish_line_attempt_invalidates_product_terminal_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            session_id = "cross-product-attempt-after-terminal"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            session_dir = (
                repo
                / ".cache"
                / "agent-validation"
                / f"session-{session_key}"
            )
            codex_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            claude_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "claude",
            }

            edit = write_payload("src/lib.rs", "fn first() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=codex_env
            )
            self.assertEqual(code, 0, stderr)
            for env in (codex_env, claude_env):
                self._run_declared_validation(
                    repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
                )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=codex_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            codex_terminal = session_dir / ".terminal-codex"
            self.assertTrue(codex_terminal.is_file())

            validation = command_event_payload(
                "PreToolUse",
                "bash scripts/ci/all.sh",
                tool_use_id="codex-after-terminal",
            )
            validation["session_id"] = session_id
            code, rewrite, stderr = run_hook(
                "finish-line-record.py", validation, cwd=repo, env=codex_env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(rewrite)
            assert rewrite is not None
            hook_output = rewrite.get("hookSpecificOutput")
            self.assertIsInstance(hook_output, dict)
            assert isinstance(hook_output, dict)
            updated_input = hook_output.get("updatedInput")
            self.assertIsInstance(updated_input, dict)
            assert isinstance(updated_input, dict)
            wrapped = str(updated_input.get("command", ""))
            self.assertFalse(codex_terminal.exists())
            pending = list(session_dir.glob("project-dev.codex.pending.*.json"))
            self.assertEqual(len(pending), 1)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=claude_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(session_dir.is_dir())
            self.assertTrue(pending[0].is_file())

            completed = subprocess.run(
                ["bash", "-lc", wrapped],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(pending[0].exists())
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=codex_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertFalse(session_dir.exists())


    def test_finish_line_contract_stem_product_tokens_do_not_confuse_ownership(
        self,
    ) -> None:
        cases = (
            ("codex", "codex", "claude"),
            ("claude", "claude", "codex"),
            ("shared", "codex", "claude"),
        )
        for token, newer_product, stale_product in cases:
            with self.subTest(token=token), tempfile.TemporaryDirectory() as tmp:
                marker = f".cache/agent-validation/foo.{token}.bar.ok"
                repo = self._init_contract_repo(tmp, marker=marker)
                session_id = f"contract-stem-{token}-product-token"
                session_key = hashlib.sha256(
                    session_id.encode("utf-8")
                ).hexdigest()
                session_dir = (
                    repo
                    / ".cache"
                    / "agent-validation"
                    / f"session-{session_key}"
                )
                envs = {
                    product: {
                        "AGENT_RUNTIME_DOCS_HOME": str(repo),
                        "AGENT_RUNTIME_PRODUCT": product,
                    }
                    for product in ("codex", "claude")
                }

                edit = write_payload("src/lib.rs", "fn first() {}\n")
                edit["session_id"] = session_id
                code, _, stderr = run_hook(
                    "finish-line-record.py",
                    edit,
                    cwd=repo,
                    env=envs[newer_product],
                )
                self.assertEqual(code, 0, stderr)
                for product in ("codex", "claude"):
                    self._run_declared_validation(
                        repo, "bash scripts/ci/all.sh", env=envs[product], session_id=session_id
                    )

                code, decision, stderr = run_hook(
                    "stop-finish-line-gate.py",
                    {"session_id": session_id},
                    cwd=repo,
                    env=envs[newer_product],
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
                self.assertTrue(session_dir.is_dir())

                edit = write_payload("src/lib.rs", "fn second() {}\n")
                edit["session_id"] = session_id
                code, _, stderr = run_hook(
                    "finish-line-record.py",
                    edit,
                    cwd=repo,
                    env=envs[newer_product],
                )
                self.assertEqual(code, 0, stderr)
                self._run_declared_validation(
                    repo, "bash scripts/ci/all.sh", env=envs[newer_product], session_id=session_id
                )

                code, decision, stderr = run_hook(
                    "stop-finish-line-gate.py",
                    {"session_id": session_id},
                    cwd=repo,
                    env=envs[newer_product],
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
                self.assertTrue(session_dir.is_dir())

                code, decision, stderr = run_hook(
                    "stop-finish-line-gate.py",
                    {"session_id": session_id},
                    cwd=repo,
                    env=envs[stale_product],
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "scripts/ci/all.sh")

                self._run_declared_validation(
                    repo, "bash scripts/ci/all.sh", env=envs[stale_product], session_id=session_id
                )
                code, decision, stderr = run_hook(
                    "stop-finish-line-gate.py",
                    {"session_id": session_id},
                    cwd=repo,
                    env=envs[stale_product],
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
                self.assertFalse(session_dir.exists())


    def test_finish_line_reserved_terminal_prefix_contract_state_is_preserved(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = ".cache/agent-validation/.terminal-codex.ok"
            repo = self._init_contract_repo(tmp, marker=marker)
            session_id = "reserved-terminal-prefix-contract"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            session_dir = (
                repo
                / ".cache"
                / "agent-validation"
                / f"session-{session_key}"
            )
            envs = {
                product: {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_PRODUCT": product,
                }
                for product in ("codex", "claude")
            }

            edit = write_payload("src/lib.rs", "fn first() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=envs["codex"]
            )
            self.assertEqual(code, 0, stderr)
            for product in ("codex", "claude"):
                self._run_declared_validation(
                    repo, "bash scripts/ci/all.sh", env=envs[product], session_id=session_id
                )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["codex"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue((session_dir / ".terminal-codex").is_file())

            edit = write_payload("src/lib.rs", "fn second() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=envs["codex"]
            )
            self.assertEqual(code, 0, stderr)
            self.assertTrue((session_dir / ".terminal-codex.dirty").is_file())
            self.assertTrue(
                (session_dir / ".terminal-codex.claude.cmd0.ran").is_file()
            )
            self.assertFalse((session_dir / ".terminal-codex").exists())

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=envs["codex"], session_id=session_id
            )
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["codex"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(session_dir.is_dir())

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["claude"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=envs["claude"], session_id=session_id
            )
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["claude"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertFalse(session_dir.exists())


    def test_finish_line_unknown_terminal_prefix_entry_is_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            session_id = "unknown-terminal-prefix-entry"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            session_dir = (
                repo
                / ".cache"
                / "agent-validation"
                / f"session-{session_key}"
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }

            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
            )
            unknown = session_dir / ".terminal-unknown"
            unknown.touch()

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(session_dir.is_dir())
            self.assertTrue(unknown.is_file())


    def test_finish_line_overlapping_contract_stems_preserve_foreign_owner(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            (repo / "VALIDATION.toml").write_text(
                "[[validation]]\n"
                'context = "project-dev"\n'
                'commands = ["bash scripts/ci/primary.sh"]\n'
                'marker = ".cache/agent-validation/foo.ok"\n\n'
                "[[validation]]\n"
                'context = "project-dev-secondary"\n'
                'commands = ["bash scripts/ci/secondary.sh"]\n'
                'marker = ".cache/agent-validation/foo.codex.ok"\n',
                encoding="utf-8",
            )
            session_id = "overlapping-contract-stems"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            session_dir = (
                repo
                / ".cache"
                / "agent-validation"
                / f"session-{session_key}"
            )
            envs = {
                product: {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_PRODUCT": product,
                }
                for product in ("codex", "claude")
            }

            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=envs["codex"]
            )
            self.assertEqual(code, 0, stderr)
            for command in (
                "bash scripts/ci/primary.sh",
                "bash scripts/ci/secondary.sh",
            ):
                self._run_declared_validation(
                    repo, command, env=envs["codex"], session_id=session_id
                )
            self._run_declared_validation(
                repo, "bash scripts/ci/secondary.sh", env=envs["claude"], session_id=session_id
            )
            self.assertTrue(
                (session_dir / "foo.codex.claude.cmd0.ran").is_file()
            )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["codex"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(session_dir.is_dir())
            self.assertTrue(
                (session_dir / "foo.codex.claude.cmd0.ran").is_file()
            )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["claude"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "bash scripts/ci/primary.sh")

            self._run_declared_validation(
                repo, "bash scripts/ci/primary.sh", env=envs["claude"], session_id=session_id
            )
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=envs["claude"],
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertFalse(session_dir.exists())


    def test_finish_line_cleanup_preserves_a_newer_dirty_generation(self) -> None:
        import importlib.util

        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            session_id = "cleanup-race-session"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            marker_dir = repo / ".cache" / "agent-validation"
            session_dir = marker_dir / f"session-{session_key}"

            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertTrue(session_dir.is_dir())
            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
            )

            dirty = session_dir / "project-dev.dirty"
            spec = importlib.util.spec_from_file_location(
                "stop_finish_line_gate_cleanup",
                HOOK_DIR / "stop-finish-line-gate.py",
            )
            self.assertIsNotNone(spec)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            markers = {
                "dir": str(session_dir),
                "dirty": str(dirty),
                "legacy_dirty": str(
                    marker_dir / "project-dev.dirty"
                ),
                "command_stem": "project-dev.codex",
                "product": "codex",
                "session_key": session_key,
            }
            states = [(markers, False)]
            snapshot = module.completed_state_snapshot(states)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None

            newer_generation = time.time_ns()
            os.utime(dirty, ns=(newer_generation, newer_generation))
            self.assertFalse(
                module.cleanup_completed_session_state(
                    states, expected_snapshot=snapshot
                )
            )
            self.assertTrue(dirty.is_file())


    def test_finish_line_cleanup_rejects_newly_created_session_namespace(
        self,
    ) -> None:
        import importlib.util

        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            marker_dir = repo / ".cache" / "agent-validation"
            marker_dir.mkdir(parents=True)
            legacy_dirty = marker_dir / "project-dev.dirty"
            legacy_dirty.touch()
            session_key = hashlib.sha256(b"created-during-cleanup").hexdigest()
            session_dir = marker_dir / f"session-{session_key}"

            spec = importlib.util.spec_from_file_location(
                "stop_finish_line_gate_namespace_race",
                HOOK_DIR / "stop-finish-line-gate.py",
            )
            self.assertIsNotNone(spec)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            markers = {
                "dir": str(session_dir),
                "dirty": str(session_dir / "project-dev.dirty"),
                "legacy_dirty": str(legacy_dirty),
                "stem": "project-dev",
                "command_stem": "project-dev.codex",
                "product": "codex",
                "session_key": session_key,
            }
            states = [(markers, True)]
            snapshot = module.completed_state_snapshot(states)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None

            session_dir.mkdir()
            self.assertFalse(
                module.cleanup_completed_session_state(
                    states, expected_snapshot=snapshot
                )
            )
            self.assertTrue(legacy_dirty.is_file())


    def test_finish_line_completed_shared_directory_contracts_are_cleaned(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            (repo / "VALIDATION.toml").write_text(
                "[[validation]]\n"
                'context = "project-dev"\n'
                'commands = ["bash scripts/ci/all.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n\n'
                "[[validation]]\n"
                'context = "project-dev-secondary"\n'
                'commands = ["bash scripts/ci/all.sh"]\n'
                'marker = ".cache/agent-validation/secondary.ok"\n',
                encoding="utf-8",
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            session_id = "shared-directory-contracts"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            session_dir = (
                repo
                / ".cache"
                / "agent-validation"
                / f"session-{session_key}"
            )

            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = session_id
            code, _, stderr = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertTrue(session_dir.is_dir())
            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=env, session_id=session_id
            )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": session_id},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertFalse(session_dir.exists())


    def test_finish_line_identified_session_retires_satisfied_legacy_only_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/legacy.rs", "fn legacy() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self._run_declared_validation(repo, "bash scripts/ci/all.sh", env=env)
            code, legacy_decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(legacy_decision)

            marker_dir = repo / ".cache" / "agent-validation"
            legacy_dirty = marker_dir / "project-dev.dirty"
            session_key = hashlib.sha256(
                b"post-upgrade-read-only-session"
            ).hexdigest()
            session_dir = marker_dir / f"session-{session_key}"
            self.assertTrue(legacy_dirty.is_file())
            self.assertFalse(session_dir.exists())

            code, upgraded_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "post-upgrade-read-only-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(upgraded_decision)
            self.assertFalse(legacy_dirty.exists())
            self.assertFalse(session_dir.exists())


    def test_finish_line_legacy_dirty_requires_transition_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/legacy.rs", "fn legacy() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            code, read_only_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "post-upgrade-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            self.assert_blocked(read_only_decision, "scripts/ci/all.sh")

            self._run_declared_validation(
                repo, "bash scripts/ci/all.sh", env=env, session_id="post-upgrade-session"
            )

            code, upgraded_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "post-upgrade-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(upgraded_decision)

            code, fresh_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "fresh-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(fresh_decision)

            code, legacy_decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(legacy_decision)


    def test_finish_line_failure_tombstone_is_scoped_per_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            command = "bash scripts/validate.sh"
            repo = self._init_contract_repo(str(repo_path), (command,))
            script = repo / "scripts" / "validate.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -rf .cache/agent-validation\n"
                "mkdir -p .cache/agent-validation\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "claude",
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
            }

            validation = command_event_payload(
                "PreToolUse", command, tool_use_id="session-failure"
            )
            validation["session_id"] = "failing-session"
            code, rewrite, stderr = run_hook(
                "finish-line-record.py", validation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)

            repo_key = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()
            failing_key = hashlib.sha256(
                "failing-session".encode("utf-8")
            ).hexdigest()
            tombstone_dir = (
                root
                / "runtime-state"
                / "validation-outcomes"
                / repo_key
                / "sessions"
                / f"session-{failing_key}"
            )
            self.assertEqual(len(list(tombstone_dir.glob("attempt-*.json"))), 1)

            code, read_only_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "read-only-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(read_only_decision)

            code, failing_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "failing-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(failing_decision, "failed with exit code 17")
            (repo / ".cache" / "agent-validation").chmod(0o755)

            script.write_text(
                "#!/usr/bin/env bash\nexit 0\n",
                encoding="utf-8",
            )
            successful_validation = command_event_payload(
                "PreToolUse", command, tool_use_id="session-success"
            )
            successful_validation["session_id"] = "successful-session"
            code, rewrite, stderr = run_hook(
                "finish-line-record.py", successful_validation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)

            code, successful_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "successful-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(successful_decision)

            code, failing_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "failing-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(failing_decision, "failed with exit code 17")

            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -rf .cache/agent-validation\n"
                "mkdir -p .cache/agent-validation\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )

            legacy_validation = command_event_payload(
                "PreToolUse", command, tool_use_id="legacy-failure"
            )
            code, rewrite, stderr = run_hook(
                "finish-line-record.py", legacy_validation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)

            code, read_only_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "post-upgrade-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(read_only_decision, command)

            (repo / ".cache" / "agent-validation").chmod(0o755)
            failed_transition = command_event_payload(
                "PreToolUse", command, tool_use_id="upgraded-failure"
            )
            failed_transition["session_id"] = "post-upgrade-session"
            code, rewrite, stderr = run_hook(
                "finish-line-record.py", failed_transition, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)

            code, pending_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "fresh-during-transition"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(pending_decision, command)

            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)

            code, upgraded_failure_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "post-upgrade-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(upgraded_failure_decision, command)
            code, fresh_failure_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "fresh-after-transition-failure"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(fresh_failure_decision, command)

            (repo / ".cache" / "agent-validation").chmod(0o755)
            script.write_text(
                "#!/usr/bin/env bash\nexit 0\n",
                encoding="utf-8",
            )
            upgraded_validation = command_event_payload(
                "PreToolUse", command, tool_use_id="upgraded-success"
            )
            upgraded_validation["session_id"] = "post-upgrade-session"
            code, rewrite, stderr = run_hook(
                "finish-line-record.py", upgraded_validation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)

            code, upgraded_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "post-upgrade-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(upgraded_decision)

            code, fresh_decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {"session_id": "fresh-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(fresh_decision)

            code, legacy_decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(legacy_decision)


    def test_finish_line_gate_uses_completed_status_and_routes_failed_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' 'umbrella resource collision'\nexit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", "bash scripts/ci/all.sh"),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(rewrite)
            assert rewrite is not None
            hook_output = rewrite.get("hookSpecificOutput")
            self.assertIsInstance(hook_output, dict)
            assert isinstance(hook_output, dict)
            self.assertEqual(hook_output.get("permissionDecision"), "allow")
            updated_input = hook_output.get("updatedInput")
            self.assertIsInstance(updated_input, dict)
            assert isinstance(updated_input, dict)
            wrapped = str(updated_input.get("command", ""))
            self.assertIn("__agent_runtime_validation_report_", wrapped)

            # Invocation alone must not release the gate. The wrapped shell's
            # EXIT trap credits only the completed validation outcome.
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")

            failed = subprocess.run(
                ["bash", "-lc", wrapped],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 17)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")
            assert decision is not None
            failure_reason = str(decision.get("reason", ""))
            self.assertIn("`issue` mode (issue-follow-up)", failure_reason)
            self.assertNotIn("L1", failure_reason)
            self.assertIn("earliest owning repository", failure_reason)
            self.assertIn("Do not create", failure_reason)

            waiver_env = {
                **base_env,
                "AGENT_RUNTIME_VALIDATION_WAIVER": "unrelated reproducible failure",
            }
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=waiver_env
            )
            self.assert_blocked(decision, "routing review required")

            # The routing review is a one-shot closeout continuation for this
            # failure signal. A second Stop honors the explicit waiver.
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=waiver_env
            )
            self.assert_allowed(decision)

            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="validation-tool-2"
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            hook_output = rewrite.get("hookSpecificOutput")
            assert isinstance(hook_output, dict)
            updated_input = hook_output.get("updatedInput")
            assert isinstance(updated_input, dict)
            wrapped = str(updated_input.get("command", ""))
            passed = subprocess.run(
                ["bash", "-lc", wrapped],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(passed.returncode, 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_validation_cleanup_preserves_failed_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            command = "rm -rf .cache/agent-validation; exit 17"
            repo = self._init_contract_repo(tmp, (command,))
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", command, tool_use_id="validation-cleanup"
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)

            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_bad_recreated_lock_preserves_recovery_signal(self) -> None:
        lock_setup = {
            "symlink": (
                "ln -s /dev/null "
                ".cache/agent-validation/.agent-runtime-validation.lock"
            ),
            "directory": (
                "mkdir .cache/agent-validation/.agent-runtime-validation.lock"
            ),
        }
        for kind, setup in lock_setup.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                command = (
                    "rm -rf .cache/agent-validation; "
                    "mkdir -p .cache/agent-validation; "
                    f"{setup}; exit 17"
                )
                repo = self._init_contract_repo(tmp, (command,))
                base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
                run_hook(
                    "finish-line-record.py",
                    write_payload("src/lib.rs", "fn main() {}\n"),
                    cwd=repo,
                    env=base_env,
                )
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", command, tool_use_id=f"bad-lock-{kind}"
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)

                completed = subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 17)
                _, decision, _ = run_hook(
                    "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
                )
                self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_external_tombstone_survives_read_only_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command = (
                "rm -rf .cache/agent-validation; "
                "mkdir -p .cache/agent-validation; "
                "chmod 0555 .cache/agent-validation; exit 17"
            )
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(str(repo_path), (command,))
            state_home = root / "runtime-state"
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_STATE_HOME": str(state_home),
            }
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", command, tool_use_id="read-only-recovery"
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)

            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)
            tombstones = list(state_home.rglob("attempt-*.json"))
            self.assertEqual(len(tombstones), 1)
            tombstone = json.loads(tombstones[0].read_text(encoding="utf-8"))
            self.assertEqual(tombstone.get("status"), "completed")
            self.assertEqual(tombstone.get("exit_code"), 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_tombstone_survives_marker_directory_relocation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command = (
                "rm -rf .cache/agent-validation; "
                "mkdir -p relocated; chmod 0555 relocated; "
                "ln -s ../relocated .cache/agent-validation; exit 17"
            )
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(str(repo_path), (command,))
            state_home = root / "runtime-state"
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_STATE_HOME": str(state_home),
            }
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", command, tool_use_id="relocated-marker-state"
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_success_clears_relocated_failure_tombstone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/stateful.sh",))
            script = repo / "scripts" / "stateful.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -rf .cache/agent-validation\n"
                "mkdir -p relocated\n"
                "ln -s ../relocated .cache/agent-validation\n"
                "chmod 0555 relocated\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            def execute(identity: str) -> int:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", "bash scripts/stateful.sh", tool_use_id=identity
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                return subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            self.assertEqual(execute("relocated-failure"), 17)
            (repo / "relocated").chmod(0o755)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            self.assertEqual(execute("relocated-success"), 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_unmatched_authoritative_tombstone_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="contract-changed-after-registration",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertIsNotNone(rewrite)
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\n'
                'commands = ["bash scripts/ci/all.sh"]\n'
                'marker = ".cache/other/project-dev.ok"\n',
                encoding="utf-8",
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "unmatched authoritative")


    def test_finish_line_removed_command_target_blocks_as_contract_change(
        self,
    ) -> None:
        commands = ("bash scripts/a.sh", "bash scripts/b.sh")
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, commands)
            script_a = repo / "scripts" / "a.sh"
            script_b = repo / "scripts" / "b.sh"
            script_a.parent.mkdir(parents=True)
            script_a.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script_b.write_text(
                "#!/usr/bin/env bash\n"
                "rm -f .cache/agent-validation/*.pending.*.json\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script_a.chmod(0o755)
            script_b.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            def execute(command: str, identity: str) -> int:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", command, tool_use_id=identity
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                return subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            self.assertEqual(
                execute(" && ".join(commands), "combined-external-failure"),
                17,
            )
            (repo / ".cache" / "agent-validation").chmod(0o755)
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\n'
                f'commands = ["{commands[0]}"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n',
                encoding="utf-8",
            )
            self.assertEqual(execute(commands[0], "remaining-command-success"), 0)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation target(s) no longer declared")
            assert decision is not None
            self.assertNotIn("failed with exit code 17", str(decision.get("reason", "")))


    def test_finish_line_replaced_command_target_cannot_clear_old_failure(
        self,
    ) -> None:
        old_command = "bash scripts/a.sh"
        new_command = "bash scripts/b.sh"
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, (old_command,))
            script_a = repo / "scripts" / "a.sh"
            script_b = repo / "scripts" / "b.sh"
            script_a.parent.mkdir(parents=True)
            script_a.write_text(
                "#!/usr/bin/env bash\n"
                "rm -f .cache/agent-validation/*.pending.*.json\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script_b.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script_a.chmod(0o755)
            script_b.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            def execute(command: str, identity: str) -> int:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", command, tool_use_id=identity
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                return subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            self.assertEqual(execute(old_command, "old-command-failure"), 17)
            (repo / ".cache" / "agent-validation").chmod(0o755)
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\n'
                f'commands = ["{new_command}"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n',
                encoding="utf-8",
            )
            self.assertEqual(execute(new_command, "new-command-success"), 0)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "validation target(s) no longer declared")


    def test_finish_line_blocks_when_external_tombstone_cannot_register(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(str(repo_path))
            unusable_state = root / "runtime-state"
            unusable_state.write_text("not a directory\n", encoding="utf-8")
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_STATE_HOME": str(unusable_state),
            }
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, decision, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="unavailable-tombstone-state",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assert_blocked(decision, "could not register")


    def test_finish_line_tampered_pending_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="tampered-pending",
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            pending = next(
                (repo / ".cache" / "agent-validation").glob("*.pending.*.json")
            )
            body = json.loads(pending.read_text(encoding="utf-8"))
            body["attempt_started_ns"] += 1_000_000_000_000
            pending.write_text(json.dumps(body) + "\n", encoding="utf-8")

            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_rejects_shell_outcomes_that_can_mask_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, ("bash scripts/ci/all.sh", "bash tests/hooks/run.sh")
            )
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            ambiguous = (
                "bash scripts/ci/all.sh || true",
                "bash scripts/ci/all.sh; true",
                "bash scripts/ci/all.sh | true",
                "bash scripts/ci/all.sh & wait",
                "bash scripts/ci/all.sh; bash tests/hooks/run.sh",
            )
            for index, command in enumerate(ambiguous):
                with self.subTest(command=command):
                    code, advisory, stderr = run_hook(
                        "finish-line-record.py",
                        command_event_payload(
                            "PreToolUse", command, tool_use_id=f"ambiguous-{index}"
                        ),
                        cwd=repo,
                        env=base_env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_unprovable_validation_advisory(advisory)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")
            self.assertFalse(
                list((repo / ".cache" / "agent-validation").glob("*.cmd*.ran"))
            )


    def test_finish_line_unprovable_validation_emits_one_private_advisory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            commands = (
                "TOOLCHAIN_SECRET=/private/runtime bash scripts/ci/all.sh",
                "bash scripts/ci/all.sh; true",
                "bash scripts/ci/all.sh || true",
                "bash scripts/ci/all.sh | true",
                "bash scripts/ci/all.sh & wait",
                "(bash scripts/ci/all.sh)",
                "prepare-runtime && bash scripts/ci/all.sh",
            )
            for index, command in enumerate(commands):
                with self.subTest(command=command):
                    code, advisory, stderr = run_hook(
                        "finish-line-record.py",
                        command_event_payload(
                            "PreToolUse",
                            command,
                            tool_use_id=f"unprovable-advisory-{index}",
                        ),
                        cwd=repo,
                        env=base_env,
                    )
                    self.assertEqual(code, 0, stderr)
                    message = self.assert_unprovable_validation_advisory(advisory)
                    self.assertIn("repository-owned declared validation wrapper", message)
                    self.assertNotIn(command, message)
                    self.assertNotIn("TOOLCHAIN_SECRET", message)
                    self.assertNotIn("/private/runtime", message)

            state = repo / ".cache" / "agent-validation"
            self.assertFalse(list(state.glob("*.pending.*.json")))
            self.assertFalse(list(state.glob("*.cmd*.ran")))

            unusable_state = repo / "unusable-runtime-state"
            unusable_state.write_text("not a directory\n", encoding="utf-8")
            code, advisory, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh; true",
                    tool_use_id="unprovable-advisory-without-state-lock",
                ),
                cwd=repo,
                env={
                    **base_env,
                    "AGENT_RUNTIME_STATE_HOME": str(unusable_state),
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(advisory)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_generated_wrapper_is_not_warned_or_nested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="wrapper-origin",
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            hook_output = rewrite["hookSpecificOutput"]
            assert isinstance(hook_output, dict)
            updated_input = hook_output["updatedInput"]
            assert isinstance(updated_input, dict)
            wrapped = str(updated_input["command"])

            code, decision, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", wrapped, tool_use_id="wrapper-replayed"
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNone(decision)


    def test_finish_line_preserves_quoted_operator_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, ("bash scripts/ci/all.sh '||' true",)
            )
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            code, advisory, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh || true",
                    tool_use_id="quoted-operator-provenance",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(advisory)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_preserves_expansion_quote_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("printf %s '$(exit 17)'",))
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            code, advisory, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    'printf %s "$(exit 17)"',
                    tool_use_id="expansion-quote-provenance",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(advisory)


    def test_finish_line_allows_safe_quoted_validation_words(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    'bash "scripts/ci/all.sh"',
                    tool_use_id="safe-quoted-word",
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_preserves_shell_syntax_word_provenance(self) -> None:
        cases = {
            "conditional": (
                "'if' bash scripts/ci/all.sh; 'then' true; 'fi'",
                "if bash scripts/ci/all.sh; then true; fi",
                False,
            ),
            "time": (
                "'time' bash scripts/ci/all.sh",
                "time bash scripts/ci/all.sh",
                True,
            ),
            "assignment": (
                "'MODE=release' bash scripts/ci/all.sh",
                "MODE=release bash scripts/ci/all.sh",
                True,
            ),
        }
        for name, (declared, actual, matched) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                repo = self._init_contract_repo(tmp, (declared,))
                base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
                code, advisory, stderr = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", actual, tool_use_id=f"syntax-word-{name}"
                    ),
                    cwd=repo,
                    env=base_env,
                )
                self.assertEqual(code, 0, stderr)
                if matched:
                    self.assert_unprovable_validation_advisory(advisory)
                else:
                    self.assertIsNone(advisory)


    def test_finish_line_quoted_append_assignment_cannot_credit_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, ("FOO+=bar bash scripts/ci/all.sh",)
            )
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\ntouch validation-ran\nexit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            impostor = bin_dir / "FOO+=bar"
            impostor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            impostor.chmod(0o755)
            path = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "PATH": path,
            }
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, advisory, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "'FOO+=bar' bash scripts/ci/all.sh",
                    tool_use_id="quoted-append-assignment",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assert_unprovable_validation_advisory(advisory)
            self.assertFalse((repo / "validation-ran").exists())
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_does_not_authorize_non_validation_preamble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            code, advisory, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    'rm -rf "$HOME/example" && bash scripts/ci/all.sh',
                    tool_use_id="sensitive-preamble",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            message = self.assert_unprovable_validation_advisory(advisory)
            self.assertNotIn("$HOME/example", message)
            self.assertNotIn("rm -rf", message)


    def test_finish_line_risky_declared_control_flow_must_match_positionally(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("true; bash scripts/ci/all.sh",))
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            code, advisory, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "true && bash scripts/ci/all.sh; true",
                    tool_use_id="relocated-semicolon",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(advisory)


    def test_finish_line_credits_success_preserving_validation_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, ("bash scripts/ci/all.sh", "bash tests/hooks/run.sh")
            )
            for relative in ("scripts/ci/all.sh", "tests/hooks/run.sh"):
                script = repo / relative
                script.parent.mkdir(parents=True, exist_ok=True)
                script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh && bash tests/hooks/run.sh",
                    tool_use_id="safe-chain",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            hook_output = rewrite["hookSpecificOutput"]
            assert isinstance(hook_output, dict)
            updated_input = hook_output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_separate_validation_commands_preserve_edit_time(
        self,
    ) -> None:
        commands = ("bash scripts/ci/all.sh", "bash tests/hooks/run.sh")
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, commands)
            for relative in ("scripts/ci/all.sh", "tests/hooks/run.sh"):
                script = repo / relative
                script.parent.mkdir(parents=True, exist_ok=True)
                script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            for command in commands:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse",
                        command,
                        tool_use_id=f"separate-{hashlib.sha256(command.encode()).hexdigest()[:8]}",
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                completed = subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_disjoint_success_keeps_external_failure(self) -> None:
        commands = ("bash scripts/a.sh", "bash scripts/b.sh")
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, commands)
            script_a = repo / "scripts" / "a.sh"
            script_b = repo / "scripts" / "b.sh"
            script_a.parent.mkdir(parents=True)
            for script in (script_a, script_b):
                script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            def execute(command: str, identity: str) -> int:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", command, tool_use_id=identity
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                completed = subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return completed.returncode

            self.assertEqual(execute(commands[0], "a-success"), 0)
            script_a.write_text(
                "#!/usr/bin/env bash\n"
                "rm -f .cache/agent-validation/*.pending.*.json\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            self.assertEqual(execute(commands[0], "a-external-failure"), 17)
            marker_dir = repo / ".cache" / "agent-validation"
            marker_dir.chmod(0o755)
            self.assertEqual(execute(commands[1], "b-success"), 0)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_separate_successes_clear_combined_tombstone(self) -> None:
        commands = ("bash scripts/a.sh", "bash scripts/b.sh")
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, commands)
            script_a = repo / "scripts" / "a.sh"
            script_b = repo / "scripts" / "b.sh"
            script_a.parent.mkdir(parents=True)
            script_a.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script_b.write_text(
                "#!/usr/bin/env bash\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 0\n",
                encoding="utf-8",
            )
            script_a.chmod(0o755)
            script_b.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            def execute(command: str, identity: str) -> int:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", command, tool_use_id=identity
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                return subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            combined = f"{commands[0]} && {commands[1]}"
            self.assertEqual(execute(combined, "combined-external-success"), 0)
            (repo / ".cache" / "agent-validation").chmod(0o755)
            script_b.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            self.assertEqual(execute(commands[0], "separate-a"), 0)
            self.assertEqual(execute(commands[1], "separate-b"), 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_prunes_stale_pending_before_new_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            marker_dir = repo / ".cache" / "agent-validation"
            stale = marker_dir / "project-dev.pending.0000000000000000.json"
            stale.write_text("{}\n", encoding="utf-8")
            old = time.time() - (25 * 60 * 60)
            os.utime(stale, (old, old))

            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="prune-attempt",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(rewrite)
            self.assertFalse(stale.exists())
            self.assertEqual(len(list(marker_dir.glob("*.pending.*.json"))), 1)


    def test_finish_line_pending_record_cap_includes_the_new_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            marker_dir = repo / ".cache" / "agent-validation"
            for index in range(128):
                (marker_dir / f"project-dev.pending.{index:016x}.json").write_text(
                    "{}\n", encoding="utf-8"
                )
            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="cap-boundary",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(rewrite)
            self.assertLessEqual(
                len(list(marker_dir.glob("*.pending.*.json"))), 128
            )


    def test_finish_line_compacts_superseded_external_tombstones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(str(repo_path))
            state_home = root / "runtime-state"
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_STATE_HOME": str(state_home),
            }
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            marker_dir = repo / ".cache" / "agent-validation"
            dirty = marker_dir / "project-dev.dirty"
            ran = marker_dir / "project-dev.cmd0.ran"
            failed = marker_dir / "project-dev.cmd0.failed.json"
            repo_key = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()
            tombstone_dir = state_home / "validation-outcomes" / repo_key
            tombstone_dir.mkdir(parents=True, exist_ok=True)
            started = time.time_ns() - 10_000
            contract_key = hashlib.sha256(
                b".cache/agent-validation/project-dev.ok"
            ).hexdigest()
            target_key = hashlib.sha256(
                f"{contract_key}\0project-dev\0{0}\0bash scripts/ci/all.sh".encode()
            ).hexdigest()
            for index in range(128):
                body = {
                    "schema_version": "agent-runtime-validation.tombstone.v1",
                    "repo_root": str(repo.resolve()),
                    "product": "shared",
                    "contract_key": contract_key,
                    "pending": str(
                        marker_dir / f"project-dev.pending.{index:016x}.json"
                    ),
                    "dirty": str(dirty),
                    "attempt_started_ns": started + index,
                    "commands": [
                        {
                            "target_key": target_key,
                            "ran": str(ran),
                            "failed": str(failed),
                        }
                    ],
                    "status": "pending",
                    "exit_code": None,
                    "event": "",
                }
                (tombstone_dir / f"attempt-{index:032x}.json").write_text(
                    json.dumps(body) + "\n", encoding="utf-8"
                )

            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="tombstone-cap",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertIsNotNone(rewrite)
            self.assertEqual(len(list(tombstone_dir.glob("attempt-*.json"))), 1)


    def test_finish_line_failed_multi_contract_registration_keeps_prior_signal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(str(repo_path))
            (repo / "VALIDATION.toml").write_text(
                "[[validation]]\n"
                'context = "project-dev"\n'
                'commands = ["bash scripts/ci/all.sh"]\n'
                'marker = ".cache/a/project-dev.ok"\n\n'
                "[[validation]]\n"
                'context = "project-dev-secondary"\n'
                'commands = ["bash scripts/ci/all.sh"]\n'
                'marker = ".cache/b/project-dev.ok"\n',
                encoding="utf-8",
            )
            state_home = root / "runtime-state"
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_STATE_HOME": str(state_home),
            }
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            marker_a = repo / ".cache" / "a"
            dirty_a = marker_a / "project-dev.dirty"
            terminal_a = marker_a / ".terminal-shared"
            terminal_a.touch()
            terminal_mtime = terminal_a.stat().st_mtime_ns
            repo_key = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()
            tombstone_dir = state_home / "validation-outcomes" / repo_key
            tombstone_dir.mkdir(parents=True, exist_ok=True)
            old = tombstone_dir / f"attempt-{'a' * 32}.json"
            contract_key = hashlib.sha256(b".cache/a/project-dev.ok").hexdigest()
            target_key = hashlib.sha256(
                f"{contract_key}\0project-dev\0{0}\0bash scripts/ci/all.sh".encode()
            ).hexdigest()
            old.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-runtime-validation.tombstone.v1",
                        "repo_root": str(repo.resolve()),
                        "product": "shared",
                        "contract_key": contract_key,
                        "pending": str(
                            marker_a / f"project-dev.pending.{'a' * 16}.json"
                        ),
                        "dirty": str(dirty_a),
                        "attempt_started_ns": time.time_ns() - 10_000,
                        "commands": [
                            {
                                "target_key": target_key,
                                "ran": str(marker_a / "project-dev.cmd0.ran"),
                                "failed": str(
                                    marker_a / "project-dev.cmd0.failed.json"
                                ),
                            }
                        ],
                        "status": "pending",
                        "exit_code": None,
                        "event": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            marker_b = repo / ".cache" / "b"
            bad_lock = marker_b / ".agent-runtime-validation.lock"
            bad_lock.unlink()
            bad_lock.mkdir()
            before_tombstones = {
                path.name for path in tombstone_dir.glob("attempt-*.json")
            }
            before_pending = {
                path.name for path in marker_a.glob("*.pending.*.json")
            }

            _, decision, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="partial-registration",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assert_blocked(decision, "could not register")
            self.assertTrue(old.is_file())
            self.assertEqual(
                {path.name for path in tombstone_dir.glob("attempt-*.json")},
                before_tombstones,
            )
            self.assertEqual(
                {path.name for path in marker_a.glob("*.pending.*.json")},
                before_pending,
            )
            self.assertTrue(terminal_a.is_file())
            self.assertEqual(terminal_a.stat().st_mtime_ns, terminal_mtime)


    def test_finish_line_multi_contract_edit_registration_is_transactional(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            command = "bash scripts/ci/all.sh"
            (repo / "VALIDATION.toml").write_text(
                "[[validation]]\n"
                'context = "project-dev-a"\n'
                f'commands = ["{command}"]\n'
                'marker = ".cache/a/project-dev.ok"\n\n'
                "[[validation]]\n"
                'context = "project-dev-b"\n'
                f'commands = ["{command}"]\n'
                'marker = ".cache/b/project-dev.ok"\n\n'
                "[[validation]]\n"
                'context = "project-dev-c"\n'
                f'commands = ["{command}"]\n'
                'marker = ".cache/c/project-dev.ok"\n',
                encoding="utf-8",
            )
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            _, first_edit, _ = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            self.assert_allowed(first_edit)
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", command, tool_use_id="both-contracts-pass"
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)

            dirty_a = repo / ".cache" / "a" / "project-dev.dirty"
            dirty_b = repo / ".cache" / "b" / "project-dev.dirty"
            dirty_c = repo / ".cache" / "c" / "project-dev.dirty"

            def marker_snapshot(path: Path) -> tuple[bytes, int, int]:
                metadata = path.stat(follow_symlinks=False)
                return path.read_bytes(), metadata.st_mode, metadata.st_mtime_ns

            before_a = marker_snapshot(dirty_a)
            before_c = marker_snapshot(dirty_c)
            dirty_b.unlink()
            dirty_c.parent.chmod(0o555)
            _, blocked_edit, _ = run_hook(
                "finish-line-record.py",
                write_payload("src/next.rs", "fn next() {}\n"),
                cwd=repo,
                env=base_env,
            )
            self.assert_blocked(
                blocked_edit, "could not register validation dirty state"
            )
            dirty_c.parent.chmod(0o755)
            self.assertEqual(marker_snapshot(dirty_a), before_a)
            self.assertFalse(dirty_b.exists())
            self.assertEqual(marker_snapshot(dirty_c), before_c)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)

            _, retried_edit, _ = run_hook(
                "finish-line-record.py",
                write_payload("src/next.rs", "fn next() {}\n"),
                cwd=repo,
                env=base_env,
            )
            self.assert_allowed(retried_edit)
            self.assertGreater(marker_snapshot(dirty_a)[2], before_a[2])
            self.assertTrue(dirty_b.is_file())
            self.assertGreater(marker_snapshot(dirty_c)[2], before_c[2])
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "project-dev-a")
            self.assert_blocked(decision, "project-dev-b")
            self.assert_blocked(decision, "project-dev-c")


    def test_finish_line_edit_rollback_preserves_concurrent_generation(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "finish_line_record_transaction",
            HOOK_DIR / "finish-line-record.py",
        )
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for initial in ("regular", "missing"):
            with self.subTest(initial=initial), tempfile.TemporaryDirectory() as tmp:
                marker = Path(tmp) / "project-dev.dirty"
                if initial == "regular":
                    marker.write_text("baseline\n", encoding="utf-8")
                snapshot = module.dirty_marker_snapshot(str(marker))
                self.assertIsNotNone(snapshot)
                assert snapshot is not None
                transaction_generation = time.time_ns()
                self.assertTrue(
                    module.write_empty_marker(
                        str(marker), mtime_ns=transaction_generation
                    )
                )
                concurrent_generation = transaction_generation + 1_000
                self.assertTrue(
                    module.write_empty_marker(
                        str(marker), mtime_ns=concurrent_generation
                    )
                )
                self.assertTrue(
                    module.restore_dirty_marker(
                        str(marker),
                        snapshot,
                        expected_generation_ns=transaction_generation,
                    )
                )
                self.assertEqual(
                    marker.stat(follow_symlinks=False).st_mtime_ns,
                    concurrent_generation,
                )


    def test_finish_line_compacts_repeated_persistence_failure_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            marker_dir = repo / ".cache" / "agent-validation"
            ran = marker_dir / "project-dev.cmd0.ran"
            failed = marker_dir / "project-dev.cmd0.failed.json"
            started = time.time_ns()
            for index in range(140):
                attempt_started_ns = started + index
                pending = marker_dir / f"project-dev.pending.{index:016x}.json"
                pending.write_text(
                    json.dumps(
                        {
                            "schema_version": "agent-runtime-validation.pending.v1",
                            "attempt_started_ns": attempt_started_ns,
                            "commands": [
                                {"ran": str(ran), "failed": str(failed)}
                            ],
                            "outcome_persistence_failed": True,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                os.utime(
                    pending,
                    ns=(attempt_started_ns, attempt_started_ns),
                )

            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="protected-cap-boundary",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(rewrite)
            self.assertLessEqual(
                len(list(marker_dir.glob("*.pending.*.json"))),
                2,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_rewrite_preserves_input_and_directly_consumes_pending(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            code, rewrite, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="direct-recorder",
                    timeout_ms=4321,
                    description="pinned validation",
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertEqual(code, 0, stderr)
            assert rewrite is not None
            hook_output = rewrite.get("hookSpecificOutput")
            assert isinstance(hook_output, dict)
            updated_input = hook_output.get("updatedInput")
            assert isinstance(updated_input, dict)
            self.assertEqual(updated_input.get("timeout_ms"), 4321)
            self.assertEqual(updated_input.get("description"), "pinned validation")
            wrapped = str(updated_input.get("command", ""))
            self.assertRegex(
                wrapped,
                r"__agent_runtime_validation_report_[0-9a-f]{16}",
            )
            marker_dir = repo / ".cache" / "agent-validation"
            pending = list(marker_dir.glob("*.pending.*.json"))
            self.assertEqual(len(pending), 1)

            completed = subprocess.run(
                ["bash", "-lc", wrapped],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(pending[0].exists())
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_stale_direct_completion_cannot_overwrite_newer_outcome(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            _, first_rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="older-attempt"
                ),
                cwd=repo,
                env=base_env,
            )
            assert first_rewrite is not None
            first_output = first_rewrite["hookSpecificOutput"]
            assert isinstance(first_output, dict)
            first_input = first_output["updatedInput"]
            assert isinstance(first_input, dict)
            first_wrapped = str(first_input["command"])

            time.sleep(0.002)
            _, second_rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="newer-success"
                ),
                cwd=repo,
                env=base_env,
            )
            assert second_rewrite is not None
            second_output = second_rewrite["hookSpecificOutput"]
            assert isinstance(second_output, dict)
            second_input = second_output["updatedInput"]
            assert isinstance(second_input, dict)
            second_wrapped = str(second_input["command"])
            passed = subprocess.run(
                ["bash", "-lc", second_wrapped],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(passed.returncode, 0)

            script.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            failed = subprocess.run(
                ["bash", "-lc", first_wrapped],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_allowed(decision)


    def test_finish_line_stale_success_cannot_overwrite_newer_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            wrappers: list[str] = []
            for identity in ("older-success", "newer-failure"):
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse",
                        "bash scripts/ci/all.sh",
                        tool_use_id=identity,
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                wrappers.append(str(updated_input["command"]))
                time.sleep(0.002)

            script.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            newer = subprocess.run(
                ["bash", "-lc", wrappers[1]],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(newer.returncode, 17)

            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            older = subprocess.run(
                ["bash", "-lc", wrappers[0]],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(older.returncode, 0)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_missing_tool_id_keeps_attempts_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )

            wrappers: list[str] = []
            for _ in range(2):
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse",
                        "bash scripts/ci/all.sh",
                        tool_use_id="",
                    ),
                    cwd=repo,
                    env=base_env,
                )
                assert rewrite is not None
                hook_output = rewrite["hookSpecificOutput"]
                assert isinstance(hook_output, dict)
                updated_input = hook_output["updatedInput"]
                assert isinstance(updated_input, dict)
                wrappers.append(str(updated_input["command"]))
                time.sleep(0.002)

            older = subprocess.run(
                ["bash", "-lc", wrappers[0]],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(older.returncode, 0)
            script.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            newer = subprocess.run(
                ["bash", "-lc", wrappers[1]],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(newer.returncode, 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_outcome_persistence_failure_keeps_pending_blocker(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, passed_rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="prior-pass"
                ),
                cwd=repo,
                env=base_env,
            )
            assert passed_rewrite is not None
            passed_output = passed_rewrite["hookSpecificOutput"]
            assert isinstance(passed_output, dict)
            passed_input = passed_output["updatedInput"]
            assert isinstance(passed_input, dict)
            passed = subprocess.run(
                ["bash", "-lc", str(passed_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(passed.returncode, 0)

            script.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            time.sleep(0.002)
            _, failed_rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="failed-write"
                ),
                cwd=repo,
                env=base_env,
            )
            assert failed_rewrite is not None
            failed_output = failed_rewrite["hookSpecificOutput"]
            assert isinstance(failed_output, dict)
            failed_input = failed_output["updatedInput"]
            assert isinstance(failed_input, dict)
            failed_marker = (
                repo
                / ".cache"
                / "agent-validation"
                / "project-dev.cmd0.failed.json"
            )
            failed_marker.mkdir()
            failed = subprocess.run(
                ["bash", "-lc", str(failed_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 17)
            pending = list((repo / ".cache").rglob("*.pending.*.json"))
            self.assertEqual(len(pending), 1)
            pending_body = json.loads(pending[0].read_text(encoding="utf-8"))
            self.assertTrue(pending_body.get("outcome_persistence_failed"))
            old = time.time() - (25 * 60 * 60)
            os.utime(pending[0], (old, old))
            run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="prune-probe"
                ),
                cwd=repo,
                env=base_env,
            )
            self.assertTrue(pending[0].exists())
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_ran_marker_directory_cannot_supersede_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/ci/all.sh",
                    tool_use_id="ran-directory-collision",
                ),
                cwd=repo,
                env=base_env,
            )
            assert rewrite is not None
            hook_output = rewrite["hookSpecificOutput"]
            assert isinstance(hook_output, dict)
            updated_input = hook_output["updatedInput"]
            assert isinstance(updated_input, dict)
            ran_marker = (
                repo / ".cache" / "agent-validation" / "project-dev.cmd0.ran"
            )
            ran_marker.mkdir()

            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_failure_marker_symlink_cannot_mask_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            script = repo / "scripts" / "ci" / "all.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            _, passed_rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="prior-pass"
                ),
                cwd=repo,
                env=base_env,
            )
            assert passed_rewrite is not None
            passed_output = passed_rewrite["hookSpecificOutput"]
            assert isinstance(passed_output, dict)
            passed_input = passed_output["updatedInput"]
            assert isinstance(passed_input, dict)
            passed = subprocess.run(
                ["bash", "-lc", str(passed_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(passed.returncode, 0)

            marker_dir = repo / ".cache" / "agent-validation"
            symlink_target = marker_dir / "future-outcome"
            symlink_target.write_text("future\n", encoding="utf-8")
            future = time.time() + 3600
            os.utime(symlink_target, (future, future))
            failed_marker = marker_dir / "project-dev.cmd0.failed.json"
            failed_marker.symlink_to(symlink_target.name)

            script.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            _, failed_rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="later-fail"
                ),
                cwd=repo,
                env=base_env,
            )
            assert failed_rewrite is not None
            failed_output = failed_rewrite["hookSpecificOutput"]
            assert isinstance(failed_output, dict)
            failed_input = failed_output["updatedInput"]
            assert isinstance(failed_input, dict)
            failed = subprocess.run(
                ["bash", "-lc", str(failed_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 17)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "failed with exit code 17")


    def test_finish_line_rejects_validation_markers_outside_repository(self) -> None:
        for escape in (
            "traversal",
            "symlink",
            "symlink-parent",
            "root-dot",
            "root-normalized",
        ):
            with self.subTest(escape=escape), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo_path = root / "repo"
                repo_path.mkdir()
                victim = root / "victim"
                victim.mkdir()
                if escape == "traversal":
                    marker = "../victim/agent-validation/project-dev.ok"
                elif escape == "symlink":
                    external = victim / "linked-cache"
                    external.mkdir()
                    (repo_path / ".linked-cache").symlink_to(
                        external,
                        target_is_directory=True,
                    )
                    marker = ".linked-cache/agent-validation/project-dev.ok"
                elif escape == "symlink-parent":
                    external = victim / "nested"
                    external.mkdir()
                    (repo_path / ".linked-parent").symlink_to(
                        external,
                        target_is_directory=True,
                    )
                    marker = ".linked-parent/../agent-validation/project-dev.ok"
                elif escape == "root-dot":
                    marker = "."
                else:
                    marker = "nested/.."
                repo = self._init_contract_repo(str(repo_path), marker=marker)
                script = repo / "scripts" / "ci" / "all.sh"
                script.parent.mkdir(parents=True)
                script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
                base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
                before = self._snapshot_outside_repo(root, repo)
                _, edit_decision, _ = run_hook(
                    "finish-line-record.py",
                    write_payload("src/lib.rs", "fn main() {}\n"),
                    cwd=repo,
                    env=base_env,
                )
                self.assert_blocked(
                    edit_decision, "could not register validation dirty state"
                )
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse",
                        "bash scripts/ci/all.sh",
                        tool_use_id=f"marker-{escape}",
                    ),
                    cwd=repo,
                    env=base_env,
                )
                self.assertIsNone(rewrite)
                self.assertEqual(
                    self._snapshot_outside_repo(root, repo),
                    before,
                    "validation state escaped or changed an external artifact",
                )
                _, decision, _ = run_hook(
                    "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
                )
                self.assert_blocked(decision, "unsafe validation marker")


    def test_finish_line_derived_marker_symlinks_fail_closed(self) -> None:

        with self.subTest(marker="session-directory"), tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(str(repo_path))
            marker_dir = repo / ".cache" / "agent-validation"
            marker_dir.mkdir(parents=True)
            victim = root / "victim"
            victim.mkdir()
            session_id = "symlinked-session-directory"
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            (marker_dir / f"session-{session_key}").symlink_to(
                victim, target_is_directory=True
            )
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            edit = write_payload("src/lib.rs", "fn main() {}\n")
            edit["session_id"] = session_id

            _, decision, _ = run_hook(
                "finish-line-record.py", edit, cwd=repo, env=base_env
            )
            self.assert_blocked(
                decision, "could not register validation dirty state"
            )
            self.assertEqual(list(victim.iterdir()), [])

        with self.subTest(marker="dirty"), tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            marker_dir = repo / ".cache" / "agent-validation"
            marker_dir.mkdir(parents=True)
            dirty = marker_dir / "project-dev.dirty"
            ran = marker_dir / "project-dev.cmd0.ran"
            dirty.symlink_to(ran.name)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            self.assertTrue(dirty.is_file())
            self.assertFalse(dirty.is_symlink())
            self.assertFalse(ran.exists())
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")

            dirty.unlink()
            dirty.symlink_to(ran.name)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "unsafe validation state marker")

        with self.subTest(marker="routing"), tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            victim = root / "victim"
            victim.mkdir()
            target = victim / "routing-target"
            target.write_text("unchanged\n", encoding="utf-8")
            repo = self._init_contract_repo(str(repo_path))
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            reviewed = (
                repo
                / ".cache"
                / "agent-validation"
                / "project-dev.routing-reviewed"
            )
            reviewed.symlink_to(target)
            before = self._snapshot_outside_repo(root, repo)
            waiver_env = {
                **base_env,
                "AGENT_RUNTIME_VALIDATION_WAIVER": "reviewed routing decision",
            }
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=waiver_env
            )
            self.assert_blocked(decision, "routing review required")
            self.assertEqual(self._snapshot_outside_repo(root, repo), before)
            self.assertTrue(reviewed.is_file())
            self.assertFalse(reviewed.is_symlink())
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=waiver_env
            )
            self.assert_allowed(decision)

        with self.subTest(marker="lock"), tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            victim = root / "victim"
            victim.mkdir()
            target = victim / "lock-target"
            target.write_text("unchanged\n", encoding="utf-8")
            repo = self._init_contract_repo(str(repo_path))
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            lock = (
                repo
                / ".cache"
                / "agent-validation"
                / ".agent-runtime-validation.lock"
            )
            lock.unlink()
            lock.symlink_to(target)
            before = self._snapshot_outside_repo(root, repo)
            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse", "bash scripts/ci/all.sh", tool_use_id="lock-symlink"
                ),
                cwd=repo,
                env=base_env,
            )
            self.assert_blocked(rewrite, "could not register")
            self.assertEqual(self._snapshot_outside_repo(root, repo), before)
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=base_env
            )
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_waiver_fails_closed_when_review_marker_cannot_persist(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=base_env,
            )
            collision = (
                repo
                / ".cache"
                / "agent-validation"
                / "project-dev.routing-reviewed"
            )
            collision.mkdir(parents=True)
            waiver_env = {
                **base_env,
                "AGENT_RUNTIME_VALIDATION_WAIVER": "bounded infrastructure failure",
            }
            for _ in range(2):
                _, decision, _ = run_hook(
                    "stop-finish-line-gate.py", {}, cwd=repo, env=waiver_env
                )
                self.assert_blocked(decision, "could not persist")


    def test_finish_line_record_requires_real_validation_command_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, ("bash scripts/ci/all.sh", "bash tests/hooks/run.sh")
            )
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            fake_command = 'printf %s "bash scripts/ci/all.sh && bash tests/hooks/run.sh"'
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", fake_command),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_matches_multiline_command_with_cd_preamble(self) -> None:
        # Regression: agents routinely run the declared validation as a
        # multi-line Bash command with a `cd` preamble, e.g.
        #     cd /repo
        #     bash scripts/ci/all.sh && bash tests/hooks/run.sh
        # An unquoted newline must act as a command separator; otherwise the
        # validation command on the second physical line is glued onto `cd` and
        # never recognized. Recognition alone earns no credit: this aggregate
        # shape cannot prove its outcome, so the recorder explains that instead
        # of silently ignoring the run.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(
                tmp, ("bash scripts/ci/all.sh", "bash tests/hooks/run.sh")
            )
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            multiline = (
                "cd /repo\n"
                "bash scripts/ci/all.sh && bash tests/hooks/run.sh\n"
                'echo "done=$?"'
            )
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", multiline),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_ignores_validation_text_inside_quotes(self) -> None:
        # Guard against a false positive: a multi-line command whose only
        # mention of the validation command is inside a quoted string (here a
        # newline-bearing double-quoted argument) must NOT satisfy the gate.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            quoted = 'cd /repo\nprintf "%s\nbash scripts/ci/all.sh\n" "header"'
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", quoted),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_ignores_validation_inside_heredoc_body(self) -> None:
        # Guard against a false positive: a command whose only mention of the
        # validation command is inside a HERE-DOC body (data fed to another
        # command such as `cat`, never executed by the shell) must NOT satisfy
        # the gate (agent-runtime-kit#351).
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            heredoc = "cat > ci.sh <<'EOF'\nbash scripts/ci/all.sh\nEOF"
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", heredoc),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_recognizes_validation_after_heredoc(self) -> None:
        # The here-doc stripping must remove only the body: a real validation
        # run AFTER the here-doc closes is still recognized (agent-runtime-kit#351).
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            payload = "cat > note.txt <<'EOF'\nsome notes\nEOF\nbash scripts/ci/all.sh"
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", payload),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_recognizes_continued_heredoc_opener(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            payload = "cat <<EOF && \\\nbash scripts/ci/all.sh\nnotes\nEOF"
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", payload),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_recognizes_validation_inside_shell_heredoc(self) -> None:
        commands = (
            "bash <<'EOF'\nbash scripts/ci/all.sh\nEOF",
            "bash -s positional <<'EOF'\nbash scripts/ci/all.sh\nEOF",
        )
        for payload in commands:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
                    env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

                    code, _, stderr = run_hook(
                        "finish-line-record.py",
                        write_payload("src/lib.rs", "fn main() {}\n"),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)

                    code, recorded, stderr = run_hook(
                        "finish-line-record.py",
                        command_event_payload("PreToolUse", payload),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_unprovable_validation_advisory(recorded)

                    code, decision, stderr = run_hook(
                        "stop-finish-line-gate.py", {}, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_ignores_shell_heredoc_stdin_not_used_as_script(self) -> None:
        commands = (
            "bash -lc 'true' <<'EOF'\nbash scripts/ci/all.sh\nEOF",
            "bash ./script.sh <<'EOF'\nbash scripts/ci/all.sh\nEOF",
        )
        for payload in commands:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
                    env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

                    code, _, stderr = run_hook(
                        "finish-line-record.py",
                        write_payload("src/lib.rs", "fn main() {}\n"),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)

                    code, recorded, stderr = run_hook(
                        "finish-line-record.py",
                        command_event_payload("PreToolUse", payload),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(recorded)

                    code, decision, stderr = run_hook(
                        "stop-finish-line-gate.py", {}, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_recognizes_validation_after_commented_heredoc_operator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            payload = "# <<EOF\nbash scripts/ci/all.sh"
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", payload),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_record_recognizes_validation_after_ansi_c_quoted_heredoc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp, ("bash scripts/ci/all.sh",))
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            payload = "cat <<$'EOF'\nnotes\nEOF\nbash scripts/ci/all.sh"
            code, recorded, stderr = run_hook(
                "finish-line-record.py",
                command_event_payload("PreToolUse", payload),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_unprovable_validation_advisory(recorded)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")


    def test_finish_line_gate_enforces_every_declared_validation_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            with (repo / "VALIDATION.toml").open("a", encoding="utf-8") as handle:
                handle.write(
                    '\n[[validation]]\ncontext = "task-tools"\n'
                    'commands = ["bash scripts/task-tools.sh"]\n'
                    'marker = ".cache/agent-validation/task-tools.ok"\n'
                )
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            self._run_declared_validation(repo, "bash scripts/ci/all.sh", env=env)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/task-tools.sh")

            self._run_declared_validation(repo, "bash scripts/task-tools.sh", env=env)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_finish_line_reads_validation_toml_without_agent_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            self.assertFalse((repo / "AGENT_DOCS.toml").exists())
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            log_path = repo / "agent-docs.args"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> {shlex.quote(str(log_path))}
exit 99
""",
            )
            env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "scripts/ci/all.sh")
            self.assertFalse(log_path.exists(), "hooks must not invoke agent-docs")

            self._run_declared_validation(repo, "bash scripts/ci/all.sh", env=env)
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

    def test_finish_line_scopes_contracts_by_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            home = repo / "home"
            home.mkdir()
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\nproduct = "codex"\n'
                'commands = ["bash codex.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n'
                '\n[[validation]]\ncontext = "project-dev"\nproducts = ["claude"]\n'
                'commands = ["bash claude.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n',
                encoding="utf-8",
            )
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "HOME": str(home),
            }

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PRODUCT": "codex"},
            )
            self.assertEqual(code, 0, stderr)

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PRODUCT": "codex"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "codex.sh")

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PRODUCT": "claude"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "claude.sh")


    def test_finish_line_command_marker_does_not_cross_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            home = repo / "home"
            home.mkdir()
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\nproduct = "codex"\n'
                'commands = ["bash codex.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n'
                '\n[[validation]]\ncontext = "project-dev"\nproducts = ["claude"]\n'
                'commands = ["bash claude.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n',
                encoding="utf-8",
            )
            base_env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "HOME": str(home),
            }

            code, _, stderr = run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PRODUCT": "codex"},
            )
            self.assertEqual(code, 0, stderr)

            self._run_declared_validation(
                repo, "bash codex.sh", env={**base_env, "AGENT_RUNTIME_PRODUCT": "codex"}
            )

            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PRODUCT": "claude"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "claude.sh")


    def test_finish_line_external_tombstones_are_product_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(
                str(repo_path), ("bash scripts/validate.sh",)
            )
            script = repo / "scripts" / "validate.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -rf .cache/agent-validation\n"
                "mkdir -p .cache/agent-validation\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            state_home = root / "runtime-state"

            def product_env(product: str) -> dict[str, str]:
                return {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_STATE_HOME": str(state_home),
                    "AGENT_RUNTIME_PRODUCT": product,
                }

            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=product_env("claude"),
            )

            def execute(product: str, identity: str) -> int:
                env = product_env(product)
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse",
                        "bash scripts/validate.sh",
                        tool_use_id=identity,
                    ),
                    cwd=repo,
                    env=env,
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                return subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            self.assertEqual(execute("claude", "claude-external-failure"), 17)
            _, codex_before_validation, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_blocked(codex_before_validation, "has not passed since")
            (repo / ".cache" / "agent-validation").chmod(0o755)
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            self.assertEqual(execute("codex", "codex-success"), 0)

            _, codex_decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_allowed(codex_decision)

            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -f .cache/agent-validation/project-dev.dirty\n"
                "rm -f .cache/agent-validation/project-dev.claude.pending.*.json\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            self.assertEqual(execute("claude", "claude-retry-same-edit"), 17)
            (repo / ".cache" / "agent-validation").chmod(0o755)
            _, codex_after_foreign_retry, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_allowed(codex_after_foreign_retry)
            _, claude_decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("claude"),
            )
            self.assert_blocked(claude_decision, "failed with exit code 17")

            run_hook(
                "finish-line-record.py",
                write_payload("src/next.rs", "fn next() {}\n"),
                cwd=repo,
                env=product_env("claude"),
            )
            _, codex_after_new_edit, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_blocked(codex_after_new_edit, "has not passed since")


    def test_finish_line_no_edit_tombstone_does_not_cross_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            repo = self._init_contract_repo(
                str(repo_path), ("bash scripts/validate.sh",)
            )
            script = repo / "scripts" / "validate.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -rf .cache/agent-validation\n"
                "mkdir -p .cache/agent-validation\n"
                "chmod 0555 .cache/agent-validation\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            state_home = root / "runtime-state"

            def product_env(product: str) -> dict[str, str]:
                return {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_STATE_HOME": str(state_home),
                    "AGENT_RUNTIME_PRODUCT": product,
                }

            _, rewrite, _ = run_hook(
                "finish-line-record.py",
                command_event_payload(
                    "PreToolUse",
                    "bash scripts/validate.sh",
                    tool_use_id="claude-no-edit-failure",
                ),
                cwd=repo,
                env=product_env("claude"),
            )
            assert rewrite is not None
            output = rewrite["hookSpecificOutput"]
            assert isinstance(output, dict)
            updated_input = output["updatedInput"]
            assert isinstance(updated_input, dict)
            completed = subprocess.run(
                ["bash", "-lc", str(updated_input["command"])],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 17)

            _, codex_decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_allowed(codex_decision)
            _, claude_decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("claude"),
            )
            self.assert_blocked(claude_decision, "failed with exit code 17")
            _, edit_decision, _ = run_hook(
                "finish-line-record.py",
                write_payload("src/next.rs", "fn next() {}\n"),
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_blocked(
                edit_decision, "could not register validation dirty state"
            )
            (repo / ".cache" / "agent-validation").chmod(0o755)


    def test_finish_line_foreign_marker_change_does_not_block_product(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_path = root / "repo"
            repo_path.mkdir()
            command = "bash scripts/validate.sh"
            old_marker = ".cache/a/project-dev.ok"
            new_marker = ".cache/b/project-dev.ok"
            repo = self._init_contract_repo(
                str(repo_path), (command,), marker=old_marker
            )
            script = repo / "scripts" / "validate.sh"
            script.parent.mkdir(parents=True)
            script.write_text(
                "#!/usr/bin/env bash\n"
                "rm -rf .cache/a\n"
                "mkdir -p .cache/a\n"
                "chmod 0555 .cache/a\n"
                "exit 17\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
            state_home = root / "runtime-state"

            def product_env(product: str) -> dict[str, str]:
                return {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_STATE_HOME": str(state_home),
                    "AGENT_RUNTIME_PRODUCT": product,
                }

            def execute(product: str, identity: str) -> int:
                _, rewrite, _ = run_hook(
                    "finish-line-record.py",
                    command_event_payload(
                        "PreToolUse", command, tool_use_id=identity
                    ),
                    cwd=repo,
                    env=product_env(product),
                )
                assert rewrite is not None
                output = rewrite["hookSpecificOutput"]
                assert isinstance(output, dict)
                updated_input = output["updatedInput"]
                assert isinstance(updated_input, dict)
                return subprocess.run(
                    ["bash", "-lc", str(updated_input["command"])],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=product_env("claude"),
            )
            self.assertEqual(execute("claude", "claude-old-marker-failure"), 17)
            (repo / ".cache" / "a").chmod(0o755)
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\n'
                f'commands = ["{command}"]\n'
                f'marker = "{new_marker}"\n',
                encoding="utf-8",
            )
            script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            self.assertEqual(execute("codex", "codex-new-marker-success"), 0)

            _, codex_decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("codex"),
            )
            self.assert_allowed(codex_decision)
            _, claude_decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env=product_env("claude"),
            )
            self.assert_blocked(claude_decision, "unmatched authoritative")


    def test_finish_line_subset_reader_matches_tomllib(self) -> None:
        # Hooks may run under a Python without tomllib; the fallback reader must
        # agree with tomllib on every validation shape it accepts.
        import tomllib

        import hook_common

        documents = [
            (REPO_ROOT / "AGENT_DOCS.toml").read_text(encoding="utf-8"),
            '[path_classes]\ntest = ["tests/**"]\n\n'
            '[[validation]] # trailing comment\n'
            "context = 'project-dev' # literal\n"
            'commands = [\n  "bash a.sh", # first\n  \'bash \\"b\\".sh\',\n'
            '  "echo \\"[x]\\" # not a comment",\n]\n'
            'product = ["codex", "claude"]\n'
            '\n[[document]]\ncontext = "x"\nnotes = """\nfree text\n"""\n',
        ]
        for text in documents:
            expected = tomllib.loads(text).get("validation", [])
            self.assertEqual(hook_common._validation_entries_subset(text), expected)
        with self.assertRaises(ValueError):
            hook_common._validation_entries_subset(
                '[[validation]]\ncontext = "x"\ncommands = """a"""\n'
            )

    def test_finish_line_invalid_declaration_fails_closed(self) -> None:
        # An existing but unreadable, malformed, or wrong-shaped contract must
        # not read as "no contract": that would let an unvalidated edit finish.
        invalid = (
            ("syntax", 'VALIDATION.toml', '[[validation]]\ncontext = "project-dev\n'),
            ("scalar-commands", 'VALIDATION.toml',
             '[[validation]]\ncontext = "project-dev"\ncommands = "bash ci.sh"\n'),
            ("unknown-key", 'VALIDATION.toml',
             '[[validation]]\ncontext = "project-dev"\ncommands = ["bash ci.sh"]\nphase = "edit"\n'),
            ("table-not-array", 'VALIDATION.toml',
             '[validation]\ncontext = "project-dev"\ncommands = ["bash ci.sh"]\n'),
            ("legacy-wrong-shape", 'AGENT_DOCS.toml',
             '[[validation]]\ncontext = "project-dev"\ncommands = []\n'),
        )
        fallback_root = tempfile.TemporaryDirectory()
        self.addCleanup(fallback_root.cleanup)
        fallback = Path(fallback_root.name)
        (fallback / "tomllib.py").write_text(
            'raise ImportError("forced fallback")\n', encoding="utf-8"
        )
        for reader, extra in (("tomllib", {}), ("subset", {"PYTHONPATH": f"{fallback}{os.pathsep}{HOOK_DIR}"})):
            for name, filename, text in invalid:
                with self.subTest(reader=reader, case=name), tempfile.TemporaryDirectory() as tmp:
                    repo = self._init_contract_repo(tmp)
                    (repo / "VALIDATION.toml").unlink()
                    (repo / filename).write_text(text, encoding="utf-8")
                    code, decision, stderr = run_hook(
                        "finish-line-record.py",
                        write_payload("src/lib.rs", "fn main() {}\n"),
                        cwd=repo,
                        env=extra,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, filename)
                    # The declaration itself stays editable so it can be fixed.
                    code, decision, stderr = run_hook(
                        "finish-line-record.py",
                        write_payload(filename, "# fixed\n"),
                        cwd=repo,
                        env=extra,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNone(decision)
                    code, decision, stderr = run_hook(
                        "stop-finish-line-gate.py", {}, cwd=repo, env=extra
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "invalid")

    def test_finish_line_invalid_primary_is_not_masked_by_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            (repo / "VALIDATION.toml").write_text("[[validation]\n", encoding="utf-8")
            (repo / "AGENT_DOCS.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\ncommands = ["bash legacy.sh"]\n',
                encoding="utf-8",
            )
            _, decision, _ = run_hook("stop-finish-line-gate.py", {}, cwd=repo)
            self.assert_blocked(decision, "VALIDATION.toml")

    def test_finish_line_subset_reader_rejects_what_tomllib_rejects(self) -> None:
        import tomllib

        import hook_common

        rejected = (
            '[[validation]]\ncontext = "a"\ncontext = "b"\ncommands = ["x"]\n',
            '[[validation]]\ncontext = "a"\ncommands = ["x" "y"]\n',
            '[[validation]]\ncontext = "a"\ncommands = ["x",, "y"]\n',
            '[[validation]]\ncontext = "a" "b"\ncommands = ["x"]\n',
            '[[validation]] junk\ncontext = "a"\ncommands = ["x"]\n',
        )
        for text in rejected:
            with self.subTest(text=text):
                with self.assertRaises(tomllib.TOMLDecodeError):
                    tomllib.loads(text)
                with self.assertRaises(ValueError):
                    hook_common._validation_entries_subset(text)

    def test_finish_line_reads_transitional_agent_docs_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            (repo / "VALIDATION.toml").unlink()
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\npath = "README.md"\n'
                '\n[[validation]]\ncontext = "project-dev"\nproduct = ["codex"]\n'
                'commands = ["bash legacy-codex.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n'
                '\n[[validation]]\ncontext = "task-tools"\nproduct = "hermes"\n'
                'commands = ["bash hermes-only.sh"]\n',
                encoding="utf-8",
            )
            env = {"AGENT_RUNTIME_PRODUCT": "codex"}

            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
                env=env,
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assert_blocked(decision, "legacy-codex.sh")
            assert decision is not None
            self.assertNotIn("hermes-only.sh", str(decision.get("reason", "")))

            # VALIDATION.toml owns a context once it declares it.
            (repo / "VALIDATION.toml").write_text(
                '[[validation]]\ncontext = "project-dev"\n'
                'commands = ["bash primary.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n',
                encoding="utf-8",
            )
            _, decision, _ = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assert_blocked(decision, "primary.sh")
            assert decision is not None
            self.assertNotIn("legacy-codex.sh", str(decision.get("reason", "")))

    def test_finish_line_gate_waiver_and_suppress_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            base_env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                {"tool_name": "Edit", "tool_input": {"file_path": "src/lib.rs"}},
                cwd=repo,
                env=base_env,
            )

            _, decision, _ = run_hook("stop-finish-line-gate.py", {}, cwd=repo, env=base_env)
            self.assert_blocked(decision, "validation")

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_VALIDATION_WAIVER": "deliberate skip"},
            )
            self.assert_blocked(decision, "routing review required")

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_VALIDATION_WAIVER": "deliberate skip"},
            )
            self.assert_allowed(decision)

            _, decision, _ = run_hook(
                "stop-finish-line-gate.py",
                {},
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_SUPPRESS_FINISH_GATE": "1"},
            )
            self.assert_allowed(decision)


    def test_finish_line_record_ignores_markdown_only_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._init_contract_repo(tmp)
            env = {"AGENT_RUNTIME_DOCS_HOME": str(repo)}
            run_hook(
                "finish-line-record.py",
                write_payload("docs/note.md", "# note\n"),
                cwd=repo,
                env=env,
            )
            code, decision, stderr = run_hook(
                "stop-finish-line-gate.py", {}, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_finish_line_gate_noops_without_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected_repo = repo.resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            run_hook(
                "finish-line-record.py",
                write_payload("src/lib.rs", "fn main() {}\n"),
                cwd=repo,
            )
            code, decision, stderr = run_hook("stop-finish-line-gate.py", {}, cwd=repo)
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_finish_line_outcome_hooks_registered_for_supported_products(self) -> None:
        for product in ("codex", "claude"):
            finish_line = inventory_rules(
                product=product,
                event="PreToolUse",
                handler="finish-line-record",
            )
            self.assertIn("Bash", inventory_tools(finish_line), product)
            for event in ("PostToolUse", "PostToolUseFailure"):
                coordination = inventory_rules(
                    product=product,
                    event=event,
                    capability="agent-session.coordination.v1",
                )
                self.assertTrue(coordination, f"{product}:{event}")

