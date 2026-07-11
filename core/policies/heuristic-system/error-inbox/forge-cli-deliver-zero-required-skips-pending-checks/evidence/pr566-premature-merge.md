# forge-cli zero-required pending-check merge reproduction

- Date: 2026-07-11
- Surface: `forge-cli 1.21.15`
- Repository PR: `graysurf/agent-runtime-kit#566`
- Command: `forge-cli pr deliver --kind docs ...`
- Result: the `wait_checks` step returned `state=success`, `required_count=0`, and `pending=[]` while its own `checks[]` rows for `scripts/ci/all.sh` and CodeQL were still `pending`. The macro immediately promoted and squash-merged the PR.
- Merge SHA: `8bc81045ff4d07a0e7fe1d765f0cd7cd38c15160`
- Independent hold: the caller continued polling workflow runs `29148841982` and `29148841380` after merge; both eventually completed successfully.
- Impact: this is an actual premature merge, not only an early `--no-merge` return.
