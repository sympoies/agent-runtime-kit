# plan-issue record close does not atomically normalize lifecycle labels

## Status

- Status: open
- First observed: 2026-07-09
- Last observed: 2026-07-12
- Area: plan-issue record close; tracking issue lifecycle-label normalization
- Severity: medium

## Signal

During closeout of `sympoies/nils-agent-console#7`, the strict
`plan-issue tracking close-ready --expect-visible` gate passed and
`plan-issue record close --dry-run` rendered a valid closeout preview. The live
`plan-issue record close` then posted the closeout comment and closed the issue,
but returned failure at the final label-edit step because the target repository
did not define the requested `state::closed` label.

The provider state after the failure was already closed and visibly complete:
the issue body linked the closeout comment and review approval, the
`state::ready` label had been removed, and a follow-up
`plan-issue record audit --profile tracking --expect-visible` recognized all
required roles including closeout. The only missing side effect was the optional
closed-state label.

A second closeout on `graysurf/agent-runtime-kit#578` exposed the complementary
case. With nils-cli `1.21.19`, live closeout succeeded, added
`state::closed`, accepted a request to remove the absent
`state::needs-triage` label, and passed the seven-role visible audit, but
preserved the pre-existing `state::ready` label.
The closed issue therefore carried two mutually exclusive lifecycle states
until the operator removed `state::ready` separately.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-09)
- Tracking issue:
  `https://github.com/sympoies/nils-agent-console/issues/7`
- Closeout comment:
  `https://github.com/sympoies/nils-agent-console/issues/7#issuecomment-4921934013`
- Approval evidence:
  `https://github.com/sympoies/nils-agent-console/pull/11#pullrequestreview-4660078265`
- Read-back audit artifact:
  `<agent-out>/projects/sympoies__nils-agent-console/20260709-134406-issue-7-closeout-readback/audit.json`
- Failure shape: `record-close-label-edit-failed`; `state::closed` label not
  found after the irreversible provider closeout side effects had already run.
- Second tracking issue:
  `https://github.com/graysurf/agent-runtime-kit/issues/578`
- Second failure shape: successful close with both `state::ready` and
  `state::closed`; seven-role visible audit passed, but lifecycle state was not
  normalized.
- Second workaround: `forge-cli issue edit 578 --remove-label state::ready`.

## Impact

The provider result can be misleading in either direction: the command may
look failed after the issue was already closed, or it may report success while
the issue retains mutually exclusive lifecycle labels. A future agent may rerun
an irreversible closeout, hand-edit provider state unnecessarily, report the
tracker as blocked, or trust an internally inconsistent closed issue.

## Current Workaround

After every close attempt, read back the provider issue and its complete
lifecycle-label group before treating the tracker as converged.

When `record close` fails only at label edit after posting closeout / closing
the issue:

- Do not rerun the mutating close command immediately.
- Read back the issue body and comments, then run
  `plan-issue record audit --profile tracking --expect-visible`.
- If audit passes and the provider issue is closed, treat closeout as complete,
  note the missing optional label, and sync the local bundle manually.
- For repositories without lifecycle labels, omit `--add-label state::closed`
  or create/ensure the label before the mutating close step.

When `record close` succeeds but a closed issue retains a conflicting state
such as `state::ready`, remove that label with a single explicit provider edit
and verify the final label set.

## Promotion Criteria

Promote only after both failure modes are resolved and validated, whether by
one combined fix or multiple changes:

- Unavailable-label handling is made safe: requested label additions are
  preflighted before provider mutation, a missing optional lifecycle label is
  downgraded only after successful read-back, or the closeout flow ensures
  required labels exist and avoids absent optional labels.
- Terminal-state exclusivity is guaranteed: conflicting lifecycle-label
  siblings are removed atomically, or closeout rejects the operation before
  irreversible mutation when it cannot guarantee normalization.

Regression coverage should include both a repository without `state::closed`
and an issue that already carries `state::ready`. Dry-run and live closeout
must not leave the operator with either an ambiguous post-close failure or a
closed issue carrying conflicting lifecycle states.

## Next Action

Route to nils-cli / plan-issue: update `record close` or the closeout skill flow
so label availability and exclusivity are preflighted before provider mutation,
terminal lifecycle labels are normalized atomically, and missing optional
labels are downgraded only after a successful read-back audit.
