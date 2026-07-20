# DEVELOPMENT.md

## What This Document Is

`DEVELOPMENT.md` is the required-reading maintenance and development guide for
`agent-runtime-kit`: setup, edit preflight, build/render, validation, and the
release boundaries. For repository orientation — what the repo owns, the runtime
model, and the directory map — start at [`README.md`](README.md). This file
covers how to work in the repo, not what it is.

This repository is the content source of truth for agent runtime surfaces:
skills, plugin metadata, hooks, render templates, manifests, policy docs, and
tests. It does not ship a CLI binary — the `agent-runtime` command and the rest
of the runtime surface live in `sympoies/nils-cli` and install through
`brew install sympoies/tap/nils-cli`. The one artifact this repo itself
publishes is the standalone Linux container image at
`ghcr.io/graysurf/agent-runtime-kit`; see [`RELEASING.md`](RELEASING.md) for how
that image is versioned and cut.

The local gate stack is mature. `scripts/ci/all.sh` runs sixteen positions
covering plan/skill governance, nils-cli pin alignment, Codex/Claude render and
golden diff, drift audit, surface-registry acceptance, the skill-surface shape
diagnostic, sandbox install rehearsal, runtime-smoke, project-local overlay
smoke, the shared hook contract, version-baseline mirrors, product leakage
audit, and deterministic memory policy/retired-reference routing.
`scripts/setup.sh` contains the brew-first host bootstrap path for installing
the released `agent-runtime` binary, rendering and wiring home prompt docs,
activating Claude/Codex runtime homes, pruning stale managed surfaces, and
running doctor.

## Setup

Install the released CLI surface first:

```bash
command -v brew >/dev/null 2>&1
brew tap sympoies/tap
brew install sympoies/tap/nils-cli
agent-runtime --version
plan-tooling --version
```

Required-doc policy is data this repo declares in `AGENT_DOCS.toml`; the harness
delivers it (home policy auto-loaded, per-intent docs hook-injected, and
SessionStart strict preflight for each declared intent). CI/manual health checks
still use `agent-docs audit` for install wiring, declared-doc validity, and
catalog validity. To inspect what this repo requires, or to audit its health:

```bash
agent-docs preflight --docs-home "$PWD" --intent project-dev --strict
agent-docs preflight --docs-home "$PWD" --intent task-tools --strict
agent-docs audit --docs-home "$PWD" --target project --strict
```

### Managed-session coordination documentation

`AGENT_HOME.md` carries the global invariant: coordination helps agents avoid
worktree and task-scope collisions, but it does not grant work authorization.
`core/policies/session-coordination.md` is the canonical detailed policy for
default advisory behavior, warning response, unmanaged sessions, and explicit
enforcement. `AGENT_DOCS.toml` loads that policy through the home-scoped
`session-coordination` intent; inspect the resolved contract with:

```bash
agent-docs preflight --docs-home "$PWD" --intent session-coordination --strict
```

Keep user authorization, repository policy, and provider consent distinct from
work-context metadata. Global policy and hook guidance belong here; the
`agent-session` CLI and protocol contract belong in `sympoies/nils-cli`.

Rendered home prompts live under `build/<product>/AGENT_HOME.md`, so manual
checks in this checkout should pass `--docs-home "$PWD"` explicitly and prefer
strict preflight for home-scoped docs until the released `agent-docs audit`
wiring check understands rendered home prompt symlinks. Repo-owned hooks do the
same docs-home fallback automatically only when the active repo is the
runtime-kit source checkout; other project catalogs inherit the active managed
docs-home.

For a first-time host or clean reinstall, prefer the setup wrapper and preview
it first. If Homebrew is already present or managed by the operator, keep
`--skip-homebrew-install`; otherwise omit that flag so setup can install
Homebrew non-interactively.

```bash
bash scripts/setup.sh --profile core --skip-homebrew-install --dry-run
bash scripts/setup.sh --profile core --skip-homebrew-install
```

