# Git, Commits, And Delivery

## Purpose

This conditional delivery runbook owns agent-authored Git and provider state:
commit signing, managed worktrees, default-branch exceptions, provider
compare-and-swap, branch naming, cleanup, and PR/MR routing. Load it for the
`project-dev` delivery phase, not for ordinary inspection or editing.

`AGENT_HOME.md` carries the always-on safety boundary. Governed CLIs and hooks
own exact command parsing and deterministic state checks; this file explains
authorization, mode choice, and recovery. Prefer current CLI help over copying
command syntax into other prompts.

## Git Mutation Ownership

Every Git mutation an agent performs has one owner. Reach for the owner first;
raw `git` for these operations is what the delivery guard is built to distrust,
because a raw invocation cannot prove what it will touch.

| Mutation | Owner |
| --- | --- |
| Commit | `semantic-commit commit` (`fixup`, `squash`) |
| Managed worktree add/remove | `git-cli worktree` |
| Publish a branch | `git-cli push` |
| Adopt the remote's default branch locally | `git-cli sync-default` |
| PR/MR record, review, merge | `forge-cli pr` |
| One local-only default-branch commit | `semantic-commit default-branch` |
| Publish the default branch | `forge-cli repo push-default` |

Raw `git` remains the right tool for reads, for staging, and for anything with
no owner above. The guard only classifies commands that could move the default
branch.

## Default-branch Fast-forward Sync

`git-cli sync-default` is the sole owner for advancing the local default branch
onto a commit already published on its remote. Raw `git merge` and `git pull`
remain refused even with `--ff-only`: a remote-tracking ref is locally writable,
and `pull` accepts local repository paths, so local state alone cannot prove the
source commit was published. The governed owner binds the operation to the
configured remote and verifies the fast-forward before moving the branch.

## Reading A Delivery Refusal

Every refusal leads with one of two markers, and they mean different things:

- `[default-delivery: blocked]` — the command was classified and is forbidden.
  Change what you are doing, not how you spell it.
- `[default-delivery: unverified]` — the command could not be classified, so it
  failed closed. Restating it more explicitly usually resolves it; the message
  names the condition that could not be resolved.

The most common `unverified` cause is a shell-context change: a `cd`, `pushd`,
`source`, or Git environment assignment earlier in the same command line makes
the Git context unverifiable for everything after it. Run the Git command on its
own with an explicit repository — `git -C /absolute/path …` — or in a separate
tool call.

Each refusal names the governed surface for the operation actually attempted,
not the policy in general.

## Delivery Mode Decision Matrix

| Mode | Authorization | Authoring and delivery | Terminal evidence |
| --- | --- | --- | --- |
| PR (provider default) | Explicit current-task provider-delivery request, or an approved workflow that already owns PR/MR delivery | Signed `semantic-commit` on a non-default managed-worktree branch, then the active `deliver-pr` path | PR/MR URL, delivered head, reviews/checks, and provider merge read-back |
| Direct-main (L0 exception) | The maintainer explicitly requests direct commit and push to the default branch in the current task | Exactly one signed `semantic-commit` on a non-default managed-worktree branch, then `forge-cli repo push-default --expected-base <full-sha> --reason-file <path>` | Structured receipt whose post-push `observed_remote_sha` equals the delivered head |
| Default-branch (L0 local completion) | The maintainer explicitly requests one local-only default-branch commit in the current task | Exact `semantic-commit default-branch` in the clean primary checkout; no provider call | `cli.semantic-commit.default-branch.v1` receipt with `provider_delivered=false` |

Implementation alone does not authorize provider mutation. Never infer
direct-main authorization from a change being small, obvious,
urgent, or described as a hotfix. The authorization expires with the current
task. If the change grows beyond one commit, its expected base moves, signing
cannot be verified, the checkout is dirty, or the delivery mode is uncertain,
retain the managed branch and request the needed delivery decision.

`AGENT_RUNTIME_PROJECT_DEV_MODE` changes only workflow preparation guidance.
Advisory or off project-dev mode does not relax this delivery matrix, commit
signing, checkout ownership, branch, provider, or user-authorization controls;
their independent hooks and governed CLIs continue to decide admission.
Never enable `extensions.worktreeConfig` or set per-worktree author or signing
configuration for tracked agent work. If signing fails, stop and report the
failure; do not change identity or signing configuration to continue.

