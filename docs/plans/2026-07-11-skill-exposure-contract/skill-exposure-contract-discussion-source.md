# Skill Exposure Contract Implementation Handoff

## Status

- Date: 2026-07-11
- Source: graysurf/agent-runtime-kit issue #561 and its 2026-07-11 refinement
- Intended next step: execute the linked L2 plan, deliver the required nils-cli and runtime-kit PRs, then close the plan tracker
- Retention: coordination artifact; archive through the plan-tracking closeout path after delivery

## Purpose

Define a machine-enforced boundary between user-facing skills and agent-only
runtime capabilities. The implementation must give Codex, Claude, and Hermes an
honest retained-skill catalog without pretending that a filesystem-discovered
`SKILL.md` can be installed but hidden.

## Confirmed Facts

- `manifests/skills.yaml` currently declares 66 skills and maps every declared
  product to a rendered `SKILL.md` path.
- Codex, Claude, and Hermes all discover runtime-kit skills from installed
  filesystem skill trees. Product plugin metadata is not a portable visibility
  filter.
- `core/docs/schemas/skills.schema.json` and the released nils-cli manifest
  parser currently support schema version 1 only and have no semantic role,
  parent intent, admission rationale, exposure, replacement, or retirement
  fields.
- The nils-cli parser uses `deny_unknown_fields`, so runtime-kit cannot safely
  add the new manifest contract without a released parser update.
- The renderer already removes outputs and cache entries for a skill removed
  from `manifests/skills.yaml`; the install/prune path can therefore retire
  skills without retaining stale managed files.
- Issue #562 owns the reviewed disposition and behavioral migration of all 66
  current skills. Issue #561 owns the vocabulary, schema, product truth,
  governance, compatibility model, and migration substrate.

## Decisions

1. `manifests/skills.yaml` schema v2 will describe active renderable skills.
   Semantic invocation role and product exposure are separate fields.
2. Retained roles are `workflow`, `maintenance`, `advanced`, and
   `compatibility`; each retained entry must name parent intents, an example
   direct user request, and an admission rationale.
3. The only enabled cross-product exposure profile in this implementation is
   `default`. A metadata-only `opt-in` mode is explicitly rejected because no
   equivalent product install/profile path exists today.
4. An `advanced` entry cannot be active while only `default` exposure exists.
   #562 must either merge/rehome such a capability or open a separate product
   exposure design before retaining it as advanced.
5. `compatibility` is permitted only with a canonical replacement and a
   time-bounded retirement condition. It cannot contain independent workflow
   logic.
6. The 66 current entries are carried through v2 as an explicit, immutable
   pending-disposition allowlist owned by #562. This is visible migration debt,
   not an internal/hidden skill class. Governance rejects additions to that
   allowlist.
7. A separate checked-in disposition manifest seeds all current IDs as
   `pending`; #562 replaces each pending row with a reviewed destination and
   migration evidence. Retired IDs remain auditable there after removal from
   the active skill manifest.
8. nils-cli owns typed parsing, schema-version compatibility, deterministic
   validation, and metadata reporting. Runtime-kit owns JSON Schemas, the live
   catalog, admission governance, migration data, product documentation, and
   fixtures.
9. Skills removed by #562 will be deleted from active source/manifest/plugin
   containment/render/golden/install expectations only after their replacement
   layer is live. #561 supplies the contract but does not make those disposition
   decisions.

## Scope

- Add nils-cli support for the skills manifest v2 contract while preserving v1
  source-root compatibility.
- Release the nils-cli change and pin runtime-kit to the released surface.
- Move runtime-kit `manifests/skills.yaml` to schema v2 with the explicit
  #562-owned pending-disposition set.
- Add semantic invocation and exposure schemas, compatibility constraints, and
  deterministic validation.
- Add the machine-auditable skill disposition manifest/schema seeded with all
  current skill IDs as pending.
- Add governance fixtures proving valid retained entrypoints and rejecting thin
  CLI wrappers, bookkeeping entries, unsupported advanced/opt-in exposure,
  unbounded compatibility shims, and pending-disposition set growth.
- Surface semantic/exposure status in deterministic skill-list diagnostics.
- Document the no-hidden-skill and no-opt-in-without-product-support decisions.
- Verify schema, render, golden, drift, install, runtime-smoke, hook, stale
  cleanup, and three-product parity behavior.

## Non-scope

- Making the 66 final disposition decisions.
- Moving Browser/Evidence or other agent-only behavior into policy, intent
  documents, hooks, gates, or CLI; #562 owns those migrations.
- Adding a user-selectable optional skill installation profile.
- Keeping agent-only `SKILL.md` files installed under a new label.
- Reimplementing deterministic nils-cli behavior in runtime-kit scripts.
- Machine-specific, account-specific, or operator-private configuration.

## Implementation Boundaries

