# Harness Shape — Claude

- Date: 2026-05-31
- Status: empirical observation; this file is the per-product
  narrative input to the root-level `SUPPORT_MATRIX.md`. For the
  unified Codex × Claude long-format table, see [`SUPPORT_MATRIX.md`](../../SUPPORT_MATRIX.md).
- Companion doc (Codex side):
  `docs/source/harness-shape-codex.md`.

## Purpose

Inventory the surfaces the Claude Code harness actually consumes at
runtime and, for each, record what `agent-runtime-kit` ships today, the
mechanism it ships through, the source artifact, and the version floor
that gates it. This is the Claude-side raw material for the unified
`SUPPORT_MATRIX.md`; do not invent capabilities here that the source
tree cannot back.

Scope rules:

- Only list primitives Claude itself reads. Out-of-process companions
  (host shell, brew, gh, etc.) belong in `cli-tools.yaml`.
- Mark a primitive `shipped` only when there is a concrete source
  artifact (`targets/claude/...`, `core/...`, manifest entry, link-map
  entry). A primitive with no source artifact yet is
  `planned-not-shipped`.
- Cite file paths (not line numbers — they rot); this doc must stay
  verifiable.

## Version Floors (Claude side)

- Claude product `min_version` / `recommended_version`: **2.1.198**;
  `min_version_effective_from`: **2026-07-09**; probe: `claude --version`
  (`manifests/runtime-roots.yaml`).
- `agent-runtime` orchestration binary (renders / installs the Claude
  surface) ships inside nils-cli; pinned snapshot **v1.20.19**
  (`docs/source/nils-cli-surface.md`, `docs/source/nils-cli-pin.yaml`).
  Released subcommands consumed today: `render`, `install`, `uninstall`,
  `doctor`, `audit-drift`, `gc-backups`, `restore-backups`,
  `purge-state`, and `pr-body render`.
- The `agent-run` capability binary (nils-cli `>=0.20.0`) is consumed by
  project-script dispatcher skills so repository-owned `.agents/scripts/*`
  commands run through explicit `.envrc` / `.env` handling.
- Per-skill nils-cli floors come from `manifests/skills.yaml`
  `required_clis` (e.g. `agent-out: ">=1.19.3"`,
  `agent-docs: ">=0.16.0"`, `agent-run: ">=0.20.0"`). These gate skill
  bodies, not the harness load path.

## Surface-By-Surface Shape

Each section below answers the same questions so the table can pivot to
a uniform shape:

1. **Claude reads from** — runtime discovery path.
2. **Source** — checked-in artifact (`-` if none).
3. **Install mechanism** — link-map entry kind or render-time handling.
4. **Acceptance lane** — what gates the surface today.
5. **Support today** — current ship state.

### 1. Home-scope prompt (`CLAUDE.md`)

- Claude reads from: `$HOME/.claude/CLAUDE.md` on every session start.
- Source: root `AGENT_HOME.md`, rendered per product to
  `build/claude/AGENT_HOME.md`; see `DEVELOPMENT.md`.
- Install mechanism: `agent-runtime render --target home-prompt --product
  claude` writes the rendered file, and `scripts/setup.sh` plus
  `scripts/sync-runtime-surfaces.sh --apply --product claude` wire
  `$HOME/.claude/CLAUDE.md` to
  `<source_root>/build/claude/AGENT_HOME.md`. Filename is deliberately distinct
  from project-local `CLAUDE.md` so Claude does not load duplicate policy in
  this repo.
- Acceptance lane: covered by the cross-product home-policy cutover
  plans; no dedicated CI gate diffs the link target.
- Support today: **shipped (rendered + linked)**.

### 2. Project-scope prompt (`./CLAUDE.md`)

- Claude reads from: `<repo>/CLAUDE.md` for repo-local policy.
- Source: `./CLAUDE.md` in this repo is a symlink to `./AGENTS.md` (the
  project-local Codex/Claude shared file).
- Install mechanism: not installed by `agent-runtime`; it ships as part
  of the repo working tree.
- Acceptance lane: covered indirectly by any test that opens this repo
  with Claude; no specific gate.
- Support today: **shipped (linked, repo-local only)**.

### 3. Plugin manifest (`.claude-plugin/plugin.json`)

- Claude reads from: `${CLAUDE_PLUGIN_ROOT}/<plugin>/.claude-plugin/plugin.json`
  at runtime (`manifests/product-capabilities.yaml`,
  `loaded_at_runtime: true`).
- Source: `targets/claude/plugins/<plugin>/.claude-plugin/plugin.json`
  — 10 plugins enumerated (`manifests/plugins.yaml`).
