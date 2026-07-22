# Main Agent Orchestration Runtime Implementation Handoff

- **Status**: ready for local implementation
- **Date**: 2026-07-22
- **Source**: `discussion-to-implementation-doc` capture of the Main Agent Mode
  workflow, durable recovery, managed-worker relationship, and Agent Console UX
  discussion.
- **Intended next step**: a new Main Agent implements the cross-repository
  contract locally in `sympoies/nils-cli`, `graysurf/agent-runtime-kit`, and
  `serenvia/agent-console`. Do not open a plan issue, issue, PR, or GitHub
  Actions run while the active GitHub account restriction remains in effect.

## Purpose

Turn Main Agent Mode from a prompt/protocol-only workflow into a recoverable
managed orchestration surface without reducing agent capability.

The implementation must let a Main Agent recover its objective, done criteria,
constraints, checkpoints, and managed workers after context compaction or
session resume. Each managed worker must recover its own assignment and primary
relationship. Agent Console must render those relationships from authoritative
runtime data rather than infer them from titles, prompts, cwd, or terminal
content.

The relationship model is for workflow ownership, attribution, routing, and UI.
It is not an access-control graph. A worker may still coordinate with or assist
another Main Agent. Existing work-context claims, scope conflict evaluation,
operation leases, repository policy, user authority, provider consent, and OS
controls remain the mutation boundaries.

## Confirmed Facts

- `agent-session` session records persist identity, provider, mode,
  coordination mode, title, cwd, timestamps, provider-resume data, and runtime
  data, but no orchestration run, role, manager, or assignment relationship.
  Public views add incarnation, status, resumability, activity, startup,
  account, and coordination projections, but still no durable Main Agent
  relationship. [F1]
- Work-context claims carry a bounded summary, repository, provider, plan,
  scope, and worktree information. They are expiring collision/admission
  resources, not durable task or orchestration records. Their `summary` is
  limited to 240 UTF-8 bytes and must not be repurposed for the full user
  request or recovery packet. [F2]
- The current Main Agent Mode protocol treats issue/plan/run-state, worktree,
  diff, validation, review, and provider read-back as durable truth, while task
  packets and manager/worker relationships remain procedural. [F3]
- The current Main Agent Mode boundary explicitly says it adds no runtime graph
  and no new nils-cli command. This implementation intentionally replaces that
  boundary with an additive orchestration contract. [F4]
- Agent Console explicitly allowlists public daemon session fields and drops
  unknown fields. New orchestration fields require intentional shared/edge/UI
  projections; placing unknown members in a session record is insufficient.
  [F5]
- Agent Console removes a card locally only after producer-confirmed delete. The
  activity stream never removes a card; a gap or a projection that omits a known
  session only signals an authoritative-list refresh, which performs the removal.
  It polls that authoritative list at a bounded interval (currently four seconds).
  [F6]
- Under `enforce`, the runtime-kit coordination-guard hook fails managed
  mutations closed unless an active work-context claim is held, and admits only
  an enumerated allowlist of read-only and claim-bootstrap command shapes;
  `agent-session` enforce mode itself only rejects conflicting work-context
  declarations. No `main-agent` shapes are in that allowlist today. [F7]
- The previously observed stopped worker card remained because the initial
  producer delete had not succeeded. The worker was later deleted and is absent
  from `agent-session list`; backend registry residue was not found. Browser
  acceptance for external-delete UI convergence is still missing. [A1]
- Runtime-kit issues #686 and #709 are closed after live acceptance. At the
  final read-back for this capture, runtime-kit and Agent Console local `main`
  match their remote-tracking refs, while nils-cli remains two commits ahead.
  The user still requires local-only execution because normal GitHub
  issue/PR/Actions delivery is unavailable for the restricted account. [A2]

## Decisions

1. **Durable resources, not repeated prompt copies**: store one orchestration
   run plus assignment resources. Sessions receive only stable relationship
   identifiers and bounded privacy-safe projections.
2. **`agent-session` remains the primitive owner**: session identity,
   incarnation, lifecycle, capability binding, claims, activity, mailbox,
   storage safety, and HTTP/API primitives remain in nils-cli `agent-session`.
3. **Add a public `main-agent` facade**: ship a separate nils-cli binary for
   Main Agent orchestration. It calls typed `agent-session` library/API
   primitives and never edits state files directly or relies on fragile shell
   chaining.
