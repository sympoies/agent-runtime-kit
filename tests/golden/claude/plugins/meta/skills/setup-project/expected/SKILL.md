---
name: setup-project
description: Set up repository .agents conventions and create or remove project-local skills.
---

# Setup Project

## Contract

Run inside the target Git repository unless another target is explicitly named.
Choose the requested procedure and load only its reference:

- Adopt repository `.agents/` conventions: `references/adoption.md`.
- Create a project-local skill or Claude discovery bridge: `references/create.md`.
- Remove a project-local skill and its approved wrappers: `references/remove.md`.

Preview adoption and removal before applying. Existing files are never
overwritten without explicit approval. Preserve historical records unless their
cleanup is separately authorized.

## Entrypoint

The bundled helpers live under this skill's `scripts/` directory:

- `scripts/setup-project.sh` for adoption (dry-run by default).
- `scripts/create-project-skill.sh` for creation (use `--dry-run` to preview).

Resolve helper paths from the installed skill directory and run them with the
target repository as the working directory. The selected reference owns flags,
prerequisites, failure handling and acceptance checks.

## Workflow

1. Resolve the target root with `git rev-parse --show-toplevel` and inspect its
   `.agents/skills`, `.agents/scripts`, policy and validation entrypoints.
2. Load the adoption, create or remove reference for the requested outcome.
3. Follow its inventory, approval, execution and validation steps.
4. Report changed paths, retained history, validation and remaining work.

## Boundary

This skill owns repository adoption and project-local skills. Host setup and
runtime synchronization use the kit's documented setup/sync scripts. Managed
runtime-kit catalog changes use `docs/source/development-reference.md`. Do not mutate global runtime homes or
runtime-kit manifests during a consuming project's local skill operation.
