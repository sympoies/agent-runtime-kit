# plan-issue close-ready and record close disagree on latest lifecycle truth

## Status

- Status: open
- First observed: 2026-07-10
- Area: plan-issue tracking closeout gates; provider lifecycle reconciliation
- Severity: medium

## Signal

Two live tracking closeouts showed the same gate divergence across different
lifecycle roles. `tracking close-ready --expect-visible` returned `ready: true`,
`blockers: []`, and `RECORD_READY_FOR_CLOSE`, but the immediately following
`record close` refused with `record-close-gate-failed`.

For #217, the run state contained `validation.overall=pass` while the latest
provider validation comment remained `partial`. For #228, close-ready passed
while the latest review payload still contained two `major` `residual`
findings; record close then rejected them as `review-unresolved-findings`.
Refreshing the provider validation or review role made the same record-close
operation succeed without a product implementation change.

## Evidence

- Raw record: not captured (manual diagnosis: close-ready / record-close
  validation mismatch, 2026-07-10).
- Installed surfaces: nils-cli / plan-issue `1.21.7` (#217) and `1.21.11`
  (#228).
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
- Second repro tracker: `sympoies/agent-console#228`. Close-ready reported
  ready, but record close rejected the latest review findings until a repaired
  review checkpoint marked the two major residuals fixed.
- Upstream tracker:
  `https://github.com/graysurf/plan-tracking-testbed/issues/79`.

## Impact

`close-ready` gives false confidence at the exact point it is intended to be the
non-mutating strict probe for `record close`. Delivery can merge and enter the
closeout mutation before discovering a provider/run-state reconciliation gap
in validation or review truth, forcing an unplanned repair checkpoint and
retry.

## Current Workaround

Before `record close`, read the latest provider validation and review roles
rather than relying only on the run-state summary. If either is stale but the
run state contains real pass/fixed evidence, publish one bounded
`tracking checkpoint --post validation,review`, rerun both visible audits, and
only then invoke `record close`.

## Promotion Criteria

Promote when `tracking close-ready` and `record close` share one normalized
lifecycle-source contract and regression fixtures prove they return the same
blocker for provider-latest validation and review disagreements.

## Next Action

Drive `graysurf/plan-tracking-testbed#79` to a shared gate contract and add the
validation mismatch fixture so close-ready and record close return the same
blocker for every terminal lifecycle role.
