# PR #254 zero-required check evidence

- Date: 2026-07-11
- Repository: `sympoies/agent-console`
- Pull request: `#254`
- Installed surface: `forge-cli 1.21.16`
- `forge-cli pr deliver --no-merge` exited successfully with `required_count=0` while two visible GitHub Actions `build` jobs were still pending.
- Pending workflow runs: `29156505230` and `29156500571`.
- The delivery owner held ready/merge and ran `forge-cli pr wait-checks 254 --required-only false --timeout 30m --interval 10s`.
- That command waited about 25 seconds and returned success only after both build jobs completed successfully.
- Ready/merge proceeded after the all-check wait, the mandatory specialist review gate, and zero unresolved review threads/tasks.

This independently reproduces the zero-required premature-success signal and validates `pr wait-checks --required-only false` as a bounded workaround for a repository with visible non-required CI.
