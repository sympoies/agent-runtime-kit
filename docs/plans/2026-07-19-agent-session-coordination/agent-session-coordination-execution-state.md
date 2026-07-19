# Execution State: Add metadata-first agent session coordination

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-plan.md`
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/676>
- Current sprint: Sprint 3 integrate the runtime-kit intent and admission policy
- Status: in progress; nils-cli v1.24.5 released and deployed from the approved
  source, runtime-kit intent and managed admission implemented and validated
- Current gate: Task 3.3 exact-head review, provider checks, and merge
- Current task: Task 3.3 apply the exact pin, review, merge, and preserve the
  separate activation gate
- Next task: commit the runtime-kit delivery head, complete specialist review,
  deliver and merge the PR, then begin Task 4.1 in local-scripts
- Planned implementation branches: `feat/agent-session-coordination-signed-final` in
  nils-cli, `feat/agent-session-coordination-policy` in runtime-kit, and
  `feat/agent-session-coordination-skill` in local-scripts
- Plan-authoring branch: `docs/agent-session-coordination-plan`
- Release prerequisite: satisfied; v1.24.5 was released from approved source
  `b8cedc78` and deployed successfully
- Installed-surface activation: not authorized by plan approval; requires a fresh
  runtime sync/private-skill sync decision after the corresponding merges
- Blockers: none
- Last updated: 2026-07-20
- Branch/commit/PR: plan PR #677 merged as `75c7402`; nils-cli signed
  replacement branch `feat/agent-session-coordination-signed-final`, exact
  signed head `a49d8412`, merged PR
  <https://github.com/sympoies/nils-cli/pull/1308>, and verified merge
  `b8cedc78`; superseded PR #1302 is closed; v1.24.5 release commit
  `dd1b6980` has approved source `b8cedc78` as its sole parent; tracking issue
  #676 remains open

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
| 1.1 | done | Commit the plan bundle and initialize the L2 tracker | Issue #676; plan PR #677 merged as `75c7402`; strict tracking status visible and reconciled | Tracker remains open; Task 1.2 selected |
| 1.2 | done | Freeze the nils-cli coordination specification and meaningful red | Frozen v1 spec and test-first evidence captured meaningful red before production edits | Spec and meaningful red complete |
| 2.1 | done | Implement structured work context and atomic claims | Structured context, atomic claims, scope/conflict truth table, authenticated broker, operation admission, HMAC fingerprinting, and race coverage implemented | Exactly one definite concurrent claimant wins |
| 2.2 | done | Add privacy-safe CLI and server projections | Privacy-safe additive CLI/HTTP/list/glance projections, capability/incarnation fencing, and route tests implemented | Existing clients remain compatible |
| 2.3 | done | Implement the private mailbox lifecycle | Bounded private mailbox, CAS/idempotency, pagination/rate/quota/expiry, recipient-only body reads, and privacy tests implemented | Message bodies remain private |
| 2.4 | done | Add fixed idle notifications without prompt forwarding | Fixed body-free idle notification with durable attempt and queue-only fallback implemented and tested | No raw terminal input or body forwarding |
| 2.5 | done | Review, merge, release, and verify nils-cli | Signed replacement PR #1308 exact head `a49d8412` merged as verified `b8cedc78`; v1.24.5 released by successful broker run 29700703602 as signed commit `dd1b6980` whose sole parent is the approved source; four platform archives and four checksum sidecars published; the fixed fleet reports agent-session and all required CLIs at 1.24.5; follow-ups nils-cli #1305 and #1309 own the non-blocking residuals | Exact-version consent and source-SHA binding satisfied |
| 3.1 | done | Add the session-coordination intent, policy, and meaningful red | Source-bound `session-coordination` intent and privacy-first policy added; test-first evidence records missing JSON recovery and absent admission guard as meaningful red | Runtime-kit consumes the released mechanism |
| 3.2 | done | Implement managed-session admission and render all products | Managed Codex/Claude Pre/Post/Failure/Stop admission guard implemented with claim coverage, exact target binding, serialized durable admit/outcome replay, fail-closed retry, fixed privacy-safe output, and deterministic routing/render coverage; hooks passed 306/306 | Only definite conflict hard-blocks in v1 |
| 3.3 | in-progress | Apply the exact pin, review, merge, and authorize activation | Exact released pin v1.24.5 and Linux archive checksums applied; host version baseline passed 24/24; first exact-head review P1s for Claude parallel hooks, admission races/replay, early Post capture, target binding, read-only trust, and host timeout were repaired; second review/provider delivery pending | Installed-surface sync remains separately gated |
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
- 2026-07-19: Nils-cli Tasks 1.2 through 2.4 reached signed head `4d837b36`.
  Test-first remediation closed all P0/P1 findings; the required exact-head
  local-fast gate passed 6968/6968 workspace tests plus docs, fmt, clippy, and
  doctests. Completion parity passed 47/47 required CLIs. Exact-head testing
  and maintainability reviews approved; the prior security and concurrency
  approvals remain applicable because the final delta only adds clap help and
  regenerated completions. The non-blocking aggregate receipt-byte quota is
  tracked by nils-cli #1305. Provider macOS CI then found a platform-only
  needless-return Clippy blocker; the expression-form repair preserves the same
  fail-closed error, and exact-head local-fast plus scoped testing and
  maintainability reviews passed again. All provider checks then passed, but
  GitHub's required-signatures ruleset rejected three early unsigned commits in
  PR #1302. Without force-push, admin bypass, or direct-main delivery, signed
  replacement PR #1308 was created as one signed commit whose tree exactly
  matches the conflict-free #1302 merge result on latest main. Exact-head
  local-fast passed 6970/6970 workspace tests and all four scoped reviews
  approved. All provider checks passed. Two non-blocking notification
  critical-section efficiency observations are tracked by nils-cli #1309 and
  their review threads are resolved. PR #1308 merged as verified commit
  `b8cedc78`; superseded PR #1302 was closed with a replacement explanation.
  Release remains gated on fresh exact-version authorization.
- 2026-07-20: The maintainer approved release-and-deploy of v1.24.5 from exact
  source `b8cedc78e64a7e1b2618ba94dc10458be3f1a026`. Request workflow
  29700696279 dispatched broker workflow 29700703602, which completed
  successfully. Release commit `dd1b6980fce874cb186c481bccffbf0fa41bee66`
  is verified signed and has the approved source as its sole parent; the release
  is non-draft/non-prerelease with four platform archives and four SHA256
  sidecars. The fixed fleet and current host report agent-session and the
  required nils-cli surfaces at 1.24.5. Non-blocking Homebrew trust annotations
  did not fail the workflow. Task 2.5 is complete and Task 3.1 is selected.
- 2026-07-20: Runtime-kit meaningful red captured two pre-production contract
  failures: generated `agent-docs session prepare` recovery omitted JSON output,
  and the managed-session admission guard did not exist. Production repair adds
  the source-bound intent and policy, exact-claim mutation admission for Codex
  and Claude, durable fail-closed operation/outcome proofs, PostTool success and
  failure completion, and Stop retry without guessing missing outcomes. Focused
  tests cover claim absence, definite conflict, uncovered scope, stale context,
  invalid leases, privacy redaction, older/unmanaged fallback, hook ordering,
  and durable completion recovery. The shared hook suite passed 306/306 against
  released nils-cli v1.24.5; version baseline audit passed 24/24 and rendered
  product/golden surfaces were refreshed. Task 3.1 and Task 3.2 are complete;
  Task 3.3 exact-head review and PR delivery are selected.
- 2026-07-20: Three specialist reviews of signed `faa39514` found no P0 and
  identified blocking P1s in Claude's parallel hook scheduling, same-call
  admission races, ambiguous-response replay, Post outcome capture, provider
  and cross-repository target binding, read-only executable trust, and Codex's
  host timeout. The repair serializes Claude mutation gates, persists replay
  material before admission, records Post outcomes before probes, retires
  records atomically, resolves explicit provider overrides/URLs, rejects
  unproven cross-repository targets, tightens read-only bypasses, and raises the
  Codex bound to 45 seconds. Focused contracts and the 306-test hook suite pass;
  an exact-head second review remains required before provider delivery.
- 2026-07-20: Exact-head second review of signed `627adeb5` found no P0 and
  confirmed the first-round concurrency/replay repairs, then identified two
  remaining P1 classes: compound or wrapped commands could still receive the
  current checkout scope without proving their destinations, and the hook's
  subprocess work could exceed the host timeout. Review also found two P2
  terminal-state/error-code mismatches against released nils-cli v1.24.5 and a
  Git read-only bypass that could invoke configured external programs. The
  current repair rejects opaque compound and wrapped provider targets, removes
  external-driver-capable Git bypasses, applies one 50-second subprocess budget
  under 60-second host bounds, covers Claude's declared sequential worst case,
  accepts outcome-consistent `completed`/`failed` leases, and retires the
  released `claim-revision-conflict` response. All five focused regression
  methods and the complete 306-test shared-hook suite pass on released v1.24.5;
  full exact-tree validation and a third exact-head review remain before
  provider delivery.
- 2026-07-20: Third exact-head concurrency and contract reviews approved signed
  `71f3c44e`; security found no P0 but reproduced two final P1 bypasses: quoted
  nested-shell destinations were not re-parsed, and Git status/pager forms could
  invoke configured executables while classified read-only. Regression tests
  failed three assertions before repair. The current repair recursively unwraps
  bounded shell `-c` scripts for compound/cross-repository detection, removes
  status/blame and forced-pagination bypasses, and keeps safe simple nested
  commands target-bound. Focused regressions pass; exact-tree validation and
  security closure remain required.

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
- This ledger change is carried on the planned runtime-kit policy branch; no
  runtime-kit production edit begins before the released nils-cli dependency is
  available.
- Nils-cli mechanism changes are delivered through replacement PR #1308 and
  release v1.24.5. Runtime-kit production surfaces, the local-scripts skill,
  installed agent homes, and live sessions remain unchanged pending their
  separate tasks and consent gates.
- Use repository-relative paths and privacy-safe evidence summaries in issue/PR
  updates. Keep session IDs, incarnations, mailbox bodies, host/user names, and
  local state paths private.

## Handoff

1. Read the discussion source, plan, and this ledger completely.
2. Run `plan-issue tracking status --expect-visible --format json` and reconcile
   the selected task against this ledger before doing implementation work.
3. Continue Task 3.1 in this runtime-kit implementation worktree; preserve the
   separate installed-surface and live-session activation gates.
4. Consume exact released nils-cli v1.24.5 in the Sprint 3 PR; do not use a
   locally rebuilt or floating CLI for final validation.
5. Keep provider-visible records privacy-minimized and close the tracker only
   after Tasks 3.1 through 5.3 are terminal.
