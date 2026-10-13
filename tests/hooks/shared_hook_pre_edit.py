"""Shared hook tests: pre edit."""
from __future__ import annotations

from shared_hook_helpers import (
    HOOK_DIR,
    HookTestCase,
    Path,
    REPO_ROOT,
    command_payload,
    importlib,
    inventory_rules,
    inventory_tools,
    mock,
    os,
    re,
    run_hook,
    shlex,
    shutil,
    snapshot_repository_content,
    subprocess,
    tempfile,
    write_payload,
)


class PreEditTests(HookTestCase):

    def test_pre_edit_intent_gate_project_dev_modes_are_isolated(self) -> None:
        """Default advisory, invalid, off, and enforce have distinct contracts."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            git_bin = shutil.which("git")
            assert git_bin is not None
            (bin_dir / "git").symlink_to(git_bin)
            base_env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "HOME": str(root / "home"),
                "PATH": str(bin_dir),
            }
            (root / "home").mkdir()
            payload = write_payload(str(repo / "src" / "lib.rs"), "x\n")
            payload["session_id"] = "project-dev-mode"

            for mode in ("", "advisory"):
                with self.subTest(mode=mode or "default"):
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=repo,
                        env={**base_env, "AGENT_RUNTIME_PROJECT_DEV_MODE": mode},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNotNone(decision)
                    assert decision is not None
                    self.assertNotEqual(decision.get("decision"), "block")
                    self.assertIn(
                        "[reason: project-dev-advisory-unavailable]", str(decision)
                    )
                    self.assertIn("work remains allowed", str(decision).lower())

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "unexpected"},
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertNotEqual(decision.get("decision"), "block")
            self.assertIn("Invalid AGENT_RUNTIME_PROJECT_DEV_MODE", str(decision))
            self.assertIn("work remains allowed", str(decision).lower())

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "off"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "enforce"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "capability")

            # Project-dev off does not bypass a separately registered delivery
            # control: raw commits remain blocked by their own hook.
            code, decision, stderr = run_hook(
                "block-direct-git-commit.py",
                command_payload("git commit -m bypass"),
                cwd=repo,
                env={**base_env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "off"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "semantic-commit")


    def test_pre_edit_intent_gate_consumes_prepare_for_literal_target_repo(
        self,
    ) -> None:
        """A target-B prepare from workdir A is consumed for B, not rebuilt for A."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = root / "repo-a"
            repo_b = root / "repo-b"
            for repo in (repo_a, repo_b):
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            docs_home = root / "docs-home"
            docs_home.mkdir()
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> {shlex.quote(str(call_log))}
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session verify --help"* ]]; then echo '--phase'; exit 0; fi
if [[ "$*" == *"session prepare"* ]]; then
  project=''
  state=''
  previous=''
  for token in "$@"; do
    if [[ "$previous" == '--project-path' ]]; then project="$token"; fi
    if [[ "$previous" == '--state-home' ]]; then state="$token"; fi
    previous="$token"
  done
  mkdir -p "$state/fixture-prepared"
  touch "$state/fixture-prepared/${{project##*/}}.prepared"
  echo '{{"schema_version":"cli.agent-docs.session.prepare.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  project=''
  state=''
  previous=''
  for token in "$@"; do
    if [[ "$previous" == '--project-path' ]]; then project="$token"; fi
    if [[ "$previous" == '--state-home' ]]; then state="$token"; fi
    previous="$token"
  done
  if [[ -f "$state/fixture-prepared/${{project##*/}}.prepared" ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            state = root / "state"
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(docs_home),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_PROJECT_DEV_MODE": "enforce",
                "AGENT_RUNTIME_STATE_HOME": str(state),
                "HOME": str(root / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            (root / "home").mkdir()
            agent_docs = str((bin_dir / "agent-docs").resolve())
            prepare = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(docs_home.resolve()),
                    "--project-path",
                    str(repo_b.resolve()),
                    "session",
                    "prepare",
                    "--session-id",
                    "target-b-prepare",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state.resolve()),
                    "--intent",
                    "project-dev",
                    "--phase",
                    "edit",
                    "--format",
                    "json",
                ]
            )
            payload = command_payload(prepare, workdir=str(repo_a))
            payload["session_id"] = "target-b-prepare"
            before_a = snapshot_repository_content(repo_a)
            before_b = snapshot_repository_content(repo_b)
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo_a, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[reason: prepared]")
            self.assertIn("[action: retry-original]", str(decision))
            self.assertTrue(
                (state / "fixture-prepared" / "repo-b.prepared").exists()
            )
            self.assertFalse(
                (state / "fixture-prepared" / "repo-a.prepared").exists()
            )
            self.assertEqual(snapshot_repository_content(repo_a), before_a)
            self.assertEqual(snapshot_repository_content(repo_b), before_b)

            edit_b = write_payload(str(repo_b / "src" / "lib.rs"), "x\n")
            edit_b["session_id"] = "target-b-prepare"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", edit_b, cwd=repo_a, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            edit_a = write_payload(str(repo_a / "src" / "lib.rs"), "x\n")
            edit_a["session_id"] = "target-b-prepare"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", edit_a, cwd=repo_a, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev-required")


    def test_pre_edit_intent_gate_verifies_and_prepares_multi_target_edits(
        self,
    ) -> None:
        """A+B edits preserve repository/code pairs in either activation order."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = root / "repo-a"
            repo_b = root / "repo-b"
            for repo in (repo_a, repo_b):
                (repo / "src").mkdir(parents=True)
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
                (repo / "src" / "lib.rs").write_text("old\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> {shlex.quote(str(call_log))}
if [[ "$*" == *"session verify --help"* ]]; then echo '--phase'; exit 0; fi
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
project=''
state=''
previous=''
for token in "$@"; do
  if [[ "$previous" == '--project-path' ]]; then project="$token"; fi
  if [[ "$previous" == '--state-home' ]]; then state="$token"; fi
  previous="$token"
done
marker="$state/fixture-prepared/${{project##*/}}.prepared"
if [[ "$*" == *"session prepare"* ]]; then
  mkdir -p "$state/fixture-prepared"
  touch "$marker"
  echo '{{"schema_version":"cli.agent-docs.session.prepare.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f "$marker" ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(root),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_STATE_HOME": str(root / "state"),
                "AGENT_SESSION_STATE_DIR": str(root / "coordination-state"),
                "HOME": str(root / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            (root / "home").mkdir()
            fixture_markers = root / "state" / "fixture-prepared"
            before_contents = {
                repo: snapshot_repository_content(repo) for repo in (repo_a, repo_b)
            }
            payload = {
                "tool_name": "apply_patch",
                "tool_input": {
                    "patch": (
                        f"*** Update File: {repo_a / 'src' / 'lib.rs'}\n"
                        f"*** Update File: {repo_b / 'src' / 'lib.rs'}\n"
                    )
                },
                "session_id": "multi-target",
            }

            for active, missing in ((repo_a, repo_b), (repo_b, repo_a)):
                with self.subTest(active=active.name):
                    for repo in (repo_a, repo_b):
                        (fixture_markers / f"{repo.name}.prepared").unlink(
                            missing_ok=True
                        )
                    fixture_markers.mkdir(parents=True, exist_ok=True)
                    (fixture_markers / f"{active.name}.prepared").write_text(
                        "prepared\n", encoding="utf-8"
                    )
                    call_log.write_text("", encoding="utf-8")
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=repo_a,
                        env={**env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "enforce"},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev-required")
                    reason = str(decision)
                    self.assertIn(str(missing.resolve()), reason)
                    self.assertNotIn(
                        f"Target `{active.resolve()}` failed", reason
                    )
                    verify_lines = [
                        line
                        for line in call_log.read_text(encoding="utf-8").splitlines()
                        if "session verify" in line and "--help" not in line
                    ]
                    self.assertEqual(len(verify_lines), 2)
                    self.assertTrue(
                        all(
                            any(f"--project-path {repo.resolve()}" in line for line in verify_lines)
                            for repo in (repo_a, repo_b)
                        )
                    )

                    call_log.write_text("", encoding="utf-8")
                    code, advisory, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=repo_a,
                        env={**env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "advisory"},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNotNone(advisory)
                    assert advisory is not None
                    self.assertNotEqual(advisory.get("decision"), "block")
                    advisory_reason = str(advisory)
                    self.assertIn("[reason: prepared]", advisory_reason)
                    self.assertTrue(
                        (fixture_markers / f"{missing.name}.prepared").exists()
                    )
                    self.assertTrue(
                        (fixture_markers / f"{active.name}.prepared").exists()
                    )
                    expected_preflight = shlex.join(
                        [
                            str((bin_dir / "agent-docs").resolve()),
                            "--docs-home",
                            str(root.resolve()),
                            "--project-path",
                            str(missing.resolve()),
                            "preflight",
                            "--intent",
                            "project-dev",
                            "--phase",
                            "edit",
                        ]
                    )
                    self.assertIn(expected_preflight, advisory_reason)
                    self.assertEqual(
                        {
                            repo: snapshot_repository_content(repo)
                            for repo in (repo_a, repo_b)
                        },
                        before_contents,
                    )
                    prepare_lines = [
                        line
                        for line in call_log.read_text(encoding="utf-8").splitlines()
                        if "session prepare" in line
                    ]
                    self.assertEqual(len(prepare_lines), 1)
                    self.assertIn(
                        f"--project-path {missing.resolve()}", prepare_lines[0]
                    )

            self.assertFalse((root / "coordination-state").exists())


    def test_pre_edit_intent_gate_prepare_parser_rejects_adversarial_argv(
        self,
    ) -> None:
        """Target-first parsing rejects aliases, reordered flags, and wrappers."""
        spec = importlib.util.spec_from_file_location(
            "pre_edit_intent_gate_adversarial",
            HOOK_DIR / "pre-edit-intent-gate.py",
        )
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            alias = root / "repo-alias"
            alias.symlink_to(repo, target_is_directory=True)
            executable = root / "agent-docs"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            state = root / "state"
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(root),
                "AGENT_RUNTIME_STATE_HOME": str(state),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                valid = gate.activation_base_args(
                    repo_root=str(repo.resolve()),
                    executable=str(executable.resolve()),
                    current_session="adversarial",
                    product="codex",
                    subcommand="prepare",
                ) + [
                    "--intent",
                    "project-dev",
                    "--phase",
                    "edit",
                    "--format",
                    "json",
                ]
                self.assertEqual(
                    gate.literal_prepare_target(
                        valid, agent_docs_executable=str(executable.resolve())
                    ),
                    str(repo.resolve()),
                )
                parsed = gate.bootstrap_activation_intents(
                    shlex.join(valid),
                    current_session="adversarial",
                    product="codex",
                    repo_root=str(repo.resolve()),
                    agent_docs_executable=str(executable.resolve()),
                )
                self.assertIsNotNone(parsed)

                project_index = valid.index("--project-path") + 1
                literal_rejections = []
                relative = list(valid)
                relative[project_index] = "../repo"
                literal_rejections.append(relative)
                symlink_alias = list(valid)
                symlink_alias[project_index] = str(alias)
                literal_rejections.append(symlink_alias)
                duplicate_project = list(valid)
                duplicate_project[project_index + 1 : project_index + 1] = [
                    "--project-path",
                    str(repo.resolve()),
                ]
                literal_rejections.append(duplicate_project)
                equals_project = list(valid)
                equals_project[project_index - 1 : project_index + 1] = [
                    f"--project-path={repo.resolve()}"
                ]
                literal_rejections.append(equals_project)
                bare = list(valid)
                bare[0] = "agent-docs"
                literal_rejections.append(bare)
                for words in literal_rejections:
                    with self.subTest(literal_words=words):
                        self.assertIsNone(
                            gate.literal_prepare_target(
                                words,
                                agent_docs_executable=str(executable.resolve()),
                            )
                        )

                parser_rejections = []
                reordered = list(valid[:-4]) + [
                    "--format",
                    "json",
                    "--phase",
                    "edit",
                ]
                parser_rejections.append(reordered)
                duplicate_phase = list(valid[:-2]) + [
                    "--phase",
                    "delivery",
                    "--format",
                    "json",
                ]
                parser_rejections.append(duplicate_phase)
                duplicate_intent = list(valid[:-4]) + [
                    "--intent",
                    "project-dev",
                    "--phase",
                    "edit",
                    "--format",
                    "json",
                ]
                parser_rejections.append(duplicate_intent)
                unknown_phase = list(valid)
                unknown_phase[-3] = "unknown"
                parser_rejections.append(unknown_phase)
                extra_flag = list(valid) + ["--strict"]
                parser_rejections.append(extra_flag)
                for words in parser_rejections:
                    with self.subTest(parser_words=words):
                        self.assertIsNone(
                            gate.bootstrap_activation_intents(
                                shlex.join(words),
                                current_session="adversarial",
                                product="codex",
                                repo_root=str(repo.resolve()),
                                agent_docs_executable=str(executable.resolve()),
                            )
                        )

                for wrapped in (
                    "env " + shlex.join(valid),
                    "time " + shlex.join(valid),
                    "bash -c " + shlex.quote(shlex.join(valid)),
                    shlex.join(valid) + "; true",
                ):
                    with self.subTest(wrapped=wrapped):
                        self.assertIsNone(
                            gate.bootstrap_activation_intents(
                                wrapped,
                                current_session="adversarial",
                                product="codex",
                                repo_root=str(repo.resolve()),
                                agent_docs_executable=str(executable.resolve()),
                            )
                        )


    def test_pre_edit_intent_gate_requires_active_project_dev_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (repo / "DEV.md").write_text("# Dev\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"session --help"* ]]; then
  printf '%s\n' '  verify    verify active intents'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\n' '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "intent-gate-block"

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            # P0-3: recovery recommends the single atomic `session prepare`
            # primitive (activate + strict preflight in one), not the older
            # two-command activate + separate preflight sequence.
            self.assertIn("session prepare", str(decision))
            self.assertIn("--intent project-dev", str(decision))
            self.assertIn("[reason: project-dev-required]", str(decision))
            self.assertIn(str(repo), str(decision))


    def test_pre_edit_intent_gate_uses_agent_docs_home_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            docs_home = repo / "docs-home"
            docs_home.mkdir()
            expected_docs_home = docs_home.resolve()
            # Reach docs-home through a symlink so the assertion below actually
            # discriminates. Without it the configured spelling and its resolved
            # form coincide wherever $TMPDIR has no symlinked ancestor, which is
            # every Linux CI run, and a hook that forwards the raw value passes
            # for free (#66).
            docs_home_link = repo / "docs-home-link"
            docs_home_link.symlink_to(docs_home)
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            log_path = repo / "agent-docs.args"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
printf '%s\\n' "$args" >> {shlex.quote(str(log_path))}
if [[ "$args" != *"--docs-home {expected_docs_home}"* ]]; then
  echo "missing AGENT_DOCS_HOME fallback" >&2
  exit 64
fi
if [[ "$args" == *"session --help"* ]]; then
  printf '%s\\n' '  verify    verify active intents'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_DOCS_HOME": str(docs_home_link),
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "intent-gate-docs-home-fallback"

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            self.assertIn(
                f"--docs-home {expected_docs_home}",
                log_path.read_text(encoding="utf-8"),
            )


    def test_pre_edit_intent_gate_resolves_effective_workdir(self) -> None:
        """P0-4: a shell command's working repository is its effective workdir.

        A command submitted with a workdir spelling the old gate ignored
        (`current_working_directory`) must be gated against that repository, not
        the hook process cwd.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_cwd = root / "repo-cwd"
            repo_target = root / "repo-target"
            for repo in (repo_cwd, repo_target):
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo_target),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(root / "state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = command_payload(
                "printf x > out.txt", current_working_directory=str(repo_target)
            )
            payload["session_id"] = "effective-workdir"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo_cwd, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            reason = str(decision)
            # Gated against the effective workdir repository, not the process cwd.
            self.assertIn(str(repo_target.resolve()), reason)
            self.assertNotIn(str(repo_cwd.resolve()), reason)


    def test_pre_edit_intent_gate_allows_git_recovery_abort(self) -> None:
        # A stuck mid-operation checkout must recover in place: a sole
        # `git <op> --abort` is admitted even when project-dev is not verified,
        # while an operation-advancing command (`--continue`) still blocks.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (repo / "DEV.md").write_text("# Dev\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"session --help"* ]]; then
  printf '%s\n' '  verify    verify active intents'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\n' '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            recovery = self._checkout_lease_payload(
                "intent-gate-recovery",
                repo,
                tool_name="Bash",
                command="git rebase --abort",
            )
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", recovery, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            advancing = self._checkout_lease_payload(
                "intent-gate-recovery",
                repo,
                tool_name="Bash",
                command="git rebase --continue",
            )
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", advancing, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")


    def test_pre_edit_intent_gate_rejects_repo_local_agent_docs_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            marker = repo / "fake-agent-docs-executed"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
