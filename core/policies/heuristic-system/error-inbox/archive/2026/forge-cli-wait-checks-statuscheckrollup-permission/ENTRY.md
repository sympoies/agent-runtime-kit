# forge-cli wait-checks can fail on GitHub statusCheckRollup permissions

## Status

- Status: promoted
- First observed: 2026-07-07
- Area: forge-cli
- Severity: medium

## Signal

During `agent-console` PR #152 delivery on 2026-07-07, the provider delivery
flow could not use `forge-cli pr wait-checks` after reviews were posted. The
command returned a GitHub GraphQL permission failure for
`repository.pullRequest.statusCheckRollup.nodes.0.commit.statusCheckRollup`,
while `gh pr checks` still returned the PR's `ci / build` checks as passing.
The same failure then recurred on `agent-console` PRs #156, #162, and #171
before the nils-cli fix shipped.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-07)
- Summary: `forge-cli pr wait-checks 152` failed with
  `Resource not accessible by integration` for the nested `statusCheckRollup`
  field. `gh pr checks 152 --json ...` returned two `ci / build` check runs in
  `SUCCESS`, and the PR merged through `forge-cli pr merge` after specialist
  reviews and thread/task gates passed.
- Recurrence evidence:
  - `evidence/forge-wait-checks-156.md`
  - `evidence/pr-162-wait-checks-permission.md`
  - `evidence/pr-171-statuscheckrollup.md`
  These records show the same GraphQL permission error while the simpler
  `gh pr checks` surface reported passing provider checks.
- Fix evidence: `sympoies/nils-cli#1044` added a regression for the
  permission-error path and changed GitHub checks lookup to avoid
  `statusCheckRollup` GraphQL rollups after that error. The fallback uses the
  commit SHA plus REST check-runs/statuses and fail-closes on truncated pages.
- Release evidence: `sympoies/nils-cli#1045` shipped `v1.20.19`; the source
  release workflow and Homebrew tap workflow completed successfully, and both
  local Mac and `sympoies` hosts verified `forge-cli 1.20.19`.

## Impact

Future agents may see a delivery primitive fail closed even though provider
checks are readable through `gh pr checks` and merge gates are otherwise clean.
Without a fallback or clearer error, the agent has to infer that this is a
GitHub GraphQL field-permission issue rather than a CI failure.

## Current Workaround

Resolved. On `forge-cli 1.20.19+`, run the normal `forge-cli pr wait-checks`
or `forge-cli pr checks` path.

Historical workaround:

Use `gh pr checks <pr> --json name,state,bucket,workflow,link,startedAt,completedAt,description`
to capture provider check evidence, then continue the normal `forge-cli`
thread/task/final-review/merge gates when the check rows are all passing.

## Promotion Criteria

Promote after nils-cli either avoids the inaccessible nested
`statusCheckRollup` field, falls back to the simpler `gh pr checks` surface, or
returns an explicit diagnostic with the supported workaround. Include a
regression that simulates this GitHub permission failure.

## Next Action

None; fixed by nils-cli v1.20.19, which avoids the unreadable GraphQL
statusCheckRollup path and falls back to REST check-runs/statuses with
fail-closed pagination handling.

Lifecycle link: `https://github.com/sympoies/nils-cli/pull/1044`

## Closeout Decision

Archive this case as promoted. No separate operation record is warranted: the
reusable lesson now lives inside released `forge-cli` behavior and regression
coverage, so the archived inbox entry plus nils-cli release are the durable
record.

## Archive

- Archived: 2026-07-08
- Reason: Promoted: fixed by nils-cli v1.20.19 forge-cli GitHub checks REST fallback and validated on both hosts
- Durable link: `https://github.com/sympoies/nils-cli/releases/tag/v1.20.19`
