# Meta Skills

The `meta` domain contains runtime-kit maintenance and repository operation
skills. These skills expose deliberate runtime maintenance, project adoption,
skill catalog lifecycle, and repository operation outcomes.
They are not application-domain implementation skills.

`manifests/skills.yaml` is the machine-checkable inventory. This README is the
human routing index for choosing the right meta skill without scanning every
`SKILL.md`.

## Summary

| Series | Skills | Use when |
| --- | ---: | --- |
| Runtime maintenance | 3 | Refreshing installed surfaces, converging a nils-cli pin, or triaging worktrees |
| Repo operation dispatchers | 4 | Running repo-owned bootstrap, deploy, release, or adoption workflows |
| Skill lifecycle | 4 | Creating or removing managed runtime-kit skills or consuming-repo project skills |

## Runtime Maintenance

| Skill | Purpose |
| --- | --- |
| [sync-runtime-surfaces](./sync-runtime-surfaces/) | Refreshes active runtime-kit managed surfaces into local Codex and Claude runtime homes. |
| [nils-cli-bump](./nils-cli-bump/) | Proposes the coordinated runtime-kit update when a new pinned nils-cli release ships. |
| [worktree-triage](./worktree-triage/) | Scans local git worktrees and classifies merged, rescue, and review-needed branches. |

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
