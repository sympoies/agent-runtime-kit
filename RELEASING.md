# Releasing

`agent-runtime-kit` ships one published artifact: the standalone Linux container
image (see `docker/`) published to the GitHub Container Registry (GHCR) at
`ghcr.io/sympoies/agent-runtime-kit`. This document defines how versions are
named and how a release is cut.

## Versioning — CalVer

Releases use **CalVer**: a date-stamped tag `vYYYY.MM.DD` (zero-padded), e.g.
`v2026.05.30`. The image is a *snapshot of the runtime surface as of that date*.
The kit is a continuously-evolving config / skills / hooks / docs layer with no
API-compatibility contract, so a dated snapshot is the honest version unit.

- One release per day is the norm. If a second release is genuinely needed the
  same day, re-run the published release's workflow (it rebuilds the same tag)
  or cut the next day's date.
- The bundled `nils-cli` version is **independent** of the CalVer tag: the image
  always builds against `docs/source/nils-cli-pin.yaml` (the repo's pin gate).
  The CalVer tag versions the kit snapshot, not its `nils-cli` dependency.

## Published image tags

Each release publishes, for `linux/amd64` and `linux/arm64`:

| Tag | Example |
| --- | --- |
| Dated | `ghcr.io/sympoies/agent-runtime-kit:2026.05.30` |
| Rolling | `ghcr.io/sympoies/agent-runtime-kit:latest` (non-prerelease only) |

## Cutting a release

1. Make sure `main` is in the state you want to ship. The release script
   refuses to publish from a dirty tree, from a non-`main` branch, or from a
   local `main` that differs from `origin/main`.
2. Preview the release:

   ```bash
   scripts/release.sh --dry-run
   ```

3. Cut the GitHub Release, wait for the publish workflow, and verify the public
   GHCR manifests:

   ```bash
   scripts/release.sh --execute
   ```

   Use `--version YYYY.MM.DD` to cut an explicit CalVer tag, or `--prerelease`
   to skip the rolling `latest` tag.
4. `.github/workflows/publish-image.yml` runs on `release: published`:
   - resolves the `nils-cli` pin from `docs/source/nils-cli-pin.yaml`,
   - builds `linux/amd64` and smoke-tests it (`claude` / `codex` /
     `agent-runtime` versions and the rendered-home symlinks),
   - builds multi-arch and pushes to GHCR with the dated tag plus `latest`,
   - emits BuildKit provenance/SBOM attestations and a GitHub provenance
     attestation for the pushed image digest,
   - verifies that the pushed GHCR manifests are anonymously readable and carry
     both `linux/amd64` and `linux/arm64`.

The project-local `$release` dispatcher is wired to the same script:

```bash
agent-run exec --cwd "$PWD" -- ./.agents/scripts/release.sh --dry-run
agent-run exec --cwd "$PWD" -- ./.agents/scripts/release.sh --execute
```

To verify an already-published image without creating a release:

```bash
scripts/release.sh --verify-only --version v2026.05.30
```

## Pulling the image

```bash
docker pull ghcr.io/sympoies/agent-runtime-kit:latest
docker run --rm -it ghcr.io/sympoies/agent-runtime-kit:latest
```

For a dated release, inspect the immutable digest and verify the provenance
attestation before running it:

```bash
docker buildx imagetools inspect ghcr.io/sympoies/agent-runtime-kit:2026.05.30
gh attestation verify \
  oci://ghcr.io/sympoies/agent-runtime-kit:2026.05.30 \
  -R sympoies/agent-runtime-kit
```
