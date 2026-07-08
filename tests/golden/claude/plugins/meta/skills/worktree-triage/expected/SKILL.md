---
name: worktree-triage
description: >
  Scan git worktrees against a base ref, classify safe/rescue/dirty/locked
  branches, cleanup safe or confirmed-superseded stale worktrees when requested,
  and open draft PRs for unmerged work only on explicit confirmation.
---

# Worktree Triage

## Contract

Prereqs:

- For one repo, run from inside the target git repository (or pass
  `--repo <path>`).
- For machine-wide cleanup, pass `--all-managed` to scan every repository
  represented under the managed worktree root
  (`${AGENT_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/worktrees`).
- `git` and `git-cli` are on `PATH`; Python 3.11+ is available (the bundled
  `worktree_triage.py` helper is stdlib-only).
- `forge-cli >=1.11.2` is installed from the released nils-cli package for the
  draft-PR rescue path. The scan itself needs no provider access.
- The base ref the work should have landed on is fetched and current in every
  scanned repo. The helper is **read-only and never fetches** — run
  `git fetch origin --prune` yourself first (in each represented repo for
  `--all-managed`) so `origin/main` is not stale, or the ahead/behind and
  supersession verdicts will be wrong.

Inputs:

- The scope to scan:
  - `--all-managed` for every repo represented under the managed worktree
    root. Use this when the user says "all worktrees", "no agents are running",
    or otherwise asks for global cleanup without naming one repo.
  - `--repo <path>` for one repo, or no scope flag to scan the current repo.
- The base ref each branch is classified against (`--base`, defaults to
  `origin/main`).

Outputs:

- A `worktree-triage.scan.v1` JSON envelope (or text) with a `scope`, optional
  `worktree_root`, a `repos` array, a `summary`
  (per-disposition counts) and a `worktrees` array. Each record carries
  `path`, `repo_root`, `branch`, `is_primary`, `disposition`,
  `suggested_action`, and — for branches with unique commits —
  `ahead`/`behind`, a `unique_commit_count`, and an `evidence` block with the
  two-dot
  `git diff <base>..<branch>` shortstat plus a `likely_superseded` flag.

Dispositions (the heart of the triage):

- `primary` — the repo's main working tree. Never a removal target.
- `dirty` — uncommitted changes present. **Blocked from removal** so
  in-progress work is never lost.
- `locked` — a git-locked worktree. Surfaced, never auto-removed.
- `safe-merged` — branch tip is an ancestor of the base (nothing ahead).
  Safe to prune.
- `safe-superseded` — branch is ahead by commit SHA, but **every** commit
  is patch-equivalent to one already in the base (`git cherry` reports
  them all as `-`). Safe to prune.
- `rescue-candidate` — branch has commits whose patch is not in the base.
  This needs human judgment: it may be genuine unmerged work, OR work that
  already reached the base via a different commit (patch-id is unreliable
  for that case — read `evidence`). **Never auto-pruned.**

Failure modes:

- Not a git repo, or `--base` does not resolve (usually a missing
  `git fetch`, or a non-`main` default branch — pass `--base`). In
  `--all-managed`, per-repo base failures are reported in `errors`; do not
  prune worktrees from a repo whose base could not be verified.
- A worktree is reported `dirty` or `locked`: that is a verdict to act on,
  not a tool error. Never remove either without resolving it first.
- A `rescue-candidate` whose `evidence` looks subtractive is a *signal* to
  review. It becomes auto-prunable only after the workflow below confirms that
  the branch's work is already represented on the base or was superseded by
  newer base content.

## Entrypoint

For all managed agent worktrees, fetch each represented repo first, then scan:

```bash
$HOME/.claude/plugins/meta/skills/worktree-triage/scripts/worktree-triage.sh --all-managed --base origin/main --format json
```

For one repo, fetch first so the base ref is current, then scan:

```bash
git fetch origin
$HOME/.claude/plugins/meta/skills/worktree-triage/scripts/worktree-triage.sh --repo . --base origin/main
```

Machine-readable envelope for selection logic:

