# Execution State: Deliver and deploy the agent-hook control plane

<!-- plan-issue-record:v2 role=state profile=dispatch -->
## Execution State

- Source document:
  `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-plan.md`
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/686>
- Shared dispatch issue: <https://github.com/graysurf/agent-runtime-kit/issues/686>
- Coordination dependency: <https://github.com/graysurf/agent-runtime-kit/issues/676>
- Status: in progress; every implementation lane is merged into the plan branch
  and the orchestrator is delivering the runtime-kit integration PR
- Current sprint: Sprint 3 integrates the approved lanes
- Current task: Task 3.3 delivers the runtime-kit integration PR
- Next task: one focused integration review, merge, then deployed-main acceptance
- Plan branch: `feat/agent-hook-control-plane`
- Active lanes: all implementation lanes are terminal; only orchestrator-owned
  integration, deployment, acceptance, and closeout remain
- Release prerequisite: satisfied by installed v1.25.5
- Deployment prerequisite: Task 3.3
- Blockers: none; exact v1.25.5 is installed and published
- Last updated: 2026-07-20
- Branch/commit/PR: plan branch `feat/agent-hook-control-plane` at `8ce8c70c`;
  runtime-kit PR #707 merged as `8ce8c70c`; nils-cli PR #1330 merged as
  `4a719a8f`; release PR #1332/tag v1.25.5 resolved to `7a04b0c9`; private PR
  #44 merged as `640f39d7`

## Validation Plan

- Plan floor: `plan-tooling validate`, `git diff --check`, source/plan/state
  snapshot attachment, dispatch run initialization, and visible status.
- Nils floor: meaningful red; focused crate/session tests; clippy; docs,
  completion, JSON, and publish audits; local-fast; independent review; release,
  tap, and installed-version read-back.
- Runtime-kit floor: meaningful red; full inventory/parity; provider render,
  setup, shadow, rollback, coordination, liveness, privacy, latency, sandbox,
  runtime smoke, `scripts/ci/all.sh`, and `tests/hooks/run.sh` against the exact
  released pin.
- Local-scripts floor: private skill portfolio coverage, `_tools/check.zsh`,
  independent review, merge read-back, and ownership-safe repository sync.
- Activation floor: merged-main preview/apply, both-provider doctor and legacy
  absence, deterministic acceptance, bounded fresh sessions, break-glass and
  remove/restore rehearsal, privacy scan, latency budget, and terminal cleanup.
- Delivery floor: v2 test-first/docs-impact evidence, exact-head checks,
  independent native review, zero unresolved actionable threads/tasks, strict
  close-ready, post-close audit, archive, and safe worktree cleanup.

## Task Ledger

