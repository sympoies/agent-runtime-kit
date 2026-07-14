# Agent Console deploy-only leaves the serve daemon on the previous binary

## Status

- Status: open
- First observed: 2026-07-14
- Area: agent-console deployment and systemd serve lifecycle
- Severity: high

## Signal

The Agent Console deploy-only workflow successfully installed nils-cli v1.21.39
but did not restart `agent-console-serve.service`. The long-running daemon
therefore continued serving the previous binary until it was restarted
manually. Production account-switch acceptance passed only after explicitly
activating the released daemon binary.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-14)
- Fleet convergence run:
  <https://github.com/graysurf/sympoies-infra/actions/runs/29320089643>
- Feature tracker and production validation:
  <https://github.com/sympoies/agent-console/issues/307>
- Existing session-durability blocker:
  <https://github.com/sympoies/agent-console/issues/122>

## Impact

The installed CLI and the daemon actually serving Agent Console can silently
diverge. New UI/API behavior may then reach an older daemon contract, while the
green deploy-only run gives false confidence that production is on the released
version.

## Current Workaround

Treat a serve restart as session-destructive until agent-console#122 is fixed.
Drain or otherwise protect live tmux sessions, restart the user service, verify
its main process uses the intended binary, and rerun the scoped production
acceptance. Edge/UI-only changes should continue to avoid the serve restart.

## Promotion Criteria

Promote after a daemon activation path preserves existing tmux sessions,
deploy-only invokes that path when the installed binary changes, and rollout
validation proves the running daemon version rather than only the installed
file version.

## Next Action

Add a session-safe daemon activation phase after agent-console#122 provides a restart path that preserves tmux sessions.
