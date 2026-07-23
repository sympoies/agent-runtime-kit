# sync-runtime-surfaces hermes-legacy cleanup probe fails on inventory compare

## Status

- Status: open
- First observed: 2026-07-23
- Area: runtime
- Severity: medium

## Signal

`scripts/ci/all.sh` position 11 (runtime deterministic smoke) fails
`meta.sync-runtime-surfaces.hermes-legacy` (`total=105 pass=103 fail=1` once the
unrelated main-agent-mode probe is fixed), with a Python `AssertionError`
(`<stdin>` line 26) surfacing during position 11.

## Evidence

- Raw record: not captured; manual diagnosis of the sync-runtime-surfaces hermes-legacy probe failure, 2026-07-23
- Probe: `run_sync_runtime_surfaces_hermes_legacy_cleanup_probe` in
  `tests/runtime-smoke/cases/meta/run.sh` (~line 1292). It seeds a fake
  `hermes-home` from `build/hermes/.../guided-feature-build` and `.../bootstrap`
  plus `tests/fixtures/retired-hermes-skill-copies/browser/canary-check`, runs
  `cleanup_hermes_legacy_runtime_kit_skill_root`, then compares the quarantined
  copy against the source via `diff -r` and a Python inventory hash
  (lines ~1351-1360) — the likely `AssertionError` source.
- Most plausible cause is a `cp -R` symlink/mode/inventory divergence on this
  Linux host rather than a behavior regression; the last touch of the probe was
  `25b1c59 fix(runtime): canonicalize macOS cleanup paths`.
- Unrelated to the Wave 4 change under test: the failure was present in the
  first smoke run before any probe edit, the subsystem (`sync-runtime-surfaces`
  Hermes cleanup) was untouched, and `main-agent-mode` is Codex/Claude-only and
  never renders to Hermes. Manual diagnosis, no raw record captured.
- Repro: `bash tests/runtime-smoke/run.sh --mode deterministic`.
- Evidence: `evidence/hermes-legacy-evidence.md`

## Impact

Blocks `scripts/ci/all.sh` at position 11 in this workspace regardless of the
change under test, so any code edit must waive that position and validate
through targeted probes instead of a fully green deterministic smoke.

## Current Workaround

Treat the position-11 `hermes-legacy` red as a documented, pre-existing waiver;
confirm the change's own smoke probe(s) pass individually (e.g.
`conversation.main-agent-mode`) rather than relying on `pass=105/105`.

## Promotion Criteria

Promote after the durable fix or accepted-risk decision is implemented,
validated, and linked from this entry.

## Next Action

Make the Hermes legacy-cleanup inventory/hash comparison portable across cp -R symlink/mode differences on Linux hosts, or characterize the divergence as host-specific in the probe
