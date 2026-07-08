# GraphQL-backed gh lookups can fail after shared quota exhaustion

## Status

- Status: open
- First observed: 2026-06-14
- Area: ci
- Severity: low

## Signal

During a release, a 25s `gh run list` poll loop waited ~10 min for
`release.yml`, then a resume step ran `gh release view --json assets,url`. That
view call failed with `GraphQL: API rate limit already exceeded for user ID
...`. The installed GitHub CLI's `gh run list` path uses the REST/core Actions
runs endpoint, so the poll loop was not the GraphQL consumer. The observed
failure was the later GraphQL-backed release lookup hitting a shared GraphQL
budget that was already exhausted, while the REST `core` budget still had
~4,800 remaining.

## Evidence

- Raw record: not captured; manual diagnosis of gh GraphQL rate-limit exhaustion, 2026-06-14
- Evidence: `evidence/rate-limit-and-rest-fallback.md`
- `project-bump-version-tag-release.sh --from-tap` aborted at
  `assert_release_assets_available` (which uses `gh release view --json`,
  GraphQL) with "GitHub Release ... is not available" — a false negative; the
  release was fully published.
- `gh api rate_limit --jq .resources` showed `graphql.remaining = 0` (reset
  ~134s out) while `core.remaining = 4821`.
- Cross-checking the release via REST (`gh api repos/<repo>/releases/tags/<tag>`)
  succeeded immediately — confirmed the release + 8 assets were present.
- Evidence: `evidence/forge-pr-ready-graphql-rate-limit.md` — during
  sympoies/symphony-board PR #228 delivery, `forge-cli pr ready` failed with
  GraphQL quota exhausted while REST/core quota still had thousands of requests
  remaining; waiting for the GraphQL reset and retrying let the PR ready/checks
  sweep/merge path complete.

## Impact

A shared GraphQL budget can be exhausted by other `gh` or API consumers while
REST/core Actions polling still has plenty of quota. A subsequent
GraphQL-backed call (`gh release view`, `gh pr view`, `gh search`) can then fail
with a misleading "not available" / not-found error rather than an explicit
rate-limit message — risking a wrong conclusion (e.g. "the release did not
publish").

## Current Workaround

- Prefer the harness's background run-completion notifications over tight
  command polling where possible.
- Before GraphQL-backed `gh` or forge PR lifecycle calls, gate on the **free**
  `gh api rate_limit` endpoint (it does not consume quota); sleep until
  `graphql.remaining` recovers before the next GraphQL-backed call.
- Cross-check release/asset existence with REST (`gh api
  repos/<repo>/releases/tags/<tag>`, `core` budget) when GraphQL is exhausted.

## Promotion Criteria

Promote when release/draft/PR lookup helpers and forge PR lifecycle helpers
either back off on the `rate_limit` endpoint before GraphQL-backed calls or
route release existence checks through REST, so a drained GraphQL budget no
longer surfaces as a false "not available" or blocks ready/merge flows.

## Next Action

Gate GraphQL-backed release/draft/PR lookups and forge PR lifecycle calls on the
free rate_limit endpoint, and fall back to REST for release asset existence
checks.

Lifecycle link: `sympoies/nils-cli#1051 (tracking issue filed 2026-07-08)`