Never infer default-branch authorization from the same words. It permits one
signed commit only, must finish in the current run, and is not provider
delivery. If it grows to multiple commits or cannot complete locally, retain
the managed branch and re-triage.

The direct-main primitive permits only a verified fast-forward update. It
requires the selected remote to have exactly one actual push URL (including any
configured `pushurl`), binds that destination to the provider repository, and
fails closed if any effective `url.*.insteadOf` or `url.*.pushInsteadOf` rule
could rewrite the expanded destination a second time, including an empty
universal match. It requires the exact expected remote base, validates one
locally verified signed commit plus a non-empty regular reason file of at most
2,000 bytes, and pins the base read, push, and remote-SHA read-back to that URL.
Provider and Git subprocesses are time- and output-bounded, and Git's inherited
push expansion is disabled for the delivery. After proving ancestry, the CLI
internally binds `--force-with-lease` to that exact old object ID as a
compare-and-swap; callers cannot supply, relax, or retry that lease. The command
exposes no force, delete, retry, or direct merge option. Raw
`git push` to the resolved default branch and the mutating `semantic-commit`
`commit`, `fixup`, and `squash` subcommands on the checked-out default branch
are blocked by hook
on supported Codex/Claude hosts, including Git's wildcard and matching-branch
refspec forms. Explicit feature-branch refspecs and documented read-only
help/dry-run forms remain available. Raw `cherry-pick`, `merge`, `pull`,
`reset`, and `update-ref` on the checked-out default branch are classified by
effect and fail closed; `git-cli sync-default` is the remote-bound fast-forward
owner (see "Default-branch Fast-forward Sync"). The PreToolUse hook uses cached local
default-branch metadata only and performs no `ls-remote` or other network
probe. Missing or ambiguous cache state fails closed; live truth belongs to
`forge-cli`. Hermes has no hook runner; policy and the governed CLI
contract remain authoritative there.

### Naming the delivery target

A `semantic-commit` invocation is classified against the repository it actually
commits in, not the tool workdir. Bind a cross-repository target with
`--repo <absolute path>`, which every mutating subcommand including
`default-branch` accepts. The exceptional command always carries an explicit
absolute `--repo`; shell retargeting is not an authorized route.
A relative, expanded, globbed, or `~` destination, a nested shell, and any
command-local `GIT_*`/`HOME` override do not resolve a governed target, and
neither does any shell-context change ahead of a raw `git` path. A blocked
verdict names the resolved repository, how it resolved, and the first failing
precondition, so the invocation can be corrected instead of retried blind.

### One-shot delivery waiver

When the target genuinely cannot be made resolvable, one command may state a
reason inline:

```
AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER='<why this target is authorized>' \
  semantic-commit default-branch ...
```

The waiver is read only from that command's own assignment prefix, so it cannot
outlive the invocation; an exported variable, a separate `export`, and an
ambient environment value are all refused. It admits only the unresolvable
class, only for `semantic-commit`, and only with a stated reason of at least 12
characters measured the way the receipt measures it: control characters become
spaces and whitespace runs collapse, so padding cannot clear the minimum. A
proven default-branch target, every raw `git` path, and every force, mirror,
delete, or all-refs push stay blocked, because no governed CLI re-verifies those
downstream. The reason is recorded in the default-branch receipt as
`data.delivery_waiver`, and the guard and the receipt writer must keep the same
minimum so an admitted delivery is never left without recorded evidence.

This is an admission path inside the handler, not a rule override: the rule
stays `override_class = "locked"`, fail-closed, and cannot be disabled or
downgraded by configuration.

### Default-branch completion

Use `semantic-commit default-branch` only after the current request explicitly
authorizes this local outcome. Bind the invocation to the full current `HEAD`,
an explicit absolute `--repo`, and a new receipt path allocated outside the
repository through `agent-out`. The CLI requires the primary worktree, an
attached branch, staged-only changes, no Git operation, and usable signing. A
remote-free repository must have no branch upstream metadata. With configured
remotes, the checked-out branch, its configured upstream, and the cached remote
default identity must agree, and the cached upstream object must equal `HEAD`.
Missing, already-ahead, behind, diverged, or ambiguous cached identity fails
closed. It performs no fetch, `ls-remote`, push, or provider lookup.

