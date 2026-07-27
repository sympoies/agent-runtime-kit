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
worker. Its packet worktree, `launch.cwd`, durable assignment worktree, and
authenticated worker cwd must resolve to the same canonical checkout root
before bootstrap can mint a shell grant. Keep those path scopes narrow. A checkout-local shell operation is
admitted only through the private grant minted by authenticated worker
bootstrap plus the claim's matching repository and worktree fingerprint. It
does not require or create repository scope. The grant coordinates the
isolated checkout; it is not a path sandbox, so acceptance must reject a final
diff outside the declared paths. Explicit edit admission and shell retargeting
to another checkout still fail closed.
Main Agent Mode has no manual paste/Enter startup path. It invokes the released
folded boundary:

```bash
main-agent worker start --assignment-file <private-json> --await-ready 5m \
  --idempotency-key <unique-key> --format json
```

The runtime creates and binds the interactive worker, transports one generated
prompt, and waits for a newer authenticated worker checkpoint. If a fresh
supported worker remains `starting`, the runtime may send exactly one recovery
Enter within the original `--await-ready` deadline. Before sending it, the
runtime rechecks that the same session incarnation is still live and serializes
the input through the session lifecycle guard. It never resends the prompt,
never applies this recovery to an existing/replayed worker, and never attempts a
second recovery Enter. The Main Agent never decides whether to inject this
keypress and never sends it itself.

Continue only when the typed result reports all of:

- `state: ready`;
- `delivery.state: confirmed`;
- `delivery.transport_state: submit-command-succeeded` with recovery not needed,
  or `delivery.transport_state: submit-key-recovery-succeeded` with
  `submit_key_recovery.eligible: true`,
  `submit_key_recovery.attempted: true`,
  `submit_key_recovery.attempt_count: 1`, and
  `submit_key_recovery.result: checkpoint-confirmed`;
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
`automatic_retry_safe: false`, the bounded `submit_key_recovery` disposition,
and a bounded safe state. The runtime has either exhausted its one recovery
Enter or marked the worker ineligible. Do not resend the prompt or inject
another Enter. Never inspect panes or transcripts to overrule the typed result,
and never downgrade it into a speculative retry. Retain the exact bound worker.
Use `main-agent self show` or `rehydrate` as read-only diagnostics only after a
typed failure; then fix the reported identity, claim-conflict, packet, or
provider cause through its owning workflow.

## Dependency-Gated Launch

An assignment packet may declare same-run dependency IDs in `depends_on`.
`worker start` checks the live registry before creating or launching the
dependent. Only `accepted` or `released` satisfies a dependency. A
`submitted`, `working`, `blocked`, `starting`, `cancelled`, missing, or
cross-run dependency returns `dependency-not-satisfied` with bounded
`blocked_on` entries, and no dependent assignment is created.

Wait boundedly for each declared upstream assignment:

```bash
main-agent worker wait <dependency-id> --until terminal --timeout 60s \
  --format json
```

Then re-read the exact dependency. A terminal wait may return `cancelled`,
which still does not satisfy the edge. Retry the unchanged dependent launch
only after every dependency is `accepted` or `released`. If a dependency ID or
packet must change, use a new idempotency key for that changed request. Never
launch speculative downstream work or treat `submitted` as dependency
acceptance.

The folded start result is a provisional snapshot, not a permanent verdict on
the bound worker. In particular, `worker-activity-not-authoritative-starting`
is a non-authoritative starting failure. If the same session incarnation later
authenticates, acquires its assignment claim, and checkpoints `working`, do not
create a duplicate assignment or worker. Run `worker supervise` on that exact
incarnation and continue from the newer durable evidence.
A folded `readiness_failed` snapshot can be superseded by that newer authoritative
evidence from the same incarnation; it never authorizes a second prompt, Enter,
assignment, or worker.

An authenticated mailbox notification is a delivery optimization, not proof
that a prompt was consumed or bootstrap completed. A pending mailbox notification is not readiness proof.
Inspect the facade's assignment, worker,
and notification evidence first. Only when the exact worker incarnation and
the one intended prompt are proven may the session-management owner perform a
deliberate privacy-safe session send. Do not resend the prompt, send a second
Enter, or infer consumption from notification metadata.
For `notification-pending` with the controller unavailable, prove through a
privacy-safe glance that the exact worker is at an idle composer before sending
one short mailbox prompt and exactly one Enter. A busy worker, startup dialog,
trust/auth/permission prompt, or unknown transport outcome blocks this fallback.
Never send a second Enter.

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

