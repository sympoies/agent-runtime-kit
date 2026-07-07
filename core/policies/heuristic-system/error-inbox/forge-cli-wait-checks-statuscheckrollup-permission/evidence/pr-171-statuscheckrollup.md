# PR #171 statusCheckRollup permission recurrence

During `sympoies/agent-console` PR #171 delivery on 2026-07-07, `forge-cli` again hit the GitHub GraphQL status-check rollup permission gap.

Observed commands:

- `forge-cli --provider github --repo sympoies/agent-console --format json pr wait-checks 171 --required-only false --timeout 20m --interval 20s`
- `forge-cli --provider github --repo sympoies/agent-console --format json pr checks 171 --required-only true`

Both failed with:

```text
GraphQL: Resource not accessible by integration (repository.pullRequest.statusCheckRollup.nodes.0.commit.statusCheckRollup)
```

Workaround used:

- `gh pr checks 171 --repo sympoies/agent-console --watch --interval 20`
- `gh pr checks 171 --repo sympoies/agent-console`

The `gh pr checks` surface showed both `build` jobs as `pass`, so delivery continued through the normal thread/task/review gates and PR #171 merged successfully.
