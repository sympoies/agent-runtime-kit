# Files, Hooks, And Validation

## Purpose

This policy holds the detailed mechanics for where agent output artifacts go,
where hook source and managed config live, and how to run project validation
commands.

It is declared as a `project-dev` document in `AGENT_DOCS.toml` (home scope),
so the harness surfaces it through the hook preflight when implementation work
starts. `AGENT_HOME.md` carries the always-on directives — follow the active
project's conventions, keep debug artifacts out of `/tmp`, do not create durable
discussion artifacts unless asked, hooks do not replace policy, and prefer
project-defined validation. This file is the procedural detail behind them.

## Output Artifacts

- For temporary/debug artifacts without a project-defined output path, create a
  project run directory with `agent-out project --topic <topic> --mkdir`.
- Debug/test artifacts without a project-defined path belong under the
  runtime-kit state out tree
  (`${CLAUDE_KIT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/out/`),
  not `/tmp`; reference that path in the reply.
- Do not override established tool/workflow artifact contracts; use
  `agent-out audit` before cleaning or enforcing the runtime-kit state out tree
  (`${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/out/`).
- The `agent-out` tree is scratch space, not a database. `skill-usage` records
  are written there unconditionally (a useful breadcrumb even when no archive is
  configured) and are **not** auto-reaped — they persist until manually cleaned
  (`agent-out`) or migrated. Durable, queryable retention beyond a session is a
  separate lane: migrate records into the agent-evidence-archive with the
  direct `evidence migrate` CLI (clone path from
  `$AGENT_EVIDENCE_ARCHIVE_HOME` / XDG; never committed into a working repo). See
  `core/policies/evidence-archive/EVIDENCE_ARCHIVE.md`.

## Sensitive Output Inspection

- When exploring container, stack, orchestrator, or provider API objects, never
  print whole objects or env-like maps by default. Treat fields named `Env`,
  `environment`, `secrets`, `config`, `auth`, `token`, `password`, or `key` as
  potentially sensitive until proven otherwise.
- Select only the safe-to-share fields needed for the task, or redact env-like
  fields in the projection before output reaches the transcript. Prefer
  presence/count/length checks over value output; if a specific value must be
  inspected, read it by name and report only whether it exists or has the
  expected shape.
- If a sensitive value is printed into the session transcript, stop using that
  value, state the leak plainly, and route credential rotation through the
  appropriate credential owner rather than preserving the raw value in evidence,
  summaries, issues, PRs, or memory.

## Hooks

- Hooks may enforce mechanical guardrails, but hooks do not replace policy.
- Shell inspection uses a shared tri-state effect contract: `read-only`,
  `mutation`, or `unknown`. Read-only admission is exact and narrow: a pipeline
  may contain pipe separators only, and every stage must match an audited
  read-only argv shape. Redirection, command substitution, another shell
  operator, an unsafe stage, or an untrusted executable leaves the effect
  `unknown`; it does not prove that a mutation occurred.
- `AGENT_RUNTIME_PROJECT_DEV_MODE` controls only the project-dev workflow gate:
  `advisory` is the default, `enforce` is explicit fail-closed behavior, and
  `off` bypasses this one check. Invalid values degrade to advisory with a stable
  warning. Advisory attempts bounded exact target preparation when safe, but
  missing/stale activation, capability, or workdir attestation never blocks the
  repository command by itself. Enforce remains fail-closed for `unknown`; its
  `project-dev-required` recovery means the shell shape was not proven
  read-only, not that the hook observed a write. Exact trusted `agent-docs`
  preparation for another declared intent is admitted without first preparing
  `project-dev`; a near miss receives targeted trusted-command recovery. In
  advisory mode that near miss is explicitly not treated as a trusted bootstrap
  and executes normally; in enforce mode it is blocked before execution. Exact
  help/version argv for the managed `agent-docs` and `forge-cli` release surface
  is also read-only; a help flag embedded in an operational argv, a trailing
  argument, a different PATH binary, or a repository-local shadow is not.
- A successful explicitly submitted in-hook `session prepare` is a completed
  state transition. Its
  block result carries `[reason: prepared] [action: retry-original]`: retry the
  original blocked command and do not run or modify the preparation command
  again. Advisory auto-preparation instead allows the original command in the
  same call and returns an exact, phase-qualified
  `agent-docs preflight --intent project-dev` next action for reading the newly
  prepared contract. A host-attested absolute workdir is the supported
  cross-repository shell route. A ready target-rooted managed session may attest
  its exact cwd through its private session record when a provider Bash envelope
  omits cwd; session id, runtime incarnation, agent, owner/mode, and process cwd
  must all match. A missing attestation tells the agent not to repeat unchanged
  Bash and points to explicit Codex workdir, target-rooted session, or exact-path
  edit recovery. An `agent-run exec --cwd` wrapper targeting
  another repository or worktree remains unsupported until nils-cli provides
  one typed command context shared by every guard; dynamic, duplicated, opaque,
  relative, shadowed, and wrapped shapes use
  `cross-repository-target-unsupported` plus the target-rooted worker fallback.
- Hook source and managed config live under the active hook source checkout plus
  the managed block in the tool's runtime config (Codex `config.toml`, Claude
  `settings.json`).
- Use the installed hook sync command to update the local runtime config; do not
  track or symlink the whole runtime config file.

## Parent Workflow Routing

`agent-docs` preflight and `agent-out` allocation are parent workflow
responsibilities, not user-selected outcomes. The active implementation or tool workflow resolves
its declared intent documents before edits and allocates its own temporary
artifacts when it needs them. Keep both CLIs directly callable for deterministic
diagnostics, audits, and explicit cleanup planning.

## Validation

- Prefer project-defined validation commands. If none exist, run the smallest
  meaningful checks and report what was or was not run.
- When running project build, test, validation, or repository-owned script
  commands, prefer `agent-run exec --cwd <repo> -- <command> ...` when available
  so `.envrc` / `.env` handling is explicit in non-interactive agent sessions,
  but only when `<repo>` is already the host-attested command repository. Do not
  use the shell wrapper to hop from one repository/worktree to another; submit
  a host-attested workdir or start the command from a managed session rooted at
  that target. Do not run `direnv allow` automatically.
