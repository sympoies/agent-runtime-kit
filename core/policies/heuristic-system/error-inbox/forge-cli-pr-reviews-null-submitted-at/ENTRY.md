# forge-cli pr reviews rejects a complete GitHub review snapshot

## Status

- Status: open
- First observed: 2026-07-16
- Area: forge-cli
- Severity: medium

## Signal

During final review convergence for two merged pull requests, the released
`forge-cli 1.22.7` surface rejected `pr reviews` before returning a usable
snapshot:

```text
forge-cli --format json --repo sympoies/nils-cli pr reviews 1249
forge-cli --format json --repo serenvia/agent-console pr reviews 337
```

Both commands returned `review_snapshot_incomplete` with
`field=review.submittedAt`. Direct read-only GitHub REST inspection of the
reviews returned for each pull request showed non-null `submitted_at` on every
returned review. This points to a normalization or GraphQL snapshot edge case,
potentially an unpublished pending review, rather than missing data in the
submitted-review list.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-16)
- Installed surface: `forge-cli 1.22.7`
- Reproduced repositories: `sympoies/nils-cli` PR 1249 and
  `serenvia/agent-console` PR 337
- CLI result: `review_snapshot_incomplete`, `field=review.submittedAt`
- Cross-check: GitHub REST `pulls/<number>/reviews` returned non-null
  `submitted_at` for every listed review on both pull requests.
- Upstream issue: none opened; this retained case is the current owner.

## Impact

PR delivery cannot use the normal strict `forge-cli pr reviews` convergence
readback for affected pull requests. Agents must switch to a lower-level
provider query and manually correlate review state and head SHA, increasing the
chance of incomplete or inconsistent closeout evidence.

## Current Workaround

Use read-only GitHub REST review inspection for the affected pull request, for
example `gh api repos/<owner>/<repo>/pulls/<number>/reviews --paginate` with a
field-limited projection. Verify review state, submission timestamp, commit ID,
and the pull request head SHA without printing whole provider objects. Keep the
`forge-cli` failure in the closeout report rather than treating the fallback as
proof that the higher-level primitive succeeded.

## Promotion Criteria

Promote after a `forge-cli` regression fixture reproduces the null or missing
`submittedAt` shape, normalization distinguishes pending reviews from malformed
submitted reviews, both affected snapshot classes return a deterministic
contract, and the fix is validated against a real pull request before this
entry is archived.

## Next Action

Reproduce GitHub review normalization with pending or null `submittedAt`
values, identify whether the GraphQL response includes a pending review absent
from the REST submitted-review list, and add regression coverage before
changing the parser.
