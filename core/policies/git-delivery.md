# Git, Commits, And Delivery

## Purpose

Required `project-dev` delivery boundaries. `AGENT_HOME.md` carries the always-on
invariants; governed CLIs and hooks own parsing and deterministic checks.
Read [Git delivery reference](references/git-delivery.md) only for the relevant
exception, refusal, or recovery. Current CLI help owns command syntax.

## Git Mutation Ownership

| Mutation | Owner |
| --- | --- |
| Commit, fixup, squash | `semantic-commit` |
| Managed worktree lifecycle | `git-cli worktree` |
| Publish a branch | `git-cli push` |
| Adopt the published default / non-default branch | `git-cli sync-default` / `git-cli sync-branch` |
| PR/MR record, review, merge | `forge-cli pr` and the active `deliver-pr` workflow |
| One local-only default-branch commit | `semantic-commit default-branch` |
| Publish the default branch | `forge-cli repo push-default` |

Use raw Git for reads, staging, and operations without an owner above. Never
bypass hooks, signing, branch protection, access controls, or concurrency guards.
Raw commit/worktree/provider creation paths cannot replace the governed owners.
Raw default-branch push and default-branch authoring (`commit`, `fixup`, `squash`,
`cherry-pick`, `merge`, `pull`, `reset`, `update-ref`) remain blocked by effect;
`--ff-only` does not prove remote publication. Force, delete, all-refs and mirror
pushes cannot become an exceptional default-branch delivery.

## Delivery Authority

| Outcome | Current-task authority | Required route and proof |
| --- | --- | --- |
| PR/MR (provider default) | Explicit current-task provider-delivery request, or an approved workflow owning delivery | Signed commit on a non-default managed worktree; active delivery workflow; checks/reviews and provider head/merge read-back |
| Direct-main (`direct` only) | Explicit request to commit and push the default branch | Exactly one verified signed commit on a non-default managed worktree; `forge-cli repo push-default` bound to the full expected remote base and a reason file; matching `observed_remote_sha` receipt |
| Default-branch (`direct` local completion) | Exact approval for one local-only default-branch commit | `semantic-commit default-branch` in the clean primary checkout, explicit absolute `--repo`, full `--expect-head`, new outside-repository receipt; `provider_delivered=false` |

Implementation alone grants no provider authority. Size, urgency, and "hotfix"
do not authorize exceptions. Authority expires with the current task. If the
scope exceeds one commit, the expected base moves, signing fails, checkout
state is unsafe, or the mode is uncertain, retain the branch and route the
needed decision. Local completion must finish in the current run; a later push
needs new authority and governed receipt adoption, never an inferred bypass.

Never enable `extensions.worktreeConfig`, set per-worktree author or signing
configuration, disable signing, or continue when signing fails. Advisory/off
project-dev preparation does not relax independent delivery or ownership guards.
Default-delivery hooks use cached local metadata and fail closed on unresolved
identity; live remote truth belongs to the governed CLI. Hermes has no hook
runner; policy and CLI contracts still apply.

