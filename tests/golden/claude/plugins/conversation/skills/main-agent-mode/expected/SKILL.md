---
name: main-agent-mode
description: >
  Run an explicit opt-in delivery workflow where one main agent owns the user
  conversation and acceptance while managed workers implement isolated lanes.
---

# Main Agent Mode

## Contract

Prereqs:

- The user explicitly asks to enable or use Main Agent Mode for the bounded
  workflow. Ordinary implementation requests never activate this mode.
- `agent-session >=1.25.11` is installed from a trusted compatible surface.
- The trusted `main-agent` facade from the compatible nils-cli surface is
  executable and advertises the exact runtime-checkpoint and run-wide closeout
  capabilities below.
  The semantic-version floor alone is not sufficient. Until that surface is
  available, report Main Agent Mode as unavailable without repairing or
  restricting ordinary agent work.
- A supported worker provider and executable provider helper pass the doctor
  gate below before mode activation or worker launch.
- The active project intent, work-tier, test-first, validation, review, and
  delivery policies remain authoritative.
- The detailed role, handoff, evidence, acceptance, and recovery protocol is
  available at `references/MAIN_AGENT_MODE_PROTOCOL.md`.

Inputs:

- The accepted request, done criteria, constraints, repository, base ref, and
  work tier.
- The literal worker provider name, `codex` or `claude`, chosen from the
  providers reported as supported by the installed `agent-session` doctor.
- Existing plan, issue, run-state, PR, and worktree references when the tier
  already owns them.
- One private mode-0600 objective packet for a new run, or an authenticated
  durable run relationship that `main-agent rehydrate` can recover.
- An optional explicit `delegate-all` preference for L0/L1 work.

Outputs:

- One main-agent-owned execution and acceptance result for the user.
- One revisioned orchestration run whose assignments, relationships,
  checkpoints, and privacy-safe projections survive compaction and resume.
- Exact task packets and isolated managed worktree assignments for workers.
- Bounded worker completion or blocker packets grounded in diff, validation,
  and durable lifecycle evidence.
- Independent main-agent inspection, validation, code-review synthesis,
  acceptance decisions, and final reporting.

Failure modes:

- Activation was not explicit, or the requested scope/done criteria are not
  sufficiently bounded to delegate safely.
- The installed `agent-session` is missing or older than `1.25.11`.
- The trusted `main-agent` facade is absent, incompatible, untrusted, does not
  advertise `main-agent.runtime-checkpoint-file.v1` and
  `main-agent.run-wide-closeout.v1`, or cannot authenticate the current
  managed-session incarnation.
- Doctor output is unhealthy, unsupported, unavailable, malformed, or reports
  a missing provider helper.
- The bounded compatibility preview is not converged, would change state, or
  exposes a representation conflict.
- Provider readiness, prompt delivery, worker ownership, durable evidence,
  scope, validation, review, or recovery cannot be established.

## Explicit Activation

Activate only after the user says to enable or use Main Agent Mode for the
current workflow. State that the mode is active, its bounded outcome, the
selected worker provider, and whether L0/L1 work is also delegated. Do not infer
activation from an ordinary request to implement, use subagents, work in
parallel, or keep going. Activation does not persist into a later unrelated
request, and an explicit user request to disable the mode takes effect before
any new worker launch.

## Entrypoint

Run the installed version and doctor checks before activating the mode or
launching any worker:

For a Claude worker, run these literal commands:

```bash
agent-session --version
main-agent capabilities --provider claude --format json
main-agent self readiness --format json
agent-session activity doctor --agent claude --format json
```


Require `agent-session >=1.25.11`, a valid
`cli.main-agent.capabilities.v1` envelope with `ok:true`, whose
`data.schema_version` is `main-agent.capabilities.v1` and whose
`data.capabilities.runtime_checkpoint_file` is exactly
`"main-agent.runtime-checkpoint-file.v1"`, whose
`data.capabilities.runtime_hook_checkpoint_write` is exactly
`"runtime-kit.checkpoint-write-admission.v1"`, and whose
`data.capabilities.run_wide_closeout` is exactly
`"main-agent.run-wide-closeout.v1"`, and whose
`data.provider` matches the selected worker provider, and whose
`data.compatible` is `true`. This provider-aware probe reads the deployed `agent-hook`
inventory, requiring bundle version `2026.07.28.1` or newer plus the locked
coordination rules for the selected provider. It also requires that provider's
converged `agent-hook doctor` record and executes its installed
`session-coordination-guard.py` capability self-probe, so a stale or missing
selected-provider handler fails closed without coupling activation to another
provider installation. It therefore rejects either mixed deployment (new CLI
with old policy/handler surfaces, or old CLI with the new runtime surfaces).

