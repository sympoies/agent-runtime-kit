# The fast local loop omits checks the authoritative gate runs, so "green locally" is not a prediction

## Status

- Status: open
- First observed: 2026-09-05
- Area: validation-design
- Severity: medium

## Signal

Two repositories in the same delivery gave a green local result for a change their own CI then
rejected, or gave a red local result for a change that was fine. In both cases the local command is
the one the repository documents as the development loop, and the divergence is only discoverable
after a push.

This is not the same failure as `gate-derived-from-what-it-guards`. There the gate could not fail
for the reason it existed. Here the gate is correct and simply is not in the loop the developer
runs, so its verdict arrives minutes-to-hours later, attached to a different context.

## Evidence

- Raw record: `evidence/loop-divergence.md`

**1. `--local-fast` omits the completion-freshness audit (sympoies/nils-cli).**
`AGENTS.md` names `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast` as the "default local
development and pre-PR check". Adding a conditional-requirement note to four clap flag doc comments
changed `--help` output, which the committed zsh completion asset mirrors. `--local-fast` passed
(1415 + 262 tests, exit 0). CI `test` and `test_macos` then failed on
`FAIL: review-specialists: stale zsh completion asset`. The audit lives in the full entrypoint, not
in `--local-fast`, and the repository's own guidance says to run the full parity checks "only when
debugging CI" — which is precisely when it is too late.

**2. `ci/all.sh` position 8 requires a clean tree (sympoies/agent-runtime-kit).**
`runtime-smoke --mode convergence` refuses to run with uncommitted changes
(`portable source must be clean; commit or stash reviewed changes`). Every first run of a change
therefore fails at position 8 with a message about tree state rather than about the change. The
correct response is to commit and re-run, but the signal is indistinguishable from a real failure
until read carefully. This cost a full re-run on three separate deliveries in one session.

## Impact

The loop stops predicting the gate. An author reasonably reports "local checks pass" and is wrong,
which is worse than having no local check at all: the false green is stated to reviewers and to the
user as evidence. In this session it produced exactly that — a delivery was reported as locally
validated, and CI then failed on an audit the local command never ran.

The second instance costs less but trains the wrong reflex: a red result that is usually noise
invites skimming the position-8 output rather than reading it.

## Current Workaround

Know which authoritative checks the fast loop excludes, and run them by hand when the change
touches their inputs. Concretely, for this pair:

- Any change to clap flag doc comments, `--help` text, or subcommand structure needs the full
  entrypoint (or at minimum `scripts/ci/completion-freshness-audit.sh`), because `--local-fast`
  will not catch a stale completion asset.
- Commit before expecting `ci/all.sh` to pass end to end; a first-run position-8 failure that names
  tree state is not a finding.

Neither is discoverable from the loop's own output. Both are learned by having been burned.

## Recurrence Shape

The pattern is a fast loop defined by *speed* rather than by *coverage of the authoritative gate*.
It recurs wherever:

- a `--fast` / `--quick` / `--changed-only` mode omits an audit that CI runs unconditionally;
- a check requires committed state, so it cannot run in the edit-test cycle at all;
- a generated asset (completions, snapshots, lockfiles, rendered docs) is verified only in the slow
  lane while its source is edited in the fast one.

## Suggested Practice

Two habits, in order of value:

- **State the delta, not just the result.** "Local checks pass" should be "`--local-fast` passes; it
  does not run the completion audit, which this change touches." That converts an unstated gap into
  a decision the reader can price — the same discipline `inference-reported-as-verified-fact` asks
  for around evidence.
- **Route by what the change touches.** Before reporting green, ask which generated artifacts the
  diff can invalidate, and whether the loop that just ran verifies them.

The durable fix belongs upstream and is not filed here as a defect, because the trade-off is real:
these fast modes exist to stay fast. The useful upstream change would be for the fast mode to *name*
what it skipped, so the omission is visible at the point of use rather than recalled.

## Promotion Criteria

Promote when a delivery in either repository reports local validation with an explicit statement of
what the fast loop did not cover, or when a fast mode emits its own skip list. Retire if two
consecutive multi-repository deliveries produce no CI failure that the documented local loop
structurally could not have caught.

## Next Action

Retain and observe. Both instances are understood and neither is a defect in the checks themselves:
the completion audit and the clean-tree requirement are both correct. The signal to watch is
whether local-validation claims in this session's style start carrying their own coverage caveat.

## Links

- Observed while delivering sympoies/nils-cli#1613 and sympoies/agent-runtime-kit#96, #99, #101.
- Related: `gate-derived-from-what-it-guards` — a gate that cannot fail, versus this one, a correct
  gate that is not in the loop.
- Related: `inference-reported-as-verified-fact` — the reporting half of the same problem.
