# Main Agent Local Delivery Follow-up Issue

Status: open, local-only  
Date: 2026-07-27  
Owner: Main Agent runtime maintainers  
Provider state: intentionally not opened on GitHub while provider delivery is unavailable

## Purpose

Retain non-blocking issues discovered during the `semantic-commit
default-branch` and resilient Main Agent local delivery. These items do not
block the current single-writer local deployment, but they should be addressed
before treating the exercised edge cases as fully optimized or concurrency
complete.

## Current Decision

- Complete the current local-only delivery and fresh-session E2E.
- Do not reopen the accepted nils candidate for these medium-severity items.
- Append any non-blocking E2E observations to this document.
- A hook bypass, authority escape, data loss, wrong-session mutation, or
  unrecoverable fresh-session failure remains blocking and is not downgraded to
  follow-up.

## Follow-ups

### FUP-01 — Bound readiness polling I/O

Priority: medium  
Area: `main-agent worker start`

Current behavior:

- The safer default waits up to five minutes for authenticated worker
  readiness.
- During that window the implementation polls the full orchestration registry
  every 250 ms and renews readiness state every five seconds.
- At the supported registry limit this can produce approximately 1,201 full
  reads and 65 full rewrites for one timeout.

Why it is deferred:

- It affects resource efficiency, not the authority or correctness result.
- Current local delivery uses bounded worker counts and observed healthy
  readiness.

Desired outcome:

- Readiness becomes event-driven or uses a compact per-assignment sidecar.
- If polling remains, it uses adaptive backoff.
- Lease renewal does not rewrite the full registry.

Acceptance:

- A five-minute non-checkpointing worker fixture against a near-limit registry
  proves bounded decode, read-byte, save, and write-byte counts.
- Concurrent worker starts remain bounded without weakening authenticated
  readiness.

### FUP-02 — Make `--expect-head` atomic with default-branch update

Priority: medium  
Area: `semantic-commit default-branch`

Current behavior:

- `--expect-head` is checked before ordinary `git commit`.
- A second writer can advance the checked-out default branch between that
  check and the ref update.
- The postcondition detects the unexpected parent, but only after the branch
  may already have been mutated.

Current-delivery mitigation:

- Use one enforced writer.
- Verify the clean primary worktree and exact expected HEAD immediately before
  the one authorized local-default bootstrap commit.
- Do not run another mutating operation against the same repository until the
  receipt and signed HEAD are verified.

Desired outcome:

- Create and sign the commit object without moving the branch.
- Atomically install it with `git update-ref <ref> <new> <expect-head>` or an
  equivalent compare-and-swap.
- Define recovery for failures after the CAS.

Acceptance:

- A deterministic barrier advances the branch from a second process after the
  expected-HEAD check.
- The command fails without installing its child commit and preserves the
  competing ref.

### FUP-03 — Add a first-class dependency-wait state

Priority: medium  
Area: Main Agent supervision and auto-resume

Current behavior:

- A worker that must wait for an accepted dependency SHA keeps a provider turn
  open and polls its authenticated mailbox from a background shell.
- The worker remains safe, but its provider activity can appear stale and
  supervision cannot distinguish an intentional dependency wait from missing
  evidence until a message arrives.

Desired outcome:

- Add a durable `dependency-waiting` or equivalent assignment checkpoint.
- Release unnecessary provider activity while preserving the exact worker,
  worktree, staged state, claim policy, and resume identity.
- An authenticated dependency message wakes the same session automatically.
- No prompt replay, manual Enter, logout, account switch, replacement worker,
  or shell polling loop is required.

Acceptance:

- A worker enters dependency wait, becomes quiescent, receives one accepted-SHA
  message, reacquires any required claim, and continues in the same session and
  incarnation.
- `worker supervise` reports the wait as healthy and actionable rather than
  `evidence_unavailable`.

### FUP-04 — Make candidate/released registry transitions explicit

Priority: low  
Area: Main Agent upgrade compatibility

Current behavior:

- During coupled development, a source-built candidate may write a newer
  orchestration registry that the still-installed released `main-agent` cannot
  decode.
- The compatible source-built facade can recover the run, but the ambient
  installed facade reports `unsupported orchestration registry schema` until
  deployment catches up.

Desired outcome:

