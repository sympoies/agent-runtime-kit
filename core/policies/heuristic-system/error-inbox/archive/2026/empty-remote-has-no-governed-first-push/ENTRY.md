# No governed path publishes the first branch of an empty remote

## Status

- Status: promoted
- First observed: 2026-08-28
- Resolved: 2026-08-28
- Area: `block-unsafe-default-delivery` default-branch resolution; `git-cli push`
- Severity: high
- Durable link: `https://github.com/sympoies/agent-runtime-kit/issues/61`
- Durable link: `https://github.com/sympoies/agent-runtime-kit/pull/62`
- Durable link: `https://github.com/sympoies/agent-runtime-kit/pull/63`
- Durable link: `https://github.com/sympoies/nils-cli/pull/1540`
- Durable link: `https://github.com/sympoies/nils-cli/pull/1544`

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

None. See Resolution.

## Resolution

Promoted 2026-08-28. All three criteria are met, and each was verified on a real
host rather than only in CI.

- **(1) met.** `resolve_default_branch()` now returns a named resolution —
  corroborated, uncorroborated, or unknown — instead of collapsing unrelated
  situations into one empty string. A primary checkout parked on a feature
  branch no longer locks raw pushes out of the whole repository, while the
  stale-cache defence the equality check existed for is preserved by the
  candidate-set rule: a planted `refs/remotes/<remote>/HEAD` still cannot clear
  a push to the real default. sympoies/agent-runtime-kit#62.
- **(2) met.** A destination outside `refs/heads/` is classified without
  resolving the default branch at all, so tag and note pushes are admitted in
  every resolution state. Same PR.
- **(3) met.** `git-cli push --bootstrap` publishes the first branch of a remote
  proven empty by `ls-remote`, and the ordinary path reports
  `remote-has-no-branches` naming that route instead of a hint that cannot run.
  sympoies/nils-cli#1540, released in v1.27.19 and adopted as `validated_tag`
  by the commit this entry ships with.

Two findings surfaced while fixing this, both repaired in the same work:

- A pre-existing hole in the same classifier admitted
  `git push --delete origin '*'`, which removes every branch including the
  default, because deletes were compared by name and a pattern matched
  literally. Confirmed by running the classifier against clean `main` and the
  patched tree side by side.
- The bootstrap push needed a create-only lease. A plain push *fast-forwards* a
  branch that appears between the emptiness check and the push, which for the
  default branch is the write the command exists to prevent. Verified against
  git 2.50.1.

Deploying the fix exposed a fourth, unrelated blocker: `sync-runtime-surfaces.sh`
— the documented refresh entrypoint — could not run on macOS at all, because
bash 3.2 aborts on an empty `"${arr[@]}"` under `set -u`. That is
sympoies/agent-runtime-kit#63, now guarded by a static `macos-portability-audit`
since Linux CI cannot reproduce the fault.

The end-to-end scenario this case opened with — empty remote, first branch,
tag, cached head — now completes entirely through governed surfaces and
produces a ref set byte-identical to the real `sympoies/night-owl-cli`.

Note: the compatibility minimum stays at `v1.27.16`, where `--bootstrap` does
not exist. That is why the delivery guard's empty-remote refusal describes the
bootstrap route in general terms instead of naming the flag.

## Archive

- Archived: 2026-08-28
- Reason: Completed entry archived out of the active error inbox.