Use these deterministic startup branches:

| Snapshot | Required route |
| --- | --- |
| CLI update offered or required | Do not apply automatically. Keep the installed executable and route the upgrade decision to its owner. |
| MCP initialization in progress | Continue bounded waiting, then supervise; a timeout or provider prose is not failure or progress proof by itself. |
| MCP initialization failure | Preserve the worker and route the typed MCP failure; never disable or repair integrations implicitly. |
| MCP authentication required | Stop for the authentication owner; never submit credentials or accept a browser/device flow automatically. |
| Repository trust prompt | Stop for explicit trust authority; never accept it automatically. |
| Provider authentication prompt | Stop for the account owner; never infer the intended account. |
| Tool permission prompt | Stop for the permission owner; never approve it automatically. |
| Ordinary provider prompt submission | Let folded `worker start` own its one bounded submission and recovery attempt. Do not send a blind Enter. |
| Pre-claim bootstrap failure | Run `worker supervise`; cancel/reassign only when `reassignment_safe:true` and preserve the failed worker otherwise. |
| Controller unavailable or broker stale | Diagnose coordination status, then use exact-controller `self recover` for a stale/lost broker before rebind. Reserve rebind for a proven controller-incarnation mismatch; do not copy capabilities or take over the worker claim. |
| Active or uncertain admitted operation | Preserve the exact worker and reconcile that operation. Never cancel, retire, release, or reassign it. |

## Active Supervision And Typed Recovery

After launch, every bounded `worker wait` timeout and every contradictory
snapshot must lead to active diagnosis:

```bash
main-agent worker supervise <assignment-id> --format json
main-agent worker diagnose <assignment-id> --format json
```

`worker supervise` is the repeatable macro-first path. Branch on its typed
`classification` and `recovery_action.kind`, never on provider prose.
`recovery_action.executable:true` means its exact `argv` can run only through
the declared `owner` and `capability_delivery`. When executable is false,
resolve every `recovery_action.required_inputs` value through that owner and
use the returned `argv_template`; do not execute placeholders, copy a private
capability, or substitute raw terminal input. `last_proven_safe_state` remains
the evidence boundary for the action. `worker diagnose` exposes the same
privacy-safe evidence without the supervisor wrapper. A provider `working`
string or fresh broker heartbeat alone is not material progress. Evaluate the
assignment revision/state, provider activity, worktree material fingerprint
and age, current claim/edit authority, authenticated mailbox state, and active
or uncertain operations together.
An active or renewed claim, dirty worktree, recent terminal heartbeat, or
provider `working` text is never progress by itself. Compare material
fingerprint change time, provider `last_progress_at`, assignment revision and
checkpoint time, mailbox state, operation state, and attention/capacity
classification. When they do not advance, stable dirty material plus stale provider progress is stalled
or attention-required, not healthy progress. Apply the same rule to stale clean
worktrees, capacity errors, and recovery deadlocks, and do not renew edit authority indefinitely
without authoritative progress.

## Post-Claim Stopped Runtime Reconciliation

A bootstrap-complete worker is post-claim only when durable assignment evidence
proves it reached `working`. If supervision also proves the exact bound worker
runtime is stopped, the recorded session and incarnation are unchanged, and no
admitted mutation operation is active or uncertain, require this public
projection:

- `classification: post_claim_failure`;
- `last_proven_safe_state.post_claim_terminalization_safe: true`;
- `automatic_retry_safe: false`;
- `recovery_action.kind: stopped_worker_terminalization`.

Consume only the public `main-agent.worker-diagnose-result.v2`,
`main-agent.worker-supervise-result.v2`, and
`main-agent.worker-recovery-action.v2` schemas. A v1 projection cannot prove
the final observed-state or quarantine contract and must fail closed.

That projection authorizes only the Main-owned, revision-fenced, idempotent
macro. Require exactly
`recovery_action.required_inputs:["terminalization_reason","idempotency_key"]`;
a third input fails closed. Resolve both values through the declared Main owner
and use the returned `recovery_action.argv_template`:

```bash
main-agent worker reconcile-stopped <assignment-id> \
  --if-revision <assignment-revision> \
  --reason <bounded-terminalization-reason> \
  --idempotency-key <unique-key> --format json
```

The macro must return schema
`main-agent.worker-reconcile-stopped-result.v2`. Continue only when its result
reports `terminalized:true`, top-level `worker_claim_active_after:false`,
`input_sent:false`, `worktree_preserved:true`, and this stable proof:

