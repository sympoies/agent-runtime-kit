# forge-cli pr deliver returns success while non-required checks are still pending

## Status

- Status: open
- First observed: 2026-07-10
- Area: forge-cli pr deliver; GitHub repositories with zero required checks
- Severity: medium

## Signal

On a GitHub repository with visible CI but no branch-protection-required checks,
`forge-cli pr deliver --no-merge` returned success after its `wait_checks` step
reported `required_count=0`, even though the same payload listed two `build`
checks as pending.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-10).
- Installed surface: `forge-cli 1.21.12`.
- Repro PR: `sympoies/agent-console#240`, final tracker-state commit
  `e3adbf5`.
- `pr deliver --no-merge` exited 0 with `wait_checks.ok=true`,
  `required_count=0`, and both CI runs still pending:
  `29127876980` and `29127875051`.
- A separate `forge-cli pr checks 240 --required-only false --format json`
  poll later reported both runs successful. Delivery was held until that
  all-check read reached `state=success`.
- Reproduced independently on `sympoies/agent-console#245` on 2026-07-11:
  `pr deliver --no-merge` exited 0 with `required_count=0` while `ci / build`
  was still pending. The delivery workflow again held review/merge until a
  separate all-check read showed both runs successful. See
  `evidence/pr245-zero-required-checks.md`.
- The repo's earlier final-content push produced the same zero-required shape:
  visible non-required builds existed, so a required-only result was not a
  complete convergence signal.
- Reproduced as an actual premature merge on `graysurf/agent-runtime-kit#566`
  with `forge-cli 1.21.15`: the macro reported success with CI and CodeQL rows
  still pending, then immediately promoted and squash-merged the PR. The caller
  separately held and verified runs `29148841982` and `29148841380` to success
  after merge. See `evidence/pr566-premature-merge.md`.

## Impact

Delivery workflows can treat a PR as CI-green while every visible build is
still running. A caller that promotes or merges immediately after the macro
returns can land unvalidated content despite believing the canonical wait step
passed.

## Current Workaround

When the delivery result has `required_count=0`, inspect all checks with
`forge-cli pr checks <pr> --required-only false --format json` and wait until
every visible row is terminal and successful before ready/merge.

## Promotion Criteria

Promote when `pr wait-checks` / `pr deliver` falls back to all-check convergence
when no required checks are configured, with a regression fixture containing
two pending optional builds followed by success.

## Next Action

File a nils-cli regression for the zero-required fallback and link its test/fix
here.