Require `main-agent self readiness` to return a valid
`cli.main-agent.self-readiness.v1` envelope with `ok:true`, whose
`data.schema_version` is `main-agent.runtime-readiness.v1`, whose `data.ready`
is `true`, and whose `data.checkpoint_file` is an absolute path. This
per-incarnation gate proves the current managed session received the exact
runtime-issued environment path and still owns a private regular checkpoint
file. `runtime-checkpoint-unavailable` stops activation; resume or restart the
managed session after the compatible surfaces are deployed. Do not run `init`
or any Main Agent mutation from that incarnation.

Also require a valid
`cli.agent-session.activity-doctor.v1` envelope with `ok:true`, exactly one
matching provider record, and `helper_executable:true`.
Require `classification` to be `"supported"` or `"partial"`. Claude reports
`"partial"` permanently because its completion signal is observed rather than
authoritative; that is the audited Claude contract, not drift.
Treat `"unavailable"` and `"unverified"` as a stop. A configured provider must
otherwise be healthy for the selected runtime. Missing fields, extra provider
ambiguity, stale or unparseable output, timeouts, or nonzero exit stop
activation.

When doctor reports `configured:false`, use only the product's literal
non-mutating compatibility probe; never use a shell provider variable in these
readiness commands:

```bash
agent-session activity setup --agent claude --repair --dry-run --format json
```


Accept the compatibility case only when the doctor reports no representation
conflict and the preview is a valid matching-provider converged result with
`compatibility_owner:"agent-hook"`, `configured:true`,
`would_change:false`, and no representation conflict. The preview must not be
applied. Any other result stops the workflow and reports the bounded readiness
problem to the user.

When the hook emits the trusted `builtin command … agent-run inspect` route,
keep its exact canonical outer envelope and provide a nonempty child argv after
`--`. `agent-run inspect` remains the child safety boundary; shell operators,
aliases, or alternate outer option forms are not equivalent readiness routes.

After the provider gate, verify the facade and recover authenticated self state:

```bash
main-agent --version
main-agent self show --format json
```

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
session and incarnation, broker zero active and zero uncertain operations, no
unfinished typed lifecycle transition, and no unique unpreserved material.
Authenticated claim inventory must also prove that every claim bound to that
exact controller session and incarnation is absent or explicitly
transferred/released through its typed owner, including any unrelated successor
claim. Unknown inventory or any surviving claim retains the controller and
fails closed.
Only then close that exact session through its owner, require fresh-list
absence, remove its clean controller worktree with `git-cli` when it has no
retained purpose, and restart once in `advisory` before attempting `init`.
Missing or ambiguous proof retains the session and worktree and fails closed;
never create the run first and promise to repair the mode later.

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

Do not infer a run, role, assignment, or manager from the prompt, title, cwd,
pane, process, or environment flags. The facade's session-ID plus incarnation
relationship is authoritative. If no run exists, create it only through the
exact private-packet bootstrap:

```bash
main-agent init --packet-file <private-json> --if-absent \
  --idempotency-key <unique-key> --format json
```

Under coordination enforcement, read-only `self show`, `rehydrate`, `status`,
`worker list/show/wait/diagnose/supervise`, and the exact bootstrap-safe
`bootstrap` and `self recover` shapes remain available before a claim. The
trusted facade must acquire or confirm the authenticated target-owned claim
before its first ordinary durable run write. Every other facade mutation
requires the active claim plus its documented revision or absence fence and
idempotency key.

## Durable Rehydration And Checkpoints

Treat the `main-agent` run and assignment records as the authoritative workflow
relationship and recovery surface. Issue, plan, worktree, diff, validation,
review, and provider records remain authoritative for their own domains and are
linked from the run; the orchestration graph never replaces them or grants
mutation authority.

At activation, after provider resume or context reset, and whenever local
workflow state may be stale, run:

```bash
main-agent rehydrate --format json
```

Use the returned durable revision, constraints, done criteria, assignments,
checkpoint, blockers, and next action. Keep observation-time annotations
separate from the deterministic durable projection. Before handing off a
material transition and after accepting a worker result, persist a bounded
checkpoint through a private file:

```bash
main-agent checkpoint --file <private-json> --if-revision <n> \
  --idempotency-key <unique-key> --format json
```

For a managed worker, use only the exact `checkpoint_file` returned by its
authenticated `main-agent bootstrap`; the runtime pre-creates that
session/incarnation-bound file outside the checkout at mode `0600`. Write the
bounded JSON object there, then pass the same literal path to `--file`. For the
Main Agent's own checkpoint, use its runtime-issued
`AGENT_SESSION_CHECKPOINT_FILE`. Never allocate an arbitrary worker checkpoint
path under the repository or a project output tree.