- Install mechanism: `plugin-manifest-copy` per plugin (e.g.
  `targets/claude/link-map.yaml` for reporting; same pattern for meta,
  media, browser, conversation, evidence, issue, code-review, pr,
  dispatch).
- Schema: local `core/docs/schemas/claude-plugin.schema.json`
  (`manifests/product-capabilities.yaml`).
- Acceptance lane: drift audit + plugin schema validation (CI gate
  position 5, `DEVELOPMENT.md`); sandbox install rehearsal verifies the
  loader still accepts the manifest (CI gate position 7,
  `DEVELOPMENT.md`).
- Support today: **shipped (rendered + copy-installed)**.

### 4. Plugin marketplace (`.claude-plugin/marketplace.json`)

- Claude reads marketplace-managed plugins after the marketplace is registered
  in user settings and each plugin is installed/enabled. The managed
  marketplace source is `$HOME/.claude/.claude-plugin/marketplace.json`
  (`manifests/product-capabilities.yaml`), but the file alone is not enough for
  live skill visibility.
- Source: `targets/claude/.claude-plugin/marketplace.json` (lists all 10
  plugins; `claude-kit` namespace).
- Install / activation mechanism: `agent-runtime install` copy-installs the
  root marketplace file (`targets/claude/link-map.yaml`,
  `id: claude-kit.marketplace`); then
  `scripts/sync-runtime-surfaces.sh --apply --product claude` materializes a
  symlink-free marketplace copy under the Claude state home, registers that
  copy with `claude plugin marketplace add`, and reinstalls each
  `<plugin>@claude-kit` entry so Claude's plugin cache refreshes even while the
  manifests carry explicit `0.1.0` versions. First-time `scripts/setup.sh`
  delegates the same activation after its bootstrap phase.
- Acceptance lane: drift audit checks the file; sandbox install rehearsal
  validates the file surface; runtime-smoke covers the `claude` CLI registry
  activation that makes plugin skills visible.
- Support today: **shipped (rendered, copy-installed, materialized into state
  home, registered, and installed through Claude's plugin registry when
  `claude` is on PATH)**.
  runtime-kit ships a parallel Codex marketplace (`codex-kit`) as of issue
  #435, and issue #437 cut it over to default activation (see
  `docs/source/harness-shape-codex.md` surface 4).

### 5. Plugin-scoped skills (`<plugin>/skills/<skill>/SKILL.md`)

- Claude reads from: `${CLAUDE_PLUGIN_ROOT}/<plugin>/skills/<skill>/`
  for plugin-scoped skill discovery
  (`manifests/product-capabilities.yaml`).
- Source: `core/skills/<domain>/<skill>/` (10 plugin domains, reporting +
  meta + media + browser + conversation + evidence + issue + code-review
  + pr + dispatch); rendered into
  `build/claude/plugins/<plugin>/skills/<skill>/`.
- Install mechanism: `symlinked-file` with `recursive: true` per plugin
  (`targets/claude/link-map.yaml` for reporting; same for the other
  nine plugins). One symlink per rendered skill file in the install plan
  output.
- Acceptance lane: render output (CI position 3); render-golden
  (position 4); drift audit (position 5); sandbox install rehearsal
  diffs `~/.claude` skill-list output (position 7); runtime-smoke
  deterministic mode exercises representative skills (position 8,
  `DEVELOPMENT.md`).
- Support today: **shipped (rendered + recursive symlink)**.

### 6. Slash command files (`commands/<name>.md` outside skills)

- Claude reads from: `$HOME/.claude/commands/<name>.md` and
  `${CLAUDE_PLUGIN_ROOT}/<plugin>/commands/<name>.md` for slash commands
  declared independently of skills.
- Source: `targets/claude/commands/` (e.g.
  `targets/claude/commands/memory-clean.md`). The runtime-kit model
  treats skill bodies as the primary slash command surface; standalone
  command `.md` files are a small, explicit set.
- Install mechanism: `symlinked-file` of `targets/claude/commands` into
  `~/.claude/commands` (`targets/claude/link-map.yaml`).
- Acceptance lane: sandbox install rehearsal (CI position 7).
- Support today: **shipped (linked directory)**.

### 7. Subagent definitions (`agents/<name>.md`)