Before mutation, the same command may run with `--dry-run` and no
`--receipt-out`; the `cli.semantic-commit.default-branch.preview.v1` result
proves only local preconditions and creates no commit or receipt. Mutation
requires `--receipt-out`, forbids combining it with `--dry-run`, and creates
exactly one signed commit from the caller-bound `--expect-head`.

The successful receipt records privacy-safe repository and object identities,
signature verification, cached upstream relation, and that provider delivery
is still false. Never commit this receipt. Receipt finalization failure after a
successful commit is a partial success: keep the commit for inspection and do
not reset or amend it automatically.

A later provider push is a new authorized action. Use
`forge-cli repo push-default --default-branch-receipt <path>` with a fresh
expected remote base and reason file. Receipt adoption is the only exception
that permits `push-default` from the checked-out default branch; it rechecks
the live remote, exact parent/head/tree, one-commit ancestry, signature,
destination, compare-and-swap, and read-back. The local receipt never bypasses
project deploy or release gates. The live expected-base and exact one-commit
range checks still must pass.

## Commits

- The `semantic-commit` body gate enforces 1-2 bullets on non-trivial commits;
  trivial commits may omit the body.
- Author commits only on a non-default managed-worktree branch. This applies to
  both PR and direct-main delivery; direct-main changes are not authored in the
  primary checkout. The sole exception is the exact authorized default-branch
  command and receipt contract above.
- Each body bullet must start with a dash, one following space, and an uppercase
  ASCII letter, or a two-space continuation line. A lowercase word, a
  backticked identifier, or a leading double-dash flag is rejected as the opener;
  auto-fix capitalizes a lowercase opening word but cannot rescue a flag or
  backtick start, so lead with a capitalized verb or noun there. The
  `semantic-commit --help` output carries exact flag examples and error strings.
- Draft an accurate 1-2 sentence summary grounded in the actual diff before
  committing or opening a record; never derive a title or body from
  `git log -1`.

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
- After authorization, use only the displayed sole `git-cli worktree
  adopt-dirty --challenge <bearer>
  --reason-file <outside-checkout-file>` transition. The PreToolUse gate requires
  the resolved managed executable and binds challenge consumption to the issuing
  agent session. The released CLI rechecks the snapshot and competing lease
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
- Managed worktree removal must run through a supported hooked shell. The
  checkout lease guard resolves the removal target, claims or refreshes its
  lease, and blocks a live foreign owner before `git-cli` executes. If the
  target lease cannot be verified or the hook is unavailable, retain the
  worktree and report the failed proof instead of removing it.
- Run exactly one managed worktree removal as the shell command's sole mutation.
  Do not combine removals or combine removal with branch deletion, redirection,
  or another checkout write; execute each lifecycle step separately so its
  lease scope stays explicit.
- For a primary checkout, switch a clean completed branch back to the intended
  base and fast-forward it from the provider before deleting the disposable
  local branch. For a managed linked worktree, run `git-cli worktree remove
  <path-or-slug> --format json` from the primary checkout. Direct mutating
  `git worktree` remains forbidden. The session's final Stop releases a clean
  primary-checkout lease and prunes lease state left by a successfully removed
  managed worktree.
- `git-cli worktree remove` intentionally leaves the branch. Delete it only
  after the provider-confirmed delivered head or direct-main remote-SHA receipt
  matches the local branch tip. This explicit proof permits cleanup after a squash merge, where
  `git branch -d` cannot infer provider equivalence from ancestry alone.
- A child PR workflow defers cleanup when its L2/L3 parent or another requested
  post-merge workflow still owns terminal duties, handing the captured checkout
  identity to that parent. The outermost successful workflow performs cleanup
  exactly once; failed or readiness-only workflows retain the checkout.

## Branches

- Branch names carry a Conventional-Commits-style prefix matching the eventual
  PR kind, since `forge-cli pr deliver/create --kind` enforces the pairing
  (`feature->feat/`, `bug->fix/`, `chore->chore/`, `docs->docs/`, `ci->ci/`,
  `refactor->refactor/`). Slugs are lowercase, hyphenated, three to six words; a
  ticket id `ABC-123` becomes `feat/abc-123-<slug>`.
- `git-cli worktree add <slug>` derives the branch from the base ref
  automatically. It defaults to `feat/<slug>`; pass
  `--kind <feature|bug|chore|docs|ci|refactor>` to select the matching prefix
  (e.g. `--kind bug` -> `fix/<slug>`) so the worktree branch already satisfies
  the `forge-cli --kind` rule at delivery — no rename step. The kind→prefix
  mapping is shared with `forge-cli` via `nils_common::git::PrKind` (nils-cli
  `>= v1.0.4`), so the two surfaces cannot drift. Manual branch creation in a
  shared checkout is rarely needed.

