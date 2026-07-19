# Execution State: Add governed dirty-checkout adoption

## Execution State

- Source document: docs/plans/2026-07-17-dirty-checkout-adoption/dirty-checkout-adoption-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/646>
- Current sprint: Sprint 2
- Status: ready-for-close
- Branch: feat/dirty-checkout-guard-final
- Last updated: 2026-07-19

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Open and initialize the L2 tracker | done | local plan bundle; https://github.com/graysurf/agent-runtime-kit/issues/646 | Bundle validated, committed, opened, initialized, and verified visible |
| 1.2 | Capture meaningful red for snapshot and adoption behavior | done | pending; L2 delivery request #646; v2 test-first baseline bound; focused nils integration compile red reaches the missing governed behavior API (exit 101) | Behavior red covers canonical snapshot sensitivity, explicit challenge binding, opaque receipts, and receipt-bound revocation before production edits |
| 1.3 | Implement canonical snapshot, adopt, and revoke commands | done | nils-cli implementation complete; v2 test-first evidence verified; 16 focused integration tests, full nils-git-cli suite, clippy, and required local-fast gate passed | Coupled nils-cli work |
| 1.4 | Deliver and review the nils-cli change | done | sympoies/nils-cli#1272 merged; v1.24.1 released with verified Linux assets and Homebrew/local convergence | Upstream dependency delivered without a second PR review, per maintainer direction |
| 2.1 | Capture meaningful red for runtime hook behavior | done | focused shared-hook red captured five expected failures while flag-off enforcement remained intact | Red demonstrates missing private advisory and overly broad malformed adopt/revoke admission before runtime production edits |
| 2.2 | Implement challenge issuance and lease integration | done | focused shared-hook adoption, lease-v2, and ref-only tests passed with the hardened nils-cli branch build; 294 shared-hook tests pass; major one-round review findings hardened at 6c06bc48; test-first evidence verifies clean | Exact session-bound transitions, trusted executables, native paths, u64 bounds, explicit no-sign, and reference-hook block are covered |
| 2.3 | Wire product parity and release/pin the CLI | done | nils-cli v1.24.1 pin and SHA-256 surfaces converge; Codex/Claude wiring and Hermes ceiling pass repository CI | No live runtime-home activation was performed |
| 2.4 | Full validation and PR review | done | Full CI positions 1-17 passed; PR #681 is provider-visible and green; one testing/maintainability/API/security review round completed; follow-ups #678, #679, and #680 track nonblocking residuals | Provider merge, tracker closeout, archive dry-run, and terminal cleanup remain governed L2 lifecycle duties after ledger completion |
| 2.5 | Prove deploy readiness without live activation | done | Isolated v1.24.1 install/convergence and Codex/Claude probe-only readiness checks passed | No live runtime-home activation or live `--apply` was performed; any later apply requires fresh approval |

## Validation Log

- 2026-07-17: Maintainer selected L2 planning for explicit agent takeover of an existing dirty checkout and did not authorize implementation.
- 2026-07-17: Duplicate search found no existing dirty-checkout adoption plan. GitHub issue #601 is related only to progressive intent-hook UX and will remain a related reference rather than the adoption tracker.
- 2026-07-17: Current-state inspection confirmed the lease guard blocks unowned dirty mutations, allows a sole managed-worktree add as remediation, refreshes same-session leases, rejects foreign live leases and Git operations, and performs non-destructive Stop audit.
- 2026-07-17: Design separates an off-by-default private advisory from unconditional mutation enforcement and binds takeover to a one-time same-session challenge, exact dirty snapshot, explicit post-warning user turn, bounded reason file, lease lock, and privacy-safe receipt.
- 2026-07-17: The durable snapshot/adopt/revoke command is assigned to nils-cli, while runtime-kit retains policy, hook payload/session challenge issuance, lease compatibility, product wiring, and acceptance-test ownership.
- 2026-07-17: `plan-tooling validate` passed for the new bundle and the complete shared hook suite passed. `bash scripts/ci/all.sh` reached the host version-alignment gate and failed because installed nils-cli 1.22.11 is ahead of the repository pin v1.22.9; this pre-existing environment drift is retained as an explicit validation gap for plan-only delivery.
- 2026-07-17: Tracking issue #646 was opened, run `20260717T113202Z-issue-646` was initialized, and `tracking status --expect-visible` confirmed source, plan, and state records are visible with no blocked transition.
- 2026-07-19: nils-cli PR #1272 merged without another review; v1.24.1 assets, Homebrew publication, and local convergence were verified before runtime-kit consumed the release pin and SHA-256 values.
- 2026-07-19: All 294 shared-hook tests and repository CI positions 1-17 passed with the verified isolated v1.24.1 toolchain. The delivery-bound v2 test-first record verifies complete with no missing fields.
- 2026-07-19: Exactly one testing, maintainability, API-contract, and security specialist round completed. Verified major findings were repaired at `6c06bc48`; nonblocking design and coverage residuals moved to #678, #679, and #680 without a second review round.
- 2026-07-19: Isolated install/convergence and Codex/Claude probe-only readiness checks passed. No live runtime-home activation or live `--apply` occurred.
- 2026-07-19: The task ledger now terminates at implementation, validation, review, and isolated-readiness proof. Expected-head merge, strict close-ready, provider audit, archive dry-run, and terminal cleanup remain mandatory governed L2 lifecycle duties and are not claimed complete by the ledger.

## Session Notes

- 2026-07-17: Plan artifacts were authored and committed in the managed worktree for branch `docs/dirty-checkout-adoption`, created from current `origin/main`.
- 2026-07-17: No implementation, release, runtime sync, or live-home apply was authorized in the planning phase.
- 2026-07-17: The current `/dispatch:deliver-plan-tracking-issue #646` request authorizes implementation, review, release/pin convergence, and delivery; live-home apply remains out of scope.
- 2026-07-19: Runtime meaningful-red coverage preceded production edits; focused tests now pass for private challenge issuance, exact adopt/revoke routing, strict lease-v2 admission and refresh, malformed/expired/foreign rejection, and the session-bound ref-only exception without lease creation.
- 2026-07-19: Maintainer constrained specialist review to one round. Major findings were repaired; remaining design or noncritical findings were routed to follow-up issues so no provider pending-review state blocks another session.
- 2026-07-19: Corrected the plan sequencing so terminal L2 merge/closeout/archive duties follow a terminal task ledger instead of being self-referential prerequisites inside the final task row.
