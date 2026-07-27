# Meta Skills

The `meta` domain contains runtime-kit maintenance and repository operation
skills. These skills expose deliberate runtime maintenance, project adoption,
skill catalog lifecycle, execution handoff, and repository operation outcomes.
They are not application-domain implementation skills.

`manifests/skills.yaml` is the machine-checkable inventory. This README is the
human routing index for choosing the right meta skill without scanning every
`SKILL.md`.

## Summary

| Series | Skills | Use when |
| --- | ---: | --- |
| Runtime maintenance | 3 | Refreshing installed surfaces, converging a nils-cli pin, or triaging worktrees |
| Execution handoff | 1 | Packaging an authorized local operation as a private reusable script with direct and supervised run paths |
| Repo operation dispatchers | 4 | Running repo-owned bootstrap, deploy, release, or adoption workflows |
| Skill lifecycle | 4 | Creating or removing managed runtime-kit skills or consuming-repo project skills |
| Repository documentation | 1 | Auditing or applying README, contributor setup, and durable docs placement |

## Runtime Maintenance

| Skill | Purpose |
| --- | --- |
| [sync-runtime-surfaces](./sync-runtime-surfaces/) | Refreshes active runtime-kit managed surfaces into local Codex and Claude runtime homes. |
| [nils-cli-bump](./nils-cli-bump/) | Advances the validated nils-cli release and refreshes consumers while preserving an explicit compatibility floor. |
| [worktree-triage](./worktree-triage/) | Scans local git worktrees and classifies merged, rescue, and review-needed branches. |

## Execution Handoff

| Skill | Purpose |
| --- | --- |
| [execution-capsule](./execution-capsule/) | Prepares a private reviewable script and manifest for direct operator or Codex-supervised execution. |

## Repo Operation Dispatchers

| Skill | Purpose |
| --- | --- |
| [bootstrap](./bootstrap/) | Dispatches project bootstrap requests to a repository-owned `.agents/scripts/bootstrap.sh` implementation. |
| [deploy](./deploy/) | Dispatches deploy requests to a repository-owned `.agents/scripts/deploy.sh` implementation. |
| [release](./release/) | Dispatches release requests to a repository-owned `.agents/scripts/release.sh` implementation. |
| [setup-project](./setup-project/) | Guides a repository into the `.agents/` conventions used by retained dispatcher skills. |

## Skill Lifecycle

| Skill | Purpose |
| --- | --- |
| [create-skill](./create-skill/) | Adds a repo-owned runtime-kit skill with source, manifests, product render surfaces, acceptance coverage, and governance validation. |
| [remove-skill](./remove-skill/) | Removes a repo-owned runtime-kit skill with dry-run-first reference audit and retained historical records. |
| [create-project-skill](./create-project-skill/) | Scaffolds a consuming-repo project-local skill under `.agents/skills` without mutating runtime-kit manifests. |
| [remove-project-skill](./remove-project-skill/) | Removes a consuming-repo project-local skill with dry-run-first inventory and explicit approval for cleanup. |

## Repository Documentation

| Skill | Purpose |
| --- | --- |
| [repo-docs-boundary](./repo-docs-boundary/) | Audits or maintains README, contributor setup, and durable documentation placement under active repository policy. |