At safe turn or tool boundaries, give Main Agents and workers only a concise
privacy-safe reminder that durable state is available through `main-agent
rehydrate` or `main-agent self show`. Do not repeat the private task packet,
block unrelated safe work, detect compaction heuristically, or expose private
paths, capabilities, prompts, transcripts, or mailbox bodies.

## Outcome Routing

Classify the request before choosing workers. Main Agent Mode changes
implementation ownership, not the tier:

- L0/L1 remain inline unless the user requests `delegate-all`; when delegated,
  use one isolated managed worker and keep the same parent outcome.
- L2 retains the plan-tracking parent, but the main agent does not implement or
  repair production or test code. One interactive managed worker owns the
  implementation in an isolated managed worktree launched with
  `--coordination-mode enforce`.
- L3 retains exact independent lane workers and the dispatch orchestrator
  acceptance boundary. The mode does not merge lanes or collapse their
  worktrees, PRs, reviews, validation, or closeout.

For L2/L3, main-agent writes are limited to orchestration, plan/run-state,
evidence, review synthesis, and authorized provider lifecycle actions. Return
code findings to the same worker and lane unless the main agent records an
explicit reassignment under the recovery protocol.

## Workflow

1. Confirm explicit activation, bounded done criteria, worker provider, tier,
   and any L0/L1 `delegate-all` preference.
2. Pass the version, doctor, and conditional dry-run compatibility gates. Do
   not launch a worker while readiness is uncertain.
3. Run authenticated `main-agent self show`. Rehydrate an existing run and
   reconcile it with durable issue/plan/run-state/worktree evidence; never
   create a second run merely because local conversation context is missing.
4. Immediately before any no-run `main-agent init` branch, execute the exact
   list-plus-runtime-observation gate defined in Entrypoint. Continue to the
   private-packet `init` only when both authenticated projections bind the same
   exact controller and prove fresh runtime-observed `advisory`; otherwise fail
   closed without creating durable run state.
5. Create one revision-fenced assignment per implementation owner through the
   facade. Each private packet names a repository, non-overlapping scope,
   invariants, exclusions, base, isolated managed worktree, test-first and
   validation duties, delivery artifact duties, and the exact
   completion/blocker packet. The Main Agent claim must not overlap a worker
   scope. For a mutating worker, the packet `worktree`, `launch.cwd`, durable
   assignment worktree, and authenticated worker cwd must resolve to the same
   canonical checkout root before bootstrap can mint its shell grant. Keep
   worker path scopes narrow; do not add repository scope merely so
   the worker can run tests, validation, delivery, or checkpoint commands.
   Authenticated worker bootstrap mints a private checkout-shell grant on the
   exact assignment-derived claim; admission also requires the matching
   repository and worktree fingerprint. This grant is checkout-level
   coordination, not a path sandbox: reject final diffs outside the assigned
   scopes. The assignment relationship is routing metadata and
   transfers no repository or provider authority. When a packet declares `depends_on`, every
   named assignment must belong to the same run and already be `accepted` or
   `released` before launch. On `dependency-not-satisfied`, no dependent
   assignment was created: wait boundedly for each upstream assignment's
   terminal transition, re-read it, and retry the unchanged launch only after
   every dependency is accepted or released. Missing, cross-run, cancelled, or
   other pre-terminal dependencies remain blocking.
6. Run the candidate conflict check, then prefer the folded readiness boundary:

   ```bash
   main-agent worker start --assignment-file <private-json> --await-ready 5m \
     --idempotency-key <unique-key> --format json
   ```

   The assignment itself must request the isolated worktree and
   `--coordination-mode enforce`.
