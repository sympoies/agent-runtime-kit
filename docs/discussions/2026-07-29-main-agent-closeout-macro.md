# Main Agent Run-Wide Closeout Macro

## Status

- Lifecycle: implemented design record
- Scope: `nils-cli` orchestration primitive plus the consuming
  `conversation:main-agent-mode` contract
- Current behavior: capability-gated `main-agent closeout` is the normal path;
  the explicit primitives remain diagnostic and intentional recovery actions
- Local implementation: nils-cli local `main` `9ebbc922` and installed
  `main-agent 1.25.11 (v1.25.9-94-g9ebbc922)` on 2026-07-31
- Runtime-kit adoption: this change deploys the consuming Codex and Claude
  surfaces locally; no public nils-cli release or provider PR is claimed

## Problem

Main Agent Mode has high-level primitives for individual lifecycle stages:

- `main-agent checkpoint` persists a revision-fenced run checkpoint;
- `main-agent worker retire` folds worker claim release, logical deletion, and
  fresh-list absence;
- `main-agent close` revision-fences the durable run transition; and
- `agent-session work-context release` releases a generic session coordination
  claim.

Before the 2026-07-31 implementation there was no run-wide action that owned
the complete closeout transaction. The Main Agent had to discover and execute
the stages separately, preserve idempotency keys and revisions per stage, and
synthesize several read-backs before it could truthfully report Main Agent Mode
closed.

The 2026-07-29 B2/B3/B5/B6 closeout exposed the practical gap:

1. the durable run was otherwise ready to close, but two earlier cancelled
   worker sessions remained `cleanup_pending`;
2. each worker required a separate typed retirement and fresh-list proof;
3. `main-agent close` successfully changed the run to `closed`; and
4. the Main controller's generic work-context claim remained active until an
   explicit authenticated release and a second status read.

No unsafe cleanup was required, and the existing primitives produced the
necessary proof. The defect is orchestration ergonomics and ownership
composition: the safe pieces exist, but no single macro owns their ordering,
replay, aggregate result, or incomplete-stage projection.

## Prior Explicit Sequence

This was the required fallback before the folded macro was adopted:

1. rehydrate or read the exact run and persist a final bounded checkpoint;
2. inspect every assignment and follow its typed terminalization path;
3. run folded worker retirement for every eligible worker;
4. require fresh orchestration and session lists proving exact workers absent
   and no unexpected `cleanup_pending` entries;
5. call revision-fenced `main-agent close`;
6. read back the exact run as `closed`;
7. inspect the Main session's generic work-context claim;
8. release that claim only when its identity and context prove it belongs to the
   closing run, then read back claim absence; and
9. keep the Main provider session alive until the final user-facing result or
   handoff prompt has been delivered.

Run close, controller-claim release, and physical provider-session deletion are
three different lifecycle transitions. None implies another.

## Implemented Interface

The facade-owned macro is:

```bash
main-agent closeout \
  --if-run-revision <revision> \
  --checkpoint-file <private-json> \
  --idempotency-key <key> \
  --format json
```

The contract is revision-fenced, authenticated, idempotent, and macro-first.
It exposes no force cleanup, raw session input, claim impersonation, or option
that weakens operation-quiescence checks.

## Required Stages

### 1. Snapshot and checkpoint

- Authenticate the current Main controller and exact run incarnation.
- Require the run record to carry a durable controller-claim binding created at
  init or rebind: bounded claim ID, controller session and incarnation,
  acquisition revision, objective/context digest, and the authorized
  renewal/successor chain.
- Context equality alone never establishes claim ownership. A legacy run that
  lacks this binding may be migrated only from retained authenticated
  acquisition evidence; otherwise closeout fails closed with a typed
  provenance-recovery result.
- Verify the expected run revision before the first mutation.
- Read the deterministic assignment set and bounded session-maintenance
  projection.
- Validate and persist the caller's runtime-issued private checkpoint file.
- Return the committed checkpoint revision in every later stage projection.

### 2. Assignment classification

- Partition assignments into already absent, retirement-eligible, retained
  exception, and blocked.
- Do not reinterpret one terminal class as another.
- A pre-claim failure, post-claim stopped worker, accepted worker, active or
  uncertain operation, and identity mismatch retain their existing typed
  recovery contracts.
