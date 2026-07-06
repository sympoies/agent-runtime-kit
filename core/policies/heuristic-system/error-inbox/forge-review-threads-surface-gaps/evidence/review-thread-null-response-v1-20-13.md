# forge-cli pr review thread-file null-thread response (v1.20.13)

Surface: `forge-cli pr review --submit-review --thread-file`

Session: graysurf/agent-runtime-kit PR #517 delivery on 2026-07-06.

While posting a red-team review finding, the review-thread mutation failed with
the same null-thread response shape already tracked by
`forge-review-threads-surface-gaps`:

```text
github review-thread response is missing an expected field
missing=/data/addPullRequestReviewThread/thread/id
response={"data":{"addPullRequestReviewThread":{"thread":null}}}
```

The attempted thread targeted a line-level review coordinate for a finding that
spanned policy/protocol wording, and GitHub did not return a creatable review
thread. The command also left a partial empty provider review event.

Workaround used:

- Posted the red-team finding as a summary-only provider review.
- Repaired the wording.
- Posted a red-team `follow-up-pass` review.
- Recorded the delivery failure in the session `skill-usage` record:
  `$HOME/.local/state/agent-runtime-kit/out/projects/graysurf__agent-runtime-kit/20260706-143041-skill-usage/skill-usage.record.json`.

Relevant PR evidence:

- PR #517 merged by squash commit `88bac8977d80b686fc198f8a8d13ef3dee0358d0`.
- Red-team finding review:
  `https://github.com/graysurf/agent-runtime-kit/pull/517#pullrequestreview-4633543528`
- Red-team follow-up review:
  `https://github.com/graysurf/agent-runtime-kit/pull/517#pullrequestreview-4633552150`