| ID | Status | Task | Lane | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| 1.1 | done | Freeze contracts, inventory inputs, and meaningful red | nils-control-plane | Bound v2 evidence; behavioral red before production edits | Contract and affected-test ownership frozen |
| 1.2 | done | Implement config, policy, dispatch, adapters, and aggregation | nils-control-plane | PR #1314; affected suite 672/672 | Publishable crate and provider adapters implemented |
| 1.3 | done | Implement setup ownership, doctor, and compatibility migration | nils-control-plane | PR #1314; config.toml/hooks.json and Claude migration regressions | One transactional registration owner |
| 1.4 | done | Implement break-glass and writer-liveness integration | nils-control-plane | PR #1314; signed recovery, shared heartbeat, process and filesystem trust regressions | Consumes #676 coordination projection |
| 1.5 | done | Validate and deliver the nils-cli lane PR | nils-control-plane | PR #1314 head `76725819`; affected 916/916, all 83 agent-hook tests, local-fast/full parity 7,059/7,059; seven final lenses and exact-head provider CI passed; 59/59 review threads resolved | Delivery-owner outcome bound to exact head; no actionable findings remain |
| 1.6 | done | Independently review, merge, release, and verify nils-cli | orchestrator | PR #1314 merged as `8c65fd02`; release PR #1328/tag v1.25.4 at `1308bdc1`; GitHub Release 8 assets; crates.io 4/4 dependency closure; tap run `29739142071`; installed `agent-hook` and `agent-session` 1.25.4 | Exact tag, registry, tap, Homebrew, and binary read-back passed |
| 1.7 | done | Close the single-ingress coordination sequencing gap | nils-coordination-ingress | PR #1330 merged as `4a719a8f`; release PR #1332/tag v1.25.5 at `7a04b0c9`; release run `29748225161`; tap run `29750702508`; crates.io run `29750951649`; installed binaries 1.25.5 | One focused review found one P1; affected-only repair/recheck passed and the only thread is resolved |
| 2.1 | done | Freeze the complete rule inventory, policy schema, and red baseline | runtime-policy-cutover | Commit `c0b07437`; 68 registrations, 22 handlers, 18 coordination rules | Exact contract consumer validated |
| 2.2 | done | Implement the policy bundle and typed rule capabilities | runtime-policy-cutover | Static 6/6; legacy 295/295; executable 9/9; p95 3.344 ms | Cutover waits for exact release |
| 2.3 | done | Replace rendered registrations and add reversible sync migration | runtime-policy-cutover | Policy 94 rules; static 6/6, cutover 4/4, executable 9/9, setup migration 3/3; hooks 311/311; PR #707 head 98104c10; migration 6/6, agent-hook 25/25, hooks 311/311, pre-PR positions 1-17 | Setup transaction now precedes legacy cleanup; forced failure preserves exact bytes and action-specific remove restores them |
| 2.4 | done | Validate and deliver the runtime-kit lane PR | runtime-policy-cutover | Focused suites green; full required gate active; PR #707 merged as 8ce8c70c; focused finding and affected-only recheck passed; remote run 29757402589 green; zero unresolved threads | One focused review only; lane merged to feat/agent-hook-control-plane |
| 3.1 | done | Update private-agent-session coordination and recovery behavior | private-session-operations | PR #44 head `80c38fac`; focused skill/portfolio/full checks passed | `off` skips coordination lifecycle only; removal consumes action-specific preview digest |
| 3.2 | done | Independently review, merge, and synchronize the private skill lane | orchestrator | Single focused review repaired two findings; PR #44 merged as `640f39d7`; zero unresolved threads | Repository synchronization remains part of post-main deployment, not another review cycle |
| 3.3 | in-progress | Deliver the runtime-kit integration PR | orchestrator | pending; Plan branch 8ce8c70c contains all approved lane merges | Prepare one integration PR to main with one focused review |
| 4.1 | pending | Reconcile #676 dependency state before activation | orchestrator | pending; Provider read-back: #676 is closed with complete tracking closeout | Reconcile the already-closed dependency during live activation; do not reopen absent contradictory evidence |
| 4.2 | pending | Preview, apply, and verify installed runtime surfaces | deployment-acceptance | pending | Deploy merged main only |
| 4.3 | pending | Run deterministic and live disposable-session acceptance | deployment-acceptance | pending | Synthetic content and cleanup |
| 4.4 | pending | Close #676 and #686 and archive the completed plan | orchestrator | pending | Strict closeout and final operator report |

## Validation Log

- 2026-07-20: The maintainer explicitly authorized implementation and
  deployment of #686, required integration with agent-session coordination, and
  requested a final remaining-hook and recovery/disable report.
- 2026-07-20: Feasibility analysis updated #686 with the accepted single-config,
  thin-ingress, versioned-policy, single-registration-owner, liveness, and
  config-independent break-glass architecture.
- 2026-07-20: Runtime-kit, nils-cli, and local-scripts primary checkouts were
  clean. Existing managed worktrees were inventoried and preserved.
- 2026-07-20: `agent-docs` strict audit/project-dev preflight passed in nils-cli
  and runtime-kit; all required repository and skill documents were read before
  this plan edit.
