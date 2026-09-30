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
- [ ] **<id>** <title>: <owner/repo#number> · after <id>

### Phase 2: <name>

- [ ] **<id>** <gate: a release, deploy, or decision> · after <id>, <id>

## Dependency graph

<One `mermaid` block generated from the phase table rows; see Phase Table Row
Grammar. Never hand-edit it.>

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

## Phase Table Row Grammar

The phase table is machine-readable. A dependency is declared in a row's
`after` clause and nowhere else, and the dependency graph is generated from
the rows. Independent parsers implement this section, so it is exact. A
child's `Depends on` line repeats its row's `after` list for the reader; the
row is authoritative.

### Lines And Sections

Read the body as lines: split on line feeds, then drop trailing whitespace,
including a carriage return, from each line. No other Markdown is
interpreted, so a code fence does not hide a heading or a row.

- The phase table starts after the first line equal to `## Phase table`,
  compared without regard to ASCII case, and ends before the next line that
  starts with `## `. The `## Dependency graph` section is found the same way.
  A body without a phase table has no rows.
- Inside the phase table, a line `### <name>` starts a phase. A phase only
  groups the rows below it. Rows above the first phase heading have no phase.
- A line that starts at column one with `- [ ]`, `- [x]`, or `- [X]` is a
  row. Every other line is ignored: prose, blank lines, other bullets, deeper
  headings, and anything indented. A row is one line; never wrap it.

### Row

```text
- [ ] **<id>** <title>: <ref> (<notes>) · after <id>, <id>
```

| Part | Rule |
| --- | --- |
| Checkbox | `[ ]` is open. `[x]` or `[X]` is done. |
| `<id>` | An ASCII letter followed by any number of ASCII letters or digits. Case-sensitive, and unique within the tracker. |
| `<title>` | Free text, kept as written. Never empty. |
| `<ref>` | `owner/repo#N`, or `#N` for the tracker's own repository. A row without a ref is a gate: a release, a deploy, or a decision. |
| `(<notes>)` | Optional free text, such as the delivering PR. |
| `· after` | Optional. The ids this row depends on. The mark is U+00B7 MIDDLE DOT. |

A row starts with `- [<state>] **<id>**`, with single spaces exactly as
shown, and the rest of the line starts with a space. Parse that rest from
right to left, so that a title may contain anything. After each step, trim
spaces and tabs from both ends of the remaining text:

1. **Dependencies.** Find the last ` · after` (space, middle dot, space,
   `after`) that is followed by a space or ends the line. The text after it
   must be one or more ids separated by commas, with optional spaces around a
   comma and no id repeated; otherwise the row is malformed. Remove the
   clause.
2. **Notes.** If the remaining text ends with `)`, find the matching `(`,
   counting nested pairs. If it exists, follows a space, and encloses
   non-blank text, that text is the notes; remove the group. Otherwise the
   row has no notes and the text is unchanged.
3. **Ref.** If the remaining text ends with `: <ref>` (colon, one space,
   ref), that is the ref and the text before the colon is the title.
   Otherwise the row is a gate and the remaining text is the title. A row
   with an empty title is malformed.

In a ref, `owner` and `repo` use ASCII letters, digits, `.`, `_`, and `-`,
and `N` is a positive decimal number with no leading zero. Two rows may name
the same issue when it is delivered in two steps; their ids stay distinct.

Three consequences to write rows by:

- A parenthesised group that ends the row, before any `· after` clause, is
  always the notes, on a gate too: `Release the CLI (v2)` has the title
  `Release the CLI`.
- A ref that is not written exactly, such as `:#12` or `: #12.`, stays in the
  title and turns the row into a gate. No finding reports it.
- A title that itself ends with ` · after <word>` is read as a dependency.

```markdown
- [ ] **B1** Board leads with trackers: #21
- [x] **A1** Local projection: example/alpha#14 (PR example/alpha#16) · after A0
- [ ] **S2** `lint | graph | tick` commands: example/beta#7 · after S1
- [ ] **REL** Release containing S2 · after S2
```

### Generated Dependency Graph

The `## Dependency graph` section holds one fenced `mermaid` block. Tooling
generates the block from the rows. Never edit it by hand: change the rows,
then regenerate it. Keep nothing else in the section.

```text
graph LR
  B1
  S1
  S2
  REL{{REL}}
  S1 --> S2
  S2 --> REL
```

- The first line is `graph LR`. Every other line is indented by two spaces.
- Node lines come next, one per row in table order: `<id>`, or
  `<id>{{<id>}}` for a gate.
- Edge lines come last, one per dependency, as
  `<prerequisite> --> <dependent>`. Order them by the dependent's table
  order, then by the order of its `after` list.
- There is no styling, label, subgraph, comment, or blank line.

The block is the lines between the first line in the section equal to three
backticks followed by `mermaid` and the next line equal to three backticks.
It is current when those lines equal the generated lines exactly. Lines
outside the block are not compared. A block that is never closed is missing.

### Findings

Linters report a broken table with these codes:

| Code | Reported |
| --- | --- |
| `malformed-row` | Once per row line that does not match the grammar. Such a row contributes no id and no dependency. |
| `duplicate-id` | Once per row that reuses the id of an earlier row. |
| `unknown-dependency` | Once per `after` id that is not the id of any row. |
| `self-dependency` | Once per row that lists its own id in `after`. |
| `cycle` | Once per largest set of two or more ids in which every id depends on every other, directly or through other rows. Unknown ids and self-dependencies do not form a cycle. |
| `stale-graph` | Once, when the `mermaid` block is missing or is not current. Only a table with no other finding has a generated graph, so this code is never reported beside another. |

### Fixtures

`tests/fixtures/tracker-row-grammar/` in the `agent-runtime-kit` repository
is the conformance corpus for this grammar: valid tracker bodies with their
expected rows and graph, and invalid bodies with their expected findings. A
repository that implements a parser copies the directory unchanged and tests
against it. A change to this grammar changes the corpus in the same commit.

## Checkpoint Discipline

- Post the normal follow-up checkpoint (Checked / Result / Decision / Next) on
  a child at each boundary.
- When a child closes, tick its tracker checkbox and post one line on the
  tracker with the PR link and any release or deploy evidence.
- Record a settled decision in the tracker's Decisions section before a child
  depends on it; open decisions stay in Open decisions until decided.
- Tick a gate row when its release, deploy, or decision has happened.
- Change a dependency only in a phase row's `after` clause, then regenerate
  the dependency graph block.

## Closeout

Close the tracker only after the `work-modes.md` program closeout holds: every
child is closed or explicitly moved, key decisions are canonised in repository
docs or the devlog, and a final tracker checkpoint is posted.
