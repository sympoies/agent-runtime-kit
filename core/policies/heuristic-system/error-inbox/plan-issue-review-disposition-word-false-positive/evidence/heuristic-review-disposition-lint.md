# plan-issue review disposition visible-lint false positive

- Date: 2026-07-11
- Surface: `plan-issue 1.21.15`
- Tracker: `graysurf/agent-runtime-kit#563`
- Reproduction: a review finding row had `severity=major`, `disposition=fixed`, and a summary beginning `Disposition schema constraints ...`.
- Result: `tracking checkpoint --post review --expect-visible` returned `review-missing-disposition` even though the rendered row contained `fixed`.
- Isolation: changing only the summary prefix from `Disposition schema` to `Ledger schema` made the same checkpoint visible-clean.
- Root cause: `body_contains_review_disposition_row` skips any table row containing the case-sensitive word `Disposition`, not only the header row.
- Workaround: avoid the word `Disposition` in review finding summaries.
