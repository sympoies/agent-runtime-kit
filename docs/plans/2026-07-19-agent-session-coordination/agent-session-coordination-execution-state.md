# Execution State: Add metadata-first agent session coordination

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-plan.md`
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/676>
- Current sprint: Sprint 1 establish the durable tracker and test-first contract
- Status: in progress; plan PR delivery
- Current gate: pass exact-head provider checks, post the L2 lifecycle checkpoint,
  and merge the plan PR without closing the tracker
- Current task: Task 1.1 commit the plan bundle and initialize the L2 tracker
- Next task: Task 1.2 freeze the nils-cli coordination specification and
  meaningful red
- Planned implementation branches: `feat/agent-session-coordination` in
  nils-cli, `feat/agent-session-coordination-policy` in runtime-kit, and
  `feat/agent-session-coordination-skill` in local-scripts
- Plan-authoring branch: `docs/agent-session-coordination-plan`
- Release prerequisite: pending Task 2.5 and later explicit authorization
- Installed-surface activation: not authorized by plan approval; requires a fresh
  runtime sync/private-skill sync decision after the corresponding merges
- Blockers: none
- Last updated: 2026-07-19
- Branch/commit/PR: initial bundle commit
  `069f2206363b136d8638590f5a1d11209e0d977a`, tracker-link commit
  `42b9b1c21bd4182e0c1e70ce52cb81b62627d3e2`, and draft plan PR
  <https://github.com/graysurf/agent-runtime-kit/pull/677>; tracking issue #676
  remains open

## Validation Plan

- Plan-authoring floor: bundle validation, `git diff --check`, full runtime-kit
  CI, hook tests, independent review, provider checks, and merged read-back.
- Nils-cli floor: meaningful red, focused coordination/CLI/server/concurrency/
  privacy tests, affected clippy, documentation/completion audits, and
  `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`.
- Runtime-kit floor: meaningful red, focused hook/routing tests, agent-docs intent
  read-back, product render/golden/sandbox/runtime-smoke, full CI, and hook tests
  on the exact released nils-cli pin.
- Local-scripts floor: focused private-skill portfolio test and
  `./_tools/check.zsh` on the exact delivery head.
- Delivery floor: verified test-first/docs-impact evidence where applicable,
  exact-head provider checks, independent specialist reviews, zero unresolved
  actionable threads, and merged-revision read-back.
- Activation floor: fresh approval, exact installed-version/surface read-back,
  bounded disposable sessions with synthetic content, privacy scan, and terminal
  cleanup. Deterministic isolated acceptance runs before this gate.

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | in-progress | Commit the plan bundle and initialize the L2 tracker | Issue #676; run `20260719T102214Z-issue-676`; draft PR #677; full pinned pre-PR, provider checks, four specialist lenses, and thread convergence passed; lifecycle checkpoint and merge pending | Tracker must remain open after plan PR merge |
| 1.2 | pending | Freeze the nils-cli coordination specification and meaningful red | pending | Start only after issue/run-state reconciliation |
| 2.1 | pending | Implement structured work context and atomic claims | pending | Nils-cli production edit starts after meaningful red |
| 2.2 | pending | Add privacy-safe CLI and server projections | pending | Additive compatibility required |
| 2.3 | pending | Implement the private mailbox lifecycle | pending | Bodies stay in private recipient-read surface only |
| 2.4 | pending | Add fixed idle notifications without prompt forwarding | pending | Queue-only fallback; no raw terminal input |
| 2.5 | pending | Review, merge, release, and verify nils-cli | pending | Release requires fresh exact-version consent |
| 3.1 | pending | Add the session-coordination intent, policy, and meaningful red | pending | Runtime-kit consumes the released mechanism |
| 3.2 | pending | Implement managed-session admission and render all products | pending | Only definite conflict hard-blocks in v1 |
| 3.3 | pending | Apply the exact pin, review, merge, and authorize activation | pending | Installed-surface sync remains separately gated |
| 4.1 | pending | Extend private-agent-session with coordination and recovery | pending | Preserve mobile handoff behavior |
| 4.2 | pending | Review, merge, and optionally synchronize private skills | pending | Overlay apply requires fresh approval |
| 5.1 | pending | Run deterministic multi-session acceptance | pending | Isolated and synthetic; no live mutation |
| 5.2 | pending | Run approval-gated live disposable-session acceptance | pending | Explicit approval or named residual required |
| 5.3 | pending | Audit evidence, close the tracker, and archive the plan | pending | Close only when all required work is terminal |

## Validation Log

- 2026-07-19: Maintainer approved the assessed design and explicitly selected a
  complete L2 plan committed to Git. This authorizes plan/tracker/provider
  delivery, not later release or live runtime activation.
- 2026-07-19: `plan-archive search` found no prior plan for session coordination,
  mailbox, or input lease. The only broader agent-session result was not a
  duplicate and had a stale-enough fetched timestamp to require live issue
  confirmation.
- 2026-07-19: Live open-issue searches in runtime-kit, nils-cli, and
  local-scripts found no matching coordination plan or implementation issue.
- 2026-07-19: Privacy-minimized session metadata inspection found no known work
  overlap with this plan-authoring scope. This is evidence of no known conflict,
  not proof of a complete semantic view because current sessions do not yet
  publish structured work context.
- 2026-07-19: The runtime-kit primary checkout was behind its remote base and had
  unrelated untracked bytecode owned by another workflow. It was not modified;
  a clean managed worktree based on `origin/main` was created for this plan.
- 2026-07-19: Required runtime-kit project-dev/task-tools documentation and the
  L2 tracking/source-document skills were read before writing. The edit intent is
  active for the managed worktree.
- 2026-07-19: `plan-tooling validate` accepted the three-file bundle with 15
  tasks and zero errors; `git diff --check` passed before the signed initial
  bundle commit `069f220`.
- 2026-07-19: L2 issue
  <https://github.com/graysurf/agent-runtime-kit/issues/676> was opened from the
  committed bundle. Private run `20260719T102214Z-issue-676` selected Task 1.1;
  strict visible status recognized source, plan, and state with no visibility
  findings. Missing session/validation/review roles are expected until the plan
  PR delivery checkpoints are posted.
- 2026-07-19: Draft plan PR
  <https://github.com/graysurf/agent-runtime-kit/pull/677> was delivered at
  `42b9b1c`. The repository-pinned nils-cli 1.24.0 wrapper passed pre-PR
  positions 1–17, direct hook validation passed 273 tests, and the four provider
  checks passed on that head. The ambient host CLI was 1.24.2, so the unpinned
  version mismatch is recorded as environment drift rather than a product
  failure.
- 2026-07-19: Independent testing, maintainability, security, and mandatory
  red-team reviews were posted to PR #677 and mirrored to issue #676 before
  repair. Findings require explicit session authorization, deterministic scope
  semantics, operation leases and mutation coverage, bound idempotency,
  realizable notification attempts, resource limits, untrusted peer-data rules,
  keyed checkout fingerprints, source-bound intent validation, legacy-list
  compatibility, and a local-scripts pre-edit evidence gate. The plan contract is
  being expanded on the same PR; threads remain open until exact-head follow-up.
- 2026-07-19: Review-repair commit `d21dc09` passed the repository-pinned
  pre-PR positions 1–17, including runtime smoke 102 pass/1 host-capability skip,
  shared hooks 273/273, version baseline 24/24, and all product/privacy/budget
  audits. Security follow-up passed. Testing and maintainability follow-up found
  three command/architecture gaps: evidence commands needed explicit output/root
  binding, heartbeat needed a persistent launch component, and public check
  needed one-to-one selectors. Follow-up then required exact current entrypoints,
  held-runtime identity-before-readiness sequencing, missed-PostTool
  reconciliation, selector-specific subject exclusion, and executable docs-impact
  commands. The current repair covers start/run/resume/HTTP/delete, concrete
  broker status/adopt/reconcile surfaces, execution-token completion proof, and
  task-scoped test/docs evidence directories. Final testing, maintainability,
  security, and red-team follow-up passed; full pinned pre-PR and provider checks
  passed; all 24 actionable threads were resolved. A later tracker-render check
  caught canonical ledger-status and current-state wording inconsistencies; both
  are repaired. Exact-head checks, lifecycle checkpoint, and merge remain the
  current gate.

## Decision Log

- 2026-07-19: Selected runtime-kit as the L2 owner because it owns the durable
  cross-product coordination policy and exact nils-cli consumption workflow.
- 2026-07-19: Selected a serial L2 rather than L3: three repositories are
  involved, but public contract/release/pin dependencies prevent independent
  implementation lanes. Specialist review may still run independently.
- 2026-07-19: Selected metadata-first inspection, explicit mailbox clarification,
  and fixed content-free notification. Automatic log/glance/transcript access and
  arbitrary prompt forwarding are excluded.
- 2026-07-19: Selected definite-conflict-only blocking for v1. Potential,
  unknown, and no-known-conflict states remain visible advisories until evidence
  justifies stricter admission.
- 2026-07-19: Kept formal multi-agent implementation under L3/provider dispatch;
  the mailbox is ephemeral coordination only.

## Session Notes

- Worktree:
  `agent-runtime-kit-228a9c3a/agent-session-coordination-plan` under the managed
  runtime-kit worktree root. The machine-local absolute prefix is intentionally
  omitted from provider-visible records.
- Current branch is documentation-only and must not be reused as an
  implementation branch.
- No nils-cli, runtime-kit production surface, local-scripts skill, installed
  agent home, live session, release, or deployment has been modified during plan
  authoring.
- Use repository-relative paths and privacy-safe evidence summaries in issue/PR
  updates. Keep session IDs, incarnations, mailbox bodies, host/user names, and
  local state paths private.

## Handoff

1. Read the discussion source, plan, and this ledger completely.
2. Run `plan-issue tracking status --expect-visible --format json` and reconcile
   the selected task against this ledger before doing implementation work.
3. If Task 1.1 is complete, create a managed nils-cli worktree for
   `feat/agent-session-coordination` and start Task 1.2, not production code.
4. Initialize nils-cli test-first evidence, declare affected tests, capture
   meaningful red, and pass the pre-edit gate before Task 2.1.
5. Preserve serial repository ordering and the separate release/runtime
   activation consent boundaries.
