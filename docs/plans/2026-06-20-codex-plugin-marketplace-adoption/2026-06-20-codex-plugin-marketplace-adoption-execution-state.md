# Execution State: Codex plugin/marketplace adoption

## Execution State

- Source document: docs/plans/2026-06-20-codex-plugin-marketplace-adoption/2026-06-20-codex-plugin-marketplace-adoption-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/435>
- Current sprint: Sprint 3 (complete)
- Status: implementation-complete; pending PR delivery
- Branch: feat/codex-plugin-marketplace-adoption
- Last updated: 2026-06-20

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Confirm and record the Resolved Decision #10 reversal | done | Reversal recorded in manifests/product-capabilities.yaml (marketplace_concept + loaded_at_runtime true) and schema descriptions; rationale in discussion-source | decision gate; blocks the capability flip |
| 1.2 | Align the Codex plugin.json render to the current loader schema | deferred | Superseded by spike (issue #435): Codex auto-discovers plugin skills/ and IGNORES the manifest skills field (array/pointer/absent all discover identically); audit array kept, no plugin.json shape change | may be coupled nils-cli render |
| 1.3 | Add core/docs/schemas/codex-plugin.schema.json | deferred | Descoped: schema_ref is dormant (no tool dereferences it), kept parallel to claude-plugin.schema.json; not load-bearing | currently referenced-but-missing |
| 2.1 | Render a Codex marketplace.json | done | targets/codex/.agents/plugins/marketplace.json (codex-kit, 10 plugins, canonical .agents/plugins path) verified by codex plugin marketplace add | path choice: .agents/plugins vs legacy .claude-plugin |
| 2.2 | Add a Codex activation branch to sync-runtime-surfaces.sh | done | sync_codex_plugin_registry in scripts/sync-runtime-surfaces.sh, gated by CODEX_PLUGIN_ACTIVATION; dry-run (both gates) + real isolated-CODEX_HOME activation rehearsal verified (10 plugins, skills discovered) | mirror the Claude block |
| 2.3 | Wire the Codex marketplace into the link-map / install plan | done | codex-kit.marketplace plugin-manifest-copy entry in targets/codex/link-map.yaml | analogous to claude-kit.marketplace |
| 3.1 | Flip the Codex capability flags | done | marketplace_concept + plugin_manifest.loaded_at_runtime flipped true; PR #434 NOTEs removed; plugin_manifest_diff + plugins/product-capabilities schema descriptions updated | marketplace_concept + loaded_at_runtime; remove PR #434 NOTEs |
| 3.2 | Promote matrix + harness-shape from pending to shipped | done | surfaces.yaml codex rows 3-5 -> partial; harness-shape-codex/claude bodies+table+legend updated (headings preserved for anchor gate); SUPPORT_MATRIX golden + tracked root re-rendered | re-render matrix + golden |
| 3.3 | Add acceptance coverage for the Codex plugin/marketplace surface | done | runtime-smoke meta codex plugin-registry probes (gated-on activation + gated-off inert) added; existing codex dry-run probe strengthened; test-first red->green verified | sandbox + runtime-smoke + live prompt-input |

## Validation Log

- 2026-06-20: spike (codex-cli 0.141.0, isolated CODEX_HOME) — `codex plugin marketplace add` + `codex plugin add <plugin>@codex-kit` register and install all 10 plugins; `codex debug prompt-input` lists skills as `<plugin>:<skill>`. Confirmed Codex auto-discovers the bundled `skills/` and ignores the manifest `skills` field across array / `"./skills/"` pointer / absent shapes; and that flat-root vs plugin discovery do not dedup (drove the gating decision).
- 2026-06-20: `sync_codex_plugin_registry` — gated-off dry-run reports `codex plugins=gated` with no live `codex plugin marketplace add`; gated-on dry-run prints the materialize + register + 10× `codex plugin add` plan; real gated-on activation against an isolated CODEX_HOME succeeded (symlink-free materialized tree).
- 2026-06-20: runtime-smoke meta codex plugin-registry probes — test-first red (origin/main sync script) → green (this branch); both new probes pass.
- 2026-06-20: `scripts/ci/all.sh` positions 1-5 green on-pin (agent-runtime v1.12.0); position 6 golden diff is the expected uncommitted-golden delta (codex rows 3-5 → partial), green after commit; full run re-confirmed post-commit.

## Session Notes

- 2026-06-20: bundle authored from the PR #434 follow-up; spike confirmed codex-cli 0.141.0 has the full plugin/marketplace surface.
- 2026-06-20: Task 1.1 decision CONFIRMED by the maintainer — adopt the Codex plugin/marketplace surface, superseding Resolved Decision #10.
- 2026-06-20: scope deviation from the plan — the spike proved Codex auto-discovers `skills/<skill>/SKILL.md` and ignores the manifest `skills` field, so Tasks 1.2 (rewrite the array to a `"./skills/"` pointer) and 1.3 (author codex-plugin.schema.json) were DEFERRED as unnecessary and harmful (the array rewrite would break the in-repo governance + audit-drift `plugin-manifest-skills` gates for no functional gain). The audit array is kept as source-organisation metadata. This avoided all nils-cli engine coupling / pin-bump risk.
- 2026-06-20: maintainer chose "ship + gate activation" for the flat-root transition — the marketplace surface is shipped and CI-tested, but live `codex plugin marketplace add` is gated behind CODEX_PLUGIN_ACTIVATION so the flat `$CODEX_HOME/skills` root stays the default and skills are not listed twice. Cut-over (removing the flat root) is a follow-up after live confirmation.
- 2026-06-20: follow-up issue #437 cut over to default Codex plugin activation and retired the runtime-kit-managed flat `$CODEX_HOME/skills/<domain>/<skill>` root. `agent-runtime doctor --class skill-surface --product codex` now reports 23 shape checks instead of the previous 72 because it no longer checks the 65 flat skill root symlink entries; CI baseline `SHAPE_EXPECTED_MIN_CHECKS` is 23 for the plugin-era shape.
- 2026-07-12: agent capability convergence retired the Browser and Evidence plugin domains after their internal workflows moved behind policy, hooks, and retained parent outcomes. The active Codex marketplace moved from 11 to 9 plugins, so the clean skill-surface doctor now reports 21/21 checks; `SHAPE_EXPECTED_MIN_CHECKS` is 21 with live prompt-input verification retained separately.
