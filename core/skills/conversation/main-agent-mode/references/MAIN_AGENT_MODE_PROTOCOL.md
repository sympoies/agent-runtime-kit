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

The Main controller uses `advisory`; every isolated implementation worker uses `enforce`.
Immediately before every `main-agent init` branch, run `agent-session list
--format json` and require `cli.agent-session.list.v1` to bind the exact
controller session ID, incarnation, and canonical cwd; its `coordination_mode`
field is identity context only and cannot distinguish requested or configured
mode from a fresh runtime observation. Initialization additionally requires the
trusted session-management owner to advertise
`session-management.controller-mode-observation.v1` and execute its
owner-supplied non-mutating invocation, returning authenticated
`session-management.controller-mode-observation-result.v1` with the same
session ID, incarnation, canonical cwd, `mode_source:"runtime-observed"`,
`fresh:true`, and `observed_mode:"advisory"`. A missing capability, wrong cwd,
unbound or stale identity, `mode_source:"requested"` or
`mode_source:"configured"`, or observed `enforce`, `off`, or unknown mode fails
closed before `main-agent init`. A controller observed in `enforce`, `off`, or
an unknown mode fails the pre-init gate. Before closing it, the session owner must prove the exact controller
session and incarnation, broker
zero active and zero uncertain operations, no unfinished typed lifecycle
transition, and no unique unpreserved material. Authenticated claim inventory
must also prove that every claim bound to that exact controller session and
incarnation is absent or explicitly transferred/released through its typed
owner, including any unrelated successor claim. Unknown inventory or any
surviving claim retains the controller and fails closed. Only then close that exact
session through its owner, require fresh-list absence, remove its clean
controller worktree with `git-cli` when it has no retained purpose, and restart
once in `advisory` before attempting `init`. Missing or ambiguous proof retains
the session and worktree and fails closed; never create durable run state from
the wrong mode and repair it afterward.

A failed controller startup before `main-agent init` may be deleted and
restarted once with a compact prompt that points to the private full packet
only when no run claim or assignment exists, the broker proves zero active and
zero uncertain operations, no unfinished typed lifecycle transition exists,
no unique unpreserved worktree material exists, and authenticated claim
inventory proves every claim bound to the exact controller session and
incarnation is absent or explicitly transferred/released. This is a controller
pre-init recovery, never a worker-start recovery. The owner must fresh-list
verify exact-session absence before the restart; any failed proof preserves the
session and fails closed.
Every pre-init close-and-restart branch, including a wrong-mode branch, must use
this restart-once boundary. It requires the trusted released
session-management owner to advertise
`session-management.failed-controller-restart.v1`, execute its owner-supplied
invocation, and return authenticated
`session-management.failed-controller-restart-result.v1`. The immutable request
digest and durable consumed/idempotency marker bind the restart owner, failed
controller session ID and incarnation, canonical cwd and controller worktree,
requested `advisory` mode, compact prompt and private-packet reference digest,
and authenticated claim-inventory projection. The marker is consumed before
the first destructive stage. Any changed request field is rejected before
deletion or restart.
Identical replay returns the same receipt without repeating deletion or
restart; partial progress resumes only the recorded remaining stage. An
ambiguous restart outcome retains the exact session and fails closed rather
than issuing another start. If that owner primitive is absent, retain the exact
session and fail closed.

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
Main Agent Mode has no Main-agent-owned manual paste/Enter startup path. After
the candidate conflict check, prefer the folded readiness boundary:

```bash
main-agent worker start --assignment-file <private-json> --await-ready 5m \
  --idempotency-key <unique-key> --format json
```