The wrapper keeps the Homebrew / CLI-tool and home-prompt gates in shell, then
feature-detects `agent-runtime bootstrap-host`. When the installed nils-cli
surface provides that command, setup delegates runtime surface bootstrap to it
for render, install, prune-stale, and skill-surface verification. When the host
is still on an older pinned release, setup stays compatible by running the same
manual phases directly. In both paths, setup then invokes
`scripts/sync-runtime-surfaces.sh --product claude --no-pull --no-prune
--no-verify` and the matching Codex command so the local `claude-kit` and
`codex-kit` marketplaces are materialized into state home, registered, and
installed when the product CLIs are available.

Manual phase recovery remains supported:

```bash
agent-runtime render --source-root "$HOME/.config/agent-runtime-kit" \
  --target home-prompt
agent-runtime render --source-root "$HOME/.config/agent-runtime-kit" \
  --target home-prompt --product codex
agent-runtime render --source-root "$HOME/.config/agent-runtime-kit" \
  --target home-prompt --product claude
agent-runtime render --source-root "$HOME/.config/agent-runtime-kit" --product codex
agent-runtime render --source-root "$HOME/.config/agent-runtime-kit" --product claude
agent-runtime install --source-root "$HOME/.config/agent-runtime-kit" \
  --product codex --live-home "${CODEX_HOME:-$HOME/.codex}" \
  --state-home \
  "${CODEX_AGENT_STATE_HOME:-$HOME/.local/state/agent-runtime-kit/codex}" \
  --apply
agent-runtime install --source-root "$HOME/.config/agent-runtime-kit" \
  --product claude --live-home "$HOME/.claude" \
  --state-home \
  "${CLAUDE_KIT_STATE_HOME:-$HOME/.local/state/agent-runtime-kit/claude}" \
  --apply
agent-runtime prune-stale --source-root "$HOME/.config/agent-runtime-kit" \
  --product codex --live-home "${CODEX_HOME:-$HOME/.codex}" --apply
agent-runtime prune-stale --source-root "$HOME/.config/agent-runtime-kit" \
  --product claude --live-home "$HOME/.claude" --apply
bash "$HOME/.config/agent-runtime-kit/scripts/sync-runtime-surfaces.sh" \
  --source-root "$HOME/.config/agent-runtime-kit" \
  --product claude --no-pull --no-prune --no-verify --apply
bash "$HOME/.config/agent-runtime-kit/scripts/sync-runtime-surfaces.sh" \
  --source-root "$HOME/.config/agent-runtime-kit" \
  --product codex --no-pull --no-verify --apply
agent-docs preflight --docs-home "$HOME/.config/agent-runtime-kit" \
  --project-path "$HOME/.config/agent-runtime-kit" \
  --intent project-dev --strict
agent-docs preflight --docs-home "$HOME/.config/agent-runtime-kit" \
  --project-path "$HOME/.config/agent-runtime-kit" \
  --intent task-tools --strict
agent-runtime doctor --source-root "$HOME/.config/agent-runtime-kit" \
  --product codex --live-home "${CODEX_HOME:-$HOME/.codex}" \
  --state-home \
  "${CODEX_AGENT_STATE_HOME:-$HOME/.local/state/agent-runtime-kit/codex}" \
  --profile core
agent-runtime doctor --source-root "$HOME/.config/agent-runtime-kit" \
  --product claude --live-home "$HOME/.claude" \
  --state-home \
  "${CLAUDE_KIT_STATE_HOME:-$HOME/.local/state/agent-runtime-kit/claude}" \
  --profile core
```

## Verified-Signature Push Fallback

`main` is protected by repository rules that require verified commit
signatures. Keep that protection in place. If a direct push fails with a rule
error such as:

```text
GH013: Repository rule violations found
Commits must have verified signatures
error: cannot run gpg: No such file or directory
```

use a branch plus PR flow instead of weakening the rule or bypassing signing.
For agent sessions, continue to use the managed worktree, `semantic-commit`,
and `forge-cli` delivery path required by the repo policy. For manual human
maintenance from a fresh machine with `gh auth login` and repo write access, the
fallback is:

```bash
git switch -c docs/<short-topic>
git push -u origin HEAD
gh pr create --base main --head "$(git branch --show-current)"
```

Local GPG or SSH commit signing is optional for this fallback path. Configure it
only when the operator wants signed local commits as part of their normal setup;
do not make GPG installation a bootstrap prerequisite for every contributor.

Generated plan bundles do not need a direct push to `main` before execution.
They need provider-visible source, plan, and state records on the tracking issue.
If the plan bundle PR remains open after execution finishes, update its
execution-state document with the final evidence before merging it, or close the
PR as obsolete if the issue closeout already superseded the branch contents.

## Refreshing Runtime Surfaces

After managed runtime surface changes land, use
`scripts/sync-runtime-surfaces.sh` for the daily refresh path. It pulls the
active checkout, renders and wires the per-product home prompts, renders Codex
and Claude targets, installs the rendered surfaces into the runtime homes,
registers/installs the local `codex-kit` and `claude-kit` plugin marketplaces
from symlink-free state-home copies when the product CLIs are available, and
runs the skill-surface doctor probes; it is dry-run by default and writes only
with `--apply`. Keep
`scripts/setup.sh` for first-time host bootstrap and CLI tool installation; it
delegates the same plugin registry activation after bootstrap.

Retired managed-surface cleanup has two separate sources of truth:
`manifests/retired-skill-ids.json` owns the product-neutral ID boundary used by
Codex, Claude, and Hermes cleanup, while
`manifests/retired-hermes-skill-copies.json` owns Hermes exact-copy digests.
The digest manifest names the immutable pre-retirement revision used to
recompute every digest from historical Hermes goldens. CI checks out full Git
history for that replay, so retired skill content does not need to remain in an
active source or fixture tree.

Exact historical Hermes copies are removed from the discoverable `skills/`
tree by an atomic no-replace move into
`$HERMES_HOME/.agent-runtime-kit-quarantine/hermes-retired-skills/`. The
quarantine is ownership-marked and retained: refresh never recursively deletes
its contents. Rollback/re-upgrade cycles retain additional deterministic
`.generation-NNNNNN` siblings after validating every existing generation as an
exact match. Top-level cleanup opens the Hermes home and skills components with
no-follow descriptors and performs symlink removal and copy moves relative to
those descriptors; empty legacy directories are harmless and deliberately
left in place. Profile roots are classified read-only: any legacy runtime-kit
surface there returns `review-needed` for manual migration and is never mutated
automatically. A pre-existing unowned quarantine, non-matching destination,
changed copy, or changed/symlinked traversal also returns `review-needed` and
leaves operator data untouched.

For non-technical operators setting up another Mac through an agent, use the
copyable clean-reinstall prompt in
[`docs/source/macos-agent-bootstrap-prompt.md`](docs/source/macos-agent-bootstrap-prompt.md).

## Overlaying Private Skills

Personal **global skills** — ones that should be available in every session but
do not belong in this repo's governed, rendered catalog — are created under
`$AGENT_PRIVATE_SKILLS_HOME`, not committed here and not hand-placed in the
runtime homes. This is the canonical home for opening a new global skill
(including sensitive or machine-local ones): scaffold it with the
create-project-skill tooling into `$AGENT_PRIVATE_SKILLS_HOME/.agents/skills/<name>/`,
then manage it from here through `scripts/sync-private-skills.sh`. The script
keeps that private skill SOURCE tree separate and symlinks each skill into the
per-user skill namespaces the local agent products discover:

- Codex: `$CODEX_HOME/skills/<name>` (default `$HOME/.codex/skills/<name>`)
- Claude: `$HOME/.claude/skills/<name>`
- Hermes: `$HOME/.hermes/external-skills/private/<name>` (presence-gated:
  included in the default product set only when `$HOME/.hermes` exists)