4. **The facade adds workflow semantics**: it owns revision-fenced run
   creation, checkpointing, rehydration, worker assignment, verified handoff,
   acceptance state, release, and cleanup. An alias-only wrapper is not
   acceptable.
5. **One primary manager, optional additional relationships**: each assignment
   has at most one primary manager and may have bounded collaborators or
   borrowers. Primary manager is the default responsibility/routing owner, not
   exclusive access control.
6. **Relationships never grant mutation authority**: borrowing,
   collaboration, UI grouping, or primary-manager status cannot acquire a
   work-context claim, operation lease, provider permission, or repository
   authority.
7. **Stable run and assignment identities**: run IDs and assignment IDs survive
   provider compaction, resume, and controller incarnation rotation.
8. **Session references are incarnation-fenced**: the authorization fence is the
   `agent-session` session ID plus session incarnation. `machine` is only an
   advisory display/routing hint, not part of identity or authorization. Reusing
   a public ID never restores the previous relationship, and V1 keeps a run's
   participants on one `agent-session` host/state root.
9. **Private packet, public summary**: full requests, done criteria,
   constraints, private refs, and checkpoints live in capability-protected
   mode-0600 records. Public projections expose only bounded summaries, state,
   identifiers, revisions, and safe counts.
10. **No compaction-detector dependency**: recovery does not rely on detecting
    provider compaction. Active sessions get a short advisory pointer at safe
    turn/tool boundaries and can deterministically call a read-only rehydrate
    command.
11. **Agent Console is projection/operator UI**: it does not infer or
    manufacture relationships. Mutations use daemon APIs with identity and
    revision fences.
12. **V1 covers managed sessions only**: `agent-session`-managed Codex and
    Claude sessions are participants. Provider-native in-process subagents are
    future scope until they expose stable identity/events.
13. **Local-only delivery while GitHub is restricted**: use managed worktrees,
    signed local commits, local validation/review, and explicit local
    integration. Do not push, publish, dispatch Actions, or open provider
    artifacts until the user confirms restoration and authorizes delivery.
14. **Enforce-mode bootstrap stays usable**: under `enforce` coordination a Main
    Agent or worker starts before holding a work-context claim. The runtime-kit
    coordination-guard hook fails facade mutations closed until an authenticated
    claim and revision fence exist, but must admit the facade's read-only
    discovery (`self show`, `rehydrate`, `status`, `worker list/show`) and
    run/claim bootstrap (`init` and claim acquisition) before a claim exists.
    Admission is a hook-layer allowlist concern: `agent-session` enforce mode
    itself only rejects conflicting declarations, so the new facade shapes must
    be added to the guard allowlist or a fresh Main Agent cannot discover state
    or bootstrap.

## Scope

### `sympoies/nils-cli`

- Versioned orchestration-run, participant, assignment, relationship,
  checkpoint, and public-projection schemas.
- Private durable orchestration storage under the trusted `agent-session`
  state boundary.
- Revision-fenced lifecycle and authenticated self/operator APIs.
- Additive `agent-session` orchestration primitives used by the facade and
  Agent Console.
- New `main-agent` binary and stable JSON envelopes.
- Codex and Claude managed-session rehydration.
- Backward-compatible list/serve/activity projections and migration behavior.

### `graysurf/agent-runtime-kit`

- Revise Main Agent Mode so the durable graph and `main-agent` CLI become the
  authoritative orchestration surface after the matching nils-cli surface is
  available.
- Add bounded rehydration/checkpoint instructions and hook reminders for Main
  Agents and managed workers.
- Extend the coordination-guard admission allowlist to the exact facade
  read-only discovery and run/claim bootstrap command shapes so `enforce` stays
  usable before a claim, keeping mutations, foreign identities, unsafe files, and
  option drift fail-closed.
- Keep reminders and instructions product-neutral and degrade gracefully where
  the host-specific `main-agent` CLI is absent, honoring the portable-contract
  boundary.
- Preserve user authority, tiering, test-first, validation, review, delivery,
  coordination, secret, and provider boundaries.
- Add Codex/Claude fixtures for compaction/recovery, worker loss, handoff,
  borrowing, and cleanup.
- Update CLI/version declarations only after the compatible nils-cli surface
  passes affected validation.

### `serenvia/agent-console`

- Safely project additive orchestration fields through shared, edge, and UI
  schemas.
- Render Main, Worker, and Standalone roles and group sessions by run.
- Link worker cards to their primary Main Agent and Main cards to worker state
  counts.
