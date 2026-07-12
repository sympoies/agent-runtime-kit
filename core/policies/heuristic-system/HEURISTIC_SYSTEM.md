# Heuristic System Framework

## Purpose

`agent-runtime-kit` owns the shared Heuristic System for agent workflow
improvement. The system does not train model weights; it turns concrete
workflow results into clearer skill policy, validation checks, scripts, tests,
runbooks, or retained operation records that both Codex and Claude can reuse.

## Read This When

Read this document before creating, updating, reviewing, or removing tracked
skills; changing skill contracts, scripts, references, tests, or workflow
primitives; designing evidence, failure-handling, or recovery conventions; or
using retained heuristic evidence to guide a workflow.

## Shared Root

The canonical retained-record root is:

```text
core/policies/heuristic-system/
```

Both Codex and Claude should route curated retained improvement records to this
same runtime-kit root. Product runtime homes may still contain transient
evidence, logs, caches, and ordinary `skill-usage` output, but retained
Heuristic System cases and operation records belong here unless a closer
project policy overrides this document.

When invoking the released `heuristic-inbox` CLI, use explicit paths so the
result does not depend on the caller's current working directory:

```bash
root="$PWD/core/policies/heuristic-system"
heuristic-inbox list --inbox-dir "$root/error-inbox" --include-archived --format json
heuristic-inbox verify "$root/error-inbox/<slug>" --strict --format json
heuristic-inbox verify "$root/operation-records/<slug>" --strict --format json
```

If a workflow exports `AGENT_RUNTIME_HEURISTIC_SYSTEM_ROOT`, it should point to
this directory. The released `heuristic-inbox` CLI does not consume that
environment variable directly; it is a workflow convention for deriving the
explicit `--inbox-dir` or case path passed to the CLI.

## System Shape

| Part | Role |
| --- | --- |
| Skills | Human-readable workflow policy, judgment boundaries, and usage contracts. |
| Scripts and primitives | Deterministic execution, validation, evidence capture, and guardrails. |
| Tests and checks | Regression protection for capabilities and workflow contracts. |
| Runtime evidence | Redacted records of failures, waivers, validation, review, browser, or API activity. |
| Curated inbox cases | Compact retained trackers for important unresolved workflow gaps. |
| Operation records | Compressed cross-case (cluster) rule, plus proof that retained evidence became durable system behavior. |
| Runbooks | Stable operating knowledge that should outlive one session. |
| Memory | Personal setup and recurring preferences only; not project state or factual proof. |

## Core Loop

When a skill workflow produces new operational knowledge: run the skill within
project rules, capture relevant result or failure evidence, diagnose from
concrete evidence before changing policy or code, fix or work around within
scope, promote repeated or important lessons into a durable location, and
compress accumulated exceptions into simpler contracts, tests, scripts, or
runbooks.

The goal is not to record everything. Preserve useful learning that a future
agent can verify and reuse.

## Session Closeout Procedure

Session closeout is parent lifecycle policy, not a standalone user outcome.
After the session goal is achieved, the parent performs this ordered procedure:

1. Enumerate and verify the session's skill-usage records.
2. Classify failures and reusable gaps; invoke `heuristic-inbox` directly only
   for a warranted curated case or operation record.
3. Run the evidence-archive migration dry-run and apply only under the clean
   conditions defined by the evidence-archive policy.
4. After verified migration, run archived-only source-prune dry-run and apply
   only when every candidate is expected.
5. Report retained, archived, skipped, and blocked records without committing
   raw runtime evidence into the working repository.

The typed CLIs retain their own validation and transaction boundaries. The
parent owns ordering and judgment; users should not need to request each
bookkeeping operation.

## Activation And Triage

Heuristic triage activates from one signal: a workflow result that failed or
felt wrong. Whether a named skill was active only changes which deterministic
record applies; it does not gate triage.

- `skill-usage.record.v1` is the strict envelope for named-skill workflows.
  Create it only when a named skill is invoked or selected and the workflow
  performs edits, tool/API calls, validation, delivery, external lookup, or
  durable artifact creation.
- `exit_code != 0`, stderr output, a single retry, or a corrected typo starts
  judgment, not persistence. Classify the case before writing durable
  artifacts.