### nils-cli

- Support per-manifest schema-version validation so `skills.yaml` v1 and v2 can
  coexist with other manifest families that remain at v1.
- Parse and validate v2 invocation, exposure, migration, and compatibility
  fields.
- Keep v1 behavior backward compatible.
- Report retained-role/exposure/pending-disposition status through deterministic diagnostics.
- Do not decide which of the 66 entries should remain skills.

### agent-runtime-kit

- Own v2 JSON Schemas and live YAML data.
- Own admission and migration governance, including the frozen pending set.
- Keep active plugin containment and rendered/install surfaces aligned with the
  active skill manifest.
- Give #562 a machine-auditable pending inventory and destination vocabulary.

## Requirements

1. Every non-pending v2 skill has one semantic role, one or more parent intents,
   an example user request, an admission rationale, and `exposure.profile:
   default`.
2. A one-command CLI wrapper, bookkeeping capability, execution mode, or child
   lifecycle phase fails admission unless a reviewed direct-user-outcome
   exception is encoded.
3. `advanced` plus `default`, any unsupported `opt-in`, and permanent hidden
   `internal` roles fail closed.
4. Compatibility entries require replacement and retirement metadata.
5. Pending entries are exactly the baseline current IDs, are visibly tied to
   #562, and cannot grow.
6. The disposition manifest contains exactly one row for each active or retired
   migration ID and uses the shared destination vocabulary.
7. v1 fixtures keep rendering unchanged; v2 fixtures prove typed metadata and
   validation behavior.
8. Removing a v2 active skill continues to reconcile build cache/output and
   permits ownership-safe live stale pruning.
9. The final runtime-kit validation runs against the released and pinned
   nils-cli version, not a local debug binary.

## Acceptance Criteria

- A released nils-cli version accepts both skills manifest v1 and the defined v2
  contract and rejects malformed v2 combinations with stable errors.
- Runtime-kit uses schema v2 and records the frozen #562 pending-disposition set.
- New retained skills cannot bypass invocation/exposure/admission fields.
- No permanent `internal` role or unsupported opt-in profile is representable as
  a valid active skill.
- A seeded, machine-auditable disposition manifest covers all 66 current IDs
  without pre-deciding #562 outcomes.
- `agent-runtime list-skills` or an equivalent deterministic report exposes role,
  exposure, and pending-disposition status consistently for Codex, Claude, and Hermes.
- Governance negative fixtures cover thin wrappers, bookkeeping, child phases,
  advanced/default mismatch, opt-in claims, compatibility lifecycle, and pending
  allowlist growth.
- Render, plugin containment, generated output, install expectations, and stale
  cleanup remain aligned.
- nils-cli and runtime-kit required validation, specialist review, PR delivery,
  release/pin update, and plan-tracking closeout all complete.

## Validation Plan

- nils-cli focused unit/integration tests for manifest v1/v2 loading,
  combination validation, list-skills metadata, and retired-output behavior.
- nils-cli full workspace validation required by its repository.
- runtime-kit targeted schema/governance fixtures before implementation and
  after migration.
- Runtime-kit declared validation: `bash scripts/ci/all.sh` and `bash
  tests/hooks/run.sh`.
- Three-product deterministic `list-skills`, render, install rehearsal, and
  stale-prune fixtures.
- Mandatory pre-merge specialist review with at least testing and
  maintainability lenses for each delivered PR.

## Risks and Guardrails

- A global manifest schema constant in nils-cli currently couples unrelated
  manifest families. Refactor version selection narrowly; do not bump every
  manifest to v2.
- Do not classify all 66 entries merely to make schema migration easy. The
  frozen pending-disposition set makes the debt explicit until #562 reviews it.
- Do not call `advanced` an opt-in surface unless render/install/discovery can
  actually enforce that behavior across all declared products.
- Do not allow a compatibility shim to become a permanent second
  implementation.
- Generated files and goldens must be refreshed through the renderer, not
  hand-edited.
- Provider-visible records must not contain local machine paths or private
  environment information.

## Read First

- graysurf/agent-runtime-kit issue #561
- graysurf/agent-runtime-kit issue #562
- `core/docs/schemas/skills.schema.json`
- `manifests/skills.yaml`
- `manifests/plugins.yaml`
- `scripts/ci/skill-governance-audit.sh`
- `SUPPORT_MATRIX.md`
- nils-cli `crates/agent-runtime/src/render/manifest.rs`
- nils-cli `crates/agent-runtime/src/render/writer.rs`
- nils-cli `crates/agent-runtime/src/commands/list_skills.rs`

## Execution

- Recommended plan: docs/plans/2026-07-11-skill-exposure-contract/skill-exposure-contract-plan.md
- Recommended execution state: docs/plans/2026-07-11-skill-exposure-contract/skill-exposure-contract-execution-state.md
