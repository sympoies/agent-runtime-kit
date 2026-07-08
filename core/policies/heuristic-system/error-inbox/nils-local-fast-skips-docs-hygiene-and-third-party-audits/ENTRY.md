# nils-cli --local-fast skips docs-hygiene + third-party audits that only run in full CI

## Status

- Status: open
- First observed: 2026-06-15
- Area: ci
- Severity: medium

## Signal

`bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast` (the declared
`project-dev` validation for nils-cli code edits) scopes to the changed
package(s) and runs fmt / clippy / tests, but does **not** run two audits that
the full GitHub CI `test` job *does* run:

- `scripts/ci/docs-hygiene-audit.sh --strict` — bans certain keywords in
  `crates/**/*.rs` and active docs (e.g. a literal `legacy`, whole-word,
  case-insensitive).
- `scripts/ci/third-party-artifacts-audit.sh --strict` — fails on drift in
  `THIRD_PARTY_*` artifacts when a crate's transitive dependency set changes.

So a change that passes `--local-fast` clean can still fail CI's `test` job.
This session hit both:

1. Comments + a test identifier used the word `legacy` (10 hits) → CI `test`
   failed `FAIL: legacy keyword reintroduced in Rust sources`; `--local-fast`
   had passed. Fix: replace `legacy` with `orphaned`.
2. Adding an intra-workspace dependency (`nils-evidence -> nils-agent-out`)
   dragged `chrono` into nils-evidence's transitive tree → third-party artifact
   drift, caught only by the third-party audit. (This particular case was then
   avoided by hoisting the shared helper into `nils-common` instead of adding
   the dep — but the audit-scope gap is the durable lesson.)

## Evidence

- Raw record: not captured (manual diagnosis, 2026-06-15; --local-fast vs full-CI audit gap, nils-cli #873).
- Summary: `--local-fast` reported "local-fast package checks passed" while the
  full CI `test` job (run via
  `.agents/skills/project-verify-required-checks/scripts/project-verify-required-checks.sh`,
  "includes third-party-artifacts-audit, completion audits, docs-hygiene-audit,
  test-stale-audit") failed. Reproduced green locally only after running
  `docs-hygiene-audit.sh --strict` and `third-party-artifacts-audit.sh --strict`
  directly. Observed on PR #873 (docs-hygiene) during nils-cli delivery.

## Impact

Relying on the declared `--local-fast` gate as the pre-push signal causes a CI
round-trip (red `test` / `test_macos`) whenever a diff touches comments/docs
with a banned keyword or changes a crate's dependency tree. Each round-trip
costs a full CI cycle (~7-11 min including the slow macOS runner).

## Current Workaround

When a diff touches Rust comments/docs or any dependency, run the two audits
locally before pushing, in addition to `--local-fast`:

```
bash scripts/ci/docs-hygiene-audit.sh --strict
bash scripts/ci/third-party-artifacts-audit.sh --strict
```

For dependency changes, prefer hoisting shared helpers into an already-shared
crate (e.g. `nils-common`) over adding a new cross-crate dependency, to avoid
dragging transitive deps (and third-party drift) into the consumer.

## Promotion Criteria

Promote when either: (a) `--local-fast` is extended to run docs-hygiene +
third-party audits (at least for the changed surface) so the local gate matches
what blocks CI; or (b) DEVELOPMENT.md / the project-dev validation contract
documents that these audits are not covered by `--local-fast` and must be run
separately. Link the change here.

## Next Action

File an upstream nils-cli issue proposing `--local-fast` either include the
docs-hygiene and third-party audits or explicitly document the coverage gap.

Lifecycle link: `sympoies/nils-cli#1053 (tracking issue filed 2026-07-08; third-party half already fixed, issue narrows to docs-hygiene on Rust-only diffs)`
