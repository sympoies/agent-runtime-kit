# Program Mode Reference

Templates and operating rules for `issue-follow-up` program mode. The mode
selection itself (when work is a `program`, its closeout, and its
specializations) belongs to `core/policies/work-modes.md`.

## Creation Order

1. Pick a stable program key, for example `<topic>-<YYYY-MM>`.
2. Deduplicate: search open issues in every target repository for the same
   outcome. Link a clear existing match as a related or prerequisite child
   instead of opening a duplicate, and post one comment on it that names the
   program.
3. Open the tracker first with a short placeholder body so children can link
   to its number. Label it `workflow::tracking`.
4. Open each child with the child template. Label children
   `workflow::follow-up` plus the usual `type::`, `area::`, `state::`,
   `priority::`, and `size::` labels. Use `state::blocked` for a child whose
   dependencies are open.
5. Replace the tracker placeholder with the full tracker template, now listing
   the real child numbers, and post the first checkpoint on the tracker.

When `forge-cli` runs outside a checkout of the target repository (for example
from a scratch directory), pass `--provider github --repo owner/name`
explicitly; remote detection otherwise fails and nothing is created. Confirm
every create returned a URL before continuing, and list open issues before
retrying a failed create so a retry cannot duplicate one.

## Public Repositories

A child in a public repository must not contain hostnames, network or tailnet
details, personal names, private repository names, or links to private
issues. Refer to the program by its key and item id instead. A private tracker
may link public children freely.

## Tracker Template

```markdown
## Purpose

Program key **`<key>`**. <What outcome the program delivers and why.>

## How to resume (read this first)

1. Read this body, then the latest checkpoint comment on this issue.
2. Pick the first unchecked item whose dependencies are all checked; items in
   one phase may run in parallel.
3. Read that child issue and its latest checkpoint; each child is
   self-contained.
4. Deliver through the owning repository's normal workflow.
5. Checkpoint the child at each boundary; when it closes, tick it here and add
   a one-line checkpoint with the PR and release or deploy evidence.
6. <Live changes and authority that planning does not grant.>

## Decisions (settled YYYY-MM-DD)

- <Decision, stated so a child can be checked against it.>

## Phase table

### Phase 1: <name>
- [ ] **<id>** <title>: <owner/repo#number>

## Dependency graph

<mermaid graph or bullet list of edges>

## Open decisions

- <Decision still needed, and which item it blocks.>

## Checkpoint log

Progress is recorded as comments on this issue. Keep the phase table in sync
with closed children.
```

## Child Template

```markdown
## Program

Program key `<key>` (tracker: <link where allowed>), item **<id>**.
Depends on <ids>. <Parallelism note.>

## Goal

<One observable outcome.>

## Current facts

- <Verified fact with a repository-relative file reference.>

## Scope

- [ ] <Concrete, checkable step.>

## Out of scope

<What belongs to other items.>

## Acceptance

- <Test-first, validation, and live-evidence requirements.>

## Unblocks

<ids this item unblocks.>
```

## Checkpoint Discipline

- Post the normal follow-up checkpoint (Checked / Result / Decision / Next) on
  a child at each boundary.
- When a child closes, tick its tracker checkbox and post one line on the
  tracker with the PR link and any release or deploy evidence.
- Record a settled decision in the tracker's Decisions section before a child
  depends on it; open decisions stay in Open decisions until decided.

## Closeout

Close the tracker only after the `work-modes.md` program closeout holds: every
child is closed or explicitly moved, key decisions are canonised in repository
docs or the devlog, and a final tracker checkpoint is posted.
