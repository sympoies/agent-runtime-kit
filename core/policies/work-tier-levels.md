# Work Tier Levels

## Purpose

This policy defines how to size the *tracking and delivery machinery* a unit of
work gets, and how the agent should triage that choice proactively. It exists to
make one decision fast and consistent: **for any work request, pick the lowest
applicable tier and use that tier's method — never run light work through a
heavy tier.**

It is declared as a `project-dev` document in `AGENT_DOCS.toml` (home scope),
so the harness injects it through the hook preflight when implementation work
starts. `AGENT_HOME.md` carries the always-on short directive; this file is the
full ladder, judge, methods, and behavior contract.

## Principle

Work has two independent axes. Do not collapse them:

- **Delivery axis — PR by default.** Almost any code change lands as a PR
  squash-merged into `main`. The PR is the durable record of *what changed and
  why*. The only exception is an explicitly authorized L0 direct-main delivery
  using the governed one-commit receipt path in `git-delivery.md`.
- **Tracking axis — the tier.** How much durable, cross-time tracking the
  problem or plan needs: none, a follow-up issue, or a plan tracking issue. This
  axis is what the tiers below measure.

The tiers are ordered by overhead. Pick the lowest tier that satisfies the
work's actual needs, and escalate only when a concrete trigger fires. Size alone
is never a reason to escalate — *"state worth tracking"* is.

## The Ladder

| Tier | Name | Tracking artifact | Primary method |
| --- | --- | --- | --- |
| **L0** | Untracked delivery | None | `semantic-commit` → `deliver-pr` by default; governed direct-main only when explicitly authorized |
| **L1** | Follow-up issue | One provider issue + comment timeline | `issue-follow-up` |
| **L2** | Plan tracking issue | Plan bundle + issue + lifecycle | `deliver-plan-tracking-issue` |
| **L3** | Dispatch plan | Shared dispatch issue + lanes | `deliver-dispatch-plan` |

L3 is for one unit of work that must be split across multiple parallel lanes
or subagents **and** needs one shared coordination spine — a shipped, exercised
path, not a placeholder. Reach for it when the work is too broad for one lane to
hold and its lane state, PRs, reviews, and closeout must be coordinated through
one dispatch issue; the user decides whether the scale warrants running it.

## Cross-Cutting Concepts

Two things ride alongside the ladder and must not be mistaken for tiers:

- **PR = the default delivery path.** L1–L3 always deliver through PRs; L0 does
  too unless the maintainer explicitly requests direct commit and push to the
  default branch in the current task. Never infer that exception from change
  size, urgency, or words such as "small" or "hotfix". The direct route is one
  signed commit from a non-default managed worktree through `forge-cli repo
  push-default`; its remote-SHA receipt replaces the PR record. For PR delivery,
  keep the body grounded in the diff with at least `## Summary` + `## Test plan`,
  produced by the active delivery skill / `agent-runtime pr-body render`.
- **Reviewable size — split what review cannot converge.** A change is sized for
  review as well as for tracking. When one PR's review surface is too large to
  converge — enough findings or threads accumulate that reviewers churn and the
  PR is "reviewed forever, never merged" — that is the signal to split it into
  independently-reviewable units (stacked or sequential PRs, or L3 lanes under a
  shared dispatch issue), not to push one giant PR through. This is a
  delivery-axis decision and does not by itself change the tier: a large L0/L1
  change stays L0/L1 but ships as several reviewable PRs. See
  `core/policies/review-thread-convergence.md` for dispositioning the threads
  that do accumulate.
- **Implementation-readiness doc = an optional spec, not a tier.** A
  `discussion-to-implementation-doc` artifact (default home
  `docs/discussions/<YYYY-MM-DD>-<slug>.md`; inside the
  `docs/plans/<YYYY-MM-DD>-<slug>/` bundle only when it feeds an L2 plan)
  captures converged intent (scope, acceptance criteria, validation plan). It
  can attach to *any* tier — linked in
  the PR body at L0, linked from the issue / `Read First` at L1/L2. It does not
  set the tier; the execution tier is chosen by the judge below when the work is
  picked up. A doc captured but not yet scheduled is simply tier-undecided
  backlog.
- **Subagents = an execution mode, not automatically L3.** Parallel or
  orchestrated subagent execution can help execute L0-L2 work when the user explicitly
  asks for subagents and no additional shared coordination record is needed.
  Use formal L3 only when the work also needs the dispatch issue spine. If the
  user hands the agent several existing provider issues and asks for subagents,
  either open one dispatch issue that references those issues as lanes, or state
  that the run is ad-hoc orchestrated execution over the existing issue set
  rather than formal L3.

## Escalation Judge

Start at **L0**. Escalate only when a trigger below fires.

**↑ L0 → L1** if any of:

- The work will not be finished now / is deliberately deferred.
- It needs a durable timeline beyond this chat — cross-session continuity or
  visibility to others.
- It needs investigation before the fix is known.
- It is a blocker to record while routing around it.
- It is a handoff to someone or something else.
- It is a recurring loop that keeps needing a timeline.

If none fire, stay at **L0** — the PR (or a one-off answer) is enough.

**↑ L1 → L2** if, on top of an L1 trigger, any of:

- The work is committed and multi-step, with a plan worth freezing (plan/reality
  drift must be detectable).
- It needs a state ledger tracked across sessions and resumable.
- It needs a structured delivery + closeout lifecycle (multiple PRs, validation
  gates, a close-ready audit).

If none fire, stay at **L1**. A follow-up issue can graduate to L2 later, so when
torn between L1 and L2, choose L1 first.

