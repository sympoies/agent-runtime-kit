# Release script PR body uses unchecked task-list items that deliver gate rejects

## Status

- Status: promoted
- First observed: 2026-06-14
- Area: forge-cli
- Severity: medium

## Signal

Diagnosed manually during the nils-cli v1.2.0 release. The PR-mode release path
(`project-bump-version-tag-release.sh`) died at its own delivery step:

```
error: unchecked_task_items: 3 unchecked task-list item(s) in the PR/MR description; disposition each ... or pass --allow-unchecked-tasks with --allow-unchecked-tasks-reason to bypass
error: forge-cli pr deliver failed; release branch chore/release-X-Y-Z left in place for recovery
```

## Evidence

- Raw record: `evidence/deliver-error.md` (ingested console output from the
  failed release deliver + the offending generated PR body; manual diagnosis
  2026-06-14, no structured skill-usage record captured).
- Versions: nils-cli host 1.1.0 (release tooling), target release v1.2.0.
- Root cause: `project-bump-version-tag-release.sh` generated the release PR
  body with three `- [ ]` task-list items under `## Test plan` (CI green, tag +
  release.yml, tap), then called `forge-cli pr deliver` (no
  `--allow-unchecked-tasks`). Those items describe **post-merge** pipeline steps
  that can never be checked at merge time, so the `unchecked_task_items` merge
  gate (forge-cli rule 13, shipped v1.0.17) rejects them — blocking **every**
  PR-mode release at the deliver step.
- Repro: run the release script in PR mode on any branch; it fails at
  `forge-cli pr deliver` regardless of the actual diff.

## Impact

Any PR-mode nils-cli release deadlocks at delivery until the body is edited or
the gate is bypassed. The release tooling is incompatible with its own merge
gate.

## Current Workaround

Two-part, both applied for v1.2.0:

1. Recovery of the stuck release: edit the open release PR body to convert the
   `- [ ]` items into plain bullets, then `forge-cli pr merge`, fast-forward
   `main`, tag, push, and resume the tap stage via `--from-tap --version X.Y.Z`.
2. Durable fix (merged, pending release): nils-cli PR #838
   (`chore(release): write release PR body as plain bullets`) changes the
   generated body to plain bullets so the deliver task gate is not tripped. It
   is on `sympoies/nils-cli` `main` but landed **after** the v1.2.0 tag, so it
   ships in the next release (> v1.2.0); until then, releases run with the
   fixed script from `main` or apply the recovery above.

## Promotion Criteria

Archive as promoted once a nils-cli release > v1.2.0 includes #838 and a
subsequent PR-mode release completes without manual body editing.

## Next Action

None. sympoies/nils-cli#838 merged the plain-bullets release PR body fix; the current release script carries the plain-bullets guard, and later PR-mode release bumps such as sympoies/nils-cli#1029 have merged successfully.

Lifecycle link: `https://github.com/sympoies/nils-cli/pull/838`

## Archive

- Archived: 2026-07-06
- Reason: Fix shipped and subsequent PR-mode releases merged
- Durable link: `https://github.com/sympoies/nils-cli/pull/1029`
