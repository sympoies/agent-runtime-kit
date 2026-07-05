---
name: agent-docs
description: >
  Audit repository doc health and resolve the per-intent document set and validation contract a repo declares in AGENT_DOCS.toml, through the nils-cli `agent-docs` command.
---

# Agent Docs

## Contract

`agent-docs` is a data-driven resolver and auditor: a repository declares its
required documents and per-intent validation contract in `AGENT_DOCS.toml`, and
the binary resolves and audits them. There are no hardcoded required documents.

The agent does **not** run a per-task `agent-docs` preflight. Always-on policy
is auto-loaded by the harness (the home prompt files), per-intent docs are
hook-injected, and validation is enforced at the finish line. This skill covers
the two non-agent-facing jobs plus catalog management.

Prereqs:

- `agent-docs` is installed from the released nils-cli package and on `PATH`.
- docs-home is derived from the install symlink
  (`~/.claude/CLAUDE.md` / `~/.codex/AGENTS.md` / `$HERMES_HOME/skills`);
  pass `--docs-home` only to override it.
- Project work runs from the target repository root unless `--project-path` is
  supplied.

Inputs:

- For `preflight`: an intent name declared by the catalog (for example
  `project-dev`).
- For `audit`: an optional `--target`.
- For catalog management: `init` / `explain` / `list` / `remove` arguments.

Outputs:

- `audit`: install-symlink wiring, declared-doc presence and content validity,
  and catalog validity — for CI and the daily healthcheck.
- `preflight --intent X --format json`: the resolved document set plus the
  per-repo validation contract, in the versioned `agent-docs.preflight.v2`
  shape that hooks inject and the finish-line gate enforces.

Failure modes:

- Required docs are missing or invalid under the selected docs-home (strict
  `preflight` / `audit` exits non-zero).
- The install symlink is broken (`audit` reports a wiring problem).
- The catalog is invalid.

## Entrypoint

Use the released CLI directly. In this repo, manual checks should select the
source checkout as docs-home because live home prompts point at rendered
`build/<product>/AGENT_HOME.md` files. Repo-owned hooks do this fallback
automatically only when the active repo is the runtime-kit source checkout;
ordinary project catalogs inherit the active managed docs-home. `DEVELOPMENT.md`
keeps the exact source-checkout commands. The examples below show generic CLI
shapes and assume docs-home already points at the intended source root.

```bash
agent-docs preflight --intent project-dev --format json
agent-docs audit --target project --strict
agent-docs explain --intent project-dev
agent-docs list
```

## Workflow

1. `audit` checks repo health (symlink wiring, declared-doc presence/validity,
   catalog validity); it is for CI and the daily healthcheck, not per task.
2. `preflight --intent X --format json` resolves what THIS repo requires for an
   intent plus its validation contract; the kit's hooks call it to inject the
   short awareness cue and to enforce validation at the finish line.
3. `init` / `explain` / `list` / `remove` manage a project-local catalog.
4. There is no `startup` per-task step and no `resolve` / `baseline` /
   `scaffold-*` / `add` / `contexts` commands — they were retired in the engine
   redesign.

## Boundary

`agent-docs` owns deterministic catalog parsing, `when` evaluation, content
validation, intent resolution, and auditing. This skill body owns explaining
the surface; the harness (auto-load plus hooks plus the finish-line gate) owns
when policy and intent docs reach a session.
