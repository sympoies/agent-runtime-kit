# plan-issue terminal task stale reproduction

- Date: 2026-07-11
- Surface: `plan-issue 1.21.15`
- Tracker: `graysurf/agent-runtime-kit#563`
- Closeout PR: `graysurf/agent-runtime-kit#566`
- Result: successful `record close --bundle` patched `Status` and inserted `Branch/commit/PR`, but retained the pre-close `Next task: run strict close-ready and canonical tracker closeout`.
- Workaround: the terminal follow-up patch changed `Next task` to `none` before PR #566 was merged.
- Final provider audit: all seven lifecycle roles were visible-clean.
