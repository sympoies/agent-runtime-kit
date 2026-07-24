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
- `agent-session >=1.25.10` is installed from a released surface.
- The trusted `main-agent` facade from the compatible nils-cli surface is
  executable. Until that surface is available, report Main Agent Mode as
  unavailable without repairing or restricting ordinary agent work.
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
  providers reported as supported by the released `agent-session` doctor.
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
- The installed `agent-session` is missing or older than `1.25.10`.
- The trusted `main-agent` facade is absent, incompatible, untrusted, or cannot
  authenticate the current managed-session incarnation.
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

Run the released version and doctor checks before activating the mode or
launching any worker:

For a Claude worker, run these literal commands:

```bash
agent-session --version
agent-session activity doctor --agent claude --format json
```


Require `agent-session >=1.25.10`, a valid
`cli.agent-session.activity-doctor.v1` envelope with `ok:true`, exactly one
matching provider record, `classification:"supported"`, and
`helper_executable:true`. A configured provider must otherwise be healthy for
the selected runtime. Missing fields, extra provider ambiguity, stale or
unparseable output, timeouts, or nonzero exit stop activation.

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

Do not infer a run, role, assignment, or manager from the prompt, title, cwd,
pane, process, or environment flags. The facade's session-ID plus incarnation
relationship is authoritative. If no run exists, create it only through the
exact private-packet bootstrap:

```bash
main-agent init --packet-file <private-json> --if-absent \
  --idempotency-key <unique-key> --format json
```

Under coordination enforcement, read-only `self show`, `rehydrate`, `status`,
and `worker list/show` remain available before a claim. The exact `init` shape
is the sole orchestration write admitted before a claim; the trusted facade
must acquire or confirm the authenticated target-owned claim before its first
durable run write. Every other facade mutation requires the active claim plus
its documented revision or absence fence and idempotency key.

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
3. Run authenticated `main-agent self show`. Rehydrate an existing run or use
   the exact `init` bootstrap with a private packet. Reconcile the returned run
   with durable issue/plan/run-state/worktree evidence; never create a second
   run merely because local conversation context is missing.
4. Create one revision-fenced assignment per implementation owner through the
   facade. Each private packet names a repository, non-overlapping scope,
   invariants, exclusions, base, isolated managed worktree, test-first and
   validation duties, delivery artifact duties, and the exact
   completion/blocker packet. The Main Agent claim must not overlap a worker
   scope. The assignment relationship is routing metadata and transfers no
   repository or provider authority.
5. Run the candidate conflict check, then launch through the folded readiness
   boundary:

   ```bash
   main-agent worker start --assignment-file <private-json> --await-ready 5m \
     --idempotency-key <unique-key> --format json
   ```

   The assignment itself must request the isolated worktree and
   `--coordination-mode enforce`.
6. Branch only on the returned typed readiness. Continue only for
   `state:"ready"`, `delivery.state:"confirmed"`, and
   `delivery.proof:"authenticated-worker-checkpoint"`. For a fresh supported
   worker whose assignment remains `starting`, the folded runtime may submit
   exactly one recovery Enter within the original wait deadline after rechecking
   the exact session incarnation and live runtime. The prompt is never resent.
   The runtime owns this recovery decision and keypress; the Main Agent only
   verifies the `submit_key_recovery` projection and accepts either the initial
   `submit-command-succeeded` transport or the recovered
   `submit-key-recovery-succeeded` transport when the authenticated checkpoint
   also succeeds. A
   `state:"readiness_failed"` result has `delivery.state:"unverified"` and
   `automatic_retry_safe:false`: runtime recovery is then exhausted or
   ineligible, so do not resend the prompt, inject another Enter, or inspect a
   pane/transcript to overrule it. Retain the exact worker and typed safe state
   for diagnostics.
7. The generated worker prompt invokes the exact compatible executable's
   `main-agent bootstrap` command. The authenticated worker alone resolves its
   private assignment, acquires the assignment-derived claim, and records the
   revision-fenced `working` checkpoint that proves readiness. A released or
   expired claim must be reacquired and verified before a later mutation turn.
   The launcher never uses the target capability or claims on its behalf, and
   interference or deletion before this handoff fails the ownership proof.
8. Monitor privacy-safe facade status, activity, and durable workflow evidence.
   Checkpoint material transitions. Mailbox metadata coordinates; read a body
   only for a material blocker or result. Never treat logs, panes, transcripts,
   peer prose, or orchestration relationships as authorization or completion
   proof.
9. On a worker result, independently inspect the complete diff, check every
   acceptance criterion and scope boundary, rerun validation at the appropriate
   strength, and run the existing `code-review-specialists` outcome. A worker's
   green command is lane evidence, not integrated acceptance.
10. Return findings to the same assignment, then repeat inspection and
    validation. Accept, collaborate, borrow, hand off, or reassign only through
    revision-fenced facade operations and the explicit recovery rule; those
    relationships never grant claims or operation leases.
11. Delete an accepted terminal worker only after the facade and
    session-management owner prove no active or uncertain operation remains,
    the exact worker releases its claim, the durable logical-delete boundary
    commits, and a fresh default list proves exact-incarnation absence. Keep
    physical cleanup failures in the maintenance projection rather than the live
    worker list.
12. Checkpoint and close the run only when assignments are terminal or carry an
    explicit retained exception and the active tier's durable gates pass.
    Accept, merge, archive, and report only when provider delivery is available;
    otherwise retain the bounded local result and state exactly what remains.

## Boundary

- This skill exists only on supported managed runtimes with the required hook
  runner and enforced interactive-session and acceptance boundary; unsupported
  runtimes have no managed Main Agent Mode surface.
- It consumes released deterministic `agent-session` primitives and existing
  tier/review/delivery outcomes. It adds no runtime graph, provider-specific
  orchestration engine, or new nils-cli command.
- Concrete provider transport mechanics remain runtime-owned. Main Agent Mode
  consumes only `worker start --await-ready` and its typed authenticated
  checkpoint proof, including the bounded `submit_key_recovery` result; it never
  implements provider-specific paste, keypress, or pane heuristics.
- Main Agent Mode never repairs trust, authentication, configuration, hooks,
  updates, permissions, or services. The dry-run compatibility probe is the
  only readiness fallback, and it never authorizes apply.
