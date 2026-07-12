# plan-issue review lint mistakes Disposition in a finding summary for the table header

## Status

- Status: open
- First observed: 2026-07-11
- Area: plan-issue tracking review checkpoint visible lint
- Severity: medium

## Signal



`tracking checkpoint --post review --expect-visible` returned
`review-missing-disposition` for a rendered finding row whose disposition was
`fixed`. The finding summary began with `Disposition schema ...`; changing only
that prefix to `Ledger schema ...` made the same row visible-clean.

## Evidence

- Raw record: `evidence/heuristic-review-disposition-lint.md`
- Summary: redacted evidence ingested at creation time; raw logs and secrets were stripped before commit.

## Impact



Valid review evidence can be blocked at the final merge/closeout gate based on
ordinary summary prose. A caller may incorrectly remove the finding or weaken
its evidence to proceed.

## Current Workaround



Avoid the case-sensitive word `Disposition` anywhere in a review finding data
row; use `Ledger`, `classification`, or another precise term in the summary.

## Promotion Criteria



Promote when the visible lint identifies the actual table header structurally
and a regression fixture proves that `Disposition` in the summary column does
not hide a valid `fixed` disposition row.

## Next Action

Narrow header detection to the actual header row and add a finding-summary regression fixture.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1137`
