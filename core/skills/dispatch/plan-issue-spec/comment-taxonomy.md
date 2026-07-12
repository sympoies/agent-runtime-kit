# Plan Tracking Issue Comment Taxonomy

## Status

- Status: implemented; canonical design
- Date: 2026-05-26
- Owner surface: lightweight plan-tracking issue workflow
- Primary consumers:
  - `core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera`
  - `sympoies/nils-cli:crates/plan-issue`
- Related controller spec:
  - `core/skills/dispatch/plan-issue-spec/run-state-controller.md`
- Related skill family spec:
  - `core/skills/dispatch/plan-issue-spec/skill-family.md`

## Purpose

This document defines the complete comment taxonomy and user-visible templates
for lightweight plan-tracking issues. Its purpose is to stop issue comments from
drifting across agents, skills, and CLI releases.

The issue body is not a lifecycle comment. It is a mutable dashboard repaired
from lifecycle evidence. Durable tracking evidence lives in append-only
comments carrying `plan-issue-record:v2` markers.

## Source Inputs

- [U1] The user requested a full redesign of the plan-tracking comment
  workflow, including all comment types, templates, timing rules, and a path
  back into `nils-cli`.
- [F1] The runtime-kit tracking outcome routes lifecycle writes through
  `plan-issue record open`, `record post`, `record repair-dashboard`, and
  `record close`.
- [F2] `docs/source/nils-cli-surface.md` pins the consumed `plan-issue`
  lifecycle surface and names the canonical marker family.
- [F3] `sympoies/nils-cli:crates/plan-issue/src/commands/record.rs`
  defines the current record roles and `--task-ledger-display` modes.
- [F4] `sympoies/nils-cli:crates/plan-issue/src/lifecycle_record.rs`
  defines the current headings, payload schema, visible renderers, and hidden
  payload carrier.
- [I1] The redesign should preserve the current structured payload model while
  making visible comment bodies deterministic enough for humans and tests.

Canonical marker family:

```text
plan-issue-record:v2 role=<source|plan|state|session|validation|review|closeout> profile=<tracking|dispatch>
```

## Design Principles

1. One lifecycle role means one comment template.
2. Every lifecycle comment starts with exactly one v2 marker on the first
   non-empty line.
3. Every lifecycle comment carries exactly one hidden payload carrier.
4. The hidden payload is the machine source of truth for audit, dashboard
   repair, and closeout gates.
5. The visible body is the human source of truth for review. A Profile-only
   comment is invalid even when the hidden payload parses.
6. The latest valid comment per role wins for machine state. Older comments
   remain historical evidence.
7. `source` and `plan` are snapshot comments created by `record open` or
   `record attach`, not progress updates.
8. `state` is the durable task ledger. It is posted from the canonical
   execution-state Markdown plus a matching structured payload.
9. `session` records work actually performed in an execution session. A
   `## Session Log` section inside state Markdown is useful context but does
   not satisfy session evidence.
10. `validation`, `review`, and `closeout` comments must expose role-specific
    visible evidence generated from structured payloads.
11. `closeout` is owned by `plan-issue record close`. Skills must not hand-post
    final closeout comments.
12. Dashboard repair follows lifecycle comments. It does not create a separate
    durable record.
13. When available, `plan-issue tracking checkpoint` is the preferred
    agent-facing entrypoint for progress comments; `record post` remains the
    lower-level lifecycle primitive.

## Comment Inventory

| Surface | Role | Owner command | Required for closeout | Purpose |
| --- | --- | --- | --- | --- |
| Issue body dashboard | none | `record open`, `record repair-dashboard`, `record close` | indirectly | Mutable scan surface with links to latest lifecycle comments. |
| Source Snapshot | `source` | `record open` / `record attach` | yes | Freezes the source or review document used to create the plan. |
| Plan Snapshot | `plan` | `record open` / `record attach` | yes | Freezes the implementation plan. |
| Execution State | `state` | `tracking checkpoint` / `record post --kind state` | yes | Durable task ledger, status, blockers, PR refs, and next action. |
| Execution Session | `session` | `tracking checkpoint` / `record post --kind session` | yes for delivery closeout | Records a meaningful work session or handoff checkpoint. |
| Validation Evidence | `validation` | `tracking checkpoint` / `record post --kind validation` | yes | Records commands, pass/fail/partial status, evidence, and waivers. |
| Review Evidence | `review` | `tracking checkpoint` / `record post --kind review` | yes when review is required | Records pre-merge review decision, lenses, findings, and dispositions. |
| Tracking Issue Closeout | `closeout` | `record close` | yes | Final completion evidence, approval, linked PR verification, and issue close. |

