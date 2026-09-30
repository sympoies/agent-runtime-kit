# Work Modes

## Purpose

This delivery-phase policy decides how much durable tracking a piece of work
needs. It does not limit how an agent plans. Pick the lightest mode that holds
the state the work actually needs. Keep routine `direct` classification to
yourself; surface a mode only when a provider artifact, delivery, or an
ambiguous escalation is actually involved.

It is a `project-dev` delivery document in `AGENT_DOCS.toml`. `AGENT_HOME.md`
carries only the routing invariant; this file owns the modes and their
artifact boundaries. It supersedes the retired numbered tier ladder.

## Three Independent Axes

| Axis | Question | Values |
| --- | --- | --- |
| Tracking mode | Which durable record does the work need? | `direct` / `issue` / `program` |
| Execution | Who does the work? | `inline` / `subagents` / `main-agent` |
| Review depth | How risky is the diff? | Risk-selected quick or full review (unchanged) |

Choose each axis separately. A `program` can run `inline`. A `direct` change
can still require full specialist review.

## Tracking Modes

| Mode | Tracking artifact | Typical scale | Choose when |
| --- | --- | --- | --- |
| `direct` | None; the PR (or one-off answer) is the record | One session, one repo, 0–3 PRs, hours | It finishes now and needs no record beyond this chat |
| `issue` | One provider issue with a comment timeline | 1–3 sessions, mostly one repo, 1–3 PRs, days, at most one release or deploy gate | Any of: deliberately deferred; needs investigation before the fix is known; a blocker to record while routing around it; a handoff; cross-session continuity or visibility to others; a recurring loop that needs a timeline |
| `program` | One tracker issue plus two or more child issues, each child in `issue` mode | Many sessions or agents, may span repos, many PRs, weeks | Two or more independently deliverable and reviewable units, **and** at least one of: ordering dependencies between them; spans repositories; authorization gates between phases (release, deploy, decision); expected to outlive one session's context |

Rules for choosing and changing mode:

- Start at `direct`. Move up only when a trigger in the table fires.
- Size alone never moves work up. When a PR is too large for review to
  converge, split it into several reviewable PRs within the same mode; see
  [Reviewable size](#cross-cutting-rules).
- When torn between `issue` and `program`, choose `issue`. An issue can later
  become a program child when a second unit appears.
- Downgrade when the need shrinks. A program left with one open child closes
  its tracker (see [Program Closeout](#program-closeout)) and continues that
  child in `issue` mode.

### Program specializations

These are retained, but they are not the default. Use one only when its
condition holds.

| Specialization | Required when | Outcome skill |
| --- | --- | --- |
| `program/dispatch` | Lanes must integrate on a shared branch before landing on main, because intermediate lane states cannot land one by one | `deliver-dispatch-plan` |

A plain `program` covers the rest. Its children merge independently, and its
tracker is the plan.

## Authority

- Choosing a mode is autonomous. Classify ordinary work as `direct` and
  proceed without announcing a mode, proposing a tracker, or pausing.
- Creating any provider artifact (an issue, a tracker, or a child issue) needs
  the user's decision first. When a trigger fires, name the durable state the
  work needs and the lightest matching mode, then ask.
- If the choice is materially ambiguous, recommend the cheaper safe option and
  ask only the question that changes the artifact or the authority.
- Re-triage when evidence changes. Escalating keeps the work already done and
  its review depth; it does not add ceremony retroactively.

## Execution Mapping

| Mode | Default execution | With `main-agent` |
| --- | --- | --- |
| `direct` | `inline` | Delegate one worker only on an explicit `delegate-all` request |
| `issue` | `inline` or one delegated worker | One isolated worker; the same issue remains the outcome |
| `program` | `inline`, or `main-agent` for waves of parallel children | See below |
| `program/dispatch` | Per `deliver-dispatch-plan` | One worker per lane; the dispatch acceptance boundary remains |

A `program` run under `main-agent` works like this:

- **One run per wave**, not one run for the whole program. Gates between waves
  (release, deploy, decision) need fresh user authority.
- **One worker per child issue.** Each packet names its child issue, and the
  packet's `depends_on` mirrors the tracker's dependency graph.
- **The tracker is the only authoritative plan.** Run state is execution
  state; do not keep a second authoritative dependency graph in it.
- **Accept before merge**, against the tracker's settled decisions. Return
  code findings to the same worker. After acceptance, tick the tracker and
  post a checkpoint.
- **Do not release or upgrade** the runtime the controller or its workers use
  while a run is active. Schedule releases between waves.

Subagents are an execution mode, not a tracking mode. Running existing issues
with subagents keeps their mode unless a shared tracker is actually needed.

## Program Records

The tracker issue must contain:

- purpose and a program key;
- how to resume;
- settled decisions, with dates;
- a phase table: one checkbox row per child issue or gate (release, deploy,
  decision), with its item id, its issue link, and the ids it depends on;
- the dependency graph, generated from the phase rows;
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
- Declare a dependency only on its phase row. The dependency graph is derived
  output: regenerate it from the rows and never edit it by hand. The row
  grammar is in `issue-follow-up`'s `references/program-mode.md`.
- A child issue must be enough on its own to resume work after compaction or a
  handoff.
- Children in public repositories carry no hostnames, personal names, or
  private links; reference the program key instead.
- Deduplicate against open issues first, and link an existing related issue
  rather than duplicating it.
- Each child's delivery follows `issue` mode. When a child closes, tick it on
  the tracker and post a one-line checkpoint with its PR.
- Labels: `workflow::tracking` for the tracker, `workflow::follow-up` for
  children (label mechanics are in `forge-label-taxonomy.md`).

## Program Closeout

1. Every child is closed, or explicitly moved to another record that the
   tracker names.
2. Key decisions are canonised into repository docs or the development log.
   Provider records alone are destructible (see
   [Capture Lifecycle](#capture-lifecycle)).
3. Post a final tracker checkpoint, then close the tracker.

## Cross-Cutting Rules

- **Delivery: PR is the default provider path, not default authority.** Once
  provider delivery is explicitly requested or owned by an approved retained
  workflow, a PR squash-merged into `main` is the default. `direct` uses a PR
  only when provider delivery is explicitly requested. Never infer direct-main
  authority from change size, urgency, or words such as "small" or "hotfix".
  That route is one signed commit from a non-default managed worktree through
  `forge-cli repo push-default`, and its remote-SHA receipt replaces the PR
  record. PR bodies stay grounded in the diff with at least `## Summary` +
  `## Test plan`, produced by the active delivery skill or
  `agent-runtime pr-body render`.
- **Default-branch is local completion, not delivery.** When the maintainer
  explicitly requests one local-only commit on the primary default checkout,
  `semantic-commit default-branch` may create exactly one signed commit and an
  outside-checkout receipt. It opens no issue or PR and performs no provider
  mutation; the receipt remains `provider_delivered=false`. Direct-main and
  default-branch are `direct`-only, need exact current-task authority, and
  their mechanics are owned by `git-delivery.md`.
- **Reviewable size: split what review cannot converge.** When one PR's review
  surface is too large to converge, and findings or threads accumulate until
  the PR is "reviewed forever, never merged", split it into independently
  reviewable units (stacked or sequential PRs, or program children). This is a
  delivery decision and does not change the mode by itself. See
  `core/policies/review-thread-convergence.md` for dispositioning accumulated
  threads.
- **Review profile is not a mode.** Tracking need does not determine code risk.
  `deliver-pr` selects the smallest safe pre-merge profile from the outer
  lifecycle, changed scope, validation, existing review state, and reviewer
  confidence.
  - Eligible `direct` or `issue` routine diffs, including program children, may
    use a quick review whose clean `pass` is terminal for the reviewed head.
  - `program/dispatch` PRs and any risk-triggering diff,
    keep the full specialist gate.
  - Escalating review depth never changes the mode.
- **Implementation-readiness doc is an optional spec, not a mode.** A
  `discussion-to-implementation-doc` capture records converged intent: scope,
  acceptance criteria, and validation plan.
  - Its default home is `docs/discussions/<YYYY-MM-DD>-<slug>.md`.
  - It can attach to any mode: linked in the PR body for `direct`, or from the
    issue or tracker otherwise.
  - The mode is chosen when the work is picked up. A capture not yet scheduled
    is mode-undecided backlog, and retiring it never requires manufacturing a
    tracker.

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

## Relationship To Nearby Surfaces

- `AGENT_HOME.md` keeps routine `direct` work internal and routes here only
  when durable delivery state or an ambiguous escalation is in play.
- `issue-follow-up` owns `issue` records and program tracker and child
  records. `deliver-dispatch-plan` owns coordinated dispatch.
  `discussion-to-implementation-doc` owns captures.
- `deliver-pr` owns default provider PR/MR delivery. `git-delivery.md` owns the
  direct-main and default-branch exceptions.
- `main-agent-mode` owns execution under `main-agent`; this file owns which
  mode that execution serves.
- `forge-label-taxonomy.md` owns label selection.
