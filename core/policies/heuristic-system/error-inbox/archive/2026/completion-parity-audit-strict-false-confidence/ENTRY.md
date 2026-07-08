# Completion parity audit run without --strict gives false pre-release confidence

## Status

- Status: promoted
- First observed: 2026-06-16
- Area: nils-cli release / completion audit
- Severity: medium

## Signal

Releasing the new `forge-cli pr review-threads list/resolve/reply` subcommand
group (nils-cli, on the way to `v1.9.0`), the local pre-release run of
`completion-flag-parity-audit.sh` passed — but it was run **without** `--strict`.
`release.yml` runs the same audit **with** `--strict` and failed on the tag: the
new subcommands had missing zsh completion blocks. The local check's green was
false confidence; the tag was created and `release.yml` went red with no
published release.

Root cause of the underlying parity miss: the initial clap shape used an
optional bare positional plus `args_conflicts_with_subcommands`, which shifts
the zsh subcommand context to `$line[2]`, while `completion-flag-parity-audit.sh`
hardcodes `$line[1]` in its `zsh_context_marker`. Under `--strict` that surfaces
as missing per-subcommand blocks; without `--strict` it is tolerated.

## Evidence

- Raw record: `evidence/parity-audit-strict-evidence.md` (redacted, ingested
  2026-06-16)
- nils-cli version at failure: `1.9.0` (tag created, `release.yml` red, never
  published). Re-released cleanly as `v1.9.1` after the fix.
- Fix: `sympoies/nils-cli#885` — switch to a clean `review-threads` subcommand
  group (drop the bare `<id>` back-compat positional), so the zsh context stays
  on `$line[1]` and `--strict` parity passes.
- Workaround source: the implementation agent ran the parity audit without
  `--strict`, so the local pass did not match what `release.yml` enforces.

## Impact

A failed release cycle: a dangling tag, a red `release.yml`, and the cost of
diagnosing from CI logs, landing a fix PR, deleting the tag, and re-releasing.
Any future agent adding or reshaping a CLI subcommand can repeat this whenever
the local parity check is run without `--strict`.

## Current Workaround

Before tagging a release, run `bash scripts/ci/completion-flag-parity-audit.sh
--strict` locally (matching `release.yml`), not the bare invocation. When adding
or changing a CLI subcommand, prefer a clean subcommand group over an optional
bare positional + `args_conflicts_with_subcommands` (which shifts the zsh
completion context off `$line[1]` and trips the `--strict` audit).

## Promotion Criteria

Promote when the local check is made to match CI by default — e.g. the release
pre-flight / `cli-completion-development-standard` / release skill invokes the
parity audit with `--strict`, or the audit's `zsh_context_marker` is taught to
handle the shifted-context subcommand shape — so a missing-block regression
fails locally before the tag, not in `release.yml`.

## Next Action

None. Resolved: the completion parity audit is now always strict (--strict is a no-op; pre-pr, release-bump --full-checks, and DEVELOPMENT.md all route through the strict path), so a local run can no longer diverge from CI. Original trigger fixed by sympoies/nils-cli#885 (re-released v1.9.1). Verified in nils-cli source at v1.20.18.

## Archive

- Archived: 2026-07-08
- Reason: Completed entry archived out of the active error inbox.
- Durable link: `sympoies/nils-cli#885`
