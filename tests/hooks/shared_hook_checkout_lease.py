"""Shared hook tests: checkout lease."""
from __future__ import annotations

from shared_hook_helpers import (
    DIRTY_ADOPTION_FIXTURE_DIR,
    HOOK_DIR,
    HookTestCase,
    Path,
    REPO_ROOT,
    concurrent,
    hashlib,
    importlib,
    inventory_rules,
    inventory_tools,
    json,
    mock,
    os,
    run_enforced_hook,
    run_hook,
    shlex,
    subprocess,
    sys,
    tempfile,
    time,
)


class CheckoutLeaseTests(HookTestCase):

    def test_checkout_lease_guard_is_wired_for_prompt_mutation_and_stop(self) -> None:
        for product in ("codex", "claude"):
            prompt = inventory_rules(
                product=product,
                event="UserPromptSubmit",
                handler="checkout-lease-guard",
            )
            self.assertEqual(len(prompt), 1, product)
            mutations = inventory_tools(
                inventory_rules(
                    product=product,
                    event="PreToolUse",
                    handler="checkout-lease-guard",
                )
            )
            self.assertIn("Bash", mutations, product)
            self.assertIn("Write", mutations, product)
            stop = inventory_rules(
                product=product,
                event="Stop",
                handler="checkout-lease-guard",
            )
            self.assertEqual(len(stop), 1, product)

        hermes_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (REPO_ROOT / "targets" / "hermes").rglob("*")
            if path.is_file()
        )
        self.assertNotIn("checkout-lease-guard.py", hermes_sources)


    def test_checkout_lease_fixture_is_independent_of_ambient_commit_signing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "fixture"
            self._init_checkout_lease_repo(repo)
            signing = subprocess.run(
                ["git", "config", "--local", "--get", "commit.gpgsign"],
                cwd=repo,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(signing.returncode, 0)
            self.assertEqual(signing.stdout.strip(), "false")


    def test_checkout_lease_parser_accepts_released_v2_fixture(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_fixture_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            fixture = DIRTY_ADOPTION_FIXTURE_DIR / "checkout-lease-v2.json"
            lease = module.load_lease(fixture)
            self.assertIsNotNone(lease)
            assert lease is not None
            self.assertEqual(lease["schema"], module.LEASE_V2_SCHEMA)
            self.assertEqual(frozenset(lease), module.LEASE_V2_KEYS)
            self.assertEqual(
                frozenset(lease["adoption"]), module.ADOPTION_KEYS
            )
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_default_advisory_and_off_do_not_acquire_or_block(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            self._init_checkout_lease_repo(repo)
            state = root / "state"
            target = repo / "README.md"
            base_env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("owner", target),
                cwd=repo,
                env=dict(base_env, AGENT_SESSION_COORDINATION_MODE="enforce"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            leases = self._checkout_lease_files(state)
            self.assertEqual(len(leases), 1)
            owner = leases[0].read_text(encoding="utf-8")

            for mode in ("", "advisory", "off"):
                with self.subTest(mode=mode or "default"):
                    code, decision, stderr = run_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            f"contender-{mode or 'default'}", target
                        ),
                        cwd=repo,
                        env=dict(base_env, AGENT_SESSION_COORDINATION_MODE=mode),
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
                    self.assertEqual(self._checkout_lease_files(state), leases)
                    self.assertEqual(leases[0].read_text(encoding="utf-8"), owner)


    def test_checkout_lease_classifies_only_governed_dirty_transition_shapes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            reason_file = root / "adoption-reason.txt"
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            reason_file.write_text("Adopt the exact warned state.\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            valid_adopt = (
                "git-cli worktree adopt-dirty --challenge challenge-opaque-7 "
                f"--reason-file {shlex.quote(str(reason_file))}"
            )
            valid_revoke = (
                "git-cli worktree revoke-dirty --receipt receipt-opaque-7"
            )

            for command in ("git-cli worktree dirty-snapshot",):
                with self.subTest(admitted=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "transition-session",
                            repo,
                            tool_name="Bash",
                            command=command,
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command in (
                valid_adopt,
                valid_revoke,
                "git-cli worktree adopt-dirty --challenge challenge-opaque-7",
                "git-cli worktree adopt-dirty "
                f"--reason-file {shlex.quote(str(reason_file))}",
                "git-cli worktree revoke-dirty",
                "git-cli worktree revoke-dirty --receipt receipt-opaque-7 "
                f"--reason-file {shlex.quote(str(reason_file))}",
                f"{valid_adopt} && touch README.md",
                f"{valid_revoke} && touch README.md",
            ):
                with self.subTest(rejected=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "transition-session",
                            repo,
                            tool_name="Bash",
                            command=command,
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "unowned changes")

            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_admits_launcher_adoption_only_for_issuing_session(
        self,
    ) -> None:
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
            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "launcher-issuing-session",
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
            command = self._dirty_adoption_launcher_command(details)
            shadow = root / "shadow" / "checkout-lease-guard.py"
            shadow.parent.mkdir()
            shadow.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            shadow.chmod(0o755)
            copied_reason = root / "elsewhere" / details["reason_file"].name
            copied_reason.parent.mkdir()
            copied_reason.write_text("", encoding="utf-8")
            launcher = shlex.quote(str(HOOK_DIR / "checkout-lease-guard.py"))
            token = details["token"]

            for session_id, candidate, fragment in (
                ("launcher-issuing-session", command, None),
                ("launcher-issuing-session", f"{command} 2>/dev/null", None),
                ("foreign-session", command, "issuing agent session"),
                (
                    "launcher-issuing-session",
                    self._dirty_adoption_launcher_command(details, shadow),
                    "unowned changes",
                ),
                (
                    "launcher-issuing-session",
                    f"{launcher} adopt-dirty --reason-file "
                    f"{shlex.quote(str(copied_reason))} <<< {token}",
                    "reason file",
                ),
                (
                    "launcher-issuing-session",
                    f"{launcher} adopt-dirty --reason-file "
                    f"{shlex.quote(str(details['reason_file']))} --bogus <<< {token}",
                    "unowned changes",
                ),
                (
                    "launcher-issuing-session",
                    f"PATH=/tmp {command}",
                    "unowned changes",
                ),
                (
                    "launcher-issuing-session",
                    f"{command} && touch README.md",
                    "unowned changes",
                ),
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
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_v2_adoption_allows_current_session_and_preserves_refresh(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {
                "AGENT_RUNTIME_STATE_HOME": str(state),
                "AGENT_RUNTIME_CHECKOUT_LEASE_TTL_SECONDS": "60",
            }
            owner = self._checkout_lease_payload(
                "adoption-owner", repo / "README.md"
            )

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lease_file = self._checkout_lease_files(state)[0]
            adopted = self._write_adopted_checkout_lease_v2(
                lease_file, expires_offset=10
            )
            adoption_provenance = adopted["adoption"]
            acquired_at = adopted["acquired_at"]
            (repo / "untracked-adopted.txt").write_text(
                "preserved by adoption\n", encoding="utf-8"
            )

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            refreshed = json.loads(lease_file.read_text(encoding="utf-8"))
            self.assertEqual(refreshed["schema"], "agent-runtime.checkout-lease.v2")
            self.assertEqual(refreshed["adoption"], adoption_provenance)
            self.assertEqual(refreshed["acquired_at"], acquired_at)
            self.assertEqual(
                refreshed["checkout_root_bytes"], adopted["checkout_root_bytes"]
            )
            self.assertEqual(
                refreshed["checkout_git_dir_bytes"],
                adopted["checkout_git_dir_bytes"],
            )
            self.assertGreater(refreshed["expires_at"], adopted["expires_at"])


    def test_checkout_lease_v2_rejects_expired_foreign_and_malformed_adoptions(
        self,
    ) -> None:
        cases = (
            ("expired", -1, None, "unowned changes"),
            ("foreign", 60, "f" * 64, "another agent session"),
            ("malformed-path", 60, None, "state path"),
            ("unknown-field", 60, None, "state path"),
            ("unknown-adoption-field", 60, None, "state path"),
            ("boolean-timestamp", 60, None, "state path"),
            ("oversized-timestamp", 60, None, "state path"),
            ("unordered-adoption", 60, None, "state path"),
            ("uppercase-digest", 60, None, "state path"),
        )
        for case, expires_offset, session_key, fragment in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                state = root / "state"
                self._init_checkout_lease_repo(repo)
                env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
                owner = self._checkout_lease_payload(
                    "adoption-owner", repo / "README.md"
                )
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py", owner, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
                lease_file = self._checkout_lease_files(state)[0]
                adopted = self._write_adopted_checkout_lease_v2(
                    lease_file,
                    expires_offset=expires_offset,
                    session_key=session_key,
                )
                if case == "malformed-path":
                    adopted["checkout_root_bytes"] = "00"
                elif case == "unknown-field":
                    adopted["unexpected"] = "not permitted"
                elif case == "unknown-adoption-field":
                    adopted["adoption"]["unexpected"] = "not permitted"
                elif case == "boolean-timestamp":
                    adopted["refreshed_at"] = True
                elif case == "oversized-timestamp":
                    adopted["expires_at"] = 2**64
                elif case == "unordered-adoption":
                    adopted["adoption"]["challenge_issued_at"] = (
                        adopted["adoption"]["adopted_at"] + 1
                    )
                elif case == "uppercase-digest":
                    adopted["adoption"]["reason_digest"] = "A" * 64
                lease_file.write_text(
                    json.dumps(adopted, sort_keys=True) + "\n", encoding="utf-8"
                )
                (repo / "untracked-adopted.txt").write_text(
                    "untracked only\n", encoding="utf-8"
                )

                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py", owner, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)


    def test_checkout_lease_treats_semantic_commit_help_and_dry_run_as_read_only(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            for command in (
                "semantic-commit commit --help",
                "semantic-commit commit --dry-run --message 'fix: inspect only'",
                "semantic-commit commit --validate-only --message 'fix: inspect only'",
                "semantic-commit default-branch --dry-run "
                "--message 'fix: inspect only'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "read-only", repo, tool_name="Bash", command=command
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_classifies_all_semantic_commit_writers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            (repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            (repo / "-h").write_text("fix: option-value help\n", encoding="utf-8")
            (repo / "--dry-run").write_text(
                "fix: option-value dry run\n", encoding="utf-8"
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            for command in (
                "semantic-commit commit --message 'fix: inspect only'",
                "semantic-commit commit --dry-run --message 'fix: inspect only' "
                "--message-out recovery.md",
                "semantic-commit commit --validate-only --message 'fix: inspect only' "
                "--message-out recovery.md",
                "semantic-commit commit --message-file -h",
                "semantic-commit commit --message-file --dry-run",
                "semantic-commit fixup HEAD~1",
                "semantic-commit squash HEAD~1",
                "semantic-commit default-branch --message 'fix: inspect only' "
                "--bullet --dry-run",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "writer", repo, tool_name="Bash", command=command
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "unowned changes")
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_classifies_git_cli_sync_branch_as_mutating(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_sync_branch_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            self.assertTrue(module.git_cli_invocation_mutates(["sync-branch"]))
            self.assertTrue(
                module.git_cli_invocation_mutates(
                    ["sync-branch", "--remote", "origin", "--format", "json"]
                )
            )
            self.assertTrue(
                module.git_cli_invocation_mutates(
                    ["sync-branch", "--remote", "help", "--format", "json"]
                )
            )
            self.assertFalse(module.git_cli_invocation_mutates(["sync-branch", "--help"]))
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_multi_edit_resolves_one_checkout_once(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                checkout = module.Checkout(
                    root=root,
                    git_dir=root / ".git",
                    common_dir=root / ".git",
                    primary=True,
                )
                probes: list[Path] = []

                def fake_checkout_from(path: Path):
                    probes.append(path)
                    return checkout

                module.checkout_from = fake_checkout_from
                payload = {
                    "cwd": str(root),
                    "tool_input": {
                        "edits": [
                            {"file_path": str(root / f"file-{index}.txt")}
                            for index in range(30)
                        ]
                    },
                }
                self.assertEqual(
                    module.target_checkouts(payload, "MultiEdit"), [checkout]
                )
                self.assertEqual(probes, [root])
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_redirect_membership_is_bounded_without_git_probes(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_redirect_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                outside = root / "outside"
                (repo / ".git").mkdir(parents=True)
                outside.mkdir()
                target = repo / "README.md"
                target.write_text("fixture\n", encoding="utf-8")
                alias = outside / "alias"
                alias.symlink_to(target)
                dangling_alias = outside / "dangling-alias"
                dangling_alias.symlink_to(repo / "future.txt")
                hard_alias = outside / "hard-alias"
                os.link(target, hard_alias)

                def unexpected_run_git(*_args, **_kwargs):
                    raise AssertionError("redirect membership must not invoke Git")

                module.run_git = unexpected_run_git
                self.assertTrue(
                    module.redirect_target_is_repo_write(str(target), repo)
                )
                self.assertTrue(
                    module.redirect_target_is_repo_write(str(alias), repo)
                )
                self.assertTrue(
                    module.redirect_target_is_repo_write(str(dangling_alias), repo)
                )
                self.assertTrue(
                    module.redirect_target_is_repo_write(str(hard_alias), repo)
                )
                for expanded_alias in (
                    str(outside / "alia?.md"),
                    str(outside / "alias.m{d..d}"),
                    str(outside / "alias.@(md)"),
                ):
                    with self.subTest(expanded_alias=expanded_alias):
                        self.assertTrue(
                            module.redirect_target_is_repo_write(
                                expanded_alias, repo
                            )
                        )
                extglob_source = f"printf x > {outside / 'alias.@(md)'}"
                self.assertTrue(
                    module.shell_command_has_parenthesized_redirect_word(
                        f"bash -O extglob -c {shlex.quote(extglob_source)}"
                    )
                )
                self.assertFalse(
                    module.shell_command_has_parenthesized_redirect_word(
                        f"printf x > {shlex.quote(str(outside / 'literal.(md)'))}"
                    )
                )
                self.assertFalse(
                    module.shell_command_has_parenthesized_redirect_word(
                        f"printf x > {outside / 'sentinel'}; (true)"
                    )
                )
                external = outside / "sentinel"
                self.assertFalse(
                    module.redirect_target_is_repo_write(str(external), repo)
                )
                repeated = next(
                    iter(
                        module.simple_commands_with_nested_shells(
                            f"true > {external} 2> {external}"
                        )
                    )
                )
                self.assertFalse(module.command_writes_repo(repeated, repo))

                targets = " ".join(
                    f"> {outside / f'sentinel-{index}'}"
                    for index in range(module.MAX_REDIRECT_TARGETS + 1)
                )
                bounded = next(
                    iter(module.simple_commands_with_nested_shells(f"true {targets}"))
                )
                self.assertTrue(module.command_writes_repo(bounded, repo))

                probes: list[str] = []
                original_membership = module.resolved_target_may_touch_checkout

                def counted_membership(raw_target: str) -> bool:
                    probes.append(raw_target)
                    return original_membership(raw_target)

                module.resolved_target_may_touch_checkout = counted_membership
                split_redirects = "; ".join(
                    f"true > {outside / f'split-{index}'}"
                    for index in range(module.MAX_REDIRECT_TARGETS + 1)
                )
                self.assertTrue(
                    module.high_confidence_shell_mutation(split_redirects, repo)
                )
                self.assertLessEqual(len(probes), module.MAX_REDIRECT_TARGETS)
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_owner_refreshes_dirty_checkout_and_blocks_foreign_writer(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            owner_payload = self._checkout_lease_payload(
                "owner-session", repo / "README.md"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner_payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            (repo / "owned.txt").write_text("owner change\n", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner_payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            foreign_payload = self._checkout_lease_payload(
                "foreign-session", repo / "README.md"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", foreign_payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")


    def test_checkout_lease_owner_refresh_is_throttled_until_renewal_window(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            owner = self._checkout_lease_payload("owner", repo / "README.md")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lease_file = self._checkout_lease_files(state)[0]
            initial = lease_file.read_bytes()
            initial_mtime = lease_file.stat().st_mtime_ns
            time.sleep(0.02)

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(lease_file.read_bytes(), initial)
            self.assertEqual(lease_file.stat().st_mtime_ns, initial_mtime)


    def test_checkout_lease_lock_wait_is_bounded(self) -> None:
        import fcntl

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            payload = self._checkout_lease_payload("owner", repo / "README.md")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lock_file = next((state / "checkout-leases").rglob("lease.lock"))

            with lock_file.open("a+", encoding="utf-8") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                started = time.monotonic()
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py", payload, cwd=repo, env=env
                )
                elapsed = time.monotonic() - started
            self.assertEqual(code, 0, stderr)
            self.assertLess(elapsed, 3.0)
            self.assert_blocked(decision, "lock timed out")


    def test_checkout_lease_blocks_unowned_dirty_and_non_default_primary_checkout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dirty_repo = root / "dirty"
            branch_repo = root / "branch"
            state = root / "state"
            self._init_checkout_lease_repo(dirty_repo)
            self._init_checkout_lease_repo(branch_repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            (dirty_repo / "unowned.txt").write_text("unknown\n", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", dirty_repo / "README.md"),
                cwd=dirty_repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "unowned changes")

            subprocess.run(
                ["git", "switch", "-q", "-c", "feature/direct-edit"],
                cwd=branch_repo,
                check=True,
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", branch_repo / "README.md"),
                cwd=branch_repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "default branch")


    def test_checkout_lease_allows_worktree_add_on_non_default_primary(self) -> None:
        # Regression for issue #622 (Bug 1): the guard must not block
        # `git-cli worktree add`, the exact escape `worktree_guidance()`
        # recommends. A primary checkout on a non-default branch blocks a direct
        # edit but must allow a sole `git-cli worktree add`, or the agent
        # deadlocks on the guard's own remediation command.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "switch", "-q", "-c", "feature/lease-guard"],
                cwd=repo,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            # A direct edit is still gated to the resolved default branch.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "default branch")

            # The recommended escape is allowed from the very same checkout.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "writer",
                    repo,
                    tool_name="Bash",
                    command="git-cli worktree add feature-lane",
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # A resolved shell wrapper around the sole add is unwrapped and still
            # allowed, so the sanctioned escape survives a `bash -c '…'` form.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "writer",
                    repo,
                    tool_name="Bash",
                    command="bash -c 'git-cli worktree add wrapped-lane'",
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # The escape short-circuits: it claims no lease on the current
            # checkout rather than acquiring or refreshing one.
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_worktree_add_allow_flows_through_carveout(self) -> None:
        # Pin that the escape is admitted via the worktree-add carve-out, not the
        # earlier "not a high-confidence mutation" return: `git-cli worktree add`
        # must stay classified as a mutation AND be cleared by the carve-out.
        # Also pins the carve-out's narrowness at the unit boundary so a
        # regression that widens any guard branch fails here.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_carveout",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            base = Path(HOOK_DIR)
            self.assertTrue(
                module.high_confidence_shell_mutation("git-cli worktree add lane")
            )
            self.assertTrue(
                module.sole_managed_worktree_add("git-cli worktree add lane", base)
            )
            self.assertTrue(
                module.sole_managed_worktree_add(
                    "bash -c 'git-cli worktree add lane'", base
                )
            )
            for command in (
                "git-cli worktree add a && git-cli worktree add b",
                "git-cli worktree add a; git-cli worktree add b",
                "git-cli worktree add a && rm -rf b",
                "git-cli worktree add a > out.txt",
                'bash -c "$UNRESOLVED"',
            ):
                self.assertFalse(
                    module.sole_managed_worktree_add(command, base), command
                )
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_git_recovery_op_carveout(self) -> None:
        # A sole `git <op> --abort`/`--quit` restores the pre-operation state
        # and authors no content, so the carve-out must admit it AND stay as
        # narrow as the worktree-add carve-out. `--continue`/`--skip` advance
        # the operation and must NOT be carved out.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_recovery",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            base = Path(HOOK_DIR)
            for op in ("rebase", "merge", "cherry-pick", "revert", "am"):
                for flag in ("--abort", "--quit"):
                    command = f"git {op} {flag}"
                    self.assertTrue(
                        module.high_confidence_shell_mutation(command), command
                    )
                    self.assertTrue(
                        module.sole_git_recovery_operation(command, base), command
                    )
            self.assertTrue(
                module.sole_git_recovery_operation(
                    "bash -c 'git rebase --abort'", base
                )
            )
            for command in (
                "git rebase --continue",
                "git rebase --skip",
                "git merge --abort && rm -rf README.md",
                "git rebase --abort > escape.txt",
                "git rebase --abort; git rebase --abort",
                "git commit -m x",
                "git status",
                'bash -c "$UNRESOLVED"',
            ):
                self.assertFalse(
                    module.sole_git_recovery_operation(command, base), command
                )
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_admits_git_recovery_op_mid_operation(self) -> None:
        # Integration: a planted MERGE_HEAD blocks a fresh (unowned) mutation
        # through the git-operation admission gate; the recovery carve-out must
        # admit `git rebase --abort` without taking a lease so the checkout can
        # recover in place, while a non-recovery edit stays blocked.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            git_dir = subprocess.run(
                ["git", "rev-parse", "--absolute-git-dir"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (Path(git_dir) / "MERGE_HEAD").write_text("fixture\n", encoding="utf-8")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "writer", repo, tool_name="Bash", command="git rebase --abort"
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(self._checkout_lease_files(state), [])

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "Git operation")


    def test_checkout_lease_worktree_add_carveout_does_not_cover_co_mutation(
        self,
    ) -> None:
        # The carve-out must not smuggle another working-tree write past the
        # gate: a co-resident mutation or an output redirection falls back to
        # normal fail-closed gating on the non-default primary checkout.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "switch", "-q", "-c", "feature/lease-guard"],
                cwd=repo,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            # A co-resident mutation, an output redirection, or a second add all
            # fall back to the primary-checkout admission gate; an unresolved
            # nested shell fails closed on the unresolvable-scope path. In every
            # case the carve-out declines to admit the command.
            for command, fragment in (
                ("git-cli worktree add feature-lane && rm -rf README.md", "default branch"),
                ("git-cli worktree add feature-lane > escape.txt", "default branch"),
                (
                    "git-cli worktree add feature-lane && git-cli worktree add other-lane",
                    "default branch",
                ),
                ('bash -c "$UNRESOLVED"', "unresolved"),
            ):
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload(
                        "writer", repo, tool_name="Bash", command=command
                    ),
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)


    def test_checkout_lease_primary_requires_authoritative_default_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "symbolic-ref", "--delete", "refs/remotes/origin/HEAD"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "init.defaultBranch", "main"], cwd=repo, check=True
            )

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "default=unknown")


    def test_checkout_lease_reclaims_expired_clean_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("first", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            lease_file = self._checkout_lease_files(state)[0]
            lease = json.loads(lease_file.read_text(encoding="utf-8"))
            lease["expires_at"] = 0
            lease_file.write_text(json.dumps(lease) + "\n", encoding="utf-8")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("second", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_checkout_lease_does_not_reclaim_expired_dirty_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("first", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lease_file = self._checkout_lease_files(state)[0]
            lease = json.loads(lease_file.read_text(encoding="utf-8"))
            lease["expires_at"] = 0
            lease_file.write_text(json.dumps(lease) + "\n", encoding="utf-8")
            (repo / "dirty.txt").write_text("unowned\n", encoding="utf-8")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("second", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "unowned changes")


    def test_checkout_lease_rejects_cross_checkout_edit_without_partial_claim(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            state = root / "state"
            self._init_checkout_lease_repo(first)
            self._init_checkout_lease_repo(second)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            payload = {
                "session_id": "writer",
                "hook_event_name": "PreToolUse",
                "tool_name": "MultiEdit",
                "cwd": str(first),
                "tool_input": {
                    "edits": [
                        {"file_path": str(first / "README.md")},
                        {"file_path": str(second / "README.md")},
                    ]
                },
            }
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", payload, cwd=first, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "spans multiple checkouts")
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_atomic_race_has_exactly_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            def attempt(session: str) -> tuple[int, dict[str, object] | None, str]:
                return run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload(session, repo / "README.md"),
                    cwd=repo,
                    env=env,
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(attempt, ("racer-one", "racer-two")))

            self.assertTrue(all(code == 0 for code, _, _ in results), results)
            allowed = [decision for _, decision, _ in results if decision is None]
            blocked = [decision for _, decision, _ in results if decision is not None]
            self.assertEqual(len(allowed), 1, results)
            self.assertEqual(len(blocked), 1, results)
            self.assert_blocked(blocked[0], "another agent session")

            lease_files = list((state / "checkout-leases").rglob("lease.json"))
            self.assertEqual(len(lease_files), 1)
            lease = json.loads(lease_files[0].read_text(encoding="utf-8"))
            lease["expires_at"] = 0
            lease_files[0].write_text(
                json.dumps(lease, sort_keys=True) + "\n", encoding="utf-8"
            )

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("second", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_checkout_lease_read_only_git_probes_disable_optional_locks(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_git_probe_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            captured: dict[str, object] = {}
            real_run = module.subprocess.run

            def inspect_run(
                *args: object, **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                captured.update(kwargs)
                return subprocess.CompletedProcess(args[0], 0, "", "")

            module.subprocess.run = inspect_run
            try:
                completed = module.run_git(REPO_ROOT, "status", "--short")
            finally:
                module.subprocess.run = real_run

            self.assertEqual(completed.returncode, 0)
            environment = captured.get("env")
            self.assertIsInstance(environment, dict)
            assert isinstance(environment, dict)
            self.assertEqual(environment.get("GIT_OPTIONAL_LOCKS"), "0")
            self.assertEqual(environment.get("PATH"), os.environ.get("PATH"))
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_instance_publication_is_complete_and_cleans_temp(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_publication_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                git_dir = root / ".git"
                git_dir.mkdir()
                checkout = module.Checkout(
                    root=root,
                    git_dir=git_dir,
                    common_dir=git_dir,
                    primary=True,
                )
                real_write = module.os.write
                real_link = module.os.link
                published_payloads: list[str] = []
                write_calls = 0

                def short_write(descriptor: int, payload: bytes) -> int:
                    nonlocal write_calls
                    write_calls += 1
                    return real_write(descriptor, payload[:3])

                def inspect_then_link(
                    source: str,
                    destination: Path,
                    *,
                    follow_symlinks: bool,
                ) -> None:
                    published_payloads.append(
                        Path(source).read_text(encoding="ascii")
                    )
                    real_link(
                        source,
                        destination,
                        follow_symlinks=follow_symlinks,
                    )

                module.os.write = short_write
                module.os.link = inspect_then_link
                try:
                    instance = module.read_instance(checkout, create=True)
                finally:
                    module.os.write = real_write
                    module.os.link = real_link

                self.assertGreater(write_calls, 1)
                self.assertRegex(instance, r"^[0-9a-f]{32}$")
                self.assertEqual(published_payloads, [f"{instance}\n"])
                self.assertEqual(
                    (git_dir / module.INSTANCE_FILE).read_text(encoding="ascii"),
                    f"{instance}\n",
                )
                self.assertEqual(
                    list(git_dir.glob(f".{module.INSTANCE_FILE}-*")), []
                )

                (git_dir / module.INSTANCE_FILE).unlink()
                module.os.write = lambda _descriptor, _payload: 0
                try:
                    with self.assertRaisesRegex(
                        module.LeaseError, "write made no progress"
                    ):
                        module.read_instance(checkout, create=True)
                finally:
                    module.os.write = real_write
                self.assertFalse((git_dir / module.INSTANCE_FILE).exists())
                self.assertEqual(
                    list(git_dir.glob(f".{module.INSTANCE_FILE}-*")), []
                )
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_instance_rejects_final_symlink_without_temp_leak(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_symlink_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                git_dir = root / ".git"
                git_dir.mkdir()
                external = root / "external"
                external.write_text("unchanged\n", encoding="utf-8")
                checkout = module.Checkout(
                    root=root,
                    git_dir=git_dir,
                    common_dir=git_dir,
                    primary=True,
                )
                real_link = module.os.link

                def race_with_symlink(
                    source: str,
                    destination: Path,
                    *,
                    follow_symlinks: bool,
                ) -> None:
                    destination.symlink_to(external)
                    real_link(
                        source,
                        destination,
                        follow_symlinks=follow_symlinks,
                    )

                module.os.link = race_with_symlink
                try:
                    with self.assertRaisesRegex(
                        module.LeaseError, "checkout lease file unavailable"
                    ):
                        module.read_instance(checkout, create=True)
                finally:
                    module.os.link = real_link

                self.assertEqual(external.read_text(encoding="utf-8"), "unchanged\n")
                self.assertEqual(
                    list(git_dir.glob(f".{module.INSTANCE_FILE}-*")), []
                )
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_recreated_worktree_gets_a_new_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/one", str(linked)],
                cwd=primary,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("first", linked / "README.md"),
                cwd=linked,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            subprocess.run(
                ["git", "worktree", "remove", str(linked)], cwd=primary, check=True
            )
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/two", str(linked)],
                cwd=primary,
                check=True,
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("second", linked / "README.md"),
                cwd=linked,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_checkout_lease_blocks_git_operation_and_missing_mutation_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            git_dir = subprocess.run(
                ["git", "rev-parse", "--absolute-git-dir"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (Path(git_dir) / "MERGE_HEAD").write_text("fixture\n", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "Git operation")
            (Path(git_dir) / "MERGE_HEAD").unlink()

            missing_session = self._checkout_lease_payload("", repo / "README.md")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", missing_session, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "session identity")


    def test_checkout_lease_blocks_preexisting_index_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            git_dir = subprocess.run(
                ["git", "rev-parse", "--absolute-git-dir"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (Path(git_dir) / "index.lock").write_text("fixture\n", encoding="utf-8")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env=env,
            )

            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "Git operation (index update)")
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_unavailable_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state_file = root / "state-is-a-file"
            self._init_checkout_lease_repo(repo)
            state_file.write_text("not a directory\n", encoding="utf-8")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state_file)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "fails closed")


    def test_checkout_lease_reports_cause_specific_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)

            dynamic = self._checkout_lease_payload(
                "writer",
                repo,
                tool_name="Bash",
                command='CMD=echo; "$CMD" hi',
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                dynamic,
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "Use a concrete executable")
            assert decision is not None
            self.assertNotIn(
                "Restore the managed runtime state path",
                str(decision.get("reason", "")),
            )

            state_file = root / "state-is-a-file"
            state_file.write_text("not a directory\n", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("writer", repo / "README.md"),
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state_file)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "Restore the managed runtime state path")


    def test_checkout_lease_reports_remaining_cause_specific_remediation(
        self,
    ) -> None:
        for command in (
            "git-cli worktree remove one two",
            "git-cli worktree remove missing-worktree",
        ):
            with self.subTest(scope_command=command), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                state = root / "state"
                self._init_checkout_lease_repo(repo)
                payload = self._checkout_lease_payload(
                    "writer",
                    repo,
                    tool_name="Bash",
                    command=command,
                )
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    payload,
                    cwd=repo,
                    env={"AGENT_RUNTIME_STATE_HOME": str(state)},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "an explicit target")
                assert decision is not None
                self.assertNotIn(
                    "Restore the managed runtime state path",
                    str(decision.get("reason", "")),
                )

        for failure in ("lock-path", "lease-file"):
            with self.subTest(state_failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                state = root / "state"
                self._init_checkout_lease_repo(repo)
                env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload("owner", repo / "README.md"),
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
                lease_file = self._checkout_lease_files(state)[0]
                if failure == "lock-path":
                    lock_path = lease_file.parent / "lease.lock"
                    lock_path.unlink()
                    lock_path.symlink_to(os.devnull)
                else:
                    lease_file.write_text("{malformed\n", encoding="utf-8")

                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload("reader", repo / "README.md"),
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(
                    decision, "Restore the managed runtime state path"
                )


    def test_checkout_lease_preserves_read_only_bash_and_stop_is_non_destructive(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            for command in (
                "git status --short",
                "git branch --show-current",
                "git branch --list",
                "git branch -avv",
                "git branch --contains HEAD",
                "git branch --merged HEAD --format='%(refname:short)'",
                "git tag --list",
                "git tag -n",
                "git tag --points-at HEAD",
                "git tag --contains HEAD --format='%(refname:short)'",
                "git stash list",
                "git bisect log",
                "git bisect terms",
                "command -v git-cli",
                "command -V git-cli",
                "/usr/bin/time -V",
                "/usr/bin/time --vers",
                "env --help",
                "env --version",
                "env -uSOMETHING printf ok",
                "env -S 'printf foo\u00a0#bar'",
                "env if touch wrapper-argument.txt",
                "wc -l < README.md",
            ):
                with self.subTest(command=command):
                    read_only = self._checkout_lease_payload(
                        "", repo, tool_name="Bash", command=command
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py", read_only, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command in (
                "git branch topic",
                "git tag v1",
                "git stash push",
                "git bisect start",
                "git pull --ff-only",
                "bash -c 'touch nested.txt'",
                "agent-run exec --cwd . -- touch wrapped.txt",
                "env - touch empty-env.txt",
                "env -uSOMETHING touch unset-env.txt",
                "env --block-signal=PIPE touch signal-env.txt",
                "! touch bang-control.txt",
                "if true; then touch if-control.txt; fi",
                "while true; do touch while-control.txt; break; done",
                "mutate() { touch function-control.txt; }; mutate",
                "function mutate { touch function-bash.txt; }; mutate",
                "function mutate() { touch function-bash-parens.txt; }; mutate",
                'CMD=touch; "$CMD" dynamic-variable.txt',
                "`printf touch` dynamic-backtick.txt",
                "$(printf touch) dynamic-substitution.txt",
                "bash -c 'CMD=touch; \"$CMD\" nested-dynamic.txt'",
                "printf x >generated.txt",
                "printf x 2>errors.txt",
                "printf x >>generated.txt",
                "printf x &>combined.txt",
                "printf x >|clobber.txt",
            ):
                with self.subTest(command=command):
                    mutation = self._checkout_lease_payload(
                        "", repo, tool_name="Bash", command=command
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py", mutation, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "session identity")

            mutation = self._checkout_lease_payload(
                "", repo, tool_name="Bash", command="touch generated.txt"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", mutation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "session identity")

            nested_mutation = "touch depth-limited.txt"
            for _ in range(6):
                nested_mutation = f"bash -c {shlex.quote(nested_mutation)}"
            mutation = self._checkout_lease_payload(
                "", repo, tool_name="Bash", command=nested_mutation
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", mutation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "session identity")

            nested_env_split = "touch env-depth-limited.txt"
            for _ in range(5):
                nested_env_split = f"-S {shlex.quote(nested_env_split)}"
            nested_env_mutation = f"env -S {shlex.quote(nested_env_split)}"
            mutation = self._checkout_lease_payload(
                "", repo, tool_name="Bash", command=nested_env_mutation
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", mutation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "session identity")

            variable_env_mutation = self._checkout_lease_payload(
                "",
                repo,
                tool_name="Bash",
                command="CMD=touch env -S '${CMD} variable-expanded.txt'",
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", variable_env_mutation, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "session identity")

            for command in (
                "export CMD=touch; env -S \"'${CMD}' quote-expanded.txt\"",
                "env -S \"'`printf touch`' backtick-expanded.txt\"",
                "env -S '# ignored' touch comment-hidden.txt",
            ):
                with self.subTest(command=command):
                    opaque_mutation = self._checkout_lease_payload(
                        "", repo, tool_name="Bash", command=command
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        opaque_mutation,
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "session identity")

            owner = self._checkout_lease_payload("owner", repo / "README.md")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lease_files = list((state / "checkout-leases").rglob("lease.json"))
            self.assertEqual(len(lease_files), 1)

            stop_payload = {"session_id": "owner", "hook_event_name": "Stop"}
            code, audit, stderr = run_enforced_hook(
                "checkout-lease-guard.py", stop_payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(audit)
            assert audit is not None
            self.assertIn("released", str(audit.get("systemMessage", "")))
            self.assertFalse(lease_files[0].exists())


    def test_checkout_lease_admits_real_native_non_utf8_checkout_path(self) -> None:
        if sys.platform == "win32":
            self.skipTest("native non-UTF-8 path bytes require a POSIX filesystem")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._native_non_utf8_checkout_path_or_skip(root)
            state = root / "state"
            self._init_checkout_lease_repo(repo)

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "native-path-owner", repo / "README.md"
                ),
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            lease_files = self._checkout_lease_files(state)
            self.assertEqual(len(lease_files), 1)
            lease = json.loads(lease_files[0].read_text(encoding="utf-8"))
            self.assertEqual(
                os.fsencode(lease["checkout_root"]), os.fsencode(repo)
            )


    def test_checkout_lease_stop_uses_v2_native_paths_to_release(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_native_release_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = root / "state"
                common_dir = root / "common"
                common_dir.mkdir()
                native_root = self._native_non_utf8_checkout_path_or_skip(root)
                native_git_dir = native_root / ".git"
                native_git_dir.mkdir(parents=True)
                repository_checkout = module.Checkout(
                    root=root / "repository",
                    git_dir=common_dir,
                    common_dir=common_dir,
                    primary=True,
                )
                session_key = "2" * 64
                instance = "c" * 32
                lease = self._released_v2_fixture_for_paths(
                    native_root,
                    native_git_dir,
                    session_key=session_key,
                    checkout_instance=instance,
                )
                native_checkout = module.Checkout(
                    root=native_root,
                    git_dir=native_git_dir,
                    common_dir=common_dir,
                    primary=False,
                )

                with mock.patch.dict(
                    os.environ,
                    {"AGENT_RUNTIME_CHECKOUT_LEASE_STATE_HOME": str(state)},
                ):
                    repository_dir = module.repository_state_dir(
                        repository_checkout
                    )
                    lease_directory = repository_dir / hashlib.sha256(
                        os.fsencode(native_root)
                    ).hexdigest()
                    module.private_directory(lease_directory)
                    lease_file = lease_directory / "lease.json"
                    module.write_lease(lease_file, lease)

                    module.checkout_from = lambda path: (
                        native_checkout
                        if os.fsencode(path) == os.fsencode(native_root)
                        else None
                    )
                    module.read_instance = lambda *_args, **_kwargs: instance
                    module.git_operation = lambda _checkout: ""
                    module.checkout_dirty = lambda _checkout: False

                    self.assertEqual(
                        module.release_clean_session_leases(
                            repository_checkout, session_key
                        ),
                        (1, 0, 0),
                    )
                    self.assertFalse(lease_file.exists())
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_stop_uses_v2_native_paths_before_pruning(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "checkout_lease_guard_native_prune_test",
            HOOK_DIR / "checkout-lease-guard.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = root / "state"
                common_dir = root / "common"
                common_dir.mkdir()
                native_root = self._native_non_utf8_checkout_path_or_skip(root)
                native_git_dir = native_root / ".git"
                native_git_dir.mkdir(parents=True)
                repository_checkout = module.Checkout(
                    root=root / "repository",
                    git_dir=common_dir,
                    common_dir=common_dir,
                    primary=True,
                )
                lease = self._released_v2_fixture_for_paths(
                    native_root, native_git_dir
                )

                with mock.patch.dict(
                    os.environ,
                    {"AGENT_RUNTIME_CHECKOUT_LEASE_STATE_HOME": str(state)},
                ):
                    repository_dir = module.repository_state_dir(
                        repository_checkout
                    )
                    lease_directory = repository_dir / hashlib.sha256(
                        os.fsencode(native_root)
                    ).hexdigest()
                    module.private_directory(lease_directory)
                    lease_file = lease_directory / "lease.json"
                    module.write_lease(lease_file, lease)

                    self.assertEqual(
                        module.prune_removed_checkout_leases(repository_checkout),
                        0,
                    )
                    self.assertTrue(lease_file.exists())
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_stop_retains_dirty_owner_and_prunes_removed_worktree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/prune", str(linked)],
                cwd=primary,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            owner = self._checkout_lease_payload("owner", primary / "README.md")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            (primary / "dirty.txt").write_text("owned\n", encoding="utf-8")
            code, audit, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {"session_id": "owner", "hook_event_name": "Stop"},
                cwd=primary,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(audit)
            self.assertIn("retained", str(audit.get("systemMessage", "")))
            self.assertEqual(len(self._checkout_lease_files(state)), 1)
            (primary / "dirty.txt").unlink()

            linked_owner = self._checkout_lease_payload("linked-owner", linked / "README.md")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", linked_owner, cwd=linked, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            linked_lease = next(
                lease_path
                for lease_path in self._checkout_lease_files(state)
                if json.loads(lease_path.read_text(encoding="utf-8"))[
                    "checkout_root"
                ]
                == str(linked.resolve())
            )
            linked_lock = linked_lease.parent / "lease.lock"
            lock_inode = linked_lock.stat().st_ino
            subprocess.run(
                ["git", "worktree", "remove", str(linked)], cwd=primary, check=True
            )
            code, _audit, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {"session_id": "other", "hook_event_name": "Stop"},
                cwd=primary,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(len(self._checkout_lease_files(state)), 1)
            self.assertTrue(linked_lock.exists())
            self.assertEqual(linked_lock.stat().st_ino, lock_inode)


    def test_checkout_lease_advisory_safe_removal_delegates_to_execution_fence(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("safe_removal_test", HOOK_DIR / "checkout-lease-guard.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                primary = Path(tmp) / "primary"
                self._init_checkout_lease_repo(primary)
                linked = self._add_checkout_lease_worktree(primary, "feature/safe-removal")
                payload = self._checkout_lease_payload("owner", primary, tool_name="Bash",
                    command=f"git-cli worktree remove {shlex.quote(str(linked))} --safe --format json")
                with mock.patch.dict(os.environ, {"AGENT_SESSION_COORDINATION_MODE": "advisory"}), \
                     mock.patch.object(module, "read_payload", return_value=payload), \
                     mock.patch.object(module, "resolved_executable_matches", return_value=True), \
                     mock.patch.object(module, "emit_block") as blocked:
                    module.main()
                blocked.assert_not_called()
                self.assertTrue(linked.exists(), "PreToolUse never performs cleanup")
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_safe_removal_rejects_bypass_and_compound_shapes(self) -> None:
        spec = importlib.util.spec_from_file_location("safe_removal_shapes", HOOK_DIR / "checkout-lease-guard.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                primary = Path(tmp) / "primary"
                self._init_checkout_lease_repo(primary)
                linked = self._add_checkout_lease_worktree(primary, "feature/safe-shapes")
                target = shlex.quote(str(linked))
                for command in (
                    f"git-cli worktree remove {target} -- --safe",
                    f"AGENT_SESSION_STATE_DIR=/unknown git-cli worktree remove {target} --safe",
                    f"export PATH=/untrusted/bin:$PATH; git-cli worktree remove {target} --safe",
                    f"export AGENT_SESSION_STATE_DIR=/empty-state; git-cli worktree remove {target} --safe",
                    f"export AGENT_RUNTIME_CHECKOUT_LEASE_STATE_HOME=/empty-leases; git-cli worktree remove {target} --safe",
                    f"unset AGENT_SESSION_STATE_DIR; git-cli worktree remove {target} --safe",
                    f"source /untrusted/setup; git-cli worktree remove {target} --safe",
                    f"git-cli worktree remove {target} --safe && touch README.md",
                    f"git-cli worktree remove {target} --safe; git-cli worktree remove {target} --safe",
                    f"git-cli worktree remove {target} --safe > README.md",
                    "git-cli branch cleanup --remove-worktrees",
                    "git-cli branch delete-merged -w",
                ):
                    with self.subTest(command=command):
                        payload = self._checkout_lease_payload("owner", primary, tool_name="Bash", command=command)
                        with mock.patch.dict(os.environ, {"AGENT_SESSION_COORDINATION_MODE": "advisory"}), \
                             mock.patch.object(module, "read_payload", return_value=payload), \
                             mock.patch.object(module, "resolved_executable_matches", return_value=True), \
                             mock.patch.object(module, "emit_block") as blocked:
                            module.main()
                        blocked.assert_called()
                payload = self._checkout_lease_payload("owner", primary, tool_name="Bash",
                    command=f"git-cli worktree remove {target} --safe")
                with mock.patch.dict(os.environ, {"AGENT_SESSION_COORDINATION_MODE": "advisory"}), \
                     mock.patch.object(module, "read_payload", return_value=payload), \
                     mock.patch.object(module, "resolved_executable_matches", return_value=False), \
                     mock.patch.object(module, "emit_block") as blocked:
                    module.main()
                blocked.assert_called()
                self.assertTrue(linked.exists())
        finally:
            sys.modules.pop(spec.name, None)


    def test_checkout_lease_advisory_removal_delegates_to_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/remove")
            state = root / "state"
            remove = self._checkout_lease_payload(
                "delivery", primary, tool_name="Bash",
                command=f"git-cli worktree remove {shlex.quote(str(linked))} --format json",
            )
            for mode in ("", "advisory", "off"):
                with self.subTest(mode=mode or "default"):
                    code, decision, stderr = run_hook(
                        "checkout-lease-guard.py", remove, cwd=primary,
                        env={"AGENT_RUNTIME_STATE_HOME": str(state),
                             "AGENT_SESSION_COORDINATION_MODE": mode},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
                    self.assertTrue(linked.exists())
                    self.assertEqual(self._checkout_lease_files(state), [])
            for mode in ("advisory", "enforce"):
                for command in ("git-cli worktree remove --help",
                                "git-cli worktree remove -h"):
                    with self.subTest(mode=mode, command=command):
                        help_payload = dict(remove, tool_input={"command": command})
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", help_payload, cwd=primary,
                            env={"AGENT_RUNTIME_STATE_HOME": str(state),
                                 "AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_allowed(decision)
                        self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_removal_diagnostic_does_not_claim_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/diagnostic")
            state = root / "state"
            payload = self._checkout_lease_payload(
                "delivery", primary, tool_name="Bash",
                command=f"git-cli worktree remove {shlex.quote(str(linked))} --format json",
            )
            environment = dict(os.environ, AGENT_RUNTIME_STATE_HOME=str(state),
                               AGENT_SESSION_COORDINATION_MODE="advisory")
            environment.pop("AGENT_SESSION_ID", None)
            result = subprocess.run(
                [sys.executable, str(HOOK_DIR / "checkout-lease-guard.py"),
                 "diagnose-removal"], input=json.dumps(payload), cwd=primary,
                env=environment, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            diagnostic = json.loads(result.stdout)
            self.assertEqual(diagnostic["schema"], "agent-runtime.worktree-removal-attestation.v1")
            self.assertEqual(diagnostic["target"]["root"], str(linked.resolve()))
            self.assertFalse(diagnostic["guard_available"])
            self.assertFalse(diagnostic["execution_fenced"])
            self.assertFalse(diagnostic["cleanup_authorized"])
            self.assertFalse(diagnostic["owner_incarnation_verified"])
            self.assertEqual(diagnostic["disposition"], "retain")
            self.assertEqual(self._checkout_lease_files(state), [])
            self.assertFalse(state.exists())
            self.assertFalse((linked / ".git").is_dir())


    def test_checkout_lease_removal_delegates_dirty_owned_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/dirty")
            env = {"AGENT_RUNTIME_STATE_HOME": str(root / "state")}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("owner", linked / "README.md"),
                cwd=linked, env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            (linked / "pending.txt").write_text("retain this work\n", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "owner", primary, tool_name="Bash",
                    command=f"git-cli worktree remove {shlex.quote(str(linked))}",
                ), cwd=primary, env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual((linked / "pending.txt").read_text(), "retain this work\n")


    def test_checkout_lease_removal_diagnostic_reports_target_replacement(self) -> None:
        module = self._load("removal_diagnostic_drift", "checkout-lease-guard.py")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                primary = root / "primary"
                self._init_checkout_lease_repo(primary)
                linked = self._add_checkout_lease_worktree(primary, "feature/drift")
                payload = self._checkout_lease_payload(
                    "owner", primary, tool_name="Bash",
                    command=f"git-cli worktree remove {shlex.quote(str(linked))}",
                )
                payload["tool_input"]["cwd"] = str(primary)

                def replace_target(*args):
                    linked.rename(root / "retained-original")
                    linked.mkdir()
                    return None

                with mock.patch.dict(os.environ, {
                    "AGENT_RUNTIME_STATE_HOME": str(root / "state"),
                    "AGENT_SESSION_COORDINATION_MODE": "advisory",
                }), mock.patch.object(module, "load_lease", side_effect=replace_target):
                    result = module.diagnose_worktree_removal(payload)
                self.assertEqual(result["disposition"], "retain")
                self.assertFalse(result["target_stable"])
                self.assertFalse(result["execution_fenced"])
                self.assertIn("identity changed", result["reason"])
                self.assertTrue((root / "retained-original" / "README.md").exists())
                self.assertFalse((root / "state").exists())
        finally:
            sys.modules.pop("removal_diagnostic_drift", None)


    def test_checkout_lease_removal_refuses_wrong_scope_and_delegates_locked_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/protected")
            nested = linked / "nested"
            nested.mkdir()
            for target in (primary, nested):
                with self.subTest(target=target.name):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "owner", primary, tool_name="Bash",
                            command=f"git-cli worktree remove {shlex.quote(str(target))}",
                        ), cwd=primary,
                        env={"AGENT_RUNTIME_STATE_HOME": str(root / "state")},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "exact registered linked checkout root")
            subprocess.run(["git", "worktree", "lock", str(linked)],
                           cwd=primary, check=True)
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "owner", primary, tool_name="Bash",
                    command=f"git-cli worktree remove {shlex.quote(str(linked))}",
                ), cwd=primary,
                env={"AGENT_RUNTIME_STATE_HOME": str(root / "state")},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertTrue(linked.exists())


    def test_checkout_lease_bounded_managed_removal_and_foreign_refusal(self) -> None:
        # Actual released lifecycle execution is limited to reconstructible,
        # isolated fixture worktrees. The production runtime is never activated.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            environment = dict(os.environ, AGENT_HOME=str(root / "managed"))
            for key in ("AGENT_SESSION_ID", "AGENT_SESSION_STATE_DIR",
                        "AGENT_SESSION_RUNTIME_ID"):
                environment.pop(key, None)
            targets = []
            for slug in ("bounded-removal", "protected-removal"):
                added = subprocess.run(
                    ["git-cli", "worktree", "add", slug, "--kind", "bug", "--format", "json"],
                    cwd=primary, env=environment, text=True, capture_output=True,
                    check=True,
                )
                targets.append(Path(json.loads(added.stdout)["data"]["path"]))
            removable, protected = targets
            lease_env = {"AGENT_RUNTIME_STATE_HOME": str(root / "leases")}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", protected / "README.md"),
                cwd=protected, env=lease_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            for target, blocked in ((protected, True), (removable, False)):
                command = f"git-cli worktree remove {shlex.quote(str(target))} --format json"
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload("owner", primary, tool_name="Bash",
                                                 command=command),
                    cwd=primary, env=lease_env,
                )
                self.assertEqual(code, 0, stderr)
                if blocked:
                    self.assert_blocked(decision, "another agent session")
                    self.assertTrue(target.exists())
                else:
                    self.assert_allowed(decision)
                    removed = subprocess.run(
                        ["git-cli", "worktree", "remove", str(target), "--format", "json"],
                        cwd=primary, env=environment, text=True, capture_output=True,
                        check=False,
                    )
                    receipt = json.loads(removed.stdout)
                    if removed.returncode == 0:
                        self.assertTrue(receipt["ok"])
                        self.assertFalse(target.exists())
                    else:
                        # Older released CLIs still require complete registry,
                        # process and delivery proof. Hook admission must not
                        # bypass that owner or turn its refusal into success.
                        self.assertFalse(receipt["ok"])
                        self.assertEqual(receipt["error"]["code"], "removal-proof-unavailable", receipt)
                        self.assertTrue(target.exists())
                    self.assertTrue(protected.exists())
                    listed = subprocess.run(["git", "worktree", "list", "--porcelain"],
                                            cwd=primary, text=True, capture_output=True, check=True)
                    self.assertEqual(str(target) in listed.stdout, target.exists())
                    self.assertIn(str(protected), listed.stdout)


    def test_checkout_lease_worktree_remove_targets_the_foreign_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/remove", str(linked)],
                cwd=primary,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", linked / "README.md"),
                cwd=linked,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            remove = self._checkout_lease_payload(
                "delivery",
                primary,
                tool_name="Bash",
                command=f"git-cli worktree remove {shlex.quote(str(linked))} --format json",
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", remove, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")

            target = shlex.quote(str(linked))
            primary_arg = shlex.quote(str(primary))
            for command in (
                f"command -- git-cli worktree remove {target}",
                f"command -p git-cli worktree remove {target}",
                f"exec -- git-cli worktree remove {target}",
                f"exec -a managed git-cli worktree remove {target}",
                f"env - git-cli worktree remove {target}",
                f"env -uSOMETHING git-cli worktree remove {target}",
                f"/usr/bin/time -f %e git-cli worktree remove {target}",
                (
                    f"agent-run exec --cwd {primary_arg} "
                    f"git-cli worktree remove {target}"
                ),
                (
                    f"agent-run exec --cwd={primary_arg} --direnv off -- "
                    f"/usr/bin/time --format %e command -- "
                    f"git-cli worktree remove {target}"
                ),
            ):
                with self.subTest(command=command):
                    wrapped = self._checkout_lease_payload(
                        "delivery",
                        primary,
                        tool_name="Bash",
                        command=command,
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py", wrapped, cwd=primary, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "another agent session")

            for command in (
                f"! git-cli worktree remove {target}",
                f"if true; then git-cli worktree remove {target}; fi",
                (
                    "while true; do git-cli worktree remove "
                    f"{target}; break; done"
                ),
                (
                    "remove_target() { git-cli worktree remove "
                    f"{target}; }}; remove_target"
                ),
                (
                    "function remove_target { git-cli worktree remove "
                    f"{target}; }}; remove_target"
                ),
                (
                    "function remove_target() { git-cli worktree remove "
                    f"{target}; }}; remove_target"
                ),
            ):
                with self.subTest(command=command):
                    controlled = self._checkout_lease_payload(
                        "delivery",
                        primary,
                        tool_name="Bash",
                        command=command,
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py", controlled, cwd=primary, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "another agent session")

            unresolved_commands = [
                (
                    "CMD=git-cli env -S '${CMD} worktree remove "
                    f"{target}'"
                ),
                (
                    "export CMD=git-cli; env -S \"'${CMD}' worktree remove "
                    f"{target}\""
                ),
                (
                    "env -S \"'`printf git-cli`' worktree remove "
                    f"{target}\""
                ),
                f"env -S '# ignored' git-cli worktree remove {target}",
                f'CMD=git-cli; "$CMD" worktree remove {target}',
                f"`printf git-cli` worktree remove {target}",
                f"$(printf git-cli) worktree remove {target}",
                (
                    "bash -c "
                    + shlex.quote(
                        f'CMD=git-cli; "$CMD" worktree remove {target}'
                    )
                ),
            ]
            split_value = f"git-cli worktree remove {target}"
            for _ in range(5):
                split_value = f"-S {shlex.quote(split_value)}"
            unresolved_commands.append(f"env -S {shlex.quote(split_value)}")
            for command in unresolved_commands:
                with self.subTest(command=command):
                    wrapped = self._checkout_lease_payload(
                        "delivery",
                        primary,
                        tool_name="Bash",
                        command=command,
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py", wrapped, cwd=primary, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be verified")
                    self.assertIn("top-level `workdir`", str(decision))


    def test_checkout_lease_semantic_commit_repo_targets_the_target_checkout(
        self,
    ) -> None:
        # `semantic-commit --repo <path>` must evaluate the checkout-writer
        # lease on the *target* repository's checkout, not the session's current
        # working directory. This is what unblocks coupled cross-repo delivery
        # (issue #674): the session commits into a second repository's managed
        # worktree while its own cwd sits in a different repository.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_repo = root / "base"
            target_repo = root / "target"
            target_wt = root / "target-wt"
            state = root / "state"
            self._init_checkout_lease_repo(base_repo)
            self._init_checkout_lease_repo(target_repo)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feature/coupled",
                    str(target_wt),
                ],
                cwd=target_repo,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            commit = (
                "semantic-commit commit --repo "
                f"{shlex.quote(str(target_wt))} --message 'fix: coupled change'"
            )

            # A foreign session owns the target worktree's lease.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", target_wt / "README.md"),
                cwd=target_wt,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # The delivery session runs the repo-scoped commit from the base
            # repo, a clean primary checkout on its default branch. Base-eval
            # would admit it; target-eval blocks on the foreign owner.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "delivery", base_repo, tool_name="Bash", command=commit
                ),
                cwd=base_repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")

            # The harness command wrapper's redirects must not defeat target
            # recognition: the same foreign target still blocks when wrapped.
            wrapped = self._harness_wrapped(commit, str(root / "cwd-sentinel"))
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "delivery", base_repo, tool_name="Bash", command=wrapped
                ),
                cwd=base_repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")


    def test_checkout_lease_semantic_commit_repo_admits_target_owner(
        self,
    ) -> None:
        # The mirror direction: when the session owns the target worktree's
        # lease, the repo-scoped commit is admitted even though the session's
        # own cwd checkout is owned by a different session (base-eval would
        # block; target-eval admits).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_repo = root / "base"
            base_wt = root / "base-wt"
            target_repo = root / "target"
            target_wt = root / "target-wt"
            state = root / "state"
            self._init_checkout_lease_repo(base_repo)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/base", str(base_wt)],
                cwd=base_repo,
                check=True,
            )
            self._init_checkout_lease_repo(target_repo)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feature/coupled",
                    str(target_wt),
                ],
                cwd=target_repo,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            # A foreign session owns the base worktree (the session cwd).
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("other", base_wt / "README.md"),
                cwd=base_wt,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # The delivery session owns the target worktree (it edited there).
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("delivery", target_wt / "README.md"),
                cwd=target_wt,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            commit = (
                "semantic-commit commit --repo "
                f"{shlex.quote(str(target_wt))} --message 'fix: coupled change'"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "delivery", base_wt, tool_name="Bash", command=commit
                ),
                cwd=base_wt,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_checkout_lease_semantic_commit_rejects_relative_repo_after_cwd_change(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_repo = root / "base"
            static_target = base_repo / "target"
            effective_target = root / "target"
            state = root / "state"
            self._init_checkout_lease_repo(base_repo)
            self._init_checkout_lease_repo(static_target)
            self._init_checkout_lease_repo(effective_target)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            for session_id, target in (
                ("delivery", static_target),
                ("foreign", effective_target),
            ):
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload(
                        session_id, target / "README.md"
                    ),
                    cwd=target,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

            for command in (
                "cd .. && semantic-commit commit --repo target --message 'fix: x'",
                "env -C .. semantic-commit commit --repo target --message 'fix: x'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "delivery",
                            base_repo,
                            tool_name="Bash",
                            command=command,
                        ),
                        cwd=base_repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be verified")


    def test_checkout_lease_semantic_commit_repo_fails_closed_on_coresident(
        self,
    ) -> None:
        # A repo-scoped commit mixed with any other repository mutation fails
        # closed: honoring only the --repo target would leave the co-resident
        # mutation unleased.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_repo = root / "base"
            target_repo = root / "target"
            target_wt = root / "target-wt"
            state = root / "state"
            self._init_checkout_lease_repo(base_repo)
            self._init_checkout_lease_repo(target_repo)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feature/coupled",
                    str(target_wt),
                ],
                cwd=target_repo,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            target = shlex.quote(str(target_wt))
            for command in (
                (
                    f"semantic-commit commit --repo {target} --message 'fix: x' "
                    "&& git commit --amend --no-edit"
                ),
                (
                    f"semantic-commit commit --repo {target} --message 'fix: x' "
                    f"&& semantic-commit commit --repo {target} --message 'fix: y'"
                ),
            ):
                with self.subTest(command=command):
                    payload = self._checkout_lease_payload(
                        "delivery", base_repo, tool_name="Bash", command=command
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py", payload, cwd=base_repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be verified")


    def test_checkout_lease_semantic_commit_repo_target_edge_cases(self) -> None:
        # Guard the repo-scoped-commit target path across the parsing variants,
        # read-only forms, and fail-closed branches that its duplicated scaffold
        # inherits from the managed-worktree-removal template.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_repo = root / "base"
            target_repo = root / "target"
            target_wt = root / "target-wt"
            nonrepo = root / "nonrepo"
            state = root / "state"
            self._init_checkout_lease_repo(base_repo)
            self._init_checkout_lease_repo(target_repo)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feature/coupled",
                    str(target_wt),
                ],
                cwd=target_repo,
                check=True,
            )
            nonrepo.mkdir()
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            tgt = shlex.quote(str(target_wt))
            msg = shlex.quote("fix: coupled change")

            # A foreign session owns the target worktree's lease.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", target_wt / "README.md"),
                cwd=target_wt,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            def run(command: str):
                return run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload(
                        "delivery", base_repo, tool_name="Bash", command=command
                    ),
                    cwd=base_repo,
                    env=env,
                )

            # Read-only repo-scoped forms are not mutation targets: they fall back
            # to the admissible base cwd and are allowed; the foreign target is
            # ignored. --repo . collapses to the cwd checkout (same base path).
            for allowed in (
                f"semantic-commit commit --repo {tgt} --dry-run --message {msg}",
                f"semantic-commit commit --repo {tgt} --validate-only --message {msg}",
                f"semantic-commit commit --repo . --message {msg}",
            ):
                with self.subTest(allowed=allowed):
                    code, decision, stderr = run(allowed)
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            # The foreign target blocks across the attached --repo= form and the
            # fixup / squash mutating subcommands, not only `commit` space-form.
            for blocked in (
                f"semantic-commit commit --repo={target_wt} --message {msg}",
                f"semantic-commit fixup --repo {tgt} HEAD~1",
                f"semantic-commit squash --repo {tgt} HEAD~1",
            ):
                with self.subTest(blocked=blocked):
                    code, decision, stderr = run(blocked)
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "another agent session")

            # Fail-closed branches inherited from the removal scaffold plus the
            # self-sufficient target checks: a non-existent target, an existing
            # non-Git-checkout target, a dynamic command position, and a
            # self-redirect that writes into the target checkout.
            for closed in (
                f"semantic-commit commit --repo {shlex.quote(str(root / 'missing'))} --message {msg}",
                f"semantic-commit commit --repo {shlex.quote(str(nonrepo))} --message {msg}",
                f'CMD=semantic-commit; "$CMD" commit --repo {tgt} --message {msg}',
                f"semantic-commit commit --repo {tgt} --message {msg} > {shlex.quote(str(target_wt / 'out.txt'))}",
            ):
                with self.subTest(closed=closed):
                    code, decision, stderr = run(closed)
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be verified")


    def test_checkout_lease_harness_wrapped_read_only_ignores_foreign_lease(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            sentinel = str(root / "cwd-sentinel")
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("owner", repo / "README.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            wrapped_read = self._harness_wrapped("git status --short", sentinel)
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "reader", repo, tool_name="Bash", command=wrapped_read
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(len(self._checkout_lease_files(state)), 1)

            in_repo = shlex.quote(str(repo / "README.md"))
            wrapped_write = self._harness_wrapped(
                f"printf x > {in_repo}", sentinel
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "reader", repo, tool_name="Bash", command=wrapped_write
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")

            outside = root / "outside"
            outside.mkdir()
            outside_alias = outside / "alias.md"
            outside_alias.symlink_to(repo / "README.md")
            for redirect_target in (
                str(outside_alias),
                str(outside / "alia?.md"),
                str(outside / "alias.m{d..d}"),
            ):
                with self.subTest(redirect_target=redirect_target):
                    alias_write = f"printf x > {redirect_target}"
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "reader", repo, tool_name="Bash", command=alias_write
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "another agent session")


    def test_checkout_lease_extglob_redirect_alias_respects_foreign_lease(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            outside = root / "outside"
            self._init_checkout_lease_repo(repo)
            outside.mkdir()
            target = repo / "README.md"
            alias = outside / "alias.md"
            alias.symlink_to(target)
            original = target.read_text(encoding="utf-8")
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("owner", target),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            nested = f"printf x > {outside / 'alias.@(md)'}"
            command = f"bash -O extglob -c {shlex.quote(nested)}"
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "reader", repo, tool_name="Bash", command=command
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")
            self.assertEqual(target.read_text(encoding="utf-8"), original)


    def test_checkout_lease_worktree_remove_survives_harness_command_wrapper(
        self,
    ) -> None:
        # Regression for issue #628: `git-cli worktree remove` must survive the
        # agent Bash tool's command wrapper. Pre-fix the trailing `< /dev/null`
        # was read as a second target ("multiple targets") and the wrapper's
        # `2>/dev/null` / `pwd >| <cwd>` tripped the sole-mutation guard. The
        # removal must instead reach lease evaluation, while a genuine
        # co-resident repository write is still rejected.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            sentinel = str(root / "cwd-sentinel")  # absolute, outside every checkout
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/wrap", str(linked)],
                cwd=primary,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            # A foreign session owns the linked checkout's lease.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", linked / "README.md"),
                cwd=linked,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            target = shlex.quote(str(linked))
            wrapped = self._harness_wrapped(
                f"git-cli worktree remove {target}", sentinel
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "delivery", primary, tool_name="Bash", command=wrapped
                ),
                cwd=primary,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            # Reached lease evaluation (foreign owner), not a parse/scope refusal.
            self.assert_blocked(decision, "another agent session")

            # Genuine co-resident repository writes are still rejected, even
            # inside the wrapper: raw deletion, an
            # absolute in-repo redirect, a relative redirect (unsafe under `cd`,
            # so fail closed), and a dynamic redirect target.
            in_repo = shlex.quote(str(primary / "README.md"))
            for co_resident in (
                f"rm -rf {in_repo}",
                f"printf x > {in_repo}",
                "cd .git && printf x > ../pwned",
                "echo x > $OUT",
            ):
                with self.subTest(co_resident=co_resident):
                    with_write = self._harness_wrapped(
                        f"git-cli worktree remove {target} && {co_resident}", sentinel
                    )
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "delivery", primary, tool_name="Bash", command=with_write
                        ),
                        cwd=primary,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    expected_reason = (
                        "Raw deletion changes directory context"
                        if co_resident.startswith("rm ")
                        else "sole mutating command"
                    )
                    self.assert_blocked(decision, expected_reason)


    def test_checkout_lease_worktree_add_survives_harness_command_wrapper(
        self,
    ) -> None:
        # Regression: the issue #622 `git-cli worktree add` carve-out must also
        # survive the agent Bash tool wrapper. Without redirect scoping the
        # wrapper's `2>/dev/null` defeated the carve-out, so a non-default primary
        # checkout still deadlocked in the live environment.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            sentinel = str(root / "cwd-sentinel")
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "switch", "-q", "-c", "feature/wrap-add"],
                cwd=repo,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            wrapped_add = self._harness_wrapped(
                "git-cli worktree add feature-lane", sentinel
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "writer", repo, tool_name="Bash", command=wrapped_add
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_worktree_remove_slug_targets_the_foreign_lease(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/slug", str(linked)],
                cwd=primary,
                check=True,
            )
            (primary / "linked").mkdir()
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", linked / "README.md"),
                cwd=linked,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            remove = self._checkout_lease_payload(
                "delivery",
                primary,
                tool_name="Bash",
                command="git-cli worktree remove linked --format json",
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", remove, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")


    def test_checkout_lease_detects_nested_checkout_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outer = root / "outer"
            nested = outer / "nested"
            state = root / "state"
            self._init_checkout_lease_repo(outer)
            (outer / ".git" / "info" / "exclude").write_text(
                "nested/\n", encoding="utf-8"
            )
            self._init_checkout_lease_repo(nested)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", nested / "README.md"),
                cwd=nested,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            multi = {
                "session_id": "outer-writer",
                "hook_event_name": "PreToolUse",
                "tool_name": "MultiEdit",
                "cwd": str(outer),
                "tool_input": {
                    "edits": [
                        {"file_path": str(outer / "README.md")},
                        {"file_path": str(nested / "README.md")},
                    ]
                },
            }
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", multi, cwd=outer, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "spans multiple checkouts")
            self.assertEqual(len(self._checkout_lease_files(state)), 1)

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "outer-writer", nested / "README.md"
                ),
                cwd=outer,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")


    def test_checkout_lease_fails_closed_on_broken_nested_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outer = root / "outer"
            broken = outer / "broken"
            state = root / "state"
            self._init_checkout_lease_repo(outer)
            (outer / ".git" / "info" / "exclude").write_text(
                "broken/\n", encoding="utf-8"
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", outer / "README.md"),
                cwd=outer,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            broken.mkdir()
            (broken / ".git").write_text(
                "gitdir: /definitely/missing/gitdir\n", encoding="utf-8"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "other", broken / "generated.txt"
                ),
                cwd=outer,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "fails closed")


    def test_checkout_lease_rejects_compound_worktree_removal_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feature/compound",
                    str(linked),
                ],
                cwd=primary,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", primary / "README.md"),
                cwd=primary,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            remove = self._checkout_lease_payload(
                "delivery",
                primary,
                tool_name="Bash",
                command=(
                    "git-cli worktree remove linked --format json; "
                    "touch collision.txt"
                ),
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", remove, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "sole mutating command")
            self.assertEqual(len(self._checkout_lease_files(state)), 1)


    def test_checkout_lease_worktree_remove_parses_option_before_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            json_worktree = root / "json"
            victim = root / "victim"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            for branch, path in (
                ("feature/json", json_worktree),
                ("feature/victim", victim),
            ):
                subprocess.run(
                    ["git", "worktree", "add", "-q", "-b", branch, str(path)],
                    cwd=primary,
                    check=True,
                )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", victim / "README.md"),
                cwd=victim,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            remove = self._checkout_lease_payload(
                "delivery",
                primary,
                tool_name="Bash",
                command="git-cli worktree remove --format json victim",
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", remove, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "another agent session")
            self.assertEqual(len(self._checkout_lease_files(state)), 1)


    def test_checkout_lease_rejects_multiple_worktree_removals_before_claim(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            available = root / "a-available"
            foreign = root / "z-foreign"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            for branch, path in (
                ("feature/available", available),
                ("feature/foreign", foreign),
            ):
                subprocess.run(
                    ["git", "worktree", "add", "-q", "-b", branch, str(path)],
                    cwd=primary,
                    check=True,
                )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("foreign", foreign / "README.md"),
                cwd=foreign,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            remove = self._checkout_lease_payload(
                "delivery",
                primary,
                tool_name="Bash",
                command=(
                    "git-cli worktree remove a-available --format json; "
                    "git-cli worktree remove z-foreign --format json"
                ),
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", remove, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "exactly one")
            self.assertEqual(len(self._checkout_lease_files(state)), 1)


    def test_checkout_lease_stop_releases_clean_failed_removal_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            linked = root / "linked"
            state = root / "state"
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "feature/fail", str(linked)],
                cwd=primary,
                check=True,
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            # Removal delegates without claiming a lease; a lease already
            # owned by the caller remains eligible for the normal Stop release.
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload("delivery", linked / "README.md"),
                cwd=linked, env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            remove = self._checkout_lease_payload(
                "delivery",
                primary,
                tool_name="Bash",
                command=f"git-cli worktree remove {shlex.quote(str(linked))}",
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", remove, cwd=primary, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(len(self._checkout_lease_files(state)), 1)

            code, audit, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {"session_id": "delivery", "hook_event_name": "Stop"},
                cwd=primary,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(audit)
            assert audit is not None
            self.assertIn("released", str(audit.get("systemMessage", "")))
            self.assertEqual(self._checkout_lease_files(state), [])
            self.assertTrue(linked.is_dir())


    def test_checkout_lease_allows_only_ref_safe_mutations_on_untracked_dirty_checkout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            fake_git = root / "shadow" / "git"
            fake_git.parent.mkdir()
            fake_git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_git.chmod(0o755)
            (repo / "browser-test-junk.log").write_text(
                "untracked output\n", encoding="utf-8"
            )
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}

            for command in (
                "git branch -d merged-topic",
                "git branch -D merged-topic",
                "git branch -m old-topic new-topic",
                "git branch -M old-topic new-topic",
                "git branch -c old-topic copied-topic",
                "git branch -C old-topic copied-topic",
                "git tag --no-sign v1.2.3",
                "git tag -d v1.2.3",
                "bash -c 'git branch -D merged-topic'",
            ):
                with self.subTest(admitted=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "ref-maintenance-session",
                            repo,
                            tool_name="Bash",
                            command=command,
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command in (
                "git branch topic",
                "git branch --edit-description topic",
                "git branch --set-upstream-to=origin/main topic",
                "git update-ref refs/heads/topic HEAD",
                'git "$OP" branch -D merged-topic',
                'git branch "$MODE" merged-topic',
                "git -C .. branch -D merged-topic",
                "git tag -a v1.2.3 -m release",
                "git tag v1.2.3",
                f"{shlex.quote(str(fake_git))} branch -D merged-topic",
                "PATH=/untrusted git branch -D merged-topic",
                "git reset --soft HEAD^",
                "git branch -D merged-topic && git tag v1.2.3",
                "git branch -D merged-topic && touch README.md",
                "git branch -D merged-topic > README.md",
                "git tag v1.2.3 && git add README.md",
                "rm browser-test-junk.log",
            ):
                with self.subTest(rejected=command):
                    code, decision, stderr = run_enforced_hook(
                        "checkout-lease-guard.py",
                        self._checkout_lease_payload(
                            "ref-maintenance-session",
                            repo,
                            tool_name="Bash",
                            command=command,
                        ),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "unowned changes")

            self.assertEqual(self._checkout_lease_files(state), [])


    def test_checkout_lease_ref_safe_exception_rejects_reference_transaction_hook(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            (repo / "untracked.log").write_text("unowned\n", encoding="utf-8")
            hook = repo / ".git" / "hooks" / "reference-transaction"
            hook.write_text(
                "#!/bin/sh\nprintf side-effect > checkout-hook-output.txt\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "ref-session",
                    repo,
                    tool_name="Bash",
                    command="git branch -D merged-topic",
                ),
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "reference-transaction hook")
            self.assertFalse((repo / "checkout-hook-output.txt").exists())


    def test_checkout_lease_ref_safe_exception_honors_custom_hooks_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            hooks = root / "custom-hooks"
            self._init_checkout_lease_repo(repo)
            hooks.mkdir()
            subprocess.run(
                ["git", "config", "core.hooksPath", str(hooks)],
                cwd=repo,
                check=True,
            )
            (repo / "untracked.log").write_text("unowned\n", encoding="utf-8")
            hook = hooks / "reference-transaction"
            hook.write_text(
                "#!/bin/sh\nprintf side-effect > checkout-hook-output.txt\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "ref-session",
                    repo,
                    tool_name="Bash",
                    command="git branch -D merged-topic",
                ),
                cwd=repo,
                env={"AGENT_RUNTIME_STATE_HOME": str(state)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "reference-transaction hook")
            self.assertFalse((repo / "checkout-hook-output.txt").exists())


    def test_checkout_lease_ref_safe_dirty_exception_remains_session_bound(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
            (repo / "untracked.log").write_text("unowned\n", encoding="utf-8")
            payload = self._checkout_lease_payload(
                "ref-session",
                repo,
                tool_name="Bash",
                command="git branch -D merged-topic",
            )
            payload.pop("session_id")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "verifiable agent session")
            self.assertEqual(self._checkout_lease_files(state), [])

        for expired, fragment in (
            (False, "another agent session"),
            (True, "unowned changes"),
        ):
            with self.subTest(expired=expired), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                state = root / "state"
                self._init_checkout_lease_repo(repo)
                env = {"AGENT_RUNTIME_STATE_HOME": str(state)}
                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload("owner", repo / "README.md"),
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
                lease_file = self._checkout_lease_files(state)[0]
                original_lease = json.loads(
                    lease_file.read_text(encoding="utf-8")
                )
                if expired:
                    original_lease["expires_at"] = 0
                    lease_file.write_text(
                        json.dumps(original_lease) + "\n", encoding="utf-8"
                    )
                (repo / "untracked.log").write_text(
                    "unowned\n", encoding="utf-8"
                )

                code, decision, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    self._checkout_lease_payload(
                        "other",
                        repo,
                        tool_name="Bash",
                        command="git branch -D merged-topic",
                    ),
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)
                retained = json.loads(lease_file.read_text(encoding="utf-8"))
                self.assertEqual(retained["session_key"], original_lease["session_key"])

