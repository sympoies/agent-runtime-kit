# Main Agent Mode Blocker Inventory

Status: B1 repaired locally; B2 and B3 remain queued
Date: 2026-07-27
Source: Phase C of `2026-07-27-main-agent-fresh-session-e2e-plan.md`

## Purpose

Phase C found that Main Agent Mode could not complete a lane. This document is
the ordered repair queue plus the E2E scope that remains to be rerun.

B1 is repaired in the local nils-cli and agent-runtime-kit delivery branches.
B2 and B3 decide whether a failed run can be recovered, and the F-items are
friction that costs turns but does not stop delivery.

Raw per-scenario evidence, rerun selectors, and receipts stay outside the
repository beside the run:

- `$AGENT_HOME/out/e2e-20260727/e2e-result-and-improvements.md` — Phase A/B
- `$AGENT_HOME/out/e2e-20260727/phase-c-result-and-improvements.md` — Phase C/D

## How A Lane Dies Today

A worker must run commands to do its job: execute the test it wrote, run the
declared validation, and create the commit. The coordination guard cannot
analyse which files a shell command will touch, so it conservatively marks every
shell invocation as targeting the whole repository
(`core/hooks/shared/session-coordination-guard.py`):

```python
operation = "shell"
targets.append({"kind": "repository", "repository": repository, "value": "."})
```

An assignment packet that declares narrow scopes — which the Main Agent Mode
skill explicitly requires — produces a claim covering only those paths. The
whole repository is not a subset of them, so every command is denied
`uncovered-mutation-scope`.

A worker can therefore still author files through an explicit file-target edit
tool, but cannot execute anything at all. That includes the command it is
supposed to use to report that it is stuck.

## Blockers

### B1 — A scoped claim and shell execution are mutually exclusive

Severity: blocked all useful work. Repaired locally on 2026-07-28.
Area: `session-coordination-guard.py`, `coordination/claims.rs`, Main Agent
Mode skill and protocol.

Observed with `scopes: ["src/sum.sh", "tests/case-sum.sh"]`. Everything after
authoring was denied `uncovered-mutation-scope`:

| Step | Command | Result |
| --- | --- | --- |
| Test-first evidence | `bash tests/case-sum.sh` | blocked |
| Declared validation | `bash tests/run.sh` | blocked |
| Delivery | `semantic-commit` | blocked |
| Widen the claim | `agent-scope-lock claim` | blocked |
| Completion packet | `main-agent checkpoint` | blocked |
| Claim release | `main-agent release` | blocked |
| Anything at all | `bash -c 'echo hi'` | blocked |

The Codex lane hit the same wall from the other side,
`[reason: shell-target-unresolved]`.

The original scope projection left no working combination. In
`crates/agent-session/src/coordination/context.rs`:

```rust
// scopes_overlap
(ScopeKind::Repository, _) | (_, ScopeKind::Repository) => true,
// scope_covers
(ScopeKind::PathPrefix, ScopeKind::Repository) => false,   // via the `_` arm
```

| Lane scope | Can run shell? | Parallel lanes in one repository? |
| --- | --- | --- |
| path or directory | no | yes |
| repository | yes | no — any two repository scopes always conflict |

So the skill's own instruction ("scopes must be narrow enough not to overlap
another live worker") guarantees a dead lane.

Worktrees are the missed lever. Every lane already runs in its own managed
worktree, and the claim already carries `worktrees` fingerprints that
`evaluate()` compares — but only as an *additional* conflict reason
(`same-worktree`), never as a disambiguator. Two claims in different worktrees
still collide on `overlapping-scope`.

The initial proposal below was to add a durable `Checkout` scope kind. The
implementation investigation rejected that proposal: `Checkout × Path` still
cannot prove path containment without threading checkout identity through
every scope comparison; a new closed enum value would also make existing v1
registries unreadable by the released binary.

The final repair keeps the v1 scope grammar. The hook emits the existing exact
shape `operation:"shell"` plus one repository-form target and one checkout
binding. Authenticated Main Agent worker bootstrap now mints a private
checkout-shell grant on the exact assignment-derived claim. During `admit`,
nils-cli accepts the opaque target only when that grant is present, the claim
names the repository, and its existing worktree fingerprint matches the
binding. Generic claims cannot request or observe the grant. Explicit edits
continue to use Path coverage, another checkout fails closed, and conflict
evaluation remains based on the narrow declared paths plus worktree identity.

