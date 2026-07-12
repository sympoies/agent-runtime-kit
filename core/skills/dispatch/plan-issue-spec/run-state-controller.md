# Plan Tracking Issue Run-State Controller

## Status

- Status: implemented; canonical design
- Date: 2026-05-26
- Depends on:
  - `core/skills/dispatch/plan-issue-spec/comment-taxonomy.md`
  - `core/skills/dispatch/plan-issue-spec/workflow.md`
  - `core/skills/dispatch/plan-issue-spec/cli.md`
  - `core/skills/dispatch/plan-issue-spec/skill-family.md`
- Chosen direction: deterministic finite state machine plus typed local run
  state under the `plan-issue` runtime workspace.

## Purpose

This document specifies Option B for the plan-tracking issue redesign:
`nils-cli` should own a deterministic workflow controller that reads provider
issue lifecycle evidence, the local plan bundle, and typed execution-run state
from the runtime workspace. The controller should then expose safe next actions
and common checkpoint writes for runtime-kit skills.

The goal is not to make `nils-cli` implement code for the agent. The goal is to
make lifecycle control deterministic, auditable, resumable, and hard to format
incorrectly.

## Core Decision

Use a deterministic finite state machine, not a LangGraph-style orchestration
runtime, for the CLI core.

Rationale:

- The plan-tracking issue lifecycle is a finite provider-record protocol:
  source, plan, state, session, validation, review, closeout, and dashboard.
- The correctness problem is deterministic state reconciliation, not dynamic
  LLM reasoning.
- Rust CLI tests can lock FSM transitions, JSON envelopes, filesystem layout,
  fixture mode, and visible comment completeness.
- An outer agent runner may later use LangGraph or another graph engine, but it
  should consume `nils-cli` primitives instead of replacing them.

## Truth Model

| Layer | Role | Durability | Source of truth for |
| --- | --- | --- | --- |
| Provider issue lifecycle comments | Append-only durable record | durable | Current lifecycle evidence, closeout gates, audit history. |
| Provider issue body dashboard | Mutable summary | derived | Human scan surface and links to latest lifecycle evidence. |
| Plan bundle files | Local source documents | durable when committed | Source, plan, and execution-state Markdown. |
| `plan-issue` run state | Local execution cache | resumable but secondary | Selected task, branch, PR, run artifacts, pending transition. |
| `events.jsonl` | Local execution journal | append-only local evidence | Resume/debug history and checkpoint provenance. |
| `agent-out` artifacts | Local evidence paths | retained by workflow policy | Command logs, validation artifacts, review evidence. |

Provider lifecycle comments win over local run state when they disagree. Local
run state may propose the next write, but it must be reconciled against live or
fixture issue evidence before provider mutation.

## Runtime Layout

The controller should reuse the existing `plan-issue` state-dir resolution:

1. `--state-dir <PATH>`
2. `PLAN_ISSUE_HOME`
3. `${XDG_STATE_HOME:-$HOME/.local/state}/plan-issue`

Run-state files live under the issue-scoped runtime root:

```text
<state-dir>/out/plan-issue-delivery/<repo-slug>/issue-<issue-number>/
  plan/
    plan.snapshot.md
    plan-branch.ref
    tasks.tsv
    issue-body.md
  runs/
    <run-id>/
      run-state.json
      events.jsonl
      inputs/
        issue-body.json
        issue-comments.json
      rendered/
        state-comment.md
        session-comment.md
        validation-comment.md
        dashboard.md
      artifacts/
        validation/
        review/
        provider/
```

Rules:

- `runs/<run-id>/run-state.json` is the current mutable local run-state file.
- `runs/<run-id>/events.jsonl` is append-only.
- `inputs/` stores provider read-back snapshots used for the latest
  reconciliation.
- `rendered/` stores dry-run or applied comment bodies for reproducibility.
- `artifacts/` stores command outputs or pointers when no project-defined
  evidence path exists.
- The controller should not write outside the issue root unless the user passes
  an explicit output path.

## Run-State Schema

Minimum `run-state.json`:

```json
{
  "schema": "plan-issue.execution-run.v1",
  "run_id": "20260526-150405-issue-123",
  "created_at": "2026-05-26T15:04:05Z",
  "updated_at": "2026-05-26T15:20:00Z",
  "repo": "owner/repo",
  "issue": 123,
  "profile": "tracking",
  "bundle": "docs/plans/example",
  "execution_state_file": "docs/plans/example/example-execution-state.md",
  "selected_scope": {
    "sprint": 1,
    "task": "1.2",
    "title": "Implement visible completeness lint"
  },
  "branch": "feat/plan-issue-visible-lint",
  "worktree": "/path/to/worktree",
  "pr": {
    "ref": "owner/repo#456",
    "url": "https://github.com/owner/repo/pull/456",
    "status": "open"
  },
  "phase": "implementing",
  "last_reconciled": {
    "at": "2026-05-26T15:18:00Z",
    "fsm_state": "RECORD_OPEN_ACTIVE",
    "dashboard_status": "current",
    "latest_comments": {
      "state": "https://github.com/owner/repo/issues/123#issuecomment-state",
      "session": "https://github.com/owner/repo/issues/123#issuecomment-session"
    }
  },
  "pending_transition": {
    "kind": "post-validation",
    "reason": "validation passed and is not issue-visible yet"
  },
  "validation": {
    "overall": "pass",
    "commands": [
      {
        "command": "cargo test -p nils-plan-issue lifecycle_record",
        "status": "pass",
        "evidence": "artifacts/validation/lifecycle-record.txt"
      }
    ]
  },
  "review": {
    "decision": "comments-only",
    "evidence": "artifacts/review/pre-merge.json"
  },
  "artifacts": {
    "latest_validation": "artifacts/validation/lifecycle-record.txt"
  },
  "notes": [
    "Local run state is secondary to provider lifecycle comments."
  ]
}
```

Required fields:

- `schema`
- `run_id`
- `repo`
- `issue`
- `profile`
- `bundle` or explicit source/plan/state files
- `execution_state_file`
- `phase`

Recommended fields:

- `selected_scope`
- `branch`
- `worktree`
- `pr`
- `last_reconciled`
- `pending_transition`
- `validation`
- `review`
- `artifacts`

## Event Schema

`events.jsonl` stores one JSON object per line:

```json
{"schema":"plan-issue.execution-event.v1","at":"2026-05-26T15:04:05Z","type":"run_started","run_id":"20260526-150405-issue-123","repo":"owner/repo","issue":123}
{"schema":"plan-issue.execution-event.v1","at":"2026-05-26T15:10:00Z","type":"task_started","task":"1.2","branch":"feat/plan-issue-visible-lint"}
{"schema":"plan-issue.execution-event.v1","at":"2026-05-26T15:15:00Z","type":"validation_recorded","command":"cargo test -p nils-plan-issue lifecycle_record","status":"pass","evidence":"artifacts/validation/lifecycle-record.txt"}
{"schema":"plan-issue.execution-event.v1","at":"2026-05-26T15:18:00Z","type":"reconciled","fsm_state":"RECORD_OPEN_ACTIVE","missing":["validation","review"]}
{"schema":"plan-issue.execution-event.v1","at":"2026-05-26T15:20:00Z","type":"checkpoint_posted","roles":["state","session","validation"],"dashboard_repaired":true}
```

Event rules:

- Append-only.
- Do not store secrets.
- Store paths or redacted previews for large artifacts.
- Provider mutation events must include the returned comment URL or a stable
  failure code.

## FSM Controller

The controller computes:

- current record state
- missing lifecycle evidence
- stale local-vs-provider fields
- safe transitions
- recommended next action
- whether visible completeness gates pass

Inputs:

- latest issue body and comments, from live provider, fixture, or explicit
  body/comment files
- plan bundle metadata
- execution-state Markdown
- run-state JSON
- optional PR/provider evidence

Output envelope:

```json
{
  "schema_version": "plan-issue.tracking.status.v1",
  "command": "tracking.status",
  "status": "ok",
  "payload": {
    "fsm_state": "RECORD_OPEN_ACTIVE",
    "issue_truth": {
      "latest_roles": ["source", "plan", "state", "session"],
      "missing_for_closeout": ["validation", "review"],
      "visible_complete": false
    },
    "run_state": {
      "run_id": "20260526-150405-issue-123",
      "phase": "implementing",
      "selected_task": "1.2"
    },
    "reconciliation": {
      "status": "warning",
      "warnings": [
        {
          "code": "run-state-validation-not-posted",
          "detail": "run-state has passing validation but issue has no validation lifecycle comment"
        }
      ]
    },
    "safe_transitions": ["post-state", "post-session", "post-validation"],
    "recommended_next_action": {
      "kind": "checkpoint",
      "roles": ["state", "session", "validation"],
      "repair_dashboard": true
    }
  }
}
```