- Render orphaned, borrowed, cross-managed, stale, and cleanup-eligible states.
- Preserve producer-confirmed deletion and add live acceptance for external
  CLI deletion convergence.

## Non-Scope

- No GitHub issue, plan issue, PR, Actions workflow, release, or Homebrew update
  during the current provider restriction.
- No replacement for provider-native Codex/Claude subagent APIs.
- No transcript, pane, prompt, or log scraping to reconstruct objectives or
  relationships.
- No graph-derived ACL preventing cross-manager communication or cooperation.
- No weakening of claims, admission, repository policy, secrets, validation,
  delivery, OS, or provider controls.
- No automatic trust, authentication, permission, service, release, or provider
  repair.
- No automatic deletion/hiding of every stopped session; stopped sessions may
  be resumable and retain provider conversations.
- No broad cleanup of dirty, rescue, locked, or unrelated worktrees/sessions.
- No public copy of the complete user request.
- No cross-host orchestration registry in V1: a run's participants share one
  `agent-session` host/state root, and multi-host federation is future scope
  alongside provider-native subagents.

## Architecture And Ownership Boundaries

```text
main-agent CLI
    orchestration workflow, checkpoints, workers, rehydration
        |
        v
agent-session library / daemon / API
    identity, incarnation, storage, capabilities, revisions, lifecycle,
    claims, mailbox, activity, authenticated projections
        |
        +--> Agent Console edge/shared/UI
        |       safe projection, grouping, navigation, operator actions
        |
        +--> agent-runtime-kit
                policy, skills, reminders, cross-product acceptance
```

`main-agent` may sequence low-level operations, but each state mutation must be
one revision-fenced daemon/library contract. It cannot infer success from
process state, tmux panes, titles, or send responses.

Session management continues to own provider readiness, verified prompt
delivery, activity proof, and deletion recovery. Main Agent Mode owns
task/run/assignment state and acceptance. Agent Console consumes the same
public truth and never becomes another orchestration database.

## Data Contracts

### Orchestration run

Use a private versioned record such as
`agent-session.orchestration-run.v1`:

```json
{
  "schema_version": "agent-session.orchestration-run.v1",
  "run_id": "uuid",
  "revision": 1,
  "state": "active",
  "tier": "L3",
  "objective_summary": "Deliver managed Main Agent recovery",
  "objective_packet_digest": "sha256:...",
  "controller": {
    "machine": "sympoies",
    "session_id": "managed-main",
    "session_incarnation": "runtime-incarnation"
  },
  "durable_refs": [],
  "checkpoint": {
    "revision": 1,
    "summary": "Schema implementation ready for integration",
    "next_action": "Run cross-repo acceptance",
    "updated_at": "2030-01-01T00:00:00Z"
  },
  "created_at": "2030-01-01T00:00:00Z",
  "updated_at": "2030-01-01T00:00:00Z"
}
```

- `objective_summary` is privacy-safe and bounded to 240 UTF-8 bytes.
- The complete objective packet is a separate mode-0600 record addressed by
  digest/ID, never a public path.
- Controller loss marks the run orphaned/recovery-needed; it does not delete
  the run or assignments.