Unlike `sync-runtime-surfaces.sh`, this overlay does not render, install through
nils-cli, or touch any manifest — project-local `SKILL.md` is already the
native format these products consume. The target namespaces do not collide with
the runtime-kit managed surface (Codex domain dirs, Claude
`plugins/<domain>/skills/`, and Hermes
`$HOME/.hermes/external-skills/agent-runtime-kit/<domain>/`). The overlay
refuses to clobber any path it does not own, so a private skill named after a
runtime-kit domain dir is skipped rather than overwriting it. The script is
dry-run by default; pass `--apply` to write, and `--prune` to drop overlay
symlinks whose source skill was removed or no longer targets that product.
When `$AGENT_PRIVATE_SKILLS_HOME` is unset it is a safe no-op, so hosts without
a private tree are unaffected.

By default a private skill is exposed to every available product. To target a
subset, add `<skill>/agents/products.txt` with one exact product per line:
`codex`, `claude`, or `hermes`. A missing file preserves the all-product
behavior. An existing file must be non-empty and must not contain blank,
duplicate, or unknown entries. The sync validates every declaration before it
creates a runtime directory, updates a link, or prunes an owned link, so invalid
metadata fails closed without partial runtime mutation. Product narrowing takes
effect on existing owned links when `--prune` is supplied; real directories and
foreign symlinks remain untouched.

The private `.agents/skills` root, each skill directory, and every subordinate
resource inside a skill must resolve to real paths below the declared private
home. Symlinked resources or canonically escaped source boundaries fail closed
before apply or prune can mutate a runtime home. Each selected product's skills
target components must also be real, canonical children of its configured
runtime home. The sync preflights every selected target before starting the
first product, so one redirected Codex, Claude, or Hermes root cannot receive
links, lose pruned entries, or leave a partial multi-product update.

The Hermes target deliberately mounts through Hermes's read-only
`skills.external_dirs` mechanism instead of the local `$HERMES_HOME/skills/`
tree: local Hermes skills are autonomously curated by the Hermes agent, and a
symlinked local skill would let that maintenance write through into the private
source repo. Each Hermes profile config must register the root once
(`skills.external_dirs: ["~/.hermes/external-skills"]`); the overlay checks the
profile configs it can see and prints that snippet when the registration is
missing. Offline coverage lives in `tests/smoke/sync-private-skills.sh`.

## Repository Layout

The directory map is owned by [`README.md`](README.md) ("Repository map"), which
is the orientation entrypoint for this repo. The validation sections below name
the `tests/` and `scripts/ci/` paths they exercise directly, so this guide does
not duplicate the tree.

## Documentation Changes

`AGENT_DOCS.toml` registers
`docs/source/docs-placement-retention-policy-v1.md` as required `project-dev`
context. Before adding or modifying `docs/**` or a repository-root `*.md` file,
resolve the normal `agent-docs` preflight and follow that policy.

## Helper And Script Boundary

Durable runtime behavior belongs in `sympoies/nils-cli`: render, install,
uninstall, doctor, drift audit, JSON contracts, exit-code contracts, parsers,
and shared capability binaries.

Top-level repository scripts under `scripts/` are Bash glue. They may bootstrap
a host, chain CI gates, compare fixture output, or call released nils-cli
binaries. Keep them compatible with macOS system Bash 3.2 and Linux Bash; avoid
Bash 4-only features unless the script declares a narrower host contract.

Python is acceptable for skill-local helpers under `core/skills/**/bin/` when the
logic is owned by one skill and does not define a shared runtime contract. Render
those helpers through a thin shell wrapper when a product expects an executable
script. If the helper becomes cross-skill, semver-sensitive, or relied on for
stable machine output, extract it to nils-cli and declare it in `required_clis`.

## Skill Lifecycle Changes

Use the `meta:create-skill` and `meta:remove-skill` skills for repo-owned managed
skill additions and removals. Use `meta:create-project-skill` and
`meta:remove-project-skill` for consuming-repo `.agents/skills` additions and
removals. The managed-skill workflows cover source, manifests, product render
output, sandbox pins, runtime-smoke coverage, and retained historical records;
the project-skill workflows must not mutate runtime-kit manifests or product
render output.

