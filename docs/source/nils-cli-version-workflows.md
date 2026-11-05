# nils-cli Version Workflows

## Purpose

This repository has two explicit nils-cli version roles in
`docs/source/nils-cli-pin.yaml`:

- `minimum_supported_tag` is the compatibility floor. Hosts below it block.
- `validated_tag` is the exact reproducibility and packaging release.

An ambient host newer than validated is admitted with a warning and must still
complete the full downstream behavior stack. Provider CI independently runs
the exact minimum and exact validated releases; when both tags are equal it
executes one job that visibly represents both roles. A scheduled/manual canary
resolves the greatest strict stable semantic release without mutating policy or
becoming a required pull-request check.

The mechanics for scoped version switching live in
`scripts/dev/with-nils-version.sh`. This reference owns authorized adoption and mirror refresh. `python3 scripts/ci/version-baseline-audit.py check` and `report` remain verify-only.

## Core principles

1. Ordinary release uptake moves `validated_tag` and its validated release
   digests only. The retained `docs/source/nils-cli-minimum-digest.yaml` lane
   identity does not move.
2. `minimum_supported_tag` moves only when compatibility is explicitly retired
   or a new manifest/consumer contract cannot run on the old floor.
3. Docker, publish-image, surface snapshots, and validated claims always use
   `validated_tag`, never the ambient host.
4. Released `agent-runtime doctor --class version-alignment` owns host-policy
   comparison and typed diagnostics. A narrow remote-canary bootstrap exception
   in `nils-cli-policy-matrix.py` runs before the candidate binary exists: it
   filters and orders GitHub tags using the same canonical, non-leading-zero
   u64 `vMAJOR.MINOR.PATCH` contract, with focused drift regressions.
5. Temporary version switching changes `PATH`; it never edits the policy.

The consumed surface is the full nils-cli release (`agent-runtime`,
`forge-cli`, `agent-hook`, and the remaining
required CLIs), not one binary. The helper therefore resolves a release
tarball or whole-workspace build.

## Gate behavior

`scripts/ci/all.sh` Position 1 reads the schema-v2 manifest through
`agent-runtime doctor`:

| Host relationship | Doctor result | Downstream gates |
| --- | --- | --- |
| Below minimum | block, non-zero | do not run |
| Exact minimum through exact validated | admitted | run |
| Above validated | explicit compatibility-not-validated warning | run |
| Any `required_clis[]` floor miss | block, non-zero | do not run |

The warning is not a compatibility claim. Success means the newer host also
completed the repository's behavioral validation. Version admission is first
so a below-minimum nils-cli cannot execute later content gates. The
newest-stable canary is additional evidence and never rewrites either role.

## Workflow A — Reproduce against another released version

Use a release-scoped full surface without touching Homebrew or policy:

```bash
scripts/dev/with-nils-version.sh release:v1.24.3 -- agent-runtime --version
scripts/dev/with-nils-version.sh release:v1.25.5 -- bash scripts/ci/all.sh
```

An older release below minimum is expected to stop at Position 1. Run a
specific historical command or focused fixture when reproducing an old bug;
do not weaken the current policy to make that historical run green.

## Workflow B — Coupled development against unreleased nils-cli

Keep nils-cli work in its own checkout, then scope the full debug surface onto
`PATH`:

```bash
scripts/dev/with-nils-version.sh local -- agent-runtime render --product codex
scripts/dev/with-nils-version.sh src:my-feature-branch -- bash tests/hooks/run.sh
scripts/dev/with-nils-version.sh path:/abs/path/to/target/debug -- \
  agent-runtime audit-drift
```

If the unreleased binary is above validated, Position 1 warns and continues.
That is intentional: the content gates determine whether consumers still work.
Do not call that surface validated, change release digests, or commit generated
snapshots as the formal validated baseline before a stable release exists.

## Workflow C — Adopt a stable release

Adopt a stable tag only when the current request explicitly authorizes adoption. `check` (the default) and `report` verify policy
and mirrors without moving either role. An installed newer release is not
adoption authority. Adoption of the greatest stable tag is allowed when the
request authorizes that selection. The procedure below is guided; it adds no
new CLI command or automatic policy writer.

### Contract

Prereqs:

- Run from the `agent-runtime-kit` repository root in a managed worktree.
- The target is a published stable `sympoies/nils-cli` release with accessible
  source comparison, assets, and SHA256 metadata.
- `docs/source/nils-cli-pin.yaml` is schema v2 and its
  `minimum_supported_tag`, `validated_tag`, validated release digests,
  retained `docs/source/nils-cli-minimum-digest.yaml` lane digests, and policy
  mirrors currently agree.
- A host newer than validated is allowed. Its warning is admission evidence,
  not permission to call the host validated or package it implicitly.

Inputs:

- Target stable tag. Default: the greatest strict `vMAJOR.MINOR.PATCH` tag from
  non-draft, non-prerelease GitHub releases; an explicit tag supports stepped
  adoption.
- Current minimum, validated release, and `required_clis[]`.
- Optional explicit compatibility-retirement decision. Without it, minimum is
  immutable during an ordinary bump.

Outputs:

- One governed PR (or dry-run summary) that updates in lock-step:
  - `validated_tag` plus the target release's validated Linux SHA256 values.
  - `docs/source/nils-cli-surface.md`, README, and every supported product's
    harness mirror for the validated role.
  - Dockerfile, `docker/build.sh`, and publish-image inputs, always from
    validated state.
  - Any affected skill bodies, runtime-smoke fixtures, and rendered goldens.
  - Only the `required_clis[]` floors whose consumed contract actually rose.
