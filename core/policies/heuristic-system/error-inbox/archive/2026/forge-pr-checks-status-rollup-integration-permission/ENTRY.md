# forge-cli pr checks can fail on GitHub statusCheckRollup integration permission

## Status

- Status: promoted
- First observed: 2026-07-05
- Area: forge-cli GitHub PR checks
- Severity: medium

## Signal

During delivery of sympoies/agent-console#60, `forge-cli pr checks` failed on a
mergeable GitHub PR even though the native GitHub check runs were readable and
passing. The command returned a GitHub GraphQL integration-permission error
while traversing nested `statusCheckRollup` data:

```text
GraphQL: Resource not accessible by integration (node.statusCheckRollup.nodes.0.commit.statusCheckRollup)
```

The same PR's checks were readable through `gh pr checks`, and the PR merged
after manual fallback verification. This means an agent following the
`forge-cli` PR lifecycle can be forced off the standard check gate even when the
provider has enough visible status data to make a safe merge decision.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-05).
- Version: `forge-cli 1.20.13`.
- Repro command:
  `forge-cli --provider github pr checks 60 --repo sympoies/agent-console --required-only false --format json`
- Observed failure:
  `GraphQL: Resource not accessible by integration (node.statusCheckRollup.nodes.0.commit.statusCheckRollup)`.
- Fallback command:
  `gh pr checks 60 --repo sympoies/agent-console --watch --interval 10`
  reported both `build` checks passed on PR head
  `b60035943f892de9f9dfd8dfc10707bdf9fa0737`.
- Related but not identical prior work: sympoies/nils-cli#439 tracked GitHub
  checks compatibility and is closed; this nested-rollup integration
  permission failure still reproduced on 2026-07-05.

## Impact

`forge-cli pr wait-checks` / delivery macros can block or require undocumented
manual fallback on GitHub PRs whose check rollup contains nested commit rollup
nodes the current integration cannot read. Without a documented fallback, an
agent can either stop despite passing CI or be tempted to merge without a
head-SHA keyed check snapshot.

## Current Workaround

When `forge-cli pr checks` fails with this exact GraphQL path, use read-only
`gh pr view --json headRefOid,statusCheckRollup,mergeable,reviewDecision` and
`gh pr checks <number> --repo <owner/repo>` as a fallback. Confirm the checks
belong to the current PR head SHA, then continue through `forge-cli pr ready`
and `forge-cli pr merge`; do not mutate provider state through raw `gh`.

## Promotion Criteria

Promote/close when `forge-cli pr checks` and `pr wait-checks` either avoid the
unreadable nested `commit.statusCheckRollup` path, degrade to the readable check
run/status fields, or return an actionable error that names the approved
head-SHA keyed `gh` fallback. Add a regression fixture for this GraphQL error
shape and link the nils-cli issue/PR.

## Next Action

None. Promoted to consolidated provider follow-up issue https://github.com/sympoies/nils-cli/issues/1030.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1030`

## Archive

- Archived: 2026-07-06
- Reason: Promoted to consolidated provider follow-up issue.
- Durable link: `https://github.com/sympoies/nils-cli/issues/1030`
