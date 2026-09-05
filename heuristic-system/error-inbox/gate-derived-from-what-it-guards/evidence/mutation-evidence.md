# Mutation observations behind this case

Both gates were claimed to protect an invariant. Each mutation breaks that invariant at its real
source and leaves everything else intact.

## Gate 1 — regenerated golden

`scripts/ci/all.sh` position 6:

    agent-runtime render --product claude --update-golden
    git diff --exit-code -- tests/golden/

Mutation: remove `model: opus` from one `core/agents/code-review/reviewer-*/AGENT.md.tera` Claude
branch and refresh goldens the way CI does.

Observed: the regenerated golden matches the mutated template, `git diff` is empty, gate green.
The gate compares source against render, never against a stated expectation, so it detects drift
between the two and nothing else.

Repair: `codex_reviewer_profile_errors` in `scripts/ci/skill-governance-audit.sh` now asserts the
Claude branch sets `model` and `effort`, with fixture cases proving the audit fails closed —
`claude_pin_missing_rejected=true claude_pin_drift_rejected=true`.

## Gate 2 — whole-file grep satisfied by same-commit prose

`code-review.outcome-routing.provider-review-metadata` asserted five flags appear in the two files
owning the canonical command, using whole-file `grep -Fq`.

Mutation: delete `--reviewable "$REVIEWABLE" \` from the fenced bash block in
`REVIEW_OUTCOME_POSTING_CONTRACT.md`, leaving intact the prose line added by the same commit that
names all five flags.

Observed before repair: `total=13 pass=13 fail=0` — green, with the guarded command missing the
flag.
Observed after repair: `total=13 pass=9 fail=4` — the probe fails, as does the golden diff for the
mutated file.

Repair: the probe extracts the fenced block containing `--profile provider-review` and asserts
against that alone; whole-file greps remain only for the three prose owners.

## Why this is one case and not two

The failure is identical in shape. In both, the value the gate compares against is produced by, or
travels with, the thing it constrains. Neither gate could go red for the reason it existed, and
both were counted as coverage in the delivery record before review.
