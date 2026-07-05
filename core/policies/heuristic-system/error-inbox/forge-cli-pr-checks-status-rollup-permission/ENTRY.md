# forge-cli pr checks can fail on GitHub statusCheckRollup permissions

## Status

- Status: open
- First observed: 2026-07-05
- Area: forge-cli pr checks
- Severity: medium

## Signal

During an agent-console delivery, `forge-cli pr deliver --no-merge` successfully
created PR #55 and waited through the GitHub Actions `build` check, but a later
direct `forge-cli --provider github pr checks 55 --repo sympoies/agent-console
--format json` failed with a provider backend error instead of returning the
same check state.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-05)
- Summary: `forge-cli pr checks` returned `backend_error` with
  `GraphQL: Resource not accessible by integration
  (node.statusCheckRollup.nodes.0.commit.statusCheckRollup)`.
- Contrasting evidence: `gh pr view 55 --repo sympoies/agent-console --json
  statusCheckRollup` returned two completed successful `ci / build` check runs,
  and `forge-cli pr deliver --no-merge` had already observed a successful
  provider check for the same PR.

## Impact

Delivery workflows may lose the canonical `forge-cli pr checks` read-back after
review comments or bot-auth context changes, forcing agents to use raw provider
commands for merge evidence. This weakens the intended provider-primitive
boundary and can block automated merge gates if the same query shape is reused
there.

## Current Workaround

Use the check state from `forge-cli pr deliver --no-merge` / `forge-cli pr
wait-checks` when available. If a later read-back is needed and `pr checks`
fails with this GraphQL permission error, use `gh pr view --json
statusCheckRollup` as a read-only fallback and record that fallback in the
delivery outcome.

## Promotion Criteria

Promote after `forge-cli pr checks` avoids the nested
`commit.statusCheckRollup` access pattern or implements a fallback that works
with GitHub App tokens, with a regression test or provider-smoke evidence
covering the permission-limited path. Wontfix only if the direct checks command
is documented as best-effort and delivery skills consistently use a separate
stable read path.

## Next Action

Investigate whether forge-cli pr checks should avoid the nested commit.statusCheckRollup field or fall back to the PR rollup shape when GitHub App tokens cannot read it.
