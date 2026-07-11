# Runtime Skills

This directory contains the portable source templates for runtime-kit skills.
`manifests/skills.yaml` is the machine-checkable inventory; this README is the
human index for scanning the skill catalog by category and skill series.

Admission roles, truthful product exposure, the frozen #562 pending cohort,
and disposition destinations are defined in the
[skill exposure contract](../../docs/source/skill-exposure-contract.md).

## Summary

| Category | Skills | Main series |
| --- | ---: | --- |
| `browser` | 2 | Browser-session evidence, canary checks |
| `code-review` | 5 | Quick pass, focused lenses, pre-merge gate, follow-up, specialist review |
| `conversation` | 7 | Advice, knowledge, handoff, work modes |
| `dispatch` | 8 | Plan-tracking issues, dispatch plans, dispatch lanes |
| `evidence` | 6 | Evidence records, impact scans, cross-checks |
| `issue` | 3 | Issue triage, durable follow-up, plan-issue finding reports |
| `media` | 2 | Image conversion, screen capture |
| `meta` | 22 | Runtime primitives, operation dispatchers, skill lifecycle, plan archive, heuristics, repo maintenance |
| `pr` | 4 | GitHub PRs, GitLab MRs, dispatch-lane PRs |
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
- At most one more clause, and only if it carries one of: the disambiguator
  that separates this skill from its siblings (e.g. `create-pr` vs `deliver-pr`
  vs `close-pr`), or a hard invoke/skip guard (destructive, dry-run-first, or a
  read-vs-write boundary).

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

## Browser

| Series | Skill | Purpose |
| --- | --- | --- |
| Browser-session evidence | [browser-session](./browser/browser-session/) | Records browser-session goals, steps, artifacts, and verification status through `browser-session`. |
| Canary checks | [canary-check](./browser/canary-check/) | Runs a local canary command, persists redacted evidence, and verifies status through `canary-check`. |

## Code Review

Routing guidance for the skill family lives in
[code-review/README.md](./code-review/README.md).

| Series | Skill | Purpose |
| --- | --- | --- |
| Quick pass | [code-review-quick-pass](./code-review/code-review-quick-pass/) | Runs a lightweight read-only review for small or ordinary diffs before escalating to specialist review. |
| Focused lens | [code-review-focused-lens](./code-review/code-review-focused-lens/) | Runs one or more explicitly requested specialist review lenses without invoking the full specialist bundle. |
| Pre-merge gate | [code-review-pre-merge-gate](./code-review/code-review-pre-merge-gate/) | Runs the shared read-only specialist review gate before PR or MR merge decisions. |
| Follow-up | [code-review-follow-up](./code-review/code-review-follow-up/) | Re-checks previous review findings after fixes and classifies each item by disposition. |
| Specialist review | [code-review-specialists](./code-review/code-review-specialists/) | Decomposes risky or broad diffs into read-only specialist review passes and merges normalized findings. |

## Conversation

| Series | Skill | Purpose |
| --- | --- | --- |
| Advice and knowledge | [actionable-advice](./conversation/actionable-advice/) | Structures actionable engineering advice around options, tradeoffs, assumptions, and one recommendation. |
| Advice and knowledge | [actionable-knowledge](./conversation/actionable-knowledge/) | Explains concepts or confusion through multiple lenses with one recommended next step. |
| Discussion capture and handoff | [discussion-to-implementation-doc](./conversation/discussion-to-implementation-doc/) | Converts completed requirements, design, feasibility, or customer-facing discussion into implementation-ready source material. |
| Discussion capture and handoff | [handoff-session-prompt](./conversation/handoff-session-prompt/) | Generates a next-session initialization prompt from current context and user-specified references. |
| Work modes | [orchestrator-first](./conversation/orchestrator-first/) | Makes the main agent own scope, dispatch, integration, validation, and final synthesis while subagents own lanes. |
| Work modes | [parallel-first](./conversation/parallel-first/) | Applies the shared parallel delegation protocol for safely parallelizable sidecar work. |

