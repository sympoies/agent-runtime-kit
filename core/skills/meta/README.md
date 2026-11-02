# Meta Skills

The `meta` domain contains seven global repository maintenance skills.
`manifests/skills.yaml` is the machine-checkable catalog.

| Skill | Purpose |
| --- | --- |
| [bootstrap](./bootstrap/) | Run the repository-owned bootstrap workflow. |
| [deploy](./deploy/) | Run the repository-owned deployment workflow. |
| [release](./release/) | Run the repository-owned release workflow. |
| [execution-capsule](./execution-capsule/) | Prepare an authorized local operation for direct or supervised execution. |
| [repo-docs-boundary](./repo-docs-boundary/) | Maintain README, contributor setup and durable docs placement. |
| [setup-project](./setup-project/) | Adopt `.agents/` conventions and create or remove project-local skills. |
| [worktree-triage](./worktree-triage/) | Classify and safely clean managed worktrees. |

Managed kit catalog changes use the repo-local
[`project-runtime-development`](../../../.agents/skills/project-runtime-development/SKILL.md)
skill and the [managed lifecycle procedures](../../../docs/source/development-reference.md#skill-lifecycle-changes).
Version adoption uses repo-local
[`project-version-baseline`](../../../.agents/skills/project-version-baseline/SKILL.md).
Runtime refresh uses the public
[`scripts/sync-runtime-surfaces.sh`](../../../scripts/sync-runtime-surfaces.sh)
and its [setup/sync reference](../../../docs/source/development-reference.md#refreshing-runtime-surfaces).

## Release Note: Catalog Consolidation (#347)

The global meta catalog shrinks from 13 entries to 7. These global names are
removed; use their existing procedure owners:

| Removed global name | Procedure now lives in |
| --- | --- |
| `meta:nils-cli-bump` | Repo-local `project-version-baseline` authorized `adopt` mode and [version workflows](../../../docs/source/nils-cli-version-workflows.md#workflow-c--adopt-a-stable-release). Default check/report stay verify-only. |
| `meta:create-skill` | Repo-local `project-runtime-development` and [managed creation](../../../docs/source/development-reference.md#managed-skill-creation). |
| `meta:remove-skill` | Repo-local `project-runtime-development` and [managed removal](../../../docs/source/development-reference.md#managed-skill-removal). |
| `meta:create-project-skill` | `meta:setup-project`, [create reference](./setup-project/references/create.md), and `setup-project/scripts/create-project-skill.sh`. |
| `meta:remove-project-skill` | `meta:setup-project` and its [remove reference](./setup-project/references/remove.md). |
| `meta:sync-runtime-surfaces` | The public `scripts/sync-runtime-surfaces.sh` and [setup/sync reference](../../../docs/source/development-reference.md#refreshing-runtime-surfaces). |

After merge, the maintainer must sync runtime surfaces from a durable primary
checkout so installed catalogs and retired surfaces converge. This change does
not activate the new catalog in live runtime homes.