The runtime creates and binds the interactive worker, transports one generated
prompt, and waits for a newer authenticated worker checkpoint. If a fresh
supported worker remains `starting`, the runtime may send exactly one recovery
Enter within the original `--await-ready` deadline. Before sending it, the
runtime rechecks that the same session incarnation is still live. Before input,
a privacy-safe observation must prove the exact already-delivered prompt at an
idle composer, the broker must prove zero active and zero uncertain operations,
and the observation must classify the surface as an ordinary provider composer
rather than a trust, authentication, account, permission, secret,
provider-mutation, startup-dialog, or unknown state. The typed result exposes
those eligibility proofs and `input_sent:true`.
Stale, partial, malformed, or ambiguous proof makes recovery ineligible. The
runtime serializes eligible input through the session lifecycle guard. It never resends the prompt,
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
claim, records the revision-fenced `working` checkpoint, and receives the
literal runtime-issued `checkpoint_file`. The prompt requires that exact file
as the only later checkpoint JSON write target and then invokes
`main-agent checkpoint --file` with the current revision and a stable
idempotency key. Activation must first verify the selected provider with
`main-agent capabilities --provider <codex|claude> --format json`, which advertises
both `main-agent.runtime-checkpoint-file.v1` and
`runtime-kit.checkpoint-write-admission.v1`, plus
`main-agent.run-wide-closeout.v1`, with `compatible:true`; the hook capability
is derived from deployed `agent-hook` bundle `2026.07.28.1` or newer and its
locked `agent-session.coordination.v1` rules for that provider. That bundle is
the first whose paired handler admits checkpoint writes. The probe additionally
requires the selected provider's converged doctor record and exact installed
handler to advertise `runtime-kit.handler-capabilities.v1`; policy metadata
alone is insufficient, while an uninstalled other provider does not block the
selected one. Activation then requires `main-agent self readiness --format
json` to prove this exact current session incarnation received its
runtime-issued environment path and still has the trusted private checkpoint
file. `runtime-checkpoint-unavailable` requires a managed resume or restart
after deployment and forbids `init` or mutation from the stale incarnation.
The `>=1.25.11` packaging floor alone does not prove this paired API. The launcher never
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

Because fixed terminal notification delivery deliberately waits for a
no-claim safe-input boundary, a Main controller with an active claim must
inspect and disposition its authenticated mailbox before returning to an idle
waiting prompt. Use inbox metadata first through `agent-session message inbox
--session "$AGENT_SESSION_ID" --capability-file
"$AGENT_SESSION_CAPABILITY_FILE" --state unread --limit <n> --format json` and
require `cli.agent-session.message-inbox.v1`. Require the exact current
recipient session and incarnation plus `sender.authenticated:true`; show only a
material message body through `agent-session message show --session
"$AGENT_SESSION_ID" --message <message-id> --capability-file
"$AGENT_SESSION_CAPABILITY_FILE" --format json` and require
`cli.agent-session.message-show.v1`. Disposition with `agent-session message
ack --session "$AGENT_SESSION_ID" --message <message-id> --if-revision <n>
--capability-file "$AGENT_SESSION_CAPABILITY_FILE" --idempotency-key
<stable-key> --format json`, require `cli.agent-session.message-ack.v1`, and
bind the revision-CAS and stable idempotency key to that exact message. A forged
sender, wrong recipient or incarnation, stale revision, or non-material message
fails closed without body access or authority change. Do not release or widen
the claim, send terminal input, or infer message consumption merely to trigger
that notification.

On mismatch, truncation, interference, missing readiness, a not-ready typed
result, or bounded-check exhaustion, stop with the exact status `session
created, prompt delivery unverified`, retain the session for bounded recovery,
and report the failed proof to the user-facing main agent. If the installed
released surface lacks `main-agent bootstrap`, Main Agent Mode is unavailable.
Prefer folded CLI startup readiness through `--await-ready` and its typed
delivery fields. Until that boundary is available, Main Agent Mode may continue
only when the trusted released session-management owner advertises
`session-management.verified-submit-recovery.v1`, supplies an owner-advertised
exact invocation, and returns authenticated
`session-management.verified-submit-recovery-result.v1`. The result carries
authenticated producer identity, the exact capability and invocation contract,
and a request digest over the bound session ID, incarnation, already-delivered
prompt fingerprint, and idempotency key. The typed request and result bind
the exact session ID, incarnation, and already-delivered prompt fingerprint;
prove `composer_state:"idle"`, `sensitive_dialog:false`, `broker_active:0`, and
`broker_uncertain:0`; persist the attempt through an atomic consumed-before-input marker; and report
`attempted:true`, `attempt_count:1`, and `input_sent:true`. The durable consumed
marker is keyed by exact session ID plus incarnation, independent of prompt
fingerprint; any existing marker for that incarnation rejects every later
request before input, even with a different prompt fingerprint or idempotency
key. The successful result
normalizes into the same readiness and `delivery` projection above only after
the authenticated worker checkpoint. A failure receipt reports
`input_sent:false` and preserves the marker and bounded reason; exact replay
returns the prior receipt without input, while changed identity, prompt,
request digest, or key is rejected before input. Self-asserted schema strings,
peer prose, or an unadvertised command never grant terminal-input authority.
Missing or forged capability, producer, binding, or fields; `attempted:false`;
a stale or mismatched identity or prompt; a sensitive or unknown surface;
replay; or a partial or ambiguous outcome fails closed. Without that executable
owner capability, Main Agent Mode is unavailable for the fallback. Send no
further input, never stack Enter presses, and never resend the prompt.

