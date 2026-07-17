# Execution State: Add a governed direct-main delivery mode

## Execution State

- Source document: docs/plans/2026-07-16-direct-main-delivery-mode/direct-main-delivery-mode-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/638>
- Current sprint: Sprint 2
- Status: complete; tracking issue closed
- Branch: feat/direct-main-delivery-mode
- Last updated: 2026-07-17
- Current task: none; tracking issue closed
- Next task: none; tracking issue closed
- Branch/commit/PR: graysurf/agent-runtime-kit#645 merged (<https://github.com/graysurf/agent-runtime-kit/pull/645>)

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Open and initialize the L2 tracker | done | https://github.com/graysurf/agent-runtime-kit/issues/638 | Bundle authored, validated, and initialized |
| 1.2 | Capture meaningful red for nils-cli | done | test-first v2 record: meaningful Clap rejection captured before production edits | Red evidence and affected-test decisions complete |
| 1.3 | Implement governed push primitive | done | focused 30/30; final package 639 unit + 337 integration; workspace 6,248/6,248; signed head `d3419acf` | Actual push URL is uniquely bound; exact-base CAS and bounded subprocess execution are covered |
| 1.4 | Deliver and review nils-cli change | done | https://github.com/sympoies/nils-cli/pull/1251; merged `374365a2` after 16/16 threads resolved and all provider gates passed | Independent testing, maintainability, security, API, performance, red-team, and delivery reviews converged |
| 2.1 | Capture meaningful red for runtime-kit hooks | done | test-first v2: lease misclassification and missing default-delivery hook reds captured | Acceptance tests added before hook production edits |
| 2.2 | Align policy and hook implementation | done | six focused tests pass; full hook suite 224/224 | Policy matrix, hook implementation, wiring, and rendered prompts updated; ambiguous no-refspec pushes fail closed |
| 2.3 | Release and pin coupled CLI surface | done | https://github.com/sympoies/nils-cli/releases/tag/v1.22.9; release request run 29499572511; broker run 29499586605; https://github.com/sympoies/nils-cli/releases/tag/v1.22.10; https://github.com/sympoies/nils-cli/releases/tag/v1.22.11; https://github.com/sympoies/nils-cli/releases/tag/v1.22.12; release request run 29576792817; broker run 29576803921 | v1.22.12 is the final consumer pin, adding trusted-head review submission, immutable-body pending-review recovery, and reviewed-head merge CAS without activating runtime homes |
| 2.4 | Full validation, PR review, merge, and closeout | done | https://github.com/graysurf/agent-runtime-kit/pull/640; merged d7f12c78814dc80684768b1a7a07f6348e1d3873 | All checks passed, 19/19 threads resolved, six specialist lenses passed, and dobi-bot native approval was recorded before squash merge |
| 2.5 | Prove deploy readiness without activating runtime | done | version baseline 24/24; version-alignment doctor 17/17; sync-runtime-surfaces --no-pull dry-run passed | Merged direct-main source plus the proposed v1.22.12 pin is deploy-ready; live runtime activation remains explicitly deferred |

## Validation Log

