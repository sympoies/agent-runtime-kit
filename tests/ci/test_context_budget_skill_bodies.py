#!/usr/bin/env python3
"""Skill bodies must be a measured context-budget surface (issue #140).

``scripts/ci/context-budget-audit.py`` budgets the context an agent is *forced*
to carry. A triggered skill loads its whole rendered ``SKILL.md`` into the turn,
which makes a skill body the largest single context cost the runtime can incur
-- and until #140 the gate did not measure one. The always-on home policy was
held to 4 KiB while ``pr/deliver-pr`` rendered to 48,133 bytes unreported.

These tests pin the behavior that closes that gap:

  * every rendered skill body is discovered and measured, checked against the
    SOURCE skill tree rather than by re-walking the build tree the way the
    implementation does (an oracle that copies the implementation cannot catch
    a traversal bug);
  * a body over target without an override fails the real gate end to end, in a
    synthetic tree, not just in a `classify()` call on synthetic integers;
  * an absent render is a coverage error rather than a vacuous pass;
  * the measured size is the LARGEST render across products, pinned with a body
    whose per-product sizes actually differ;
  * an override must be reasoned and tracked, and one naming a body that no
    longer renders is a coverage error.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
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


def source_skill_ids():
    """Expected surface ids derived from the SOURCE tree, not the build tree.

    Independent of `discover_skill_bodies`: if the implementation's traversal
    and this disagree, that is the bug worth reporting. Source skills live at
    ``core/skills/<plugin>/<skill>/SKILL.md[.tera]``.
    """
    ids = set()
    skills_root = os.path.join(ROOT, "core", "skills")
    for plugin in sorted(os.listdir(skills_root)):
        plugin_dir = os.path.join(skills_root, plugin)
        if not os.path.isdir(plugin_dir):
            continue
        for skill in sorted(os.listdir(plugin_dir)):
            skill_dir = os.path.join(plugin_dir, skill)
            if not os.path.isdir(skill_dir):
                continue
            if any(os.path.isfile(os.path.join(skill_dir, name))
                   for name in ("SKILL.md", "SKILL.md.tera")):
                ids.add("skill-body.%s.%s" % (plugin, skill))
    return ids


def build_tree_present():
    return os.path.isdir(os.path.join(ROOT, audit.BUILD_DIR))


def write_body(root, product, plugin, skill, size):
    path = os.path.join(root, audit.BUILD_DIR, product, "plugins", plugin,
                        "skills", skill, "SKILL.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("x" * size)
    return path


class SkillBodyDiscovery(unittest.TestCase):
    def setUp(self):
        if not build_tree_present():
            self.skipTest("no build/ tree; run `agent-runtime render` first")

    def test_discovery_matches_the_source_skill_set(self) -> None:
        discovered = {spec["id"] for spec in audit.discover_skill_body_budgets()}
        self.assertEqual(
            discovered,
            source_skill_ids(),
            "every source skill must render into a measured body, and every "
            "measured body must come from a source skill",
        )

    def test_deliver_pr_body_is_a_measured_surface(self) -> None:
        ids = {spec["id"] for spec in audit.discover_skill_body_budgets()}
        self.assertIn("skill-body.pr.deliver-pr", ids)

    def test_specs_are_actively_measured(self) -> None:
        for spec in audit.discover_skill_body_budgets():
            self.assertIn(spec["measure"][0], audit._MEASURED_KINDS)
            self.assertEqual(spec["target"], audit.SKILL_BODY_TARGET)


class SkillBodyMeasurement(unittest.TestCase):
    """The measured size is the worst case an agent could load."""

    def test_largest_product_render_wins(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            write_body(root, "codex", "demo", "skew", 100)
            write_body(root, "claude", "demo", "skew", 4096)
            write_body(root, "hermes", "demo", "skew", 2048)
            spec, = audit.discover_skill_body_budgets(root)
            actual, detail = audit.measure_bytes(spec["measure"])
            self.assertEqual(actual, 4096)
            self.assertNotEqual(actual, 100, "must not take the smallest render")
            self.assertIn("largest", detail)

    def test_identical_renders_are_reported_as_identical(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            for product in ("codex", "claude", "hermes"):
                write_body(root, product, "demo", "same", 321)
            spec, = audit.discover_skill_body_budgets(root)
            actual, detail = audit.measure_bytes(spec["measure"])
            self.assertEqual(actual, 321)
            self.assertIn("identical", detail)


class SkillBodyEnforcement(unittest.TestCase):
    def test_oversized_body_without_override_fails_the_gate(self) -> None:
        """The headline claim, end to end: discovery -> measure -> FAIL."""
        with tempfile.TemporaryDirectory() as root:
            write_body(root, "codex", "demo", "huge",
                       audit.SKILL_BODY_TARGET + 1)
            spec, = audit.discover_skill_body_budgets(root)
            actual, _ = audit.measure_bytes(spec["measure"])
            verdict, note = audit.classify(
                spec["target"], actual, spec["override"])
            self.assertEqual(verdict, "FAIL", note)

    def test_body_at_target_passes(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            write_body(root, "codex", "demo", "snug", audit.SKILL_BODY_TARGET)
            spec, = audit.discover_skill_body_budgets(root)
            actual, _ = audit.measure_bytes(spec["measure"])
            verdict, _ = audit.classify(spec["target"], actual, spec["override"])
            self.assertIn(verdict, ("ok", "near-limit"))

    def test_absent_render_is_a_coverage_error(self) -> None:
        """A render that did not run must not pass vacuously."""
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(audit.discover_skill_body_budgets(root), [])
        errors = audit.coverage_errors(
            [{"id": "x", "measure": ("file", "x"), "target": 1,
              "override": None}],
            require_skill_bodies=True,
        )
        self.assertTrue(
            any("no rendered skill bodies" in err for err in errors), errors)

    def test_waived_body_warns_before_it_runs_out_of_room(self) -> None:
        target = audit.SKILL_BODY_TARGET
        override = {"allow": target + 1000, "reason": "r", "tracking": "t"}
        roomy, note = audit.classify(target, target + 100, override)
        self.assertEqual(roomy, "waived")
        self.assertNotIn("waived headroom", note)
        tight, note = audit.classify(
            target, override["allow"] - audit.WAIVED_HEADROOM_WARN_BYTES,
            override)
        self.assertEqual(tight, "waived")
        self.assertIn("waived headroom", note)

    def test_override_must_carry_reason_and_tracking(self) -> None:
        bad = [{
            "id": "skill-body.x.y",
            "measure": ("file", "x"),
            "target": 100,
            "override": {"allow": 200, "reason": "  ", "tracking": "t"},
        }]
        self.assertTrue(audit.coverage_errors(bad))

    def test_override_for_unrendered_skill_is_a_coverage_error(self) -> None:
        errors = audit.skill_body_override_errors(
            {"skill-body.pr.no-such-skill": {"allow": 1, "reason": "r",
                                             "tracking": "t"}},
            [{"id": "skill-body.pr.deliver-pr"}],
        )
        self.assertTrue(errors)
        self.assertIn("no-such-skill", " ".join(errors))

    def test_shipped_overrides_all_name_a_rendered_skill(self) -> None:
        if not build_tree_present():
            self.skipTest("no build/ tree; run `agent-runtime render` first")
        errors = audit.skill_body_override_errors(
            audit.SKILL_BODY_OVERRIDES, audit.discover_skill_body_budgets()
        )
        self.assertEqual(errors, [], "\n".join(errors))


class GateIntegration(unittest.TestCase):
    """The shipped gate, run the way CI runs it."""

    def test_check_reports_skill_body_surfaces_and_passes(self) -> None:
        if not build_tree_present():
            self.skipTest("no build/ tree; run `agent-runtime render` first")
        result = subprocess.run(
            [sys.executable, AUDIT, "check"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        self.assertIn("skill-body.pr.deliver-pr", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_self_test_does_not_need_a_rendered_tree(self) -> None:
        """--self-test is the classifier's own proof; it must not need build/."""
        with tempfile.TemporaryDirectory() as sandbox:
            script_dir = os.path.join(sandbox, "scripts", "ci")
            os.makedirs(script_dir)
            shutil.copy(AUDIT, os.path.join(script_dir, os.path.basename(AUDIT)))
            result = subprocess.run(
                [sys.executable,
                 os.path.join(script_dir, os.path.basename(AUDIT)),
                 "--self-test"],
                cwd=sandbox, check=False, capture_output=True, text=True,
            )
            self.assertEqual(
                result.returncode, 0,
                "self-test must pass with no build/ tree:\n"
                + result.stdout + result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
