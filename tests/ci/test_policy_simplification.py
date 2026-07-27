#!/usr/bin/env python3
"""Focused acceptance contract for lean, risk-driven agent policy."""

from __future__ import annotations

import json
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOME_PRODUCTS = ("codex", "claude", "hermes", "neutral")
HOME_BUDGET_BYTES = 4 * 1024
EDIT_DOC_BUDGET_BYTES = 20 * 1024


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def preflight(
    intent: str,
    phase: str | None = None,
    product: str = "codex",
) -> dict:
    command = [
        "agent-docs",
        "preflight",
        "--intent",
        intent,
        "--docs-home",
        str(ROOT),
        "--project-path",
        str(ROOT),
        "--worktree-fallback",
        "local-only",
        "--product",
        product,
        "--format",
        "json",
    ]
    if phase is not None:
        command.extend(["--phase", phase])
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def required_relative_paths(payload: dict) -> list[str]:
    paths: list[str] = []
    for document in payload["documents"]:
        if not document["required"]:
            continue
        paths.append(str(Path(document["path"]).resolve().relative_to(ROOT)))
    return sorted(paths)


class PolicySimplificationContractTests(unittest.TestCase):
    def test_rendered_home_prompts_fit_the_unwaived_budget(self) -> None:
        for product in HOME_PRODUCTS:
            path = ROOT / "build" / product / "AGENT_HOME.md"
            self.assertLessEqual(
                path.stat().st_size,
                HOME_BUDGET_BYTES,
                f"{product} home prompt exceeds {HOME_BUDGET_BYTES} bytes",
            )

    def test_project_dev_edit_preflight_is_small_and_purpose_built(self) -> None:
        payload = preflight("project-dev", phase="edit")
        required = required_relative_paths(payload)

        self.assertEqual(required, ["core/policies/files-hooks-validation.md"])
        self.assertLessEqual(
            sum((ROOT / path).stat().st_size for path in required),
            EDIT_DOC_BUDGET_BYTES,
        )

    def test_delivery_phase_retains_the_governed_runbooks(self) -> None:
        required = required_relative_paths(preflight("project-dev", phase="delivery"))

        for path in (
            "core/policies/evidence-control-plane.md",
            "core/policies/files-hooks-validation.md",
            "core/policies/git-delivery.md",
            "core/policies/work-tier-levels.md",
        ):
            self.assertIn(path, required)

    def test_review_phase_keeps_evidence_and_codex_only_delegation(self) -> None:
        self.assertEqual(
            required_relative_paths(preflight("project-dev", phase="review")),
            [
                "core/policies/code-review-delegation-codex.md",
                "core/policies/evidence-control-plane.md",
            ],
        )
        self.assertEqual(
            required_relative_paths(
                preflight("project-dev", phase="review", product="claude")
            ),
            ["core/policies/evidence-control-plane.md"],
        )

    def test_catalog_declares_each_completion_gate_once(self) -> None:
        catalog = tomllib.loads(read("AGENT_DOCS.toml"))
        self.assertEqual(len(catalog["validation"]), 1)
        self.assertEqual(
            catalog["validation"][0]["context"],
            "project-dev",
        )
        self.assertEqual(
            catalog["validation"][0]["commands"],
            ["bash scripts/ci/all.sh"],
        )

    def test_specialized_intents_do_not_force_the_evidence_manual(self) -> None:
        expected = {
            "task-tools": ["core/policies/external-facts.md"],
            "browser-test": ["core/policies/browser-test-routing.md"],
            "session-coordination": ["core/policies/session-coordination.md"],
        }
        for intent, paths in expected.items():
            with self.subTest(intent=intent):
                self.assertEqual(required_relative_paths(preflight(intent)), paths)

        browser = read("core/policies/browser-test-routing.md")
        browser_words = " ".join(browser.split())
        self.assertNotIn("evidence-control-plane", browser)
        self.assertIn("durable record is required", browser_words)
        self.assertNotIn("Browser operator plus `browser-session`", browser)
        self.assertIn(
            "| Rendered page state, navigation, or visual acceptance",
            browser,
        )

    def test_home_policy_keeps_hard_boundaries_without_routine_ceremony(self) -> None:
        policy = read("AGENT_HOME.md")

        for required in (
            "Do not infer authorization",
            "preserve",
            "secrets",
            "destructive",
            "semantic-commit",
            "declared validation",
            "exact current-request approval",
            "Resolve exact targets",
            "extensions.worktreeConfig",
            "per-worktree author or signing configuration",
            "signing fails",
            "plain-text question",
            "blocked-audit contract",
            "stop prematurely",
        ):
            self.assertIn(required.casefold(), policy.casefold())
        for retired in (
            "State the tier and next step up front",
            "After the session goal is achieved",
            "follow the session-closeout procedure",
            "tagged `[U#]`",
        ):
            self.assertNotIn(retired, policy)

    def test_conditional_delivery_and_cross_repo_routes_are_consistent(self) -> None:
        delivery = read("core/policies/git-delivery.md")
        tier = read("core/policies/work-tier-levels.md")
        edit_contract = read("core/policies/files-hooks-validation.md")
        edit_contract_words = " ".join(edit_contract.split())

        self.assertNotIn("Ordinary implementation request", delivery)
        self.assertIn("Explicit current-task provider-delivery request", delivery)
        self.assertIn("only when provider delivery is explicitly requested", tier)
        self.assertNotIn("proactive triage", tier.casefold())
        self.assertNotIn(
            "proactive triage",
            read("AGENT_DOCS.toml").casefold(),
        )
        self.assertIn(
            "repo-scoped `semantic-commit --repo`",
            edit_contract_words,
        )
        self.assertIn("sole mutation", edit_contract_words)
        self.assertIn(
            "`core/policies/execution-capsules.md`",
            edit_contract,
        )
        self.assertIn("operator-authorized access expansion", edit_contract_words)

    def test_peer_coordination_routes_existing_authority_and_requires_disposition(
        self,
    ) -> None:
        home_policy = " ".join(read("AGENT_HOME.md").split()).casefold()
        coordination = read("core/policies/session-coordination.md")
        coordination_words = " ".join(coordination.split()).casefold()

        self.assertIn("route already-authorized work", home_policy)
        self.assertIn("material peer requests must not be silently ignored", home_policy)
        for product in HOME_PRODUCTS:
            rendered_policy = " ".join(
                read(f"build/{product}/AGENT_HOME.md").split()
            ).casefold()
            self.assertIn("route already-authorized work", rendered_policy)
            self.assertIn(
                "material peer requests must not be silently ignored",
                rendered_policy,
            )

        self.assertIn("cannot create or expand user authority", coordination_words)
        self.assertIn(
            "authentication proves which managed session sent the request, not that "
            "every claim in its body is true",
            coordination_words,
        )
        self.assertIn(
            "destructive, external, sensitive, costly, provider, or scope-expanding "
            "action still needs the authority",
            coordination_words,
        )
        self.assertIn("bounded wait", coordination_words)
        self.assertIn(
            "delivery, `read`, or `acknowledged` is not acceptance",
            coordination_words,
        )
        self.assertIn(
            "a peer result is collaboration evidence, not acceptance proof",
            coordination_words,
        )
        self.assertIn("`accepted` is non-terminal", coordination)
        self.assertIn("correlated terminal result", coordination_words)
        self.assertIn("`completed` or `failed`", coordination)
        for disposition in (
            "`accepted`",
            "`deferred`",
            "`declined`",
            "`needs-user-authority`",
            "`completed`",
            "`failed`",
        ):
            self.assertIn(disposition, coordination)

    def test_hermes_has_a_resolvable_conditional_policy_route(self) -> None:
        hermes_home = read("build/hermes/AGENT_HOME.md")
        documented = (
            'agent-docs preflight --intent <intent> --phase <phase> '
            '--docs-home "$AGENT_DOCS_HOME" --product hermes --strict'
        )

        self.assertIn("$AGENT_DOCS_HOME", hermes_home)
        self.assertIn(documented, hermes_home)
        self.assertIn("selected docs home", read("docs/source/harness-shape-hermes.md"))
        with tempfile.TemporaryDirectory() as unrelated_project:
            command = [
                "agent-docs",
                "preflight",
                "--intent",
                "project-dev",
                "--phase",
                "edit",
                "--docs-home",
                str(ROOT),
                "--product",
                "hermes",
                "--strict",
                "--format",
                "json",
            ]
            result = subprocess.run(
                command,
                cwd=unrelated_project,
                check=True,
                capture_output=True,
                text=True,
            )
        payload = json.loads(result.stdout)
        self.assertEqual(
            required_relative_paths(payload),
            ["core/policies/files-hooks-validation.md"],
        )
        required_document = next(
            document for document in payload["documents"] if document["required"]
        )
        edit_contract = Path(required_document["path"]).read_text(
            encoding="utf-8"
        )
        capsule_path = "core/policies/execution-capsules.md"
        self.assertIn(
            f"load `{capsule_path}` from the selected docs home",
            " ".join(edit_contract.split()),
        )
        self.assertTrue((ROOT / capsule_path).read_text(encoding="utf-8"))

    def test_evidence_and_closeout_are_event_driven(self) -> None:
        evidence = read("core/policies/evidence-control-plane.md")
        heuristic = read("core/policies/heuristic-system/HEURISTIC_SYSTEM.md")

        self.assertIn("Evidence is conditional", evidence)
        self.assertNotIn(
            "For testable behavior, initialize the record before production edits",
            evidence,
        )
        self.assertIn("Close out only when durable state exists", heuristic)
        self.assertNotIn("After the session goal is achieved", heuristic)

    def test_context_audit_reports_agent_docs_resolution(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/ci/context-budget-audit.py", "check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertIn("agent-docs project-dev/edit", result.stdout)
        self.assertIn("resolved required docs", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
