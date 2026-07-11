# AGENT_HOME.md

## Purpose & Scope

- Shared home-scope defaults for the local agent runtime layer, git-managed in
  `agent-runtime-kit` and rendered per product into
  `build/<product>/AGENT_HOME.md` (wiring lives in the kit README /
  `DEVELOPMENT.md` / `SUPPORT_MATRIX.md`).
- This must be safe fallback policy for unrelated workspaces. A closer project
{% if product == "codex" %}
  or directory `AGENTS.md` can override or extend it.
{% elif product == "claude" %}
  or directory `CLAUDE.md` can override or extend it.
{% elif product == "hermes" %}
  or directory `AGENTS.md` / `.hermes.md` can override or extend it.
{% else %}
  or directory `AGENTS.md` / `CLAUDE.md` can override or extend it.
{% endif %}
{% if product == "hermes" -%}
- Keep this file concise. Detailed workflows belong in the runtime-kit source
  docs; Hermes copies only this rendered development-policy skill.
{% else -%}
- Keep this file concise. Detailed workflows belong in docs resolved by
  `agent-docs`.
{%- endif %}

## Required Preflight

{% if product == "hermes" %}
- Each repository declares its required docs and validation in
  `AGENT_DOCS.toml`. Hermes has no agent-docs or hook system: open
  `AGENT_DOCS.toml` directly to see a repo's declared docs, read them before
  writing, and run the declared validation commands via the terminal tool.
- Do not declare a code-editing task done before the declared validation has
  run; state an explicit waiver when it cannot.
{% else %}
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
{% endif %}

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

## Intent Routing

{% if product == "hermes" -%}
- Classify the natural-language request, then open only the relevant declared
  intent docs in `AGENT_DOCS.toml`: `project-dev` for implementation and
  delivery, `browser-test` for browser acceptance, and `task-tools` for
  external or unstable facts. Hermes has no runtime-kit agent-docs hooks, so
  this manual selection must not be reported as hook-enforced activation.
{% else -%}
- Classify the natural-language request and activate only the relevant
  `agent-docs` intents: `project-dev` for implementation and delivery,
  `browser-test` for browser acceptance, and `task-tools` for external or
  unstable facts. Read each activated intent's preflight documents before
  writing; users do not need to name evidence or lifecycle primitives.
- When the installed `agent-docs` supports durable session state, use
  `agent-docs session activate/status/verify`; the pre-edit hook verifies
  `project-dev` for every direct-edit target repository and for the working
  repository of shell commands. Run cross-repository shell mutations with each
  target repository as CWD because pre-tool hooks cannot observe expanded shell
  destinations. Only an explicitly recognized older CLI uses
  legacy direct preflight; missing or broken capability probes fail closed on
  supported hooked hosts.
{%- endif %}

{% if product == "codex" %}
## Code Review Delegation

- Codex-only: when the active host exposes `multi_agent_v1.spawn_agent` or an
  equivalent dispatch tool, dispatch reviewer subagents for code-review
  requests instead of reviewing inline; if dispatch is unavailable or blocked,
  review inline and state that fallback. Full contract:
  `core/policies/code-review-delegation-codex.md`.

{% endif %}
## Work Tier Levels

- Classify every substantive work request into the lowest applicable tier and
  use that tier's method: L0 direct / PR-only, L1 follow-up issue, L2 plan
  tracking issue, L3 dispatch plan. PR delivery is the shared floor under
  every tier.
- State the tier and recommended next step at the start of such work. L1+ or
  ambiguous classification: surface the level as a decision and wait.
  Unambiguous L0: say so and proceed. Re-triage if the work escalates
  mid-flight.
{% if product == "hermes" -%}
- Full ladder, escalation judge, and per-tier methods:
  `core/policies/work-tier-levels.md` in the runtime-kit checkout.
{% else -%}
- Full ladder, escalation judge, and per-tier methods:
  `core/policies/work-tier-levels.md` (injected for `project-dev`).
{%- endif %}

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
{% if product == "hermes" -%}
- Hermes has no runtime-kit hook runner for this copied skill; policy still
  applies. Prefer project-defined validation commands; if none exist, run the
  smallest meaningful checks and report what was or was not run.
- Artifact paths, `agent-out` usage, and validation mechanics:
  `core/policies/files-hooks-validation.md` in the runtime-kit checkout.
{% else -%}
- Hooks may enforce mechanical guardrails, but hooks do not replace policy.
  Prefer project-defined validation commands; if none exist, run the smallest
  meaningful checks and report what was or was not run.
- Artifact paths, `agent-out` usage, and hook mechanics:
  `core/policies/files-hooks-validation.md` (injected for `project-dev`).
{%- endif %}

## Git, Commits, Issues, PRs, And MRs

{% if product == "hermes" -%}
- Commit through the owning implementation or delivery workflow using the
  `semantic-commit` CLI; direct `git commit` bypasses the managed boundary.
- Use `git-cli worktree` for agent worktree lifecycle; direct mutating
  `git worktree` commands bypass the managed lifecycle.
{% else -%}
- Commit through the owning implementation or delivery workflow using the
  `semantic-commit` CLI; direct `git commit` is blocked by hook.
- Use `git-cli worktree` for agent worktree lifecycle; direct mutating
  `git worktree` commands are blocked by hook.
{% endif -%}
- Never enable `extensions.worktreeConfig` or set per-worktree
  identity/signing config; never use `--no-gpg-sign` for tracked work. If
  signing fails, stop and report the blocker.
{% if product == "hermes" -%}
- For agent-owned provider issues, PRs, and MRs, use the active workflow or
  `forge-cli` surface; direct provider CLI mutations bypass delivery gates.
{% else -%}
- For agent-owned provider issues, PRs, and MRs, use the active workflow or
  `forge-cli` surface; direct `gh pr create` or `glab mr create` are blocked
  by hook.
{% endif -%}
- Run the repo's pre-commit tests/checks per `DEVELOPMENT.md`. Never
  force-push `main`.
{% if product == "hermes" -%}
- Commit body gate, managed worktree paths, branch naming, label selection,
  and PR/MR body format: `core/policies/git-delivery.md` in the runtime-kit
  checkout.
{% else -%}
- Commit body gate, managed worktree paths, branch naming, label selection,
  and PR/MR body format: `core/policies/git-delivery.md` (injected for
  `project-dev`).
{%- endif %}

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
- After the session goal is achieved, follow the session-closeout procedure in
  `core/policies/heuristic-system/HEURISTIC_SYSTEM.md`: review available
  evidence, run `evidence migrate` when durable `skill-usage` retention is
  warranted, and preserve warranted records on `main`.
- Full routing policy for turning failures and repeated lessons into durable
  knowledge: `core/policies/heuristic-system/HEURISTIC_SYSTEM.md`.