## Proposed CLI Surface

### `plan-issue tracking run init`

Create or refresh a run-state directory.

```bash
plan-issue tracking run init \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --bundle "$PLAN_BUNDLE" \
  --task 1.2 \
  --branch "$BRANCH" \
  --format json
```

Responsibilities:

- Resolve the issue root under `state-dir`.
- Create `runs/<run-id>/`.
- Write initial `run-state.json`.
- Append `run_started`.
- Fetch or accept issue evidence and compute initial FSM state when possible.

### `plan-issue tracking status`

Read issue truth plus run state and return FSM status.

```bash
plan-issue tracking status \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --expect-visible \
  --format json
```

Responsibilities:

- Run `record audit` internally or share its parser.
- Apply visible-completeness lint when requested.
- Reconcile run state against issue evidence.
- Return safe transitions and recommended next action.
- Write provider snapshots under `inputs/` unless `--no-write` is supplied.

### `plan-issue tracking run update`

Update local run state without posting provider comments.

```bash
plan-issue tracking run update \
  --run-state "$RUN_STATE" \
  --phase validating \
  --validation-command "cargo test -p nils-plan-issue lifecycle_record" \
  --validation-status pass \
  --validation-evidence "$VALIDATION_LOG" \
  --format json
```

Responsibilities:

- Validate fields against the run-state schema.
- Append an event for every meaningful update.
- Preserve prior fields unless explicitly cleared.
- Never mutate provider state.

### `plan-issue tracking checkpoint`

Convert run state into one or more lifecycle comments and dashboard repair.

```bash
plan-issue tracking checkpoint \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --post state,session,validation \
  --repair-dashboard \
  --dry-run \
  --format json
```

Responsibilities:

- Reconcile against latest issue truth before rendering.
- Build role payloads from run state plus explicit overrides.
- Render lifecycle comments through the template registry.
- Apply visible-completeness lint before posting.
- In dry-run, write rendered bodies under `rendered/` and mutate nothing.
- In live mode, call the same internal path as `record post`, then repair the
  dashboard if requested.
- Append success or failure events with comment URLs or stable error codes.

Non-responsibilities:

- Do not create source or plan snapshots.
- Do not close the issue.
- Do not create or merge PRs.
- Do not edit implementation files.

### `plan-issue tracking close-ready`

Evaluate closeout without mutation.

```bash
plan-issue tracking close-ready \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --linked-pr "$OWNER_REPO#$PR_NUMBER" \
  --approval "$APPROVAL" \
  --expect-visible \
  --format json
```

Responsibilities:

- Run the same strict gate as `record close`.
- Verify visible completeness when requested.
- Reconcile linked PRs from issue state, run state, and explicit flags.
- Return exact blocked codes and unblock actions.
- Mutate nothing.

## Reconciliation Rules

1. Provider issue evidence wins over run state.
2. Run state can fill candidate payload fields only when the provider issue
   lacks that lifecycle evidence.
3. If run state says validation passed but the issue lacks validation evidence,
   the recommended next action is `post-validation`.
4. If the issue has newer state than run state, status reports
   `run-state-stale` and recommends `tracking run sync`.
5. If the issue is closed but run state says active, status reports
   `run-state-stale-closed`.
6. If run state names a PR that is not present in latest state payload, the
   checkpoint must either update state or refuse close readiness.
7. If visible completeness fails, checkpoint must not post live comments unless
   an explicit repair-only override is implemented later.

## Outcome Usage Model

The complete two-outcome inventory and phase boundaries are defined in
`core/skills/dispatch/plan-issue-spec/skill-family.md`.

- `deliver-plan-tracking-issue` opens or resumes the tracker, uses
  `tracking checkpoint` for session, validation, review, and final state, then
  uses `tracking close-ready` before merge/closeout decisions.
- `deliver-dispatch-plan` uses the same controller only within the dispatch
  profile and the lane boundaries assigned by the parent.

The parent outcome still owns judgment:

- selected task
- validation strength
- whether review findings are fixed or accepted
- whether a blocker requires user input
- whether an issue should remain open