A one-shot inline delivery waiver admits only an unresolvable `semantic-commit`
target, with a normalized reason of at least 12 characters recorded in the
receipt. It cannot waive a proven violation, raw Git, or force/mirror/delete/
all-refs pushes. Ambient/exported waivers are refused; the rule stays locked.
Read the [reference](references/git-delivery.md#one-shot-delivery-waiver) before
using this narrow admission path.

## Bounded Exceptions

- Collaboration ledger operations use only the repository's `tools/collab.py`
  when a tracked regular top-level `.agent-collab` on the remote default tree
  contains exactly `collab-protocol: 1`. Working-tree/index/feature-only markers
  do not qualify. No raw Git/provider path, unrelated delivery, release, or
  history rewrite is authorized. Read the ledger section in the reference.
- A maintainer-provisioned scheduled devlog fold job may update only the indexed
  log through `devlog fold` / `check`, verified App-authenticated commits and a
  narrow protection exception (or an independently approved auto-merge route).
  No agent-side push, month edits, force update, release, or rollout follows
  from this exception. Read [the fold owner](devlog/ci-fold.md).

## Commits And Provider Records

- Stage only owned paths. Use `semantic-commit`; non-trivial bodies require
  1-2 bullets with uppercase ASCII openers (two-space continuation permitted).
  Draft an accurate summary from the actual diff, never `git log -1`.
- Branch prefix must match delivery kind. `git-cli worktree add --kind` derives
  it; use CLI help for the mapping. Slugs are lowercase, hyphenated, 3-6 words.
- Use the active workflow / `forge-cli` for issues, PRs and MRs. Bodies use
  `agent-runtime pr-body render`, with at least `## Summary` + `## Test plan`.
  Select labels from the project's catalog through
  [label policy](forge-label-taxonomy.md).
- Required checks, risk-selected review, current-head review disposition,
  ledger, thread/task convergence, expected-head binding and merge read-back
  remain owned by `deliver-pr` and `forge-cli`. Never substitute a custom loop
  or silently downgrade a failed governed review publisher.

## Worktrees

- `git-cli worktree` is the managed lifecycle surface; direct mutating
  `git worktree` is blocked by hook so paths, branch names, JSON contracts, and
  cleanup behavior stay consistent across sessions.
- Managed agent worktrees live under the runtime-kit state worktree tree
  (`${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/worktrees/<repo-key>/<branch-slug>`);
  the sibling `.../agent-runtime-kit/out/` tree stays owned by `agent-out` for
  workflow artifacts.
- `git-cli worktree remove` reclaims the working tree but intentionally leaves
  the branch ref in place; delete a merged throwaway branch explicitly, or use
  `meta:worktree-triage` to batch-clean stale worktrees and branches.

### Adaptive checkout writer lease

- Supported PreToolUse hooks coordinate one writer lease per physical Git
  checkout. Explicit edit tools participate unconditionally; Bash participates
  only for conservative high-confidence mutations, recursively recognizing
  known shell / `agent-run exec` wrappers. Read-only inspection stays available.
  Cross-repository shell mutations must still run with each target repository
  as CWD except for explicitly target-aware managed worktree removal and a
  repo-scoped `semantic-commit … --repo <path>` commit, which the guard
  evaluates on the resolved target checkout so coupled cross-repository delivery
  can commit into a second repository's managed worktree without switching CWD.
  Both carve-outs require the target-aware command to be its command's sole
  mutation; raw `git -C <path>` / `--git-dir` mutations stay CWD-scoped.
  Cross-repository staging is a separate tool call: set the tool call's
  top-level `workdir` to the target checkout and run
  `git add -- <owned-paths>` there. Do not encode that transition with shell
  `cd`, raw `git -C`, or nested `agent-run exec --cwd`; if the host cannot
  attest a target workdir, continue from a managed session rooted at the target
  checkout.
  A nested `agent-run exec --cwd <other-repo>` is not another target-aware
  exception: the pre-edit gate rejects that cross-repository wrapper and directs
  the agent to a session rooted at the target checkout.
- A clean linked worktree can acquire a lease. The primary checkout has a
  narrow direct-edit exception: it must be clean, on the resolved default
  branch, outside an existing Git operation, and free of a live foreign lease.
  This editing exception does not itself authorize a commit or delivery mode.
  Only the current-request default-branch authorization plus its exact CLI shape
  can extend it to one commit.
- Once acquired, the owning session refreshes its lease and may continue after
  its own edits dirty the checkout, including resolving a Git operation it
  initiated after acquisition. A live foreign lease, dirty checkout without a
  matching lease, or pre-existing merge/rebase/cherry-pick/revert/bisect state
  blocks mutation and routes the agent to a managed worktree.
- A sole git recovery command (`git rebase|merge|cherry-pick|revert|am
  --abort`, or `--quit`) is always admitted by both the checkout writer lease
  and the pre-edit intent gate — even without owning the lease or an active
  project-dev activation — because aborting restores the clean pre-operation
  state and authors no content. This lets a checkout that is stuck mid-operation
  recover in place instead of being discarded; `--continue`/`--skip` advance the
  operation and stay gated. The carve-out is as narrow as `git-cli worktree add`:
  one recovery command, no co-resident mutation, and no output redirect.
- Lease state uses a privacy-safe session digest plus a checkout-instance
  sentinel stored under the checkout's Git admin directory. Removing and
  recreating a linked worktree therefore cannot inherit its predecessor's
  ownership. The default lease lifetime is eight hours and may be tuned with
  `AGENT_RUNTIME_CHECKOUT_LEASE_TTL_SECONDS`; an expired foreign lease is
  reclaimable only while the checkout is clean.
- Missing session identity or unwritable/malformed lease state fails closed for
  explicit mutations. Stop releases only a clean lease owned by its matching
  session and prunes stale lease records for physically removed worktrees while
  retaining stable per-checkout lock inodes; otherwise it reports and retains
  ownership. Stop never deletes a worktree, branch, commit, or dirty file.
- Dirty-checkout takeover is available only when the launch environment sets
  `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION` to `1`. A private
  `UserPromptSubmit` advisory binds a one-time five-minute challenge to the
  current session, user turn, checkout instance, and exact `git-cli worktree
  dirty-snapshot`. Remain read-only for Q&A. Before implementation, present the
  warned choice and obtain explicit authorization for that exact state; otherwise
  use `git-cli worktree add`. Never infer authorization from the task or invoke
  `adopt-dirty` merely because the challenge exists.
- After authorization, run only the displayed sole adoption command unchanged.
  An older git-cli gets `git-cli worktree adopt-dirty --challenge <bearer>
  --reason-file <file>`. A released git-cli that reads the challenge only
  through `--challenge-fd` gets the hook's launcher,
  `checkout-lease-guard.py adopt-dirty --reason-file <file> <<< <bearer>`.
  The PreToolUse gate requires the resolved managed executable or the hook's own
  launcher path and binds challenge consumption to the issuing agent session. The released CLI rechecks the snapshot and competing lease
  under the lock, consumes the challenge once, and writes matching
  receipt/lease-v2 provenance. Same-session refresh preserves that embedded
  provenance. Revoke only through `git-cli worktree revoke-dirty` with the
  matching receipt and owning session; adoption and revocation never stash,
  reset, clean, stage, commit, or otherwise change checkout content.
- Keep the bearer and local adoption evidence
  private. Provider-visible adoption records may state that governed adoption
  occurred and cite validation outcomes, but must not contain the challenge, raw
  prompt, reason text, filenames, paths, diffs, or file contents.
  Missing/expired/malformed challenges, snapshot drift, foreign ownership,
  unsupported dirty state, or CLI failure returns to the ordinary fail-closed
  worktree guidance.
- A dirty checkout may admit one narrow ref-only operation through the resolved
  `git` executable without acquiring a lease: selected branch delete/move/copy
  forms, tag deletion, or lightweight/forced tag creation with explicit
  `--no-sign`. The command must be the sole mutation with no redirect, dynamic
  argument, command-local executable/Git retargeting, or executable
  `reference-transaction` hook. Live foreign ownership, stale/unowned lease
  state, Git operations, and an off-default primary checkout still block. Any
  file/index write—also with untracked-only dirt—or compound ref-plus-file command
  remains blocked. Codex and Claude enforce this hook contract; Hermes does not
  ship the runtime-kit hook runner.

### Terminal local cleanup

- Capture the checkout root, branch, delivery mode, and delivered head SHA.
  Cleanup becomes eligible only after provider truth is read back and matches
  that head: PR/MR merge truth for the default path, or the governed
  `observed_remote_sha` receipt for direct-main. Linked issue closeout, archive
  duties, requested deployment/activation, evidence migration, and other
  parent-owned terminal work must also be complete.
- Recheck local status immediately before cleanup. Dirty, locked, missing,
  provider-unverified, or otherwise ambiguous state is retained and reported;
  never force removal merely to make the local tree look tidy.
- From the primary checkout, run exactly one sanctioned cleanup command:
  `git-cli worktree remove <path-or-slug> --safe --format json`. The supported
  shell hook delegates this sole, trusted invocation to the CLI's execution
  fence in advisory and enforce modes. Older CLIs reject `--safe` before their
  legacy removal path; upgrade through the normal release owner rather than
  removing the flag or changing coordination mode.
- The CLI holds the target checkout lease lock and session registry lock through
  removal. It requires an exact registered managed target, a clean stable
  checkout outside a Git operation, no active checkout lease (including the
  requester), no live session binding or nonterminal operation, and complete
  process cwd/open-file visibility. Missing tools, malformed state, incomplete
  process visibility, identity drift, and unavailable remote/provider proof
  retain the target with a reason. Unmanaged removal remains forbidden.
- Delivery proof uses the current remote default HEAD or a provider-confirmed
  merged PR/MR whose head exactly matches the target HEAD. Unpushed and unmerged
  commits are retained. Squash/rebase merges do not require rewriting the local
  branch. The CLI never forces removal and leaves the branch ref intact.
- The lease owner supports `checkout-lease-guard.py diagnose-removal` with the
  proposed PreToolUse shell payload on stdin. Its target-bound
  `agent-runtime.worktree-removal-attestation.v1` diagnostic observes the root,
  Git directory, common directory, HEAD, checkout instance and existing lease
  without acquiring or refreshing ownership. It always reports
  `execution_fenced=false` and `cleanup_authorized=false`: this observation,
  hook registration, and a successful lifecycle command are never execution
  receipts. The v1/v2 lease does not prove a managed session incarnation.
- Keep delivery classification separate from producer release. Provider merge
  proof does not release an active checkout lease, session binding, rollback
  hold, or pending parent duty. Finish the owning workflow first and release
  ownership through its sanctioned lifecycle. Absence of a report alone never
  establishes completion; the cleanup command independently proves idle local
  ownership and exact-head delivery.
- Run exactly one managed worktree removal as the shell command's sole mutation.
  Do not combine removals or combine removal with branch deletion, redirection,
  or another checkout write; execute each lifecycle step separately so its
  lease scope stays explicit.
- For a primary checkout, switch a clean completed branch back to the intended
  base and fast-forward it from the provider before deleting the disposable
  local branch. For a managed linked worktree, run `git-cli worktree remove
  <path-or-slug> --safe --format json` from the primary checkout. Direct mutating
  `git worktree` remains forbidden. The session's final Stop releases a clean
  primary-checkout lease and prunes lease state left by a successfully removed
  managed worktree.
- `git-cli worktree remove` intentionally leaves the branch. Delete it only
  after the provider-confirmed delivered head or direct-main remote-SHA receipt
  matches the local branch tip. This explicit proof permits cleanup after a squash merge, where
  `git branch -d` cannot infer provider equivalence from ancestry alone.
- A child PR workflow defers cleanup when its `program/dispatch` parent or
  another requested post-merge workflow still owns
  terminal duties, handing the captured checkout identity to that parent. The outermost successful workflow performs cleanup
  exactly once; failed or readiness-only workflows retain the checkout.

## Parent Workflow Routing

Commit preparation and repository pre-PR validation are internal delivery
phases. Run the repository-owned `.agents/scripts/pre-pr.sh` dispatcher when
present before provider mutation; stop on failure. Stage through a separate
shell call whose top-level `workdir` is the target repository, then invoke
repo-scoped `semantic-commit` as its command's sole mutation. A blocked shell
retarget is a routing instruction; use a target-rooted managed session if the
host cannot attest the target, then report a capability blocker if unavailable.

Load [evidence-control-plane](evidence-control-plane.md) when retained test-first
proof, a delivery gate, audit, handoff, or other durable evidence is required.
Its conditional status never waives a gate. `forge-cli` owns opt-in feature/bug
`test-first-evidence.record.v2` admission on create/adopt/dry-run; other kinds are
exempt. Meaningful red or an honest waiver, affected-test judgment, scoped final
validation and residual-gap disclosure remain required by the engineering
contract. Storage/schema/typed failures belong to CLI help and the
[on-demand reference](references/git-delivery.md#test-first-evidence-gate).