printf 'executed\n' > {shlex.quote(str(marker))}
if [[ "$*" == *"session --help"* ]]; then printf '%s\n' 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  printf '%s\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
exit 64
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": "",
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "repo-local-agent-docs"

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "trusted")
            self.assertFalse(marker.exists())


    def test_pre_edit_intent_gate_allows_verified_session(self) -> None:
        for product in ("codex", "claude"):
            with self.subTest(product=product), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
                bin_dir = root / "bin"
                bin_dir.mkdir()
                body = f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"{product}","active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
exit 64
"""
                self._write_fake_agent_docs(bin_dir, body)
                env = {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_PRODUCT": product,
                    "CLAUDE_KIT_STATE_HOME": str(repo / "state"),
                    "HOME": str(root / "home"),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                }
                (root / "home").mkdir()
                payload = write_payload("src/lib.rs", "fn main() {}\n")
                payload["session_id"] = "intent-gate-allow"

                code, decision, stderr = run_hook(
                    "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_pre_edit_intent_gate_pre_session_cli_is_never_admitted_unverified(
        self,
    ) -> None:
        """A CLI without the session surface fails verification, not open.

        The supported nils-cli floor ships ``session verify``; an older binary
        that reports a pre-session version must not bypass enforcement. Enforce
        blocks at verification; advisory still preserves the work.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then
  printf '%s\\n' 'agent-docs 1.21.16 (v1.21.16)'
  exit 0
