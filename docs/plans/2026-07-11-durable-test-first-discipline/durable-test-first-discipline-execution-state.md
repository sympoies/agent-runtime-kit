# Execution State: Strengthen Test-First Discipline for Durable Tests

## Execution State

- Source document: docs/plans/2026-07-11-durable-test-first-discipline/durable-test-first-discipline-discussion-source.md
- Plan document: docs/plans/2026-07-11-durable-test-first-discipline/durable-test-first-discipline-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/578>
- Current sprint: Sprint 4
- Status: delivery in progress
- Current task: Task 4.3
- Next task: checkpoint review/state, merge #583, then complete tracker closeout
- Branch: feat/durable-test-first-discipline
- PR: https://github.com/graysurf/agent-runtime-kit/pull/583
- Upstream issue: https://github.com/sympoies/nils-cli/issues/1124
- Last updated: 2026-07-12
- Branch/review repair/PR: feat/durable-test-first-discipline; 8b83ab6; #583
- Implementation commit: 9ab9ed84

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Open and initialize the runtime-kit plan tracker | done | plan bundle committed; plan validation passed; #578 source/plan/state visible audit clean; run 20260711T234618Z-issue-578 initialized | Tracker reconciled; no lifecycle blocker |
| 1.2 | Open the linked nils-cli implementation issue | done | sympoies/nils-cli#1124 created, read back, and linked from #578 | Implementation-ready upstream dependency linked to #578 |
| 1.3 | Freeze evidence v2 fixtures and error taxonomy | done | focused pre-edit failures retained under agent-out; positive, negative, compatibility, and duplicate fixtures committed in sympoies/nils-cli#1125 | Meaningful-red expectations and stable error taxonomy frozen before production edits |
| 2.1 | Implement the v2 record and CLI lifecycle | done | sympoies/nils-cli#1125; package tests and full local-fast pass | New writes use v2; v1 remains readable and is rejected by strict verification |
| 2.2 | Make forge consume strict durable evidence | done | sympoies/nils-cli#1125; forge package tests and validation-kind integration pass | Existing gate opt-in and exemptions remain; v1 gets an actionable re-record error |
| 2.3 | Validate, review, deliver, and release nils-cli | done | PR #1125 merged at f054ba60; release PR #1128; v1.21.19 release/tap; Linux/macOS/coverage/CodeQL green; #1124 closed | Four specialist lenses converged; five review threads resolved; #1126 retains subject-binding follow-up |
| 3.1 | Rewrite the test-first engineering contract | done | released v2 evidence under agent-out; canonical skill source and three product goldens updated | One full qualitative contract; home policy remains a concise pointer |
| 3.2 | Strengthen testing review and guided implementation | done | testing agent/specialist and guided-build source/golden assertions; focused domains 7/7 each | Qualitative review remains outside deterministic CLI |
| 3.3 | Pin the release and add deterministic acceptance coverage | done | pin/sha/snapshot/mirrors at v1.21.19; evidence 6/6; PR 5/5; version baseline 21/21 | Released binary only; v2 accepted, v1 rejected, no off-pin output |
| 4.1 | Run declared runtime-kit validation | done | `bash scripts/ci/all.sh` positions 1-15 pass; runtime smoke 89 pass/1 host skip/0 fail; `bash tests/hooks/run.sh` 97/97 | Released pin v1.21.19; strict v2 evidence verify complete with no residual gaps |
| 4.2 | Run mandatory specialist review and converge findings | done | four lens findings posted to #583; repair 8b83ab6 passed follow-up testing, maintainability, API-contract, and red-team review; six threads resolved; combined approval recorded | Local CI 15/15, hooks 97/97, GitHub CI and CodeQL green |
| 4.3 | Merge, close, and archive the L2 tracker | in-progress | #583 is mergeable with zero unresolved threads, zero unchecked tasks, and non-closing `Refs #578` linkage | State/review checkpoint, merge, terminal tracker close, and archive pending |

## Blockers

- None.

## Validation

| Command | Status | Evidence |
| --- | --- | --- |
| `plan-tooling validate --file docs/plans/2026-07-11-durable-test-first-discipline/durable-test-first-discipline-plan.md --format text --explain` | pass | 1 plan valid; 0 errors on 2026-07-11 |
| `bash scripts/ci/all.sh` | pass | positions 1-15 pass on v1.21.19; runtime smoke 89 pass, 1 host-capability skip, 0 fail |
| `bash tests/hooks/run.sh` | pass | 97 tests passed on 2026-07-12 |

## Session Log

- 2026-07-11: Classified the work as L2 because it couples an evidence schema,
  released nils-cli/forge behavior, runtime-kit policy and rendered skill
  surfaces, review contracts, acceptance coverage, and lifecycle closeout.
- 2026-07-11: Plan-archive searches found no existing plan for test maintenance,
  meaningful-red evidence, or old-spec migration. Current record v1 and forge
  verification were inspected to ground the v2 scope.
- 2026-07-11: Authored the implementation-ready source, four-sprint plan, and
  initial execution ledger on `feat/durable-test-first-discipline`.
- 2026-07-11: Plan validation passed with one valid plan and zero errors before
  the provider tracker dry-run.
- 2026-07-11: Reconciled #578 into run `20260711T234618Z-issue-578`, opened and
  read back sympoies/nils-cli#1124, and started the upstream test-first fixture
  task in `feat/durable-test-first-evidence`.
- 2026-07-12: Captured focused failing evidence before production edits,
  implemented deterministic evidence v2 and strict forge consumption, passed
  package tests plus the 5,835-test local-fast gate, and opened
  sympoies/nils-cli#1125 for mandatory specialist review.
- 2026-07-12: Converged testing, maintainability, API-contract, and red-team
  review; merged #1125; released v1.21.19 through #1128; passed tag-commit CI,
  four-platform artifact audit, Homebrew tap update, and installed-binary v2
  pre-edit verification; closed sympoies/nils-cli#1124 with #1126 retained.
- 2026-07-12: Rewrote the canonical durable lifecycle, testing review, and
  guided-build pointer; pinned v1.21.19; regenerated three-product goldens;
  passed focused evidence, PR, code-review, conversation, governance, baseline,
  security, and product-leak gates before the signed runtime-kit checkpoint.
- 2026-07-12: Committed 9ab9ed84, passed all 15 CI positions and all 97 hook
  contract tests, then finalized a verify-clean v2 record with six scoped
  passing validations and no residual gaps.
- 2026-07-12: Opened #583; testing, maintainability, API-contract, and red-team
  review exposed an incomplete test-impact ledger, create/deliver owner drift,
  missing deliver-gate acceptance, retained vocabulary drift, and stale tracker
  evidence. Posted six native threads before repair, then split create/deliver
  probes, added exact deliver preflight verdict assertions, reconciled docs and
  evidence, and reran all 15 CI positions plus 97 hook tests successfully.
- 2026-07-12: All four follow-up lenses passed at repair 8b83ab6; resolved all
  six native review threads, confirmed four checked PR tasks and green GitHub
  CI/CodeQL, posted combined approval, and changed the tracker link to
  non-closing `Refs #578` so merge cannot race the L2 close-ready workflow.