- The minimum, its retained lane digests, and its mirrors change
  only when the work explicitly retires compatibility and includes
  below-minimum evidence.

Failure modes:

- Target release, comparison, digest, or source-head evidence is unavailable.
- Target behavior fails downstream validation.
- Packaging digest/defaults differ from `validated_tag`.
- A blocking minimum/validated CI lane lacks its manifest-owned archive digest.
- A retired surface remains referenced without a migration.
- An ordinary bump attempts to move minimum automatically.
- A partial/non-lock-step release is treated as uniform without checking each
  consumed binary and `required_clis[]` floor.

### Entrypoint

Read policy and ambient admission:

```bash
agent-runtime doctor --class version-alignment \
  --pin docs/source/nils-cli-pin.yaml --format text
gh api --paginate 'repos/sympoies/nils-cli/releases?per_page=100'
```

Resolve current validated and compare it with the target:

```bash
current="$(awk -F'"' '/validated_tag:/ {print $2; exit}' \
  docs/source/nils-cli-pin.yaml)"
target="<target-stable-tag>"
gh api "repos/sympoies/nils-cli/compare/${current}...${target}" \
  --jq '.files[].filename' | sort -u
```

Run the target without mutating Homebrew:

```bash
NILS_RELEASE_SHA256="<target-platform-archive-sha256>" \
  scripts/dev/with-nils-version.sh "release:${target}" -- bash scripts/ci/all.sh
```

### Workflow

1. Resolve target, current minimum, and current validated. If target already
   equals validated, digests/mirrors agree, and gates pass, stop.
2. Verify the stable release URL, source head, asset names, and tarball SHA256
   values. Never infer digests from an ambient installation.
3. Compare current validated to target. Map touched crates to produced binaries
   through the surface snapshot, then inspect release notes and changed APIs,
   flags, and JSON envelopes consumed by this repository.
4. Search `core/skills/**/*.tera`, `tests/runtime-smoke/**`, `tests/golden/**`,
   workflows, Docker, and docs for each touched surface. Classify every hit as
   unchanged or requiring migration.
5. Run focused and full downstream behavior under the target release through
   `scripts/dev/with-nils-version.sh`. An above-validated warning must continue
   to downstream gates.
6. Set `validated_tag` to target and replace validated release digests. Raise
   only genuinely required `required_clis[]` floors. Leave minimum and its
   retained lane digests unchanged unless an explicit retirement is part of
   this PR.
7. If minimum moves, state the incompatibility, replace the retained minimum
   lane digests, add below-minimum coverage, and prove the new exact minimum.
   Never derive minimum from validated merely because the versions happen to
   be equal.
8. Refresh surface/README/harness mirrors, Docker/publish inputs, affected
   consumers, and every supported product's renders/goldens.
9. Prove exact minimum and exact validated CI roles. Equal tags may share one
   physical job only when output preserves both role labels. Confirm the
   scheduled/manual newest-stable canary remains advisory, rejects stale or
   semver-suffixed selections, and stays policy-free.
10. Run the canonical `bash scripts/ci/all.sh` gate, then deliver one
    PR through `pr:deliver-pr` / `forge-cli`, never raw `gh pr create`.

### Boundary

The adopt procedure owns validated-release adoption, compatibility-retirement
judgement, consumer refresh, and the single-PR handoff. It does not publish
nils-cli, auto-move minimum, or infer packaging from the ambient host. Released
`agent-runtime doctor` owns host-policy ordering and diagnostics. The CI matrix
owns only the pre-download remote-canary bootstrap exception: canonical u64
stable-tag filtering and candidate ordering, covered by focused regressions;
the GitHub compare/release APIs own upstream facts.

## Workflow D — Retire the compatibility floor

Moving minimum is a compatibility decision, not routine housekeeping:

1. State why the older release can no longer execute the repository contract.
2. Add or update a below-minimum fixture and preserve exact-old evidence where
   practical.
3. Move `minimum_supported_tag` and
   `docs/source/nils-cli-minimum-digest.yaml` explicitly; do not infer either
   from validated.
4. Prove exact minimum and exact validated CI roles (or their equal-tag
   de-duplicated representation) and document the retirement.

The schema-v1 to schema-v2 migration is such a retirement: releases before
`v1.25.0` cannot parse the new manifest, so the initial minimum is `v1.25.0`.

## Helper reference

```text
scripts/dev/with-nils-version.sh <spec> [-- <command> [args...]]

release:<tag>   Download a stable release surface.
<tag>           Shorthand for release:<tag> when it looks like vX.Y.Z.
src:<ref>       Build the whole workspace in a detached worktree.
local           Use the nils-cli checkout's debug build.
path:<dir>      Use an existing full binary directory.
```

Environment overrides:

- `NILS_CLI_REPO` — nils-cli checkout for `src:` / `local`.
- `NILS_REPO_SLUG` — release repository (default `sympoies/nils-cli`).
- `NILS_RELEASE_ASSET_PATTERN` — explicit release asset glob.
- `NILS_RELEASE_SHA256` — expected release archive SHA256. Blocking CI sets it
  from the role-specific manifest digest; the helper verifies the cached or
  downloaded archive, re-extracts verified bytes, and removes provider tokens
  before executing the release surface.
- `NILS_BUILD_ARGS` — additional Cargo build arguments.

Release surfaces are cached below
`${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/out/nils-versions/`.
Removing one tag directory forces a fresh download; no helper mode mutates the
Homebrew installation or version policy.

## Out of scope

- Ambient-version Docker builds or checksum inference.
- Automatically moving minimum whenever validated advances.
- Treating a canary or ahead-host pass as formal validated state.
- A gate bypass for below-minimum or required-CLI failures.
