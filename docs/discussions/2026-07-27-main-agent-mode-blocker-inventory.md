# Main Agent Mode Blocker Inventory

Status: B1/B4 deployed, and their real-product C02-C05 closure canary is now
closed on both providers — but only with four manual workarounds, filed here as
new blockers B5-B8. B5 now has implementation closure in source: every finite
projected lifecycle and mailbox shape accepts the exact trusted absolute
`agent-session` path while relative and shadow spellings remain denied. Its
deployed real-product release/retire canary is still pending. B6 now has
implementation closure in a regression-first paired nils-cli/runtime-kit
candidate: the
runtime issues one session/incarnation-bound mode-`0600` checkpoint file, and
the coordination hook admits only that exact path through ordinary `Write` or
canonical `printf` redirection. Provider-aware surface compatibility and an
exact-incarnation readiness gate prevent mixed deployments and pre-B6 sessions
from reaching claim acquisition. B6 delivery, deployment, and real-product
field closure are not yet claimed. B2 implementation, signed local-main
integration, release binary install, and rendered-surface deployment are
complete. A positive stopped-runtime canary ran and passed, but it does NOT
establish B2 field closure: the fixture's clean provider exit released the
claim and tore down the broker before the action ran, so B2's defining
condition — a dead worker still holding a claim alive on TTL — was never
reproduced. B2 field closure remains UNCLAIMED. GitHub provider delivery is
spam-blocked; this session is authorized to use governed local-main delivery
instead. Open work: B5 field validation, B6 delivery/deployment and field
validation, B7-B8 implementation and field validation, the
unexercised B2 live-claim branch, then B3, then C06/C07, the residual C08
recovery classifications, and the remaining Phase D parity items
Date: 2026-07-27
Updated: 2026-07-28
Source: Phase C of `2026-07-27-main-agent-fresh-session-e2e-plan.md`

## Purpose

Phase C found that Main Agent Mode could not complete a lane. This document is
the ordered repair queue plus the E2E scope that remains to be rerun.

B1 is in local `main` in both repositories, the rebuilt nils-cli binaries and
runtime surfaces are deployed, and the installed-binary coupled acceptance is
green. The separate B1 real-product C02-C05 closure canary has now closed on
both providers. Reaching that closure required working around four distinct
root causes by hand, filed below as blockers B5-B8. B5 is deployed; B6 has
implementation closure in its paired candidate but remains undelivered,
undeployed, and field-unvalidated. B7-B8 remain
unrepaired. None of them was a defect in the B1 scope/admission design itself.
Both lanes bootstrapped, ran
checkout-bound shell validation under a narrow claim, created signed commits,
checkpointed `submitted`, took one revision-fenced `request-changes` plus a
private mailbox message, resumed in the same session without widening the
claim, resubmitted, and were accepted, released, deleted, and proven absent
from a fresh session list.

B2's repair purpose is achieved in candidate source: a bootstrap-complete
worker whose exact runtime stopped can be terminalized without deleting the
Main session, losing its worktree/diff, sending input, or revoking unrelated
coordination authority. The final signed, clean nils-cli candidate head is
`99ba960e914e58f2813ca1864044aa858759080b`; its local-fast gate completed
7,666 tests plus two doctests, and the release binary is installed. Its signed
one-commit current-main integration head is
`c64b52ee92bdd62b2f0c10786bbc6b1f87323561`; the final integration gate
completed 7,669 tests plus two doctests, and the same tree is committed on
local nils-cli `main` at `a3f9b2f3e7412cd47fae78ca95178f87e4f3675f`.
The final
signed, clean runtime-kit B2 implementation head is
`d35f3960338bc4893dc0bb158e88c341cb15a44a`; this doc-only status closeout
follows it. A signed one-commit integration candidate based on current
runtime-kit `main` also passes full CI positions 1-17. Deterministic smoke
passed 105 cases with one host-capability skip, shared hooks passed 349/349,
and the final specialist review reported no findings.

The runtime surfaces were deployed successfully, preview before apply, from
the durable checkout
`$HOME/.local/state/agent-runtime-kit/deploy-checkouts/agent-runtime-kit-b2-20260728`;
doctor, prompt, and plugin checks are green. The installed live-runtime
negative `reconcile-stopped` canary failed closed with assignment revision and
state unchanged, and that negative result was re-verified against a fresh live
lane on 2026-07-28.

A positive stopped-runtime canary has now run and passed, but it does **not**
establish B2 field closure, and field closure remains unclaimed.

The fixture was obtained without any prohibited technique: an ordinary lane was
launched, bootstrapped to `working`, submitted, returned to `working` by a
normal typed `request-changes`, and then its runtime was stopped by sending the
provider's own exit command (`/quit`) through the released `agent-session send`
API while the worker was idle with zero admitted operations. No raw tmux
control, no signal or kill, no `agent-session delete`, no force group cleanup,
and no controller impersonation were used. The durable session record survived
with the same incarnation and `resumable: true`, and the worktree kept its
uncommitted work.

That clean exit is exactly why the run is not field closure. A graceful
provider shutdown also tears down the coordination broker and releases the
claim. B2's defining condition is the opposite — "its assignment stays
`working` with a claim alive on TTL" — and that condition was absent: the
post-stop projection recorded `claim_active:false`, `claim_id:null`,
`broker_authoritative:false`, and the action's own
`proof.worker_claim.observed_at_stage1:false`. The claim-revocation branch that
makes B2 a blocker was therefore never exercised against a real product. What
the run does establish is narrower but still real: the terminalization path is
correct on an already-quiescent, claim-absent stopped worker, and the
fail-closed side is correct against a live one.

See "What the positive canary did and did not prove" under B2 for the exact
split, and the run directory named below for raw evidence.

Both direct-main candidates are ready, but the dry-run form of
`forge-cli repo push-default` fails before mutation in both repositories
because GitHub GraphQL returns HTTP 403
(`The owner of this application has been marked as spammy`).
Both candidates were instead committed through governed local-only
default-branch completion: nils-cli at
`a3f9b2f3e7412cd47fae78ca95178f87e4f3675f`, and runtime-kit in the commit
containing this inventory. Both receipts record `provider_delivered=false`;
this workflow did not push. After those local receipts were written, both
`origin/main` refs were independently observed at the same commits as their
local `main` branches, with reflogs recording `update by push`. That later
remote update was not initiated by this workflow and its provenance is not
established here; treat the alignment as observed external state, not as this
delivery's provider evidence. Do not bypass the governed provider-delivery
path with a raw Git push.