```text
proof.worker_claim:{
  active_disposition:"absent",
  release_provenance:"not_attributed_to_attempt",
  observed_at_stage1:<bool>
}
```

The result proves observed claim absence without claiming that the current
attempt performed a release. The transition is
`working` → `reconcile-stopped` → `cancelled` → `retire`: terminalization
fences the exact stopped worker session authority against resume.
It installs a session-only authority quarantine for the exact worker.
It preserves a frozen assignment schema v3 for the exact worker.
CLI and HTTP resume are denied while quarantined.
Unrelated session, run, and coordination authority remains unchanged.
Read-only observational coordination access does not renew generic claims or operations.
It preserves the worktree, branch, diff, durable run, and Main session.
It neither accepts the failed work nor authorizes a new writer.
After the `cancelled` read-back, retire the reconciled worker or create a distinct replacement assignment.
Apply the ordinary non-overlap and ownership gates to any replacement.

A stopped-worker reconciliation has two exact replay-safe stale-revision cases.
First, the replay must use the exact same request, original revision
(`--if-revision`), and same idempotency key. With a matching completed v2
terminal receipt, it returns that committed result despite the now-stale
revision. The return occurs before revision checking and without repeating
mutation.

Second, an exact replay of an interrupted stage 1 must retain the original
now-stale `--if-revision` and original idempotency key. That replay may finish
stage 2 only after validating a matching strict progress receipt. It must also
validate the cancelled assignment, session-only quarantine, exact worker
identity, stopped runtime, operation quiescence,
and current controller authority.
Stage 2 accepts the exact original controller claim or an explicit distinct successor.
That authority must be bound to the same current run, Main session, and incarnation.
The authorized retry rolls orphaned progress forward instead of discarding
the frozen assignment, weakening the quarantine, or repeating already
committed effects.

New key, changed request, or a replay with neither a matching completed v2
terminal receipt nor a matching strict progress receipt fails closed.

A live or unknown runtime, or any active or uncertain operation, fails closed.
Treat `worker-runtime-still-live`, `coordination-runtime-unverified`,
`worker-not-quiescent`, `worker-incarnation-changed`, and
`assignment-state-conflict` as fail-closed refusal codes.
Refusal status alone does not report a safe state.
Require a fresh v2 `worker diagnose` or `worker supervise` projection before
continuing, unless an envelope explicitly exposes that proof.
Expired or released Main controller claim authority
continues to use the existing coordination-authorization failure contract; do
not reinterpret it as a post-claim terminalization result. Outside the two
exact receipt-backed replays above, a stale revision, different incarnation,
changed assignment state, or new operation evidence must not mutate anything.

For `post_claim_failure`, do not call ordinary `cancel` or `reassign`, do not
force-delete a session or group, and do not resume or send input to the stopped
worker.
Never use raw tmux, terminal input, group cleanup, or a B3 runtime-stop primitive for this B2 transition.
B3 owns the separate still-live pre-claim/readiness-failure stop problem.

If `worker wait`, supervision, or another facade action returns
`coordination-unauthorized`, diagnose the coordination boundary before choosing
a recovery:

```bash
agent-session work-context status --format json
agent-session broker status --session "$AGENT_SESSION_ID" --format json
```

When those observations prove a stale or lost broker for the still-authoritative
controller incarnation, the active claim is retained, and no operation is active
or uncertain, run exact-controller `main-agent self recover` before attempting rebind:

```bash
main-agent self recover --idempotency-key <unique-key> --format json
```

Require an authoritative recovery result and re-read `self show` before
resuming wait or supervision.
`rebind` is reserved for a proven controller-incarnation mismatch;
it is not a stale-broker recovery and can be
rejected by the same authorization gate. Never copy a capability, clear an
operation fence, change accounts, resume or replace a provider, resend a
prompt, or inject Enter as part of broker recovery.

The capability-failure-closed recovery lane is finite and independent of
ordinary hook capability validation. It admits only the trusted exact
version/status, `self show`, `self recover`, `rehydrate`, and revision-fenced
`rebind` shapes mirrored by both shared hooks and the binary argv contract.
Arbitrary Bash, raw terminal input, worker start, trust, authentication,
permission, account, and repository mutations remain denied. If even an exact
recovery shape cannot execute, enter the durable blocked hold below rather than
repeating Stop or broadening the lane.

