---
name: removable-project-skill
description:
  Fixture project-local skill used to prove remove-project-skill dry-run
  coverage.
---

# Removable Project Skill

## Contract

Prereqs:

- Run inside a fixture project git work tree.

Inputs:

- None.

Outputs:

- A deterministic fixture marker.

Failure modes:

- The fixture script is missing.

## Scripts

- `.agents/skills/removable-project-skill/scripts/removable-project-skill.sh`

## Workflow

1. Run the fixture script.
2. Verify the marker exists.
