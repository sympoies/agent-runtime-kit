# Code Review Outcome

Runtime-kit exposes one user-visible code-review outcome:
`code-review-specialists`. It selects the review context and the smallest depth
that satisfies the request and risk. Pre-merge is a delivery context; quick,
focused, and specialist are review depths, while follow-up rechecks prior
findings. None are separate skills.

| Situation | Internal mode | Behavior |
| --- | --- | --- |
| Small, routine, docs-only, or ordinary diff | `quick` | Lightweight read-only review; escalate when scope or confidence requires it. |
| Explicit lens requested | `focused` | Run only the requested testing, security, performance, data-migration, API-contract, maintainability, or red-team lenses unless concrete scope requires more. |
| Eligible L0/L1 PR/MR near merge | `pre-merge` + `quick` | Treat a clean quick pass as terminal review evidence for the current head; escalate on scope, risk, findings, or confidence. |
| L2/L3 or risk-triggering PR/MR near merge | `pre-merge` + `specialist` | Force at least testing and maintainability, add risk lenses, produce a delivery outcome, and leave provider writes and merge decisions to the owning delivery workflow. |
| Previous findings repaired | `follow-up` | Run closed-set closure review over supplied findings, repair hunks, and their direct regression surface; admit only material repair-introduced regressions. |
| Broad or high-risk change | `specialist` | Select and dispatch the relevant specialist bundle, then validate and merge findings. |

## Reviewer Subagents

Managed reviewers render from `core/agents/code-review/` into each product home
(`~/.codex/agents/reviewer-<lens>.toml`,
`~/.claude/agents/reviewer-<lens>.md`). When the active host exposes subagent
dispatch, each selected lens is delegated read-only; Codex uses
`multi_agent_v1.spawn_agent` or its equivalent. Inline review is the stated
fallback only when dispatch is unavailable or blocked.

## Parent Workflow Integration

- `deliver-pr` invokes pre-merge context before merge, selects quick or full
  review, and owns provider comments, fixes, checks, and merge.
- `deliver-plan-tracking-issue` invokes pre-merge context with the full profile
  for each PR, then owns issue-visible review evidence and strict closeout.
- `deliver-dispatch-plan` invokes the generic outcome for independent lane
  review and keeps provider writes, checkpoints, integration, and closeout in
  the dispatch parent.
- `discussion-to-implementation-doc` records the expected review mode in the
  implementation source document but does not review by default.
- When retained findings matter, the parent creates a `review-evidence` CLI
  record under the evidence control-plane policy.

## Boundary

The review outcome is read-only. It selects modes and lenses, dispatches
reviewers, validates findings, and returns evidence-grounded conclusions. It
does not fix code, post provider comments, merge or close PRs/MRs, mutate plan
issues, or execute the recommended next step.
