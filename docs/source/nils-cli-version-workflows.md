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
`scripts/dev/with-nils-version.sh`. The `meta:nils-cli-bump` skill owns policy
movement and mirror refresh.

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
`plan-issue`, `plan-tooling`, `forge-cli`, `agent-docs`, and the remaining
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

This is owned by `meta:nils-cli-bump`:

1. Verify the stable release, source head, assets, and SHA256 sidecars.
2. Run affected behavior against the target release.
3. Move `validated_tag`, validated release digests, Docker defaults, surface
   snapshots, and policy mirrors together. Preserve the retained minimum-lane
   digest manifest.
4. Leave `minimum_supported_tag` unchanged unless the change explicitly
   retires older compatibility. If minimum and validated are equal, CI keeps
   both role labels while de-duplicating the physical run.
5. Render Codex, Claude, and Hermes outputs; run the full repository gate; then
   deliver the governed PR.

Installing the release on a host and adopting it as validated are separate
facts. An ahead ambient host may work before the validated role moves.

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
