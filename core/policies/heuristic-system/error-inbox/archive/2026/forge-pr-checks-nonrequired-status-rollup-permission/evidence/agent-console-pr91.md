# PR #91 Non-Required Check Readback Evidence

During delivery of `sympoies/agent-console` PR #91 on 2026-07-05,
`forge-cli pr wait-checks 91 --provider github --required-only false --timeout 30m --interval 20s --format json`
failed with:

```text
GraphQL: Resource not accessible by integration (node.statusCheckRollup.nodes.0.commit.statusCheckRollup)
```

The PR had no required checks, but two visible non-required GitHub Actions
`ci / build` check runs existed. The workflow used `gh pr checks 91 --watch`
and `gh pr checks 91 --json name,state,bucket,workflow,startedAt,completedAt,link`
as a read-only fallback; both build checks reported `SUCCESS` before merge.

Delivery outcome:

- PR: https://github.com/sympoies/agent-console/pull/91
- Merge commit: `711ec3cffd91a36f430dce650cc23bff65879914`
- Tool version: `forge-cli 1.20.13`
- Skill usage record: project `sympoies__agent-console`,
  `20260706-054912-skill-usage`, status `pass`, with the fallback recorded as a
  delivery-phase `external_service` failure handled by `gh pr checks`.
