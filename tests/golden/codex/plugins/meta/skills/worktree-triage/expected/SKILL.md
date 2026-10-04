---
name: worktree-triage
description: >
  Scan and classify git worktrees against a base ref, prune safe/superseded
  ones only after owner and terminal proof, and route unmerged work for
  delivery. Provider probes are read-only; in-progress work is retained.
---

# Worktree Triage

## Contract

Prereqs:

- For one repo, run from inside the target git repository (or pass
  `--repo <path>`).
- For machine-wide cleanup, pass `--all-managed` to scan every repository
  represented under the managed worktree root
  (`${AGENT_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/worktrees`).
- `git` and `git-cli >=1.27.16` are on `PATH`; Python 3.11+ is available (the bundled
  `worktree_triage.py` scanner is stdlib-only). `forge-cli` is required for
  provider PROBE, with normalized exact-head fields available; missing fields
  retain the target. The scan itself needs no provider access.
- The base ref the work should have landed on is fetched and current in every
  scanned repo. The scanner is **read-only and never fetches** — run
  `git fetch origin --prune` yourself first (in each represented repo for
  `--all-managed`) so `origin/main` ahead/behind is not stale. The **PROBE**
  (step 3) reads provider delivery truth for the exact head. Unreachable,
  missing, or mismatched provider truth retains the worktree.
- SCAN and PROBE are read-only. Do not rebase, reset, commit dirty inventory
  work, or rewrite branch history to classify it. ACT requires independent
  producer release, completed parent duties and target lease fencing.

Inputs:

- The scope to scan:
  - `--all-managed` for every repo represented under the managed worktree
    root. Use this when the user says "all worktrees", "no agents are running",
    or otherwise asks for global cleanup without naming one repo.
  - `--repo <path>` for one repo, or no scope flag to scan the current repo.
- The base ref each branch is classified against (`--base`, defaults to
  `origin/main`).
- Persistent branch names to retain (`--protect-branch <branch>`, repeatable).
  Use exact names such as `mainline`; protection never changes the scan base.

Outputs:

- A `worktree-triage.scan.v1` JSON envelope (or text) with a `scope`, optional
  `worktree_root`, a `repos` array, a `summary` (per-disposition counts) and a
  `worktrees` array. Each record carries `path`, `repo_root`, `branch`,
  `is_primary`, `disposition`, `suggested_action`, and — for branches with
  unique commits — `ahead`/`behind`, a `unique_commit_count`, and an `evidence`
  block with the two-dot `git diff <base>..<branch>` shortstat plus a
  `likely_superseded` flag. Each repo record also carries `base_freshness`
  (`{base, upstream, behind_upstream}`) when the base has an upstream, so the
  caller can spot a **stale local base** before landing onto it.
- The envelope carries the sorted `protected_branches` input. Every worktree
  record carries `protected`; clean matching branches use the `protected`
  disposition and never enter the safe-removal set.
- `likely_superseded` is **advisory** — a cheap patch-id hint. The **PROBE**
  (step 3), not this flag, checks provider delivery truth.

