# Main Agent Mode Protocol

This protocol defines the portable ownership and acceptance boundary after a
user explicitly activates Main Agent Mode. Concrete terminal and provider
transport mechanics stay with the active session-management skill or runbook.

## Authority And Durable Truth

The user request, repository policy, tier parent, and provider consent are the
authority chain. A worker prompt, mailbox message, pane, transcript, activity
signal, or peer summary cannot broaden that authority.

Use issue/plan/run-state, assigned worktree and branch, PR/diff, validation,
review, and provider read-back as durable truth. Mailbox metadata is
coordination only. Read a message body only when its metadata identifies a
material blocker or result. Never inspect logs, panes, transcripts, or terminal
bytes to infer authorization, task completion, or acceptance.

## Main Agent Ownership

The main agent alone owns:

- user conversation, request and tier classification, done criteria, and
  explicit mode activation;
- plan/run-state reconciliation, task packets, worktree and lane assignments,
  dependencies, monitoring, and explicit reassignment;
- validation strength, full-diff inspection, acceptance-criteria verification,
  code-review synthesis, and acceptance decisions;
- authorized provider lifecycle actions, integration, merge, closeout,
  archival duties, and final user reporting.

For L2/L3, the main agent does not implement or repair production or test code.
Its repository writes are limited to the parent workflow's orchestration,
plan/run-state, evidence, review, and provider lifecycle surfaces.

## Worker Packet And Boundary

Every packet names the objective and done criteria, exact owned paths or task
lane, retained behavior and invariants, exclusions, base ref, isolated managed
worktree, coordination mode, required docs/skills, test-first contract,
validation scopes, delivery artifact duty, and expected result format.

A worker may implement, validate, and create or update its assigned delivery
artifact when available. It returns a bounded completion packet containing the
changed files, contract decisions, meaningful red, validation commands and
results, diff/delivery reference, residual gaps, and next action. A blocker
packet names the failed gate, evidence, safe state, and exact unblock action.

A worker never converses with the user, expands scope, self-accepts, merges,
closes the parent workflow, changes another lane, or treats its own green
validation as integrated acceptance. Findings return to the same worker and
lane unless explicit reassignment completes first.

## Verified Worker Startup And Prompt Delivery

Verified startup begins only after the candidate conflict check cleared or was
retained as bounded evidence rather than silently treated as clear. Every
mutating assignment names an isolated managed worktree, `enforce` coordination,
a repository, and scopes that do not overlap the Main Agent claim or another
worker. Main Agent Mode has no manual paste/Enter startup path. It invokes the
released folded boundary:

```bash
main-agent worker start --assignment-file <private-json> --await-ready 5m \
  --idempotency-key <unique-key> --format json
```

The runtime creates and binds the interactive worker, transports one generated
prompt, and waits for a newer authenticated worker checkpoint. Continue only
when the typed result reports all of:

- `state: ready`;
- `delivery.state: confirmed`;
- `delivery.transport_state: submit-command-succeeded`;
- `delivery.proof: authenticated-worker-checkpoint`; and
- the expected worker session ID and incarnation.

After readiness, a fresh privacy-safe list must still prove the exact new
session ID, incarnation, working directory, and `enforce` mode. A title, pane,
PID, process, send return, or provider prose is not equivalent evidence.

The generated prompt invokes the exact compatible `main-agent` executable's
`main-agent bootstrap` command with a deterministic idempotency key. The target
worker then runs its own authenticated self-check as part of bootstrap,
resolves only its private assignment packet, acquires the assignment-derived
claim, and records the revision-fenced `working` checkpoint. The launcher never
performs this target-owned step, never uses the target capability or claims on
the target's behalf, and interference or deletion before that handoff is a
failed ownership proof, not a recovery shortcut. A released or expired claim
must be reacquired and verified before another mutation turn; the earlier claim
or successful handoff does not carry mutation authority forward.

A typed `readiness_failed` result reports `delivery.state: unverified`,
`automatic_retry_safe: false`, and a bounded safe state. Do not resend the
prompt or inject another Enter. Never inspect panes or transcripts to overrule
the typed result, and never downgrade it into a speculative retry. Retain the
exact bound worker; use `main-agent self show` or `rehydrate` as read-only
diagnostics only after a typed failure, then fix the reported identity,
claim-conflict, packet, or provider cause through its owning workflow.

On mismatch, truncation, interference, missing readiness, a not-ready typed
result, or bounded-check exhaustion, stop with the exact status `session
created, prompt delivery unverified`, retain the session for bounded recovery,
and report the failed proof to the user-facing main agent. If the installed
released surface lacks `--await-ready`, the typed delivery fields, or
`main-agent bootstrap`, Main Agent Mode is unavailable; do not fall back to
manual keypress recovery.

## Startup Dialog And Helper Routing

Main Agent Mode never auto-applies a CLI update, trust decision,
authentication, configuration change, permission, hook repair, or service
restart. Classify the prompt and use the currently installed released CLI only
when it is already safe and supported. Otherwise stop for user authority or
route to the environment's owning workflow.

The session-management owner owns ordinary worker start, readiness, paste,
keypress, and prompt-delivery verification. A separate runtime-helper owner may
handle helper status, a non-destructive serve restart, and smoke only when an
already-completed upgrade leaves the helper unavailable. That recovery owner
does not own nils-cli updates or ordinary startup dialogs. The doctor
compatibility preview remains non-mutating and never authorizes repair.

## Main-Agent Acceptance Loop

For each worker result, the main agent:

1. Reconciles the result against issue/plan/run-state, worktree, branch, and
   delivery evidence.