## Startup Dialog And Helper Routing

Main Agent Mode never auto-applies a CLI update, trust decision,
authentication, configuration change, permission, hook repair, or service
restart. Classify the prompt and use the currently installed released CLI only
when it is already safe and supported. Otherwise stop for user authority or
route to the environment's owning workflow.

Account choice or change, permission elevation, secret access, provider or
other external mutation, and every non-quiescent or unknown operation are also
explicit authority boundaries. Transport recovery and resource closeout never
authorize them and fail closed whenever their state is present or uncertain.

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
the exact `checkpoint_file` returned by the worker's authenticated
`main-agent bootstrap`. The runtime pre-creates this private mode-0600 path and
binds it to the current session incarnation. Write the bounded object there and
pass the same literal path to `--file`; do not allocate a project-output
substitute. When review finds bounded defects, return the exact submitted
assignment to its bound worker:

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

Every Main Agent Mode controller, worker, provider session, and managed
worktree requires a final disposition. Never close or delete an owner that has
an active or uncertain operation, an unfinished assignment without a safe typed
transition, unique unpreserved material, or the only recovery evidence.

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

The committed logical-delete boundary removes the worker from the default live
worker list. Facade logical live-worker absence is not physical session-owner
absence: a tombstone or default facade list cannot prove that the provider
session was deleted. If later physical deletion fails or a fresh list still returns the
session, retain a typed maintenance tombstone and its structured error in the
maintenance projection, set `workers_absent:true` for the logical list and
`cleanup_pending:true`, and route the failed deletion through the
session-management recovery owner. Identical replay returns that same
tombstone. Do not restore a live worker card, remove metadata manually, or
report physical cleanup complete before producer-owned recovery and a new
list-absence proof succeed.

Where the session-management workflow provides a folded retire step, invoke it
and branch on its typed result instead of hand-running these stages. The folded
step must still prove operation quiescence, a verified claim release, a
committed logical-delete boundary, and fresh list-absence, and must surface a
typed failure with its safe state rather than a bare success. Treat a missing or
ambiguous stage result as a failed deletion and route it through the recovery
owner; a folded success never substitutes for a proof the main agent has not
seen. The concrete command and typed-result vocabulary belong to that workflow's
skill or runbook.

## Run Closeout And Handoff

Run closeout is a Main-owned lifecycle transition after assignment acceptance or
typed terminalization. A final chat response, committed repository state, or
closed provider record is not durable orchestration closeout.

Before closing the run, rehydrate or read status, prepare the private final
bounded checkpoint, and inspect every assignment. No assignment may remain
`starting`, `working`, `blocked`, or `submitted` without an explicit retained
exception that the run close contract accepts. Use each assignment's typed
classification and recovery path; never collapse pre-claim cancellation,
post-claim stopped reconciliation, accepted-worker release, or uncertain
operation recovery into generic deletion.

