# forge-cli pr checks can fail on GitHub statusCheckRollup permissions

## Status

- Status: promoted
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

- Raw record: manual diagnosis for sympoies/agent-console PR #55 checks
  read-back, 2026-07-05
- Summary: `forge-cli pr checks` returned `backend_error` with
  `GraphQL: Resource not accessible by integration
  (nested status check rollup commit field)`.
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
with GitHub App authentication, with a regression test or provider-smoke evidence
covering the permission-limited path. Wontfix only if the direct checks command
is documented as best-effort and delivery skills consistently use a separate
stable read path.

## Next Action

None. Promoted to consolidated provider follow-up issue https://github.com/sympoies/nils-cli/issues/1030.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1030`

## Archive

- Archived: 2026-07-06
- Reason: Promoted to consolidated provider follow-up issue.
- Durable link: `https://github.com/sympoies/nils-cli/issues/1030`
