# sync-runtime-surfaces hermes-legacy cleanup probe fails on inventory compare

## Status

- Status: promoted
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

## Resolution

Resolved 2026-07-23 in agent-runtime-kit. The quarantine step itself is
mode-preserving (`os.rename` plus explicit `fchmod`); the divergence came from
the probe's setup. The inventory assertion compares exact `S_IMODE` bits against
the canonical source, but the fake legacy copy was staged with plain `cp -R`,
which remodes files through the ambient umask (a 664 source file becomes 600
under umask 077), diverging host to host while `diff -r` stayed silent because
it ignores mode bits.

Fix: stage the `guided-feature-build` legacy copy with `cp -Rp` in
`tests/runtime-smoke/cases/meta/run.sh` so the staged tree faithfully mirrors
source modes and the "quarantine preserved the tree exactly" assertion holds
across umasks.

Validation: `bash tests/runtime-smoke/run.sh --mode deterministic` ->
`total=105 pass=104 fail=0 skip-host-capability=1`, with
`meta.sync-runtime-surfaces.hermes-legacy status=pass`.

## Promotion Criteria

Promote after the durable fix or accepted-risk decision is implemented,
validated, and linked from this entry.

## Next Action

None. Resolved in agent-runtime-kit: the hermes-legacy probe in
`tests/runtime-smoke/cases/meta/run.sh` now stages the `guided-feature-build`
copy with `cp -Rp` so the exact-mode inventory assertion is umask-portable;
`runtime-smoke --mode deterministic` is green (105, 0 fail). See Resolution.

## Archive

- Archived: 2026-07-23
- Reason: fixed in agent-runtime-kit; see ENTRY Resolution
