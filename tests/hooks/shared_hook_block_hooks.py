"""Shared hook tests: block hooks."""
from __future__ import annotations

from shared_hook_helpers import (
    HookTestCase,
    Path,
    command_payload,
    run_hook,
    shlex,
    tempfile,
)


class BlockHooksTests(HookTestCase):

    def test_block_hooks_descend_into_nested_shell_wrappers(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "bash -c 'git commit -m test'",
                "semantic-commit",
            ),
            (
                "block-direct-git-commit.py",
                "eval 'git commit -m test'",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "sh -c 'git worktree add ../repo-topic'",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "bash -lc 'gh pr create --draft'",
                "forge-cli",
            ),
            (
                "block-direct-git-commit.py",
                "cat <(git commit -m test)",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "cat <(git worktree add ../repo-topic)",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "diff <(gh pr create --draft) /dev/null",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("bash -c 'python -m pytest'", workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_parse_combined_wrapper_options(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "/usr/bin/time -af %e git commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "/usr/bin/time -pvo /dev/null git worktree remove ../victim",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "exec -ca renamed gh pr create --draft",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("exec -aname python -m pytest", workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_ignore_inert_heredoc_prose(self) -> None:
        # A quoted-delimiter here-doc body is data with no expansion at all;
        # prose that merely mentions command-like words must not trip the
        # command classifiers (it blocked commit-message heredocs in practice).
        inert_prose = (
            "cat > /tmp/notes.txt <<'EOF'\n"
            "- a bare `env python3` resolved to the Apple CLT interpreter; the\n"
            "  dispatcher then reported capability-failure-closed and denied\n"
            "  all mutations, e.g. git commit -m test never ran.\n"
            "EOF\n"
            "echo done"
        )
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload(inert_prose)
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(inert_prose, workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

        # An unquoted delimiter expands only its substitutions; fed to a data
        # consumer, the rest of the body is data as well (issue #206).
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload("cat <<EOF\ngit commit -m test $HOME\nEOF"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        # The conservative bias is preserved where real ambiguity exists: a
        # shell-executor body is script text, a substitution in an expanding
        # body runs, and a body for an unknown command or one whose output
        # feeds a pipe stays visible to the guards.
        for visible in (
            "bash <<'EOF'\ngit commit -m test\nEOF",
            "cat <<EOF\n$(git commit -m test)\nEOF",
            "runner <<EOF\ngit commit -m test\nEOF",
            "cat <<EOF | bash\ngit commit -m test\nEOF",
        ):
            with self.subTest(command=visible):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(visible)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "semantic-commit")


    def test_block_hooks_fail_closed_on_opaque_wrapper_candidates(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "/usr/bin/time --future-option git commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "exec --future-option git worktree remove ../victim",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "agent-run exec --future-option gh pr create --draft",
                "forge-cli",
            ),
            (
                "block-direct-git-commit.py",
                "/usr/bin/time --future-option env -S 'git commit -m test'",
                "semantic-commit",
            ),
            (
                "block-direct-pr-create.py",
                "agent-run exec --future-option bash -c 'gh pr create --draft'",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        opaque_nested = "git commit -m test"
        for _ in range(6):
            opaque_nested = f"bash -c {shlex.quote(opaque_nested)}"
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload(f"/usr/bin/time --future-option {opaque_nested}"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "rule=opaque-executable")

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("command --future-option python -m pytest", workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_parse_gnu_time_values_and_unique_abbreviations(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "/usr/bin/time -fV git commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "/usr/bin/time -pvoV git worktree remove ../victim",
                "git-cli worktree",
            ),
            (
                "block-direct-git-commit.py",
                "/usr/bin/time --fo=V env -S 'git commit -m test'",
                "semantic-commit",
            ),
            (
                "block-direct-pr-create.py",
                "/usr/bin/time --fo=V bash -c 'gh pr create --draft'",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(
                    "/usr/bin/time --fo=V agent-run exec --cwd . -- "
                    "command -- python -m pytest",
                    workdir=str(repo),
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_parse_gnu_env_lone_dash_and_attached_values(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "env - git commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-commit.py",
                "env -uSOMETHING git commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "env -iuSOMETHING git worktree remove ../victim",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "env - gh pr create --draft",
                "forge-cli",
            ),
            (
                "block-direct-git-commit.py",
                "env --block-signal=PIPE git commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "env --default-signal git worktree remove ../victim",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "env --ignore-signal=PIPE gh pr create --draft",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            for command in (
                "env -uSOMETHING python -m pytest",
                "env --debug python -m pytest",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-python.py",
                        command_payload(command, workdir=str(repo)),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_fail_closed_at_nested_shell_depth_limit(self) -> None:
        def nested(command: str) -> str:
            for _ in range(6):
                command = f"bash -c {shlex.quote(command)}"
            return command

        cases = (
            (
                "block-direct-git-commit.py",
                nested("git commit -m test"),
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-worktree.py",
                nested("git worktree remove ../victim"),
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                nested("gh pr create --draft"),
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        read_only = "git status --short"
        for _ in range(5):
            read_only = f"bash -c {shlex.quote(read_only)}"
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload(read_only)
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(nested("python -m pytest"), workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_fail_closed_at_env_split_depth_limit(self) -> None:
        def nested(command: str) -> str:
            split_value = command
            for _ in range(5):
                split_value = f"-S {shlex.quote(split_value)}"
            return f"env -S {shlex.quote(split_value)}"

        cases = (
            (
                "block-direct-git-commit.py",
                nested("git commit -m test"),
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-worktree.py",
                nested("git worktree remove ../victim"),
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                nested("gh pr create --draft"),
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(nested("python -m pytest"), workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_fail_closed_on_env_split_variable_expansion(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "CMD=git env -S '${CMD} commit -m test'",
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-commit.py",
                "CMD=git env -S '\"${CMD}\" commit -m test'",
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-commit.py",
                "export CMD=git; env -S \"'${CMD}' commit -m test\"",
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-commit.py",
                "env -S \"'`printf git`' commit -m test\"",
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-worktree.py",
                "CMD=git env -S '${CMD} worktree remove ../victim'",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "CMD=gh env -S '${CMD} pr create --draft'",
                "forge-cli",
            ),
            (
                "block-direct-git-worktree.py",
                "export CMD=git; env -S \"'${CMD}' worktree remove ../victim\"",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "export CMD=gh; env -S \"'${CMD}' pr create --draft\"",
                "forge-cli",
            ),
            (
                "block-direct-git-worktree.py",
                "env -S \"'`printf git`' worktree remove ../victim\"",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "env -S \"'`printf gh`' pr create --draft\"",
                "forge-cli",
            ),
            (
                "block-direct-git-commit.py",
                "env -S '# ignored' git commit -m test",
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-worktree.py",
                "env -S '# ignored' git worktree remove ../victim",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "env -S '# ignored' gh pr create --draft",
                "forge-cli",
            ),
            (
                "block-direct-git-commit.py",
                "env -S 'git\\_commit -m test'",
                "rule=opaque-executable",
            ),
            (
                "block-direct-git-worktree.py",
                "env -S 'git\\_worktree remove ../victim'",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "env -S 'gh\\_pr create --draft'",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(
                    "CMD=python env -S '${CMD} -m pytest'", workdir=str(repo)
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")

            for command in (
                "export CMD=python; env -S \"'${CMD}' -m pytest\"",
                "env -S \"'`printf python`' -m pytest\"",
                "env -S '# ignored' python -m pytest",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-python.py",
                        command_payload(command, workdir=str(repo)),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "uv run --locked python")

            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("env -S 'python\\_-m pytest'", workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_block_hooks_allow_legitimate_nested_shell_commands(self) -> None:
        cases = (
            ("block-direct-git-commit.py", "bash -c 'git status'"),
            ("block-direct-git-worktree.py", "bash -c 'git worktree list'"),
            ("block-direct-pr-create.py", "sh -c 'forge-cli pr view 123'"),
            ("block-direct-git-commit.py", "/usr/bin/time --future-option printf ok"),
            ("block-direct-git-worktree.py", "exec --future-option printf ok"),
            ("block-direct-pr-create.py", "agent-run exec --future-option printf ok"),
            ("block-direct-git-commit.py", "env if git commit -m test"),
            ("block-direct-git-worktree.py", "env then git worktree remove ../victim"),
            ("block-direct-pr-create.py", "env do gh pr create --draft"),
            ("block-direct-git-commit.py", "env -S 'printf foo#bar'"),
            ("block-direct-git-worktree.py", "env -S 'printf foo#bar'"),
            ("block-direct-pr-create.py", "env -S 'printf foo#bar'"),
            ("block-direct-git-commit.py", "env -S 'printf foo\u00a0#bar'"),
            ("block-direct-git-worktree.py", "env -S 'printf foo\u00a0#bar'"),
            ("block-direct-pr-create.py", "env -S 'printf foo\u00a0#bar'"),
        )
        for hook, command in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(
                    "bash -c 'uv run --locked python -m pytest'",
                    workdir=str(repo),
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_block_hooks_handle_env_wrappers_and_shell_terminators(self) -> None:
        cases = (
            (
                "block-direct-git-commit.py",
                "env -S 'git commit -m test'",
                "semantic-commit",
            ),
            (
                "block-direct-pr-create.py",
                "env -S 'gh pr create --draft'",
                "forge-cli",
            ),
            (
                "block-direct-git-worktree.py",
                "env -C /tmp git worktree add ../repo-topic",
                "git-cli worktree",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("env -S 'python -m pytest'", workdir=str(repo)),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")

        allowed_shell_terminator_cases = (
            ("block-direct-git-commit.py", "bash -- -c 'git commit -m test'"),
            ("block-direct-pr-create.py", "sh -- -c 'gh pr create --draft'"),
            ("block-direct-git-commit.py", "bash --command 'git commit -m test'"),
        )
        for hook, command in allowed_shell_terminator_cases:
            with self.subTest(hook=hook, command=command):
                code, decision, stderr = run_hook(
                    hook,
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_block_hooks_are_not_bypassed_by_multiline_commands(self) -> None:
        # Regression: an unquoted newline must act as a command separator in the
        # block guards. Otherwise a blocked command placed after a preamble line
        # (commonly `cd <dir>`) is glued onto that line's command, so the guard
        # inspects the preamble's command position and never sees the blocked
        # one. Same root cause fixed in simple_commands() for the finish-line
        # matcher; here it is a guard bypass, not just a missed validation.
        cases = (
            (
                "block-direct-git-commit.py",
                "cd repo\ngit commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "cd repo\ngit worktree add ../repo-topic",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "cd repo\ngh pr create --draft",
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

        # block-direct-python: a python invocation on a second physical line, in
        # a workspace with a project virtualenv, must still be blocked.
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / ".venv"
            venv.mkdir()
            (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("echo setup\npython manage.py migrate"),
                cwd=Path(tmp),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "local virtualenv")


    def test_block_hooks_are_not_bypassed_by_line_continuations(self) -> None:
        # Regression: a backslash-newline line continuation between an executable
        # and its subcommand must not bypass the guards. A real shell removes the
        # `\<newline>` entirely and runs e.g. `git commit`, but a normalizer that
        # preserves the pair leaves a stray newline token between `git` and
        # `commit`, so the subcommand walker returns that token instead of the
        # real subcommand and the guard allows the command (agent-runtime-kit#351).
        cases = (
            (
                "block-direct-git-commit.py",
                "git \\\n commit -m test",
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                "git \\\n worktree add ../repo-topic",
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                "gh \\\n pr create --draft",
                "forge-cli",
            ),
            # Bash also removes a backslash-LF continuation INSIDE double quotes,
            # so a quoted subcommand split this way still runs the forbidden
            # command and must be blocked (agent-runtime-kit#351 review).
            (
                "block-direct-git-commit.py",
                'git "com\\\nmit" -m test',
                "semantic-commit",
            ),
            (
                "block-direct-git-worktree.py",
                'git "work\\\ntree" add ../repo-topic',
                "git-cli worktree",
            ),
            (
                "block-direct-pr-create.py",
                'gh pr "cre\\\nate" --draft',
                "forge-cli",
            ),
        )
        for hook, command, fragment in cases:
            with self.subTest(hook=hook):
                code, decision, stderr = run_hook(hook, command_payload(command))
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, fragment)