fi
exit 64
""",
            )
            (root / "home").mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(root / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "pre-session-cli"

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "[reason: project-dev-required]")
            self.assertIn("Project-dev verification failed for target", str(decision))
            self.assertNotIn("intent-not-active-or-stale", str(decision))

            code, advisory, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={**env, "AGENT_RUNTIME_PROJECT_DEV_MODE": "advisory"},
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            assert advisory is not None
            self.assertNotEqual(advisory.get("decision"), "block")
            self.assertIn(
                "[reason: project-dev-advisory-unavailable]", str(advisory)
            )


    def test_pre_edit_intent_gate_blocks_repository_shell_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "lib.rs").write_text("x\n", encoding="utf-8")
            (repo / "scripts").mkdir()
            (repo / "scripts" / "generate.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then printf '%s\n' 'agent-docs 1.21.17 (v1.21.17)'; exit 0; fi
if [[ "$*" == *"session --help"* ]]; then printf '%s\n' 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  printf '%s\n' '{"ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "HOME": str(repo / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            (repo / "home").mkdir()
            commands = (
                "printf x > src/lib.rs",
                "sed -i.bak 's/x/y/' src/lib.rs",
                "ruff format src/lib.rs",
                "bash scripts/generate.sh",
            )
            for command in commands:
                with self.subTest(command=command):
                    payload = command_payload(command)
                    payload["session_id"] = "shell-mutation"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")


    def test_pre_edit_intent_gate_block_message_includes_copyable_recovery_commands(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "R&D (runtime)#1\nline"
            root.mkdir()
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            agent_run = bin_dir / "agent-run"
            agent_run.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            agent_run.chmod(0o755)
            active_marker = root / "active"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session activate"* ]]; then
  printf 'active\n' > {shlex.quote(str(active_marker))}
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f {shlex.quote(str(active_marker))} ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            agent_docs = str((bin_dir / "agent-docs").resolve())
            state_home = (repo / "state").resolve()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            activation = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "activate",
                    "--session-id",
                    "intent-recovery",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home),
                    "--intent",
                    "project-dev",
                ]
            )
            preflight = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "preflight",
                    "--intent",
                    "project-dev",
                ]
            )
            # P0-3: the block recommends one atomic `session prepare` command
            # (activate + strict preflight), not the old two-command activate +
            # separate preflight sequence.
            prepare_cmd = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "prepare",
                    "--session-id",
                    "intent-recovery",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home),
                    "--intent",
                    "project-dev",
                    "--format",
                    "json",
                ]
            )
            # Classifiable mutations (a direct edit, a simple-argv command)
            # recover through the phase-scoped `edit` preparation.
            prepare_edit_cmd = prepare_cmd.replace(
                " --format json", " --phase edit --format json"
            )
            # The fallback requires preparation for unverified reads and writes;
            # this assertion checks the mutation recovery command.
            payload = command_payload("printf x > out.txt")
            payload["session_id"] = "intent-recovery"

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )

            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            assert decision is not None
            reason = str(decision.get("reason", ""))
            self.assertIn(prepare_cmd, reason)
            self.assertIn("[reason: project-dev-required]", reason)

            unknown_payload = command_payload("python3 -c 'print(1)'")
            unknown_payload["session_id"] = "intent-recovery"
            code, unknown_decision, stderr = run_hook(
                "pre-edit-intent-gate.py", unknown_payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(unknown_decision, "project-dev")
            assert unknown_decision is not None
            unknown_reason = str(unknown_decision.get("reason", ""))
            inspect_route = (
                "builtin command "
                + shlex.quote(str(agent_run.resolve()))
                + " inspect --cwd "
                + shlex.quote(str(repo.resolve()))
                + " -- <argv...>"
            )
            self.assertEqual(unknown_reason.count("Route "), 2)
            self.assertIn(f"Route 1 (local exploration): `{inspect_route}`", unknown_reason)
            self.assertIn(
                f"Route 2 (exact-target project-dev): run `{prepare_edit_cmd}`",
                unknown_reason,
            )

            direct_edit = write_payload("src/lib.rs", "fn main() {}\n")
            direct_edit["session_id"] = "intent-recovery"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", direct_edit, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            assert decision is not None
            direct_reason = str(decision.get("reason", ""))
            self.assertIn(prepare_edit_cmd, direct_reason)
            self.assertIn("[reason: project-dev-required]", direct_reason)

            # Backward compatibility: an explicit `session activate` bootstrap is
            # still consumed and verified in place, so existing muscle-memory and
            # older cues keep working while `session prepare` becomes primary.
            payload = command_payload(activation)
            payload["session_id"] = "intent-recovery"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "consumed")
            self.assertTrue(active_marker.is_file())

            payload = command_payload(preflight)
            payload["session_id"] = "intent-recovery"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_pre_edit_intent_gate_allows_only_trusted_bootstrap_before_activation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            active_marker = root / "active"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session activate"* ]]; then
  printf 'active\n' > {shlex.quote(str(active_marker))}
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f {shlex.quote(str(active_marker))} ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            fake_forge_cli = bin_dir / "forge-cli"
            fake_forge_cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_forge_cli.chmod(0o755)
            state_home = repo / "state"
            agent_docs = str((bin_dir / "agent-docs").resolve())
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            activation = (
                f"{shlex.quote(str((bin_dir / 'agent-docs').resolve()))} "
                f"--docs-home {shlex.quote(str(repo.resolve()))} "
                f"--project-path {shlex.quote(str(repo.resolve()))} session activate "
                "--session-id shell-bootstrap --product codex "
                f"--state-home {shlex.quote(str(state_home.resolve()))} "
                "--intent project-dev"
            )
            preflight = (
                f"{shlex.quote(str((bin_dir / 'agent-docs').resolve()))} "
                f"--docs-home {shlex.quote(str(repo.resolve()))} "
                f"--project-path {shlex.quote(str(repo.resolve()))} "
                "preflight --intent task-tools"
            )
            bare_activation = activation.replace(
                str((bin_dir / "agent-docs").resolve()), "agent-docs", 1
            )
            bare_preflight = preflight.replace(
                str((bin_dir / "agent-docs").resolve()), "agent-docs", 1
            )
            wrong_project_preflight = (
                f"{shlex.quote(str((bin_dir / 'agent-docs').resolve()))} "
                f"--docs-home {shlex.quote(str(repo.resolve()))} "
                f"--project-path {shlex.quote(str(root.resolve()))} "
                "preflight --intent task-tools"
            )
            # Still gated as repository mutations: shell writes, a file-writing
            # --output flag, and shell-control wrappers all require project-dev.
            blocked = (
                "git diff --output=src/diff.txt",
                f"{preflight} --output src/preflight.json",
                f"alias agent-docs='printf x > src/lib.rs'; {bare_activation}",
                f"agent-docs() {{ printf x > src/lib.rs; }}; {bare_activation}",
            )
            for command in blocked:
                with self.subTest(blocked=command):
                    payload = command_payload(command)
                    payload["session_id"] = "shell-bootstrap"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            # A bare agent-docs spelling is a near miss, not evidence that the
            # requested non-project-dev intent itself requires project-dev.
            for command in (bare_activation, bare_preflight):
                with self.subTest(agent_docs_near_miss=command):
                    payload = command_payload(command)
                    payload["session_id"] = "shell-bootstrap"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "trusted agent-docs")
                    self.assertIn(
                        "[reason: agent-docs-command-untrusted]", str(decision)
                    )
                    self.assertNotIn("before mutating", str(decision).lower())

            # These direct fallback calls have no verified capability.
            # Real managed queries are admitted by the released dispatcher,
            # covered by the paired-capability consumer test.
            unverified_reads = (
                "git status --short",
                preflight,
                wrong_project_preflight,
                f"{preflight} --product claude",
                f"{agent_docs} --help",
                f"{agent_docs} session prepare --help",
                "agent-docs --help",
                "agent-docs session prepare --help",
                "forge-cli --help",
                "forge-cli issue create --help",
                "forge-cli --version",
            )
            for command in unverified_reads:
                with self.subTest(unverified_read=command):
                    payload = command_payload(command)
                    payload["session_id"] = "shell-bootstrap"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            repo_bin = repo / "bin"
            repo_bin.mkdir()
            repo_bin_log = root / "repo-bin.log"
            self._write_fake_agent_docs(
                repo_bin,
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {shlex.quote(str(repo_bin_log))}
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            shadowed = activation.replace(
                str((bin_dir / "agent-docs").resolve()),
                str((repo_bin / "agent-docs").resolve()),
                1,
            )
            payload = command_payload(shadowed)
            payload["session_id"] = "shell-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={
                    **env,
                    "PATH": f"{repo_bin}{os.pathsep}{env['PATH']}",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "resolved trusted agent-docs")
            self.assertIn("[reason: agent-docs-command-untrusted]", str(decision))
            self.assertFalse(repo_bin_log.exists())

            shadow_forge_marker = root / "shadow-forge-ran"
            shadow_forge = repo_bin / "forge-cli"
            shadow_forge.write_text(
                "#!/bin/sh\ntouch "
                + shlex.quote(str(shadow_forge_marker))
                + "\nexit 0\n",
                encoding="utf-8",
            )
            shadow_forge.chmod(0o755)
            payload = command_payload("forge-cli --help")
            payload["session_id"] = "shell-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={
                    **env,
                    "PATH": f"{repo_bin}{os.pathsep}{env['PATH']}",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            self.assertFalse(shadow_forge_marker.exists())

            foreign_bin = root / "foreign-bin"
            foreign_bin.mkdir()
            foreign_forge_marker = root / "foreign-forge-ran"
            foreign_forge = foreign_bin / "forge-cli"
            foreign_forge.write_text(
                "#!/bin/sh\ntouch "
                + shlex.quote(str(foreign_forge_marker))
                + "\nexit 0\n",
                encoding="utf-8",
            )
            foreign_forge.chmod(0o755)
            payload = command_payload("forge-cli --help")
            payload["session_id"] = "shell-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={
                    **env,
                    "PATH": f"{foreign_bin}{os.pathsep}{env['PATH']}",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            self.assertFalse(foreign_forge_marker.exists())

            for command in (
                "forge-cli issue create",
                "forge-cli --config malicious --help",
                "forge-cli issue create --help --body payload",
                "agent-docs session prepare --help --format json",
            ):
                with self.subTest(non_help_cli_shape=command):
                    payload = command_payload(command)
                    payload["session_id"] = "shell-bootstrap"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            payload = command_payload(activation)
            payload["session_id"] = "shell-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "consumed")
            self.assertTrue(active_marker.is_file())

            payload = command_payload(preflight)
            payload["session_id"] = "shell-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_pre_edit_intent_gate_claim_bootstrap_has_no_read_admission(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            other_repo = root / "other-repo"
            other_repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=other_repo, check=True)
            (other_repo / "AGENT_DOCS.toml").write_text(
                "# fixture\n", encoding="utf-8"
            )

            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session verify --help"* ]]; then echo '--phase'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  printf '%s\n' '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                "#!/bin/sh\necho 'agent-session 1.24.5'\nexit 0\n",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            agent_run = bin_dir / "agent-run"
            agent_run.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            agent_run.chmod(0o755)
            ripgrep = bin_dir / "rg"
            ripgrep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            ripgrep.chmod(0o755)
            private_dir = root / "private"
            private_dir.mkdir()
            claim_file = private_dir / "work-context.json"
            claim_file.write_text("{}\n", encoding="utf-8")
            claim_file.chmod(0o600)
            capability_file = private_dir / "capability"
            capability_file.write_text("fixture\n", encoding="utf-8")
            capability_file.chmod(0o600)
            foreign_capability_file = private_dir / "foreign-capability"
            foreign_capability_file.write_text("fixture\n", encoding="utf-8")
            foreign_capability_file.chmod(0o600)
            repository_claim_file = repo / "work-context.json"
            repository_claim_file.write_text("{}\n", encoding="utf-8")
            repository_claim_file.chmod(0o600)

            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "AGENT_SESSION_ID": "session-readiness",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability_file.resolve()),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            trusted_agent_run = str(agent_run.resolve())
            claim = (
                "agent-session work-context claim "
                "--session session-readiness "
                f"--file {claim_file.resolve()} "
                f"--capability-file {capability_file.resolve()} "
                "--idempotency-key readiness-claim-0001 --format json"
            )
            literal_claim = (
                "agent-session work-context claim "
                '--session "$AGENT_SESSION_ID" '
                f"--file {claim_file.resolve()} "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key readiness-claim-0001 --format json"
            )
            revision_fenced_claim = literal_claim.replace(
                f"--file {claim_file.resolve()} ",
                f"--file {claim_file.resolve()} --if-revision 1 ",
            )
            former_readiness_reads = (
                "agent-session --version",
                "agent-session activity doctor --agent codex --format json",
                "agent-session activity doctor --agent claude --format json",
                "agent-session activity setup --agent codex --repair --dry-run --format json",
                "agent-session activity setup --agent claude --repair --dry-run --format json",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- git status --short --branch",
                "rg --no-config readiness .",
            )
            claim_bootstraps = (claim, literal_claim, revision_fenced_claim)
            for command in claim_bootstraps:
                with self.subTest(claim_bootstrap=command):
                    payload = command_payload(command)
                    payload["session_id"] = "session-readiness"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            for command in former_readiness_reads:
                with self.subTest(unverified_read=command):
                    payload = command_payload(command)
                    payload["session_id"] = "session-readiness"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            foreign_bin = root / "foreign-bin"
            foreign_bin.mkdir()
            foreign_agent_session = foreign_bin / "agent-session"
            foreign_agent_session.write_text(
                "#!/bin/sh\nexit 0\n", encoding="utf-8"
            )
            foreign_agent_session.chmod(0o755)
            foreign_agent_run = foreign_bin / "agent-run"
            foreign_agent_run.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            foreign_agent_run.chmod(0o755)
            blocked = (
                "main-agent self readiness --format json",
                "main-agent bootstrap --idempotency-key retirement-0001 --format json",

                "agent-session --help",
                "agent-session -V",
                "agent-session --version | cat",
                f"agent-session --version > {root / 'version.txt'}",
                "agent-session --version && true",
                "agent-session --version; true",
                'echo "$(agent-session --version)"',
                f"{agent_session.resolve()} --version",
                claim.replace("agent-session", str(agent_session.resolve()), 1),
                claim.replace(
                    "agent-session", str(foreign_agent_session.resolve()), 1
                ),
                "agent-session activity doctor --agent gemini --format json",
                "agent-session activity doctor --agent codex",
                "agent-session activity doctor --format json --agent codex",
                "agent-session activity doctor --agent=codex --format json",
                "agent-session activity doctor --agent codex --format=json",
                "agent-session activity doctor --agent codex --format json extra",
                "agent-session activity setup --agent codex --repair --format json",
                "agent-session activity setup --agent codex --repair --dry-run",
                "agent-session activity setup --agent codex --repair --dry-run --apply --format json",
                "agent-session activity setup --agent codex --repair --dry-run --format json extra",
                claim.replace("--session session-readiness ", ""),
                claim.replace("--file " + str(claim_file.resolve()) + " ", ""),
                claim.replace(
                    "--capability-file " + str(capability_file.resolve()) + " ", ""
                ),
                claim.replace("--idempotency-key readiness-claim-0001 ", ""),
                claim.replace(" --format json", ""),
                claim.replace(
                    "--session session-readiness", "--session another-session"
                ),
                claim.replace(str(claim_file.resolve()), "work-context.json"),
                claim.replace(
                    str(claim_file.resolve()), str(repository_claim_file.resolve())
                ),
                claim.replace(
                    str(capability_file.resolve()),
                    str(foreign_capability_file.resolve()),
                ),
                claim + " extra",
                claim.replace(
                    "--idempotency-key readiness-claim-0001 --format json",
                    "--format json --idempotency-key readiness-claim-0001",
                ),
                claim.replace("--format json", "--if-revision 1 --format json"),
                claim.replace(
                    "work-context claim", "--host untrusted work-context claim"
                ),
                claim.replace(
                    "work-context claim",
                    f"--state-dir {repo.resolve()} work-context claim",
                ),
                literal_claim.replace(
                    "$AGENT_SESSION_ID", "$OTHER_SESSION_ID"
                ),
                literal_claim.replace(
                    "$AGENT_SESSION_CAPABILITY_FILE", "$OTHER_CAPABILITY_FILE"
                ),
                literal_claim.replace('"$AGENT_SESSION_ID"', "$AGENT_SESSION_ID"),
                literal_claim.replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    "$AGENT_SESSION_CAPABILITY_FILE",
                ),
                literal_claim.replace(
                    "--idempotency-key readiness-claim-0001 --format json",
                    "--format json --idempotency-key readiness-claim-0001",
                ),
                literal_claim + " --if-revision 1",
                f"agent-run inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"{trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"builtin {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"command builtin {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"builtin -- command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"builtin command -- {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"builtin command {foreign_agent_run.resolve()} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd . -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve() / '..' / 'repo'} -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd {other_repo.resolve()} -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd '$PWD' -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} --",
                f"builtin command {trusted_agent_run} inspect --cwd={repo.resolve()} -- rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect -- {repo.resolve()} --cwd rg --no-config readiness .",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg readiness . | cat",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg readiness . > {root / 'inspect.txt'}",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg readiness . && true",
                f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg readiness .; true",
                f'echo "$(builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg readiness .)"',
                f"builtin command {trusted_agent_run} --future inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                f"env builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                "rg readiness .",
            )
            for command in blocked:
                with self.subTest(blocked=command):
                    payload = command_payload(command)
                    payload["session_id"] = "session-readiness"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            shadow_bin = repo / "bin"
            shadow_bin.mkdir()
            shadow_agent_session = shadow_bin / "agent-session"
            shadow_agent_session.write_text(
                "#!/bin/sh\nexit 0\n", encoding="utf-8"
            )
            shadow_agent_session.chmod(0o755)
            shadow_agent_run = shadow_bin / "agent-run"
            shadow_agent_run.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            shadow_agent_run.chmod(0o755)
            for candidate in (shadow_bin, foreign_bin):
                for command in (
                    "agent-session --version",
                    claim,
                    f"builtin command {trusted_agent_run} inspect --cwd {repo.resolve()} -- rg --no-config readiness .",
                ):
                    with self.subTest(
                        readiness_companion_shadow=candidate, command=command
                    ):
                        payload = command_payload(command)
                        payload["session_id"] = "session-readiness"
                        code, decision, stderr = run_hook(
                            "pre-edit-intent-gate.py",
                            payload,
                            cwd=repo,
                            env={
                                **env,
                                "PATH": f"{candidate}{os.pathsep}{env['PATH']}",
                            },
                        )
                        self.assertEqual(code, 0, stderr)
                        self.assert_blocked(decision, "project-dev")

            alias_bin = root / "foreign-alias-bin"
            alias_bin.mkdir()
            (alias_bin / "agent-session").symlink_to(agent_session.resolve())
            (alias_bin / "agent-run").symlink_to(agent_run.resolve())
            alias_env = {
                **env,
                "PATH": f"{alias_bin}{os.pathsep}{env['PATH']}",
            }
            alias_commands = claim_bootstraps
            for command in alias_commands:
                with self.subTest(foreign_same_release_alias=command):
                    payload = command_payload(command)
                    payload["session_id"] = "session-readiness"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=repo,
                        env=alias_env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            payload = command_payload("python3 -c 'print(1)'")
            payload["session_id"] = "session-readiness"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env=alias_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            assert decision is not None
            self.assertNotIn("Route 1", str(decision.get("reason", "")))


    def test_pre_edit_trusted_release_companions_require_lexical_and_resolved_siblings(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "pre_edit_companion_trust_under_test",
            HOOK_DIR / "pre-edit-intent-gate.py",
        )
        assert spec is not None and spec.loader is not None
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            release_bin = root / "release" / "bin"
            release_bin.mkdir(parents=True)
            foreign_release_bin = root / "foreign-release" / "bin"
            foreign_release_bin.mkdir(parents=True)
            for directory in (release_bin, foreign_release_bin):
                for name in (
                    "agent-docs",
                    "agent-session",
                    "agent-run",
                ):
                    executable = directory / name
                    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                    executable.chmod(0o755)

            linked_bin = root / "linked-bin"
            linked_bin.mkdir()
            for name in ("agent-docs", "agent-session", "agent-run"):
                (linked_bin / name).symlink_to(release_bin / name)

            base_env = {
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(linked_bin),
                "PATH": f"{linked_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            with mock.patch.dict(os.environ, base_env, clear=False):
                for name in ("agent-session", "agent-run"):
                    with self.subTest(valid_shared_symlink_surface=name):
                        self.assertEqual(
                            gate.trusted_release_companion(
                                name,
                                agent_docs_executable=str(
                                    (release_bin / "agent-docs").resolve()
                                ),
                                repositories=[str(repo.resolve())],
                            ),
                            str((release_bin / name).resolve()),
                        )

            alias_bin = root / "foreign-alias-bin"
            alias_bin.mkdir()
            for name in ("agent-session", "agent-run"):
                (alias_bin / name).symlink_to(release_bin / name)
            with mock.patch.dict(
                os.environ,
                {
                    **base_env,
                    "PATH": f"{alias_bin}{os.pathsep}{base_env['PATH']}",
                },
                clear=False,
            ):
                for name in ("agent-session", "agent-run"):
                    with self.subTest(foreign_lexical_alias=name):
                        self.assertIsNone(
                            gate.trusted_release_companion(
                                name,
                                agent_docs_executable=str(
                                    (release_bin / "agent-docs").resolve()
                                ),
                                repositories=[str(repo.resolve())],
                            )
                        )

            mixed_bin = root / "mixed-bin"
            mixed_bin.mkdir()
            (mixed_bin / "agent-docs").symlink_to(release_bin / "agent-docs")
            for name in ("agent-session", "agent-run"):
                (mixed_bin / name).symlink_to(foreign_release_bin / name)
            with mock.patch.dict(
                os.environ,
                {
                    "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(mixed_bin),
                    "PATH": f"{mixed_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                },
                clear=False,
            ):
                for name in ("agent-session", "agent-run"):
                    with self.subTest(foreign_resolved_release=name):
                        self.assertIsNone(
                            gate.trusted_release_companion(
                                name,
                                agent_docs_executable=str(
                                    (release_bin / "agent-docs").resolve()
                                ),
                                repositories=[str(repo.resolve())],
                            )
                        )


    def test_pre_edit_bootstrap_admits_prepare_from_superseded_release_path(
        self,
    ) -> None:
        """A mid-session CLI upgrade must not strand the trusted bootstrap.

        The bootstrap identity prefix embeds the *resolved* agent-docs path,
        which a Homebrew install version-pins under
        ``Cellar/nils-cli/<version>/bin``. When the release is upgraded
        mid-session the stable ``bin/agent-docs`` symlink repoints, so a
        preparation command replayed from earlier in the session still names the
        superseded -- but equally governed -- sibling. Rejecting it reports
        ``agent-docs-bootstrap-shape-mismatch`` for every prepare variant, and
        the edit gate stays unsatisfiable until the session restarts. The parser
        admits the sibling and canonicalizes it onto the active release, so the
        hook always probes the binary that is installed now. A path outside the
        shared package root, or inside the repository, is still not a bootstrap.
        """
        spec = importlib.util.spec_from_file_location(
            "pre_edit_superseded_release_under_test",
            HOOK_DIR / "pre-edit-intent-gate.py",
        )
        assert spec is not None and spec.loader is not None
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            cellar = root / "prefix" / "Cellar" / "nils-cli"
            superseded_bin = cellar / "1.25.5" / "bin"
            active_bin = cellar / "1.25.6" / "bin"
            foreign_bin = root / "prefix" / "Cellar" / "other-cli" / "1.0.0" / "bin"
            shadow_bin = repo / "vendor" / "bin"
            for directory in (superseded_bin, active_bin, foreign_bin, shadow_bin):
                directory.mkdir(parents=True)
                executable = directory / "agent-docs"
                executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                executable.chmod(0o755)

            stable_bin = root / "prefix" / "bin"
            stable_bin.mkdir()
            (stable_bin / "agent-docs").symlink_to(active_bin / "agent-docs")

            repo_root = str(repo.resolve())
            active = str((active_bin / "agent-docs").resolve())
            env = {
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(stable_bin),
                "AGENT_RUNTIME_STATE_HOME": str(root / "state"),
                "AGENT_RUNTIME_DOCS_HOME": repo_root,
                "PATH": f"{stable_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                base = gate.activation_base_args(
                    repo_root=repo_root,
                    executable=active,
                    current_session="mid-session-upgrade",
                    product="claude",
                    subcommand="prepare",
                )
                tail = [
                    "--intent",
                    "project-dev",
                    "--phase",
                    "edit",
                    "--format",
                    "json",
                ]

                def parse(executable: str):
                    return gate.bootstrap_activation_intents(
                        shlex.join([executable] + base[1:] + tail),
                        current_session="mid-session-upgrade",
                        product="claude",
                        repo_root=repo_root,
                        agent_docs_executable=active,
                    )

                # Sanity: the active release is the already-supported baseline.
                self.assertIsNotNone(parse(active))

                superseded = parse(str((superseded_bin / "agent-docs").resolve()))
                self.assertIsNotNone(
                    superseded,
                    "a superseded release sibling must stay a trusted bootstrap",
                )
                assert superseded is not None
                words, intents, subcommand = superseded
                self.assertEqual(intents, ["project-dev"])
                self.assertEqual(subcommand, "prepare")
                self.assertEqual(
                    words[0],
                    active,
                    "the bootstrap must run the release installed now",
                )
                self.assertEqual(words[1:], base[1:] + tail)

                for label, path in (
                    ("foreign package root", foreign_bin / "agent-docs"),
                    ("repository shadow", shadow_bin / "agent-docs"),
                ):
                    with self.subTest(rejected=label):
                        self.assertIsNone(parse(str(path.resolve())))


    def test_pre_edit_intent_gate_rejects_cross_repository_agent_run_workdir_once(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_repo = root / "session-repo"
            target_repo = root / "target-repo"
            for repo in (session_repo, target_repo):
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text(
                    "# fixture\n", encoding="utf-8"
                )
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","active_intents":["project-dev"],"verified":true}}'
  exit 0
fi
exit 64
""",
            )
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "HOME": str(root / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            (root / "home").mkdir()

            cross_repo_commands = (
                "agent-run exec --cwd "
                + shlex.quote(str(target_repo))
                + " -- cargo check",
                "agent-run exec --cwd="
                + shlex.quote(str(target_repo))
                + " -- cargo check",
                "agent-run exec --direnv off --cwd ../target-repo cargo check",
                "env agent-run exec --cwd ../target-repo -- cargo check",
                "time agent-run exec --cwd ../target-repo -- cargo check",
                "command -- agent-run exec --cwd ../target-repo -- cargo check",
                "bash -c "
                + shlex.quote(
                    "agent-run exec --cwd ../target-repo -- cargo check"
                ),
                "env -S "
                + shlex.quote(
                    "agent-run exec --cwd ../target-repo -- cargo check"
                ),
            )
            for command in cross_repo_commands:
                with self.subTest(command=command):
                    payload = command_payload(command)
                    payload["session_id"] = "cross-repo-workdir"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=session_repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "session rooted at")
                    self.assertIn(
                        "[reason: cross-repository-target-unsupported]",
                        str(decision),
                    )
                    self.assertIn(str(target_repo.resolve()), str(decision))
                    self.assertIn("top-level `workdir`", str(decision))
                    self.assertIn("Do not use shell `cd`", str(decision))
                    self.assertNotIn("session prepare", str(decision))

            for command in (
                'agent-run exec --cwd "$TARGET_REPO" -- cargo check',
                "env --chdir=.. agent-run exec --cwd target-repo -- cargo check",
                "bash -c "
                + shlex.quote(
                    "cd .. && agent-run exec --cwd target-repo -- cargo check"
                ),
            ):
                with self.subTest(opaque_command=command):
                    payload = command_payload(command)
                    payload["session_id"] = "cross-repo-workdir"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=session_repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "cannot be resolved and attested")
                    self.assertIn(
                        "[reason: cross-repository-target-unsupported]",
                        str(decision),
                    )

            same_repo = command_payload(
                "agent-run exec --cwd "
                + shlex.quote(str(session_repo))
                + " -- cargo check"
            )
            same_repo["session_id"] = "cross-repo-workdir"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", same_repo, cwd=session_repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            for command in (
                "agent-run exec -- some-tool --cwd ../target-repo",
                "agent-run exec some-tool --cwd=../target-repo",
            ):
                with self.subTest(child_cwd_argument=command):
                    payload = command_payload(command)
                    payload["session_id"] = "cross-repo-workdir"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=session_repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            mentioned_as_data = command_payload(
                "echo agent-run exec --cwd ../target-repo"
            )
            mentioned_as_data["session_id"] = "cross-repo-workdir"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                mentioned_as_data,
                cwd=session_repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_pre_edit_intent_gate_requires_preparation_for_unverified_reads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            trusted_rg = bin_dir / "rg"
            trusted_rg.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            trusted_rg.chmod(0o755)
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "HOME": str(repo / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            (repo / "home").mkdir()
            read_only = (
                "git status --short",
                "git log --no-ext-diff --no-textconv --oneline -5",
                "git diff --no-ext-diff --no-textconv --stat",
                "git show --no-ext-diff --no-textconv HEAD",
                "git rev-parse --abbrev-ref HEAD",
                "git blame README.md",
                "gh issue view 601",
                "gh pr list",
                "gh pr diff 12",
                "gh repo view",
                "cat README.md",
                "ls -la",
                "grep -rn TODO .",
                "wc -l README.md",
                "which git",
                "rg --no-config TODO .",
                "rg --no-config TODO . | head -n 20",
                "rg --no-config TODO . | wc -l | head -n 1",
                "nl -ba README.md | sed -n '1,20p'",
            )
            # Raw argv is not capability evidence. Without verified preparation
            # the fallback handler must not independently authorize these reads.
            for command in read_only:
                with self.subTest(unverified_read=command):
                    payload = command_payload(command)
                    payload["session_id"] = "read-only-lane"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            shadow_marker = repo / "shadow-rg-ran"
            shadow_bin = repo / "bin"
            shadow_bin.mkdir()
            shadow_rg = shadow_bin / "rg"
            shadow_rg.write_text(
                "#!/bin/sh\ntouch "
                + shlex.quote(str(shadow_marker))
                + "\nexit 0\n",
                encoding="utf-8",
            )
            shadow_rg.chmod(0o755)
            shadow_env = {
                **env,
                "PATH": f"{shadow_bin}{os.pathsep}{env['PATH']}",
            }
            payload = command_payload("rg --no-config TODO .")
            payload["session_id"] = "read-only-lane"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=shadow_env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            self.assertFalse(shadow_marker.exists())

            # Write- or exec-capable shapes are not read-only and stay gated.
            # The git-grep pager, `file -C`, and path-prefixed executable cases
            # are security-review regressions: each could execute code or write a
            # file, so each must fall through to the mutation gate.
            gated = (
                "git diff --output=out.diff",
                "git grep -O foo",
                "git grep --open-files-in-pager=rm needle",
                "git grep foo",
                "gh api /repos/x",
                "gh pr checkout 3",
                "rg foo src",
                "rg --no-config --pre cat foo src",
                "rg --no-config --hostname-bin ./evil TODO .",
                "rg --no-config --hostname-bin=./evil TODO .",
                "rg --no-config --search-zip TODO archive.gz",
                "rg --no-config -z TODO archive.gz",
                "rg --no-config -Hz TODO archive.gz",
                "rg TODO . -- --no-config",
                "rg --no-config TODO . || head -n 1 README.md",
                "git log --oneline -5",
                "git diff --stat",
                "git show HEAD",
                "git diff --ext-diff",
                "git show --textconv HEAD",
                "find . -delete",
                "sort -o out in",
                "cat a | tee b",
                "cat README.md > copy.md",
                "cat $(pwd)/README.md",
                "echo 'read\\' ; touch owned ; echo 'tail\\'",
                "nl -ba README.md | sed -n '1,20e touch owned'",
                "env FOO=1 cat f",
                "file -C -m mymagic",
                "file README.md",
                "./grep TODO",
                "bin/ls",
                "/usr/bin/cat README.md",
            )
            for command in gated:
                with self.subTest(gated=command):
                    payload = command_payload(command)
                    payload["session_id"] = "read-only-lane"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","active_intents":["project-dev"],"verified":true}}'
  exit 0
fi
exit 64
""",
            )
            for command in read_only:
                with self.subTest(prepared_read=command):
                    payload = command_payload(command)
                    payload["session_id"] = "read-only-lane"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_pre_edit_intent_gate_prepares_any_declared_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            active_marker = root / "active"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session activate"* ]]; then
  printf 'active\\n' > {shlex.quote(str(active_marker))}
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f {shlex.quote(str(active_marker))} ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["memory","task-tools","project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            state_home = repo / "state"
            agent_docs = str((bin_dir / "agent-docs").resolve())
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            def activation_for(*intents: str) -> str:
                argv = [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "activate",
                    "--session-id",
                    "any-intent",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home.resolve()),
                ]
                for intent in intents:
                    argv += ["--intent", intent]
                return shlex.join(argv)

            for intents in (("memory",), ("task-tools",), ("memory", "task-tools")):
                with self.subTest(intents=intents):
                    if active_marker.exists():
                        active_marker.unlink()
                    payload = command_payload(activation_for(*intents))
                    payload["session_id"] = "any-intent"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "consumed")
                    assert decision is not None
                    reason = str(decision.get("reason", ""))
                    self.assertIn("Prepared", reason)
                    for intent in intents:
                        self.assertIn(intent, reason)
                    self.assertTrue(active_marker.is_file())


    def test_pre_edit_intent_gate_consumes_session_prepare(self) -> None:
        """P0-1/P0-3: `session prepare` is consumed atomically.

        The trusted preparation primitive activates and strict-preflights in a
        single call and returns a stable JSON result, so the hook must not fire a
        second `session verify` probe. Failure messages use fixed text and do not
        copy arbitrary structured error codes from the CLI.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            state_home = repo / "state"
            agent_docs = str((bin_dir / "agent-docs").resolve())

            def prepare_command(*intents: str) -> str:
                argv = [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "prepare",
                    "--session-id",
                    "prep-session",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home.resolve()),
                ]
                for intent in intents:
                    argv += ["--intent", intent]
                argv += ["--format", "json"]
                return shlex.join(argv)

            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            # A fake that succeeds for `session prepare` and would emit a distinct
            # marker if the hook ever fell back to `session verify`.
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {shlex.quote(str(call_log))}
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session prepare"* ]]; then
  intents='["project-dev"]'
  if [[ "$*" == *"--intent project-dev"* && "$*" == *"--intent task-tools"* ]]; then
    intents='["project-dev","task-tools"]'
  elif [[ "$*" == *"--intent task-tools"* ]]; then
    intents='["task-tools"]'
  fi
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.prepare.v1","ok":true,"data":{{"product":"codex","active_intents":'"$intents"',"record_file":"r.json","verified":true,"prepared_intents":'"$intents"',"reason":"prepared"}}}}'
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  printf '%s\\n' 'FALLBACK-VERIFY-SHOULD-NOT-RUN'
  exit 0