`skill-governance` is not a user-facing skill. The repo-owned governance check is
`bash scripts/ci/skill-governance-audit.sh`, with fixture modes for create/remove
lifecycle coverage. If lifecycle work needs deterministic mutation, dry-run/apply
plans, or machine-readable reference graphs, implement that primitive in
`sympoies/nils-cli`, release it, then declare the consumed binary in
`required_clis`.

## Coupled nils-cli Work

Many changes here need unreleased `nils-cli` behavior. That work stays in
`sympoies/nils-cli`, not this repo. Build a debug binary without replacing the
Homebrew release and point the content gates at it:

```bash
cargo build -p nils-agent-runtime \
  --manifest-path "$HOME/Project/sympoies/nils-cli/Cargo.toml"

AGENT_RUNTIME="$HOME/Project/sympoies/nils-cli/target/debug/agent-runtime"
"$AGENT_RUNTIME" render --product codex
"$AGENT_RUNTIME" audit-drift
```

`scripts/dev/with-nils-version.sh` wraps this — it resolves a released, source,
or local nils-cli surface, puts the full binary set on `PATH`, prints the
resolved version, and runs your command:

```bash
scripts/dev/with-nils-version.sh local           -- \
  agent-runtime render --product codex
scripts/dev/with-nils-version.sh src:my-fix      -- bash tests/hooks/run.sh
scripts/dev/with-nils-version.sh release:v1.0.0  -- agent-runtime audit-drift
```

Mind the version-policy gate: Position 1 blocks below the compatibility minimum,
admits exact minimum through validated, and warns while continuing when the host
is newer than validated. This lets coupled development run the full behavior
stack without calling an unreleased/ahead surface validated. Policy movement is
owned by `meta:nils-cli-bump`; `cargo install --path` is never the default loop.

`docs/source/nils-cli-version-workflows.md` owns the full clone / worktree /
downgrade / coupled-dev / bump procedures and the exact content-gate command
list.

## Build And Render

Regenerate product outputs from repository root:

```bash
agent-runtime render --product codex
agent-runtime render --product claude
```

Refresh render-golden snapshots when the intended output changes:

```bash
agent-runtime render --product codex --update-golden
agent-runtime render --product claude --update-golden
git diff -- tests/golden/
```

Review the generated diff before committing it.

## Validation

Run the current full local gate:

```bash
bash scripts/ci/all.sh
```

That currently performs:

1. nils-cli minimum/validated policy: `agent-runtime doctor --class
   version-alignment --pin docs/source/nils-cli-pin.yaml` — blocks below
   `minimum_supported_tag` or any `required_clis[]` floor, admits through
   `validated_tag`, and warns above validated before continuing downstream
2. `plan-tooling validate --format text --explain` plus
   `scripts/ci/skill-governance-audit.sh` repo/create/remove fixture checks
3. `agent-runtime render --target home-prompt` for neutral / Codex / Claude,
   then `agent-runtime render --product codex`
4. `agent-runtime render --product claude`
5. `agent-runtime render --target support-matrix`
6. render-golden refresh plus `git diff --exit-code -- tests/golden/`
7. `agent-runtime audit-drift` plus all fixtures under `tests/drift/`
8. `python3 scripts/ci/security-hardening-audit.py` plus
   `bash scripts/ci/validate-surfaces-manifest.sh --execute-acceptance`
9. `agent-runtime doctor --class skill-surface --product codex` shape preflight
10. sandbox install rehearsal dry-run plus expected skill-list diff
11. `bash tests/runtime-smoke/run.sh --mode deterministic`
12. `bash tests/projects/project-local-smoke/run.sh`
13. `bash tests/hooks/run.sh`
14. `python3 scripts/ci/version-baseline-audit.py check` — deterministic,
    network-free consistency gate over the version-baseline mirrors: the
    `README.md` "Version baseline" table, each `docs/source/harness-shape-*.md`
    "Version Floors" statement, and `docs/source/nils-cli-surface.md` must
    agree with their sources of truth (`manifests/runtime-roots.yaml` for the
    product floor, `docs/source/nils-cli-pin.yaml` for both nils-cli roles). Run
    `… report` for an advisory installed-vs-latest probe.