A zero-assignment pre-launch-blocked run may checkpoint a zero-assignment blocker
and use run-wide closeout once it is terminal-ready. The checkpoint preserves
the original objective and blocker and never claims the product objective was
completed. For a post-init controller-mode mismatch, never widen the Main
claim into worker scopes or stack terminal input. Checkpoint the blocker and
use typed closeout when admitted. If closeout is not admitted, preserve broker
zero active/zero uncertain state until claim expiry permits authenticated
mailbox wakeup, then resume only through the typed owner path.

A post-init wrong-mode incident with one or more assignments is different:
freeze every new launch and Main-owned mutation, preserve every worker, claim,
worktree, and unique material, and reconcile active or uncertain operations
only through their exact owners. Never use zero-assignment closeout for a
nonzero run. Assignments in `starting`, `working`, `submitted`, and `accepted`
remain in their current typed lifecycle until a trusted owner recovery proves
the exact safe transition. Recovery requires the released facade to advertise
`main-agent.nonzero-wrong-mode-recovery.v1` with its exact owner-supplied
invocation and return authenticated
`main-agent.nonzero-wrong-mode-recovery-result.v1`. Its revision-CAS request
binds the controller session and incarnation, canonical cwd, run ID and
revision, immutable assignment ID/revision/state snapshot, broker
active/uncertain projection, request digest, and idempotency key. The result
binds the same digest and records one typed-owner receipt per assignment:
`starting` may move only through worker-start reconciliation, `working` only
through worker checkpoint/supervision, `submitted` only through manager review,
and `accepted` is preserved unchanged. It also returns the durable post-recovery
run revision and authenticated read-back. Before the first assignment mutation,
the owner durably consumes a progress marker keyed by the full request digest,
original run and assignment revisions, and idempotency key. Its authenticated
progress receipt records completed assignment stages and their typed-owner
receipts. Identical replay accepts that receipt across the now-stale original
revisions and resumes only uncommitted stages; changed run, assignment snapshot,
controller identity, digest, or key is rejected before mutation. A partial
result preserves its committed stages, freezes every remaining stage, and
requires authenticated read-back reconciliation; an ambiguous stage is never
repeated until its exact typed owner proves whether it committed. When this
executable typed owner recovery is unavailable, retain the run unchanged and
fail closed.

After resolving any assignment that needs an explicit recovery decision, invoke
the run-wide closeout macro with the run revision observed before its first
stage:

```bash
main-agent closeout \
  --if-run-revision <initial-run-revision> \
  --checkpoint-file <private-final-checkpoint-json> \
  --idempotency-key <stable-closeout-key> \
  --format json
```

Require a `main-agent.closeout-result.v1` projection with
`handoff_ready:true`, `run_closed:true`, `workers_absent:true`,
`cleanup_pending:false`, `provider_session_preserved:true`, no retained
exceptions, and `controller_claim.run_owned_claim_absent:true`. Preserve its
expected, checkpoint, and final run revisions, worker dispositions, claim
disposition, and completed-stage receipt as the bounded proof. The macro owns
the ordered checkpoint, terminal-worker retirement, active-operation fence,
run close, release of only the durably bound run-owned controller claim, and
final read-back. It preserves an unrelated successor claim rather than
releasing it. Here `cleanup_pending:false` covers only run and worker cleanup;
controller cleanup remains the separate retained disposition below.

`handoff_ready:false` is resumable progress. Inspect the typed retained
exceptions, cleanup flag, worker and controller-claim dispositions, and
`progress_receipt.completed_stages`. Resolve only the named condition through
its owner, then replay the identical checkpoint content, original expected run
revision, request, and parent idempotency key. Do not mint a new key after a
stage commits. Missing authenticated controller-claim provenance fails closed
with `controller-claim-provenance-required`; context equality is never an
ownership substitute.

