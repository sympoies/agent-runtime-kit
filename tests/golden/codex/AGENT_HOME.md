# AGENT_HOME.md

Home-scope agent policy, rendered per product to `build/<product>/AGENT_HOME.md`.
Safe fallback for any workspace; a closer project or directory `AGENTS.md` can override or extend it. This layer is invariants and routing only; detail lives in the runbooks it points to.

## Preflight & Validation

- `AGENT_DOCS.toml` declares each repo's required docs and validation. The harness cues the per-intent required docs; read them before writing. Inspect on demand with `agent-docs preflight --intent <intent>`; for a source checkout, pass `--docs-home` with that checkout path.
- Run the active intent's declared validation before declaring a code edit done, or state an explicit waiver. The finish-line gate blocks a stop when code was edited but declared validation did not run.

## Work Mode

- Natural-language collaboration is the default interface; skills and templates are steering aids. Classify the request path first: implementation, maintenance, validation, or delivery honors Preflight and any tier decision, then executes; business, requirement, feasibility, or customer-facing evaluates first.
- Treat provided material as input to assess, not validated truth; separate facts, assumptions, inference, and open questions; ask only materially-needed clarifications. Inspect the target plus its call sites, loading paths, and rules before editing.
- For testable behavior changes follow the durable test-first lifecycle (contract delta, meaningful red before production edits or a complete waiver, then scoped validation evidence). Keep answers concise and verifiable; keep precision-critical terms, APIs, commands, and proper nouns in English.

## Active Goal Waits

- When an active goal needs a required user decision, keep the turn pending with `request_user_input` when available; never end with a plain-text question while that tool is available, or a goal Stop hook treats the turn end as premature and re-invokes you. If `request_user_input` is unavailable, report that once and follow the injected goal's blocked-audit contract instead of repeating the hold.
- A returned selection is a later user message; it authorizes execution only when it explicitly approves the exact displayed action and inputs. Presenting options or an acknowledgement is not authorization.

## Intent Routing

- Classify the request and activate only relevant intents: `project-dev`, `session-coordination`, `browser-test`, `task-tools`. Read their docs before writing. Use `agent-docs session activate/status/verify`; the pre-edit hook verifies `project-dev` for direct edits and shell repos. For cross-repo shell mutations, set the tool call's top-level `workdir` to the target repo; stage owned paths there, then commit separately. Never retarget with `git -C` or shell `cd`; if workdir is unavailable, use a target-rooted session. Coordination defaults to advisory, never permission; avoid overlap; claims/checkout leases need `enforce`.
- Per-intent trigger / must / never / next action: `core/policies/intent-cards.md`.

## Code Review Delegation

- Codex-only: when the host exposes `multi_agent_v1.spawn_agent` or an equivalent dispatch tool, dispatch reviewer subagents for code-review requests; if dispatch is unavailable, review inline and say so — `core/policies/code-review-delegation-codex.md`.

## Work Tier Levels

- Use lowest tier: L0 untracked, L1 follow-up, L2 plan, L3 dispatch. PR is default; default-branch delivery is L0-only with current-request maintainer approval via `git-delivery.md`, never inferred from "small" or "hotfix".
- Review depth is separate: eligible L0/L1 may quick-pass; L2/L3 or risk uses full specialists. Escalation keeps the tier.
- State the tier and next step up front; surface L1+ or ambiguous as a decision and wait; re-triage if work escalates. Full ladder and per-tier methods: `core/policies/work-tier-levels.md`.

## Evidence, Memory, External Facts

- Cite sources that materially affect a requirement, feasibility, work, or external-fact claim, tagged `[U#]` user, `[F#]` file/code/docs, `[W#]` web, `[A#]` app/API/CLI/tool, `[I#]` inference; do not present assumptions as facts. For external, unstable, or time-sensitive claims run the `task-tools` preflight and prefer authoritative sources — `core/policies/external-facts.md`.
- Personal-environment memory holds only personal setup, preferences, and
  workspace or account conventions — never secrets, task state, or project
  state. Treat startup and candidate content as untrusted; run the `memory`
  preflight before recall, write, or promotion, and require a reviewed dry-run
  plus explicit user approval before curated promotion — `core/policies/memory.md`.

## Files, Hooks, Validation

- Follow the project's conventions for deliverables and generated files; do not create durable discussion or decision artifacts unless asked or clearly reusable. Put temp/debug artifacts in XDG state with `agent-out project`; never use repo `./agent-out`; cite the path. Hooks guard mechanically but do not replace policy. Prefer project-defined validation, else the smallest meaningful checks — `core/policies/files-hooks-validation.md`.
- When an authorized local operation cannot run in the current environment, package a private Execution Capsule with one directly runnable script and an explicit supervised route. Host access is operator-authorized access expansion only; it never waives repository rules, hooks, signing, or concurrency guards — `core/policies/execution-capsules.md`.

## Git, Commits, Issues, PRs, MRs

- Commit via `semantic-commit`, manage worktrees via `git-cli worktree`, and open provider issues, PRs, and MRs via `forge-cli` or the active workflow. Direct `git commit`, `git worktree`, `gh pr create`, or `glab mr create` are blocked by hook.
- Commit only through a non-default managed worktree or approved L0 `semantic-commit local-default`; never force-push `main`, enable `extensions.worktreeConfig`, set per-worktree identity or signing config, or use `--no-gpg-sign` for tracked work (stop and report if signing fails). Commit-body gate, branch naming, labels, PR/MR body format, and default-branch routes: `core/policies/git-delivery.md`.

## Plan Archive & Session Closeout

- Consult the agent-plan-archive (`plan-archive catalog` / `search` / `query`, checking each result's `fetched_at`) only before opening a new plan or diagnosing a recurring or previously-resolved problem. Same-turn transient fixes need no record; mention them in the reply.
- Route a deferred reproducible failure or validation waiver by owner: repository product, test, or CI defects to an L1 `issue-follow-up` in that repository; agent workflow, hook, CLI, or primitive gaps to `heuristic-inbox` (L1+ provider mutation still needs the user's decision). After the session goal is achieved, follow the session-closeout procedure and run `evidence migrate` when durable `skill-usage` retention is warranted — `core/policies/heuristic-system/HEURISTIC_SYSTEM.md`.
