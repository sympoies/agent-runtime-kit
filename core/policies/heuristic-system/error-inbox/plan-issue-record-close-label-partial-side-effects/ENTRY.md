# plan-issue record close mutates provider state before failing on missing labels

## Status

- Status: open
- First observed: 2026-07-09
- Area: plan-issue record close; tracking issue closeout labels
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

## Impact

The command looks failed even though the issue is already closed and the
closeout marker is already posted. A future agent may rerun mutating closeout,
hand-edit provider state unnecessarily, or report the tracker as blocked instead
of doing a read-back audit and accepting the completed closeout minus the
optional label.

## Current Workaround

When `record close` fails only at label edit after posting closeout / closing
the issue:

- Do not rerun the mutating close command immediately.
- Read back the issue body and comments, then run
  `plan-issue record audit --profile tracking --expect-visible`.
- If audit passes and the provider issue is closed, treat closeout as complete,
  note the missing optional label, and sync the local bundle manually.
- For repositories without lifecycle labels, omit `--add-label state::closed`
  or create/ensure the label before the mutating close step.

## Promotion Criteria

Promote after one of these lands and is validated:

- `plan-issue record close` preflights requested label additions before any
  provider mutation.
- `plan-issue record close` treats a missing optional lifecycle label as a
  warning when closeout, provider close, dashboard update, and read-back audit
  have already succeeded.
- The closeout skill flow ensures required labels exist, or avoids passing
  absent optional lifecycle labels on repositories that do not use them.

Regression coverage should include a repository without `state::closed` where
dry-run passes and live closeout cannot leave the operator with an ambiguous
post-close failure.

## Next Action

Route to nils-cli / plan-issue: update `record close` or the closeout skill flow
so label availability is preflighted before provider mutation, or missing
optional lifecycle labels are downgraded after a successful read-back audit.