```bash
$HOME/.claude/plugins/meta/skills/worktree-triage/scripts/worktree-triage.sh --repo . --base origin/main --format json
```

## Workflow

1. **Choose scope, fetch, then scan.** If the user names one repo, use
   `--repo`; if the user asks for all worktrees or says no agents are running,
   use `--all-managed`. Run `git fetch origin --prune` for every represented
   repo in scope (state it; the helper never fetches), then run the helper.
   Treat its output as read-only evidence.
2. **Present the triage table.** Show the user each worktree's
   `disposition`, branch, ahead/behind, and `suggested_action`, grouped
   into: safe-to-prune (`safe-merged` + `safe-superseded`),
   rescue-candidates, and blocked (`dirty` / `locked` / `primary`).
3. **Prune the mechanically safe set.** When the user has asked to clean up
   worktrees, prune every `safe-merged` / `safe-superseded` record without
   per-item confirmation. Run the removal against the reported `path` and delete
   the branch from that record's `repo_root` (this matters for `--all-managed`,
   where rows may come from different repos):

   ```bash
   git-cli worktree remove <path-or-slug> --format json
   git -C <repo_root> branch -D <branch>
   ```

   Delete the remote branch only when it has no open PR, or its PR is
   itself superseded/closed. Never prune a `primary`, `dirty`, or `locked`
   worktree, and never prune anything from a repo listed in `errors`.
4. **Auto-prune high-confidence stale rescue candidates.** Judge each
   `rescue-candidate` from evidence instead of asking the user for another
   cleanup confirmation:
   - `likely_superseded: true` (net diff empty or subtractive) means the
     branch's content probably landed on the base via another commit. Confirm
     it by checking the full unique commit subjects against recent base commit
     bodies:

     ```bash
     git -C <repo_root> cherry -v <base> <branch>
     git -C <repo_root> log <base> --format=%B --max-count=600
     git -C <repo_root> diff --shortstat <base>..<branch>
     ```

     If every unique commit subject is present verbatim in recent base commit
     bodies and the two-dot diff is empty or net-subtractive, treat it as a
     confirmed stale duplicate and prune it like the safe set. If
     `unique_commit_count` is larger than `evidence.sample_unique_commits`,
     derive the full subject list from `git cherry -v`; do not rely only on the
     sample.
   - `likely_superseded: false` usually means real unmerged work. It can still
     be pruned without another user confirmation only when provider or base-log
     evidence proves the exact branch work already landed (for example, the
     branch's PR is merged or every unique subject appears in a squash commit)
     and the remaining two-dot diff is clearly the branch moving the checkout
     backward relative to newer base content, such as older dependency or
     generated-file versions. Otherwise retain it.
   - Exact subject misses, related-but-not-equal base commits, open PRs, and
     content diffs that are not clearly stale are retained and reported.
5. **Stop at the remaining human gate.** The skill may auto-prune only
   mechanically safe worktrees and high-confidence stale duplicates after the
   user has requested cleanup. It never removes `primary`, `dirty`, or `locked`
   worktrees, never removes rows from repos with scan errors, never opens or
   merges PRs without explicit confirmation, and never treats a related commit
   as proof of supersession.

## Boundary

`worktree_triage.py` owns worktree enumeration, the ahead/behind and
ancestor checks, the patch-equivalence (`git cherry`) call, the two-dot
net-diff evidence, and the disposition verdict. The skill body owns when to
fetch and scan, how to present the triage for selection, and the cleanup act
phase: prune mechanically safe worktrees, prune high-confidence stale
rescue-candidates after base/provider confirmation, and hand genuine unmerged
work to PR delivery. It never re-implements the helper's classification in
prose, never auto-removes a dirty/locked/primary worktree, never deletes a
branch from a repo with scan errors, and never merges.

## Related Skills

- `create-pr` / `deliver-pr` — open the draft PR a genuine
  `rescue-candidate` is handed off to. Triage never merges.
- `close-pr` — close the PR of a `rescue-candidate` confirmed to be
  already-on-base (superseded).
- `sync-runtime-surfaces` — its apply path refuses linked-worktree source
  roots; this skill is the companion that cleans those worktrees up.