| Outcome | Use when |
| --- | --- |
| Ignore | The issue was a transient typo, wrong cwd, obvious authoring miss, or immediate fix with no reusable lesson. |
| Summarize | The friction helps explain the current result but does not justify a retained repo artifact. |
| Retain or promote | The lesson is important, unresolved, repeated, skill-contract relevant, or reusable by future agents. |

Use this checklist before retaining observed friction:

- Did the same command, validation, or workaround require repeated retries?
- Did documented behavior and actual behavior disagree?
- Was the error output unclear for the action the agent needed to take?
- Did the fix require a semantic workaround rather than a simple formatting
  correction?
- Did the friction happen inside a named skill workflow or contradict a skill
  contract?
- Would a future agent benefit from a test, runbook, issue, inbox entry,
  primitive change, or skill policy update?

Skill-contract relevance lowers the retention threshold. If friction happens
inside an active named skill workflow that already requires a
`skill-usage.record.v1` envelope, record the command/script/dependency failure
in that envelope's failures list, then decide whether a curated follow-up is
also warranted. Do not commit raw stderr or ordinary authoring mistakes as
retained artifacts.

## Promotion Ladder

| Signal | Preferred durable form |
| --- | --- |
| One-off execution result | Runtime evidence or final response summary. |
| Important unresolved workflow gap | Curated `heuristic-system/error-inbox/` entry. |
| Repeated or cross-skill failure | Focused test, script fix, shared runbook, primitive, or `heuristic-system/operation-records/` entry. |
| Stable project policy | `AGENTS.md`, project docs, or repo-local runbook. |
| Personal recurring preference | Memory, when allowed by the memory policy. |

Do not promote secrets, raw credentials, unredacted logs, or temporary task
state into durable docs or memory.

## Three Layers

Keep these layers separate:

1. Runtime evidence:
   - Written by tools such as `skill-usage`, `review-evidence`,
     `test-first-evidence`, `browser-session`, or `agent-out`.
   - May live under project output directories or product state homes.
   - Not automatically committed or copied into this shared root.
   - Has its own durable, queryable retention lane — the
     agent-evidence-archive, reached via the direct `evidence migrate` CLI (see
     `core/policies/evidence-archive/EVIDENCE_ARCHIVE.md`). That archive stores
     the machine-emitted `skill-usage` records themselves and is distinct from
     this shared root, which holds curated lessons. The two lanes join through
     a record's `promotion.heuristic_inbox_case` link: an archived record can
     point at the curated case it motivated, and vice versa.
2. Curated improvement inbox:
   - Written through the direct `heuristic-inbox` CLI when a retained follow-up is justified.
   - Contains compact `ENTRY.md` case folders and optional redacted evidence
     excerpts.
   - Shared by Codex and Claude under this root.
3. Stable policy and retained operation records:
   - Tracked under `core/policies/heuristic-system/`.
   - Updated only when a lesson should outlive one workflow.

## Error Inbox

Use curated `error-inbox/` entries when an important workflow gap is observed
but not fixed in the same turn. Keep raw runtime records in their evidence
location. Commit only a short tracker entry with signal, evidence pointer,
impact, workaround, promotion criteria, and next action.

The active lifecycle is `open | promoted | wontfix`. Progress between `open`
and `promoted` is represented by `Next Action` text and linked plan, issue, or
PR references, not by extra enum values. Older entries may carry legacy
lifecycle values; the primitive reads them but does not accept them on new
writes.

An entry may carry an optional `Cluster: <kebab-slug>` field naming the
root-cause class it belongs to. When a later entry shares that class, give it
the same slug; once two or more such entries are resolved, the shared slug is
what the closeout cluster sweep groups on to propose an operation record.
Leave it unset until a sibling actually appears — a singleton cluster is noise.

After a gap is fixed, validated, and has no remaining next action, keep its
status as `promoted` or `wontfix` and move the entry under
`error-inbox/archive/YYYY/` so the active inbox stays focused. Archiving does
not delete curated evidence.

Use the nils-cli `heuristic-inbox` primitive directly to list, verify,
create, update, ingest redacted evidence, and archive these entries.

## Case Layout

