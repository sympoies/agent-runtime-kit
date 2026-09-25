#!/usr/bin/env python3
"""Measure the always-on and per-intent context budgets (issue #601 P1).

Progressive context disclosure (graysurf/agent-runtime-kit#601, P1 workstream 4
"visible context budgets") turns the context an agent is *forced* to carry into
a set of reviewable numbers instead of letting it grow invisibly. This gate
measures each budgeted surface and fails closed when one exceeds its target
without an explicit, tracked override.

Surfaces and targets come from the issue's quantitative acceptance budgets
(1 KiB = 1024 bytes):

  * rendered always-on home policy  (build/<product>/AGENT_HOME.md)  <= 4 KiB
  * resolved project-dev edit-phase required reading                 <= 20 KiB
  * startup memory context (header + profile)                        <= 1.25 KiB
  * new context on an unchanged repeat prompt                        == 0 bytes
  * each rendered skill body (build/*/plugins/*/skills/*/SKILL.md)    <= 16 KiB

The skill-body surface (graysurf/agent-runtime-kit#140) is the one an agent pays
on demand rather than always: a triggered skill loads its whole ``SKILL.md`` into
the turn, which makes one body the largest single context cost the runtime can
incur. Leaving it unmeasured is how the always-on home policy came to be held to
4 KiB while ``pr/deliver-pr`` rendered to 48,133 bytes unreported. Skill-body
surfaces are DISCOVERED from the build tree rather than listed inline, so a newly
added oversized skill fails closed instead of escaping an allowlist nobody
updated, and each body is measured at its largest render across products -- the
worst case an agent could actually load.

Each surface is classified:

  ok             actual <= target with room left
  near-limit     actual <= target but at or above ``WARN_RATIO`` of it. Advisory
                 only -- it never fails the gate. A pass/FAIL gate tells an
                 author their addition does not fit only after they have written
                 it; a surface sitting at 99% of target looks identical to one
                 sitting at 40%. This reports the remaining headroom so the
                 "there is no room here" decision can be made before the work,
                 and so a surface approaching its ceiling becomes visible while
                 trimming is still cheap.
  waived         actual >  target but an explicit ``override`` allows it. An
                 override records the allowed ceiling, WHY the surface is over
                 target, and a tracking ref -- either debt a later slice removes
                 (bringing the surface back under target) or a permanent
                 documented budget decision when the target is an aspiration the
                 surface's irreducible content cannot meet. Either way it is a
                 visible, reasoned decision -- never silent growth.
  FAIL           actual >  target and no override covers it (there is no
                 override, or actual even exceeds ``override.allow``).
  stale-override actual <= target yet an override is still declared. The
                 override must be removed so the target is enforced bare -- this
                 is the RED->GREEN step each #601 P1 slice performs when it
                 brings a surface under budget.
  skip           surface is recorded for visibility but measured/enforced
                 elsewhere (``pending`` = wired by a later slice; ``behavioral``
                 = enforced by a named test).

``check`` (default, the CI gate) is deterministic and network-free: it exits
non-zero if any surface FAILs or carries a stale override. ``near-limit`` is
advisory and never changes the exit code.

``--self-test`` runs the classifier against synthetic surfaces and asserts the
verdicts, proving the gate actually detects an over-budget surface, honors an
override, rejects an override that no longer applies, and warns before a
surface runs out of room.

Budgets are declared inline (see ``BUDGETS``) rather than in a YAML manifest so
the gate stays stdlib-only and runs on any python3 (including macOS system
python), matching scripts/ci/version-baseline-audit.py.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KIB = 1024
# The always-on home prompt carries every product's shared invariants; 4 KiB plus
# a 256-byte margin accommodates the voice-input confirmation rule.
HOME_PROMPT_TARGET = 4 * KIB + 256


# --- budget declarations -----------------------------------------------------
# Each entry:
#   id          stable surface identifier
#   description human-readable surface
#   measure     how the actual size is obtained:
#                 ("file", "<repo-relative path>")     -> size of one file
#                 ("doc-set", ["<path>", ...])         -> sum of file sizes
#                 ("agent-docs", intent, phase, product) -> resolved required set
#                 ("pending", "<owner>")               -> not yet measured here
#                 ("behavioral", "<covered_by>")       -> enforced elsewhere
#   target      byte target (the budget)
#   override    None, or {"allow": int, "reason": str, "tracking": str}: an
#               explicit ceiling above target with a reason and a tracking ref.
#               An override is either tracked debt a later slice removes (remove
#               it -> the bare target is enforced) OR a permanent documented
#               budget decision when the target is an aspiration the surface's
#               irreducible content cannot meet (the issue's "explicit documented
#               budget decision" exception).
BUDGETS = [
    {
        "id": "rendered-agent-home.codex",
        "description": "Rendered Codex always-on home policy (AGENT_HOME).",
        "measure": ("file", "build/codex/AGENT_HOME.md"),
        "target": HOME_PROMPT_TARGET,
        "override": None,
    },
    {
        "id": "rendered-agent-home.claude",
        "description": "Rendered Claude always-on home policy (AGENT_HOME).",
        "measure": ("file", "build/claude/AGENT_HOME.md"),
        "target": HOME_PROMPT_TARGET,
        "override": None,
    },
    {
        "id": "rendered-agent-home.hermes",
        "description": "Rendered Hermes always-on home policy (AGENT_HOME).",
        "measure": ("file", "build/hermes/AGENT_HOME.md"),
        "target": HOME_PROMPT_TARGET,
        "override": None,
    },
    {
        "id": "rendered-agent-home.neutral",
        "description": "Rendered neutral always-on home policy (AGENT_HOME).",
        "measure": ("file", "build/neutral/AGENT_HOME.md"),
        "target": HOME_PROMPT_TARGET,
        "override": None,
    },
    {
        "id": "edit-phase-required-reading.project-dev",
        "description": (
            "Actual required documents resolved by agent-docs for this kit's "
            "project-dev edit phase, including applicable project and home scope."
        ),
        "measure": ("agent-docs", "project-dev", "edit", "codex"),
        "target": 20 * KIB,
        "override": None,
    },
    {
        "id": "startup-memory.codex",
        "description": (
            "Codex startup memory context (micro-header + bounded recall "
            "profile) injected by core/hooks/shared/user-prompt-agent-memory.sh."
        ),
        "measure": ("behavioral",
                    "tests/hooks/test_shared_hooks.py "
                    "(startup header + profile byte budget)"),
        "target": 1280,  # 1.25 KiB
        "override": None,
    },
    {
        "id": "route-cue.unchanged-prompt",
        "description": (
            "New agent-docs context emitted on an unchanged repeat prompt; "
            "startup memory runs only at SessionStart boundaries."
        ),
        "measure": ("behavioral",
                    "tests/hooks/test_shared_hooks.py "
                    "(delta cue unchanged-prompt suppression)"),
        "target": 0,
        "override": None,
    },
]


# Surfaces that must stay actively measured (file / doc-set). Downgrading one to
# a non-measured kind (pending / behavioral) or deleting it silently drops
# enforcement, so ``check`` treats that as a coverage failure -- the gate defends
# its own coverage, not only its classifier (see the #601 slice 3a review).
REQUIRED_MEASURED_IDS = frozenset({
    "rendered-agent-home.codex",
    "rendered-agent-home.claude",
    "rendered-agent-home.hermes",
    "rendered-agent-home.neutral",
    "edit-phase-required-reading.project-dev",
})

_MEASURED_KINDS = ("file", "doc-set", "agent-docs", "skill-body")


# --- skill-body surfaces (#140) ----------------------------------------------
# Unlike the surfaces above, these are DISCOVERED from the rendered build tree
# instead of being declared inline. An inline list is an allowlist: a skill
# nobody added to it is a skill nobody measures, and the failure is silent. With
# discovery, adding an oversized skill fails the gate on the commit that adds it.
BUILD_DIR = "build"
SKILL_BODY_TARGET = 16 * KIB

# Bodies allowed above target. Same contract as ``BUDGETS`` overrides: an
# explicit ceiling, WHY, and a tracking ref -- either debt a later slice removes
# or a documented budget decision. Keyed by surface id.
SKILL_BODY_OVERRIDES = {
    "skill-body.pr.deliver-pr": {
        "allow": 46 * KIB,
        "reason": (
            "The review-loop fence that drove this body is now delegated: "
            "nils-cli 1.28.30 (sympoies/nils-cli#1740) added `observe "
            "--auto-state` / `--preflight` and `pr review --recover-pending`, "
            "so the genesis dance, the dry-run/live pair, and the 122-line "
            "pending-review recovery state machine are gone. That removed 67 "
            "lines but only 1,422 bytes, because the bash was replaced with "
            "prose explaining what the CLI now guarantees and, in particular, "
            "why the closing observation must keep `--expected-state` rather "
            "than `--auto-state`. That explanation is the part a future editor "
            "would otherwise get wrong, so it is not a candidate for removal. "
            "What remains above target is the lifecycle/review/publication "
            "contract itself. GitLab v1 statements that "
            "tests/runtime-smoke/cases/pr pins by exact phrase also stay: an "
            "agent delivering an MR must not be able to miss them by skipping "
            "a reference. The ceiling is one KiB above the measured size, so "
            "this body cannot drift upward unnoticed."
        ),
        "tracking": "graysurf/agent-runtime-kit#140 (upstream delegation landed; residue is contract prose)",
    },
    "skill-body.conversation.main-agent-mode": {
        "allow": 47 * KIB,
        "reason": (
            "Lane/worker orchestration contract carried entirely in prose. "
            "#140 is the first gate to measure it; the ceiling is the measured "
            "size rounded up one KiB, and no reduction has been "
            "designed. #140 owns the decision."
        ),
        "tracking": "graysurf/agent-runtime-kit#140 (measured, no reduction scheduled)",
    },
    "skill-body.dispatch.deliver-plan-tracking-issue": {
        "allow": 34 * KIB,
        "reason": (
            "Plan bundle + issue lifecycle + strict closeout + archive handoff "
            "in one body. The review-loop and pending-review machinery this "
            "shared with deliver-pr is now delegated to nils-cli 1.28.30, "
            "which took 2,162 bytes off. The remainder is the lifecycle "
            "contract, and no further reduction is designed; the ceiling is "
            "the measured size rounded up one KiB and #140 owns the decision."
        ),
        "tracking": "graysurf/agent-runtime-kit#140 (delegation landed; no further reduction scheduled)",
    },
    "skill-body.dispatch.deliver-dispatch-plan": {
        "allow": 23 * KIB,
        "reason": (
            "Shared dispatch spine plus per-lane delivery and closeout. The "
            "review-loop and pending-review machinery is now delegated to "
            "nils-cli 1.28.30, which took 2,326 bytes off. The remainder is "
            "the lane/orchestrator contract, and no further reduction is "
            "designed; the ceiling is the measured size rounded up one KiB "
            "and #140 owns the decision."
        ),
        "tracking": "graysurf/agent-runtime-kit#140 (delegation landed; no further reduction scheduled)",
    },
    "skill-body.computer-use.macos-desktop": {
        "allow": 22 * KIB,
        "reason": (
            "AX-first action vocabulary, guarded replay, and privacy-preserving "
            "journal rules. First measured by #140; no reduction designed, "
            "ceiling is the measured size rounded up one KiB and #140 "
            "owns the decision."
        ),
        "tracking": "graysurf/agent-runtime-kit#140 (measured, no reduction scheduled)",
    },
}


def discover_skill_bodies(repo_root=None):
    """Return {surface_id: [repo-relative SKILL.md paths]} from the build tree.

    One surface per (plugin, skill) across every product, because the same body
    is the same context cost whichever product loaded it.
    """
    root = repo_root or REPO_ROOT
    build = os.path.join(root, BUILD_DIR)
    found = {}
    if not os.path.isdir(build):
        return found
    for product in sorted(os.listdir(build)):
        plugins = os.path.join(build, product, "plugins")
        if not os.path.isdir(plugins):
            continue
        for plugin in sorted(os.listdir(plugins)):
            skills = os.path.join(plugins, plugin, "skills")
            if not os.path.isdir(skills):
                continue
            for skill in sorted(os.listdir(skills)):
                body = os.path.join(skills, skill, "SKILL.md")
                if not os.path.isfile(body):
                    continue
                sid = "skill-body.%s.%s" % (plugin, skill)
                rel = os.path.relpath(body, root)
                found.setdefault(sid, []).append(rel)
    return found


def discover_skill_body_budgets(repo_root=None):
    """Expand discovered skill bodies into budget specs.

    The discovery root travels inside the measure tuple. Without it a spec
    discovered under a fixture root would be measured against ``REPO_ROOT``,
    which either raises or -- worse -- silently returns the size of a
    same-named real file, so the gate could not be tested against a synthetic
    tree at all.
    """
    root = repo_root or REPO_ROOT
    specs = []
    for sid, rels in sorted(discover_skill_bodies(root).items()):
        specs.append({
            "id": sid,
            "description": "Rendered skill body loaded when %s triggers." % (
                sid[len("skill-body."):]),
            "measure": ("skill-body", root, sorted(rels)),
            "target": SKILL_BODY_TARGET,
            "override": SKILL_BODY_OVERRIDES.get(sid),
        })
    return specs


def skill_body_override_errors(overrides, discovered_specs):
    """Overrides must name a body that actually renders (empty list == ok).

    A dangling override is not harmless: it is an exemption for something the
    gate is no longer measuring, so it must be removed with the body it excused.
    """
    known = {spec["id"] for spec in discovered_specs}
    return [
        "skill-body override %r names no rendered skill body; remove it "
        "(the body it excused is gone, so the exemption is too)." % sid
        for sid in sorted(overrides)
        if sid not in known
    ]


def all_budgets(repo_root=None):
    """The full measured set: declared surfaces plus discovered skill bodies."""
    return list(BUDGETS) + discover_skill_body_budgets(repo_root)


# --- measurement -------------------------------------------------------------


def measure_bytes(measure):
    """Return (actual_bytes | None, detail).

    ``None`` means the surface is recorded for visibility but not measured by
    this gate (``pending`` / ``behavioral``). A ``file`` / ``doc-set`` whose
    path is missing raises, so a render that did not run fails loudly rather
    than passing vacuously.
    """
    kind = measure[0]
    if kind == "file":
        rel = measure[1]
        return os.path.getsize(os.path.join(REPO_ROOT, rel)), rel
    if kind == "doc-set":
        rels = measure[1]
        total = sum(os.path.getsize(os.path.join(REPO_ROOT, rel)) for rel in rels)
        return total, "%d docs" % len(rels)
    if kind == "agent-docs":
        _, intent, phase, product = measure
        command = [
            "agent-docs",
            "preflight",
            "--intent",
            intent,
            "--phase",
            phase,
            "--product",
            product,
            "--docs-home",
            REPO_ROOT,
            "--project-path",
            REPO_ROOT,
            "--worktree-fallback",
            "local-only",
            "--format",
            "json",
        ]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        required = [item for item in payload["documents"] if item["required"]]
        paths = [os.path.realpath(item["path"]) for item in required]
        for path in paths:
            if os.path.commonpath((REPO_ROOT, path)) != REPO_ROOT:
                raise ValueError(
                    "agent-docs resolved required path outside source root: %s"
                    % path
                )
        total = sum(os.path.getsize(path) for path in paths)
        return total, (
            "agent-docs %s/%s: %d resolved required docs"
            % (intent, phase, len(paths))
        )
    if kind == "skill-body":
        _, root, rels = measure
        sizes = [(os.path.getsize(os.path.join(root, rel)), rel)
                 for rel in rels]
        largest, where = max(sizes)
        if len(sizes) == 1:
            return largest, where
        if largest == min(size for size, _ in sizes):
            return largest, "identical across %d product renders" % len(sizes)
        return largest, "largest of %d product renders (%s)" % (
            len(sizes), where.split(os.sep)[1])
    if kind == "pending":
        return None, "measurement pending, owned by %s" % measure[1]
    if kind == "behavioral":
        return None, "enforced by %s" % measure[1]
    raise ValueError("unknown measure kind: %r" % (kind,))


# Fraction of target at or above which an in-budget surface is reported as
# near-limit. Advisory only; it never fails the gate.
WARN_RATIO = 0.90

# Remaining bytes below ``override.allow`` at or under which a waived surface is
# reported as running out of room. A waived body sits above target, so the
# near-limit band above can never reach it; without this a tight ratchet gives no
# warning and the next routine edit is a hard FAIL on work already written.
# Override ceilings are set one KiB above the measured size (two when that would
# leave under this much room), so this fires only on real growth.
WAIVED_HEADROOM_WARN_BYTES = 512


def classify(target, actual, override):
    """Classify one surface. Returns (verdict, note).

    verdict in {"ok", "near-limit", "waived", "FAIL", "stale-override", "skip"}.
    """
    if actual is None:
        return "skip", ""
    if actual <= target:
        if override is not None:
            return "stale-override", (
                "actual %d <= target %d but an override is still declared; "
                "remove it so the target is enforced bare (RED->GREEN for %s)"
                % (actual, target, override.get("tracking", "?"))
            )
        # target > 0 guards the percentage below: a zero-target surface (an
        # "emit nothing" budget such as route-cue.unchanged-prompt) has no band
        # to be near, and dividing by it would crash the gate instead of
        # reporting. Zero-target surfaces stay ok until they actually exceed 0.
        if target > 0 and actual >= target * WARN_RATIO:
            return "near-limit", (
                "only %d byte(s) left of target %d (%.1f%% used); trim this "
                "surface before adding to it"
                % (target - actual, target, 100.0 * actual / target)
            )
        return "ok", ""
    # actual > target
    if override is not None and actual <= override["allow"]:
        note = "allow=%d over target by %d; tracking %s" % (
            override["allow"], actual - target, override["tracking"])
        # A waived surface sits above target, so the near-limit band below can
        # never reach it. Without this, a ratchet set just above actual gives no
        # warning at all -- the next routine edit is a hard FAIL on work that is
        # already written, which is exactly what near-limit exists to prevent.
        headroom = override["allow"] - actual
        if headroom <= WAIVED_HEADROOM_WARN_BYTES:
            note += ("; only %d byte(s) of waived headroom left -- trim this "
                     "surface or revisit the override before adding to it"
                     % headroom)
        return "waived", note
    if override is not None:
        return "FAIL", "actual %d exceeds override.allow %d (tracking %s)" % (
            actual, override["allow"], override["tracking"])
    return "FAIL", "actual %d exceeds target %d and no override is declared" % (
        actual, target)


# --- check -------------------------------------------------------------------


def evaluate(budgets):
    rows = []
    for spec in budgets:
        actual, detail = measure_bytes(spec["measure"])
        verdict, note = classify(spec["target"], actual, spec["override"])
        rows.append((spec, actual, detail, verdict, note))
    return rows


def coverage_errors(budgets, skill_overrides=None, require_skill_bodies=False):
    """Return coverage-integrity errors (empty list == ok); fail-closed.

    ``skill_overrides`` / ``require_skill_bodies`` add the skill-body rules
    (#140). They are opt-in so the synthetic self-test cases, which carry no
    discovered bodies, stay valid -- but the real gate passes both, so every
    coverage rule has one owner and one entry point.

    The classifier self-test proves verdicts are correct, but a gate that
    silently loses surfaces is worse than a wrong verdict: an emptied BUDGETS,
    a deleted required surface, or a required surface downgraded to a
    non-measured kind (pending / behavioral) would pass vacuously. This asserts
    the gate keeps measuring what it must, and that every override is a real,
    reasoned, tracked decision rather than a bare escape hatch.
    """
    if not budgets:
        return ["BUDGETS is empty; the gate would pass vacuously."]
    errors = []
    by_id = {}
    for spec in budgets:
        by_id.setdefault(spec["id"], spec)
    for rid in sorted(REQUIRED_MEASURED_IDS):
        spec = by_id.get(rid)
        if spec is None:
            errors.append("required surface %r is missing from BUDGETS." % rid)
        elif spec["measure"][0] not in _MEASURED_KINDS:
            errors.append(
                "required surface %r is declared %r; it must stay actively "
                "measured (%s), not downgraded."
                % (rid, spec["measure"][0], "/".join(_MEASURED_KINDS)))
    for spec in budgets:
        ov = spec.get("override")
        if ov is None:
            continue
        if ov.get("allow", 0) <= spec["target"]:
            errors.append(
                "surface %r override.allow (%r) must exceed target (%d); an "
                "override at or below target is meaningless."
                % (spec["id"], ov.get("allow"), spec["target"]))
        if not str(ov.get("reason", "")).strip():
            errors.append("surface %r override is missing a reason." % spec["id"])
        if not str(ov.get("tracking", "")).strip():
            errors.append(
                "surface %r override is missing a tracking ref." % spec["id"])
    discovered = [s for s in budgets if s["id"].startswith("skill-body.")]
    if require_skill_bodies and not discovered:
        # A render that did not run would otherwise drop every skill body from
        # the measured set and still exit 0.
        errors.append(
            "no rendered skill bodies were discovered under %s/; run "
            "`agent-runtime render --product <product>` before this gate."
            % BUILD_DIR)
    if skill_overrides is not None:
        errors.extend(skill_body_override_errors(skill_overrides, discovered))
    return errors


def _emit(rows):
    failing = 0
    near = 0
    for spec, actual, detail, verdict, note in rows:
        actual_s = "%d" % actual if actual is not None else "-"
        print("  %-14s %-52s target=%-6d actual=%-7s %s" % (
            verdict, spec["id"], spec["target"], actual_s, note or detail))
        if verdict in ("FAIL", "stale-override"):
            failing += 1
        elif verdict == "near-limit":
            near += 1
    print("\ncontext-budget-audit: %d surfaces, %d failing, %d near-limit"
          % (len(rows), failing, near))
    if near:
        print(
            "\n%d surface(s) are within %d%% of target. They pass, but they "
            "have little room left: trim them before adding anything, or the "
            "next addition will fail this gate after it is already written."
            % (near, int(round((1.0 - WARN_RATIO) * 100)))
        )
    if failing:
        print(
            "\nBudget gate failed. For each failing surface either bring it "
            "under its target, or -- if the overage is a reviewed, tracked "
            "decision -- declare an explicit override in BUDGETS with "
            "allow/reason/tracking. Remove a stale override once its surface is "
            "back under target."
        )
    return failing


# --- self-test ---------------------------------------------------------------

# (target, actual, override, expected_verdict)
_OV = {"allow": 200, "reason": "x", "tracking": "t"}
SELF_TEST_CASES = [
    (100, 50, None, "ok"),                # under target, no override
    (100, 150, _OV, "waived"),            # over target, override covers it
    (100, 250, _OV, "FAIL"),              # over target, override too small
    (100, 150, None, "FAIL"),             # over target, no override
    (100, 80, _OV, "stale-override"),     # under target but override lingers
    (100, None, None, "skip"),            # not measured here
    (100, 89, None, "ok"),                # just below the warn band
    (100, 90, None, "near-limit"),        # exactly at WARN_RATIO
    (100, 99, None, "near-limit"),        # in budget with 1 byte to spare
    (100, 100, None, "near-limit"),       # exactly at target: no room left
    (100, 95, _OV, "stale-override"),     # a stale override outranks near-limit
    (0, 0, None, "ok"),                   # zero-target surface: no band, no division
    (0, 1, None, "FAIL"),                 # zero-target surface still fails when exceeded
]


def run_self_test():
    failures = []
    for i, (target, actual, override, expected) in enumerate(SELF_TEST_CASES):
        verdict, _ = classify(target, actual, override)
        ok = verdict == expected
        print("  %s self-test[%d] target=%s actual=%s override=%s -> %s (expected %s)"
              % ("ok  " if ok else "FAIL", i, target, actual,
                 "yes" if override else "no", verdict, expected))
        if not ok:
            failures.append(i)
    total = len(SELF_TEST_CASES)

    # Coverage-integrity self-tests: prove ``check`` defends its own coverage
    # (empty / missing / downgraded / malformed-override must be flagged) and
    # that the SHIPPED BUDGETS is itself coverage-clean -- tying the self-test
    # to the real config, not only synthetic inputs.
    def _spec(rid, kind=("file", "x"), target=1, override=None):
        return {"id": rid, "measure": kind, "target": target, "override": override}

    required = sorted(REQUIRED_MEASURED_IDS)
    healthy_required = [_spec(r) for r in required]
    downgraded = [_spec(r, kind=("pending", "o")) if r == required[0] else _spec(r)
                  for r in required]
    bad_allow = [_spec(r) for r in required]
    bad_allow[0] = _spec(required[0],
                         override={"allow": 1, "reason": "r", "tracking": "t"})
    blank_reason = [_spec(r) for r in required]
    blank_reason[0] = _spec(required[0],
                            override={"allow": 2, "reason": "  ", "tracking": "t"})

    cov_cases = [
        ("empty", [], True),
        ("healthy-required", healthy_required, False),
        ("missing-required", [_spec("some-unrelated-surface")], True),
        ("downgraded-required", downgraded, True),
        ("override-allow-not-above-target", bad_allow, True),
        ("override-blank-reason", blank_reason, True),
        ("shipped-BUDGETS", BUDGETS, False),
    ]
    for name, budgets, expect_errors in cov_cases:
        errs = coverage_errors(budgets)
        ok = bool(errs) == expect_errors
        total += 1
        print("  %s coverage[%s] errors=%d (expected %s)" % (
            "ok  " if ok else "FAIL", name, len(errs),
            "some" if expect_errors else "none"))
        if not ok:
            failures.append("coverage:" + name)

    # Skill-body coverage (#140), against SYNTHETIC surfaces so --self-test stays
    # render-independent: a fresh checkout with no build/ must not report a
    # missing render as a classifier bug. `check` owns the live-tree verdict and
    # already fails closed on an absent render with the correct remediation.
    synthetic = [_spec("skill-body.demo.alpha"), _spec("skill-body.demo.beta")]
    ok_override = {"skill-body.demo.alpha": {"allow": 2, "reason": "r",
                                             "tracking": "t"}}
    dangling = {"skill-body.demo.gone": {"allow": 2, "reason": "r",
                                         "tracking": "t"}}
    skill_cases = [
        ("resolving-override-accepted",
         not skill_body_override_errors(ok_override, synthetic), True),
        ("dangling-override-detected",
         bool(skill_body_override_errors(dangling, synthetic)), True),
        ("empty-discovery-is-a-coverage-error",
         any("no rendered skill bodies" in e for e in coverage_errors(
             healthy_required, require_skill_bodies=True)), True),
        ("discovered-bodies-satisfy-the-requirement",
         not any("no rendered skill bodies" in e for e in coverage_errors(
             healthy_required + synthetic, require_skill_bodies=True)), True),
    ]
    for name, observed, expected in skill_cases:
        ok = observed == expected
        total += 1
        print("  %s skill-body[%s] -> %s (expected %s)" % (
            "ok  " if ok else "FAIL", name, observed, expected))
        if not ok:
            failures.append("skill-body:" + name)

    print("\ncontext-budget-audit self-test: %d cases, %d failing"
          % (total, len(failures)))
    if failures:
        print("\nThe budget gate self-test failed; fix classify() / "
              "coverage_errors() before trusting the gate.")
    return 1 if failures else 0


# --- entrypoint --------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic context-budget gate for #601 P1.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "mode", nargs="?", default="check", choices=["check"],
        help="check: deterministic budget gate (default).",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="run the classifier self-test (proves the gate detects violations) "
             "and exit.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    budgets = all_budgets()
    cov = coverage_errors(
        budgets,
        skill_overrides=SKILL_BODY_OVERRIDES,
        require_skill_bodies=True,
    )
    rows = evaluate(budgets)
    failing = _emit(rows)
    if cov:
        print("\ncoverage integrity FAILED (the gate must not silently drop "
              "enforcement):")
        for err in cov:
            print("  - " + err)
    return 1 if (failing or cov) else 0


if __name__ == "__main__":
    sys.exit(main())
