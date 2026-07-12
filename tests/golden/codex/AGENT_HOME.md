# AGENT_HOME.md

## Purpose & Scope

- Shared home-scope defaults for the local agent runtime layer, git-managed in
  `agent-runtime-kit` and rendered per product into
  `build/<product>/AGENT_HOME.md` (wiring lives in the kit README /
  `DEVELOPMENT.md` / `SUPPORT_MATRIX.md`).
- This must be safe fallback policy for unrelated workspaces. A closer project

  or directory `AGENTS.md` can override or extend it.

- Keep this file concise. Detailed workflows belong in docs resolved by
  `agent-docs`.

## Required Preflight


- Each repository declares its required docs and validation in
  `AGENT_DOCS.toml`; the harness injects a start-of-session cue naming the
  per-intent required docs and validation commands. Read those docs before
  writing.
- Before declaring a code-editing task done, run the validation the active
  intent declares, or state an explicit waiver; the finish-line gate blocks a
  stop when code was edited but declared validation did not run.
- Inspect a repo's requirements on demand with `agent-docs preflight --intent
  <intent>` or `agent-docs explain --intent <intent>`; when checking a source
  docs-home checkout instead of the installed rendered home, pass
  `--docs-home` with that checkout path.


## Work Mode

- Natural-language collaboration is the default interface; prompt templates
  and skills are steering aids, used when explicitly invoked or required by
  active policy, tooling, or workflow routing.
- Classify the request path first. Implementation, maintenance, validation, or
  delivery: honor Required Preflight and any required tier decision, then
  execute instead of prolonging planning. Business, requirement, feasibility,
  or customer-facing discussions: evaluate first and do not jump to
  implementation unless asked.
- On every path, treat user-provided or customer-provided material as input to
  assess, not as already-validated truth.
- Ask only the minimum clarification needed when objective, done criteria,
  scope, constraints, environment, or safety/reversibility are materially
  unclear; when assumptions are acceptable, state them briefly and proceed.
- When conclusions depend on uncertainty, separate known facts, assumptions,
  inferences, and open questions.
- Before editing code, scripts, docs, or config, inspect the target plus
  relevant definitions, call sites, loading paths, or project rules.
- For testable production behavior changes, follow the canonical
  `test-first-evidence` durable lifecycle: declare the contract/test impact and
  capture meaningful red before production edits, or record a complete waiver.
- Keep answers concise, high-signal, and easy to verify; keep
  precision-critical technical terms, standards, APIs, commands, and proper
  nouns in English when clearer.


## Code Review Delegation

- Codex-only: when the active host exposes `multi_agent_v1.spawn_agent` or an
  equivalent dispatch tool, dispatch reviewer subagents for code-review
  requests instead of reviewing inline; if dispatch is unavailable or blocked,
  review inline and state that fallback. Full contract:
  `core/policies/code-review-delegation-codex.md`.


## Work Tier Levels

- Classify every substantive work request into the lowest applicable tier and
  use that tier's method: L0 direct / PR-only, L1 follow-up issue, L2 plan
  tracking issue, L3 dispatch plan. PR delivery is the shared floor under
  every tier.
- State the tier and recommended next step at the start of such work. L1+ or
  ambiguous classification: surface the level as a decision and wait.
  Unambiguous L0: say so and proceed. Re-triage if the work escalates
  mid-flight.
- Full ladder, escalation judge, and per-tier methods:
  `core/policies/work-tier-levels.md` (injected for `project-dev`).

## Evidence, Memory, And External Facts

- Use traceable citations when source material materially affects a
  requirement, feasibility, work, or external-fact claim; do not present
  unsupported assumptions as facts.
- Tag cited sources as `[U#]` user input (record in English, paraphrasing
  non-English input), `[F#]` local files/code/docs, `[W#]` web source, `[A#]`
  app/API/CLI/tool result, `[I#]` inference from cited facts.
- For external, unstable, or time-sensitive claims, run `task-tools`
  preflight and prefer authoritative sources. Full external-fact workflow:
  `core/policies/external-facts.md` (required for `task-tools`); the optional
  CLI tool catalog is `core/policies/cli-tools.md`.
- Use personal environment memory only for personal setup, recurring
  preferences, workspace/account conventions, or phrases like "same as
  before"; never for secrets, temporary task state, or project state.

## Files, Hooks, And Validation

- Follow the active project's conventions for deliverables and generated
  files; do not create durable discussion or decision artifacts unless asked,
  required by project rules, or clearly reusable.
- Keep temporary/debug artifacts out of `/tmp`: put them under the runtime-kit
  state out tree (via `agent-out`) and reference that path in the reply.
- Hooks may enforce mechanical guardrails, but hooks do not replace policy.
  Prefer project-defined validation commands; if none exist, run the smallest
  meaningful checks and report what was or was not run.
- Artifact paths, `agent-out` usage, and hook mechanics:
  `core/policies/files-hooks-validation.md` (injected for `project-dev`).

## Git, Commits, Issues, PRs, And MRs

- Always use the `semantic-commit` skill; direct `git commit` is blocked by
  hook.
- Use `git-cli worktree` for agent worktree lifecycle; direct mutating
  `git worktree` commands are blocked by hook.
- Never enable `extensions.worktreeConfig` or set per-worktree
  identity/signing config; never use `--no-gpg-sign` for tracked work. If
  signing fails, stop and report the blocker.
- For agent-owned provider issues, PRs, and MRs, use the active workflow or
  `forge-cli` surface; direct `gh pr create` or `glab mr create` are blocked
  by hook.
- Run the repo's pre-commit tests/checks per `DEVELOPMENT.md`. Never
  force-push `main`.
- Commit body gate, managed worktree paths, branch naming, label selection,
  and PR/MR body format: `core/policies/git-delivery.md` (injected for
  `project-dev`).

## Plan Archive

- The agent-plan-archive stores past plans, issues, PRs, and MRs for recurring
  implementation context. Consult it only before opening a new plan, or when
  diagnosing a suspected recurring or previously resolved problem — not as a
  per-task or background step.
- Discover with `plan-archive catalog` / `plan-archive search`, fetch with
  `plan-archive query`; check each result's `fetched_at` before relying on it.

## Session Closeout

- Same-turn transient fixes need no retained record; mention them in the
  reply.
- Important unresolved workflow gaps or suspected nils-cli / primitive bugs go
  through `heuristic-inbox` (version, minimal repro, upstream issue link when
  found, current workaround); archive promoted or `wontfix` inbox entries via
  `heuristic-inbox`, never by deleting them in place.
- After the session goal is achieved, run `$heuristic-session-closeout`: it
  reviews available evidence, drives `evidence migrate` for durable
  `skill-usage` retention, and preserves warranted records on `main`.
- Full routing policy for turning failures and repeated lessons into durable
  knowledge: `core/policies/heuristic-system/HEURISTIC_SYSTEM.md`.
