# plan-issue close-ready and record close disagree on latest validation truth

## Status

- Status: open
- First observed: 2026-07-10
- Area: plan-issue tracking closeout gates; provider validation reconciliation
- Severity: medium

## Signal

On a live tracking closeout, `tracking close-ready --expect-visible` returned
`ready: true`, `blockers: []`, and `RECORD_READY_FOR_CLOSE`, but the immediately
following `record close` refused with `record-close-gate-failed` because the
latest provider validation payload was `partial`.

The run state already contained `validation.overall=pass` plus a later final
acceptance row. The latest provider validation comment had not been refreshed,
so the two closeout gates selected different validation truth.

## Evidence

- Raw record: not captured (manual diagnosis: close-ready / record-close
  validation mismatch, 2026-07-10).
- Installed surface: nils-cli / plan-issue `1.21.7`.
- Repro tracker: `sympoies/agent-console#217`.
- Stale validation evidence:
  `https://github.com/sympoies/agent-console/issues/217#issuecomment-4936332056`
  (`Overall: partial`).
- Repair validation evidence:
  `https://github.com/sympoies/agent-console/issues/217#issuecomment-4936970143`
  (`Overall: pass`).
- After posting the current run-state validation once, `close-ready` remained
  ready and `record close` succeeded without any implementation or validation
  change.

## Impact

`close-ready` gives false confidence at the exact point it is intended to be the
non-mutating strict probe for `record close`. Delivery can merge and enter the
closeout mutation before discovering a provider/run-state reconciliation gap,
forcing an unplanned repair checkpoint and retry.

## Current Workaround

Before `record close`, read the latest provider validation role rather than
relying only on the run-state summary. If it is stale but the run state contains
real pass evidence, publish one `tracking checkpoint --post validation`, rerun
`close-ready`, and only then retry `record close`.

## Promotion Criteria

Promote when `tracking close-ready` and `record close` share one normalized
validation-source contract and a regression fixture proves they return the same
blocker for provider-latest `partial` / run-state `pass` disagreement.

## Next Action

File an upstream nils-cli regression with a fixture where the provider latest validation is partial but run-state is pass; make close-ready and record close return the same blocker.
