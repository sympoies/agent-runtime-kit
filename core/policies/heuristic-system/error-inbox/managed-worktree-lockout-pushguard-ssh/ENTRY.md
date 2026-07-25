# Deletions-first lockout and slow-SSH push-guard fail-closed during managed-worktree delivery

## Status

- Status: open
- First observed: 2026-07-17
- Area: managed-worktree delivery; checkout-lease / intent hooks; block-unsafe-default-delivery push guard
- Severity: high

## Signal

Task: retire the public `nils-agent-console` counterpart in `serenvia/agent-console`
(delete a boundary doc + a project skill, trim `AGENTS.md`/`DEVELOPMENT.md`, add a
devlog entry, deliver by PR). A routine docs/skill removal became a multi-hour
session because of two guard interactions plus activation churn.

1. **Deletions-first lockout.** In a fresh managed worktree I ran raw
   `git rm <tracked files>` **before** any tool edit. Those staged deletions were
   "unowned" to `checkout-lease-guard`, which then blocked **every** mutation on
   that checkout: Edit/Write tools, `git checkout -- <paths>` (restore),
   `semantic-commit` of the already-staged deletions, and `git-cli worktree remove`.
   The #651 sole-`--abort` carve-out did not apply (no in-progress operation).
   The only escape was to abandon the worktree and start a fresh one.

2. **Push guard fail-closed on slow SSH.** `git push -u origin <feature-branch>`
   was blocked by `block-unsafe-default-delivery`, which resolves the remote
   default branch via a live `git ls-remote --symref <push-url> HEAD` inside a
   fixed 4s total `GitProbe` budget. The SSH handshake to GitHub was ~2.5–3.6s;
   the harness-invoked probe exceeded budget -> `default_branch()` returned "" ->
   `AMBIGUOUS_REASON`. HTTPS `ls-remote` was ~1s and repo-local SSH ControlMaster
   dropped my own probe to ~1s, but neither helped the harness-invoked probe.
   `forge-cli` has no feature-branch push (only `repo push-default`), so there was
   no sanctioned agent push path.

3. **Activation churn.** `project-dev` activation went "stale" after each tracked
   mutation, forcing re-activate + re-read-preflight before nearly every mutating
   step (see #601).

## Evidence

- Raw record: manual diagnosis, 2026-07-17 (`serenvia/agent-console`, retire-public-counterpart).
- Tracked in `agent-runtime-kit` issues: #652 (push guard slow `ls-remote`),
  #646 (governed dirty-checkout adoption), #601 (progressive intent hooks),
  #651 (merged sole-git-recovery carve-out).
- Corroboration comments posted on #652 and #646.
- Timings: SSH `ls-remote` 3.63s cold / ~2.5s warm; HTTPS ~0.8–1.1s;
  SSH+ControlMaster ~1.0s.

## Impact

An ordinary docs/skill-removal delivery took multiple hours. The deletions-first
lockout can strand a managed worktree with no in-place recovery (it must be
destroyed). The push guard can make feature-branch delivery impossible from an
agent session on a slow-SSH host, forcing a manual out-of-band push.

## Current Workaround

- In a managed worktree, make **all tool edits first** (they become "owned"), then
  do file deletions + `semantic-commit` in the **same** Bash invocation so
  `checkout-lease-guard` evaluates once while only owned changes are present.
  Never leave raw-shell tracked-file mutations (e.g. `git rm`) sitting before a
  tool edit.
- If a checkout is already locked by unowned changes, do not fight it: create a
  fresh `git-cli worktree add` and redo the work in the correct order.
- If the push guard fails closed, have the maintainer push the feature branch from
  a non-agent shell (the in-session `!` prefix bypasses the PreToolUse Bash
  hooks), then continue with `forge-cli pr create`.

## Promotion Criteria

Promote when: (a) governed in-place adoption of a session's own pre-existing /
unowned changes exists (#646), covering staged raw-git deletions, not only
`--abort` recovery; (b) the push guard tolerates slow default-branch resolution
via a cached-default fallback, tunable budget, or fast transport (#652); and
(c) a sanctioned feature-branch push path exists for agents.

### Re-triage 2026-07-26 — first-hand status per criterion

Not promotable: (b) is met, (a) is met but inert by default, (c) is unmet.
#646, #652 and #601 are all CLOSED, so issue state alone is misleading here.

- **(a) partially effective.** `git-cli worktree adopt-dirty` / `dirty-snapshot` /
  `revoke-dirty` are released verbs, and `checkout-lease-guard` implements the
  bound adoption path. But that path is gated on
  `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION=1` (`dirty_adoption_enabled()`), which is
  **unset on this host** and is not set by the agent-hook config, the Claude
  settings bundle, or the policy bundle. Until it is enabled, the deletions-first
  lockout still has no in-place recovery and the "destroy the worktree" workaround
  above remains the real path.
- **(b) met, verified.** `block-unsafe-default-delivery` now carries
  `cached_default_branch` / `resolve_default_branch`. Confirmed live on
  2026-07-26: a bare fully-qualified feature refspec pushed successfully over the
  same SSH remote that used to fail closed.
- **(c) unmet, verified.** `forge-cli repo` still exposes only `push-default`, and
  `git-cli` has no push group, so a raw `git push` is still the only feature-branch
  route. #653 is still OPEN with no movement since 2026-07-17.

A second, distinct push-guard false positive was found during the same 2026-07-26
session and split out to its own case rather than folded in here: a compound
`cd <worktree> && git push …` fails closed because shell control makes the refspec
unparseable — see `push-guard-fails-closed-on-compound-command`. That is not the
#652 timeout, and it is not (c).

## Next Action

Two independent unblockers, either of which narrows this entry:

1. Decide whether `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION` should default to on
   (or be set in the shipped policy bundle). The #646 mechanism is inert without
   it, so (a) currently buys nothing at runtime.
2. Land a sanctioned feature-branch push verb for (c) — tracked in #653.

Until then keep the workaround above, and prefer a single bare push command with a
fully-qualified refspec (`git -C <path> push -u origin refs/heads/X:refs/heads/X`)
over any `cd … && git push` form.
