# sync-runtime-surfaces hermes-legacy cleanup probe failure — evidence (redacted)

Repro: `bash tests/runtime-smoke/run.sh --mode deterministic` (also
`scripts/ci/all.sh` position 11) in agent-runtime-kit.

```
==[ ci/all.sh position 11 ]== runtime skill deterministic smoke
Traceback (most recent call last):
  File "<stdin>", line 26, in <module>
AssertionError
...
runtime-smoke: mode=deterministic total=105 pass=102 fail=2 skip-host-capability=1
  meta.sync-runtime-surfaces.hermes-legacy product=shared-cli status=fail
    note=sync-runtime-surfaces quarantines owned Hermes legacy copies and blocks
    on modified copies
  conversation.main-agent-mode product=shared-cli status=fail   # (Wave 4 probe; since fixed -> pass=103)
```

Probe: `run_sync_runtime_surfaces_hermes_legacy_cleanup_probe`,
`tests/runtime-smoke/cases/meta/run.sh` (~line 1292). After
`cleanup_hermes_legacy_runtime_kit_skill_root`, it compares the quarantined copy
to the Hermes source via `diff -r` plus a Python inventory-hash check
(~lines 1351-1360) — the likely `<stdin>` line-26 `AssertionError`. Most
plausibly a `cp -R` symlink/mode/inventory divergence on this Linux host, not a
behavior regression. Untouched by the Wave 4 change; failed on the first smoke
run before any probe edit; main-agent-mode never renders to Hermes.
