"""Shared hook tests: default delivery."""
from __future__ import annotations

from shared_hook_helpers import (
    HOOK_DIR,
    HookTestCase,
    Path,
    command_payload,
    hook_common,
    importlib,
    json,
    os,
    run_hook,
    shlex,
    shutil,
    subprocess,
    sys,
    tempfile,
    time,
)


class DefaultDeliveryTests(HookTestCase):

    def test_default_delivery_collaboration_marker_grants_no_push_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for marked in (True, False):
                with self.subTest(marked=marked):
                    repo = Path(tmp) / ("marked" if marked else "unmarked")
                    self._init_checkout_lease_repo(repo)
                    if marked:
                        (repo / ".agent-collab").write_text(
                            "collab-protocol: 1\n", encoding="utf-8",
                        )
                        for arguments in (
                            ["add", "--", ".agent-collab"],
                            ["commit", "-q", "-m", "ledger marker fixture"],
                            ["push", "-q", "origin", "main"],
                        ):
                            subprocess.run(
                                ["git", *arguments], cwd=repo, check=True,
                                capture_output=True,
                            )
                    tracked = subprocess.run(
                        ["git", "ls-files", "--", ".agent-collab"], cwd=repo,
                        check=True, capture_output=True, text=True,
                    )
                    self.assertEqual(bool(tracked.stdout.strip()), marked)
                    remote_marker = subprocess.run(
                        ["git", "--git-dir", str(repo.parent / f"{repo.name}-origin.git"),
                         "show", "HEAD:.agent-collab"],
                        capture_output=True,
                    )
                    self.assertEqual(remote_marker.returncode == 0, marked)
                    if marked:
                        self.assertEqual(remote_marker.stdout, b"collab-protocol: 1\n")
                    # The default-delivery hook sees the invocation, not its
                    # Python subprocesses. Policy owns the tool's authority.
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload("python3 tools/collab.py post draft.md"),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
                    for command in ("git push", "git push origin HEAD:main"):
                        code, decision, stderr = run_hook(
                            "block-unsafe-default-delivery.py",
                            command_payload(command), cwd=repo,
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(decision, "[default-delivery:")


    def test_default_delivery_hook_blocks_default_branch_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "semantic-commit commit --message 'fix: tiny repair'",
                "semantic-commit fixup HEAD~1",
                "semantic-commit squash HEAD~1",
                "git push",
                "git push origin main",
                "git push origin HEAD:main",
                "git push origin HEAD:refs/heads/main",
                "git push origin @",
                "git push origin +@",
                "git push origin heads/main",
                "git push origin HEAD:heads/main",
                "git push --force origin HEAD:main",
                "git push --force-with-lease origin HEAD:refs/heads/main",
                "git push origin +HEAD:refs/heads/main",
                "git push origin :",
                "git push origin +:",
                "git push origin --delete main",
                "git push --all origin",
                "git push origin 'refs/heads/*:refs/heads/*'",
                "git push origin 'heads/*:heads/*'",
                "git push -omerge_request.target=main origin HEAD:refs/heads/main",
                "git push -odeploy=true origin HEAD:refs/heads/main",
                "git -c alias.ship='push origin HEAD:main' ship",
                "git -c alias.push=status push origin HEAD:main",
                "semantic-commit commit --message-file -h",
                "semantic-commit commit --message-file --dry-run",
                "bash -c 'git push origin HEAD:main'",
                "noglob git push origin HEAD:main",
                "nocorrect git push origin HEAD:main",
                "- git push origin HEAD:main",
                "noglob semantic-commit commit --message 'fix: tiny repair'",
                "zsh -c 'noglob git push origin HEAD:main'",
                "nice git push origin HEAD:main",
                "nice -n 5 git merge origin/main",
                "timeout 5 git pull origin main",
                "timeout --signal TERM 5 git reset --hard HEAD~1",
                "nohup git cherry-pick HEAD~1",
                "stdbuf -oL git update-ref refs/heads/main HEAD",
                "nice timeout 5 stdbuf -oL git push origin HEAD:main",
                "nice noglob git push origin HEAD:main",
                "noglob nice git push origin HEAD:main",
                "opts='-n 5'; nice $opts git push origin HEAD:main",
                "opts=-oL; stdbuf $opts git push origin HEAD:main",
                "cmd=git; nice $cmd push origin HEAD:main",
                "setsid git push origin HEAD:main",
                "ionice git merge origin/main",
                "chrt -o 0 git pull origin main",
                "taskset -c 0 git reset --hard HEAD~1",
                "nice setsid git update-ref refs/heads/main HEAD",
                "cmd=git; setsid $cmd push origin HEAD:main",
                "action=push; git $action origin HEAD:main",
                "action=push; setsid git $action origin HEAD:main",
                "cmd=git; action=push; setsid $cmd $action origin HEAD:main",
                "cmd=git; setsid $cmd ship",
                "action=commit; semantic-commit $action --message 'fix: x'",
                "cmd=semantic-commit; setsid $cmd commit --message 'fix: x'",
                "prlimit -- git push origin HEAD:main",
                "setpriv -- git push origin HEAD:main",
                "unshare git push origin HEAD:main",
                "strace -o /tmp/trace git push origin HEAD:main",
                "nsenter --target 1 --mount git push origin HEAD:main",
                "cmd=git; prlimit -- $cmd push origin HEAD:main",
                "cmd=git; setpriv -- $cmd push origin HEAD:main",
                "cmd=git; unshare $cmd push origin HEAD:main",
                "cmd=git; strace -o /tmp/trace $cmd push origin HEAD:main",
                "cmd=git; nsenter --target 1 --mount $cmd push origin HEAD:main",
                "cmd=semantic-commit; prlimit -- $cmd commit --message 'fix: x'",
                "cmd=semantic-commit; setpriv -- $cmd commit --message 'fix: x'",
                "cmd=semantic-commit; unshare $cmd commit --message 'fix: x'",
                "cmd=semantic-commit; strace -o /tmp/trace $cmd commit --message 'fix: x'",
                "cmd=semantic-commit; nsenter --target 1 --mount $cmd commit --message 'fix: x'",
                "perf stat --null git push origin HEAD:main",
                "perf stat record -e dummy:u -o /dev/null -- git push origin HEAD:main",
                "watch -n 1 git push origin HEAD:main",
                "systemd-run --user --scope git push origin HEAD:main",
                "systemd-run -P git push origin HEAD:main",
                "systemd-run -G git push origin HEAD:main",
                "action=push; perf stat --null git $action origin HEAD:main",
                "action=push; watch -n 1 git $action origin HEAD:main",
                "action=push; systemd-run --user --scope git $action origin HEAD:main",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "forge-cli repo push-default")


    def test_default_delivery_hook_blocks_semantic_commit_behind_launchers(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "prlimit -- semantic-commit commit --message 'fix: x'",
                "setpriv -- semantic-commit commit --message 'fix: x'",
                "unshare semantic-commit commit --message 'fix: x'",
                "strace -o /tmp/trace semantic-commit commit --message 'fix: x'",
                "nsenter --target 1 --mount semantic-commit commit --message 'fix: x'",
                "perf stat --null semantic-commit commit --message 'fix: x'",
                "perf stat record -e dummy:u -o /dev/null -- semantic-commit commit --message 'fix: x'",
                "systemd-run --user --scope semantic-commit commit --message 'fix: x'",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "behind a process wrapper")


    def test_default_delivery_hook_classifies_watch_default_shell_payloads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            static_commands = (
                "watch 'git push origin HEAD:main'",
                "watch -n 1 'git push origin HEAD:main'",
                "watch -tn1 'git push origin HEAD:main'",
                "nice watch 'git push origin HEAD:main'",
                "watch -x watch 'git push origin HEAD:main'",
                "watch 'semantic-commit commit --message x'",
                "watch -n 1 'semantic-commit commit --message x'",
                "timeout 1 watch 'semantic-commit commit --message x'",
            )
            for command in static_commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "forge-cli repo push-default")

            exec_commands = (
                ("watch -x git push origin HEAD:main", "forge-cli repo push-default"),
                (
                    "watch --exec semantic-commit commit --message x",
                    "behind a process wrapper",
                ),
            )
            for command, fragment in exec_commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)

            dynamic_commands = (
                "watch 'action=push; git $action origin HEAD:main'",
                "watch 'action=commit; semantic-commit $action --message x'",
            )
            for command in dynamic_commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "opaque-governed-operation")


    def test_default_delivery_hook_preserves_watch_exec_and_data_routes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "watch -x git status",
                "watch --exec git status",
                "watch -x semantic-commit commit --help",
                "watch --exec semantic-commit commit --help",
                "watch 'git status'",
                "watch 'semantic-commit commit --help'",
                "watch 'printf git push origin HEAD:main'",
                "watch 'printf semantic-commit commit --message x'",
                "nice watch 'printf git push origin HEAD:main'",
                "watch -x watch 'git status'",
                "watch -tn1 'printf git push origin HEAD:main'",
                "watch -txn1 printf git push origin HEAD:main",
                "watch -td 'printf git push origin HEAD:main'",
                "watch -xd printf git push origin HEAD:main",
                "watch 'printf $HOME'",
                "watch 'printf ~'",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_classifies_watch_exec_shell_payloads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            below_limit = "nice " * 6
            exact_limit = "nice " * 7
            beyond_limit = "nice " * 8
            blocked_commands = (
                (
                    "watch -x sh -c 'git push origin HEAD:main'",
                    "forge-cli repo push-default",
                ),
                (
                    "watch --exec bash -c "
                    "'semantic-commit commit --message x'",
                    "default branch",
                ),
                (
                    "nice watch -x zsh -c 'git push origin HEAD:main'",
                    "forge-cli repo push-default",
                ),
                (
                    f"{below_limit}watch -x sh -c "
                    "'git push origin HEAD:main'",
                    "forge-cli repo push-default",
                ),
                (
                    f"{exact_limit}watch -x sh -c "
                    "'git push origin HEAD:main'",
                    "forge-cli repo push-default",
                ),
                (
                    f"{exact_limit}watch --exec bash -c "
                    "'semantic-commit commit --message x'",
                    "default branch",
                ),
                (
                    f"{beyond_limit}watch -x sh -c "
                    "'git push origin HEAD:main'",
                    "wrapper-depth-limit",
                ),
            )
            for command, fragment in blocked_commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)

            for command in (
                "watch -x sh -c 'git status'",
                "watch --exec bash -c 'printf git push origin HEAD:main'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_preserves_watch_parent_environment_guards(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(
                primary, "feat/watch-environment"
            )
            blocked_commands = (
                (
                    "PATH=/tmp watch 'semantic-commit commit --message x'",
                    "command-local `PATH` override",
                ),
                (
                    "PATH=/tmp nice watch 'semantic-commit commit --message x'",
                    "command-local `PATH` override",
                ),
                (
                    "PATH=/tmp watch -x semantic-commit commit --message x",
                    "behind a process wrapper",
                ),
            )
            for command, fragment in blocked_commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    "PATH=/tmp watch 'printf semantic-commit commit --message x'"
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_hook_preserves_unresolved_context_inside_watch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            self._init_checkout_lease_repo(source)
            self._init_checkout_lease_repo(target)
            subprocess.run(["git", "branch", "-m", "trunk"], cwd=source, check=True)
            subprocess.run(
                ["git", "push", "-q", "origin", "trunk"], cwd=source, check=True
            )
            subprocess.run(
                [
                    "git",
                    "symbolic-ref",
                    "refs/remotes/origin/HEAD",
                    "refs/remotes/origin/trunk",
                ],
                cwd=source,
                check=True,
            )
            source_target = shlex.quote(str(target))
            commands = (
                f"target={source_target}; cd \"$target\"; watch 'git push origin HEAD:main'",
                f"target={source_target}; cd \"$target\"; nice watch 'git push origin HEAD:main'",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=source,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be resolved safely")


    def test_default_delivery_hook_rejects_watch_after_context_changing_wrapper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            self._init_checkout_lease_repo(source)
            self._init_checkout_lease_repo(target)
            subprocess.run(["git", "branch", "-m", "trunk"], cwd=source, check=True)
            subprocess.run(
                ["git", "push", "-q", "origin", "trunk"], cwd=source, check=True
            )
            subprocess.run(
                [
                    "git",
                    "symbolic-ref",
                    "refs/remotes/origin/HEAD",
                    "refs/remotes/origin/trunk",
                ],
                cwd=source,
                check=True,
            )
            target_arg = shlex.quote(str(target))
            blocked_commands = (
                (
                    "systemd-run --user --wait "
                    "watch 'git push origin HEAD:main'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    f"systemd-run --user --working-directory={target_arg} --wait "
                    "watch 'git push origin HEAD:main'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    f"systemd-run --user --pty --working-directory={target_arg} "
                    "watch 'git push origin HEAD:main'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "systemd-run --user --pty "
                    "watch 'git push origin HEAD:main'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "systemd-run --user -t "
                    "watch -x git push origin HEAD:main",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "systemd-run --user --same-dir --wait "
                    "watch 'semantic-commit commit --message x'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "systemd-run --user -d --wait watch 'git status'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    f"unshare --wd={target_arg} "
                    "watch 'git push origin HEAD:main'",
                    "opaque-process-wrapper-context",
                ),
                (
                    f"systemd-run --user --working-directory={target_arg} --wait "
                    "watch -x git push origin HEAD:main",
                    "opaque-process-wrapper-executable",
                ),
                (
                    f"unshare --wd={target_arg} watch --exec "
                    "git push origin HEAD:main",
                    "opaque-process-wrapper-context",
                ),
                (
                    "watch 'systemd-run --user "
                    f"--working-directory={target_arg} --wait "
                    "git push origin HEAD:main'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    f"watch 'unshare --wd={target_arg} "
                    "git push origin HEAD:main'",
                    "opaque-process-wrapper-context",
                ),
                (
                    "systemd-run --user --setenv=PATH=/tmp --wait "
                    "watch 'semantic-commit commit --help'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "watch 'systemd-run --user --setenv=GIT_DIR=/tmp/repo.git "
                    "--wait git status'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "nsenter --target 1 --env "
                    "watch 'semantic-commit commit --help'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "nsenter --target 1 -e watch 'git status'",
                    "opaque-process-wrapper-executable",
                ),
                (
                    "nsenter --target 1 --mount watch 'git status'",
                    "opaque-process-wrapper-executable",
                ),
            )
            for command, fragment in blocked_commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=source,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    f"systemd-run --user --working-directory={target_arg} "
                    "--wait watch 'printf git push origin HEAD:main'"
                ),
                cwd=source,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            for command in (
                "systemd-run --user --scope "
                "watch 'git push origin HEAD:main'",
                f"unshare --wd={target_arg} watch 'git status'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=source,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    "nsenter --target 1 --no-fork "
                    "watch 'printf semantic-commit commit --message x'"
                ),
                cwd=source,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_hook_watch_wrapper_depth_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            exact_limit = "nice " * 8
            cases = (
                (f"{exact_limit}printf ok", True, ""),
                (
                    f"{exact_limit}watch 'git push origin HEAD:main'",
                    False,
                    "forge-cli repo push-default",
                ),
                (
                    f"nice {exact_limit}printf ok",
                    False,
                    "wrapper-depth-limit",
                ),
            )
            for command, allowed, fragment in cases:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    if allowed:
                        self.assert_allowed(decision)
                    else:
                        self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_blocks_dynamic_semantic_modes_behind_launchers(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "action=commit; prlimit -- semantic-commit $action --message x",
                "action=commit; setpriv -- semantic-commit $action --message x",
                "action=commit; unshare semantic-commit $action --message x",
                "action=commit; strace -o /tmp/trace semantic-commit $action --message x",
                "action=commit; nsenter --target 1 --mount semantic-commit $action --message x",
                "action=commit; perf stat --null semantic-commit $action --message x",
                "action=commit; perf stat record -e dummy:u -o /dev/null -- semantic-commit $action --message x",
                "action=commit; watch -n 1 semantic-commit $action --message x",
                "action=commit; systemd-run --user --scope semantic-commit $action --message x",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    fragment = (
                        "opaque-process-wrapper-executable"
                        if "nsenter" in command
                        else "semantic-commit operation depends on shell expansion"
                    )
                    self.assert_blocked(
                        decision, fragment
                    )


    def test_default_delivery_hook_blocks_configured_and_shell_git_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "config", "alias.ship", "push origin HEAD:main"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "alias.first", "second"], cwd=repo, check=True
            )
            subprocess.run(
                ["git", "config", "alias.second", "push origin HEAD:main"],
                cwd=repo,
                check=True,
            )
            included = Path(tmp) / "included-aliases.config"
            included.write_text(
                "[alias]\n\tfrominclude = push origin HEAD:main\n",
                encoding="utf-8",
            )
            commands = (
                ("git ship", None),
                ("git first", None),
                ("git -c alias.shell='!git push origin HEAD:main' shell", None),
                (
                    "git -c include.path="
                    f"{shlex.quote(str(included))} frominclude",
                    None,
                ),
                (
                    "git --config-env=include.path=HOOK_INCLUDE frominclude",
                    {"HOOK_INCLUDE": str(included)},
                ),
            )
            for command, env in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "forge-cli repo push-default")


    def test_default_delivery_hook_preserves_inline_remote_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            self._init_checkout_lease_repo(repo)
            alternate = root / "alternate.git"
            subprocess.run(
                [
                    "git",
                    "init",
                    "-q",
                    "--bare",
                    "--initial-branch=trunk",
                    str(alternate),
                ],
                check=True,
            )
            subprocess.run(
                ["git", "push", "-q", str(alternate), "HEAD:trunk"],
                cwd=repo,
                check=True,
            )
            command = (
                "git -c remote.origin.pushurl="
                f"{shlex.quote(str(alternate))} push origin HEAD:trunk"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(command),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "forge-cli repo push-default")


    def test_default_delivery_hook_fails_closed_on_command_local_git_config(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            alternate_home = Path(tmp) / "alternate-home"
            alternate_home.mkdir()
            (alternate_home / ".gitconfig").write_text(
                "[alias]\n\tship = push origin HEAD:main\n", encoding="utf-8"
            )
            commands = (
                (
                    "HOOK_ALIAS='push origin HEAD:main' "
                    "git --config-env=alias.ship=HOOK_ALIAS ship",
                    {"HOOK_ALIAS": "status"},
                ),
                (
                    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.ship "
                    "GIT_CONFIG_VALUE_0='push origin HEAD:main' git ship",
                    None,
                ),
                (
                    "env HOOK_ALIAS='push origin HEAD:main' "
                    "git --config-env=alias.ship=HOOK_ALIAS ship",
                    {"HOOK_ALIAS": "status"},
                ),
                (
                    f"HOME={shlex.quote(str(alternate_home))} git ship",
                    None,
                ),
            )
            for command, env in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "Do not author or push")


    def test_default_delivery_hook_fails_closed_on_repository_retargeting(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = root / "repo-a"
            repo_b = root / "repo-b"
            self._init_checkout_lease_repo(repo_a)
            self._init_checkout_lease_repo(repo_b)
            subprocess.run(
                ["git", "branch", "-m", "trunk"], cwd=repo_b, check=True
            )
            subprocess.run(
                ["git", "push", "-q", "origin", "HEAD:trunk"],
                cwd=repo_b,
                check=True,
            )
            subprocess.run(
                ["git", "symbolic-ref", "HEAD", "refs/heads/trunk"],
                cwd=root / "repo-b-origin.git",
                check=True,
            )
            git_dir = shlex.quote(str(repo_b / ".git"))
            commands = (
                f"git --git-dir={git_dir} push origin HEAD:trunk",
                f"GIT_DIR={git_dir} git push origin HEAD:trunk",
                f"env -C {shlex.quote(str(repo_b))} git push origin HEAD:trunk",
                f"env --ch={shlex.quote(str(repo_b))} git push origin HEAD:trunk",
                "env --sp='-C "
                f"{shlex.quote(str(repo_b))} git push origin HEAD:trunk'",
                "env - git push origin HEAD:refs/heads/feat/safe",
                "env --pa=/usr/bin git push origin HEAD:refs/heads/feat/safe",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo_a,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be resolved safely")


    def test_default_delivery_hook_allows_contextual_diagnostics_and_dry_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            alternate_home = Path(tmp) / "alternate-home"
            alternate_home.mkdir()
            commands = (
                "GIT_DIR=.git git status",
                "git --git-dir=.git status",
                "env -C . git status",
                f"HOME={shlex.quote(str(alternate_home))} git status",
                "GIT_DIR=.git git check-ignore README.md",
                "HOME=/tmp git check-attr diff README.md",
                "env -C . git merge-base HEAD HEAD",
                "GIT_DIR=.git git version",
                "GIT_DIR=.git git submodule status",
                "HOME=/tmp git mergetool --tool-help",
                "git --git-dir=.git push --dry-run origin HEAD:main",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_fails_closed_after_shell_context_change(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = root / "repo-a"
            repo_b = root / "repo-b"
            self._init_checkout_lease_repo(repo_a)
            self._init_checkout_lease_repo(repo_b)
            subprocess.run(
                ["git", "branch", "-m", "trunk"], cwd=repo_b, check=True
            )
            subprocess.run(
                ["git", "push", "-q", "origin", "HEAD:trunk"],
                cwd=repo_b,
                check=True,
            )
            subprocess.run(
                ["git", "symbolic-ref", "HEAD", "refs/heads/trunk"],
                cwd=root / "repo-b-origin.git",
                check=True,
            )
            alternate_home = root / "alternate-home"
            alternate_home.mkdir()
            (alternate_home / ".gitconfig").write_text(
                "[alias]\n\tship = push origin HEAD:main\n", encoding="utf-8"
            )
            context_script = root / "context.sh"
            context_script.write_text(
                f"export HOME={shlex.quote(str(alternate_home))}\n",
                encoding="utf-8",
            )
            commands = (
                f"cd {shlex.quote(str(repo_b))} && git push origin HEAD:trunk",
                f"export HOME={shlex.quote(str(alternate_home))}; git ship",
                f"HOME={shlex.quote(str(alternate_home))}; git ship",
                "unset HOME; git push origin HEAD:refs/heads/feat/safe",
                "builtin cd "
                f"{shlex.quote(str(repo_b))}; git push origin HEAD:trunk",
                "noglob cd "
                f"{shlex.quote(str(repo_b))}; git push origin HEAD:trunk",
                f"HOME={shlex.quote(str(alternate_home))} export HOME; git ship",
                "builtin export HOME="
                f"{shlex.quote(str(alternate_home))}; git ship",
                f". {shlex.quote(str(context_script))}; git ship",
                f"source {shlex.quote(str(context_script))}; git ship",
                "nocorrect source "
                f"{shlex.quote(str(context_script))}; git ship",
                "builtin builtin cd "
                f"{shlex.quote(str(repo_b))}; git push origin HEAD:trunk",
                "builtin builtin export HOME="
                f"{shlex.quote(str(alternate_home))}; git ship",
                "builtin builtin . "
                f"{shlex.quote(str(context_script))}; git ship",
                "context_builtin=cd; builtin \"$context_builtin\" "
                f"{shlex.quote(str(repo_b))}; git push origin HEAD:trunk",
                "builtin builtin builtin builtin builtin builtin builtin "
                "builtin builtin cd "
                f"{shlex.quote(str(repo_b))}; git push origin HEAD:trunk",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo_a,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be resolved safely")


    def test_default_delivery_hook_does_not_probe_an_unreachable_remote(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(
                primary, "feat/tiny-repair"
            )
            subprocess.run(
                [
                    "git",
                    "remote",
                    "set-url",
                    "--push",
                    "origin",
                    str(root / "missing.git"),
                ],
                cwd=repo,
                check=True,
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    "semantic-commit commit --message 'fix: tiny repair'"
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_git_probe_caps_output_and_kills_descendants(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_git_probe_resource_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fake_git = root / "fake-git"
                child_pid = root / "child.pid"
                fake_git.write_text(
                    "#!/bin/sh\n"
                    "sleep 30 &\n"
                    "printf '%s' \"$!\" > \"$1\"\n"
                    "yes x | head -c 131072\n"
                    "wait\n",
                    encoding="utf-8",
                )
                fake_git.chmod(0o755)
                probe = module.GitProbe(
                    timeout_seconds=2.0,
                    output_limit_bytes=1024,
                    executable=str(fake_git),
                )
                started = time.perf_counter()
                completed, status = probe.run_with_status(root, str(child_pid))
                elapsed = time.perf_counter() - started
                self.assertIsNone(completed)
                self.assertEqual(status, "output-limit")
                self.assertLess(elapsed, 1.5)
                self.assert_process_stopped(int(child_pid.read_text(encoding="utf-8")))
        finally:
            sys.modules.pop(spec.name, None)


    def test_default_delivery_git_probe_timeout_kills_descendants(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_git_probe_timeout_cleanup_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fake_git = root / "fake-git"
                child_pid = root / "child.pid"
                fake_git.write_text(
                    "#!/bin/sh\n"
                    "sleep 30 &\n"
                    "printf '%s' \"$!\" > \"$1\"\n"
                    "wait\n",
                    encoding="utf-8",
                )
                fake_git.chmod(0o755)
                probe = module.GitProbe(
                    timeout_seconds=0.25,
                    output_limit_bytes=1024,
                    executable=str(fake_git),
                )
                completed, status = probe.run_with_status(root, str(child_pid))
                self.assertIsNone(completed)
                self.assertEqual(status, "timeout")
                self.assert_process_stopped(int(child_pid.read_text(encoding="utf-8")))
        finally:
            sys.modules.pop(spec.name, None)


    def test_default_delivery_git_probe_uses_one_total_deadline(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_git_probe_deadline_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fake_git = root / "fake-git"
                fake_git.write_text(
                    "#!/bin/sh\nsleep 0.65\nprintf ok\n", encoding="utf-8"
                )
                fake_git.chmod(0o755)
                probe = module.GitProbe(
                    timeout_seconds=1.0,
                    output_limit_bytes=1024,
                    executable=str(fake_git),
                )
                started = time.perf_counter()
                first = probe.run(root, "status")
                second = probe.run(root, "status")
                elapsed = time.perf_counter() - started
                self.assertIsNotNone(first)
                self.assertIsNone(second)
                self.assertLess(elapsed, 1.6)
        finally:
            sys.modules.pop(spec.name, None)


    def test_default_delivery_hook_blocks_stale_cached_remote_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                [
                    "git",
                    "symbolic-ref",
                    "refs/remotes/origin/HEAD",
                    "refs/remotes/origin/feat/safe",
                ],
                cwd=repo,
                check=True,
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("git push origin HEAD:main"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            # A stale cached head makes the destination unprovable rather than
            # proven-bad, so this is the unverified class, and the remedy is the
            # governed push surface — which re-resolves the default itself.
            self.assert_blocked(decision, "[default-delivery: unverified]")
            self.assert_blocked(decision, "git-cli push")


    def test_default_delivery_hook_uses_only_cached_head_for_push_classification(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_cached_timeout_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)

            class DefaultBranchProbe:
                def __init__(
                    self,
                    *,
                    cached_ref: str = "origin/main\n",
                    primary_ref: str = "main",
                ) -> None:
                    self.cached_ref = cached_ref
                    self.primary_ref = primary_ref

                def run(
                    self, _cwd: Path, *arguments: str
                ) -> subprocess.CompletedProcess[str] | None:
                    if "ls-remote" in arguments or arguments[:2] == (
                        "remote",
                        "get-url",
                    ):
                        raise AssertionError(f"network probe attempted: {arguments!r}")
                    if arguments[-1] == "refs/remotes/origin/HEAD":
                        return subprocess.CompletedProcess(
                            ["git", *arguments],
                            0 if self.cached_ref else 1,
                            self.cached_ref,
                            "",
                        )
                    if arguments[-2:] == ("list", "--porcelain"):
                        branch = (
                            f"branch refs/heads/{self.primary_ref}\n"
                            if self.primary_ref
                            else ""
                        )
                        return subprocess.CompletedProcess(
                            ["git", *arguments],
                            0,
                            f"worktree /repo\nHEAD deadbeef\n{branch}\n",
                            "",
                        )
                    if arguments[-1] == "HEAD":
                        return subprocess.CompletedProcess(
                            ["git", *arguments], 0, "feat/tiny-repair\n", ""
                        )
                    if "config" in arguments and "--get" in arguments:
                        return subprocess.CompletedProcess(
                            ["git", *arguments], 1, "", ""
                        )
                    raise AssertionError(f"unexpected git probe: {arguments!r}")

            for arguments in (
                ["origin", "feat/tiny-repair"],
                ["origin", "HEAD:refs/heads/feat/tiny-repair"],
            ):
                with self.subTest(allowed=arguments):
                    self.assertIs(
                        module.push_targets_default(
                            DefaultBranchProbe(), arguments, Path("."), []
                        ),
                        False,
                    )

            self.assertEqual(
                module.invocation_block_reason(
                    DefaultBranchProbe(),
                    ["git", "push", "-u", "origin", "feat/tiny-repair"],
                    Path("."),
                ),
                "",
            )
            self.assertIs(
                module.push_targets_default(
                    DefaultBranchProbe(), ["origin", "HEAD:main"], Path("."), []
                ),
                True,
            )
            # No cached head at all leaves the default's name unknown, so a
            # branch destination cannot be cleared.
            self.assertIsNone(
                module.push_targets_default(
                    DefaultBranchProbe(cached_ref=""),
                    ["origin", "HEAD:refs/heads/feat/tiny-repair"],
                    Path("."),
                    [],
                )
            )
            # An uncorroborated cached head still names a candidate default, and
            # this destination is not it. See
            # `test_default_delivery_hook_classifies_pushes_without_a_corroborated_default`
            # for the candidate-set rules this relies on.
            self.assertIs(
                module.push_targets_default(
                    DefaultBranchProbe(primary_ref=""),
                    ["origin", "HEAD:refs/heads/feat/tiny-repair"],
                    Path("."),
                    [],
                ),
                False,
            )

            expected = (
                (["origin"], None),
                (["--all", "origin"], True),
                (["--mirror", "origin"], True),
                (["--delete", "origin", "feat/tiny-repair"], False),
                (["--delete", "origin", "main"], True),
                # A delete classified by name alone missed this: the pattern
                # compared unequal to `main` and the push was admitted, even
                # though it deletes every branch including the default.
                (["--delete", "origin", "*"], True),
                (["--delete", "origin"], None),
                (["origin", ":feat/tiny-repair"], False),
                (["origin", ":main"], True),
                (["origin", "HEAD"], False),
                (["origin", "refs/heads/release/*:refs/heads/release/*"], False),
            )
            for arguments, result in expected:
                with self.subTest(arguments=arguments):
                    self.assertIs(
                        module.push_targets_default(
                            DefaultBranchProbe(), arguments, Path("."), []
                        ),
                        result,
                    )
        finally:
            sys.modules.pop(spec.name, None)


    def test_default_delivery_hook_classifies_pushes_without_a_corroborated_default(
        self,
    ) -> None:
        """An unresolved default must not make every push unclassifiable.

        Three situations collapse into "no corroborated default" today, and each
        one carries different evidence:

        * no cached remote HEAD at all — the default's name is unknown, so any
          branch destination stays unverified;
        * a cached HEAD the primary worktree does not corroborate — the default
          is one of two candidate names, so a destination that is neither is
          provably safe;
        * a destination that is not a branch at all — provably safe whatever the
          default branch turns out to be.
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_uncorroborated_default_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)

            class DefaultBranchProbe:
                """Answer only the local probes the classifier is allowed to make."""

                def __init__(
                    self,
                    *,
                    cached_ref: str = "origin/main\n",
                    primary_ref: str = "main",
                    current_ref: str = "feat/tiny-repair\n",
                ) -> None:
                    self.cached_ref = cached_ref
                    self.primary_ref = primary_ref
                    self.current_ref = current_ref

                def run(
                    self, _cwd: Path, *arguments: str
                ) -> subprocess.CompletedProcess[str] | None:
                    if "ls-remote" in arguments or arguments[:2] == (
                        "remote",
                        "get-url",
                    ):
                        raise AssertionError(f"network probe attempted: {arguments!r}")
                    if arguments[-1] == "refs/remotes/origin/HEAD":
                        return subprocess.CompletedProcess(
                            ["git", *arguments],
                            0 if self.cached_ref else 1,
                            self.cached_ref,
                            "",
                        )
                    if arguments[-2:] == ("list", "--porcelain"):
                        branch = (
                            f"branch refs/heads/{self.primary_ref}\n"
                            if self.primary_ref
                            else ""
                        )
                        return subprocess.CompletedProcess(
                            ["git", *arguments],
                            0,
                            f"worktree /repo\nHEAD deadbeef\n{branch}\n",
                            "",
                        )
                    if arguments[-1] == "HEAD":
                        return subprocess.CompletedProcess(
                            ["git", *arguments], 0, self.current_ref, ""
                        )
                    if "config" in arguments and "--get" in arguments:
                        return subprocess.CompletedProcess(
                            ["git", *arguments], 1, "", ""
                        )
                    raise AssertionError(f"unexpected git probe: {arguments!r}")

            def verdict(probe: object, arguments: list[str]) -> bool | None:
                return module.push_targets_default(probe, arguments, Path("."), [])

            # Resolution states are named, so the dead always-false second
            # element of the old tuple cannot come back.
            self.assertEqual(
                module.resolve_default_branch(
                    DefaultBranchProbe(), Path("."), "origin", []
                ).confidence,
                module.DEFAULT_BRANCH_CORROBORATED,
            )
            self.assertEqual(
                module.resolve_default_branch(
                    DefaultBranchProbe(primary_ref="feat/work"), Path("."), "origin", []
                ).confidence,
                module.DEFAULT_BRANCH_UNCORROBORATED,
            )
            self.assertEqual(
                module.resolve_default_branch(
                    DefaultBranchProbe(cached_ref=""), Path("."), "origin", []
                ).confidence,
                module.DEFAULT_BRANCH_UNKNOWN,
            )

            # A destination outside refs/heads/ cannot move any branch, so it
            # needs no default-branch name at all.
            for arguments in (
                ["origin", "refs/tags/v1.0.0:refs/tags/v1.0.0"],
                ["origin", "refs/tags/*:refs/tags/*"],
                ["origin", "refs/notes/commits:refs/notes/commits"],
                ["origin", "v1.0.0^{}:refs/tags/v1.0.0"],
            ):
                for probe in (
                    DefaultBranchProbe(),
                    DefaultBranchProbe(cached_ref=""),
                    DefaultBranchProbe(cached_ref="", primary_ref=""),
                    DefaultBranchProbe(primary_ref="feat/work"),
                ):
                    with self.subTest(non_branch=arguments, cached=probe.cached_ref):
                        self.assertIs(verdict(probe, arguments), False)

            # An uncorroborated cache narrows the default to two candidate
            # names. A destination that is neither is provably safe.
            uncorroborated = DefaultBranchProbe(primary_ref="feat/work")
            for arguments in (
                ["origin", "refs/heads/feat/a:refs/heads/feat/a"],
                # A bare destination carries the same risk as the qualified
                # form, and it is the shape the refusal text recommends.
                ["origin", "feat/a:feat/a"],
                ["origin", "HEAD:refs/heads/feat/tiny-repair"],
                ["--delete", "origin", "feat/a"],
            ):
                with self.subTest(uncorroborated_safe=arguments):
                    self.assertIs(verdict(uncorroborated, arguments), False)
            # Either candidate stays unverified: neither name is disproved.
            for arguments in (
                ["origin", "main:main"],
                ["origin", "feat/work:feat/work"],
                ["origin", "refs/heads/*:refs/heads/*"],
                ["--delete", "origin", "main"],
                ["origin"],
            ):
                with self.subTest(uncorroborated_candidate=arguments):
                    self.assertIsNone(verdict(uncorroborated, arguments))

            # A cached HEAD the primary worktree cannot corroborate because the
            # inventory is unreadable is still one candidate name.
            self.assertIs(
                verdict(
                    DefaultBranchProbe(primary_ref=""),
                    ["origin", "HEAD:refs/heads/feat/tiny-repair"],
                ),
                False,
            )
            self.assertIsNone(
                verdict(DefaultBranchProbe(primary_ref=""), ["origin", "main:main"])
            )

            # With no cached HEAD the default's name is unknown, so a branch
            # destination must not be admitted just because it looks like a
            # feature branch.
            unknown = DefaultBranchProbe(cached_ref="")
            for arguments in (
                ["origin", "main:main"],
                ["origin", "refs/heads/feat/a:refs/heads/feat/a"],
                ["origin", "HEAD:refs/heads/feat/tiny-repair"],
            ):
                with self.subTest(unknown_branch=arguments):
                    self.assertIsNone(verdict(unknown, arguments))

            # An all-refs or mirror push moves every branch, so it is proven bad
            # without knowing which one is the default.
            for arguments in (["--all", "origin"], ["--mirror", "origin"]):
                with self.subTest(all_refs=arguments):
                    self.assertIs(verdict(unknown, arguments), True)

            # The refusal names the condition that actually tripped, instead of
            # recommending a surface that cannot run here either.
            reason = module.invocation_block_reason(
                DefaultBranchProbe(cached_ref=""),
                ["git", "push", "origin", "main:main"],
                Path("."),
            )
            self.assertIn(module.MARK_UNVERIFIED, reason)
            self.assertIn("no cached default branch", reason)
            self.assertIn("git remote set-head origin --auto", reason)
            # An empty remote cannot answer that hint, so the refusal has to say
            # so rather than sending the caller around the same loop.
            self.assertIn("has no branches yet", reason)
        finally:
            sys.modules.pop(spec.name, None)


    def test_default_delivery_hook_authors_commits_without_a_corroborated_default(
        self,
    ) -> None:
        """A commit branch that is provably not the default must not be refused.

        The authoring check only ever needs to disprove that the checked-out
        branch is the default, and an uncorroborated cache already narrows the
        default to two candidate names. Routing the question through
        `default_branch`, which withholds an uncorroborated name, refused every
        managed worktree on a repository whenever the primary checkout was
        parked off the default branch — including the delivery workflows that
        park it deliberately and then cannot commit their own follow-up work.

        These are the push-side rules of
        `test_default_delivery_hook_classifies_pushes_without_a_corroborated_default`
        applied to the authoring surface.
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "default_delivery_uncorroborated_authoring_test",
            HOOK_DIR / "block-unsafe-default-delivery.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)

            class DefaultBranchProbe:
                """Answer only the local probes the classifier is allowed to make."""

                def __init__(
                    self,
                    *,
                    cached_ref: str = "origin/main\n",
                    primary_ref: str = "main",
                    current_ref: str = "feat/tiny-repair\n",
                ) -> None:
                    self.cached_ref = cached_ref
                    self.primary_ref = primary_ref
                    self.current_ref = current_ref

                def run(
                    self, _cwd: Path, *arguments: str
                ) -> subprocess.CompletedProcess[str] | None:
                    if "ls-remote" in arguments or arguments[:2] == (
                        "remote",
                        "get-url",
                    ):
                        raise AssertionError(f"network probe attempted: {arguments!r}")
                    if arguments[-1] == "refs/remotes/origin/HEAD":
                        return subprocess.CompletedProcess(
                            ["git", *arguments],
                            0 if self.cached_ref else 1,
                            self.cached_ref,
                            "",
                        )
                    if arguments[-2:] == ("list", "--porcelain"):
                        branch = (
                            f"branch refs/heads/{self.primary_ref}\n"
                            if self.primary_ref
                            else ""
                        )
                        return subprocess.CompletedProcess(
                            ["git", *arguments],
                            0,
                            f"worktree /repo\nHEAD deadbeef\n{branch}\n",
                            "",
                        )
                    if arguments[-1] == "HEAD":
                        return subprocess.CompletedProcess(
                            ["git", *arguments], 0, self.current_ref, ""
                        )
                    if "config" in arguments and "--get" in arguments:
                        return subprocess.CompletedProcess(
                            ["git", *arguments], 1, "", ""
                        )
                    raise AssertionError(f"unexpected git probe: {arguments!r}")

            def verdict(probe: object) -> str:
                return module.semantic_commit_block_reason(
                    probe,
                    ["commit", "--message", "fix(agent): tighten hook parser"],
                    Path("."),
                    "the tool workdir",
                )

            # A primary checkout parked off the default leaves two candidate
            # names. A commit branch that is neither is provably not the
            # default, under either hypothesis.
            self.assertEqual(
                verdict(DefaultBranchProbe(primary_ref="dependabot/cargo/bump")), ""
            )

            # Either candidate stays unproven, so neither is cleared. This is
            # the half that keeps an over-correction from opening up `main`.
            for current in ("main\n", "dependabot/cargo/bump\n"):
                with self.subTest(uncorroborated_candidate=current):
                    self.assertIn(
                        module.MARK_UNVERIFIED,
                        verdict(
                            DefaultBranchProbe(
                                primary_ref="dependabot/cargo/bump",
                                current_ref=current,
                            )
                        ),
                    )

            # No cached head at all leaves the default's name unknown, so no
            # commit branch can be cleared.
            self.assertIn(
                module.MARK_UNVERIFIED, verdict(DefaultBranchProbe(cached_ref=""))
            )
            # An unreadable checked-out branch is undecidable for the same
            # reason, whatever the default resolves to.
            self.assertIn(
                module.MARK_UNVERIFIED, verdict(DefaultBranchProbe(current_ref=""))
            )

            # A corroborated default still blocks authoring on it, and still
            # clears every other branch.
            self.assertIn(
                module.MARK_BLOCKED, verdict(DefaultBranchProbe(current_ref="main\n"))
            )
            self.assertEqual(verdict(DefaultBranchProbe()), "")
        finally:
            sys.modules.pop(spec.name, None)


    def test_default_delivery_hook_allows_feature_governed_and_read_only_routes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(
                primary, "feat/tiny-repair"
            )
            commands = (
                "semantic-commit commit --message 'fix: tiny repair'",
                "semantic-commit fixup HEAD~1",
                "semantic-commit squash HEAD~1",
                "semantic-commit commit --help",
                "semantic-commit fixup --help",
                "semantic-commit squash --dry-run HEAD~1",
                "semantic-commit commit --dry-run --message 'fix: tiny repair'",
                "git push -u origin feat/tiny-repair",
                "git push origin HEAD:refs/heads/feat/tiny-repair",
                "noglob git push origin HEAD:refs/heads/feat/tiny-repair",
                "nocorrect git push origin HEAD:refs/heads/feat/tiny-repair",
                "zsh -c "
                + shlex.quote(
                    "noglob git push origin "
                    "HEAD:refs/heads/feat/tiny-repair"
                ),
                "noglob semantic-commit commit --message 'fix: tiny repair'",
                "nice git status",
                "timeout 5 git status",
                "nohup git status",
                "stdbuf -oL git status",
                "nice printf --version",
                "setsid git status",
                "ionice git status",
                "chrt -o 0 git status",
                "taskset -c 0 git status",
                "setsid printf --version",
                "prlimit -- git status",
                "setpriv -- git status",
                "unshare git status",
                "strace -o /tmp/trace git status",
                "prlimit --nofile=1024 -- git status",
                "setpriv --no-new-privs git status",
                "unshare --fork git status",
                "strace --seccomp-bpf -o /tmp/trace git status",
                "perf stat --null git status",
                "perf stat record -e dummy:u -o /dev/null -- git status",
                "watch -n 1 git status",
                "systemd-run --user --scope git status",
                "prlimit -- semantic-commit commit --help",
                "setpriv -- semantic-commit commit --help",
                "unshare semantic-commit commit --help",
                "strace -o /tmp/trace semantic-commit commit --help",
                "perf stat --null semantic-commit commit --help",
                "perf stat record -e dummy:u -o /dev/null -- semantic-commit commit --help",
                "watch -n 1 semantic-commit commit --help",
                "systemd-run --user --scope semantic-commit commit --help",
                "echo git push origin HEAD:main",
                "printf git push origin HEAD:main",
                "rg git push README.md",
                "echo nice semantic-commit commit",
                "printf timeout semantic-commit commit",
                "rg env semantic-commit commit README.md",
                "echo $cmd push",
                "git push --tags origin",
                "git push origin refs/tags/v1.0.0",
                "git push origin 'refs/heads/release/*:refs/heads/release/*'",
                "git push --dry-run origin HEAD:refs/heads/main",
                "forge-cli repo push-default --expected-base "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --reason-file reason.md",
                "forge-cli repo push-default --help",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_allows_expanded_non_governed_executables(
        self,
    ) -> None:
        self.assertEqual(
            hook_common.shell_tokens(
                r"printf x '\'; /usr/bin/@(git) push origin HEAD:main"
            ),
            [
                "printf",
                "x",
                "\\",
                ";",
                "/usr/bin/@(git)",
                "push",
                "origin",
                "HEAD:main",
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(
                primary, "feat/tiny-repair"
            )
            command = (
                "scripts/install-hotfix-agent-runtimes.sh && "
                '"$HOME/.local/bin/hotfix-codex" --cwd "$PWD" --version && '
                '"$HOME/.local/bin/hotfix-claude" --cwd "$PWD" --version'
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(command),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            for hidden in (
                "$tool --version",
                '"$HOME/.local/bin/semantic-commit" commit '
                "--message 'fix: hidden writer'",
                '"$HOMEBREW_PREFIX/bin/semantic-*" commit '
                "--message 'fix: glob writer'",
                '"$HOMEBREW_PREFIX/bin/semanti?-commit" commit '
                "--message 'fix: glob writer'",
                '"$HOMEBREW_PREFIX/bin/semanti[c]-commit" commit '
                "--message 'fix: glob writer'",
                '"$HOMEBREW_PREFIX/bin/{semantic-commit,tool}" commit '
                "--message 'fix: brace writer'",
            ):
                with self.subTest(hidden=hidden):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(hidden),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNotNone(decision)
                    if hidden.startswith("$tool"):
                        self.assert_blocked(decision, "rule=opaque-executable")
                        self.assert_blocked(
                            decision, "operation=dynamic-executable"
                        )
                    else:
                        self.assert_blocked(decision, "semantic-commit")

            semantic_commit = Path(
                shutil.which("semantic-commit") or "/usr/bin/semantic-commit"
            )
            dynamic_executables = (
                "/usr/bin/g[i]t push origin HEAD:main",
                "/usr/bin/g?t push origin HEAD:main",
                "/usr/bin/{git,echo} push origin HEAD:main",
                "~/bin/git push origin HEAD:main",
                str(semantic_commit.with_name("semantic-*"))
                + " commit --message 'fix: glob writer'",
            )
            for hidden in dynamic_executables:
                with self.subTest(dynamic_executable=hidden):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(hidden),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    if hidden.startswith("~"):
                        self.assert_blocked(decision, "push")
                    else:
                        self.assert_blocked(decision, "rule=opaque-executable")

            shell_expanded_governed_executables = (
                "=git push origin HEAD:main",
                "command =git push origin HEAD:main",
                "exec =git push origin HEAD:main",
                "/usr/bin/@(git) push origin HEAD:main",
                "/usr/bin/@(git|echo) push origin HEAD:main",
                "/usr/bin/git(N) push origin HEAD:main",
                "/usr/bin/git(.) push origin HEAD:main",
                "setopt EXTENDED_GLOB; /usr/bin/gi#t push origin HEAD:main",
                "setopt EXTENDED_GLOB; /usr/bin/gi##t push origin HEAD:main",
                "setopt EXTENDED_GLOB; /usr/bin/git~notgit push origin HEAD:main",
                "setopt EXTENDED_GLOB; /usr/bin/git^notgit push origin HEAD:main",
                r"printf x '\'; /usr/bin/@(git) push origin HEAD:main",
                "/usr/bin/@(semantic-commit) commit --message 'fix: extglob writer'",
                "/usr/bin/semantic-commit(N) commit "
                "--message 'fix: qualifier writer'",
                "setopt EXTENDED_GLOB; /usr/bin/semanti#c-commit commit "
                "--message 'fix: repetition writer'",
                "bash -O extglob -c "
                + shlex.quote("/usr/bin/@(git) push origin HEAD:main"),
                "bash -O extglob -c "
                + shlex.quote(
                    "/usr/bin/@(semantic-commit) commit "
                    "--message 'fix: nested extglob writer'"
                ),
                "zsh -c "
                + shlex.quote("/usr/bin/git(N) push origin HEAD:main"),
                "zsh -c "
                + shlex.quote(
                    "/usr/bin/semantic-commit(.) commit "
                    "--message 'fix: nested qualifier writer'"
                ),
                "zsh -o EXTENDED_GLOB -c "
                + shlex.quote("/usr/bin/gi#t push origin HEAD:main"),
                "zsh -o EXTENDED_GLOB -c "
                + shlex.quote("/usr/bin/git^notgit push origin HEAD:main"),
                "zsh -o EXTENDED_GLOB -c "
                + shlex.quote(
                    "/usr/bin/semanti#c-commit commit "
                    "--message 'fix: nested repetition writer'"
                ),
            )
            for hidden in shell_expanded_governed_executables:
                with self.subTest(shell_expansion=hidden):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(hidden),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "rule=opaque-executable")

            alias_hidden_governed_executables = (
                "alias runner=git; eval 'runner push origin HEAD:main'",
                "alias runner='git push origin HEAD:main'; eval runner",
                "definition=runner=git; alias \"$definition\"; "
                "eval 'runner push origin HEAD:main'",
                "builtin alias runner=git; "
                "eval 'runner push origin HEAD:main'",
                "noglob alias runner=git; "
                "eval 'runner push origin HEAD:main'",
                "nocorrect alias runner=git; "
                "eval 'runner push origin HEAD:main'",
                "- alias runner=git; "
                "eval 'runner push origin HEAD:main'",
                "- hash runner=/usr/bin/git; "
                "runner push origin HEAD:main",
                "- nocorrect noglob alias runner=git; "
                "eval 'runner push origin HEAD:main'",
                "noglob hash runner=/usr/bin/git; "
                "runner push origin HEAD:main",
                "alias runner=git; (unalias runner); "
                "eval 'runner push origin HEAD:main'",
                "alias runner=git; bash -c 'unalias runner'; "
                "eval 'runner push origin HEAD:main'",
                "hash runner=/usr/bin/git; runner push origin HEAD:main",
                "hash -p /usr/bin/git runner; runner push origin HEAD:main",
                "action=-c; functions \"$action\" git runner; "
                "runner push origin HEAD:main",
                "commands[runner]=/usr/bin/git; runner push origin HEAD:main",
                "source <(printf 'runner() { git push origin HEAD:main; }'); "
                "runner",
                "alias runner=semantic-commit; "
                "eval \"runner commit --message 'fix: alias writer'\"",
                "zsh -c "
                + shlex.quote(
                    "alias runner=git; eval 'runner push origin HEAD:main'"
                ),
                "zsh -c "
                + shlex.quote(
                    "noglob alias runner=git; "
                    "eval 'runner push origin HEAD:main'"
                ),
                "zsh -c "
                + shlex.quote(
                    "nocorrect noglob alias runner=git; "
                    "eval 'runner push origin HEAD:main'"
                ),
                "bash -O expand_aliases -c "
                + shlex.quote(
                    "alias runner=git; eval 'runner push origin HEAD:main'"
                ),
            )
            for hidden in alias_hidden_governed_executables:
                with self.subTest(alias_expansion=hidden):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(hidden),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(
                        decision, "rule=opaque-shell-resolution"
                    )

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    "alias runner=git; /usr/bin/printf --version"
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            read_only_resolution_queries = (
                "alias",
                "alias runner",
                "hash",
                "hash -t git",
                "functions",
                "functions runner",
                "enable",
                "enable -p",
                "enable -a",
            )
            for query in read_only_resolution_queries:
                with self.subTest(read_only_resolution_query=query):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(f"{query}; printf --version"),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            resolution_mutations = (
                "hash -r",
                "functions -c runner copy",
                "enable printf",
            )
            for mutation in resolution_mutations:
                with self.subTest(executable_resolution_mutation=mutation):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(f"{mutation}; printf --version"),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(
                        decision, "rule=opaque-shell-resolution"
                    )

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("/usr/bin/printf --version"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_hook_admits_literal_conditional_command_words(
        self,
    ) -> None:
        # `[` and `[[` are literal test words, and a zsh `$+name[key]` presence
        # test expands only to 0 or 1. None can expand to `git` or
        # `semantic-commit`, yet the bracket read as a glob made ordinary
        # read-only loops and conditionals unverified.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            allowed = (
                "if [ -f AGENTS.md ]; then cat AGENTS.md; "
                "else printf 'none\\n'; fi",
                'for f in a b; do if [[ -e "$f" ]]; then echo "$f"; fi; done',
                '[ ! -e ~/.kube/config ] && [ -d "$HOME" ] || exit 1',
                "git merge-tree $(git merge-base HEAD HEAD) HEAD HEAD | "
                "while read -r blob path; do "
                'if [ "$blob" != x ]; then printf \'%s\\n\' "$path"; fi; done',
                "zsh -ic '(( $+functions[z] )) && print yes || print no'",
                "(( $+commands[zoxide] )) && print present",
                "zsh -ic 'alias bat 2>/dev/null'; git status --short",
            )
            for command in allowed:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            still_classified = (
                (
                    "[ -f README.md ] && git push origin main",
                    "[default-delivery: blocked]",
                ),
                (
                    "if [[ -f README.md ]]; then git push origin HEAD:main; fi",
                    "[default-delivery: blocked]",
                ),
                ('[ -n "$x" ] && $tool push origin main', "rule=opaque-executable"),
                (
                    "(( $+functions[$(printf git)] )) push origin main",
                    "rule=opaque-executable",
                ),
                ("$+tool[$key] push origin main", "rule=opaque-executable"),
                ("[x] push origin main", "rule=opaque-executable"),
                (
                    "alias g=git 2>/dev/null; g push origin main",
                    "rule=opaque-shell-resolution",
                ),
                (
                    "[ -f README.md ] && semantic-commit commit "
                    "--message 'fix: x'",
                    "changed executable resolution",
                ),
            )
            for command, fragment in still_classified:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_classifies_indirect_quoted_heredocs(self) -> None:
        # Issue #210: classify literal shell input without treating document
        # prose or an interpreter's own language as shell commands.
        shapes = (
            "sudo bash <<'EOF'\n{body}\nEOF",
            "doas sh <<'EOF'\n{body}\nEOF",
            "env bash <<'EOF'\n{body}\nEOF",
            "command sh <<'EOF'\n{body}\nEOF",
            "exec bash <<'EOF'\n{body}\nEOF",
            "nice bash <<'EOF'\n{body}\nEOF",
            "nohup sh <<'EOF'\n{body}\nEOF",
            "source /dev/stdin <<'EOF'\n{body}\nEOF",
            ". /dev/fd/0 <<'EOF'\n{body}\nEOF",
            "cat <<'EOF' | bash\n{body}\nEOF",
            "{{ cat <<'EOF'\n{body}\nEOF\n}} | bash",
            "(cat <<'EOF'\n{body}\nEOF\n) | sh",
            "bash <(cat <<'EOF'\n{body}\nEOF\n)",
            "cat <<'EOF' > x.sh\n{body}\nEOF\nbash x.sh",
            "cat <<'EOF' > x.sh\n{body}\nEOF\n./x.sh",
            "cat <<'EOF' > x.sh\n{body}\nEOF\nnohup ./x.sh",
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            for shape in shapes:
                for body, blocked in (
                    ("git push origin HEAD:main", True),
                    ("/usr/bin/git status --short", False),
                ):
                    command = shape.format(body=body)
                    with self.subTest(command=command):
                        code, decision, stderr = run_hook(
                            "block-unsafe-default-delivery.py",
                            command_payload(command),
                            cwd=repo,
                        )
                        self.assertEqual(code, 0, stderr)
                        if blocked:
                            self.assert_blocked(decision, "[default-delivery:")
                        else:
                            self.assert_allowed(decision)

            for command in (
                "cat <<'EOF'\ngit push origin HEAD:main\nEOF",
                "cat > notes.md <<'EOF'\ngit push origin HEAD:main\nEOF",
                "cat <<'EOF' | grep bash\ngit push origin HEAD:main\nEOF",
                "python3 - <<'EOF'\nprint('git push origin HEAD:main')\nEOF",
                "bash ./reader.sh <<'EOF'\ngit push origin HEAD:main\nEOF",
                "source ./reader.sh <<'EOF'\ngit push origin HEAD:main\nEOF",
                "cat <<'EOF'\ngit push origin HEAD:main\nEOF\nbash -c 'git status'",
                "cat > notes.md <<'EOF'\ngit push origin HEAD:main\nEOF\nbash other.sh",
                "cat <<'EOF'\ngit push origin HEAD:main\nEOF\n"
                "source /dev/stdin <<'READ'\n/usr/bin/git status\nREAD",
                "cat <<'EOF' | bash -n\ngit push origin HEAD:main\nEOF",
                "source /dev/stdin 3<<'EOF'\ngit push origin HEAD:main\nEOF",
                "xargs git status <<'EOF'\n--short\nEOF",
                "cat <<'EOF' > notes.md | bash\ngit push origin HEAD:main\nEOF",
                "(cat <<'EOF' > notes.md\ngit push origin HEAD:main\nEOF\n) | bash",
                "cat reader.sh <<'EOF' | bash\ngit push origin HEAD:main\nEOF",
                "doas sh <<'EOF' </dev/null\ngit push origin HEAD:main\nEOF",
                "source /dev/stdin <<'EOF' </dev/null\ngit push origin HEAD:main\nEOF",
                "cat<<'EOF' | bash -n\ngit push origin HEAD:main\nEOF",
            ):
                with self.subTest(read=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("xargs git <<'EOF'\npush origin HEAD:main\nEOF"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery:")

            # A caller-controlled word must never identify an internal body.
            # Include quote concatenation and a collision with the first
            # namespace a raw-text-only collision check would choose.
            for preamble in (
                "echo __agent_runtime_heredoc_body_0__; ",
                ": __agent_runtime_heredoc_body_0__\n",
                "echo '__agent_runtime_heredoc_body_0__'; ",
                "echo '__agent_runtime_'heredoc_body_0__; ",
                "echo '__agent_runtime_heredoc_body_'_0__; ",
            ):
                for shape in (shapes[7], shapes[9], shapes[13]):
                    for body, blocked in (
                        ("git push origin HEAD:main", True),
                        ("/usr/bin/git status --short", False),
                    ):
                        command = preamble + shape.format(body=body)
                        with self.subTest(forged_marker=command):
                            code, decision, stderr = run_hook(
                                "block-unsafe-default-delivery.py",
                                command_payload(command),
                                cwd=repo,
                            )
                            self.assertEqual(code, 0, stderr)
                            if blocked:
                                self.assert_blocked(decision, "[default-delivery:")
                            else:
                                self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    "cat 3<<'DATA' <<'READ'\nnotes\nDATA\nnotes\nREAD\n"
                    "cat <<'SCRIPT' | bash\ngit push origin HEAD:main\nSCRIPT"
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery:")


    def test_default_delivery_hook_admits_read_only_inventory_shapes(
        self,
    ) -> None:
        # sympoies/agent-runtime-kit#206: cross-repository read-only
        # inventories were refused as unverified delivery. Each shape below is
        # a read the guard misparsed: a `[[`/`[` operand list exhausted the
        # opaque-candidate scan, `${m%|*}` split at its `|`, a zsh `path=`
        # look-alike inside a grep pattern counted as a PATH assignment, an
        # unprobeable `-C` directory hid the `merge-base` builtin, a `~/`
        # executable path read as dynamic, an arithmetic expansion led with a
        # dynamic word, and an unquoted here-document body fed to a data
        # consumer was tokenized as shell.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            allowed = (
                "gh api repos/o/r/contents/README.md?ref=main --jq .content",
                'gh api -X GET "repos/$r/contents/$p?ref=$b" --jq .content',
                "while IFS='|' read -r r paths; do "
                "b=$(awk -v r=\"$r\" '$1==r{print $2}' repos.txt); "
                'for p in $paths; do [[ "$p" == *CLAUDE.md ]] || continue; '
                'c=$(gh api "repos/$r/contents/$p?ref=$b" --jq .content '
                "2>/dev/null | base64 -d 2>/dev/null | head -c 120); "
                'echo "$r:$p => $c"; done; done < inventory.txt',
                "while IFS='|' read -r r paths; do "
                "b=$(awk -v r=\"$r\" '$1==r{print $2}' repos.txt); "
                'for p in $paths; do [[ "$p" == *CLAUDE.md ]] || continue; '
                'c=$(gh api -X GET "repos/$r/contents/$p?ref=$b" --jq .content); '
                'echo "$r:$p => $c"; done; done < inventory.txt',
                "while IFS='|' read -r r paths; do "
                '[[ -z "$paths" ]] && continue; d=~/Project/$r; '
                '[[ -d $d ]] || { echo "$r => (no local clone)"; continue; }; '
                'for p in $paths; do [[ "$p" == *CLAUDE.md ]] || continue; '
                "printf '%s:%s => %s\\n' \"$r\" \"$p\" "
                '"$(git -C $d show HEAD:$p 2>/dev/null | head -c 100)"; '
                "done; done < inventory.txt",
                'while read d; do git -C "$d" show HEAD:FILE; done < repos.txt',
                'for d in /a /b; do git -C "$d" log --oneline -3; done',
                "R=/srv/repo; git -C $R cat-file -t HEAD 2>&1; for f in a b; do "
                'a=$(git -C $R rev-parse "HEAD:$f"); '
                'b=$(git -C $R rev-parse "HEAD~1:$f"); '
                '[ "$a" = "$b" ] && echo "same $f" || echo "DIFF $f"; done',
                "W4=/srv/worktree; git -C $W4 fetch -q origin; "
                "git -C $W4 log --oneline origin/main -1; "
                "git -C $W4 merge-base --is-ancestor origin/main HEAD "
                '&& echo "on top of main" || echo "needs rebase"',
                "S=85a7379c; for m in $(agent-session message inbox --session $S "
                "--state unread --format json | jq -r '.data.messages[]? | "
                '"\\(.message_id)|\\(.sender.session_id[0:8])"\'); do '
                'id=${m%|*}; echo "== $id from ${m#*|}"; '
                "agent-session message show --session $S --message $id "
                "--format json | jq -r '.data.message.body.text'; "
                "agent-session message ack --session $S --message $id "
                "--if-revision 2 --idempotency-key ack-$id --format json "
                ">/dev/null; done",
                'for m in a b c; do agent-session message show "$m"; done',
                'for s in 9c2dc137 0d3aa4a3; do echo "=== $s"; '
                'if [[ $s == 9c2dc137* ]]; then ssh c8 "agent-session glance $s" '
                "2>&1; else agent-session glance $s 2>&1; fi | "
                "grep -v '^\\s*$' | tail -8; done",
                'args="--oneline -3"; git log $args',
                'for args in "" "--topic decision --title x"; do '
                "diff <(printf 'a' | X=1 ~/Project/laoda/bin/laoda notify $args "
                "2>&1) <(printf 'a' | X=1 ./bin/laoda notify $args 2>&1) "
                '>/dev/null && echo "same: $args" || echo "DIFF: $args"; done',
                "LAODA_TOOLS=/srv/w ~/Project/gamalife/bin/jusheng help | head -2",
                "O=/srv/ops; python3 - <<EOF\n"
                "import re\n"
                "p='$O/README.md'\n"
                "lines=open(p).read().split('\\n')\n"
                "start=lines.index('## daily')+2\n"
                "i=start\n"
                "while i<len(lines) and re.match(r'^\\d+\\. ',lines[i]): i+=1\n"
                "rest=[f\"{n+1}. \"+re.sub(r'^\\d+\\. ','',x) "
                "for n,x in enumerate(lines[start:i])]\n"
                "lines[start:i]=rest\n"
                "open(p,'w').write('\\n'.join(lines))\n"
                "EOF\n"
                "sed -n '20,29p' $O/README.md",
                "D=/srv/scratch; cat > $D/p.md <<EOF\n"
                "Retire repo-root \\`CLAUDE.md\\` files in: "
                "$(grep -v '^x$' $D/repos.txt | tr '\\n' ' ')\n"
                "EOF",
                "systemctl show review-broker -p ExecStart --value | "
                "grep -o 'path=[^ ;]*\\|/[^ ;]*review_broker[^ ;]*' | head -3",
                "echo $(( $(stat -c%s README.md) - 400000 ))",
                "echo $(( $x + 1 ))",
                "D=/srv/missing; git -C $D count-objects -v",
                "O=/srv/ops; python3 - <<EOF 2>&1 >/dev/null\nprint('$O')\nEOF",
                "/usr/bin/python3 - <<EOF\nprint('$HOME')\nEOF",
                # A resolution-looking word that is only an argument changes
                # nothing a consumer name resolves to.
                "O=/tmp; python3 - <<EOF\nprint('$O')\nEOF\n"
                "echo 'path=/x' | grep -o 'path=[^ ]*'",
                "O=/tmp; python3 - <<EOF\nprint('$O')\nEOF\ngrep alias notes.txt",
            )
            for command in allowed:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            still_classified = (
                ("git push origin HEAD:main", "[default-delivery: blocked]"),
                (
                    'for d in /a; do git -C "$d" push origin HEAD:main; done',
                    "[default-delivery:",
                ),
                (
                    "semantic-commit commit --message 'fix: x'",
                    "[default-delivery: blocked]",
                ),
                (
                    "forge-cli repo push-default --help; git push origin HEAD:main",
                    "[default-delivery: blocked]",
                ),
                (
                    "action=push; git $action origin HEAD:main",
                    "rule=opaque-governed-operation",
                ),
                ('args="origin HEAD:main"; git push $args', "[default-delivery:"),
                (
                    '[[ "$p" == *CLAUDE.md ]] && git push origin HEAD:main',
                    "[default-delivery: blocked]",
                ),
                (
                    '[ "$a" = "$b" ] && git push origin HEAD:main',
                    "[default-delivery: blocked]",
                ),
                (
                    '[[ "$(git push origin HEAD:main)" == x ]]',
                    "[default-delivery: blocked]",
                ),
                (
                    "id=${m%|*}; git push origin HEAD:main",
                    "[default-delivery: blocked]",
                ),
                (
                    'x=${y:-"$(git push origin HEAD:main)"}',
                    "[default-delivery: blocked]",
                ),
                (
                    "cat <<EOF\n$(git push origin HEAD:main)\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "python3 - <<EOF\nprint('$(git push origin HEAD:main)')\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "python3 - <<EOF\nprint(`git push origin HEAD:main`)\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "bash <<EOF\ngit push origin HEAD:main\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "sudo bash <<EOF\ngit push origin HEAD:main\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "source /dev/stdin <<EOF\ngit push origin HEAD:main\nEOF",
                    "[default-delivery:",
                ),
                (
                    "echo $(( $(git push origin HEAD:main) + 1 ))",
                    "[default-delivery: blocked]",
                ),
                ("~/bin/git push origin HEAD:main", "[default-delivery: blocked]"),
                ("~/bin/$tool push origin HEAD:main", "rule=opaque-executable"),
                (
                    "path=(/tmp/evil $path); printf --version",
                    "[default-delivery: unverified]",
                ),
                ("PATH=/tmp/evil; printf --version", "rule=opaque-shell-resolution"),
                ("PATH+=:/tmp/evil; printf --version", "rule=opaque-shell-resolution"),
                (
                    "2>/dev/null PATH=/tmp/evil; printf --version",
                    "rule=opaque-shell-resolution",
                ),
                (
                    "cat <<EOF | bash\ngit push origin HEAD:main\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "tee >(bash) <<EOF\ngit push origin HEAD:main\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "cat <<EOF\nnote\nEO\\\nF\ngit push origin HEAD:main\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "bash <(cat <<EOF\ngit push origin HEAD:main\nEOF\n)",
                    "[default-delivery: blocked]",
                ),
                (
                    "{ cat <<EOF\ngit push origin HEAD:main\nEOF\n} | bash",
                    "[default-delivery: blocked]",
                ),
                (
                    "cat <<EOF > x.sh\ngit push origin HEAD:main\nEOF\nbash x.sh",
                    "[default-delivery: blocked]",
                ),
                (
                    "cat <<EOF > x.sh\ngit push origin HEAD:main\nEOF\n"
                    "chmod +x x.sh; ./x.sh",
                    "[default-delivery: blocked]",
                ),
                (
                    "cat >> .git/hooks/post-checkout <<EOF\ngit push origin HEAD:main\nEOF",
                    "[default-delivery: blocked]",
                ),
                (
                    "tee x.sh <<EOF\ngit push origin HEAD:main\nEOF\nnohup ./x.sh",
                    "[default-delivery: blocked]",
                ),
                (
                    'cat <<EOF &>x.sh\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    'cat <<EOF >&x.sh\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    'cat <<EOF >& x.sh\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    'cat <<EOF 1<>x.sh\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    '{ cat <<EOF\ngit push origin HEAD:main\nEOF\n} > x.sh',
                    "[default-delivery: blocked]",
                ),
                (
                    '(cat <<EOF\ngit push origin HEAD:main\nEOF\n) > x.sh',
                    "[default-delivery: blocked]",
                ),
                (
                    './cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    'bin/python3 - <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    'alias cat=dash 2>/dev/null; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'export PATH=/tmp/evil:$PATH; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'true && hash -p /tmp/evil/cat cat; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'X=1 alias cat=dash; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'builtin hash -p /tmp/evil/cat cat; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'noglob hash -p /tmp/evil/cat cat; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'nocorrect alias cat=dash; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'time hash -p /tmp/evil/cat cat; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    '- alias cat=dash; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'X+=1 alias cat=dash; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'x[1]=2 hash -p /tmp/evil/cat cat; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'env PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'env -i PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'env -u FOO PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'env -C /tmp PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'env --unset FOO PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    '/usr/bin/env PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'nice env PATH=/tmp/evil cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'PATH=/tmp/evil:$PATH; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery:",
                ),
                (
                    'cat() { dash; }; cat <<EOF\ngit push origin HEAD:main\nEOF',
                    "[default-delivery: blocked]",
                ),
                (
                    'echo "$(( $(git push origin HEAD:main) + 1 ))"',
                    "[default-delivery: blocked]",
                ),
                (
                    "echo $${x;git push origin HEAD:main;true}",
                    "[default-delivery: blocked]",
                ),
                ("git send-pack origin HEAD:main", "[default-delivery:"),
                (
                    "D=/srv/missing; git -C $D send-pack origin HEAD:main",
                    "[default-delivery:",
                ),
                ("local PATH=/tmp/evil; printf --version", "rule=opaque-shell-resolution"),
                ("! PATH=/tmp/evil; printf --version", "rule=opaque-shell-resolution"),
                ("{ PATH=/tmp/evil; }; printf --version", "rule=opaque-shell-resolution"),
                (
                    "if true; then PATH=/tmp/evil; fi; printf --version",
                    "rule=opaque-shell-resolution",
                ),
                (
                    "while PATH=/tmp/evil; do break; done; printf --version",
                    "rule=opaque-shell-resolution",
                ),
                ("time PATH=/tmp/evil; printf --version", "rule=opaque-shell-resolution"),
                (
                    "nocorrect PATH=/tmp/evil; printf --version",
                    "rule=opaque-shell-resolution",
                ),
            )
            for command, fragment in still_classified:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_keeps_semantic_commit_flag_bypasses_closed(
        self,
    ) -> None:
        # The shapes sympoies/nils-cli#2016 and #2020 closed in the DSH port:
        # a dynamic word, an unknown option, or a redirection in a value slot
        # before `--help`, `--dry-run`, or `--validate-only` can swallow that
        # flag in semantic-commit's own parser, so the invocation still authors
        # a commit on the default branch.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subject = "--type feat --subject 'change behavior'"
            authoring = (
                f"semantic-commit commit {subject} $(printf %s --message-out) --help",
                "semantic-commit commit --type feat $(printf %s --subject) --help",
                f"semantic-commit commit {subject} $OUT --dry-run",
                "semantic-commit commit $F --help",
                'semantic-commit commit "$@" --help',
                "semantic-commit commit ${=F} --validate-only",
                "semantic-commit commit --message --help",
                "semantic-commit commit -m --help",
                "semantic-commit commit --message $M --help",
                f"semantic-commit commit --unknown-option --dry-run {subject}",
                f"semantic-commit commit {subject} --body-bullet >/dev/null --dry-run",
                f"semantic-commit commit {subject} --body-bullet 2>/dev/null --help",
                f"semantic-commit commit {subject} --trailer > /dev/null "
                "--validate-only",
                f"semantic-commit commit {subject} --trailer '<x' --trailer "
                "--validate-only",
                "semantic-commit commit --type feat --subject '>x' "
                "--body-bullet --help",
                f"semantic-commit commit {subject} --body-bullet '>x' "
                "--body-bullet --dry-run",
                f"semantic-commit commit {subject} --body-bullet \\>x "
                "--body-bullet --dry-run",
                f"semantic-commit commit {subject} --body-bullet '2>x' "
                "--body-bullet --dry-run",
                "semantic-commit commit -m 'feat: x' --message-out nofile(N) --dry-run",
                "semantic-commit commit --type feat --subject x --body-bullet "
                "nofile(N) --validate-only",
                # semantic-commit rejects a positional word before any work, but
                # the guard cannot prove that, so it stays authoring (as in the
                # DSH port).
                "semantic-commit squash HEAD~1 --dry-run",
                "semantic-commit fixup HEAD~1 --help",
            )
            for command in authoring:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "[default-delivery:")

            inspection = (
                "semantic-commit commit --help",
                "semantic-commit commit -h",
                "semantic-commit commit --help >/dev/null",
                "semantic-commit commit --help > /dev/null",
                "semantic-commit commit 2>/dev/null --dry-run",
                f"semantic-commit commit --dry-run {subject}",
                "semantic-commit commit --validate-only --message 'feat: x'",
                "semantic-commit commit --quiet --json --help",
                "semantic-commit fixup --help",
                "semantic-commit commit --dry-run --message 'feat(hooks): add x'",
                "semantic-commit squash --dry-run --target HEAD~1",
            )
            for command in inspection:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_names_the_word_it_could_not_classify(
        self,
    ) -> None:
        # An unverified refusal is only actionable when it names the word the
        # guard could not resolve and the rewrite that makes it classifiable.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            cases = (
                (
                    "bin=/srv/laoda/bin/laoda; $bin peek x",
                    ("rule=opaque-executable", "word=`$bin`", "literal"),
                ),
                (
                    'L="bin/laoda log"; $L "note"',
                    ("rule=opaque-executable", "word=`$L`"),
                ),
                (
                    "cat > notes.md <<EOF\n"
                    "lanes 1-4 are merged (org/repo#204, org/other#305).\nEOF",
                    ("rule=opaque-executable", "<<'EOF'"),
                ),
                (
                    'for c in "agent-memory doctor"; do eval "$c"; done',
                    ("rule=opaque-executable", "word=`$c`"),
                ),
                (
                    "LAODA_ROOT=$PWD bash -c "
                    "'source libexec/_resolve; resolve_session b1ab22df'",
                    (
                        "rule=opaque-shell-resolution",
                        "word=`resolve_session`",
                        "`source libexec/_resolve`",
                    ),
                ),
            )
            for command, fragments in cases:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    for fragment in fragments:
                        self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_names_an_exhausted_candidate_budget(
        self,
    ) -> None:
        # The opaque-candidate scan also stops at its word budget, not only at
        # its depth limit, so the refusal names a work limit.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            command = "$tool " + " ".join(["word"] * 5000)
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(command),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "operation=work-limit")
            self.assertNotIn("depth", str((decision or {}).get("reason", "")))


    def test_default_delivery_hook_names_a_missing_cached_origin_head(
        self,
    ) -> None:
        # Without `refs/remotes/origin/HEAD` the default branch is unknown. The
        # refusal must name that cause and its repair, not a generic "could
        # not be read" that sends the agent to `--repo`.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "symbolic-ref", "--delete", "refs/remotes/origin/HEAD"],
                cwd=repo,
                check=True,
            )
            for command in (
                "semantic-commit commit --message 'fix: x'",
                "git reset --hard HEAD",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "[default-delivery: unverified]")
                    self.assert_blocked(decision, "`refs/remotes/origin/HEAD`")
                    self.assert_blocked(
                        decision, f"`git -C {repo.resolve()} remote set-head origin --auto`"
                    )


    def test_default_delivery_hook_classifies_quoted_command_substitutions(
        self,
    ) -> None:
        # A double-quoted `$(...)` and a backtick substitution, quoted or not,
        # run exactly like an unquoted `$(...)`, including inside test words
        # and assignments (issue #182). Single-quoted text stays literal.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            blocked = (
                "echo $(git push origin main)",
                'echo "$(git push origin main)"',
                "echo `git push origin main`",
                'echo "`git push origin main`"',
                'x="$(git push origin main)"',
                '[ "$(git push origin main)" ]',
                "[[ -n `git push origin main` ]]",
                'test "`git push origin HEAD:main`"',
                'echo "a $(printf "%s" "$(git push origin main)") b"',
                'echo "$(printf ok)" "$(git push origin main)"',
                "bash -c 'echo \"`git push origin main`\"'",
                "echo a#`git push origin main`",
                'echo "$(echo ${x:-)} ; git push origin main)"',
                'echo "$((git push origin main) )"',
                'semantic-commit commit -m "$(git push origin main)"',
                "cat <<E\n## Fix `git push origin main`\nE",
                'echo ${x:-"}" #"$(git push origin main)"}',
                "cat <<E\nit's fine\nE\ngit push origin main",
                "cat <<E\n\"\nE\necho '$(x)'; git push origin main",
                "echo a\\\n#b; git push origin main",
                "echo a\\ #b; git push origin main",
            )
            for command in blocked:
                with self.subTest(blocked=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "[default-delivery: blocked]")

            allowed = (
                "echo '$(git push origin main)'",
                "echo '`git push origin main`'",
                'echo "\\$(git push origin main)"',
                'echo "$HOME"',
                "[ -f x ]",
                "readlink -f $(which a) $(which b)",
                'echo "$(git rev-parse HEAD)" `git status --short`',
                "cat <<'EOF'\n$(git push origin main)\n`git push origin main`\nEOF",
                "git status  # then `git push origin main` later",
                'ls  # "$(git push origin main)"',
                "cat <<E\nit's fine\nE\ngit status",
                "gh issue comment 1 --body-file - <<E\nit's done\nE",
                "git status  # don't worry, it's read-only",
            )
            for command in allowed:
                with self.subTest(allowed=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload('[ "$(printf git)" ] push origin main'),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # A `#` inside a `[[` regex is not a comment; the `$` the tokenizer
            # then sees in command position keeps the refusal unverified.
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    "while read -r line; do [[ $line =~ ^(#|$) ]] && continue; "
                    'echo "$line"; done < f; git push origin main'
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: ")

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload('echo "unterminated; git push origin main'),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")

            nested = "$(echo " * 40 + "true" + ")" * 40
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(f"echo {nested}"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")


    def test_default_delivery_hook_scopes_substitution_state_to_the_subshell(
        self,
    ) -> None:
        # A command substitution runs in a subshell: it cannot change the
        # parent's aliases, functions, hashes, PATH, or cwd, so its body must
        # not taint the command it expands. State changes still apply within
        # the same substitution body.
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(primary, "feat/subst")
            allowed = (
                "semantic-commit commit --message \"$(cat <<'EOF'\n"
                "fix: x\n\n- Explain the fix\nEOF\n)\"",
                'semantic-commit commit -m "$(date)"',
                "semantic-commit commit -m $(date)",
                "semantic-commit commit -m `date`",
                'semantic-commit commit --message "$(printf body)"',
            )
            for command in allowed:
                with self.subTest(allowed=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command, fragment in (
                (
                    'echo "$(alias g=git; g push origin main)"',
                    "rule=opaque-shell-resolution",
                ),
                (
                    'semantic-commit commit -m "$(printf ok; semantic-commit '
                    "commit -m 'fix: x')\"",
                    "changed executable resolution",
                ),
                (
                    "printf ok; semantic-commit commit -m \"$(date)\"",
                    "changed executable resolution",
                ),
            ):
                with self.subTest(blocked=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_classifies_each_identical_substitution(
        self,
    ) -> None:
        # Two textually identical substitutions are distinct executions under
        # different inherited shell state, so the second must be classified
        # after a `cd`, alias, or PATH change instead of being deduplicated.
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(primary, "feat/twice")
            target = shlex.quote(str(primary))
            for command in (
                'echo "$(git push origin HEAD)"',
                'echo "$(semantic-commit commit -m x)"',
            ):
                with self.subTest(allowed=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
            for command, fragment in (
                (
                    f'echo "$(git push origin HEAD)"; cd {target} && '
                    'echo "$(git push origin HEAD)"',
                    "[default-delivery: ",
                ),
                (
                    f'echo "$(semantic-commit commit -m x)"; cd {target} && '
                    'echo "$(semantic-commit commit -m x)"',
                    "[default-delivery: ",
                ),
                (
                    'echo "$(git push origin HEAD)"; alias git=true; '
                    'echo "$(git push origin HEAD)"',
                    "rule=opaque-shell-resolution",
                ),
                (
                    'echo "$(git push origin HEAD)"; export PATH=/tmp:$PATH; '
                    'echo "$(git push origin HEAD)"',
                    "rule=opaque-shell-resolution",
                ),
                (
                    f"bash -c 'git push origin HEAD'; cd {target} && "
                    "bash -c 'git push origin HEAD'",
                    "[default-delivery: ",
                ),
            ):
                with self.subTest(blocked=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_treats_zsh_disable_as_resolution_change(
        self,
    ) -> None:
        # zsh `disable` removes a builtin, reserved word, alias, or function
        # from lookup, so a later bare word of the same name can resolve to a
        # PATH executable; listing forms without names stay query-only.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            for mutation in (
                "disable printf",
                "disable -r [[",
                "disable -f runner",
                "disable -m 'p*'",
            ):
                with self.subTest(mutation=mutation):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(f"{mutation}; printf --version"),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "rule=opaque-shell-resolution")
            for query in ("disable", "disable -f", "disable -ra"):
                with self.subTest(query=query):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(f"{query}; printf --version"),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_admits_non_committing_semantic_commit_after_commands(
        self,
    ) -> None:
        # Help, dry-run, and validate-only forms author nothing, so an earlier
        # command in the same call cannot turn them into default-branch
        # delivery. An authoring form still fails closed, but as unverified:
        # the executable identity could not be proven, which is not a proven
        # default-branch write (issue #21).
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            allowed = (
                "cat README.md; semantic-commit commit --help",
                "git status --short && semantic-commit commit --help | head -5",
                "printf ok; semantic-commit commit --dry-run --message 'fix: x'",
                "printf ok; semantic-commit commit --validate-only "
                "--message 'fix: x'",
                "printf ok; semantic-commit default-branch --help",
            )
            for command in allowed:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            waiver = (
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                "'the primary checkout target is authorized'"
            )
            unverified = (
                "printf ok; semantic-commit commit --message 'fix: x'",
                "git add -- README.md && semantic-commit commit --repo "
                f"{shlex.quote(str(repo))} --message 'fix: x'",
                f"printf ok; {waiver} semantic-commit commit --message 'fix: x'",
                "cat README.md; semantic-commit fixup --target HEAD",
            )
            for command in unverified:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "[default-delivery: unverified]")
                    self.assert_blocked(decision, "rule=executable-resolution")
                    self.assert_blocked(decision, "changed executable resolution")
                    reason = str((decision or {}).get("reason", ""))
                    self.assertNotIn("[default-delivery: blocked]", reason)


    def test_default_delivery_hook_uses_custom_exec_transcript_workdir(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(
                primary, "feat/tiny-repair"
            )
            command = (
                "semantic-commit commit --type fix --scope hooks "
                "--subject 'classify the real worktree' --expect-head "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --format json"
            )
            transcript = root / "transcript.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "payload": {
                            "type": "custom_tool_call",
                            "name": "exec",
                            "call_id": "semantic-call",
                            "input": (
                                '// @exec: {"yield_time_ms": 30000}\n'
                                "const r = await tools.exec_command("
                                + json.dumps(
                                    {
                                        "cmd": command,
                                        "workdir": str(repo),
                                        "yield_time_ms": 30000,
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
            payload = command_payload(command)
            payload.update(
                {
                    "tool_use_id": "semantic-call",
                    "transcript_path": str(transcript),
                    "cwd": str(primary),
                }
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                payload,
                cwd=primary,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # A JavaScript object outside the JSON-compatible literal subset
            # (here, single-quoted strings) is deliberately not interpreted as
            # host attestation. It must report the failed classifier instead of
            # claiming the fallback primary checkout is the command target.
            transcript.write_text(
                json.dumps(
                    {
                        "payload": {
                            "type": "custom_tool_call",
                            "name": "exec",
                            "call_id": "semantic-call",
                            "input": (
                                "const r = await tools.exec_command({"
                                f"cmd: 'semantic-commit commit', workdir: '{repo}'"
                                "});\ntext(r.output);\n"
                            ),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                payload,
                cwd=primary,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")
            self.assert_blocked(
                decision, "rule=governed-authoring-target"
            )
            self.assert_blocked(decision, "operation=semantic-commit commit")
            self.assert_blocked(decision, "context=session-cwd")
            self.assert_blocked(
                decision, "diagnostic=workdir-attestation-missing"
            )
            self.assert_blocked(decision, "--repo <absolute path>")
            reason = str((decision or {}).get("reason", ""))
            self.assertLess(
                reason.index("Classification:"),
                reason.index("Do not author or push"),
            )

            explicit = command + f" --repo {shlex.quote(str(repo))}"
            explicit_payload = command_payload(explicit)
            explicit_payload.update(
                {
                    "tool_use_id": "semantic-call",
                    "transcript_path": str(transcript),
                    "cwd": str(primary),
                }
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                explicit_payload,
                cwd=primary,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_hook_classifies_code_mode_calls_by_their_workdir(
        self,
    ) -> None:
        # A Codex code-mode session is rooted at the primary checkout while
        # each nested exec call names its own workdir. The managed-session
        # record authenticates only the session root, so it must not stand in
        # for a call whose own workdir the transcript could not decode.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            worktree = self._add_checkout_lease_worktree(
                primary, "feat/code-mode"
            )
            state = root / "agent-session-state"
            session_dir = state / "sessions" / "managed-codex"
            session_dir.mkdir(parents=True)
            record = session_dir / "session.json"
            record.write_text(
                json.dumps(
                    {
                        "id": "managed-codex",
                        "agent": "codex",
                        "cwd": str(primary),
                        "runtime": {"launch_id": "managed-launch"},
                        "startup": {"state": "ready"},
                    }
                ),
                encoding="utf-8",
            )
            record.chmod(0o600)
            env = {
                "AGENT_SESSION_ID": "managed-codex",
                "AGENT_SESSION_STATE_DIR": str(state),
                "AGENT_SESSION_RUNTIME_ID": "managed-launch",
                "AGENT_RUNTIME_PRODUCT": "codex",
            }
            command = (
                "semantic-commit commit --type fix --scope hooks "
                "--subject 'classify the call workdir' --format json"
            )
            transcript = root / "transcript.jsonl"

            def run(
                source: str,
                call_id: str = "code-mode-call",
                command: str = command,
            ):
                transcript.write_text(
                    json.dumps(
                        {
                            "payload": {
                                "type": "custom_tool_call",
                                "name": "exec",
                                "call_id": "code-mode-call",
                                "input": source,
                            }
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                payload = command_payload(command)
                payload.update(
                    {
                        "tool_use_id": call_id,
                        "transcript_path": str(transcript),
                        "cwd": str(primary),
                    }
                )
                return run_hook(
                    "block-unsafe-default-delivery.py",
                    payload,
                    cwd=primary,
                    env=env,
                )

            literal = (
                f"const w={json.dumps(str(worktree))};"
                f"const r=await tools.exec_command({{cmd:{json.dumps(command)},"
                "workdir:w,yield_time_ms:30000});text(r);\n"
            )
            code, decision, stderr = run(literal)
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            parallel = (
                "const r = await Promise.allSettled([tools.exec_command("
                f"{{cmd: {json.dumps(command)}, workdir: "
                f"{json.dumps(str(worktree))}}}), tools.exec_command("
                '{cmd: "git status"})]);\ntext(JSON.stringify(r));\n'
            )
            code, decision, stderr = run(parallel)
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")
            self.assert_blocked(decision, "rule=governed-authoring-target")
            self.assert_blocked(decision, "--repo <absolute path>")
            reason = str((decision or {}).get("reason", ""))
            self.assertNotIn("[default-delivery: blocked]", reason)

            # A call the transcript has not recorded yet (Claude flushes after
            # the hook) keeps the authenticated managed-session fallback.
            code, decision, stderr = run(parallel, call_id="not-yet-flushed")
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: blocked]")
            self.assert_blocked(decision, "context=managed-session-cwd")

            # The same provenance decides raw Git: a feature-worktree merge is
            # not a default-branch merge because the session root is on `main`.
            merge = "git merge --no-commit --no-ff origin/main"
            merge_literal = literal.replace(
                json.dumps(command), json.dumps(merge)
            )
            code, decision, stderr = run(merge_literal, command=merge)
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            merge_parallel = parallel.replace(
                json.dumps(command), json.dumps(merge)
            )
            code, decision, stderr = run(merge_parallel, command=merge)
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")
            self.assert_blocked(decision, "rule=governed-authoring-target")
            reason = str((decision or {}).get("reason", ""))
            self.assertNotIn("[default-delivery: blocked]", reason)


    def test_default_delivery_hook_rejects_unattested_raw_git_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            feature = self._add_checkout_lease_worktree(
                primary, "feat/unattested-git"
            )
            transcript = root / "transcript.jsonl"
            transcript.write_text("", encoding="utf-8")
            commands = (
                "git merge main",
                "git pull origin main",
                "git reset --hard HEAD",
                "git cherry-pick HEAD",
                "git update-ref refs/heads/main HEAD",
                "git push origin HEAD",
            )
            for command in commands:
                with self.subTest(command=command):
                    payload = command_payload(command)
                    payload.update(
                        {
                            "tool_use_id": "missing-call",
                            "transcript_path": str(transcript),
                            "cwd": str(feature),
                        }
                    )
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        payload,
                        cwd=feature,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(
                        decision, "[default-delivery: unverified]"
                    )
                    self.assert_blocked(
                        decision, "rule=governed-authoring-target"
                    )
                    self.assert_blocked(
                        decision, "diagnostic=workdir-attestation-missing"
                    )

            explicit = f"git -C {shlex.quote(str(feature))} merge main"
            payload = command_payload(explicit)
            payload.update(
                {
                    "tool_use_id": "missing-call",
                    "transcript_path": str(transcript),
                    "cwd": str(primary),
                }
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                payload,
                cwd=primary,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_hook_allows_validate_only_on_default_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "semantic-commit commit --validate-only "
                "--message 'fix: inspect only'",
                "semantic-commit commit --dry-run --subject 'fix: inspect only' "
                f"--message-out {shlex.quote(str(repo / 'recovery.md'))}",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_rejects_removed_local_default_shape_when_ahead(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            receipts = root / "agent-out"
            receipts.mkdir()
            self._init_checkout_lease_repo(repo)
            (repo / "README.md").write_text(
                "# lease fixture\n\nlocal-only commit\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "fixture: local ahead"],
                cwd=repo,
                check=True,
            )
            cached_gap = subprocess.run(
                ["git", "rev-list", "--count", "origin/main..HEAD"],
                cwd=repo,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            self.assertEqual(cached_gap, "1", "fixture must be ahead-only")
            subprocess.run(
                ["git", "branch", "--set-upstream-to", "origin/main", "main"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "README.md").write_text(
                "# lease fixture\n\nlocal-only commit\n\nnext change\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            governed = (
                "semantic-commit local-default --message 'fix: tiny repair' "
                f"--expect-head {head} --expected-branch main "
                "--remote-mode local-only "
                f"--receipt-out {shlex.quote(str(receipts / 'receipt.json'))} "
                "--automation --format json"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(governed),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "semantic-commit default-branch")

            replacement = (
                "semantic-commit default-branch --message 'fix: tiny repair' "
                f"--expect-head {head} --repo {shlex.quote(str(repo.resolve()))} "
                f"--receipt-out {shlex.quote(str(receipts / 'replacement.json'))} "
                "--automation --format json"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(replacement),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "not aligned")

            invalid = (
                "semantic-commit local-default --message 'fix: tiny repair' "
                f"--expect-head {head} --expected-branch main "
                f"--receipt-out {shlex.quote(str(repo / 'receipt.json'))}"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(invalid),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "semantic-commit default-branch")


    def test_default_delivery_hook_admits_only_exact_default_branch_shape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            receipts = root / "agent-out"
            receipts.mkdir()
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "branch", "--set-upstream-to", "origin/main", "main"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "README.md").write_text(
                "# lease fixture\n\ndefault-branch change\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            exact = (
                "semantic-commit default-branch --message 'fix: tiny repair' "
                f"--expect-head {head} --repo {shlex.quote(str(repo.resolve()))} "
                f"--receipt-out {shlex.quote(str(receipts / 'receipt.json'))} "
                "--automation --format json"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(exact),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            shadow_dir = root / "shadow-bin"
            shadow_dir.mkdir()
            shadow = shadow_dir / "semantic-commit"
            shadow.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            shadow.chmod(0o755)
            for command, env in (
                (exact.replace("semantic-commit", str(shadow), 1), None),
                (
                    exact,
                    {
                        "PATH": (
                            f"{shadow_dir}{os.pathsep}"
                            f"{os.environ.get('PATH', '')}"
                        )
                    },
                ),
            ):
                with self.subTest(untrusted_semantic_commit=command, env=env):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "untrusted `semantic-commit`")

            waiver = "maintainer authorized an otherwise unresolved repository"
            for command in (
                f"PATH={shlex.quote(str(shadow_dir))} {exact}",
                f"env PATH={shlex.quote(str(shadow_dir))} {exact}",
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} "
                f"PATH={shlex.quote(str(shadow_dir))} {exact}",
            ):
                with self.subTest(command_local_path=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "command-local `PATH`")

            hidden = (
                f"env PATH={shlex.quote(str(shadow_dir))} {exact}"
            )
            wrapped = (
                f"nice {hidden}",
                f"timeout 5 {hidden}",
                f"nohup {hidden}",
                f"stdbuf -oL {hidden}",
                f"sudo -n {exact}",
                f"xargs -n1 {exact}",
                f"builtin exec {exact}",
                f"builtin command {exact}",
                f"set -A path {shlex.quote(str(shadow_dir))}; "
                f"builtin exec {exact}",
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} nice {hidden}",
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} builtin command {exact}",
            )
            for command in wrapped:
                with self.subTest(process_wrapper=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "behind a process wrapper")

            retarget_file = root / "retarget.sh"
            retarget_file.write_text(
                f"PATH={shadow_dir}\n", encoding="utf-8"
            )
            persistent_retargeting = (
                f"export PATH={shlex.quote(str(shadow_dir))} && {exact}",
                f"PATH={shlex.quote(str(shadow_dir))}; {exact}",
                f"unset PATH && {exact}",
                f"hash -p {shlex.quote(str(shadow))} semantic-commit && {exact}",
                f"alias semantic-commit={shlex.quote(str(shadow))} && {exact}",
                f"source {shlex.quote(str(retarget_file))} && {exact}",
                f"path={shlex.quote(str(shadow_dir))}; {exact}",
                f"export path={shlex.quote(str(shadow_dir))} && {exact}",
                f"typeset path={shlex.quote(str(shadow_dir))} && {exact}",
                f"path[1]={shlex.quote(str(shadow_dir))}; {exact}",
                "commands[semantic-commit]="
                f"{shlex.quote(str(shadow))}; {exact}",
                f"set -A path {shlex.quote(str(shadow_dir))}; {exact}",
                f"true && {exact}",
                f"export PATH={shlex.quote(str(shadow_dir))} && "
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} {exact}",
                f"path={shlex.quote(str(shadow_dir))}; "
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} {exact}",
                f"path[1]={shlex.quote(str(shadow_dir))}; "
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} {exact}",
                "commands[semantic-commit]="
                f"{shlex.quote(str(shadow))}; "
                "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} {exact}",
                f"true && AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                f"{shlex.quote(waiver)} {exact}",
            )
            for command in persistent_retargeting:
                with self.subTest(persistent_retargeting=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(
                        decision,
                        (
                            "untrusted `semantic-commit`"
                            if command.startswith("commands[")
                            else (
                                "changed executable resolution"
                                if command.startswith(("set -A ", "true "))
                                else "rule=opaque-shell-resolution"
                            )
                        ),
                    )

            trusted_semantic_commit = shutil.which("semantic-commit")
            self.assertIsNotNone(trusted_semantic_commit)
            absolute = exact.replace(
                "semantic-commit", str(trusted_semantic_commit), 1
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    f"export PATH={shlex.quote(str(shadow_dir))} && {absolute}"
                ),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "changed executable resolution")

            dynamic = (
                exact.replace("semantic-commit", "$sc", 1),
                exact.replace("semantic-commit", '"$sc"', 1),
            )
            for tail in dynamic:
                commands = (
                    f"sc=semantic-commit; "
                    f"export PATH={shlex.quote(str(shadow_dir))}; {tail}",
                    f"sc=semantic-commit; "
                    f"AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                    f"{shlex.quote(waiver)} {tail}",
                    tail,
                )
                for command in commands:
                    with self.subTest(dynamic_command=command):
                        code, decision, stderr = run_hook(
                            "block-unsafe-default-delivery.py",
                            command_payload(command),
                            cwd=repo,
                            env={"sc": "semantic-commit"},
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(
                            decision, "could not be resolved safely"
                        )

            fully_dynamic = (
                exact.replace("semantic-commit", "$sc", 1).replace(
                    "default-branch", "$mode", 1
                ),
                exact.replace("semantic-commit", '"$sc"', 1).replace(
                    "default-branch", '"$mode"', 1
                ),
            )
            for tail in fully_dynamic:
                for command in (
                    f"sc=semantic-commit; mode=default-branch; {tail}",
                    "sc=semantic-commit; mode=default-branch; "
                    "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                    f"{shlex.quote(waiver)} {tail}",
                    tail,
                ):
                    with self.subTest(fully_dynamic=command):
                        code, decision, stderr = run_hook(
                            "block-unsafe-default-delivery.py",
                            command_payload(command),
                            cwd=repo,
                            env={
                                "sc": "semantic-commit",
                                "mode": "default-branch",
                            },
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(
                            decision, "could not be resolved safely"
                        )

            preview = exact.replace(
                f"--receipt-out {receipts / 'receipt.json'} ",
                "--dry-run ",
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(preview),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            deprecated = exact.replace("default-branch", "local-default", 1)
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(deprecated),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "forge-cli repo push-default")

            malformed = (
                exact.replace(f"--expect-head {head} ", ""),
                exact.replace(f"--receipt-out {receipts / 'receipt.json'} ", ""),
                exact.replace("--automation", "--dry-run --automation"),
                exact.replace(str(repo.resolve()), "repo", 1),
                exact.replace(
                    f"--expect-head {head}",
                    f"--expect-head {head} --expect-head {head}",
                ),
                exact.replace("--automation", "--remote-mode local-only --automation"),
                exact.replace("--automation", "--type fix --automation"),
                exact.replace("--automation", "--scope hooks --automation"),
                exact.replace(
                    "--automation", "--subject 'tiny repair' --automation"
                ),
                exact.replace(
                    "--automation", "--body-bullet 'why' --automation"
                ),
            )
            for command in malformed:
                with self.subTest(malformed=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "semantic-commit default-branch")


    def test_default_delivery_hook_owns_default_branch_state_invariants(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipts = root / "agent-out"
            receipts.mkdir()

            def command(repo: Path, receipt: Path) -> str:
                head = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo,
                    check=True,
                    text=True,
                    capture_output=True,
                ).stdout.strip()
                return (
                    "semantic-commit default-branch "
                    "--message 'fix: tiny repair' "
                    f"--expect-head {head} "
                    f"--repo {shlex.quote(str(repo.resolve()))} "
                    f"--receipt-out {shlex.quote(str(receipt))} "
                    "--automation --format json"
                )

            def prepare(name: str, *, remote: bool = True) -> Path:
                repo = root / name
                self._init_checkout_lease_repo(repo)
                if remote:
                    subprocess.run(
                        [
                            "git",
                            "branch",
                            "--set-upstream-to",
                            "origin/main",
                            "main",
                        ],
                        cwd=repo,
                        check=True,
                        capture_output=True,
                    )
                else:
                    subprocess.run(
                        ["git", "remote", "remove", "origin"],
                        cwd=repo,
                        check=True,
                    )
                (repo / "README.md").write_text(
                    "# lease fixture\n\ndefault-branch change\n",
                    encoding="utf-8",
                )
                subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
                return repo

            remote_free = prepare("remote-free", remote=False)
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    command(remote_free, receipts / "remote-free.json")
                ),
                cwd=remote_free,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            cases: list[tuple[Path, Path, str]] = []

            no_staged = root / "no-staged"
            self._init_checkout_lease_repo(no_staged)
            subprocess.run(
                [
                    "git",
                    "branch",
                    "--set-upstream-to",
                    "origin/main",
                    "main",
                ],
                cwd=no_staged,
                check=True,
                capture_output=True,
            )
            cases.append(
                (no_staged, receipts / "no-staged.json", "no staged changes")
            )

            untracked = prepare("untracked")
            (untracked / "untracked.txt").write_text(
                "untracked\n", encoding="utf-8"
            )
            cases.append(
                (
                    untracked,
                    receipts / "untracked.json",
                    "unstaged or untracked",
                )
            )

            existing_receipt_repo = prepare("existing-receipt")
            existing_receipt = receipts / "existing.json"
            existing_receipt.write_text("{}\n", encoding="utf-8")
            cases.append(
                (
                    existing_receipt_repo,
                    existing_receipt,
                    "does not name a new file",
                )
            )

            symlink_receipt_repo = prepare("symlink-receipt")
            real_receipt_dir = root / "real-receipts"
            real_receipt_dir.mkdir()
            symlink_receipt_dir = root / "receipt-link"
            symlink_receipt_dir.symlink_to(real_receipt_dir, target_is_directory=True)
            cases.append(
                (
                    symlink_receipt_repo,
                    symlink_receipt_dir / "receipt.json",
                    "parent is a symlink",
                )
            )

            operation = prepare("operation")
            operation_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=operation,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            (operation / ".git" / "MERGE_HEAD").write_text(
                f"{operation_head}\n", encoding="utf-8"
            )
            cases.append(
                (
                    operation,
                    receipts / "operation.json",
                    "Git operation in progress",
                )
            )

            wrong_default = prepare("wrong-default")
            subprocess.run(
                [
                    "git",
                    "symbolic-ref",
                    "refs/remotes/origin/HEAD",
                    "refs/remotes/origin/not-main",
                ],
                cwd=wrong_default,
                check=True,
            )
            cases.append(
                (
                    wrong_default,
                    receipts / "wrong-default.json",
                    "authoritative cached default branch",
                )
            )

            ahead = prepare("ahead")
            subprocess.run(
                ["git", "commit", "-q", "-m", "ahead fixture"],
                cwd=ahead,
                check=True,
            )
            (ahead / "README.md").write_text(
                "# lease fixture\n\nahead change\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "README.md"], cwd=ahead, check=True)
            cases.append(
                (
                    ahead,
                    receipts / "ahead.json",
                    "not aligned with the cached default-branch upstream",
                )
            )

            stale_remote_free = prepare("stale-remote-free", remote=False)
            subprocess.run(
                ["git", "config", "branch.main.remote", "origin"],
                cwd=stale_remote_free,
                check=True,
            )
            subprocess.run(
                ["git", "config", "branch.main.merge", "refs/heads/main"],
                cwd=stale_remote_free,
                check=True,
            )
            cases.append(
                (
                    stale_remote_free,
                    receipts / "stale-remote-free.json",
                    "stale upstream metadata",
                )
            )

            detached = prepare("detached")
            subprocess.run(
                ["git", "checkout", "--detach", "-q"],
                cwd=detached,
                check=True,
            )
            cases.append(
                (
                    detached,
                    receipts / "detached.json",
                    "no attached branch",
                )
            )

            unknown_remote = prepare("unknown-remote")
            subprocess.run(
                ["git", "config", "branch.main.remote", "ghost"],
                cwd=unknown_remote,
                check=True,
            )
            cases.append(
                (
                    unknown_remote,
                    receipts / "unknown-remote.json",
                    "configured upstream remote is not authoritative",
                )
            )

            mismatched_merge = prepare("mismatched-merge")
            subprocess.run(
                [
                    "git",
                    "config",
                    "branch.main.merge",
                    "refs/heads/not-main",
                ],
                cwd=mismatched_merge,
                check=True,
            )
            cases.append(
                (
                    mismatched_merge,
                    receipts / "mismatched-merge.json",
                    "upstream branch does not match",
                )
            )

            missing_upstream = prepare("missing-upstream")
            subprocess.run(
                ["git", "update-ref", "-d", "refs/remotes/origin/main"],
                cwd=missing_upstream,
                check=True,
            )
            cases.append(
                (
                    missing_upstream,
                    receipts / "missing-upstream.json",
                    "cached ref is not authoritative",
                )
            )

            primary = prepare("linked-primary")
            linked = self._add_checkout_lease_worktree(
                primary, "feature/linked-default"
            )
            (linked / "README.md").write_text(
                "# lease fixture\n\nlinked change\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "README.md"], cwd=linked, check=True)
            cases.append(
                (
                    linked,
                    receipts / "linked.json",
                    "linked worktree, not the primary checkout",
                )
            )

            for repo, receipt, reason in cases:
                with self.subTest(repo=repo.name, reason=reason):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command(repo, receipt)),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, reason)


    def test_default_delivery_hook_fails_closed_after_literal_cd_for_bare_commit(
        self,
    ) -> None:
        # Any preceding shell command can retarget a later bare executable
        # through shell-specific state. Even a literal absolute `cd` therefore
        # fails closed; callers must use a separate command tool call with the
        # target checkout as its top-level workdir.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            receipts = root / "agent-out"
            receipts.mkdir()
            self._init_checkout_lease_repo(primary)
            feature = self._add_checkout_lease_worktree(primary, "feat/elsewhere")
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=primary,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            authored = (
                f"cd {shlex.quote(str(primary))} && semantic-commit commit "
                "--message 'fix: tiny repair'"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(authored),
                cwd=feature,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "changed executable resolution")

            local_default_tail = (
                "semantic-commit local-default --message 'fix: tiny repair' "
                f"--expect-head {head} --expected-branch main "
                "--remote-mode local-only "
                f"--receipt-out {shlex.quote(str(receipts / 'receipt.json'))} "
                "--automation --format json"
            )
            governed = f"cd {shlex.quote(str(primary))} && {local_default_tail}"
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(governed),
                cwd=feature,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "changed executable resolution")

            # Dynamic, relative, and normalized destinations all remain
            # compound bare-command forms and therefore fail closed alike.
            for command in (
                f'cd "$TARGET" && {local_default_tail}',
                f"cd {shlex.quote(primary.name)} && {local_default_tail}",
                f"cd {shlex.quote(str(primary))}/.. && {local_default_tail}",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=root,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(
                        decision, "changed executable resolution"
                    )


    def test_default_delivery_hook_fails_closed_on_semantic_commit_retargeting(
        self,
    ) -> None:
        # Command-local Git context can move where `semantic-commit` actually
        # commits, so the guard must not classify it against the tool workdir.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            feature = self._add_checkout_lease_worktree(primary, "feat/elsewhere")
            alternate_home = root / "alternate-home"
            alternate_home.mkdir()
            for command in (
                f"HOME={shlex.quote(str(alternate_home))} semantic-commit commit "
                "--message 'fix: tiny repair'",
                f"GIT_DIR={shlex.quote(str(primary / '.git'))} semantic-commit "
                "commit --message 'fix: tiny repair'",
                f"env -C {shlex.quote(str(primary))} semantic-commit commit "
                "--message 'fix: tiny repair'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=feature,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be resolved safely")


    def test_default_delivery_hook_names_its_default_branch_discriminator(
        self,
    ) -> None:
        # An unresolvable verdict must name what it resolved and what failed, or
        # the caller cannot tell a wrong repository from a wrong expected head.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            other = root / "other"
            receipts = root / "agent-out"
            receipts.mkdir()
            self._init_checkout_lease_repo(primary)
            subprocess.run(
                ["git", "branch", "--set-upstream-to", "origin/main", "main"],
                cwd=primary,
                check=True,
                capture_output=True,
            )
            self._init_checkout_lease_repo(other)
            # Identical fixtures commit to the same object id in the same second,
            # which would make the foreign head match and the shape valid.
            (other / "OTHER.md").write_text("# other fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "OTHER.md"], cwd=other, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "fixture: other head"],
                cwd=other,
                check=True,
            )
            foreign_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=other,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            mistargeted = (
                "semantic-commit default-branch --message 'fix: tiny repair' "
                f"--expect-head {foreign_head} "
                f"--repo {shlex.quote(str(primary.resolve()))} "
                f"--receipt-out {shlex.quote(str(receipts / 'receipt.json'))} "
                "--automation --format json"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(mistargeted),
                cwd=primary,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "semantic-commit default-branch")
            reason = str((decision or {}).get("reason", ""))
            self.assertIn(str(primary.resolve()), reason)
            self.assertIn("tool workdir", reason)
            self.assertIn("--expect-head", reason)
            self.assertIn(foreign_head[:12], reason)
            self.assertIn("--repo", reason)


    def test_default_delivery_hook_refuses_waiver_for_known_identity_mismatch(
        self,
    ) -> None:
        # The waiver is read from the command's own assignment prefix, so it
        # cannot outlive one invocation, and it must carry a stated reason.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            receipts = root / "agent-out"
            receipts.mkdir()
            self._init_checkout_lease_repo(primary)
            foreign = "0" * 40
            tail = (
                "semantic-commit default-branch --message 'fix: tiny repair' "
                f"--expect-head {foreign} "
                f"--repo {shlex.quote(str(primary.resolve()))} "
                f"--receipt-out {shlex.quote(str(receipts / 'receipt.json'))} "
                "--automation --format json"
            )
            reason = "maintainer authorized this cross-repo local completion"
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(
                    f"AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER={shlex.quote(reason)} "
                    f"{tail}"
                ),
                cwd=primary,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "semantic-commit default-branch")

            # A separate assignment command, an ambient export, and a reason that
            # states nothing all keep the unresolvable verdict.
            for command in (
                f"export AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER={shlex.quote(reason)}"
                f" && {tail}",
                f"AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER=1 {tail}",
                f"AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER='' {tail}",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=primary,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(
                        decision,
                        (
                            "changed executable resolution"
                            if command.startswith("export ")
                            else "Do not author or push"
                        ),
                    )

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(tail),
                cwd=primary,
                env={"AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER": reason},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "Do not author or push")


    def test_default_delivery_waiver_length_matches_what_the_receipt_records(
        self,
    ) -> None:
        # Admission and recording must agree on what counts as a stated reason.
        # The receipt writer collapses whitespace runs before measuring, so a
        # reason that only clears the minimum through padding would otherwise be
        # admitted here and then dropped from the receipt, leaving no evidence.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            receipts = root / "agent-out"
            receipts.mkdir()
            self._init_checkout_lease_repo(primary)
            alternate_home = root / "alternate-home"
            alternate_home.mkdir()
            tail = (
                f"HOME={shlex.quote(str(alternate_home))} "
                "semantic-commit default-branch --message 'fix: tiny repair' "
                f"--expect-head {'0' * 40} "
                f"--repo {shlex.quote(str(primary.resolve()))} "
                f"--receipt-out {shlex.quote(str(receipts / 'receipt.json'))} "
                "--automation --format json"
            )
            padded = "aaa   bbb   ccc"
            self.assertGreaterEqual(len(padded), 12, "fixture must clear raw length")
            self.assertLess(
                len(" ".join(padded.split())), 12, "fixture must fail normalized"
            )
            for value, admitted in ((padded, False), ("authorized here", True)):
                with self.subTest(value=value):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(
                            "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER="
                            f"{shlex.quote(value)} {tail}"
                        ),
                        cwd=primary,
                    )
                    self.assertEqual(code, 0, stderr)
                    if admitted:
                        self.assert_allowed(decision)
                    else:
                        self.assert_blocked(decision, "could not be resolved safely")


    def test_default_delivery_hook_refuses_a_waiver_outside_the_ambiguous_class(
        self,
    ) -> None:
        # A waiver only admits an invocation the guard could not classify. A
        # proven default-branch target and every raw Git path stay blocked,
        # because no governed CLI re-verifies those downstream.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            reason = "maintainer authorized this cross-repo local completion"
            waiver = (
                f"AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER={shlex.quote(reason)} "
            )
            cases = (
                (
                    f"{waiver}semantic-commit commit --message 'fix: tiny repair'",
                    "forge-cli repo push-default",
                ),
                (f"{waiver}git push", "could not be resolved safely"),
                (
                    f"{waiver}git push --force origin HEAD:main",
                    "forge-cli repo push-default",
                ),
                (f"{waiver}git push --mirror origin", "forge-cli repo push-default"),
                (f"{waiver}git reset --hard HEAD~1", "forge-cli repo push-default"),
            )
            for command, fragment in cases:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=primary,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)


    def test_default_delivery_hook_blocks_raw_default_branch_rewrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "git merge feat/unsafe",
                "git cherry-pick HEAD",
                "git reset --hard HEAD^",
                "git update-ref refs/heads/main HEAD^",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "Do not author or push")


    def test_default_delivery_hook_preserves_recovery_and_governed_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "git merge --abort",
                "git merge --quit",
                "git merge --help",
                "git cherry-pick --abort",
                "git cherry-pick --quit",
                "git cherry-pick --help",
                "git reset -- README.md",
                "git-cli sync-default --format json",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_default_delivery_hook_does_not_treat_option_values_as_recovery(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "git merge -m --help feat/unsafe",
                "git merge -m --abort feat/unsafe",
                "git merge --continue",
                "git cherry-pick --continue",
                "git cherry-pick --skip",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "[default-delivery: blocked]")


    def test_default_delivery_hook_routes_raw_fast_forward_to_sync_owner(self) -> None:
        # Local state cannot prove publication: remote-tracking refs are
        # writable and pull accepts local repository paths. The governed owner
        # verifies the remote-bound fast-forward instead.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "git merge --ff-only origin/main",
                "git merge --ff-only --quiet refs/remotes/origin/main",
                "git pull --ff-only origin main",
                "git pull --ff-only",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "git-cli sync-default")


    def test_default_delivery_hook_blocks_a_pull_that_can_author_a_commit(
        self,
    ) -> None:
        # The superset was the hole: a bare `git pull` on the default branch can
        # author a merge commit, which is precisely what this guard exists to
        # prevent, and it passed unexamined while `git merge --ff-only` did not.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "git pull",
                "git pull origin main",
                "git pull --no-ff origin main",
                "git pull --rebase origin main",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "Do not author or push")


    def test_default_delivery_hook_blocks_fast_forward_onto_unpublished_work(
        self,
    ) -> None:
        # Neither a local branch nor a locally writable remote-tracking ref
        # proves publication. Pull also accepts a local repository source.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "branch", "feat/local-only"], cwd=repo, check=True
            )
            subprocess.run(
                ["git", "update-ref", "refs/remotes/origin/fake", "HEAD"],
                cwd=repo,
                check=True,
            )
            for command in (
                "git merge --ff-only feat/local-only",
                "git merge --ff-only HEAD",
                "git merge --ff-only origin/fake",
                "git pull --ff-only . feat/local-only",
                f"git pull --ff-only {repo} feat/local-only",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "Do not author or push")


    def test_default_delivery_hook_prefixes_every_refusal_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            commands = (
                "/tmp/semantic-commit commit --message 'fix: x'",
                "PATH=/tmp:$PATH semantic-commit commit --message 'fix: x'",
                "time semantic-commit commit --message 'fix: x'",
                "printf ok; semantic-commit commit --message 'fix: x'",
                "semantic-commit default-branch --message 'fix: x' --repo .",
            )
            for command in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNotNone(decision)
                    reason = str((decision or {}).get("reason", ""))
                    self.assertTrue(
                        reason.startswith(
                            (
                                "[default-delivery: blocked]",
                                "[default-delivery: unverified]",
                            )
                        ),
                        reason,
                    )
                    self.assertEqual(
                        reason.count("[default-delivery: blocked]")
                        + reason.count("[default-delivery: unverified]"),
                        1,
                        reason,
                    )

            marker_repo = Path(tmp) / "repo-[default-delivery: unverified]"
            self._init_checkout_lease_repo(marker_repo)
            command = (
                "semantic-commit default-branch --message 'fix: x' --repo "
                f"{shlex.quote(str(marker_repo))}"
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(command),
                cwd=marker_repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: blocked]")
            reason = str((decision or {}).get("reason", ""))
            self.assertIn(str(marker_repo), reason)
            self.assertEqual(reason.count("[default-delivery: blocked]"), 1)
            self.assertEqual(reason.count("[default-delivery: unverified]"), 1)


    def test_default_delivery_hook_marks_blocked_apart_from_unverified(
        self,
    ) -> None:
        # An agent can only act on a refusal if it can tell "this is forbidden"
        # from "restate this so it can be checked"; only the second is worth
        # retrying with a different command shape.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            self._init_checkout_lease_repo(repo)

            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("git push origin main"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: blocked]")
            proven = str((decision or {}).get("reason", ""))
            self.assertNotIn("[default-delivery: unverified]", proven)

            subprocess.run(
                ["git", "switch", "-q", "-c", "feat/tiny-repair"],
                cwd=repo,
                check=True,
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("git push"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")
            unverified = str((decision or {}).get("reason", ""))
            self.assertNotIn("[default-delivery: blocked]", unverified)


    def test_default_delivery_hook_names_the_shell_context_it_tripped(
        self,
    ) -> None:
        # The `cd` is the discriminator, not the push. Naming the policy instead
        # of the tripped condition sends an agent guessing at command shapes.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            # The primary checkout stays on the default branch so the cached
            # remote head remains trustworthy; the feature branch lives in a
            # linked worktree, which is where an agent authors anyway.
            repo = self._add_checkout_lease_worktree(primary, "feat/tiny-repair")
            quoted = shlex.quote(str(repo))
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(f"cd {quoted} && git push origin feat/tiny-repair"),
                cwd=root,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[default-delivery: unverified]")
            reason = str((decision or {}).get("reason", ""))
            self.assertIn("`cd`", reason)
            self.assertIn("git -C", reason)

            # The same push without the context change is classifiable, so it is
            # simply allowed. That difference is what the message has to convey.
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload(f"git -C {quoted} push origin feat/tiny-repair"),
                cwd=root,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_default_delivery_hook_offers_a_remedy_for_the_actual_operation(
        self,
    ) -> None:
        # Naming `forge-cli repo push-default` for a feature-branch push is a
        # non-substitute; it publishes the default branch, which is not what was
        # attempted.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "switch", "-q", "-c", "feat/tiny-repair"],
                cwd=repo,
                check=True,
            )
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("git push"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "git-cli push")

            subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
            code, decision, stderr = run_hook(
                "block-unsafe-default-delivery.py",
                command_payload("git merge origin/main"),
                cwd=repo,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "git-cli sync-default")


    def test_default_delivery_hook_scopes_path_override_to_governed_commands(
        self,
    ) -> None:
        # The rule exists to stop a governed CLI being retargeted. Applying it to
        # every executable blocks ordinary tooling with a message that claims a
        # governed executable was involved, while the strictly broader
        # `export PATH=...; <command>` passes.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            for command in (
                "PATH=/opt/toolchain/bin:$PATH cargo test",
                "PATH=/opt/toolchain/bin:$PATH bash scripts/ci/checks.sh",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command in (
                "PATH=/tmp/evil:$PATH git push origin main",
                "PATH=/tmp/evil:$PATH semantic-commit commit --message 'fix: x'",
            ):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "`PATH` override")


    def test_default_delivery_hook_blocks_ambiguous_feature_pushes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self._init_checkout_lease_repo(repo)
            subprocess.run(
                ["git", "switch", "-q", "-c", "feat/tiny-repair"],
                cwd=repo,
                check=True,
            )
            for command in ("git push", "git push origin", "git push --prune origin"):
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=repo,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "could not be resolved safely")


    def test_default_delivery_hook_honors_explicit_repository_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "repo"
            self._init_checkout_lease_repo(primary)
            repo = self._add_checkout_lease_worktree(
                primary, "feat/tiny-repair"
            )
            commands = (
                (f"git -C {shlex.quote(str(repo))} push origin HEAD:main", True),
                (
                    "semantic-commit commit --repo "
                    f"{shlex.quote(str(repo))} --message 'fix: tiny repair'",
                    False,
                ),
            )
            for command, blocked in commands:
                with self.subTest(command=command):
                    code, decision, stderr = run_hook(
                        "block-unsafe-default-delivery.py",
                        command_payload(command),
                        cwd=root,
                    )
                    self.assertEqual(code, 0, stderr)
                    if blocked:
                        self.assert_blocked(decision, "forge-cli repo push-default")
                    else:
                        self.assert_allowed(decision)

