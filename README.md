# agent-runtime-kit

`agent-runtime-kit` is the source repository for the local agent runtime layer
shared by **Codex CLI** and **Claude Code**. Skills, hooks, policy docs, plugin
metadata, manifests, and adapter templates are edited here, then rendered into
product-specific runtime homes such as `$HOME/.codex` and `$HOME/.claude`.

Per-surface ship state is tracked in [`SUPPORT_MATRIX.md`](SUPPORT_MATRIX.md).

## What this repo owns

- Portable runtime source under `core/`: skills, hooks, policies, schemas, and
  product-independent helper content.
- Product adapters under `targets/`: Codex and Claude link maps, templates, and
  activation surfaces.
- Machine-readable inventory under `manifests/`: skills, plugins, product
  capabilities, runtime roots, CLI floors, and labels.
- Generated review output under `build/`, pinned by `tests/golden/`.
- Repository docs, plans, fixtures, and validation scripts.

This repo does **not** ship binaries and does not track host runtime state,
auth, sessions, logs, caches, generated backups, or secrets.

## Version baseline

| component | floor | source |
|---|---|---|
| Codex CLI (`codex --version`) | `0.144.5` (effective 2026-07-10) | `manifests/runtime-roots.yaml` |
| Claude Code (`claude --version`) | `2.1.211` (effective 2026-07-10) | `manifests/runtime-roots.yaml` |
| Hermes Agent (`hermes --version`) | `0.17.0` (effective 2026-06-30) | `manifests/runtime-roots.yaml` |
| `nils-cli` surface (`agent-runtime --version`) | minimum `v1.25.13`; validated `v1.26.2` | `docs/source/nils-cli-surface.md` |

Per-skill `nils-cli` floors live in `manifests/skills.yaml` `required_clis`
and may be tighter than the surface compatibility floor.

## Runtime model

The repo separates source, rendered output, installed runtime homes, and
writable per-host state.

```text
core/                     manifests/         targets/
  skills/  hooks/  docs/  *.yaml             codex/   claude/
  policies/                                  link-map.yaml + adapter files
        |                     |                      |
        +---------------------+----------------------+
                              |
                              | agent-runtime render --product <codex|claude>
                              v
                         build/<product>/      (regenerated, golden-pinned)
                              |
                              | agent-runtime install --apply
                              v
       live_home: $HOME/.codex   $HOME/.claude       (managed runtime)
       state_home: $XDG_STATE_HOME/agent-runtime-kit/{codex,claude}/
                   override via CODEX_AGENT_STATE_HOME / CLAUDE_KIT_STATE_HOME
                   (writable artifacts under <state_home>/out/ and /backups/)
```

Product output is manifest-selected rather than a recursive copy of `core/`.
The default `product` render target emits declared skills and agents; run
`agent-runtime render --target home-prompt --product <product>` for the separate
home-prompt target. Canonical policy documents stay under `core/policies/` and
`agent-docs` resolves them from the selected docs home; they are not duplicated
under `build/<product>/core/policies/`.

Live Codex skill discovery reads installed `codex-kit` plugin bundles as
`<plugin>:<skill>` entries; live Claude discovery reads
`$HOME/.claude/plugins/<p>/skills/`. Both are populated from this repo's
rendered `build/` output by the runtime sync and install surfaces.

## CLI boundary

