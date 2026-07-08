# PR #388 did not auto-close issue #381

Date: 2026-06-15

During `graysurf/agent-runtime-kit` issue #381 delivery, PR #388 was merged by
`forge-cli pr merge 388 --method squash`. The GitHub-stored PR body contained
`Fixes #381`.

Observed timeline:

- PR #388 merged successfully with merge SHA `ce2c6bd`.
- Immediate `gh issue view 381 --json state,closed,closedAt` returned
  `state=OPEN`, `closed=false`.
- A second check about 10 seconds later still returned `state=OPEN`,
  `closed=false`.
- The issue was closed manually with a closeout comment and
  `forge-cli issue close 381`.
- Final verification returned `state=CLOSED`, `closed=true`,
  `closedAt=2026-06-15T13:31:56Z`.

This is another occurrence of the regular issue-backed PR auto-close gap
described by the existing case.
