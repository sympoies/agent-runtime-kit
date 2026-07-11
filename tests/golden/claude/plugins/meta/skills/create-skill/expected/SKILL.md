---
name: create-skill
description: >
  Add a repo-owned runtime-kit skill with source, manifests, product render
  surfaces, acceptance coverage, and governance validation.
---

# Create Skill

## Contract

Prereqs:

- Run from the `agent-runtime-kit` repository root.
- The request is for a repo-owned managed skill, not a project-local overlay.
- `agent-runtime` is installed from the released nils-cli package and available
  on `PATH`.
- The caller has supplied or accepted a canonical skill ID in the form
  `<domain>.<skill>`.

Inputs:

- Skill ID, domain, skill name, supported products, description,
  `required_clis` floors, parent intents, example user request, and admission
  rationale.
- Optional skill-owned `scripts/`, `bin/`, `fixtures/`, or docs support
  folders when the workflow needs them.
- Explicit approval for any new plugin domain.

Outputs:

- `core/skills/<domain>/<skill>/SKILL.md.tera`.
- `manifests/skills.yaml` v2 entry with complete `invocation`, honest
  `exposure.profile: default`, and concrete `required_clis` values or an
  explicit empty map for prose-only skills.
- `manifests/plugins.yaml` containment update, and product plugin metadata
  only when a new domain was approved.
- Rendered product output, golden snapshots, sandbox expected skill list
  updates, runtime-smoke matrix/case coverage, and reminder metadata when the
  skill should be agent-invoked.

Failure modes:

- The skill ID is malformed or collides with an existing source or manifest
  entry.
- A new domain was requested without explicit user approval.
- `required_clis` contains placeholders or references an unreleased binary.
- The capability is agent bookkeeping, a one-command wrapper, execution mode,
  or child lifecycle phase without a reviewed direct-user outcome.
- The entry claims `advanced`, `internal`, or `opt-in` exposure that the three
  product installers cannot implement.
- The workflow would leave a skill without render, sandbox, or runtime-smoke
  acceptance coverage.

## Entrypoint

Use the repository shape directly:

```bash
skill_id="<domain>.<skill>"
domain="${skill_id%%.*}"
skill="${skill_id#*.}"

mkdir -p "core/skills/$domain/$skill"
$EDITOR "core/skills/$domain/$skill/SKILL.md.tera"
$EDITOR manifests/skills.yaml
$EDITOR manifests/plugins.yaml
```

After editing, run governance and render validation:

```bash
bash scripts/ci/skill-governance-audit.sh --update-counts
bash scripts/ci/skill-governance-audit.sh
agent-runtime render --product codex --update-golden
agent-runtime render --product claude --update-golden
agent-runtime render --product hermes --update-golden
bash scripts/ci/sandbox-install-rehearsal.sh
bash tests/runtime-smoke/run.sh --mode deterministic --domain "$domain"
```

Use the full gate before committing or opening a PR:

```bash
bash scripts/ci/all.sh
```

## Workflow

1. Resolve the canonical ID and reject project-local overlay requests.
2. Inspect existing `core/skills/<domain>/`, `manifests/skills.yaml`, and
   `manifests/plugins.yaml` before editing.
3. If the domain is new, stop and get explicit approval because it changes both
   product surfaces.
4. Create `SKILL.md.tera` with the standard front matter, H1, Contract,
   Entrypoint, Workflow, and Boundary sections.
5. Add the v2 skill manifest entry for every supported product. Name the parent
   intent, a direct example request, and why this is a user outcome. New skills
   must never enter `migration.pending_disposition` or the #562 ledger.
6. Add plugin containment for the skill. For existing domains, do not touch
   unrelated plugin metadata.
7. Add reminder metadata only when agents should invoke the skill as a workflow.
8. Add runtime-smoke matrix coverage and any case-runner probe needed to prove
   the skill surface.
9. Run `bash scripts/ci/skill-governance-audit.sh --update-counts` after the
   source, manifest, sandbox, and runtime-smoke surfaces are in place.
10. Render both products, refresh golden snapshots, run governance audit, and
   run the relevant smoke checks.
11. Leave staging, commit, PR creation, and issue state updates to the caller's
    delivery workflow.

## Boundary

This skill owns scope judgment and the ordered lifecycle checklist for adding a
repo-owned skill. It does not hide broad YAML rewrites inside prose. If repeated
adds require structured mutation, dry-run/apply plans, or reference graph
output, extract that behavior to released `nils-cli` first and then call it
from this workflow.
