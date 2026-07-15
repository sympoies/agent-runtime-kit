# Execution State: Replace the macOS automation engine with pinned Peekaboo

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-07-15-peekaboo-macos-agent-migration/peekaboo-macos-agent-migration-plan.md`
- Tracking issue: not opened; use the L2 `dispatch:deliver-plan-tracking-issue` workflow when execution is authorized
- Current sprint: Sprint 1
- Status: ready to start; implementation and release have not begun
- Current gate: open the L2 tracker, create a managed nils-cli worktree, then run Task 1.1
- Current task: none
- Next task: Task 1.1 — review and freeze the Peekaboo candidate
- Plan branches: `feat/peekaboo-macos-agent-adapter` (nils-cli), then `feat/peekaboo-macos-agent-cutover` (runtime-kit)
- Upstream candidate: Peekaboo `v3.9.3`, verified tag commit `3cfd612adbcb1b43e8431a7a1f3b02ec45d01269`; freshness recheck required by Task 1.1
- Release prerequisite: later explicit release consent through `project-release-nils-cli`
- Blockers: none
- Last updated: 2026-07-15
- Branch/commit/PR: none

## Validation Plan

- Per task: update this ledger with command/evidence paths, pass/fail/waiver,
  provider links, and residual gaps before advancing.
- Nils-cli deterministic floor: focused crate tests, completion/docs audits, and
  `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`.
- Nils-cli live floor: locked provenance; strict doctor; local/SSH capability
  matrix; journal/redaction/replay/MCP; stability and rollback.
- Runtime-kit floor: focused computer-use smoke, render/golden/install/prune,
  `bash scripts/ci/all.sh`, and `bash tests/hooks/run.sh` on the released pin.
- Delivery floor: verified test-first/docs-impact evidence, provider checks,
  specialist reviews, zero unresolved review threads/tasks, and merged PRs.
- Activation floor: merged-revision read-back, fresh product sessions, private
  privacy-minimized journals, significant-defect review, and rollback dry-run.

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | pending | Review and freeze the Peekaboo candidate | — | Recheck latest/security; candidate changes require full review |
| 1.2 | pending | Declare test impacts and capture meaningful red | — | Separate v2 test-first records for nils-cli and runtime-kit |
| 2.1 | pending | Implement backend install, verification, doctor, and rollback | — | User-scoped, exact lock, app runtime default |
| 2.2 | pending | Implement local/SSH exec, scenario transport, and artifacts | — | Versioned stdin remote request; no shell interpolation |
| 2.3 | pending | Implement journal, redaction, guarded replay, and review | — | Always-on structural evidence; significant defects are blocking |
| 2.4 | pending | Implement stdio MCP/tool profiles and retire the old engine | — | No released legacy fallback |
| 3.1 | pending | Run deterministic, security, and release-readiness validation | — | Full focused/affected/workspace and fault-injection gates |
| 3.2 | pending | Run the private macOS capability and journal canary | — | Local + SSH; synthetic/read-only data; rollback rehearsal |
| 3.3 | pending | Review, merge, release, and verify nils-cli | — | Release dispatch pauses for later explicit consent |
| 4.1 | pending | Replace the computer-use skill and publish the capability matrix | — | Remove Python helper; released CLI is sole mechanics owner |
| 4.2 | pending | Apply the governed nils-cli pin and deliver the cutover PR | — | One skill/pin/generated-surface PR via `meta:nils-cli-bump` |
| 5.1 | pending | Synchronize the runtime and run fresh-agent acceptance | — | Only merged/pinned source; no disabled tools or stale helper |
| 5.2 | pending | Review retained evidence and close the L2 tracker | — | Route every significant defect; raw desktop evidence stays local |

## Validation Log

- 2026-07-15: `plan-tooling validate` accepted the three-file bundle with 13
  tasks and no errors; `git diff --check` passed.
- 2026-07-15: On pinned nils-cli `v1.21.39`, `scripts/ci/all.sh` positions 1-7
  passed: plan/governance, version alignment, all product renders, support
  matrix, goldens, drift fixtures, and security hardening. Position 8 reached
  convergence acceptance and stopped only because that harness requires a
  committed clean source, while this plan-only authoring turn intentionally
  leaves the new bundle uncommitted. No clean-tree bypass or temporary commit
  was used.
- 2026-07-15: The remaining independently runnable on-pin gates passed:
  skill-surface doctor 21/21, sandbox install, deterministic runtime smoke
  99 pass / 1 declared host-capability skip / 0 fail, project-local smoke,
  hooks 178/178, version baseline 21/21, product leak audit, and memory-runtime
  policy/audit. The sole validation waiver is the clean-source convergence
  execution in position 8; it must run without waiver when the plan bundle is
  committed through the L2 delivery workflow.

## Session Notes

- 2026-07-15: Classified as L2 because one outcome spans an upstream binary
  lock, a nils-cli replacement/release, a runtime-kit skill/pin cutover, private
  deployment, and retained acceptance evidence.
- 2026-07-15: Locked architecture: Peekaboo owns native UI behavior;
  `macos-agent` owns supply chain, transport, journaling, replay, and rollback;
  the skill owns intent, approvals, postconditions, privacy, and defect routing.
- 2026-07-15: Peekaboo latest changed from `v3.9.2` to `v3.9.3` during plan
  research. The plan therefore treats `v3.9.3` as an immutable candidate and
  requires an explicit freshness review rather than resolving `latest` at run
  time.
- 2026-07-15: The maintainer added execution journaling as a core requirement.
  Release is blocked until structural records, redaction, guarded replay,
  significant-defect clustering, owner routing, and private retention are
  proven.
- 2026-07-15: Browser MCP, AI, shell, audio, and permission mutation are
  intentionally disabled in the first release. Authenticated browser acceptance
  is read-only and does not create a real credential.
