# Second occurrence: forge-cli squash merge did not auto-close linked issue

Date: 2026-06-14

Repository: `sympoies/nils-alfredworkflow`

Observed sequence:

- PR #194 was created by `forge-cli pr deliver --kind refactor --no-merge` with a rendered PR body containing `Closes #190`.
- `gh pr view 194 --json closingIssuesReferences` reported issue #190 in `closingIssuesReferences`.
- `forge-cli pr merge 194 --method squash` succeeded with merge SHA `3a8b28dd52b5a0eefdfcf99a5fc9c96113d49dfa` at `2026-06-14T06:21:12Z`.
- Immediately after merge, both `forge-cli issue view 190` and `gh issue view 190 --json state,closedAt` reported issue #190 still open (`closedAt=null`).
- The issue was closed manually with a closeout comment plus `forge-cli issue close 190`; final `gh issue view 190` reported `state=CLOSED`, `closedAt=2026-06-14T06:21:54Z`.

Interpretation:

- This is a second occurrence of a regular issue-backed forge-cli delivery where a body closing keyword did not close the issue by the time the delivery workflow reached close verification.
- Because manual close happened within roughly one minute, this still does not fully rule out delayed GitHub auto-close processing.
- The next reproduction should wait several minutes after merge and capture the issue timeline before manual close, unless the user explicitly requires immediate closeout.
