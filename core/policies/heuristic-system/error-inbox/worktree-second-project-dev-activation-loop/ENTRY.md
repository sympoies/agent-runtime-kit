# Second managed worktree stuck in project-dev missing-activation loop

## Status

- Status: open
- First observed: 2026-07-16
- Area: cli
- Severity: medium
- Versions: agent-docs 1.22.7, git-cli 1.22.7 (nils-cli 1.22.7)
- Upstream issue: not yet filed

## Signal

During a single live session, `project-dev` auto-activation worked for the
**first** managed worktree of `serenvia/agent-console` but then appeared to
refuse for a **second, newly created** worktree. The pattern: after
`git-cli worktree add` + `EnterWorktree`, the pre-edit / pre-bash hook reported
`project-dev` as unactivated for the new checkout path, and every attempt to
run the printed `agent-docs session activate` command was itself blocked as a
"bare agent-docs invocation" — an unrecoverable `missing-activation` loop.

Root mechanism (confirmed by reproducing and escaping it on 2026-07-16, same
tool versions): the loop is triggered specifically because `EnterWorktree` pins
the Bash-tool CWD into the not-yet-activated worktree. The pre-bash hook is
CWD-scoped, so with the shell pinned inside an unactivated checkout it blocks
**all** bash — including the very `agent-docs session activate` command needed
to clear the state, and even read-only `ls`. It is not that activation is
impossible for the second worktree; it is that you cannot reach a shell context
from which activation is allowed while the session is entered into it.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-16). No `skill-usage`
  envelope was retained; attach redacted evidence later via
  `heuristic-inbox ingest-evidence` if the loop recurs and can be captured.
- Environment: agent-docs / git-cli 1.22.7 on Linux; `AGENT_HOME` at
  `<workspace>/.local/state/agent-runtime-kit`.
- The first worktree of the same repo activated and edited normally in the same
  session; only the second concurrent worktree exhibited the refusal, which
  points at per-checkout-path activation state that does not initialize cleanly
  for an additional worktree created later in the session (suspected
  one-time / residual session state rather than a repo-content problem).

## Impact

When an agent needs a second managed worktree of the same repository in one
session (a normal pattern when the primary checkout is dirty and blocked by the
`unowned-changes` guard), the second worktree can become permanently
un-actionable: no bash mutation and no edits pass the `project-dev` gate. The
only observed escape was manual host-side intervention, so an unattended agent
would be hard-blocked.

## Current Workaround

Confirmed self-serve recovery (no host-side reset needed): **activate the
worktree before entering it, and do not stay entered while activating.**

1. `git-cli worktree add <slug>` (allowed even from a blocked checkout).
2. From the parent-anchored shell — NOT inside an `EnterWorktree` session —
   run the printed `agent-docs ... session activate` and `... preflight`
   commands with an explicit `cd <worktree-path> &&` prefix so the hook's
   CWD-scoped check sees the matching checkout. (If already stuck inside the
   worktree, `ExitWorktree` with `keep` first; the shell returns to the parent
   checkout where bash works again.)
3. Do the edits via **absolute worktree paths** with the file tools, and run
   commands `cd <worktree> && …`, without re-entering the worktree via
   `EnterWorktree`. Edits and bash then pass the guard normally.

The earlier host-side reset (remove the stale worktree checkout and re-sync
`main`) also works but is unnecessary once the above is used. Do not copy raw
hook logs or tokens into this entry.

## Promotion Criteria

Promote once the root cause is confirmed and a durable fix lands: either
`agent-docs session activate` reliably initializes activation state for a
second/Nth worktree created mid-session, or the hook surfaces a deterministic,
self-serve recovery instead of an unrecoverable `missing-activation` loop.
Reproduce with two managed worktrees of one repo in a single session, validate
the second activates and edits cleanly, then link the fix from this entry.

## Next Action

Repro is confirmed and a self-serve workaround exists (above). File an upstream
nils-cli / agent-docs issue proposing that the pre-bash hook special-case its
own `agent-docs session activate` command — it must never block the exact
command it prints as the remedy, even when the pinned CWD is an unactivated
checkout — so an agent entered into a fresh worktree can always recover without
`ExitWorktree`. Link the issue here when filed.
