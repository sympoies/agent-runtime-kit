# Harness Shape — Hermes

This is the Hermes-side raw material for the unified
[`SUPPORT_MATRIX.md`](../../SUPPORT_MATRIX.md). It mirrors
[`harness-shape-codex.md`](harness-shape-codex.md) and
[`harness-shape-claude.md`](harness-shape-claude.md) so the three product
views pivot into one matrix.

Hermes (the `hermes` agent, home `~/.hermes`) is a filesystem-first agent: it
loads its identity from `~/.hermes/SOUL.md`, auto-discovers skills under
`~/.hermes/skills/<domain>/<skill>/SKILL.md` plus configured
`skills.external_dirs` roots, and dispatches subagents through the
`delegate_task` tool rather than file-based agent definitions. It has no plugin
marketplace and the runtime-kit does not render Hermes hook scripts.

## Purpose

Inventory the surfaces the Hermes harness actually consumes at runtime and, for
each, record what `agent-runtime-kit` ships today, the mechanism it ships
through, the source artifact, and the version floor that gates it.

Scope rules:

- Mark a primitive `shipped` only when there is a concrete source artifact
  (`targets/hermes/...`, `core/...`, manifest entry, link-map entry).
- Surfaces that are specific to another product's harness (Claude
  `settings.json`, Codex `config.toml`, the Claude plugin marketplace) are
  marked `not-applicable` to keep this file pivotable with the codex / claude
  shape docs.
- Cite file paths (not line numbers — they rot); this doc must stay verifiable.

## Version Floors (Hermes side)

- Hermes product `min_version` / `recommended_version`: **0.17.0**;
  `min_version_effective_from`: **2026-06-30**; probe:
  `hermes --version` (`manifests/runtime-roots.yaml`).
- `agent-runtime` orchestration binary (renders / installs the Hermes surface)
  ships inside nils-cli; pinned snapshot **v1.21.15**
  (`docs/source/nils-cli-surface.md`, `docs/source/nils-cli-pin.yaml`).
  Hermes support was introduced in nils-cli v1.20.0 (`render --product hermes`,
  `render --target support-matrix` with a hermes column, `install` / `doctor`
  product handling, and `gc-backups` coverage) and completed in v1.20.1
  (`list-skills` and `prune-stale` product handling).
- Per-skill nils-cli floors come from `manifests/skills.yaml` `required_clis`
  and gate skill bodies, identical to the codex / claude render of the same
  shared skill source.

## Surface-By-Surface Shape

Each section answers the same questions so the table can pivot to a uniform
shape: what Hermes reads from, the checked-in source, the install mechanism,
the acceptance lane, and the current ship state.

### 1. Home-scope prompt (`SOUL.md` + development-policy skill)

- Hermes reads from: `~/.hermes/SOUL.md` (identity) which points at the rendered
  development-policy skill.
- Source: root `AGENT_HOME.md`, rendered to `build/hermes/AGENT_HOME.md`.
- Install mechanism: `agent-runtime render --target home-prompt --product
  hermes`, then `sync-runtime-surfaces.sh --apply --product hermes` copies the
  rendered prompt to `~/.hermes/skills/development-policy/SKILL.md`. `SOUL.md`
  itself is the user's identity file and is never overwritten by the kit.
- Support today: **shipped**.

### 2. Project-scope prompt (`./AGENTS.md` / `.hermes.md`)

- Hermes reads from: `AGENTS.md` or `.hermes.md` discovered from the working
  directory up to the git root.
