---
name: remove-project-skill
description: >
  Remove a project-local `.agents/skills` skill with dry-run-first reference
  inventory and explicit approval for wrappers or historical cleanup.
---

# Remove Project Skill

## Contract

Prereqs:

- Run inside the target consuming project's git work tree.
- The target is a project-local skill under `.agents/skills/<skill>`, not a
  repo-owned runtime-kit managed skill. Use `remove-skill` for managed
  runtime-kit skills.
- The first pass is dry-run only. File mutation requires explicit apply
  approval from the user or the active delivery plan.

Inputs:

- Project-local skill name.
- Optional wrapper command name under `.agents/scripts/<command>.sh`.
- Optional explicit cleanup approval for retained historical docs. Historical
  `docs/plans/**` records are retained by default.

Outputs:

- A dry-run list of project-local files and reference classes that would
  change.
- After apply approval: removed `.agents/skills/<skill>/` source and approved
  wrappers or bridge files.
- A validation summary proving no active project references remain outside the
  allowed historical set.

Failure modes:

- The current directory is not inside a git work tree.
- The target skill is missing or ambiguous.
- The workflow would delete historical docs without explicit cleanup approval.
- Active references remain after apply.
- The workflow would mutate runtime-kit manifests, product render output,
  golden snapshots, or global runtime homes.

## Entrypoint

Start with a dry-run inventory:

```bash
project_root="$(git rev-parse --show-toplevel)"
skill="<skill-name>"
skill_dir="$project_root/.agents/skills/$skill"

test -d "$skill_dir"
rg -n "$skill|.agents/skills/$skill" \
  "$project_root/.agents" \
  "$project_root/AGENTS.md" \
  "$project_root/README.md" \
  "$project_root/docs" 2>/dev/null || true
```

Classify matches before editing:

- project skill source: `.agents/skills/<skill>/`
- skill-owned scripts: `.agents/skills/<skill>/scripts/`
- optional project command wrappers: `.agents/scripts/<command>.sh`
- Claude bridge surface: `.claude/skills` or related `.gitignore` entries
- project policy or README references
- maintained docs references outside `docs/plans/**`
- retained historical records under `docs/plans/**`

After apply approval:

```bash
rm -rf "$skill_dir"
# Remove approved wrappers only after the dry-run classified ownership.
```

## Workflow

1. Resolve the target project root with `git rev-parse --show-toplevel`.
2. Confirm this is a project-local skill removal. If the target lives in
   runtime-kit manifests, switch to `remove-skill`.
3. Confirm `.agents/skills/<skill>/` exists exactly once.
4. Build the dry-run inventory with `rg` and classify every active reference.
5. Exclude `docs/plans/**` from default mutation. Keep those records as
   historical evidence unless the user explicitly asks for cleanup.
6. Present the planned active delta and stop unless apply approval is already
   part of the active plan.
7. Remove the project skill directory and only the approved project command
   wrappers or bridge files that are owned by this skill.
8. Update maintained docs or policy references that list active project-local
   skills.
9. Re-run the reference inventory and fail if active references remain outside
   the allowed historical set.
10. Run focused validation: absence checks, shell syntax for remaining wrappers,
    project-owned checks when available, and the user's requested validation
    command.
11. Report removed paths, retained historical references, validation status, and
    any follow-up work.

## Boundary

This skill owns safe project-local skill removal sequencing and retention
judgment. It does not remove runtime-kit managed skills, edit
`manifests/skills.yaml`, edit `manifests/plugins.yaml`, regenerate product
build output, or clean live global runtime homes. If removal needs a stable
dry-run/apply planner or machine-readable reference graph, implement and
release that primitive in `sympoies/nils-cli`, then consume it from this
workflow.