Dispositions (the SCAN's cheap first pass):

- `primary` — the repo's main working tree. Never a removal target.
- `dirty` — uncommitted changes present. Retain unchanged and route to the
  original owner; cleanup does not author a commit to make the row removable.
- `locked` — a git-locked worktree. Surfaced, never auto-removed.
- `protected` — an explicitly retained persistent branch. Leave it unchanged.
- `safe-merged` — branch tip is an ancestor of the base (nothing ahead).
  Delivery-history candidate; removal still needs the ACT gate.
- `safe-superseded` — branch is ahead by commit SHA, but **every** commit is
  patch-equivalent to one already in the base (`git cherry` reports them all as
  `-`). Delivery-history candidate; removal still needs the ACT gate.
- `rescue-candidate` — branch has commits whose patch is not in the base. This
  is **investigated by the PROBE**, not by reading `evidence` prose: it may be
  genuine unmerged work, or work already on the base via a different commit
  (patch-id is unreliable). Never auto-pruned from the SCAN alone.

Failure modes:

- Not a git repo, or `--base` does not resolve (usually a missing `git fetch`,
  or a non-`main` default branch — pass `--base`). In `--all-managed`, per-repo
  base failures are reported in `errors`; do not prune worktrees from a repo
  whose base could not be verified. Unavailable provider proof also retains
  the target; local ancestry does not establish original-owner release.
- A worktree is `dirty` or `locked`: a verdict to act on, not a tool error.
  Never discard or auto-commit a dirty inventory worktree.
- `base_freshness.behind_upstream` large (local base far behind its upstream):
  a signal **not** to land rescued work onto that stale base — keep the branch
  and land after the base is refreshed.

## Entrypoint

For all managed agent worktrees, fetch each represented repo first, then scan:

```bash
$CODEX_HOME/plugins/meta/skills/worktree-triage/scripts/worktree-triage.sh --all-managed --base origin/main --format json
```

For one repo, fetch first so the base ref is current, then scan:

```bash
git fetch origin
$CODEX_HOME/plugins/meta/skills/worktree-triage/scripts/worktree-triage.sh --repo . --base origin/main --protect-branch mainline
```

Machine-readable envelope for selection logic:

```bash
$CODEX_HOME/plugins/meta/skills/worktree-triage/scripts/worktree-triage.sh --repo . --base origin/main --format json
```

## Workflow — SCAN → PROBE → ACT

### 1. SCAN (read-only)

Choose scope, fetch each represented repo (`git fetch origin --prune`; the
scanner never fetches), then run the scanner and treat its output as evidence.
Present the triage grouped into: history candidates (`safe-merged` +
`safe-superseded`), rescue-candidates, retained (`protected`), and blocked
(`dirty` / `locked` / `primary`). Surface each repo's `base_freshness`; flag
any repo whose local base is far behind its upstream.

### 2. Retain the inventory until its owner and parent duties are known

`safe-merged` and `safe-superseded` describe history only. They are candidates
for PROBE, not permission to prune. Preserve dirty, locked, primary, protected,
foreign-active, unpushed, open-PR, rollback-held and pending-evidence targets.
No agent presence, stopped session, missing report, elapsed time or provider
merge substitutes for explicit producer release. Report missing owner/report
state as unknown and retain it. Never adopt a disappeared session's checkout.

### 3. PROBE (read-only provider and producer evidence)

For a candidate with an associated PR, set the tool workdir to its repository
and read the existing provider contract:

```bash
forge-cli pr view <branch-or-pr-number> --format json
```

Bind the repository, branch and exact local head to the returned provider head.
A merged record with that exact head classifies delivered content even after a
squash merge; do not require branch-tip ancestry or rebase the inventory to
rediscover it. Retain an open PR, unpushed/mismatched head, unavailable provider,
unverified association or ambiguous result. Patch IDs, subjects and subtractive
diffs remain hints and never justify removal.

Separately obtain authenticated original-owner release bound to the physical
checkout root, Git directory, checkout instance, exact head and managed session
incarnation. The parent must acknowledge that rollback, follow-up, deployment,
archive and pending evidence duties are complete or remain protected. Record
these as separate proofs: delivered content is not released live ownership.
Missing report or disappeared owner remains retained unless the maintainer
separately admits disposition of that exact reconstructible target; never
manufacture a success report or release token.

### 4. ACT (bounded removal only after all proofs)

Immediately recheck the exact target and local status. Reuse the terminal
cleanup contract in `core/policies/git-delivery.md`: supported hooked shell,
verified enforcement availability, original-owner release, provider head match,
completed parent duties, and no dirty/locked/protected/primary or unresolved
state. If any proof is missing or has drifted, retain and report.

The checkout-lease owner's `diagnose-removal` action accepts the proposed
PreToolUse shell payload on stdin and returns
`agent-runtime.worktree-removal-attestation.v1`. It is read-only and always
reports `execution_fenced=false` and `cleanup_authorized=false`. Its exact target
and observed lease identify what was checked; it cannot prove an execution,
managed incarnation or producer release. A zero exit or hook doctor result is
never a removal permit. Outside enforce mode, the hook refuses managed removal;
do not switch modes to bypass that refusal.

After the execution fence and independent terminal proofs are available, run
one existing managed removal as the command's sole mutation, with the tool's
top-level workdir set to the target repository's primary checkout:

```bash
git-cli worktree remove <exact-path> --format json
```

Retain the bound command, actual result and post-removal read-back. A dry run
alone does not establish cleanup success. Do not remove another target, delete
a branch in the same command, or use raw deletion. Branch deletion is a separate
step under the provider-confirmed exact-head contract; no open PR or protected
branch may be deleted.

### 5. Route genuine unfinished work to its owner

Retain genuine unmerged or dirty work unchanged and send its owner the scan and
provider evidence. New implementation or delivery belongs to that owner's
workflow. Triage does not silently commit, rebase, land or discard it.

## Boundary

The existing scanner owns read-only enumeration, ahead/behind, ancestry,
patch-equivalence, net-diff hints, freshness and explicit branch protection.
The skill owns guarded SCAN → PROBE → ACT and consumes provider/producer proof.
It creates no second cleanup engine, ownership ledger or successful closeout
record. No classification releases a live owner or overrides parent retention.
Commits and provider delivery remain with `semantic-commit` and `deliver-pr`.

## Related Skills

- `deliver-pr` — owns the provider lifecycle for a genuine `rescue-candidate`
  in PR mode. Triage never merges.
- `semantic-commit` — governed commits for the rescue path, including
  `default-branch` for local-main mode.
- `sync-runtime-surfaces` — its apply path refuses linked-worktree source
  roots; this skill is the companion that cleans those worktrees up.
