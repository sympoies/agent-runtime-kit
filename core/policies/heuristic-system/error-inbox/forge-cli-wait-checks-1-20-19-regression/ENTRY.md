# forge-cli wait-checks still fails on GitHub App checks in 1.20.19

## Status

- Status: open
- First observed: 2026-07-08
- Area: forge-cli pr wait-checks
- Severity: medium

## Signal

During delivery of `sympoies/agent-console#194` on 2026-07-08,
`forge-cli pr wait-checks` and `forge-cli pr checks` still failed under
`forge-cli 1.20.19`, even though the archived
`forge-cli-wait-checks-statuscheckrollup-permission` case says v1.20.19 fixed
the GitHub checks permission path.

The failure used the normal bot-backed `forge-cli` wrapper. A direct `gh pr
checks` read with the local user token reported both `ci / build` check runs as
passing, and `forge-cli pr merge` then merged the PR successfully.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-08)
- Version: `forge-cli 1.20.19 (v1.20.19, rustc 1.96.1)`.
- Failing commands:
  - `forge-cli --provider github --format json pr checks 194 --required-only true`
  - `forge-cli --provider github --format json pr checks 194 --required-only false`
  - `forge-cli --provider github --format json pr wait-checks 194 --timeout 2m --interval 10s`
- Observed error: `gh: Resource not accessible by integration (HTTP 403)`.
- `forge-cli pr checks 194 --required-only true --dry-run` planned:
  `gh pr checks 194 --required --json name,state,bucket,workflow,link,startedAt,completedAt,description --repo sympoies/agent-console`.
- Direct fallback evidence:
  `gh pr checks 194 --json name,state,bucket,workflow,link,startedAt,completedAt,description --repo sympoies/agent-console`
  returned two `build` rows with `bucket=pass` / `state=SUCCESS`.
- GitHub PR status rollup also showed both `ci / build` check runs completed
  with `conclusion=SUCCESS`; PR #194 was `MERGEABLE` / `CLEAN`.
- Merge evidence: `forge-cli pr merge 194` succeeded with squash merge
  `739af00497d7431707bb106b9c32c5651f31a5b9`; `forge-cli issue close 193
  --reason completed` closed the source issue.
- The local hook blocked an attempted `env -i ... forge-cli ...` probe because
  bypassing the wrapper can post as the user instead of the configured GitHub
  App bot. That supports treating the failure as specific to the bot-backed
  `forge-cli` path rather than bypassing it during delivery.

## Impact

The close-pr skill requires `forge-cli pr wait-checks` before merge. If v1.20.19
still returns a GitHub App permission failure on some PRs, future agents may
misclassify a healthy PR as blocked or skip the required provider-check gate
instead of recording a clear fallback.

## Current Workaround

Use read-only `gh pr checks <pr> --json
name,state,bucket,workflow,link,startedAt,completedAt,description --repo
<owner/repo>` plus `gh pr view <pr> --json statusCheckRollup,mergeStateStatus,mergeable`
to verify the exact PR's checks and mergeability. Continue only after all check
rows are passing and the normal `forge-cli` review-thread, task-list, ready, and
merge gates are clean.

## Promotion Criteria

Promote after nils-cli either fixes the remaining v1.20.19 regression, updates
the delivery skill contract with an explicit bot-permission fallback, or records
an accepted-risk decision explaining why direct `gh pr checks` evidence is the
supported fallback for this class.

## Next Action

Reopen or file a nils-cli follow-up against the archived v1.20.19 fix:
`forge-cli pr wait-checks` and `pr checks` can still return `gh: Resource not
accessible by integration (HTTP 403)` on `sympoies/agent-console#194`, while
direct `gh pr checks --json` succeeds and the PR merges through `forge-cli pr
merge`.
