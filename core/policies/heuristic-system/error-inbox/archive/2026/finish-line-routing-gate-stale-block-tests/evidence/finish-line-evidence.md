# finish-line #599 routing-gate test drift — evidence (redacted)

Repro: `bash tests/hooks/run.sh` in agent-runtime-kit (working tree at
`b9e0e56`; `core/hooks/shared/stop-finish-line-gate.py` clean/committed).

Representative failures (temp paths are hermetic test dirs, not secrets):

```
FAIL: test_finish_line_missing_tool_id_keeps_attempts_distinct
    self.assert_blocked(decision, "failed with exit code 17")
AssertionError: 'failed with exit code 17' not found in 'Validation is being
waived in tmp<redacted>; discovered-defect routing review required before
finishing. ... This is a one-shot routing prompt; the next Stop honors the
waiver only after the review marker persists.'

FAIL: test_finish_line_external_tombstone_survives_read_only_state
    self.assert_blocked(decision, "failed with exit code 17")
AssertionError: 'failed with exit code 17' not found in 'Validation is being
waived in repo; discovered-defect routing review required ... The routing-review
marker could not persist, so the waiver remains blocked.'

test_shared_hooks: 15/16 parallel shard(s) FAILED
```

Interpretation: the committed `#599` gate returns the routing-review prompt (and
in hermetic temp envs cannot persist `routing_review_marker`) where the older
`test_finish_line_*` cases still assert the pre-`#599` block strings
(`failed with exit code 17`, `has not passed since`). Persisted after scrubbing
`AGENT_SESSION_ID` / `AGENT_SESSION_STATE_DIR` / `AGENT_SESSION_CAPABILITY_FILE`
/ `AGENT_RUNTIME_STATE_HOME` / `HOME`.