- 2026-07-16: Maintainer selected L2 and authorized execution through deploy readiness, with live runtime update explicitly deferred to a later approval.
- 2026-07-16: Current-state audit confirmed runtime-kit policy says PR floor while mechanical enforcement does not block every default-branch commit/push path; provider main requires signed commits but not PRs.
- 2026-07-16: Security review found that a configured Git `pushurl` could differ from the fetch URL; the CLI now requires one actual push destination and binds it to the provider repository.
- 2026-07-16: Hook review found that an implicit feature-branch push can be retargeted by Git configuration; live pushes without an explicit refspec now fail closed.
- 2026-07-16: Diff audit found Git's lone `:` / `+:` matching-branch refspecs could include the default branch; a meaningful red was captured and the hook now blocks both forms.
- 2026-07-16: Semantic-commit surface audit found `fixup` and `squash` were missing from both default-branch and checkout-writer classification; red coverage was captured and all three writer subcommands now share the guard.
- 2026-07-16: `semantic-commit --dry-run` remains read-only only when it has no `--message-out`; the file-writing combination now requires checkout writer admission and has focused red/green evidence.
- 2026-07-16: After installing the new hook with executable mode, the expanded hook suite passed all 224 cases.
- 2026-07-16: Final nils-cli validation passed 13/13 focused integration tests, all 637 unit and 317 integration tests, and the 6226-test local-fast workspace gate on the destination-pinned implementation.
- 2026-07-16: The signed nils-cli change committed as `99e87b3`; the repository pre-PR gate repeated the complete 6226-test local-fast validation and PR #1251 was opened through the governed delivery macro.
- 2026-07-16: Specialist review replaced a precheck-only normal push with a verified fast-forward plus an internal exact-old-object lease, closing the check/use race without exposing a caller-controlled force surface. The same repair bounded Git subprocess time and output and aligned repository/provider error contracts; focused 30/30 and all-feature package tests (637 unit + 334 integration) pass at signed head `9688200a`.
- 2026-07-16: Upstream runtime-kit advanced with the checkout-lease race fix in #639; the delivery branch must rebase and retain that independent fix before its final gates.
- 2026-07-16: The runtime-kit branch was rebased onto `origin/main` with #639 retained; the complete 224-case hook suite remained green.
- 2026-07-16: nils-cli PR #1251 merged as `374365a2` after 16/16 review threads resolved and all local/provider gates passed; final local validation covered 6,248 workspace tests plus 639 unit and 337 forge-cli integration tests.
- 2026-07-16: The two-stage release workflow published `v1.22.9`; broker run 29499586605 verified the release, Homebrew tap, sympoies host, and macOS peer converged. The installed host now reports 1.22.9.
- 2026-07-16: Runtime-kit pin metadata, Linux artifact digests, baseline mirrors, and the global `forge-cli` floor were advanced to `v1.22.9`; `agent-session` remains unconsumed and existing PR/L2/L3 skill floors remain at their narrower `>= 1.21.34` contract.
- 2026-07-17: nils-cli `v1.22.10` published the guarded pending-review recovery needed after a native GitHub review became stuck; the exact-node delete restored dobi-bot approval for runtime-kit PR #640.
- 2026-07-17: Runtime-kit PR #640 merged as `d7f12c78814dc80684768b1a7a07f6348e1d3873` after all provider checks, 19/19 review threads, six specialist lenses, and the independent native approval converged.
- 2026-07-17: The consumer pin, Linux artifact digests, baseline mirrors, and the three merge-owning workflow floors advanced to `v1.22.10`; focused PR runtime smoke passed 6/6.
- 2026-07-17: nils-cli PR #1266 and release `v1.22.11` bound native review submission to an expected provider head and returned a typed viewer-draft conflict for guarded recovery.
- 2026-07-17: nils-cli PR #1269 and release `v1.22.12` added expected-head merge CAS plus exact-head, exact-commit, immutable-body pending-review deletion; release request run 29576792817 and broker run 29576803921 completed successfully.
- 2026-07-17: Runtime-kit PR #645 merged as `1914f25be20d597af43d69bf5658d37ea99bbbee` with the final `v1.22.12` pin, Linux artifact digests, reviewed-head merge binding, immutable review-body retry, refreshed rendered surfaces, and corresponding runtime-smoke contract coverage.
- 2026-07-17: Deploy-readiness checks passed with version baseline 24/24, version-alignment doctor 17/17, and a three-product `scripts/sync-runtime-surfaces.sh --no-pull` dry-run. No live runtime apply was executed.

## Session Notes

- 2026-07-16: Runtime-kit primary checkout is owned by another session lease, so this plan uses a managed worktree created from current `origin/main`.
- 2026-07-16: The maintainer removed the unrelated unowned heuristic source from the primary checkout after its exact contents were preserved under `$HOME/.local/state/agent-runtime-kit/out/quarantine/20260716-gitlab-reviewer-bot-profile-mapping-gap/ENTRY.md`; the delivery work is no longer blocked.
- 2026-07-16: No live runtime sync/apply command is authorized by this plan; only dry-run or isolated verification is allowed at Task 2.5.

## Handoff

- Tracking issue <https://github.com/graysurf/agent-runtime-kit/issues/638> is closed. After this sync lands, no plan closeout or product action remains.
