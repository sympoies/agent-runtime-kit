# No governed path publishes the first branch of an empty remote

## Status

- Status: open
- First observed: 2026-08-28
- Area: `block-unsafe-default-delivery` default-branch resolution; `git-cli push`
- Severity: high

## Signal

Migrating `night-owl-cli` off a retired GitHub account into a newly created,
empty `sympoies/night-owl-cli`. Every surface refused the initial publish, and
each refusal's hint named a step that cannot succeed on an empty remote, so the
guidance formed a closed loop:

```text
git push origin main:main            -> [default-delivery: unverified]; use git-cli push / forge-cli repo push-default
git-cli push                         -> default-branch-unresolved; run `git remote set-head origin --auto`
git remote set-head origin --auto    -> error: Cannot determine remote HEAD
git-cli push --expect-default main   -> default-branch-unverifiable; run `set-head --auto` (same dead end)
forge-cli repo push-default --dry-run -> provider returned an invalid default branch ref
```

The scope was wider than the default branch: on an empty remote *no* branch of
any name could be published. Verified with a scratch clone on `feat/x` against
an empty bare remote, which failed the same way.

Three further defects surfaced during the diagnosis, all downstream of one root
cause — `resolve_default_branch()` returning `""` collapsed several unrelated
situations into a single unverified verdict:

1. **Primary-worktree conflation.** Resolution required the cached
   `refs/remotes/<remote>/HEAD` to equal the primary worktree's branch. A
   primary checkout parked on a feature branch therefore made *every* raw push
   in that repository unverified, including a plain feature refspec.
2. **Dead `cached_timeout` flag.** `resolve_default_branch()` returned `False`
   for its second tuple element on all three paths, so the `if cached_timeout:`
   block in `push_targets_default()` was unreachable — and that block held the
   only explicit-refspec fallback for an unresolved default. A vestige of the
   `#652` live-`ls-remote` design after resolution became local-only.
3. **Non-branch destinations refused.** `explicit_branch_refspec_target()`
   returned `""` for wildcards, for destinations needing a current-branch
   lookup, and for destinations that provably are not branches. A
   `refs/tags/...` destination cannot move a branch whatever the default is, but
   was still unverified.

## Evidence

- Raw record: manual diagnosis, 2026-08-28 (`sympoies/night-owl-cli` migration).
- Tracked in `agent-runtime-kit` issues: #61.
- Same command, only the cache differing, on one repository:
  `git push origin refs/tags/v1.0.0:refs/tags/v1.0.0` was unverified with no
  cached `origin/HEAD` and admitted after `git remote set-head origin -a`.
- Versions: nils-cli 1.27.18; hook at 9d91069.
- Related: #21 (an unresolvable target reported as a policy refusal rather than
  a failure to classify) — same asymmetry, a distinct trigger.

## Impact

A repository created from an agent session could not receive its first branch
through any governed surface, and the only escape was to leave the session and
push from a non-agent shell. Separately, a primary checkout parked on a feature
branch — an ordinary state — locked raw pushes out of the whole repository while
reporting a cause that pointed nowhere.

## Current Workaround

None needed once the fixes below ship. Before them, the initial publish had to
be run from a non-agent shell; the in-session `!` prefix does not help, because
it runs through the same PreToolUse hooks.

## Promotion Criteria

Promote when all three hold:

1. the guard distinguishes a corroborated default from an uncorroborated one and
   from no evidence at all, so a parked primary checkout no longer blocks
   unrelated pushes;
2. a destination that provably is not a branch is classified without resolving
   the default branch;
3. a governed surface can publish the first branch of a remote proven empty, and
   the refusals name that route instead of a hint that cannot run.

## Next Action

Criteria (1) and (2) are addressed in this repository alongside this entry;
(3) lands in `sympoies/nils-cli` as `git-cli push --bootstrap` and reaches hosts
only through a nils-cli release and a pin bump. Until that pin moves, the hook's
refusal deliberately describes the bootstrap route in general terms rather than
naming a flag the pinned CLI does not have. Re-triage after the bump.