**↑ L2 → L3** if the single unit of work must be split across multiple parallel
lanes or subagents whose independent PRs, reviews, validation, and closeout need
one shared dispatch issue. If subagents are useful but the existing artifact set
already provides enough tracking, keep the lower tier and use
  parallel/orchestrated execution guidance.

## Methods By Tier

### L0 — Untracked delivery

- Do the work, commit through the `semantic-commit` CLI, deliver through
  `deliver-pr` (squash → `main`) by default.
- Only when the maintainer explicitly authorizes direct commit and push to the
  default branch in the current task, use the direct-main mode in
  `git-delivery.md`. Do not carry that authorization into another task.
- PR body: `## Summary` + `## Test plan`, grounded in the diff.
- If a spec doc backs the work, link it in the PR body and close the doc's loop
  per its retention intent (retire when cleanup-eligible, promote when durable).
- No issue.

### L1 — Follow-up issue

- Use `issue-follow-up` (open mode): normalize the problem or objective into the
  issue with `type::`, `area::`, and `state::` labels plus `workflow::follow-up`
  (label mechanics owned by `forge-cli` / `forge-label-taxonomy.md`).
- Maintain the timeline with one concise comment per meaningful step
  (Checked / Result / Decision / Next). Do not let chat become the only source
  of truth once the issue exists.
- When implementing, deliver via the L0 PR path and link the PR to the issue;
  record merge / close on the issue.
- Graduate to L2 when the work becomes a committed, state-tracked plan.

### L2 — Plan tracking issue

- Assemble the bundle in `docs/plans/<YYYY-MM-DD>-<slug>/`: its
  `<slug>-discussion-source.md` is either written fresh by
  `discussion-to-implementation-doc` or **promoted** from an existing
  `docs/discussions/` capture (moved in and renamed, original retired); then
  author `<slug>-plan.md` + `<slug>-execution-state.md`.
- Use `deliver-plan-tracking-issue` for the complete parent outcome. It opens or
  resumes the tracker, owns state/session/validation checkpoints and PR delivery,
  performs strict closeout, then routes `plan-archive migrate` dry-run/apply as
  an internal policy phase.

### L3 — Dispatch plan

- Use `deliver-dispatch-plan` for one effort split across parallel lanes /
  subagents that need a shared dispatch spine. Lane execution, plan-branch PR
  creation, independent review, orchestrator merge, and strict closeout are
  internal phases of that parent outcome.
- Each lane delivers its own PR; the dispatch issue is the spine. Direct-main is
  L0-only and is not a dispatch-lane shortcut.
- Do not label an ad-hoc subagent run as formal L3. Existing issue sets may be
  executed with ad-hoc parallel/orchestrated execution at their existing tier,
  or promoted into L3 by opening one shared dispatch issue that references those
  issues as lanes.

### Doc Lifecycle At L0 / L1

L2 retires its bundle through its internal closeout plus `plan-archive migrate`. An L0/L1
spec lives in `docs/discussions/` and has **no** automatic retirement step, so
when it is executed, close its loop by hand: link it from the PR or issue, mark
it done, and retire or promote it per its retention intent. Otherwise
`docs/discussions/` fills with shipped-but-still-"to do" orphan source docs.

## Agent Behavior: Proactive Triage

At the start of a substantive work request — a code, docs, or config change, or
a tracked task; not pure question-answering or open discussion — the agent
should:

1. **Classify.** Run the escalation judge and state the tier (L0–L3) in one line
   with the trigger that set it (for example, "L1: needs root-cause
   investigation before any fix").
2. **Recommend the next step.** Name the concrete method for that tier (the
   skill or command from Methods By Tier).
3. **Surface at the escalation boundary.** When the tier is **L1+** (it
   creates a durable provider artifact or commits to a heavier path) or the
   classification is **ambiguous**, present the level and recommended next
   step as a decision and wait for the user before creating the artifact. For
   an **unambiguous L0**, say so and proceed — stopping to ask on trivial work
   is itself over-tiering.
4. **Re-triage on signal change.** If new evidence escalates the work mid-flight
   (an L0 fix balloons into a multi-step effort), say so and re-surface the
   decision.

This behavior obeys the same principle it enforces: it adds ceremony only at the
escalation boundary, never on routine L0 work.

## Examples

- Fix a typo, a clear bug, or add a flag — finished in one pass → **L0**.
- A bug is found but other work comes first, or the root cause is unknown → **L1**.
- "Refactor subsystem X" spanning several days and PRs with progress to
  track → **L2**.
- A broad migration across many independent modules, run as parallel lanes with
  one shared dispatch issue for lane state / PRs / reviews / closeout → **L3**.
- Several existing issues executed with subagents but no shared dispatch
  spine → keep their existing tier and use **ad-hoc orchestrated execution**.
- A doc recorded "do Y later" that is not yet scheduled → **capture (tier
  undecided)**; classify when picked up, usually L0 or L1.

## Relationship To Nearby Surfaces

- `AGENT_HOME.md` carries the always-on short directive that triggers proactive
  triage; this file is the full reference it points to.
- `issue-follow-up`, `deliver-plan-tracking-issue`, `deliver-dispatch-plan`, and
  `discussion-to-implementation-doc` are the retained per-tier outcomes.
- `deliver-pr` owns default provider PR/MR delivery, including create, repair,
  merge, and close modes. `git-delivery.md` owns the narrow L0 direct-main
  exception.
- `forge-label-taxonomy.md` owns label selection for L1/L2 issues.
