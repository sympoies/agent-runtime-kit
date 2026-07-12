# Dispatch closeout renderer conflicts with visible-lint heading

## Status

- Status: open
- First observed: 2026-07-11
- Area: plan-issue
- Severity: high

## Signal

Skill `dispatch:dispatch-plan-closeout` ended with `worked_around`. The released
`plan-issue record close --profile dispatch` renderer emits
`## Dispatch Issue Closeout`, while the active vNext registry and visible lint
require `## Tracking Issue Closeout`; strict read-back therefore reports
`closeout-missing-heading` after an otherwise successful close.

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/graysurf__agent-runtime-kit/20260712-063537-dispatch-closeout-heading-gap/skill-usage.record.json`
- Summary: linked `skill-usage.record.v1` envelope; raw runtime details remain in the evidence location.

## Impact

Future agents may repeat this workflow gap unless the retained entry is triaged,
routed, and later promoted into a durable fix, runbook, test, script, or skill
policy.

## Current Workaround

Append an evidence-identical closeout comment with only the heading changed to
`## Tracking Issue Closeout` through `forge-cli issue comment`, run
`record repair-dashboard`, and require `record audit --expect-visible` to pass
all seven roles. Preserve the original generated comment for diagnosis.

## Promotion Criteria

Promote after the durable fix or accepted-risk decision is implemented,
validated, and linked from this entry.

## Next Action

Align dispatch closeout rendering with the active Tracking Issue Closeout heading contract and add dispatch read-back regression coverage.
