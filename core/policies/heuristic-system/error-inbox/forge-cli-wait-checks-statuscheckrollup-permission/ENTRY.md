# forge-cli wait-checks can fail on GitHub statusCheckRollup permissions

## Status

- Status: open
- First observed: 2026-07-07
- Area: forge-cli
- Severity: medium

## Signal

During `agent-console` PR #152 delivery on 2026-07-07, the provider delivery
flow could not use `forge-cli pr wait-checks` after reviews were posted. The
command returned a GitHub GraphQL permission failure for
`repository.pullRequest.statusCheckRollup.nodes.0.commit.statusCheckRollup`,
while `gh pr checks` still returned the PR's `ci / build` checks as passing.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-07)
- Summary: `forge-cli pr wait-checks 152` failed with
  `Resource not accessible by integration` for the nested `statusCheckRollup`
  field. `gh pr checks 152 --json ...` returned two `ci / build` check runs in
  `SUCCESS`, and the PR merged through `forge-cli pr merge` after specialist
  reviews and thread/task gates passed.

## Impact

Future agents may see a delivery primitive fail closed even though provider
checks are readable through `gh pr checks` and merge gates are otherwise clean.
Without a fallback or clearer error, the agent has to infer that this is a
GitHub GraphQL field-permission issue rather than a CI failure.

## Current Workaround

Use `gh pr checks <pr> --json name,state,bucket,workflow,link,startedAt,completedAt,description`
to capture provider check evidence, then continue the normal `forge-cli`
thread/task/final-review/merge gates when the check rows are all passing.

## Promotion Criteria

Promote after nils-cli either avoids the inaccessible nested
`statusCheckRollup` field, falls back to the simpler `gh pr checks` surface, or
returns an explicit diagnostic with the supported workaround. Include a
regression that simulates this GitHub permission failure.

## Next Action

Add a nils-cli regression or fallback so wait-checks handles GitHub statusCheckRollup permission errors, or emits the documented gh pr checks workaround.