15. `bash scripts/ci/product-leak-audit.sh --self-test` plus
    `bash scripts/ci/product-leak-audit.sh` — broad-sentinel leakage audit over
    rendered/loaded product artifacts, with documented allowlist reasons in
    `scripts/ci/product-leak-allow.yaml`.

Position 1 retains the silent-drift protection while separating admission from
reproducibility. As of nils-cli v1.25.0 the schema-v2 doctor owns stable-version
comparison: below minimum blocks, above validated warns and must still traverse
the behavior stack, and exact minimum/validated provider lanes retain formal
reproducibility. Blocking CI verifies role-owned archive digests before running
downloaded surfaces. Docker and published images always use validated plus its
checked-in release digests.

The surface manifest validation at position 8 also executes the promoted
acceptance entries, which currently cover one `kind=ci` command and one
`kind=live` command from the registry.

The skill-surface shape diagnostic at position 9 is a deterministic
preflight, not live Codex Desktop acceptance. It validates only the
runtime-kit source/link-map surface that Codex would discover; live skill
visibility still requires `codex debug prompt-input` in a fresh Codex
Desktop session. When the source surface grows new entries, bump
`SHAPE_EXPECTED_MIN_CHECKS` only if the doctor-reported check count changes,
and record the reason in the bump commit.

For targeted checks:

```bash
plan-tooling validate --format text --explain
bash scripts/ci/skill-governance-audit.sh
bash scripts/ci/skill-governance-audit.sh --fixture create
bash scripts/ci/skill-governance-audit.sh --fixture remove
python3 scripts/ci/security-hardening-audit.py
bash scripts/ci/validate-surfaces-manifest.sh
bash scripts/ci/validate-surfaces-manifest.sh --execute-acceptance
if bash scripts/ci/validate-surfaces-manifest.sh \
  tests/surfaces/invalid-acceptance.yaml; then exit 1; else test $? -ne 0; fi
agent-runtime audit-drift
agent-runtime audit-drift --source-root tests/drift/source-manifest-missing/
bash scripts/ci/sandbox-install-rehearsal.sh
bash tests/runtime-smoke/run.sh --mode matrix
bash tests/runtime-smoke/run.sh --mode install
bash tests/runtime-smoke/run.sh --mode install --format json
bash tests/runtime-smoke/run.sh --mode deterministic
bash tests/runtime-smoke/run.sh --mode deterministic --domain meta
bash tests/runtime-smoke/run.sh --mode deterministic --domain media
bash tests/runtime-smoke/run.sh --mode deterministic --domain browser
bash tests/runtime-smoke/run.sh --mode deterministic --domain conversation
bash tests/runtime-smoke/run.sh --mode deterministic --domain evidence
bash tests/runtime-smoke/run.sh --mode deterministic --domain pr
bash tests/runtime-smoke/run.sh --mode deterministic --domain dispatch
bash tests/runtime-smoke/run.sh --mode deterministic --domain reporting
bash tests/projects/project-local-smoke/run.sh
bash tests/runtime-smoke/run.sh --mode product --product codex
bash tests/runtime-smoke/run.sh --mode product --product claude
bash tests/runtime-smoke/run.sh --mode product --product codex --probe-only
bash tests/runtime-smoke/run.sh --mode product --product claude --probe-only
bash tests/runtime-smoke/run.sh --mode convergence
bash tests/runtime-smoke/run.sh --mode product --format json \
  > /tmp/runtime-smoke-product-summary.json
diff -u tests/runtime-smoke/product/expected/product-summary.json \
  /tmp/runtime-smoke-product-summary.json
if bash tests/smoke/deliver-lifecycle.sh; then exit 1; else test $? -ne 0; fi
bash tests/smoke/deliver-lifecycle.sh \
  --scratch-fork graysurf/agent-runtime-kit-smoke \
  --scratch-branch agent-runtime-kit-delivery-smoke
```

