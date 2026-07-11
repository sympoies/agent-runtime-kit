# PR #245 zero-required check convergence

- Repository: `sympoies/agent-console`
- PR: `#245`
- Observed: 2026-07-11
- Command: `forge-cli pr deliver --no-merge`
- Result: exit 0 with `wait_checks.ok=true`, `required_count=0`, and a visible `ci / build` row still `pending`.
- Delivery action: held promotion and merge, then polled all checks separately. Two `ci / build` runs later completed successfully before review and merge.
- Impact confirmation: this independently reproduces the existing case on a second PR and shows the macro still cannot be treated as all-check convergence when branch protection declares no required checks.