7. Branch only on the returned typed readiness. Continue immediately only for
   `state:"ready"`, `delivery.state:"confirmed"`, and
   `delivery.proof:"authenticated-worker-checkpoint"`. For a fresh supported
   worker whose assignment remains `starting`, the folded runtime may submit
   exactly one recovery Enter within the original wait deadline after rechecking
   the exact session incarnation and live runtime. Before input, a privacy-safe
   observation must prove the exact already-delivered prompt at an idle
   composer, the broker must prove zero active and zero uncertain operations,
   and the observation must classify the surface as an ordinary provider
   composer rather than a trust, authentication, account, permission, secret,
   provider-mutation, startup-dialog, or unknown state. The typed result must
   expose those eligibility proofs and `input_sent:true`; stale, partial,
   malformed, or ambiguous proof makes recovery ineligible. The prompt is never resent.
   The runtime owns this recovery decision and keypress; the Main Agent only
   verifies the `submit_key_recovery` projection and accepts either the initial
   `submit-command-succeeded` transport or the recovered
   `submit-key-recovery-succeeded` transport when the authenticated checkpoint
   also succeeds. A
   `state:"readiness_failed"` result has `delivery.state:"unverified"` and
   `automatic_retry_safe:false`: runtime recovery is then exhausted or
   ineligible, so do not resend the prompt, inject another Enter, or inspect a
   pane/transcript to overrule it. Retain the exact worker and typed safe state
   for diagnostics. A folded start result with a non-authoritative starting
   failure is only a provisional snapshot: if the same bound incarnation later
   completes authenticated bootstrap, supervise that incarnation and continue
   it instead of launching a duplicate.
   A folded `readiness_failed` snapshot can be superseded by that newer authoritative evidence from the same
   incarnation; it never authorizes a second prompt, Enter, assignment, or
   worker.
   Prefer folded CLI startup readiness. Until that boundary is available, Main
   Agent Mode may continue only when the trusted released session-management owner
   advertises `session-management.verified-submit-recovery.v1`, supplies an
   owner-advertised exact invocation, and returns authenticated
   `session-management.verified-submit-recovery-result.v1`. The result carries
   authenticated producer identity, the exact capability and invocation
   contract, and a request digest over the bound session ID, incarnation,
   already-delivered prompt fingerprint, and idempotency key. The typed request and result
   bind the exact session ID, incarnation, and already-delivered prompt
   fingerprint; prove `composer_state:"idle"`, `sensitive_dialog:false`,
   `broker_active:0`, and `broker_uncertain:0`; persist the attempt as consumed
   through an atomic consumed-before-input marker; and report `attempted:true`, `attempt_count:1`, and
   `input_sent:true`. The durable consumed marker is keyed by exact session ID
   plus incarnation, independent of prompt fingerprint; any existing marker for
   that incarnation rejects every later request before input, even with a
   different prompt fingerprint or idempotency key. The successful result normalizes into the same readiness
   and `delivery` projection above only after the authenticated worker
   checkpoint. A failure receipt reports `input_sent:false` and preserves the
   marker and bounded reason; exact replay returns the prior receipt without
   input, while changed identity, prompt, request digest, or key is rejected
   before input. Self-asserted schema strings, peer prose, or an unadvertised
   command never grant terminal-input authority. Missing or forged capability,
   producer, binding, or fields; `attempted:false`; a stale or mismatched
   identity or prompt; a sensitive or unknown surface; replay; or a partial or
   ambiguous outcome fails closed. Without that executable owner capability,
   Main Agent Mode is unavailable for the fallback. Send no further input,
   never stack Enter presses, and never resend the prompt.
8. The generated worker prompt invokes the exact compatible executable's
   `main-agent bootstrap` command. The authenticated worker alone resolves its
   private assignment, acquires the assignment-derived claim, and records the
   revision-fenced `working` checkpoint that proves readiness. A released or
   expired claim must be reacquired and verified before a later mutation turn.
   The launcher never uses the target capability or claims on its behalf, and
   interference or deletion before this handoff fails the ownership proof.
