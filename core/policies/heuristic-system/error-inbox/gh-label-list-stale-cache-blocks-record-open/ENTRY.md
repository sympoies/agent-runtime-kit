# gh issue list --label refuses requests on a stale cached X-Ratelimit-Remaining: 0 (cli/cli#12812), blocking plan-issue record open

## Status

- Status: open
- First observed: 2026-06-14
- Area: plan-issue record open dedup; gh HTTP cache; label-filtered gh issue list
- Severity: medium

## Signal

`plan-issue record open` failed for ~1h with `record-open-list-failed` /
`GraphQL: API rate limit already exceeded for user ID`, while `gh api
rate_limit` showed a full GraphQL bucket (5000/5000) and both REST
(`gh api repos/.../issues?labels=`) and a no-label `gh issue list` succeeded
throughout. The failure survived a primary-window reset and long quiet windows,
so it was not the live rate limit.

Root cause (cli/cli#12812): `gh` caches a `SearchType` introspection GraphQL query
with `X-Gh-Cache-Ttl: 24h`. If cached while the rate limit was momentarily
exhausted, the cached response carries a stale `X-Ratelimit-Remaining: 0` for up
to 24h. `gh issue list --label …` reads the stale cached header and refuses to
send the request; REST and cache-bypassing paths stay healthy. `record open`'s
duplicate-tracker pre-check is exactly such a label-filtered `gh issue list`, so
it is blocked while everything else works. Burst retries do not help (and waste
time) because the block is a stale cache entry, not a live limit. The older
closed umbrella report cli/cli#8321 observed the symptom but did not track this
cache mechanism; use cli/cli#12812 for fix status.

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/graysurf__agent-runtime-kit/20260614-174237-skill-usage/skill-usage.record.json`
- Summary: linked `skill-usage.record.v1` envelope; raw runtime details remain in the evidence location.

## Impact

Any nils-cli surface whose dedup or lookup runs `gh issue list --label …`
(`plan-issue record open`, and potentially other plan-issue / forge-cli
label-filtered queries) can be hard-blocked for up to 24h on a host whose `gh`
cache was poisoned, even though the account's real rate limit is healthy. Agents
mis-diagnose this as an abuse / quota limit and waste time on backoff retries
that never recover. Observed cost this session: ~1h of retries and quiet windows.

## Current Workaround

1. Diagnose: if `gh issue list --label` reports a rate limit but `gh api
   rate_limit` shows quota remaining and REST (`gh api repos/<owner>/<repo>/issues?labels=…`)
   or a no-label `gh issue list` both succeed, it is the poisoned cache.
2. Clear it: `grep -rl "X-Ratelimit-Remaining: 0" ~/.cache/gh/ 2>/dev/null | xargs rm -f`
   (macOS path here is `~/.cache/gh`). The blocked command works immediately
   after — no waiting.
3. Do not burst-retry the failing command; retries only restate the same stale
   cache and waste time.

Verified this session: removing the single poisoned cache file unblocked
`gh issue list --label workflow::tracking` and `record open` (issue #352) at once.

## Promotion Criteria

Promote when the nils-cli `record open` dedup is changed to avoid the gh
`SearchType` cache path — REST `issues?labels=` (verified working here, with
REST pull-request rows filtered out via their `pull_request` key) or an
exhaustive no-label list filtered client-side with explicit pagination / limit
coverage — and/or it detects the stale-cache symptom and surfaces the
cache-clear remedy instead of the generic `record-open-list-failed`. Link the
upstream nils-cli fix from this entry. Track upstream gh fix at cli/cli#12812.

## Next Action

Fix nils-cli record-open dedup to avoid the gh SearchType cache path: use REST
`issues?labels=` while excluding PR rows, or use an exhaustive no-label issue
list with explicit pagination before client-side filtering. Detect the
stale-cache symptom and surface the cache-clear remedy.

Lifecycle link: `sympoies/nils-cli#1050 (tracking issue filed 2026-07-08)`