- Source: repo-local `AGENTS.md` (this repo's `./CLAUDE.md` imports it).
- Install mechanism: working tree only; no render step.
- Support today: **shipped**.

### 3. Plugin manifest (`.hermes-plugin/plugin.json`)

- Hermes reads from: filesystem skill discovery; the `plugin.json` is
  metadata-only and not loaded at runtime.
- Source: `targets/hermes/plugins/<domain>/.hermes-plugin/plugin.json`.
- Install mechanism: `plugin-manifest-copy` per plugin into
  `~/.hermes/plugins/<domain>/.hermes-plugin/plugin.json`
  (`targets/hermes/link-map.yaml`, `manifests/plugins.yaml`).
- Support today: **shipped**.

### 4. Plugin marketplace

- Hermes has no plugin marketplace concept; skills are standalone `SKILL.md`
  files discovered from the skills tree.
- Support today: **not-applicable**.

### 5. Plugin-scoped skill discovery (`plugins/<p>/skills/<s>/`)

- This is the Claude nested layout. Hermes discovers skills from filesystem
  skill roots (see section 15), not from a `plugins/<p>/skills/` tree.
- Support today: **not-applicable**.

### 6. Slash command files (`commands/<name>.md`)

- The runtime-kit ships no Hermes slash-command files; Hermes invokes skills by
  name (`/skill <domain>/<skill>`) against the discovered skill tree.
- Support today: **not-applicable**.

### 7. Subagent definitions (`agents/<name>.md`)

- Hermes dispatches subagents through the `delegate_task` tool, not file-based
  agent definitions, so the kit renders no Hermes `agents/` tree.
- Support today: **not-applicable**.

### 8. Hook scripts (`hooks/<name>.*`)

- The runtime-kit does not render Hermes hook scripts. Hermes manages its own
  approval / hook configuration natively under `~/.hermes`, outside this kit.
- Support today: **not-applicable**.

### 9. Hook registration (`settings.json` block)

- `settings.json` hook registration is a Claude-specific primitive.
- Support today: **not-applicable**.

### 10. Output styles (`output-styles/<name>.md`)

- Output styles are a Claude-specific primitive; the kit ships none for Hermes.
- Support today: **not-applicable**.

### 11. Status line

- The `statusLine` setting is a Claude-specific primitive.
- Support today: **not-applicable**.

### 12. MCP servers (per-user MCP config)

- Hermes supports MCP natively, but the runtime-kit does not ship Hermes MCP
  server configuration today (the same stance as codex / claude).
- Support today: **not-shipped**.

### 13. Heuristic system (curated retained records)

- Hermes reads from: the shared policy root
  `core/policies/heuristic-system/`, referenced through `SOUL.md` and the
  rendered skills.
- Source / install mechanism: shared policy root (no per-product render).
- Support today: **shipped**.

### 14. Runtime state (`state_home`)

- Hermes reads from: `~/.hermes` (override via the `HERMES_HOME` env var).
- Source: `manifests/runtime-roots.yaml` hermes `state_home`.
- Support today: **shipped**.

### 15. Local and external skill roots

- Hermes reads from: `~/.hermes/skills/<domain>/<skill>/SKILL.md` and every
  configured `skills.external_dirs` root (nested filesystem discovery), the
  direct analogue of the Codex local skill root.
- Source: shared skill sources rendered to
  `build/hermes/plugins/<domain>/skills/<skill>/SKILL.md`.
- Install mechanism: recursive `symlinked-file` copy of each plugin's rendered
  skills tree into
  `~/.hermes/external-skills/agent-runtime-kit/<domain>` via
  `targets/hermes/link-map.yaml`. The local `~/.hermes/skills` tree remains for
  Hermes-native or operator-managed skills.
- Support today: **shipped**.

### 16. Codex hook registration (`config.toml` managed block)

- The Codex `config.toml` managed block is a Codex-specific primitive.
- Support today: **not-applicable**.

### 17. Prompt-mode delegation policy (`AGENT_HOME.md`)

- Hermes reads no prompt-mode delegation policy from `AGENT_HOME.md`; the
  Codex-only delegation block is omitted from
  `build/hermes/AGENT_HOME.md`.
- Hermes-specific subagent dispatch guidance remains in the rendered
  code-review skills that use `delegate_task`.
- Support today: **not-applicable**.

## Coverage Summary

| # | Surface | Hermes support |
| --- | --- | --- |
| 1 | Home-scope prompt | shipped |
| 2 | Project-scope prompt | shipped |
| 3 | Plugin manifest | shipped |
| 4 | Plugin marketplace | not-applicable |
| 5 | Plugin-scoped skill discovery | not-applicable |
| 6 | Slash command files | not-applicable |
| 7 | Subagent definitions | not-applicable |
| 8 | Hook scripts | not-applicable |
| 9 | Hook registration (`settings.json`) | not-applicable |
| 10 | Output styles | not-applicable |
| 11 | Status line | not-applicable |
| 12 | MCP servers | not-shipped |
| 13 | Heuristic system | shipped |
| 14 | Runtime state | shipped |
| 15 | Local skill root | shipped |
| 16 | Codex hook registration | not-applicable |
| 17 | Prompt-mode delegation policy | not-applicable |