fi
exit 64
""",
            )

            for intents in (
                ("project-dev",),
                ("task-tools",),
                ("project-dev", "task-tools"),
            ):
                with self.subTest(intents=intents):
                    call_log.write_text("", encoding="utf-8")
                    payload = command_payload(prepare_command(*intents))
                    payload["session_id"] = "prep-session"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "consumed")
                    assert decision is not None
                    reason = str(decision.get("reason", ""))
                    self.assertIn("Prepared", reason)
                    self.assertIn("[reason: prepared]", reason)
                    self.assertIn("[action: retry-original]", reason)
                    self.assertIn("Retry the original command", reason)
                    self.assertIn(
                        "Do not run this preparation command again", reason
                    )
                    for intent in intents:
                        self.assertIn(intent, reason)
                    log_text = call_log.read_text(encoding="utf-8")
                    self.assertIn("session prepare", log_text)
                    # Atomic: the hook trusts the prepare envelope and never
                    # fires a second verify probe.
                    self.assertNotIn("session verify", log_text)
                    self.assertNotIn("FALLBACK-VERIFY-SHOULD-NOT-RUN", reason)

            # Untrusted structured error codes are not copied into hook output.
            fail_log = root / "fail.log"
            fixture_code = "err-7f21"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {shlex.quote(str(fail_log))}
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session prepare"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.prepare.v1","ok":false,"error":{{"code":"{fixture_code}","message":"strict preflight failed"}}}}'
  exit 65
fi
exit 64
""",
            )
            payload = command_payload(prepare_command("project-dev"))
            payload["session_id"] = "prep-session"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert decision is not None
            reason = str(decision.get("reason", ""))
            self.assertIn("preparation did not verify", reason)
            self.assertNotIn(fixture_code, reason)
            # The submitted shell body is consumed, not re-dispatched.
            self.assertIn("consumed", reason)

            # Defense in depth: a well-formed ok/verified envelope on a NONZERO
            # exit fails closed, matching verify_intent's returncode==0 success
            # gate. The success message must not be emitted.
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session prepare"* ]]; then
  printf '%s\\n' '{"schema_version":"cli.agent-docs.session.prepare.v1","ok":true,"data":{"product":"codex","active_intents":["project-dev"],"record_file":"r.json","verified":true,"prepared_intents":["project-dev"],"reason":"prepared"}}'
  exit 3
