# Push guard fails closed on a compound cd-and-push command

## Status

- Status: promoted
- First observed: 2026-07-25
- Resolved: 2026-08-03
- Area: block-unsafe-default-delivery; managed-worktree feature-branch push
- Severity: medium
- Durable link: `https://github.com/sympoies/agent-runtime-kit/pull/11`
- Durable link: `https://github.com/sympoies/agent-runtime-kit/issues/10`
- Durable link: `https://github.com/sympoies/agent-runtime-kit/issues/7`

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

Superseded — publish the branch through the governed surface instead:

```text
git-cli push --format json
```

The former workaround was a single bare command with a fully-qualified explicit
refspec and no shell control
(`git -C <worktree> push -u origin refs/heads/<branch>:refs/heads/<branch>`).
That shape is still classifiable, but it is no longer the route to reach for.
Either way, never wrap a push in `cd … && …`, a pipe, or a subshell.

## Promotion Criteria

Promote when the guard either distinguishes "command not parseable" from
"destination genuinely ambiguous" for an otherwise explicit non-default push, or
its block text names the bare-parseable-push remedy alongside the direct-main
route. A sanctioned feature-branch push verb (`#653`) would remove the need for a
raw `git push` here entirely and would also satisfy this entry.

## Resolution

Promoted 2026-08-03. Every branch of the criteria is now satisfied, and by the
route the entry preferred — the sanctioned push verb — so the raw-push remedy is
no longer the primary path.

- **Sanctioned push verb exists.** `git-cli push` shipped in nils-cli v1.25.13,
  which `docs/source/nils-cli-pin.yaml` pins as both `minimum_supported_tag` and
  `validated_tag`. It pins the destination to
  `refs/heads/<branch>:refs/heads/<branch>`, refuses the remote's default branch,
  and sets the upstream to the branch's own ref, so a feature-branch publish no
  longer needs a raw `git push` at all. This is the `#653` ask.
- **Parseability is distinguished from genuine ambiguity.** Every reason now
  leads with `[default-delivery: blocked]` or `[default-delivery: unverified]`,
  so a caller can tell "forbidden" from "restate this so it can be checked" —
  only the second is worth retrying with a different shape.
- **The block text names the real remedy.** `REMEDY_SHELL_CONTEXT` states that a
  `cd`, `pushd`, `source`, or Git environment assignment earlier in the command
  line is what makes the rest unclassifiable, and gives the worked
  `git -C <path>` form. `REMEDY_FEATURE_PUSH` names `git-cli push` for a branch
  publish and keeps `forge-cli repo push-default` scoped to the default branch,
  which was the mis-steer this entry reported.

Consumer alignment followed in the delivery skills, so the workflow an agent
reads and the surface the guard demands now agree; before that, the guard named
`git-cli push` while no skill did.

The compound `cd … && git push` form is still refused, and that remains correct:
the shell control genuinely makes the refspec unparseable. The difference is that
the refusal now says so and names what to run instead.

Related: `managed-worktree-lockout-pushguard-ssh` criterion (c), which this same
release satisfies — that entry stays open on its criterion (a).
