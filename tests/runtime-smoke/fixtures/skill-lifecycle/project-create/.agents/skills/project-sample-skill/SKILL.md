---
name: project-sample-skill
description:
  Fixture project-local skill used to prove create-project-skill governance
  coverage.
---

# Sample Project Skill

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

- `.agents/skills/project-sample-skill/scripts/project-sample-skill.sh`

## Workflow

1. Run the fixture script.
2. Verify the marker exists.
