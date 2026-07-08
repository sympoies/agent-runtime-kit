# project-bump-version-tag-release git checkout main fails from a non-main worktree

## Status

- Status: open
- First observed: 2026-06-14
- Area: release
- Severity: medium

## Signal

`project-bump-version-tag-release.sh` (nils-cli, shipped in
`.agents/skills/project-bump-version-tag-release/scripts/`) runs a post-merge
`git checkout main` after `forge-cli pr deliver` merges the release PR. When the
script is launched from a dedicated (non-main) git worktree — the
shared-worktree isolation policy's required setup — that checkout fails with
`fatal: 'main' is already used by worktree at '<primary checkout>'` (exit 128),
because `main` is held by the primary checkout. Hit on three consecutive
nils-cli releases: v1.4.0, v1.5.0, v1.6.0.

## Evidence

- Raw record: not captured; manual diagnosis of the release-script post-merge checkout failure, 2026-06-14
- Evidence: `evidence/failure-and-recovery.md`
- Script: `project-bump-version-tag-release.sh`, PR-mode branch, the
  `note "switching back to main and fast-forwarding"; git checkout main` step
  (~line 1417) that runs after `forge-cli pr deliver` succeeds.
- The release PR merges cleanly first ("delivered: N steps"); only the
  post-merge `git checkout main` aborts, so the tag + release.yml + tap + brew
  stages never run.
- Observed for sympoies/nils-cli v1.4.0, v1.5.0, v1.6.0 (host nils-cli 1.6.0).
- Direct conflict with [[feedback_shared_worktree_isolation]] (do not branch /
  switch in the shared main checkout; use a dedicated worktree).

## Impact

Every lock-step nils-cli release run from a dedicated worktree aborts mid-flow
after the release PR is already merged, leaving an untagged merge commit and no
tap/brew update until the operator runs a manual recovery. Silent if the
non-zero exit is masked by a trailing command.

## Current Workaround

After the abort, from the primary `main` checkout:

1. `git fetch origin main && git merge --ff-only origin/main` (advance to the
   merged release bump).
2. Create the signed annotated tag on the merged release-PR commit:
   `git tag -a vX.Y.Z -m vX.Y.Z <merge-sha>` then `git push origin vX.Y.Z`
   (triggers `release.yml`).
3. After `release.yml` publishes the GitHub Release assets, resume the tap +
   brew stages with `project-bump-version-tag-release.sh --from-tap --version
   X.Y.Z`.

Verified across all three releases this session.

## Promotion Criteria

Promote when `project-bump-version-tag-release.sh` detects a non-main-worktree
run and performs the post-merge tag against `origin/main` without
`git checkout main`.

## Next Action

Add a worktree-aware post-merge tag step in
project-bump-version-tag-release.sh; file an upstream nils-cli issue
referencing this entry.

Lifecycle link: `sympoies/nils-cli#1049 (tracking issue filed 2026-07-08)`
