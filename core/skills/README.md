# Runtime Skills

This directory contains the portable source templates for runtime-kit skills.
`manifests/skills.yaml` is the machine-checkable inventory; this README is the
human index for scanning the skill catalog by category and skill series.

Admission roles, truthful product exposure, the completed #562 migration,
and retained retirement history are defined in the
[skill exposure contract](../../docs/source/skill-exposure-contract.md).

## Summary

| Category | Skills | Main series |
| --- | ---: | --- |
| `code-review` | 1 | Generic read-only code review with internal mode selection |
| `computer-use` | 1 | macOS desktop automation and GUI testing |
| `conversation` | 3 | Discussion capture, guided build, and handoff |
| `dispatch` | 2 | L2 plan tracking and L3 dispatch outcomes |
| `issue` | 2 | Issue triage and durable follow-up |
| `media` | 2 | Image conversion, screen capture |
| `meta` | 13 | Explicit execution handoff, repository, documentation, and runtime maintenance outcomes |
| `pr` | 1 | Governed GitHub PR and GitLab MR delivery |
| `reporting` | 3 | Topic radar, daily brief, project retrospective |

## Skill Body Editing Rubric

When editing a `SKILL.md.tera`, keep the body decision-minimal: short enough to
scan, but explicit about anything that changes an agent's next action.

Keep text that carries one of these roles:

- Hard prerequisites: CLI floors, provider auth, branch/base state, required
  docs, validation contracts, or committed bundle state.
- Irreversible or externally visible operations: provider mutation, merge,
  issue close, archive, install/apply, runtime-home mutation, or destructive
  cleanup.
- Provider differences: GitHub/GitLab behavior, label shape, PR/MR refs, check
  gates, reviewability, and provider API limits.
- Stop conditions: exact blocker codes, stale state, missing evidence,
  visible-lint failures, forbidden roles, or no-safe-retry cases.
- Ownership boundaries: what the skill owns, what it must not own, and which
  skill or CLI takes over at handoff.
- Canonical entrypoints and validation: the smallest command sequence and
  checks that prove the workflow shape.

Remove or rehome text that only restates CLI help, repeats sibling-skill rules
without local differences, explains history that no longer affects decisions,
or expands optional branches into long examples. Shared rules belong in the
narrowest domain reference folder, not copied across every sibling skill.

## Skill Description Rubric

The frontmatter `description` is always-loaded context: every skill's `name` +
`description` sits in the system prompt of every session, for both products,
before any skill is invoked. The body loads only on invocation. So keep the
description minimal and *distinctive*, not comprehensive.

Keep:

- Sentence 1 — identity: verb + object + via-what (the CLI or mechanism). One
  line.
- At most one more clause, and only if it carries a disambiguator between
  distinct user outcomes or a hard invoke/skip guard (destructive,
  dry-run-first, or a read-vs-write boundary).

Cut (it belongs in the body, not the always-loaded description):

- Trigger enumeration — `Use when the user asks "…"`, `Trigger whenever …`, and
  lists of example phrasings. Explicit invocation and skill-to-skill handoff do
  not read these; only naive auto-routing does.
- Restatements of the body, optional branches, and history.
- Safety-mechanic narration (e.g. "dry-run first, applies only when clean") —
  state the guard in one clause; the mechanics live in the body.

Target: a leaf skill is ~1 line (≤120 chars); a family member or safety-gated
skill may keep a second clause (≤220 chars). Those two numbers are **advisory
authoring targets, not gates** — the only mechanically enforced limit is the
hard fail `scripts/ci/skill-governance-audit.sh` raises on any description over
**240 chars**. Each audit run reports `desc_max=N/240` plus advisory
`desc_over120` / `desc_over220` counts, so drift toward the ceiling stays
visible without blocking.

## Code Review

Routing guidance for the skill family lives in
[code-review/README.md](./code-review/README.md).

| Series | Skill | Purpose |
| --- | --- | --- |
| Code review | [code-review-specialists](./code-review/code-review-specialists/) | Selects review context plus quick, focused, or specialist depth internally and returns evidence-grounded findings. |

## Conversation

