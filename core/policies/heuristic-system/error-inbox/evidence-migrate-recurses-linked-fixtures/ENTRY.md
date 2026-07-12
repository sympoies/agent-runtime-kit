# evidence migrate recursively treats linked test fixtures as source records

## Status

- Status: open
- First observed: 2026-07-12
- Area: evidence archive; agent-out source enumeration
- Severity: medium

## Signal

The session-closeout archive dry-run scanned 157 `skill-usage.record.json`
files but reported zero eligible records and 157 blocked records. The blocked
paths were not canonical project run records: they were linked runtime-smoke
fixtures nested below a retained `test-first-evidence` artifact.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-12).
- `evidence migrate --format json`: `scanned=157`, `eligible=0`; all 157
  records were blocked.
- Blocked-reason split: 122 unresolved repo identities and 35 deliberately
  malformed JSON fixtures.
- Representative redacted shape:
  `<agent-out>/projects/graysurf__agent-runtime-kit/<run>/focused-runtime-smoke/meta/evidence-migrate/out/projects/graysurf__agent-runtime-kit/<fixture>/skill-usage.record.json`.
- `evidence prune-source --archived-only --format json`: `scanned=157`,
  `prunable=0`, `kept=157`, all with reason `not archived`.

## Impact

Whole-tree closeout retention is permanently noisy: expected runtime-smoke
fixtures look like live source records, so every closeout surfaces a large
blocked set and cannot distinguish a new real blocker from test data. Source
pruning also retains the same nested fixtures indefinitely.

## Current Workaround

Do not vouch for or manually delete these paths. Recognize the nested
`runtime-smoke/.../out/projects/...` records as test fixtures, leave them
blocked, and report the retention lane as surfaced-for-review.

## Promotion Criteria

Promote when `evidence migrate` and `evidence prune-source` enumerate only
canonical agent-out run records, while a regression test proves that linked
evidence containing nested `skill-usage.record.json` fixtures is not treated as
an independent source run.

## Next Action

Restrict source enumeration to canonical agent-out run records and add a regression fixture with nested skill-usage evidence.
