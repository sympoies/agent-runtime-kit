# Discussion Source: Governed direct-main delivery mode

## Trigger

The maintainer wants to preserve an explicitly authorized path for very small
changes and hotfixes to land directly on the repository default branch without
opening a PR. The current runtime policy says that PR delivery is the shared
floor, while the actual enforcement is incomplete: raw `git commit` is blocked,
`semantic-commit` can still create a commit on the default branch, and no
dedicated hook blocks a normal or forced raw push to that branch.

## Findings

- Direct-main delivery is currently forbidden by policy but only partially
  prevented by mechanics. That mismatch makes the effective contract hard to
  explain and easy to use accidentally.
- GitHub currently requires signed commits on `main`, but does not require a PR.
  Remote protection therefore does not replace a local delivery-mode contract.
- The adaptive checkout lease is useful for editing isolation, but delivery to
  the remote default branch is a separate decision. A direct-main commit can be
  authored safely in a temporary managed worktree and pushed to the default
  branch without editing the shared primary checkout.
- The safe primitive belongs in `sympoies/nils-cli`; runtime-kit should own the
  natural-language policy, hook routing, rendered configuration, and acceptance
  tests that make the primitive the only supported agent path.

## Decisions

1. PR delivery remains the default for every work tier. Direct-main is one
   explicit L0 exception and must be requested by the user in the current task;
   the agent must never infer approval from the words “small” or “hotfix”.
2. Implement `forge-cli repo push-default` as the governed primitive. It accepts
   a non-default-branch head, an expected remote-base SHA, and a reason file;
   requires a clean checkout with exactly one signed commit ahead; proves the
   update is a fast-forward; binds an internal exact-old-object lease as a
   compare-and-swap; and reads the remote SHA back into a structured receipt.
   Caller-controlled force and raw force-with-lease are never supported.
3. Author the commit in a managed worktree created from the current remote
   default branch. `semantic-commit` is blocked on the checked-out default branch
   so direct-main does not become an accidental primary-checkout workflow.
4. Add a default-branch push hook that blocks raw `git push` attempts targeting
   the resolved default branch, including force forms, while preserving ordinary
   feature-branch pushes. The governed `forge-cli` command is the agent route.
5. Treat help, dry-run, validation-only, and other documented inspection forms
   as read-only in the checkout lease classifier when they do not mutate state.
6. Successful terminal delivery evidence is either a PR URL/head receipt or a
   direct-main remote-SHA receipt. Stop remains a closeout reporter rather than
   a blanket “PR must exist” blocker.

## Scope

- In scope: the nils-cli command and contract tests; runtime-kit policy wording,
  Codex/Claude hook wiring, hook acceptance tests, and nils-cli surface/pin
  integration needed to consume the released command.
- Out of scope: allowing multiple commits, forced updates, bypassing signing,
  direct merge primitives, weakening provider branch rules, or automatically
  applying the finished runtime surfaces to the live Codex/Claude homes.

## Deployment boundary

Implementation, review, provider delivery, required release/pin convergence,
and deploy-readiness validation belong to this L2. Applying the new managed
runtime surfaces to the live runtime homes is a separate final step and requires
fresh explicit maintainer approval after deploy readiness is proven.

## Execution

- Recommended plan: docs/plans/2026-07-16-direct-main-delivery-mode/direct-main-delivery-mode-plan.md
- Recommended execution state: docs/plans/2026-07-16-direct-main-delivery-mode/direct-main-delivery-mode-execution-state.md
