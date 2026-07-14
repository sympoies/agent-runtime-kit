# nils-cli release helper times out before healthy release completion

## Status

- Status: open
- First observed: 2026-07-14
- Area: nils-cli release automation
- Severity: medium

## Signal

The nils-cli release helper uses a fixed 1,200-second wait budget. During the
v1.21.39 release it returned a timeout while the GitHub release workflow was
still healthy; the workflow later completed successfully with all four
platform artifacts and dispatched the Homebrew tap update. The same timeout
pattern had already occurred during the preceding v1.21.36-v1.21.38 hotfix
release sequence.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-14)
- Successful release after the client timeout:
  <https://github.com/sympoies/nils-cli/actions/runs/29317966351>
- Published release: <https://github.com/sympoies/nils-cli/releases/tag/v1.21.39>

## Impact

The helper reports a failed release operation even though provider work is
still progressing normally. That can trigger duplicate release attempts,
confuse recovery decisions, and leave the tap/install verification phase
unfinished unless an operator notices the still-running workflow.

## Current Workaround

Watch the exact GitHub Actions run to a terminal state. After the release and
tap workflows succeed, rerun the project release helper with `--from-tap` to
complete installation and verification without recreating the tag.

## Promotion Criteria

Promote after the helper waits on the exact workflow to a terminal state with a
realistic or configurable budget, recovery remains idempotent, and a regression
test covers a healthy release lasting longer than 20 minutes.

## Next Action

Make release waiting follow the workflow terminal state with a realistic configurable budget, then cover the long-running success path.