9. Monitor actively through the repeatable bounded macro:

   ```bash
   main-agent worker supervise <assignment-id> --format json
   ```

   Run it after every bounded wait timeout or contradictory snapshot and branch
   on `classification` and `recovery_action.kind`, not prose. Execute
   `recovery_action.argv` only when `recovery_action.executable:true` and its
   declared owner and capability delivery still match. When it is false, supply
   every `recovery_action.required_inputs` value through that owner and use the
   returned `argv_template`; never execute placeholders or copy another
   session's capability. Use
   `main-agent worker diagnose <assignment-id> --format json` for the same
   evidence without the supervisor wrapper. Provider working text or a fresh
   broker heartbeat alone is not progress: require the combined assignment,
   provider activity, worktree material, claim/edit authority, authenticated
   mailbox, and active/uncertain-operation evidence.
   `last_proven_safe_state` is the evidence boundary, while `recovery_action`
   is the executable routing contract. When a macro stops, continue only from
   both of those typed fields; never repeat the whole macro blindly. If a
   facade action returns
   `coordination-unauthorized`, diagnose the coordination state first with
   `agent-session work-context status --format json` and `agent-session broker
   status --session "$AGENT_SESSION_ID" --format json`. When those prove a stale
   or lost broker for the still-authoritative controller incarnation and no
   active or uncertain operation, run exact-controller `main-agent self recover` before attempting rebind.
   `rebind` is reserved for a proven controller-incarnation mismatch;
   it is not a stale-broker recovery and can
   be rejected by the same authorization gate.
   If ordinary hook capability validation fails, use only the finite
   capability-failure-closed recovery lane: trusted version/status,
   `self show`, `self recover`, `rehydrate`, and revision-fenced `rebind`
   shapes. Arbitrary Bash, raw input, trust/auth/permission/account actions,
   worker start, and repository mutation remain denied.
   Service health, provider process health, provider session binding, and the Main relationship are four distinct states.
   A healthy service restart does not repair a stale provider binding. With
   explicit user authorization, use the typed provider restart-resume action
   when available; otherwise gracefully stop the provider, run
   `agent-session resume <session-id> --format json`, prove a new generation
   and incarnation, revision-fence `rebind`, then re-read `self show`. Preserve
   thread, account binding, repository/worktrees, workers, and the durable run.
   Verify post-rebind assignment ownership before worker actions. Use a folded
   rebind-and-adopt result when exposed; otherwise revision-fence `adopt` only
   for assignments still bound to the exact prior run controller.
   Stable dirty material, a renewed claim, a heartbeat, or provider `working`
   text is not progress. When material fingerprints, provider
   `last_progress_at`, assignment/checkpoint revision time, mailbox state, and
   operation state do not advance, stable dirty material plus stale provider progress is stalled
   or attention-required, including capacity failures. Do not classify it as
   healthy progress, and do not renew edit authority indefinitely without new
   authoritative progress.
   When supervision proves that an assignment completed authenticated
   bootstrap into `working`, the exact bound worker runtime is stopped, the
   worker session and incarnation are unchanged, and no admitted operation is
   active or uncertain, require `classification:"post_claim_failure"`,
   `last_proven_safe_state.post_claim_terminalization_safe:true`,
   `automatic_retry_safe:false`, and
   `recovery_action.kind:"stopped_worker_terminalization"`.
   Require the public `main-agent.worker-diagnose-result.v2`,
   `main-agent.worker-supervise-result.v2`, and
   `main-agent.worker-recovery-action.v2` schemas; v1 projections are stale.
   Require exactly
   `recovery_action.required_inputs:["terminalization_reason","idempotency_key"]`;
   a third input fails closed. Resolve both values through the declared Main
   owner and use the returned `recovery_action.argv_template`.
   A live or unknown runtime, or any active or uncertain operation must fail closed.
   Run only the revision-fenced, idempotent typed action:

   ```bash
   main-agent worker reconcile-stopped <assignment-id> \
     --if-revision <assignment-revision> \
     --reason <bounded-terminalization-reason> \
     --idempotency-key <unique-key> --format json
   ```

   Require a `main-agent.worker-reconcile-stopped-result.v2` result with
   `terminalized:true`, top-level `worker_claim_active_after:false`,
   `input_sent:false`, `worktree_preserved:true`, and
   `proof.worker_claim:{active_disposition:"absent",release_provenance:"not_attributed_to_attempt",observed_at_stage1:<bool>}`.
   Claim absence is stable observed truth; never attribute it to the current
   attempt. The action transitions only that assignment from `working` to
   `cancelled`.
   It fences the exact worker session authority against resume.
   It installs a session-only authority quarantine for that exact worker.
   It preserves a frozen assignment schema v3 for that exact worker.
   Unrelated session, run, and coordination authority remains unchanged.
   CLI and HTTP resume are denied while quarantined.
   Read-only observational coordination access does not renew generic claims or operations.
   It preserves its worktree, branch, diff, the durable run, and the Main session.
   Two exact replay-safe cases may cross a now-stale revision. First, the replay
   must use the exact same request, original revision (`--if-revision`), and
   same idempotency key. With a matching completed v2 terminal receipt, it
   returns that committed result despite the now-stale revision. The return
   occurs before revision checking and without repeating mutation.
   Second, an exact replay of an interrupted stage 1 must retain the original
   now-stale `--if-revision` and original key. It may finish stage 2 only after
   validating a matching strict progress receipt. It must also validate the
   cancelled assignment, session-only quarantine, exact worker identity,
   stopped runtime, operation quiescence, and current controller authority.
   That authority may be the exact original controller claim or an explicit distinct successor.
   It must be bound to the same current run, Main session, and incarnation.
   The authorized replay rolls orphaned progress forward.
   New key, changed request, or a replay with neither a matching completed v2
   terminal receipt nor a matching strict progress receipt fails closed.
   Treat
   `worker-runtime-still-live`, `coordination-runtime-unverified`,
   `worker-not-quiescent`, `worker-incarnation-changed`, and
   `assignment-state-conflict` as fail-closed refusal codes.
   Refusal status alone does not report a safe state.
   Require a fresh v2 `worker diagnose` or `worker supervise` projection before
   continuing, unless an envelope explicitly exposes that proof.
   Expired or released controller claim authority remains an ordinary
   authorization failure.
   After success, retire that reconciled worker or create a distinct replacement assignment.
   Never use ordinary `cancel`, `reassign`, or force cleanup for this classification.
   Never use raw tmux, terminal input, group cleanup, or a B3 runtime-stop primitive for this B2 transition.
