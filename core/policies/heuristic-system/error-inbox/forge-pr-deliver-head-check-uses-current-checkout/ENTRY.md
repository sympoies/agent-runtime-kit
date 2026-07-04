# forge-cli pr deliver head_not_pushed when run from a checkout whose HEAD is not the --head branch

## Status

- Status: open
- First observed: 2026-06-15
- Area: forge-cli
- Severity: medium

## Signal

`forge-cli pr deliver --head <branch> --repo <owner/name> ...` fails with
`error: head_not_pushed: HEAD differs from its upstream (push the branch first)`
even though `<branch>` *was* pushed and is up to date on the remote. The
pushed-state check is evaluated against the **current checkout's HEAD**, not the
`--head` branch. So running `deliver` from a checkout sitting on a different,
stale branch trips the guard.

Concrete trigger this session (host nils-cli 1.7.1): the shared primary checkout
of `sympoies/nils-cli` had local `main` at `1da4d3c` while `origin/main` had
advanced to `ea21ab2` (only `git fetch` had run, not a fast-forward of local
`main`). The feature branch `fix/evidence-migration-host-resolution` was created
in a dedicated `git-cli worktree` and pushed clean. Running
`forge-cli pr deliver --head fix/evidence-migration-host-resolution` from the
**primary checkout** (HEAD = stale `main`) failed `head_not_pushed`; the deliver
got only as far as the `repo_view` step. Re-running the identical command from
the **feature worktree** (HEAD = the pushed feature branch) succeeded and opened
the PR.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-06-15; forge-cli pr deliver head_not_pushed, nils-cli #873/#874).
- Summary: same `forge-cli pr deliver --head <feat> --repo sympoies/nils-cli`
  invocation fails from the primary checkout (stale local `main`) and succeeds
  unchanged from the feature worktree. PRs #873 / #874 were both delivered from
  their worktrees after this.
- 2026-07-05 recurrence: `forge-cli pr create --head
  feat/issue-17-attachments-title-workdirs --dry-run` failed with
  `head_not_pushed` from a clean checkout whose current HEAD had no upstream,
  even though the requested head branch was pushed. Running the same create from
  a checkout of the requested head branch succeeded and opened
  `sympoies/agent-console#22`. See
  `evidence/2026-07-05-pr-create-head-guard.md`.

## Impact

The shared-worktree isolation policy means agents routinely deliver from a
dedicated worktree while the primary checkout stays on a possibly-stale `main`.
An agent that runs `deliver` from the wrong cwd (or that delivers a second PR
from the primary checkout after the first merge advanced `origin/main`) hits a
confusing `head_not_pushed` that wrongly implies the branch was not pushed,
costing retries and misdiagnosis.

## Current Workaround

Run `forge-cli pr create` / `pr deliver` / `pr merge` from the feature branch's
own worktree (HEAD = the `--head` branch). Alternatively, fast-forward the
current checkout's branch to its upstream before delivering. Passing `--head`
alone is not enough — the pushed-state guard ignores it and inspects the current
HEAD.

## Promotion Criteria

Promote when either: (a) `forge-cli pr create` / `pr deliver` are fixed to
evaluate the pushed-state guard against the resolved `--head` branch rather than
the current checkout's HEAD; or (b) the PR delivery skills document "run provider
PR commands from the feature worktree" as the contract and that guidance is
validated. Link the upstream change or skill edit here.

## Next Action

File an upstream nils-cli `forge-cli` issue: the `head_not_pushed` guard in
`pr create` / `pr deliver` should check the `--head` branch's local-vs-remote
state, not the current checkout's HEAD. Until then, the PR delivery skills should
note the run-from-worktree requirement.