## Controller Inputs

The templates below can be rendered from explicit payload files, but the
preferred agent-facing path is the run-state controller:

```bash
plan-issue tracking checkpoint \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --post state,session,validation \
  --repair-dashboard \
  --format json
```

Controller rendering rules:

- `run-state.json` supplies selected task, branch, PR, validation, review, and
  artifact pointers.
- The canonical execution-state Markdown supplies visible state body and Task
  Ledger content.
- Provider issue comments remain durable truth; stale run state must be
  reconciled before live posts.
- The same role templates apply whether the body is rendered by `tracking
  checkpoint` or lower-level `record post`.

## Shared Comment Frame

Every lifecycle comment uses this outer frame:

```markdown
<!-- plan-issue-record:v2 role=<role> profile=tracking -->

## <Role Heading>

- Profile: tracking
<role-specific visible content>

<!-- plan-issue-record-payload:hex:<hex-encoded plan-issue-record.payload.v2 JSON> -->
```

Rules:

- The marker must be the first non-empty line.
- The payload carrier is hidden HTML-comment content.
- New comments must not render the legacy visible
  `plan-issue-record-payload` fenced JSON block.
- The role heading must match the role-specific heading below.
- The visible body must contain more than `- Profile: tracking`.

## Source Snapshot Template

Created when the tracking issue is opened or attached to an existing issue.

```markdown
<!-- plan-issue-record:v2 role=source profile=tracking -->

## Source Snapshot

- Profile: tracking
- Path: `docs/plans/<slug>/<slug>-discussion-source.md`
- Commit: `<full-sha>`
- Summary: <one-line source summary>
- Snapshot mode: local committed Markdown

<details>
<summary>Source snapshot</summary>

<verbatim source or review document content>

</details>

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "path": "docs/plans/<slug>/<slug>-discussion-source.md",
  "commit": "<full-sha>",
  "title": "<optional title>",
  "summary": "<optional summary>"
}
```

Posting policy:

- Post once at issue creation or attach.
- Re-post only when repairing an older issue that lacks v2 evidence or when a
  new source document supersedes the old source by explicit decision.

## Plan Snapshot Template

Created when the tracking issue is opened or attached to an existing issue.

```markdown
<!-- plan-issue-record:v2 role=plan profile=tracking -->

## Plan Snapshot

- Profile: tracking
- Path: `docs/plans/<slug>/<slug>-plan.md`
- Commit: `<full-sha>`
- Summary: <one-line plan summary>
- Snapshot mode: local committed Markdown

<details>
<summary>Plan snapshot</summary>

<verbatim plan content>

</details>

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "path": "docs/plans/<slug>/<slug>-plan.md",
  "commit": "<full-sha>",
  "title": "<optional title>",
  "summary": "<optional summary>"
}
```

Posting policy:

- Post once at issue creation or attach.
- Re-post only when the plan itself is intentionally revised and the issue
  should use the revised plan as current evidence.

## Execution State Template

Execution State is the canonical progress comment. It must be generated from
the canonical `<slug>-execution-state.md` file through
`record post --kind state --execution-state-file`.

On the `tracking checkpoint` path, the visible header (`Status` / `Target
scope` / `Current task` / `Next task`) is re-rendered from the derived payload
(nils-cli v0.31.2+), while the `## Task Ledger` and any other authored sections
are taken from the file; `record open` / `record post` emit the authored header
verbatim. See run-state-controller Open Question #1.

Non-final progress state:

```markdown
<!-- plan-issue-record:v2 role=state profile=tracking -->

## Execution State

- Profile: tracking
- Status: in-progress
- Target scope: <issue-backed scope>
- Current task: <task or sprint currently being executed>
- Next task: <next action>
- Last updated: YYYY-MM-DD
- Branch: <branch>
- PR: <owner/repo#number or pending>
- Source document: docs/plans/<slug>/<source-file>
- Plan document: docs/plans/<slug>/<slug>-plan.md

## Task Ledger

<details>
<summary>Show task ledger</summary>

| ID | Status | Task | Notes |
| --- | --- | --- | --- |
| 1.1 | in-progress | <task title> | <short note> |
| 1.2 | pending | <task title> |  |

</details>

## Blockers

- <blocker or `None`>

## Validation

| Command | Status | Evidence |
| --- | --- | --- |
| `<command>` | pass|fail|skipped | <path or URL> |

<!-- plan-issue-record-payload:hex:<payload> -->
```