Service health, provider process health, provider session binding, and the Main relationship are four distinct states.
A successful Agent Console/service restart does not prove the existing provider
process or session binding recovered. For a proven provider-session mismatch,
require explicit user authorization before interrupting the provider. Prefer the
typed provider restart-resume action when the compatible facade exposes it.
Otherwise use the executable lifecycle fallback:

1. Gracefully stop the exact provider process.
2. Run `agent-session resume <session-id> --format json`.
3. Prove the same durable session at a new generation and incarnation.
4. Run revision-fenced `main-agent rebind`.
5. Re-read `main-agent self show --format json`.

Preserve the provider thread, exact account binding, repository/worktrees,
workers, and durable run. Never use logout, account switching, blind Enter, raw
input, or worker replacement for this recovery.

After rebind, verify post-rebind assignment ownership before any worker
message, diagnosis, supervision, or mutation. Prefer an atomic replay-safe
rebind-and-adopt result when exposed. Otherwise, after rebind restores ordinary
authority, use revision-fenced `main-agent adopt <assignment-id>` only for each
assignment whose primary manager is still the exact prior controller of this
run. Leave unrelated, orphaned, borrowed, and collaborator relationships
unchanged, and re-read every adopted assignment before continuing.

Use macro-first recovery for `self recover`, `worker start`, `worker
supervise`, `guidance-reconcile`, `guidance-quarantine`, `account-handoff`,
`account-handoff-cancel`, `submit-recovery`, `reconcile-recovery`, `cancel`,
`reconcile-stopped`, `reassign`, `accept`, and `retire`. When a macro returns a
partial or typed failure, continue only with the named primitive from
`last_proven_safe_state`. Do not replay the entire macro, prompt, or terminal
input. Edit-authority renewal belongs to the exact worker: ask it to renew its
current claim and revision with its own capability file.

Guidance continuity retains message identity and unread state.
`guidance-reconcile` forwards only eligible exact-controller guidance to a
retained previous worker; `guidance-quarantine` quarantines only orphaned stale
incarnation records when no previous worker exists. Neither action proves
consumption or permits reading message bodies automatically.

Account selection, exact incumbent account binding, and auto-resume re-arm are
three distinct durable transitions. `account-handoff` requires explicit
`--account`, current revision, `--authorize-account-change`, a managed worker
advertising the required capability, authoritative broker and claim, and
operation quiescence. The account binding is verified before structured auto-resume is re-armed.
`account-handoff-cancel` handles only the exact
queued/failed reservation under the same authority checks. Never use `/logout` or raw terminal input
as the normal account switch, and never choose an account
implicitly. If a raw or unmanaged worker lacks managed account handoff, surface
`account_handoff_capability_gap` and follow the executable lifecycle fallback;
do not describe it as recoverable through a daemon-only path.

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

Until the facade exposes a dedicated submit action, worker submission is a
revision-fenced `main-agent checkpoint` packet with `state:"submitted"` and a
bounded `result_summary`; do not invent `worker submit`. Its `--file` must be
an absolute normalized `.json` path outside the governed checkout, a regular
file owned by the current user, and mode `0600`; allocate it under a
project-owned private state/output directory. When review finds bounded
defects, return the exact submitted assignment to its bound worker:

```bash
main-agent worker request-changes <assignment-id> \
  --if-revision <assignment-revision> \
  --reason "<bounded-review-reason>" \
  --idempotency-key <unique-key> --format json
```

This manager-only transition is revision-fenced and changes only `submitted` to `working`.
It preserves the bound worker and private packet, clears stale result and
blocker summaries, and records the review reason as the next action. It does not send review guidance, provider input, or re-arm auto-resume.
Write the actionable findings to a private body file and send them separately:

```bash
main-agent worker message <assignment-id> --body-file <private-text> \
  --idempotency-key <unique-key> --format json
```

The mailbox notification is still not consumption proof. Supervise the exact
worker and follow the one-send notification fallback only when its existing
idle-composer preconditions are proven. Do not send another Enter, create a
duplicate lane because the submitted provider turn ended, or repurpose
account-handoff auto-resume; that structured re-arm remains limited to its
typed quota-recovery transition. Re-run the complete acceptance loop on the
worker's next submitted revision. Rejection is never acceptance.
A submitted assignment with a released claim, clean worktree, terminated
provider turn, and no active or uncertain operation is ready for read-only
review; do not renew mutation authority merely because supervision reports
`claim_renewal_required`. A later repair still requires a new or renewed claim
owned by the exact authorized worker.