Keep the Main provider session live until the user-facing result or handoff
prompt is delivered.
The session hosting the current response cannot be deleted first and still
complete that response. Physical stop or deletion of the Main provider session
is a later session-owner action after delivery; it is not implied by run close
or controller-claim release.
Because the response-hosting turn has no post-delivery callback, its final
response must explicitly hand off the retained disposition `controller cleanup
pending` to an already-authenticated session-management owner and must not claim
that physical cleanup ran. The trusted released session-management owner must
advertise `session-management.controller-cleanup-handoff.v1` and exact persist
and consume invocations. The persist request writes authenticated, run-bound,
replay-safe `main-agent.controller-cleanup-handoff.v1` state and binds the
producer and recipient-owner identities, run ID and revision, controller
session and incarnation, canonical controller worktree, remaining cleanup
stages, request digest, and idempotency key. It returns authenticated
`session-management.controller-cleanup-handoff-result.v1` with the same digest,
persisted revision, bounded cleanup status, and opaque handoff reference.
Identical persist replay returns the same receipt; altered identity, worktree,
run revision, cleanup stages, digest, recipient, or key fails closed. The later
owner passes that opaque reference, matching run/controller bindings, persisted
revision, and a consume idempotency key to the exact consume invocation. That
owner atomically consumes the handoff reference before the first destructive
stage and returns an authenticated progress receipt containing the request
digest, consume key, original persisted revision, and completed stages.
Identical consume replay returns that receipt and resumes only uncommitted
stages. An interrupted consume after session deletion reconciles exact-session
absence through fresh authenticated identity/list evidence and never repeats
deletion; changed reference, identity, revision, digest, or consume key fails
before mutation. Cleanup requires authenticated result read-back with matching
run/controller bindings and revision. Public final prose exposes only bounded cleanup status and opaque
handoff reference, never a private path or unauthenticated deletion
instruction. In a later authenticated owner turn, after result delivery, that owner must
prove broker zero active and zero uncertain operations, no unfinished typed
lifecycle transition, no unique unpreserved material, and authenticated claim
inventory proving every claim bound to the exact controller session and
incarnation is absent or explicitly transferred/released, including any
unrelated successor claim preserved by closeout; delete the
exact controller session; require a fresh default list to prove exact-session
absence; and remove its clean controller worktree through `git-cli` when no
retained purpose remains. That later owner records the ordinary durable broker,
exact-session deletion, fresh-list, and worktree evidence owned by the
session-management lifecycle. Until a subsequent authenticated read-back proves
every stage, lifecycle cleanup is pending and no owner may claim physical
closeout complete. Missing or ambiguous proof retains the session/worktree and
records the failed stage without repeating deletion.

Folded worker retirement, run close, and work-context release remain diagnostic
and intentional recovery primitives. They are not the normal closeout path and
must not replace an exact replay of an admitted closeout macro.

## Stop And Recovery Matrix