## Dispatch

| Series | Skill | Purpose |
| --- | --- | --- |
| Plan-tracking issue | [create-plan-tracking-issue](./dispatch/create-plan-tracking-issue/) | Creates or previews a lightweight issue-backed plan tracker with shared dashboard and append-only lifecycle comments. |
| Plan-tracking issue | [execute-plan-tracking-issue](./dispatch/execute-plan-tracking-issue/) | Resumes lightweight issue-backed plan execution from lifecycle comments and keeps the dashboard current. |
| Plan-tracking issue | [deliver-plan-tracking-issue](./dispatch/deliver-plan-tracking-issue/) | Delivers a lightweight issue-backed plan through implementation, review, PR delivery, and close readiness gates. |
| Plan-tracking issue | [plan-tracking-issue-closeout](./dispatch/plan-tracking-issue-closeout/) | Closes a lightweight plan-tracking issue after lifecycle audit, validation, approval, PR evidence, and dashboard repair. |
| Dispatch plan | [deliver-dispatch-plan](./dispatch/deliver-dispatch-plan/) | Delivers a dispatch-ready plan by creating the shared issue record, dispatching lanes, reviewing PRs, and closing gates. |
| Dispatch plan | [dispatch-plan-closeout](./dispatch/dispatch-plan-closeout/) | Closes out a shared dispatch plan record after lane PRs, review, validation, approval, and lifecycle gates pass. |
| Dispatch lane | [execute-dispatch-lane](./dispatch/execute-dispatch-lane/) | Executes an assigned lane, opens or updates its PR, and reports lane state back to the shared issue record. |
| Dispatch lane | [review-dispatch-lane-pr](./dispatch/review-dispatch-lane-pr/) | Reviews dispatch-lane PRs with retained evidence, provider comments, and issue-visible lifecycle updates. |

## Evidence

| Series | Skill | Purpose |
| --- | --- | --- |
| Web evidence | [web-evidence](./evidence/web-evidence/) | Captures redacted HTTP metadata, previews, and manifests through `web-evidence`. |
| Review evidence | [review-evidence](./evidence/review-evidence/) | Persists review findings, validation commands, artifacts, and verification status through `review-evidence`. |
| Test-first evidence | [test-first-evidence](./evidence/test-first-evidence/) | Governs a change with failing-test discipline — classify, failing test or waiver before production edits, scoped implementation, final validation — and produces the record the `forge-cli` test-first gate verifies. |
| Skill usage evidence | [skill-usage](./evidence/skill-usage/) | Records skill invocation intent, linked evidence, validation, failures, and outcomes through `skill-usage`. |
| Documentation impact | [docs-impact](./evidence/docs-impact/) | Scans Git changes for documentation impact through `docs-impact`. |
| Model cross-check | [model-cross-check](./evidence/model-cross-check/) | Records primary and checker model observations through `model-cross-check` without owning provider calls. |

## Issue

Shared issue label, comment, and close discipline lives in
[issue/issue-lifecycle/README.md](./issue/issue-lifecycle/README.md).

| Series | Skill | Purpose |
| --- | --- | --- |
| Issue triage | [issue-triage](./issue/issue-triage/) | Reviews open GitHub or GitLab issues from `forge-cli inbox`, classifies readiness and blockers, and recommends execution order. |
| Durable issue follow-up | [issue-follow-up](./issue/issue-follow-up/) | Opens or continues a GitHub or GitLab issue as the durable timeline for a discovered problem, blocker, or handoff. |
| Plan-issue finding report | [report-plan-issue-finding](./issue/report-plan-issue-finding/) | Files plan-issue / plan-tracking family skill, CLI, or driver drift as a labeled issue in the canonical tracker, and closes it when the upstream fix lands. |

## Media

| Series | Skill | Purpose |
| --- | --- | --- |
| Image processing | [image-processing](./media/image-processing/) | Validates SVG inputs and converts SVG, PNG, JPEG, or WebP files through `image-processing`. |
| Screen capture | [screen-record](./media/screen-record/) | Captures screenshots or recordings from windows or displays through `screen-record`. |