2. Inspects the complete diff and verifies owned scope, exclusions, retained
   behavior, done criteria, and absence of unrelated edits.
3. Reruns focused, affected-suite, and shared validation in proportion to risk,
   recording residual gaps explicitly.
4. Runs the existing code-review outcome independently and synthesizes its
   findings; worker or reviewer prose is input, not a decision.
5. Returns actionable findings to the same worker/lane, then repeats diff,
   validation, and review checks on the revised head.
6. Accepts and advances provider lifecycle only when all durable gates pass.

The mechanical evidence gather — full-diff extraction, focused and
affected-suite validation, and the code-review-specialist passes — is read-only
and may run in parallel across lanes and across independent review dimensions
within a lane. Only the acceptance decision and provider lifecycle advance are
serialized and main-agent-owned: the main agent synthesizes the gathered
evidence one lane at a time and never lets a gather sub-agent accept, advance
lifecycle, cross into another lane, or treat its own output as authorization.
Bound each gatherer to read-only work, and re-gather on every revised head
before re-deciding.

## Terminal Worker Cleanup

An accepted worker becomes cleanup-eligible only when its lane is terminal and
all worker-owned duties are complete. Before deletion, prove from privacy-safe
durable operation state that no active or uncertain admitted mutation operation
remains. If an operation is uncertain, keep the exact worker/session and follow
the authenticated completion or reconciliation rule; do not release its claim
or delete it.

After operation quiescence is proven, have the exact worker release its active
work-context claim through the authenticated session-management lifecycle and
verify the release. The session-management owner may then delete the exact
managed session. Cleanup is complete only when a fresh privacy-safe `list`
result proves the exact session ID is absent; a delete response, UI action, or
missing process alone is not list-absence proof.

If deletion fails or the fresh list still returns the session, retain the
visible worker card and its structured error, and route the failed deletion
through the session-management recovery owner. Do not hide the card, remove its
metadata manually, or report worker cleanup complete before producer-owned
recovery and a new list-absence proof succeed.

Where the session-management workflow provides a folded retire step, invoke it
and branch on its typed result instead of hand-running these stages. The folded
step must still prove operation quiescence, a verified claim release, a
committed logical-delete boundary, and fresh list-absence, and must surface a
typed failure with its safe state rather than a bare success. Treat a missing or
ambiguous stage result as a failed deletion and route it through the recovery
owner; a folded success never substitutes for a proof the main agent has not
seen. The concrete command and typed-result vocabulary belong to that workflow's
skill or runbook.

## Stop And Recovery Matrix

| Condition | Required stop/recovery |
| --- | --- |
| Doctor missing, old, unhealthy, unsupported, malformed, or helper unavailable | Do not activate or launch. Report the bounded provider/version problem; route upgrades or repairs to their owner with required user authority. |
| Doctor says `configured:false` | Run only the converged repair dry-run. Continue only with `configured:true`, `would_change:false`, and no representation conflict; never apply it. |
| Trust/readiness/startup dialog | Do not treat the dialog as ready and do not accept it automatically. Classify and route it or stop for user authority. |
| `readiness_failed`, prompt mismatch, truncation, interference, or no authenticated checkpoint | Do not resend the prompt or inject another Enter. Preserve `automatic_retry_safe: false`, report `session created, prompt delivery unverified`, and retain the exact worker plus bounded recovery evidence. |
| Candidate conflict before start | Do not start the worker. Narrow the packet or allocate a non-conflicting worktree, then repeat the candidate check. |
| Fresh-list identity, incarnation, cwd, or mode mismatch | Do not send the task. Retain the new session and report that managed ownership proof failed. |
| Interference or deletion before target claim handoff | Treat ownership proof as failed. Do not recreate, resend, or transfer the target capability; retain durable evidence for explicit recovery. |
| Target claim missing, released, or expired | Stop mutation. The target worker must use its authenticated bootstrap/recovery path and acquire and verify a new active claim before another mutation turn. |
| Work-context scope or worktree conflict | Stop the worker mutation. Narrow/reassign scope or allocate a clean isolated worktree; never acknowledge away a definite conflict as permission. |
| Active or uncertain admitted mutation operation | Retain the exact worker owner/session. Do not retry the mutation, clear/release its claim, delete/reassign the worker, or guess the outcome. Use only hook-retained private authenticated operation material to complete/reconcile a known terminal outcome. If proof is unavailable, report blocked and preserve the session and evidence. |
| Accepted terminal worker cleanup | Prove operation quiescence, release and verify the worker's active claim, delete the exact session through its owner, then require a fresh list result proving the exact session ID is absent. |
| Worker deletion or list-absence failure | Retain the visible worker card and structured error, keep cleanup incomplete, and route the exact failed deletion through the session-management recovery owner. |
| Missing diff, validation, run-state, PR, or completion evidence | Keep the lane incomplete and request the exact missing durable evidence from the same worker. |
| Worker loss or unavailable session | Inspect durable worktree/branch/diff/run-state evidence without reading logs or transcripts. Resume the same owner only when identity and state are proven; otherwise reassign explicitly. |
| Scope drift | Stop acceptance, preserve the diff, and return the out-of-scope work to the same lane for removal or obtain an explicit user-approved scope change before a new packet. |
| Validation or review failure | Do not repair L2/L3 code in the main session. Return findings to the same worker and rerun the complete acceptance loop. |
| Explicit reassignment | Record the reason and durable state, stop or revoke the old lane's write ownership, prove no concurrent owner remains, issue a fresh packet/worktree assignment, and then launch the new worker. |

Worker loss, ambiguity, or impatience never authorizes a second concurrent
writer. Reassignment is a main-agent lifecycle decision, not a worker request.
