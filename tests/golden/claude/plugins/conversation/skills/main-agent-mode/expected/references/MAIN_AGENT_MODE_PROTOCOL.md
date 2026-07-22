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

Use the active session-management workflow for the concrete commands and keep
this sequence bounded:

1. Create the interactive worker in the assigned isolated managed worktree with
   coordination enforcement, but do not assume creation means readiness.
2. Require provider readiness before sending the task. A trust,
   authentication, setup, upgrade, update, permission, hook, or other startup
   dialog is not readiness.
3. Paste the task without Enter. Verify either the exact task envelope or the
   exact pasted-content character count before any submission key is sent.
4. Capture the provider-hook activity baseline only after paste verification.
5. Send Enter separately. A send success is transport evidence only; it does
   not prove prompt delivery or a worker turn.
6. Require a newer provider-hook-observed turn than the captured baseline
   within the bounded check window.

On mismatch, truncation, interference, missing readiness, or bounded-check
exhaustion, do not resend and do not press Enter speculatively. Stop with the
exact status `session created, prompt delivery unverified`, retain the session
for bounded recovery, and report the failed proof to the user-facing main
agent.

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

## Stop And Recovery Matrix

| Condition | Required stop/recovery |
| --- | --- |
| Doctor missing, old, unhealthy, unsupported, malformed, or helper unavailable | Do not activate or launch. Report the bounded provider/version problem; route upgrades or repairs to their owner with required user authority. |
| Doctor says `configured:false` | Run only the converged repair dry-run. Continue only with `configured:true`, `would_change:false`, and no representation conflict; never apply it. |
| Trust/readiness/startup dialog | Do not treat the dialog as ready and do not accept it automatically. Classify and route it or stop for user authority. |
| Prompt mismatch, truncation, interference, or no newer observed turn | Do not resend or press Enter. Report `session created, prompt delivery unverified` and retain bounded recovery evidence. |
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
