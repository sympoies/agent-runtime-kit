# Agent Write-Location Contract

## Purpose

Every file an agent or agent tool produces belongs to one declared class with
one owner, one env selector, and one retention bound. Owners implement against
this table; cleaners only enforce the retention a class declares and never
reverse-engineer a tool's paths. Tracking:
[#302](https://github.com/sympoies/agent-runtime-kit/issues/302).

## Root

All agent-produced writes go under one root, `AGENT_HOME` (default
`${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit`). Moving the root,
for example to another disk on a shared agent host, must be a single env change;
no class may hard-code the default.

## Classes

| Class | Path | Selected by | Owner (writes / reclaims) | Content | Retention |
| --- | --- | --- | --- | --- | --- |
| evidence | `${AGENT_HOME}/out/projects/<owner__repo>/<ts>-<topic>/` | `AGENT_HOME` via `agent-out project` | `agent-out` allocates; `agent-out cleanup` reclaims | Small kept artifacts: logs, screenshots, reports, receipts | Long (default 30 days; class-configurable); may be promoted to an evidence archive. No build trees. |
| scratch | `${AGENT_HOME}/out/scratch/<owner__repo>/<ts>-<topic>/` | `AGENT_HOME` via `agent-out project --kind scratch` (planned) | `agent-out` | Rebuildable run intermediates: fixtures, unpacked archives, one-off clones | Short (default 3 days) |
| build | `${AGENT_HOME}/build/<worktree-slug>/` or `${AGENT_HOME}/build/run/<run-id>/` | `CARGO_TARGET_DIR` and equivalents, exported by the worktree or run owner | `git-cli` for worktree builds; `agent-out` for run builds | Compiler and bundler output | Deleted with its worktree or run; never inside `out/` |
| tmp | `${AGENT_HOME}/tmp/<session-id>/` | `TMPDIR`, injected by the session launcher | `agent-session` creates at start, reclaims at stop | Harness scratchpads, `mktemp` output | Removed at session stop plus a grace period (default 24 h); orphans swept when the session record is gone |
| worktrees | `${AGENT_HOME}/worktrees/<repo>-<hash>/<slug>` | `AGENT_HOME` | `git-cli worktree`; `worktree-triage` | Managed checkouts | Delivered or idle policy (unchanged) |
| tool state | `${XDG_STATE_HOME}/<tool>/` or a tool env such as `AGENT_SESSION_STATE_DIR` | Tool-specific env, XDG fallback | The tool | Durable tool state with its own bound | Owner-declared bound (size or age) |

Evidence and worktrees are shipped today. The `scratch` selector, the `build`
exports, and the per-session `TMPDIR` are owner implementations that follow
this contract; until an owner ships its selector, keep build output out of
evidence runs (rule 2) and prefer a worktree-local build directory. Until the
scratch kind ships, allocate temporary and debug artifacts with
`agent-out project --topic <topic> --mkdir`; never hand-build an `out/scratch`
directory.

## Rules

1. A tool that writes outside these classes must declare a class and an env
   override. Do not add a hard-coded `~/.local/state/<dir>`,
   `${AGENT_HOME}/<dir>`, or `/tmp/<fixed-name>` path; derive the path from the
   class selector (`AGENT_HOME`, `TMPDIR`, or the tool's own env).
2. Build output never goes into `out/`. Point `CARGO_TARGET_DIR` and its
   equivalents at the `build` class; a worktree-local `target/` is acceptable
   only because it is deleted with the worktree.
3. `TMUX_TMPDIR` (sockets) stays separate from `TMPDIR` so socket paths stay
   short.
4. Harness homes (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`) are out of scope for this
   contract version because of login and broker risk.
5. Each class has one reclaiming owner. Other cleaners may only enforce that
   class's declared retention; they never invent new path rules.
6. On macOS, the per-session `TMPDIR` applies only to agent sessions, never to
   launchd services.

## Lint

`scripts/ci/write-location-audit.py` (gate position 15) flags new literals of
`~/.local/state/<name>`, `$HOME/.local/state/<name>`, `${AGENT_HOME}/<name>`, and
fixed `/tmp/<name>` roots in tracked tool sources and runbooks. A literal passes
when it names a declared class root above or an entry in
`scripts/ci/write-location-allow.toml`; every allowlist entry carries a reason,
and a stale entry fails the gate. Each finding names the class to use instead.

## Changes

Record each change to a class, path, selector, owner, or default retention here
with its tracking reference.

- Initial contract adopted from #302 as designed.
