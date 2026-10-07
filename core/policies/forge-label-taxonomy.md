# Forge Label Taxonomy

`manifests/forge-labels.yaml` is the machine-readable catalog for GitHub
issues / PRs and GitLab issues / MRs. `forge-cli label audit|ensure` consumes
that catalog; this policy defines how agents choose and apply the labels.
`manifests/forge-label-classification-rules.yaml` records the first shared
agent classification heuristics for consistent triage and review.

## Versioned Semantics

The catalog keeps `schema: forge-label-catalog.v1` for existing definition
readers and adds `semantics_schema: forge-label-semantics.v1`. Each label's
`description` gives its meaning; its `semantics` resolves a shared profile
with `allowed_writers`, `readers`, `gate`, and any `removal_rule`. Preserve
existing names, applicability, colors, descriptions, and group membership.
Writer roles constrain authorized automation; metadata does not grant provider
permissions or implement writer access control.

`forge-cli-label-audit-ensure` reads definitions for provider label setup and
drift. `forge-cli-selected-label-validation` checks supplied labels against
catalog definitions, applicability, and exclusive groups. Neither enforces
writer roles, a complete issue/PR label profile, or merge approval. Role readers
such as a coordinator or reviewer use classification for their declared work.
`state::ready` is workflow classification only; provider state remains the
source of truth for open/closed records. `provider::` classifies the scope of
work, rather than identifying the provider hosting the record.

## Merge Controls

The compatibility hold set is `state::do-not-merge`, bare `do-not-merge`, and
`control::hold`. All three mean an explicit PR/MR hold. `control::hold` is
independent of the exclusive `state::` classification; leave the existing
`state::do-not-merge` definition in place for compatibility. A head change,
new review, green checks, or ordinary reclassification does not release a hold.
Only the maintainer or authorized hold owner may remove it after explicit
release of its conditions; classification automation must preserve all holds.

The hold readers are `forge-cli pr merge` and the shared merge path used by
`forge-cli pr deliver`: complete fresh provider reads fail closed before both
direct merge and merge-queue enqueue, naming the matched label and its release
instruction. Repository-base `[merge].hold_labels` and global configuration
can add names without removing the three defaults. Missing, incomplete, or
failed reads must not permit a merge.

The `merge-freeze` label belongs to an open control issue and freezes merging
across the repository. Its reader is the existing repository-freeze path,
also used by PR/MR merge delivery. Closing/releasing that issue or using its
existing reasoned override is separate from releasing a PR/MR hold; a freeze
override does not waive a hold.

Roll out the hold reader before new automated hold writers. The reader change
is [nils-cli #2164](https://github.com/sympoies/nils-cli/pull/2164); this catalog
neither activates a runtime nor advances the validated nils-cli release pin.
Verify that the maintainer's released guard is installed before activating new
hold writers. Existing labels and historical records remain in place.

## Required Selection

- Issues: choose one `type::` label, one primary `area::` label, and a
  `state::` label. Use `state::needs-triage` unless a more specific state is
  known. When re-labeling historical closed records, use `state::closed` unless
  a more specific reopened workflow state is being recorded.
- Bug, incident, or security issues: add one `severity::` label when impact is
  known. Severity describes impact, not scheduling order.
- Triaged issues: add one `priority::` label when scheduling order is known.
  Priority owns ordering; do not add an `urgency::` group in the first rollout.
- PRs and MRs: choose one `type::`, one primary `area::`, and one `size::`
  label before provider mutation.
- Risky PRs and MRs: add one `risk::` label and strengthen the review /
  rollback notes accordingly.
- Provider workflow work: add `provider::github`, `provider::gitlab`,
  `provider::both`, or `provider::neutral` when provider behavior is part of
  the scope.
- Agent-owned durable workflow records: use `workflow::tracking` for program
  tracker issues, `workflow::dispatch` for dispatch lane PRs/MRs, and
  `workflow::follow-up` for ordinary child or investigation issues.

## Provider Operations

- Before the first live issue, PR, or MR mutation in a repository, run:

  ```bash
  forge-cli label ensure --catalog manifests/forge-labels.yaml --repo "$OWNER_REPO" --format json
  ```

- Use `forge-cli label audit --catalog ...` when mutation is not allowed or
  when checking drift after setup.
- `forge-cli label ensure` may create missing labels. It must not delete or
  rename labels during rollout.
- Do not pass `--update-existing` unless the user or owning issue explicitly
  approves color / description drift repair.
- For PR/MR creation and delivery, pass selected labels with repeatable
  `--label` flags. When the catalog is available, add `--label-catalog
  manifests/forge-labels.yaml --strict-labels` so invalid or conflicting
  labels fail before provider mutation.

## Historical Labels

- Preserve labels already attached to historical records, including `plan`
  and `workflow::plan`. The retired plan lifecycle is not a route for new work;
  do not create or apply its labels to new issues.
- Repo-local `area::` extensions are allowed when a repository needs a primary
  area outside the shared catalog. Shared automation should still prefer the
  cataloged core areas when one fits.

## Agent Classification Rules

- Use the classification rules manifest as the default routing aid when
  re-labeling existing provider records.
- Treat rule output as an agent recommendation, not an override of explicit
  issue text or user direction.
- Apply each workflow rule only to its declared artifact kind. A program key
  or mention of a lane is shared context and does not make an issue a tracker.
  Select tracker issues by their title or phase table; select child issues by
  their program relationship. Dispatch lane PRs/MRs use the dispatch label.
- Remove stale labels from exclusive taxonomy groups before applying the new
  selected label for that group, except hold labels: never remove a hold as
  part of classification. Request explicit release from its authorized owner
  before a conflicting state change. Preserve historical compatibility labels
  when reclassifying older records.
- If a record matches multiple areas, pick the primary area that owns the next
  implementation or review action; mention secondary concerns in the issue or
  PR comment instead of stacking exclusive `area::` labels.
