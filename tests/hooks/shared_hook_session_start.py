"""Shared hook tests: session start."""
from __future__ import annotations

from shared_hook_helpers import (
    HookTestCase,
    Path,
    json,
    os,
    run_shell_hook,
    subprocess,
    tempfile,
)


class SessionStartTests(HookTestCase):

    def test_session_start_healthcheck_evidence_stamp_is_machine_wide(self) -> None:
        # The evidence-archive lane is machine-wide: once per day across
        # repositories, and a session that is not opted in does not consume it.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            evidence = bin_dir / "evidence"
            evidence.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            evidence.chmod(0o755)
            home = root / "home"
            home.mkdir()
            base_env = {
                "HOME": str(home),
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
            for name in ("repo-a", "repo-b", "plain"):
                repo = root / name
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
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

            # A session that is not opted in stays silent and stamps nothing.
            self.assertEqual(context_in("repo-a", base_env), "")
            self.assertFalse((home / ".cache" / "agent-runtime-kit").exists())

            first = context_in("repo-b", opted_in_env)
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
            for name in ("evidence",):
                script = bin_dir / name
                script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
            return bin_dir

        def base_env(home: Path, cfg_home: Path, data_home: Path) -> dict[str, str]:
            return {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(cfg_home),
                "XDG_DATA_HOME": str(data_home),
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

