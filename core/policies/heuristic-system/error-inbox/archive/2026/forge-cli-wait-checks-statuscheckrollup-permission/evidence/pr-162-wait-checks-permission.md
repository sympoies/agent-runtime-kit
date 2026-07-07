# PR 162 wait-checks permission evidence

## Context

- Repo: sympoies/agent-console
- PR: https://github.com/sympoies/agent-console/pull/162
- Date: 2026-07-07 UTC
- CLI: forge-cli 1.20.18

## Observation

During PR #162 delivery, both `forge-cli pr checks 162` and
`forge-cli pr wait-checks 162` failed with the same GitHub GraphQL backend
error:

```text
GraphQL: Resource not accessible by integration (repository.pullRequest.statusCheckRollup.nodes.0.commit.statusCheckRollup)
```

The provider checks were still readable through GitHub CLI:

```text
gh pr checks 162 --repo sympoies/agent-console
build  pass  45s  https://github.com/sympoies/agent-console/actions/runs/28891511625/job/85705136458
build  pass  45s  https://github.com/sympoies/agent-console/actions/runs/28891514548/job/85705146719
```

`gh pr view 162 --json statusCheckRollup` also showed both `ci / build`
check runs completed with `SUCCESS`.

## Workaround used

I used the read-only `gh pr checks` / `gh pr view` status evidence, confirmed
`forge-cli pr review-threads list 162` reported `unresolved: 0`, confirmed
`forge-cli pr tasks 162` reported `unchecked: 0`, then merged through
`forge-cli pr merge 162 --method squash`. The merge succeeded and returned
merge commit `4132d2780794a108293fd0d9bfc066957dfaa8a8`.
