# AGENTS.md

## Scope

- Repo-local agent policy for `agent-runtime-kit`. Global / home-scope
  defaults live in `AGENT_HOME.md`, loaded by Codex via
  `$HOME/.codex/AGENTS.md` and by Claude via `$HOME/.claude/CLAUDE.md`
  (both symlinks point at this repo's `AGENT_HOME.md`).
- `./CLAUDE.md` in this repo is a one-line file containing `@AGENTS.md`,
  using Claude Code's import syntax so Claude reads the same repo-local
  rules without maintaining a second copy.

## Project Purpose

- This repo is the single canonical source for the local agent runtime layer
  shared by Codex and Claude: skills, workflows, hooks, docs, plugin metadata,
  install/link management, and drift auditing.
- Codex and Claude are product targets/adapters rendered from this shared
  source, not separate source repos that require manual porting.

## Local Source Repositories

- Single source of truth: this repo (`agent-runtime-kit`). Codex and Claude
  read it through symlinks (`$HOME/.codex/AGENTS.md`, `$HOME/.claude/CLAUDE.md`
  → `AGENT_HOME.md`) and through rendered targets in `targets/`.
- Live Codex home: `$HOME/.codex`
- Live Claude home: `$HOME/.claude`

## Important Boundaries

- Do not symlink or version the whole `~/.codex/config.toml`; the managed
  Codex block is synced separately and now carries no hook commands — provider
  hook ingress is owned by `agent-hook setup` (run via
  `scripts/sync-runtime-surfaces.sh`).
- Do not track runtime state: auth, history, sessions, logs, caches, plugin
  install artifacts, local generated state, or secrets.
- Use dry-run-first workflows for install/link/render/drift-audit changes.
- Provider issue / PR / MR labels are sourced from
  `manifests/forge-labels.yaml`; human guidance lives in
  `core/policies/forge-label-taxonomy.md`.
- Required env to operate the runtime:
  - `AGENT_HOME` — `agent-out` artifact root, e.g.
    `${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit`.
  - `AGENT_DOCS_HOME` — `agent-docs` catalog root, e.g. this checkout
    (`$HOME/Project/<org>/agent-runtime-kit`).
  - `AGENT_EVIDENCE_ARCHIVE_HOME` — optional `agent-evidence-archive` clone
    root (resolution order: `evidence --archive` flag > this env var > XDG
    config `agent-evidence-archive/config.yaml` > XDG data-home default). See
    `core/policies/evidence-archive/EVIDENCE_ARCHIVE.md`.

## Orientation

- Repo layout, setup, and validation: `DEVELOPMENT.md`.
- Where docs belong and how long they live:
  `docs/source/docs-placement-retention-policy-v1.md`.
- Per-product surface coverage (what ships into Codex / Claude today):
  `SUPPORT_MATRIX.md`, with the per-product narrative in
  `docs/source/harness-shape-codex.md` and
  `docs/source/harness-shape-claude.md`.