- If any assignment needs a recovery decision that the macro cannot safely
  execute, stop before run close and return its exact recovery action.

### 3. Worker retirement

- Invoke the existing folded retirement behavior for each eligible exact
  assignment.
- Preserve worktrees, branches, diffs, evidence, and retained quarantine unless
  a separate owning workflow explicitly authorizes their cleanup.
- Serialize mutations even if read-only evidence gathering is parallelized.
- Require fresh default-list absence for every retired session.
- Keep cleanup failures visible as typed maintenance results.

### 4. Run close

- Close only when all assignments are terminal or carry an explicitly admitted
  retained exception.
- Recheck the run revision after child mutations and use the macro's
  deterministic internal revision progression.
- Commit the existing durable `closed` transition once.
- Read back the exact run state rather than trusting the write response alone.

### 5. Controller claim disposition

- Treat the Main controller's work-context claim as a distinct
  session-management resource.
- Release it only when its durable claim ID, controller incarnation, acquisition
  revision, and authorized renewal/successor chain prove that the active claim
  is the exact claim established or retained for this run.
- Never release an unrelated later claim held by the same provider session.
- Record stable absence when no claim exists.
- On ambiguous provenance, preserve the claim and return closeout incomplete
  with the exact evidence needed for the session-management owner.

### 6. Final verification

- Re-read run state, assignment maintenance state, session list, active or
  uncertain operations, and controller work context.
- Report success only when the run is closed, no unexpected worker remains,
  cleanup is not pending, and the run-owned controller claim is absent.
- Preserve the Main provider session. The macro must not terminate the
  conversation transport that still owes the user its final response.

## Implemented Result Contract

The public result exposes bounded proof, not private capabilities or raw
session material. A successful projection has this shape:

```json
{
  "schema_version": "main-agent.closeout-result.v1",
  "run_id": "<bounded-id>",
  "expected_run_revision": 3,
  "checkpoint_revision": 4,
  "final_run_revision": 7,
  "progress_receipt": {
    "schema_version": "main-agent.closeout-progress-receipt.v1",
    "completed_stages": [
      "checkpoint",
      "workers",
      "run_close",
      "claim_release",
      "readback"
    ]
  },
  "run_closed": true,
  "worker_dispositions": [
    {
      "assignment_id": "assignment-a",
      "released": true,
      "deleted": true,
      "cleanup_pending": false,
      "retired": true
    }
  ],
  "workers_absent": true,
  "cleanup_pending": false,
  "retained_exceptions": [],
  "controller_claim": {
    "bound": true,
    "claim_id": "claim-a",
    "disposition": "released",
    "run_owned_claim_absent": true,
    "active_after": false
  },
  "provider_session_preserved": true,
  "handoff_ready": true
}
```

Each worker disposition is the bounded folded-retirement result. The three
revision fields distinguish the caller's fence, the committed checkpoint, and
the final read-back instead of overloading one number.

An incomplete result must retain the same progress-receipt and per-worker
shapes, plus fields equivalent to:

```json
{
  "schema_version": "main-agent.closeout-result.v1",
  "run_closed": false,
  "workers_absent": false,
  "cleanup_pending": false,
  "retained_exceptions": [
    {
      "assignment_id": "assignment-b",
      "state": "working",
      "reason": "assignment-not-retireable"
    }
  ],
  "controller_claim": {
    "disposition": "pending",
    "run_owned_claim_absent": false,
    "active_after": true
  },
  "progress_receipt": {
    "schema_version": "main-agent.closeout-progress-receipt.v1",
    "completed_stages": ["checkpoint"]
  },
  "provider_session_preserved": true,
  "handoff_ready": false
}
```

It must never reduce partial closeout to a bare nonzero exit or invite replay
of the entire macro with a new key.

## Idempotency and replay

- One logical closeout request uses one caller idempotency key.
- Bind its request digest to the original expected run revision, checkpoint
  digest, and initial assignment snapshot.
- Internal child keys must be deterministic derivatives of that parent key.
- A replay with the same request and key returns the committed aggregate result
  or resumes only from a validated progress receipt.
- Run revision and assignment changes produced by the macro are valid only when
  the matching progress receipt attests them; they do not change the request.
- Changed caller input requires a new key after fresh state inspection.
  Unexplained external revision or assignment-membership drift fails closed and
  cannot be adopted merely by choosing a new key.
