# Changes Outside The Current Repository

## Purpose

Use this policy when work in one repository appears to require a change in
another repository. The escalation order applies to every repository outside
the current one, including another project published by the same organization.
The third-party submission, identity, and disclosure gates apply when the
other repository is owned by someone else.

An upstream contribution is the last option. The objective is to solve the
accepted problem at its proper ownership boundary without exporting a local
integration concern, private context, or avoidable maintenance burden.

## Authorization Boundary

For a third-party project, an agent may investigate, reconstruct a public
reproduction, write tests, prepare a patch, and draft issue or pull-request
text. It must not create the upstream issue, open the upstream pull request,
or sign a DCO or CLA. A human maintainer performs those publicly attributed or
legally significant actions.

Work in another repository owned by the same organization continues through
that repository's normal governed issue and delivery workflows when the user
has authorized it. Do not vendor, fork, or silently patch a sibling repository
instead of raising the change in its actual owner.

## Escalation Order

Before proposing work outside the current repository, use the first viable
rung and record where the investigation stopped and why:

1. Configuration or a supported extension point.
2. A local adapter or wrapper owned by the current repository.
3. Pinning or moving the external project's version.
4. A version-scoped, hash-authenticated downstream patch.
5. A contribution to the other repository.

Apply one hard filter first: if only the current project needs the change, it
does not go upstream. A boundary that exists solely for a local integration or
hook belongs in a local adapter or authenticated downstream patch. Upstream
work requires a problem another user of that project could also encounter.

Search existing issues, pull requests, and discussions before drafting. Also
inspect changes already merged to the default branch but not yet released. If
the needed behavior already exists, upgrade or pin instead of submitting a
duplicate.

## Issue Or Pull Request

Classify the proposed change against the other project's own documented or
intended behavior:

- For a bug, an issue and pull request may be prepared together.
- For anything that is not a bug, prepare an issue first. Do not prepare a
  pull request until a maintainer responds positively. This includes a small
  feature.
- Use issue-first regardless of size when the change touches a public API or
  schema, adds a dependency, requires a migration, changes a documented
  default, or requires new documentation.

These rules control what may be drafted. The third-party human-submission gate
still controls whether any issue or pull request is opened.

## Contribution Rules Are A Blocking Gate

Before drafting for a third-party project, verify and record the applicable
rules from the exact project and target branch. At minimum, inspect:

- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md`;
- DCO or CLA requirements;
- issue and pull-request templates;
- commit and pull-request title conventions;
- required test and lint commands;
- branch and target-branch rules; and
- the required submission language.

Unverified requirements are a blocker, not a reason to assume conventional
defaults.

A suspected security defect must never become a public issue, pull request,
reproduction, or discussion. Follow the project's `SECURITY.md` private
disclosure route. If no private route is published, escalate to the human
maintainer for a decision and make no public report in the meantime.

## Public Evidence And Disclosure

Upstream evidence must stand on its own in the other repository:

- a minimal, de-identified reproduction that runs inside that repository;
- tests using that project's own framework and conventions;
- observed and expected behavior; and
- the exact external version or commit.

State the real impact. Internal validation, downstream smoke runs, patch apply
receipts, private logs, and local workflow evidence stay with the current
project; they are not substitutes for an upstream reproduction.

Reconstruct evidence for a public audience. The diff, reproduction, logs, and
prose must not contain credentials, machine-local paths, internal hostnames,
private topology, private skill contents, employer or client names that are not
already public, or internal identifiers.

A link to the current project's workaround is optional. Include it only when
the target is public and contains no internal information. Label it explicitly
as a downstream expedient, not the proposed upstream implementation.

## Identity, Licensing, And Attribution

- A human chooses the account and email that determine personal or employer
  attribution.
- An agent must not sign a DCO or CLA or accept another legal contribution
  agreement.
- Do not add a `Co-Authored-By: Claude` trailer.
- Disclose AI assistance when the other project's rules require it.

## Aftercare

Treat an accepted submission as an ongoing obligation to answer review,
update the change, rebase when required, and carry it to a terminal outcome.
If it is rejected or becomes stale, retain the downstream workaround and
record the result with its owner.

When an upstream issue or pull request corresponds to a downstream patch,
record the public link beside that patch when its manifest supports the field.
The link is the removal signal: once the fix is released and the supported
version has moved, remove the patch through its normal authenticated lifecycle.
