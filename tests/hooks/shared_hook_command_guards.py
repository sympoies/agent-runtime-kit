"""Shared hook tests: command guards."""
from __future__ import annotations

from shared_hook_helpers import (
    HOOK_DIR,
    HookTestCase,
    Path,
    REPO_ROOT,
    codex_link_map_hook_body,
    command_matches_validation,
    command_payload,
    effective_workdir,
    gate_env,
    hashlib,
    hook_common,
    importlib,
    inventory_rules,
    inventory_tools,
    itertools,
    json,
    mock,
    os,
    run_enforced_hook,
    run_hook,
    secrets,
    session_id_from_payload,
    shlex,
    shutil,
    subprocess,
    sys,
    tempfile,
    time,
    write_payload,
)


class CommandGuardsTests(HookTestCase):
    def test_graphql_masking_has_bounded_runtime(self) -> None:
        # A strict child deadline bounds a regression in the classifier itself,
        # without timing the shared shell parser.
        probe = (
            "import importlib.util, json, sys\n"
            "sys.dont_write_bytecode = True\n"
            "spec = importlib.util.spec_from_file_location('forge_guard', sys.argv[1])\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "document = json.load(sys.stdin)\n"
            "print(json.dumps(module.raw_write_hint(['gh', 'api', 'graphql', '-XGET', '-f', 'query=' + document])))\n"
        )
        for repetitions in (28, 200000):
            with self.subTest(repetitions=repetitions):
                document = 'query { field(argument: """' + '\\a' * repetitions
                result = subprocess.run(
                    [sys.executable, "-c", probe, str(HOOK_DIR / "block-direct-pr-create.py")],
                    input=json.dumps(document), capture_output=True, text=True,
                    timeout=1, env=gate_env({"PYTHONPATH": str(HOOK_DIR)}),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("forge-cli", json.loads(result.stdout))


    def test_all_sessions_forge_operation_fixtures(self) -> None:
        cases = json.loads((REPO_ROOT / "tests/hooks/fixtures/forge-writes.json").read_text())
        for case in cases:
            for bound in (False, True):
                with self.subTest(case=case["id"], bound=bound):
                    code, decision, stderr = run_hook(
                        "block-direct-pr-create.py", command_payload(case["command"]),
                        env={"FORGE_IDENTITY_PRINCIPAL": "fixture-principal" if bound else ""},
                    )
                    self.assertEqual(code, 0, stderr)
                    if case["hint"]:
                        self.assert_blocked(decision, case["hint"])
                    else:
                        self.assert_allowed(decision)


    def test_session_id_from_payload_prefers_managed_launch_identity(self) -> None:
        payload = {"session_id": "provider-session"}
        with mock.patch.dict(
            os.environ, {"AGENT_SESSION_ID": "managed-session"}, clear=False
        ):
            self.assertEqual(session_id_from_payload(payload), "managed-session")
        with mock.patch.dict(os.environ, {"AGENT_SESSION_ID": ""}, clear=False):
            self.assertEqual(session_id_from_payload(payload), "provider-session")


    def test_delivery_boundary_negative_fixtures(self) -> None:
        cases = json.loads((Path(__file__).parent / "fixtures" /
                            "delivery-boundaries.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            for case in cases:
                with self.subTest(command=case["command"]):
                    code, decision, stderr = run_hook(
                        case["hook"], command_payload(case["command"]), cwd=repo)
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, case["reason"])


    def test_blocks_direct_git_commit(self) -> None:
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload("git commit -m test"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "semantic-commit")


    def test_git_config_hook_refuses_shared_configuration_writes(self) -> None:
        commands = (
            "HOME=/tmp/fixture-home git config --global user.name fixture",
            "git config --global --add safe.directory /tmp/fixture",
            "git config --global --unset user.name",
            "git config --global --replace-all user.name fixture",
            "git config --global --rename-section old new",
            "git config --global --remove-section old",
            "git config --global --edit",
            "git config set --global user.name fixture",
            "git config unset --global user.name",
            "git config --system user.name fixture",
            "GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig git config --system user.name fixture",
            "GIT_CONFIG_GLOBAL=/home/example/gitconfig git config --global user.name fixture",
            "GIT_CONFIG_GLOBAL=/tmp/$fixture/gitconfig git config --global user.name fixture",
            "GIT_CONFIG_GLOBAL=/tmp/fixture/../../home/example/gitconfig git config --global user.name fixture",
            "env -u GIT_CONFIG_GLOBAL git config --global user.name fixture",
            "bash -c 'HOME=/tmp/fixture-home git config --global user.name fixture'",
            "false && export GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig; git config --global user.name fixture",
            "(export GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig); git config --global user.name fixture",
        )
        for command in commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    env={"GIT_CONFIG_GLOBAL": ""},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")


    def test_git_config_hook_preserves_reads_and_isolated_global_writes(self) -> None:
        commands = (
            "git config --global --get user.name",
            "git config --system --get user.name",
            "git config --global --get-regexp '^user\\.'",
            "git config --global --list",
            "git config --global user.name",
            "git config get --global user.name",
            "git config list --system",
            "git config --local user.name fixture",
            "git config user.name fixture",
            "GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig git config --global user.name fixture",
            "env GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig git config --global --add safe.directory /tmp/fixture",
            "export GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig; git config --global user.name fixture",
            "env GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig bash -c 'git config --global user.name fixture'",
            "true && GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig git config --global user.name fixture",
        )
        for command in commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    env={"GIT_CONFIG_GLOBAL": ""},
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNone(decision)


    def test_git_config_hook_checks_resolved_output_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            output.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (output / "escape").symlink_to(outside, target_is_directory=True)
            for target, blocked in ((output / "gitconfig", False),
                                    (output / "escape" / "gitconfig", True)):
                with self.subTest(target=target):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py",
                        command_payload(f"GIT_CONFIG_GLOBAL={shlex.quote(str(target))} git config --global user.name fixture"),
                        env={"AGENT_HOME": str(root), "TMPDIR": str(output)},
                    )
                    self.assertEqual(code, 0, stderr)
                    if blocked:
                        self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")
                    else:
                        self.assertIsNone(decision)


    def test_git_config_hook_invalidates_retargeted_inherited_configuration(self) -> None:
        commands = (
            "GIT_CONFIG_GLOBAL=/home/example/gitconfig; git config --global user.name fixture",
            "source fixture-env.sh; git config --global user.name fixture",
            "env - git config --global user.name fixture",
            "GIT_CONFIG_GLOBAL=/tmp/fixture/other env - git config --global user.name fixture",
            "unset GIT_CONFIG_GLOBAL; git config --global user.name fixture",
        )
        for command in commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    env={"GIT_CONFIG_GLOBAL": "/tmp/fixture/gitconfig"},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")

        for command in ("git config --global user.name fixture",
                        "echo $(unset GIT_CONFIG_GLOBAL); git config --global user.name fixture"):
            with self.subTest(control=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    env={"GIT_CONFIG_GLOBAL": "/tmp/fixture/gitconfig"},
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNone(decision)

        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload("GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig; git config --global user.name fixture"),
            unset_env=("GIT_CONFIG_GLOBAL",),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")


    def test_git_config_hook_resolves_option_spellings_and_operand_boundaries(self) -> None:
        commands = [f"git config {scope} user.name fixture"
                    for scope in ("--gl", "--glo", "--glob", "--sy", "--sys", "--glo''bal")]
        commands += ["git con\\fig --global user.name fixture", "git con''fig --global user.name fixture"]
        commands += [f"git config --global {action} user.name"
                     for action in ("--unset-a", "--rem", "--remove-s", "--ed", "--repl", "--un")]
        commands += ["git config --global core.hooksPath /example --get",
                     "git config --global -- core.hooksPath /example -h",
                     "git config --global user.name -- --list"]
        for command in commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    unset_env=("GIT_CONFIG_GLOBAL",),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")
        for command in ("git config --glo --get user.name",
                        "git config --sys --list", "git config --global --get-regexp user.name fixture",
                        "GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig git config --glo user.name fixture"):
            with self.subTest(control=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    unset_env=("GIT_CONFIG_GLOBAL",),
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNone(decision)


    def test_git_config_hook_invalidates_shell_binding_forms(self) -> None:
        variable = "GIT_CONFIG_GLOBAL"
        changes = (
            f"{{ export {variable}=/srv/shared/gitconfig; }}",
            f"{{ unset {variable}; }}",
            f"if true; then export {variable}=/srv/shared/gitconfig; fi",
            f"for i in 1; do export {variable}=/srv/shared/gitconfig; done",
            f"if false; then :; else export {variable}=/srv/shared/gitconfig; fi",
            f"! export {variable}=/srv/shared/gitconfig",
            f"time export {variable}=/srv/shared/gitconfig",
            f"declare -x {variable}=/srv/shared/gitconfig",
            f"typeset -x {variable}=/srv/shared/gitconfig",
            f"readonly {variable}=/srv/shared/gitconfig",
            f"builtin export {variable}=/srv/shared/gitconfig",
            f"command export {variable}=/srv/shared/gitconfig",
            f"export -n {variable}",
            f"{variable}+=/../../../srv/shared/gitconfig",
            f"read {variable}", f"printf -v {variable} /srv/shared/gitconfig",
            f"eval 'export {variable}=/srv/shared/gitconfig'",
            "builtin source fixture-env.sh", "command . fixture-env.sh",
        )
        for change in changes:
            command = f"{change}; git config --global user.name fixture"
            for nested in (False, True):
                body = f"bash -c {shlex.quote(command)}" if nested else command
                with self.subTest(command=body):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py", command_payload(body),
                        env={variable: "/tmp/fixture/gitconfig"},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, variable)


    def test_git_config_hook_invalidates_inline_append_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            output.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (output / "configescape").symlink_to(outside, target_is_directory=True)
            inherited = output / "config"
            appended = Path(str(inherited) + "escape/gitconfig")
            self.assertEqual(appended.resolve(), outside / "gitconfig")
            environment = {
                "AGENT_HOME": str(root), "TMPDIR": str(output),
                "GIT_CONFIG_GLOBAL": str(inherited),
            }
            commands = (
                "GIT_CONFIG_GLOBAL+=escape/gitconfig git config --global user.name fixture",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig nice git config --global user.name fixture",
                "bash -c 'GIT_CONFIG_GLOBAL+=escape/gitconfig git config --global user.name fixture'",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig bash -c 'git config --global user.name fixture'",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig nice bash -c 'git config --global user.name fixture'",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig env bash -c 'git config --global user.name fixture'",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py", command_payload(command),
                        env=environment,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")

            direct = shlex.quote(str(output / "direct-config"))
            controls = (
                "git config --global user.name fixture",
                f"GIT_CONFIG_GLOBAL={direct} git config --global user.name fixture",
                f"GIT_CONFIG_GLOBAL+=escape/gitconfig env GIT_CONFIG_GLOBAL={direct} git config --global user.name fixture",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig git config --global --get user.name",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig git config --local user.name fixture",
                "GIT_CONFIG_GLOBAL+=escape/gitconfig git config user.name fixture",
            )
            for launcher in ("bash", "nice bash", "env bash"):
                for script in (
                    f"GIT_CONFIG_GLOBAL={direct} git config --global user.name fixture",
                    "git config --global --get user.name",
                    "git config --local user.name fixture",
                    "git config user.name fixture",
                ):
                    controls += (
                        f"GIT_CONFIG_GLOBAL+=escape/gitconfig {launcher} -c {shlex.quote(script)}",
                    )
                controls += (
                    f"GIT_CONFIG_GLOBAL+=escape/gitconfig env GIT_CONFIG_GLOBAL={direct} "
                    f"{launcher} -c 'git config --global user.name fixture'",
                )
            for command in controls:
                with self.subTest(control=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py", command_payload(command),
                        env=environment,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNone(decision)


    def test_direct_git_commit_hook_classifies_quoted_command_substitutions(
        self,
    ) -> None:
        # The shell runs a command substitution inside double quotes, and a
        # backtick substitution quoted or not, exactly like an unquoted `$(...)`
        # (issue #182). Single-quoted text and escaped markers stay literal.
        blocked = (
            "echo $(git commit -m y)",
            'echo "$(git commit -m y)"',
            "echo `git commit -m y`",
            'echo "`git commit -m y`"',
            'x="$(git commit -m y)"',
            "x=`git commit -m y`",
            '[ "$(git commit -m y)" ]',
            "[[ -n `git commit -m y` ]]",
            'test "`git commit -m y`"',
            'echo "a $(printf "%s" "$(git commit -m y)") b"',
            'echo "$(printf ok)" "$(git commit -m y)"',
            "bash -c 'echo \"$(git commit -m y)\"'",
            'echo "${x:-$(git commit -m y)}"',
            'echo "$(case x in a) git commit -m y;; esac)"',
            'echo "$(echo case; git commit -m y)"',
            "echo a#`git commit -m y`",
            'echo "$(echo ${x:-)} ; git commit -m x)"',
            'x="$(: ${y#)} ; git commit -m x)"',
            "echo ${x:- #} `git commit -m y`",
            'echo "$((git commit -m x) )"',
            "echo $((git commit -m x) )",
            'x="$(cat <<E\n# "$(git commit -m x)"\nE\n)"',
            "cat <<E\n## Fix `git commit -m x` hook\nE",
            'cat <<E\n# note "$(git commit -m x)"\nE',
            "gh issue comment 1 --body-file - <<E\n## Fix `git commit -m x`\nE",
            'cat <<E\n# "`git commit -m x`"\nE',
            "cat <<E\nit's $(git commit -m x)\nE",
            'echo ${x:-"}" #"$(git commit -m x)"}',
            "cat <<E\nit's fine\nE\ngit commit -m x",
            "cat <<E\n\"\nE\necho '$(x)'; git commit -m x",
            "git status # don't stop here\ngit commit -m x",
            "echo a\\ #b; git commit -m x",
            "echo a\\\n#b; git commit -m x",
            "[[ x =~ (#) ]]; git commit -m x",
            "[[ x =~ a|#b ]]; git commit -m x",
            "[[ $l =~ ^(#|$) ]] || git commit -m x",
            "[[ a == @(b|#c) ]] && git commit -m x",
            "ls @(a|#b); git commit -m x",
            'echo "$(echo a\\ #b; git commit -m x)"',
            "echo $(( 1 + (2 #3) )); git commit -m x",
        )
        for command in blocked:
            with self.subTest(blocked=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "Use semantic-commit instead")

        allowed = (
            "echo '$(git commit -m y)'",
            "echo '`git commit -m y`'",
            'echo "\\$(git commit -m y)"',
            'echo "\\`git commit -m y\\`"',
            'echo "$HOME"',
            "[ -f x ]",
            "[[ -f x ]]",
            "[ -x /usr/bin/git ]",
            '[[ "$tool" == git ]]',
            'test "$(git rev-parse --abbrev-ref HEAD)" = main',
            "readlink -f $(which a) $(which b)",
            'git status --short && echo "$(git rev-parse HEAD)"',
            "cat <<'EOF'\n$(git commit -m y)\n`git commit -m y`\nEOF",
            'gh pr view --json body "$(cat <<\'EOF\'\n'
            "don't run `git commit` here (see #182)\nEOF\n)\"",
            "git status  # then `git commit -m y` later",
            'ls  # "$(git commit -m y)"',
            "ls  # see `git commit --amend` docs\ngit status",
            'echo "$(( 1 + (2) ))"',
            "echo $(( (1 + 2) * 3 ))",
            "echo ok # it's $(git commit -m y)",
            "cat <<'E'\n# `git commit`\nE",
            "cat <<E\n# plain note\nE\necho ok # it's `git commit -m y`",
            "cat <<E >/dev/null\n$(printf ok)\nE\necho '$(git commit -m y)'",
            "cat <<E\nit's fine\nE\ngit status",
            "gh issue comment 1 --body-file - <<E\nit's done\nE",
            "git status  # don't worry, it's read-only",
            "echo x #; git commit -m y",
        )
        for command in allowed:
            with self.subTest(allowed=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        # A command the tokenizer cannot parse fails closed instead of
        # silently yielding no commands.
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload('echo "unterminated; git commit -m x'),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "rule=opaque-executable")

        # Nesting beyond the bounded parser fails closed without recursion.
        nested = "$(echo " * 40 + "true" + ")" * 40
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload(f"echo {nested}")
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "rule=opaque-executable")


    def test_shell_tokenizer_exposes_command_substitutions_structurally(
        self,
    ) -> None:
        # Every command substitution becomes its own simple command, ordered
        # before the command whose words it expands, and the containing word
        # keeps a dynamic marker instead of leaving a stray `$` token in
        # command position (issue #182).
        commands = hook_common.simple_commands_with_nested_shells(
            "readlink -f $(which a) $(which b)"
        )
        self.assertEqual(commands[:2], [["which", "a"], ["which", "b"]])
        self.assertEqual(len(commands), 3)
        outer = commands[2]
        self.assertEqual(outer[:2], ["readlink", "-f"])
        self.assertEqual(len(outer), 4)
        self.assertTrue(all("$" in word for word in outer[2:]))
        self.assertEqual(hook_common.invocation_tokens(outer)[0], "readlink")

        for command, inner in (
            ('echo "$(git push origin main)"', ["git", "push", "origin", "main"]),
            ("echo `git push origin main`", ["git", "push", "origin", "main"]),
            ('x="`printf a`"', ["printf", "a"]),
            ('echo "`echo \\"q\\" \\`printf b\\``"', ["printf", "b"]),
        ):
            with self.subTest(command=command):
                self.assertIn(
                    inner, hook_common.simple_commands_with_nested_shells(command)
                )

        for command in (
            "echo '$(git push origin main)'",
            "echo '`git push origin main`'",
            'echo "\\$(git push origin main)"',
            "cat <<'EOF'\n$(git push origin main)\nEOF",
        ):
            with self.subTest(literal=command):
                self.assertNotIn(
                    ["git", "push", "origin", "main"],
                    hook_common.simple_commands_with_nested_shells(command),
                )


    def test_direct_git_commit_hook_does_not_misdiagnose_git_show(self) -> None:
        issue_reproducer = (
            'R=$HOME/Project/sympoies/agent-runtime-kit\n'
            "for f in a.py b.py; do\n"
            '  git -C "$R" show "origin/main:core/hooks/shared/$f" | sha256sum\n'
            "done"
        )
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload(issue_reproducer)
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        opaque_read = "CMD=git env -S '${CMD} show origin/main:README.md'"
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload(opaque_read)
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "rule=opaque-executable")
        assert decision is not None
        reason = str(decision.get("reason", ""))
        self.assertNotIn("git commit", reason)
        self.assertNotIn("semantic-commit", reason)

        for command in (
            "CMD=git env -S '${CMD} show commit-history'",
            "op=commit; git \"$op\" -m test",
            "op=commit; git \"${op}\" -m test",
            'git "$(printf commit)" -m test',
            "part=mm; git co${part}it -m test",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "rule=opaque-executable")
                assert decision is not None
                reason = str(decision.get("reason", ""))
                self.assertNotIn("git commit", reason)
                self.assertNotIn("semantic-commit", reason)

        for command in (
            "git -c alias.ci=commit ci -m test",
            "git -c 'alias.ci=!git commit' ci",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "rule=git-alias-resolution")

        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload("git -c color.ui=false status --short"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            aliases = (
                ("ci", "commit"),
                ("one", "two"),
                ("two", "commit"),
                ("shell-ci", "!git commit"),
            )
            for name, value in aliases:
                subprocess.run(
                    ["git", "config", f"alias.{name}", value],
                    cwd=repo,
                    check=True,
                )
            for command in (
                "git ci -m test",
                "git one -m test",
                "git shell-ci",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "rule=git-alias-resolution")


    def test_direct_git_commit_hook_allows_installed_non_builtin_commands(
        self,
    ) -> None:
        # Git dispatches builtins and installed `git-<name>` programs (exec-path
        # porcelain such as submodule/mergetool, or PATH extensions such as
        # git-lfs) before aliases, so those names cannot hide a commit alias.
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            extension = bin_dir / "git-fixture-extension"
            extension.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            extension.chmod(0o755)
            env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
            for command in (
                "git submodule update --init",
                "git mergetool",
                "git fixture-extension pull",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py",
                        command_payload(command),
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            # A command that retargets PATH or the exec-path can hide the
            # installed program, letting Git fall back to a same-named alias.
            # Builtins stay admitted because Git never looks them up there.
            for command in (
                "PATH=/usr/bin git status --short",
                "GIT_EXEC_PATH=/nonexistent git status",
                "git --exec-path=/nonexistent status",
                "export PATH=/usr/bin:/bin; git status",
                "export FOO=1; git fixture-extension pull",
                "git fixture-extension pull; echo PATH",
                "source .venv/bin/activate; git status",
                "git add . && git fixture-extension pull",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py",
                        command_payload(command),
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command in (
                "git fixture-not-installed pull",
                "git -c alias.submodule=commit submodule",
                "PATH=/usr/bin git fixture-extension pull",
                "GIT_EXEC_PATH=/nonexistent git fixture-extension pull",
                "env PATH=/usr/bin git fixture-extension pull",
                "env -u PATH git fixture-extension pull",
                "env -i git fixture-extension pull",
                "git --exec-path=/nonexistent fixture-extension pull",
                "git --exec-path /nonexistent fixture-extension pull",
                "GIT_EXEC_PATH=/nonexistent git submodule update",
                # Earlier statements in the same command retarget lookup too.
                "export PATH=/usr/bin:/bin; git fixture-extension pull",
                "PATH=/usr/bin:/bin; git fixture-extension pull",
                "PATH+=:/nonexistent; git fixture-extension pull",
                "unset PATH; git fixture-extension pull",
                "export GIT_EXEC_PATH=/nonexistent; git submodule update",
                "declare -x PATH=/usr/bin; git fixture-extension pull",
                "for PATH in /usr/bin; do git fixture-extension pull; done",
                "read PATH <<< /usr/bin; git fixture-extension pull",
                "printf -v PATH %s /usr/bin; git fixture-extension pull",
                "bash -c 'export PATH=/usr/bin; git fixture-extension pull'",
                "git config alias.fixture-extension commit && "
                "export PATH=/usr/bin && git fixture-extension -m x",
                # Sourced files and namerefs can change lookup invisibly.
                "source /tmp/env.sh; git fixture-extension pull",
                "set -a; . ./env; git fixture-extension pull",
                "declare -n r=PATH; r=/x; git fixture-extension pull",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-commit.py",
                        command_payload(command),
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "rule=git-alias-resolution")


    def test_block_messages_name_the_governed_route(self) -> None:
        # `git-cli worktree` has no move/repair/lock/unlock, so the message
        # must route those to the override instead of a nonexistent command.
        code, decision, stderr = run_hook(
            "block-direct-git-worktree.py",
            command_payload("git worktree move ../old ../new"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "no git-cli worktree equivalent")
        assert decision is not None
        self.assertIn("ALLOW_DIRECT_GIT_WORKTREE=1", str(decision.get("reason", "")))

        for command in ("gh pr create --draft", "glab mr create --draft"):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "forge-cli pr deliver")
                assert decision is not None
                reason = str(decision.get("reason", ""))
                self.assertIn("forge-cli pr create", reason)
                if command.startswith("glab"):
                    self.assertIn("AGENT_RUNTIME_PR_SKILL", reason)


    def test_blocks_direct_git_worktree_and_allows_git_cli(self) -> None:
        blocked_commands = (
            "git -C repo worktree add ../repo-topic",
            "env GIT_OPTIONAL_LOCKS=0 git worktree remove ../repo-topic",
            "git status && git worktree prune",
            "command git worktree lock ../repo-topic",
            "printf 'ALLOW_DIRECT_GIT_WORKTREE=1'; git worktree add ../repo-topic",
            "ALLOW_DIRECT_GIT_WORKTREE=0 git worktree add ../repo-topic",
        )
        for command in blocked_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "git-cli worktree")

        allowed_commands = (
            "git worktree list",
            "git worktree --help",
            "git-cli worktree list",
            "git status",
            "printf 'git worktree list\\n'",
            "ALLOW_DIRECT_GIT_WORKTREE=1 git worktree add ../repo-topic",
            "env ALLOW_DIRECT_GIT_WORKTREE=1 git worktree add ../repo-topic",
            "env -S 'ALLOW_DIRECT_GIT_WORKTREE=1 git worktree add ../repo-topic'",
            "env -uSOMETHING ALLOW_DIRECT_GIT_WORKTREE=1 git worktree add ../repo-topic",
            "ALLOW_DIRECT_GIT_WORKTREE=1 bash -lc 'git worktree add ../repo-topic'",
        )
        for command in allowed_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        code, decision, stderr = run_hook(
            "block-direct-git-worktree.py",
            command_payload("git worktree add ../repo-topic"),
            env={"AGENT_RUNTIME_ALLOW_DIRECT_GIT_WORKTREE": "1"},
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)


    def test_git_worktree_override_respects_env_option_boundaries(self) -> None:
        blocked_commands = (
            "env -iC ALLOW_DIRECT_GIT_WORKTREE=1 git worktree move ../victim",
            "env --ch ALLOW_DIRECT_GIT_WORKTREE=1 git worktree move ../victim",
            "ALLOW_DIRECT_GIT_WORKTREE=1 env - git worktree move ../victim",
            "ALLOW_DIRECT_GIT_WORKTREE=1 bash -c 'env -i git worktree move ../victim'",
            "ALLOW_DIRECT_GIT_WORKTREE=1 bash -c 'env -u ALLOW_DIRECT_GIT_WORKTREE git worktree move ../victim'",
            "ALLOW_DIRECT_GIT_WORKTREE=1 /usr/bin/time -f x env -i git worktree move ../victim",
        )
        for command in blocked_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "git-cli worktree")

        code, decision, stderr = run_hook(
            "block-direct-git-worktree.py",
            command_payload(
                "env -iC . ALLOW_DIRECT_GIT_WORKTREE=1 "
                "git worktree move ../victim"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        for command in (
            "env -- ALLOW_DIRECT_GIT_WORKTREE=1 git worktree move ../victim",
            "ALLOW_DIRECT_GIT_WORKTREE=1 bash -c 'git worktree move ../victim'",
            "ALLOW_DIRECT_GIT_WORKTREE=1 bash -c 'env -i ALLOW_DIRECT_GIT_WORKTREE=1 git worktree move ../victim'",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        code, decision, stderr = run_hook(
            "block-direct-git-worktree.py",
            command_payload("env -i git worktree move ../victim"),
            env={"ALLOW_DIRECT_GIT_WORKTREE": "1"},
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "git-cli worktree")


    def test_python_hooks_do_not_write_bytecode_in_source_checkout(self) -> None:
        pycache = HOOK_DIR / "__pycache__"
        if pycache.exists():
            for path in pycache.iterdir():
                path.unlink()
            pycache.rmdir()

        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload("git status"),
            dont_write_bytecode=False,
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)
        self.assertFalse(pycache.exists())


    def test_blocks_nontrivial_semantic_commit_without_body(self) -> None:
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload("semantic-commit commit --message 'fix(agent): tighten hook parser'"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "missing a body")


    def test_default_branch_route_keeps_commit_content_gates(self) -> None:
        bodyless = (
            "semantic-commit default-branch "
            "--message 'fix(agent): tighten hook parser'"
        )
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload(bodyless),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "missing a body")

        for suffix in ("--dry-run", "--help"):
            with self.subTest(read_only=suffix):
                code, decision, stderr = run_hook(
                    "semantic-commit-body-gate.py",
                    command_payload(f"{bodyless} {suffix}"),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        removed = bodyless.replace("default-branch", "local-default", 1)
        for hook in ("semantic-commit-body-gate.py",):
            with self.subTest(removed_local_default=hook):
                code, decision, stderr = run_hook(
                    hook,
                    command_payload(removed),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_blocks_nontrivial_body_gate_via_structured_subject_without_bullet(self) -> None:
        # Bypass repro: a non-trivial commit carried via structured
        # --type/--scope/--subject with no --body-bullet had no --message body
        # for extract_message() to recover, so the gate fell through to ALLOW.
        command = (
            "semantic-commit commit --type fix --scope hooks --subject 'tighten gate'"
        )
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload(command),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "missing a body")


    def test_blocks_nontrivial_body_gate_via_message_file_without_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            msg = Path(tmp) / "msg.txt"
            msg.write_text("fix(agent): tighten hook parser\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "semantic-commit-body-gate.py",
                command_payload(f"semantic-commit commit --message-file {msg}"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "missing a body")


    def test_body_gate_treats_option_like_message_filename_as_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "--dry-run").write_text(
                "fix(agent): tighten hook parser\n", encoding="utf-8"
            )
            code, decision, stderr = run_hook(
                "semantic-commit-body-gate.py",
                command_payload(
                    "semantic-commit commit --message-file --dry-run"
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "missing a body")


    def test_body_gate_allows_dry_run_message_file_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recovery = Path(tmp) / "recovery.md"
            command = (
                "semantic-commit commit --dry-run "
                "--subject 'fix(hooks): inspect message' "
                f"--message-out {shlex.quote(str(recovery))}"
            )
            code, decision, stderr = run_hook(
                "semantic-commit-body-gate.py",
                command_payload(command),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_body_gate_trailer_does_not_count_as_body(self) -> None:
        # A --trailer is metadata, not an explanatory body bullet; a non-trivial
        # commit with only a trailer must still be blocked.
        command = (
            "semantic-commit commit --subject 'fix(hooks): tighten gate' "
            "--trailer 'Reviewed-by: Jane Dev <jane@example.com>'"
        )
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload(command),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "missing a body")


    def test_body_gate_names_mixed_message_and_structured_forms(self) -> None:
        # semantic-commit rejects --message/--message-file combined with the
        # structured fields, so the bullets never become a body. The gate must
        # say that instead of reporting a missing body next to visible bullets.
        command = (
            "semantic-commit commit --message 'fix(hooks): tighten gate' "
            "--body-bullet 'first reason' --body-bullet 'second reason'"
        )
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload(command),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "cannot be combined")
        assert decision is not None
        self.assertNotIn("missing a body", str(decision.get("reason", "")))


    def test_allows_body_gate_with_structured_body_bullet(self) -> None:
        command = (
            "semantic-commit commit --type fix --scope hooks "
            "--subject 'tighten gate' --body-bullet 'covers structured args'"
        )
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload(command),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)


    def test_allows_trivial_structured_type_without_body(self) -> None:
        # --type chore is trivial; reconstructing the conventional header from
        # the structured flags keeps the trivial allowance intact.
        command = "semantic-commit commit --type chore --subject 'bump pinned surface'"
        code, decision, stderr = run_hook(
            "semantic-commit-body-gate.py",
            command_payload(command),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)


    def test_allows_body_gate_message_file_with_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            msg = Path(tmp) / "msg.txt"
            msg.write_text("fix(agent): tighten parser\n\n- explain why\n", encoding="utf-8")
            code, decision, stderr = run_hook(
                "semantic-commit-body-gate.py",
                command_payload(f"semantic-commit commit --message-file {msg}"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_blocks_bare_python_in_uv_project_and_allows_shared_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")
            payload = command_payload("python3 -m pytest", workdir=str(repo))

            code, decision, stderr = run_hook("block-direct-python.py", payload, cwd=repo)
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")

            code, decision, stderr = run_hook(
                "block-direct-python.py",
                payload,
                cwd=repo,
                env={"AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON": "1"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload(
                    "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python3 -m pytest",
                    workdir=str(repo),
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            for command in (
                "env -S 'AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python -m pytest'",
                "env -uSOMETHING AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python -m pytest",
                "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 bash -lc 'python -m pytest'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-python.py",
                        command_payload(command, workdir=str(repo)),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_direct_python_bypass_must_prefix_same_simple_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "uv.lock").write_text("# fixture\n", encoding="utf-8")

            blocked = (
                "printf AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1; python -m pytest",
                "python -m pytest --note AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1",
                "# AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1\npython -m pytest",
                "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 env - python -m pytest",
                "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 bash -c 'env -i python -m pytest'",
                "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 bash -c 'env -u AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON python -m pytest'",
                "/usr/bin/time -f AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python -m pytest",
                "exec -a AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python -m pytest",
            )
            for command in blocked:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-python.py",
                        command_payload(command, workdir=str(repo)),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "uv run --locked python")

            for command in (
                "env -- AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python -m pytest",
                "AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 bash -c 'env -i AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON=1 python -m pytest'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-python.py",
                        command_payload(command, workdir=str(repo)),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("env -i python -m pytest", workdir=str(repo)),
                cwd=repo,
                env={"AGENT_RUNTIME_ALLOW_SYSTEM_PYTHON": "1"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_nested_direct_python_uses_current_shell_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sub = repo / "subproject"
            sub.mkdir()
            (sub / "uv.lock").write_text("# fixture\n", encoding="utf-8")

            code, decision, stderr = run_hook(
                "block-direct-python.py",
                command_payload("cd subproject && bash -c 'python -m pytest'"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "uv run --locked python")


    def test_github_has_no_skill_marker_bypass_and_gitlab_retains_it(self) -> None:
        code, decision, stderr = run_hook(
            "block-direct-pr-create.py",
            command_payload("gh pr create --draft"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "forge-cli")

        for marker in (
            "AGENT_RUNTIME_PR_SKILL=deliver-pr",
            "AGENT_RUNTIME_PR_SKILL=pr:deliver-pr",
        ):
            code, decision, stderr = run_hook(
                "block-direct-pr-create.py",
                command_payload(f"{marker} gh pr create --draft"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "forge-cli")

        for retired_marker in (
            "AGENT_RUNTIME_PR_SKILL=create-pr",
            "AGENT_RUNTIME_PR_SKILL=pr:create-pr",
            "AGENT_RUNTIME_PR_SKILL=create-dispatch-lane-pr",
            "AGENT_RUNTIME_PR_SKILL=pr:create-dispatch-lane-pr",
        ):
            code, decision, stderr = run_hook(
                "block-direct-pr-create.py",
                command_payload(f"{retired_marker} gh pr create --draft"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "forge-cli")

        # Retired legacy product markers must no longer bypass the gate.
        for legacy in (
            "AGENT_KIT_PR_SKILL=create-pr",
            "CLAUDE_KIT_PR_SKILL=pr:create-pr",
        ):
            code, decision, stderr = run_hook(
                "block-direct-pr-create.py",
                command_payload(f"{legacy} gh pr create --draft"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "forge-cli")

        for command in (
            "gh pr create --draft --body 'AGENT_RUNTIME_PR_SKILL=deliver-pr'",
            "AGENT_RUNTIME_PR_SKILL=deliver-pr printf ok; gh pr create --draft",
            "# AGENT_RUNTIME_PR_SKILL=deliver-pr\ngh pr create --draft",
            "AGENT_RUNTIME_PR_SKILL=deliver-pr env - gh pr create --draft",
            "AGENT_RUNTIME_PR_SKILL=deliver-pr /usr/bin/time -f x env -i gh pr create --draft",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "forge-cli")

        code, decision, stderr = run_hook(
            "block-direct-pr-create.py",
            command_payload("env AGENT_RUNTIME_PR_SKILL=deliver-pr gh pr create --draft"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "forge-cli")

        code, decision, stderr = run_hook(
            "block-direct-pr-create.py",
            command_payload(
                "env -- AGENT_RUNTIME_PR_SKILL=deliver-pr gh pr create --draft"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "forge-cli")

        for command in (
            "env -S 'AGENT_RUNTIME_PR_SKILL=deliver-pr gh pr create --draft'",
            "env -uSOMETHING AGENT_RUNTIME_PR_SKILL=deliver-pr gh pr create --draft",
            "AGENT_RUNTIME_PR_SKILL=deliver-pr bash -lc 'gh pr create --draft'",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "forge-cli")

        blocked_pr_mr_commands = (
            "gh api -X POST /repos/example/project/pulls -f title=x -f head=topic -f base=main",
            "gh api --method POST repos/example/project/pulls -f title=x -f head=topic -f base=main",
            "gh api repos/example/project/pulls -f title=x -f head=topic -f base=main",
            "gh api repos/example/project/pulls -ftitle=x -fhead=topic -fbase=main",
            "gh api repos/example/project/pulls -Ftitle=x -Fhead=topic -Fbase=main",
            "glab mr create --draft",
            "bash -lc 'glab mr create --draft'",
            "glab api -X POST /projects/1/merge_requests",
        )
        for command in blocked_pr_mr_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "forge-cli")

        for command in (
            "env AGENT_RUNTIME_PR_SKILL=pr:deliver-pr gh api -X POST /repos/example/project/pulls -f title=x -f head=topic -f base=main",
            "AGENT_RUNTIME_PR_SKILL=pr:deliver-pr glab mr create --draft",
            "env AGENT_RUNTIME_PR_SKILL=pr:deliver-pr glab api -X POST /projects/1/merge_requests",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                if " glab " in command:
                    self.assert_allowed(decision)
                else:
                    self.assert_blocked(decision, "forge-cli")


    def test_github_subresource_writes_refused_and_gitlab_subresources_allowed(self) -> None:
        # Regression for agent-runtime-kit#474: the pulls / merge_requests
        # endpoint regexes used a trailing [/?#] class, so they over-matched the
        # whole /pulls/... and /merge_requests/... subtree. A POST to any
        # sub-resource (review comments, replies, reviews, reactions, notes) was
        # wrongly blocked as a PR/MR create. GitLab retains that contract;
        # all GitHub API writes are now refused, including subresources.
        still_blocked = (
            # GitHub PR create endpoint at end of path.
            "gh api --method POST repos/example/project/pulls "
            "-f title=x -f head=topic -f base=main",
            # GitHub PR create endpoint with a trailing query string.
            "gh api --method POST 'repos/example/project/pulls?per_page=1' "
            "-f title=x -f head=topic -f base=main",
            # GitHub PR create endpoint with a fragment (locks in the '#' half
            # of the trailing class).
            "gh api --method POST 'repos/example/project/pulls#frag' "
            "-f title=x -f head=topic -f base=main",
            # GitHub PR create endpoint with a single trailing slash (a bare
            # create form; defense-in-depth even though GitHub 404s it).
            "gh api --method POST repos/example/project/pulls/ "
            "-f title=x -f head=topic -f base=main",
            # GitLab MR create endpoint at end of path.
            "glab api -X POST /projects/1/merge_requests -f title=x "
            "-f source_branch=topic -f target_branch=main",
            # GitLab MR create endpoint with a trailing query string (provider
            # parity with the GitHub query-string case above).
            "glab api -X POST '/projects/1/merge_requests?per_page=1' -f title=x "
            "-f source_branch=topic -f target_branch=main",
            # GitLab MR create endpoint with a single trailing slash.
            "glab api -X POST /projects/1/merge_requests/ -f title=x "
            "-f source_branch=topic -f target_branch=main",
        )
        for command in still_blocked:
            with self.subTest(blocked=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "forge-cli")

        subresource_commands = (
            # GitHub PR review-comment reaction (the case from the report).
            "gh api --method POST "
            "repos/example/project/pulls/comments/123/reactions "
            "-f content=+1",
            # GitHub PR review-comment reply.
            "gh api --method POST "
            "repos/example/project/pulls/476/comments/9/replies "
            "-f body=ack",
            # GitHub PR review submission.
            "gh api --method POST "
            "repos/example/project/pulls/476/reviews -f event=APPROVE",
            # GitHub PR requested reviewers (another /pulls sub-resource).
            "gh api --method POST "
            "repos/example/project/pulls/476/requested_reviewers "
            "-f reviewers=octocat",
            # GitLab MR note.
            "glab api -X POST /projects/1/merge_requests/5/notes -f body=ack",
            # GitLab MR award-emoji (reaction).
            "glab api -X POST /projects/1/merge_requests/5/award_emoji "
            "-f name=thumbsup",
        )
        for command in subresource_commands:
            with self.subTest(allowed=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                if command.startswith("gh "):
                    self.assert_blocked(decision, "forge-cli")
                else:
                    self.assert_allowed(decision)


    def test_glab_help_and_explicit_get_are_reads_not_creates(self) -> None:
        for command in (
            "glab mr create --help",
            "glab mr create -h",
            # An explicit method decides regardless of where the fields sit.
            "glab api /projects/1/merge_requests -f state=opened -X GET",
            "glab api /projects/1/merge_requests -F state=opened --method=GET",
            "glab api -f state=opened -XGET /projects/1/merge_requests",
            "glab api /projects/1/merge_requests -H 'Accept: application/json' -f state=opened -X GET",
        ):
            with self.subTest(allowed=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        for command in (
            # Help is data for a value option, so this still creates.
            "glab mr create --title --help",
            "glab mr create --help --title x",
            "glab api -f source_branch=topic /projects/1/merge_requests",
            "glab api /projects/1/merge_requests -X GET -f title=x -X POST",
            "glab api /projects/1/merge_requests -f title=x --method=POST",
            # An option value is data: a header or field that merely looks
            # like a method flag must not override the real method.
            "glab api /projects/1/merge_requests -X POST -H '-XGET: value' -f title=x",
            "glab api /projects/1/merge_requests -H '-XGET: value' -f title=x",
            "glab api /projects/1/merge_requests -X POST -f '-XGET=value' -f title=x",
            "glab api /projects/1/merge_requests -X POST --header=--method=GET -f title=x",
        ):
            with self.subTest(blocked=command):
                code, decision, stderr = run_hook(
                    "block-direct-pr-create.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "forge-cli")


    def test_git_commit_help_and_dry_run_are_admitted_only_without_a_message(self) -> None:
        for command in (
            "git commit --help",
            "git commit -h",
            "git -C /tmp/example commit --dry-run",
            "git commit --dry-run --short --branch",
            "git commit -a --dry-run",
            "bash -c 'git commit --help'",
        ):
            with self.subTest(allowed=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        for command in (
            "git commit -m --help",
            "git commit -m fixture --dry-run",
            "git commit --dry-run -F message.txt",
            "git commit --dry-run --author --help",
            "git commit --help --amend",
            "git commit --amend --no-edit",
            "bash -c 'git commit -m fixture'",
        ):
            with self.subTest(blocked=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "semantic-commit")


    def test_git_worktree_help_and_prune_preview_are_reads(self) -> None:
        for command in (
            "git worktree add --help",
            "git worktree remove -h",
            "git worktree prune --dry-run",
            "git worktree prune -n -v",
            "bash -c 'git worktree prune --dry-run'",
        ):
            with self.subTest(allowed=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        for command in (
            "git worktree prune",
            "git worktree prune --expire now",
            "git worktree prune --dry-run --expire=now",
            "git worktree add --help ../repo-topic",
            "git worktree remove ../repo-topic",
            "bash -c 'git worktree prune'",
        ):
            with self.subTest(blocked=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-worktree.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "git-cli worktree")


    def test_backslash_cr_is_not_a_line_continuation(self) -> None:
        # A backslash before a CR is NOT a bash line continuation: `\<CR>` escapes
        # the CR and a following LF still separates commands, so `git \<CR><LF>
        # commit` runs `git $'\r'` then `commit` (neither a direct `git commit`).
        # The normalizer must not collapse `\<CR><LF>` into `git commit`, which
        # would false-block input bash never executes as a commit
        # (agent-runtime-kit#351 review).
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py",
            command_payload("git \\\r\n commit -m test"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)


    def test_forge_label_reminder_fires_only_without_label(self) -> None:
        reminded_commands = (
            "forge-cli pr create --title x",
            "forge-cli pr deliver --kind feature",
            "forge-cli issue create --title x",
            # A global option value must not be mistaken for the subcommand.
            "forge-cli --repo owner/x --format json pr create --title x",
            "forge-cli --host gitlab.example.com pr create --title x",
            "forge-cli --host=gitlab.example.com issue create --title x",
            # The agent-run exec wrapper is unwrapped before matching.
            "agent-run exec --cwd /repo -- forge-cli issue create --title x",
            # --label-catalog is not a label selection.
            "forge-cli pr create --label-catalog manifests/forge-labels.yaml",
        )
        for command in reminded_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "forge-label-reminder.py",
                    command_payload(command),
                    env={"AGENT_RUNTIME_FORGE_IDENTITY_ROUTER_REQUIRED": ""},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "--label")
                assert decision is not None
                reason = str(decision.get("reason", ""))
                self.assertIn("FORGE_NO_LABELS=1", reason)
                self.assertNotIn("not a hard requirement", reason)

        allowed_commands = (
            "forge-cli pr create --title x --label type::feature",
            "forge-cli issue create --label=type::bug",
            "forge-cli pr deliver --kind feature --label size::m",
            # Non-labelable subcommands and non-forge commands stay silent.
            "forge-cli pr view 123",
            "forge-cli issue list",
            "forge-cli label ensure",
            "forge-cli pr create --help",
            "forge-cli pr deliver --help",
            "forge-cli issue create -h",
            # A dry run creates no record.
            "forge-cli --dry-run pr create --title x",
            "forge-cli pr create --dry-run --title x",
            "forge-cli pr deliver --kind feature --dry-run",
            "forge-cli issue create --title x --dry-run",
            "gh pr create --title x",
            # Explicit no-label opt-out via the inline bypass marker.
            "FORGE_NO_LABELS=1 forge-cli pr create --title x",
            "AGENT_RUNTIME_FORGE_NO_LABELS=true forge-cli issue create --title x",
        )
        for command in allowed_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "forge-label-reminder.py", command_payload(command)
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        # The bypass also honours the process environment.
        code, decision, stderr = run_hook(
            "forge-label-reminder.py",
            command_payload("forge-cli pr create --title x"),
            env={"FORGE_NO_LABELS": "1"},
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)


    def test_forge_cli_identity_routing_is_environment_owned(self) -> None:
        environment_routed_commands = (
            "env -u SOME_SETTING forge-cli pr review 448",
            "env - forge-cli pr review 448",
            "env -uSOMETHING forge-cli pr review 448",
            "env --block-signal=PIPE forge-cli pr review 448",
            "env SOME_SETTING=value forge-cli pr review 448",
            "env -S 'forge-cli pr review 448'",
            "env -S 'SOME_SETTING=value forge-cli pr review 448'",
            "export CMD=forge-cli; env -S \"'${CMD}' pr review 448\"",
            "env -S \"'`printf forge-cli`' pr review 448\"",
            "env -S '# ignored' forge-cli pr review 448",
            "env -S'forge-cli pr review 448'",
            "env -iS'forge-cli pr review 448'",
            "env -C /tmp forge-cli pr review 448",
            "env --chdir=/tmp forge-cli pr review 448",
            "env -P /bin forge-cli pr review 448",
            "command forge-cli pr review 448",
            "command env -S 'forge-cli pr review 448'",
            "exec forge-cli pr review 448",
            "/opt/homebrew/bin/forge-cli pr review 448",
            "time /opt/homebrew/bin/forge-cli pr review 448",
            "time SOME_SETTING=value env forge-cli pr review 448",
            "/usr/bin/time -o /dev/null env forge-cli pr review 448",
            "/usr/bin/time --output=/dev/null env forge-cli pr review 448",
            "/usr/bin/time -af %e forge-cli pr review 448",
            "/usr/bin/time --fo=V env forge-cli pr review 448",
            "exec -ca reviewed forge-cli pr review 448",
            "agent-run exec --cwd /repo -- time env forge-cli pr review 448",
            "agent-run exec --cwd /repo -- env -u SOME_SETTING forge-cli pr review 448",
            "agent-run exec --cwd /repo env -u SOME_SETTING forge-cli pr review 448",
            "agent-run exec --cwd /repo -- env -S 'forge-cli pr review 448'",
            "agent-run exec --cwd /repo -- forge-cli pr review 448",
            "nice forge-cli pr review 448",
            "nohup forge-cli pr review 448",
            "timeout 5 forge-cli pr review 448",
            "setsid forge-cli pr review 448",
            "stdbuf -oL forge-cli pr review 448",
            "printf '448\\n' | xargs -n1 forge-cli pr review",
            "printf '448\\n' | xargs --replace forge-cli pr review {}",
            "printf '448\\n' | xargs -J % forge-cli pr review %",
            "printf '448\\n' | xargs -J% forge-cli pr review %",
            "printf '448\\n' | xargs -I {} -R 2 forge-cli pr review {}",
            "printf '448\\n' | xargs -I{} -R2 forge-cli pr review {}",
            "printf '448\\n' | xargs -I {} -S 255 forge-cli pr review {}",
            "printf '448\\n' | xargs -I{} -S255 forge-cli pr review {}",
            "bash -lc 'env -u SOME_SETTING forge-cli pr review 448'",
            "zsh -lc '/opt/homebrew/bin/forge-cli pr review 448'",
            "dash -c 'forge-cli pr review 448'",
            "ksh -c 'forge-cli pr review 448'",
            "bash -c 'exec \"$@\"' _ forge-cli pr review 448",
            "zsh -c 'exec \"$@\"' _ forge-cli pr review 448",
            "dash -c 'exec \"$@\"' _ forge-cli pr review 448",
            "ksh -c 'exec \"$@\"' _ forge-cli pr review 448",
            "bash -c 'eval \"$0\"' 'forge-cli pr review 448'",
            "bash -c 'exec \"$1\"' _ forge-cli pr review 448",
            "zsh -c 'exec \"$1\"' _ forge-cli pr review 448",
            "dash -c 'exec \"$1\"' _ forge-cli pr review 448",
            "ksh -c 'exec \"$1\"' _ forge-cli pr review 448",
            "bash -c '\"$1\" pr review 448' _ forge-cli",
            "bash -c 'exec \"$2\" pr review 448' _ true forge-cli",
            "zsh -c '\"$1\" pr review 448' _ forge-cli",
            "dash -c '\"$1\" pr review 448' _ forge-cli",
            "ksh -c '\"$1\" pr review 448' _ forge-cli",
            "bash -c 'nice \"$1\" pr review 448' _ forge-cli",
            "bash -c 'nohup \"$1\" pr review 448' _ forge-cli",
            "bash -c 'timeout 5 \"$1\" pr review 448' _ forge-cli",
            "bash -c 'stdbuf -oL \"$1\" pr review 448' _ forge-cli",
            "CMD=forge-cli bash -c 'exec \"$CMD\" pr review 448'",
            "bash -c 'source /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "zsh -c 'source /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "dash -c '. /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "ksh -c '. /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'bash /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "zsh -c 'zsh /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "dash -c 'sh /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "ksh -c 'ksh /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'bash -e /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c '/bin/bash /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'exec bash /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'env -i /bin/bash -e /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'command /bin/bash /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'nice bash -e /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'bash -s' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'bash -' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'bash' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'bash -e' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'time bash /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'agent-run exec -- bash /dev/stdin' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(cat)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(cat -)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(cat --)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(cat </dev/stdin)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(< /dev/stdin)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(/bin/cat -)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(command cat -)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(cat <&0)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'eval \"$(cat < /dev/stdin)\"' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash <<'EOF'\nforge-cli pr review 448\nEOF",
            "dash <<'EOF'\nforge-cli pr review 448\nEOF",
            "ksh <<'EOF'\nforge-cli pr review 448\nEOF",
            "agent-run exec --cwd /repo -- bash -lc 'env -u SOME_SETTING forge-cli pr review 448'",
            "FORGE_NO_LABELS=1 env -u SOME_SETTING forge-cli pr review 448",
        )

        # Public runtime-kit installs do not assume an identity router exists.
        for command in environment_routed_commands:
            with self.subTest(command=command, router_required=False):
                code, decision, stderr = run_hook(
                    "forge-label-reminder.py",
                    command_payload(command),
                    env={"AGENT_RUNTIME_FORGE_IDENTITY_ROUTER_REQUIRED": ""},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        # Identity routing remains environment-owned even when the environment
        # advertises an independent review identity capability.
        for command in environment_routed_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "forge-label-reminder.py",
                    command_payload(command),
                    env={"AGENT_RUNTIME_FORGE_IDENTITY_ROUTER_REQUIRED": "1"},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        allowed_commands = (
            "forge-cli pr review 448",
            "SOME_SETTING=value forge-cli pr review 448",
            "env printf forge-cli",
            "command -v forge-cli",
            "bash -- -c 'forge-cli pr review 448'",
            "cat <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -lc 'true' <<'EOF'\nforge-cli pr review 448\nEOF",
            "bash -c 'echo \"$@\"' _ forge-cli pr review 448",
            "bash -c 'printf \"%s\\n\" \"$1\"' _ forge-cli",
            "CMD=forge-cli bash -c 'echo \"$CMD\"'",
            "bash -c 'nice echo \"$1\"' _ forge-cli",
            "bash -c 'echo forge-cli; exec \"$1\"' _ true",
            "bash -c 'printf \"%s\\n\" forge-cli; nice \"$1\"' _ true",
            "CMD=forge-cli RUN=echo bash -c 'exec \"$RUN\" ok'",
            "CMD=forge-cli bash -c 'exec \"$OTHER\" ok'",
            "bash -c 'exec \"$2\"' _ forge-cli true",
        )
        for command in allowed_commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "forge-label-reminder.py",
                    command_payload(command),
                    env={"AGENT_RUNTIME_FORGE_IDENTITY_ROUTER_REQUIRED": "true"},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_blocks_project_memory_write(self) -> None:
        code, decision, stderr = run_hook(
            "block-project-memory-write.py",
            write_payload(".codex/memories/project_state/project_notes.md", "x"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "project-state memory")


    def test_blocks_mcp_secret_and_portable_path_writes(self) -> None:
        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            write_payload(".mcp.json", '{"apiKey": "sk-proj-abcdefghijklmnopqrstuvwxyz"}'),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, ".mcp.json")

        code, decision, stderr = run_hook(
            "portable-paths-scan.py",
            write_payload("docs/example.md", "Path: /Users/example/project\n"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "portable-paths")


    def test_bash_authored_write_scanners_cover_redirection_heredoc_and_tee(self) -> None:
        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload(
                "cat > .mcp.json <<'EOF'\n"
                '{"apiKey":"sk-ant-abcdefghijklmnopqrstuvwxyz"}\n'
                "EOF"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, ".mcp.json")

        for command in (
            "echo 'sk-ant-abcdefghijklmnopqrstuvwxyz' >| .mcp.json",
            "cat >| .mcp.json <<'EOF'\n"
            '{"apiKey":"sk-ant-abcdefghijklmnopqrstuvwxyz"}\n'
            "EOF",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, ".mcp.json")

        code, decision, stderr = run_hook(
            "block-project-memory-write.py",
            command_payload(
                "cat > .codex/memories/project_state/project_notes.md <<'EOF'\n"
                "project notes\n"
                "EOF"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "project-state memory")

        code, decision, stderr = run_hook(
            "block-project-memory-write.py",
            command_payload("cp /tmp/source .codex/memories/project_state/project_notes.md"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "project-state memory")

        for command in (
            "cp /tmp/project_notes.md .codex/memories/project_state/",
            "cp /tmp/project_notes.md ~/.codex/memories/project_state/",
            "mkdir -p ~/.codex/memories/project_state && cp /tmp/project_notes.md ~/.codex/memories/project_state",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-project-memory-write.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "project-state memory")

        for command in (
            "mkdir -p .vscode && cp /tmp/mcp.json .vscode",
            "cd .vscode && echo 'sk-ant-abcdefghijklmnopqrstuvwxyz' > mcp.json",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, ".vscode/mcp.json")

        code, decision, stderr = run_hook(
            "block-project-memory-write.py",
            command_payload(
                "cd ~/.codex/memories/project_state && echo notes > project_notes.md"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "project-state memory")

        code, decision, stderr = run_hook(
            "portable-paths-scan.py",
            command_payload("printf '/Users/example/project\\n' | tee docs/example.md"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "portable-paths")

        code, decision, stderr = run_hook(
            "portable-paths-scan.py",
            command_payload("cd docs && printf '/Users/example/project\\n' > example.md"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "portable-paths")

        for hook in (
            "mcp-secret-scan.py",
            "block-project-memory-write.py",
            "portable-paths-scan.py",
        ):
            with self.subTest(hook=hook):
                code, decision, stderr = run_hook(
                    hook,
                    command_payload(
                        "printf '%s\\n' '.mcp.json sk-ant-abcdefghijklmnopqrstuvwxyz /Users/example'"
                    ),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_portable_paths_scan_covers_canonical_skill_and_policy_sources(
        self,
    ) -> None:
        # Rendered SKILL.md and policy docs come from these canonical sources,
        # so a home path must be caught where it is authored.
        for path in (
            "core/skills/example/SKILL.md.tera",
            "core/skills/example/references/guide.md.tera",
            "core/policies/example-policy.md",
            "core/policies/evidence-archive/EXAMPLE.md",
        ):
            with self.subTest(path=path):
                code, decision, stderr = run_hook(
                    "portable-paths-scan.py",
                    write_payload(path, "Run /Users/example/project/tool\n"),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "portable-paths")

        for path in (
            "core/policies/agent-hook/example.toml",
            "tests/fixtures/example/SKILL.md.tera",
        ):
            with self.subTest(path=path):
                code, decision, stderr = run_hook(
                    "portable-paths-scan.py",
                    write_payload(path, "Run /Users/example/project/tool\n"),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_mcp_secret_scan_covers_broader_paths_and_redacts_secret_samples(self) -> None:
        aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        cases = (
            (".vscode/mcp.json", "github_pat_1234567890abcdef1234567890abcdef1234", "value"),
            # A 40-character AWS secret is only recognizable by its key context.
            (".cursor/mcp.json", aws_secret, "AWS_SECRET_ACCESS_KEY"),
            (".mcp.json", aws_secret, "aws_secret_access_key"),
            (".mcp.json", aws_secret, "SecretAccessKey"),
            ("mcp.json", "-----BEGIN OPENSSH PRIVATE KEY-----", "value"),
            (".mcp.json", "AGE-SECRET-KEY-1QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ", "value"),
            (".mcp.json", "AIzaSyDExampleExampleExampleExample12345", "value"),
            (".mcp.json", "ya29.a0AfH6SMBExampleExampleExampleExample", "value"),
        )
        contents = [
            (path, secret, key, f'{{"{key}":"{secret}"}}') for path, secret, key in cases
        ]
        # A CLI flag followed by its value in a JSON args array.
        for flag in ("--aws-secret-access-key", "--secret-access-key"):
            contents.append(
                (".mcp.json", aws_secret, flag, f'{{"args": ["{flag}", "{aws_secret}"]}}')
            )
        for path, secret, key, content in contents:
            with self.subTest(path=path, secret=secret[:8], key=key):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    write_payload(path, content),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, path)
                assert decision is not None
                reason = str(decision.get("reason", ""))
                self.assertIn("<redacted>", reason)
                self.assertNotIn(secret, reason)


    def test_mcp_secret_scan_allows_benign_config_writes(self) -> None:
        benign = '{"mcpServers":{"local":{"command":"node","args":["server.js"]}}}'
        for path in (".mcp.json", ".vscode/mcp.json", ".cursor/mcp.json"):
            with self.subTest(path=path):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    write_payload(path, benign),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        # 40-character git SHAs, hex digests, and other runs without an AWS
        # secret key name are not AWS secret keys.
        sha = "3f786850e387550fdab836ed7e6dc881de23001b"
        for content in (
            '{"mcpServers":{"tool":{"command":"npx",'
            f'"args":["github:org/tool#{sha}"]}}}}}}',
            f'{{"integrity":{{"sha1":"{sha}"}}}}',
            f'{{"args": ["--revision", "{sha}"]}}',
            '{"value":"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}',
        ):
            with self.subTest(content=content[:40]):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    write_payload(".mcp.json", content),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)

        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload("cat > .mcp.json <<'EOF'\n{}\nEOF"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload(
                "cat <<'EOF'; echo '{}' > .mcp.json\n"
                "sk-ant-abcdefghijklmnopqrstuvwxyz\n"
                "EOF"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)


    def test_mcp_secret_scan_blocks_unknown_bash_mcp_writes_and_redacts_paths(self) -> None:
        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload("cp /private/source.json .mcp.json"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "could not inspect")

        for command in (
            "cp /private/.mcp.json .",
            "mv /tmp/.mcp.json .",
            "install /tmp/.mcp.json .",
        ):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "could not inspect")

        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload(
                "cat > /Users/example/project/.vscode/mcp.json <<'EOF'\n"
                '{"apiKey":"sk-ant-abcdefghijklmnopqrstuvwxyz"}\n'
                "EOF"
            ),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, ".vscode/mcp.json")
        assert decision is not None
        self.assertNotIn("/Users/example", str(decision.get("reason", "")))


    def test_mcp_secret_scan_blocks_generated_and_ordered_unknown_bash_writes(self) -> None:
        commands = (
            "printf '%s%s\\n' 'sk-ant-' 'abcdefghijklmnopqrstuvwxyz' > .mcp.json",
            "printf '%s%s\\n' 'sk-ant-' 'abcdefghijklmnopqrstuvwxyz' | tee .mcp.json",
            "cat > .mcp.json <<'EOF'\n{}\nEOF\ncp /private/source.json .mcp.json",
            "curl -fsSL -o .mcp.json https://example.invalid/mcp.json",
            "curl --output=.vscode/mcp.json https://example.invalid/mcp.json",
            "curl --remote-name https://example.invalid/.mcp.json",
            "curl --remote-name --output-dir .vscode https://example.invalid/mcp.json",
            "curl --url=https://example.invalid/.mcp.json --remote-name",
            "curl --output-dir .vscode --url https://example.invalid/mcp.json -O",
            "wget -O .cursor/mcp.json https://example.invalid/mcp.json",
            "wget --output-document=.mcp.json https://example.invalid/mcp.json",
            "wget -O.mcp.json https://example.invalid/mcp.json",
            "wget https://example.invalid/.mcp.json",
            "wget -P .vscode https://example.invalid/mcp.json",
            "wget --directory-prefix=.vscode https://example.invalid/mcp.json",
            "cat > .mcp.json <<'EOF'\n{}\nEOF\nnode generate-secret.js > .mcp.json",
            "cat > .mcp.json <<'EOF'\n{}\nEOF\nnode generate-secret.js 2> .mcp.json",
            "cat > .mcp.json <<'EOF'\n{}\nEOF\nnode generate-secret.js 2>>.mcp.json",
            "cat > .mcp.json <<'EOF'\n{}\nEOF\nnode generate-secret.js &>.mcp.json",
            "cat > .mcp.json <<'EOF'\n{}\nEOF\nnode generate-secret.js &>>.mcp.json",
            "node generate-secret.js >| .mcp.json",
            "node generate-secret.js >|.mcp.json",
            "bash > .mcp.json <<'EOF'\n"
            "printf '%s%s\\n' 'sk-ant-' 'abcdefghijklmnopqrstuvwxyz'\n"
            "EOF",
            "bash >| .mcp.json <<'EOF'\n"
            "printf '%s%s\\n' 'sk-ant-' 'abcdefghijklmnopqrstuvwxyz'\n"
            "EOF",
            "MCP_TOKEN=sk-ant-abcdefghijklmnopqrstuvwxyz; cat > .mcp.json <<EOF\n"
            '{"apiKey":"$MCP_TOKEN"}\n'
            "EOF",
            "printf '\\x73\\x6b-ant-abcdefghijklmnopqrstuvwxyz' > .mcp.json",
            "echo -e '\\x73\\x6b-ant-abcdefghijklmnopqrstuvwxyz' > .mcp.json",
        )
        for command in commands:
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "mcp-secret-scan.py",
                    command_payload(command),
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "could not inspect")

        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload("printf '{}' > .mcp.json"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_allowed(decision)

        code, decision, stderr = run_hook(
            "mcp-secret-scan.py",
            command_payload("printf '$MCP_TOKEN' > .mcp.json"),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "could not inspect")


    def test_command_match_requires_declared_shell_heredoc_body(self) -> None:
        declared = "bash <<'EOF'\nbash scripts/ci/all.sh\nEOF"
        self.assertTrue(command_matches_validation(declared, declared))
        self.assertFalse(
            command_matches_validation("bash <<'EOF'\necho skip\nEOF", declared)
        )


    def test_command_match_shell_heredoc_parser_edge_cases(self) -> None:
        # Regression for the four PR #359 follow-up parser edge cases
        # (agent-runtime-kit#360). Each `actual` carries the validation command
        # inside a here-doc body; the body is credited only when bash actually
        # executes it as stdin script content.
        declared = "bash scripts/ci/all.sh"
        validation = "bash scripts/ci/all.sh"

        # Bodies bash does NOT execute as its script -> must not credit the gate.
        not_executed = (
            # GNU long option must not be scanned as compact `-s`; bash runs the
            # script-file operand and the here-doc is its stdin data.
            f"bash --posix ./script.sh <<'EOF'\n{validation}\nEOF",
            # A long option consumes its own filename argument; the later token
            # is the script file, so the body is still data.
            f"bash --rcfile ./rc ./script.sh <<'EOF'\n{validation}\nEOF",
            # Script-file operand AFTER the `<<` operator: invisible to a
            # prefix-only tokenizer, so the body looks executed when it is data.
            f"bash <<'EOF' ./script.sh\n{validation}\nEOF",
            # A later stdin input redirection overrides the here-doc.
            f"bash <<'EOF' < ./script.sh\n{validation}\nEOF",
            # `-n` is noexec: the body is parsed but never run.
            f"bash -n <<'EOF'\n{validation}\nEOF",
            # noexec must win even when `-s` also forces stdin as the script.
            f"bash -sn <<'EOF'\n{validation}\nEOF",
            # A second stdin here-doc overrides the first; neither body is the
            # reliably executed script, so both are dropped.
            f"bash <<'A' <<'EOF'\n{validation}\nA\nfoo\nEOF",
            # Explicit non-stdin descriptor: fd 3 is not the shell's script.
            f"bash -s 3<<'EOF'\n{validation}\nEOF",
            # PR #361 follow-up: an option that requires a filename argument
            # cannot bind the here-doc operator as that argument -- bash aborts
            # with "option requires an argument" and never runs the body.
            f"bash --rcfile <<'EOF'\n{validation}\nEOF",
            f"bash --init-file <<'EOF'\n{validation}\nEOF",
            # An unknown shopt name aborts before stdin is executed.
            f"bash -O does_not_exist <<'EOF'\n{validation}\nEOF",
            f"bash +O does_not_exist <<'EOF'\n{validation}\nEOF",
            # PR #368 follow-up: keep version-specific shopt names out of the
            # parser's portable safe set. Bash 5.2 and older reject these names
            # before reading stdin, so crediting them is unsafe even if a newer
            # local bash accepts them.
            f"bash -O array_expand_once <<'EOF'\n{validation}\nEOF",
            f"bash -O bash_source_fullpath <<'EOF'\n{validation}\nEOF",
            # Issue #377: these invocation options print metadata/help and exit
            # before reading stdin, so the here-doc body is never executed.
            f"bash --version <<'EOF'\n{validation}\nEOF",
            f"bash --help <<'EOF'\n{validation}\nEOF",
            f"bash --usage <<'EOF'\n{validation}\nEOF",
            # Issue #381: value-suffixed metadata options also exit before
            # reading stdin. Bash rejects them as invalid long options, so the
            # here-doc body must not satisfy declared validation.
            f"bash --version=1 <<'EOF'\n{validation}\nEOF",
            f"bash --help=1 <<'EOF'\n{validation}\nEOF",
            f"bash --usage=1 <<'EOF'\n{validation}\nEOF",
        )
        for actual in not_executed:
            with self.subTest(actual=actual):
                self.assertFalse(command_matches_validation(actual, declared))

        # Bodies bash DOES execute as its script -> must credit the gate.
        executed = (
            # Bare stdin here-doc: the body is the script.
            f"bash <<'EOF'\n{validation}\nEOF",
            # `-s` forces stdin as the script; trailing tokens are positional
            # args to it, not a competing script file, so the body still runs.
            f"bash -s <<'EOF' arg1\n{validation}\nEOF",
            # Explicit stdin descriptor really feeds and runs the body.
            f"bash 0<<'EOF'\n{validation}\nEOF",
            # PR #361 follow-up: `+n` turns the noexec flag back off, so a `-s`
            # invocation still runs the here-doc body as its script.
            f"bash -s +n <<'EOF'\n{validation}\nEOF",
            # `+n` alone leaves noexec off and stdin is the script.
            f"bash +n <<'EOF'\n{validation}\nEOF",
            # PR #368 follow-up: bare `-O`/`+O` list shopt state, then stdin is
            # still the script. Valid shopt names are consumed and stdin still
            # runs when no script-file operand follows.
            f"bash -O <<'EOF'\n{validation}\nEOF",
            f"bash +O <<'EOF'\n{validation}\nEOF",
            # `-O shopt` consumes its own name argument, leaving no script-file
            # operand, so stdin (the body) is the executed script.
            f"bash -O extglob <<'EOF'\n{validation}\nEOF",
            f"bash +O extglob <<'EOF'\n{validation}\nEOF",
            # PR #368 follow-up: `+s` still leaves stdin as the script; trailing
            # operands are positional args to that script, not script files.
            f"bash +s arg <<'EOF'\n{validation}\nEOF",
            # A word-argument option can receive its argument after a here-doc
            # redirection on the same shell command line. The shell removes the
            # redirection and still passes `-s` as the option argument.
            f"bash --rcfile <<'EOF' -s\n{validation}\nEOF",
            f"bash --init-file <<'EOF' -s\n{validation}\nEOF",
        )
        for actual in executed:
            with self.subTest(actual=actual):
                self.assertTrue(command_matches_validation(actual, declared))


    def test_command_match_non_bash_heredoc_executor_edge_cases(self) -> None:
        # Regression for the PR #371 follow-up parser edge cases
        # (graysurf/agent-runtime-kit#371 review threads). The earlier rewrite
        # applied Bash-only invocation grammar uniformly to every shell in
        # SHELL_HEREDOC_EXECUTORS, so a POSIX `sh`/`dash` invocation -- or an
        # exotic Bash ordering -- could be credited even though the shell would
        # never run the here-doc body as its script. The unsafe direction is a
        # false credit, so each of these must NOT credit the gate.
        declared = "bash scripts/ci/all.sh"
        validation = "bash scripts/ci/all.sh"

        not_executed = (
            # `+s` only leaves stdin as the script on Bash. For dash/sh the
            # documented stdin-script form is `-s`; `+s arg` opens `arg` as a
            # command file and never reads stdin, so the body is data.
            f"sh +s arg <<'EOF'\n{validation}\nEOF",
            f"dash +s arg <<'EOF'\n{validation}\nEOF",
            # `--rcfile` / `--init-file` are Bash-only long options. A POSIX
            # sh/dash aborts on the unknown option before reading stdin.
            f"sh --rcfile <<'EOF' -s\n{validation}\nEOF",
            f"sh --init-file <<'EOF' -s\n{validation}\nEOF",
            f"dash --rcfile <<'EOF' -s\n{validation}\nEOF",
            # `-O` / `+O` shopt options are Bash-only; dash/sh exit on the
            # illegal option before stdin is read.
            f"sh -O extglob <<'EOF'\n{validation}\nEOF",
            f"sh +O extglob <<'EOF'\n{validation}\nEOF",
            f"dash -O extglob <<'EOF'\n{validation}\nEOF",
            # A GNU long option after a single-character option is rejected by
            # Bash before stdin is read (long options must precede short ones),
            # so a late `--rcfile` must not be credited.
            f"bash -O extglob --rcfile <<'EOF' -s\n{validation}\nEOF",
            f"bash -e --rcfile rc <<'EOF'\n{validation}\nEOF",
            # PR #373 review follow-up (P1): an output-redirection-shaped token
            # is never a safe `--rcfile`/`--init-file` word argument. An unquoted
            # `>out` is a real redirection bash removes, leaving the option with
            # no argument so it aborts before reading stdin; a quoted `'>foo'` is
            # indistinguishable from it after `shell_tokens` strips the quotes.
            # Either way the conservative reading refuses to credit the body.
            # The redirect-shape refusal covers every output operator
            # `_REDIRECT_TOKEN_RE` matches in the arg slot, including a
            # fd-prefixed one (`2>log`), not just the literal `>` spelling.
            f"bash --rcfile >out <<'EOF'\n{validation}\nEOF",
            f"bash --init-file >>log <<'EOF'\n{validation}\nEOF",
            f"bash --rcfile > out <<'EOF'\n{validation}\nEOF",
            f"bash --rcfile 2>log <<'EOF'\n{validation}\nEOF",
            f"bash --rcfile '>foo' <<'EOF' ./script.sh\n{validation}\nEOF",
            # The same refusal fires without a trailing operand: here the new
            # redirect-shape check is the only thing that makes the body data.
            f"bash --rcfile '>foo' <<'EOF'\n{validation}\nEOF",
            # A non-bash, non-zsh long option still aborts before stdin runs;
            # zsh's long-option grammar must not leak to dash/sh/ksh. `ksh` is
            # folded into the POSIX reject path, so its long options are refused.
            f"dash --no-rcs <<'EOF'\n{validation}\nEOF",
            f"ksh --no-rcs <<'EOF'\n{validation}\nEOF",
            # A zsh long option followed by a script-file operand runs that file,
            # so stdin is data, not the executed script.
            f"zsh --no-rcs ./script.sh <<'EOF'\n{validation}\nEOF",
            # Broadening zsh long options must not re-credit a `-c`/`--command`
            # invocation, whose script is the command string, not the here-doc.
            f"zsh -c 'true' <<'EOF'\n{validation}\nEOF",
            f"zsh --command 'true' <<'EOF'\n{validation}\nEOF",
            # Only the allowlisted zsh startup-file toggles are credited. Other
            # zsh long options are refused because real zsh (5.9) does not run
            # the here-doc body: `--noexec`/`--no-exec` parse but do not execute
            # it, `--version`/`--help` exit first, `--emulate` needs a word
            # argument, and an unknown name aborts with "no such option".
            f"zsh --noexec <<'EOF'\n{validation}\nEOF",
            f"zsh --no-exec <<'EOF'\n{validation}\nEOF",
            f"zsh --version <<'EOF'\n{validation}\nEOF",
            f"zsh --help <<'EOF'\n{validation}\nEOF",
            f"zsh --emulate sh <<'EOF'\n{validation}\nEOF",
            f"zsh --not-a-real-option <<'EOF'\n{validation}\nEOF",
            # PR #376 review follow-up: a zsh long option is credited only before
            # any short option. Some zsh short options end option processing
            # (`-b`, a cluster ending in `-` like `-x-`), turning a following
            # `--no-rcs` into a script-file operand whose stdin (the body) is
            # DATA -- verified against zsh 5.9, which reports "can't open input
            # file: --no-rcs". A long option after any short flag is therefore
            # refused as the safe direction (this also conservatively drops the
            # benign `zsh -f --no-rcs`, where real zsh would run the body).
            f"zsh -b --no-rcs <<'EOF'\n{validation}\nEOF",
            f"zsh -x- --no-rcs <<'EOF'\n{validation}\nEOF",
            f"zsh -bf --no-rcs <<'EOF'\n{validation}\nEOF",
            f"zsh -f --no-rcs <<'EOF'\n{validation}\nEOF",
        )
        for actual in not_executed:
            with self.subTest(actual=actual):
                self.assertFalse(command_matches_validation(actual, declared))

        # Legitimate POSIX-shell here-doc scripts must still credit the gate.
        executed = (
            f"sh <<'EOF'\n{validation}\nEOF",
            f"dash <<'EOF'\n{validation}\nEOF",
            # `-s` forces stdin-as-script on every POSIX shell.
            f"sh -s <<'EOF'\n{validation}\nEOF",
            # A leading short flag still leaves stdin as the script.
            f"sh -e <<'EOF'\n{validation}\nEOF",
            # A Bash word-argument option still binds its argument after the
            # here-doc redirection when it is the first option.
            f"bash --rcfile <<'EOF' -s\n{validation}\nEOF",
            # A real `--rcfile <file>` argument binds normally; stdin stays the
            # script when no script-file operand follows.
            f"bash --rcfile rc.sh <<'EOF'\n{validation}\nEOF",
            # PR #373 review follow-up (P2): zsh accepts an allowlist of
            # startup-file toggle long options (--rcs/--no-rcs/--globalrcs/
            # --no-globalrcs) that still run stdin as the script, so a real
            # `zsh --no-rcs <<EOF` validation -- including the enable spelling
            # and a chain of long options -- must be credited.
            f"zsh --no-rcs <<'EOF'\n{validation}\nEOF",
            f"zsh --no-globalrcs --no-rcs <<'EOF'\n{validation}\nEOF",
            f"zsh --rcs <<'EOF'\n{validation}\nEOF",
        )
        for actual in executed:
            with self.subTest(actual=actual):
                self.assertTrue(command_matches_validation(actual, declared))


    def test_command_match_does_not_credit_indirect_heredoc_text(self) -> None:
        declared = "bash scripts/ci/all.sh"
        for actual in (
            f"source /dev/stdin <<'EOF'\n{declared}\nEOF",
            f". /dev/fd/0 <<'EOF'\n{declared}\nEOF",
            f"cat <<'EOF' | bash\n{declared}\nEOF",
            f"(cat <<'EOF'\n{declared}\nEOF\n) | sh",
            f"bash <(cat <<'EOF'\n{declared}\nEOF\n)",
            f"cat <<'EOF' > x.sh\n{declared}\nEOF\nbash x.sh",
        ):
            with self.subTest(actual=actual):
                self.assertFalse(command_matches_validation(actual, declared))


    def test_effective_workdir_resolves_codex_and_claude_envelopes(self) -> None:
        """P0-4: the shared resolver agrees with a tool call's real workdir.

        It fans out across the union of Codex and Claude envelope shapes so every
        guard resolves the same effective working directory instead of the hook
        process cwd.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            # `command_context` canonicalizes, as any guard comparing a workdir
            # against a repo root must. Compare against the canonical spelling,
            # or this asserts nothing wherever $TMPDIR has a symlinked ancestor
            # (macOS resolves /var to /private/var).
            target = target.resolve()

            # 1. Every recognized workdir spelling in tool_input.
            for key in (
                "workdir",
                "cwd",
                "current_working_directory",
                "working_directory",
            ):
                with self.subTest(key=key):
                    payload = {
                        "tool_name": "Bash",
                        "tool_input": {"command": "x", key: str(target)},
                    }
                    self.assertEqual(effective_workdir(payload), target)

            # 2. A workdir key nested anywhere in tool_input.
            nested = {
                "tool_name": "Bash",
                "tool_input": {"command": "x", "shell": {"working_directory": str(target)}},
            }
            self.assertEqual(effective_workdir(nested), target)

            # 3. Codex transcript: workdir lives in the exec_command arguments,
            #    referenced by call_id == tool_use_id.
            transcript = root / "transcript.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "payload": {
                            "call_id": "call-1",
                            "arguments": json.dumps(
                                {"command": ["bash", "-lc", "x"], "workdir": str(target)}
                            ),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            transcript_payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "x"},
                "tool_use_id": "call-1",
                "transcript_path": str(transcript),
            }
            self.assertEqual(effective_workdir(transcript_payload), target)

            # 4. Codex custom-tool transcripts wrap exec_command in the
            #    JavaScript orchestration input rather than exposing the legacy
            #    `arguments` field. Accept only its strict JSON argument object.
            custom_transcript = root / "custom-transcript.jsonl"
            custom_transcript.write_text(
                json.dumps(
                    {
                        "payload": {
                            "type": "custom_tool_call",
                            "name": "exec",
                            "call_id": "custom-call-1",
                            "input": (
                                "const r = await tools.exec_command("
                                + json.dumps(
                                    {
                                        "cmd": "printf x",
                                        "workdir": str(target),
                                    }
                                )
                                + ");\ntext(r.output);\n"
                            ),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            custom_payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "printf x"},
                "tool_use_id": "custom-call-1",
                "transcript_path": str(custom_transcript),
            }
            self.assertEqual(effective_workdir(custom_payload), target)

            # The code-mode exec surface may prefix the same canonical wrapper
            # with one strict-JSON execution pragma. It is provider metadata,
            # not arbitrary JavaScript, and must not discard the call workdir.
            pragma_transcript = root / "pragma-custom-transcript.jsonl"
            pragma_transcript.write_text(
                json.dumps(
                    {
                        "payload": {
                            "type": "custom_tool_call",
                            "name": "exec",
                            "call_id": "pragma-custom-call-1",
                            "input": (
                                '// @exec: {"yield_time_ms": 30000}\n'
                                "const r = await tools.exec_command("
                                + json.dumps(
                                    {
                                        "cmd": "printf x",
                                        "workdir": str(target),
                                    }
                                )
                                + ");\ntext(r.output);\n"
                            ),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                effective_workdir(
                    {
                        "tool_name": "Bash",
                        "tool_input": {"command": "printf x"},
                        "tool_use_id": "pragma-custom-call-1",
                        "transcript_path": str(pragma_transcript),
                    }
                ),
                target,
            )

            # 5. The transcript workdir wins over the top-level session cwd.
            transcript_payload["cwd"] = str(root)
            self.assertEqual(effective_workdir(transcript_payload), target)

            # 6. Top-level cwd fallback (Claude session envelope).
            self.assertEqual(
                effective_workdir(
                    {"tool_name": "Bash", "tool_input": {"command": "x"}, "cwd": str(target)}
                ),
                target,
            )

            # 7. A relative workdir resolves against the hook process cwd.
            self.assertEqual(
                effective_workdir(
                    {"tool_name": "Bash", "tool_input": {"command": "x", "workdir": "sub"}}
                ),
                Path.cwd() / "sub",
            )

            # 8. Nothing declared → the hook process cwd.
            self.assertEqual(
                effective_workdir({"tool_name": "Bash", "tool_input": {"command": "x"}}),
                Path.cwd(),
            )


    def test_effective_workdir_transcript_read_is_bounded_and_fail_soft(self) -> None:
        """P0-4 hardening: the transcript read never crashes a fail-closed guard.

        A missing, malformed, or huge transcript resolves to the ordinary
        fallback rather than raising, and the newest matching event still wins
        after many preceding lines (reverse/tail scan).
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            target = target.resolve()  # see the sibling test: the resolver canonicalizes

            # Missing transcript -> fail soft to the top-level cwd fallback.
            missing = {
                "tool_name": "Bash",
                "tool_input": {"command": "x"},
                "tool_use_id": "miss-1",
                "transcript_path": str(root / "nope.jsonl"),
                "cwd": str(target),
            }
            self.assertEqual(effective_workdir(missing), target)

            # Malformed transcript -> fail soft to the cwd fallback (no crash).
            bad = root / "bad.jsonl"
            bad.write_text("not json\n{also not json\n", encoding="utf-8")
            malformed = {
                "tool_name": "Bash",
                "tool_input": {"command": "x"},
                "tool_use_id": "bad-1",
                "transcript_path": str(bad),
                "cwd": str(target),
            }
            self.assertEqual(effective_workdir(malformed), target)

            # The newest matching event wins after many preceding lines.
            busy = root / "busy.jsonl"
            lines = [
                json.dumps({"payload": {"call_id": "other", "arguments": "{}"}})
                for _ in range(200)
            ]
            lines.append(
                json.dumps(
                    {
                        "payload": {
                            "call_id": "busy-1",
                            "arguments": json.dumps({"workdir": str(target)}),
                        }
                    }
                )
            )
            busy.write_text("\n".join(lines) + "\n", encoding="utf-8")
            busy_payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "x"},
                "tool_use_id": "busy-1",
                "transcript_path": str(busy),
            }
            self.assertEqual(effective_workdir(busy_payload), target)


    def test_effective_workdir_rejects_untrusted_custom_exec_shapes(self) -> None:
        resolver = getattr(hook_common, "command_context", None)
        self.assertTrue(callable(resolver), "command_context resolver is missing")
        assert callable(resolver)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            cases = (
                (
                    "javascript-object",
                    f"const r = await tools.exec_command({{workdir: '{target}'}});",
                ),
                (
                    "string-bait",
                    "const bait = \"await tools.exec_command("
                    + json.dumps({"workdir": str(target)})
                    + ")\";",
                ),
                (
                    "multiple-calls",
                    "const r = await tools.exec_command("
                    + json.dumps({"cmd": "x", "workdir": str(target)})
                    + "); tools.exec_command("
                    + json.dumps({"cmd": "y", "workdir": str(target)})
                    + ");",
                ),
                (
                    "multiple-calls-spaced",
                    "const r = await tools.exec_command("
                    + json.dumps({"cmd": "x", "workdir": str(target)})
                    + "); await tools.exec_command ("
                    + json.dumps({"cmd": "y", "workdir": str(root)})
                    + ");",
                ),
                (
                    "nested-workdir-bait",
                    "const r = await tools.exec_command("
                    + json.dumps(
                        {
                            "cmd": "x",
                            "metadata": {"workdir": str(target)},
                        }
                    )
                    + ");",
                ),
                (
                    "non-string-command",
                    "const r = await tools.exec_command("
                    + json.dumps(
                        {
                            "cmd": {"workdir": str(target)},
                            "workdir": str(target),
                        }
                    )
                    + ");",
                ),
                # The object-literal subset admits only JSON-compatible scalar
                # values, identifier or JSON keys, and names bound by a leading
                # `const NAME = "<JSON string>"`. Everything else stays opaque.
                (
                    "unbound-identifier",
                    'const r = await tools.exec_command({cmd: "x", workdir: w});',
                ),
                (
                    "duplicate-key",
                    'const r = await tools.exec_command({cmd: "x", workdir: '
                    + json.dumps(str(root))
                    + ', "workdir": '
                    + json.dumps(str(target))
                    + "});",
                ),
                (
                    "template-literal",
                    "const r = await tools.exec_command({cmd: `x`, workdir: `"
                    + str(target)
                    + "`});",
                ),
                (
                    "computed-key",
                    'const k = "workdir"; const r = await tools.exec_command('
                    '{cmd: "x", [k]: '
                    + json.dumps(str(target))
                    + "});",
                ),
                (
                    "spread",
                    "const r = await tools.exec_command({...o, cmd: \"x\", "
                    "workdir: "
                    + json.dumps(str(target))
                    + "});",
                ),
                (
                    "comment",
                    'const r = await tools.exec_command({cmd: "x", /* c */ '
                    "workdir: "
                    + json.dumps(str(target))
                    + "});",
                ),
                (
                    "javascript-only-escape",
                    'const r = await tools.exec_command({cmd: "x", workdir: "'
                    + str(target)
                    + '\\x41"});',
                ),
                (
                    "nested-object-value",
                    'const r = await tools.exec_command({cmd: "x", workdir: '
                    + json.dumps(str(target))
                    + ', env: {A: "b"}});',
                ),
                (
                    "let-binding",
                    "let w = "
                    + json.dumps(str(target))
                    + '; const r = await tools.exec_command({cmd: "x", '
                    "workdir: w});",
                ),
                (
                    "multi-declarator",
                    'const a = "x", w = '
                    + json.dumps(str(target))
                    + '; const r = await tools.exec_command({cmd: "x", '
                    "workdir: w});",
                ),
                (
                    "reassigned-binding",
                    "const w = "
                    + json.dumps(str(root))
                    + "; w = "
                    + json.dumps(str(target))
                    + '; const r = await tools.exec_command({cmd: "x", '
                    "workdir: w});",
                ),
                (
                    "statement-after-call",
                    'const r = await tools.exec_command({cmd: "x", workdir: '
                    + json.dumps(str(target))
                    + '}); await tools.exec_command({cmd: "y"});',
                ),
                (
                    "rendered-call-then-call",
                    'text(await tools.exec_command({cmd: "x", workdir: '
                    + json.dumps(str(target))
                    + '})); await tools.exec_command({cmd: "y"});',
                ),
                (
                    "rendered-call-member",
                    'text(await tools.exec_command({cmd: "x", workdir: '
                    + json.dumps(str(target))
                    + "}).output);",
                ),
                (
                    "stringify-with-arguments",
                    'const r = await tools.exec_command({cmd: "x", workdir: '
                    + json.dumps(str(target))
                    + "}); text(JSON.stringify(r, null, tools));",
                ),
                (
                    "binding-shadows-declaration",
                    "const r = "
                    + json.dumps(str(root))
                    + '; const r = await tools.exec_command({cmd: "x", '
                    "workdir: r});",
                ),
                (
                    "parallel-calls",
                    "const r = await Promise.allSettled([tools.exec_command("
                    '{cmd: "x", workdir: '
                    + json.dumps(str(target))
                    + '}), tools.exec_command({cmd: "y", workdir: '
                    + json.dumps(str(target))
                    + "})]);",
                ),
            )
            for call_id, source in cases:
                with self.subTest(call_id=call_id):
                    transcript = root / f"{call_id}.jsonl"
                    transcript.write_text(
                        json.dumps(
                            {
                                "payload": {
                                    "type": "custom_tool_call",
                                    "name": "exec",
                                    "call_id": call_id,
                                    "input": source,
                                }
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    context = resolver(
                        {
                            "tool_name": "Bash",
                            "tool_input": {"command": "x"},
                            "tool_use_id": call_id,
                            "transcript_path": str(transcript),
                            "cwd": str(root),
                        }
                    )
                    self.assertEqual(context.path, root.resolve())
                    self.assertEqual(context.source, "session-cwd")
                    self.assertFalse(context.attested)
                    self.assertEqual(
                        context.diagnostic, "workdir-attestation-missing"
                    )


    def test_effective_workdir_reads_literal_custom_exec_objects(self) -> None:
        # Codex code-mode calls are written as JavaScript object literals far
        # more often than as strict JSON. A literal whose keys are identifiers
        # or JSON strings, whose values are JSON scalars, and whose names are
        # bound by a leading `const NAME = "<JSON string>"` still names exactly
        # one workdir. Rejecting it attested the session checkout instead.
        resolver = getattr(hook_common, "command_context", None)
        self.assertTrue(callable(resolver), "command_context resolver is missing")
        assert callable(resolver)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            quoted = json.dumps(str(target))
            cases = (
                (
                    "identifier-keys",
                    "const r = await tools.exec_command({\n"
                    '  cmd: "git status --short",\n'
                    f"  workdir: {quoted},\n"
                    "  yield_time_ms: 10000,\n"
                    "  max_output_tokens: 3000\n"
                    "});\ntext(r.output);\n",
                ),
                (
                    "const-binding",
                    f"const w={quoted};const r=await tools.exec_command("
                    '{cmd:"semantic-commit commit --format json",workdir:w,'
                    "yield_time_ms:30000,max_output_tokens:2000});text(r);\n",
                ),
                (
                    "mixed-keys-trailing-comma",
                    'const r = await tools.exec_command({cmd:"x","workdir":'
                    f'{quoted},"tty":false,"login":null,}});',
                ),
                (
                    "pragma-newline-binding",
                    '// @exec: {"yield_time_ms": 1000}\n'
                    f"const base = {quoted}\n"
                    'const r = await tools.exec_command({cmd: "x", '
                    "workdir: base});\n",
                ),
                (
                    "stringified-result",
                    'const r = await tools.exec_command({cmd: "x", workdir: '
                    f"{quoted}}});\ntext(JSON.stringify(r));\n",
                ),
                (
                    "rendered-call",
                    'text(await tools.exec_command({cmd:"x",workdir:'
                    f"{quoted},max_output_tokens:1500}}));",
                ),
                (
                    "rendered-grouped-output",
                    f"const w={quoted};text((await tools.exec_command("
                    '{cmd:"x",workdir:w})).output);\n',
                ),
            )
            for call_id, source in cases:
                with self.subTest(call_id=call_id):
                    transcript = root / f"{call_id}.jsonl"
                    transcript.write_text(
                        json.dumps(
                            {
                                "payload": {
                                    "type": "custom_tool_call",
                                    "name": "exec",
                                    "call_id": call_id,
                                    "input": source,
                                }
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    context = resolver(
                        {
                            "tool_name": "Bash",
                            "tool_input": {"command": "x"},
                            "tool_use_id": call_id,
                            "transcript_path": str(transcript),
                            "cwd": str(root),
                        }
                    )
                    self.assertEqual(context.path, target.resolve())
                    self.assertEqual(context.source, "matching-transcript-call")
                    self.assertTrue(context.attested)
                    self.assertIsNone(context.diagnostic)


    def test_custom_exec_malformed_remainder_is_rejected_in_linear_time(
        self,
    ) -> None:
        source = (
            "const r = await tools.exec_command("
            + json.dumps({"cmd": "x", "workdir": "/tmp"})
            + ")"
            + (" " * 12_000)
            + "unexpected"
        )
        started = time.monotonic()
        arguments, diagnostic = hook_common._custom_exec_arguments(
            {
                "type": "custom_tool_call",
                "name": "exec",
                "input": source,
            }
        )
        elapsed = time.monotonic() - started
        self.assertIsNone(arguments)
        self.assertEqual(diagnostic, "transcript-custom-input-ambiguous")
        self.assertLess(elapsed, 0.5)


    def test_command_context_records_workdir_provenance_and_attestation(self) -> None:
        """Cross-repository gating retains where the canonical target came from."""
        resolver = getattr(hook_common, "command_context", None)
        self.assertTrue(callable(resolver), "command_context resolver is missing")
        assert callable(resolver)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()

            inline = resolver(
                command_payload("touch out", workdir=str(target))
            )
            self.assertEqual(inline.path, target.resolve())
            self.assertEqual(inline.source, "tool-input")
            self.assertTrue(inline.attested)
            self.assertIsNone(inline.diagnostic)

            transcript = root / "transcript.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "payload": {
                            "call_id": "context-call",
                            "arguments": json.dumps(
                                {"command": "touch out", "workdir": str(target)}
                            ),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            transcript_context = resolver(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "touch out"},
                    "tool_use_id": "context-call",
                    "transcript_path": str(transcript),
                    "cwd": str(root),
                }
            )
            self.assertEqual(transcript_context.path, target.resolve())
            self.assertEqual(transcript_context.source, "matching-transcript-call")
            self.assertTrue(transcript_context.attested)

            mismatched = resolver(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "touch out"},
                    "tool_use_id": "different-call",
                    "transcript_path": str(transcript),
                    "cwd": str(root),
                }
            )
            self.assertEqual(mismatched.path, root.resolve())
            self.assertEqual(mismatched.source, "session-cwd")
            self.assertFalse(mismatched.attested)
            self.assertEqual(mismatched.diagnostic, "workdir-attestation-missing")

            missing_call_id = resolver(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "touch out"},
                    "transcript_path": str(transcript),
                    "cwd": str(root),
                }
            )
            self.assertEqual(missing_call_id.source, "session-cwd")
            self.assertFalse(missing_call_id.attested)
            self.assertEqual(
                missing_call_id.diagnostic, "workdir-attestation-missing"
            )

            payload_metadata = resolver(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "touch out"},
                    "host": {"working_directory": str(target)},
                }
            )
            self.assertEqual(payload_metadata.source, "payload")
            self.assertTrue(payload_metadata.attested)

            relative = resolver(command_payload("touch out", workdir="target"))
            self.assertEqual(relative.source, "tool-input")
            self.assertFalse(relative.attested)
            self.assertEqual(relative.diagnostic, "workdir-attestation-missing")

            claude = resolver(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "touch out"},
                    "cwd": str(target),
                }
            )
            self.assertEqual(claude.source, "session-cwd")
            self.assertTrue(claude.attested)

            with mock.patch.object(hook_common.Path, "cwd", return_value=target):
                process = resolver(command_payload("touch out"))
            self.assertEqual(process.path, target.resolve())
            self.assertEqual(process.source, "process-cwd")
            self.assertFalse(process.attested)
            self.assertEqual(process.diagnostic, "workdir-attestation-missing")

            managed_state = root / "agent-session-state"
            managed_id = "managed-claude"
            managed_dir = managed_state / "sessions" / managed_id
            managed_dir.mkdir(parents=True)
            (managed_dir / "session.json").write_text(
                json.dumps(
                    {
                        "id": managed_id,
                        "agent": "claude",
                        "cwd": str(target),
                        "runtime": {"launch_id": "managed-launch"},
                        "startup": {"state": "ready"},
                    }
                ),
                encoding="utf-8",
            )
            (managed_dir / "session.json").chmod(0o600)
            managed_env = {
                "AGENT_SESSION_ID": managed_id,
                "AGENT_SESSION_STATE_DIR": str(managed_state),
                "AGENT_SESSION_RUNTIME_ID": "managed-launch",
                "AGENT_RUNTIME_PRODUCT": "claude",
            }
            with (
                mock.patch.dict(os.environ, managed_env, clear=False),
                mock.patch.object(hook_common.Path, "cwd", return_value=target),
            ):
                managed = resolver(command_payload("touch out"))
            self.assertEqual(managed.path, target.resolve())
            self.assertEqual(managed.source, "managed-session-cwd")
            self.assertTrue(managed.attested)
            self.assertIsNone(managed.diagnostic)

            with (
                mock.patch.dict(os.environ, managed_env, clear=False),
                mock.patch.object(hook_common.Path, "cwd", return_value=target),
            ):
                managed_before_transcript_flush = resolver(
                    {
                        "tool_name": "Bash",
                        "tool_input": {"command": "touch out"},
                        "tool_use_id": "not-yet-flushed",
                        "transcript_path": str(transcript),
                        "cwd": str(target),
                    }
                )
            self.assertEqual(
                managed_before_transcript_flush.source, "managed-session-cwd"
            )
            self.assertTrue(managed_before_transcript_flush.attested)
            self.assertIsNone(managed_before_transcript_flush.diagnostic)
            self.assertFalse(
                managed_before_transcript_flush.call_workdir_unreadable
            )

            # Only a recorded call whose own workdir could not be decoded marks
            # the managed-session context. A readable call without a workdir
            # runs in the session cwd, and an unrecorded call keeps the
            # before-flush fallback.
            readable_call = 'const r = await tools.exec_command({cmd:"x"});'
            unreadable_cases = (
                (
                    "unreadable-malformed",
                    "const r = await tools.exec_command({cmd: 'x'});",
                    "unreadable-malformed",
                    "transcript-custom-input-malformed",
                    True,
                ),
                (
                    "unreadable-ambiguous",
                    'const r = await tools.exec_command({cmd:"x"}); '
                    'await tools.exec_command({cmd:"y"});',
                    "unreadable-ambiguous",
                    "transcript-custom-input-ambiguous",
                    True,
                ),
                (
                    "readable-without-workdir",
                    readable_call,
                    "readable-without-workdir",
                    "transcript-workdir-missing",
                    False,
                ),
                (
                    "call-id-mismatch",
                    readable_call,
                    "some-other-call",
                    "transcript-call-mismatch",
                    False,
                ),
            )
            for name, source, call_id, diagnostic, unreadable in unreadable_cases:
                with self.subTest(transcript_case=name):
                    case_transcript = root / f"{name}.jsonl"
                    case_transcript.write_text(
                        json.dumps(
                            {
                                "payload": {
                                    "type": "custom_tool_call",
                                    "name": "exec",
                                    "call_id": call_id,
                                    "input": source,
                                }
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    self.assertEqual(
                        hook_common._transcript_workdir_result(
                            str(case_transcript), name
                        ).diagnostic,
                        diagnostic,
                    )
                    with (
                        mock.patch.dict(os.environ, managed_env, clear=False),
                        mock.patch.object(
                            hook_common.Path, "cwd", return_value=target
                        ),
                    ):
                        context = resolver(
                            {
                                "tool_name": "Bash",
                                "tool_input": {"command": "x"},
                                "tool_use_id": name,
                                "transcript_path": str(case_transcript),
                                "cwd": str(target),
                            }
                        )
                    self.assertEqual(context.path, target.resolve())
                    self.assertEqual(context.source, "managed-session-cwd")
                    self.assertTrue(context.attested)
                    self.assertIsNone(context.diagnostic)
                    self.assertIs(context.call_workdir_unreadable, unreadable)

            with (
                mock.patch.dict(
                    os.environ,
                    {**managed_env, "AGENT_SESSION_RUNTIME_ID": "wrong-launch"},
                    clear=False,
                ),
                mock.patch.object(hook_common.Path, "cwd", return_value=target),
            ):
                mismatched_managed = resolver(command_payload("touch out"))
            self.assertEqual(mismatched_managed.source, "process-cwd")
            self.assertFalse(mismatched_managed.attested)
            self.assertEqual(
                hook_common.COMMAND_CONTEXT_SOURCES,
                {
                    "tool-input",
                    "matching-transcript-call",
                    "payload",
                    "session-cwd",
                    "managed-session-cwd",
                    "process-cwd",
                },
            )


    def test_command_context_hot_path_is_in_process_and_under_latency_budget(
        self,
    ) -> None:
        """A synthetic hot path adds no subprocess and keeps p95 below 10 ms."""
        resolver = getattr(hook_common, "command_context", None)
        self.assertTrue(callable(resolver), "command_context resolver is missing")
        assert callable(resolver)
        payload = command_payload("touch out", workdir=str(REPO_ROOT))
        durations: list[float] = []
        with mock.patch.object(
            hook_common.subprocess,
            "run",
            side_effect=AssertionError("command context must not spawn"),
        ):
            for _ in range(1000):
                started = time.perf_counter()
                resolver(payload)
                durations.append(time.perf_counter() - started)
        p95 = sorted(durations)[949]
        self.assertLess(p95, 0.010, f"command-context p95 {p95:.6f}s")



    def test_normalized_cli_argv_accepts_only_bare_or_absolute_named_cli(
        self,
    ) -> None:
        for executable_name in ("agent-run", "agent-session"):
            with self.subTest(executable_name=executable_name, spelling="bare"):
                words = [executable_name, "status"]
                self.assertIs(
                    hook_common.normalized_cli_argv(words, executable_name),
                    words,
                )
            with self.subTest(executable_name=executable_name, spelling="absolute"):
                self.assertEqual(
                    hook_common.normalized_cli_argv(
                        [f"/trusted/bin/{executable_name}", "status"],
                        executable_name,
                    ),
                    [executable_name, "status"],
                )
            for spelling in (
                f"./{executable_name}",
                f"relative/{executable_name}",
                f"/trusted/bin/foreign-{executable_name}",
            ):
                with self.subTest(
                    executable_name=executable_name,
                    spelling=spelling,
                ):
                    self.assertIsNone(
                        hook_common.normalized_cli_argv(
                            [spelling, "status"],
                            executable_name,
                        )
                    )


    def test_bash_scanner_hooks_registered_for_codex_and_claude(self) -> None:
        expected_handlers = {
            "mcp-secret-scan",
            "block-project-memory-write",
            "portable-paths-scan",
        }
        for product in ("codex", "claude"):
            for handler in expected_handlers:
                with self.subTest(product=product, handler=handler):
                    rules = inventory_rules(
                        product=product,
                        event="PreToolUse",
                        handler=handler,
                    )
                    self.assertIn("Bash", inventory_tools(rules))


    def test_released_git_cli_dirty_adoption_lifecycle(self) -> None:
        git_cli = shutil.which("git-cli")
        agent_runtime = shutil.which("agent-runtime")
        self.assertIsNotNone(git_cli, "released git-cli is required")
        self.assertIsNotNone(agent_runtime, "released agent-runtime is required")
        assert git_cli is not None
        assert agent_runtime is not None
        version = subprocess.run(
            [git_cli, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(version.returncode, 0, version.stderr)
        runtime_version = subprocess.run(
            [agent_runtime, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(runtime_version.returncode, 0, runtime_version.stderr)
        self.assertEqual(version.stdout.split()[:1], ["git-cli"])
        self.assertEqual(runtime_version.stdout.split()[:1], ["agent-runtime"])
        self.assertEqual(version.stdout.split()[1], runtime_version.stdout.split()[1])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            state = root / "state"
            self._init_checkout_lease_repo(repo)
            dirty_file = repo / "unowned.txt"
            dirty_file.write_text("exact warned state\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                "AGENT_RUNTIME_STATE_HOME": str(state),
                "AGENT_RUNTIME_CHECKOUT_LEASE_TTL_SECONDS": "60",
            }
            self._dirty_snapshot_capability_or_skip(repo)

            code, advisory, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                {
                    "session_id": "released-lifecycle-owner",
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "take over this exact dirty state",
                },
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            details = self._dirty_adoption_command(advisory)
            token = details["token"]
            reason_file = details["reason_file"]
            reason = "Continue the user-authorized dirty checkout work.\n"
            reason_file.write_text(reason, encoding="utf-8")

            adopt_command = self._dirty_adoption_shell_command(
                details, "--format=json"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "released-lifecycle-owner",
                    repo,
                    tool_name="Bash",
                    command=adopt_command,
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            cli_env = dict(os.environ)
            cli_env.update(env)
            # The hook fixture trusts this selected released package root.
            # Its actual launcher subprocess needs the same bounded binding.
            cli_env["AGENT_RUNTIME_TRUSTED_CLI_ROOT"] = str(
                Path(git_cli).absolute().parent
            )
            adopted_result = subprocess.run(
                ["/bin/bash", "-c", adopt_command],
                cwd=repo,
                env=cli_env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                adopted_result.returncode,
                0,
                adopted_result.stdout + adopted_result.stderr,
            )
            self.assertEqual(adopted_result.stderr, "")
            adopted_envelope = json.loads(adopted_result.stdout)
            self.assertEqual(
                frozenset(adopted_envelope), {"schema_version", "ok", "data"}
            )
            self.assertEqual(
                adopted_envelope["schema_version"],
                "cli.git-cli.worktree.adopt-dirty.v1",
            )
            self.assertIs(adopted_envelope["ok"], True)
            self.assertEqual(
                frozenset(adopted_envelope["data"]),
                {"receipt_id", "snapshot_id"},
            )
            receipt_id = adopted_envelope["data"]["receipt_id"]
            self.assertRegex(receipt_id, r"^[0-9a-f]{64}$")
            for private_value in (token, reason, str(reason_file), str(repo)):
                self.assertNotIn(
                    private_value,
                    adopted_result.stdout + adopted_result.stderr,
                )

            lease_file = self._checkout_lease_files(state)[0]
            adopted_lease = json.loads(lease_file.read_text(encoding="utf-8"))
            self.assertEqual(
                adopted_lease["schema"], "agent-runtime.checkout-lease.v2"
            )
            adoption_provenance = adopted_lease["adoption"]
            acquired_at = adopted_lease["acquired_at"]
            adopted_lease["expires_at"] = int(time.time()) + 10
            lease_file.write_text(
                json.dumps(adopted_lease, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            owner = self._checkout_lease_payload(
                "released-lifecycle-owner", repo / "README.md"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            refreshed = json.loads(lease_file.read_text(encoding="utf-8"))
            self.assertEqual(refreshed["adoption"], adoption_provenance)
            self.assertEqual(refreshed["acquired_at"], acquired_at)
            self.assertEqual(
                refreshed["checkout_root_bytes"],
                adopted_lease["checkout_root_bytes"],
            )
            self.assertEqual(
                refreshed["checkout_git_dir_bytes"],
                adopted_lease["checkout_git_dir_bytes"],
            )
            self.assertGreater(
                refreshed["expires_at"], adopted_lease["expires_at"]
            )

            revoke_command = (
                "git-cli worktree revoke-dirty "
                f"--receipt {receipt_id} --format=json"
            )
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "foreign-lifecycle-session",
                    repo,
                    tool_name="Bash",
                    command=revoke_command,
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "owning agent session")

            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py",
                self._checkout_lease_payload(
                    "released-lifecycle-owner",
                    repo,
                    tool_name="Bash",
                    command=revoke_command,
                ),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            revoke_env = dict(cli_env)
            revoke_env["AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION"] = ""
            revoked_result = subprocess.run(
                [
                    git_cli,
                    "worktree",
                    "revoke-dirty",
                    "--receipt",
                    receipt_id,
                    "--format=json",
                ],
                cwd=repo,
                env=revoke_env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                revoked_result.returncode, 0, revoked_result.stderr
            )
            self.assertEqual(revoked_result.stderr, "")
            revoked_envelope = json.loads(revoked_result.stdout)
            self.assertEqual(
                frozenset(revoked_envelope), {"schema_version", "ok", "data"}
            )
            self.assertEqual(
                revoked_envelope["schema_version"],
                "cli.git-cli.worktree.revoke-dirty.v1",
            )
            self.assertIs(revoked_envelope["ok"], True)
            self.assertEqual(
                revoked_envelope["data"],
                {"receipt_id": receipt_id, "revoked": True},
            )
            self.assertEqual(self._checkout_lease_files(state), [])
            self.assertEqual(
                dirty_file.read_text(encoding="utf-8"), "exact warned state\n"
            )

            blocked_env = dict(env)
            blocked_env["AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION"] = ""
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=repo, env=blocked_env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "unowned changes")


    def test_released_git_cli_rejects_unusable_dirty_challenges(self) -> None:
        git_cli = shutil.which("git-cli")
        self.assertIsNotNone(git_cli, "released git-cli is required")
        assert git_cli is not None

        for case in (
            "stale-instance",
            "snapshot-changed",
            "expired",
            "malformed",
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                state = root / "state"
                self._init_checkout_lease_repo(repo)
                (repo / "unowned.txt").write_text("warned\n", encoding="utf-8")
                env = {
                    "AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION": "1",
                    "AGENT_RUNTIME_STATE_HOME": str(state),
                }
                self._dirty_snapshot_capability_or_skip(repo)
                code, advisory, stderr = run_enforced_hook(
                    "checkout-lease-guard.py",
                    {
                        "session_id": f"negative-{case}",
                        "hook_event_name": "UserPromptSubmit",
                        "prompt": f"inspect {case}",
                    },
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNotNone(advisory)
                assert advisory is not None
                details = self._dirty_adoption_command(advisory)
                token = details["token"]
                reason_file = details["reason_file"]
                reason = f"Attempt rejected {case}.\n"
                reason_file.write_text(reason, encoding="utf-8")
                challenge_file = next(state.rglob("challenges/*.json"))

                if case == "stale-instance":
                    (
                        repo / ".git" / ".agent-runtime-checkout-instance"
                    ).write_text("f" * 32 + "\n", encoding="ascii")
                elif case == "snapshot-changed":
                    (repo / "changed-after-warning.txt").write_text(
                        "changed\n", encoding="utf-8"
                    )
                elif case == "expired":
                    challenge = json.loads(
                        challenge_file.read_text(encoding="utf-8")
                    )
                    challenge["issued_at"] = int(time.time()) - 600
                    challenge["expires_at"] = int(time.time()) - 1
                    challenge_file.write_text(
                        json.dumps(challenge, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                else:
                    challenge_file.write_text("{malformed\n", encoding="utf-8")

                cli_env = dict(os.environ)
                cli_env.update(env)
                # The hook fixture trusts this selected released package root.
                # Its actual launcher subprocess needs the same bounded binding.
                cli_env["AGENT_RUNTIME_TRUSTED_CLI_ROOT"] = str(
                    Path(git_cli).absolute().parent
                )
                rejected = subprocess.run(
                    [
                        "/bin/bash",
                        "-c",
                        self._dirty_adoption_shell_command(
                            details, "--format=json"
                        ),
                    ],
                    cwd=repo,
                    env=cli_env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(rejected.returncode, 0)
                error_envelope = json.loads(rejected.stdout)
                self.assertIs(error_envelope["ok"], False)
                self.assertTrue(challenge_file.exists())
                self.assertEqual(self._checkout_lease_files(state), [])
                for private_value in (token, reason, str(reason_file), str(repo)):
                    self.assertNotIn(
                        private_value, rejected.stdout + rejected.stderr
                    )


    def test_dirty_adoption_launcher_passes_bearer_through_parent_socket(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "record.json"
            bin_dir = root / "bin"
            self._write_challenge_fd_git_cli_stub(bin_dir, record)
            token = secrets.token_hex(32)
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            reason_file = root / "reasons" / f"{digest}.txt"
            reason_file.parent.mkdir()
            reason_file.write_text("Adopt the warned state.\n", encoding="utf-8")

            result = self._run_dirty_adoption_launcher(
                ["--reason-file", str(reason_file), "--format=json"],
                token + "\n",
                bin_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout), {"ok": True})
            observed = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(
                observed["argv"],
                [
                    "worktree",
                    "adopt-dirty",
                    "--challenge-fd",
                    "0",
                    "--reason-file",
                    str(reason_file),
                    "--format=json",
                ],
            )
            self.assertTrue(observed["is_socket"])
            self.assertEqual(observed["digest"], digest)
            self.assertFalse(observed["bearer_in_argv"])
            self.assertFalse(observed["bearer_in_env"])
            if sys.platform.startswith("linux"):
                self.assertTrue(observed["peer_is_parent"])
            self.assertNotIn(token, result.stdout + result.stderr)


    def test_dirty_adoption_launcher_rejects_unbound_or_malformed_input(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "record.json"
            bin_dir = root / "bin"
            self._write_challenge_fd_git_cli_stub(bin_dir, record)
            token = secrets.token_hex(32)
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            reason_file = root / "reasons" / f"{digest}.txt"
            reason_file.parent.mkdir()
            reason_file.write_text("Adopt the warned state.\n", encoding="utf-8")
            other_reason = root / "reasons" / f"{'0' * 64}.txt"
            other_reason.write_text("Other.\n", encoding="utf-8")

            for label, arguments, stdin, trusted in (
                ("malformed-bearer", ["--reason-file", str(reason_file)], "xyz\n", True),
                ("extra-input", ["--reason-file", str(reason_file)], token + "\nmore\n", True),
                ("reason-mismatch", ["--reason-file", str(other_reason)], token + "\n", True),
                ("missing-reason", [], token + "\n", True),
                ("unknown-argument", ["--reason-file", str(reason_file), "--bogus"], token, True),
                ("bearer-on-argv", ["--reason-file", str(reason_file), "--challenge", token], token, True),
                ("untrusted-cli", ["--reason-file", str(reason_file)], token + "\n", False),
            ):
                with self.subTest(label=label):
                    record.unlink(missing_ok=True)
                    result = self._run_dirty_adoption_launcher(
                        arguments, stdin, bin_dir, trusted=trusted
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(record.exists())
                    self.assertNotIn(token, result.stdout + result.stderr)


    def test_process_launcher_option_kinds_are_disjoint(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_launcher_option_invariant_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            for launcher in module.PROCESS_LAUNCH_VALUE_OPTIONS:
                kinds = (
                    module.PROCESS_LAUNCH_VALUE_OPTIONS[launcher],
                    module.PROCESS_LAUNCH_FLAG_OPTIONS[launcher],
                    module.PROCESS_LAUNCH_OPTIONAL_VALUE_OPTIONS[launcher],
                )
                with self.subTest(launcher=launcher):
                    self.assertFalse(kinds[0] & kinds[1])
                    self.assertFalse(kinds[0] & kinds[2])
                    self.assertFalse(kinds[1] & kinds[2])
        finally:
            sys.modules.pop(spec.name, None)


    def test_semantic_commit_effects_ignore_redirections(self) -> None:
        # The shell removes a redirection before semantic-commit parses, so it
        # never fills `--repo` or hides `--message-out`.
        effects = hook_common.semantic_commit_invocation_effects
        self.assertEqual(
            effects(["commit", "2>/dev/null", "--dry-run", "--message-out", "f"]),
            (False, True, ""),
        )
        self.assertEqual(
            effects(["commit", ">", "/dev/null", "--repo", "/srv/r", "--dry-run"]),
            (False, False, "/srv/r"),
        )


    def test_trusted_removal_all_modes(self) -> None:
        module = self._load("trusted_removal_modes", "checkout-lease-guard.py")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                primary = root / "primary"
                self._init_checkout_lease_repo(primary)
                linked = self._add_checkout_lease_worktree(primary, "feature/removal-modes")
                target = shlex.quote(str(linked))
                for mode in ("", "off", "advisory", "enforce"):
                    for command in (
                        f"git-cli worktree remove {target}",
                        f"git-cli worktree remove {target} --safe",
                        f"echo ready; git-cli worktree remove {target}",
                        f"command -- git-cli worktree remove {target}",
                        f"cd {shlex.quote(str(primary))} && git-cli worktree remove {target}",
                        f"cd -- {shlex.quote(str(primary))} && git-cli worktree remove ../{linked.name}",
                    ):
                        with self.subTest(mode=mode, command=command):
                            payload = self._checkout_lease_payload("owner", primary, tool_name="Bash", command=command)
                            with mock.patch.dict(os.environ, {
                                "AGENT_SESSION_COORDINATION_MODE": mode,
                                "AGENT_RUNTIME_STATE_HOME": str(root / "state"),
                            }), mock.patch.object(module, "read_payload", return_value=payload), \
                                 mock.patch.object(module, "resolved_executable_matches", return_value=True), \
                                 mock.patch.object(module, "emit_block") as blocked:
                                module.main()
                            blocked.assert_not_called()
                self.assertTrue(linked.exists(), "PreToolUse never removes a worktree")
                self.assertEqual(self._checkout_lease_files(root / "state"), [])
        finally:
            sys.modules.pop("trusted_removal_modes", None)


    def test_trusted_removal_backup_acknowledgement_permutations(self) -> None:
        module = self._load("trusted_removal_acknowledgement", "checkout-lease-guard.py")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                primary = root / "primary"
                self._init_checkout_lease_repo(primary)
                linked = self._add_checkout_lease_worktree(primary, "feature/removal-acknowledgement")
                target = shlex.quote(str(linked))
                for safe in ((), ("--safe",)):
                    for format_args in ((), ("--format text",), ("--format json",),
                                        ("--format=text",), ("--format=json",)):
                        options = (target, "--acknowledge-backup-omissions") + safe + format_args
                        for arguments in itertools.permutations(options):
                            removal = "git-cli worktree remove " + " ".join(arguments)
                            for prefix in ("", f"cd {shlex.quote(str(primary))} && "):
                                for mode in ("", "off", "advisory", "enforce"):
                                    command = prefix + removal
                                    with self.subTest(mode=mode, command=command):
                                        payload = self._checkout_lease_payload(
                                            "owner", primary, tool_name="Bash", command=command
                                        )
                                        with mock.patch.dict(os.environ, {
                                            "AGENT_SESSION_COORDINATION_MODE": mode,
                                            "AGENT_RUNTIME_STATE_HOME": str(root / "state"),
                                        }), mock.patch.object(module, "read_payload", return_value=payload), \
                                             mock.patch.object(module, "resolved_executable_matches", return_value=True), \
                                             mock.patch.object(module, "emit_block") as blocked:
                                            module.main()
                                        blocked.assert_not_called()
                self.assertTrue(linked.exists(), "PreToolUse never removes a worktree")
                self.assertEqual(self._checkout_lease_files(root / "state"), [])
        finally:
            sys.modules.pop("trusted_removal_acknowledgement", None)


    def test_trusted_removal_refuses_unrelated_flags_and_formats(self) -> None:
        module = self._load("trusted_removal_options", "checkout-lease-guard.py")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                primary = Path(tmp) / "primary"
                self._init_checkout_lease_repo(primary)
                linked = self._add_checkout_lease_worktree(primary, "feature/removal-options")
                for mode in ("", "off", "advisory", "enforce"):
                    for options in ("--force", "-f", "--dry-run", "--format yaml",
                                    "--format=yaml", "--format", "--format=",
                                    "--acknowledge-backup-omissions=true"):
                        command = (f"git-cli worktree remove {shlex.quote(str(linked))} "
                                   f"--acknowledge-backup-omissions {options}")
                        with self.subTest(mode=mode, options=options):
                            payload = self._checkout_lease_payload(
                                "owner", primary, tool_name="Bash", command=command
                            )
                            with mock.patch.dict(os.environ, {"AGENT_SESSION_COORDINATION_MODE": mode}), \
                                 mock.patch.object(module, "read_payload", return_value=payload), \
                                 mock.patch.object(module, "resolved_executable_matches", return_value=True), \
                                 mock.patch.object(module, "emit_block") as blocked:
                                module.main()
                            blocked.assert_called_once()
                # Exercise format validation independently of acknowledgement admission.
                for option in ("--format yaml", "--format=yaml", "--format="):
                    with self.subTest(option=option):
                        with self.assertRaises(module.MutationScopeError):
                            module.worktree_remove_target_argument(
                                ["git-cli", "worktree", "remove", str(linked)] + shlex.split(option)
                            )
                self.assertTrue(linked.exists())
        finally:
            sys.modules.pop("trusted_removal_options", None)


    def test_raw_removal_override_stays_blocked(self) -> None:
        for mode in ("advisory", "enforce"):
            for command in (
                "git worktree remove ../target",
                "ALLOW_DIRECT_GIT_WORKTREE=1 git worktree remove ../target",
                "env ALLOW_DIRECT_GIT_WORKTREE=1 bash -c 'git worktree remove ../target'",
            ):
                with self.subTest(mode=mode, command=command):
                    code, decision, stderr = run_hook(
                        "block-direct-git-worktree.py", command_payload(command),
                        env={"AGENT_SESSION_COORDINATION_MODE": mode,
                             "AGENT_RUNTIME_ALLOW_DIRECT_GIT_WORKTREE": "1"},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "git-cli worktree")


    def test_raw_rm_registered_worktree_stays_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/raw-rm")
            for mode in ("advisory", "enforce"):
                for command in (
                    f"rm -rf {shlex.quote(str(linked))}",
                    f"TARGET={shlex.quote(str(linked))}; rm -rf \"$TARGET\"",
                    f"cd .. && rm -rf {shlex.quote(linked.name)}",
                    f"cd -- .. && rm -rf {shlex.quote(linked.name)}",
                    f"agent-run exec --cwd {shlex.quote(str(linked.parent))} rm -rf {shlex.quote(linked.name)}",
                    f"cd {shlex.quote(str(Path(tmp) / 'missing'))} || rm -rf ../{shlex.quote(linked.name)}",
                ):
                    with self.subTest(mode=mode, command=command):
                        payload = self._checkout_lease_payload("owner", primary, tool_name="Bash", command=command)
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", payload, cwd=primary,
                            env={"AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(decision, "git-cli worktree remove")
                        self.assertTrue(linked.exists())


    def test_raw_deletion_verbs_registered_worktree_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/deletion-verbs")
            target = shlex.quote(str(linked))
            env = {"AGENT_RUNTIME_STATE_HOME": str(root / "state")}
            owner = self._checkout_lease_payload("owner", linked / "README.md")
            code, decision, stderr = run_enforced_hook(
                "checkout-lease-guard.py", owner, cwd=linked, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            commands = (
                f"unlink {target}", f"shred --remove {target}",
                f"find {target} -delete", f"find {target} -depth -delete",
                f"find {target} -mindepth 1 -delete", "find -delete",
                rf"find {target} \( -type f \) -delete",
                f"find {target} '(' -type f ')' -delete",
                f"find {target} -exec rm -rf {{}} +",
                rf"find {target} -exec unlink {{}} \;",
                f"find {target} -exec shred --remove {{}} +",
                f"find {target} -execdir rm -rf {{}} +",
                rf"find {target} -exec echo {{}} \; -delete",
                f"find {target} -exec echo {{}} ';' -delete",
                f"find {shlex.quote(str(root))} -exec rm -rf {target} +",
                rf"find {target} -ok unlink {{}} \;",
                rf"find {target} -okdir shred --remove {{}} \;",
                f"TARGET={target}; find \"$TARGET\" -delete",
                f"cd .. && find {shlex.quote(linked.name)} -delete",
                f"agent-run exec --cwd {shlex.quote(str(linked.parent))} find {shlex.quote(linked.name)} -delete",
            )
            for mode in ("advisory", "enforce"):
                for command in commands:
                    with self.subTest(mode=mode, command=command):
                        payload = self._checkout_lease_payload(
                            "owner", linked, tool_name="Bash", command=command
                        )
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", payload, cwd=linked,
                            env={**env, "AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(decision, "git-cli worktree remove")
                        self.assertTrue(linked.exists())


    def test_wrapped_deletions_keep_registered_worktrees_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/wrapped-deletion")
            target = shlex.quote(str(linked))
            env = {"AGENT_RUNTIME_STATE_HOME": str(root / "state")}
            commands = [f"{wrapper} {deletion}" for wrapper in (
                "sudo", "sudo -n -u fixture --", "nice", "nice -n 5",
                "nice --adjustment=5", "nohup", "nohup --", "nice nohup",
            ) for deletion in (f"rm -rf {target}", f"find {target} -delete")]
            commands += [f"xargs rm -rf {target}", f"xargs -n1 rm -rf {target}",
                         f"xargs --eof rm -rf {target}", f"xargs --eof=STOP rm -rf {target}",
                         f"xargs --max-lines rm -rf {target}", f"xargs --max-lines=1 rm -rf {target}",
                         f"xargs -I% rm -rf {target}", f"xargs --replace=% rm -rf {target}",
                         f"xargs find {target} -delete", "xargs rm -rf",
                         "xargs -I% rm -rf %", "xargs -J% rm -rf %",
                         f"printf '%s\\n' {target} | xargs rm -rf",
                         f"printf '%s\\n' {target} | xargs --max-lines rm -rf",
                         f"find {target} -exec nice rm -rf {{}} +"]
            for mode in ("advisory", "enforce"):
                for command in commands:
                    with self.subTest(mode=mode, command=command):
                        payload = self._checkout_lease_payload(
                            "owner", linked, tool_name="Bash", command=command
                        )
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", payload, cwd=linked,
                            env={**env, "AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(decision, "git-cli worktree remove")
                        self.assertTrue(linked.exists(), "Hooks never execute deletion payloads")


    def test_wrapped_commands_preserve_file_deletions_and_read_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "primary"
            self._init_checkout_lease_repo(primary)
            commands = ("sudo -n rm README.md", "nice -n5 rm README.md",
                        "nohup rm README.md", "nice find README.md -delete",
                        "xargs -I% rm README.md", "xargs echo rm -rf .",
                        "xargs --max-lines echo rm -rf .", "xargs --max-lines=1 echo hi",
                        "nice echo rm -rf .", "sudo -u rm echo .",
                        "sudo --help", "nice --version", "nohup --help")
            for mode in ("advisory", "enforce"):
                for command in commands:
                    with self.subTest(mode=mode, command=command):
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py",
                            self._checkout_lease_payload("owner", primary, tool_name="Bash", command=command),
                            cwd=primary, env={"AGENT_SESSION_COORDINATION_MODE": mode},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_allowed(decision)


    def test_wrapped_direct_git_and_provider_commands_keep_boundaries(self) -> None:
        for wrapper in ("sudo -n", "nice -n5", "nohup --", "xargs -n1"):
            for hook, payload, fragment in (
                ("block-direct-git-commit.py", "git commit -m fixture", "semantic-commit"),
                ("block-direct-pr-create.py", "gh pr create --title fixture", "forge-cli"),
            ):
                with self.subTest(wrapper=wrapper, hook=hook):
                    code, decision, stderr = run_hook(hook, command_payload(f"{wrapper} {payload}"))
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)
            for command in (f"{wrapper} git status", f"{wrapper} echo git commit -m fixture"):
                with self.subTest(control=command):
                    code, decision, stderr = run_hook("block-direct-git-commit.py", command_payload(command))
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNone(decision)


    def test_wrapped_git_configuration_tracks_environment_boundaries(self) -> None:
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload("xargs git config --global"),
            unset_env=("GIT_CONFIG_GLOBAL",),
        )
        self.assertEqual(code, 0, stderr)
        self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")
        code, decision, stderr = run_hook(
            "block-direct-git-commit.py", command_payload("xargs git config --global --get user.name"),
            unset_env=("GIT_CONFIG_GLOBAL",),
        )
        self.assertEqual(code, 0, stderr)
        self.assertIsNone(decision)
        for command in ("sudo git config --global user.name fixture",
                        "GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig sudo git config --global user.name fixture",
                        "nice env -u GIT_CONFIG_GLOBAL git config --global user.name fixture",
                        "nohup env -i git config --global user.name fixture"):
            with self.subTest(command=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    env={"GIT_CONFIG_GLOBAL": "/tmp/fixture/gitconfig"},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "GIT_CONFIG_GLOBAL")
        for wrapper in ("nice -n5", "nohup --", "sudo -n"):
            command = f"{wrapper} env GIT_CONFIG_GLOBAL=/tmp/fixture/gitconfig git config --global user.name fixture"
            with self.subTest(control=command):
                code, decision, stderr = run_hook(
                    "block-direct-git-commit.py", command_payload(command),
                    unset_env=("GIT_CONFIG_GLOBAL",),
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNone(decision)


    def test_sudo_does_not_credit_inherited_git_program_lookup(self) -> None:
        module = self._load("sudo_git_lookup", "block-direct-git-commit.py")
        try:
            with mock.patch.object(module, "git_builtin_commands", return_value=frozenset({"status"})), \
                 mock.patch.object(module, "git_installed_commands", return_value=frozenset({"fixture-extension"})):
                self.assertEqual(module.git_commit_block_reason("sudo -n git fixture-extension"), module.ALIAS_REASON)
                for command in ("sudo -n git status", "nice git fixture-extension", "nohup git fixture-extension"):
                    with self.subTest(control=command):
                        self.assertEqual(module.git_commit_block_reason(command), "")
        finally:
            sys.modules.pop("sudo_git_lookup", None)


    def test_shared_wrappers_do_not_bypass_default_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            for wrapper in ("sudo -n", "nice -n5", "nohup --", "xargs -n1"):
                with self.subTest(wrapper=wrapper):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(f"{wrapper} git push origin HEAD:main"), cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "forge-cli repo push-default")
                for command in (f"{wrapper} git status", f"{wrapper} echo git push origin HEAD:main"):
                    with self.subTest(control=command):
                        code, decision, stderr = run_hook(
                            "block-unsafe-default-delivery.py", command_payload(command), cwd=repo,
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_allowed(decision)


    def test_raw_rm_resolves_target_checkout_from_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp)
            primary = outside / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/outside-rm")
            for mode in ("advisory", "enforce"):
                payload = self._checkout_lease_payload("owner", outside, tool_name="Bash",
                    command=f"rm -rf {shlex.quote(str(linked))}")
                code, decision, stderr = run_hook(
                    "checkout-lease-guard.py", payload, cwd=outside,
                    env={"AGENT_SESSION_COORDINATION_MODE": mode},
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "git-cli worktree remove")
                self.assertTrue(linked.exists())


    def test_untrusted_removal_binary_all_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            self._init_checkout_lease_repo(primary)
            linked = self._add_checkout_lease_worktree(primary, "feature/untrusted-remove")
            binary_dir = root / "untrusted"
            binary_dir.mkdir()
            binary = binary_dir / "git-cli"
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o755)
            for mode in ("advisory", "enforce"):
                for executable in ("git-cli", str(binary)):
                    with self.subTest(mode=mode, executable=executable):
                        payload = self._checkout_lease_payload("owner", primary, tool_name="Bash",
                            command=f"{shlex.quote(executable)} worktree remove {shlex.quote(str(linked))} --safe")
                        code, decision, stderr = run_hook(
                            "checkout-lease-guard.py", payload, cwd=primary,
                            env={"AGENT_SESSION_COORDINATION_MODE": mode,
                                 "PATH": str(binary_dir) + os.pathsep + os.environ["PATH"]},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(decision, "trusted git-cli executable")
                        self.assertTrue(linked.exists())


    def test_cleanup_rendered_contract_has_no_retired_removal_gates(self) -> None:
        retired = (
            "outside enforce mode", "verified enforcement availability",
            "only after all proofs", "requires owner/terminal proof",
            "Never adopt a disappeared session's checkout",
            "Verify each provider-confirmed delivered head before removing",
            "only for a clean,\n   unowned managed worktree",
        )
        skills = ("meta/worktree-triage", "pr/deliver-pr", "dispatch/deliver-dispatch-plan")
        texts = [
            (REPO_ROOT / "core/policies/git-delivery.md").read_text().split("### Terminal local cleanup", 1)[1].split("## Branches", 1)[0]
        ]
        for product in ("codex", "claude", "hermes"):
            for skill in skills:
                plugin, name = skill.split("/")
                texts.append((REPO_ROOT / f"tests/golden/{product}/plugins/{plugin}/skills/{name}/expected/SKILL.md").read_text())
        for text in texts:
            for gate in retired:
                self.assertNotIn(gate, text)
            self.assertIn("git-cli worktree remove", text)
            self.assertIn("backup_ref", text)
            self.assertIn("seven days", text)


    def test_invocation_without_redirections_strips_operators(self) -> None:
        import hook_common

        clobber = f">{hook_common.CLOBBER_REDIRECT_MARKER}"
        for invocation, expected in (
            (["git-cli", "worktree", "remove", "slug", "<", "/dev/null"],
             ["git-cli", "worktree", "remove", "slug"]),
            (["cmd", "arg", "2>/dev/null"], ["cmd", "arg"]),
            (["cmd", ">>", "log", "arg"], ["cmd", "arg"]),
            (["cmd", "arg", clobber, "out"], ["cmd", "arg"]),
            (["cmd", "1>", "a", "2>", "b", "arg"], ["cmd", "arg"]),
            (["cmd", "arg"], ["cmd", "arg"]),
        ):
            with self.subTest(invocation=invocation):
                self.assertEqual(
                    hook_common.invocation_without_redirections(invocation), expected
                )


    def test_claude_multiedit_hooks_exclude_content_only_scanners(self) -> None:
        """MultiEdit carries its content in `edits[]`, not at the top level.

        A scanner that only reads `content`/`new_string` sees nothing there, so
        registering one costs a process spawn and inspects an empty string.
        `mcp-secret-scan` is still exactly that and stays excluded.

        `portable-paths-scan` is no longer content-only: it also carries agent
        artifact routing, which reads `file_path` -- a key MultiEdit does have,
        and the reason MultiEdit needs this handler at all.

        Its content half is *narrowed* on MultiEdit, not absent:
        `proposed_content` returns "" here, but `patch_text_candidates` still
        recurses into `edits[]`, so embedded apply-patch text can raise a
        portable-path hit. `test_portable_paths_on_multiedit_scans_only_patch_text`
        pins both sides of that boundary.
        """
        multiedit = [
            rule
            for rule in inventory_rules(product="claude", event="PreToolUse")
            if "MultiEdit" in inventory_tools([rule])
        ]
        self.assertTrue(multiedit)
        handlers = {rule["legacy_handler"] for rule in multiedit}
        self.assertNotIn("mcp-secret-scan", handlers)
        self.assertIn("portable-paths-scan", handlers)


    def test_provider_fragments_defer_path_resolution_to_agent_hook(self) -> None:
        codex_block = (REPO_ROOT / "targets" / "codex" / "hooks" / "config.block.toml").read_text(
            encoding="utf-8"
        )
        claude_fragment = (
            REPO_ROOT / "core" / "hooks" / "claude" / "settings.hooks.jsonc"
        ).read_text(encoding="utf-8")
        self.assertNotIn("command =", codex_block)
        self.assertNotIn('"command"', claude_fragment)
        self.assertIn("agent-hook setup", codex_block)
        self.assertIn("agent-hook setup", claude_fragment)


    def test_codex_hook_block_source_matches_install_body_template(self) -> None:
        source_block = (REPO_ROOT / "targets" / "codex" / "hooks" / "config.block.toml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source_block, codex_link_map_hook_body())


    def test_delivery_trusts_the_per_user_root_without_any_override(self) -> None:
        with self._managed_cli_home_fixture() as (home_bin, _other_bin):
            module = self._load("delivery_home_root", "block-unsafe-default-delivery.py")
            os.environ["PATH"] = f"{home_bin}{os.pathsep}/usr/bin"
            self.assertTrue(
                module.trusted_managed_cli_invocation("semantic-commit", "semantic-commit")
            )


    def test_delivery_trusts_the_per_user_root_through_a_symlinked_ancestor(self) -> None:
        """A symlinked parent is not a reason to distrust the binary.

        `os.path.realpath` resolves ancestors as well as the leaf, so comparing
        it against the whole lexical path rejects every managed CLI whose HOME
        is reached through a link — which is every macOS temp path, and any
        `$HOME` on a linked volume.
        """
        with self._managed_cli_home_fixture(symlinked_ancestor=True) as (home_bin, _other):
            module = self._load("delivery_symlinked_home", "block-unsafe-default-delivery.py")
            os.environ["PATH"] = f"{home_bin}{os.pathsep}/usr/bin"
            self.assertTrue(
                module.trusted_managed_cli_invocation("semantic-commit", "semantic-commit")
            )


    def test_a_symlink_out_of_the_per_user_root_is_still_rejected(self) -> None:
        """Tolerating a symlinked ancestor must not tolerate a symlinked leaf.

        The leaf check is the whole point of the pairing: the trusted roots are
        writable, so a link planted *in* one that points at another binary must
        stay untrusted, with or without a symlinked ancestor above it.
        """
        for symlinked_ancestor in (False, True):
            with self.subTest(symlinked_ancestor=symlinked_ancestor):
                with self._managed_cli_home_fixture(
                    symlinked_ancestor=symlinked_ancestor
                ) as (home_bin, other_bin):
                    planted = Path(home_bin) / "planted"
                    planted.symlink_to(Path(other_bin) / "semantic-commit")
                    os.environ["PATH"] = f"{home_bin}{os.pathsep}/usr/bin"
                    delivery = self._load(
                        f"delivery_planted_{symlinked_ancestor}",
                        "block-unsafe-default-delivery.py",
                    )
                    self.assertFalse(
                        delivery.trusted_managed_cli_invocation("planted", "planted")
                    )
                    coordination = self._load(
                        f"coord_planted_{symlinked_ancestor}",
                        "session-coordination-guard.py",
                    )
                    self.assertIsNone(coordination.resolved_trusted_cli("planted"))


    def test_delivery_still_rejects_an_unrelated_directory(self) -> None:
        with self._managed_cli_home_fixture() as (_home_bin, other_bin):
            module = self._load("delivery_home_root_reject", "block-unsafe-default-delivery.py")
            os.environ["PATH"] = f"{other_bin}{os.pathsep}/usr/bin"
            self.assertFalse(
                module.trusted_managed_cli_invocation("semantic-commit", "semantic-commit")
            )


    def test_explicit_root_still_replaces_the_builtin_list(self) -> None:
        """Setting an explicit root narrows trust to exactly that root.

        Guards differ on this by design, not by accident: pre-edit-intent-gate
        pairs the same early return with a repository-local executable check, so
        falling through to the packaged prefixes would skip that check. The
        per-user root is a built-in, so it needs no override to be trusted.
        """
        with self._managed_cli_home_fixture() as (home_bin, other_bin):
            module = self._load("coord_home_root_replace", "session-coordination-guard.py")
            os.environ["AGENT_RUNTIME_TRUSTED_CLI_ROOT"] = str(other_bin)
            os.environ["PATH"] = f"{home_bin}{os.pathsep}/usr/bin"
            self.assertIsNone(module.resolved_trusted_cli("agent-session"))
            os.environ["PATH"] = f"{other_bin}{os.pathsep}/usr/bin"
            self.assertIsNotNone(module.resolved_trusted_cli("agent-session"))


    def test_hook_common_helper_matches_lexical_and_resolved_forms(self) -> None:
        with self._managed_cli_home_fixture() as (home_bin, other_bin):
            import hook_common

            self.assertTrue(hook_common.is_managed_cli_home_bin(str(home_bin)))
            self.assertFalse(hook_common.is_managed_cli_home_bin(str(other_bin)))
            self.assertEqual(hook_common.managed_cli_home_bin(), str(home_bin))


    def test_portable_paths_on_multiedit_scans_only_patch_text(self) -> None:
        """Registering this handler on MultiEdit made one more path reachable.

        `proposed_content` returns "" for MultiEdit, so an ordinary edit raises
        no portable-path hit. `patch_text_candidates` still recurses into
        `edits[]` though, so embedded apply-patch text does. Both sides are
        asserted because the registration is new here and the boundary was
        previously described in a comment rather than owned by a test.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._artifact_routing_repo(tmp)

            code, decision, stderr = run_hook(
                "portable-paths-scan.py",
                {
                    "tool_name": "MultiEdit",
                    "tool_input": {
                        "file_path": "docs/source/y.md",
                        "edits": [
                            {
                                "old_string": "a",
                                "new_string": "/Users/example/project/notes",
                            }
                        ],
                    },
                },
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "portable-paths-scan.py",
                {
                    "tool_name": "MultiEdit",
                    "tool_input": {
                        "file_path": "src/main.py",
                        "edits": [
                            {
                                "old_string": "a",
                                "new_string": (
                                    "*** Add File: docs/source/y.md\n"
                                    "+/Users/example/project/notes\n"
                                    "*** End Patch"
                                ),
                            }
                        ],
                    },
                },
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "portable-paths")

