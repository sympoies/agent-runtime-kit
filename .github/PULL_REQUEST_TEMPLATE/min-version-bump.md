<!--
Use this template ONLY for PRs that bump `min_version`, `recommended_version`,
or `min_version_effective_from` in `manifests/runtime-roots.yaml`. Pure
follow-ups (changelog, docs around an existing bump) can use the default
template.

This template is a reminder, not a required CI check. It is loud-by-design
so reviewers can see at a glance whether the Bump Ceremony was followed.

The version fields live in `manifests/runtime-roots.yaml`; the
`version-alignment` gate that enforces them is in `DEVELOPMENT.md`
(`## Validation`). The ceremony, captured by the sections below, is:
latest-stable floor with no rolling support window — keep a
`recommended_version` runway ahead of `min_version`, forward-pin
`min_version_effective_from`, surface the upgrade path via
`agent-runtime doctor --suggest-upgrade`, and fill in this template.
-->

## Acceptance and verification

<!-- Before implementation, list each observable criterion and the command,
test, or check that will verify it. -->

## Product version bump summary

- Product: `codex` / `claude` (pick one)
- Field changed: `min_version` / `recommended_version` /
  `min_version_effective_from` (pick all that apply)
- Old value → new value:
- Reason for the bump (feature dependency, security fix, EOL, etc.):

## Impacted Environments

List every host class this bump affects. Use the table; add rows as needed.

| Environment | Current product version | Action needed |
| --- | --- | --- |
| Local dev (macOS, Homebrew) | | `brew upgrade …` |
| Local dev (Linux, Linuxbrew) | | `brew upgrade …` |
| CI runner (GitHub Actions / matrix) | | `setup.sh --upgrade-products` |
| Remote dev box | | |
| Corp sandbox | | |

If an environment lags behind the new `min_version` floor with no upgrade
path before `min_version_effective_from`, **either delay the
effective-from date or call out the impact explicitly** (the runway is
the lever, not the floor).

## Tested Version Combinations

Tick each combination this PR has been exercised against. Untested
combinations are not necessarily blockers, but reviewers should know
which gaps exist.

- [ ] Old `min_version` host running old skill bodies (pre-bump baseline)
- [ ] New `min_version` host running new skill bodies (post-bump target)
- [ ] Old `min_version` host running new skill bodies (runway scenario)
- [ ] CI matrix updated to install / pin the new version

## Suggest-upgrade output

Paste the relevant portion of `agent-runtime doctor --suggest-upgrade`
so a copy-paste upgrade path is visible in the PR description:

```text
$ agent-runtime doctor --suggest-upgrade
…
```

## Rollback Path

- Revert commit: <link or note>
- Tap formula pin to revert to: `sympoies/tap/nils-cli@<previous>` (if
  this bump rides on a nils-cli release)
- Forward-pin extension: bump `min_version_effective_from` further out
  instead of reverting, if the bump itself is sound but the host
  upgrade timeline slipped

## Team Notice Timestamp

24–48 h advance notification posted in:

- Channel:
- Timestamp:
- Link / message ID:

If notice was skipped (e.g. emergency security bump), explain why here.