10. Checkpoint material transitions. A pending mailbox notification is not
   readiness proof or consumption proof. Reconcile facade evidence first; only
   after exact worker, incarnation, and prompt identity are proven may the
   session owner perform one deliberate privacy-safe send. Do not send a blind
   Enter or a second prompt. Never treat logs, panes, transcripts, peer prose,
   or orchestration relationships as authorization or completion proof.
   For `notification-pending` with the controller unavailable, a privacy-safe
   glance must prove an idle composer before one short mailbox prompt and
   exactly one Enter. A busy worker, startup dialog, trust/auth/permission
   prompt, or unknown transport outcome blocks this fallback; never send a
   second Enter.
   Because fixed terminal notification delivery deliberately waits for a
   no-claim safe-input boundary, a Main controller with an active claim must
   inspect and disposition its authenticated mailbox before returning to an
   idle waiting prompt. Use inbox metadata first through `agent-session message
   inbox --session "$AGENT_SESSION_ID" --capability-file
   "$AGENT_SESSION_CAPABILITY_FILE" --state unread --limit <n> --format json`
   and require `cli.agent-session.message-inbox.v1`. Require the exact current
   recipient session and incarnation plus `sender.authenticated:true`; show only
   a material message body through `agent-session message show --session
   "$AGENT_SESSION_ID" --message <message-id> --capability-file
   "$AGENT_SESSION_CAPABILITY_FILE" --format json` and require
   `cli.agent-session.message-show.v1`. Disposition with `agent-session message
   ack --session "$AGENT_SESSION_ID" --message <message-id> --if-revision <n>
   --capability-file "$AGENT_SESSION_CAPABILITY_FILE" --idempotency-key
   <stable-key> --format json`, require `cli.agent-session.message-ack.v1`, and
   bind the revision-CAS and stable idempotency key to that exact message. A
   forged sender, wrong recipient or incarnation, stale revision, or
   non-material message fails closed without body access or authority change.
   Do not release or widen the claim, send terminal input, or infer message
   consumption merely to trigger that notification.
11. On a worker result, independently inspect the complete diff, check every
   acceptance criterion and scope boundary, rerun validation at the appropriate
   strength, and run the existing `code-review-specialists` outcome. A worker's
   green command is lane evidence, not integrated acceptance.
12. Until a dedicated submit macro exists, the worker submits only through a
    revision-fenced checkpoint with `state:"submitted"`. Return bounded review
    findings to that exact lane with manager-only, revision-fenced
    `main-agent worker request-changes`; it changes only `submitted` to
    `working`, preserves the worker and private packet, clears stale result and
    blocker summaries, and records the reason as the next action. The transition
    does not send review guidance, provider input, or re-arm auto-resume. Send
    the private findings separately with `main-agent worker message`, then
    supervise notification and consumption through the existing mailbox rules.
    Do not create a duplicate assignment merely because the submitted provider
    turn ended; account-handoff auto-resume remains reserved for its typed quota
    recovery contract. Repeat inspection and validation on the worker's next
    submitted revision, and never falsely accept rejected work.
    A submitted assignment with a released claim, clean worktree, terminated provider turn, and no
    active or uncertain operation is ready for read-only review;
    do not renew mutation authority merely because supervision reports
    `claim_renewal_required`.
    A durable blocked hold must preserve the full goal and unfinished checklist.
    Do not reinvoke an identical Stop action while the unchanged blocking fingerprint
    has no executable recovery capability. Resume only after new user input,
    changed external state, or a verified recovery transition.
13. Use revision-fenced typed macros for recovery: `self recover`, `worker
    start`, `worker supervise`, `guidance-reconcile`,
    `guidance-quarantine`, `account-handoff`, `account-handoff-cancel`,
    `reconcile-stopped`, `cancel`, `reassign`, `accept`, and `retire`. Account
    selection, exact incumbent account binding, and structured auto-resume
    re-arm are separate transitions; account binding is verified before
    structured auto-resume is re-armed.
    Never use `/logout` or raw terminal input to switch accounts.
    A capability gap on an unmanaged/raw worker requires the typed executable
    lifecycle fallback, not a daemon-only recovery claim.
