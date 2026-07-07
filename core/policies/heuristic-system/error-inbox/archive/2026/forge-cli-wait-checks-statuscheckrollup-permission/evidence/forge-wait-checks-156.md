# forge-cli wait-checks statusCheckRollup recurrence on PR #156

During sympoies/agent-console PR #156 delivery on 2026-07-07,
`forge-cli pr wait-checks 156 --format json` failed with:

```text
GraphQL: Resource not accessible by integration (repository.pullRequest.statusCheckRollup.nodes.0.commit.statusCheckRollup)
```

The fallback `gh pr checks 156 --watch --interval 10` returned two `build`
jobs, both passing after the amended commit. `forge-cli pr review-threads list
156 --format json` reported `unresolved: 0`, and `forge-cli pr tasks 156
--format json` reported `unchecked: 0`. The PR was then readied and squash
merged through `forge-cli pr ready 156` and `forge-cli pr merge 156`.

This matches the existing workaround: use the simpler `gh pr checks` surface
only to establish CI status, then keep the normal `forge-cli` thread/task/merge
gates.