B3 is still the next implementation gap. It decides how to stop a still-live
pre-claim/readiness-failure runtime without raw terminal control. Its original
blocking justification is weaker now that a controlled stop of an idle worker
is demonstrably reachable through the provider's own exit path, but that route
needs a cooperative, idle provider; B3's own scenario is an exhausted-readiness
worker that is still live and cannot be driven, and that still has no typed
stop. The F-items are friction that costs turns but does not independently stop
delivery.

Raw per-scenario evidence, rerun selectors, and receipts stay outside the
repository beside the run:

- `$AGENT_HOME/out/e2e-20260727/e2e-result-and-improvements.md` — Phase A/B
- `$AGENT_HOME/out/e2e-20260727/phase-c-result-and-improvements.md` — Phase C/D
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260728-083244-b1-closure-b2-positive-canary/result-and-improvements.md`
  — the closed B1 C02-C05 canary and the passing B2 positive canary

## Continuation Order

1. **Keep delivery governed while provider delivery is unavailable.** GitHub
   delivery is spam-blocked for this session. Use the user's authorized
   local-main path, signed commits, compare-and-swap, and outside-repository
   receipts; never weaken hooks or leases. A repository already ahead by one
   governed default-branch commit must first regain an aligned state before a
   second default-branch delivery.
2. **Repair the four B1 canary root causes.** The canary closed, but each
   closure step required a manual workaround that an unattended worker cannot
   discover. In severity order: the `agent-session` lifecycle bare-name
   deadlock (B5, implementation repaired; field validation pending), the
   unwritable out-of-checkout checkpoint file (B6, implementation closure in
   its paired candidate; delivery/deployment and field validation pending), the
   Codex untrusted-repository bootstrap death (B7), and `worker start`
   persisting an assignment before validating its cwd (B8). B5 and B6 each
   independently prevented an unattended lane from ever terminating cleanly;
   B5's field closure and B6's deployment/field closures remain separate.
3. **Close B2 in the field.** Re-run the positive canary against a stopped
   worker whose assignment-derived claim is still active on TTL, and require
   `proof.worker_claim.observed_at_stage1:true` plus a post-action read proving
   the claim gone. Separately, supervise a lane whose provider process is dead
   but whose tmux session still exists, and require a non-`healthy_progress`
   classification. Until both run, B2 field closure stays unclaimed. This
   likely needs B3's typed stop, since a cooperative exit cannot leave the
   claim behind.
4. **Repair B3 after the failure-state split is explicit.** Add a typed
   exact-incarnation runtime-stop primitive that stops the runtime without
   deleting durable session state. After stopped proof, route a failed
   pre-claim worker through guarded cancel/retire/reassign; retain
   `reconcile-recovery` for an unknown `attempting` send.
   Do **not** key the new classification on `submit_recovery.state:"failed"`
   alone. The 2026-07-28 canary observed a fully healthy lane — `running`,
   `healthy_progress`, `failed_preclaim:false`, which went on to bootstrap,
   commit, submit, and take a `request-changes` — carrying
   `submit_recovery.state:"failed"` with
   `result:"worker-activity-not-authoritative-starting"` from a recovery
   attempt nine seconds after session creation. That field is not a
   discriminator. Pair it with F25's composer-presence check or with proven
   absence of subsequent assignment and worktree progress.
5. **Run C06, C07, and the remaining Phase D parity items.** C02-C05 are closed
   on both providers, and C09 is closed on both but only with hand-supplied
   release argv pending B5 field validation. C08's recovery
   boundary is only partly closed: the
   B2 post-claim path ran on a single Codex fixture lane, and only in its
   claim-absent form. C06 dependency wait and C07 account-next /
   unsupported-account behaviour were not reached because both provider
   accounts hit their usage ceilings during the closure session.
6. **Then take the friction wave.** Fold F25 prompt-presence truth into B3;
   address F22 and F33 together while touching the supervision and
   pre-bootstrap classifier. Take F30, F31, and F34 as the remaining
   claim/operation ownership work; B5's source repair does not close them.
   Take F32 with F13, since both are the same discarded-serde-error shape.
   Follow with F24/F28/F27 input and guidance clarity; F28 in particular is not
   closed, because the closure canary's own packets shipped wrong mailbox argv.
   Keep F18/F05/F20 as the later ambient-tooling wave.

B2 established the missing distinction between post-claim failure and
pre-claim failure, and its implementation closure holds; its field closure does
not, because the one positive run never reproduced a live claim. The
implementations are on both local default branches. First restore the governed
GitHub provider-delivery path, then repair the four B1 canary root causes, then
close B2 in the field, then implement B3's typed stop, then finish C06/C07 and
Phase D.
B3 may reuse B2's exact-runtime and quiescence proof helpers, but after the
typed stop it should enter the existing pre-claim cancellation path rather
than the B2 post-claim transition. Do not implement B3 by classifying a live
exhausted worker as `pre_claim_failure`; `worker cancel` deliberately rejects
a live worker.

## How A Lane Died Before The B1 Repair

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

Ids are filing order, and the sections are grouped narratively: B5-B8 sit
directly after B1 because they are what its closure canary uncovered. The
Continuation Order above, not this section's sequence and not any per-blocker
"priority" wording, is the authoritative repair order.

### B1 — A scoped claim and shell execution are mutually exclusive

Severity: blocked all useful work. Repaired, integrated, and deployed on
2026-07-28.
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

Portable acceptance is complete: a packet declaring only its own targets can
run checkout-bound shell work without widening its claim, explicit
out-of-scope edits still fail closed, and two lanes in one repository can hold
disjoint claims concurrently. The installed-binary coupled acceptance is
green. The real-product C02-C05 closure canary is now closed on both providers
and confirmed the B1 scope/admission design: both lanes ran their tests,
validation, and `semantic-commit` from a narrow two-path claim, and neither
lane ever needed repository scope.

**B1 closure canary root causes.** The canary closed, but only after four
separate obstacles were worked around by hand. B5 is deployed; B6 has
implementation closure in its paired candidate. Both still need field
validation, while B6 also needs delivery and deployment. B7-B8 remain
unrepaired. None is a defect in B1's scope projection
or admission rule; all
four are in the surrounding worker lifecycle, and each is filed as its own
blocker below. B5 and B6 independently made an *unattended* lane unable to
finish; field closure is still required before the end-to-end promise is safe.

### B5 — A worker cannot release its own claim unless it uses the bare name

Severity: an accepted lane can never be retired. Implementation repaired on
2026-07-28; deployed real-product field validation remains open.
Area: `core/hooks/shared/session-coordination-guard.py`
(`projected_lifecycle_invocation`).

Before the repair, `projected_lifecycle_invocation` required
`words[:1] == ["agent-session"]`. A worker invoking the identical projected
shape by absolute path missed the admission bypass, was admitted as an ordinary
shell mutation, and the CLI then refused its own release:

```text
work-context release -> operation-in-progress
"the claim remains bound to an active or uncertain mutation operation"
```

The blocking operation is the release command itself. The worker can therefore
never release, its claim is renewed indefinitely by the broker heartbeat, and
`worker retire` fails `worker-not-quiescent` forever. In the canary this
deadlocked both accepted lanes until the exact bare-name shape recorded in the
Reproduction Notes was supplied by hand.

The two lanes are not equally strong evidence, and the difference matters. The
Codex lane is direct proof: it was given the exact shape, ran it, and its own
output showed `work-context release ... ok:true` followed by "Claim released
successfully". The Claude lane took three messages. Told only *that* the bare
name was required, it still composed a near-miss
(`work-context release --claim <id> --if-revision 1`, with no `--session`,
`--capability-file`, `--idempotency-key`, or `--format json`) and was refused
`operation-in-progress` twice. It released only after the complete invocation
was supplied verbatim. Because its runtime was alive and the broker was still
renewing, the claim could not have lapsed on its own at that point, so the
release is attributable to the exact shape rather than to TTL expiry.

That lane also reported, correctly, that it had no self-service recovery: see
F34.

This is the same defect class already repaired for `main-agent` in runtime-kit
`0ca2819c`, where `worker start` writes an absolute path into the worker prompt
while the allowlist compares the bare name. The `agent-session` lifecycle
allowlist carried the surviving sibling until this B5 repair.

Acceptance: a worker invoking any projected lifecycle shape by absolute path is
admitted exactly as the bare-name form, and a lane that holds its claim through
`request-changes` can still release and retire without hand-supplied argv.

Implementation closure is captured at the hook boundary. Regression-first
coverage made all 16 existing projected lifecycle and mailbox shapes fail
`shell-target-unresolved` when their trusted fixture executable was spelled by
absolute path. The repair normalizes only a bare name or absolute path whose
basename is `agent-session` for finite-shape comparison; the caller still
requires an absolute spelling to lexically equal the exact trusted resolved
executable. Bare-name PATH resolution retains its existing trust check. All 16
trusted absolute forms and their bare-name controls now pass, while a relative
`./agent-session` resolving to that same executable, an absolute same-name
shadow, a realpath-equivalent absolute symlink alias, a symlink-plus-dot-segment
alias, dynamic variables, shell wrappers, redirects, and every existing near
miss remain denied. The final shared-hook suite runs 350 cases: 349 pass and
one host-capability case skips.

Field closure is deliberately separate: deploy the repaired surface, run a
lane through `request-changes`, and prove that its own pinned absolute
`agent-session work-context release ...` succeeds followed by ordinary retire,
without supplying a bare-name workaround.

B5 covers only a *cooperative* worker that is able to run a command but is
using the wrong argv form. It does not cover a worker that cannot act at all —
quota-exhausted, wedged, or unresponsive — which still leaves an accepted lane
unretirable because no Main-owned action can revoke that claim. That residual
case is F31 and must be closed separately; landing B5 does not resolve it.

### B6 — The mandated out-of-checkout checkpoint file is nearly unwritable

Severity: a worker cannot report `submitted` or `blocked` without the manual
argv workaround. Implementation repaired in a regression-first paired
candidate; delivery, deployment, and real-product field closure remain open.
Area: the checkpoint file contract, `canonical_target_path`, and `SHELL_CONTROL`.

The checkpoint contract requires an absolute mode-0600 `.json` file outside the
governed checkout. Both natural routes are denied:

| Route | Result |
| --- | --- |
| edit tool (`Write`, `apply_patch`) | `target-boundary-unavailable` — `canonical_target_path` resolves an edit target against a git repository, and the path is outside every repository |
| shell redirection or heredoc | `shell-target-unresolved` — `SHELL_CONTROL` forbids unquoted `>`, `{`, and `}`, and JSON always contains braces |

The only admitted form is a simple-argv command carrying the JSON inside single
quotes, such as `perl -e '…' <path> '<json>'`. The Claude worker found it after
five failed attempts; the Codex worker never found it and stalled with its
implementation complete and no checkpoint. This is the mirror of F29. It is a
proven contributing cause of the previous canary's Claude lane stopping at
`working` without reaching `submitted`, but not an isolated one: F30's
prompt-versus-packet contradiction strands a lane at the same point, and the
2026-07-28 canary hit both. Fixing B6 alone is not proven sufficient.

Acceptance: a worker can create its private checkpoint file through an ordinary
edit tool or an ordinary shell redirection, without discovering an arg-form
trick.

The candidate is deliberately narrow and paired across repositories. On
managed start/resume, nils-cli pre-creates one empty regular mode-`0600` file
under the exact session's mode-`0700` coordination directory. Its filename is
bound to the SHA-256 digest of the runtime incarnation, its path is projected
as `AGENT_SESSION_CHECKPOINT_FILE`, and authenticated worker bootstrap returns
the same private `checkpoint_file`. A successor incarnation removes the prior
file.

The runtime-kit coordination hook independently reconstructs that path from
`AGENT_SESSION_STATE_DIR`, `AGENT_SESSION_ID`, and
`AGENT_SESSION_RUNTIME_ID`; it does not trust an arbitrary project-output
path. It requires the issued path to match byte-for-byte, verifies the private
session/coordination directories and single-link owner-only regular file, and
admits only a bounded JSON object through one ordinary `Write` or one
byte-canonical `printf '%s\n' '<json>' > <path>` command. The canonical raw
shell comparison rejects command substitution, parameter/backtick expansion,
compound commands, and alternate redirections without duplicating the
facade's closed checkpoint schema.

Compatibility is paired but provider-specific. `main-agent capabilities
--provider <codex|claude> --format json` requires the selected provider's
locked inventory rules, converged doctor record, and installed handler
self-probe; an absent other provider does not cause a false failure. The
separate authenticated `main-agent self readiness` proves the current
incarnation received the exact runtime path and still owns the trusted file.
`init`, `rebind`, and worker `bootstrap` enforce the same readiness before
claim acquisition or orchestration mutation. A pre-B6 session therefore fails
closed with `runtime-checkpoint-unavailable` and a typed resume/restart action,
rather than acquiring a claim and failing only at its final write.

Regression coverage first failed the natural runtime env/file projection,
bootstrap result, resume cleanup, provider-aware capability contract,
per-incarnation readiness, finite pre-claim command admission, handler
self-probe, and symlinked supported state-root case. Runtime-kit also retained
the observed `target-boundary-unavailable` and `shell-target-unresolved`
failures before its production edits. Focused nils-cli unit/integration tests,
the complete agent-session integration suite, the complete shared-hook suite,
the aggregate Codex/Claude dispatcher test, completion freshness, and the
deterministic conversation product-isolation smoke are green. API-contract,
maintainability, testing, and adversarial specialist review are closed with no
remaining findings after the provider-aware and per-incarnation corrections.

Implementation closure does not imply deployment or field closure. B6 still
requires signed delivery of both paired commits, rebuilt nils-cli plus synced
runtime surfaces, and a real-product worker that writes and submits through an
ordinary `Write` or canonical `printf` route with no `perl` workaround. It
does not close F30's independent prompt-versus-packet contradiction.

### B7 — A Codex worker dies at startup in an untrusted repository root

Severity: no Codex lane can bootstrap in a new repository. Worked around, not
repaired.
Area: managed worker launch and Codex project trust.

Every managed worker worktree belongs to a repository root Codex has never
trusted, so Codex opens a blocking trust dialog at startup. `worker start` then
submits the generated bootstrap prompt into that dialog; the keystrokes resolve
the list selection and the runtime exits within seconds, leaving
`submit_recovery.result: "session-not-running"` and no bootstrap.

Confirmed by direct probe: a plain `agent-session start` in the same worktree
reproduces the dialog, and trusting the repository root once makes every
subsequent lane in that repository bootstrap normally. This is the systematic
reason Codex workers "fail before bootstrap", and it recurs for every new
repository.

Acceptance: managed Codex worker launch either establishes repository trust as
part of the launch contract or fails with an explicit
`provider-trust-required` classification instead of a silent startup death.

### B8 — `worker start` persists an assignment before validating its cwd

Severity: costs a launch and blocks retry of the same id. Not repaired.
Area: `main-agent worker start`.

`worker start` writes the durable assignment record, then fails
`cwd-unavailable` when the assignment worktree does not exist. The orphaned
assignment blocks retry of the same id with `assignment-exists`, so recovery
needs a distinct replacement packet through `reassign`. This exactly reproduces
the previous canary's Codex assignments that carried `worker: null`.

Note that `worker start` does not create the managed worktree; it must already
exist, created with `git-cli worktree add`.

Acceptance: the cwd precondition is validated before the durable assignment
record is written, so a failed launch leaves no orphan.

### B2 — A `working` lane whose runtime died cannot be terminalized

Severity: a failed run could never be closed. Repaired in signed nils-cli and
runtime-kit local-main commits, release-installed and surface-deployed.
Implementation closure is achieved; real-product field closure is NOT, because
the one positive canary never reproduced a live claim. Governed provider
delivery remains blocked before mutation.
Area: `crates/agent-session/src/main_agent.rs`.

After a worker dies past bootstrap, its assignment stays `working` with a claim
alive on TTL. `worker cancel` requires a proven pre-claim failure, so it
refuses; `worker reassign` fails at diagnosis. Supervision still reported
`healthy_progress` for one such lane and `startup_dialog_failure` for the other.

The only remaining tool is Agent Console `group-cleanup` with `mode:"force"`,
which deletes the Main session — the session that would have to run it.

This is the direct generalization of the defect repaired in `7b3aba77`, which
only covers `starting` and `blocked`.

The final implementation classifies a bootstrap-complete `working` assignment
whose exact bound runtime is proven stopped as `post_claim_failure`.
Supervision exposes
`last_proven_safe_state.post_claim_terminalization_safe:true`,
`automatic_retry_safe:false`, and
`recovery_action.kind:"stopped_worker_terminalization"` through public
schemas `main-agent.worker-diagnose-result.v2`,
`main-agent.worker-supervise-result.v2`, and
`main-agent.worker-recovery-action.v2`. Main supplies only a bounded reason and
idempotency key to the returned revision-fenced action:

```bash
main-agent worker reconcile-stopped <assignment-id> \
  --if-revision <assignment-revision> \
  --reason <bounded-terminalization-reason> \
  --idempotency-key <unique-key> --format json
