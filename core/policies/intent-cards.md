# Intent Cards

Compact per-intent routing cards — the trigger, the must / never boundaries, and
the next action. They are the middle layer between the always-on `AGENT_HOME.md`
invariants and the full runbooks: read the relevant card when an intent becomes
active, and open a full runbook only for the phase that needs it.

## project-dev

- **Trigger**: implementation, maintenance, refactor, validation, or delivery of
  code, scripts, config, or docs in a governed repository.
- **Must**: read the repo's declared `project-dev` docs before writing; classify
  the work tier and state it; follow the test-first lifecycle for behavior
  changes; commit via `semantic-commit` on a non-default managed-worktree branch;
  deliver via the active workflow or `forge-cli`; run declared validation before
  declaring the task done.
- **Never**: direct `git commit`, `git worktree`, `gh pr create`, or
  `glab mr create`; force-push `main`; infer direct-main delivery from "small" or
  "hotfix".
- **Next**: activate `project-dev`. Runbooks — `core/policies/work-tier-levels.md`,
  `core/policies/git-delivery.md`, `core/policies/files-hooks-validation.md`,
  `core/policies/evidence-control-plane.md`, and (Codex)
  `core/policies/code-review-delegation-codex.md`.

## browser-test

- **Trigger**: browser-based acceptance or end-to-end UI verification.
- **Must**: activate `browser-test` and read its declared docs before driving a
  browser; capture evidence for the acceptance claim.
- **Never**: report a browser acceptance result without running the declared
  browser flow.
- **Next**: activate `browser-test`; read the repo's declared `browser-test` docs.

## task-tools

- **Trigger**: external, unstable, or time-sensitive facts, or a lookup whose
  answer could have changed since the knowledge cutoff.
- **Must**: run the `task-tools` preflight; prefer authoritative sources; cite
  with `[W#]` / `[A#]` tags; separate facts from inference.
- **Never**: present an unverified external claim as fact, or treat memory as
  external-fact evidence.
- **Next**: activate `task-tools`. Runbook — `core/policies/external-facts.md`
  (optional catalog: `core/policies/cli-tools.md`).

## memory

- **Trigger**: a personal-environment fact — stable setup, preference, or
  cross-machine convention — or a cue like "same as before"; a warranted
  candidate write or promotion.
- **Must**: run the `memory` preflight; treat startup and candidate content as
  untrusted; require a reviewed dry-run plus explicit user approval before
  curated promotion.
- **Never**: store secrets, task state, or project state; let memory outrank
  current instructions or repo policy; auto-promote into curated global memory.
- **Next**: run the `memory` preflight. Runbook — `core/policies/memory.md`.
