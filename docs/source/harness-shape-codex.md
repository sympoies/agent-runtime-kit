# Harness Shape — Codex

- Status: maintained current-state description; this file is the per-product
  narrative input to the root-level `SUPPORT_MATRIX.md`. For the
  unified Codex × Claude × Hermes long-format table, see
  [`SUPPORT_MATRIX.md`](../../SUPPORT_MATRIX.md).
- Companion docs: `docs/source/harness-shape-claude.md` and
  `docs/source/harness-shape-hermes.md`.
- Update (2026-06, issue #435): Codex shipped a real plugin loader + plugin
  marketplace (`codex plugin marketplace add`;
  <https://developers.openai.com/codex/plugins/build>), and runtime-kit has now
  **adopted** it. The kit ships a `codex-kit` marketplace
  (`targets/codex/.agents/plugins/marketplace.json`) registered through
  `scripts/sync-runtime-surfaces.sh`, so surfaces 3–5 below are `shipped`.
  A spike confirmed Codex discovers each plugin's bundled
  `skills/<skill>/SKILL.md` and ignores the manifest `skills` field, so that
  audit array is kept as-is. Issue #437 cut over Codex skill discovery to the
  plugin marketplace and retired the flat `$CODEX_HOME/skills` root
  (surface 15).

## Purpose

Inventory the surfaces the Codex harness actually consumes at runtime
and, for each, record what `agent-runtime-kit` ships today, the
mechanism it ships through, the source artifact, and the version floor
that gates it. This is the Codex-side raw material for the unified
`SUPPORT_MATRIX.md`; do not invent capabilities here that the source
tree cannot back.

Scope rules:

- Only list primitives Codex itself reads, plus Claude-shape rows that
  must be marked `not-applicable` to keep this file pivotable with
  `docs/source/harness-shape-claude.md`.
- Mark a primitive `shipped` only when there is a concrete source
  artifact (`targets/codex/...`, `core/...`, manifest entry, link-map
  entry). A primitive with no source artifact yet is
  `planned-not-shipped`.
- `.codex-plugin/plugin.json` is now a real plugin manifest Codex loads when a
  plugin is registered via the `codex-kit` marketplace; its `skills` array is
  retained as source-organisation audit metadata because Codex auto-discovers
  the bundled `skills/<skill>/SKILL.md` and ignores the field
  (`manifests/product-capabilities.yaml`; see the Update note above).
- Cite file paths (not line numbers — they rot); this doc must stay
  verifiable.

## Version Floors (Codex side)

- Codex product `min_version` / `recommended_version`: **0.150.1**;
  `min_version_effective_from`: **2026-09-01**; probe:
  `codex --version` (`manifests/runtime-roots.yaml`).
- `agent-runtime` orchestration binary (renders / installs the Codex surface)
  ships inside nils-cli; minimum supported **v1.27.35**; validated snapshot
  **v1.27.35**
  (`docs/source/nils-cli-surface.md`, `docs/source/nils-cli-pin.yaml`).
  Released subcommands consumed today: `render`, `install`, `uninstall`,
  `doctor` (including `--class skill-surface --product codex`),
  `audit-drift`, `gc-backups`, `restore-backups`, `purge-state`, and
  `pr-body render`.
- The `agent-run` capability binary (nils-cli `>=0.20.0`) is consumed by
  project-script dispatcher skills so repository-owned `.agents/scripts/*`
  commands run through explicit `.envrc` / `.env` handling.
- Per-skill nils-cli floors come from `manifests/skills.yaml`
  `required_clis` and gate skill bodies, not Codex's core load path.
  Project-script dispatcher skills that depend on explicit project
  environment execution pin `agent-run` at `>=0.20.0`. Dispatch / PR floors
  evolve with their consumed delivery contracts and are intentionally not
  duplicated here; `manifests/skills.yaml` is authoritative.
- Live Codex Desktop acceptance is separate from the deterministic
  version floor: `codex debug prompt-input` must show required skills
  in a fresh session
  (`docs/plans/2026-06-20-codex-plugin-marketplace-adoption/`).

## Surface-By-Surface Shape

Each section below answers the same questions so the table can pivot to
a uniform shape:

1. **Codex reads from** — runtime discovery path.
2. **Source** — checked-in artifact (`-` if none).
3. **Install mechanism** — link-map entry kind or render-time handling.
4. **Acceptance lane** — what gates the surface today.
5. **Support today** — current ship state.

### 1. Home-scope prompt (`AGENTS.md`)

- Codex reads from: `$CODEX_HOME/AGENTS.md` on session start.
- Source: root `AGENT_HOME.md`, rendered per product to
  `build/codex/AGENT_HOME.md` (`AGENT_HOME.md`, `DEVELOPMENT.md`).
- Install mechanism: `agent-runtime render --target home-prompt --product
  codex` writes the rendered file, and `scripts/setup.sh` plus
  `scripts/sync-runtime-surfaces.sh --apply --product codex` wire
  `$CODEX_HOME/AGENTS.md` to
  `<source_root>/build/codex/AGENT_HOME.md`. The source filename is deliberately
  distinct from repo-local `AGENTS.md` so Codex does not load duplicate
  home/project policy in this repo.
- Acceptance lane: covered by home-policy cutover and live Codex session
  observation; no dedicated CI gate diffs the link target.
- Support today: **shipped (rendered + linked)**.

### 2. Project-scope prompt (`./AGENTS.md`)

- Codex reads from: project-local `AGENTS.md` files while working in a
  repo; this is why home policy uses `AGENT_HOME.md` instead of a
  source-root `AGENTS.md`.
- Source: `./AGENTS.md` in this repo, which declares the repo-local
  policy and notes that `./CLAUDE.md` imports it through `@AGENTS.md`.
- Install mechanism: not installed by `agent-runtime`; it ships as part
  of the repo working tree.
- Acceptance lane: covered indirectly by any Codex session opened in
  this repo; no specific gate.
- Support today: **shipped (repo-local only)**.

### 3. Plugin manifest (`.codex-plugin/plugin.json`)

- Codex reads from: Codex's plugin loader reads `.codex-plugin/plugin.json`
  once a plugin is registered through the `codex-kit` marketplace
  (`manifests/product-capabilities.yaml`). A spike under issue #435 confirmed
  Codex discovers the plugin's bundled `skills/<skill>/SKILL.md` directly and
  IGNORES the manifest `skills` field (array, `"./skills/"` pointer, and absent
  all discover identically), so the kit keeps the `skills: [{id, source}]`
  array as source-organisation audit metadata rather than rewriting it.
- Source: `targets/codex/plugins/<plugin>/.codex-plugin/plugin.json`
  exists for all 9 direct-outcome plugin domains (`manifests/plugins.yaml`); the
  reporting artifact shows the audit schema shape
  (`targets/codex/plugins/reporting/.codex-plugin/plugin.json`).
- Install mechanism: `plugin-manifest-copy` into
  `$CODEX_HOME/plugins/<domain>/.codex-plugin/plugin.json`
  (`targets/codex/link-map.yaml`); the marketplace materialization copies the
  same manifest beside each plugin's rendered `skills/` tree.
- Acceptance lane: gate 1 governance (`plugin-manifest` skills audit) and gate
  5 audit-drift (`plugin-manifest-skills`) validate the audit array; the
  runtime-smoke codex plugin-registry probe covers registration planning.
- Support today: **shipped** — the manifest is installed and Codex-loadable
  through the default `codex-kit` marketplace activation path.

### 4. Plugin marketplace (`.agents/plugins/marketplace.json`)

- Codex reads from: `codex plugin marketplace add <root>` registers a
  marketplace whose manifest lives at the canonical
  `.agents/plugins/marketplace.json` (Codex also reads
  `.claude-plugin/marketplace.json` as a legacy source). runtime-kit ships the
  canonical path.
- Source: `targets/codex/.agents/plugins/marketplace.json` — the `codex-kit`
  marketplace listing all 9 direct-outcome plugins by `./plugins/<name>`, installed by the
  `codex-kit.marketplace` `plugin-manifest-copy` entry
  (`targets/codex/link-map.yaml`).
- Install mechanism: `sync-runtime-surfaces.sh --apply --product codex`
  (`sync_codex_plugin_registry`) materializes a
  symlink-free marketplace under the Codex state home, registers it as
  `codex-kit`, and installs every `<plugin>@codex-kit`. First-time
  `scripts/setup.sh` delegates the same Codex activation after bootstrap.
- Acceptance lane: gate 8 runtime-smoke codex plugin-registry probes assert
  default dry-run prints the activation plan without executing it, and a
  stubbed apply registers `codex-kit` and installs each `<plugin>@codex-kit`.
- Support today: **shipped** — the marketplace is the default Codex skill
  discovery path for runtime-kit-managed skills.

### 5. Plugin-scoped skills (`<plugin>/skills/<skill>/SKILL.md`)

- Codex reads from: once a plugin is installed from the `codex-kit`
  marketplace, Codex discovers each bundled `skills/<skill>/SKILL.md` and
  surfaces it as `<plugin>:<skill>`.
- Source: `build/codex/plugins/<domain>/skills/<skill>/` is the rendered tree;
  29 Codex plugin-scoped skill entries are declared in `manifests/skills.yaml`
  (count auto-maintained by
  `scripts/ci/skill-governance-audit.sh --update-counts`);
  the marketplace materialization copies it symlink-free beside each plugin's
  `.codex-plugin/plugin.json` (`scripts/sync-runtime-surfaces.sh`). The
  link-map also links it under `$CODEX_HOME/plugins/<domain>/skills`.
- Install mechanism: default marketplace install (see surface 4); the flat
  skill root install (surface 15) is retired.
- Acceptance lane: gate 3 render, gate 4 golden, gate 5 drift, and the gate 8
  runtime-smoke codex plugin-registry probe; sandbox install rehearsal diffs
  `tests/sandbox/codex/expected-skills.txt:1-29`.
- Support today: **shipped** — plugin-scoped discovery is the default
  runtime-kit-managed Codex skill path.

### 6. Slash command files (`commands/<name>.md` outside skills)

- Codex reads from: **nowhere** in the runtime-kit activation surface;
  the documented Codex load set is `$CODEX_HOME/AGENTS.md`, local
  skills, `config.toml`, and hook-referenced files.
- Source: **none**.
- Install mechanism: not installed.
- Acceptance lane: none.
- Support today: **not-applicable**. This is a Claude harness primitive,
  not a Codex one.

### 7. Subagent definitions (`agents/<name>.md`)

- Codex reads from: `$CODEX_HOME/agents/<name>.toml` (personal) and
  `.codex/agents/<name>.toml` (project) for file-backed subagents Codex can
  spawn, per the Codex subagents docs
  (<https://developers.openai.com/codex/subagents>).
- Source: one canonical `core/agents/<domain>/<name>/AGENT.md.tera`, rendered
  per product. The `product` Tera variable branches the Codex TOML body —
  `name`, `description`, `developer_instructions`, optional `model` and
  `model_reasoning_effort`, and (for a reviewer) `sandbox_mode = "read-only"`
  (`manifests/agents.yaml`).
- Install mechanism: rendered to `build/codex/agents/<name>.toml`, then one
  non-recursive `symlinked-file` directory symlink (`id: agents-tree`) at
  `$CODEX_HOME/agents` (`targets/codex/link-map.yaml`). The whole directory is
  linked, not one symlink per profile, because codex-cli resolves an advertised
  `agent_type` back to its directory entry at dispatch time: it enumerates
  `$CODEX_HOME/agents/*.toml` into the `spawn_agent` schema through a
  path-following stat, but refuses a profile whose directory entry is itself a
  symlink with `agent type is currently not available`
  (agent-runtime-kit#58, reproduced on codex-cli 0.150.0). Linking the parent
  directory keeps every leaf a regular file, so every advertised identity
  dispatches. Two consequences follow. Codex has no unmanaged
  `$CODEX_HOME/agents/` slot — the directory is runtime-kit owned, and a
  personal profile belongs in a project-level `.codex/agents/` instead. And
  `agent-runtime install` will not swap a real directory for a symlink, so
  `reset_codex_managed_agents_root` in `scripts/sync-runtime-surfaces.sh` runs
  before install and normalizes that surface. It leaves an `agents` symlink that
  already matches the active source root alone (so a converged host still
  installs zero changes), removes a provably runtime-kit-owned surface in either
  shape — the retired directory of per-profile symlinks, or a directory symlink
  into another owned checkout, which is what a rollback to a pre-#58 revision
  needs — and refuses when anything unmanaged is present. Claude reads a
  symlinked leaf fine and stays `recursive: true`.
- Acceptance lane: render / golden / audit-drift / sandbox install rehearsal
  gates (the rehearsal pins the installed reviewer agents per product against
  `tests/sandbox/codex/expected-agents.txt`, and pins the Codex install shape
  itself: a plan that reverts to per-profile symlinks fails the gate) plus
  manifest-driven governance of every Codex reviewer's explicit model,
  reasoning effort, and sandbox. The opt-in authenticated probe
  `tests/runtime-smoke/product/codex-reviewer-dispatch.sh` checks installed
  profiles, rejects a symlinked profile leaf, and dispatches every canonical
  identity when the active `spawn_agent` schema exposes `agent_type`. It
  separates three outcomes. A selector-less host records
  `skip-host-capability` and the required inline fallback instead of silently
  spawning a generic child. A host that advertises a canonical identity but
  refuses to dispatch it fails the probe: the inline fallback still preserves
  correctness, but a schema advertising an undispatchable reviewer is a broken
  surface, not a supported host shape. That verdict is read from the host's
  verbatim `agent type is currently not available` in the Codex event stream,
  so a misreporting model cannot downgrade it to a skip or a pass. Only a full
  eight-identity dispatch passes.
- Support today: **shipped (`reviewer-quick` + seven specialist lenses)**. The
  cross-product agents render surface ships in nils-cli v1.3.0; the managed
  read-only reviewers are `reviewer-quick` (quick pass) plus seven specialist
  lenses (testing, maintainability, security, performance, api-contract,
  data-migration, red-team). Codex renders all eight with `gpt-5.6-sol`:
  `reviewer-quick` uses `low` reasoning and all seven specialists use `medium`
  reasoning; all eight are read-only. Dispatch uses
  each manifest's canonical hyphenated identity as `agent_type`; `task_name`
  remains only a workflow label. Claude agent definitions remain unpinned.

### 8. Hook scripts (`hooks/<name>.*`)

- Codex reads from: one `agent-hook dispatch --product codex` command per
  owned event/matcher group in `$CODEX_HOME/config.toml`; the dispatcher
  invokes allowlisted files under `$CODEX_HOME/hooks/` from the selected
  policy.
- Source: portable logic under `core/hooks/shared/`; there is no
  `core/hooks/codex/` tree today. Registration behavior is canonical in
  `core/policies/agent-hook/runtime-kit-v1.toml` and
  `manifests/hook-rules.yaml`.
  The shared `user-prompt-agent-memory.sh` hook is registered separately for
  Codex and Claude at each `startup|resume|clear` SessionStart boundary. It
  invokes `agent-memory recall startup` and reads at most 768 bytes without
  falling back to the full global index or any producer-candidate root. It
  keeps no delivery stamp, so an aggregate block cannot suppress recall on the
  next eligible boundary. Failures emit no memory context and do not block the
  session. Deeper Codex-owned recall uses `agent-memory
  recall on-demand <term> --agent codex`; durable cross-agent proposals go
  through the Codex producer candidate root under the governed memory policy.
- Install mechanism: `scripts/sync-runtime-surfaces.sh` copies the shared
  source into an independently owned `$CODEX_HOME/hooks` directory. Handler
  files are materialized as owner-only regular files (`0700`; non-executable
  data files use `0600`) so source-checkout permission drift cannot make the
  live hook root untrusted.
- Acceptance lane: shared hook contract tests
  (`bash tests/hooks/run.sh`, CI position 10, `DEVELOPMENT.md`).
- `checkout-lease-guard.py` is registered for `UserPromptSubmit`, `PreToolUse`,
  and `Stop`, but performs lease work only for explicit coordination mode
  `enforce`. Default/advisory/off and unmanaged launches never acquire or block
  on a physical checkout lease. In enforce mode the prompt path is silent unless dirty-checkout adoption is opted
  in and released `git-cli >=1.24.1` can issue an exact five-minute snapshot
  challenge; file/index mutation remains fail-closed regardless of the adoption opt-in.
  Adopted lease-v2 provenance survives same-session refresh, receipt-bound
  revocation changes no content, and the only lease-free dirty exception is a
  sole recognized ref-only branch/tag operation.
- Support today: **shipped (shared scripts symlinked)**.

### 9. Hook registration (`settings.json` `hooks` block)

- Codex reads from: **nowhere**. Codex has no `settings.json`-equivalent
  hook registration; hook activation is TOML-only through
  `$CODEX_HOME/config.toml`.
- Source: **none** for `settings.json`; the Codex TOML managed block is
  recorded separately in surface 16.
- Install mechanism: not installed.
- Acceptance lane: none for `settings.json`; Codex hook acceptance uses
  the TOML managed block in surface 16.
- Support today: **not-applicable**.

### 10. Output styles (`output-styles/<name>.md`)

- Codex reads from: **nowhere** in the runtime-kit activation surface.
- Source: **none**.
- Install mechanism: not installed.
- Acceptance lane: none.
- Support today: **not-applicable**. This is a Claude-only primitive.

### 11. Status line (`statusLine` in `settings.json`)

- Codex reads from: **nowhere**. Codex hook/config activation is TOML
  managed-block based, not `settings.json` based
  (`manifests/runtime-roots.yaml`).
- Source: **none**.
- Install mechanism: not installed.
- Acceptance lane: none.
- Support today: **not-applicable**. This is a Claude-only primitive.

### 12. MCP servers (per-user MCP config)

- Codex reads from: Codex's own per-user config / connector setup, not
  an `agent-runtime-kit` surface. Runtime-kit only owns the hook managed
  block inside `$CODEX_HOME/config.toml`
  (`manifests/product-capabilities.yaml`).
- Source: **none** — runtime-kit does not template MCP servers.
- Install mechanism: not installed; per-user MCP connection strings are
  classified as sensitive.
- Acceptance lane: none.
- Support today: **not-shipped**. Out-of-scope by design (secret
  boundary).

### 13. Heuristic system (curated retained records)

- Codex reads from: not directly as a harness loader. The home prompt
  points at the heuristic system as policy / workflow guidance, and parent
  workflows use the `heuristic-inbox` CLI for retained records.
- Source: shared root under `core/policies/heuristic-system/`
  (HEURISTIC_SYSTEM.md + error-inbox + operation-records).
- Install mechanism: currently a docs / skill surface; consumed via the
  `heuristic-inbox` nils-cli binary with explicit `--inbox-dir`
  arguments rather than a fixed Codex load path.
- Acceptance lane: runtime-smoke deterministic mode exercises the
  policy-owned `heuristic-inbox` CLI path (`DEVELOPMENT.md`).
- Support today: **shipped (shared policy root)**.

### 14. Runtime state (`state_home`)

- Codex reads from: not directly — `state_home` is owned by parent workflows
  and hooks via the `agent-out` CLI and `CODEX_AGENT_STATE_HOME`.
- Source: contract in `manifests/runtime-roots.yaml` and
  `manifests/product-capabilities.yaml`.
- Install mechanism: `agent-runtime install` resolves runtime roots;
  the `agent-out` CLI allocates artifact paths at runtime.
- Acceptance lane: `runtime-smoke --mode convergence` verifies a clean receipt,
  backup restore rehearsal, retired-surface prune, stubbed plugin activation,
  active-ID read-back, installed-runtime provenance, and idempotent reapply in
  an isolated runtime home.
- Support today: **shipped (env var + runtime allocator)**.

### 15. Codex local skill root (`skills/<domain>/<skill>/SKILL.md`)

- Codex reads from: no runtime-kit-managed content. This flat root was the
  pre-plugin discovery path and is retired by issue #437.
- Source: none for runtime-kit-managed skills; source skills still render to
  `build/codex/plugins/<domain>/skills/<skill>/` for plugin-scoped discovery
  (surface 5).
- Install mechanism: no flat `$CODEX_HOME/skills/<domain>/<skill>/` entries are
  installed by `targets/codex/link-map.yaml`.
- Acceptance lane: covered by surface 5 plugin-scoped discovery and live
  `codex debug prompt-input` showing `<plugin>:<skill>` names.
- Support today: **not-applicable (retired)**.

### 16. Codex hook registration (`config.toml` managed block)

- Codex reads from: `$CODEX_HOME/config.toml` TOML hook definitions
  (`manifests/product-capabilities.yaml`, `manifests/runtime-roots.yaml`).
- Source: `core/policies/agent-hook/runtime-kit-v1.toml` with the audited
  inventory in `manifests/hook-rules.yaml`. The compatibility source
  `targets/codex/hooks/config.block.toml` intentionally contains no commands.
- Install mechanism: `sync-runtime-surfaces.sh` clears the retired managed
  registrations, installs the digest-pinned XDG policy/config, then applies the
  exact reviewed `agent-hook setup` plan. Setup owns one dispatcher per
  event/matcher group and composes Codex `notify` without losing a foreign or
  Computer Use notifier.
- Acceptance lane: agent-hook policy, executable, migration, runtime-smoke,
  and shared hook contract tests (`DEVELOPMENT.md`).
- Support today: **shipped (setup-owned dispatcher)**.

### 17. Work-tier delegation policy (`core/policies/work-tier-levels.md`)

- Codex reads from: delivery-phase `project-dev` resolution names the work-tier
  policy only when durable tracking or delivery is in play. Routine L0
  classification stays internal; the policy may select parallel or
  orchestrator execution without exposing those execution modes as skills.
- Source: `core/policies/work-tier-levels.md`, routed by
  `AGENT_DOCS.toml` and summarized by the rendered home policy.
- Install mechanism: shared policy tree plus `agent-docs` intent resolution;
  there is no separate skill or Codex file loader for an execution mode.
- Acceptance lane: agent-docs preflight and policy-render validation.
- Support today: **shipped (policy-routed)**.

## Coverage Summary

| # | Surface | runtime-kit ships | Mechanism | Min Codex | Min nils-cli |
|---|---|---|---|---|---|
| 1 | `AGENTS.md` (home) | yes | rendered home prompt symlink to `build/codex/AGENT_HOME.md` | 0.130.0 | v1.12.1 |
| 2 | `./AGENTS.md` (repo-local) | yes | repo working tree | 0.130.0 | n/a |
| 3 | `.codex-plugin/plugin.json` | yes | plugin-manifest-copy; Codex loads it via the `codex-kit` marketplace (skills auto-discovered, manifest `skills` field ignored) | 0.141.0 | v0.17.5 |
| 4 | `.agents/plugins/marketplace.json` | yes | `codex-kit` marketplace activated by `sync-runtime-surfaces.sh` / `setup.sh` | 0.141.0 | v0.17.5 |
| 5 | `plugins/<p>/skills/<s>/` discovery | yes | bundled `skills/<skill>/SKILL.md` discovered as `<plugin>:<skill>` once installed | 0.141.0 | v1.21.15 |
| 6 | `commands/<n>.md` | not-applicable | — | n/a | n/a |
| 7 | `agents/<n>.toml` | yes | rendered + directory symlink into `$CODEX_HOME/agents` | 0.139.0 | v1.3.0 |
| 8 | `hooks/<n>.*` scripts | yes | shared scripts materialized as owner-only regular files under `$CODEX_HOME/hooks` | 0.130.0 | v1.24.5 |
| 9 | `settings.json` hooks block | not-applicable | — | n/a | n/a |
| 10 | `output-styles/<n>.md` | not-applicable | — | n/a | n/a |
| 11 | `statusLine` / `settings.json` | not-applicable | — | n/a | n/a |
| 12 | MCP servers | no | — | n/a | n/a |
| 13 | Heuristic system | yes | shared policy root | 0.130.0 | v1.8.0 (heuristic-inbox) |
| 14 | `state_home` | yes | env var + `agent-out` CLI allocation | 0.130.0 | v1.19.2 (`path-for`; reviewed cleanup is policy-owned) |
| 15 | `$CODEX_HOME/skills/<d>/<s>/` | not-applicable | retired; plugin-scoped discovery is row 5 | n/a | n/a |
| 16 | `config.toml` hook ingress | yes | digest-bound `agent-hook setup` | 0.130.0 | v1.26.4 |
| 17 | work-tier delegation policy | yes | agent-docs policy routing | 0.130.0 | v1.12.1 |

Status legend:

- **yes** — concrete source artifact + link-map entry or repo-local
  prompt artifact + acceptance lane.
- **partial** — surface shipped with a concrete source artifact, but not the
  default/active path yet.
- **planned-not-shipped** — contract defined in manifests but no source
  artifact yet.
- **no** — Codex-capable or adjacent primitive that runtime-kit does not
  target; not on the current roadmap unless added explicitly.
- **not-applicable** — Claude harness primitive or local metadata row
  with no Codex runtime loader.

## Acceptance Lanes (Codex-Relevant CI Gates)

From `DEVELOPMENT.md`:

1. `plan-tooling validate` — covers manifest schemas.
2. **`agent-runtime render --product codex`** — render gate.
3. `agent-runtime render --product claude` — not Codex-side, but run in
   the shared gate stack.
4. **render-golden refresh + `git diff --exit-code`** — render
   determinism gate.
5. **`agent-runtime audit-drift` + fixtures** — drift audit gate
   (includes local-only Codex `plugin.json` schema validation and
   managed-block checks).
6. **`agent-runtime doctor --class skill-surface --product codex`** —
   Codex-only skill-surface shape preflight. It validates the
   source/link-map shape that feeds plugin-scoped Codex discovery; it is
   not live Codex Desktop acceptance.
7. **sandbox install rehearsal** — installs into temp `live_home`,
   compares installed skill surfaces with
   `tests/sandbox/codex/expected-skills.txt`, and accepts doctor only
   when `block=0` (`DEVELOPMENT.md`).
8. **runtime-smoke deterministic mode** — exercises representative
   installed skills across current domains (`DEVELOPMENT.md`).
9. **runtime-smoke convergence mode** — proves a portable historical
   66-to-current-skill upgrade, rollback, prune, exact registry refs, receipt/ID
   transition, operator-state preservation, idempotency, and redacted route
   contract fixtures without real product credentials.
10. **project-local overlay smoke** — Codex-side project-local shims for
   `bootstrap`, `deploy`, `pre-pr`, and `release`, plus `setup-project`
   adoption diagnostics (`DEVELOPMENT.md`).
11. **`bash tests/hooks/run.sh`** — shared hook contract tests.

Quarantined (not in default CI):

- `bash tests/runtime-smoke/run.sh --mode product --product codex`;
  `--probe-only` validates isolated CLI invocation without full prompt
  execution.

`codex-cli agent prompt`, `advice`, `knowledge`, and `commit` are a separate
one-shot child surface. They default to a temporary `CODEX_HOME`, ignore user
config and project rules, disable lifecycle hooks and optional runtime
features, and always run ephemerally. This isolates the child only: an outer
managed Codex invocation remains governed by the hooks above. Explicit
`--runtime inherited` restores the legacy full-home behavior, while
`agent resume` is always inherited. `codex-cli agent doctor --format json`
provides the no-API capability probe used by product smoke.

Live Codex acceptance:

- Public convergence acceptance validates four isolated prompt/route contract
  fixtures for implementation, review, rendered-browser evidence, and bounded
  desktop operation. It intentionally does not claim classification or model
  execution.

- `codex debug prompt-input` in a fresh Codex Desktop session is the
  live acceptance lane. Pass signal: each required skill appears as a
  `- <name>: ...` entry in the `<skills_instructions>` block with a
  file path under
  `agent-runtime-kit/build/codex/plugins/<domain>/skills/<skill>/SKILL.md`
  (`docs/plans/2026-06-20-codex-plugin-marketplace-adoption/`).

## Open Items For Schema Design

Things that may need a dedicated column as the unified
`SUPPORT_MATRIX.md` schema evolves:

- A `runtime_loaded` field separate from `metadata_shipped`, so Codex
  `.codex-plugin/plugin.json` can be represented as copied/audited but
  not loaded.
- A `runtime_skill_root` field that distinguishes retired flat roots from
  active plugin-scoped skill discovery.
- A `config_surface` enum that can express `config.toml` managed blocks
  and Claude `settings.json` blocks without pretending they are the same
  upstream primitive.
- A `ci_acceptance` field separate from `live_acceptance`, because Codex
  has both the deterministic skill-surface doctor and the live
  `codex debug prompt-input` protocol.
- A `hook_logic_origin` field that can say `shared` vs
  `product-specific`; Codex currently ships shared scripts plus a Codex
  TOML block and has no `core/hooks/codex/` adapter tree.
