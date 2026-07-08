# forge-cli pr review thread-file null-thread response

Date: 2026-06-27
Surface: `forge-cli pr review --submit-review --thread-file`
Version: `forge-cli 1.17.0`
Reviewable: sympoies/symphony-board#502

During PR delivery, a testing specialist finding needed an actionable GitHub
review thread. The first thread file anchored the finding to
`packages/ui/scripts/render-smoke.mjs` line 1777, which was useful context but
not inside the PR's changed diff hunk.

Command shape:

```sh
FORGE_BOT_PROFILE=review-testing-bot forge-cli --provider github pr review 502 \
  --repo sympoies/symphony-board \
  --decision comments-only \
  --submit-review \
  --thread-file review-testing-threads.json \
  --comment-file review-testing.md \
  --lens testing \
  --format json
```

Observed error:

```json
{"schema_version":"cli.forge-cli.error.v1","ok":false,"error":{"code":"software_error","message":"github review-thread response is missing an expected field","details":{"detail":"missing=/data/addPullRequestReviewThread/thread/id; response=Object {\"data\": Object {\"addPullRequestReviewThread\": Object {\"thread\": Null}}}"}}}
```

`forge-cli pr review-threads list 502` then reported `total=0` and
`unresolved=0`, so no resolvable thread was left behind.

Workaround used: omit `line` from the thread file and create a file-level
thread. The retry succeeded and returned thread id `PRRT_kwDOSuLIhc6Mn0F8`
with `subject_type=FILE`; that thread was later resolved after the repair.

Impact: an invalid or out-of-diff line anchor can surface as a low-level
`software_error` from a null GitHub GraphQL thread response instead of a
local validation error or provider error explaining that the line is not
threadable. Agents should use file-level threads for cross-hunk findings or
anchor only to changed diff lines until the CLI reports this case explicitly.