fi
exit 64
""",
            )
            payload = command_payload(prepare_command("project-dev"))
            payload["session_id"] = "prep-session"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            assert decision is not None
            reason = str(decision.get("reason", ""))
            self.assertIn("[reason: preparation-verification-failed]", reason)
            self.assertNotIn("[reason: prepared]", reason)


    def test_pre_edit_intent_gate_scopes_edit_phase_for_direct_edits(self) -> None:
        """#601 3d: a direct edit is gated on the phase-scoped `edit` doc set.

        When the trusted CLI advertises `--phase`, the block recovery and the
        `session verify` probe the hook fires are both scoped to `--phase edit`,
        so an edit no longer forces the full delivery/review runbook set.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            marker = root / "prepared"
            self._write_fake_agent_docs(
                bin_dir,
                self._phase_aware_fake_agent_docs(log_path=call_log, marker=marker),
            )
            env = self._phase_gate_env(repo, bin_dir)
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "edit-phase"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")
            reason = str(decision)
            self.assertIn("--intent project-dev", reason)
            self.assertIn("--phase edit", reason)
            verify_calls = self._verify_calls(call_log)
            self.assertTrue(verify_calls)
            self.assertTrue(all("--phase edit" in line for line in verify_calls))


    def test_pre_edit_intent_gate_scopes_delivery_phase_for_delivery_tools(self) -> None:
        """#601 3d: governed delivery CLIs verify the `delivery` phase.

        `semantic-commit`/`forge-cli`/`git-cli` are delivery-phase mutations; any
        other mutation-capable shell (a build, a generic file write) is content
        work and stays on the `edit` phase.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            marker = root / "prepared"
            self._write_fake_agent_docs(
                bin_dir,
                self._phase_aware_fake_agent_docs(log_path=call_log, marker=marker),
            )
            env = self._phase_gate_env(repo, bin_dir)
            cases = [
                ("semantic-commit --type chore --message x", "delivery"),
                ("forge-cli pr create", "delivery"),
                ("git-cli worktree add slug", "delivery"),
                ("touch generated.txt", "edit"),
            ]
            for command, phase in cases:
                with self.subTest(command=command):
                    call_log.write_text("", encoding="utf-8")
                    payload = command_payload(command)
                    payload["session_id"] = "delivery-phase"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")
                    self.assertIn(f"--phase {phase}", str(decision))
                    verify_calls = self._verify_calls(call_log)
                    self.assertTrue(verify_calls)
                    self.assertTrue(
                        all(f"--phase {phase}" in line for line in verify_calls)
                    )


    def test_pre_edit_intent_gate_uninspectable_shell_uses_full_intent(self) -> None:
        """#601 3d: a shell command the parser cannot reduce falls back to full.

        A delivery CLI wrapped in shell control (a `$(...)` / heredoc commit
        message) -- or any other uninspectable mutation -- must NOT be downgraded
        to the lighter `edit` phase. Verification falls back to the full, no-phase
        project-dev set (the safe superset), so the delivery/review runbooks are
        still required when the command cannot be classified.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            marker = root / "prepared"
            self._write_fake_agent_docs(
                bin_dir,
                self._phase_aware_fake_agent_docs(log_path=call_log, marker=marker),
            )
            env = self._phase_gate_env(repo, bin_dir)
            for command in (
                'semantic-commit commit --message "$(printf body)"',
                "printf x > out.txt",
            ):
                with self.subTest(command=command):
                    call_log.write_text("", encoding="utf-8")
                    payload = command_payload(command)
                    payload["session_id"] = "uninspectable"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")
                    self.assertNotIn("--phase", str(decision))
                    verify_calls = self._verify_calls(call_log)
                    self.assertTrue(verify_calls)
                    self.assertTrue(all("--phase" not in line for line in verify_calls))


    def test_pre_edit_intent_gate_full_prepare_satisfies_phase_verify(self) -> None:
        """#601 3d: a full (no-phase) preparation satisfies a phase verify.

        The safe fallback the design preserves: an agent that prepared the whole
        `project-dev` intent is never blocked by phase-scoping, and the hook
        still threads the mapped phase into the verify probe.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            marker = root / "prepared"
            marker.write_text("prepared\n", encoding="utf-8")  # a full prep exists
            self._write_fake_agent_docs(
                bin_dir,
                self._phase_aware_fake_agent_docs(log_path=call_log, marker=marker),
            )
            env = self._phase_gate_env(repo, bin_dir)
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "full-prep"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            verify_calls = self._verify_calls(call_log)
            self.assertTrue(verify_calls)
            self.assertTrue(all("--phase edit" in line for line in verify_calls))


    def test_pre_edit_intent_gate_consumes_phase_scoped_prepare(self) -> None:
        """#601 3d: a trusted phase-scoped `session prepare --phase edit` runs.

        The bootstrap parser must accept a trailing `--phase` after the intent
        pairs so the phase-scoped recovery command the gate itself emits is
        recognized as a preparation and consumed, not re-dispatched.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            marker = root / "prepared"
            self._write_fake_agent_docs(
                bin_dir,
                self._phase_aware_fake_agent_docs(log_path=call_log, marker=marker),
            )
            env = self._phase_gate_env(repo, bin_dir)
            agent_docs = str((bin_dir / "agent-docs").resolve())
            prepare = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "prepare",
                    "--session-id",
                    "phase-prep",
                    "--product",
                    "codex",
                    "--state-home",
                    str((repo / "state").resolve()),
                    "--intent",
                    "project-dev",
                    "--phase",
                    "edit",
                    "--format",
                    "json",
                ]
            )
            payload = command_payload(prepare)
            payload["session_id"] = "phase-prep"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "consumed")
            self.assertIn("Prepared", str(decision))
            prepare_calls = [
                line
                for line in call_log.read_text(encoding="utf-8").splitlines()
                if "session prepare" in line
            ]
            self.assertTrue(prepare_calls)
            self.assertTrue(all("--phase edit" in line for line in prepare_calls))
            self.assertTrue(all("--format json" in line for line in prepare_calls))


    def test_pre_edit_intent_gate_recovers_from_trusted_prepare_shape_mismatch(
        self,
    ) -> None:
        """Recoverable stale prepares preserve their intent and phase."""
        cases = (
            (
                "project-dev-edit",
                "project-dev",
                "edit",
                write_payload("src/lib.rs", "fn main() {}\n"),
            ),
            (
                "project-dev-delivery",
                "project-dev",
                "delivery",
                command_payload("forge-cli pr create"),
            ),
            ("task-tools", "task-tools", None, None),
        )
        for name, intent, phase, original_payload in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / "repo"
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text(
                    "# fixture\n", encoding="utf-8"
                )
                bin_dir = root / "runtime-bin"
                bin_dir.mkdir()
                call_log = root / "calls.log"
                marker = root / "prepared"
                self._write_fake_agent_docs(
                    bin_dir,
                    self._phase_aware_fake_agent_docs(
                        log_path=call_log,
                        marker=marker,
                        prepared_intent=intent,
                    ),
                )
                managed_session = f"managed-shape-recovery-{name}"
                env = dict(
                    self._phase_gate_env(repo, bin_dir),
                    AGENT_SESSION_ID=managed_session,
                )
                agent_docs = str((bin_dir / "agent-docs").resolve())
                base = [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "prepare",
                    "--session-id",
                    managed_session,
                    "--product",
                    "codex",
                    "--state-home",
                    str((repo / "state").resolve()),
                    "--intent",
                    intent,
                ]
                if phase is not None:
                    base += ["--phase", phase]
                stale_prepare = shlex.join(base)
                canonical_prepare = shlex.join(base + ["--format", "json"])

                stale_payload = command_payload(stale_prepare)
                stale_payload["session_id"] = "provider-shape-recovery"
                code, advisory, stderr = run_hook(
                    "pre-edit-intent-gate.py",
                    stale_payload,
                    cwd=repo,
                    env={
                        **env,
                        "AGENT_RUNTIME_PROJECT_DEV_MODE": "advisory",
                    },
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNotNone(advisory)
                assert advisory is not None
                self.assertNotEqual(advisory.get("decision"), "block")
                advisory_reason = str(advisory.get("systemMessage", ""))
                self.assertIn(
                    "not treated as a trusted bootstrap", advisory_reason
                )
                self.assertIn("will execute normally", advisory_reason)
                self.assertNotIn("was not executed", advisory_reason)

                code, decision, stderr = run_hook(
                    "pre-edit-intent-gate.py", stale_payload, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(
                    decision, "agent-docs-bootstrap-shape-mismatch"
                )
                assert decision is not None
                recovery_commands = re.findall(
                    r"`([^`\n]+)`", str(decision.get("reason", ""))
                )
                self.assertEqual(recovery_commands, [canonical_prepare])
                self.assertFalse(
                    marker.exists(), "the stale command must not execute"
                )

                recovery_payload = command_payload(recovery_commands[0])
                recovery_payload["session_id"] = "provider-shape-recovery"
                code, decision, stderr = run_hook(
                    "pre-edit-intent-gate.py", recovery_payload, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "[reason: prepared]")
                self.assertTrue(marker.exists())

                if original_payload is not None:
                    original_payload["session_id"] = "provider-shape-recovery"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        original_payload,
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_pre_edit_intent_gate_defers_unverified_agent_docs_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            agent_docs = str((bin_dir / "agent-docs").resolve())
            base = (
                f"{shlex.quote(agent_docs)} "
                f"--docs-home {shlex.quote(str(repo.resolve()))} "
                f"--project-path {shlex.quote(str(repo.resolve()))} "
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            unverified_reads = (
                base + "preflight --intent memory",
                base + "preflight --intent browser-test",
                base + "status",
                base + "explain --intent memory",
                base + "list --format json",
                base + "catalog",
                base + "session status",
                base + "session verify --require-intent memory",
            )
            for command in unverified_reads:
                with self.subTest(unverified_read=command):
                    payload = command_payload(command)
                    payload["session_id"] = "adocs-read"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            blocked = (
                base + "preflight --intent memory --output /tmp/x",
                "agent-docs preflight --intent memory",
            )
            for command in blocked:
                with self.subTest(blocked=command):
                    payload = command_payload(command)
                    payload["session_id"] = "adocs-read"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")


    def test_pre_edit_intent_gate_blocks_unquoted_glob_executable_substitution(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")

            trusted_bin = root / "runtime[1]"
            expanded_bin = root / "runtime1"
            trusted_bin.mkdir()
            expanded_bin.mkdir()
            active_marker = root / "active"
            self._write_fake_agent_docs(
                trusted_bin,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session activate"* ]]; then
  printf 'active\n' > {shlex.quote(str(active_marker))}
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f {shlex.quote(str(active_marker))} ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )
            self._write_fake_agent_docs(expanded_bin, "#!/bin/sh\nexit 0\n")

            state_home = repo / "state"
            agent_docs = str((trusted_bin / "agent-docs").resolve())
            activation = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "activate",
                    "--session-id",
                    "glob-bootstrap",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home.resolve()),
                    "--intent",
                    "project-dev",
                ]
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "PATH": f"{trusted_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            unquoted_activation = activation.replace(
                shlex.quote(agent_docs), agent_docs, 1
            )
            self.assertNotEqual(unquoted_activation, activation)
            payload = command_payload(unquoted_activation)
            payload["session_id"] = "glob-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")

            payload = command_payload(activation)
            payload["session_id"] = "glob-bootstrap"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "consumed")
            self.assertTrue(active_marker.is_file())


    def test_pre_edit_intent_gate_consumes_activation_before_shell_dispatch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")

            bin_dir = root / "runtime-bin"
            bin_dir.mkdir()
            active_marker = root / "active"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session activate"* ]]; then
  if [[ "${{ACTIVATION_FAIL:-0}}" == 1 ]]; then exit 70; fi
  printf 'active\n' > {shlex.quote(str(active_marker))}
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f {shlex.quote(str(active_marker))} ]]; then
    echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"codex","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  echo '{{"ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
