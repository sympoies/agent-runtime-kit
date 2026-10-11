# Work Mode Reference

On-demand record operation and examples for [work-mode boundaries](../work-modes.md).
Issue/tracker command syntax belongs to `issue-follow-up` and CLI help.

## Program Records

The tracker issue must contain:

- purpose and a program key;
- how to resume;
- settled decisions, with dates;
- a phase table: one checkbox row per child issue or gate (release, deploy,
  decision), with its item id, its issue link, and the ids it depends on;
- the dependency graph, derived from the phase rows;
- open decisions;
- a checkpoint log.

Each child issue must contain:

- a program line: key, item id, and the tracker link where allowed;
- the goal;
- verified current facts, with file references;
- a scope checklist;
- out of scope;
- acceptance;
- what it depends on and what it unblocks.

Operating rules:

- Open the tracker first as a placeholder, open the children linking to it,
  then fill the tracker with the real child numbers.
- The phase row is the authoritative declaration of a dependency; a child's
  depends-on line repeats it. The dependency graph is derived from the rows
  by the rules in `issue-follow-up`'s `references/tracker-row-grammar.md`,
  through the Tracker Commands in its `references/program-mode.md`. Never
  change the graph independently of the rows.
- A child issue must be enough on its own to resume work after compaction or a
  handoff.
- Children in public repositories carry no hostnames, personal names, or
  private links; reference the program key instead.
- Deduplicate against open issues first, and link an existing related issue
  rather than duplicating it.
- Each child's delivery follows `issue` mode. When a child closes, tick it on
  the tracker and post a one-line checkpoint with its PR (Tracker Commands).
- Labels: `workflow::tracking` for the tracker, `workflow::follow-up` for
  children (label mechanics are in `forge-label-taxonomy.md`).

## Program Closeout

1. Every child is closed, or explicitly moved to another record that the
   tracker names.
2. Key decisions are canonised into repository docs or the development log.
   Provider records alone are destructible (see
   [Capture Lifecycle](#capture-lifecycle)).
3. Post a final tracker checkpoint, then close the tracker.

## Capture Lifecycle

`docs/discussions/` is **staging, not storage**. It holds a capture only while
that capture has not yet reached an exit. Every capture leaves by one of three
exits, and **all three are a move or a delete**; none of them leaves the file
where it is. A capture that is part durable canon and part outstanding backlog
takes two exits: `canonise` the durable half, then open a record for the
remainder and delete what is left.

| `Exit:` | Action | When |
| --- | --- | --- |
| `open-issue` | Open a tracked record carrying the outstanding work, then `git rm` the capture | The work is real but not finished now. Any mode works: an ordinary issue is enough; do not manufacture a tracker to justify the exit. If the provider cannot accept the record, keep the capture staged until it can take a valid exit instead of creating a second tracker. |
| `canonise` | `git mv` into the owning domain doc or `docs/source/` | The content is durable canon that outlives the change |
| `retire` | `git rm` | Shipped or abandoned (the default) |

Rules that keep this true:

- **There is no "keep" state.** `Retention: Keep`, `retained as the acceptance
  source`, and every other self-declared retention are prohibited. A capture
  worth keeping is worth `canonise`, which moves it out. Treat any such
  declaration as a `canonise` that was never executed.
- **No file outside `docs/discussions/` may link to a capture inside it.** The
  invariant is exactly this: nothing outside the directory may reference a
  `docs/discussions/<YYYY-MM-DD>-<slug>.md` path.
  - A devlog entry, a provider issue, a README, or a test that points at a
    capture turns staging into storage, because deleting the capture then
    breaks a reference. Quote the conclusion instead of linking the file.
  - Exempt: the directory's own `README.md`, and a bare `docs/discussions/`
    directory mention. Neither pins a capture.
  - This invariant is what makes `retire` always safe, and it is one grep:

  ```sh
  grep -rIl --exclude-dir=.git 'docs/discussions/[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-' . \
    | grep -v '^\./docs/discussions/'
  ```
- **The exit is chosen when the capture is written**, recorded in its `Exit:`
  header, and executed by the same PR that ships the work.
- **Do not delete on the strength of a provider record alone.** Provider
  history is destructible: a repository that is deleted and re-created loses
  its issues and PRs. Before `retire`, the reasoning must already exist inside
  the repository, either as an entry in its development log (`docs/devlog/` or
  `docs/source/devlog/`) or as promoted canon. A repository with no
  development log must add one before retiring captures.

## Examples

| Situation | Mode |
| --- | --- |
| Fix a typo or a clear bug, or add a flag, finished in one pass | `direct` |
| A security-sensitive change finished in one pass | `direct`, with a full specialist review |
| A bug found while other work comes first, or its root cause unknown | `issue` |
| A small low-risk fix retained on an existing follow-up issue | `issue`, with an eligible quick review |
| A capability split into a spec, CLI, service, and rollout across repos, with phase gates | `program` |
| Several existing issues run with subagents, with no shared tracker needed | Keep their modes; ad-hoc execution |
| A migration whose lanes must integrate before main | `program/dispatch` |
| A doc that records "do Y later", not yet scheduled | Capture; mode undecided until picked up |