- Run close requires terminal assignments or explicit retained exceptions.
- `controller.machine` is an advisory display/routing hint (as in Agent Console's
  per-session `machine` and `agent-session`'s transient SSH-attach host); the
  authorization fence is `session_id` plus `session_incarnation`. V1 keeps all of
  a run's participants on one `agent-session` host/state root.
- Orchestration run/assignment records are a new typed store owned by
  `agent-session` under its trusted state root, distinct from per-session
  `session.json` and the coordination `registry.json`; the facade never writes
  them directly.

### Session orchestration projection

Add an optional public projection; legacy and standalone sessions omit it:

```json
{
  "orchestration": {
    "schema_version": "agent-session.session-orchestration.v1",
    "run_id": "uuid",
    "role": "main",
    "assignment_id": null,
    "primary_manager": null,
    "relationship_revision": 4,
    "run_state": "active",
    "assignment_state": null,
    "objective_summary": "Deliver managed Main Agent recovery"
  }
}
```

Worker projections use `role:"worker"`, an assignment ID, and a primary
manager reference. Public output must never expose task bodies, capabilities,
private paths, mailbox bodies, provider prompts, or unrestricted checkpoints.

### Assignment

Use `agent-session.orchestration-assignment.v1` with:

- stable assignment ID/run ID and revision;
- state: `assigned`, `starting`, `working`, `blocked`, `submitted`,
  `accepted`, `released`, or `cancelled`;
- primary-manager and worker incarnation-fenced refs;
- private packet digest and public task summary;
- repository/worktree/base/scope and provider/plan refs;
- validation/delivery duties and latest checkpoint/result/blocker metadata;
- reassignment/relationship history;
- cleanup eligibility derived from terminal state, operation quiescence, claim
  release, and fresh list absence.

Unknown schema/state fails closed for mutation while remaining safely
displayable as unsupported/stale metadata.

### Relationship semantics

- `primary_manager` is singular and revision-fenced.
- `collaborator` and `borrowed_by` are optional, non-authoritative edges.
- Borrowing is time-bounded; expiry changes routing metadata only and cannot
  cancel or grant an operation lease.
- Read-only inspection and mailbox coordination remain available across
  manager boundaries under existing privacy/authentication rules.
- Mutable primary handoff requires explicit reassignment, old-owner quiescence,
  and proof no concurrent writer remains.
- A collaborator/borrower never receives claims, capabilities, assignment
  ownership, or user authorization from the relationship alone.

## Authentication, Storage, And Privacy

- Store private resources below the trusted `agent-session` state directory in
  a non-symlink root owned by the effective user: directories 0700, files 0600.
- Use atomic replace, fsync ordering, bounded locks, revisions, and idempotency
  consistent with coordination storage.
- Bind self reads/mutations to the live incarnation and capability. A worker
  reads only its assignment; a Main Agent reads its run and assignments.
- Operator/API actions use server-operator authentication and expected
  revision/incarnation fences. Operator authority cannot manufacture a session
  capability or impersonate a worker.
- Controller rebind after incarnation rotation is authorized only when the same
  public session ID authenticates at the new live incarnation with a fresh
  capability and `agent-session` proves the prior incarnation stopped (its
  broker-provision continuity guarantee); the run's controller reference then
  updates under an expected run-revision fence. A recreated (delete/recreate)
  session presents a clean incarnation with no continuity and is refused rebind,
  staying orphaned until an explicit adopt.
- Agent Console output is allowlisted. Recovery output excludes secrets,
  prompts, transcripts, mailbox bodies, raw private paths, capabilities, tmux
  IDs, PIDs, and environment values.

## `main-agent` CLI Contract

The exact syntax may follow nils-cli conventions, but V1 must cover:

```text
main-agent init --packet-file <private-json> --format json
main-agent self show --format json
main-agent rehydrate --format json|markdown
main-agent status --format json
main-agent checkpoint --file <private-json> --if-revision <n> --format json

main-agent worker start --assignment-file <private-json> --if-run-revision <n> --format json
main-agent worker list --format json
main-agent worker show <assignment-id> --format json
main-agent worker message <assignment-id> --body-file <private-file> --format json
main-agent worker accept <assignment-id> --if-revision <n> --format json
main-agent worker release <assignment-id> --if-revision <n> --format json
main-agent worker delete <assignment-id> --if-revision <n> --format json

main-agent collaborate <assignment-id> --session <ref> --if-revision <n> --format json
main-agent borrow <assignment-id> --session <ref> --duration <bounded> --if-revision <n> --format json
main-agent handoff <assignment-id> --to <session-ref> --if-revision <n> --format json
main-agent adopt <assignment-id> --if-revision <n> --format json
main-agent close --if-revision <n> --format json
```

The facade must:

- resolve its Main Agent from authenticated self context, not a role env flag;
- fence every state-mutating command with an expected revision (`--if-revision`,
  or `--if-run-revision` for run-scoped creation) and an `--idempotency-key`,
  matching the `agent-session` work-context lifecycle contract, while read-only
  discovery (`self show`, `status`, `rehydrate`, `worker list/show`) carries
  neither;
- preserve candidate check, exact start/list identity, readiness, paste-count,
  provider-turn acceptance, worker self-check, and claim handoff;
- return partial/uncertain outcomes explicitly and never equate transport with
  acceptance;
- never use a worker capability, pre-admit mutation, or infer completion;
- delete only after terminal assignment, operation quiescence, claim release,
  producer confirmation, and fresh list absence;
- retain failed workers and recovery metadata when deletion/list absence fails.

Low-level `agent-session` APIs may expose primitives for workers/tests/Agent
Console, but ordinary Main Agent operation uses the facade so required proofs
are not accidentally omitted.

## Context Rehydration And Checkpointing

`main-agent rehydrate` returns a bounded recovery capsule containing:

- run identity, revision, role, state, and controller identity;
- objective summary and authorized private objective access;
- done criteria and constraints;
- durable issue/plan/run-state/worktree/diff/delivery refs when present;
- managed assignment counts and each worker's privacy-safe state;
- blockers/findings and pending acceptance duties;
- latest checkpoint, next action, and stale/orphan/cleanup warnings.

The capsule is a deterministic function of the run/assignment records at a named
revision: worker entries are ordered by assignment ID and counts derive from
those records, so identical durable state yields byte-stable output. Only the
liveness-derived annotations (stale/orphan/cleanup, checkpoint age) vary with the
observation clock and are labeled as observation-time.

Workers need an authenticated self command returning only their assignment,
constraints, scope, result contract, manager relationship, and current
claim/operation status. It cannot expose sibling packets.

Recovery behavior:

1. Start/resume projects run/assignment identity without putting the private
   packet in argv or public diagnostics.
2. Runtime-kit gives active Main Agents/workers a concise advisory reminder at
   safe turn/tool boundaries.
3. The reminder points to the read-only self/rehydrate command; it neither
   repeats task content nor blocks unrelated work.
4. Revision-sensitive mutation with stale local state returns current metadata
   and retry guidance rather than guessing.
5. Compaction, provider resume, or replacement UI clients reconstruct the same
   capsule from durable state.

## Agent Console UX Contract

### Session presentation

- Badges: `Main`, `Worker`, and `Standalone`.
- Group by orchestration run while retaining standalone view.
- Main cards show working, blocked, submitted, accepted, cleanup-pending, and
  orphaned worker totals.
- Worker cards show `Managed by <main title>`, jump-to-main, and run navigation.
- Main views show bounded objective, checkpoint age, next action, and workers.
- Worker views show assignment summary, manager, collaborators/borrowers, and
  claim/cleanup status.

### Relationship states

- `Orphaned`: assignment active, primary controller absent/incarnation-stale.
- `Borrowed`: temporary collaborator present; primary ownership is unchanged.
- `Cross-managed`: coordinated by more than one run/session without transfer.
- `Stale`: UI revision older than daemon state; reconcile before mutation.
- `Cleanup pending`: logical delete committed; physical janitor may remain,
  while the session is absent from the live list.

### Delete behavior

- A stopped card is not automatically residue. Preserve it when producer truth
  still lists a resumable or failed-delete session.
- UI delete removes local card/slot/focus only after producer confirmation.
- External CLI delete makes the stream flag a reconcile (missing projection or
  sequence gap), which refreshes the authoritative list and removes the card; the
  bounded authoritative poll (currently four seconds) is the fallback when no
  stream signal arrives.
- Delete failure retains the card and structured recovery UI.
- Never hide a card to simulate cleanup while producer truth lists it.

## Requirements

- **R1**: Add versioned run, assignment, session projection, and relationship
  schemas in nils-cli.
- **R2**: Persist private recovery state under trusted `agent-session` storage
  with atomic revision-fenced operations.
- **R3**: Add optional orchestration projections to list, serve, activity, and
  create/resume without breaking legacy records/clients.
- **R4**: Implement `main-agent` as a typed separate binary with stable JSON
  envelopes and no direct state-file writes.
- **R5**: Survive compaction, provider resume, and controller incarnation
  rotation through explicit validated rebind.
- **R6**: Provide least-privilege Main/worker recovery capsules.
- **R7**: Preserve verified startup, transport, self-check, claim, operation,
  acceptance, and cleanup boundaries.
- **R8**: Keep primary manager as routing/ownership metadata, not ACL; preserve
  cross-manager mailbox/read-only collaboration.
- **R9**: Require quiescent handoff for mutable ownership change; borrowing
  never transfers write authority.
- **R10**: Revise runtime-kit Main Agent Mode to consume the graph/CLI instead
  of claiming no graph exists.
- **R11**: Add advisory, privacy-safe rehydration reminders without restricting
  general agent capability.
- **R12**: Project safe data through Agent Console shared/edge/API/activity/UI.
- **R13**: Add desktop/mobile role grouping and manager/worker navigation.
- **R14**: Preserve stopped/resumable and failed-delete cards until producer
  truth changes; prove successful external deletion disappears live.
- **R15**: Use one product-neutral contract for Codex and Claude.
- **R16**: Keep V1 managed-session-only; do not invent provider-native IDs.
- **R17**: Admit facade read-only discovery and run/claim bootstrap under
  `enforce` before a claim exists via the coordination-guard allowlist, while
  every facade mutation stays fail-closed until an authenticated claim and
  revision fence are present.

## Acceptance Criteria

### Schema, compatibility, and privacy

- **A1**: Legacy records without orchestration list unchanged as standalone.
- **A2**: New records round-trip run, assignment, role, manager, incarnation,
  state, and revision; unknown schema/state rejects mutation safely.
- **A3**: Old Agent Console fixtures ignore additive fields; new projection
  drops unknown, oversized, and private nested members.
- **A4**: Public CLI/API/activity output contains no private packet, capability,
  prompt, transcript, mailbox body, raw private path, token, environment, tmux
  ID, or PID.
- **A5**: Unsafe roots/owners/modes, path escape, stale revision/incarnation,
  and invalid digest fail before mutation.
- **A6**: Delete/recreate of a public session ID cannot inherit old controller,
  assignment, capability, or relationship.

### Rehydration and lifecycle

- **A7**: A Main Agent creates a run and two assignments, checkpoints, then a
  fresh controller incarnation with no in-memory context recovers objective,
  constraints, workers, checkpoint, and next action solely from authenticated
  rehydrate output, byte-stable across repeated calls at the same revision.
- **A8**: A fresh worker incarnation similarly recovers only its
  assignment/manager from authenticated self output after resume or context reset.
- **A9**: Controller incarnation rotation rebinds the run only after the same
  public session ID authenticates at the new incarnation with a fresh capability,
  `agent-session` proves the prior incarnation stopped, and the run-revision fence
  matches; the run is neither deleted nor silently transferred, and a recreated
  (ABA) session is refused rebind.
- **A10**: Stale checkpoint revision returns current metadata/retry guidance
  without invalidating the run.
- **A11**: Reminders are bounded/private and do not block unrelated safe work.
- **A12**: Worker start proves session identity/incarnation/cwd/mode, readiness,
  paste, newer provider turn, worker self-check, and active claim.
- **A13**: Transport-only/readiness-uncertain/identity-mismatch/interference/
  missing-claim states remain explicitly incomplete.
- **A14**: A second Main Agent can inspect safe metadata and use mailbox without
  becoming primary or gaining mutation authority.
- **A15**: Borrowing is visible and expires without changing ownership or
  granting/cancelling a lease.
- **A16**: Mutable handoff requires old-owner quiescence, claim/scope release,
  revision-fenced update, and new-owner verification.
- **A17**: Worker loss marks orphan/unavailable while retaining durable task,
  diff, worktree, validation, and result refs.
- **A18**: Cleanup requires terminal assignment, no active/uncertain operation,
  released claim, producer delete, and fresh list absence.

### Agent Console and regression

- **A19**: Desktop/mobile distinguish and group Main, Worker, Standalone.
- **A20**: Navigation uses exact session ID/incarnation, run ID, assignment ID,
  and revisions as the fence, with `machine` as a display/routing hint only.
- **A21**: Orphaned, borrowed, cross-managed, stale, and cleanup states render
  without private packet leakage.
- **A22**: Delete failure retains card/recovery; UI delete success removes only
  after producer confirmation.
- **A23**: With Agent Console open, external exact `agent-session delete` removes
  the card through an authoritative-list refresh — triggered eagerly by the stream
  reconcile signal or by the bounded poll (currently four seconds) — within one
  poll interval and without manual refresh; a dropped stream event (sequence gap)
  still converges via the poll.
- **A24**: Stopped but listed/resumable remains visible.
- **A25**: Disposable Codex/Claude Main/worker pairs pass create, rehydrate,
  checkpoint, collaborate, handoff, accept, release, and cleanup.
- **A26**: Standalone start/list/resume/activity/message/delete remains
  compatible except additive optional fields.
- **A27**: Advisory/enforce/off and locked hook semantics remain unchanged.
- **A28**: Unrelated/native/third-party hooks and Codex notifier composition
  survive deployment.
- **A29**: Under `enforce` with no active claim, facade read-only discovery and
  run/claim bootstrap are admitted, while a facade mutation without a claim/lease
  fails closed with claim-recovery guidance; `agent-session` advisory/enforce/off
  semantics are otherwise unchanged.

## Findings And Fix-Later Backlog

| Priority | Finding | Evidence | Fix owner | Acceptance |
| --- | --- | --- | --- | --- |
| P0 | Main purpose and worker ownership are not durable across compaction. | Session schema lacks run/assignment; protocol is procedural. [F1][F3] | nils-cli + runtime-kit | A7–A11 |
| P0 | Main Agent Mode currently denies the graph/new CLI required here. | Current skill boundary. [F4] | runtime-kit after nils | R10, A25–A28 |
| P1 | Agent Console cannot render authoritative relationships and drops unknown fields. | Projection allowlist. [F5] | Agent Console | A19–A21 |
| P1 | External successful CLI deletion lacks live browser acceptance. | Source has stream/poll paths; only backend absence was proven. [F6][A1] | Agent Console | A23 |
| P1 | GitHub restriction prevents normal issue/PR/Actions delivery and the pending nils-cli release. | nils-cli remains ahead by two commits; provider Actions rejected the account. [A2] | External/later delivery | Local-only guardrail |
| P1 | Under `enforce`, the coordination-guard admission allowlist has no `main-agent` shapes, so a fresh Main Agent's read-only discovery and run/claim bootstrap would be blocked before a claim. | Hook admission allowlist. [F7] | runtime-kit | R17, A29 |
| P2 | Provider-native subagents lack stable Agent Console identity. | UI consumes managed sessions only. [F5] | Future integration | Outside V1 |

## Validation Plan

### nils-cli

- Test-first reds for migration, stale revision/incarnation, privacy,
  capability isolation, atomic storage, rehydrate, collaborate, handoff, and
  cleanup.
- Focused `agent-session`/`main-agent` tests plus serve/API/CLI JSON fixtures,
  legacy compatibility, and claim/lease regression.
- Repository gate:

  ```bash
  bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast
  ```

### agent-runtime-kit

- Test-first reds for Main Agent source/render/runtime behavior.
- Codex/Claude golden/runtime-smoke coverage for CLI requirement, rehydrate,
  reminders, lifecycle, and locked controls.
- Declared gate:

  ```bash
  bash scripts/ci/all.sh && bash tests/hooks/run.sh
  ```

- Deploy only from integrated validated local main via
  `scripts/sync-runtime-surfaces.sh`; never hand-edit live registrations.

### Agent Console

- Shared/edge/UI projection tests for optional fields, limits, unknown members,
  privacy, revisions, and old daemons.
- Desktop/mobile behavior tests for grouping, badges, navigation, orphan,
  borrow, stale state, and deletion convergence.
- Declared gate:

  ```bash
  pnpm install --frozen-lockfile
  pnpm run typecheck
  pnpm run test
  pnpm run check:app-versions
  pnpm run build
  ```

- Live browser acceptance with open Agent Console, disposable sessions,
  external deletion, activity interruption, reconnect, and poll fallback.

### Integrated acceptance

- Use synthetic private packets and disposable repositories/sessions.
- Exercise Codex and Claude with one Main Agent, two workers, a second Main
  collaborator, one borrow, one handoff, one resumed incarnation, one orphan
  recovery, and terminal cleanup.
- Collect privacy/latency evidence without session content, then remove
  disposable sessions/state while retaining sanitized machine results.
- Run one focused independent review per repository and one integration review
  of the cross-repository contract. Do not restart review for optional style.

## Risks And Guardrails

- **Second truth store**: storage/lifecycle stay in `agent-session`; Agent
  Console is projection-only and `main-agent` uses typed primitives.
- **Privacy leakage**: private packet records, public allowlists, bounded
  summaries, and capability-backed reads.
- **Relationship mistaken for authority**: claims/leases remain independent;
  borrow/collaboration are tested not to grant mutation.
- **Stale/ABA identity**: machine + ID + incarnation refs, revisions, and
  explicit rebind/handoff.
- **Facade skips proof**: atomic primitive outcomes and existing verified
  handoff sequence remain mandatory.
- **Compaction loses reminder**: durable self-rehydrate, start/resume projection,
  and repeated lightweight safe-boundary reminders.
- **Stopped-card auto-hide loses data**: only producer-confirmed deletion and
  fresh list absence remove sessions.
- **Version skew**: implement nils schema/CLI first locally, then runtime-kit
  consumers and Agent Console against the exact built surface.
- **GitHub unavailable**: retain signed local commits/exact heads; never weaken
  signing/rules or claim provider success.
- **Unrelated dirty work**: use isolated managed worktrees and preserve primary
  `agent-out`, user untracked paths, dirty/rescue branches, and other sessions.
- **Enforce starves bootstrap**: extend the hook admission allowlist to the exact
  facade read-only and run/claim bootstrap shapes so `enforce` stays usable
  before a claim; keep every mutation, foreign identity, and unsafe file
  fail-closed. [F7]

## Execution

- Status: not started; ready for local cross-repository implementation.
- Next-task source: this document.
- Recommended workflow: a newly activated Main Agent reads this document,
  rehydrates repository/provider state, creates bounded managed-worktree lanes,
  implements nils-cli primitive/facade first, then runtime-kit consumption and
  Agent Console projection/UI, and owns integrated acceptance.
- Provider workflow: local-only until the user confirms GitHub restoration. No
  plan issue/provider artifact is required.
- Delivery: signed local commits with exact integration heads and validation
  evidence under XDG state. No push without later explicit authorization.
- This `docs/discussions/` capture intentionally has no `Recommended plan` or
  `Recommended execution state` lines.

## Captured Local Baseline

Re-read all repositories before implementation; these are 2026-07-22 evidence,
not moving targets:

- Runtime-kit local `main`:
  `e4ef1597503945ddfe1d5a4d55f8f775a2fec4ae`, equal to `origin/main`, with
  unrelated user untracked paths that must be preserved.
- nils-cli local `main`:
  `16644968869414397c1d806dd5d61d9cba9e44d9`, ahead of remote; the local
  agent-hook hotfix is deployed while Homebrew 1.25.9 remains rollback.
- Agent Console local `main`:
  `7c29824eaafa2cadbc6b4b8c266b7e7808412820`, equal to `origin/main`, with an
  unrelated repo-root `agent-out/` that must not be deleted/absorbed without
  verification.
- Runtime-kit final live evidence:
  `$HOME/.local/state/agent-runtime-kit/out/projects/graysurf__agent-runtime-kit/20260722-164155-final-live-acceptance/`.

## Retention Intent

Coordination material and primary read-first artifact for this local
implementation. After all three repositories ship and integrated acceptance
passes, remove it after reference audit or promote stable architecture into the
owning canonical docs. Do not retain a stale duplicate of promoted canon.

## Read-First References

- `[U1]` User requirements from the 2026-07-22 Main Agent Mode discussion:
  compaction recovery, manager/worker UI, durable relationships, dedicated CLI,
  and flexible cross-manager worker use.
- `[F1]` `$HOME/Project/sympoies/nils-cli/crates/agent-session/src/lib.rs`
  (`SessionRecord`, `SessionView`).
- `[F2]`
  `$HOME/Project/sympoies/nils-cli/crates/agent-session/docs/specs/session-coordination-v1.md`.
- `[F3]`
  `core/skills/conversation/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md`.
- `[F4]` `core/skills/conversation/main-agent-mode/SKILL.md.tera`.
- `[F5]` `$HOME/Project/serenvia/agent-console/packages/shared/src/api.ts` and
  `$HOME/Project/serenvia/agent-console/packages/ui/src/types.ts`.
- `[F6]` `$HOME/Project/serenvia/agent-console/packages/ui/src/Dashboard.tsx`
  and `packages/ui/src/activityStream.ts`.
- `[F7]` `core/hooks/shared/session-coordination-guard.py` — the coordination
  admission allowlist (`invocation_bypasses_admission` /
  `command_bypasses_admission`) that fails mutations closed without a claim and
  admits only enumerated read-only and claim-bootstrap command shapes.
- `[A1]` 2026-07-22 live `agent-session list` and worker-delete reconciliation
  during runtime-kit #686 final cleanup.
- `[A2]` Runtime-kit #686/#709 provider read-back plus local git/deployed
  evidence in the final live evidence directory above.
- `DEVELOPMENT.md` and
  `docs/source/docs-placement-retention-policy-v1.md` in this repository.
- `AGENTS.md`, `AGENT_DOCS.toml`, and `DEVELOPMENT.md` in each affected repo.

## Recommended Next Artifact

The next Main Agent should create a private local execution/task packet linking
this document as `Read First` and recording managed worktrees, owners,
dependency order, local heads, reviews, validation, deploy, and live acceptance.
It must not create a GitHub-backed plan issue while the restriction remains.