Inbox cases and operation records are stored as per-case folders so the
curated tracker and optional redacted evidence can live together:

- Inbox case: `error-inbox/<slug>/ENTRY.md` plus
  `<slug>/evidence/<artifact>.md`.
- Archived inbox case:
  `error-inbox/archive/YYYY/<slug>/ENTRY.md` plus optional
  `<slug>/evidence/`.
- Operation record:
  `operation-records/<slug>/RECORD.md` plus optional `<slug>/evidence/`.
- Archived operation record:
  `operation-records/archive/YYYY/<slug>/RECORD.md` plus optional
  `<slug>/evidence/`.

Plans stay in `docs/plans/<slug>/` under their own lifecycle. A case folder may
reference a plan from `ENTRY.md` or `RECORD.md`, but it does not duplicate plan
content.

Use `heuristic-inbox ingest-evidence` to add redacted artifacts. The primitive
rejects raw `skill-usage.record.json` files, token-like content, files above
the configured size limit, and absolute local home paths that have not been
rewritten to `<workspace>`. New or updated retained cases should pass
`heuristic-inbox verify --strict` before they are committed or reported
complete.

## Operation Records

Use `operation-records/` for the **cross-case compression rule**: a single
durable rule distilled from two or more resolved cases that share one root
cause, plus the proof that retained evidence became durable system behavior.
Keep raw runtime records in their evidence location; commit only the compressed
record that names signal, evidence, diagnosis, promotion decision, durable fix,
validation, and retention outcome.

Operation records are the narrow tip of the promotion ladder, not a per-case
artifact. A single resolved case is already captured by its archived inbox
`ENTRY.md` plus the test, script fix, runbook update, or skill policy it
promoted into; a separate single-case record only duplicates that. Reserve an
operation record for the value those cannot hold: a reusable cross-case rule a
future agent applies when writing *new* similar code (for example
`ci-watch-exact-commit-keying`), plus audit proof that the loop operated across
a broader surface. When a lesson is fully enforced by one mechanical gate or
lives inside one released CLI, prefer that gate/CLI plus an archived inbox entry
over a new record.

### Lifecycle

Operation records are born resolved (the fix already landed), so they do not use
the inbox `open → promoted` lifecycle. Their state tracks whether the rule is
still load-bearing, recorded in the `## Status` block:

- `Status: active | superseded | retired`.
- Optional `Cluster: <kebab-slug>` names the shared root-cause class, matching
  the `Cluster:` field on the inbox entries it compresses; it is the grouping
  key the closeout cluster sweep reads.
- Optional `Enforced-by: <gate/CLI>` records a mechanical enforcer — a CI gate,
  hook, or released CLI behavior — that now upholds the rule.
- Optional `Superseded-by: <path-or-record>` points at the gate, CLI, or broader
  re-compressed record that replaced this one.

A record stops being load-bearing — becoming a `superseded` / `retired` archive
candidate — when its rule is mechanically enforced (an agent calls the gate/CLI
instead of remembering the rule), its governed surface is retired, or it is
absorbed into a broader re-compressed record. Archive retired records under
`operation-records/archive/YYYY/<slug>/`, mirroring the inbox archive; archiving
preserves the record as audit history and never deletes it. Use
`heuristic-inbox archive` with the operation-record path and re-run
`heuristic-inbox verify --strict` on the archived path.

## Compression Rule

Heuristic Systems decay when they only grow. When a skill accumulates several
local exceptions, retries, or failure notes: group by root cause, keep the
smallest stable rule that explains the group, replace repeated prose with a
test, guardrail, or script when practical, and archive resolved inbox entries
once they are `promoted` or `wontfix` with no remaining next action.

Add broader heuristic-system tooling only after several related archived inbox
or operation records prove a repeatable command surface. Until then, keep
compression work inside the narrow workflow skill or implementation plan that
owns the records.

## Boundaries

- Skills own workflow framing, judgment, and repo-local policy.
- nils-cli primitives own deterministic record writing, validation,
  redaction-aware evidence ingestion, and machine-checkable execution.
- `agent-docs` owns read-first context selection and hard-gate preflight.
- Runtime evidence is not automatically a repo artifact. Commit only curated
  evidence or docs that project policy expects to retain.