- Claude reads from: `$HOME/.claude/agents/<name>.md` (user) and
  `${CLAUDE_PLUGIN_ROOT}/<plugin>/agents/<name>.md` for subagents invokable
  via the Agent tool (<https://code.claude.com/docs/en/sub-agents>).
- Source: one canonical `core/agents/<domain>/<name>/AGENT.md.tera`, rendered
  per product. The `product` Tera variable branches the Claude body — YAML
  frontmatter (`name`, `description`, read-only `tools: Read, Grep, Glob,
  Bash`) plus the Markdown system prompt (`manifests/agents.yaml`).
- Install mechanism: rendered to `build/claude/agents/<name>.md`, then
  `symlinked-file` `recursive: true` (`id: agents-tree`) into
  `~/.claude/agents/` (`targets/claude/link-map.yaml`).
- Acceptance lane: render / golden / audit-drift / sandbox install rehearsal
  gates (the rehearsal pins the installed reviewer agents per product against
  `tests/sandbox/claude/expected-agents.txt`); the live Claude discovery probe
  is manual-only, documented in `tests/runtime-smoke/README.md`.
- Support today: **shipped (`reviewer-quick` + seven specialist lenses)**. The
  managed read-only subagents are `reviewer-quick` (quick pass) plus seven
  specialist lenses (testing, maintainability, security, performance,
  api-contract, data-migration, red-team), each at user-level
  `~/.claude/agents/reviewer-<lens>.md`.

### 8. Hook scripts (`hooks/<name>.*`)

- Claude reads from: `$HOME/.claude/hooks/<name>.*` referenced by
  `settings.json` `hooks` block (`manifests/product-capabilities.yaml`).
- Source: portable logic under `core/hooks/shared/`; Claude adapter slot
  reserved under `core/hooks/claude/` (`core/hooks/` tree present in
  repo).
- Install mechanism: `symlinked-file` (`targets/claude/link-map.yaml`,
  `id: hooks.shared-scripts`, source `core/hooks/shared` →
  `$HOME/.claude/hooks`). Per-product adapters are expected under
  `targets/claude/hooks/`; no files shipped under that path yet.
- Acceptance lane: hooks adapter contract tests
  (`bash tests/hooks/run.sh`, CI position 10, `DEVELOPMENT.md`).
- Support today: **shipped (shared scripts symlinked)**; the
  Claude-specific adapter slot is **planned-not-shipped** (manifest +
  link-map describe it; no `targets/claude/hooks/` files exist today).

### 9. Hook registration (`settings.json` `hooks` block)

- Claude reads from: `$HOME/.claude/settings.json` `hooks` block plus
  `statusLine`, etc. (`manifests/product-capabilities.yaml`,
  `hook_config_strategy: settings-json` in
  `manifests/runtime-roots.yaml`).
- Source: `core/hooks/claude/settings.hooks.jsonc` is the runtime-kit
  hook registration fragment. It intentionally is not a full
  `settings.json` replacement.
- Install mechanism: `scripts/sync-runtime-surfaces.sh --apply --product
  claude` merges the fragment into `$HOME/.claude/settings.json` after
  `agent-runtime install`, replacing only runtime-kit managed hook
  commands and preserving custom user hooks / unrelated settings.
- Acceptance lane: runtime-smoke `meta.sync-runtime-surfaces` fixture
  validates custom hook preservation, retired managed hook removal,
  source hook insertion, and idempotency.
- Support today: **shipped** for the `hooks` block managed by
  runtime-kit; other `settings.json` surfaces such as `statusLine`
  remain not shipped.

### 10. Output styles (`output-styles/<name>.md`)

- Claude reads from: `$HOME/.claude/output-styles/<name>.md`.
- Source: **none**.
- Install mechanism: not installed.
- Acceptance lane: none.
- Support today: **not shipped**. Claude-only primitive.

### 11. Status line (`statusLine` in `settings.json`)

- Claude reads from: `$HOME/.claude/settings.json` `statusLine` block.
- Source: **none** (same gap as the `settings.json` template itself).
- Install mechanism: not installed.
- Acceptance lane: none.
- Support today: **not shipped**.

### 12. MCP servers (per-user MCP config)

- Claude reads from: per-user MCP config managed via Claude CLI; not
  part of `settings.json` first-class blocks.
- Source: **none** — runtime-kit does not template MCP servers.
- Install mechanism: not installed; per-user MCP credentials are
  classified as sensitive.
- Acceptance lane: none.
- Support today: **not shipped**. Out-of-scope by design (secret
  boundary).

### 13. Heuristic system (curated retained records)

- Claude reads from: `$HOME/.claude/HEURISTIC_SYSTEM.md` plus
  `heuristic-system/operation-records/`,
  `heuristic-system/error-inbox/`.
- Source: shared root under `core/policies/heuristic-system/`
  (HEURISTIC_SYSTEM.md + error-inbox + operation-records).
- Install mechanism: currently a docs surface; consumed via the
  `heuristic-inbox` nils-cli binary with explicit `--inbox-dir`
  arguments rather than a fixed install path.
- Acceptance lane: runtime-smoke deterministic mode exercises the
  `heuristic-inbox` skill (position 8 / meta domain).
- Support today: **shipped (shared policy root)**.

### 14. Runtime state (`state_home`)

- Claude reads from: not directly — `state_home` is owned by
  skills/hooks via `agent-out` and product-specific env vars
  (`CLAUDE_KIT_STATE_HOME`).
- Source: contract in `manifests/runtime-roots.yaml` and
  `manifests/product-capabilities.yaml`.
- Install mechanism: `agent-runtime install` sets the env var via the
  managed block; `agent-out` allocates artifact paths at runtime.
- Acceptance lane: drift audit + doctor verify resolution; backup
  retention reported by `doctor`.
- Support today: **shipped (env var + runtime allocator)**.

## Coverage Summary

| # | Surface | runtime-kit ships | Mechanism | Min Claude | Min nils-cli |
|---|---|---|---|---|---|
| 1 | `CLAUDE.md` (home) | yes | rendered home prompt symlink to `build/claude/AGENT_HOME.md` | 2.1.145 | v1.12.1 |
| 2 | `./CLAUDE.md` (repo-local) | yes | symlink to `./AGENTS.md` | 2.1.145 | n/a |
| 3 | `.claude-plugin/plugin.json` | yes | rendered + copy-install | 2.1.145 | v0.17.5 |
| 4 | `.claude-plugin/marketplace.json` | yes | rendered + copy-install | 2.1.145 | v0.17.5 |
| 5 | `plugins/<p>/skills/<s>/` | yes | rendered + recursive symlink | 2.1.145 | v0.20.0 |
| 6 | `commands/<n>.md` | yes | linked directory | 2.1.145 | v0.17.5 |
| 7 | `agents/<n>.md` | yes | rendered + directory symlink into `~/.claude/agents` | 2.1.145 | v1.3.0 |
| 8 | `hooks/<n>.*` scripts | partial | shared scripts linked; claude adapter slot empty | 2.1.145 | v0.17.5 |
| 9 | `settings.json` hooks block | yes | fragment merge into live settings | 2.1.145 | v0.17.5 |
| 10 | `output-styles/<n>.md` | no | — | n/a | n/a |
| 11 | `statusLine` | no | — | n/a | n/a |
| 12 | MCP servers | no | — | n/a | n/a |
| 13 | Heuristic system | yes | shared policy root | 2.1.145 | v1.8.0 (heuristic-inbox) |
| 14 | `state_home` | yes | env var + `agent-out` allocation | 2.1.145 | v1.19.2 (`path-for`; reviewed cleanup plan/apply is skill-specific in `meta.agent-out`) |

Status legend:

- **yes** — concrete source artifact + link-map entry + acceptance
  lane.
- **partial** — some sub-surfaces present, others reserved but empty.
- **planned-not-shipped** — contract defined in manifests but no source
  artifact yet.
- **no** — Claude harness primitive that runtime-kit does not target;
  not on the current roadmap unless added explicitly.

## Acceptance Lanes (Claude-Relevant CI Gates)

From `DEVELOPMENT.md`:

1. `plan-tooling validate` — covers manifest schemas.
2. `agent-runtime render --product codex` — not Claude-side.
3. **`agent-runtime render --product claude`** — render gate.
4. **render-golden refresh + `git diff --exit-code`** — render
   determinism gate.
5. **`agent-runtime audit-drift` + fixtures** — drift audit gate
   (includes Claude plugin manifest schema diff).
6. `agent-runtime doctor --class skill-surface --product codex` —
   Codex-only today; **no Claude-side skill-surface diagnostic** in the
   default gate.
7. **sandbox install rehearsal** — installs into a temp `live_home`,
   diffs `tests/sandbox/claude/expected-skills.txt` and
   `tests/sandbox/claude/expected-agents.txt`.
8. **runtime-smoke deterministic mode** — exercises representative
   Claude-installed skills.
9. project-local overlay smoke — Codex-side; not Claude.
10. **`bash tests/hooks/run.sh`** — hook adapter contract tests.

Quarantined (not in default CI):

- `bash tests/runtime-smoke/run.sh --mode product --product claude`;
  `--probe-only` validates isolated CLI invocation. Prompt execution
  requires `RUNTIME_SMOKE_PRODUCT_EXECUTE=1` plus isolated
  provider/auth.

Live Claude acceptance (a fresh Claude session reading the installed
surface) has no in-tree CI gate today. The closest analogue on the
Codex side is `codex debug prompt-input` in
`docs/plans/2026-06-20-codex-plugin-marketplace-adoption/`; no
equivalent Claude protocol exists yet.
