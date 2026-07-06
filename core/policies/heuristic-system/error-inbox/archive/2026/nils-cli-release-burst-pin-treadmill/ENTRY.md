# nils-cli release burst outpaces the exact version-alignment pin, blocking delivery mid-flight

## Status

- Status: promoted
- First observed: 2026-07-01
- Area: nils-cli pin / version-alignment gate; PR delivery; sync-runtime-surfaces
- Severity: medium

## Signal

During a same-day nils-cli release burst, the host `agent-runtime` and CI both
auto-upgrade to the latest release while the repo pin
(`docs/source/nils-cli-pin.yaml`) lags. The `scripts/ci/all.sh` Position 2
`version-alignment` gate is EXACT (blocks ahead OR behind, sympoies/nils-cli#636),
so it fails closed on every push and every CI run until the pin is bumped to
match. This blocked a feature PR from both sides at once: the local pre-push
`ci-gate-stack` refused (host ahead of pin) and remote CI failed Position 2 (CI
`brew install`s latest > pin). Worse, a single `meta:nils-cli-bump` can be stale
minutes later — pinning `v1.20.5` (#493) was outdated by `v1.20.6` before the
feature PR's CI finished, forcing a second bump (#494): a catch-up treadmill.

## Evidence

- Raw record: `evidence/session-2026-07-01.md` (redacted session evidence; manual diagnosis 2026-07-01, no skill-usage record captured)
- Session 2026-07-01: to land `graysurf/agent-runtime-kit#492`, the pin was
  bumped `v1.20.1`->`v1.20.5` (#493) then `v1.20.5`->`v1.20.6` (#494) as releases
  kept shipping mid-delivery.
- Release cadence that day: nils-cli `v1.20.2` (06-30 21:23) -> `v1.20.3`
  (03:12) -> `v1.20.4` (06:56) -> `v1.20.5` (08:16) -> `v1.20.6` (09:14), all in
  the session window.

## Impact

During a nils-cli release burst, delivery of unrelated feature/chore PRs is
blocked repo-wide until the pin catches up. Each catch-up is a full
`meta:nils-cli-bump` PR plus a rebase of the in-flight PR, and can loop while
releases continue.

## Current Workaround

- Push in-flight branches under the pinned binary so the pre-push gate runs
  on-pin, not on the drifted host:
  `scripts/dev/with-nils-version.sh release:<pin> -- git push ...`. This
  validates against the pin (legitimate, not a bypass — goldens are also
  rendered on-pin), and incidentally runs the full `scripts/ci/all.sh` on-pin.
- Catch the pin up to whatever CI installs (latest) via `meta:nils-cli-bump`;
  repeat if a new release lands before the in-flight PR's CI finishes.
- When the burst is active, prefer waiting for it to settle before delivering
  unrelated PRs, then do a single pin catch-up.

## Promotion Criteria

Promote when a structural fix lands: make CI install the PINNED nils-cli version
(from `nils-cli-pin.yaml`) instead of `brew install`ing latest, so remote CI is
deterministic regardless of new releases and only a conscious pin bump — not
every upstream release — gates delivery. Local host drift would remain but is
covered by the on-pin push wrapper above.

## Next Action

None. GitHub Actions CI now resolves docs/source/nils-cli-pin.yaml and runs scripts/ci/all.sh through scripts/dev/with-nils-version.sh release:<pin>, so remote CI validates against the pinned nils-cli surface instead of Homebrew latest during release bursts.

Lifecycle link: `.github/workflows/ci.yml`

## Archive

- Archived: 2026-07-06
- Reason: CI now runs on the pinned nils-cli release
- Durable link: `.github/workflows/ci.yml`
