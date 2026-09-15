#!/usr/bin/env python3
"""Skill bodies must be a measured context-budget surface (issue #140).

``scripts/ci/context-budget-audit.py`` budgets the context an agent is *forced*
to carry. A triggered skill loads its whole rendered ``SKILL.md`` into the turn,
which makes a skill body the largest single context cost the runtime can incur
-- and until #140 the gate did not measure one. The always-on home policy was
held to 4 KiB while ``pr/deliver-pr`` rendered to 48,133 bytes unreported.

These tests pin the behavior that closes that gap:

  * every rendered skill body is discovered and measured (no inline allowlist to
    fall out of date, so a newly added oversized skill fails closed);
  * a body over target without an override FAILs;
  * an override must be a reasoned, tracked decision, and must disappear once
    its body comes back under target;
  * an override naming a skill that no longer renders is a coverage error,
    rather than quietly shrinking the measured set.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
AUDIT = os.path.join(ROOT, "scripts", "ci", "context-budget-audit.py")


def load_audit():
    spec = importlib.util.spec_from_file_location("context_budget_audit", AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load_audit()


def rendered_skill_count() -> int:
    """Skills actually rendered, counted independently of the gate's discovery.

    The gate must not be allowed to define its own coverage: if discovery and
    the build tree disagree, that is the bug this asserts.
    """
    total = set()
    build = os.path.join(ROOT, "build")
    for product in sorted(os.listdir(build)):
        plugins = os.path.join(build, product, "plugins")
        if not os.path.isdir(plugins):
            continue
        for plugin in sorted(os.listdir(plugins)):
            skills = os.path.join(plugins, plugin, "skills")
            if not os.path.isdir(skills):
                continue
            for skill in sorted(os.listdir(skills)):
                if os.path.isfile(os.path.join(skills, skill, "SKILL.md")):
                    total.add((plugin, skill))
    return len(total)


class SkillBodyDiscovery(unittest.TestCase):
    def test_every_rendered_skill_body_is_measured(self) -> None:
        discovered = audit.discover_skill_body_budgets()
        self.assertEqual(
            len(discovered),
            rendered_skill_count(),
            "discovery must cover every rendered skill body; an inline list "
            "that drifts is how an oversized skill escapes the gate",
        )
        for spec in discovered:
            self.assertTrue(spec["id"].startswith("skill-body."))
            self.assertIn(spec["measure"][0], audit._MEASURED_KINDS)
            self.assertGreater(spec["target"], 0)

    def test_deliver_pr_body_is_a_measured_surface(self) -> None:
        ids = {spec["id"] for spec in audit.discover_skill_body_budgets()}
        self.assertIn("skill-body.pr.deliver-pr", ids)

    def test_measured_size_is_the_largest_product_render(self) -> None:
        """A body an agent could load is the worst case across products.

        Measuring one product would let a divergent render hide behind a
        smaller sibling.
        """
        by_id = {s["id"]: s for s in audit.discover_skill_body_budgets()}
        spec = by_id["skill-body.pr.deliver-pr"]
        actual, _ = audit.measure_bytes(spec["measure"])
        sizes = []
        build = os.path.join(ROOT, "build")
        for product in os.listdir(build):
            path = os.path.join(
                build, product, "plugins", "pr", "skills", "deliver-pr", "SKILL.md"
            )
            if os.path.isfile(path):
                sizes.append(os.path.getsize(path))
        self.assertTrue(sizes, "deliver-pr must render for at least one product")
        self.assertEqual(actual, max(sizes))


class SkillBodyEnforcement(unittest.TestCase):
    def test_oversized_body_without_override_fails(self) -> None:
        verdict, note = audit.classify(audit.SKILL_BODY_TARGET,
                                       audit.SKILL_BODY_TARGET + 1, None)
        self.assertEqual(verdict, "FAIL", note)

    def test_override_must_carry_reason_and_tracking(self) -> None:
        bad = [{
            "id": "skill-body.x.y",
            "measure": ("file", "x"),
            "target": 100,
            "override": {"allow": 200, "reason": "  ", "tracking": "t"},
        }]
        self.assertTrue(audit.coverage_errors(bad))

    def test_override_for_unrendered_skill_is_a_coverage_error(self) -> None:
        """A dangling override must not silently shrink the measured set."""
        errors = audit.skill_body_override_errors(
            {"skill-body.pr.no-such-skill": {"allow": 1, "reason": "r",
                                             "tracking": "t"}},
            audit.discover_skill_body_budgets(),
        )
        self.assertTrue(errors)
        self.assertIn("no-such-skill", " ".join(errors))

    def test_shipped_overrides_all_name_a_rendered_skill(self) -> None:
        errors = audit.skill_body_override_errors(
            audit.SKILL_BODY_OVERRIDES, audit.discover_skill_body_budgets()
        )
        self.assertEqual(errors, [], "\n".join(errors))


class GateIntegration(unittest.TestCase):
    def test_check_reports_skill_body_surfaces_and_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, AUDIT, "check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertIn("skill-body.pr.deliver-pr", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_self_test_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, AUDIT, "--self-test"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
