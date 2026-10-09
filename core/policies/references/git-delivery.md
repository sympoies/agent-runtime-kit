# Git Delivery Reference

On-demand explanations and recovery for [delivery boundaries](../git-delivery.md).
Read the relevant section for a refusal or exceptional delivery route; current
CLI help owns exact syntax. Worktree lifecycle rules remain in the boundary policy.

## Collaboration Ledgers

A repository with a tracked, regular top-level `.agent-collab` file containing
exactly `collab-protocol: 1` on one line is a collaboration message ledger.
The marker qualifies only from the committed tree of the remote's default
branch. A marker present only in the working tree, index, or a non-default
branch does not qualify.
The marker belongs in ledger repositories, not in their tooling/template
source repositories; a `PROTOCOL.md` filename alone is not a marker.

For ledger operations, the repository's `tools/collab.py` owns authoring,
synchronization, provider calls, and direct default-branch delivery: one commit
per message under its protocol. Use only that tool; agents must never invoke
raw `git` or `gh`/`glab` there. The code-repository PR/MR flow, managed-worktree
commit route, and `forge-cli repo push-default` exception do not apply to these
operations. The marker grants no general delivery bypass or authority to
change unrelated repositories, publish releases, or rewrite ledger history.
Unmarked repositories retain the ordinary delivery rules.

The default-delivery PreToolUse hook classifies the submitted shell command,
not Python subprocesses. A literal `python3 tools/collab.py ...` already passes
the default-delivery hook; its internal Git calls need no exemption from that
hook. Other hooks still apply, including the Python runner policy in a
repository with `uv.lock`. Hook admission alone does not verify the marker or
authorize this route in an unmarked repository.
Direct default-branch pushes remain refused even when the marker is present.


## Resolving The Remote's Default Branch

The guard has to know which branch is the default before it can say whether a
push would move it. It resolves that locally, from the cached
`refs/remotes/<remote>/HEAD` corroborated by the primary worktree's branch,
because a cached head is locally writable and a stale or planted one would
reclassify a default-branch push as a feature push.

How firmly it resolves decides what a refusal can claim, and the three states
are not interchangeable:

- **Corroborated** — cache and primary worktree agree. A destination can be
  proven to be the default, or proven not to be.
- **Uncorroborated** — a cached name the primary worktree does not confirm,
  which is the ordinary state when the primary checkout is parked on a feature
  branch. The default is one of those two names, so a destination that is
  neither is admitted, and either candidate stays unverified. This is why a
  parked primary checkout no longer makes every push in the repository
  unclassifiable.
- **Unknown** — no cached head at all. No branch destination is decidable, and
  the primary worktree's branch is not accepted as a substitute: a repository
  whose primary checkout sits on a feature branch would otherwise make the real
  default look like a safe destination.

Two classes of push need no default-branch name at all. A destination outside
`refs/heads/` — a tag, a note — cannot move a branch whatever the default turns
out to be, so it is admitted in every state. An `--all` or `--mirror` push moves
every branch there is, so it is refused in every state.

A push that cannot be classified names the condition that tripped. "The default
branch could not be resolved" is not actionable on its own, and steering such a
caller to a governed surface that fails the same way is worse than saying
nothing.

### Publishing to an empty remote

A remote that advertises no refs has no default branch, so publishing its first
branch cannot move one. Nothing in the resolution above can establish that from
local state, and the usual remedy is a dead end: `git remote set-head <remote>
--auto` has no remote HEAD to read, and `forge-cli repo push-default` needs an
expected base that does not exist yet. Publishing the first branch of an empty
remote is therefore a governed bootstrap publish, whose safety argument is the
emptiness itself — checked against the remote, never inferred from missing
remote-tracking refs, which a fresh clone also lacks. It creates a ref and
forces nothing.


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

An authoring `semantic-commit` after any other command in the same tool call is
`unverified` with `rule=executable-resolution`: the guard cannot prove which
executable that word resolves to. Run it as its own tool call, after staging
with `git add -- <paths>` in a separate call. Its help, `--dry-run`, and
`--validate-only` forms are not affected.

When one word could not be classified, the refusal names it as `word=`. An
executable held in a variable (`bin=/path/tool; $bin …`) or run through `eval`
is opaque because it could expand to `git` or `semantic-commit`; spell the
command literally. After `source`, an alias, or a `PATH` change, the refusal
also names the command that changed executable resolution; run the later
command in a separate tool call or by absolute path. Read-only loops, `[[ ]]`
tests, `${var%|*}` expansions, arithmetic, and here-doc input to `python3` or
`cat` are classified as reads.

Each refusal names the governed surface for the operation actually attempted,
not the policy in general.


## Delivery Mode Decision Matrix

| Mode | Authorization | Authoring and delivery | Terminal evidence |
| --- | --- | --- | --- |
| PR (provider default) | Explicit current-task provider-delivery request, or an approved workflow that already owns PR/MR delivery | Signed `semantic-commit` on a non-default managed-worktree branch, then the active `deliver-pr` path | PR/MR URL, delivered head, reviews/checks, and provider merge read-back |
| Direct-main (`direct` exception) | The maintainer explicitly requests direct commit and push to the default branch in the current task | Exactly one signed `semantic-commit` on a non-default managed-worktree branch, then `forge-cli repo push-default --expected-base <full-sha> --reason-file <path>` | Structured receipt whose post-push `observed_remote_sha` equals the delivered head |
| Default-branch (`direct` local completion) | The maintainer explicitly requests one local-only default-branch commit in the current task | Exact `semantic-commit default-branch` in the clean primary checkout; no provider call | `cli.semantic-commit.default-branch.v1` receipt with `provider_delivered=false` |

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
owner (read `git-cli sync-default --help`). The PreToolUse hook uses cached local
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

## Scheduled devlog fold exception

Once the maintainer enables the kit fragment rule and provisions a repository's
fold job, that job may update its protected default branch without an
agent-authored managed-worktree commit. This bounded CI exception applies only
to the indexed development log: fold eligible pending entries, update month
files and their index, and consume the folded fragments. It grants no agent
permission to edit month files in a PR, push other content, bypass hooks, merge
feature work, release, or enable the kit switch.

The trusted default-branch job must run `devlog fold` and `devlog check`, create
no commit when the fold is empty, and publish only App-authenticated commits
whose provider verification is true. Provision the App as the narrowly scoped
protection exception, or use an independently approved auto-merge PR route;
never weaken required signatures or branch protections for other actors.
A rejected fast-forward update caused by a moved default branch is refetched
and folded again from the new tip, with a bounded retry budget. Other failures
stop. No force update or agent-side fallback is authorized.

The [fold recipe](../devlog/ci-fold.md) owns workflow wiring and provider acceptance.


## Test-First Evidence Gate

- The test-first gate is enforced in the released `forge-cli` surface, not a
  client-side hook: when `[test_first].require` resolves true, `forge-cli pr
  create` / `pr deliver` require `--test-first-evidence <dir>` for `--kind
  feature` / `bug` records (both the create and adopt paths, and the
  `--dry-run` preflight). `docs` / `chore` / `ci` / `refactor` are exempt.
- The retained PR and dispatch parent outcomes (`deliver-pr` and
  `deliver-dispatch-plan`) thread that flag
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