Final pre-closeout state:

```markdown
<!-- plan-issue-record:v2 role=state profile=tracking -->

## Execution State

- Profile: tracking
- Status: complete
- Target scope: <issue-backed scope>
- Current task: complete
- Next task: closeout
- Last updated: YYYY-MM-DD
- Branch: <branch>
- PR: <owner/repo#number>

## Task Ledger

| ID | Status | Task | Notes |
| --- | --- | --- | --- |
| 1.1 | done | <task title> | <evidence> |
| 1.2 | deferred | <task title> | <reason and follow-up> |

## Validation

| Command | Status | Evidence |
| --- | --- | --- |
| `<command>` | pass | <path or URL> |

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "status": "in-progress|complete|blocked",
  "target_scope": "<issue-backed scope>",
  "current": "<current task or state>",
  "next_action": "<next task or unblock action>",
  "tasks": [
    {"id": "1.1", "status": "done", "title": "<task title>"},
    {"id": "1.2", "status": "in-progress", "title": "<task title>"},
    {"id": "1.3", "status": "pending|in-progress|done|deferred|blocked|waived", "title": "<task title>"}
  ],
  "prs": [
    {"ref": "owner/repo#123", "url": "<url>", "status": "open|merged|closed"}
  ],
  "blockers": ["<blocking fact>"],
  "links": {
    "source": "<url>",
    "plan": "<url>",
    "previous_state": "<url>"
  }
}
```

`tasks[]` is **accumulative**: every `state` post carries the full per-task
table from the canonical execution-state `## Task Ledger` (every task known at
post time), not just the current/selected task, and `tasks[].status` shares the
ledger vocabulary (`pending|in-progress|done|deferred|blocked|waived`). The
canonical payload schema is owned by `nils-cli`
(`crates/plan-issue/docs/specs/issue-backed-plan-record-contract-v2.md`);
this taxonomy mirrors it.

Posting policy:

- Post initial state during `record open` or `record attach`.
- Post through `tracking checkpoint` before implementation when the selected
  task, current status, or next action is not already issue-visible.
- Post through `tracking checkpoint` after meaningful task ledger changes, PR
  changes, blockers, or handoff decisions.
- Post a final expanded state before closeout.
- `record open` posts the initial state with `--task-ledger-display open` (an
  open `<details open>` fold) so the full Task Ledger is visible when the issue
  loads while the collapse toggle stays.
- Use `--task-ledger-display collapsed` for intermediate updates.
- Use `--task-ledger-display expanded` for the final pre-closeout state (raw
  rows, no `<details>` wrapper — required by visible-completeness lint).

## Execution Session Template

Execution Session records a work session, not every file edit.

```markdown
<!-- plan-issue-record:v2 role=session profile=tracking -->

## Execution Session

- Profile: tracking
- Summary: <what was done in this session>

### Highlights

- <meaningful implementation, investigation, or handoff note>
- <branch, PR, or issue-visible decision>

### Links

- State: <latest state comment URL>
- PR: <PR URL or pending>
- Artifacts: <validation or evidence path>

### Session Fields

- branch: <branch>
- pr: <owner/repo#number or pending>
- selected_task: <task id>

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "summary": "<one-line summary>",
  "highlights": ["<short bullet>"],
  "links": {"state": "<url>", "pr": "<url>"}
}
```

Posting policy:

- Post through `tracking checkpoint` after a meaningful implementation or
  investigation block.
- Post before merge or final success when closeout readiness is being claimed.
- Post on handoff, interruption, or blocker if the next agent needs issue-visible
  context.
- Do not post an empty "started work" session without useful information.

## Validation Evidence Template

Validation Evidence records command outcomes. It can be pass, partial, or fail.

```markdown
<!-- plan-issue-record:v2 role=validation profile=tracking -->

## Validation Evidence

- Profile: tracking
- Overall: pass|partial|fail

| Command | Status | Evidence |
| --- | --- | --- |
| `<exact command>` | pass|fail|skipped | <artifact path, URL, or short reason> |

### Waivers

- `<command>`: <why it was not run or why failure is accepted>

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "overall": "pass|partial|fail",
  "commands": [
    {"command": "<exact command>", "status": "pass|fail|skipped", "evidence": "<optional path or URL>"}
  ],
  "waivers": [
    {"command": "<command>", "reason": "<reason>"}
  ]
}
```

