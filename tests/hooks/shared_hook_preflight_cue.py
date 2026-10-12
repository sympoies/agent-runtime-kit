"""Shared hook tests: preflight cue."""
from __future__ import annotations

from shared_hook_helpers import (
    HookTestCase,
    Path,
    gate_env,
    json,
    os,
    run_shell_hook,
    shlex,
    shutil,
    subprocess,
    tempfile,
)


class PreflightCueTests(HookTestCase):

    def test_preflight_cue_rejects_repo_local_agent_docs_without_execution(self) -> None:
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
printf '%s\n' '{{"intents":["project-dev"]}}'
""",
            )
            home = repo / "home"
            home.mkdir()
            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "repo-local-cue", "prompt": "hello"},
                cwd=repo,
                env={
                    "AGENT_RUNTIME_TRUSTED_CLI_ROOT": "",
                    "HOME": str(home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNone(decision)
            self.assertFalse(marker.exists())


    def test_preflight_cue_expands_only_active_intents_when_sessions_supported(
        self,
    ) -> None:
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
args="$*"
if [[ "$args" == *"session --help"* ]]; then
  printf '%s\n' '  status verify    show and verify active intents'
  exit 0
fi
if [[ "$args" == *"preflight --help"* ]]; then
  printf '%s\n' '      --require-declared-intent'
  printf '%s\n' '      --product <PRODUCT>'
  exit 0
fi
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\n' '{"intents":["project-dev","browser-test"]}'
  exit 0
fi
if [[ "$args" == *"session status"* ]]; then
  printf '%s\n' '{"schema_version":"cli.agent-docs.session.status.v1","ok":true,"data":{"active_intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\n' '{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{"active_intents":["project-dev"],"verified":true}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\n' '{"intent":"project-dev","documents":[{"path":"DEV.md","required":true,"scope":"project"}],"validation":{"declared":true,"commands":["bash scripts/ci/all.sh"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent browser-test"* ]]; then
  printf '%s\n' '{"intent":"browser-test","documents":[{"path":"BROWSER.md","required":true,"scope":"project"}],"validation":{"declared":false,"commands":[]}}'
  exit 0
fi
exit 64
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_SESSION_ID": "managed-selective-cue",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "provider-selective-cue", "prompt": "test the browser"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            output = decision.get("hookSpecificOutput")
            self.assertIsInstance(output, dict)
            assert isinstance(output, dict)
            context = str(output.get("additionalContext", ""))
            self.assertIn("DEV.md", context)
            self.assertIn("browser-test", context)
            self.assertNotIn("BROWSER.md", context)
            # P0-1 alignment: the durable-session cue recommends the atomic
            # `session prepare` primitive, not the older `session activate`.
            self.assertIn("session prepare", context)
            self.assertNotIn("session activate", context)
            self.assertIn("agent-docs --docs-home", context)
            self.assertIn(f"--docs-home {repo.resolve()}", context)
            self.assertIn(f"--project-path {repo.resolve()}", context)
            self.assertIn(f"--state-home {repo / 'state'}", context)
            self.assertIn("--session-id managed-selective-cue", context)
            self.assertIn("--intent <intent> --format json", context)
            # P0-2 bullet 6: ordinary durable-session cues do not expand the full
            # validation command list (the finish-line gate still enforces it).
            self.assertNotIn("scripts/ci/all.sh", context)
            self.assertNotIn("declared validation", context)


    def test_preflight_cue_emits_only_newly_active_docs(self) -> None:
        """P0-2 bullet 2: on a later activation, list only the newly-active
        intent's required docs, not the already-announced ones."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            phase = repo / "phase"
            phase.write_text("1", encoding="utf-8")
            # The fake toggles active intents by a test-controlled phase file:
            # phase 1 -> project-dev active; phase 2 -> project-dev + task-tools.
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
phase="$(cat {shlex.quote(str(phase))})"
if [[ "$args" == *"session --help"* ]]; then echo 'status verify prepare'; exit 0; fi
if [[ "$args" == *"preflight --help"* ]]; then echo '--require-declared-intent --product'; exit 0; fi
if [[ "$args" == *"list --format json"* ]]; then echo '{{"intents":["project-dev","task-tools"]}}'; exit 0; fi
active='["project-dev"]'
if [[ "$phase" == "2" ]]; then active='["project-dev","task-tools"]'; fi
if [[ "$args" == *"session status"* ]]; then echo '{{"schema_version":"cli.agent-docs.session.status.v1","ok":true,"data":{{"active_intents":'"$active"'}}}}'; exit 0; fi
if [[ "$args" == *"session verify"* ]]; then echo '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"active_intents":'"$active"',"verified":true}}}}'; exit 0; fi
if [[ "$args" == *"--intent project-dev"* ]]; then echo '{{"intent":"project-dev","documents":[{{"path":"DEV.md","required":true,"scope":"project"}}],"validation":{{"declared":false,"commands":[]}}}}'; exit 0; fi
if [[ "$args" == *"--intent task-tools"* ]]; then echo '{{"intent":"task-tools","documents":[{{"path":"EXT.md","required":true,"scope":"project"}}],"validation":{{"declared":false,"commands":[]}}}}'; exit 0; fi
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

            def cue_context() -> str:
                _code, decision, _stderr = run_shell_hook(
                    "user-prompt-agent-docs.sh",
                    {"session_id": "delta-cue", "prompt": "hello"},
                    cwd=repo,
                    env=env,
                )
                if not decision:
                    return ""
                out = decision.get("hookSpecificOutput", {})
                return str(out.get("additionalContext", "")) if isinstance(out, dict) else ""

            first = cue_context()
            self.assertIn("DEV.md", first)

            phase.write_text("2", encoding="utf-8")
            second = cue_context()
            # The newly-active intent's docs surface; the already-announced
            # project-dev docs are not re-listed.
            self.assertIn("EXT.md", second)
            self.assertIn("task-tools", second)
            self.assertNotIn("DEV.md", second)


    def test_preflight_cue_invalidates_cache_on_same_name_reactivation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            state_home = repo / "state"
            record = state_home / "agent-docs" / "sessions" / "record.json"
            record.parent.mkdir(parents=True)
            record.write_text('{"activated_at":"one"}\n', encoding="utf-8")
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$args" == *"preflight --help"* ]]; then echo '--require-declared-intent --product'; exit 0; fi
if [[ "$args" == *"list --format json"* ]]; then echo '{{"intents":["project-dev"]}}'; exit 0; fi
if [[ "$args" == *"session status"* ]]; then echo '{{"ok":true,"data":{{"active_intents":["project-dev"],"record_file":"agent-docs/sessions/record.json"}}}}'; exit 0; fi
if [[ "$args" == *"session verify"* ]]; then echo '{{"ok":true,"data":{{"active_intents":["project-dev"],"verified":true,"record_file":"agent-docs/sessions/record.json"}}}}'; exit 0; fi
if [[ "$args" == *"preflight"* ]]; then echo '{{"intent":"project-dev","project_path":"{repo.resolve()}","documents":[{{"path":"DEV.md","required":true,"scope":"project"}}],"validation":{{"declared":false,"commands":[]}}}}'; exit 0; fi
exit 64
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = {"session_id": "reactivation-cache", "prompt": "continue"}
            first = run_shell_hook("user-prompt-agent-docs.sh", payload, cwd=repo, env=env)
            second = run_shell_hook("user-prompt-agent-docs.sh", payload, cwd=repo, env=env)
            self.assertIsNotNone(first[1])
            self.assertIsNone(second[1])

            record.write_text('{"activated_at":"two"}\n', encoding="utf-8")
            third = run_shell_hook("user-prompt-agent-docs.sh", payload, cwd=repo, env=env)
            # P0-2 bullet 4: the record change still invalidates the per-fingerprint
            # stamp (the cache is re-evaluated), but a same-name reactivation with an
            # unchanged active-intent/document set no longer reproduces the cue — the
            # intent was already announced, so the delta is empty and nothing is
            # emitted. A genuinely new activation still emits (see
            # test_preflight_cue_emits_only_newly_active_docs).
            self.assertIsNone(third[1])


    def test_preflight_cue_invalidates_no_active_cache_on_catalog_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
            catalog = repo / "catalog.json"
            catalog.write_text('{"intents":["project-dev"]}\n', encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$args" == *"preflight --help"* ]]; then echo '--require-declared-intent --product'; exit 0; fi
if [[ "$args" == *"list --format json"* ]]; then cat {shlex.quote(str(catalog))}; exit 0; fi
if [[ "$args" == *"session status"* ]]; then echo '{{"ok":true,"data":{{"active_intents":[]}}}}'; exit 0; fi
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
            payload = {"session_id": "no-active-cache", "prompt": "continue"}
            first = run_shell_hook("user-prompt-agent-docs.sh", payload, cwd=repo, env=env)
            second = run_shell_hook("user-prompt-agent-docs.sh", payload, cwd=repo, env=env)
            self.assertIsNotNone(first[1])
            self.assertIsNone(second[1])

            catalog.write_text(
                '{"intents":["browser-test","project-dev"]}\n', encoding="utf-8"
            )
            third = run_shell_hook("user-prompt-agent-docs.sh", payload, cwd=repo, env=env)
            self.assertIsNotNone(third[1])
            context = str((third[1] or {}).get("hookSpecificOutput", {}).get("additionalContext", ""))
            self.assertIn("browser-test", context)


    def test_preflight_cue_surfaces_stale_activation_instead_of_cached_docs(self) -> None:
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
args="$*"
if [[ "$args" == *"session --help"* ]]; then echo 'status verify'; exit 0; fi
if [[ "$args" == *"preflight --help"* ]]; then echo '--require-declared-intent --product'; exit 0; fi
if [[ "$args" == *"list --format json"* ]]; then echo '{"intents":["project-dev"]}'; exit 0; fi
if [[ "$args" == *"session status"* ]]; then echo '{"ok":true,"data":{"active_intents":["project-dev"],"record_file":"record.json"}}'; exit 0; fi
if [[ "$args" == *"session verify"* ]]; then echo '{"ok":false,"error":{"code":"catalog-drift"}}'; exit 1; fi
if [[ "$args" == *"preflight"* ]]; then echo '{"intent":"project-dev","documents":[{"path":"STALE.md","required":true}],"validation":{"declared":false,"commands":[]}}'; exit 0; fi
exit 64
""",
            )
            home = repo / "home"
            home.mkdir()
            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "stale-cue", "prompt": "continue"},
                cwd=repo,
                env={
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "AGENT_RUNTIME_PRODUCT": "codex",
                    "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                    "HOME": str(home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            context = str((decision or {}).get("hookSpecificOutput", {}).get("additionalContext", ""))
            self.assertIn("stale", context.lower())
            self.assertIn("prepare", context)
            self.assertNotIn("STALE.md", context)


    def test_preflight_cue_covers_every_declared_intent(self) -> None:
        self._require_agent_docs()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected_repo = repo.resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "DEV.md").write_text("# Dev\n", encoding="utf-8")
            (repo / "core" / "policies").mkdir(parents=True)
            (repo / "core" / "policies" / "ext.md").write_text(
                "# Ext\n", encoding="utf-8"
            )
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n\n'
                '[[document]]\ncontext = "task-tools"\nscope = "project"\n'
                'path = "core/policies/ext.md"\nrequired = true\nwhen = "always"\n\n'
                '[[validation]]\ncontext = "project-dev"\n'
                'commands = ["bash scripts/ci/all.sh"]\n'
                'marker = ".cache/agent-validation/project-dev.ok"\n',
                encoding="utf-8",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
            }

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            hook_output = decision.get("hookSpecificOutput", {})
            ctx = ""
            if isinstance(hook_output, dict):
                ctx = str(hook_output.get("additionalContext", ""))
            # Every declared intent is routed, but nothing is active yet, so no
            # runbook or validation command is injected.
            self.assertIn("Inactive available intents: project-dev, task-tools.", ctx)
            self.assertIn("session prepare --session-id cue-test", ctx)
            self.assertNotIn("DEV.md", ctx)
            self.assertNotIn("ext.md", ctx)
            self.assertNotIn("scripts/ci/all.sh", ctx)


    def test_preflight_cue_qualifies_required_docs_with_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            docs_home = repo / "runtime-kit"
            project = repo / "project"
            project.mkdir(parents=True)
            docs_home.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=project, check=True)
            (project / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "DEV.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (project / "DEV.md").write_text("# Dev\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"session status"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"active_intents":["project-dev"]}}}}'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' '{{"intent":"project-dev","docs_home":{json.dumps(str(docs_home))},"project_path":{json.dumps(str(project))},"documents":[{{"path":{json.dumps(str(docs_home / "core" / "policies" / "work-modes.md"))},"required":true,"scope":"home","source":"project"}},{{"path":{json.dumps(str(project / "DEV.md"))},"required":true,"scope":"project","source":"project"}}],"validation":{{"declared":true,"commands":[]}}}}'
  exit 0
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(docs_home),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-doc-roots-test", "prompt": "hello"},
                cwd=project,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            hook_output = decision.get("hookSpecificOutput", {})
            ctx = ""
            if isinstance(hook_output, dict):
                ctx = str(hook_output.get("additionalContext", ""))
            self.assertIn(f"Doc roots: home={docs_home}, project={project}.", ctx)
            self.assertIn("home:core/policies/work-modes.md", ctx)
            self.assertIn("project:DEV.md", ctx)
            self.assertNotIn(str(docs_home / "core" / "policies" / "work-modes.md"), ctx)


    def test_preflight_cue_forwards_agent_docs_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "AGENT_DOCS.toml").write_text(
                '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                'path = "CODEX.md"\nrequired = true\nwhen = "always"\n',
                encoding="utf-8",
            )
            (repo / "CODEX.md").write_text("# Codex\n", encoding="utf-8")
            (repo / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
            bin_dir = repo / "bin"
            bin_dir.mkdir()
            log_path = repo / "agent-docs.args"
            self._write_fake_agent_docs(
                bin_dir,
                f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
printf '%s\\n' "$args" >> {shlex.quote(str(log_path))}
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"session status"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"active_intents":["project-dev"]}}}}'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"active_intents":["project-dev"],"verified":true}}}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  if [[ "$args" == *"--product codex"* ]]; then
    printf '%s\\n' '{{"intent":"project-dev","documents":[{{"path":"CODEX.md","required":true}}],"validation":{{"declared":true,"commands":["bash codex.sh"]}}}}'
    exit 0
  fi
  if [[ "$args" == *"--product claude"* ]]; then
    printf '%s\\n' '{{"intent":"project-dev","documents":[{{"path":"CLAUDE.md","required":true}}],"validation":{{"declared":true,"commands":["bash claude.sh"]}}}}'
    exit 0
  fi
  printf '%s\\n' '{{"intent":"project-dev","documents":[{{"path":"CODEX.md","required":true}},{{"path":"CLAUDE.md","required":true}}],"validation":{{"declared":true,"commands":["bash unfiltered.sh"]}}}}'
  exit 0
fi
exit 65
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

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-product-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            hook_output = decision.get("hookSpecificOutput", {})
            ctx = ""
            if isinstance(hook_output, dict):
                ctx = str(hook_output.get("additionalContext", ""))
            self.assertIn("CODEX.md", ctx)
            self.assertNotIn("CLAUDE.md", ctx)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            preflights = [call for call in calls if " preflight " in f" {call} "]
            self.assertTrue(preflights)
            for call in preflights:
                self.assertIn("--require-declared-intent --product codex", call)
            # The supported floor ships these flags and the session surface, so
            # the prompt hook no longer spends a `--help` probe on every prompt.
            self.assertFalse([call for call in calls if "--help" in call])


    def test_preflight_cue_defaults_docs_home_to_runtime_kit_source_root(self) -> None:
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
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' '{{"intent":"project-dev","documents":[{{"path":"DEV.md","required":true}}],"validation":{{"declared":true,"commands":["bash scripts/ci/all.sh"]}}}}'
  exit 0
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-default-docs-home-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            self.assertIn(
                f"--docs-home {expected_repo}", log_path.read_text(encoding="utf-8")
            )


    def test_preflight_cue_uses_agent_docs_home_fallback(self) -> None:
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
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' '{{"intent":"project-dev","documents":[{{"path":"DEV.md","required":true}}],"validation":{{"declared":true,"commands":["bash scripts/ci/all.sh"]}}}}'
  exit 0
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

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-docs-home-fallback-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            self.assertIn(
                f"--docs-home {expected_docs_home}",
                log_path.read_text(encoding="utf-8"),
            )


    def test_preflight_cue_does_not_default_project_catalog_to_docs_home(self) -> None:
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
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\\n' '{{"intents":["project-dev"]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  printf '%s\\n' '{{"intent":"project-dev","documents":[{{"path":"DEV.md","required":true}}],"validation":{{"declared":true,"commands":["bash scripts/ci/all.sh"]}}}}'
  exit 0
fi
exit 65
""",
            )
            home = repo / "home"
            home.mkdir()
            env = {
                "AGENT_DOCS_HOME": "",
                "AGENT_RUNTIME_DOCS_HOME": "",
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(repo / "state"),
                "HOME": str(home),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-project-catalog-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            self.assertNotIn(
                f"--docs-home {expected_repo}", log_path.read_text(encoding="utf-8")
            )


    def test_preflight_cue_fails_closed_for_undeclared_active_intent(self) -> None:
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
            self._write_fake_agent_docs(
                bin_dir,
                """#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"list --format json"* ]]; then
  printf '%s\n' '{"intents":["project-dev","project_dev"]}'
  exit 0
fi
if [[ "$args" == *"session status"* ]]; then
  printf '%s\n' '{"ok":true,"data":{"active_intents":["project-dev","project_dev"]}}'
  exit 0
fi
if [[ "$args" == *"session verify"* ]]; then
  printf '%s\n' '{"ok":true,"data":{"active_intents":["project-dev","project_dev"],"verified":true}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project-dev"* ]]; then
  if [[ "$args" != *"--require-declared-intent"* ]]; then
    echo "missing declared-intent guard" >&2
    exit 64
  fi
  printf '%s\n' '{"intent":"project-dev","documents":[{"path":"DEV.md","required":true}],"validation":{"declared":false,"commands":[]}}'
  exit 0
fi
if [[ "$args" == *"preflight"* && "$args" == *"--intent project_dev"* ]]; then
  if [[ "$args" != *"--require-declared-intent"* ]]; then
    echo "missing declared-intent guard" >&2
    exit 64
  fi
  echo '{"ok":false,"error":{"code":"undeclared-intent"}}' >&2
  exit 65
fi
exit 65
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

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-guard-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertNotEqual(code, 0)
            self.assertIsNone(decision)
            self.assertIn("project_dev", stderr)


    def test_preflight_cue_is_silent_without_runtime_product(self) -> None:
        """Without a codex/claude product there is no session context to cue.

        agent-hook always exports AGENT_RUNTIME_PRODUCT, so an unset or foreign
        product exits quietly before spending any agent-docs call.
        """
        for product in (None, "hermes"):
            with self.subTest(product=product), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                (repo / "AGENT_DOCS.toml").write_text("# fixture\n", encoding="utf-8")
                bin_dir = repo / "bin"
                bin_dir.mkdir()
                log_path = repo / "agent-docs.args"
                self._write_fake_agent_docs(
                    bin_dir,
                    f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> {shlex.quote(str(log_path))}
printf '%s\\n' '{{"intents":["project-dev"]}}'
""",
                )
                home = repo / "home"
                home.mkdir()
                env = {
                    "AGENT_RUNTIME_DOCS_HOME": str(repo),
                    "HOME": str(home),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                }
                if product is not None:
                    env["AGENT_RUNTIME_PRODUCT"] = product

                code, decision, stderr = run_shell_hook(
                    "user-prompt-agent-docs.sh",
                    {"session_id": "cue-no-product", "prompt": "hello"},
                    cwd=repo,
                    env=env,
                )
                self.assertEqual(code, 0, stderr)
                self.assertIsNone(decision)
                self.assertFalse(log_path.exists())


    def test_preflight_cue_lists_all_required_docs(self) -> None:
        self._require_agent_docs()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected_repo = repo.resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            docs = repo / "docs"
            docs.mkdir()
            entries: list[str] = []
            for index in range(1, 8):
                path = docs / f"doc-{index}.md"
                path.write_text(f"# Doc {index}\n", encoding="utf-8")
                entries.append(
                    '[[document]]\ncontext = "project-dev"\nscope = "project"\n'
                    f'path = "docs/doc-{index}.md"\n'
                    'required = true\nwhen = "always"\n'
                )
            (repo / "AGENT_DOCS.toml").write_text("\n".join(entries), encoding="utf-8")
            home = repo / "home"
            home.mkdir()
            state_home = repo / "state"
            env = {
                "AGENT_RUNTIME_DOCS_HOME": str(repo),
                "AGENT_RUNTIME_PRODUCT": "codex",
                "CODEX_AGENT_STATE_HOME": str(state_home),
                "HOME": str(home),
            }
            agent_docs = shutil.which("agent-docs")
            assert agent_docs is not None
            subprocess.run(
                [
                    agent_docs,
                    "--docs-home",
                    str(repo),
                    "--project-path",
                    str(repo),
                    "session",
                    "prepare",
                    "--session-id",
                    "cue-overflow-test",
                    "--product",
                    "codex",
                    "--state-home",
                    str(state_home),
                    "--intent",
                    "project-dev",
                    "--format",
                    "json",
                ],
                cwd=repo,
                env=gate_env({"HOME": str(home)}),
                capture_output=True,
                text=True,
                check=True,
            )

            code, decision, stderr = run_shell_hook(
                "user-prompt-agent-docs.sh",
                {"session_id": "cue-overflow-test", "prompt": "hello"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            hook_output = decision.get("hookSpecificOutput", {})
            ctx = ""
            if isinstance(hook_output, dict):
                ctx = str(hook_output.get("additionalContext", ""))
            self.assertIn("doc-1.md", ctx)
            self.assertIn("doc-6.md", ctx)
            self.assertIn("doc-7.md", ctx)
            self.assertNotIn("+1 more", ctx)

