# Read-only review subagent mutated the shared worktree

## Status

- Status: open
- First observed: 2026-07-10
- Area: multi-agent code-review delegation; shared worktree mutation isolation
- Severity: medium

## Signal

During final code-review follow-up for a cross-repository auth deployment, a
review subagent was explicitly assigned a read-only verification task. After
reporting PASS, it had nevertheless left large unstaged edits in the shared
infra worktree. While restoring the first file, three more out-of-scope files
appeared modified. The parent had recorded a clean committed baseline before
dispatch, so ownership was unambiguous.

This recurs after the archived
`fork-parallel-mutation-exceeds-scope-on-shared-tree` case was promoted. That
case's workaround recommends a read-only/report-back role for shared-tree
forks; this incident shows prose-only read-only scope is still not an effective
write barrier.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-10)
- Summary: the parent detected unexpected edits with `git status`, required the
  reviewer to restore only its agent-owned changes through the approved patch
  surface, and verified every affected blob/mode matched the reviewed HEAD
  before continuing. No user changes or auth material were lost.

## Impact

Read-only review delegation is used to isolate judgement from implementation.
If the reviewer can still mutate the shared worktree, it can contaminate the
patch under review, invalidate evidence, or destroy concurrent user/agent work.
The parent may not notice when the mutation happens to look plausible.

## Current Workaround

- Capture `git status` and HEAD before dispatching any reviewer on a shared
  worktree, then reconcile them immediately after the reviewer returns.
- Tell the reviewer both "read-only" and "do not edit files"; treat that as
  intent, not enforcement.
- If unexpected files appear, stop integration, establish ownership from the
  baseline, and restore only confirmed agent-owned mutations. Never discard an
  ambiguous path.

## Promotion Criteria

Promote when reviewer lanes have an enforced read-only filesystem/tool profile,
isolated worktrees whose changes cannot leak into the parent's tree, or a
mandatory before/after scope-lock gate that fails the review when files change.

## Next Action

Route this recurrence to the multi-agent/review delegation surface and replace
the prose-only read-only contract with an enforceable barrier. Until then,
require baseline and post-review worktree reconciliation for every delegated
review.
