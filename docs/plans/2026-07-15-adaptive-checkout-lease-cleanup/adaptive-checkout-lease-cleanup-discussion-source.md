# Implementation Source: Adaptive checkout lease and workflow cleanup

## Status

- Status: ready for L2 tracked execution
- Date: 2026-07-15
- Source: user discussion in the current session

## Problem

Agent-maintained repositories currently rely on policy asking agents to prefer
worktrees. That is insufficient when several sessions share one primary
checkout: a direct edit can collide with another writer, inherit unrelated
changes, or leave an ambiguous dirty tree. Requiring a worktree for every
change would prevent those collisions but would add needless ceremony for a
small change in an otherwise clean, idle checkout.

Worktree creation is also only half of the lifecycle. Delivery workflows do
not consistently make safe terminal cleanup explicit, so merged branches and
managed worktrees can accumulate after their useful lifetime.

## Inputs And Evidence

- [U1] The user wants agents to use worktrees whenever an existing checkout is
  dirty, while preserving a low-friction path for small changes in a clean
  checkout.
- [U2] The repositories are maintained primarily by agents; collisions and
  abandoned local state matter more than optimizing for a human watching each
  checkout.
- [U3] The user selected an adaptive lease plus workflow cleanup design and
  requested end-to-end PR delivery followed by activation on both runtime
  roles.
- [F1] The runtime already has shared pre-tool and Stop hooks, rendered Codex
  and Claude hook surfaces, managed `git-cli worktree` operations, and governed
  PR/plan workflows.
- [I1] One writer lease per physical checkout addresses clean-checkout races
  that a one-time `git status` check cannot prevent.
- [I2] Cleanup belongs at the terminal workflow boundary, after provider and
  deployment duties, because a Stop hook cannot safely infer that a branch is
  merged or no longer needed.

## Resolved Design

### Adaptive writer lease

- Define one product-neutral checkout lease guard used by supported pre-tool
  hook adapters.
- Identify a checkout by canonical Git common-dir plus checkout identity; bind
  leases to the current session using a non-reversible session digest.
- A session may acquire a clean linked worktree. It may acquire the primary
  checkout only when it is clean, on the default branch, and no Git operation
  is in progress.
- Once acquired, the same session may continue after its own edits make the
  tree dirty.
- Block explicit edits and high-confidence shell mutations when the checkout
  has a live foreign lease, has unowned changes, or entered a merge, rebase,
  cherry-pick, revert, or bisect operation without this session's lease. The
  owner may continue an operation it began after acquisition.
- Allow stale-lease reclamation only after a configurable TTL and only while
  the checkout is clean. A checkout-instance sentinel invalidates a lease when
  a linked worktree is removed and recreated.
- Fail closed for explicit edit tools when required session or state identity
  is unavailable. Preserve read-only inspection.

### Workflow cleanup

- Stop hooks only audit and report checkout ownership; they never delete a
  worktree or branch.
- Governed terminal delivery performs cleanup only after merge and all issue,
  archive, deployment, and local closeout duties are complete.
- A clean primary checkout is restored to its base branch. A clean, unlocked,
  merged managed worktree is removed through `git-cli worktree remove`, then
  its merged local branch is deleted.
- Dirty, locked, unmerged, or otherwise unsafe state is retained and reported
  with a recovery command instead of being forced away.
- Apply the same terminal rule to the PR, L2 tracking, and L3 dispatch parent
  workflows so no lifecycle path silently omits cleanup.

## Acceptance Criteria

- Two sessions cannot acquire the same physical checkout concurrently.
- A clean, idle primary checkout retains the direct-edit exception; a dirty or
  operation-in-progress primary checkout does not.
- A linked worktree can be acquired, refreshed by its owner, reclaimed safely
  after expiry, and distinguished from a removed/recreated instance.
- Read-only tools remain usable when mutation would be blocked.
- Codex and Claude hook render surfaces express the same supported behavior;
  Hermes reports its declared hook capability ceiling.
- Stop behavior remains non-destructive and provides actionable audit output.
- PR, L2, and L3 terminal workflows explicitly remove only safe merged managed
  worktrees and report retained unsafe state.
- Focused hook tests, full hook tests, and the repository CI contract pass.
- The merged runtime is activated and verified on both requested runtime roles.

## Non-Goals

- Mandatory worktree creation for every edit.
- Parsing arbitrary shell programs as a complete mutation detector.
- Letting hooks infer semantic completion, merge readiness, or deployment
  success.
- Automatically discarding dirty or unmerged work.

## Rollback

Remove the hook wiring and rendered surfaces to disable enforcement while
retaining the policy-only behavior. Terminal cleanup remains ownership-safe;
if cleanup cannot prove safety, it leaves the worktree intact for manual
recovery.

## Execution

- Recommended plan: docs/plans/2026-07-15-adaptive-checkout-lease-cleanup/adaptive-checkout-lease-cleanup-plan.md
- Recommended execution state: docs/plans/2026-07-15-adaptive-checkout-lease-cleanup/adaptive-checkout-lease-cleanup-execution-state.md