The `agent-runtime` command and the rest of the runtime surface
(`agent-docs`, `agent-out`, `plan-tooling`, `forge-cli`,
`heuristic-inbox`, and related tools) live in
[`sympoies/nils-cli`](https://github.com/sympoies/nils-cli) and install via
Homebrew.

```bash
brew tap sympoies/tap
brew install sympoies/tap/nils-cli
agent-runtime --version
plan-tooling --version
```

Skills declare the binaries they need through `required_clis`. Released
contracts are pinned only after the upstream nils-cli release and Homebrew tap
update complete. Local debug builds are validation tools, not the default
development loop.

Shell and Python helpers in this repo are glue: CI gates, fixture checks, and
skill-local data helpers. Stable parsers, exit-code contracts, cross-product
behavior, and shared capabilities belong upstream in nils-cli.

## Local setup

Clone or enter your local checkout. docs-home is normally derived from the
installed prompt symlink. Bind manual source-checkout commands explicitly with
`--docs-home` and `--project-path`: `AGENT_DOCS_HOME` is a lower-precedence CLI
fallback, so exporting it alone does not override an installed prompt symlink.
Repository-owned hooks promote the environment value to the explicit flag;
setup selects its checkout root directly.

```bash
cd /path/to/agent-runtime-kit
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  audit --target project --strict
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  preflight --intent project-dev --strict --format json
```

For persistent hook integration, add a host-local path to `~/.zshenv`:

```zsh
# Replace this with your local checkout path.
export AGENT_DOCS_HOME="/path/to/agent-runtime-kit"
```

Do not commit a personal absolute path to this repo. Do not point
`AGENT_DOCS_HOME` at `$AGENT_HOME`, `$HOME/.agents`, `$HOME/.codex`, or
`$HOME/.claude`; it should point at the checked-out `agent-runtime-kit` docs
catalog. `$AGENT_HOME` is reserved for writable `agent-out` state.

For an agent-driven clean install or reinstall on another Mac, use the
copyable prompt in
[`docs/source/macos-agent-bootstrap-prompt.md`](docs/source/macos-agent-bootstrap-prompt.md).

## Development workflow

Required reading and validation are declared in `AGENT_DOCS.toml`. The compact
home policy is auto-loaded; phase-relevant intent docs are cued by hooks and
validation is enforced at the finish line. Agents load only the active
contract; humans can inspect or audit it from the repository root:

```bash
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  preflight --intent project-dev --strict --format json
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  audit --target project --strict
```

Documentation placement changes can load
[`docs/source/docs-placement-retention-policy-v1.md`](docs/source/docs-placement-retention-policy-v1.md),
which remains canonical but is optional `project-dev` context rather than
required reading for every edit.

The full local validation gate is:

```bash
bash scripts/ci/all.sh
```

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for setup details, render and golden
refresh commands, drift audit, sandbox install rehearsal, runtime-smoke checks,
and coupled nils-cli debug-build guidance.

## Repository map

```text
.
├── AGENT_HOME.md        # shared home-scope policy for Codex and Claude
├── AGENTS.md            # repo-local policy for this checkout
├── CLAUDE.md            # Claude import wrapper for AGENTS.md
├── AGENT_DOCS.toml      # project-local agent-docs dispatch entries
├── DEVELOPMENT.md       # maintenance/dev guide: setup, validation, release boundary
├── RELEASING.md         # how the GHCR container image is versioned and cut
├── SUPPORT_MATRIX.md    # per-surface ship state
├── core/
│   ├── docs/            # schemas and shared source docs
│   ├── hooks/           # shared and product-specific hook sources
│   ├── policies/        # portable runtime policies and retained records
│   └── skills/          # portable skill source by domain
├── targets/             # Codex and Claude adapter surfaces
├── manifests/           # machine-checkable runtime inventory
├── docs/
│   ├── source/          # architecture, policies, specs, and references
│   ├── plans/           # plan bundles and retained execution records
│   └── discussions/     # captured discussion / implementation-readiness specs
├── build/               # generated render output
├── docker/              # container image build context (published to GHCR)
├── tests/
│   ├── golden/          # render-golden snapshots
│   ├── drift/           # drift-audit fixtures
│   ├── runtime-smoke/   # runtime skill acceptance harness
│   ├── projects/        # project-local overlay smoke fixtures
│   ├── surfaces/        # surface-registry acceptance fixtures
│   ├── sandbox/         # install-rehearsal expected surfaces
│   ├── smoke/           # PR delivery lifecycle smoke
│   └── hooks/           # shared hook contract smoke
└── scripts/             # setup, sync, CI, dev, and validation glue
```

## Skills

Nine skill domains are currently rendered into Codex and Claude plugins:

`code-review` · `computer-use` · `conversation` · `dispatch` · `issue` ·
`media` · `meta` · `pr` · `reporting`

Representative skills include `pr:deliver-pr`,
`dispatch:deliver-plan-tracking-issue`, `issue:issue-triage`,
`meta:sync-runtime-surfaces`, `reporting:project-retro`, and
`computer-use:macos-desktop`.

The authoritative skill list and CLI floors live in `manifests/skills.yaml`.
The skill catalog is summarized in [`core/skills/README.md`](core/skills/README.md).

## Policy wiring

```text
AGENT_HOME.md   <- single source of global agent policy
       ^                 ^
       | symlink         | symlink
$HOME/.codex/AGENTS.md   $HOME/.claude/CLAUDE.md

AGENTS.md       <- project-scope policy for this repo
       ^
       | @AGENTS.md import
./CLAUDE.md
```

`AGENT_HOME.md` intentionally has a different name from `AGENTS.md` and
`CLAUDE.md`, so neither product reads the same policy twice when this source
repo is the active project.

## Next reading

- [`DEVELOPMENT.md`](DEVELOPMENT.md): setup, validation gates, and release boundary.
- [`SUPPORT_MATRIX.md`](SUPPORT_MATRIX.md): per-surface ship state and acceptance lanes.
- [`docs/source/macos-agent-bootstrap-prompt.md`](docs/source/macos-agent-bootstrap-prompt.md):
  copyable macOS agent prompt for clean zsh-kit / agent-runtime-kit setup.
- [`core/skills/README.md`](core/skills/README.md): skill catalog by category and series.
- [`AGENT_HOME.md`](AGENT_HOME.md): global agent policy loaded by both products.
- [`AGENTS.md`](AGENTS.md): project-scope policy and current boundaries.
