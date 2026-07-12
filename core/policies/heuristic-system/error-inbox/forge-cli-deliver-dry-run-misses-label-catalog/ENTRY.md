# forge-cli pr deliver dry-run misses strict-label catalog failure

## Status

- Status: open
- First observed: 2026-07-12
- Area: forge-cli pr deliver; dry-run/live preflight parity
- Severity: medium

## Signal

`forge-cli pr deliver --dry-run --strict-labels` returned `ok=true` and reported
every local preflight rule as passing even though no `--label-catalog` was
supplied. The otherwise-identical live delivery then failed before provider
mutation with `label_catalog_missing`. Retrying without `--strict-labels`
succeeded and the owning delivery completed.

## Evidence

- Raw record: `$HOME/.local/state/agent-runtime-kit/out/projects/sympoies__agent-console/20260712-080453-skill-usage/skill-usage.record.json`
- The verified record classifies the failure as `skill_contract`, records exit
  code 2, and retains the successful retry plus PR #267 merge validation.
- No matching `sympoies/nils-cli` issue was found by issue-title/body search on
  2026-07-12.

## Impact

The dry-run describes itself as a faithful predictor of live local gates. This
false pass wastes a delivery round trip and can make callers trust a preflight
that does not enforce the live command's argument contract.

## Current Workaround

When a repository has no label catalog, omit `--strict-labels`. When strict
validation is required, pass an explicit `--label-catalog` even if dry-run
currently accepts the incomplete flag set.

## Promotion Criteria

Promote after a nils-cli regression proves dry-run and live delivery make the
same `--strict-labels` / `--label-catalog` decision before provider mutation,
and the released fix is linked here.

## Next Action

File the upstream nils-cli issue with the retained minimal repro, add a
regression proving dry-run and live delivery reject `--strict-labels` without
`--label-catalog` before provider mutation, then align both preflight paths.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1131`
