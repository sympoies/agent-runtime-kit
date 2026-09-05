# A gate whose expectation comes from the thing it guards proves nothing, and reads as passing

## Status

- Status: open
- First observed: 2026-09-05
- Area: validation-design
- Severity: high

## Signal

Two gates in the same delivery were structurally incapable of failing for the reason they existed,
and both looked green. Neither was a coding mistake. Both were the same design error: the gate
derived its expected value from the artifact it was supposed to constrain, or accepted evidence
that the change itself supplied.

This matters more than an ordinary missing test. A test that does not exist is visibly absent. A
gate that cannot fail is *worse than absent*, because it is counted as coverage — by CI, by the
author, and by the next reader deciding whether the invariant is protected.

## Evidence

- Raw record: `evidence/mutation-evidence.md`

Both instances are from sympoies/agent-runtime-kit#96, and both were found by review, not by the
author. The raw record above holds the exact mutation, the command, and the observed pass/fail for
each gate.

**1. The golden gate cannot detect removal from its own source.**
`scripts/ci/all.sh` position 6 runs `agent-runtime render --product claude --update-golden` and
*then* `git diff --exit-code -- tests/golden/`. The goldens are regenerated from the templates
immediately before being compared. So a template that drops a field regenerates a golden that
matches, and the gate is green. This is exactly how the eight Claude reviewer subagents went
without a `model` pin for as long as they did, while the Codex branch — guarded separately by
`codex_reviewer_profile_errors` in `scripts/ci/skill-governance-audit.sh` — kept its pins.

The maintainability lens stated it; the red-team lens verified it against `ci/all.sh` directly.
The author's own PR had proposed the golden refresh *as the proof* that the new pin could not
regress.

**2. A new probe was satisfied by prose the same commit added.**
`code-review.outcome-routing.provider-review-metadata` asserted that five CLI flags appear in the
files owning the canonical command, using whole-file `grep`. The same commit added, to those same
files, a sentence naming all five flags ("`--reviewable`, `--lens`, `--lens-verdict`, `--scope`,
and `--evidence-reviewed` are not optional for this profile"). Every assertion was satisfied by
that sentence. Mutation confirmed it: deleting `--reviewable` from the posting contract's fenced
command block while leaving the prose intact kept the probe green.

The probe was written specifically to prevent a placeholder header from being published again. It
could not have caught the original defect.

## Impact

Both gates were reported to the user as protection. The first was offered as the reason the model
pin was safe; the second as the regression guard for the whole delivery. Had review not caught
them, the delivery would have shipped a repair for a detection gap while reproducing that same
detection gap in the new guard — and the next occurrence would have been harder to diagnose,
because a green gate is evidence *against* the hypothesis that the invariant broke.

## Recurrence Shape

The pattern is not specific to goldens or to grep. It appears wherever the expected value and the
actual value share an upstream:

- snapshot/approval tests refreshed in the same step that compares them;
- schema or fixture checks regenerated from the code under test;
- lint-by-grep over a file that also documents the thing being grepped for;
- a contract test whose fixture is produced by the component it verifies;
- any assertion satisfiable by a comment, a docstring, or documentation added by the same change.

## Current Workaround

There is no tool that detects this shape, so it is caught by hand or by review. What worked here
was a mutation run against each new gate before trusting it: break the invariant at its real
source, leave everything else intact, and confirm the gate goes red. Both instances were settled
that way in under a minute.

Until something enforces it, the practical workaround is to treat "the gate is green" as
unevidenced for a *newly added or changed* gate, and to record the observed red alongside the
observed green — the same discipline `test-first-evidence` already applies to production changes,
applied to the guard itself.

## Suggested Practice

The check is mechanical and takes one question, asked *before* the gate is trusted:

> If I break the invariant right now — at its real source, leaving everything else intact — does
> this gate go red?

Run it as a mutation, not as a thought experiment. Both instances above were settled in under a
minute that way, and in both the intuition had said "yes, it is covered".

Two structural habits follow:

- **Never let the comparison refresh its own baseline.** If a gate regenerates the expected value,
  it is a drift detector between source and render, not an invariant guard. Both may be wanted;
  they are not the same gate and should not be described interchangeably.
- **Scope textual assertions to the construct, not the file.** The repaired probe extracts the
  fenced block containing the command and asserts against that alone; whole-file greps remain only
  for prose owners, where prose is genuinely the thing being pinned.

## Promotion Criteria

Promote when a delivery in this repository adds or changes a gate and the mutation question above
is answered in the record — a stated red observation for the new gate, not an assertion that it
would fail. Retire if two consecutive multi-round deliveries produce no reviewer finding of this
shape.

## Next Action

Retain and observe. Both instances are repaired in
sympoies/agent-runtime-kit#96; no upstream tool defect is implied, because the gates were doing
exactly what they were written to do. The signal to watch is whether new gates arrive with a
recorded red, or only with a green.

Worth a separate look, not yet filed: the golden-regeneration property is a repository-wide
characteristic of `ci/all.sh` position 6, not a one-off. Every surface whose only guard is a
regenerated golden has the same hole. The Claude reviewer pins now have a fail-closed audit; no
survey has been done of what else relies on goldens alone.

## Links

- Observed while delivering sympoies/agent-runtime-kit#96.
- Repairs: block-scoped probe assertions and `claude_pin_missing_rejected` /
  `claude_pin_drift_rejected` in the reviewer-profile fixture.
- Related: `inference-reported-as-verified-fact` — the same delivery offered the golden refresh as
  proof without running the mutation that would have tested it.