Acceptance: a packet declaring only its own targets completes test-first,
validation, one signed commit, and a `submitted` checkpoint without widening its
claim, and two lanes in one repository run concurrently.

### B2 — A `working` lane whose runtime died cannot be terminalized

Severity: a failed run can never be closed. Not repaired.
Area: `crates/agent-session/src/main_agent.rs`.

After a worker dies past bootstrap, its assignment stays `working` with a claim
alive on TTL. `worker cancel` requires a proven pre-claim failure, so it
refuses; `worker reassign` fails at diagnosis. Supervision still reported
`healthy_progress` for one such lane and `startup_dialog_failure` for the other.

The only remaining tool is Agent Console `group-cleanup` with `mode:"force"`,
which deletes the Main session — the session that would have to run it.

This is the direct generalization of the defect repaired in `7b3aba77`, which
only covers `starting` and `blocked`.

Acceptance: bootstrap a worker, stop its runtime, and require a non-healthy
classification plus an executable terminal action that leaves the run and the
Main session intact.

### B3 — An exhausted-readiness live worker has no recovery route

Severity: recovery requires stepping outside the CLI. Not repaired.
Area: `main_agent.rs` supervision, `session-coordination-guard.py` allowlist,
`agent-session` command surface.

A worker that launched but never received its prompt is durably recorded as
`submit_recovery.state: "failed"`, yet supervision classifies it
`claim_renewal_required` and prescribes `agent-session work-context renew`.

That prescription is not admitted: the guard's allowlist covers `status`, `set`,
`clear`, `advise`, `acknowledge`, and `claim`, but not `renew`, `release`,
`show`, or `check`. The supervisor's own recovery command is blocked.

The documented alternative, `main-agent worker reconcile-recovery`, requires the
runtime to already be stopped, and `agent-session` exposes no command to stop
one. Recovery needed a raw `tmux kill-session`.

Acceptance: an exhausted-readiness live worker returns an executable recovery
action needing no raw terminal command.

### B4 — Worker lifecycle commands are treated as repository mutations

Severity: removed the escape hatch. Repaired locally with B1 on 2026-07-28.
Area: `session-coordination-guard.py`.

`main-agent checkpoint` and the claim-release path change the orchestration
registry and the claim, not repository content, yet they are classified as shell
mutations and gated by claim scope. A scoped worker therefore cannot record the
`blocked` checkpoint its own packet asks for.

`command_bypasses_admission` already short-circuits admission unconditionally,
so admitting these exact authenticated, revision-fenced shapes is a contained
change in the same family as the `bootstrap` shape that is already allowed:

- `main-agent checkpoint --file <private-json> --if-revision <n> --idempotency-key <key> --format json`
- `agent-session work-context renew` / `release` (revision-fenced)
- `agent-session work-context show` / `check` (read-only)

The projected `agent-session` lifecycle shapes were already exact-validated.
B1 adds the missing private-file, revision-fenced checkpoint shape. Acceptance
now proves a worker with any claim scope can record a checkpoint and release
its claim while untrusted and malformed near misses remain rejected.

## B1 Final Implementation

Scope remained B1. B2 and B3 stay queued. The checkpoint part of B4 was
included because it is required by B1's submitted-lane acceptance; the existing
exact `show`, `check`, `renew`, and `release` lifecycle projections remain
unchanged.

### Contract

`worktree_fingerprint(epoch, key, checkout)` remains a keyed HMAC owned by
nils-cli. The runtime hook never receives the key and raw checkout paths never
enter public output or the durable claim. `OperationTargetsInput` already
carries the private checkout binding needed for admission.

The special coverage rule is intentionally exact:

1. `operation` is `shell`;
2. there is exactly one `repository` target with value `.`;
3. there is exactly one checkout binding for that repository;
4. authenticated Main Agent worker bootstrap minted the active claim's private
   checkout-shell grant;
5. before minting, the packet worktree, launch cwd, durable assignment
   worktree, and authenticated session cwd resolved to one canonical checkout;