| Condition | Required stop/recovery |
| --- | --- |
| Doctor missing, old, unhealthy, unsupported, malformed, or helper unavailable | Do not activate or launch. Report the bounded provider/version problem; route upgrades or repairs to their owner with required user authority. |
| Doctor says `configured:false` | Run only the converged repair dry-run. Continue only with `configured:true`, `would_change:false`, and no representation conflict; never apply it. |
| Trust/readiness/startup dialog | Do not treat the dialog as ready and do not accept it automatically. Classify and route it or stop for user authority. |
| `readiness_failed`, prompt mismatch, truncation, interference, or no authenticated checkpoint | Treat runtime-owned single-Enter recovery as exhausted or ineligible. Do not resend the prompt or inject another Enter. Preserve `automatic_retry_safe: false`, report `session created, prompt delivery unverified`, and retain the exact worker plus bounded recovery evidence. |
| Candidate conflict before start | Do not start the worker. Narrow the packet or allocate a non-conflicting worktree, then repeat the candidate check. |
| Pre-init Main controller mode is not observed `advisory` | Do not call `init`. Prove exact controller session/incarnation, broker zero active/zero uncertain, no unfinished typed transition, and no unique material; otherwise retain it and fail closed. Then close through its owner, prove fresh-list absence, remove its clean no-purpose worktree through `git-cli`, and restart once in `advisory`. |
| Post-init Main controller mode mismatch with zero assignments | Do not widen the claim or send terminal input. Checkpoint the blocker, use typed closeout when admitted, or preserve broker zero/zero until claim expiry permits authenticated mailbox wakeup. |
| Post-init Main controller mode mismatch with one or more assignments | Freeze launches and Main-owned mutation. Preserve every assignment, worker, claim, worktree, and unique material; reconcile active/uncertain operations only through exact owners. Never use zero-assignment closeout. If typed owner recovery is unavailable, retain the nonzero run unchanged. |
| Fresh-list identity, incarnation, cwd, or mode mismatch | Do not send the task. Retain the new session and report that managed ownership proof failed. |
| Interference or deletion before target claim handoff | Treat ownership proof as failed. Do not recreate, resend, or transfer the target capability; retain durable evidence for explicit recovery. |
| Target claim missing, released, or expired | Stop mutation. The target worker must use its authenticated bootstrap/recovery path and acquire and verify a new active claim before another mutation turn. |
| Submitted lane has no active claim | If the assignment is submitted, the worktree is clean, the provider turn is terminated, and no operation is active or uncertain, proceed with read-only review. Do not renew mutation authority solely to satisfy `claim_renewal_required`; require it only for a later authorized mutation. |
| Work-context scope or worktree conflict | Stop the worker mutation. Narrow/reassign scope or allocate a clean isolated worktree; never acknowledge away a definite conflict as permission. |
| Active or uncertain admitted mutation operation | Retain the exact worker owner/session. Do not retry the mutation, clear/release its claim, delete/reassign the worker, or guess the outcome. Use only hook-retained private authenticated operation material to complete/reconcile a known terminal outcome. If proof is unavailable, report blocked and preserve the session and evidence. |
| Bootstrap-complete exact worker runtime is stopped | Require `post_claim_failure`, `last_proven_safe_state.post_claim_terminalization_safe:true`, and `automatic_retry_safe:false`; run only revision-fenced `worker reconcile-stopped`, verify the typed terminalization result, then retire or create a distinct replacement. Preserve worktree/diff/run/Main and send no input. |
| Post-claim worker runtime is live or unknown, or operation state is active or uncertain | Fail closed. Do not reconcile-stopped, cancel, reassign, retire, resume, send input, stop the runtime, or force group cleanup. Preserve the exact worker and typed refusal. |
| Accepted terminal worker cleanup | Prove operation quiescence, release and verify the worker's active claim, delete the exact session through its owner, then require a fresh list result proving the exact session ID is absent. |
| Pre-init controller startup failed before `main-agent init` | This controller-only recovery requires no run claim or assignment, broker zero active/zero uncertain, no unfinished typed lifecycle transition, no unique unpreserved material, and authenticated claim inventory proving all exact-session/incarnation claims absent or transferred/released. Only the authenticated typed restart-once owner primitive may consume the full immutable request digest before deletion, fresh-list-verify absence, and restart with the bound canonical cwd/worktree, advisory mode, and compact private-packet pointer digest. Identical replay returns its receipt; changed, partial, or ambiguous progress never repeats deletion or restart. Any missing primitive or proof preserves the session. |
| Worker deletion or list-absence failure after logical delete | Keep the worker absent from the default live list, retain its typed maintenance tombstone and structured error with `workers_absent:true` and `cleanup_pending:true`, and route the exact failed physical deletion through the session-management recovery owner. |
| Missing diff, validation, run-state, PR, or completion evidence | Keep the lane incomplete and request the exact missing durable evidence from the same worker. |
| Worker loss or unavailable session | Inspect durable worktree/branch/diff/run-state evidence without reading logs or transcripts. Resume the same owner only when identity and state are proven; otherwise reassign explicitly. |
| Scope drift | Stop acceptance, preserve the diff, and return the out-of-scope work to the same lane for removal or obtain an explicit user-approved scope change before a new packet. |
| Validation or review failure | Do not repair L2/L3 code in the main session. Return findings to the same worker and rerun the complete acceptance loop. |
| Explicit reassignment | Record the reason and durable state, stop or revoke the old lane's write ownership, prove no concurrent owner remains, issue a fresh packet/worktree assignment, and then launch the new worker. |

Worker loss, ambiguity, or impatience never authorizes a second concurrent
writer. Reassignment is a main-agent lifecycle decision, not a worker request.
