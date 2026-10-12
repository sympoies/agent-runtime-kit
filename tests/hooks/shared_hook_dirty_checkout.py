"""Shared hook tests: dirty checkout."""
from __future__ import annotations

from shared_hook_helpers import (
    HOOK_DIR,
    HookTestCase,
    Path,
    hashlib,
    json,
    os,
    run_enforced_hook,
    shlex,
    tempfile,
)


class DirtyCheckoutTests(HookTestCase):

    def test_dirty_checkout_adoption_flag_off_is_silent_and_preserves_guard(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "flag-off-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "inspect this checkout",
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(advisory)
            self.assertFalse(state.exists())

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "flag-off-session", repo / "README.md"
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "unowned changes")
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_dirty_checkout_adoption_reports_typed_snapshot_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            fake_bin = root / "bin"
            fake_bin.mkdir(mode=0o700)
            fake_git_cli = fake_bin / "git-cli"
            fake_git_cli.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' "
                "'{\"schema_version\":\"cli.git-cli.worktree.dirty-snapshot.v1\","
                "\"ok\":false,\"error\":{\"code\":"
                "\"dirty-checkout-resource-unavailable\",\"message\":"
                "\"dirty snapshot worker executable path is not trusted; "
                "PRIVATE-SNAPSHOT-DETAIL\"}}'\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_git_cli.chmod(0o700)
            self._init_checkout_lease_repo(repo)
            private_prompt = "PRIVATE-PROMPT-snapshot-5319"
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
                "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
            }

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "snapshot-failure-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": private_prompt,
                },
                cwd=repo,
                env=env,
            )

            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            hook_output = advisory.get("hookSpecificOutput")
            self.assertIsInstance(hook_output, dict)
            assert isinstance(hook_output, dict)
            context = str(hook_output.get("additionalContext", ""))
            self.assertIn(
                "dirty-checkout-resource-unavailable/worker-path-untrusted",
                context,
            )
            self.assertIn("remain read-only", context.lower())
            self.assertIn("git-cli worktree dirty-snapshot --format=json", context)
            self.assertIn("git-cli worktree add", context)
            rendered = json.dumps(advisory, sort_keys=True)
            self.assertNotIn(private_prompt, rendered)
            self.assertNotIn("PRIVATE-SNAPSHOT-DETAIL", rendered)
            self.assertFalse(state.exists())


    def test_dirty_checkout_adoption_flag_on_emits_one_private_challenge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            private_name = "customer-alpine-secret.txt"
            private_content = "PRIVATE-CONTENT-summit-7421"
            private_prompt = "PRIVATE-PROMPT-river-9853"
            (repo / private_name).write_text(private_content, encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            self._dirty_snapshot_capability_or_skip(repo)

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "advisory-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": private_prompt,
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            self.assertNotIn("decision", advisory)
            hook_output = advisory.get("hookSpecificOutput")
            self.assertIsInstance(hook_output, dict)
            assert isinstance(hook_output, dict)
            self.assertEqual(
                hook_output.get("hookEventName"), "UserPromptSubmit"
            )
            context = str(hook_output.get("additionalContext", ""))
            self.assertIn("read-only", context.lower())
            self.assertRegex(
                context,
                r"(?:git-cli worktree adopt-dirty --challenge \S+|\S+ adopt-dirty)"
                r" --reason-file \S+",
            )
            self.assertNotIn("<token>", context)
            self.assertIn("git-cli worktree add", context)

            rendered_advisory = json.dumps(advisory, sort_keys=True)
            for private_value in (
                private_prompt,
                private_name,
                private_content,
                str(repo),
            ):
                self.assertNotIn(private_value, rendered_advisory)

            challenge_files = [
                path
                for path in state.rglob("*.json")
                if path.is_file()
            ]
            self.assertEqual(len(challenge_files), 1)
            challenge_file = challenge_files[0]
            self.assertEqual(challenge_file.stat().st_mode & 0o777, 0o600)
            challenge_state = challenge_file.read_text(encoding="utf-8")
            challenge = json.loads(challenge_state)
            self.assertEqual(
                challenge["authorization_turn_digest"],
                hashlib.sha256(private_prompt.encode("utf-8")).hexdigest(),
            )
            reason_file = self._dirty_adoption_command(advisory)["reason_file"]
            self.assertTrue(reason_file.is_file())
            self.assertEqual(reason_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(reason_file.read_text(encoding="utf-8"), "")
            for private_value in (
                private_prompt,
                private_name,
                private_content,
                str(repo),
            ):
                self.assertNotIn(private_value, challenge_state)
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_dirty_checkout_adoption_quotes_private_reason_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state home"
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            self._dirty_snapshot_capability_or_skip(repo)

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "quoted-reason-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "authorize nothing yet",
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            details = self._dirty_adoption_command(advisory)
            argv = details["argv"]
            if details["transport"] == "argv":
                self.assertEqual(len(argv), 7)
                self.assertEqual(
                    argv[:4], ["git-cli", "worktree", "adopt-dirty", "--challenge"]
                )
                self.assertEqual(argv[5], "--reason-file")
            else:
                self.assertEqual(len(argv), 4)
                self.assertEqual(
                    Path(argv[0]).resolve(),
                    (HOOK_DIR / "checkout-lease-guard.py").resolve(),
                )
                self.assertEqual(argv[1:3], ["adopt-dirty", "--reason-file"])
            reason_file = details["reason_file"]
            self.assertTrue(reason_file.is_file())
            self.assertEqual(reason_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(reason_file.parent.stat().st_mode & 0o777, 0o700)
            self.assertFalse(
                reason_file.resolve(strict=False).is_relative_to(repo.resolve())
            )


    def test_dirty_checkout_adoption_reason_path_is_challenge_specific(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            self._dirty_snapshot_capability_or_skip(repo)
            reason_paths: list[Path] = []

            for prompt in ("first authorization turn", "second authorization turn"):
                code, advisory, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    {
                        "session_id": "unique-reason-session",
                        "hook_event_name": "UserPromptSubmit",
                        "prompt": prompt,
                    },
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNotNone(advisory)
                assert advisory is not None
                reason_paths.append(
                    self._dirty_adoption_command(advisory)["reason_file"]
                )

            self.assertNotEqual(reason_paths[0], reason_paths[1])
            self.assertFalse(reason_paths[0].exists())
            self.assertTrue(reason_paths[1].is_file())


    def test_dirty_checkout_adoption_is_silent_when_state_is_inside_checkout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            state = repo / ".runtime-state"
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "inside-state-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "inspect only",
                },
                cwd=repo,
                env={
                    "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                    "AGENT_RUNTIME_STATE_HOME": str(state),
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(advisory)
            self.assertFalse(state.exists())


    def test_dirty_checkout_adoption_is_silent_for_matching_live_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "existing-owner", repo / "README.md"
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lease_files = self._checkout_lease_files(state)
            self.assertEqual(len(lease_files), 1)
            before = lease_files[0].read_bytes()
            (repo / "owned.txt").write_text("owned\n", encoding="utf-8")

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "existing-owner",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "continue owned changes",
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(advisory)
            self.assertEqual(lease_files[0].read_bytes(), before)
            self.assertEqual(list(state.rglob("challenges/*.json")), [])


    def test_dirty_checkout_adoption_ignores_live_lease_from_stale_instance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            owner = self._checkout_lease_payload(
                "obsolete-owner", repo / "README.md"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            stale_lease = json.loads(
                self._checkout_lease_files(state)[0].read_text(encoding="utf-8")
            )
            replacement_instance = "f" * 32
            self.assertNotEqual(
                stale_lease["checkout_instance"], replacement_instance
            )
            (repo / ".git" / ".agent-runtime-checkout-instance").write_text(
                replacement_instance + "\n", encoding="ascii"
            )
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            self._dirty_snapshot_capability_or_skip(repo)

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "new-checkout-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "inspect recreated checkout",
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            self._dirty_adoption_command(advisory)


    def test_dirty_checkout_transition_requires_issuing_session_and_trusted_cli(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            fake_bin = root / "shadow" / "git-cli"
            fake_bin.parent.mkdir()
            fake_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_bin.chmod(0o755)
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            self._dirty_snapshot_capability_or_skip(repo)
            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "issuing-session",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "authorize this exact state",
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            details = self._dirty_adoption_command(advisory)
            argv = details["argv"]
            command = self._dirty_adoption_shell_command(details)
            if details["transport"] == "argv":
                shadow_command = shlex.join([str(fake_bin), *argv[1:]])
            else:
                # A launcher copy outside the trusted hook path is not the
                # governed transition, so the ordinary dirty-checkout gate
                # blocks it.
                fake_launcher = fake_bin.parent / "checkout-lease-guard.py"
                fake_launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                fake_launcher.chmod(0o755)
                shadow_command = self._dirty_adoption_launcher_command(
                    details, fake_launcher
                )

            for session_id, candidate, fragment in (
                ("issuing-session", command, None),
                ("foreign-session", command, "issuing agent session"),
                ("issuing-session", shadow_command, "unowned changes"),
            ):
                with self.subTest(session_id=session_id, command=candidate):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            session_id,
                            repo,
                            tool_name="Bash",
                            command=candidate,
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    if fragment is None:
                        self.assert_allowed(decision)
                    else:
                        self.assert_blocked(decision, fragment)

            redirected = f"{command} 2>/dev/null"
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "issuing-session",
                    repo,
                    tool_name="Bash",
                    command=redirected,
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

