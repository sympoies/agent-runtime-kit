---
name: remove-skill
description: >
  Remove a repo-owned runtime-kit skill with a dry-run-first active reference
  audit and retained historical plan records.
---

# Remove Skill

## Contract

Prereqs:

- Run from the `agent-runtime-kit` repository root.
- The target is a repo-owned managed skill in `manifests/skills.yaml`.
- The first pass is dry-run only. File mutation requires explicit apply
  approval from the user or the active delivery plan.
- `agent-runtime` is installed from the released nils-cli package and available
  on `PATH`.

Inputs:

- Canonical skill ID in the form `<domain>.<skill>`.
- Optional explicit cleanup approval for retained historical docs. Historical
  plan records are retained by default.

Outputs:

- A dry-run list of active files and reference classes that would change.
- After apply approval: removed `core/skills/<domain>/<skill>/` source,
  `manifests/skills.yaml` entry, `manifests/plugins.yaml` containment, product
  render metadata, golden snapshots, sandbox expected skill pins, runtime-smoke
  cases, hook/reminder metadata, and maintained docs references.
- A reviewed `manifests/skill-dispositions.yaml` row is retained when the skill
  belongs to the frozen #562 migration cohort; it records destination,
  replacement/compatibility needs, and live cleanup instead of deleting history.
- A validation summary proving no active references remain.

Failure modes:

- The target skill is ambiguous or not represented in the manifest.
- Active references remain after apply.
- The workflow would edit historical `docs/plans/**` records without explicit
  cleanup approval.
- The validation gate fails after removal.

## Entrypoint

Start with a dry-run reference inventory:

```bash
skill_id="<domain>.<skill>"
domain="${skill_id%%.*}"
skill="${skill_id#*.}"

rg -n "$skill_id|$skill" \
  core manifests targets tests docs/source SUPPORT_MATRIX.md DEVELOPMENT.md
```

Classify matches before editing:

- source skill directory
- skill manifest entry
- plugin containment
- product plugin metadata or target path
- rendered build output and golden snapshots
- sandbox expected skill lists
- runtime-smoke matrix and case-runner probes
- hook/reminder metadata
- maintained docs
- retained historical records under `docs/plans/**`

After apply approval and edits:

```bash
bash scripts/ci/skill-governance-audit.sh --update-counts
bash scripts/ci/skill-governance-audit.sh
agent-runtime render --product codex --update-golden
agent-runtime render --product claude --update-golden
agent-runtime render --product hermes --update-golden
bash scripts/ci/sandbox-install-rehearsal.sh
bash tests/runtime-smoke/run.sh --mode deterministic --domain "$domain"
bash scripts/ci/all.sh
```

## Workflow

1. Confirm the skill ID exists exactly once in `manifests/skills.yaml`.
2. Build the dry-run inventory with `rg` and classify every active reference.
3. Exclude `docs/plans/**` from default mutation. Keep those records as
   historical evidence unless the user explicitly asks for cleanup.
4. Present the planned active delta and stop unless apply approval is already
   part of the active plan.
5. Remove the source directory and active manifest entry. If the ID belongs to
   the frozen migration cohort, update its disposition row to `reviewed`; never
   delete or replace a baseline row to make a new pending skill fit.
6. Remove plugin containment and product metadata for the target skill.
7. Remove rendered/golden/sandbox/runtime-smoke/hook/reminder references.
8. Run `bash scripts/ci/skill-governance-audit.sh --update-counts` to refresh
   maintained active skill-count surfaces without touching historical
   `docs/plans/**` records.
9. Re-run the reference inventory and fail if active references remain outside
   the allowed historical set.
10. Run governance, render, sandbox, runtime-smoke, and full CI validation.

## Boundary

This skill owns safe removal sequencing and the decision to retain historical
records. It does not own a general-purpose deletion engine. If removal needs a
stable dry-run/apply planner or machine-readable reference graph, implement and
release that primitive in `sympoies/nils-cli`, then pin the consumed binary in
`manifests/skills.yaml`.
