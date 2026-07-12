# heuristic-inbox verify treats manual placeholders as duplicate raw records

## Status

- Status: open
- First observed: 2026-07-12
- Area: heuristic-inbox verify; duplicate detection
- Severity: medium

## Signal

`heuristic-inbox verify --strict` reported two unrelated open cases as
duplicates solely because both were created manually on 2026-07-10. The manual
source scaffold gives every same-day case the identical raw-record placeholder
`not captured (manual diagnosis, YYYY-MM-DD)`, and duplicate detection treats
that placeholder as a retained-record identity.

## Evidence

- Raw record: not captured; deterministic reproduction retained in sympoies/nils-cli#1139
- Summary: strict verification paired
  `plan-issue-tracking-run-init-dry-run-mutates` with
  `read-only-review-subagent-mutates-shared-worktree` for reason `raw_record`,
  despite different slugs, titles, areas, and signals. Current nils-cli source
  confirms that manual scaffolding emits the shared placeholder and duplicate
  detection intersects all normalized raw-record strings without excluding it.

## Impact

Unrelated cases fail strict verification and cannot be delivered through the
canonical closeout path. The false match also obscures real duplicate evidence
because the result presents the same `raw_record` reason for both placeholder
and durable-record collisions.

## Current Workaround

Give manually authored cases a distinct non-placeholder evidence pointer before
strict verification, without inventing a raw record or copying unredacted logs.

## Promotion Criteria

Promote after manual `not captured` placeholders are excluded from raw-record
identity matching while exact shared skill-usage or evidence pointers still
trigger duplicate detection.

## Next Action

Track the fix and regression coverage in
[sympoies/nils-cli#1139](https://github.com/sympoies/nils-cli/issues/1139).
