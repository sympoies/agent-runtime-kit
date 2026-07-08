# forge-cli PR review-thread surface gaps

## Status

- Status: promoted
- First observed: 2026-06-16
- Area: forge-cli
- Severity: medium

## Signal

`forge-cli` review-thread surfaces have gaps a PR delivery or thread-sweep
agent can hit:

1. `pr review-threads list --dry-run` is NOT dry — it issues a live `gh`
   PR-view call before the dry-run plan branch, so it depends on network /
   `gh` auth / a live PR. Sibling `pr` subcommands (`checks` / `create` /
   `resolve` / `reply`) plan offline under `--dry-run`.
2. The `pr review-threads list` JSON carries only each thread's first comment
   (author / body / url) — not later replies or the diff hunk — so triage that
   depends on a reply or the hunk needs a separate fetch.
3. `pr review --submit-review --thread-file` can return a low-level
   `software_error` when a requested line-level thread is not actually
   threadable by GitHub (observed with a line outside the PR diff hunk). The
   GraphQL mutation returned `thread: null`, and the CLI reported
   "github review-thread response is missing an expected field" instead of a
   local validation or actionable provider error.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-06-16).
- Evidence: `evidence/review-threads-dryrun-repro.md` (dry-run live-call repro).
- Evidence: `evidence/review-thread-null-response.md` (`--thread-file` line
  anchor outside the diff hunk returns `thread: null` / `software_error` in
  `forge-cli` v1.17.0; file-level retry succeeds).
- Evidence: `evidence/review-thread-null-response-v1-20-13.md` (`--thread-file`
  line-level thread creation still returns `thread: null` / `software_error` in
  `forge-cli` v1.20.13; summary-only provider review was the delivery
  workaround).
- Version: `forge-cli` v1.9.1.
- Later observation: `forge-cli` v1.17.0 still has the `--thread-file` null
  response failure shape.
- Later observation: `forge-cli` v1.20.13 still has the `--thread-file` null
  response failure shape and may leave a partial empty provider review event.
- Repro (gap 1): `forge-cli --provider github --repo graysurf/agent-runtime-kit
  --dry-run --format json pr review-threads list 9999999` returns a live
  GraphQL error ("Could not resolve to a PullRequest 9999999"), while
  `pr checks 9999999 --dry-run` and `pr review-threads resolve/reply --dry-run`
  return offline `plan` envelopes.
- Upstream: sympoies/nils-cli#887 (dry-run live call) and sympoies/nils-cli#888
  (umbrella: first-comment-only payload + host-aware writes, text-id,
  PR-id validation, JSON error contract from #883 review).
- In-repo fixes/workarounds landed: agent-runtime-kit#416 (smoke dropped the
  `list` dry-run probe; skill documents normalized `resolved`/`outdated` fields
  + full-context fetch) and #417 (surface-snapshot signatures, `deliver-pr` /
  `close-pr` floors to `>=1.9.1`, convergence-policy wiring, acceptance-matrix).

## Impact

A "deterministic" runtime-smoke probe over `list --dry-run` fails closed on a
host without network / `gh` auth / a live PR; an agent triaging threads off the
`list` payload alone can disposition on incomplete evidence (missing replies or
diff hunks); and an agent posting actionable review findings can lose time to a
non-actionable `software_error` when a line-level thread anchor is invalid for
GitHub's review-thread mutation.

## Current Workaround

- Do not dry-run-probe `list`; probe only `resolve` / `reply` (which plan
  offline) plus the documented-surface assertions (agent-runtime-kit
  runtime-smoke does this).
- Before dispositioning a thread whose finding depends on a reply or the diff,
  fetch full context (open the thread `url`, or `gh api` the thread comments /
  PR diff).
- Filter on the normalized `resolved` / `outdated` envelope fields, not the raw
  GraphQL `isResolved` / `isOutdated`.
- For `pr review --thread-file`, use file-level threads for cross-hunk findings
  and line-level threads only for changed diff lines until the CLI reports
  out-of-diff anchors explicitly.

## Promotion Criteria

Promote/close when nils-cli#887 (dry-run honored for `list`), #888 (incl.
replies/hunks in the `list` payload), and the `--thread-file` invalid-anchor /
null-thread response path are fixed in a `forge-cli` release and the
agent-runtime-kit nils-cli pin is bumped.

## Next Action

None. Resolved: pr review-threads list --dry-run now plans offline (verified on forge-cli v1.20.19); umbrella hardening delivered via sympoies/nils-cli#887 and #888 (both closed) plus in-repo agent-runtime-kit#416/#417. Residual first-comment-only list payload and out-of-diff --thread-file line anchor remain covered by the documented workarounds (fetch full context; use file-level threads for cross-hunk findings).

Lifecycle link: `sympoies/nils-cli#887 + #888 (both closed)`

## Archive

- Archived: 2026-07-08
- Reason: Completed entry archived out of the active error inbox.
- Durable link: `sympoies/nils-cli#888`