14. Retire an accepted terminal worker only after the facade and
    session-management owner prove no active or uncertain operation remains,
    the exact worker releases its claim, the durable logical-delete boundary
    commits, and a fresh default list proves exact-incarnation absence. A
    committed logical delete removes the worker from the default live-worker
    list. Facade logical live-worker absence is not physical session-owner
    absence: a tombstone or default facade list cannot prove that the provider
    session was deleted. Keep any later physical cleanup failure as a typed maintenance
    tombstone in the maintenance projection, set `workers_absent:true` for the
    logical list and `cleanup_pending:true` until physical recovery and fresh
    list-absence proof succeed, and make identical replay return that same
    tombstone. A stopped or rejected session whose assignment was never
    accepted is not directly deletable: preserve its work and use typed
    recovery for its proven classification. In particular,
    `post_claim_failure` must pass through `reconcile-stopped` before retirement
    or a distinct replacement.
15. Checkpoint and close the run only when assignments are terminal or carry an
    explicit retained exception and the active tier's durable gates pass.
    Accept, merge, archive, and report only when provider delivery is available;
    otherwise retain the bounded local result and state exactly what remains.

Trust, authentication, account choice or change, permission elevation, secret
access, provider or other external mutation, and every non-quiescent or unknown
operation remain explicit authority boundaries. Startup transport recovery and
resource closeout never authorize them and always fail closed when their state
is present or uncertain.

## Run Closeout And Handoff

The Main Agent owns run closeout; a user-facing result does not by itself close
the durable run or release its coordination authority. Before ending or handing
off a Main Agent Mode workflow:

1. Give every Main Agent Mode controller, worker, provider session, and managed
   worktree a final disposition. Never close or delete an owner with an active
   or uncertain operation, an unfinished assignment without a safe typed
   transition, unique unpreserved material, or the only recovery evidence.
   Reconcile any worker that still needs an explicit typed recovery decision.
   When the run is terminal-ready, retain its current revision, write one
   private final checkpoint file, choose one stable parent idempotency key, and
   invoke the run-wide macro:

   ```bash
   main-agent closeout \
     --if-run-revision <initial-run-revision> \
     --checkpoint-file <private-final-checkpoint-json> \
     --idempotency-key <stable-closeout-key> \
     --format json
   ```

2. Require `main-agent.closeout-result.v1` with `handoff_ready:true`,
   `run_closed:true`, `workers_absent:true`, `cleanup_pending:false`,
   `provider_session_preserved:true`, an empty `retained_exceptions`, and
   `controller_claim.run_owned_claim_absent:true`. Retain
   `expected_run_revision`, `checkpoint_revision`, `final_run_revision`,
   `worker_dispositions`, and `progress_receipt.completed_stages` as the
   bounded closeout proof. Here `cleanup_pending:false` covers only run and
   worker cleanup; controller cleanup remains the separate retained disposition
   below.
3. `handoff_ready:false` is a resumable partial result, not permission to
   improvise cleanup. Inspect only its typed `retained_exceptions`,
   `cleanup_pending`, worker dispositions, controller-claim disposition, and
   completed stages. Resolve the named worker, operation, or maintenance
   condition through its owner, then replay the identical checkpoint content,
   original run revision, request, and parent idempotency key. Do not choose a
   new key after a stage commits. A pre-provenance run that returns
   `controller-claim-provenance-required` remains incomplete; never infer claim
   ownership from matching context.
4. A zero-assignment pre-launch-blocked run may checkpoint a zero-assignment blocker
   and use run-wide closeout when terminal-ready. Its checkpoint must preserve
   the objective and blocker and must not claim that the product objective
   completed. A post-init controller-mode mismatch follows this bounded route:
   never widen the Main claim into worker scopes or stack terminal input;
   checkpoint the blocker and use typed closeout when admitted. If closeout is
   not admitted, preserve broker zero active/zero uncertain state until claim
   expiry permits authenticated mailbox wakeup, then resume only through the
   typed owner path.
   A post-init wrong-mode incident with one or more assignments is different:
   freeze every new launch and Main-owned mutation, preserve every worker,
   claim, worktree, and unique material, and reconcile active or uncertain
   operations only through their exact owners. Never use zero-assignment
   closeout for a nonzero run. Assignments in `starting`, `working`,
   `submitted`, and `accepted` remain in their current typed lifecycle until a
   trusted owner recovery proves the exact safe transition. Recovery requires
   the released facade to advertise
   `main-agent.nonzero-wrong-mode-recovery.v1` with its exact owner-supplied
   invocation and return authenticated
   `main-agent.nonzero-wrong-mode-recovery-result.v1`. Its revision-CAS request
   binds the controller session and incarnation, canonical cwd, run ID and
   revision, immutable assignment ID/revision/state snapshot, broker
   active/uncertain projection, request digest, and idempotency key. The result
   binds the same digest and records one typed-owner receipt per assignment:
   `starting` may move only through worker-start reconciliation, `working` only
   through worker checkpoint/supervision, `submitted` only through manager
   review, and `accepted` is preserved unchanged. It also returns the durable
   post-recovery run revision and authenticated read-back. Before the first
   assignment mutation, the owner durably consumes a progress marker keyed by
   the full request digest, original run and assignment revisions, and
   idempotency key. Its authenticated progress receipt records completed
   assignment stages and their typed-owner receipts. Identical replay accepts
   that receipt across the now-stale original revisions and resumes only
   uncommitted stages; changed run, assignment snapshot, controller identity,
   digest, or key is rejected before mutation. A partial result preserves its
   committed stages, freezes every remaining stage, and requires authenticated
   read-back reconciliation; an ambiguous stage is never repeated until its
   exact typed owner proves whether it committed. When this executable typed
   owner recovery is unavailable, retain the run unchanged and fail closed.