A durable blocked terminal/hold state must preserve the full goal and unfinished checklist.
When an unchanged blocking fingerprint has no executable recovery capability,
do not reinvoke the same Stop action. Resume only after new user input, changed
external state, or a verified recovery transition; retain the complete
unfinished checklist and do not claim completion.

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

A stopped or rejected session without an accepted assignment is not directly
deletable through the accepted-worker path. Preserve its work and evidence.
Use typed `cancel` for a proven failed pre-claim assignment, `reassign` only
when supervision proves safe reassignment, and group cleanup after an accepted
replacement. A `post_claim_failure` instead follows the exact
`reconcile-stopped` transition above before retirement or a distinct
replacement; never use cancel, reassign, or group cleanup to bypass that
transition. Never rewrite registry state or discard the retained lane merely to
make it disappear.

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
| `readiness_failed`, prompt mismatch, truncation, interference, or no authenticated checkpoint | Treat runtime-owned single-Enter recovery as exhausted or ineligible. Do not resend the prompt or inject another Enter. Preserve `automatic_retry_safe: false`, report `session created, prompt delivery unverified`, and retain the exact worker plus bounded recovery evidence. |
| Candidate conflict before start | Do not start the worker. Narrow the packet or allocate a non-conflicting worktree, then repeat the candidate check. |
| Fresh-list identity, incarnation, cwd, or mode mismatch | Do not send the task. Retain the new session and report that managed ownership proof failed. |
| Interference or deletion before target claim handoff | Treat ownership proof as failed. Do not recreate, resend, or transfer the target capability; retain durable evidence for explicit recovery. |
| Target claim missing, released, or expired | Stop mutation. The target worker must use its authenticated bootstrap/recovery path and acquire and verify a new active claim before another mutation turn. |
| Submitted lane has no active claim | If the assignment is submitted, the worktree is clean, the provider turn is terminated, and no operation is active or uncertain, proceed with read-only review. Do not renew mutation authority solely to satisfy `claim_renewal_required`; require it only for a later authorized mutation. |
| Work-context scope or worktree conflict | Stop the worker mutation. Narrow/reassign scope or allocate a clean isolated worktree; never acknowledge away a definite conflict as permission. |
| Active or uncertain admitted mutation operation | Retain the exact worker owner/session. Do not retry the mutation, clear/release its claim, delete/reassign the worker, or guess the outcome. Use only hook-retained private authenticated operation material to complete/reconcile a known terminal outcome. If proof is unavailable, report blocked and preserve the session and evidence. |
| Bootstrap-complete exact worker runtime is stopped | Require `post_claim_failure`, `last_proven_safe_state.post_claim_terminalization_safe:true`, and `automatic_retry_safe:false`; run only revision-fenced `worker reconcile-stopped`, verify the typed terminalization result, then retire or create a distinct replacement. Preserve worktree/diff/run/Main and send no input. |
| Post-claim worker runtime is live or unknown, or operation state is active or uncertain | Fail closed. Do not reconcile-stopped, cancel, reassign, retire, resume, send input, stop the runtime, or force group cleanup. Preserve the exact worker and typed refusal. |
| Accepted terminal worker cleanup | Prove operation quiescence, release and verify the worker's active claim, delete the exact session through its owner, then require a fresh list result proving the exact session ID is absent. |
| Worker deletion or list-absence failure | Retain the visible worker card and structured error, keep cleanup incomplete, and route the exact failed deletion through the session-management recovery owner. |
| Missing diff, validation, run-state, PR, or completion evidence | Keep the lane incomplete and request the exact missing durable evidence from the same worker. |
| Worker loss or unavailable session | Inspect durable worktree/branch/diff/run-state evidence without reading logs or transcripts. Resume the same owner only when identity and state are proven; otherwise reassign explicitly. |
| Scope drift | Stop acceptance, preserve the diff, and return the out-of-scope work to the same lane for removal or obtain an explicit user-approved scope change before a new packet. |
| Validation or review failure | Do not repair L2/L3 code in the main session. Return findings to the same worker and rerun the complete acceptance loop. |
| Explicit reassignment | Record the reason and durable state, stop or revoke the old lane's write ownership, prove no concurrent owner remains, issue a fresh packet/worktree assignment, and then launch the new worker. |

Worker loss, ambiguity, or impatience never authorizes a second concurrent
writer. Reassignment is a main-agent lifecycle decision, not a worker request.
