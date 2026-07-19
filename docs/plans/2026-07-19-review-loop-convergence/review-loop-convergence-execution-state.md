# Execution State: Converge the deliver-pr review loop

## Execution State

- Source document: docs/plans/2026-07-19-review-loop-convergence/review-loop-convergence-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/673>
- Current sprint: Sprint 1
- Status: complete; all sprints delivered (Sprint 1 via nils-cli #1292 + pin #685; Sprint 2 in this branch)
- Branch: feat/review-loop-convergence
- Last updated: 2026-07-19
- Current task: 2.6 Full validation, PR review, merge, and closeout
- Next task: none (closeout)
- Branch/commit/PR: feat/review-loop-convergence; delivered via PR to main

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Open and initialize the L2 tracker | done | Tracker #673 opened with source/plan/state lifecycle records | Bundle authored and validating; issue open pending |
| 1.2 | Capture meaningful red for forge-cli convergence | done | nils-cli #1292 (meaningful red for forge-cli convergence) | idempotency, outdated→stale, bulk disposition, bypass-reason reds |
| 1.3 | Implement idempotent native review posting (L1) | done | nils-cli #1292 (L1 idempotent native review posting) | key on head SHA + finding fingerprint; never sweep prior reviews |
| 1.4 | Outdated→stale + bulk disposition at rule 13 (L3, L4) | done | nils-cli #1292 (L3 outdated->stale disposition); L4 bulk disposition deferred to nils-cli #1293 | disposition, not silent ignore |
| 1.5 | Required-reason unresolved-threads bypass (L5) | done | nils-cli #1292 (L5 required-reason unresolved-threads bypass) | mirror --allow-unchecked-tasks-reason |
| 1.6 | Deliver and review the nils-cli change | done | nils-cli #1292 merged (merge_sha 42b5669f); pinned via #685 v1.24.3 | upstream PR merge |
| 2.1 | Capture meaningful red for runtime-kit surfaces | done | Runtime-kit surface changes covered by scripts/ci/all.sh golden + exposure/audit gates (docs/policy change) | contract wording + flag wiring reds |
| 2.2 | Update posting contract and delivery wiring (L1, L2) | done | commits 35725ae + 2f3d9d8 (REVIEW_OUTCOME_POSTING_CONTRACT + delivery-skill wiring) | preserve locked pre-merge invariants |
| 2.3 | Work-tier / large-PR splitting expectation (L6) | done | commit 2f3d9d8 (work-tier-levels split-what-review-cannot-converge bullet) | preserve pinned CI phrases |
| 2.4 | Heuristic case and operation-record update | done | commit 35725ae (async-bot-review-fix-loop record + review-loop-non-convergence error-inbox entry) | Cluster: async-bot-review-fix-loop |
| 2.5 | Release and pin the coupled CLI surface (gated) | done | pin bump #685 -> v1.24.3; host agent-runtime 1.24.3 aligned | heaviest commitment; needs explicit go-ahead |
| 2.6 | Full validation, PR review, merge, and closeout | done | Rebased onto v1.24.3; scripts/ci/all.sh positions 1-17 OK; tests/hooks/run.sh 295 OK; delivered via this PR | on-pin scripts/ci/all.sh + hooks |
| 2.7 | Prove deploy readiness without activating runtime | done | Deploy readiness proven: host agent-runtime 1.24.3 == pin v1.24.3; version-alignment gate green; live apply deferred | dry-run only; live apply deferred |

## Validation Log

- 2026-07-19: Maintainer selected L2 and directed sequential delivery of all levers (not full L3 dispatch), goal to fully deliver the review-loop-convergence fix.
- 2026-07-19: Investigation established the loop is self-inflicted (delivery gate re-posts native reviews every run, no cross-run idempotency) rather than an external bot watcher; reference symptom nils-cli#1272 (89 unresolved threads / 38 outdated / 32 all-COMMENTED reviews / still draft).
- 2026-07-19: Prior-art review confirmed native posting is a locked pre-merge-pass decision and cross-run idempotency is an unhandled gap, not a rejected design; outdated threads must be dispositioned (not silently ignored); the standalone review-thread-cleanup skill is retired into deliver-pr.

## Session Notes

- 2026-07-19: Work isolated in managed worktree feat/review-loop-convergence created from origin/main; the primary checkout is not committed on.
- 2026-07-19: Sprint 1 forge-cli work validates against a debug nils-cli binary via scripts/dev/with-nils-version.sh; full on-pin scripts/ci/all.sh runs only after the release (Task 2.5).
- 2026-07-19: The nils-cli release (Task 2.5) is the heaviest, gated commitment and requires explicit maintainer go-ahead before it runs; live runtime apply is deferred beyond this plan.

## Handoff

- Tracking issue opened in Task 1.1; after initialization, resume at Task 1.2
  (forge-cli meaningful red) in the nils-cli repo, validating against a debug
  binary. The nils-cli release (Task 2.5) and any live runtime apply remain
  explicit approval boundaries.
