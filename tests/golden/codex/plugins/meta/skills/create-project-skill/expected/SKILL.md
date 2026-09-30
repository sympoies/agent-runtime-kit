---
name: create-project-skill
description: >
  Scaffold a project-local skill under a consuming repo's `.agents/skills`
  tree for Codex and Claude by default, with Codex-only and bridge-only modes.
---

# Create Project Skill

## Contract

Prereqs:

- Run inside the target consuming project's git work tree.
- The request is for a project-local skill, not a repo-owned runtime-kit managed
  skill. Use `create-skill` for `agent-runtime-kit` managed skills.
- The caller has supplied or accepted a lowercase hyphenated skill name that
  starts with `project-` (project-local skills) or `private-` (skills under the
  private overlay home, `$AGENT_PRIVATE_SKILLS_HOME`).
- Existing files are never overwritten without explicit user approval.
- Claude-only creation is unsupported. Claude exposure is a bridge to the
  canonical `.agents/skills` source tree, not a second source location.

Inputs:

- Skill name, description, intended entrypoint, and whether the skill needs
  skill-owned `scripts/`, `tests/`, `references/`, `fixtures/`, or `bin/`.
- Creation mode:
  - default / `--target both`: create the canonical skill source and ensure
    `.claude/skills -> ../.agents/skills`.
  - `--codex-only` / `--target codex`: create only the canonical skill source
    and do not mutate `.claude/`.
  - `--bridge-only`: create or verify only the Claude bridge for an existing
    `.agents/skills` tree.
- Optional `.agents/scripts/<command>.sh` thin wrapper for project
  slash-command style dispatch.
- Optional project validation command to run after scaffolding.

Outputs:

- `.agents/skills/<skill>/SKILL.md`.
- Optional `.agents/skills/<skill>/scripts/<skill>.sh` executable stub.
- Optional `.agents/skills/<skill>/{tests,references,fixtures,bin}/` support
  directories.
- Default `.claude/skills` symlink and `.gitignore` entry for `.claude/`
  unless `--codex-only` is used.
- Optional `.agents/scripts/<command>.sh` wrapper that delegates to the
  skill-owned script or another canonical project command.
- A validation summary with created paths and any skipped optional surfaces.

Failure modes:

- The current directory is not inside a git work tree.
- The skill name is malformed (does not match `^(project|private)-[a-z0-9-]+`),
  ambiguous, or collides with an existing `.agents/skills/<skill>` path.
- A requested wrapper path already exists and replacement was not approved.
- `--target claude`, `--claude-only`, or removed `--link-only` is requested.
- `--bridge-only` is requested without an existing `.agents/skills` tree.
- The workflow would mutate runtime-kit manifests, product render output,
  golden snapshots, or global runtime homes.
- Validation fails after scaffolding.

## Entrypoint

Use the bundled helper for deterministic file creation:

```bash
$CODEX_HOME/plugins/meta/skills/create-project-skill/scripts/create-project-skill.sh <skill-name> --description "One-line description."
```

Default creation exposes the skill to both Codex-style `.agents/skills`
consumers and Claude through the project-local bridge. Use Codex-only only when
the current repo should not receive a `.claude/` local directory:

```bash
$CODEX_HOME/plugins/meta/skills/create-project-skill/scripts/create-project-skill.sh <skill-name> --codex-only
```

Use bridge-only when `.agents/skills` already exists and only Claude discovery
needs to be wired:

```bash
$CODEX_HOME/plugins/meta/skills/create-project-skill/scripts/create-project-skill.sh --bridge-only
```

Optional support surfaces are explicit:

```bash
$CODEX_HOME/plugins/meta/skills/create-project-skill/scripts/create-project-skill.sh <skill-name> --with-script --with-tests --with-wrapper <command>
```

## Workflow

1. Resolve the target project root with `git rev-parse --show-toplevel`.
2. Confirm this is a project-local skill request. If the user wants a
   runtime-kit managed skill, switch to `create-skill`.
3. Normalize and validate the skill name as lowercase hyphenated text that
   starts with `project-` (project-local) or `private-` (private overlay);
   reject any other prefix.
4. Inspect `.agents/skills/`, `.agents/scripts/`, `.claude/`, project
   `AGENTS.md`, and nearby local skill conventions before editing.
5. Refuse to overwrite existing skill directories, scripts, wrappers, symlinks,
   or project policy files unless the user explicitly approves replacement.
6. Create `SKILL.md` with front matter, H1, Contract, Entrypoint or Scripts,
   Workflow, and Boundary sections.
7. Add only the support folders explicitly requested. Keep stubs small and mark
   TODO behavior clearly when implementation remains.
8. In the default mode, create or verify `.claude/skills ->
   ../.agents/skills` and ensure `.claude/` is ignored. Skip all `.claude/`
   mutation only when `--codex-only` is requested.
9. If a slash-command style wrapper is requested, create a thin
   `.agents/scripts/<command>.sh` wrapper that delegates to the skill-owned
   script or another canonical project command.
10. Create `.agents/scripts/pre-pr.sh` only when `--with-pre-pr-stub` is
    requested.
11. Refuse removed Claude-only flags: `--target claude`, `--claude-only`, and
    `--link-only`.
12. Run focused validation: `test -f`, shell syntax for generated scripts,
    project-owned checks when available, and the user's requested validation
    command.
13. Report created paths, skipped optional paths, validation status, and next
    implementation work.

## Boundary

This skill owns project-local skill scaffolding only. It does not mutate
`manifests/skills.yaml`, `manifests/plugins.yaml`, `targets/`, `build/`,
`tests/golden/`, sandbox expected skill lists, or live global runtime homes. If
project-local creation needs a reusable dry-run/apply planner, reference graph,
or machine-readable mutation contract, extract that deterministic behavior to
released `nils-cli` first and then call it from this workflow.