| Series | Skill | Purpose |
| --- | --- | --- |
| Discussion capture and handoff | [discussion-to-implementation-doc](./conversation/discussion-to-implementation-doc/) | Converts completed requirements, design, feasibility, or customer-facing discussion into implementation-ready source material. |
| Discussion capture and handoff | [handoff-session-prompt](./conversation/handoff-session-prompt/) | Generates a next-session initialization prompt from current context and user-specified references. |
| Guided feature build | [guided-feature-build](./conversation/guided-feature-build/) | Explores, designs, implements, and reviews a feature while selecting delegation modes internally. |

## Dispatch

| Series | Skill | Purpose |
| --- | --- | --- |
| Plan-tracking issue | [deliver-plan-tracking-issue](./dispatch/deliver-plan-tracking-issue/) | Delivers a lightweight issue-backed plan through implementation, review, PR delivery, and close readiness gates. |
| Dispatch plan | [deliver-dispatch-plan](./dispatch/deliver-dispatch-plan/) | Delivers a dispatch-ready plan by creating the shared issue record, dispatching lanes, reviewing PRs, and closing gates. |

## Issue

Shared issue label, comment, and close discipline lives in
[issue/issue-lifecycle/README.md](./issue/issue-lifecycle/README.md).

| Series | Skill | Purpose |
| --- | --- | --- |
| Issue triage | [issue-triage](./issue/issue-triage/) | Reviews open GitHub or GitLab issues from `forge-cli inbox`, classifies readiness and blockers, and recommends execution order. |
| Durable issue follow-up | [issue-follow-up](./issue/issue-follow-up/) | Opens or continues a GitHub or GitLab issue as the durable timeline for a discovered problem, blocker, or handoff. |

## Media

| Series | Skill | Purpose |
| --- | --- | --- |
| Image processing | [image-processing](./media/image-processing/) | Validates SVG inputs and converts SVG, PNG, JPEG, or WebP files through `image-processing`. |
| Screen capture | [screen-record](./media/screen-record/) | Captures screenshots or recordings from windows or displays through `screen-record`. |

## Computer Use

| Series | Skill | Purpose |
| --- | --- | --- |
| macOS desktop automation | [macos-desktop](./computer-use/macos-desktop/) | Operates and tests a local or SSH-reachable Mac through nils-cli `macos-agent`, retaining screenshots, guarded multi-step flows, permission gaps, and structured evidence. |

## Meta

The meta domain is large enough to need its own routing index. Detailed
classification lives in [meta/README.md](./meta/README.md).

| Series | Skills | Purpose |
| --- | --- | --- |
| Runtime maintenance | [sync-runtime-surfaces](./meta/sync-runtime-surfaces/), [nils-cli-bump](./meta/nils-cli-bump/), [worktree-triage](./meta/worktree-triage/) | Runtime refresh, dependency pin convergence, and safe worktree maintenance. |
| Execution handoff | [execution-capsule](./meta/execution-capsule/) | Private reusable scripts with direct and Codex-supervised run paths. |
| Repo operation dispatchers | [bootstrap](./meta/bootstrap/), [deploy](./meta/deploy/), [release](./meta/release/), [setup-project](./meta/setup-project/) | Explicit repo-owned operation dispatch and project adoption. |
| Skill lifecycle | [create-skill](./meta/create-skill/), [remove-skill](./meta/remove-skill/), [create-project-skill](./meta/create-project-skill/), [remove-project-skill](./meta/remove-project-skill/) | Managed runtime-kit skills and consuming-repo project-local skills. |
| Repository documentation | [repo-docs-boundary](./meta/repo-docs-boundary/) | README, contributor setup, and durable docs placement under active repository policy. |

## PR And MR

Shared PR/MR body, label, branch, provider, and merge gate rules live in
[pr/pr-lifecycle/README.md](./pr/pr-lifecycle/README.md).

| Series | Skill | Purpose |
| --- | --- | --- |
| PR/MR lifecycle | [deliver-pr](./pr/deliver-pr/) | Delivers GitHub pull requests or GitLab merge requests end to end through the released `forge-cli pr deliver` macro. |

## Reporting

| Series | Skill | Purpose |
| --- | --- | --- |
| Topic radar | [topic-radar](./reporting/topic-radar/) | Aggregates read-only AI and technology trend signals into source-grounded Markdown or JSON digests. |
| Topic radar | [daily-brief](./reporting/daily-brief/) | Prepares a source-grounded daily information brief and orchestrates `topic-radar` JSON output. |
| Project retrospective | [project-retro](./reporting/project-retro/) | Generates a repo-local project implementation retrospective through `repo-retro`. |