- Completed child retirement or run-close stages must not repeat mutation.
- An interrupted claim-release stage must prove current claim identity and
  disposition before continuing.

## Failure boundaries

The macro must fail closed when:

- any assignment is non-terminal without an executable typed recovery;
- a worker identity or incarnation changed;
- an admitted operation is active or uncertain;
- fresh session-list truth is unavailable;
- worker cleanup remains pending;
- the run revision or controller identity changed;
- controller-claim provenance is ambiguous or cannot be proven; or
- the private checkpoint input or capability binding is unavailable.

Failure preserves every resource not already changed by a committed stage and
never rolls a committed stage back. The result reports the exact current
disposition of the run, every worker, the controller claim, worktrees, and the
provider session at the last proven safe stage. It never uses raw tmux input,
arbitrary kill, generic session deletion, force group cleanup, or
prior-controller impersonation.

## Ownership boundaries

- `main-agent` owns orchestration ordering, revision fencing, aggregate
  idempotency, run state, and the public result.
- `agent-session` remains the owner of worker/session lifecycle, generic
  work-context claims, operation quiescence, and list truth.
- The provider session owner controls physical stop or deletion of the Main
  session after the handoff is delivered.
- Repository worktree and branch cleanup remains with the active Git delivery
  workflow.
- The handoff-session prompt workflow may produce continuity text, but it does
  not mutate orchestration state and is not a substitute for closeout.

## Acceptance criteria

1. A run whose workers are already retired closes in one idempotent macro call,
   releases its run-owned controller claim, preserves the Main provider session,
   and returns complete read-back proof.
2. A terminal worker whose logical deletion leaves `cleanup_pending` returns a
   partial result; exact replay re-observes the retained tombstone and advances
   only after maintenance clears it.
3. An active or uncertain worker operation stops before retirement and returns
   the existing typed recovery action without closing the run.
4. A worker-retirement partial failure is replay-safe and cannot hide the worker
   or advance run close.
5. A closed run with its run-owned claim still active can resume the same
   closeout request at claim disposition without repeating worker or run
   mutations.
6. An unrelated active claim held by the same Main provider session is
   preserved and reported, the run-owned claim is recorded absent, and closeout
   can succeed; the macro does not broaden claim ownership.
7. Exact replay with the original now-stale revision returns or resumes the
   committed result only when the matching progress receipt accounts for every
   internal transition. A changed request, unexplained stale revision, missing
   receipt, or external drift fails closed.
8. The Main provider session remains live until a separate session-owner action
   occurs after the user-facing handoff.
9. Codex and Claude rendered Main Agent Mode surfaces require the exact
   closeout capability, prefer the macro, and retain primitives only for
   diagnosis or intentional recovery.

## Validation plan

- Nils-cli integration coverage exercises complete closeout and exact replay,
  nonterminal-worker resume, cleanup-tombstone resume, active-operation
  blocking, unrelated-successor preservation, missing-provenance rejection,
  and provider-session preservation.
- CLI contract coverage asserts the public command and capability.
- The canonical nils-cli `--local-fast` gate passed with all 7,816 nextest
  cases, doctests, clippy, fmt, docs, and hygiene checks.
- A real-product multi-worker closeout remains useful residual field evidence;
  it is not required to prove the local command and consumer deployment.
- Runtime-kit deterministic conversation smoke asserts macro-first closeout,
  partial exact replay, capability admission, and provider-session preservation.

## Rollout

1. Nils-cli implementation and schema documentation landed on local `main`.
2. The compatible nils-cli surface was installed locally; public release was
   intentionally skipped because provider delivery was unavailable.
3. `conversation:main-agent-mode` now requires the capability and prefers the
   folded macro; primitives are recovery-only.
4. Render and deploy Codex and Claude runtime surfaces locally.
5. Retain the multi-worker real-product closeout as optional residual field
   evidence.
6. Record F35 implementation, local deployment, and installed acceptance in the
   canonical blocker inventory without claiming a public release.

## Non-goals

- Automatically deciding how to terminalize a worker whose typed state is
  ambiguous.
- Deleting retained worktrees, branches, evidence, or quarantines.
- Stopping the Main provider session before its final response.
- Replacing provider delivery, plan closeout, or repository cleanup workflows.
- Weakening revision, incarnation, claim, operation, signing, hook, or
  authorization boundaries.