6. the active claim names the repository; and
7. nils-cli fingerprints the bound checkout and finds it in the claim's
   existing `worktrees`.

Only then may the repository-form shell target bypass ordinary `scope_covers`.
Generic claim/set inputs have no field for the private grant, public
work-context output removes it, and old records default it to absent. An
ordinary enforce claim therefore cannot obtain the exception from its
automatically attached worktree fingerprint.
`validate_physical_targets` still proves the checkout origin. Explicit Path
targets still require Path coverage. A missing binding, a second binding, a
different checkout, a different repository, or any non-shell operation fails
normal coverage.

The grant is deliberately checkout-level coordination, not a filesystem
sandbox or repository authorization. Path scopes remain the semantic lane and
review boundary; Main Agent acceptance must reject an out-of-scope diff. An
adversarial same-user process requires an OS security boundary outside this
hook/coordination contract.

### Why there is no Checkout scope kind

The claim already records worktree identity independently of scopes. Reusing
that identity at operation admission avoids a registry schema change and keeps
the existing separation:

- scopes declare semantic lane overlap;
- worktrees identify physical checkout overlap; and
- the private bootstrap grant plus operation binding prove which isolated
  checkout may hold an opaque shell lease.

Adding `Checkout` to the closed v1 enum would have introduced mixed-version
decode failure. It would also have required checkout identity on Path targets
to define `Checkout × Path` coverage without either false conflict or unsafe
widening. The admission-only rule needs neither change.

### Runtime integration

The hook retains its existing shell projection:

```python
operation = "shell"
targets.append({"kind": "repository", "repository": repository, "value": "."})
checkouts.append({"repository": repository, "path": str(root)})
```

The Main Agent Mode skill and protocol now say to keep assignment Path scopes
narrow; workers do not add repository scope merely to run tests or delivery.
The exact trusted, private-file, revision-fenced `main-agent checkpoint` shape
is a control-plane operation and bypasses repository admission. Near-miss
shapes remain denied.

### Validation

- nils-cli regression: a bootstrap-granted narrow Path claim plus its own
  checkout-bound shell is admitted, while an ordinary claim is denied;
- negative coverage: another checkout and an explicit out-of-scope edit are
  denied `uncovered-mutation-scope`;
- repository binding: a claim that does not name the checkout repository
  cannot borrow its worktree fingerprint;
- concurrency: two sessions in the same repository, distinct worktrees and
  disjoint Path scopes, both hold active shell operation leases;
- runtime hook: shell projection remains one repository target plus one exact
  checkout binding;
- lifecycle: only the exact private revision-fenced checkpoint shape bypasses
  admission;
- paired-change owner: build the nils-cli source checkout, then run
  `AGENT_SESSION_SOURCE_BIN=<absolute-agent-session> bash
  scripts/ci/session-coordination-coupled-acceptance.sh`;
- gates: `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast` and
  `bash scripts/ci/all.sh`.

The full Phase C worker acceptance is rerun after the local binaries and runtime
surfaces are deployed: test-first, implementation, validation, signed commit,
and `submitted` checkpoint without claim widening or raw terminal input.

### Note for whoever picks up B3

A partial fix was prototyped and deliberately reverted this session: adding
`submit_recovery_exhausted` to `worker_failed_preclaim` made the classification
`pre_claim_failure`, but its next action (`cancel`) still fails for a live
worker, so it would have shipped an unexecutable instruction. B3 needs its own
classification plus a typed runtime-stop, not an extension of the pre-claim
fact.

## Repaired In This Session

Local `main` in both repositories; nils-cli is still unpushed.

| Item | Commit | Defect |
| --- | --- | --- |
| Pre-claim startup failure was unrecoverable | nils-cli `7b3aba77` | `provider_terminated` is turn-derived, so a provider exiting during startup left `failed_preclaim` false; `claim_renewal_required` outranked `pre_claim_failure` and both `cancel` and `reassign` refused |
| A dead worker was reported healthy | nils-cli `7b3aba77` | The classifier read `preclaim_blocker`/`terminal_recovery_reconciled` but never the computed pre-claim verdict |
| The pinned bootstrap command was denied | runtime-kit `0ca2819c` | `worker start` writes an absolute `main-agent` path into every worker prompt, but both pre-claim allowlists compared argv against the bare name |
| No Claude worker could pass the readiness gate | runtime-kit `0ca2819c` | The gate required `classification:"supported"`; `agent-session` reports `partial` for Claude permanently |

