# skill-usage stores https:// artifacts as https:/ paths

## Status

- Status: open
- First observed: 2026-07-07
- Area: skill-usage CLI; evidence retention URL fields
- Severity: low

## Signal

During session closeout, `skill-usage` accepted absolute HTTPS URLs for
`link-record --path` and `record-outcome --artifact`, but persisted them as
`https:/...` with only one slash after the scheme. The record had to be patched
manually before `skill-usage verify` so the retained evidence links stayed
usable.

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/sympoies__agent-console/20260708-054549-skill-usage/skill-usage.record.json`
- Summary: linked `skill-usage.record.v1` envelope; raw runtime details remain in the evidence location.
- Observed commands:
  - `skill-usage link-record --type plan-issue-closeout --path 'https://github.com/sympoies/nils-cli/issues/1046#issuecomment-4909586590'`
    stored `https:/github.com/sympoies/nils-cli/issues/1046#issuecomment-4909586590`.
  - `skill-usage record-outcome --artifact 'https://github.com/sympoies/nils-cli/issues/1046'`
    and sibling PR URLs stored `https:/github.com/...`.

## Impact

Raw `skill-usage` evidence can lose clickable provider links even when the user
workflow succeeded. That makes later evidence migration, plan archive queries,
and closeout audits harder to follow, and it can hide the durable issue / PR
trail unless the agent notices and patches the JSON by hand.

## Current Workaround

After using URL-valued `--path` or `--artifact` fields, run
`skill-usage show` or `skill-usage verify` and inspect retained URLs. If any
provider URL was normalized to `https:/...`, patch the record back to
`https://...` before evidence migration. Keep raw runtime evidence in place; do
not copy full logs into retained records.

## Promotion Criteria

Promote after `skill-usage` treats URL-like strings as URLs rather than
filesystem paths for `link-record --path` and `record-outcome --artifact`, with
regression coverage for both fields and a verified retained record containing
unchanged `https://` links.

## Next Action

Add a nils-cli regression for URL-valued link-record paths and record-outcome artifacts, then preserve absolute URLs without Path normalization.
