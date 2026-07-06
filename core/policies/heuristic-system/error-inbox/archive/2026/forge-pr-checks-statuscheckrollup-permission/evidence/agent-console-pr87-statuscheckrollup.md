# forge-cli statusCheckRollup Permission Evidence: sympoies/agent-console#87

## Context

- Date: 2026-07-05.
- Repo/PR: `sympoies/agent-console#87`.
- PR head: `07d14250f3f4b4ffce30b7c0c47df99fe76a5738`.
- Related delivery: fix new-session initial prompts so the prefilled prompt is submitted by sending Enter after session creation.

## Observed Failure

During PR delivery, the canonical `forge-cli` check gates failed on a mergeable PR with passing GitHub Actions checks:

```text
forge-cli --provider github pr wait-checks 87 --repo sympoies/agent-console --format json
```

returned:

```text
GraphQL: Resource not accessible by integration (node.statusCheckRollup.nodes.0.commit.statusCheckRollup)
```

The direct check snapshot failed with the same error:

```text
forge-cli --provider github pr checks 87 --repo sympoies/agent-console --format json
```

## Workaround Used

The delivery used read-only GitHub CLI surfaces to confirm the exact PR head and checks:

```text
gh pr view 87 --repo sympoies/agent-console --json headRefOid,isDraft,mergeStateStatus,reviewDecision,statusCheckRollup,url
gh pr checks 87 --repo sympoies/agent-console --watch --interval 10
```

The fallback confirmed:

- `headRefOid` matched `07d14250f3f4b4ffce30b7c0c47df99fe76a5738`.
- Two `ci / build` check runs completed successfully.
- PR merge state was `CLEAN` before merge.

The PR was then merged through `forge-cli pr ready` and `forge-cli pr merge`, preserving provider mutation through the standard primitive.

## Outcome

This reinforces the existing open heuristic case that `forge-cli pr checks` / `wait-checks` can fail on GitHub App `statusCheckRollup` permissions and need a fallback keyed to the exact PR head SHA.
