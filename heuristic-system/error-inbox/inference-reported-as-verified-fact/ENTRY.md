# Inference is reported to the user with the confidence of an executed check

## Status

- Status: open
- First observed: 2026-09-02
- Area: agent-behavior
- Severity: medium

## Signal

While delivering sympoies/agent-runtime-kit#90/#91/#94, three separate claims were stated to the
user or written into the repository as established fact when they were actually inferences from
reading code. Reviewers caught all three. In every case the *conclusion* survived scrutiny and the
*reasoning offered for it* did not.

The failure is not being wrong. It is that nothing in the phrasing distinguished "I read this and
concluded X" from "I ran this and observed X", so the user had no way to price the claim.

## Evidence

Two instances with exact text retained:

1. **`normpath` was defensible.** The user was told twice that resolving candidate paths with
   `os.path.normpath` rather than a physical resolution was an accepted trade-off, with a security
   rationale attached. A bot reviewer blocked the merge over it and was right. The decisive case
   was not adversarial at all: a physical/logical path mismatch silently disabled `.cache`
   enforcement. The repair added a physical resolution. The trade-off had been asserted, never
   tested against the non-adversarial case.

2. **A MultiEdit assertion inverted on a false premise.** A test docstring justified flipping
   `assertNotIn` to `assertIn` by claiming the portable-paths half is a no-op on MultiEdit because
   `proposed_content` returns `""`. `hook_contents_to_scan` has a second content source:
   `patch_text_candidates` recurses into `edits[]`, so embedded apply-patch text does raise a hit.
   Direct invocation confirmed both directions in under a minute - the check was available the
   whole time and simply was not run. The inversion itself was correct on the merits.

A third instance in the same session concerned `agent-hook setup`'s legacy-residue detection
(`legacy_command` in `setup.rs`). Its exact wording was not retained, so it is recorded here as a
count, not as a quotable case.

Adjacent to the same pattern, and the reason the severity is not low: the dispatch-budget outage
was diagnosed incorrectly twice before being settled by controlled experiment. Both wrong
diagnoses were reasoned from a local `nils-cli` checkout at `e21b149c` while the deployed binary
was 1.27.36. The source of truth was assumed rather than checked.

## Impact

The user cannot calibrate. A claim that was reasoned and a claim that was executed read identically,
so either everything gets re-verified downstream - which defeats the point of delegating - or an
unverified claim gets built on. Here that cost two review rounds on a fix that was itself repairing
an outage, and put a false justification into a committed test docstring, where it would have
misled the next reader long after the session ended.

It is worse in exactly the situations where it is most likely: under time pressure after a
self-inflicted breakage, when reaching for a conclusion is fastest and running the check feels like
a detour.

## Current Workaround

Two habits, in order of cost:

- Before asserting behavior of code under change, run it. All three instances were cheap to check;
  the MultiEdit case took one direct invocation. "I read the source" is a hypothesis, not evidence.
- When a check was not run, mark the claim as inference in the sentence that makes it. Reviewers
  and the user can then decide whether to spend the verification. Silent inference removes that
  choice from them.

Specifically for docstrings and comments that justify a test assertion: the justification must
describe an observation that was made, because the assertion outlives the session and the reader
has no way to re-derive whether it was checked.

## Promotion Criteria

Promote when a session completes work of comparable scope with no reviewer finding of the form
"the conclusion holds but the stated reason is unverified", or when a durable practice exists that
makes the inference/observation distinction visible by default rather than by recall.

## Next Action

Retain and observe. This is a behavioral pattern, not a tool defect, so there is no upstream fix to
file. Re-check on the next multi-round delivery in this repository: the signal to watch is whether
justifications offered in review responses and in committed comments name something that ran.

## Links

- Observed while delivering sympoies/agent-runtime-kit#90, #91, #94.
- Related: `semantic-commit-body-error-mislabel` was filed in the same session; that one is a
  genuine tool defect and is not an instance of this pattern.
