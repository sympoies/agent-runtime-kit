# forge-cli PR checks can fail on GitHub statusCheckRollup permission

## Status

- Status: promoted
- First observed: 2026-07-04
- Area: forge-cli pr checks / wait-checks; GitHub GraphQL statusCheckRollup permissions
- Severity: medium

## Signal

During live delivery of `graysurf/foraver#74`, the lower-level
`forge-cli pr checks` / `forge-cli pr wait-checks` GitHub path could not be used
for CI gating because the GitHub GraphQL query failed with:
`Resource not accessible by integration
(node.statusCheckRollup.nodes.0.commit.statusCheckRollup)`.

The PR was otherwise healthy and mergeable. The delivery had to fall back to
`gh run list` / `gh run watch` against the branch workflow run, manually
confirming the latest run's `headSha` matched the PR head commit before trusting
the successful CI result.

## Evidence

- Raw record: manual diagnosis during graysurf/foraver#74 delivery, 2026-07-04;
  `forge-cli pr checks` / `wait-checks` GraphQL statusCheckRollup permission
  error with fallback to Actions run watch.
- Summary: `graysurf/foraver#74` delivery, PR head `bf25f28`, GitHub CI run
  `28716027239` passed after the fallback. The provider-visible delivery
  approval recorded the fallback: "`forge-cli` checks lookup was unavailable
  earlier due provider GraphQL statusCheckRollup permissions, so CI was verified
  with `gh run watch`/`gh run list`."

## Impact

PR delivery skills tell agents to use `forge-cli pr wait-checks` as the normal
check gate. If this GitHub field is inaccessible to the invoking integration,
agents can misclassify a healthy PR as blocked or skip the required head-SHA
cross-check when falling back manually. The failure is especially confusing
because GitHub Actions itself has enough visible information through workflow
runs, but the GraphQL status rollup path is not available through the same auth
surface.

## Current Workaround

Use the Actions run surface as a fallback:

1. Run `gh run list --branch <head-branch> --workflow CI --json databaseId,status,conclusion,headSha,url`.
2. Confirm the newest run's `headSha` equals the PR head commit.
3. Wait with `gh run watch <databaseId> --exit-status`.
4. Record the fallback in the delivery review outcome before merge.

## Promotion Criteria

Promote after `forge-cli` either:

- Avoids permission-sensitive `statusCheckRollup` GraphQL fields for the GitHub
  checks path; or
- Falls back to a REST / Actions-run implementation keyed by PR head SHA when
  the status rollup query returns this permission error.

Validation should include a regression fixture for the GraphQL permission error
and a live or stubbed fallback run proving the selected check result is keyed to
the exact PR head commit.

## Next Action

None. Promoted to consolidated provider follow-up issue https://github.com/sympoies/nils-cli/issues/1030.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1030`

## Archive

- Archived: 2026-07-06
- Reason: Promoted to consolidated provider follow-up issue.
- Durable link: `https://github.com/sympoies/nils-cli/issues/1030`