- 2026-07-20: Plan archive and live provider searches found no existing L3
  dispatch record for this control plane. #676 is a complementary serial
  coordination dependency, not a duplicate.
- 2026-07-20: #676 live tracking status passed visible reconciliation at
  `RECORD_REVIEWED`; its nils mechanism is merged into current nils `main`, but
  installed v1.24.4 lacks the coordination commands because release and
  downstream activation remain pending.
- 2026-07-20: The request was reclassified from the issue's proposed L2 into L3
  because the maintainer requested complete cross-repository implementation,
  independent lane review, release, deployment, live acceptance, and closeout.
- 2026-07-20: Lane A delivered nils-cli PR #1314. Seven independent specialist
  lenses posted findings before repair. The repaired exact head `860a4e4d`
  passed the affected 672-test suite, workspace all-feature clippy, docs and
  doctests, and the 7,002-test local-fast gate; exact-head test-first evidence is
  complete. Testing and security follow-up passed; remaining follow-up lenses
  and required provider CI are still active.
- 2026-07-20: Lane B completed the strict policy/inventory foundation without
  provider cutover. It recorded 68 legacy registrations, 22 unique handlers,
  and 18 coordination rules; the exact executable consumer passed 9/9 with
  p95 3.344 ms. Tasks 2.3 and 2.4 remain release-gated.
- 2026-07-20: Lane A final exact-head evidence converged at nils-cli PR #1314
  head `76725819c2b7e0645c271cb0fd2c47414b370258`. The affected suite passed
  916/916 tests including all 83 agent-hook tests; full CI-parity validation
  passed 7,059/7,059. Testing, security, performance, maintainability,
  API-contract, data-migration, and red-team lenses all passed.
- 2026-07-20: Provider read-back for the exact head reported all checks green,
  59/59 historical review threads resolved, zero current unresolved threads,
  and zero pending native reviews. Current nils-cli `main` at `c5e517f7` changes
  only an unrelated git-cli test path after the review base and produces a
  conflict-free merge tree; the delivery-owner review marked the head
  merge-ready without another broad review round.
- 2026-07-20: The orchestrator squash-merged nils-cli PR #1314 at bound head
  `76725819` into merge `8c65fd02`. Release PR #1328 then merged v1.25.4 at
  `1308bdc1`; exact-main Linux, macOS, coverage, cargo-deny, and CodeQL gates
  passed before the tag release proceeded.
- 2026-07-20: GitHub Release v1.25.4 published eight cross-platform assets and
  dispatched Homebrew tap run `29739142071`, which passed. Homebrew upgraded
  the local installation to 1.25.4; both `agent-hook --version` and
  `agent-session --version` read back 1.25.4.
- 2026-07-20: crates.io publish run `29739333705` published the minimum ordered
  dependency closure (`nils-test-support`, `nils-build-info`, `nils-common`,
  `nils-agent-hook`) at 1.25.4. The post-run registry snapshot reported 4/4
  published, zero missing, zero yanked, and zero errors.
- 2026-07-20: Runtime cutover found a real v1.25.4 contract gap. The compiled
  handler allowlist excludes transactional session coordination; the evaluator
  can project semantic/liveness decisions but cannot defer `admit` until the
  aggregate policy result allows or complete/reconcile the PostTool operation.
  Registering coordination as a separate Claude sibling would race. The
  orchestrator rejected advisory-only downgrade and a second registration
  writer, opened bounded Task 1.7, and held Task 2.3 until the next exact patch
  release is installed.
- 2026-07-20: Private-agent-session PR #44 converged after one focused review.
  Two real findings were repaired on exact head `80c38fac`; the same reviewer
  passed the affected-only recheck, both threads were resolved, and the
  orchestrator merged the PR as `640f39d7` without another broad review round.