5. Keep the Main provider session live until the user-facing result or handoff
   prompt is delivered.
   Physical provider-session stop or deletion is a later session-owner action;
   the Main Agent must not terminate the transport that still owes the user its
   final response.
   Because the response-hosting turn has no post-delivery callback, its final
   response must explicitly hand off the retained disposition `controller
   cleanup pending` to an already-authenticated session-management owner and
   must not claim that physical cleanup ran. The trusted released
   session-management owner must advertise
   `session-management.controller-cleanup-handoff.v1` and exact persist and
   consume invocations. The persist request writes authenticated, run-bound,
   replay-safe `main-agent.controller-cleanup-handoff.v1` state and binds the
   producer and recipient-owner identities, run ID and revision, controller
   session and incarnation, canonical controller worktree, remaining cleanup
   stages, request digest, and idempotency key. It returns authenticated
   `session-management.controller-cleanup-handoff-result.v1` with the same
   digest, persisted revision, bounded cleanup status, and opaque handoff
   reference. Identical persist replay returns the same receipt; altered
   identity, worktree, run revision, cleanup stages, digest, recipient, or key
   fails closed. The later owner passes that opaque reference, matching
   run/controller bindings, persisted revision, and a consume idempotency key to
   the exact consume invocation. That owner atomically consumes the handoff
   reference before the first destructive stage and returns an authenticated
   progress receipt containing the request digest, consume key, original
   persisted revision, and completed stages. Identical consume replay returns
   that receipt and resumes only uncommitted stages. An interrupted consume
   after session deletion reconciles exact-session absence through fresh
   authenticated identity/list evidence and never repeats deletion; changed
   reference, identity, revision, digest, or consume key fails before mutation.
   Cleanup requires authenticated result read-back with matching run/controller
   bindings and revision.
   Public final prose exposes only bounded cleanup status and opaque handoff
   reference, never a private path or unauthenticated deletion instruction.
   In a later authenticated owner turn, after
   result delivery, that owner must prove broker zero active and zero uncertain
   operations, no unfinished typed lifecycle transition, no unique
   unpreserved material, and authenticated claim inventory proving every claim
   bound to the exact controller session and incarnation is absent or explicitly
   transferred/released, including any unrelated successor claim preserved by
   closeout; delete the exact controller session; require a fresh
   default list to prove exact-session absence; and remove its clean controller
   worktree through `git-cli` when no retained purpose remains. That later owner
   records the ordinary durable broker, exact-session deletion, fresh-list, and
   worktree evidence owned by the session-management lifecycle. Until a
   subsequent authenticated read-back proves every stage, lifecycle cleanup is
   pending and no owner may claim physical closeout complete. Missing or
   ambiguous proof retains the session/worktree and records the failed stage
   without repeating deletion.

`worker retire`, `main-agent close`, and `work-context release` remain
diagnostic and intentional recovery primitives. They are not the normal
closeout path and must not replace exact replay of an admitted closeout macro.

## Boundary

- This skill exists only on supported managed runtimes with the required hook
  runner and enforced interactive-session and acceptance boundary; unsupported
  runtimes have no managed Main Agent Mode surface.
- It consumes compatible deterministic `agent-session` primitives and existing
  tier/review/delivery outcomes. It adds no runtime graph, provider-specific
  orchestration engine, or provider transport command.
- Concrete provider transport mechanics remain runtime-owned. Main Agent Mode
  prefers `worker start --await-ready` and its typed authenticated checkpoint
  proof, including the bounded `submit_key_recovery` result. Until folded
  startup is available, it consumes only the advertised session-management
  owner's typed, one-attempt, per-incarnation verified-submit result defined
  above; it never implements provider-specific paste, keypress, or pane
  heuristics or consumes an untyped result.
- Main Agent Mode never repairs trust, authentication, configuration, hooks,
  updates, permissions, or services. The dry-run compatibility probe is the
  only readiness fallback, and it never authorizes apply.
