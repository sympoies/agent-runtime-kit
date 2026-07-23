# agent-docs edit gate becomes unsatisfiable after mid-session nils-cli upgrade

## Status

- Status: open
- First observed: 2026-07-20
- Area: agent-docs
- Severity: high

## Signal

Workflow gap captured from an ingested evidence file. See the Evidence section for the redacted source.

## Evidence

- Raw record: `evidence/task-1.2-handoff.md`
- Summary: redacted evidence ingested at creation time; raw logs and secrets were stripped before commit.

## Impact

Future agents may repeat this workflow gap unless the retained entry is triaged,
routed, and later promoted into a durable fix, runbook, test, script, or skill
policy.

## Current Workaround

Apply the safest manual workaround for the affected workflow until the durable
fix lands, and avoid copying raw logs or secrets into this entry.

## Promotion Criteria

Promote after the durable fix or accepted-risk decision is implemented,
validated, and linked from this entry.

## Next Action

Reproduce a 1.25.5 to 1.25.6 in-session upgrade, then make bootstrap/session preparation tolerate the producer-version transition or emit a recoverable rebootstrap path without requiring a session restart.
