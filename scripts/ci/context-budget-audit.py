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
  * representative project-dev edit-phase required reading           <= 20 KiB
  * startup memory context (header + profile)                        <= 1.25 KiB
  * new context on an unchanged repeat prompt                        == 0 bytes

Each surface is classified:

  ok             actual <= target
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
non-zero if any surface FAILs or carries a stale override.

``--self-test`` runs the classifier against synthetic surfaces and asserts the
verdicts, proving the gate actually detects an over-budget surface, honors an
override, and rejects an override that no longer applies.

Budgets are declared inline (see ``BUDGETS``) rather than in a YAML manifest so
the gate stays stdlib-only and runs on any python3 (including macOS system
python), matching scripts/ci/version-baseline-audit.py.
"""

from __future__ import annotations

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KIB = 1024


# --- budget declarations -----------------------------------------------------
# Each entry:
#   id          stable surface identifier
#   description human-readable surface
#   measure     how the actual size is obtained:
#                 ("file", "<repo-relative path>")     -> size of one file
#                 ("doc-set", ["<path>", ...])         -> sum of file sizes
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
        "target": 4 * KIB,
        "override": {
            "allow": 6656,
            "reason": "Documented budget decision (#601 slice 3c): 4 KiB is the "
                      "aspirational target; ~6.5 KiB is the irreducible always-on "
                      "floor after the three-layer compaction (from 11,360 bytes). "
                      "The remainder is safety and behavioral invariants "
                      "(delivery gates, memory/consent boundaries, goal-wait, "
                      "tier and intent routing); detailed procedure moved to "
                      "core/policies/intent-cards.md and the runbooks this layer "
                      "points to. Further reduction would compress "
                      "safety-critical wording.",
            "tracking": "graysurf/agent-runtime-kit#601 (documented budget decision)",
        },
    },
    {
        "id": "rendered-agent-home.claude",
        "description": "Rendered Claude always-on home policy (AGENT_HOME).",
        "measure": ("file", "build/claude/AGENT_HOME.md"),
        "target": 4 * KIB,
        "override": {
            "allow": 6400,
            "reason": "Documented budget decision (#601 slice 3c): same "
                      "AGENT_HOME source as codex; 4 KiB aspirational, ~6 KiB "
                      "irreducible always-on floor after compaction "
                      "(from 10,612 bytes).",
            "tracking": "graysurf/agent-runtime-kit#601 (documented budget decision)",
        },
    },
    {
        "id": "rendered-agent-home.hermes",
        "description": "Rendered Hermes always-on home policy (AGENT_HOME).",
        "measure": ("file", "build/hermes/AGENT_HOME.md"),
        "target": 4 * KIB,
        "override": {
            "allow": 6272,
            "reason": "Documented budget decision (#601 slice 3c): same "
                      "AGENT_HOME source as codex; 4 KiB aspirational, ~6 KiB "
                      "irreducible always-on floor after compaction "
                      "(from 9,963 bytes).",
            "tracking": "graysurf/agent-runtime-kit#601 (documented budget decision)",
        },
    },
    {
        "id": "edit-phase-required-reading.project-dev",
        "description": (
            "Home-scope project-dev policy docs this kit forces a consumer to "
            "read before an edit (the inheritable required set). Phase-scoped by "
            "#601 P1 slice 3d: the `edit` phase keeps the test-first and "
            "edit-mechanics runbooks and excludes the delivery (git-delivery, "
            "work-tier-levels) and review (code-review-delegation) runbooks. This "
            "list MUST mirror the home-scoped (scope = \"home\") project-dev docs "
            "tagged phase = \"edit\" (or left untagged) in AGENT_DOCS.toml."
        ),
        "measure": ("doc-set", [
            "core/policies/files-hooks-validation.md",
            "core/policies/evidence-control-plane.md",
        ]),
        "target": 20 * KIB,
        # Override removed in #601 P1 slice 3d: with phase-scoped resolution the
        # edit phase no longer inherits the delivery/review runbooks, so the
        # measured set is back under the bare 20 KiB target (RED->GREEN).
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
            "New agent-docs / memory context emitted on an unchanged repeat "
            "prompt."
        ),
        "measure": ("behavioral",
                    "tests/hooks/test_shared_hooks.py (delta cue + memory "
                    "once-per-session dedupe)"),
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
    "edit-phase-required-reading.project-dev",
})

_MEASURED_KINDS = ("file", "doc-set")


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
    if kind == "pending":
        return None, "measurement pending, owned by %s" % measure[1]
    if kind == "behavioral":
        return None, "enforced by %s" % measure[1]
    raise ValueError("unknown measure kind: %r" % (kind,))


def classify(target, actual, override):
    """Classify one surface. Returns (verdict, note).

    verdict in {"ok", "waived", "FAIL", "stale-override", "skip"}.
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
        return "ok", ""
    # actual > target
    if override is not None and actual <= override["allow"]:
        return "waived", "allow=%d over target by %d; tracking %s" % (
            override["allow"], actual - target, override["tracking"])
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


def coverage_errors(budgets):
    """Return coverage-integrity errors (empty list == ok); fail-closed.

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
    return errors


def _emit(rows):
    failing = 0
    for spec, actual, detail, verdict, note in rows:
        actual_s = "%d" % actual if actual is not None else "-"
        print("  %-14s %-42s target=%-6d actual=%-7s %s" % (
            verdict, spec["id"], spec["target"], actual_s, note or detail))
        if verdict in ("FAIL", "stale-override"):
            failing += 1
    print("\ncontext-budget-audit: %d surfaces, %d failing" % (len(rows), failing))
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

    cov = coverage_errors(BUDGETS)
    rows = evaluate(BUDGETS)
    failing = _emit(rows)
    if cov:
        print("\ncoverage integrity FAILED (the gate must not silently drop "
              "enforcement):")
        for err in cov:
            print("  - " + err)
    return 1 if (failing or cov) else 0


if __name__ == "__main__":
    sys.exit(main())