## Issues, PRs, And MRs

- For agent-owned provider issues, PRs, and MRs, use the active workflow or
  `forge-cli` surface instead of raw provider commands. Direct `gh pr create`
  or `glab mr create` are blocked by hook; PR/MR delivery goes through the
  active delivery skill.
- PR/MR bodies come from the active delivery skill / `agent-runtime pr-body
  render` (the canonical formatter; minimum `## Summary` + `## Test plan`). Do
  not hand-write body scaffolding or copy the formatter's section table into
  policy files.

## Parent Workflow Routing

Commit mutation and repository pre-PR validation are internal phases of the
implementation and governed PR outcome. Parent workflows stage only their owned
changes and invoke `semantic-commit`; they do not ask the user to select a commit
helper. Before provider mutation, the PR parent runs the repository-owned
`.agents/scripts/pre-pr.sh` dispatcher when present and stops on failure. Keep
the deterministic CLI and repository dispatcher directly callable for
diagnostics without exposing either as a separate delivery outcome.

For a second repository, the parent must stage its owned paths itself through a
standalone shell tool call whose top-level `workdir` is that repository, then
invoke the repo-scoped `semantic-commit` as a separate sole mutation. A blocked
`git -C` or shell-embedded cwd change is a routing instruction, not a request
for the user to stage on the agent's behalf. If no attested target-workdir
surface exists, use a target-rooted managed session; only report a capability
blocker after that route is unavailable.

## Labels

- Labels describe the record's type, area, state or size, and workflow for
  triage and automation.
- When the active project provides `manifests/forge-labels.yaml`, select labels
  from that catalog and follow `core/policies/forge-label-taxonomy.md`; current
  CLI / skill surfaces handle ensure, validation, and application details.

## Test-First Evidence Gate

- The test-first gate is enforced in the released `forge-cli` surface, not a
  client-side hook: when `[test_first].require` resolves true, `forge-cli pr
  create` / `pr deliver` require `--test-first-evidence <dir>` for `--kind
  feature` / `bug` records (both the create and adopt paths, and the
  `--dry-run` preflight). `docs` / `chore` / `ci` / `refactor` are exempt.
- The retained PR and plan parent outcomes (`deliver-pr`,
  `deliver-plan-tracking-issue`, and `deliver-dispatch-plan`) thread that flag
  through their internal create/deliver phases for `--kind feature` / `bug` and
  omit it for exempt kinds. Point it at the `verify`-clean directory produced
  by the policy-owned `test-first-evidence` CLI flow.
- The gate is **off by default**. It is opt-in via `[test_first] require =
  true` in either a repo `.forge-cli.toml` or the user-global
  `${XDG_CONFIG_HOME:-$HOME/.config}/forge-cli/config.toml`. Precedence: explicit
  flag > repo config > global config > default (off). A global opt-in turns the
  gate on for every repo without a per-repo file.
- The evidence directory must hold a strict-verification-clean
  `test-first-evidence.record.v2`: testable classification, actual contract
  delta, affected-test decision, meaningful failing fields or a complete
  waiver, scoped passing validation, and explicit residual gaps. The parent
  workflow owns classification, affected-test and waiver judgment, suite
  convergence, and residual-gap disclosure;
  `core/policies/evidence-control-plane.md` owns routing, while the
  `test-first-evidence` CLI owns storage and strict verification.
- Record v1 remains readable but is ineligible for feature/bug delivery. Re-run
  the v2 lifecycle rather than inferring missing impact and ownership facts.
- A non-testable waiver records why meaningful red cannot exist and substitute
  validation. Deferred test debt additionally requires follow-up and expiry;
  neither path removes final-validation or residual-gap requirements.
- Failures surface as `test_first_evidence_required`,
  `test_first_evidence_v1`, `test_first_evidence_classification`,
  `test_first_evidence_incomplete`, or `test_first_evidence_unreadable` (exit
  `DATA`). Pin and consumed-surface detail live in
  `docs/source/nils-cli-surface.md`; the full engineering contract lives in
  `core/policies/evidence-control-plane.md`, and record mechanics live in the
  `test-first-evidence` CLI.
