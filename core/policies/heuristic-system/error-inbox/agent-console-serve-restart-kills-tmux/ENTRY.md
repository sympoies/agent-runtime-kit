# agent-console serve restart can kill tmux sessions

## Status

- Status: open
- First observed: 2026-07-05
- Area: agent-console deployment; systemd user service; tmux session durability
- Severity: high

## Signal

During the `sympoies/agent-console#26` deployment, upgrading the installed
`agent-session` binary required bringing the live `agent-console-serve.service`
daemon onto the new version. The unit uses systemd's default
`KillMode=control-group`, and `systemctl --user status` showed tmux session
servers in the same unit cgroup as the `agent-session serve` daemon.

Attempting the narrowest available restart path,
`systemctl --user kill --kill-who=main -s SIGKILL agent-console-serve.service`,
still caused systemd to clear the cgroup: the tmux server disappeared and the
pre-existing session changed from `running` to `stopped`.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-05)
- `systemctl --user show agent-console-serve.service` reported
  `KillMode=control-group`, `Restart=on-failure`, and the service control group
  under the user app slice.
- `systemctl --user status agent-console-serve.service` listed both the main
  `agent-session serve --bind 127.0.0.1:8781 --machine sympoies` process and a
  tmux server for an existing `hs-codex-*` session in that same cgroup.
- `systemctl --user set-property --runtime agent-console-serve.service
  KillMode=process` failed with `Cannot set property KillMode`.
- After `systemctl --user kill --kill-who=main -s SIGKILL
  agent-console-serve.service`, `tmux ls` returned `no server running`, and
  `agent-session list --format json` reported that the previously running
  session was `stopped`.
- The daemon did restart on the new installed binary and the console deploy
  completed, but session durability was lost for the pre-existing session.

## Impact

The mobile console is meant to supervise durable tmux-backed sessions. A routine
daemon upgrade or deploy restart can silently kill every live session if tmux
servers stay in the serve unit's control group. Future agents may choose
`restart`, `try-restart`, or main-process kill expecting daemon-only impact and
instead terminate active user work.

## Current Workaround

Before restarting `agent-console-serve.service`, treat the action as
session-destructive unless the unit or launcher has been fixed and verified.
Drain or explicitly delete/accept loss of live sessions first, then restart the
daemon and verify `agent-session list --format json`.

For deployments that only change the edge/UI, restart
`agent-console-edge.service` only; do not restart `agent-console-serve.service`.

## Promotion Criteria

Promote after one of these is implemented and validated:

- The serve unit/launcher starts tmux servers outside the serve service cgroup,
  so daemon restarts leave active tmux sessions running.
- The unit uses an intentional `KillMode`/scope design with a documented,
  tested daemon-only restart path.
- The deployment runbook explicitly marks serve daemon restarts as
  session-destructive and requires draining/confirmation first.

## Next Action

Update the agent-console serve unit or launcher so daemon restarts do not keep tmux servers in the service control-group, then document the safe restart path.
