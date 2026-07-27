# Work Tier Levels

## Purpose

This delivery-phase policy sizes durable tracking, not the agent's ability to
plan. Pick the lowest tier that owns the state the work genuinely needs. Keep
routine L0 classification internal; load and surface this ladder only when a
follow-up, plan, dispatch, provider artifact, or ambiguous escalation is
actually in play.

It is a `project-dev` delivery document in `AGENT_DOCS.toml`. `AGENT_HOME.md`
carries only the routing invariant; this file owns the ladder and artifact
boundaries.

## Principle

Work has three independent axes. Do not collapse them:

- **Delivery axis — PR for requested provider delivery.** Once provider
  delivery is explicitly requested or owned by an approved retained workflow,
  a PR squash-merged into `main` is the default. The exceptions are explicitly
  authorized L0 direct-main delivery and default-branch completion using the
  separate governed one-commit receipt paths in `git-delivery.md`.
- **Tracking axis — the tier.** How much durable, cross-time tracking the
  problem or plan needs: none, a follow-up issue, or a plan tracking issue. This
  axis is what the tiers below measure.
- **Review axis — risk-selected depth.** Every delivered PR receives a
  pre-merge review, but the review can be quick or full. Eligible L0/L1 routine
  diffs may use a quick review whose clean `pass` is terminal for the reviewed
  head; findings block merge and an `escalate` verdict routes to the full
  specialist gate. L2/L3 PRs and risk-triggering diffs keep the full gate.

The tiers are ordered by overhead. Pick the lowest tier that satisfies the
work's actual needs, and escalate only when a concrete trigger fires. Size alone
is never a reason to escalate — *"state worth tracking"* is.

## The Ladder

| Tier | Name | Tracking artifact | Primary method |
| --- | --- | --- | --- |
| **L0** | Untracked delivery | None | Local `semantic-commit`; `deliver-pr`, direct-main, or default-branch only with the matching explicit authority |
| **L1** | Follow-up issue | One provider issue + comment timeline | `issue-follow-up` |
| **L2** | Plan tracking issue | Plan bundle + issue + lifecycle | `deliver-plan-tracking-issue` |
| **L3** | Dispatch plan | Shared dispatch issue + lanes | `deliver-dispatch-plan` |

L3 is for one unit of work that must be split across multiple parallel lanes
or subagents **and** needs one shared coordination spine — a shipped, exercised
path, not a placeholder. Reach for it when the work is too broad for one lane to
hold and its lane state, PRs, reviews, and closeout must be coordinated through
one dispatch issue; the user decides whether the scale warrants running it.

## Cross-Cutting Concepts

Several concepts ride alongside the ladder and must not be mistaken for tiers:

- **PR = the default provider delivery path, not default authority.** L1–L3
  deliver through PRs after their retained workflow is approved. L0 uses a PR
  only when provider delivery is explicitly requested. Never infer direct-main
  authority from change size, urgency, or words such as "small" or "hotfix".
  That route is one signed commit from a non-default managed worktree through
  `forge-cli repo push-default`; its remote-SHA receipt replaces the PR record.
  For PR delivery, keep the body grounded in the diff with at least
  `## Summary` + `## Test plan`, produced by the active delivery skill /
  `agent-runtime pr-body render`.
- **Default-branch = local completion, not delivery.** When the maintainer
  explicitly requests one local-only commit on the primary default checkout,
  `semantic-commit default-branch` may create exactly one signed commit and an
  outside-checkout receipt. It opens no issue or PR and performs no provider
  mutation. Remote-free repositories must have no upstream metadata. With
  configured remotes, the checked-out primary branch, configured upstream, and
  cached remote default must agree and the cached upstream must equal `HEAD`.
  The command performs no network access; missing, ahead, behind, diverged, or
  ambiguous cached identity fails closed. The receipt remains
  `provider_delivered=false`.
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
- **Review profile is not a tier.** Tracking need does not determine code risk:
  a tiny deferred L1 fix can qualify for quick review, while a security-sensitive
  L0 change requires specialists. `deliver-pr` selects the smallest safe
  pre-merge profile from the outer lifecycle, changed scope, validation, existing
  review state, and reviewer confidence. Escalating review depth does not change
  the work tier or require a new tracking artifact.
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

- Do the work and commit through `semantic-commit`. Use `deliver-pr` only when
  provider delivery is explicitly requested; otherwise stop at the authorized
  local outcome.
- Let `deliver-pr` select quick or full pre-merge review from scope and risk;
  requesting quick review never bypasses automatic escalation.
- Only when the maintainer explicitly authorizes direct commit and push to the
  default branch in the current task, use the direct-main mode in
  `git-delivery.md`. Do not carry that authorization into another task.
- Only when the maintainer explicitly authorizes default-branch completion in
  the current task, use the default-branch mode in `git-delivery.md`. It is
  terminal only for the local task; later provider delivery requires fresh
  authorization and live revalidation.
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
- A bounded low-risk L1 implementation may use quick review; the durable issue
  timeline does not by itself require specialist depth.
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

## Agent Behavior

1. Classify ordinary same-session work internally as L0 and proceed without a
   tier announcement, tracker proposal, or permission pause.
2. When an L1+ trigger fires, explain the durable state that is needed, name the
   lowest matching method, and obtain the required user decision before
   creating provider or plan artifacts.
3. If classification is materially ambiguous, recommend the lower-cost safe
   default and ask only the decision that changes the artifact or authority.
4. Re-triage when evidence changes. Escalation preserves completed work and
   review depth; it does not retroactively make routine steps require ceremony.

## Examples

- Fix a typo, a clear bug, or add a flag — finished in one pass → **L0**.
- A small low-risk fix retained on an existing follow-up issue → **L1** tracking
  with an eligible quick-review PR.
- A security-sensitive change finished in one pass → **L0** tracking with a full
  specialist-review PR.
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

- `AGENT_HOME.md` keeps routine L0 internal and routes here only when durable
  delivery state or a materially ambiguous escalation is in play.
- `issue-follow-up`, `deliver-plan-tracking-issue`, `deliver-dispatch-plan`, and
  `discussion-to-implementation-doc` are the retained per-tier outcomes.
- `deliver-pr` owns default provider PR/MR delivery, including create, repair,
  merge, and close modes. `git-delivery.md` owns the narrow L0 direct-main
  exception.
- `forge-label-taxonomy.md` owns label selection for L1/L2 issues.