- Document and test the supported coupled-development transition.
- Prefer an explicit compatibility projection or migration boundary over an
  opaque ambient-facade failure.

Acceptance:

- An upgrade fixture covers old released facade, candidate registry write,
  candidate facade recovery, final install, and post-install readback.
- The failure state identifies the required compatible executable without
  mutating or losing the durable run.

### FUP-05 — Repaired during the fresh-session E2E

Priority: resolved locally, unpushed
Area: `main-agent` supervision, `agent-hook` pre-claim allowlists, Main Agent
Mode skill

Three defects each independently prevented Main Agent Mode from completing, and
were repaired during the Phase C run. They are recorded here because the
commits are local-only.

1. **Pre-claim startup failure was unrecoverable.** `provider_terminated` is
   derived only from turn activity, so a provider that exits during startup
   records no turn and `failed_preclaim` stayed false. `claim_renewal_required`
   then outranked `pre_claim_failure`, `worker cancel` and `worker reassign`
   both refused, and the only remaining recovery was Agent Console
   `group-cleanup --force`, whose preview deletes the Main session itself.
   Repaired in nils-cli local main `7b3aba77`.
2. **Supervision reported a dead worker as healthy.** The classifier read
   `preclaim_blocker`/`terminal_recovery_reconciled` but never the computed
   pre-claim verdict, so it returned `healthy_progress` for a worker whose
   runtime was gone. Same commit.
3. **The pinned `main-agent bootstrap` was denied.** `worker start` writes the
   worker prompt with an absolute `main-agent` path, but both pre-claim
   allowlists compared argv against the bare name, so every managed worker had
   its mandated first command blocked for lacking the claim only `bootstrap`
   can create. Repaired in runtime-kit local main `0ca2819c`, together with a
   product-aware readiness gate so a Claude worker can pass the documented
   doctor check at all.

Acceptance already met locally:

- `worker supervise` returns `pre_claim_failure` with an executable
  `distinct_assignment_replacement` action for a worker whose runtime is gone.
- `worker reassign` recovers the lane without touching the run or Main session.
- A fresh Codex worker and a fresh Claude worker both reach
  `Assignment authenticated; worker bootstrap complete`.
- nils-cli `--local-fast` is green (887/887, clippy clean); the runtime-kit
  hooks suite shows no new failures against the pristine baseline.

Remaining: push and open the provider records when provider delivery is
authorized again.

### FUP-06 — Fresh-session E2E improvement log

Priority: medium
Area: cross-cutting

The full evidence, per-scenario verdicts, and rerun selectors live outside this
repository beside the run:

- `e2e-result-and-improvements.md` — Phase A/B, findings E2E-F01..F10
- `phase-c-result-and-improvements.md` — Phase C/D, findings E2E-F11..F26

The highest-value unresolved items:

- Validate an assignment packet's `repository` identifier inside `worker start`
  instead of failing at worker bootstrap after a full launch cycle (E2E-F24).
- Report a distinct `prompt-not-present` transport result instead of
  `submit-key-recovery-succeeded` when nothing reached the composer (E2E-F25).
- Route an exhausted-readiness live worker to `reconcile-recovery`, and expose a
  typed runtime-stop so its precondition can be met without raw `tmux
  kill-session` (E2E-F26).
- Give the pre-bootstrap window its own supervision state instead of
  `claim_renewal_required` (E2E-F22).
- Surface the failing field when an assignment packet is rejected; the serde
  error is currently discarded and the message names nothing (E2E-F13).
- Classify read-only `semantic-commit` probes before default-delivery argument
  analysis, including composed and redirected forms (E2E-F18, extending
  E2E-F02/F09).
- Reconcile `agent-session activity doctor` with `agent-hook` ownership; it
  reports `configured:false` while the compatibility probe reports
  `configured:true` with `compatibility_owner:"agent-hook"` (E2E-F05).

## Follow-up Checkpoint Template

```markdown
## Follow-up YYYY-MM-DD

### Checked
- Scenario and exact candidate/deployed versions

### Result
- Evidence and observed behavior

### Decision
- ready-for-implementation | implemented-locally | retained

### Next
- Exact owner, acceptance test, and rerun command
```

## Retention

Keep this document until every retained item is implemented and verified. If
provider issue delivery becomes available, open or update one issue from this
source and retain the provider URL here; do not create duplicate issues.
