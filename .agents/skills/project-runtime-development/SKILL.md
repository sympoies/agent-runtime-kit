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

## Project Delta

Apply the repository's active `project-dev` documents and `DEVELOPMENT.md` for
inspection, test-first work, validation, Git, review, and delivery. This skill
adds only the replacement for the retired heuristic workflow:

1. Route recurring friction to the earliest owning test, diagnostic, policy,
   skill, runbook, or external repository.
2. Fix that owner in the current task when it is in scope. Do not create a
   second local tracker for work that is complete.
3. When authorized durable follow-up remains, use an ordinary
   `issue-follow-up` record in the canonical repository. Keep chronology in the
   issue and public-safe devlog.

## Boundary

This skill coordinates development decisions inside
`sympoies/agent-runtime-kit`. It does not grant automatic issue creation,
provider writes, deployment, credential access, cross-repository mutation,
release, merge, or runtime activation. It does not retain prompts, raw model
output, credentials, local paths, or private topology in issues or the devlog.
Preserve all repository-owned controls. This skill creates no parallel inbox,
operation-record lifecycle, or automatic session-closeout work.
