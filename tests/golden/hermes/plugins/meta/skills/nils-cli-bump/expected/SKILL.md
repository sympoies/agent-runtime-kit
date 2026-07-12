---
name: nils-cli-bump
description: >
  Propose one PR that bumps the pinned nils-cli surface and refreshes every
  consumer when a new nils-cli release ships; owns the surface-refresh
  judgement over the mechanical version-alignment diff.
---

# nils-cli Bump

## Contract

Prereqs:

- Run from the `agent-runtime-kit` repository root.
- `agent-runtime` is installed from the released nils-cli package and on
  `PATH`. The bump targets the tag the host is actually on, so the host must
  already be upgraded to the target release (`brew upgrade
  sympoies/tap/nils-cli`) before the pin can be moved — the
  `version-alignment` gate is exact, ahead **or** behind.
- `gh` is authenticated for `sympoies/nils-cli` (read) so the compare API and
  release metadata are reachable.
- The current pin (`docs/source/nils-cli-pin.yaml`) and the human-readable
  snapshot (`docs/source/nils-cli-surface.md`) exist and agree on `pinned_tag`.

Inputs:

- Target tag. Default: the latest published nils-cli release
  (`gh release view --repo sympoies/nils-cli`). Override with an explicit tag
  for a stepped bump.
- The current `pinned_tag` and `required_clis[]` floors from the pin manifest.

Outputs:

- One bump PR (or a dry-run summary) that updates, in lock-step:
  - `docs/source/nils-cli-pin.yaml` — `pinned_tag` and any `required_clis[]`
    floor that a newly-consumed surface raised.
  - `docs/source/nils-cli-surface.md` — header pointers (snapshot date, tag,
    head commit, release link, and the `pinned_tag:` prose cue), new / changed
    crate rows, and the consumed-surface notes for any binary whose surface
    moved.
  - The `pinned_tag` prose mirrors the Position 14 baseline audit enforces: the
    `pinned snapshot **<tag>**` line in `docs/source/harness-shape-codex.md`
    and `harness-shape-claude.md`, and the `nils-cli` surface row in the
    `README.md` "Version baseline" table.
  - Any SKILL body, runtime-smoke fixture, or golden snapshot that referenced
    a surface the target release retired or renamed, plus the re-rendered
    goldens.
  - The `min_nils_cli` row in `manifests/surfaces.yaml` (and the rendered
    `SUPPORT_MATRIX.md`) only when a consumed product surface's floor moved.

Failure modes:

- The host `agent-runtime --version` is not the target tag, so the post-bump
  `version-alignment` gate cannot pass. Stop and upgrade the host first.
- The compare API is unreachable or the tag is unpublished.
- A retired or renamed surface is still referenced by a consumer and no
  migration is proposed — never bump the pin while leaving a consumer pointed
  at a surface the target release removed.
- The release is a partial / non-lock-step bump: the `pinned_tag` exact match
  still holds against the host, but `required_clis[]` floors must be checked
  per binary rather than assumed uniform.

## Entrypoint

Read current drift and the latest published tag:

```bash
agent-runtime doctor --class version-alignment \
  --pin docs/source/nils-cli-pin.yaml --format text
gh release view --repo sympoies/nils-cli --json tagName,publishedAt
```

Diff the consumed surface between the current pin and the target tag:

```bash
current="$(gh api repos/sympoies/nils-cli/git/refs/tags --jq '.[].ref' >/dev/null 2>&1; \
  grep -E '^\s*pinned_tag:' docs/source/nils-cli-pin.yaml | sed -E 's/.*"(v[0-9.]+)".*/\1/')"
target="<target-tag>"
gh api "repos/sympoies/nils-cli/compare/${current}...${target}" \
  --jq '.files[].filename' | sort -u
```

After moving the pin, confirm the gate is green against the upgraded host:

```bash
agent-runtime doctor --class version-alignment \
  --pin docs/source/nils-cli-pin.yaml --format text   # expect block=0, exit 0
bash scripts/ci/all.sh                                 # Position 2 now aligned
```

## Workflow

1. Resolve the target tag (latest published release, or an explicit stepped
   tag) and read the current `pinned_tag`. If they already match and the gate
   is green, there is nothing to bump — stop.
2. Confirm the host is on the target tag. If `agent-runtime --version` is
   behind, `brew upgrade sympoies/tap/nils-cli` first; the exact gate blocks
   until host and pin agree.
3. Run the GitHub compare API between current and target. Reduce the changed
   files to: which crates changed, which produced binaries those map to (cross
   the **Crate → binary** table in the snapshot), and which downstream-consumed
   flags / JSON envelopes the release notes or diff touched.
4. For each touched binary surface, grep the consumers — `core/skills/**/*.tera`,
   `tests/runtime-smoke/**`, `tests/golden/**`, and the snapshot notes — for the
   retired or renamed flag / envelope. Classify each hit as no-op (surface
   unchanged for that path) or needs-rewrite (surface retired / renamed).
5. Update `docs/source/nils-cli-pin.yaml`: set `pinned_tag` to the target, and
   raise only the `required_clis[]` floors that a newly-required surface moved.
   Do not float every floor to the target — floors record the minimum consumed
   surface, not the current pin.
6. Refresh `docs/source/nils-cli-surface.md`: bump the header pointers
   (including the `pinned_tag:` prose cue and `Active git describe` line), add
   or edit crate rows for added / changed crates, and append the `As of <tag>`
   note to any binary whose consumed surface moved. Then update the remaining
   `pinned_tag` prose mirrors the Position 14 baseline audit enforces: the
   `pinned snapshot **<tag>**` line in `docs/source/harness-shape-codex.md` and
   `harness-shape-claude.md`, and the `nils-cli` surface row in the `README.md`
   "Version baseline" table.
7. Apply every needs-rewrite migration in the consumer it touches, then
   re-render goldens (`agent-runtime render --product codex|claude|hermes
   --update-golden`) and run `scripts/ci/skill-governance-audit.sh`.
8. Run `scripts/ci/all.sh`. Position 2 must now report aligned, and Position 14
   (`version-baseline-audit.py check`) must be green — it fails closed if any
   `pinned_tag` prose mirror still lags. Downstream render / drift /
   runtime-smoke positions catch any consumer the rewrite missed.
9. Deliver one bump PR through the active PR workflow
   (`pr:deliver-pr` / `forge-cli pr`), not raw
   `gh pr create`. Title it as a `chore` (pin + snapshot only) or `feat`
   (consumer surface rewrites included) per the actual diff.

## Boundary

This skill owns when to bump, the surface-refresh judgement (new floors, which
consumers to rewrite, the snapshot edits), and the single-PR delivery handoff.
The mechanical version-number gate is owned by `agent-runtime doctor --class
version-alignment` — do not reimplement the comparison in skill prose. The
inter-tag surface diff is owned by the GitHub compare API. This skill answers
"what does this release change for our consumers, and is the pin safe to move?"
It does not judge the correctness of arbitrary upstream code changes, does not
publish nils-cli releases, and does not move the pin while a consumer still
points at a retired surface. If a future bump needs structured envelope
diffing or reference-graph output, extract that into released `nils-cli` first
and call it from here.

## Related Skills

- The policy-owned semantic commit phase preserves the staged-change boundary.
- `pr:deliver-pr` — open and drive the single bump PR; this skill never
  calls raw `gh pr create`.
- `meta:sync-runtime-surfaces` — after the host upgrade, refresh the live Codex
  and Claude skill surfaces so a local session sees the rewritten bodies.
