"""Shared hook tests: session coordination."""
from __future__ import annotations

from shared_hook_helpers import (
    Any,
    HOOK_DIR,
    HookTestCase,
    Path,
    command_payload,
    hashlib,
    importlib,
    inventory_rules,
    inventory_tools,
    json,
    mock,
    os,
    re,
    run_enforced_hook,
    run_hook,
    secrets,
    shlex,
    shutil,
    subprocess,
    tempfile,
    time,
    unittest,
    write_payload,
)


class SessionCoordinationTests(HookTestCase):

    def test_session_coordination_guard_requires_claim_for_managed_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://example.invalid/example/repo.git"],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.24.5'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\n' '{"schema_version":"cli.agent-session.work-context-show.v1","ok":false,"error":{"code":"claim-not-found","message":"private /home/canary capability secret"}}'
  exit 1
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "capability"
            capability.write_text("private-capability\n", encoding="utf-8")
            capability.chmod(0o600)
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_SESSION_ID": "managed-private-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload["session_id"] = "product-private-session"
            payload["tool_use_id"] = "tool-private-id"
            payload["hook_event_name"] = "PreToolUse"
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "active work-context claim")
            reason = str(decision)
            for private in (
                str(repo),
                str(capability),
                "managed-private-session",
                "product-private-session",
                "private-capability",
                "/home/canary",
            ):
                self.assertNotIn(private, reason)


    def test_session_coordination_default_is_advisory_and_never_blocks_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            (repo / "src").mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://example.invalid/example/repo.git"],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {shlex.quote(str(call_log))}
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.25.2'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'status set clear advise acknowledge show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context advise"* ]]; then
  case "${{COORD_SCENARIO:-warning}}" in
    warning) printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.work-context-advisory.v1","managed":true,"mode":"advisory","available":true,"severity":"warning","suppressed":false,"reasons":[{{"code":"same-worktree","peer_session_id":"peer-private","repository":"example/repo"}}],"peers":[]}}}}' ;;
    mixed) printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.work-context-advisory.v1","managed":true,"mode":"advisory","available":false,"severity":"warning","suppressed":false,"reasons":[{{"code":"same-worktree","peer_session_id":"peer-private","repository":"example/repo"}}],"peers":[]}}}}' ;;
    suppressed) printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.work-context-advisory.v1","managed":true,"mode":"advisory","available":true,"severity":"warning","suppressed":true,"reasons":[{{"code":"same-worktree","peer_session_id":"peer-private","repository":"example/repo"}}],"peers":[]}}}}' ;;
    unavailable) printf '%s\\n' '{{"ok":false,"error":{{"code":"coordination-store-unavailable","message":"private /home/canary capability"}}}}'; exit 1 ;;
  esac
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "capability"
            capability.write_text("private-capability\n", encoding="utf-8")
            capability.chmod(0o600)
            base_env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_SESSION_COORDINATION_MODE": "",
                "AGENT_SESSION_ID": "managed-private-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload.update(
                {
                    "session_id": "product-private-session",
                    "tool_use_id": "advisory-tool",
                    "hook_event_name": "PreToolUse",
                }
            )

            # Read-only pipelines and unknown shell effects are not recognized
            # mutations, so advisory mode stays silent and does not query peer
            # overlap. Enforce mode retains its separate fail-closed path.
            call_log.write_text("", encoding="utf-8")
            for command in (
                "rg --no-config TODO . | head -n 5",
                "nl -ba README.md | sed -n '1,5p'",
                "python3 -c 'print(1)'",
                "git push --dry-run origin HEAD:topic",
                "git branch --list",
                "git branch --list topic",
                "git tag --list",
                "gh release view v1",
            ):
                with self.subTest(advisory_non_mutation=command):
                    inspection = command_payload(command)
                    inspection.update(
                        {
                            "session_id": "product-private-session",
                            "tool_use_id": "advisory-non-mutation",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_hook(
                        "session-coordination-guard.py",
                        inspection,
                        cwd=repo,
                        env=base_env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)
                    self.assertEqual(call_log.read_text(encoding="utf-8"), "")

            # Positively recognized shell and provider mutations still consult
            # advisory overlap. These commands are inspected by the hook only;
            # the test never executes the payload command itself.
            for command in (
                "echo changed > src/out.txt",
                "cat README.md | tee src/out.txt",
                "forge-cli issue close 1",
                "git push origin HEAD:topic",
                "git branch topic",
                "git branch --set-upstream-to=origin/main",
                "git tag v1",
                "gh release create v1",
                "gh release upload v1 artifact.tgz",
                "gh api -X POST /repos/example/repo/dispatches",
            ):
                with self.subTest(advisory_mutation=command):
                    mutation = command_payload(command)
                    mutation.update(
                        {
                            "session_id": "product-private-session",
                            "tool_use_id": "advisory-mutation",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_hook(
                        "session-coordination-guard.py",
                        mutation,
                        cwd=repo,
                        env=dict(base_env, COORD_SCENARIO="warning"),
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNotNone(decision)
                    self.assertIn("possible overlap", str(decision).lower())

            for scenario, warning in (
                ("warning", "possible overlap"),
                ("mixed", "possible overlap"),
                ("unavailable", "coordination is unavailable"),
            ):
                with self.subTest(scenario=scenario):
                    code, decision, stderr = run_hook(
                        "session-coordination-guard.py",
                        payload,
                        cwd=repo,
                        env=dict(base_env, COORD_SCENARIO=scenario),
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assertIsNotNone(decision)
                    assert decision is not None
                    self.assertNotEqual(decision.get("decision"), "block")
                    self.assertIn(warning, str(decision).lower())
                    for private in (
                        str(repo),
                        str(capability),
                        "managed-private-session",
                        "product-private-session",
                        "peer-private",
                        "private-capability",
                        "/home/canary",
                    ):
                        self.assertNotIn(private, str(decision))

            code, decision, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=dict(
                    base_env,
                    AGENT_SESSION_COORDINATION_MODE="unexpected-value",
                    COORD_SCENARIO="warning",
                ),
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertNotEqual(decision.get("decision"), "block")
            self.assertIn("possible overlap", str(decision).lower())

            code, decision, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=dict(base_env, COORD_SCENARIO="suppressed"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            calls_before_off = call_log.read_text(encoding="utf-8")
            code, decision, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=dict(base_env, AGENT_SESSION_COORDINATION_MODE="off"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(call_log.read_text(encoding="utf-8"), calls_before_off)


    def test_session_coordination_advisory_private_file_failures_are_best_effort(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_advisory_cleanup_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "advisory-targets.json"
            with mock.patch.object(guard.os, "fdopen", side_effect=OSError("write failed")):
                self.assertFalse(guard.write_private(target, "private checkout path\n"))
            self.assertFalse(target.exists())
            residue = Path(tmp) / "residue"
            residue.write_text("private checkout path\n", encoding="utf-8")
            with mock.patch.object(guard.Path, "unlink", side_effect=OSError("busy")):
                guard.best_effort_unlink(residue)


    def test_session_coordination_advisory_multi_edit_resolves_checkout_once(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_advisory_subprocesses_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "src").mkdir(parents=True)
            payload = {
                "cwd": str(repo),
                "tool_name": "MultiEdit",
                "tool_input": {
                    "edits": [
                        {"file_path": "src/one.py", "content": "one\n"},
                        {"file_path": "src/two.py", "content": "two\n"},
                        {"file_path": "README.md", "content": "readme\n"},
                    ]
                },
            }

            def completed(args: list[str]) -> subprocess.CompletedProcess[str]:
                stdout = (
                    f"{repo}\n"
                    if "rev-parse" in args
                    else "https://example.invalid/example/repo.git\n"
                )
                return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

            with mock.patch.object(guard, "run_cli", side_effect=completed) as run:
                operation, targets = guard.operation_targets(payload, "MultiEdit")
            self.assertEqual(operation, "edit")
            self.assertIsInstance(targets, dict)
            assert isinstance(targets, dict)
            self.assertEqual(len(targets["targets"]), 3)
            self.assertEqual(run.call_count, 2)


    def test_session_coordination_shell_projection_is_checkout_bound(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_checkout_projection_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "src").mkdir(parents=True)
            subprocess.run(
                ["git", "init", "--quiet", "--initial-branch", "main"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    "https://example.invalid/example/repository.git",
                ],
                cwd=repo,
                check=True,
            )
            payload = command_payload("touch src/generated.txt")
            payload["cwd"] = str(repo)
            operation, targets = guard.operation_targets(payload, "Bash")

            self.assertEqual(operation, "shell")
            self.assertEqual(
                targets,
                {
                    "schema_version": "agent-session.operation-targets.v1",
                    "targets": [
                        {
                            "kind": "repository",
                            "repository": "example/repository",
                            "value": ".",
                        }
                    ],
                    "provider_refs": [],
                    "checkouts": [
                        {
                            "repository": "example/repository",
                            "path": str(repo.resolve()),
                        }
                    ],
                },
            )


    def test_session_coordination_pull_request_head_targets_per_command_shape(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_pull_request_heads_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)

        def head(repository: str, branch: str) -> dict[str, object]:
            return {
                "schema_version": "agent-session.operation-targets.v1",
                "targets": [],
                "provider_refs": [],
                "pull_requests": [
                    {
                        "kind": "pull-request-head",
                        "repository": repository,
                        "head": branch,
                    }
                ],
                "checkouts": [],
            }

        def provider(kind: str, number: int) -> dict[str, object]:
            return {
                "schema_version": "agent-session.operation-targets.v1",
                "targets": [],
                "provider_refs": [
                    {
                        "kind": kind,
                        "repository": "example/repository",
                        "number": number,
                    }
                ],
                "checkouts": [],
            }

        own = head("example/repository", "feat/topic")
        cases: tuple[tuple[str, str | None, object], ...] = (
            # Head-bound shapes resolve to the pull request of one branch.
            ("forge-cli pr create --kind feature --title x", "provider-pr", own),
            (
                "forge-cli pr deliver --kind feature --title x --no-merge",
                "provider-pr",
                own,
            ),
            (
                "forge-cli --format json pr deliver --no-merge --kind bug --title x",
                "provider-pr",
                own,
            ),
            (
                "forge-cli pr create --title x --kind feature --head feat/topic",
                "provider-pr",
                own,
            ),
            (
                "forge-cli pr create --title x --kind feature "
                "--repo example/repository --remote origin",
                "provider-pr",
                own,
            ),
            # A forced provider with `--repo` can select another forge's default
            # host for the same repository path.
            (
                "forge-cli --provider gitlab --repo example/repository pr create "
                "--title x --kind feature --head feat/topic",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli pr deliver --no-merge --provider=github "
                "--kind feature --title x",
                None,
                "provider-pr-unresolved",
            ),
            # Another branch or repository is emitted as named, so the broker's
            # head grant (not this parser) is what denies it.
            (
                "forge-cli pr create --title x --kind feature --head feat/other",
                "provider-pr",
                head("example/repository", "feat/other"),
            ),
            (
                "forge-cli pr deliver --title x --kind feature --no-merge "
                "--repo Other/Repository",
                "provider-pr",
                head("other/repository", "feat/topic"),
            ),
            (
                "forge-cli pr create --title x --kind feature -R other/repository "
                "--head=feat/topic",
                "provider-pr",
                head("other/repository", "feat/topic"),
            ),
            (
                "forge-cli pr create --title x --kind feature -Rother/repository",
                "provider-pr",
                head("other/repository", "feat/topic"),
            ),
            (
                "forge-cli pr create --title x --kind feature -Ra/b --repo c/d",
                None,
                "provider-pr-unresolved",
            ),
            # A delivery that would merge stays with the coordinator.
            ("forge-cli pr deliver --kind feature --title x", None, "provider-pr-unresolved"),
            # Ambiguous or unprovable heads and repositories fail closed.
            (
                "forge-cli pr create --title x --kind feature --head a --head b",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli pr create --title x --kind feature --repo a/b -R c/d",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli pr create --title x --kind feature --head fork:feat/topic",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli pr create --title x --kind feature --head feat..topic",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli pr create --title x --kind feature --remote upstream",
                None,
                "provider-pr-unresolved",
            ),
            # Repository identity is host-less, so the forge authority must
            # remain the checkout origin's.
            (
                "forge-cli pr create --title x --kind feature "
                "--repo example/repository --remote upstream",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli pr create --title x --kind feature "
                "--host other.example --provider gitlab",
                None,
                "provider-pr-unresolved",
            ),
            (
                "forge-cli --host=other.example pr deliver --no-merge "
                "--kind feature --title x",
                None,
                "provider-pr-unresolved",
            ),
            ("gh pr create --title x --head feat/topic", None, "provider-pr-unresolved"),
            # Numbered shapes keep their provider reference; a worker claim
            # carries no pull-request reference, so merge stays uncovered.
            ("forge-cli pr merge 7", "provider-pr", provider("pr", 7)),
            ("forge-cli pr comment 7 --body-file x.md", "provider-pr", provider("pr", 7)),
            ("forge-cli pr review 7", "provider-pr", provider("pr", 7)),
            ("forge-cli issue comment 12 --body-file x.md", "provider-issue", provider("issue", 12)),
            # The coordinator owns new issues.
            ("forge-cli issue create --title x", None, "provider-issue-unresolved"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._pull_request_head_repo(Path(tmp))
            for command, operation, expected in cases:
                with self.subTest(command=command):
                    payload = command_payload(command)
                    payload["cwd"] = str(repo)
                    result = guard.operation_targets(
                        payload, "Bash", pull_request_targets=True
                    )
                    if operation is None:
                        self.assertEqual(result, (None, expected))
                    else:
                        self.assertEqual(result, (operation, expected))

            # Without the capability every head-bound shape keeps the released
            # unresolved result, and no shape grows a `pull_requests` field.
            for command, _operation, expected in cases:
                with self.subTest(command=command, gated=False):
                    payload = command_payload(command)
                    payload["cwd"] = str(repo)
                    operation, targets = guard.operation_targets(payload, "Bash")
                    if isinstance(expected, dict) and "pull_requests" in expected:
                        self.assertIsNone(operation)
                        self.assertEqual(targets, "provider-pr-unresolved")
                    elif isinstance(targets, dict):
                        self.assertNotIn("pull_requests", targets)

            subprocess.run(
                ["git", "commit", "--quiet", "--allow-empty", "-m", "seed"],
                cwd=repo,
                check=True,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "fixture",
                    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "fixture",
                    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                },
            )
            subprocess.run(
                ["git", "checkout", "--quiet", "--detach"], cwd=repo, check=True
            )
            payload = command_payload("forge-cli pr create --kind feature --title x")
            payload["cwd"] = str(repo)
            self.assertEqual(
                guard.operation_targets(payload, "Bash", pull_request_targets=True),
                (None, "provider-pr-unresolved"),
            )


    def test_session_coordination_pull_request_capability_follows_version(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_pull_request_capability_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        for output, expected in (
            ("agent-session 1.29.0 (v1.29.0, rustc 1.98.1)", False),
            ("agent-session 1.24.5", False),
            ("agent-session 1.29.1 (v1.29.1, rustc 1.98.1)", True),
            ("agent-session 1.30.0", True),
            ("agent-session unknown", False),
        ):
            with self.subTest(output=output):
                completed = subprocess.CompletedProcess(
                    ["agent-session", "--version"], 0, stdout=output + "\n", stderr=""
                )
                with mock.patch.object(guard, "run_cli", return_value=completed):
                    self.assertEqual(
                        guard.pull_request_target_capability(
                            f"/fixture/{secrets.token_hex(4)}/agent-session"
                        ),
                        expected,
                    )


    def test_session_coordination_guard_admits_only_own_pull_request_head(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._pull_request_head_repo(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            agent_session = bin_dir / "agent-session"
            # The fake broker mirrors the released contract: an older surface
            # rejects the unknown `pull_requests` field as invalid scope, and a
            # newer one covers only the claim's private head grant.
            agent_session.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo "agent-session ${FAKE_VERSION}"; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\\n' '{"ok":true,"data":{"schema_version":"agent-session.work-context.v1","session_id":"private-session","session_incarnation":"incarnation-1","claim_id":"claim-1","revision":3,"state":"active"}}'
  exit 0
fi
if [[ "$*" == *"work-context check"* ]]; then
  printf '%s\\n' '{"ok":true,"data":{"schema_version":"agent-session.conflict-evaluation.v1","classification":"clear","complete":true,"reasons":[],"peers":[]}}'
  exit 0
fi
if [[ "$*" == *"work-context admit"* ]]; then
  targets=''
  previous=''
  for argument in "$@"; do
    [[ "$previous" == '--targets-file' ]] && targets="$argument"
    previous="$argument"
  done
  body="$(cat "$targets")"
  printf 'admit %s\\n' "$body" >> "$CALL_LOG"
  if [[ "$body" == *'"pull_requests"'* && "$FAKE_VERSION" == 1.29.0* ]]; then
    printf '%s\\n' '{"ok":false,"error":{"code":"invalid-scope","message":"unknown field pull_requests"}}'
    exit 1
  fi
  grant='{"head": "feat/topic", "kind": "pull-request-head", "repository": "example/repository"}'
  if [[ "$body" != *"\\"pull_requests\\": [$grant]"* ]]; then
    printf '%s\\n' '{"ok":false,"error":{"code":"uncovered-mutation-scope","message":"not covered"}}'
    exit 1
  fi
  printf '%s\\n' '{"ok":true,"data":{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","revision":1,"state":"active"}}'
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "private-capability"
            capability.write_text("secret\n", encoding="utf-8")
            capability.chmod(0o600)
            base_env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
                "AGENT_SESSION_ID": "private-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "CALL_LOG": str(call_log),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            own = "forge-cli pr deliver --kind feature --title x --no-merge"

            def run(command: str, version: str, call: str) -> dict[str, object] | None:
                payload = command_payload(command)
                payload.update(
                    {
                        "cwd": str(repo),
                        "session_id": "private-product-session",
                        "tool_use_id": call,
                        "hook_event_name": "PreToolUse",
                    }
                )
                code, decision, stderr = run_enforced_hook(
                    "session-coordination-guard.py",
                    payload,
                    cwd=repo,
                    env=dict(base_env, FAKE_VERSION=version),
                )
                self.assertEqual(code, 0, stderr)
                return decision

            # Released v1.29.0 surface: unchanged fail-closed result, and the
            # broker is never asked to admit a field it would reject.
            for index, command in enumerate(
                (own, "forge-cli pr create --kind feature --title x")
            ):
                with self.subTest(version="1.29.0", command=command):
                    decision = run(
                        command, "1.29.0 (v1.29.0, rustc 1.98.1)", f"old-{index}"
                    )
                    self.assert_blocked(decision, "provider-pr-unresolved")
            self.assertFalse(call_log.exists())

            decision = run(own, "1.29.1 (v1.29.1, rustc 1.98.1)", "own-head")
            self.assert_allowed(decision)
            admitted = call_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(admitted), 1)
            self.assertEqual(
                json.loads(admitted[0].removeprefix("admit ")),
                {
                    "schema_version": "agent-session.operation-targets.v1",
                    "checkouts": [],
                    "provider_refs": [],
                    "pull_requests": [
                        {
                            "head": "feat/topic",
                            "kind": "pull-request-head",
                            "repository": "example/repository",
                        }
                    ],
                    "targets": [],
                },
            )

            for command, fragment in (
                (
                    "forge-cli pr create --kind feature --title x --head feat/other",
                    "uncovered-mutation-scope",
                ),
                (
                    "forge-cli pr deliver --kind feature --title x --no-merge "
                    "--repo other/repository",
                    "uncovered-mutation-scope",
                ),
                ("forge-cli pr merge 7", "uncovered-mutation-scope"),
                ("forge-cli pr deliver --kind feature --title x", "provider-pr-unresolved"),
                ("forge-cli issue create --title x", "provider-issue-unresolved"),
            ):
                with self.subTest(command=command):
                    decision = run(
                        command,
                        "1.30.0",
                        "denied-" + hashlib.sha256(command.encode()).hexdigest()[:12],
                    )
                    self.assert_blocked(decision, fragment)


    @unittest.skipUnless(
        os.environ.get("AGENT_SESSION_COUPLED_ACCEPTANCE") == "1",
        "requires a source-linked agent-session binary",
    )
    def test_session_coordination_source_linked_cross_product_acceptance(self) -> None:
        agent_session = os.environ.get("AGENT_SESSION_SOURCE_BIN")
        self.assertIsNotNone(agent_session)
        assert agent_session is not None
        self.assertTrue(Path(agent_session).is_absolute())
        self.assertTrue(os.access(agent_session, os.X_OK))
        version = subprocess.run(
            [agent_session, "--version"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        parsed_version = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
        self.assertIsNotNone(parsed_version)
        assert parsed_version is not None
        self.assertGreaterEqual(
            tuple(int(part) for part in parsed_version.groups()), (1, 25, 2)
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "--quiet", "--initial-branch", "main"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    "https://example.invalid/example/repository.git",
                ],
                cwd=repo,
                check=True,
            )
            state = root / "state"
            sessions = state / "sessions"
            coordination = state / "coordination"
            sessions.mkdir(parents=True, mode=0o700)
            coordination.mkdir(mode=0o700)
            now = int(time.time())
            brokers: dict[str, object] = {}
            capabilities: dict[str, Path] = {}
            for session_id in ("alpha", "beta"):
                incarnation = f"incarnation-{session_id}"
                capability_value = f"private-capability-material-{session_id}-000001"
                session_dir = sessions / session_id
                capability_dir = session_dir / "coordination"
                capability_dir.mkdir(parents=True, mode=0o700)
                record = {
                    "schema_version": "agent-session.session.v1",
                    "id": session_id,
                    "agent": "codex",
                    "mode": "interactive",
                    "coordination_mode": "advisory",
                    "title": "coupled acceptance",
                    "title_revision": 0,
                    "cwd": str(repo),
                    "tmux_session": f"hs-codex-{session_id}",
                    "prompt_file": None,
                    "log_file": None,
                    "created_at": "2030-01-01T00:00:00Z",
                    "updated_at": "2030-01-01T00:00:00Z",
                    "runtime": {
                        "kind": "tmux",
                        "tmux_session": f"hs-codex-{session_id}",
                        "generation": 1,
                        "started_at": "2030-01-01T00:00:00Z",
                        "launch_id": incarnation,
                    },
                }
                record_path = session_dir / "session.json"
                record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                record_path.chmod(0o600)
                capability_path = capability_dir / (
                    "capability-" + hashlib.sha256(incarnation.encode()).hexdigest()
                )
                capability_path.write_text(capability_value, encoding="utf-8")
                capability_path.chmod(0o600)
                heartbeat = capability_dir / "heartbeat"
                heartbeat.write_text(f"{incarnation}:{now}\n", encoding="utf-8")
                heartbeat.chmod(0o600)
                capabilities[session_id] = capability_path
                brokers[session_id] = {
                    "session_id": session_id,
                    "incarnation": incarnation,
                    "capability_digest": hashlib.sha256(
                        capability_value.encode()
                    ).hexdigest(),
                    "generation": 1,
                    "state": "ready",
                    "heartbeat_at": "2030-01-01T00:00:00Z",
                    "heartbeat_epoch": now,
                }
            registry_path = coordination / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-session.coordination-registry.v1",
                        "fingerprint_epoch": 1,
                        "fingerprint_key": "fixture-private-fingerprint-key-material-0000000001",
                        "brokers": brokers,
                        "claims": [],
                        "operations": [],
                        "messages": [],
                        "receipts": {},
                        "notifications": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            registry_path.chmod(0o600)
            binary_dir = str(Path(agent_session).resolve().parent)
            managed_env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": binary_dir,
                "AGENT_SESSION_ID": "alpha",
                "AGENT_SESSION_CAPABILITY_FILE": str(capabilities["alpha"]),
                "AGENT_SESSION_STATE_DIR": str(state),
                "AGENT_SESSION_COORDINATION_MODE": "",
                "PATH": binary_dir + os.pathsep + os.environ.get("PATH", ""),
            }
            payload = write_payload(str(repo / "src/lib.rs"), "fn main() {}\n")
            payload.update(
                {
                    "cwd": str(repo),
                    "session_id": "product-alpha",
                    "tool_use_id": "coupled-first-mutation",
                    "hook_event_name": "PreToolUse",
                }
            )
            command_env = dict(os.environ)
            command_env.update(managed_env)
            probe = subprocess.run(
                [
                    agent_session,
                    "--state-dir",
                    str(state),
                    "work-context",
                    "advise",
                    "--format",
                    "json",
                ],
                cwd=repo,
                env=command_env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                probe.returncode,
                0,
                f"source-linked advise failed: stdout={probe.stdout} stderr={probe.stderr}",
            )
            code, advisory, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=managed_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(advisory)
            self.assertNotEqual((advisory or {}).get("decision"), "block")
            self.assertIn("possible overlap", str(advisory).lower())

            acknowledged = subprocess.run(
                [
                    agent_session,
                    "--state-dir",
                    str(state),
                    "work-context",
                    "acknowledge",
                    "--for",
                    "30m",
                    "--format",
                    "json",
                ],
                cwd=repo,
                env=command_env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(acknowledged.returncode, 0, acknowledged.stderr)
            code, suppressed, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=managed_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(suppressed)

            provider = command_payload("forge-cli issue edit 1318 --title advisory")
            provider.update(
                {
                    "cwd": str(repo),
                    "session_id": "product-alpha",
                    "tool_use_id": "coupled-provider-mutation",
                    "hook_event_name": "PreToolUse",
                }
            )
            code, provider_advisory, stderr = run_hook(
                "session-coordination-guard.py",
                provider,
                cwd=repo,
                env=managed_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(provider_advisory)

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["brokers"]["beta"]["state"] = "starting"
            registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")
            registry_path.chmod(0o600)
            degraded_payload = dict(payload)
            degraded_payload["tool_use_id"] = "coupled-broker-degraded"
            code, degraded, stderr = run_hook(
                "session-coordination-guard.py",
                degraded_payload,
                cwd=repo,
                env=managed_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertNotEqual((degraded or {}).get("decision"), "block")
            self.assertIn("coordination is unavailable", str(degraded).lower())
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["brokers"]["beta"]["state"] = "ready"
            registry["brokers"]["beta"]["heartbeat_epoch"] = int(time.time())
            registry["advisory_acknowledgements"] = {}
            registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")
            registry_path.chmod(0o600)

            code, enforced, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=dict(managed_env, AGENT_SESSION_COORDINATION_MODE="enforce"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(enforced, "active work-context claim")
            code, off, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env=dict(managed_env, AGENT_SESSION_COORDINATION_MODE="off"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(off)
            code, unmanaged, stderr = run_hook(
                "session-coordination-guard.py",
                payload,
                cwd=repo,
                env={
                    "AGENT_RUNTIME_PRODUCT": "codex",
                    "AGENT_SESSION_ID": "",
                    "AGENT_SESSION_CAPABILITY_FILE": "",
                    "AGENT_SESSION_STATE_DIR": "",
                    "AGENT_SESSION_COORDINATION_MODE": "",
                },
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(unmanaged)

            claude_payload = dict(payload)
            claude_payload["tool_use_id"] = "coupled-claude-mutation"
            code, claude, stderr = run_hook(
                "session-coordination-guard.py",
                claude_payload,
                cwd=repo,
                env=dict(managed_env, AGENT_RUNTIME_PRODUCT="claude"),
            )
            self.assertEqual(code, 0, stderr)
            self.assertNotEqual((claude or {}).get("decision"), "block")
            self.assertIn("possible overlap", str(claude).lower())

            runtime_identity = {
                "launch_id": "incarnation-alpha",
                "session_id": "$94",
                "pane_id": "%94",
                "pane_pid": os.getpid(),
                "process_group_id": os.getpgrp(),
                "process_session_id": os.getsid(0),
            }
            alpha_record_path = sessions / "alpha" / "session.json"
            alpha_record = json.loads(
                alpha_record_path.read_text(encoding="utf-8")
            )
            alpha_record["coordination_mode"] = "enforce"
            alpha_record["delete_tmux_identity"] = runtime_identity
            alpha_record_path.write_text(
                json.dumps(alpha_record) + "\n", encoding="utf-8"
            )
            alpha_record_path.chmod(0o600)
            activity_path = sessions / "alpha" / "activity.json"
            activity_path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-session.activity.v1",
                        "runtime_id": "incarnation-alpha",
                        "runtime_generation": 1,
                        "state": {
                            "schema_version": "agent-session.turn-state.v1",
                            "phase": "working",
                            "phase_changed_at": "2030-01-01T00:00:00Z",
                            "revision": 1,
                            "source": {
                                "kind": "runtime",
                                "provider": None,
                                "confidence": "authoritative",
                            },
                            "current_turn": {
                                "provider_turn_id": "turn-coupled-shell",
                                "started_at": "2030-01-01T00:00:00Z",
                            },
                            "last_turn": None,
                        },
                        "pending_attention": [],
                        "seen_event_count": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            activity_path.chmod(0o600)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["brokers"]["alpha"]["coordination_mode"] = "enforce"
            registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")
            registry_path.chmod(0o600)
            claim_file = root / "alpha-claim.json"
            claim_file.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-session.work-context-input.v1",
                        "intent": "implementation",
                        "tier": "program/dispatch",
                        "repositories": ["example/repository"],
                        "worktrees": [],
                        "provider_refs": [],
                        "plan_refs": [],
                        "scopes": [
                            {
                                "kind": "path-prefix",
                                "repository": "example/repository",
                                "value": "src",
                            }
                        ],
                        "summary": "coupled checkout shell acceptance",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            claim_file.chmod(0o600)
            claimed = subprocess.run(
                [
                    agent_session,
                    "--state-dir",
                    str(state),
                    "work-context",
                    "claim",
                    "--session",
                    "alpha",
                    "--file",
                    str(claim_file),
                    "--capability-file",
                    str(capabilities["alpha"]),
                    "--idempotency-key",
                    "coupled-checkout-shell-claim-0001",
                    "--format",
                    "json",
                ],
                cwd=repo,
                env=command_env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                claimed.returncode,
                0,
                f"source-linked claim failed: stdout={claimed.stdout} stderr={claimed.stderr}",
            )
            shell_payload = write_payload(str(repo / "src" / "generated.txt"), "fixture\n")
            shell_payload.update(
                {
                    "cwd": str(repo),
                    "session_id": "product-alpha",
                    "tool_use_id": "coupled-checkout-shell",
                    "hook_event_name": "PreToolUse",
                }
            )
            enforce_env = dict(
                managed_env, AGENT_SESSION_COORDINATION_MODE="enforce"
            )
            code, shell_pre, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                shell_payload,
                cwd=repo,
                env=enforce_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertNotEqual((shell_pre or {}).get("decision"), "block")

            shell_post = dict(shell_payload)
            shell_post["hook_event_name"] = "PostToolUse"
            shell_post["tool_response"] = {"exit_code": 0}
            code, shell_complete, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                shell_post,
                cwd=repo,
                env=enforce_env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(shell_complete)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            alpha_operations = [
                operation
                for operation in registry["operations"]
                if operation["session_id"] == "alpha"
            ]
            self.assertEqual(len(alpha_operations), 1)
            self.assertEqual(alpha_operations[0]["operation"], "write")
            self.assertEqual(alpha_operations[0]["state"], "completed")

            # Pull-request head targets: a surface below the capability floor
            # rejects the unknown field, so the guard must keep the released
            # unresolved result and never send it.
            source_version = tuple(int(part) for part in parsed_version.groups())
            supports_heads = source_version >= (1, 29, 1)
            if supports_heads:
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                alpha_claim = next(
                    claim
                    for claim in registry["claims"]
                    if claim["session_id"] == "alpha" and claim["state"] == "active"
                )
                alpha_claim["pull_request_head"] = {
                    "repository": "example/repository",
                    "head": "main",
                }
                registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")
                registry_path.chmod(0o600)
            elif "(v" in version:
                # A tagged release below the floor must reject the field, which
                # is why the guard withholds it. An untagged source build may
                # already accept it while still reporting the older version.
                targets_file = root / "direct-pull-request.targets.json"
                targets_file.write_text(
                    json.dumps(
                        {
                            "schema_version": "agent-session.operation-targets.v1",
                            "pull_requests": [
                                {
                                    "kind": "pull-request-head",
                                    "repository": "example/repository",
                                    "head": "main",
                                }
                            ],
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                targets_file.chmod(0o600)
                token_file = root / "direct-pull-request.token"
                token_file.write_text("hook-" + "0" * 32, encoding="utf-8")
                token_file.chmod(0o600)
                active_claim = next(
                    claim
                    for claim in json.loads(registry_path.read_text(encoding="utf-8"))[
                        "claims"
                    ]
                    if claim["session_id"] == "alpha" and claim["state"] == "active"
                )
                claim_id = active_claim["claim_id"]
                claim_revision = active_claim["revision"]
                direct = subprocess.run(
                    [
                        agent_session,
                        "--state-dir",
                        str(state),
                        "work-context",
                        "admit",
                        "--session",
                        "alpha",
                        "--claim",
                        claim_id,
                        "--if-revision",
                        str(claim_revision),
                        "--targets-file",
                        str(targets_file),
                        "--operation",
                        "provider-pr",
                        "--execution-token-file",
                        str(token_file),
                        "--capability-file",
                        str(capabilities["alpha"]),
                        "--idempotency-key",
                        "coupled-direct-pull-request-0001",
                        "--format",
                        "json",
                    ],
                    cwd=repo,
                    env=command_env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(direct.returncode, 0, direct.stdout)
                self.assertEqual(
                    json.loads(direct.stdout)["error"]["code"], "invalid-scope"
                )
            operations_before = len(alpha_operations)
            for index, (command, blocked_reason) in enumerate(
                (
                    ("forge-cli pr deliver --kind feature --title x --no-merge", None),
                    (
                        "forge-cli pr create --kind feature --title x --head feat/other",
                        "uncovered-mutation-scope",
                    ),
                    (
                        "forge-cli pr create --kind feature --title x "
                        "--repo other/repository",
                        "uncovered-mutation-scope",
                    ),
                )
            ):
                pull_request = command_payload(command)
                pull_request.update(
                    {
                        "cwd": str(repo),
                        "session_id": "product-alpha",
                        "tool_use_id": f"coupled-pull-request-{index}",
                        "hook_event_name": "PreToolUse",
                    }
                )
                code, pull_request_pre, stderr = run_enforced_hook(
                    "session-coordination-guard.py",
                    pull_request,
                    cwd=repo,
                    env=enforce_env,
                )
                self.assertEqual(code, 0, stderr)
                if not supports_heads:
                    self.assert_blocked(pull_request_pre, "provider-pr-unresolved")
                    continue
                if blocked_reason is not None:
                    self.assert_blocked(pull_request_pre, blocked_reason)
                    continue
                self.assertNotEqual(
                    (pull_request_pre or {}).get("decision"), "block"
                )
                pull_request_post = dict(pull_request)
                pull_request_post["hook_event_name"] = "PostToolUse"
                pull_request_post["tool_response"] = {"exit_code": 0}
                code, completed_pull_request, stderr = run_enforced_hook(
                    "session-coordination-guard.py",
                    pull_request_post,
                    cwd=repo,
                    env=enforce_env,
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(completed_pull_request)
            operations = [
                operation
                for operation in json.loads(
                    registry_path.read_text(encoding="utf-8")
                )["operations"]
                if operation["session_id"] == "alpha"
            ]
            if supports_heads:
                self.assertEqual(len(operations), operations_before + 1)
                self.assertEqual(
                    operations[-1]["pull_request_targets"],
                    [
                        {
                            "kind": "pull-request-head",
                            "repository": "example/repository",
                            "head": "main",
                        }
                    ],
                )
                self.assertEqual(operations[-1]["state"], "completed")
            else:
                self.assertEqual(len(operations), operations_before)


    def test_session_coordination_guard_admits_advises_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            (repo / "src").mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://example.invalid/example/repo.git"],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            call_log = root / "calls.log"
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {shlex.quote(str(call_log))}
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.24.5'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-session.work-context-show.v1","ok":true,"data":{{"schema_version":"agent-session.work-context.v1","session_id":"managed-session","session_incarnation":"incarnation-1","claim_id":"claim-1","revision":3,"state":"active"}}}}'
  exit 0
fi
if [[ "$*" == *"work-context check"* ]]; then
  printf '%s\\n' '{{"schema_version":"cli.agent-session.work-context-check.v1","ok":true,"data":{{"schema_version":"agent-session.conflict-evaluation.v1","classification":"potential_conflict","complete":true,"reasons":[],"peers":[]}}}}'
  exit 0
fi
if [[ "$*" == *"work-context admit"* ]]; then
  previous=''
  for argument in "$@"; do
    if [[ "$previous" == '--targets-file' ]]; then
      printf 'TARGETS=%s\\n' "$(<"$argument")" >> {shlex.quote(str(call_log))}
      break
    fi
    previous="$argument"
  done
  printf '%s\\n' '{{"schema_version":"cli.agent-session.work-context-admit.v1","ok":true,"data":{{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","claim_id":"claim-1","claim_revision":3,"revision":1,"state":"active"}}}}'
  exit 0
fi
if [[ "$*" == *"work-context complete"* ]]; then
  state='completed'
  outcome='pass'
  if [[ "$*" == *"--outcome fail"* ]]; then state='failed'; outcome='fail'; fi
  printf '{{"schema_version":"cli.agent-session.work-context-complete.v1","ok":true,"data":{{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","revision":2,"state":"%s","outcome":"%s"}}}}\\n' "$state" "$outcome"
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "capability"
            capability.write_text("private-capability\n", encoding="utf-8")
            capability.chmod(0o600)
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
                "AGENT_SESSION_ID": "managed-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            pre = write_payload("src/lib.rs", "fn main() {}\n")
            pre.update(
                {
                    "session_id": "product-session",
                    "tool_use_id": "coord-tool-1",
                    "hook_event_name": "PreToolUse",
                }
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", pre, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertNotEqual(decision.get("decision"), "block")
            self.assertIn("potential conflict", str(decision).lower())

            post = dict(pre)
            post["hook_event_name"] = "PostToolUse"
            post["tool_response"] = {"exit_code": 0}
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", post, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            calls = call_log.read_text(encoding="utf-8")
            self.assertIn("work-context admit", calls)
            self.assertIn("work-context complete", calls)
            self.assertIn("--outcome pass", calls)
            self.assertIn('"kind": "path-exact"', calls)
            self.assertIn('"value": "src/lib.rs"', calls)

            failed_pre = write_payload("src/failed.rs", "fn failed() {}\n")
            failed_pre.update(
                {
                    "session_id": "product-session",
                    "tool_use_id": "coord-tool-2",
                    "hook_event_name": "PreToolUse",
                }
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", failed_pre, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            failed_post = dict(failed_pre)
            failed_post["hook_event_name"] = "PostToolUseFailure"
            failed_post["tool_response"] = {"error": "synthetic failure"}
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", failed_post, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertIn("--outcome fail", call_log.read_text(encoding="utf-8"))
            namespace = (
                root
                / "runtime-state"
                / "session-coordination"
                / hashlib.sha256(b"managed-session").hexdigest()
            )
            self.assertEqual(list(namespace.glob("*.json")), [])
            self.assertEqual(list(namespace.glob("*.token")), [])
            self.assertEqual(list(namespace.glob("*.outcome")), [])


    def test_session_coordination_guard_blocks_conflict_uncovered_and_stale_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            (repo / "src").mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://example.invalid/example/repo.git"],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.24.5'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* && "${COORD_SCENARIO:-}" == 'stale' ]]; then
  printf '%s\n' '{"ok":false,"error":{"code":"session-incarnation-mismatch","message":"private-session /home/private/cap"}}'
  exit 1
fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\n' '{"ok":true,"data":{"schema_version":"agent-session.work-context.v1","session_id":"private-session","session_incarnation":"incarnation-1","claim_id":"claim-1","revision":3,"state":"active"}}'
  exit 0
fi
if [[ "$*" == *"work-context check"* ]]; then
  classification='clear'
  [[ "${COORD_SCENARIO:-}" == 'conflict' ]] && classification='conflict'
  printf '{"ok":true,"data":{"schema_version":"agent-session.conflict-evaluation.v1","classification":"%s","complete":true,"reasons":[],"peers":[]}}\n' "$classification"
  exit 0
fi
if [[ "$*" == *"work-context admit"* && "${COORD_SCENARIO:-}" == 'uncovered' ]]; then
  printf '%s\n' '{"ok":false,"error":{"code":"uncovered-mutation-scope","message":"private target path"}}'
  exit 1
fi
if [[ "$*" == *"work-context admit"* && "${COORD_SCENARIO:-}" == 'invalid-lease' ]]; then
  printf '%s\n' '{"ok":true,"data":{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","revision":1,"state":"unknown"}}'
  exit 0
fi
if [[ "$*" == *"work-context admit"* ]]; then
  printf '%s\n' '{"ok":true,"data":{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","revision":1,"state":"active"}}'
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "private-capability"
            capability.write_text("secret\n", encoding="utf-8")
            capability.chmod(0o600)
            base_env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
                "AGENT_SESSION_ID": "private-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            for scenario, fragment in (
                ("conflict", "definite peer conflict"),
                ("uncovered", "uncovered-mutation-scope"),
                ("stale", "active work-context claim"),
                ("invalid-lease", "invalid-operation-lease"),
            ):
                with self.subTest(scenario=scenario):
                    env = dict(base_env, COORD_SCENARIO=scenario)
                    payload = write_payload("src/lib.rs", "fn main() {}\n")
                    payload.update(
                        {
                            "session_id": "private-product-session",
                            "tool_use_id": f"tool-{scenario}",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_enforced_hook(
                        "session-coordination-guard.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, fragment)
                    rendered = str(decision)
                    for private in (
                        str(repo),
                        str(capability),
                        "private-session",
                        "private-product-session",
                        "/home/private",
                    ):
                        self.assertNotIn(private, rendered)

            namespace = (
                root
                / "runtime-state"
                / "session-coordination"
                / hashlib.sha256(b"private-session").hexdigest()
            )
            self.assertEqual(
                len(
                    [
                        path
                        for path in namespace.glob("*.json")
                        if not path.name.endswith(".targets.json")
                    ]
                ),
                1,
            )

            provider_payload = command_payload("forge-cli issue comment --body synthetic")
            provider_payload.update(
                {
                    "session_id": "private-product-session",
                    "tool_use_id": "tool-provider",
                    "hook_event_name": "PreToolUse",
                }
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                provider_payload,
                cwd=repo,
                env=dict(base_env, COORD_SCENARIO="clear"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "provider-issue-unresolved")

            outside = root / "outside.txt"
            symlink = repo / "src" / "escape"
            symlink.symlink_to(root)
            escape_payload = write_payload(str(symlink / outside.name), "escape\n")
            escape_payload.update(
                {
                    "session_id": "private-product-session",
                    "tool_use_id": "tool-escape",
                    "hook_event_name": "PreToolUse",
                }
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                escape_payload,
                cwd=repo,
                env=dict(base_env, COORD_SCENARIO="clear"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "target-boundary-unavailable")


    def test_session_coordination_guard_older_surface_is_advisory_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                "#!/usr/bin/env bash\necho 'agent-session 1.24.4'\n",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "capability"
            capability.write_text("secret\n", encoding="utf-8")
            capability.chmod(0o600)
            payload = write_payload("src/lib.rs", "fn main() {}\n")
            payload.update(
                {
                    "session_id": "product-session",
                    "tool_use_id": "older-tool",
                    "hook_event_name": "PreToolUse",
                }
            )
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_SESSION_ID": "managed-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", payload, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertNotEqual(decision.get("decision"), "block")
            self.assertIn("no enforcement claim", str(decision))


    def test_session_coordination_guard_retries_completion_and_audits_dropped_post(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            (repo / "src").mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://example.invalid/example/repo.git"],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fail_once = root / "fail-once"
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.24.5'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.work-context.v1","session_id":"managed-session","session_incarnation":"incarnation-1","claim_id":"claim-1","revision":3,"state":"active"}}}}'
  exit 0
fi
if [[ "$*" == *"work-context check"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.conflict-evaluation.v1","classification":"clear","complete":true,"reasons":[],"peers":[]}}}}'
  exit 0
fi
if [[ "$*" == *"work-context admit"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","revision":1,"state":"active"}}}}'
  exit 0
fi
if [[ "$*" == *"work-context complete"* ]]; then
  if [[ ! -f {shlex.quote(str(fail_once))} ]]; then
    : > {shlex.quote(str(fail_once))}
    printf '%s\\n' '{{"ok":false,"error":{{"code":"coordination-store-unavailable"}}}}'
    exit 1
  fi
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","revision":2,"state":"completed","outcome":"pass"}}}}'
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability = root / "capability"
            capability.write_text("secret\n", encoding="utf-8")
            capability.chmod(0o600)
            runtime_state = root / "runtime-state"
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(runtime_state),
                "AGENT_SESSION_ID": "managed-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            pre = write_payload("src/lib.rs", "fn main() {}\n")
            pre.update(
                {
                    "session_id": "product-session",
                    "tool_use_id": "retry-tool",
                    "hook_event_name": "PreToolUse",
                }
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", pre, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            duplicate = dict(pre)
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", duplicate, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "operation-pending")

            dropped_stop = {
                "hook_event_name": "Stop",
                "session_id": "product-session",
            }
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", dropped_stop, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertEqual(
                decision.get("schema_version"),
                "runtime-kit.session-coordination-result.v1",
            )
            self.assertEqual(decision.get("status"), "pending")
            self.assertIn("does not release or guess", str(decision.get("message")))

            post = dict(pre)
            post["hook_event_name"] = "PostToolUse"
            post["tool_response"] = {"exit_code": 0}
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", post, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            self.assertIn("completion is pending", str(decision))

            namespace = runtime_state / "session-coordination" / hashlib.sha256(
                b"managed-session"
            ).hexdigest()
            record_path = next(
                path
                for path in namespace.glob("*.json")
                if not path.name.endswith(".targets.json")
            )
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["outcome"], "pass")
            self.assertEqual(
                Path(record["outcome_file"]).read_text(encoding="utf-8"), "pass\n"
            )
            record["outcome"] = None
            record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", dropped_stop, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(
                decision,
                {
                    "schema_version": "runtime-kit.session-coordination-result.v1",
                    "status": "clean",
                },
            )
            self.assertEqual(list(namespace.glob("*.json")), [])
            self.assertEqual(list(namespace.glob("*.token")), [])
            self.assertEqual(list(namespace.glob("*.outcome")), [])


    def test_session_coordination_refused_sibling_admission_leaves_no_record(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                Path(tmp)
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("sibling-a"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)

            # A parallel sibling reaches admission while the first call still
            # holds the session's single operation slot.
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("sibling-b"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "coordination-unavailable")
            self.assertEqual(
                [record["phase"] for record in self.operation_records(namespace)],
                ["active"],
            )

            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("sibling-a", "PostToolUse"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                {"hook_event_name": "Stop", "session_id": "product-session"},
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(decision and decision.get("status"), "clean")
            self.assertEqual(list(namespace.glob("*.token")), [])
            self.assertIn("work-context complete", call_log.read_text(encoding="utf-8"))


    def test_session_coordination_next_call_reconciles_orphaned_active_lease(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                Path(tmp)
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("orphaned-call"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            # PostToolUse for the admitted call never arrives.

            # Records of an earlier incarnation sort ahead of the orphan but
            # cannot be recovered here; they must not crowd it out.
            orphan = self.operation_records(namespace)[0]
            for index in range(5):  # one more than the recovery window
                stale = namespace / f"{index:064d}.json"
                stale.write_text(
                    json.dumps(dict(orphan, session_incarnation="incarnation-0")),
                    encoding="utf-8",
                )
                stale.chmod(0o600)

            def current(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
                return [
                    record
                    for record in records
                    if record["session_incarnation"] == "incarnation-1"
                ]

            # Within the same turn the runtime cannot prove the call inactive,
            # so the orphan is retained and the next mutation stays blocked.
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("same-turn-call"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "coordination-unavailable")
            self.assertEqual(
                [
                    record["phase"]
                    for record in current(self.operation_records(namespace))
                ],
                ["active"],
            )

            quiescent = dict(env, FAKE_BROKER_QUIESCENT="1")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("next-turn-call"),
                cwd=repo,
                env=quiescent,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "operation-reconcile-pending")
            # An immediate retry precedes the broker's second observation.
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("too-soon-retry"),
                cwd=repo,
                env=quiescent,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "operation-reconcile-pending")
            pending = current(self.operation_records(namespace))
            self.assertEqual(
                [(record["lease_id"], record["lease_revision"]) for record in pending],
                [("lease-1", 2)],
            )
            Path(env["FAKE_BROKER_FLAGS"], "reconcile-ready").write_text(
                "", encoding="utf-8"
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("next-turn-retry"),
                cwd=repo,
                env=quiescent,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            records = current(self.operation_records(namespace))
            self.assertEqual([record["phase"] for record in records], ["active"])
            self.assertEqual(records[0]["lease_id"], "lease-2")
            broker = json.loads(Path(env["FAKE_BROKER_STATE"]).read_text("utf-8"))
            self.assertEqual(broker["leases"]["lease-1"]["state"], "failed")
            calls = call_log.read_text(encoding="utf-8")
            self.assertIn("RECONCILE-PROOF outcome=fail", calls)
            self.assertNotIn("RECONCILE-PROOF outcome=pass", calls)


    def test_session_coordination_recovers_admitting_record_left_by_lost_response(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                root
            )
            # The broker commits the lease but the hook never sees the result,
            # as when the hook times out between admission and persistence.
            (root / "garble-admit").write_text("", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("lost-admission"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assertIsNotNone(decision)
            self.assertEqual(
                [record["phase"] for record in self.operation_records(namespace)],
                ["admitting"],
            )

            # A replay refused by broker checks that precede admit's
            # idempotency lookup must keep the record and its token.
            (root / "broker-lost").write_text("", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("broker-lost-call"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "coordination-unavailable")
            self.assertEqual(
                [record["phase"] for record in self.operation_records(namespace)],
                ["admitting"],
            )
            self.assertEqual(len(list(namespace.glob("*.token"))), 1)

            quiescent = dict(env, FAKE_BROKER_QUIESCENT="1")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("next-call"),
                cwd=repo,
                env=quiescent,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "operation-reconcile-pending")
            recovered = self.operation_records(namespace)
            self.assertEqual([record["phase"] for record in recovered], ["active"])
            self.assertEqual(recovered[0]["lease_id"], "lease-1")
            (root / "reconcile-ready").write_text("", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("next-retry"),
                cwd=repo,
                env=quiescent,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(
                [record["lease_id"] for record in self.operation_records(namespace)],
                ["lease-2"],
            )


    def test_session_coordination_retires_records_without_nonterminal_lease(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                root
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("externally-finished"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            # The lease reached a terminal state outside the hook, for example
            # through controller-owned reconciliation.
            state_path = Path(env["FAKE_BROKER_STATE"])
            broker = json.loads(state_path.read_text(encoding="utf-8"))
            broker["leases"]["lease-1"].update(state="failed", revision=3)
            state_path.write_text(json.dumps(broker), encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("after-external-finish"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(
                [record["lease_id"] for record in self.operation_records(namespace)],
                ["lease-2"],
            )
            self.assertNotIn(
                "work-context reconcile", call_log.read_text(encoding="utf-8")
            )


    def test_session_coordination_reconciles_orphan_after_lease_ttl(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                root
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("expired-orphan"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            # TTL expiry moves an unfinished lease to completing, one revision on.
            state_path = Path(env["FAKE_BROKER_STATE"])
            broker = json.loads(state_path.read_text(encoding="utf-8"))
            broker["leases"]["lease-1"].update(state="completing", revision=2)
            state_path.write_text(json.dumps(broker), encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("after-expiry"),
                cwd=repo,
                env=dict(env, FAKE_BROKER_QUIESCENT="1"),
            )
            self.assertEqual(code, 0, stderr)
            self.assert_blocked(decision, "operation-reconcile-pending")
            reconciles = [
                line
                for line in call_log.read_text(encoding="utf-8").splitlines()
                if line.startswith("work-context reconcile")
            ]
            self.assertEqual(len(reconciles), 2)
            self.assertIn("--if-revision 1 ", reconciles[0])
            self.assertIn("--if-revision 2 ", reconciles[1])
            self.assertEqual(
                [
                    (record["lease_id"], record["lease_revision"])
                    for record in self.operation_records(namespace)
                ],
                [("lease-1", 3)],
            )


    def test_session_coordination_orphan_recovery_stops_after_time_slice(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_orphan_slice_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            namespace = Path(tmp)
            record_path = namespace / f"{'a' * 64}.json"
            record = {
                "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                "phase": "active",
                "session": "managed-session",
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "session_incarnation": "incarnation-1",
                "lease_id": "lease-1",
                "lease_revision": 1,
            }
            record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            record_path.chmod(0o600)
            arguments = {
                "managed_session": "managed-session",
                "capability_file": "/private/capability",
                "state_dir": "/private/state",
                "session_incarnation": "incarnation-1",
            }
            unavailable = subprocess.CompletedProcess([], 1, stdout="", stderr="")
            for elapsed, expected_calls in ((0.0, 1), (2.0, 0)):
                with self.subTest(elapsed=elapsed), mock.patch.object(
                    guard, "run_cli", return_value=unavailable
                ) as run, mock.patch.object(
                    guard,
                    "HOOK_DEADLINE",
                    time.monotonic() + guard.HOOK_BUDGET_SECONDS - elapsed,
                ):
                    guard.recover_orphaned_records(
                        "agent-session",
                        namespace,
                        namespace / "current.json",
                        **arguments,
                    )
                    self.assertEqual(run.call_count, expected_calls)
            # Calls started inside the slice are bounded by its aggregate
            # cutoff, not by the per-call timeout.
            timeouts: list[float] = []

            def bounded_run(
                *_args: Any, timeout: float, **_kwargs: Any
            ) -> subprocess.CompletedProcess[str]:
                timeouts.append(timeout)
                return unavailable

            with mock.patch.object(
                guard.subprocess, "run", side_effect=bounded_run
            ), mock.patch.object(
                guard,
                "HOOK_DEADLINE",
                time.monotonic() + guard.HOOK_BUDGET_SECONDS - 1.0,
            ):
                guard.recover_orphaned_records(
                    "agent-session",
                    namespace,
                    namespace / "current.json",
                    **arguments,
                )
            self.assertEqual(len(timeouts), 1)
            self.assertLessEqual(timeouts[0], 0.5)
            self.assertIsNone(guard.RUN_CLI_CUTOFF)
            self.assertEqual(guard.read_record(record_path), record)


    def test_session_coordination_post_tool_completes_admission_lost_by_timeout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                root
            )
            (root / "garble-admit").write_text("", encoding="utf-8")
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("timed-out-admission"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            # A provider that treats the hook timeout as non-blocking still
            # runs the tool and reports its result.
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("timed-out-admission", "PostToolUse"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(self.operation_records(namespace), [])
            broker = json.loads(Path(env["FAKE_BROKER_STATE"]).read_text("utf-8"))
            self.assertEqual(broker["leases"]["lease-1"]["state"], "completed")


    def test_session_coordination_background_shell_completes_at_launch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, env, namespace, call_log = self.single_slot_coordination_fixture(
                Path(tmp)
            )
            pre = command_payload("make validate", run_in_background=True)
            pre.update(
                {
                    "session_id": "product-session",
                    "tool_use_id": "background-shell",
                    "hook_event_name": "PreToolUse",
                    "cwd": str(repo),
                }
            )
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", pre, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(
                [record["operation"] for record in self.operation_records(namespace)],
                ["shell"],
            )
            # Claude reports a background Bash call at launch, not at exit.
            post = dict(pre)
            post["hook_event_name"] = "PostToolUse"
            post["tool_response"] = {
                "stdout": "",
                "stderr": "",
                "interrupted": False,
                "isImage": False,
                "backgroundTaskId": "task-1",
            }
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py", post, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)
            self.assertEqual(self.operation_records(namespace), [])
            self.assertEqual(list(namespace.glob("*.token")), [])
            code, decision, stderr = run_enforced_hook(
                "session-coordination-guard.py",
                self.edit_event("after-background"),
                cwd=repo,
                env=env,
            )
            self.assertEqual(code, 0, stderr)
            self.assert_allowed(decision)


    def test_session_coordination_stop_retires_exact_externally_reconciled_operation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            (repo / "src").mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    "https://example.invalid/example/repo.git",
                ],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            reconciled = root / "operator-reconciled"
            calls = root / "agent-session-calls"
            capability = root / "capability"
            state_dir = root / "session-state"
            claim_id = "11111111-1111-4111-8111-111111111111"
            agent_session = bin_dir / "agent-session"
            active_batch = json.dumps(
                {
                    "ok": True,
                    "data": {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": "managed-session",
                        "session_incarnation": "incarnation-1",
                        "generation": 1,
                        "proofs": [
                            {
                                "index": index,
                                "ok": True,
                                "proof": {
                                    "kind": "operation",
                                    "found": True,
                                    "lease_id": "lease-1",
                                    "state": "active",
                                    "revision": 1,
                                    "outcome": None,
                                    "claim": {
                                        "claim_id": claim_id,
                                        "revision": 3,
                                    },
                                },
                            }
                            for index in range(40)
                        ],
                    },
                }
            )
            terminal_batch = json.dumps(
                {
                    "ok": True,
                    "data": {
                        "schema_version": "agent-session.broker-proof.v1",
                        "session_id": "managed-session",
                        "session_incarnation": "incarnation-1",
                        "generation": 1,
                        "proofs": [
                            {
                                "index": index,
                                "ok": True,
                                "proof": {
                                    "kind": "operation",
                                    "found": True,
                                    "lease_id": "lease-1",
                                    "state": "completed",
                                    "revision": 2,
                                    "outcome": "pass",
                                    "claim": {
                                        "claim_id": claim_id,
                                        "revision": 3,
                                    },
                                },
                            }
                            for index in range(40)
                        ],
                    },
                }
            )
            agent_session.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.25.11'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* || "$*" == *"broker status"* || "$*" == *"broker proof"* ]]; then
  [[ " $* " == *" --state-dir {shlex.quote(str(state_dir))} "* ]] || exit 65
  [[ " $* " == *" --session managed-session "* ]] || exit 66
  [[ " $* " == *" --capability-file {shlex.quote(str(capability))} "* ]] || exit 67
  printf '%s\\n' "$*" >> {shlex.quote(str(calls))}
fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.work-context.v1","session_id":"managed-session","session_incarnation":"incarnation-1","claim_id":"{claim_id}","revision":3,"state":"active"}}}}'
  exit 0
fi
if [[ "$*" == *"work-context check"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.conflict-evaluation.v1","classification":"clear","complete":true,"reasons":[],"peers":[]}}}}'
  exit 0
fi
if [[ "$*" == *"work-context admit"* ]]; then
  printf '%s\\n' '{{"ok":true,"data":{{"schema_version":"agent-session.operation-lease.v1","lease_id":"lease-1","claim_id":"{claim_id}","claim_revision":3,"revision":1,"state":"active"}}}}'
  exit 0
fi
if [[ "$*" == *"broker status"* ]]; then
  active=1
  [[ -f {shlex.quote(str(reconciled))} ]] && active=0
  printf '{{"ok":true,"data":{{"schema_version":"agent-session.coordination-broker.v1","session_id":"managed-session","state":"ready","generation":1,"capability_available":true,"heartbeat_fresh":true,"claim":{{"claim_id":"{claim_id}","revision":3,"state":"active"}},"operation":{{"active":%s,"uncertain":0}}}}}}\\n' "$active"
  exit 0
fi
if [[ "$*" == *"broker proof"* ]]; then
  if [[ -f {shlex.quote(str(reconciled))} ]]; then
    printf '%s\\n' {shlex.quote(terminal_batch)}
  else
    printf '%s\\n' {shlex.quote(active_batch)}
  fi
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            capability.write_text("secret\n", encoding="utf-8")
            capability.chmod(0o600)
            runtime_state = root / "runtime-state"
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(runtime_state),
                "AGENT_SESSION_ID": "managed-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability),
                "AGENT_SESSION_STATE_DIR": str(state_dir),
                "AGENT_SESSION_COORDINATION_MODE": "enforce",
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            for index in range(40):
                pre = write_payload("src/lib.rs", "fn main() {}\n")
                pre.update(
                    {
                        "session_id": "product-session",
                        "tool_use_id": f"externally-reconciled-tool-{index}",
                        "hook_event_name": "PreToolUse",
                    }
                )
                code, decision, stderr = run_enforced_hook(
                    "session-coordination-guard.py", pre, cwd=repo, env=env
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)
            calls.write_text("", encoding="utf-8")
            stop = {
                "hook_event_name": "Stop",
                "session_id": "product-session",
            }
            code, pending, stderr = run_enforced_hook(
                "session-coordination-guard.py", stop, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertIn("does not release or guess", str(pending))
            self.assertEqual(
                calls.read_text(encoding="utf-8").count("broker status"), 1
            )
            self.assertEqual(
                calls.read_text(encoding="utf-8").count("broker proof"), 1
            )
            self.assertNotIn("work-context show", calls.read_text(encoding="utf-8"))

            reconciled.touch()
            code, reconciled_stop, stderr = run_enforced_hook(
                "session-coordination-guard.py", stop, cwd=repo, env=env
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(
                reconciled_stop,
                {
                    "schema_version": "runtime-kit.session-coordination-result.v1",
                    "status": "clean",
                },
            )
            call_text = calls.read_text(encoding="utf-8")
            self.assertEqual(call_text.count("broker status"), 2)
            self.assertEqual(call_text.count("broker proof"), 2)
            self.assertNotIn("work-context show", call_text)
            namespace = runtime_state / "session-coordination" / hashlib.sha256(
                b"managed-session"
            ).hexdigest()
            self.assertEqual(list(namespace.glob("*.json")), [])
            self.assertEqual(list(namespace.glob("*.token")), [])
            self.assertEqual(list(namespace.glob("*.outcome")), [])


    def test_session_coordination_malformed_version_degrades_safely(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_version_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        malformed = subprocess.CompletedProcess(
            ["agent-session", "--version"],
            0,
            stdout="unknown build\n",
            stderr="",
        )
        with mock.patch.object(guard, "run_cli", return_value=malformed):
            self.assertFalse(
                guard.coordination_capability("/trusted/agent-session", "enforce")
            )


    def test_session_coordination_guard_unmanaged_and_read_only_degrade_safely(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            for payload in (
                write_payload("src/lib.rs", "fn main() {}\n"),
                command_payload("git status --short"),
            ):
                payload["hook_event_name"] = "PreToolUse"
                payload["session_id"] = "unmanaged-product-session"
                code, decision, stderr = run_hook(
                    "session-coordination-guard.py",
                    payload,
                    cwd=repo,
                    env={
                        "AGENT_RUNTIME_PRODUCT": "codex",
                        "AGENT_SESSION_ID": "",
                        "AGENT_SESSION_CAPABILITY_FILE": "",
                        "AGENT_SESSION_STATE_DIR": "",
                    },
                )
                self.assertEqual(code, 0, stderr)
                self.assert_allowed(decision)


    def test_session_coordination_target_extraction_fails_closed_across_boundaries(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_guard_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo-a"
            other = root / "repo-b"
            for path, remote in (
                (repo, "https://example.invalid/example/repo-a.git"),
                (other, "https://example.invalid/example/repo-b.git"),
            ):
                path.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=path, check=True)
                subprocess.run(
                    ["git", "remote", "add", "origin", remote], cwd=path, check=True
                )

            cases = (
                (root, "touch outside.txt", "outside-governed-repository"),
                (repo, f"git -C {other} add README.md", "cross-repository-shell-target"),
                (repo, f"cp README.md {other / 'copy.md'}", "cross-repository-shell-target"),
                (repo, f"semantic-commit --repo {other} --message x", "cross-repository-shell-target"),
                (repo, "env GH_REPO=other/repo gh pr edit 12 --title x", "provider-target-unresolved"),
                (
                    repo,
                    "env -S 'GH_REPO=other/repo gh pr edit 12 --title x'",
                    "provider-target-unresolved",
                ),
                (
                    repo,
                    "sh -c 'gh -R other/repo pr edit 12 --title x'",
                    "provider-target-unresolved",
                ),
                (
                    repo,
                    f"cd {other} && touch escaped.txt",
                    "shell-target-unresolved",
                ),
                (
                    repo,
                    f"printf x > {other / 'redirected.txt'}",
                    "shell-target-unresolved",
                ),
                (
                    repo,
                    f"bash -c 'printf x > {other / 'nested-redirected.txt'}'",
                    "shell-target-unresolved",
                ),
                (
                    repo,
                    f"bash -c 'cp README.md {other / 'nested-copy.md'}'",
                    "cross-repository-shell-target",
                ),
                (
                    repo,
                    f"bash -O extglob -c 'cp README.md {other / 'nested-option-copy.md'}'",
                    "cross-repository-shell-target",
                ),
                (
                    repo,
                    f"command bash -c 'cp README.md {other / 'nested-command-copy.md'}'",
                    "cross-repository-shell-target",
                ),
                (
                    repo,
                    f"env bash -c 'cp README.md {other / 'nested-env-copy.md'}'",
                    "cross-repository-shell-target",
                ),
            )
            prior = Path.cwd()
            try:
                for cwd, command, reason in cases:
                    with self.subTest(command=command):
                        os.chdir(cwd)
                        operation, result = guard.operation_targets(
                            command_payload(command), "Bash"
                        )
                        self.assertIsNone(operation)
                        self.assertEqual(result, reason)
            finally:
                os.chdir(prior)

            recovery = guard.mutation_target_recovery(
                "cross-repository-shell-target"
            )
            self.assertIn("top-level `workdir`", recovery)
            self.assertIn("`git add -- <owned-paths>`", recovery)
            self.assertIn("target-rooted managed session", recovery)

            os.chdir(repo)
            try:
                operation, result = guard.operation_targets(
                    command_payload(
                        "forge-cli --provider github --repo other/repo "
                        "pr edit 12 --title x"
                    ),
                    "Bash",
                )
            finally:
                os.chdir(prior)
            self.assertEqual(operation, "provider-pr")
            self.assertEqual(
                result["provider_refs"],
                [{"kind": "pr", "repository": "other/repo", "number": 12}],
            )
            operation, result = guard.operation_targets(
                command_payload("gh -Rother/repo issue edit 9 --title x"), "Bash"
            )
            self.assertEqual(operation, "provider-issue")
            self.assertEqual(result["provider_refs"][0]["repository"], "other/repo")
            operation, result = guard.operation_targets(
                command_payload(
                    "gh pr edit https://github.com/third/project/pull/21 --title x"
                ),
                "Bash",
            )
            self.assertEqual(operation, "provider-pr")
            self.assertEqual(
                result["provider_refs"],
                [{"kind": "pr", "repository": "third/project", "number": 21}],
            )
            operation, reason = guard.operation_targets(
                command_payload("gh pr edit --milestone 2026 --title x"), "Bash"
            )
            self.assertIsNone(operation)
            self.assertEqual(reason, "provider-pr-unresolved")



    def test_session_coordination_handler_has_no_retired_checkpoint_capability(
        self,
    ) -> None:
        completed = subprocess.run(
            [
                str(HOOK_DIR / "session-coordination-guard.py"),
                "--capabilities",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": "runtime-kit.handler-capabilities.v1",
                "capabilities": {},
            },
        )


    def test_session_coordination_preserves_uncertain_admit_and_records_post_offline(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_durability_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            namespace = Path(tmp)
            operation_key = hashlib.sha256(b"offline-post").hexdigest()
            record_path = namespace / f"{operation_key}.json"
            token = namespace / f"{operation_key}.attempt.token"
            targets = namespace / f"{operation_key}.attempt.targets.json"
            outcome = namespace / f"{operation_key}.attempt.outcome"
            token.write_text("execution-token\n", encoding="utf-8")
            targets.write_text(
                '{"schema_version":"agent-session.operation-targets.v1"}\n',
                encoding="utf-8",
            )
            for path in (token, targets):
                path.chmod(0o600)
            record = {
                "schema_version": "agent-runtime-kit.session-coordination-operation.v1",
                "phase": "admitting",
                "session": "managed-session",
                "capability_file": str(namespace / "capability"),
                "state_dir": str(namespace / "state"),
                "claim_id": "claim-1",
                "claim_revision": 3,
                "session_incarnation": "incarnation-1",
                "operation": "edit",
                "token_file": str(token),
                "targets_file": str(targets),
                "outcome_file": str(outcome),
                "outcome": None,
                "admit_idempotency": "stable-admit-key",
                "complete_idempotency": "stable-complete-key",
            }
            record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            record_path.chmod(0o600)
            lost = subprocess.CompletedProcess([], 1, stdout="", stderr="lost")
            with mock.patch.object(guard, "run_cli", return_value=lost) as run:
                status, reason = guard.submit_admission(
                    "agent-session", record_path, record
                )
                self.assertEqual((status, reason), ("uncertain", "coordination-unavailable"))
                self.assertTrue(record_path.exists())
                self.assertTrue(token.exists())
                self.assertTrue(targets.exists())
                self.assertEqual(run.call_count, 1)
                self.assertIn("stable-admit-key", run.call_args.args[0])

            active = dict(record, phase="active", lease_id="lease-1", lease_revision=1)
            record_path.write_text(json.dumps(active) + "\n", encoding="utf-8")
            self.assertEqual(active["phase"], "active")
            payload = {
                "tool_use_id": "offline-post",
                "hook_event_name": "PostToolUse",
                "tool_response": {"exit_code": 0},
            }
            with mock.patch.object(guard, "private_namespace", return_value=namespace):
                code = guard._post_tool_locked(
                    payload,
                    executable=None,
                    managed_session="managed-session",
                    product="codex",
                    event="PostToolUse",
                )
            self.assertEqual(code, 0)
            self.assertEqual(outcome.read_text(encoding="utf-8"), "pass\n")

            stale_path = namespace / "stale.json"
            stale_token = namespace / "stale.token"
            stale_targets = namespace / "stale.targets.json"
            stale_outcome = namespace / "stale.outcome"
            stale_token.write_text("execution-token\n", encoding="utf-8")
            stale_targets.write_text(
                '{"schema_version":"agent-session.operation-targets.v1"}\n',
                encoding="utf-8",
            )
            stale = dict(record)
            stale.update(
                {
                    "token_file": str(stale_token),
                    "targets_file": str(stale_targets),
                    "outcome_file": str(stale_outcome),
                }
            )
            stale_path.write_text(json.dumps(stale) + "\n", encoding="utf-8")
            conflict = subprocess.CompletedProcess(
                [],
                1,
                stdout=json.dumps(
                    {"ok": False, "error": {"code": "claim-revision-conflict"}}
                ),
                stderr="",
            )
            with mock.patch.object(guard, "run_cli", return_value=conflict):
                status, reason = guard.submit_admission(
                    "agent-session", stale_path, stale
                )
            self.assertEqual((status, reason), ("rejected", "claim-revision-conflict"))
            self.assertFalse(stale_path.exists())
            self.assertFalse(stale_token.exists())
            self.assertFalse(stale_targets.exists())


    def test_session_coordination_read_only_bypass_rejects_write_flags_and_shadows(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_readonly_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        agent_session = shutil.which("agent-session") or "/usr/bin/false"
        with tempfile.TemporaryDirectory() as tmp:
            trusted_bin = Path(tmp)
            trusted_rg = trusted_bin / "rg"
            trusted_rg.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            trusted_rg.chmod(0o755)
            trusted_env = {
                "PATH": f"{trusted_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(trusted_bin),
            }
            with mock.patch.dict(os.environ, trusted_env):
                self.assertTrue(
                    guard.command_bypasses_admission(
                        "rg --no-config TODO . | head -n 5", agent_session
                    )
                )
                self.assertTrue(
                    guard.command_bypasses_admission(
                        "nl -ba README.md | sed -n '1,5p'", agent_session
                    )
                )
                for command in (
                    "rg TODO .",
                    "rg --no-config --pre cat TODO .",
                    "rg --no-config --hostname-bin ./evil TODO .",
                    "rg --no-config --hostname-bin=./evil TODO .",
                    "rg --no-config --search-zip TODO archive.gz",
                    "rg --no-config -z TODO archive.gz",
                    "rg --no-config -Hz TODO archive.gz",
                    "rg TODO . -- --no-config",
                    "rg --no-config TODO . || head -n 1 README.md",
                    "cat README.md > copy.md",
                    "cat README.md | tee copy.md",
                    "cat $(pwd)/README.md",
                    "echo 'read\\' ; touch owned ; echo 'tail\\'",
                    "nl -ba README.md | sed -n '1,5e touch owned'",
                ):
                    with self.subTest(unsafe_pipeline=command):
                        self.assertFalse(
                            guard.command_bypasses_admission(command, agent_session)
                        )
        self.assertFalse(guard.command_bypasses_admission("git status --short", agent_session))
        self.assertFalse(
            guard.command_bypasses_admission("git blame README.md", agent_session)
        )
        self.assertFalse(
            guard.command_bypasses_admission(
                "git --paginate rev-parse --show-toplevel", agent_session
            )
        )
        self.assertFalse(
            guard.command_bypasses_admission(
                "git diff --output=/tmp/session-coordination-write", agent_session
            )
        )
        self.assertFalse(
            guard.command_bypasses_admission("git diff --ext-diff", agent_session)
        )
        self.assertFalse(
            guard.command_bypasses_admission(
                "git cat-file --filters HEAD:README.md", agent_session
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            shadow = Path(tmp) / "git"
            shadow.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            shadow.chmod(0o755)
            self.assertFalse(
                guard.command_bypasses_admission(f"{shadow} status", agent_session)
            )


    def test_session_coordination_guard_allows_only_exact_literal_claim_bootstrap(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.24.5'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)

            private_dir = root / "private"
            private_dir.mkdir()
            claim_file = private_dir / "work-context.json"
            claim_file.write_text("{}\n", encoding="utf-8")
            claim_file.chmod(0o600)
            repository_claim_file = repo / "work-context.json"
            repository_claim_file.write_text("{}\n", encoding="utf-8")
            repository_claim_file.chmod(0o600)
            capability_file = private_dir / "capability"
            capability_file.write_text("fixture\n", encoding="utf-8")
            capability_file.chmod(0o600)
            foreign_capability_file = private_dir / "foreign-capability"
            foreign_capability_file.write_text("fixture\n", encoding="utf-8")
            foreign_capability_file.chmod(0o600)

            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
                "AGENT_SESSION_ID": "managed-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability_file.resolve()),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            literal_claim = (
                "agent-session work-context claim "
                '--session "$AGENT_SESSION_ID" '
                f"--file {claim_file.resolve()} "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key claim-bootstrap-0001 --format json"
            )
            revision_fenced_claim = literal_claim.replace(
                f"--file {claim_file.resolve()} ",
                f"--file {claim_file.resolve()} --if-revision 1 ",
            )
            expanded_claim = (
                "agent-session work-context claim "
                "--session managed-session "
                f"--file {claim_file.resolve()} "
                f"--capability-file {capability_file.resolve()} "
                "--idempotency-key claim-bootstrap-0001 --format json"
            )

            for index, command in enumerate((literal_claim, revision_fenced_claim)):
                with self.subTest(allowed=command):
                    payload = command_payload(command)
                    payload.update(
                        {
                            "cwd": str(repo),
                            "session_id": "product-session",
                            "tool_use_id": f"literal-claim-allowed-{index}",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_enforced_hook(
                        "session-coordination-guard.py", payload, cwd=repo, env=env
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            blocked = (
                literal_claim.replace("$AGENT_SESSION_ID", "$OTHER_SESSION_ID"),
                literal_claim.replace(
                    "$AGENT_SESSION_CAPABILITY_FILE", "$OTHER_CAPABILITY_FILE"
                ),
                literal_claim.replace('"$AGENT_SESSION_ID"', "$AGENT_SESSION_ID"),
                literal_claim.replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    "$AGENT_SESSION_CAPABILITY_FILE",
                ),
                literal_claim.replace(
                    "--idempotency-key claim-bootstrap-0001 --format json",
                    "--format json --idempotency-key claim-bootstrap-0001",
                ),
                literal_claim + " --if-revision 1",
                expanded_claim.replace(
                    "--session managed-session", "--session foreign-session"
                ),
                expanded_claim.replace(
                    str(capability_file.resolve()),
                    str(foreign_capability_file.resolve()),
                ),
                literal_claim.replace(
                    str(claim_file.resolve()), str(repository_claim_file.resolve())
                ),
            )
            for index, command in enumerate(blocked):
                with self.subTest(blocked=command):
                    payload = command_payload(command)
                    payload.update(
                        {
                            "cwd": str(repo),
                            "session_id": "product-session",
                            "tool_use_id": f"literal-claim-blocked-{index}",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_enforced_hook(
                        "session-coordination-guard.py",
                        payload,
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_blocked(decision, "active work-context claim")



    def test_session_coordination_guard_allows_only_exact_projected_lifecycle_commands(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    "https://example.invalid/example/repo.git",
                ],
                cwd=repo,
                check=True,
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            agent_session = bin_dir / "agent-session"
            agent_session.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"--version"* ]]; then echo 'agent-session 1.24.5'; exit 0; fi
if [[ "$*" == *"work-context --help"* ]]; then echo 'show check admit complete reconcile'; exit 0; fi
if [[ "$*" == *"work-context show"* ]]; then
  printf '%s\n' '{"ok":true,"data":{"schema_version":"agent-session.work-context.v1","session_id":"managed-session","session_incarnation":"incarnation-1","claim_id":"claim-1","revision":3,"state":"active"}}'
  exit 0
fi
if [[ "$*" == *"work-context check"* ]]; then
  printf '%s\n' '{"ok":true,"data":{"schema_version":"agent-session.conflict-evaluation.v1","classification":"clear","complete":true,"reasons":[],"peers":[]}}'
  exit 0
fi
exit 64
""",
                encoding="utf-8",
            )
            agent_session.chmod(0o755)
            shadow_dir = root / "shadow"
            shadow_dir.mkdir()
            shadow_agent_session = shadow_dir / "agent-session"
            shadow_agent_session.write_text(
                "#!/usr/bin/env bash\nexit 0\n",
                encoding="utf-8",
            )
            shadow_agent_session.chmod(0o755)
            alias_dir = root / "alias"
            alias_dir.mkdir()
            alias_agent_session = alias_dir / "agent-session"
            alias_agent_session.symlink_to(agent_session)
            attacker_dir = root / "attacker"
            attacker_child = attacker_dir / "child"
            attacker_bin = attacker_dir / "bin"
            attacker_child.mkdir(parents=True)
            attacker_bin.mkdir()
            attacker_agent_session = attacker_bin / "agent-session"
            attacker_agent_session.write_text(
                "#!/usr/bin/env bash\nexit 0\n",
                encoding="utf-8",
            )
            attacker_agent_session.chmod(0o755)
            dot_segment_alias = root / "dot-segment-alias"
            dot_segment_alias.symlink_to(attacker_child, target_is_directory=True)
            relative_agent_session = repo / "agent-session"
            relative_agent_session.symlink_to(agent_session)

            capability_file = root / "capability"
            capability_file.write_text("fixture\n", encoding="utf-8")
            capability_file.chmod(0o600)
            foreign_capability_file = root / "foreign-capability"
            foreign_capability_file.write_text("fixture\n", encoding="utf-8")
            foreign_capability_file.chmod(0o600)
            targets_file = root / "operation-targets.json"
            targets_file.write_text("{}\n", encoding="utf-8")
            token_file = root / "execution-token"
            token_file.write_text("fixture-token\n", encoding="utf-8")
            token_file.chmod(0o600)
            proof_file = root / "reconcile-proof.json"
            proof_file.write_text("{}\n", encoding="utf-8")
            body_file = root / "message-body"
            body_file.write_text("fixture body\n", encoding="utf-8")
            body_file.chmod(0o600)
            repository_proof = repo / "proof.json"
            repository_proof.write_text("{}\n", encoding="utf-8")
            repository_body = repo / "message-body"
            repository_body.write_text("fixture body\n", encoding="utf-8")
            repository_token = repo / "execution-token"
            repository_token.write_text("fixture-token\n", encoding="utf-8")
            env = {
                "AGENT_RUNTIME_PRODUCT": "codex",
                "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
                "AGENT_RUNTIME_STATE_HOME": str(root / "runtime-state"),
                "AGENT_SESSION_ID": "managed-session",
                "AGENT_SESSION_CAPABILITY_FILE": str(capability_file.resolve()),
                "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            projected_check = (
                "agent-session work-context check --self "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --format json'
            )
            projected_show = (
                "agent-session work-context show "
                '--session "$AGENT_SESSION_ID" '
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --format json'
            )
            projected_status = (
                "agent-session broker status "
                '--session "$AGENT_SESSION_ID" '
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --format json'
            )
            projected_renew = (
                "agent-session work-context renew "
                '--session "$AGENT_SESSION_ID" --claim claim-1234 '
                "--if-revision 7 "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key renew-key-0001 --format json"
            )
            projected_release = projected_renew.replace(
                "work-context renew", "work-context release"
            ).replace("renew-key-0001", "release-key-0001")
            projected_admit = (
                "agent-session work-context admit "
                '--session "$AGENT_SESSION_ID" --claim claim-1234 '
                f"--if-revision 7 --targets-file {targets_file.resolve()} "
                f"--operation shell-mutation --execution-token-file {token_file.resolve()} "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key admit-key-0001 --format json"
            )
            projected_complete = (
                "agent-session work-context complete "
                '--session "$AGENT_SESSION_ID" --lease lease-1234 '
                f"--if-revision 3 --execution-token-file {token_file.resolve()} "
                "--outcome pass "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key complete-key-0001 --format json"
            )
            projected_reconcile = (
                "agent-session work-context reconcile "
                '--session "$AGENT_SESSION_ID" --lease lease-1234 '
                f"--if-revision 4 --proof-file {proof_file.resolve()} "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key reconcile-key-0001 --format json"
            )
            projected_send = (
                "agent-session message send "
                '--from "$AGENT_SESSION_ID" --to worker-session '
                f"--body-file {body_file.resolve()} "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key message-send-0001 "
                "--reply-to message-1234 --expires-in 15m --format json"
            )
            projected_inbox = (
                "agent-session message inbox "
                '--session "$AGENT_SESSION_ID" '
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--state unread --cursor cursor-1234 --limit 50 --format json"
            )
            projected_message_show = (
                "agent-session message show "
                '--session "$AGENT_SESSION_ID" --message message-1234 '
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --format json'
            )
            projected_ack = (
                "agent-session message ack "
                '--session "$AGENT_SESSION_ID" --message message-1234 '
                "--if-revision 2 "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key message-ack-0001 --format json"
            )
            projected_reply = (
                "agent-session message reply "
                '--session "$AGENT_SESSION_ID" --message message-1234 '
                f"--if-revision 2 --body-file {body_file.resolve()} "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                "--idempotency-key message-reply-0001 --format json"
            )
            projected_wait = (
                "agent-session message wait "
                '--session "$AGENT_SESSION_ID" --message message-1234 '
                "--if-revision 2 --timeout 30s "
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --format json'
            )

            bare_projected_commands = (
                projected_check,
                projected_show,
                projected_status,
                projected_renew,
                projected_release,
                projected_admit,
                projected_complete,
                projected_reconcile,
                projected_send,
                projected_send.replace(
                    " --reply-to message-1234 --expires-in 15m", ""
                ),
                projected_inbox,
                projected_inbox.replace(
                    " --state unread --cursor cursor-1234 --limit 50", ""
                ),
                projected_message_show,
                projected_ack,
                projected_reply,
                projected_wait,
            )
            pinned_projected_commands = tuple(
                command.replace(
                    "agent-session",
                    str(agent_session.resolve()),
                    1,
                )
                for command in bare_projected_commands
            )

            for index, command in enumerate(
                (*bare_projected_commands, *pinned_projected_commands)
            ):
                with self.subTest(allowed=command):
                    payload = command_payload(command)
                    payload.update(
                        {
                            "cwd": str(repo),
                            "session_id": "product-session",
                            "tool_use_id": f"projected-lifecycle-allowed-{index}",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_enforced_hook(
                        "session-coordination-guard.py",
                        payload,
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    self.assert_allowed(decision)

            blocked = (
                projected_check.replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    '"$OTHER_CAPABILITY_FILE"',
                ),
                projected_show.replace('"$AGENT_SESSION_ID"', '"$OTHER_SESSION_ID"'),
                projected_show.replace('"$AGENT_SESSION_ID"', "foreign-session").replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    str(capability_file.resolve()),
                ),
                projected_show.replace('"$AGENT_SESSION_ID"', "managed-session").replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    str(foreign_capability_file.resolve()),
                ),
                projected_renew.replace('"$AGENT_SESSION_ID"', "managed-session").replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    str(capability_file.resolve()),
                ),
                projected_show.replace('"$AGENT_SESSION_ID"', "$AGENT_SESSION_ID"),
                projected_show.replace(
                    '"$AGENT_SESSION_CAPABILITY_FILE"',
                    "$AGENT_SESSION_CAPABILITY_FILE",
                ),
                projected_show.replace(
                    '--session "$AGENT_SESSION_ID" '
                    '--capability-file "$AGENT_SESSION_CAPABILITY_FILE"',
                    '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" '
                    '--session "$AGENT_SESSION_ID"',
                ),
                projected_show.replace(
                    " --format json",
                    " --host untrusted --format json",
                ),
                projected_show.replace(
                    " --format json",
                    f" --state-dir {root / 'other-state'} --format json",
                ),
                projected_show + " extra",
                projected_check.replace("--self", "--candidate candidate.json"),
                projected_show.replace("work-context show", "work-context renew"),
                projected_show.replace("work-context show", "work-context release"),
                projected_renew.replace("claim-1234", "../foreign-claim"),
                projected_renew.replace("--if-revision 7", "--if-revision -1"),
                projected_renew.replace("--if-revision 7", "--if-revision 01"),
                projected_renew.replace(
                    "--if-revision 7", "--if-revision 18446744073709551616"
                ),
                projected_renew.replace("renew-key-0001", "short"),
                projected_admit.replace(
                    str(token_file.resolve()), str(repository_token.resolve())
                ),
                projected_complete.replace("--outcome pass", "--outcome unknown"),
                projected_reconcile.replace(
                    str(proof_file.resolve()), str(repository_proof.resolve())
                ),
                projected_send.replace(
                    str(body_file.resolve()), str(repository_body.resolve())
                ),
                projected_send.replace("--expires-in 15m", "--expires-in 8d"),
                projected_inbox.replace("--state unread", "--state deleted"),
                projected_inbox.replace("cursor-1234", "../foreign-cursor"),
                projected_inbox.replace("--limit 50", "--limit 101"),
                projected_wait.replace("--timeout 30s", "--timeout 61s"),
                projected_ack.replace(
                    '--session "$AGENT_SESSION_ID"',
                    '--session "$AGENT_SESSION_ID" --session "$AGENT_SESSION_ID"',
                ),
                projected_send.replace("agent-session", "foreign-agent-session", 1),
                projected_release.replace(
                    "agent-session",
                    str(shadow_agent_session.resolve()),
                    1,
                ),
                projected_release.replace(
                    "agent-session",
                    str(alias_agent_session),
                    1,
                ),
                projected_release.replace(
                    "agent-session",
                    f"{dot_segment_alias}/../bin/agent-session",
                    1,
                ),
                projected_release.replace("agent-session", "./agent-session", 1),
                f"sh -c '{projected_show}'",
                projected_show + " | cat",
                projected_show + f" > {root / 'status.json'}",
                f'echo "$(agent-session work-context show '
                '--session "$AGENT_SESSION_ID" '
                '--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --format json)"',
            )
            for index, command in enumerate(blocked):
                with self.subTest(blocked=command):
                    payload = command_payload(command)
                    payload.update(
                        {
                            "cwd": str(repo),
                            "session_id": "product-session",
                            "tool_use_id": f"projected-lifecycle-blocked-{index}",
                            "hook_event_name": "PreToolUse",
                        }
                    )
                    code, decision, stderr = run_enforced_hook(
                        "session-coordination-guard.py",
                        payload,
                        cwd=repo,
                        env=env,
                    )
                    self.assertEqual(code, 0, stderr)
                    fragment = (
                        "coordination-lifecycle-untrusted"
                        if command.startswith("agent-session") and "$" not in command
                        else "shell-target-unresolved"
                    )
                    self.assert_blocked(decision, fragment)


    def test_session_coordination_effect_avoids_git_probe_for_non_mutations(
        self,
    ) -> None:
        spec = importlib.util.spec_from_file_location(
            "session_coordination_effect_under_test",
            HOOK_DIR / "session-coordination-guard.py",
        )
        assert spec is not None and spec.loader is not None
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        agent_session = shutil.which("agent-session") or "/usr/bin/false"
        with mock.patch.object(guard, "bounded_git_toplevel") as git_root:
            read_only = guard.command_effect(
                "cat README.md | head -n 5", agent_session, Path.cwd()
            )
            unknown = guard.command_effect(
                "python3 -c 'print(1)'", agent_session, Path.cwd()
            )
        self.assertEqual(read_only.kind, "read-only")
        self.assertEqual(unknown.kind, "unknown")
        git_root.assert_not_called()


    def test_session_coordination_guard_registration_matches_supported_products(
        self,
    ) -> None:
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
            for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
                registered = inventory_tools(
                    inventory_rules(
                        product=product,
                        event=event,
                        capability="agent-session.coordination.v1",
                    )
                )
                self.assertEqual(registered, expected, f"{product}:{event}")
            stop = inventory_rules(
                product=product,
                event="Stop",
                capability="agent-session.coordination.v1",
            )
            self.assertEqual(len(stop), 1, product)
            self.assertIsNone(stop[0]["matcher"])


    def test_session_coordination_guard_classifies_launcher_adoption_as_mutation(
        self,
    ) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "session_coordination_guard_launcher",
            HOOK_DIR / "session-coordination-guard.py",
        )
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        launcher = str(HOOK_DIR / "checkout-lease-guard.py")
        self.assertTrue(
            module.invocation_is_recognized_mutation(
                [launcher, "adopt-dirty", "--reason-file", "/tmp/reason.txt"],
                None,
            )
        )
        self.assertFalse(
            module.invocation_is_recognized_mutation([launcher, "--help"], None)
        )