""",
            )

            state_home = repo / "state"
            agent_docs = str((bin_dir / "agent-docs").resolve())
            activation = shlex.join(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo.resolve()),
                    "--project-path",
                    str(repo.resolve()),
                    "session",
                    "activate",
                    "--session-id",
                    "function-shadow",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home.resolve()),
                    "--intent",
                    "project-dev",
                ]
            )
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            payload = command_payload(activation)
            payload["session_id"] = "function-shadow"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={**env, "ACTIVATION_FAIL": "1"},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "consumed")
            self.assertFalse(active_marker.exists())

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "consumed")
            self.assertTrue(active_marker.is_file())

            shell_probes = (
                (
                    f"function {agent_docs} {{ printf path-shadow; }}; {activation}",
                    "path-shadow",
                ),
                (
                    f"function command {{ printf command-shadow; }}; command {activation}",
                    "command-shadow",
                ),
                (
                    f"function builtin {{ printf builtin-shadow; }}; builtin command {activation}",
                    "builtin-shadow",
                ),
            )
            shells = (
                (shutil.which("bash"), "-c"),
                (shutil.which("zsh"), "-fc"),
            )
            for shell, flag in shells:
                if shell is None:
                    continue
                for script, expected in shell_probes:
                    with self.subTest(shell=shell, expected=expected):
                        completed = subprocess.run(
                            [shell, flag, script],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertEqual(completed.stdout, expected)


    def test_pre_edit_intent_gate_allows_unrelated_workspace_shell_commands(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside"
            outside.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=outside, check=True)
            env = {"AGENT_RUNTIME_PRODUCT": "codex"}
            cases = (
                "pwd",
                "ls -la",
                "git status --short",
                "bash -c 'printf unrelated-workspace'",
                "printf x > local.txt",
            )
            for command in cases:
                with self.subTest(command=command):
                    payload = command_payload(command)
                    payload["session_id"] = "undiscovered-shell"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=outside, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)


    def test_pre_edit_intent_gate_blocks_ambiguous_shell_and_cross_repo_wrappers(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "governed"
            outside = root / "outside"
            repo.mkdir()
            outside.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "lib.rs").write_text("x\n", encoding="utf-8")
            (repo / "scripts").mkdir()
            (repo / "scripts" / "mutate.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  echo '{"ok":false,"error":{"code":"required-intent-not-active"}}'
  exit 1
fi
exit 64
""",
            )
            env = {
                "AGENT_RUNTIME_PRODUCT": "claude",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            target = shlex.quote(str(repo / "src" / "lib.rs"))
            script = shlex.quote(str(repo / "scripts" / "mutate.sh"))
            governed_cases = (
                (repo, "bash -c 'printf x > src/lib.rs'"),
                (repo, "sh -c 'printf x > src/lib.rs'"),
                (repo, "target=src/lib.rs; printf x > \"$target\""),
                (repo, "printf x > \"$(pwd)/src/lib.rs\""),
                (repo, "mutate_repo"),
                (repo, "mutate_repo() { printf x > src/lib.rs; }; mutate_repo"),
                (repo, "printf x > 'src/lib.rs"),
            )
            for cwd, command in governed_cases:
                with self.subTest(cwd=cwd.name, command=command):
                    payload = command_payload(command)
                    payload["session_id"] = "ambiguous-shell"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=cwd, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")

            # A pre-tool Bash hook cannot observe shell-expanded destination
            # paths reliably. The enforceable contract is the command CWD;
            # cross-repository shell writes must execute with the target repo
            # as CWD, while direct-edit tools retain per-target verification.
            outside_cases = (
                f"bash -c 'printf x > {target}'",
                f"target={target}; printf x > \"$target\"",
                f"printf x > \"$(dirname {target})/lib.rs\"",
                f"bash {script}",
            )
            for command in outside_cases:
                with self.subTest(cwd="outside", command=command):
                    payload = command_payload(command)
                    payload["session_id"] = "cwd-scoped-shell"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=outside, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            payload = command_payload("printf x > src/lib.rs", workdir=str(repo))
            payload["session_id"] = "payload-workdir-governed"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=outside, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")

            payload = command_payload("printf x > local.txt", workdir=str(outside))
            payload["session_id"] = "payload-workdir-unmanaged"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            payload = command_payload("printf x > src/lib.rs")
            payload["cwd"] = str(repo)
            payload["session_id"] = "payload-top-level-cwd"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=outside, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")


    def test_pre_edit_intent_gate_requires_strict_verified_response_shape(self) -> None:
        invalid_responses = (
            "{}",
            "[]",
            '{"schema_version":"wrong","ok":true,"data":{"product":"codex","active_intents":["project-dev"],"verified":true}}',
            '{"ok":false,"data":{"verified":true}}',
            '{"ok":true}',
            '{"ok":true,"data":{}}',
            '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"claude","active_intents":["project-dev"],"verified":true}}',
            '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","verified":true}}',
            '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","active_intents":[],"verified":true}}',
            '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","active_intents":["browser-test"],"verified":true}}',
            '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","active_intents":"project-dev","verified":true}}',
            '{"ok":true,"data":{"verified":false}}',
            '{"ok":true,"data":{"verified":"true"}}',
            '{"ok":true,"data":{"verified":1}}',
            '{"ok":true,"data":{"verified":null}}',
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then printf '%s\n' "$VERIFY_RESPONSE"; exit 0; fi
exit 64
""",
            )
            base_env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "x\n")
            payload["session_id"] = "strict-verify"
            for response in invalid_responses:
                with self.subTest(response=response):
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py",
                        payload,
                        cwd=repo,
                        env={**base_env, "VERIFY_RESPONSE": response},
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "verification")

            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={
                    **base_env,
                    "VERIFY_RESPONSE": '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"product":"codex","active_intents":["project-dev"],"verified":true}}',
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_pre_edit_intent_gate_verifies_every_canonical_target_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = root / "repo-a"
            repo_b = root / "repo-b"
            for repo in (repo_a, repo_b):
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
                (repo / "src").mkdir()
                (repo / "src" / "lib.rs").write_text("x\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            log_path = root / "verify.log"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then printf '%s\\n' 'agent-docs 1.21.17 (v1.21.17)'; exit 0; fi
if [[ "$*" == *"session --help"* ]]; then printf '%s\\n' 'status verify'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  printf '%s\\n' "$*" >> {shlex.quote(str(log_path))}
  if [[ "$*" == *"--project-path {repo_b.resolve()}"* ]]; then
    printf '%s\\n' '{{"ok":false,"error":{{"code":"required-intent-not-active"}}}}'
    exit 1
  fi
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"claude","active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
exit 64
""",
            )
            env = {
                "AGENT_RUNTIME_PRODUCT": "claude",
                "HOME": str(root / "home"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            (root / "home").mkdir()
            payloads = (
                (
                    write_payload(str(repo_b / "src" / "lib.rs"), "y\n"),
                    {str(repo_b.resolve())},
                ),
                (
                    write_payload("../repo-b/src/lib.rs", "y\n"),
                    {str(repo_b.resolve())},
                ),
                ({
                    "tool_name": "apply_patch",
                    "tool_input": {
                        "patch": "*** Update File: src/lib.rs\n*** Update File: ../repo-b/src/lib.rs\n"
                    },
                }, {str(repo_a.resolve()), str(repo_b.resolve())}),
            )
            for payload, expected_repos in payloads:
                with self.subTest(payload=payload):
                    log_path.unlink(missing_ok=True)
                    payload["session_id"] = "mixed-repos"
                    code, decision, stderr = run_hook(
                        "pre-edit-intent-gate.py", payload, cwd=repo_a, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "project-dev")
                    verified_repos = set()
                    for line in log_path.read_text(encoding="utf-8").splitlines():
                        words = shlex.split(line)
                        verified_repos.add(words[words.index("--project-path") + 1])
                    self.assertEqual(verified_repos, expected_repos)

            outside = root / "outside"
            outside.mkdir()
            payload = write_payload(str(repo_b / "src" / "lib.rs"), "y\n")
            payload["session_id"] = "outside-target"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py", payload, cwd=outside, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")


    def test_pre_edit_intent_gate_unusable_agent_docs_fails_closed(self) -> None:
        cases = {
            "crash": (
                "if [[ \"$*\" == *\"--version\"* ]]; then echo 'agent-docs 1.21.17'; exit 0; fi\nexit 70",
                "intent-not-active-or-stale",
            ),
            "legacy-text-nonzero": (
                "if [[ \"$*\" == *\"--version\"* ]]; then echo 'agent-docs 1.21.16'; exit 70; fi\nexit 64",
                "intent-not-active-or-stale",
            ),
            "malformed": (
                "echo 'unknown build'; exit 0",
                "intent-verification-malformed",
            ),
            "timeout": (
                "sleep 0.2\necho 'agent-docs 1.21.17'",
                "intent-verification-timeout",
            ),
            "untrusted-structured-error": (
                """if [[ "$*" == *"--version"* ]]; then echo 'agent-docs 1.21.17'; exit 0; fi
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
printf '%s\\n' '{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{"code":"sensitive-verification-code-that-must-not-leak"}}'
exit 65""",
                "sensitive-verification-code-that-must-not-leak",
            ),
        }
        for name, (body, verification_code) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
                bin_dir = repo / "bin"
                bin_dir.mkdir()
                self._write_fake_agent_docs(
                    bin_dir, f"#!/usr/bin/env bash\nset -euo pipefail\n{body}\n"
                )
                payload = write_payload("src/lib.rs", "x\n")
                payload["session_id"] = "unusable-agent-docs"
                code, decision, stderr = run_hook(
                    "pre-edit-intent-gate.py",
                    payload,
                    cwd=repo,
                    env={
                        "AGENT_RUNTIME_PRODUCT": "codex",
                        "AGENT_RUNTIME_AGENT_DOCS_TIMEOUT_SECONDS": "0.05",
                        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                    },
                )
                self.assertEqual(code, 0, stderr)
                self.assert_blocked(decision, "[reason: project-dev-required]")
                self.assertNotIn(verification_code, str(decision))


    def test_pre_edit_intent_gate_advisory_redacts_agent_docs_error_codes(self) -> None:
        verify_code = "sensitive-verification-code-that-must-not-leak"
        prepare_code = "sensitive-preparation-code-that-must-not-leak"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-docs 1.21.17'; exit 0; fi
if [[ "$*" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$*" == *"session verify"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{{"code":"{verify_code}"}}}}'
  exit 65
fi
if [[ "$*" == *"session prepare"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.prepare.v1","ok":false,"error":{{"code":"{prepare_code}"}}}}'
  exit 65
fi
exit 64
""",
            )
            payload = write_payload("src/lib.rs", "x\\n")
            payload["session_id"] = "advisory-redaction"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={
                    "AGENT_RUNTIME_PRODUCT": "codex",
                    "AGENT_RUNTIME_PROJECT_DEV_MODE": "advisory",
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, stderr)
            assert decision is not None
            self.assertNotEqual(decision.get("decision"), "block")
            reason = str(decision)
            self.assertIn("Project-dev advisory preparation was unavailable", reason)
            self.assertNotIn(verify_code, reason)
            self.assertNotIn(prepare_code, reason)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            git_bin = shutil.which("git")
            assert git_bin is not None
            (bin_dir / "git").symlink_to(git_bin)
            payload = write_payload("src/lib.rs", "x\n")
            payload["session_id"] = "missing-agent-docs"
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={"AGENT_RUNTIME_PRODUCT": "codex", "PATH": str(bin_dir)},
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "agent-docs capability is unavailable")


    def test_pre_edit_intent_gate_gates_real_notebook_path_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
if [[ "$*" == *"--version"* ]]; then echo 'agent-docs 1.21.17'; exit 0; fi
if [[ "$*" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
echo '{"ok":false,"error":{"code":"required-intent-not-active"}}'
exit 1
""",
            )
            payload = {
                "tool_name": "NotebookEdit",
                "session_id": "notebook-real-shape",
                "tool_input": {"notebook_path": "analysis.ipynb", "new_source": "1 + 1"},
            }
            code, decision, stderr = run_hook(
                "pre-edit-intent-gate.py",
                payload,
                cwd=repo,
                env={
                    "AGENT_RUNTIME_PRODUCT": "claude",
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "project-dev")


    def test_pre_edit_intent_gate_registration_matches_supported_products(self) -> None:
        for product, expected in (
            (
                "codex",
                {"Bash", "Write", "Edit", "NotebookEdit", "apply_patch"},
            ),
            (
                "claude",
                {"Bash", "Write", "Edit", "NotebookEdit", "MultiEdit"},
            ),
        ):
            gated = inventory_tools(
                inventory_rules(
                    product=product,
                    event="PreToolUse",
                    handler="pre-edit-intent-gate",
                )
            )
            self.assertEqual(gated, expected, product)

        hermes_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (REPO_ROOT / "targets" / "hermes").rglob("*")
            if path.is_file()
        )
        self.assertNotIn("pre-edit-intent-gate.py", hermes_sources)

