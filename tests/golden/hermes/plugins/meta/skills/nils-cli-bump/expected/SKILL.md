---
name: nils-cli-bump
description: >
  Propose one PR that advances the validated nils-cli release and refreshes
  every consumer; move the compatibility minimum only for an explicit
  retirement, while preserving exact packaging and CI evidence.
---

# nils-cli Bump

## Contract

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
- Current `minimum_supported_tag`, `validated_tag`, and `required_clis[]`.
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
- `minimum_supported_tag`, its retained lane digests, and its mirrors change
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

## Entrypoint

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

## Workflow

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
10. Run `bash scripts/ci/all.sh` and `bash tests/hooks/run.sh`, then deliver one
    PR through `pr:deliver-pr` / `forge-cli`, never raw `gh pr create`.

## Boundary

This skill owns validated-release adoption, compatibility-retirement
judgement, consumer refresh, and the single-PR handoff. It does not publish
nils-cli, auto-move minimum, or infer packaging from the ambient host. Released
`agent-runtime doctor` owns host-policy ordering and diagnostics. The CI matrix
owns only the pre-download remote-canary bootstrap exception: canonical u64
stable-tag filtering and candidate ordering, covered by focused regressions;
the GitHub compare/release APIs own upstream facts.

## Related Skills

- `project-version-baseline` verifies both role mirrors without mutating them.
- `pr:deliver-pr` delivers the governed bump PR.
- `meta:sync-runtime-surfaces` applies merged rendered surfaces only when live
  activation is separately authorized.
