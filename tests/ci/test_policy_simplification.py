#!/usr/bin/env python3
"""Focused acceptance contract for lean, risk-driven agent policy."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOME_PRODUCTS = ("codex", "claude", "hermes", "neutral")
SHARED_HOME_PRODUCTS = ["codex", "claude", "hermes"]
HOME_PRODUCT_EXCEPTIONS = {
    "core/policies/code-review-delegation-codex.md": "codex",
}
HOME_BUDGET_BYTES = 4 * 1024 + 256
EDIT_DOC_BUDGET_BYTES = 20 * 1024
PRE_REPLACEMENT_EDIT_CONTEXT_BYTES = 8135
PROJECT_SKILL_CONTEXT_DELTA_BYTES = 2 * 1024


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class PolicySimplificationContractTests(unittest.TestCase):
    def test_test_first_tiers_agree_across_policy_surfaces(self) -> None:
        paths = [
            "AGENT_HOME.md", "DEVELOPMENT.md",
            "core/skills/conversation/guided-feature-build/SKILL.md.tera",
            "core/policies/session-coordination.md",
        ]
        paths.extend(f"build/{product}/AGENT_HOME.md" for product in HOME_PRODUCTS)
        paths.extend(
            f"build/{product}/plugins/conversation/skills/guided-feature-build/SKILL.md"
            for product in SHARED_HOME_PRODUCTS
        )
        for path in paths:
            text = " ".join(read(path).split())
            with self.subTest(path=path):
                for criterion in ("record", "before merge", "small UI tweaks", "spikes"):
                    self.assertTrue(criterion in text, f"{path}: missing {criterion!r}")
        guided = read("core/skills/conversation/guided-feature-build/SKILL.md.tera")
        self.assertNotIn("red or complete waiver before production edits", guided)
        coordination = read("core/policies/session-coordination.md")
        self.assertNotIn("capture a\nmeaningful red before production edits", coordination)

    def test_test_first_review_and_released_gate_ownership(self) -> None:
        for path in ("core/policies/files-hooks-validation.md",
                     "core/policies/evidence-control-plane.md"):
            text = " ".join(read(path).split())
            with self.subTest(path=path):
                self.assertIn("Review checks for deleted tests or weakened assertions", text)
        for path in ("core/policies/evidence-control-plane.md",
                     "core/policies/references/git-delivery.md"):
            text = read(path)
            with self.subTest(path=path):
                self.assertIn("1.36.11", text)
                self.assertIn("test_first.require_kinds", text)
                self.assertNotIn("per-kind setting lands", text)
                self.assertNotIn("gate does not yet", text.casefold())
                self.assertIn('require_kinds = ["bug"]', text)
                self.assertIn("cross-boundary feature contracts", text)

    def test_program_workflow_labels_distinguish_delivery_artifacts(self) -> None:
        def load_manifest(path: str) -> dict:
            result = subprocess.run(
                [
                    "ruby", "-ryaml", "-rjson", "-e",
                    "puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0)), aliases: true))",
                    str(ROOT / path),
                ],
                check=True, capture_output=True, text=True,
            )
            return json.loads(result.stdout)

        rules = load_manifest("manifests/forge-label-classification-rules.yaml")
        catalog = load_manifest("manifests/forge-labels.yaml")
        labels = {row["name"]: row for row in catalog["labels"]}
        smoke = read("tests/runtime-smoke/cases/dispatch/run.sh")
        tracker_body = smoke.split('tracker.md" <<\'BODY\'\n', 1)[1].split("\nBODY", 1)[0]
        child_body = smoke.split('child.md" <<BODY\n', 1)[1].split("\nBODY", 1)[0]
        fixtures = (
            ("issue", "Dispatch smoke tracker", tracker_body, "workflow::tracking"),
            ("issue", "Dispatch smoke lane A", child_body, "workflow::follow-up"),
            ("pr", "Dispatch lane A", child_body, "workflow::dispatch"),
            ("mr", "Dispatch lane A", child_body, "workflow::dispatch"),
        )
        for artifact, title, body, expected in fixtures:
            with self.subTest(artifact=artifact, expected=expected):
                text = f"{title}\n{body}".casefold()
                matches = [
                    rule["label"] for rule in rules["rules"]["workflow"]
                    if artifact in rule.get("applies_to", rules["scope"]["artifacts"])
                    and (
                        any(title.casefold().startswith(prefix.casefold())
                            for prefix in rule.get("title_prefixes", []))
                        or any(marker.casefold() in text for marker in rule.get("any", []))
                    )
                ]
                self.assertEqual(matches, [expected])
                self.assertIn(artifact, labels[expected]["applies_to"])
        self.assertEqual(labels["workflow::tracking"]["applies_to"], ["issue"])
        self.assertEqual(labels["workflow::dispatch"]["applies_to"], ["pr", "mr"])

    def test_rendered_home_prompts_fit_the_unwaived_budget(self) -> None:
        for product in HOME_PRODUCTS:
            path = ROOT / "build" / product / "AGENT_HOME.md"
            self.assertLessEqual(
                path.stat().st_size,
                HOME_BUDGET_BYTES,
                f"{product} home prompt exceeds {HOME_BUDGET_BYTES} bytes",
            )

    def test_edit_contract_is_small_and_routed_from_home(self) -> None:
        self.assertLessEqual(
            (ROOT / "core/policies/files-hooks-validation.md").stat().st_size,
            EDIT_DOC_BUDGET_BYTES,
        )
        for product in HOME_PRODUCTS:
            rendered = " ".join(read(f"build/{product}/AGENT_HOME.md").split())
            with self.subTest(product=product):
                self.assertIn("`files-hooks-validation.md` (edits, validation)", rendered)
                self.assertIn("`VALIDATION.toml` declares its finish-line validation", rendered)
                self.assertNotIn("agent-docs", rendered)
                self.assertNotIn("AGENT_DOCS", rendered)

    def test_edit_contract_maintains_affected_test_owners(self) -> None:
        edit_contract = " ".join(
            read("core/policies/files-hooks-validation.md").split()
        )

        self.assertIn(
            "Treat materially affected tests as part of the change",
            edit_contract,
        )
        self.assertIn(
            "add or update the lowest stable behavioral owner",
            edit_contract,
        )
        self.assertIn(
            "merge, refactor, or remove affected cases that no longer protect "
            "a distinct still-valid risk",
            edit_contract,
        )

    def test_delivery_routes_conditional_evidence(self) -> None:
        delivery = read("core/policies/git-delivery.md")
        self.assertIn("evidence-control-plane.md", delivery)
        self.assertIn("test-first", delivery)
        self.assertIn("handoff", delivery)

    def test_delivery_policies_are_bounded_and_keep_on_demand_owners(self) -> None:
        for policy, ceiling in (("git-delivery", 20 * 1024),
                                ("work-modes", 5 * 1024)):
            self.assertLessEqual((ROOT / f"core/policies/{policy}.md").stat().st_size,
                                 ceiling)
            self.assertIn(f"references/{policy}.md", read(f"core/policies/{policy}.md"))
            self.assertTrue(read(f"core/policies/references/{policy}.md"))

    def test_upstream_contribution_route_and_hard_boundaries_are_semantically_owned(
        self,
    ) -> None:
        for product in HOME_PRODUCTS:
            rendered = " ".join(
                read(f"build/{product}/AGENT_HOME.md").split()
            )
            self.assertIn("read `upstream-contribution.md`", rendered)
            self.assertIn("a human submits and signs DCO/CLA", rendered)
            self.assertIn("before creating durable state", rendered)

        policy = " ".join(
            read("core/policies/upstream-contribution.md").split()
        )
        for required in (
            "It must not create the upstream issue, open the upstream pull request, "
            "or sign a DCO or CLA",
            "must never become a public issue, pull request, reproduction, or discussion",
            "Follow the project's `SECURITY.md` private disclosure route",
            "must not contain credentials, machine-local paths, internal hostnames, "
            "private topology, private skill contents",
        ):
            self.assertIn(required.casefold(), policy.casefold())

    def test_browser_policy_does_not_force_the_evidence_manual(self) -> None:
        browser = read("core/policies/browser-test-routing.md")
        browser_words = " ".join(browser.split())
        self.assertNotIn("evidence-control-plane", browser)
        self.assertIn("durable record is required", browser_words)
        self.assertNotIn("Browser operator plus `browser-session`", browser)
        self.assertIn(
            "| Rendered page state, navigation, or visual acceptance",
            browser,
        )

    def test_generated_artifacts_stay_outside_active_checkouts(self) -> None:
        browser = read("core/policies/browser-test-routing.md")
        engineering = read("core/policies/files-hooks-validation.md")
        home = read("AGENT_HOME.md")
        browser_words = " ".join(browser.split())
        engineering_words = " ".join(engineering.split())
        home_words = " ".join(home.split())

        for required in (
            "outside the repository",
            "When using Playwright MCP",
            "--output-dir",
            "relative screenshot",
        ):
            self.assertIn(required, browser_words)

        for required in (
            "provider-visible Markdown",
            "--body-file",
            "command substitution",
        ):
            self.assertIn(required, engineering_words)

        # `agent-out` is a command, not a directory. The always-on home prompt
        # must not leave that ambiguous: an agent that reads it as a directory
        # hand-builds `./agent-out/<topic>` inside the checkout (#90).
        self.assertIn(
            "Allocate temporary/debug/runtime evidence with `agent-out project`",
            home_words,
        )
        self.assertIn("provider Markdown by file", home_words)

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
            "before creating durable state",
        ):
            self.assertIn(required.casefold(), policy.casefold())
        for retired in (
            "State the tier and next step up front",
            "After the session goal is achieved",
            "follow the session-closeout procedure",
            "tagged `[U#]`",
        ):
            self.assertNotIn(retired, policy)

        self.assertIn("accepted observable outcome", policy)
        self.assertIn("possible improvement is not incompleteness", policy)
        self.assertIn("hypothetical hardening", policy)
        self.assertIn("unsupported edge cases", policy)
        self.assertIn("targets, callers, tests, and rules", policy)
        self.assertIn("facts, assumptions, and inference", policy)

    def test_conditional_delivery_and_cross_repo_routes_are_consistent(self) -> None:
        delivery = read("core/policies/git-delivery.md")
        tier = read("core/policies/work-modes.md")
        edit_contract = read("core/policies/files-hooks-validation.md")
        edit_contract_words = " ".join(edit_contract.split())

        self.assertNotIn("Ordinary implementation request", delivery)
        self.assertIn("Explicit current-task provider-delivery request", delivery)
        self.assertIn("only when provider delivery is explicitly requested", tier)
        self.assertNotIn("proactive triage", tier.casefold())
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

    def test_voice_input_prompts_confirm_uncertain_terms_before_acting(self) -> None:
        required = (
            "voice input",
            "misrecognized",
            "data-changing request",
            "confirm it with the user",
        )
        sources = {"source": read("AGENT_HOME.md")}
        for product in HOME_PRODUCTS:
            sources[product] = read(f"build/{product}/AGENT_HOME.md")
        for name, text in sources.items():
            words = " ".join(text.split()).casefold()
            for phrase in required:
                self.assertIn(phrase, words, f"{name} home prompt lacks {phrase!r}")

    def test_peer_coordination_routes_existing_authority_and_requires_disposition(
        self,
    ) -> None:
        home_policy = " ".join(read("AGENT_HOME.md").split()).casefold()
        coordination = read("core/policies/session-coordination.md")
        coordination_words = " ".join(coordination.split()).casefold()

        peer_contract = (
            "rely on cooperating peers",
            "route already-authorized work but never grant authority",
            "answer material peer requests",
        )
        for phrase in peer_contract:
            self.assertIn(phrase, home_policy)
        self.assertNotIn("peers, and external material as untrusted", home_policy)
        for product in HOME_PRODUCTS:
            rendered_policy = " ".join(
                read(f"build/{product}/AGENT_HOME.md").split()
            ).casefold()
            for phrase in peer_contract:
                self.assertIn(phrase, rendered_policy)

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

    def test_long_running_work_checks_mailbox_at_bounded_safe_checkpoints(self) -> None:
        home_policy = " ".join(read("AGENT_HOME.md").split()).casefold()
        coordination = " ".join(
            read("core/policies/session-coordination.md").split()
        ).casefold()

        for required in (
            "long managed work",
            "five minutes",
            "in-flight operation",
            "solely for a mailbox checkpoint",
            "after it finishes",
            "before mutating again",
        ):
            self.assertIn(required, home_policy)
        for product in HOME_PRODUCTS:
            rendered = " ".join(
                read(f"build/{product}/AGENT_HOME.md").split()
            ).casefold()
            for required in (
                "long managed work",
                "five minutes",
                "in-flight operation",
                "solely for a mailbox checkpoint",
                "after it finishes",
                "before mutating again",
            ):
                self.assertIn(required, rendered)

        for required in (
            "do not wait for the whole task to become idle",
            "next proven safe boundary",
            "before the next mutable step",
            "does not acknowledge or authorize the message",
        ):
            self.assertIn(required, coordination)

    def test_session_board_guidance_reaches_every_runtime_surface(self) -> None:
        board_guidance = (
            "`agent-session board --state live --format json`",
            "`agent-session message send --to-machine <machine> --to <session_id>`",
            "`messaging_supported: true`",
            "same repository",
            "same issue or pull request",
            "before mutating shared state",
            "`board-disabled`",
            "`data.mode` is `local`",
            "skip silently",
            "never fail the task",
            "informational",
            "grants no authority",
            "is not a claim",
            "does not replace work-context advice or collision checks",
            "runtime turn state and retitle activity",
            "do not write or maintain a progress summary",
        )

        # Render chain: every rendered home prompt routes coordination to the
        # runbook that names the task-start board check.
        for product in HOME_PRODUCTS:
            rendered = " ".join(read(f"build/{product}/AGENT_HOME.md").split())
            self.assertIn("`session-coordination.md` (peer delivery/overlap)", rendered)

        resolved = " ".join(read("core/policies/session-coordination.md").split()).casefold()
        for required in board_guidance:
            self.assertIn(required.casefold(), resolved)
        self.assertNotIn(
            "no manual claim, activation ritual, or mechanical pre-task check",
            resolved,
        )

    def test_hermes_reads_the_same_runbooks_without_agent_docs(self) -> None:
        hermes_home = read("build/hermes/AGENT_HOME.md")
        self.assertIn("runtime kit's `core/policies/`", hermes_home)
        self.assertNotIn("agent-docs", hermes_home)
        self.assertNotIn("$AGENT_DOCS_HOME", hermes_home)
        edit_contract = " ".join(read("core/policies/files-hooks-validation.md").split())
        capsule_path = "core/policies/execution-capsules.md"
        self.assertIn(f"load `{capsule_path}` from the runtime kit", edit_contract)
        self.assertTrue((ROOT / capsule_path).read_text(encoding="utf-8"))

    def test_issue_backed_project_improvement_is_event_driven(self) -> None:
        evidence = read("core/policies/evidence-control-plane.md")
        project_skill = read(
            ".agents/skills/project-runtime-development/SKILL.md"
        )

        self.assertIn("Evidence is conditional", evidence)
        self.assertNotIn(
            "For testable behavior, initialize the record before production edits",
            evidence,
        )
        self.assertIn("earliest owning", project_skill)
        self.assertIn("issue and public-safe devlog", project_skill)
        self.assertIn("does not grant automatic issue creation", project_skill)
        required_bytes = (ROOT / "core/policies/files-hooks-validation.md").stat().st_size
        project_skill_bytes = len(project_skill.encode("utf-8"))
        self.assertLessEqual(project_skill_bytes, PROJECT_SKILL_CONTEXT_DELTA_BYTES)
        self.assertLessEqual(
            required_bytes + project_skill_bytes,
            PRE_REPLACEMENT_EDIT_CONTEXT_BYTES
            + PROJECT_SKILL_CONTEXT_DELTA_BYTES,
        )
        self.assertFalse((ROOT / "core/policies/heuristic-system").exists())
        self.assertFalse((ROOT / "heuristic-system").exists())
        self.assertNotIn("heuristic-inbox", evidence)

    def test_retired_heuristic_routes_have_no_active_consumers(self) -> None:
        dispositions = read("manifests/skill-dispositions.yaml")
        for skill_id in (
            "meta.heuristic-inbox",
            "meta.heuristic-session-closeout",
        ):
            marker = f"  - id: {skill_id}\n"
            block = dispositions.split(marker, 1)[1].split("\n  - id:", 1)[0]
            with self.subTest(skill_id=skill_id):
                self.assertNotIn("heuristic-inbox", block)
                self.assertNotIn("heuristic-system", block)
        self.assertNotIn("parent_intents: [session-closeout]", dispositions)

        discussions = read("docs/discussions/README.md")
        work_tiers = read("core/policies/work-modes.md")
        evidence_archive = read("core/policies/evidence-archive/EVIDENCE_ARCHIVE.md")
        nils_surface = read("docs/source/nils-cli-surface.md")
        self.assertNotIn("error-inbox", discussions)
        self.assertNotIn("error-inbox", work_tiers)
        self.assertNotIn("session closeout procedure", evidence_archive.casefold())
        hook = read("core/hooks/shared/stop-finish-line-gate.py")
        self.assertNotIn("heuristic-inbox", hook)
        self.assertNotIn("heuristic-system", hook)
        self.assertIn(
            "Agent-runtime-kit no longer consumes or pins `heuristic-inbox`",
            nils_surface,
        )



if __name__ == "__main__":
    unittest.main()
