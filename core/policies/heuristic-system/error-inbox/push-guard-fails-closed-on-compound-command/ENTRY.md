# Push guard fails closed on a compound cd-and-push command

## Status

- Status: open
- First observed: 2026-07-25
- Area: block-unsafe-default-delivery; managed-worktree feature-branch push
- Severity: medium

## Signal

Delivering a managed-worktree feature branch, this push was blocked:

```text
cd <worktree> && git push -u origin fix/<slug>
-> Default-branch delivery target could not be resolved safely.
```

The immediately following bare command, same checkout and same remote, was
admitted and succeeded:

```text
git -C <worktree> push -u origin refs/heads/fix/<slug>:refs/heads/fix/<slug>
-> [new branch] fix/<slug> -> fix/<slug>
```

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-25)
- Both commands ran in the same turn against the same checkout and SSH remote and
  returned opposite verdicts.
- `refs/remotes/origin/HEAD` resolved to `refs/remotes/origin/main` in both the
  worktree and the primary checkout, so the cached-default fallback added for
  `#652` was available. This is **not** the `#652` slow-`ls-remote` timeout.
- Cause: the guard's `simple_shell_words` returns `None` on any shell control, so
  `&&` makes the push refspec unparseable; with no parseable refspec the guard
  cannot prove the target is non-default and fails closed with
  `AMBIGUOUS_REASON`.

## Impact

The compound form is the natural shape an agent writes when the host exposes no
per-call working-directory parameter and the shell cwd resets between calls, so a
routine feature-branch delivery can look unshippable. The block text names only
the direct-main route (`forge-cli repo push-default`) and never states the actual
remedy — issue a bare, parseable push — so the guard steers a caller toward
default-branch delivery when a plain feature refspec would have been allowed.
That is the diagnosability gap already noted on `#652` before it closed, now with
a concrete second trigger.

## Current Workaround

Issue the push as a single bare command with a fully-qualified explicit refspec
and no shell control, binding the checkout with `git -C <path>`:

```text
git -C <worktree> push -u origin refs/heads/<branch>:refs/heads/<branch>
```

Never wrap it in `cd … && …`, a pipe, or a subshell.

## Promotion Criteria

Promote when the guard either distinguishes "command not parseable" from
"destination genuinely ambiguous" for an otherwise explicit non-default push, or
its block text names the bare-parseable-push remedy alongside the direct-main
route. A sanctioned feature-branch push verb (`#653`) would remove the need for a
raw `git push` here entirely and would also satisfy this entry.

## Next Action

Add the bare-parseable-push remedy to the `AMBIGUOUS_REASON` block text, and
comment this second trigger on `#653` so the push-verb design accounts for it.
Related: `managed-worktree-lockout-pushguard-ssh` criterion (c), and the closed
`#652`.