The third item was a cross-repository regression: nils-cli started pinning the
absolute path on 2026-07-25 (`3aa6aca4`) without updating the runtime-kit
allowlist written on 2026-07-22 (`546d7a2c`). Every managed worker launched in
that window had its mandated first command denied.

## Remaining Friction

| ID | Problem | Suggested fix |
| --- | --- | --- |
| F22 | A worker between launch and bootstrap is classified `claim_renewal_required`, telling the manager to renew a claim that never existed | Give the pre-bootstrap window its own state |
| F24 | A packet whose `repository` is a path instead of `owner/name` is accepted by `worker start` and only fails at bootstrap, costing a launch, a readiness wait, and a reassign | Validate the identifier inside `worker start` before creating a session |
| F25 | A fresh Claude worker launched with an empty composer; the runtime still reported `submit-key-recovery-succeeded`. Transient — a relaunch delivered normally, and Codex delivered first time | Verify the composer holds the prompt before reporting success; report `prompt-not-present` otherwise |
| F27 | In a checkout with no git remote, repository identity cannot resolve, and every scoped write plus the blocked-checkpoint escape hatch is denied with a generic identity error | Detect a remote-less checkout at claim or bootstrap time and fail with that specific cause |
| F28 | A worker told it had mailbox mail did not know the consumption command and searched the web for it. It also invented `main-agent checkpoint --revision --state --blocker-summary`; the real shape needs `--file <json>` | Name the exact commands in the worker prompt or the notification |
| F29 | With identical packets, Claude's writes were admitted and Codex's were denied `shell-target-unresolved`, because Claude edits through a file-target tool and Codex writes through shell | Resolved by B1 |
| F13 | `worker start` rejects a packet with `invalid-assignment-packet: coordination input is invalid` and names no field; the serde error is discarded. The skill also names `exclusions` and `invariants`, which are not top-level schema fields | Surface the field path; align the skill with the schema |
| F18 | Read-only `semantic-commit` probes are denied when composed — `cd X && semantic-commit …`, or a trailing `2>&1` parsed as a CLI argument | Classify read-only subcommands and redirections before default-delivery analysis |
| F05 | `agent-session activity doctor` reports `configured:false` while the compatibility probe reports `configured:true` with `compatibility_owner:"agent-hook"` | Reconcile the doctor with agent-hook ownership |
| F20 | The tool shell is zsh, which sources neither `.profile` nor `.bashrc`, so `cargo` is absent; the natural `PATH=…` workaround is blocked by the governed-executable hook | Extend login-shell parity to zsh, or have the block name the sanctioned entrypoint |

## E2E Scope Still Unrun

Reached: C01 activation, C02 startup on both products, C03 supervision and
claims, C04 authenticated mailbox.

Blocked by B1, to rerun once it is fixed:

- C05 request-changes and same-session resume
- C06 dependency wait
- C07 account-next (Codex) and unsupported-account behaviour (Claude)
- C08 graceful recovery boundary
- C09 acceptance and retirement
- Phase D parity beyond the two differences already recorded (F25, F29)

Phase A/B were completed in the earlier run and re-verified on a fresh fixture:
the governed `default-branch` dry-run, one signed commit, stale `--expect-head`
rejection, and hook denial of an ordinary default-branch commit all passed.

## Reproduction Notes

- Fixture: a local clone reduced to a minimal shell project by one governed
  `default-branch` commit. It needs a remote configured, even a non-routable
  one, or F27 blocks every write.
- An assignment packet's `repository` must be `owner/name`; `worktree` and
  `launch.cwd` are absolute paths.
- `exclusions` and `invariants` belong inside the free-form `task` object;
  `AssignmentInput` is `deny_unknown_fields`.
- The run started in this session, `2dfae16e`, cannot be closed from inside its
  own Main session. The exact force-cleanup command is in
  `phase-c-result-and-improvements.md`.
