# Execution State: Agent capability convergence

## Execution State

- Source document: docs/plans/2026-07-11-agent-capability-convergence/agent-capability-convergence-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/568>
- Current sprint: Sprint 4
- Status: in-progress
- Current gate: Post-integration dual-role activation
- Plan branch: `feat/agent-capability-convergence`
- Integration PR: pending; Task 3.2 is merged into the plan branch
- Current lanes: Lane D (`post-integration-acceptance`)
- Next task: Task 4.1 — integrate to `main`, activate, and verify both runtime roles
- Upstream prerequisite: complete; nils-cli v1.21.17 and Tasks 2.1/2.2 landed
- Task 3.1 gate: complete; PR #577 merged as 92da055
- Task 3.2 gate: complete; PR #581 merged as bda76df
- Blockers: none
- Last updated: 2026-07-12

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Review all 66 disposition rows | done | #561 handoff and frozen ledger; https://github.com/graysurf/agent-runtime-kit/issues/568; reviewed=26 pending=40; focused reviewed-active contract and full `scripts/ci/all.sh` positions 1-15 pass; PR #569 merged as b4a5a8a | Lane A (`disposition`); no source retirement in this pass |
| 2.1 | Migrate Browser and Evidence behavior | done | PR #575 merged as 09536bc7; final approval; 13/13 review threads resolved; Browser 3/3, Evidence 7/7, hooks 113/113, full CI positions 1-15, and provider CI pass | Lane B (`browser-evidence`); documented Bash CWD and host-trust ceilings |
| 2.2 | Converge all remaining agent-only skill families | done | PR #571 merged as 0c9cb095; provider CI pass; review threads resolved; pinned full CI positions 1-15 and hooks 97/97 pass | Lane C (`remaining-skills`); replacement behavior only |
| 3.1 | Apply manifest, render, compatibility, and cleanup retirement | done | PR #577 merged as 92da055; provider CI pass; 3/3 findings fixed; testing and maintainability follow-up pass; 0 unresolved threads | Atomic retirement complete: 26 active outcomes, 40 retired surfaces, ownership-safe rollback |
| 3.2 | Add portable convergence deployment acceptance | done | PR #581 merged as bda76df; detached-HEAD Codex/Claude convergence 5/5; pinned pre-PR positions 1-15; provider CI and specialist review pass | Lane D portable acceptance; generic roles and redacted evidence only |
| 4.1 | Activate and verify both runtime roles from merged main | in-progress | pending integration PR and private redacted acceptance | Lane D post-integration; private artifacts stay local |

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
- 2026-07-11: Lane B Task 2.1 landed through PR #575 as 09536bc7 after
  nils-cli v1.21.17 release convergence. Final focused repairs passed 6/6,
  Browser 3/3, Evidence 7/7, hooks 113/113, full CI positions 1-15, and
  provider CI; 13/13 review threads were resolved and final red-team found no
  actionable findings.
- 2026-07-12: Task 3.1 landed through PR #577 as 92da055. The final surface has
  26 active user outcomes and 40 retired internal surfaces. Provider CI passed;
  three review findings were fixed in b85eb24, testing and maintainability
  follow-up passed, all review threads resolved, and cleanup fault injection
  proves descriptor-bound rollback after rename, during deletion, and before
  final removal.
- 2026-07-12: Task 3.2 landed through PR #581 as bda76df. Detached-HEAD
  convergence passed 5/5 for Codex and Claude, including historical upgrade,
  independently rebuilt receipt digests, rollback, retired-surface pruning,
  operator-state preservation, and idempotency. The pinned pre-PR stack passed
  all 15 positions; provider CI and testing, maintainability, and security
  review passed with no unresolved threads.

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
- 2026-07-11: both replacement lanes are merged. Task 3.1 now owns the single
  atomic transition from 66 exposed skill surfaces to 26 direct user outcomes,
  including stale installed-plugin cleanup and compatibility-negative tests.
- 2026-07-12: Task 3.1 is merged and the plan advances to Task 3.2. Portable
  acceptance remains product-neutral and may publish only generic role names,
  revision provenance, redacted artifact metadata, and deterministic results.
- 2026-07-12: Task 3.2 is merged and the plan advances to Task 4.1. The final
  integration must preserve plan-branch ancestry so the historical retirement
  revision remains available. Live Codex and Claude activation and bounded
  desktop evidence remain private; the public record receives only generic,
  redacted pass/fail results.
