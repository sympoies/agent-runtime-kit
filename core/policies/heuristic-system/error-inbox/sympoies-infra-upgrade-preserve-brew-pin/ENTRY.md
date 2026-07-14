# sympoies-infra nils-cli fleet upgrade fails when the formula is pinned

## Status

- Status: open
- First observed: 2026-07-14
- Area: sympoies-infra deploy-only fleet convergence
- Severity: medium
- Cluster: managed-homebrew-pin-preservation

## Signal

The sympoies-infra deploy-only workflow invokes the nils-cli fleet upgrader
without accounting for an existing `brew pin nils-cli`. The first v1.21.39
fleet convergence run failed on sympoies because Homebrew correctly refused to
upgrade the pinned formula. After manually preserving the pin across the
upgrade, the rerun converged successfully.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-14)
- Failed fleet convergence:
  <https://github.com/graysurf/sympoies-infra/actions/runs/29319974867>
- Successful rerun after pin-preserving recovery:
  <https://github.com/graysurf/sympoies-infra/actions/runs/29320089643>
- Related local release case:
  `error-inbox/release-skill-preserve-brew-pin/ENTRY.md`

## Impact

Deploy-only cannot reliably converge a managed host that intentionally pins
nils-cli. The workflow fails mid-rollout and leaves the fleet on mixed versions
until an operator performs host-specific recovery.

## Current Workaround

On each pinned host, record that the formula is pinned, temporarily unpin it,
upgrade and verify the target version, then restore the pin. Rerun deploy-only
and require the fleet convergence job to pass.

## Promotion Criteria

Promote after the fleet upgrader restores the original pin on both success and
failure, verifies the requested nils-cli version, and has regression coverage
for pinned and unpinned hosts.

## Next Action

Teach the fleet upgrader to preserve the existing Homebrew pin across upgrade success and failure, with regression coverage.
