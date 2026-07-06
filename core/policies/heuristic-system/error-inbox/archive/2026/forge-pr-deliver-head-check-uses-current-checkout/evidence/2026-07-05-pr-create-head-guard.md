# forge-cli pr create current-HEAD guard recurrence

- Date: 2026-07-05
- Repo: `sympoies/agent-console`
- Surface: `forge-cli pr create --head feat/issue-17-attachments-title-workdirs --dry-run`
- Requested head: `feat/issue-17-attachments-title-workdirs`, already pushed and up to date with `origin/feat/issue-17-attachments-title-workdirs`.
- Current checkout: clean managed worktree on `feat/issue-17-pr-create`, which had no upstream tracking branch.
- Result: `head_not_pushed` with message `HEAD has no upstream tracking branch (push the branch first)`.
- Workaround: run the same `forge-cli pr create` from a checkout whose current HEAD is the requested pushed branch. The dry-run then passed and live create opened `sympoies/agent-console#22`.
- Inference: the current-HEAD pushed-state guard applies to `pr create` as well as the previously recorded `pr deliver` case; passing `--head` alone is not sufficient.
