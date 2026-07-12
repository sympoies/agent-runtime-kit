# plan-issue tracking run init --dry-run rewrites live run-state

## Status

- Status: open
- First observed: 2026-07-10
- Area: plan-issue tracking run controller; dry-run safety
- Severity: medium

## Signal

During the close-ready handoff for `sympoies/agent-console#216`,
`plan-issue tracking run init ... --out <existing-run-state> --dry-run --format
json` returned a success envelope carrying `dry_run: true`, but still replaced
the existing run-state. The file changed from the accumulated `reviewing` run
to a new `initial` run with a new timestamp, one linked PR, and no retained
validation, review, or notes.

## Evidence

- Raw record: not captured (manual diagnosis of agent-console#216 tracking run dry-run, 2026-07-10)
- Reproduction surface: `plan-issue tracking run init --out
  <existing-run-state> --dry-run --format json`.
- Provider workflow: <https://github.com/sympoies/agent-console/issues/216>.
- Source anchor: `sympoies/nils-cli:crates/plan-issue/src/execute.rs`,
  `run_tracking_run_init`; the write and event-append path executes without a
  local dry-run guard.
- Recovery validation: the run was reconstructed through `tracking run update`;
  the final `tracking close-ready` probe returned `ready: true` with zero
  blockers.

## Impact

Dry-run is expected to be non-mutating, so using it as the prescribed preflight
against an existing `--out` path can silently destroy the current local run
summary and append a duplicate start event. Provider comments remain durable,
but the agent must reconstruct local validation, review, notes, and linked PRs
before a correct close-ready checkpoint can be rendered.

## Current Workaround

Do not run `tracking run init --dry-run` with an existing run-state path. Use
`tracking status`, `tracking checkpoint` without `--live`, or a disposable
`--out` path for preflight. If an existing run was overwritten, reconstruct it
through typed `tracking run update` calls and verify the rendered checkpoint
before posting.

## Promotion Criteria

Promote after a regression proves both `run-state.json` and `events.jsonl`
remain byte-identical under `tracking run init --dry-run`, the implementation
returns before all filesystem writes, and a released binary passes the live
command shape above.

## Next Action

File a focused nils-cli bug, add a failing CLI regression proving `--dry-run`
leaves `run-state.json` and `events.jsonl` byte-identical, then make `tracking
run init` honor dry-run before filesystem writes.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1138`