```

The `main-agent.worker-reconcile-stopped-result.v2` success proves
`terminalized:true`, top-level `worker_claim_active_after:false`,
`input_sent:false`, `worktree_preserved:true`, and stable observed-state proof:

```text
proof.worker_claim:{
  active_disposition:"absent",
  release_provenance:"not_attributed_to_attempt",
  observed_at_stage1:<bool>
}
```

There is no attempt-dependent `worker_claim_revoked` claim. The action fences
the exact stopped worker session against resume, installs a session-only
authority quarantine, preserves a frozen assignment schema v3, and leaves
unrelated session, run, and coordination authority unchanged. CLI and HTTP
resume are denied while quarantined; read-only observational coordination
access does not renew generic claims or operations. It preserves the
worktree/branch/diff/run/Main session and transitions
`working → reconcile-stopped → cancelled → retire`.

Reconciliation has two exact replay-safe stale-revision cases. The exact same
request, original revision, and idempotency key may return an already committed
v2 terminal receipt without repeating mutation. An exact interrupted-stage-1
replay may continue only with matching strict progress and full revalidation;
stage 2 accepts either the exact original controller claim or an explicit
distinct successor bound to the same current run, Main session, and
incarnation. An authorized retry rolls orphaned stage-1 progress forward
rather than discarding the frozen assignment, weakening quarantine, or
repeating committed effects. A new key, changed request, or replay with
neither receipt fails closed. A distinct replacement remains possible after
the cancelled read-back.

The boundary fails closed for `worker-runtime-still-live`,
`coordination-runtime-unverified`, `worker-not-quiescent`,
`worker-incarnation-changed`, and `assignment-state-conflict`. Expired or
released Main controller authority remains an ordinary claim-authorization
failure. This classification never routes through ordinary cancel/reassign,
raw tmux or terminal input, force group cleanup, or the future B3 stop
primitive.

Regression-first work caught the missing stopped-worker boundary, a null
terminalized-assignment quarantine projection, and an expiry race where the
generic lock path auto-renewed an expired controller claim. Subsequent
red-to-green passes replaced attempt-dependent release attribution with stable
observed-state v2 proof, made quarantine session-only, denied CLI/HTTP resume,
kept observational access from renewing generic authority, admitted the exact
original controller or a same-incarnation successor at stage 2, and rolled
orphaned progress forward.

Final nils-cli candidate validation is green:

- the focused `reconcile-stopped` boundary: 5/5;
- the existing exact B2 scenario: 1/1;
- the typed progress parser: 1/1;
- strict completion freshness: PASS (`required=49`, `snapshots=66`,
  `failures=0`);
- Bash and zsh syntax checks: PASS;
- `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`: exit 0,
  docs/fmt/clippy green, nextest 7,666/7,666 (one unrelated configured retry
  and two known leaky classifications), and 2/2 doctests green.
- current-main direct-main integration: 7,669/7,669 plus 2/2 doctests green;
- canonical review: 2/2 green; full specialist and red-team closeout: green;
- release install and installed binary checksum/version proof: green;
- installed B1 coupled acceptance: green;
- live-runtime negative `reconcile-stopped` canary: fail-closed with revision
  and state unchanged.

The runtime-kit consuming contract first failed its focused deterministic
conversation smoke at 4/5, then passed at 5/5 after the v2 source, protocol,
assertions, and Codex/Claude goldens converged. The first signed runtime-kit
candidate is `8339fcb351b7a4d02df4292561b88b914be840f2`; final signed B2
implementation head `d35f3960338bc4893dc0bb158e88c341cb15a44a`
supersedes its v1 result wording, passes full CI positions 1-17, deterministic
smoke 105 pass plus one host skip, and shared hooks 349/349. This doc-only
status closeout follows that implementation head. Final specialist review
reported no findings.
Rendered surfaces were previewed and then applied successfully from the
durable deploy checkout; doctor, prompt, and plugin checks are green.

#### What the positive canary did and did not prove (2026-07-28)

A positive stopped-runtime canary ran against the installed 1.25.11 binary and
the deployed surfaces. **B2 field closure is not claimed.** Lane
`b2-positive-fixture-20260728`, worker incarnation
`b9c9d33e-6108-44b6-9ee2-6fdc3b9f7898`.

The fixture's clean provider exit made B2's most important branches vacuous:

| Branch | Status |
| --- | --- |
| Terminalize a stopped, quiescent, claim-absent worker | proven in the field |
| Fail closed against a live runtime | proven in the field |
| Terminalize a stopped worker whose claim is **still active on TTL** (`observed_at_stage1:true`) | NOT exercised — the defining B2 case |
| Detect a dead worker whose stop signal is ambiguous (process dead, tmux alive) | NOT exercised — the original B2 misreport |
| Interrupted stage-1 replay rollforward | NOT exercised |
| Stage-2 admission of a distinct successor controller | NOT exercised (`controller_authorization.mode:"original"`, successor == original) |
| Expired-claim non-renewal under the generic lock path | NOT exercisable — no claim was present |
| HTTP resume denial under quarantine | NOT exercised; only the CLI path was |

Two consequences deserve emphasis. First, `worker_claim_active_after:false`
proves nothing here about the action's effect, because the claim was already
absent before stage 1; the v2 contract is deliberately honest about this by
reporting `release_provenance:"not_attributed_to_attempt"`. Second, the
classification flipped to `post_claim_failure` only because the clean exit made
`worker.status` unambiguously `stopped` — the same projection still carried
`progress.provider_active:true` and `activity.phase:"working"`. A hostile stop
that leaves tmux alive would reproduce the original `healthy_progress`
misreport, which is precisely the defect B2 exists to fix.

Closing B2 in the field requires a stopped worker whose assignment-derived
claim is still active on TTL, with `observed_at_stage1:true` and a post-action
read proving the claim gone.

The negative side was re-verified first on the same live lane: exit
`worker-runtime-still-live` with assignment state and revision unchanged.

Supervision after the runtime stopped returned exactly the contracted shape —
`main-agent.worker-supervise-result.v2`, `post_claim_failure`,
`post_claim_terminalization_safe: true`, `automatic_retry_safe: false`,
`recovery_action.kind: "stopped_worker_terminalization"` on
`main-agent.worker-recovery-action.v2`, `required_inputs` exactly
`["terminalization_reason","idempotency_key"]`, worker `status: stopped` with
`identity_matched: true`, and zero active or uncertain operations.

The typed action returned `main-agent.worker-reconcile-stopped-result.v2` with
`terminalized: true`, top-level `worker_claim_active_after: false`,
`input_sent: false`, `worktree_preserved: true`,
`proof.worker_runtime: "stopped"`, `proof.coordination: "quiescent"`,
`proof.lifecycle_boundary: "revalidated-exclusive-record-lock"`, and
`proof.worker_claim: {active_disposition:"absent",
release_provenance:"not_attributed_to_attempt", observed_at_stage1:false}`.
The assignment moved `working -> cancelled` at revision 7.

Safety envelope, with each row's actual evidence strength:

| Property | Strength |
| --- | --- |
| Worktree, branch, and uncommitted diff survived | captured in the run directory |
| Durable run and Main session survived | captured in the run directory |
| Unrelated sessions still running | captured, but this is a liveness observation over n=2 sessions on one machine, not an authority check; their claims and operations were not read before and after |
| Read-only broker observation did not renew a claim | captured, but vacuous: there was no claim present to renew |
| No input sent by the action (`input_sent:false`) | in the result JSON |
| CLI resume denied `worker-quarantined` | observed live during the run; the raw output was NOT captured, and the session has since been deleted, so it is narrative-only in the retained record |
| Quarantine session-only and identity-bound | observed live as a single `authority-quarantine.json` carrying the exact incarnation and runtime identity digest; the file was NOT copied into the run directory and is gone with the deleted session, so it is narrative-only |

The terminalized assignment projects `worker_quarantine: null`. That is not the
previously repaired null-projection defect resurfacing: the quarantine is
deliberately session-scoped, so the assignment record carries null by design
while the session carries the record. Enforcement was confirmed behaviourally
by the denied resume.

Replay safety, two of at least four documented paths:

| Case | Result |
| --- | --- |
| Exact replay: same stale revision, same reason, same idempotency key | returned the committed v2 receipt, revision still 7, no re-mutation |
| Changed request: new idempotency key on the stale revision | failed closed `orchestration-revision-conflict` |
| Interrupted stage-1 replay rollforward | not exercised |
| Stage-2 distinct-successor controller admission | not exercised |

The reconciled worker was then retired, deleted, and proven absent from a fresh
session list.

The fixture method, stated here so the repo record is self-contained: the
provider's own exit command was delivered with `agent-session send` to an idle
worker holding zero admitted operations. **That route is fixture construction
only.** It is untyped provider input — not revision-fenced, not
incarnation-bound, carries no idempotency key, and nothing enforces quiescence
at send time. It must never be used as a recovery action, must never substitute
for the B2 transition it was used to set up, and does not satisfy B3's typed
stop acceptance.

Signed one-commit current-main integration candidates exist for both
repositories, and their exact trees are committed to both local default
branches through governed local-only completion. Their provider-delivery
preflights both stop before mutation on the same GitHub GraphQL HTTP 403. That
workflow did not push; both remote default refs were only later observed
aligned with the local commits through an external update whose provenance is
not established here.

### B3 — An exhausted-readiness live worker has no recovery route

Severity: recovery requires stepping outside the CLI. Not repaired; queued
after B5/B6 field validation and B7-B8 per the Continuation Order.
Area: `main_agent.rs` supervision, `session-coordination-guard.py` allowlist,
`agent-session` command surface.

A worker that launched but never received its prompt is durably recorded as
`submit_recovery.state: "failed"`, yet supervision classifies it
`claim_renewal_required` and prescribes `agent-session work-context renew`.
The exact projected `renew`, `release`, `show`, and `check` lifecycle shapes are
now admitted by the B4 repair, so allowlisting is no longer this blocker's root
cause. Renewal is simply the wrong recovery for terminal prompt-delivery
failure.

The documented `main-agent worker reconcile-recovery` path accepts only an
unknown `attempting` recovery and requires the runtime to already be stopped.
`agent-session` exposes no typed stop-only command: `delete` kills the runtime
and removes session state. A terminal `failed` recovery with a live worker
therefore still requires raw `tmux kill-session`, and even then needs a guarded
classification/cancellation path rather than `reconcile-recovery`.

The 2026-07-28 B2 positive canary showed that an *idle, cooperative* provider
can be stopped through its own clean exit path, delivered by the released
`agent-session send` API, leaving durable state and the incarnation intact.
That is a legitimate fixture route and it removed B2's field-closure blocker,
but it is not a substitute for B3: it needs a provider that is idle and still
responsive to its own exit command. B3's subject is a worker that is live,
non-responsive, and cannot be driven, which is exactly the case that route
cannot reach.

Acceptance: an exhausted-readiness live worker returns an executable,
Main-owned typed stop action needing no raw terminal command. The stop is bound
to the exact incarnation, does not delete durable state, is idempotent and
revision-fenced, and is followed by a non-healthy stopped-runtime
classification plus guarded terminalization. An unknown `attempting` send
continues to use `reconcile-recovery`; a terminal `failed` send never resends
the prompt or injects another Enter.

### B4 — Worker lifecycle commands are treated as repository mutations

Severity: removed the escape hatch. Repaired and deployed with B1 on
2026-07-28.
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

Recorded for the 2026-07-27 B1 delivery session; B2 and B3 were queued at that
time. B2 has since reached implementation closure, but not field closure.
Scope remained B1. The checkpoint part of B4 was
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

The local binaries and runtime surfaces are deployed, and the installed-binary
coupled acceptance covers hook projection through claim/admit/complete. The
C02-C05 closure canary has since run and closed. Full fresh-session Phase C
acceptance is still incomplete: C06, C07, and the residual C08 recovery
classifications remain, per the Continuation Order above.

### Note for whoever picks up B3

A partial fix was prototyped and deliberately reverted this session: adding
`submit_recovery_exhausted` to `worker_failed_preclaim` made the classification
`pre_claim_failure`, but its next action (`cancel`) still fails for a live
worker, so it would have shipped an unexecutable instruction. B3 needs its own
classification plus a typed runtime-stop, not an extension of the pre-claim
fact.

## Repair Log

Entries are dated. "This session" in any older paragraph below refers to the
2026-07-27 B1/B2 delivery session, not the latest entry.

### B5 implementation closure, 2026-07-28

The coordination guard now normalizes a pinned absolute `agent-session`
executable only for the existing finite lifecycle/mailbox shape comparison.
Trust remains bound to the original argv: an absolute form must lexically equal
the exact trusted resolved executable before bypassing admission, so an
arbitrary realpath-equivalent symlink cannot introduce a check/use race.
Regression-first
coverage exercises all 16 projected shapes in bare and trusted-absolute forms
and retains explicit rejection for an absolute same-name shadow, a
realpath-equivalent absolute symlink alias, a symlink-plus-dot-segment alias,
and a relative symlink spelling. Focused coverage is green; the final
shared-hook suite records 349 pass and one host-capability skip across 350
cases.
Deployment and the real-product release/retire canary remain open, so this is
implementation closure only.

### B1/B4 and B2 delivery, 2026-07-27 to 2026-07-28

B1/B4 remain deployed. B2 nils-cli implementation is at signed, clean head
`99ba960e914e58f2813ca1864044aa858759080b`, release-installed, and verified
against the installed binary; its signed current-main integration head is
`c64b52ee92bdd62b2f0c10786bbc6b1f87323561`, and the same tree is on local
`main` at `a3f9b2f3e7412cd47fae78ca95178f87e4f3675f`. The runtime-kit v2
contract's final signed, clean implementation head is
`d35f3960338bc4893dc0bb158e88c341cb15a44a`; this doc-only status closeout
follows it, and the commit containing this inventory is its signed local-main
landing. Its rendered surfaces are deployed from the durable checkout and pass
doctor, prompt, and plugin checks. Both governed provider-delivery preflights
are blocked before mutation by the same GitHub GraphQL 403. Both local default
branches are complete. This workflow did not push; both `origin/main` refs
were later observed aligned with the local commits through an external update
whose provenance is not established here.

| Item | Commit | Defect |
| --- | --- | --- |
| Narrow claims could not run shell work | nils-cli `eb36be24`, runtime-kit `04aba506` | Authenticated bootstrap now mints a private checkout-shell grant; exact checkout-bound opaque shell admission no longer requires repository scope |
| Worker checkpoint/lifecycle escape hatch was blocked | runtime-kit `04aba506` | Exact private revision-fenced checkpoint plus existing projected lifecycle commands bypass repository mutation admission; near misses remain denied |
| Pre-claim startup failure was unrecoverable | nils-cli `7b3aba77` | `provider_terminated` is turn-derived, so a provider exiting during startup left `failed_preclaim` false; `claim_renewal_required` outranked `pre_claim_failure` and both `cancel` and `reassign` refused |
| A dead worker was reported healthy | nils-cli `7b3aba77` | The classifier read `preclaim_blocker`/`terminal_recovery_reconciled` but never the computed pre-claim verdict |
| The pinned bootstrap command was denied | runtime-kit `0ca2819c` | `worker start` writes an absolute `main-agent` path into every worker prompt, but both pre-claim allowlists compared argv against the bare name |
| No Claude worker could pass the readiness gate | runtime-kit `0ca2819c` | The gate required `classification:"supported"`; `agent-session` reports `partial` for Claude permanently |
| A stopped post-claim worker could not be terminalized safely | nils-cli `99ba960e`; runtime-kit `d35f3960` | Exact stopped/quiescent proof now yields `post_claim_failure`; revision-fenced `reconcile-stopped` reports stable claim absence without attempt-dependent release attribution, quarantines only the exact worker session, preserves work/run/Main, and fails closed on live/unknown/non-quiescent or stale identity |

The third item was a cross-repository regression: nils-cli started pinning the
absolute path on 2026-07-25 (`3aa6aca4`) without updating the runtime-kit
allowlist written on 2026-07-22 (`546d7a2c`). Every managed worker launched in
that window had its mandated first command denied. B5 is the surviving sibling
of that same defect on the `agent-session` lifecycle allowlist.

### Canary closeout, 2026-07-28

No production code changed in this closeout; it is a doc-only status landing on
top of the B2 implementation. What it records is real-product execution against
the installed 1.25.11 binary and the already-deployed surfaces:

| Canary | Result |
| --- | --- |
| B1 C02-C05 closure, Claude lane | closed — released at revision 10, absent from a fresh list |
| B1 C02-C05 closure, Codex lane | closed — released at revision 10, absent from a fresh list |
| B2 live-runtime negative reconcile | fail-closed `worker-runtime-still-live`, state and revision unchanged |
| B2 positive stopped-runtime reconcile | passed on a claim-absent stopped worker, with the v2 proof fields and two of at least four replay paths; does NOT establish field closure |

Run `5f959c6d-e71d-4951-bf8e-059a50c1cdc1`, closed at revision 3. Lane commits
in the disposable fixture `graysurf/main-agent-b1-canary`: Claude `eb4f4cec`
and `37f8516d`; Codex `60d5abbd` and `32bce53f`; all signed and all confined to
their declared scopes.

## Remaining Friction

| ID | Problem | Suggested fix |
| --- | --- | --- |
| F22 | A worker between launch and bootstrap is classified `claim_renewal_required`, telling the manager to renew a claim that never existed | Give the pre-bootstrap window its own state |
| F24 | A packet whose `repository` is a path instead of `owner/name` is accepted by `worker start` and only fails at bootstrap, costing a launch, a readiness wait, and a reassign | Validate the identifier inside `worker start` before creating a session |
| F25 | A fresh Claude worker launched with an empty composer; the runtime still reported `submit-key-recovery-succeeded`. Transient — a relaunch delivered normally, and Codex delivered first time | Verify the composer holds the prompt before reporting success; report `prompt-not-present` otherwise |
| F27 | In a checkout with no git remote, repository identity cannot resolve, and every scoped write plus the blocked-checkpoint escape hatch is denied with a generic identity error | Detect a remote-less checkout at claim or bootstrap time and fail with that specific cause |
| F28 | A worker told it had mailbox mail did not know the consumption command and searched the web for it. It also invented `main-agent checkpoint --revision --state --blocker-summary`; the real shape needs `--file <json>`. Still open: the 2026-07-28 closure canary tried to fix this by naming commands in the packet, but the named mailbox shapes were themselves wrong (missing `--session`, positional id for `show`), so a hand-written command list is not a reliable fix | Generate the exact commands from the CLI surface rather than hand-writing them into prompts or notifications |
| F29 | With identical packets, Claude's writes were admitted and Codex's were denied `shell-target-unresolved`, because Claude edits through a file-target tool and Codex writes through shell | Resolved by B1 for in-checkout targets; B6 has implementation closure for the runtime-issued out-of-checkout checkpoint, with deployment and field validation pending |
| F30 | The runtime-generated worker prompt tells the worker to release its claim, while an assignment packet that needs the `request-changes` resume path tells it to hold the claim. A Claude worker correctly surfaced the contradiction as a question and blocked on it; an unattended worker stalls there. This is the likely cause of the earlier `working`/`needs-input` stall | Make the generated prompt defer to the packet, or state the release step as post-acceptance only |
| F31 | A worker returned to `working` by `request-changes` must hold its claim for the resume path, but retirement requires the claim released, and no Main-owned typed action can revoke it. When the worker is quota-exhausted or otherwise unable to act, the accepted lane cannot be retired. Shares B5's symptom but not its cause: B5 is a cooperative worker using the wrong argv form, F31 is a worker that cannot act at all | Give the Main Agent a typed post-acceptance claim-revocation action for its own exact worker |
| F32 | `main-agent checkpoint` rejected a worker packet with `invalid-checkpoint: coordination input is invalid` and named no field, the same discarded-serde-error shape as F13 | Surface the field path in checkpoint validation too |
| F33 | Codex reported "Selected model is at capacity" mid-lane and its turn ended without progress, yet supervision still classified `healthy_progress` | Treat a provider capacity failure as attention-required, per the documented capacity rule |
| F34 | A worker cannot clear a dangling operation lease on its own claim. `work-context complete` requires `--lease` plus `--execution-token-file`, and `work-context reconcile` requires `--lease` plus `--proof-file`; both the lease id and the execution token are minted by the hook layer at implicit admit time and never handed to the worker. The only correct worker behaviour left is to report and wait — the canary's Claude lane did exactly that, and explicitly refused to scavenge capability material out of `coordination/registry.json` to satisfy the guard checking it | Either return the lease id and execution token to the worker that owns the operation, or give the Main Agent a typed action to complete/reconcile a dangling lease on its own worker's claim |
| F13 | `worker start` rejects a packet with `invalid-assignment-packet: coordination input is invalid` and names no field; the serde error is discarded. The skill also names `exclusions` and `invariants`, which are not top-level schema fields | Surface the field path; align the skill with the schema |
| F18 | Read-only `semantic-commit` probes are denied when composed — `cd X && semantic-commit …`, or a trailing `2>&1` parsed as a CLI argument | Classify read-only subcommands and redirections before default-delivery analysis |
| F05 | `agent-session activity doctor` reports `configured:false` while the compatibility probe reports `configured:true` with `compatibility_owner:"agent-hook"` | Reconcile the doctor with agent-hook ownership |
| F20 | The tool shell is zsh, which sources neither `.profile` nor `.bashrc`, so `cargo` is absent; the natural `PATH=…` workaround is blocked by the governed-executable hook | Extend login-shell parity to zsh, or have the block name the sanctioned entrypoint |

## E2E Continuation Scope

Closed on both products: C01 activation, C02 startup, C03 supervision and
claims, C04 authenticated mailbox, C05 request-changes and same-session resume.
C09 acceptance and retirement is closed on both products but only with
hand-supplied release argv; it does not yet pass unattended, pending B5.
C08's recovery boundary is only partly closed: the B2 post-claim path ran on a
single Codex fixture lane and only in its claim-absent form.

Still open:

- C06 dependency wait
- C07 account-next (Codex) and unsupported-account behaviour (Claude)
- C08 for the B2 live-claim case, for dead-worker detection under an ambiguous
  stop, and for the remaining recovery classifications including B3's live
  worker
- C09 unattended, once B5 is deployed and removes the hand-supplied release argv
- Phase D parity beyond the differences recorded as F25, F29, and now F30-F34

C06 and C07 were not reached because both provider accounts hit their usage
ceilings during the closure session, not because of any product defect.

B2 nils-cli is release-installed at the canonical head; checksum/version proof,
the installed B1 coupled acceptance, the live-runtime negative reconcile canary,
and the claim-absent positive stopped-runtime canary are all green, but the
live-claim positive case that would close B2 in the field has not run.
Runtime-kit B2
implementation head `d35f3960338bc4893dc0bb158e88c341cb15a44a` passes full CI
and its rendered surfaces are deployed from the durable checkout. Both prepared
one-commit trees are on their primary local default branches, and the exact
runtime-kit local landing is deployed.

Next: field-validate B5, deliver/deploy/field-validate B6, repair B7-B8, close B2
in the field against a live claim, then B3's typed stop, then C06/C07 and Phase D
as the final parity gate. Before provider delivery, restore governed GitHub access and
revalidate the expected remote bases. The GitHub GraphQL 403 still blocks
governed provider delivery. Both remote default refs were later observed
aligned with the local commits through an external update whose provenance is
not established here; revalidate before any future provider action. A B2 or B3
failure should update this inventory with the exact typed classification and
last proven safe state; it must not be worked around with raw tmux input or
destructive Main-session cleanup.

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
- `main-agent worker start` does not create the managed worktree. Create it
  first with `git-cli worktree add <slug> --from <base> --kind chore`, or the
  launch fails `cwd-unavailable` after already persisting the assignment (B8).
- A Codex lane needs its repository root trusted before launch, or it dies at
  startup with no bootstrap (B7).
- Until the B6 repair is deployed and field-validated, retain the exact legacy
  workaround: the only admitted way for a worker to create its out-of-checkout
  checkpoint file is a simple-argv command carrying the JSON in single quotes,
  for example
  `perl -e 'open(my $fh, ">", $ARGV[0]) or die; print $fh $ARGV[1], "\n"; close $fh or die; chmod 0600, $ARGV[0] or die;' <path> '<json>'`.
- Until the B5 repair is deployed and field-validated, a worker must invoke the
  projected lifecycle shapes as
  the bare name `agent-session`, with the literal quoted `"$AGENT_SESSION_ID"`
  and `"$AGENT_SESSION_CAPABILITY_FILE"`; an absolute path deadlocks the
  release. The exact admitted release invocation is:
  `agent-session work-context release --session "$AGENT_SESSION_ID" --claim <claim-id> --if-revision <n> --capability-file "$AGENT_SESSION_CAPABILITY_FILE" --idempotency-key <key> --format json`
  Supplying only the *description* of this shape is not enough: the canary's
  Claude lane was told the bare name was required and still composed a
  near-miss. Send the complete invocation verbatim.
- The mailbox commands all require `--session`, and `show`/`ack` take
  `--message` rather than a positional id. The closure canary's own assignment
  packets shipped the wrong shapes here, which is the same F28 failure the
  packets were meant to fix. The correct forms are:
  - `agent-session message inbox --session <session-id> --state unread --limit <n> --format json`
  - `agent-session message show --session <session-id> --message <message-id> --format json`
  - `agent-session message ack --session <session-id> --message <message-id> --if-revision <n> --idempotency-key <key> --format json`
  Reading a message advances its revision, so re-read the inbox before `ack`
  or the compare-and-swap fails `message-revision-conflict`.
- The earlier retained run `2dfae16e` is now `closed` in the registry, as is
  the closure-canary run `5f959c6d`. Two `submitted` assignments from
  2026-07-23 remain orphaned in runs `706def5a` and `cf750754`; their worker
  sessions no longer exist and their controllers are gone, so they need typed
  adoption rather than impersonation.
