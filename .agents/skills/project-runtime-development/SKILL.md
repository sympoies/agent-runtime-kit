---
name: project-runtime-development
description: >
  Develop, diagnose, test, and deliver agent-runtime-kit changes through the
  earliest owning validation layer, then route durable follow-up to ordinary
  issues and strengthen the canonical test, diagnostic, policy, or skill.
allowed-tools: Bash, Read, Edit, Write
---

# Project Runtime Development

Use this project-local skill for material changes to `agent-runtime-kit`.
Apply the repository's existing `project-dev` intent and `DEVELOPMENT.md`; this
skill supplies the small project-specific decision loop and does not duplicate
their engineering, Git, review, or delivery contracts.

## Contract

Before editing, state a compact validation map:

- observable delta and retained invariants;
- canonical source owner plus affected consumers, renders, manifests, tests,
  and runtime boundary;
- earliest owning regression or substitute validation;
- focused iteration command and expected secret-safe result;
- outer validations actually required by the change;
- authority or exact identities needed for provider, release, deployment, or
  cross-repository work.

Capture meaningful RED at the earliest testable owner when practical. Iterate
there, then run the repository's declared finish-line once on the stable
candidate. Stop before mutation when the target, authority, source owner,
checkout ownership, or required identity cannot be proved.

The completed result is the smallest correct source change, aligned derived
surfaces, current validation, explicit residual gaps, and governed delivery
only when authorized.

## Workflow

1. Read the closest repository instructions and the active `project-dev`
   documents. Search the development log when it may explain an existing
   contract, guardrail, default, or removal.
2. Inspect the source owner, material callers, tests, generated surfaces,
   manifests, package/runtime consumers, and relevant current documentation.
3. Record the validation map. Add or select the focused regression and capture
   RED, or state why meaningful RED is impractical and name the substitute.
4. Repair only the owning contract. Do not compensate for a lower-layer gap
   with retries, waits, prompt prose, or a broader end-to-end assertion.
5. Advance only through validations required by the observable delta. A stale
   outer receipt cannot be reused, but invalidation alone does not put an
   otherwise unrelated deployment, release, or provider run in scope.
6. If a generic failure recurs, the same layer fails again without new
   evidence, or the missing primitive belongs to another repository, stop and
   route the gap to its canonical owner instead of broadening the workaround.
7. Run the declared repository gate once against the final candidate. Complete
   review, PR delivery, merge, deployment, runtime sync, or release only under
   the separately authorized owning workflow.

## Self-Improvement Loop

When work exposes repeatable friction:

1. Preserve the first bounded failure and observable result.
2. Identify the earliest owning layer and the missing assertion, diagnostic,
   fixture, primitive, or policy.
3. Fix that owner within the active task and prove it with a focused regression;
   otherwise prepare the smallest actionable handoff.
4. Create or update an ordinary `issue-follow-up` record in the canonical
   repository only when durable cross-session follow-up is authorized.
5. Put incident chronology in the issue and public-safe devlog. Update
   normative policy or this skill only when the lesson applies
   to future work.
6. Record the improved diagnostic or validation decision in final evidence so
   the next agent starts from the strengthened owner.

Transient mistakes, one-off command failures, and problems fixed completely in
the current change create no additional tracker. General lessons live in
tests, diagnostics, policy, skills, or runbooks; do not create a parallel inbox
or operation-record lifecycle.

## Boundary

This skill coordinates development decisions inside
`sympoies/agent-runtime-kit`. It does not grant automatic issue creation,
provider writes, deployment, credential access, cross-repository mutation,
release, merge, or runtime activation. It does not retain prompts, raw model
output, credentials, local paths, or private topology in issues or the devlog.
Preserve all repository validation, managed-worktree, signing, review,
delivery, evidence, and cleanup controls.