The CLI owns mechanics:

- state reconciliation
- allowed transitions
- payload schema
- visible templates
- dashboard repair
- closeout gate evaluation

## Failure Codes

Initial stable codes:

| Code | Meaning | Unblock action |
| --- | --- | --- |
| `run-state-missing` | `--run-state` path does not exist. | Run `tracking run init` or pass the correct path. |
| `run-state-invalid` | JSON schema or field values are invalid. | Fix the local run-state file or use `tracking run update`. |
| `run-state-stale` | Provider issue has newer lifecycle evidence. | Run `tracking status` or `tracking run sync` before checkpoint. |
| `issue-evidence-missing` | Required issue source/plan/state evidence is absent. | Repair with `record attach` or stop for manual triage. |
| `visible-completeness-failed` | Rendered or existing comments are Profile-only or missing required visible sections. | Fix renderer/input before live post. |
| `transition-not-allowed` | Requested checkpoint role is not valid from current FSM state. | Follow `recommended_next_action`. |
| `checkpoint-empty` | Requested checkpoint would post no useful state/session/validation change. | Do not post; continue local work. |
| `close-ready-blocked` | Strict closeout gate would fail. | Follow returned closeout gate codes. |

## Testing Requirements

`nils-cli` tests:

- Unit tests for run-state schema parsing and validation.
- FSM tests for each state transition.
- Reconciliation tests for issue-newer-than-run-state and run-state-newer-than
  issue cases.
- Fixture-mode tests for `tracking status`.
- Dry-run tests for `tracking checkpoint` rendered comments.
- Live-path adapter tests should remain provider-fixture backed where possible.

Runtime-kit tests:

- Runtime smoke uses `tracking checkpoint --dry-run` once released.
- Smoke asserts rendered comments are visible-complete.
- Smoke asserts stale run-state does not overwrite newer issue evidence.
- Golden skill output references the controller commands instead of raw
  lifecycle assembly when the released CLI floor supports them.

## Migration Plan

1. Land docs in runtime-kit.
2. Create the vNext controller modules inside `plan-issue` while keeping
   the existing crate, binaries, provider abstraction, runtime layout, and
   released command compatibility.
3. Add run-state schema and parser to the vNext controller.
4. Add `tracking status` with fixture tests.
5. Add `tracking run init` and `tracking run update`.
6. Add `tracking checkpoint --dry-run`.
7. Add live `tracking checkpoint`.
8. Add `tracking close-ready`.
9. Migrate existing `record` rendering internals toward the vNext lifecycle
   registry only after the controller has fixture coverage.
10. Build a local `nils-cli` binary and validate controller output against the
   design documents.
11. Rewrite runtime-kit plan issue skills from the skill family redesign using
   the local binary for focused smoke.
12. Release `nils-cli`.
13. Update runtime-kit skills to consume the released controller surface.
14. Keep lower-level `record post`, `record repair-dashboard`, and
    `record close` documented as escape hatches and implementation primitives.

## Open Questions

1. Should `tracking checkpoint` edit the canonical execution-state Markdown?

   Resolved (nils-cli v0.31.2, sympoies/nils-cli#703): the CLI still does not
   *edit the file*, but `tracking checkpoint` now re-renders the visible
   Execution State comment header (`Status` / `Target scope` / `Current task` /
   `Next task`) from the derived payload instead of echoing the file's header
   verbatim, while preserving the `## Task Ledger` and any other authored
   sections from the file. `record open` / `record post` still emit the
   authored header verbatim. This fixes the dashboard / state-comment staleness
   where a completed plan kept its pre-flight header
   (`Status: ready-to-start`, `Tracking issue: tbd`, `… snapshot: pending`) —
   graysurf/plan-tracking-testbed#54. Deriving payloads, and now the comment
   header, is in scope; a structured *writer* that mutates the canonical
   Markdown file remains out of scope.

2. Should `tracking run update` accept arbitrary extra fields?

   Recommendation: allow an `extra` object but keep top-level fields strict.

3. Should run state live under `plan-issue` state-dir or `agent-out`?

   Recommendation: use `plan-issue` state-dir for controller-owned state and
   link to `agent-out` for larger workflow evidence artifacts.

4. Should the controller auto-post comments at phase boundaries?

   Recommendation: no. It should require explicit `tracking checkpoint` so live
   provider mutation remains deliberate.
