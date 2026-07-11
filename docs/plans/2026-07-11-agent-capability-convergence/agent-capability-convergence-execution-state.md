# Execution State: Agent capability convergence

## Execution State

- Source document: docs/plans/2026-07-11-agent-capability-convergence/agent-capability-convergence-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/568>
- Current sprint: Sprint 2
- Status: in-progress
- Current gate: Replacement behavior lanes
- Plan branch: `feat/agent-capability-convergence`
- Integration PR: pending
- Current lanes: Lane B (`browser-evidence`) and Lane C (`remaining-skills`)
- Next tasks: Tasks 2.1 and 2.2 — land replacement behavior
- Upstream prerequisite: <https://github.com/sympoies/nils-cli/issues/1115> for Task 2.1
- Task 3.1 gate: Tasks 2.1 and 2.2 must both land before shared retirement begins
- Blockers: none
- Last updated: 2026-07-11

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Review all 66 disposition rows | done | #561 handoff and frozen ledger; https://github.com/graysurf/agent-runtime-kit/issues/568; reviewed=26 pending=40; focused reviewed-active contract and full `scripts/ci/all.sh` positions 1-15 pass; PR #569 merged as b4a5a8a | Lane A (`disposition`); no source retirement in this pass |
| 2.1 | Migrate Browser and Evidence behavior | in-progress | pending lane PR and validation; nils-cli #1115; dispatch #568 | Lane B (`browser-evidence`); replacement behavior only |
| 2.2 | Converge all remaining agent-only skill families | done | PR #571 merged as 0c9cb095; provider CI pass; review threads resolved; pinned full CI positions 1-15 and hooks 97/97 pass | Lane C (`remaining-skills`); replacement behavior only |
| 3.1 | Apply manifest, render, compatibility, and cleanup retirement | pending | pending second Lane A PR and validation | Sole shared manifest/source retirement owner |
| 3.2 | Add portable convergence deployment acceptance | pending | pending Lane D PR and validation | Public generic roles; no private host details |
| 4.1 | Activate and verify both runtime roles from merged main | pending | pending private redacted acceptance | Lane D post-integration; private artifacts stay local |

## Validation Log

- 2026-07-11: `agent-docs preflight --intent project-dev --docs-home .`
  resolved all required documents and declared `bash scripts/ci/all.sh` plus
  `bash tests/hooks/run.sh` as the project-dev completion contract.
- 2026-07-11: installed `agent-runtime`, `plan-issue`, `plan-tooling`, and
  `forge-cli` report v1.21.15, satisfying dispatch workflow floors.
- 2026-07-11: Lane A Task 1.1 reviewed all 66 frozen sources and callers.
  Twenty-six direct outcomes now carry reviewed invocation metadata and
  `exposure.profile: default`; 40 replacement-dependent rows remain pending
  for Lanes B/C and atomic Task 3.1 retirement. Main governance, the focused
  reviewed-active contract, Codex/Claude/Hermes list-skills read-back,
  `git diff --check`, and 97/97 hook tests passed.
- 2026-07-11: after the Task 1.1 catalog became mixed reviewed/pending, the
  exposure-contract negative fixture's literal pending-row rewrite no longer
  constructed its intended invalid case. Expanded Lane A scope replaced that
  setup with deterministic active-baseline selection and explicit removal of
  invocation/exposure metadata. Failing-first evidence captured the regression;
  `bash scripts/ci/all.sh` then passed all 15 positions.

## Session Notes

- 2026-07-11: promoted #562 to L3 after the user explicitly requested one
  shared dispatch spine with four lanes and end-to-end dual-role activation.
- 2026-07-11: lane boundaries centralize shared manifest and retirement edits
  in Lane A. Lanes B and C land replacement behavior first; Lane D validates
  portable activation and then performs private post-merge acceptance.
- 2026-07-11: dispatch issue #568 opened with superseding source/plan/state
  snapshots after read-only lane scoping corrected pending/reviewed sequencing
  and product capability claims.
- 2026-07-11: Lane A Task 1.1 retained Reporting, direct Media and macOS
  desktop outcomes, discussion/build/handoff outcomes, Issue triage/follow-up,
  one generic Code Review outcome, one governed PR lifecycle, one L2 plan
  lifecycle, one L3 dispatch lifecycle, and explicitly user-requested
  maintenance outcomes. Browser/Evidence and all other control-plane,
  bookkeeping, duplicate, mode, and lifecycle-substep decisions remain pending
  until their assigned replacement lane lands.