- 2026-07-20: Nils-cli PR #1330 converged on exact head `fb54272a`. One focused
  review found the Codex no-capability guard-removal P1; the bounded repair and
  same-reviewer fingerprint recheck passed. Linux, macOS, coverage, CodeQL,
  cargo-deny, and JUnit were terminal green; the only thread was resolved; the
  orchestrator merged the PR as `4a719a8f`.
- 2026-07-20: Release PR #1332 merged v1.25.5 as `7a04b0c9`. Release run
  `29748225161` passed exact-SHA CI, published eight assets, and dispatched tap
  run `29750702508`, which passed. Homebrew and both installed binaries read
  back 1.25.5.
- 2026-07-20: Crates.io run `29750951649` published the minimum dependency
  closure (`nils-test-support`, `nils-build-info`, `nils-common`,
  `nils-agent-hook`) at 1.25.5. Registry read-back reported 4/4 published and
  zero missing, yanked, or errors.
- 2026-07-20: Lane B completed Task 2.3 against exact v1.25.5. Native
  rule-specific Codex/Claude registrations and the Claude sibling sequencer
  were retired; sync now installs the digest-pinned XDG policy/config and uses
  an exact setup preview/apply digest. Policy 6/6, cutover 4/4, executable 9/9,
  setup migration 3/3, version policy 13/13, memory 3/3, and shared hooks
  311/311 passed before the full required gate.
- 2026-07-20: Runtime-kit PR #707 converged at exact head `98104c10`. The one
  focused review found a setup-before-cleanup rollback P1; the bounded repair
  added production-order, forced-failure exact-preservation, and
  success/remove exact-restoration regressions. The same reviewer passed the
  affected-only recheck, pre-PR positions 1-17 and remote run `29757402589`
  passed, zero threads remained, and the orchestrator squash-merged the PR to
  the plan branch as `8ce8c70c`.
- 2026-07-20: Provider truth shows coordination dependency #676 already closed.
  Task 4.1 will reconcile that terminal dependency during activation without
  reopening it unless live acceptance contradicts its closeout evidence.

## Decision Log

- 2026-07-20: Reuse #686 as the one shared dispatch issue instead of opening a
  duplicate tracker.
- 2026-07-20: Preserve #676 as a dependency ledger and close it only after the
  coordination release, runtime admission, private workflow, and live
  acceptance are evidenced here.
- 2026-07-20: Keep nils mechanism, runtime policy, private operations, and
  post-merge deployment as separate ownership lanes. Only the orchestrator may
  merge approved lane PRs or close either tracker.
- 2026-07-20: Keep a hard known-live physical-writer invariant and definite
  semantic-conflict block. Config cannot disable locked invariants; exceptional
  repair uses bounded explicit break-glass.
- 2026-07-20: Apply an explicit review stopping rule: each remaining PR gets
  exactly one focused independent review plus required checks and the thread
  gate. Preference or optional improvements do not reopen review. A real defect
  receives one bounded affected-only repair and same-reviewer fingerprint
  recheck, then the PR is merged when its gates are green.
- 2026-07-20: Treat already-closed #676 as a completed dependency to reconcile,
  not as a tracker that must be reopened before activation.

## Session Notes

- Plan/integration worktree: managed runtime-kit worktree slug
  `agent-hook-control-plane`; provider-visible records omit its machine-local
  absolute path.
- This session is the dispatch orchestrator. It does not implement lane code,
  review its own work, or merge before an independent approval.
- Provider evidence must use repository-relative paths, issue/PR links, generic
  runtime roles, versions, digests, and redacted result summaries. Raw session
  IDs, mailbox bodies, capabilities, host aliases, users, and machine-local
  paths stay private.

## Handoff

1. Deliver the plan branch to `main` through one integration PR and exactly one
   focused integration review; do not reopen completed lane reviews.
2. Reconcile already-closed #676, deploy only merged `main`, and run the full
   installed plus disposable-session acceptance matrix.
3. Finalize every ledger row, close/audit #686, archive the plan, and report the
   exact remaining hook inventory and governed disable/recovery paths.