Runtime smoke install mode creates temporary Codex and Claude `live_home` and
`state_home` roots, runs `agent-runtime install --apply`, compares installed
skill surfaces with `tests/sandbox/<product>/expected-skills.txt`, and accepts
`agent-runtime doctor` only when its summary reports `block=0`. Host warnings
can vary and are not treated as install-smoke blockers.

Runtime smoke deterministic mode runs command-level probes inside temporary
fixture workspaces and writes artifacts under the run artifact directory.
Current deterministic coverage includes the `meta`, `media`, `browser`,
`conversation`, `evidence`, `issue`, `code-review`, `pr`, `dispatch`, and
`reporting` domains.
`screen-record` is host-sensitive: the deterministic media probe records a pass
when `screen-record --preflight` succeeds and records `skip-host-capability`
when the host capture prerequisites are unavailable.

`tests/projects/project-local-smoke/run.sh` validates project-local shim
coverage for `bootstrap`, `deploy`, `pre-pr`, and `release`. It executes
fixture `.agents/scripts/*.sh` files, installs Codex into a temp runtime home,
runs `agent-runtime doctor --check-project`, verifies both wired and
missing-script overlay reports, and exercises `setup-project` adoption
diagnostics against temporary repositories.

`tests/smoke/deliver-lifecycle.sh` is a controlled PR delivery smoke.
It refuses to run without a scratch fork and branch, and its default mode is a
credential-free `forge-cli pr deliver --dry-run`. Use `--execute-live` only for
an intentional scratch-repository PR lifecycle run.

Runtime smoke product mode is quarantined outside the default CI gate. Use
`--probe-only` to validate that Codex and Claude can be invoked with temporary
runtime homes only:

```bash
bash tests/runtime-smoke/run.sh --mode product --product codex --probe-only
bash tests/runtime-smoke/run.sh --mode product --product claude --probe-only
```

The probe is allowed to pass with a manual-only prompt note when the product CLI
is isolated correctly but the host lacks an isolated local provider or API key.
Without `--probe-only`, product mode also installs the current runtime surface
into temporary product homes and records prompt cases for representative skills.
Prompt execution is skipped by default. Set `RUNTIME_SMOKE_PRODUCT_EXECUTE=1`
only when the host has isolated provider/auth state for the product prompt path.
Product mode must not read or mutate real `$HOME/.codex`, `$HOME/.claude`,
auth, sessions, history, logs, or caches.

Portable convergence mode stays credential-free and isolated. From a clean
committed clone, it verifies a historical 66-to-current-skill upgrade, receipt
  revision transition, independently rebuilt receipt entry/plan digests,
  baseline re-sync rollback, retired-surface prune, exact plugin refs and active
  skill IDs, operator-state preservation, and idempotency. Its four
redacted prompt/route fixtures validate only the declared routing contract;
authenticated routing and the bounded desktop action remain the post-merge
live acceptance lane.

## Release Boundary

Two independent release axes touch this repo:

- **This repo's own artifact** is the GHCR container image, cut from `main` on a
  CalVer tag. It is fully owned by [`RELEASING.md`](RELEASING.md) — that is the
  entrypoint for publishing a kit snapshot through `scripts/release.sh` /
  `.agents/scripts/release.sh`, not anything below.
- **The nils-cli surface** is an upstream dependency pinned by
  `docs/source/nils-cli-pin.yaml`. The steps below cover promoting a stable
  coupled nils-cli change into that pin.

Unreleased nils-cli debug binaries can be used to develop and validate this
repo, but they do not satisfy a released `required_clis` contract. After a
coupled change is stable:

1. Land the nils-cli PR.
2. Cut the nils-cli release.
3. Bump `sympoies/homebrew-tap`.
4. Upgrade the local Homebrew install and verify `agent-runtime --version`.
5. Refresh `docs/source/nils-cli-surface.md`.
6. Bump affected `required_clis` floors in `manifests/`.
7. Re-run `bash scripts/ci/all.sh`.

Do not touch `sympoies/homebrew-tap` for ordinary day-to-day development. It is
the release destination only.