Posting policy:

- Post through `tracking checkpoint` whenever validation status changes the
  issue-visible truth.
- Post failures when they block or redirect work.
- Post the final passing validation before closeout.
- Use one validation comment per coherent validation checkpoint, not one
  comment per trivial command.

## Review Evidence Template

Review Evidence records the pre-merge review gate or explicit review outcome.

```markdown
<!-- plan-issue-record:v2 role=review profile=tracking -->

## Review Evidence

- Profile: tracking
- Decision: approve|request-changes|comments-only
- Lenses: testing, maintainability
- Outcome comment: <provider comment URL or retained evidence path>

| ID | Severity | Disposition | Summary |
| --- | --- | --- | --- |
| F1 | major | fixed|residual|follow-up|deferred|no-action | <finding summary> |

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "decision": "approve|request-changes|comments-only",
  "lenses": ["testing", "maintainability"],
  "findings": [
    {
      "id": "F1",
      "severity": "blocker|major|minor|nit",
      "disposition": "fixed|residual|follow-up|deferred|no-action",
      "summary": "<finding summary>"
    }
  ],
  "outcome_comment_url": "<optional URL>"
}
```

Posting policy:

- Post through `tracking checkpoint` after the review gate runs.
- Re-post when findings are fixed or explicitly dispositioned.
- Do not claim closeout readiness when blocker or major residual findings remain.

## Tracking Issue Closeout Template

Tracking Issue Closeout is produced by `plan-issue record close` after the
strict gate passes.

```markdown
<!-- plan-issue-record:v2 role=closeout profile=tracking -->

## Tracking Issue Closeout

- Profile: tracking
- Final status: complete
- Approver: <login or source>
- Approval: <comment URL or approval text>
- Final validation: <validation evidence URL>
- Notes: <optional closeout note>

### Non-required Check Override

- Reason: <reason, only when used>
- Observed failures: <non-required failures, only when used>

| PR | Merge SHA | Checks | Required | Non-required failures |
| --- | --- | --- | --- | --- |
| <PR URL or ref> | <sha> | pass|fail|none | pass|fail|none (<count>) | none |

<!-- plan-issue-record-payload:hex:<payload> -->
```

Payload data:

```json
{
  "final_status": "complete",
  "approval": {"comment_url": "<optional URL>", "approver": "<optional login>"},
  "linked_prs": [
    {
      "ref": "owner/repo#123",
      "url": "<optional URL>",
      "merge_sha": "<sha>",
      "checks": "pass|fail|none",
      "required_state": "pass|fail|none",
      "required_count": 2,
      "non_required_failures": []
    }
  ],
  "non_required_check_override": {"reason": "<reason>", "observed_non_required_failures": []},
  "final_validation_url": "<optional URL>",
  "notes": "<optional note>"
}
```

Posting policy:

- Post exactly through `plan-issue record close`.
- Post only after source, plan, complete state, session, validation, review,
  linked PR, and approval evidence satisfy the closeout gate.
- If closeout fails, do not post a manual closeout comment. Leave the issue open
  and post state/session/validation evidence for the blocker when useful.

## Dashboard Template

The issue body is a derived dashboard. It is mutable and not the durable task
ledger.

Required dashboard behavior:

- Current records use `## Current Dashboard`.
- Closed records use `## Final Dashboard`.
- Durable record links point to the latest valid lifecycle comments.
- Missing lifecycle roles display `pending`.
- Dashboard repair is idempotent.

Agents must run dashboard repair after every lifecycle update that changes the
latest role URL or status:

```bash
plan-issue --repo "$OWNER_REPO" --format json record repair-dashboard \
  --issue "$ISSUE"
```

## Invalid Comment Shapes

The following shapes are invalid for new lifecycle comments:

- Marker plus hidden payload with no visible role-specific content.
- Visible fenced `plan-issue-record-payload` JSON as the normal payload carrier.
- `state` comments generated from a short ad hoc summary instead of the
  canonical execution-state file.
- A collapsed final state Task Ledger.
- A closeout comment posted through `record post` or raw provider comments.
- A session hidden inside state Markdown with no `role=session` lifecycle
  comment when closeout readiness is claimed.
