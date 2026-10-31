"""Shared hook tests: artifact routing."""
from __future__ import annotations

from shared_hook_helpers import (
    Any,
    HookTestCase,
    Path,
    command_payload,
    run_hook,
    tempfile,
)


class ArtifactRoutingTests(HookTestCase):

    def test_artifact_routing_is_not_waived_by_the_portable_paths_hatch(self) -> None:
        """`SKIP_PORTABLE_PATH_SCAN` waives portable paths, not artifact routing.

        The two checks share a process for budget reasons only. An escape hatch
        documented for portable-path false positives must not silently switch
        off a guard it was never meant to cover.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            env = {"SKIP_PORTABLE_PATH_SCAN": "1"}

            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                command_payload("echo notes > agent-out/progress.md"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "agent-out")

            # The hatch still does what it exists for.
            code, decision, stderr = run_hook(
                "portable-paths-scan.py",
                command_payload(
                    "printf '/Users/example/project\\n' > docs/example.md"
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_artifact_routing_allows_existing_tracked_source_in_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_tracked_worktree(tmp)
            target = "crates/agent-out/tests/integration/retention.rs"
            payloads = (
                {"tool_name": "Write", "tool_input": {"file_path": target}},
                {"tool_name": "Edit", "tool_input": {"file_path": target}},
                {"tool_name": "MultiEdit",
                 "tool_input": {"file_path": target, "edits": []}},
                {"tool_name": "apply_patch", "tool_input": {"input": (
                    "*** Begin Patch\n"
                    f"*** Update File: {target}\n"
                    "@@\n-tracked fixture\n+changed fixture\n*** End Patch\n"
                )}},
                command_payload(f"echo changed > {target}"),
            )
            self.assertTrue((repo / ".git").is_file())
            for payload in payloads:
                with self.subTest(tool=payload["tool_name"]):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK, payload, cwd=repo)
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                {"tool_name": "Edit",
                 "tool_input": {"file_path": "tests/integration/retention.rs"}},
                cwd=repo / "crates" / "agent-out")
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_artifact_routing_allows_new_source_in_tracked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_tracked_worktree(tmp)
            for target in (
                "crates/agent-out/src/new_module.rs",
                "crates/agent-out/tests/integration/new.rs",
            ):
                self.assertFalse((repo / target).exists())
                payloads = (
                    {"tool_name": "Write", "tool_input": {"file_path": target}},
                    {"tool_name": "apply_patch", "tool_input": {"input": (
                        "*** Begin Patch\n"
                        f"*** Add File: {target}\n"
                        "+source fixture\n*** End Patch\n"
                    )}},
                    command_payload(f"echo source > {target}"),
                    command_payload(f"touch {target}"),
                )
                for payload in payloads:
                    with self.subTest(target=target, tool=payload["tool_name"]):
                        code, decision, stderr = run_hook(
                            self.ARTIFACT_ROUTING_HOOK, payload, cwd=repo)
                        self.assertEqual(code, 0, stderr)
                        self.assert_allowed(decision)
                # A new source remains editable before it is staged.
                (repo / target).write_text("source fixture\n", encoding="utf-8")
                code, decision, stderr = run_hook(
                    self.ARTIFACT_ROUTING_HOOK,
                    {"tool_name": "Edit", "tool_input": {"file_path": target}},
                    cwd=repo)
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_artifact_routing_tracked_source_does_not_allow_scratch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_tracked_worktree(tmp)
            (repo / "crates/agent-out/scratch").mkdir()
            (repo / "crates/agent-out/src/.gitignore").write_text(
                "ignored.rs\n", encoding="utf-8")
            payloads = (
                {"tool_name": "Write", "tool_input": {
                    "file_path": "crates/agent-out/tests/integration/retention?.rs"}},
                command_payload("mkdir -p crates/agent-out/scratch/new"),
                command_payload("mkdir -p crates/agent-out/src/scratch"),
                {"tool_name": "Write", "tool_input": {
                    "file_path": "crates/agent-out/scratch/notes.md"}},
                {"tool_name": "Write", "tool_input": {
                    "file_path": "crates/agent-out/src/ignored.rs"}},
                {"tool_name": "Edit", "tool_input": {
                    "file_path": "agent-out/tracked-scratch.md"}},
                {"tool_name": "Edit", "tool_input": {
                    "file_path": ".cache/agent-out/tracked-scratch.md"}},
            )
            for payload in payloads:
                with self.subTest(payload=payload):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK, payload, cwd=repo)
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "agent-out")


    def test_artifact_routing_tracked_source_does_not_allow_symlink_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_tracked_worktree(tmp)
            source = repo / "crates" / "agent-out"
            (repo / "notes").symlink_to(source, target_is_directory=True)
            (source / "alias.rs").symlink_to(source / "tests/integration/retention.rs")
            for target in (
                "notes/tests/integration/retention.rs",
                "crates/agent-out/alias.rs",
                "notes/tests/integration/new.rs",
            ):
                with self.subTest(target=target):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        {"tool_name": "Edit", "tool_input": {"file_path": target}},
                        cwd=repo)
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "agent-out")


    def test_artifact_routing_tracked_source_does_not_allow_internal_root_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_tracked_worktree(tmp)
            (repo / "alias").symlink_to(".", target_is_directory=True)
            for target in (
                "alias/crates/agent-out/tests/integration/retention.rs",
                "alias/alias/crates/agent-out/tests/integration/retention.rs",
            ):
                with self.subTest(target=target):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        {"tool_name": "Edit", "tool_input": {"file_path": target}},
                        cwd=repo)
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "agent-out")


    def test_artifact_routing_allows_external_checkout_root_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_tracked_worktree(tmp)
            alias = Path(tmp) / "checkout-alias"
            alias.symlink_to(repo, target_is_directory=True)
            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                {"tool_name": "Edit", "tool_input": {"file_path": str(
                    alias / "crates/agent-out/tests/integration/retention.rs")}},
                cwd=repo)
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_artifact_routing_blocks_repo_local_agent_out_bash_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for command in (
                "echo notes > agent-out/progress.md",
                "cat > agent-out/progress.md <<'EOF'\nnotes\nEOF",
                "mkdir -p agent-out/topic && cp /tmp/source agent-out/topic",
                "cp /tmp/source agent-out/",
                "cd agent-out && echo notes > progress.md",
                # The directory itself is the leak. These create it without
                # writing content, so a content-write-only guard misses them
                # while the block message still promises to stop them.
                "mkdir agent-out",
                "mkdir -p agent-out/topic",
                "touch agent-out/progress.md",
                "cd agent-out && touch progress.md",
                "mkdir -p build && mkdir -p agent-out",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "agent-out")


    def test_artifact_routing_blocks_every_known_wrong_agent_out_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for path in (
                "/home/example/.local/state/agent-runtime-kit/agent-out/topic/x.json",
                "~/agent-out/x.txt",
                "/home/example/.local/state/agent-out/x.txt",
                str(repo / "agent-out" / "x.txt"),
            ):
                with self.subTest(path=path):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        {"tool_name": "Write", "tool_input": {"file_path": path}},
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "agent-out")


    def test_artifact_routing_covers_every_registered_matcher_payload(self) -> None:
        """Each registered matcher carries the path in its own payload shape.

        The rule registers Bash, Write/Edit/NotebookEdit, apply_patch, and
        MultiEdit. Registering a matcher whose payload the handler cannot read
        is a rule that silently does nothing, so every shape gets an assertion
        rather than only the two that happen to share `file_path`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            target = "agent-out/leaked.md"
            payloads: tuple[dict[str, Any], ...] = (
                {"tool_name": "Write", "tool_input": {"file_path": target}},
                {"tool_name": "Edit", "tool_input": {"file_path": target}},
                {
                    "tool_name": "MultiEdit",
                    "tool_input": {"file_path": target, "edits": []},
                },
                {
                    "tool_name": "NotebookEdit",
                    "tool_input": {"notebook_path": "agent-out/leaked.ipynb"},
                },
                {
                    "tool_name": "apply_patch",
                    "tool_input": {
                        "input": (
                            "*** Begin Patch\n"
                            f"*** Add File: {target}\n"
                            "+leaked\n"
                            "*** End Patch\n"
                        )
                    },
                },
            )
            for payload in payloads:
                with self.subTest(tool=payload["tool_name"]):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK, payload, cwd=repo
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "agent-out")


    def test_artifact_routing_follows_symlinks_into_the_guarded_tree(self) -> None:
        """A lexical check alone reads the name, not the destination.

        Two distinct failures, both real: an alias whose name is innocent but
        which resolves into `agent-out`, and a checkout reached through a
        symlink, where `git rev-parse --show-toplevel` reports the physical
        root while the workdir is logical -- so the `.cache` comparison would
        fail to relate two spellings of one directory and stop enforcing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            (repo / "agent-out").mkdir()
            (repo / "notes").symlink_to(repo / "agent-out")

            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(repo / "notes" / "leaked.md")},
                },
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "agent-out")

            alias = Path(tmp) / "alias"
            alias.symlink_to(repo)
            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                command_payload("echo scratch > .cache/i62.txt"),
                cwd=alias,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, ".cache")

            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                command_payload("touch .cache/agent-validation/project-dev.ok"),
                cwd=alias,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_artifact_routing_names_the_allocation_command_in_the_block(self) -> None:
        """A block must tell the agent the exact route, not just the rule.

        Issue #90: the recurrence cause was an agent that knew a directory name
        but not the command that owns it. The message also has to close off the
        adjacent wrong answer -- hand-building `$AGENT_HOME/out/<topic>`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                command_payload("echo notes > agent-out/progress.md"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            reason = str(decision.get("reason", ""))
            self.assertIn("agent-out project --topic", reason)
            self.assertIn("--mkdir", reason)
            self.assertIn("out/projects/", reason)
            self.assertIn("Do not hand-build", reason)
            self.assertIn("core/policies/files-hooks-validation.md", reason)
            # The retired `$AGENT_HOME` anchor must not come back through a
            # block message; audit-drift's agent-home-leak class owns this.
            self.assertNotIn("$AGENT_HOME", reason)


    def test_artifact_routing_allows_canonical_allocated_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for path in (
                "/home/example/.local/state/agent-runtime-kit/out/projects/"
                "sympoies__agent-runtime-kit/20260902-195921-topic/notes.md",
                # `agent-out` as a filename fragment is not a path segment.
                "/home/example/.local/state/agent-runtime-kit/out/agent-out-plan.json",
                "core/hooks/shared/portable-paths-scan.py",
            ):
                with self.subTest(path=path):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        {"tool_name": "Write", "tool_input": {"file_path": path}},
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_artifact_routing_blocks_repo_local_cache_scratch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for command in (
                "echo scratch > .cache/i62.txt",
                "cd .cache && echo scratch > i62.txt",
                "cp /tmp/source .cache/tmp",
                "mkdir -p .cache/scratch",
                "touch .cache/i62.txt",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, ".cache")

            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(repo / ".cache" / "scratch.txt")},
                },
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, ".cache")


    def test_artifact_routing_allows_the_agent_validation_marker_subtree(self) -> None:
        """`.cache/agent-validation/` is the declared validation marker root.

        `VALIDATION.toml` owns it (`marker = ".cache/agent-validation/*.ok"`),
        the finish-line gate reads it, and it is legitimately repo-local.
        Blocking it would break the validation contract it exists to record.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for command in (
                "touch .cache/agent-validation/project-dev.ok",
                "echo x > .cache/agent-validation/session-abc/project-dev.dirty",
                "mkdir -p .cache/agent-validation/session-abc",
                # The container itself. Blocking its creation while allowing
                # the marker beneath it would be incoherent, and the documented
                # bootstrap creates both levels at once.
                "mkdir -p .cache",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_artifact_routing_leaves_non_repo_cache_paths_alone(self) -> None:
        """The XDG cache is not a checkout; only repo-local `.cache/` is scoped."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for path in ("~/.cache/pip/wheel", "/home/example/.cache/whatever"):
                with self.subTest(path=path):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        {"tool_name": "Write", "tool_input": {"file_path": path}},
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_artifact_routing_cache_rule_needs_a_repo_to_scope_against(self) -> None:
        """Outside a checkout there is no repo-local `.cache` to protect."""
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            (plain / ".cache").mkdir(parents=True)
            code, decision, stderr = run_hook(
                self.ARTIFACT_ROUTING_HOOK,
                command_payload("echo scratch > .cache/i62.txt"),
                cwd=plain,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_artifact_routing_ignores_read_only_and_unrelated_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)
            for command in (
                "ls agent-out",
                "cat agent-out/progress.md",
                "agent-out project --topic release-notes --mkdir",
                "grep -rn agent-out core/policies",
                "printf '%s\\n' 'agent-out/progress.md'",
                # Ordinary creation must stay allowed: the guard owns one
                # directory name, not directory creation in general.
                "mkdir -p build",
                "touch README.md",
                "mkdir -p ~/.cache/foo",
                "mkdir -p node_modules/.cache",
                # `-r` takes a value, so an `agent-out` reference file is a
                # flag argument, not a creation target. This is the assertion
                # that catches a flag-parsing regression turning one into the
                # other.
                "touch -r agent-out/ref.md notes.md",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        self.ARTIFACT_ROUTING_HOOK,
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

