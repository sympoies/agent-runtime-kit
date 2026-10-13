"""Shared hook tests: session start."""
from __future__ import annotations

from shared_hook_helpers import (
    HookTestCase,
    Path,
    json,
    os,
    run_shell_hook,
    shlex,
    subprocess,
    tempfile,
)


class SessionStartTests(HookTestCase):

    def test_session_start_healthcheck_defaults_docs_home_to_runtime_kit_source_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected_repo = repo.resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (repo / "DEV.md").write_text("# Dev\n", encoding="utf-8")
            self._mark_runtime_kit_source_checkout(repo)
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            log_path = repo / "agent-docs.args"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
printf '%s\\n' "$args" >> {shlex.quote(str(log_path))}
if [[ "$args" != *"--docs-home {expected_repo}"* ]]; then
  echo "missing repo-root docs-home" >&2
  exit 64
fi
if [[ "$args" != *"--project-path {expected_repo}"* ]]; then
  echo "missing project path" >&2
  exit 64
fi
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' 'ok'
  exit 0
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "session-start-healthcheck.sh",
                {"hook_event_name": "SessionStart"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNone(decision)
            log = log_path.read_text(encoding="utf-8")
            self.assertIn(f"--docs-home {expected_repo}", log)
            self.assertIn(f"--project-path {expected_repo}", log)


    def test_session_start_healthcheck_uses_agent_docs_home_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (repo / "DEV.md").write_text("# Dev\n", encoding="utf-8")
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
            expected_repo = repo.resolve()
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
if [[ "$args" != *"--project-path {expected_repo}"* ]]; then
  echo "missing project path" >&2
  exit 64
fi
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' 'ok'
  exit 0
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": str(docs_home_link),
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "session-start-healthcheck.sh",
                {"hook_event_name": "SessionStart"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNone(decision)
            log = log_path.read_text(encoding="utf-8")
            self.assertIn(f"--docs-home {expected_docs_home}", log)
            self.assertIn(f"--project-path {expected_repo}", log)


    def test_session_start_healthcheck_does_not_default_project_catalog_to_docs_home(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected_repo = repo.resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (repo / "DEV.md").write_text("# Dev\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            log_path = repo / "agent-docs.args"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
printf '%s\\n' "$args" >> {shlex.quote(str(log_path))}
if [[ "$args" == *"--docs-home {expected_repo}"* ]]; then
  echo "repo-local catalog must not replace inherited docs-home" >&2
  exit 64
fi
if [[ "$args" != *"--project-path {expected_repo}"* ]]; then
  echo "missing project path" >&2
  exit 64
fi
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' 'ok'
  exit 0
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "session-start-healthcheck.sh",
                {"hook_event_name": "SessionStart"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNone(decision)
            log = log_path.read_text(encoding="utf-8")
            self.assertNotIn(f"--docs-home {expected_repo}", log)
            self.assertIn(f"--project-path {expected_repo}", log)


    def test_session_start_healthcheck_blocks_when_agent_docs_list_fails(self) -> None:
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
if [[ "$args" == *"list --format json"* ]]; then
  echo "catalog parse failed" >&2
  exit 65
fi
printf '%s\\n' 'unexpected agent-docs invocation' >&2
exit 66
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "session-start-healthcheck.sh",
                {"hook_event_name": "SessionStart"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            context = decision.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("agent-docs list failed", str(context))


    def test_session_start_healthcheck_blocks_when_preflight_fails(self) -> None:
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
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{"intents":["project-dev","task-tools"]}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  [[ "$args" == *"--strict"* ]] || exit 64
  printf '%s\\n' 'project-dev ok'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent task-tools"* ]]; then
  [[ "$args" == *"--strict"* ]] || exit 64
  printf '%s\\n' 'task-tools missing docs'
  exit 65
fi
printf '%s\\n' 'unexpected agent-docs invocation' >&2
exit 66
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "session-start-healthcheck.sh",
                {"hook_event_name": "SessionStart"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            context = decision.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("intent task-tools", str(context))
            self.assertIn("task-tools missing docs", str(context))


    def test_session_start_healthcheck_daily_stamp_is_per_repository(self) -> None:
        # The first session of the day in a repository without a catalog must
        # not consume the agent-docs check for every other repository.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{"intents":["project-dev"]}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' 'project-dev missing docs'
  exit 65
fi
exit 66
""",
            )
            home = root / "home"
            home.mkdir()
            env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            repos: dict[str, Path] = {}
            for name in ("plain", "catalog-a", "catalog-b"):
                repo = root / name
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                if name != "plain":
                    (repo / "AGENT_DOCS.toml").write_text(
                        '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                        'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                        encoding="utf-8",
                    )
                repos[name] = repo

            def context_in(name: str) -> str:
                code, decision, stderr = run_shell_hook(
                    "session-start-healthcheck.sh",
                    {"hook_event_name": "SessionStart"},
                    cwd=repos[name],
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                if decision is None:
                    return ""
                return str(
                    decision.get("hookSpecificOutput", {}).get("additionalContext", "")
                )

            self.assertEqual(context_in("plain"), "")
            self.assertIn("project-dev missing docs", context_in("catalog-a"))
            # The nudge stays once per day for the same repository.
            self.assertEqual(context_in("catalog-a"), "")
            self.assertIn("project-dev missing docs", context_in("catalog-b"))


    def test_session_start_healthcheck_evidence_stamp_is_machine_wide(self) -> None:
        # The evidence-archive lane is machine-wide: once per day across
        # repositories, and a docs-only session must not consume its stamp.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{"intents":["project-dev"]}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' 'ok'
  exit 0
fi
exit 66
""",
            )
            evidence = bin_dir / "evidence"
            evidence.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            evidence.chmod(0o755)
            home = root / "home"
            home.mkdir()
            base_env = {
                "HOME": str(home),
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            opted_in_env = {
                **base_env,
                "AGENT_EVIDENCE_ARCHIVE_HOME": str(root / "missing-archive"),
            }
            repos: dict[str, Path] = {}
            for name in ("catalog-a", "catalog-b", "plain"):
                repo = root / name
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                if name != "plain":
                    (repo / "AGENT_DOCS.toml").write_text(
                        '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                        'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                        encoding="utf-8",
                    )
                repos[name] = repo

            def context_in(name: str, env: dict[str, str]) -> str:
                code, decision, stderr = run_shell_hook(
                    "session-start-healthcheck.sh",
                    {"hook_event_name": "SessionStart"},
                    cwd=repos[name],
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                if decision is None:
                    return ""
                return str(
                    decision.get("hookSpecificOutput", {}).get("additionalContext", "")
                )

            # A docs-lane-only session (not opted in) runs and stamps only docs.
            self.assertEqual(context_in("catalog-a", base_env), "")
            stamps = sorted(
                path.name for path in (home / ".cache" / "agent-runtime-kit").iterdir()
            )
            self.assertEqual(len(stamps), 1, stamps)
            self.assertIn("-docs-", stamps[0])

            first = context_in("catalog-b", opted_in_env)
            self.assertIn("evidence-archive", first)
            self.assertIn("archive clone not found", first)
            # Suppressed for the rest of the day, in any other repository.
            self.assertNotIn("evidence-archive", context_in("plain", opted_in_env))


    def test_session_start_healthcheck_evidence_archive_optin(self) -> None:
        # The SessionStart healthcheck must validate evidence-archive wiring only
        # when the user has opted in (env / local config / a default clone with
        # commits), and stay completely silent otherwise so non-users are not
        # nagged. CLI-side behavior is out of scope; this is kit-owned.
        valid_hosts = (
            "schema: agent-evidence-archive.hosts.v1\n"
            "version: 1\n"
            "hosts:\n"
            "  github.com:\n"
            "    class: personal\n"
            "    primary_identity: tester\n"
        )

        def local_config(archive_path: Path, *, quoted: bool = False) -> str:
            archive_value = json.dumps(str(archive_path)) if quoted else str(archive_path)
            return (
                "version: 1\n"
                f"archive_clone_path: {archive_value}\n"
                "working_repo_roots: []\n"
                "performance:\n"
                "  migrate_batch_size: 50\n"
            )

        def stub_bin(root: Path) -> Path:
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name in ("agent-docs", "evidence"):
                script = bin_dir / name
                script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
            return bin_dir

        def base_env(home: Path, cfg_home: Path, data_home: Path) -> dict[str, str]:
            return {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(cfg_home),
                "XDG_DATA_HOME": str(data_home),
                # Keep the agent-docs half quiet/deterministic in the sandbox;
                # the evidence assertions below tolerate any agent-docs noise.
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                # Default to NOT opted in via env; cases opt in explicitly.
                "AGENT_EVIDENCE_ARCHIVE_HOME": "",
            }

        def context_of(out: dict[str, object] | None) -> str:
            if out is None:
                return ""
            return out["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]

        payload = {"hook_event_name": "SessionStart"}

        # Case A: opted in via local config, but the archive clone is missing.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(root / "missing-archive"), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env=base_env(home, cfg_home, data_home),
            )
            self.assertEqual(code, 0, err)
            self.assertIsNotNone(out, f"expected JSON output; stderr={err}")
            self.assertIn("evidence-archive", context_of(out))

        # Case B: not opted in at all -> evidence-archive stays silent.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            cfg_home.mkdir()
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env=base_env(home, cfg_home, data_home),
            )
            self.assertEqual(code, 0, err)
            self.assertNotIn("evidence-archive", context_of(out))

        # Case C: opted in via config AND wiring is healthy -> stays silent.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            archive = root / "archive"
            (archive / "config").mkdir(parents=True)
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            subprocess.run(["git", "init", "-q"], cwd=archive, check=True)
            subprocess.run(["git", "add", "-A"], cwd=archive, check=True)
            subprocess.run(
                ["git", "-c", "user.email=t@example.com", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "seed"],
                cwd=archive, check=True,
            )
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertNotIn("evidence-archive", context_of(out))

        # Case D: quoted archive_clone_path is valid YAML and should resolve.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            archive = root / "archive"
            (archive / "config").mkdir(parents=True)
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            subprocess.run(["git", "init", "-q"], cwd=archive, check=True)
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive, quoted=True), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertNotIn("evidence-archive", context_of(out))

        # Case E: archive clones may be Git worktrees, where .git is a file
        # pointing at a real gitdir. A GENUINE linked worktree (created by
        # `git worktree add`, so Git can resolve it) is a healthy archive and
        # must stay silent.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.email=t@example.com", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "seed", "--allow-empty"],
                cwd=repo, check=True,
            )
            archive = root / "archive"
            # A real linked worktree: `archive/.git` is a file whose gitdir
            # target is a valid worktree admin directory Git can resolve.
            subprocess.run(
                ["git", "-c", "commit.gpgsign=false", "worktree", "add", "-q", str(archive)],
                cwd=repo, check=True,
            )
            (archive / "config").mkdir(parents=True)
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertNotIn("evidence-archive", context_of(out))

        # Case F: a stale / invalid worktree leaves a .git file behind whose
        # `gitdir:` target no longer exists. A bare existence check would treat
        # the archive as present and suppress the warning even though Git
        # operations will fail; the healthcheck must instead flag it as missing.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            archive = root / "archive"
            (archive / "config").mkdir(parents=True)
            # The gitdir target is absent -> a stale / invalid worktree pointer.
            (archive / ".git").write_text(
                "gitdir: ../repo/.git/worktrees/archive\n", encoding="utf-8"
            )
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertIn("evidence-archive", context_of(out))

        # Case G: opt-in is established ONLY by a default-location clone (no env,
        # no local config), and that clone is stale (its `.git` gitfile points at
        # a gone gitdir). Opt-in detection must be separate from metadata
        # validity: the bare `.git` marker still means the user opted in, so the
        # stale archive must be SURFACED, not silently skipped as "not opted in".
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            cfg_home.mkdir()
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            # The XDG-default clone location, opted in by a stale .git gitfile.
            default_archive = data_home / "agent-evidence-archive"
            default_archive.mkdir(parents=True)
            (default_archive / ".git").write_text(
                "gitdir: ../repo/.git/worktrees/archive\n", encoding="utf-8"
            )
            bin_dir = stub_bin(root)
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertIn("evidence-archive", context_of(out))

        # Case H: a .git gitfile whose `gitdir:` target path EXISTS but is not a
        # real Git directory (an empty directory). The path resolves, yet
        # `git -C <archive> …` still fails with "not a git repository"; the
        # healthcheck must require a resolvable repo, not just any existing path,
        # and flag it.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            archive = root / "archive"
            (archive / "config").mkdir(parents=True)
            # The gitdir target EXISTS but is an empty dir -> not a real gitdir.
            (root / "repo" / ".git" / "worktrees" / "archive").mkdir(parents=True)
            (archive / ".git").write_text(
                "gitdir: ../repo/.git/worktrees/archive\n", encoding="utf-8"
            )
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertIn("evidence-archive", context_of(out))

        # Case I: the archive path is a SUBDIRECTORY of an enclosing Git checkout
        # (not a standalone clone). `git -C <archive> rev-parse` would resolve the
        # OUTER repo and pass, but the evidence archive must be its own repo, so
        # the healthcheck must require the resolved top level to be the archive
        # itself and flag this.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            outer = root / "outer"
            outer.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=outer, check=True)
            archive = outer / "sub"
            (archive / "config").mkdir(parents=True)
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, err)
            self.assertIn("evidence-archive", context_of(out))

        # Case J: a non-repo archive directory, but the session inherits an
        # exported GIT_DIR pointing at some OTHER repo. Unscrubbed, `git -C
        # <archive> rev-parse` would validate that other repo and pass; the
        # healthcheck must scrub Git's repo-selection env so the probe really
        # targets the archive, and flag the non-repo archive.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            cfg_home = root / "config"
            data_home = root / "data"
            data_home.mkdir()
            work = root / "work"
            work.mkdir()
            other_repo = root / "other-repo"
            other_repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=other_repo, check=True)
            archive = root / "archive"  # a plain directory, NOT a git repo
            (archive / "config").mkdir(parents=True)
            (archive / "config" / "hosts.yaml").write_text(valid_hosts, encoding="utf-8")
            bin_dir = stub_bin(root)
            cfg_dir = cfg_home / "agent-evidence-archive"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(
                local_config(archive), encoding="utf-8"
            )
            code, out, err = run_shell_hook(
                "session-start-healthcheck.sh", payload, cwd=work,
                env={
                    **base_env(home, cfg_home, data_home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                    "GIT_DIR": str(other_repo / ".git"),
                },
            )
            self.assertEqual(code, 0, err)
            self.assertIn("evidence-archive", context_of(out))

