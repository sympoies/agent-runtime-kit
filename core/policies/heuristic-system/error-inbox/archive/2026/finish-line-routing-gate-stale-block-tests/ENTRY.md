# finish-line #599 routing gate breaks legacy block-message tests

## Status

- Status: promoted
- First observed: 2026-07-23
- Area: hooks
- Severity: medium

## Signal

`bash tests/hooks/run.sh` (position 13 of `scripts/ci/all.sh`) fails ~15
`test_finish_line_*` cases across 15/16 parallel shards in this workspace, while
the finish-line hook itself is clean/committed and the change under test only
adds unrelated `main-agent quick` allowlist coverage.

## Evidence

- Raw record: not captured; manual diagnosis of the finish-line #599 routing-gate test drift, 2026-07-23
- The routing-review gate landed committed in `ab6176c`
  (`feat(hooks): route discovered validation defects (#599)`);
  `core/hooks/shared/stop-finish-line-gate.py` is clean in the working tree.
- The failing tests assert the pre-`#599` block strings (`failed with exit code
  17`, `has not passed since`) but the hook now returns the
  `discovered-defect routing review required` prompt instead. In the hermetic
  temp env the prompt also appends `The routing-review marker could not persist,
  so the waiver remains blocked` — i.e. `routing_review_marker` / `touch_marker`
  cannot write under the test's temp `dir`.
- Not simple session-env contamination: failures persist after scrubbing
  `AGENT_SESSION_ID`, `AGENT_SESSION_STATE_DIR`,
  `AGENT_SESSION_CAPABILITY_FILE`, `AGENT_RUNTIME_STATE_HOME`, and `HOME`.
- Repro: `bash tests/hooks/run.sh`. Manual diagnosis (no raw skill-usage
  record); redacted excerpt ingested.
- Evidence: `evidence/finish-line-evidence.md`

## Impact

Blocks `tests/hooks/run.sh` (and therefore `scripts/ci/all.sh` position 13) as a
whole in this workspace regardless of the change under test, so any code edit
must waive that position. The same gate also re-fires the Stop routing-review
prompt because its marker never persists, forcing repeated manual routing.

## Current Workaround

Treat the position-13 finish-line reds as a documented, pre-existing waiver and
validate the specific change through targeted probes (skill-governance,
exposure-contract, golden diff, runtime-smoke, and the change's own hook tests)
instead of relying on a fully green `tests/hooks/run.sh`.

## Resolution

Resolved 2026-07-23 in agent-runtime-kit. The root cause was narrower than the
first diagnosis: both the finish-line hook and the `test_finish_line_*`
assertions were correct, and there was no marker-persistence defect (the marker
persisted fine in the writable temp repos). The real defect was test
hermeticity — `run_hook`/`run_shell_hook` in
`tests/hooks/test_shared_hooks.py` built the hook subprocess environment from
`dict(os.environ)` and scrubbed only `AGENT_SESSION_ID`, so the live agent's
ambient `AGENT_RUNTIME_VALIDATION_WAIVER=1` (a `WAIVER_ENVS` member) leaked in
and forced the `#599` routing-review branch for every fixture that expected the
ordinary block message.

Fix: scrub the finish-line waiver/suppress envs (`AMBIENT_GATE_ENVS`) from the
inherited environment before applying each fixture's explicit `env=`, so tests
that exercise the waiver/suppress path re-supply it deliberately and all others
run hermetically.

Validation: `bash tests/hooks/run.sh` -> all 329 tests pass across 16 shards
(previously ~45 `test_finish_line_*` failures across 15/16 shards).

## Promotion Criteria

Promote after the durable fix or accepted-risk decision is implemented,
validated, and linked from this entry.

## Next Action

None. Resolved in agent-runtime-kit: `run_hook`/`run_shell_hook` in
`tests/hooks/test_shared_hooks.py` now scrub the ambient finish-line
waiver/suppress envs (`AMBIENT_GATE_ENVS`) before applying each fixture's
explicit `env=`, so all 329 hook tests pass across 16 shards. See Resolution.

## Archive

- Archived: 2026-07-23
- Reason: fixed in agent-runtime-kit; see ENTRY Resolution