## Computer Use

| Series | Skill | Purpose |
| --- | --- | --- |
| macOS desktop automation | [macos-desktop](./computer-use/macos-desktop/) | Operates and tests a local or SSH-reachable Mac through nils-cli `macos-agent`, retaining screenshots, scenarios, permission gaps, and structured evidence. |

## Meta

The meta domain is large enough to need its own routing index. Detailed
classification lives in [meta/README.md](./meta/README.md).

| Series | Skills | Purpose |
| --- | --- | --- |
| Runtime primitives | [agent-docs](./meta/agent-docs/), [agent-out](./meta/agent-out/), [agent-scope-lock](./meta/agent-scope-lock/), [sync-runtime-surfaces](./meta/sync-runtime-surfaces/) | Required docs, output paths, edit scope locks, and runtime surface sync. |
| Repo operation dispatchers | [bootstrap](./meta/bootstrap/), [deploy](./meta/deploy/), [pre-pr](./meta/pre-pr/), [release](./meta/release/), [setup-project](./meta/setup-project/) | Repo-owned `.agents/scripts/*` dispatch and project adoption. |
| Skill lifecycle | [create-skill](./meta/create-skill/), [remove-skill](./meta/remove-skill/), [create-project-skill](./meta/create-project-skill/), [remove-project-skill](./meta/remove-project-skill/) | Managed runtime-kit skills and consuming-repo project-local skills. |
| Plan archive | [plan-archive-query](./meta/plan-archive-query/), [plan-archive-discover](./meta/plan-archive-discover/), [plan-archive-migrate](./meta/plan-archive-migrate/) | Work-history lookup and completed plan migration. |
| Evidence archive | [evidence-migrate](./meta/evidence-migrate/) | Durable, scrubbed skill-usage evidence migration into the agent-evidence-archive. |
| Heuristic system | [heuristic-inbox](./meta/heuristic-inbox/), [heuristic-session-closeout](./meta/heuristic-session-closeout/) | Curated workflow-gap records and session closeout retention. |
| Delivery and repo maintenance | [semantic-commit](./meta/semantic-commit/), [worktree-triage](./meta/worktree-triage/), [nils-cli-bump](./meta/nils-cli-bump/), [repo-retro](./meta/repo-retro/) | Semantic commits, worktree cleanup, nils-cli pin bumps, and retrospectives. |

## PR And MR

Shared PR/MR body, label, branch, provider, and merge gate rules live in
[pr/pr-lifecycle/README.md](./pr/pr-lifecycle/README.md).

| Series | Skill | Purpose |
| --- | --- | --- |
| PR/MR lifecycle | [create-pr](./pr/create-pr/) | Creates a GitHub pull request or GitLab merge request through the released `forge-cli pr create` surface. |
| PR/MR lifecycle | [close-pr](./pr/close-pr/) | Closes or merges GitHub pull requests or GitLab merge requests through released `forge-cli pr` lifecycle surfaces. |
| PR/MR lifecycle | [deliver-pr](./pr/deliver-pr/) | Delivers GitHub pull requests or GitLab merge requests end to end through the released `forge-cli pr deliver` macro. |
| Dispatch-lane PR | [create-dispatch-lane-pr](./pr/create-dispatch-lane-pr/) | Creates a GitHub dispatch-lane pull request after a plan issue assigns the lane. |

## Reporting

| Series | Skill | Purpose |
| --- | --- | --- |
| Topic radar | [topic-radar](./reporting/topic-radar/) | Aggregates read-only AI and technology trend signals into source-grounded Markdown or JSON digests. |
| Topic radar | [daily-brief](./reporting/daily-brief/) | Prepares a source-grounded daily information brief and orchestrates `topic-radar` JSON output. |
| Project retrospective | [project-retro](./reporting/project-retro/) | Generates a repo-local project implementation retrospective through `repo-retro`. |
