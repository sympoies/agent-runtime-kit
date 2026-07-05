# forge-cli pr checks --required-only false can fail on GitHub App statusCheckRollup access

## Status

- Status: open
- First observed: 2026-07-05
- Area: forge-cli pr checks; GitHub App status rollup
- Severity: medium

## Signal

During delivery of `sympoies/agent-console` PR #37, `forge-cli pr checks 37 --required-only false --format json` failed while the PR had a non-required GitHub Actions check. The required-only gate had already succeeded because the repo has zero required checks, but the non-required status read hit a GitHub GraphQL permission error under the integration token.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-05)
- Tool versions: `forge-cli 1.20.12 (v1.20.12, rustc 1.96.1)`.
- Repro command: `forge-cli pr checks 37 --required-only false --format json`.
- Observed error: `GraphQL: Resource not accessible by integration (node.statusCheckRollup.nodes.0.commit.statusCheckRollup)`.
- Same PR's Actions run was readable with `gh run view 28738417253 --repo sympoies/agent-console --json status,conclusion,jobs`, which reported `conclusion: success`.

## Impact

Delivery workflows that self-gate non-required checks on repos with no required checks can be forced out of the `forge-cli` surface and into an ad hoc `gh run view` fallback. That weakens the intended provider abstraction and can confuse future agents into either skipping non-required CI or treating a `forge-cli` read failure as a failed check.

## Current Workaround

When required checks are empty but a non-required Actions check exists, use the run URL or run id from the earlier `forge-cli pr deliver` / PR check payload and verify it read-only with `gh run view <run-id> --repo <owner/repo> --json status,conclusion,jobs`. Record the fallback explicitly before merge.

## Promotion Criteria

- Add a nils-cli regression that exercises `forge-cli pr checks --required-only false` against a GitHub PR/check payload that the App token can partially read.
- Fix or intentionally degrade the non-required check reader so it returns usable check evidence or a structured fallback hint instead of a backend GraphQL error.
- Update delivery docs/skills if the intended fallback is not fully automatable.

## Next Action

Reproduce in nils-cli with a PR that has non-required Actions checks under the GitHub App token, then adjust the non-required check reader or add a fallback.
