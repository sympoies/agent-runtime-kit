# AGENT_HOME.md

## Purpose & Scope

- Shared home-scope defaults for the local agent runtime layer, git-managed in
  `agent-runtime-kit` and rendered per product into
  `build/<product>/AGENT_HOME.md` (wiring lives in the kit README /
  `DEVELOPMENT.md` / `SUPPORT_MATRIX.md`).
- This must be safe fallback policy for unrelated workspaces. A closer project

  or directory `AGENTS.md` / `.hermes.md` can override or extend it.

- Keep this file concise. Detailed workflows belong in the runtime-kit source
  docs; Hermes copies only this rendered development-policy skill.


## Required Preflight


- Each repository declares its required docs and validation in
  `AGENT_DOCS.toml`. Hermes has no agent-docs or hook system: open
  `AGENT_DOCS.toml` directly to see a repo's declared docs, read them before
  writing, and run the declared validation commands via the terminal tool.
- Do not declare a code-editing task done before the declared validation has
  run; state an explicit waiver when it cannot.


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
- For testable production behavior changes, follow the `test-first-evidence`
  discipline: capture failing-test evidence before editing production code, or
  state an explicit waiver with substitute validation.
- Keep answers concise, high-signal, and easy to verify; keep
  precision-critical technical terms, standards, APIs, commands, and proper
  nouns in English when clearer.


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
  `core/policies/work-tier-levels.md` in the runtime-kit checkout.


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
- Hermes has no runtime-kit hook runner for this copied skill; policy still
  applies. Prefer project-defined validation commands; if none exist, run the
  smallest meaningful checks and report what was or was not run.
- Artifact paths, `agent-out` usage, and validation mechanics:
  `core/policies/files-hooks-validation.md` in the runtime-kit checkout.


## Git, Commits, Issues, PRs, And MRs

- Always use the `semantic-commit` skill for supported commit workflows.
- Use `git-cli worktree` for agent worktree lifecycle; direct mutating
  `git worktree` commands bypass the managed lifecycle.
- Never enable `extensions.worktreeConfig` or set per-worktree
  identity/signing config; never use `--no-gpg-sign` for tracked work. If
  signing fails, stop and report the blocker.
- For agent-owned provider issues, PRs, and MRs, use the active workflow or
  `forge-cli` surface; direct provider CLI mutations bypass delivery gates.
- Run the repo's pre-commit tests/checks per `DEVELOPMENT.md`. Never
  force-push `main`.
- Commit body gate, managed worktree paths, branch naming, label selection,
  and PR/MR body format: `core/policies/git-delivery.md` in the runtime-kit
  checkout.


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
