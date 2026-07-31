# Main Agent Mode Blocker Inventory

Status: B1/B4 are deployed and their real-product C02-C05 closure canary is
closed on both providers, but it needed four manual workarounds, filed as
B5-B8. All four now have implementation closure and are deployed locally.
B5 admits the exact trusted absolute `agent-session` lifecycle and mailbox
shapes. B6 issues and admits one exact session/incarnation-bound private
checkpoint file. B7 validates an exact canonical Codex trust root and pins the
verified Codex configuration through launch and replay. B8 validates and
canonicalizes `launch.cwd` before assignment, receipt, or session side effects.
The exact missing-cwd and untrusted-root negatives plus the repaired same-id
retry and trusted-root startup close B7/B8 in the field. The fresh v5 Codex
lane now also closes B5/B6 in the field without provider input: it wrote an
authenticated `submitted` checkpoint through the ordinary issued-file path and
released its assignment-derived claim through the pinned absolute lifecycle.
The same preserved worker then completed an authenticated `request-changes`
cycle through the new typed F37 re-entry path: it consumed exact private
guidance, re-bootstrapped at the current revision before mutation, changed only
the two scoped files, passed validation, released its claim, resubmitted, and
was accepted and retired. F30 and F37 are therefore also field-closed.

B2 is now fully closed in implementation and the field. Its original
live-claim branch remains proven: an exact revision/incarnation-fenced
`stop-claimed-runtime` action stopped the bootstrap-complete worker without
provider input, preserved the assignment-derived claim on TTL, and
`reconcile-stopped` observed and removed that claim at stage 1. The final
process-dead/tmux-live boundary is also closed by a fresh scope-empty Codex
lane on signed installed nils-cli build
`cbb31799212a35ab8735f190388d9c27e7d6aba2`. Typed provider stop returned
`provider_process:"stopped"`, `tmux_wrapper:"running"`, and
`input_sent:false`; both supervision views classified
`provider_process_stopped_wrapper_live`. Typed release, stopped
reconciliation, retirement, closeout, and both claim releases completed
without worker input or a second worker. Runtime-kit's authenticated typed
bootstrap authorization is signed at
`828beef55bf4413296b9e2beffe838d215e34082`; nils-cli's paired marker and hook
boundary are signed at `d9ec40a0c682852f78ce21cae964250ae50055a8`.
B3's distinct pre-claim typed
exact-incarnation stop remains integrated and deployed at nils-cli local
`main` `452f3ccbe9bd270e5792a8e1c63f6b2fe5ebb731`, and its
exhausted-readiness real-product field case is now closed. Two fresh trusted
Codex starts independently exhausted the bounded checkpoint wait; both
projected `readiness_stop_required`, stopped through the exact typed action
without provider input, cancelled, retired, and disappeared from fresh session
lists. Post-stop supervision explicitly classified the first worker
`pre_claim_failure`. This B3 evidence must not be counted as B2 evidence.

The failed B5/B6 field lane exposed F30 as an independent unattended-lane
blocker. F30 now has implementation, signed local-main integration, and release
installation closure at nils-cli local `main`
`46c00f18927cfcaea63559aa642cede18c668844`: orchestration owns claim
lifecycle, workers release after successful task checkpoints, and a
request-changes worker re-bootstraps for the current revision before mutating.
Historical persisted-start replay remains compatible with the immediately
prior generated prompt. The preserved v5 unattended lane has now completed the
entire cycle after F37 and closes F30 in the field.

F25 and F36 now have regression-backed implementation, signed governed
local-main integration, release installation, and real-product field closure
at nils-cli commit
`82ca3422eb7eca0dd38437a821726d77244a9ef9`. F25 holds a definitive
submit-key recovery failure pending until authenticated bootstrap,
authoritative turn end, or the original deadline, and reconciles the final
receipt under the registry lock. F36 validates, descriptor-pins, and safely
tightens only the owned state root, `session-locks`, and `sessions` ancestors
to `0700`; unsafe symlinks, ownership, type, or replacement fail with typed
causes without recursively mutating session contents.

The one fresh v5 Codex lane exercised both repairs together. Its submit-key
recovery reported failure, but authenticated bootstrap arrived inside the
original deadline and `worker start --await-ready` returned `ready` with the
durable recovery state `checkpoint_confirmed`. The root, both lifecycle
ancestors, session leaf, and coordination directory were `0700`, and the
issued checkpoint was `0600`. The worker changed only its two scoped fixture
files, passed its test, wrote an authenticated `submitted` checkpoint through
the ordinary supported path, and released the claim. This closes F25, F36,
B5, and B6 in the field.

The same lane exposed F37 after authenticated `request-changes`: the
assignment moved to revision 6 `working` and one private review message was
queued, but the provider turn had authoritatively ended, worker auto-resume was
unsupported, and the guidance initially remained unread. A bounded typed wait
timed out without current-revision re-bootstrap or mutation.

F37 now has regression-backed implementation, signed governed local-main
integration, installed-binary deployment, specialist-review closure, and
real-product field closure. Signed nils-cli local `main`
`6b244f701b4d390e0f6e1c7893f5a91ea5b0b2a2` adds manager-only `worker
reenter` with exact assignment revision, worker incarnation, unread
notification generation, authoritative idle-turn, detached composer,
live-runtime, broker, no-claim, and no-active-or-uncertain-operation fences.
The action creates no message generation, resends no assignment prompt, and
durably seals crash replay. The signed compatibility follow-up is integrated
to nils-cli local `main` at
`1a3315df04ba74109a43322b9e315bc728f46151`; it may reconstruct the missing
pre-upgrade request-changes companion identity only from one retained receipt
whose authenticated controller, run, revision, worker, manager, guidance,
idempotency binding, and recomputed request digest all match. Every missing,
corrupt, foreign, stale, or ambiguous form fails closed.

The first real re-entry attempt safely returned
`worker-reentry-state-conflict` because the preserved revision-6 transition
predated the companion identity; it sent no provider input and left the lane
unchanged. After the compatibility install, replay of the same logical
re-entry and idempotency key queued notification generation 1 exactly once.
The same worker consumed guidance, authenticated current-revision bootstrap,
acquired its own claim, moved to revision 7 `working`, changed only the two
scoped files to the requested `field-f30-reviewed` behavior, passed
`bash tests/field-f30.sh`, released the claim, and wrote revision 8
`submitted`. Independent Main Agent review confirmed the exact two-file diff,
passing validation, `guidance.state:"consumed"`, `claim_active:false`, and zero
active or uncertain operations. The assignment was accepted at revision 9,
typed retirement returned `released:true`, `deleted:true`,
`cleanup_pending:false`, the run closed at revision 2, and the controller claim
was separately released. No prompt resend, provider input, raw terminal
transport, or second worker was used.

F31 now has implementation, signed local-main integration, release
installation, and real-product field closure at nils-cli local `main`
`7857fe76c992bad6c4ec0a6f6154362f6e5c1e31`. The typed
`main-agent worker revoke-claim` action accepted only the exact revision- and
incarnation-fenced, authoritative-idle live worker with an active
assignment-derived claim and no active or uncertain operations. It sent no
provider input, changed the assignment from `working` to `cancelled`, removed
only that claim and broker authority, quarantined resume authority, and
preserved the durable session plus the dirty worktree with the same status
digest. A fresh post-action read proved the claim absent; the other preserved
worker's claim remained active. This closes F31, not B2: the F31 worker
remained live, while B2 requires an independently stopped worker whose claim
is still active on TTL before terminalization.

F38 and F39 were repaired after the closed v5 cycle while preparing B2's final
field boundary. F38 now selects one exact active run and current worker
incarnation before continuity mutations, serializes rebind, init, admission,
claim renewal, and rollback under typed authority locks, and preserves exact
receipt replay across historical records. Its focused regression suite,
clippy, formatting, specialist review, and red-team follow-up are green. The
signed governed local-main integration is nils-cli
`02ac792bb10c0b4d921141869831ec3223f08988`; combined F38/F39
`agent-session` and `main-agent` binaries are installed from that tree.

F39 closes the repeated Stop-hook self-deadlock without weakening ordinary
admission. Only an activity-capability failure on terminal `Stop` degrades to
typed `activity-stop-reconciliation-required`; prompt and tool events remain
fail-closed, and coordination transaction authority remains independent. The
repair is signed and integrated on nils-cli local `main`
`949b92c188ca8b74f70d1259eb8825ec1b1ce3c2`; the installed `agent-hook`
reports `v1.25.9-93-g4a282e1f`, and Codex plus Claude doctors are converged.
No repeated unchanged Stop fingerprint has recurred in the repaired session.

The historical governed local-main authorization was exercised for B2; it is
not standing authority for another delivery. Any later delivery needs a new
explicit user selection and must retain compare-and-swap, hooks, signing, and
outside-repository receipts. Step 3 and B2 are field-closed. The next
authoritative incomplete items are C06/C07, the remaining C08 recovery
classifications, and Phase D parity.
Date: 2026-07-27
Updated: 2026-08-01
Source: Phase C of `2026-07-27-main-agent-fresh-session-e2e-plan.md`

## Post-landing closeout, 2026-08-01

B2 remains closed. Its reviewed trees are now represented on the two local
default branches by signed squash landing commits:

- agent-runtime-kit `8b27d215c766dd13f39db67f8b0f3db5854f103b`
  (`fix(main-agent): close B2 field boundary`), whose complete positions 1-17
  gate passed on the landed tree;
- nils-cli `7d0b63192eb856ec99f23eb0bacbaae005bc472e`
  (`fix(agent-session): close B2 recovery boundary`), whose landing validation
  passed formatting, clippy, and all 7,873 functional tests, but whose first
  enclosing local-fast run remained red because the final private-`TMPDIR`
  probe found one late `.tmp.../state` directory.

Both outside-repository `semantic-commit default-branch` receipts report a
verified-good signature, `provider_delivery_attempted:false`, and
`provider_delivered:false`. They also record the historical local completion
boundary: cached upstream was aligned before each commit and ahead by one
afterward, with no network observation or provider mutation. Fresh cached and
live reads on 2026-08-01 instead found each `origin/main` at its corresponding
landing head (`0 behind / 0 ahead`). That later alignment was not performed by
this closeout and does not retroactively convert either local-only receipt into
provider-delivery evidence.

The nils residue did not reproduce in 20 focused runs of
`group_cleanup_success_replay_finishes_all_daemon_registry_evictions`, one
complete 1,107-test `nils-agent-session` probe, or three complete 7,873-test
workspace probes. Every probe finished with an empty private `TMPDIR` except
for the explicitly allowed bounded `git-cli-test-worker.<euid>` cache. The
narrowest proven boundary is therefore an intermittent full-suite test
teardown/concurrency race; there is no evidence of a B2 product-lifecycle
regression and no established cause that justifies a speculative code change.
The final landed-diff rerun forced the canonical local-fast gate with
`--base HEAD^`; formatting, clippy, 7,873/7,873 tests, two doctests, and its
final tempdir probe all passed. This later green result bounds but does not
erase the first run's unexplained residue.

The installed field identities remain distinct and authoritative for what was
actually exercised: nils-cli `cbb31799` for the final provider-stop field
build, nils-cli `d9ec40a0` for the paired bootstrap marker/hook boundary, and
runtime-kit `828beef5` for authenticated typed bootstrap authorization. The
squash landing heads do not replace those field-build identities.

## Purpose

Phase C found that Main Agent Mode could not complete a lane. This document is
the ordered repair queue plus the E2E scope that remains to be rerun.

B1 is in local `main` in both repositories, the rebuilt nils-cli binaries and
runtime surfaces are deployed, and the installed-binary coupled acceptance is
green. The separate B1 real-product C02-C05 closure canary has now closed on
both providers. Reaching that closure required working around four distinct
root causes by hand, filed below as blockers B5-B8. B5-B8 now have signed
local-main implementation closure and are deployed. B5-B8 field validation is
closed. None of them was a defect in the B1 scope/admission design itself.
Both lanes bootstrapped, ran
checkout-bound shell validation under a narrow claim, created signed commits,
checkpointed `submitted`, took one revision-fenced `request-changes` plus a
private mailbox message, resumed in the same session without widening the
claim, resubmitted, and were accepted, released, deleted, and proven absent
from a fresh session list.

The following paragraphs retain the historical B2 implementation lineage; the
current default-branch identities are the 2026-08-01 squash landing heads
recorded above. B2's repair purpose was first achieved in candidate source: a
bootstrap-complete
worker whose exact runtime stopped can be terminalized without deleting the
Main session, losing its worktree/diff, sending input, or revoking unrelated
coordination authority. The final signed, clean nils-cli candidate head is
`99ba960e914e58f2813ca1864044aa858759080b`; its local-fast gate completed
7,666 tests plus two doctests, and the release binary is installed. Its signed
historical one-commit current-main integration head was
`c64b52ee92bdd62b2f0c10786bbc6b1f87323561`; the final integration gate
completed 7,669 tests plus two doctests, and the same tree is committed on
local nils-cli `main` at `a3f9b2f3e7412cd47fae78ca95178f87e4f3675f`.
The historical final signed, clean runtime-kit B2 topic implementation head is
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

The 2026-07-28 positive stopped-runtime canary passed, but it did **not**
establish B2 live-claim field closure. The later 2026-07-29 typed-stop canary
does close that defining branch; the paragraphs immediately below retain the
earlier run's narrower evidence and explain why it did not count.

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

B3's implementation, local-main integration, release installation, and
runtime deployment gaps are closed. The new Main-owned command
stops a still-live pre-claim/readiness-failure runtime without raw terminal
control while preserving its durable session state. Real-product B3 field
validation is closed on 2026-07-29 by two independent fresh Codex workers that
exhausted the checkpoint wait and completed typed stop, guarded cancellation,
and typed retirement without provider input. The cooperative provider-exit fixture remains
insufficient for both B3 and B2's live-claim branch:
B3's own scenario is an exhausted-readiness worker that cannot be driven, while
B2 requires a stopped post-claim worker whose claim remains alive on TTL.
F-items normally record friction rather than blocker closure, but F30 proved an
independent unattended-lane blocker and F31 prevented safe retirement of the
preserved worker until its typed field closure on 2026-07-29; their promotion
in the Continuation Order is intentional.

Raw per-scenario evidence, rerun selectors, and receipts stay outside the
repository beside the run:

- `$AGENT_HOME/out/e2e-20260727/e2e-result-and-improvements.md` — Phase A/B
- `$AGENT_HOME/out/e2e-20260727/phase-c-result-and-improvements.md` — Phase C/D
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260728-083244-b1-closure-b2-positive-canary/result-and-improvements.md`
  — the closed B1 C02-C05 canary and the passing B2 positive canary
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260728-193740-b5-b8-field-canary/result-and-improvements.md`
  — B7/B8 field closure, the failed B5/B6 unattended attempt, the authorized
  manual-recovery boundary, and the preserved F31-stuck lane
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260729-040232-f31-field-closure-f30/`
  — F31 pre-action supervision, typed revocation result, and post-action read
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260729-040002-f31-local-main-delivery/default-branch-receipt.json`
  — signed governed nils-cli local-main delivery receipt
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260729-042606-b2-postclaim-stop-action/`
  — regression evidence, signed candidate receipt, specialist review, exact
  typed-stop result, live-claim reconcile result, and post-action supervision
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260729-095000-b5-b6-f30-field-v2/`
  — two fresh B5/B6 launch attempts blocked before bootstrap, plus the complete
  B3 typed stop/cancel/retire evidence and fresh-list absence
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260729-115832-codex-readiness-prompt-truth/`
  — regression-first typed prompt/composer repair, focused validation,
  specialist-review disposition, signed local-main receipt, and the unrelated
  full-gate baseline failure
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260729-124736-b5-b6-f30-field-v4/`
  — exact prompt/composer launch truth, the authenticated late bootstrap,
  F36 checkpoint-admission failure, typed claim revocation and retirement,
  closed run, released controller claim, and fresh-list absence
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260729-132453-f25-f36-readiness-state-ancestors/`
  — F25/F36 regression-first evidence, focused and repository validation,
  specialist-review disposition, signed delivery receipt, and install result
- `$AGENT_HOME/out/projects/graysurf__agent-runtime-kit/20260729-150532-b5-b6-f30-field-v5/`
  — the single fresh unattended Codex lane: repaired readiness and ancestor
  proof, authenticated checkpoints, pinned absolute releases, request-changes
  transition, F37 typed re-entry, current-revision re-bootstrap, bounded
  revision, resubmission, acceptance, retirement, closed run, and released
  controller claim
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260729-f37-request-changes-reentry-review/`
  — F37 regressions, focused/full validation, specialist-review disposition,
  governed delivery receipts, and the compatibility follow-up receipt
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260730-131419-f39-stop-activity-failure/`
  — F39 regressions, installed-product Stop-versus-PreToolUse proof,
  specialist-review disposition, and signed delivery receipt
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260730-160200-f38-active-run-selection-final/`
  — F38 focused validation, specialist-review disposition, installed versions,
  doctors, and signed candidate receipt
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260730-163500-f38-local-main-integration/`
  — governed signed local-main integration receipt for combined F38/F39 source
- `$AGENT_HOME/out/projects/sympoies__nils-cli/20260731-202402-b2-provider-stop-field-success-cbb31799/`
  — signed installed-build B2 process-dead/tmux-live field proof, bounded
  lifecycle JSON, typed closeout, and retained evidence summary

## Continuation Order

1. **Keep delivery governed.** The two B2 receipts remain local-only and report
   no provider delivery. On 2026-08-01 both cached and live upstream refs were
   externally aligned with the squash landing heads, but that observation is
   not this workflow's delivery evidence and grants no new delivery authority.
   Prepare later changes in a managed non-default worktree unless the user
   explicitly selects a current delivery mode; never weaken hooks or leases.
2. **Keep B3's completed typed-stop repair deployed and field-closed, but keep
   its evidence separate from B2.** Candidate commit
   `453b52c982d6160fcc93dce1b674e470bb612094` adds the typed,
   exact-incarnation `main-agent worker stop-runtime` primitive for an
   exhausted-readiness runtime without deleting durable session state. It
   revision-fences and idempotently seals the exact runtime stop, denies
   conflicting resume/claim/bootstrap paths, and supports guarded successor
   replay after controller loss. The existing pre-claim cancellation path
   remains the terminalization route after stopped proof, and
   `reconcile-recovery` remains the route for an unknown `attempting` send.
   It is integrated at signed nils-cli local-main commit
   `452f3ccbe9bd270e5792a8e1c63f6b2fe5ebb731`, release-installed, and
   deployed. On 2026-07-29 two fresh, trusted Codex workers independently
   exhausted the bounded checkpoint wait while live and claim-absent.
   Supervision returned executable `readiness_stop_required` with exact
   incarnation and revision 3. Both typed stops returned
   `runtime_stopped:true`, `input_sent:false`,
   `session_state_preserved:true`, and `worktree_preserved:true`; post-stop
   proof classified `pre_claim_failure`, guarded cancellation succeeded, typed
   retirement deleted each session, and fresh lists proved both absent. B3
   implementation, deployment, and real-product field closure are complete.
   It does not authorize raw terminal control, and this pre-claim evidence
   must not be counted as B2 terminalization proof.
3. **Keep the completed v5 F25/F36/B5/B6/F30/F37 cycle closed; do not launch a
   second worker for this step.**
   B7/B8 field closure is complete. The v4 lane proved exact prompt presence
   and composer transition, then isolated F25's late-bootstrap terminal-verdict
   race and F36's inherited-`0775` ancestor defect. Both repairs are now
   regression-backed, signed at nils-cli local-main `82ca3422`, installed, and
   field-closed. The one distinct v5 Codex start observed submit-key recovery
   failure but returned `ready` after the same worker authenticated inside the
   original deadline. Its state root, `session-locks`, `sessions`, leaf, and
   coordination directory were `0700`; the issued checkpoint was `0600`.

   The authenticated v5 worker changed only `src/field-f30.sh` and
   `tests/field-f30.sh`, passed `bash tests/field-f30.sh`, checkpointed
   `submitted` through the ordinary issued-file path, and released its claim
   through the pinned absolute lifecycle. F25, F36, B5, and B6 therefore have
   implementation, deployment, and real-product field closure.

   Authenticated `request-changes` moved the same assignment to revision 6
   `working`, and one private review message was sent exactly once. The
   provider turn was already authoritatively terminated, worker auto-resume was
   unsupported, and the guidance initially remained `queued_unread`.
   Regression-backed F37 adds a typed exact-worker re-entry transition with
   revision/incarnation, notification-generation, idle-composer, quiescence,
   one-send, and crash-replay fences. Its narrow compatibility path recovers
   only from one exact authenticated retained request-changes receipt.

   After installation, the same preserved worker consumed its guidance without
   provider input, authenticated current-revision re-bootstrap, acquired its
   new claim, changed only the two scoped files, passed validation, released
   the claim, and wrote revision 8 `submitted`. Independent review confirmed
   the final `field-f30-reviewed` behavior, exactly two changes,
   `guidance.state:"consumed"`, `claim_active:false`, and no active or uncertain
   operations. It was accepted, typed-retired with cleanup pending zero, and
   absent from the fresh session list; the run closed and the controller claim
   was separately released. F25, F36, B5, B6, F30, and F37 all have
   implementation, installed deployment, and real-product field closure.
   Exactly one v5 worker was used.
4. **Keep F31's typed exact-worker claim revocation deployed and closed.**
   Signed nils-cli local-main commit
   `7857fe76c992bad6c4ec0a6f6154362f6e5c1e31` adds the revision-fenced,
   incarnation-bound, idempotent Main-owned action. Its 2026-07-29
   real-product run started from an authoritative-idle live worker whose
   assignment-derived claim was active and operations were quiescent. The
   action removed only that claim, quarantined exact-session resume authority,
   preserved the durable session and unchanged dirty worktree, and sent no
   provider input. A fresh read proved `claim_active:false`, while the other
   live worker retained its claim. F31 implementation and field closure are
   complete; this evidence must not be counted as B2 because the worker stayed
   live.
5. **Keep B2 fully closed and retain the signed final field evidence.** The
   defining live-claim reconciliation branch closed first. On 2026-07-29 the
   typed, exact
   revision/incarnation-fenced `stop-claimed-runtime` action stopped worker
   incarnation `a87597f0-fa6d-4de8-888d-1db883ddb1bf` at assignment revision
   4 without provider input and returned `worker_claim_active_after:true`.
   `reconcile-stopped` then returned
   `proof.worker_claim.observed_at_stage1:true`,
   `worker_claim_active_after:false`, and revision 5 `cancelled`; a fresh
   supervision read reported the exact worker `stopped` and
   `claim_active:false`. No session deletion occurred before evidence capture.
   F38 and F39 are regression-backed, reviewed, integrated, and installed
   prerequisites: active continuity selection is exact, and an activity child
   failure on terminal Stop no longer creates an infinite provider-hook loop.

   The remaining process-dead/tmux-live classifier closed on 2026-07-31.
   Signed nils-cli `d9ec40a0` and runtime-kit `828beef5` authorize only the
   exact typed worker bootstrap marker, removing dependence on a long
   terminal-composer prompt. Signed nils-cli `cbb31799` then corrected the
   provider cgroup lifecycle: exact members are stopped first, all pinned
   children are reaped, and only then is the cgroup removed. Its complete
   local-fast gate passed 7,865/7,865 tests plus 2/2 doctests.

   The final fresh scope-empty Codex worker authenticated through the typed
   bootstrap marker and reached authoritative idle with an active claim, zero
   active or uncertain operations, and a clean worktree. Typed
   `stop-provider-canary` returned provider stopped / wrapper running /
   `input_sent:false`; `worker supervise` and `worker diagnose` both returned
   `provider_process_stopped_wrapper_live`. Typed release then stopped the
   wrapper, and stopped reconciliation, retirement, and `main-agent closeout`
   proved the worker absent, cleanup pending zero, run closed, and controller
   claim released. No worker input, second worker, raw tmux control, arbitrary
   process signal, transcript inspection, runtime-state rewrite, force
   cleanup, or pre-evidence session deletion was used.
6. **Run C06, C07, and the remaining Phase D parity items.** C02-C05 are closed
   on both providers. C09 is closed on both with hand-supplied release argv,
   and the v5 Codex lane now also closes its full unattended path through
   F37/F30. C08's B2 recovery boundary is closed in claim-absent,
   claim-active-at-stage-1, and process-dead/tmux-live forms. Other recovery
   classifications remain.
   C06 dependency wait and C07 account-next / unsupported-account behaviour
   were not reached because both provider accounts hit their usage ceilings
   during the closure session.
7. **Then take the remaining friction wave.** F25 prompt-presence truth and
   late-bootstrap reconciliation are closed in step 3; B3's typed recovery is
   field-closed. Address F22 and F33
   together while touching the supervision and
   pre-bootstrap classifier. F30 and F37 are field-closed in step 3. F31
   remains recorded at step 4
   as closed field evidence. Take F34 as the
   remaining operation-ownership work; B5's source repair does not close it.
   Take F32 with F13, since both are the same discarded-serde-error shape.
   Follow with F24/F28/F27 input and guidance clarity; F28 in particular is not
   closed, because the closure canary's own packets shipped wrong mailbox argv.
   Keep F18/F05/F20 as the later ambient-tooling wave.

B2 established the missing distinction between post-claim failure and
pre-claim failure. Its reconcile implementation, independently stopped
live-claim branch, authenticated bootstrap boundary, and
process-dead/tmux-live classification are all field-closed. The signed final
nils-cli build is `cbb31799`; the paired runtime-kit bootstrap authorization
is `828beef5`. B5-B8 are repaired, deployed, and
field-closed. B3 is implemented, integrated, deployed, and field-closed. F25
and F36 are implemented, integrated, installed, and field-closed. F30 and F37
are implemented, integrated, installed, specialist-reviewed, and field-closed
by the same v5 worker. F31 is implemented, integrated, installed, and
field-closed. F38 and F39 are implemented, reviewed, integrated, and installed;
F39's installed-product Stop failure contract is field-proven. C06/C07,
remaining C08 recovery classifications, and Phase D are next.
The completed B3 candidate reuses B2's exact-runtime and quiescence proof
helpers, then enters the existing pre-claim cancellation path after the typed
stop rather than the B2 post-claim transition. It deliberately does not
classify a live exhausted worker as `pre_claim_failure`, because `worker
cancel` rejects a live worker.

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
separate obstacles were worked around by hand. B5-B8 are now implemented,
signed on local `main`, release-installed or surface-deployed as applicable,
and deterministically validated. None is a defect in B1's scope projection or
admission rule; all four are in the surrounding worker lifecycle, and each is
filed as its own blocker below. B5-B8 real-product field validation is now
closed. F30's complete unattended request-changes cycle remains separate.

### B5 — A worker cannot release its own claim unless it uses the bare name

Severity: an accepted lane could never be retired. Implementation repaired and
deployed on 2026-07-28; the pinned absolute release boundary is field-closed by
the unattended v5 Codex lane on 2026-07-29.
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

The v5 lane supplies the separate field proof. Its authenticated initial
checkpoint reached `submitted`; the worker then executed the runtime-generated
pinned absolute `agent-session work-context release ...` lifecycle without a
bare-name workaround or provider input. Typed supervision observed the
assignment-derived claim absent with no active or uncertain operation. This
closes B5's real-product release boundary. Final post-request-changes release
and retirement remain part of F30's still-open end-to-end cycle.

B5 covers only a *cooperative* worker that is able to run a command but is
using the wrong argv form. It does not cover a worker that cannot act at all —
quota-exhausted, wedged, or unresponsive — which still leaves an accepted lane
unretirable before the Main-owned F31 action can revoke that claim. That
residual case was closed separately on 2026-07-29; landing B5 did not resolve
it.

### B6 — The mandated out-of-checkout checkpoint file is nearly unwritable

Severity: a worker could not report `submitted` or `blocked` without the manual
argv workaround. Implementation repaired, signed on both local default
branches, release-installed, surface-deployed, and field-closed by the
unattended v5 Codex lane on 2026-07-29.
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

The paired local-main deliveries are nils-cli
`3106e9598195fdba77772804aeeed59854651aa6` and runtime-kit
`63861ecaed56c0ccbaf4a8dc7b96ec30a34a2427`. The rebuilt runtime first exposed
`v1.25.9-79-g3106e959`; the later B7/B8 rebuild contains the same B6 tree and
advances the installed binaries to `v1.25.9-80-g391d3d4b`. Synced
Codex/Claude/Hermes surfaces pass skill-surface and installed-runtime doctor,
hook convergence, plugin registry, and Codex prompt-input verification.

The v5 Codex worker supplies the missing real-product proof. With the repaired
F36 ancestors at `0700`, its ordinary supported write populated the exact
mode-`0600` issued checkpoint file with an authenticated `submitted` packet;
the packet records the two scoped files and passing
`bash tests/field-f30.sh`. No `perl` workaround or provider input was used.
B6 implementation, deployment, and field closure are complete. F30's later
request-changes/re-bootstrap cycle is independently field-closed by the same
v5 worker after the F37 repair.

### B7 — A Codex worker dies at startup in an untrusted repository root

Severity: no Codex lane could bootstrap in a new repository. Implementation
repaired, signed on nils-cli local `main`, release-installed, and field-closed
on 2026-07-28.
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

Implementation closure is fail-closed rather than implicit trust mutation.
Fresh launch canonicalizes the exact cwd and the active Codex configuration
root before durable assignment or session side effects, then requires an exact
`trust_level = "trusted"` project entry. Parent-only trust is insufficient.
Missing trust returns `provider-trust-required`; malformed, oversized, symlink,
FIFO, or otherwise unverifiable configuration returns
`provider-trust-unverified`. The verified canonical configuration directory is
persisted in the pending receipt and session runtime, inherited by the actual
Codex child, and retained through replay even if the caller's `CODEX_HOME`
symlink is retargeted.

### B8 — `worker start` persists an assignment before validating its cwd

Severity: cost a launch and blocked retry of the same id. Implementation
repaired, signed on nils-cli local `main`, release-installed, and field-closed
on 2026-07-28.
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

Implementation closure canonicalizes and validates an existing directory
before assignment, pending-receipt, or session mutation. Symlinked checkouts
launch from their canonical target. A missing or invalid root fails
`assignment-launch-cwd-unavailable` and remains resumable in batch mode; exact
parent replay launches only repaired lanes. The same change adds a durable
controller-bound worker-start operation fence from final authority validation
through worker attachment, so claim release or replacement cannot create an
unowned child in the remaining check/create/attach window. Crash replay adopts
the same deterministic child and fence instead of duplicating launch.

B7/B8 share nils-cli local-main commit
`391d3d4bd69f54010304e4a7ef0907a409a0ce85`. The exact candidate tree passed
the complete 201-case agent-session integration suite, all focused worker-start
and trust/fence regressions, clippy with warnings denied, and the full
workspace local-fast gate: 7,684/7,684 tests plus all doctests. Security,
API-contract, performance, maintainability, testing, and adversarial review
closed with no findings. The signed local-main tree matches the reviewed
managed candidate exactly; its outside-repository receipt records
`provider_delivered:false`. That deployment installed `main-agent` and
`agent-session` at `v1.25.9-80-g391d3d4b`; later B3 and F30 repairs advanced
the installed binaries without changing the B7/B8 tree.

Field closure used distinct negative and positive observations. A missing cwd
returned `assignment-launch-cwd-unavailable`, was retryable, and left no
assignment or session; after `git-cli worktree add`, the same assignment id
started successfully. The exact new Codex root first returned
`provider-trust-required` with no worker/session side effects. After the user
authorized only that canonical root and its exact trusted entry was installed,
the same assignment id and idempotency key started successfully without a
trust dialog. These observations close B7/B8 only; they do not imply B5/B6
field closure.

### B2 — A `working` lane whose runtime died cannot be terminalized

Severity: a failed run could never be closed. Repaired in signed nils-cli and
runtime-kit commits, release-installed and surface-deployed. Original
reconcile implementation closure and the defining real-product live-claim
branch closed before the final process-dead/tmux-live classifier field case.
Full B2 field closure is claimed on 2026-07-31 against signed installed
nils-cli build `cbb31799212a35ab8735f190388d9c27e7d6aba2` and runtime-kit
bootstrap authorization `828beef55bf4413296b9e2beffe838d215e34082`.
No provider delivery is claimed in this closeout.
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
candidate is `8339fcb351b7a4d02df4292561b88b914be840f2`; the historical final signed B2
topic head `d35f3960338bc4893dc0bb158e88c341cb15a44a`
supersedes its v1 result wording, passes full CI positions 1-17, deterministic
smoke 105 pass plus one host skip, and shared hooks 349/349. This doc-only
status closeout followed that topic head. Final specialist review
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

Closing B2's defining live-claim branch requires a stopped worker whose
assignment-derived claim is still active on TTL, with
`observed_at_stage1:true` and a post-action read proving the claim gone. Full
field closure additionally requires a non-`healthy_progress` classification
for the process-dead/tmux-live ambiguous-stop case.

#### Defining live-claim branch closed (2026-07-29)

The new Main-owned command

```bash
main-agent worker stop-claimed-runtime <assignment-id> \
  --worker-incarnation <exact-incarnation> \
  --if-revision <assignment-revision> \
  --idempotency-key <unique-key> --format json
```

is a stop-only action for the post-claim case. It fences assignment revision,
worker incarnation, controller authority, active assignment-derived claim,
claim TTL, authoritative-idle activity, exact runtime identity, broker
authority, work context, and operation quiescence. It persists replay-safe
claim-mutation state before stopping the exact runtime, sends no provider
input, does not delete the durable session, and deliberately preserves the
same worker claim for `reconcile-stopped`. Original-controller and guarded
same-incarnation successor replay are covered in integration tests.

Regression-first work caught controller-TTL reservation, successor adoption
and partial-replay conflicts, and a pre-claim marker-first compatibility
regression before the final production tree. The final combined-tree gate
passed documentation, format, clippy, and 7,733/7,733 tests. Focused claimed
stop coverage passed 15/15, the CLI contract passed 4/4, and projection tests
passed 2/2. API-contract, security, performance, data-migration, testing, and
red-team reviews closed cleanly. Two low maintainability notes remain: the
principal acceptance test is broad, and the transaction function still
contains a large implicit state machine.

The signed nils-cli candidate is
`94719ffc00af5a6b81574c07df672120c60687e3`. Installed
`main-agent` and `agent-session` report
`v1.25.9-85-g2f440ecc`. The candidate tree is integrated at signed nils-cli
local-main commit `2f440ecc392bbcf376ada245f2c73818a9fe742d`; its
outside-repository receipt records verified-good signing and no provider
delivery. No hook, signing, lease, or delivery guard was bypassed.

The live field sequence used assignment
`b5-b8-field-codex-20260728`, exact worker incarnation
`a87597f0-fa6d-4de8-888d-1db883ddb1bf`, and revision 4. Pre-action supervision
proved the worker authoritative-idle, runtime running, broker authoritative,
operations zero, and claim
`87822363-ebbd-4a8e-b4af-0e4327644a62` active on TTL. The typed stop returned
`runtime_stopped:true`, `worker_claim_active_after:true`, and
`input_sent:false`, with the assignment still revision 4 `working`.

The first reconcile admission failed closed after the new coordination schema
made the still-running older broker non-authoritative. The authorized typed
`main-agent self recover` adopted the unchanged Main runtime with the same
session incarnation, retained its active controller claim, sent no prompt or
input, and restored authoritative broker proof. Retrying the identical
reconcile request and idempotency key then returned:

```text
terminalized:true
assignment: revision 5, state:"cancelled"
worker_claim_active_after:false
input_sent:false
worktree_preserved:true
proof.worker_runtime:"stopped"
proof.worker_claim:{
  active_disposition:"absent",
  release_provenance:"not_attributed_to_attempt",
  observed_at_stage1:true
}
```

A separate post-action `worker supervise` read proved the same worker
`status:"stopped"` and coordination `claim_active:false`, with the dirty
worktree still preserved. Raw stop, reconcile, and post-action JSON were
written to the run directory before any session deletion. This closes the
defining B2 live-claim field branch without raw tmux input, arbitrary kill,
provider exit input, session deletion, force cleanup, or prior-controller
impersonation.

#### Process-dead/tmux-live boundary closed (2026-07-31)

The remaining classifier boundary was exercised through the reviewed typed
provider-stop canary, not through raw tmux control, arbitrary process
termination, provider exit input, session deletion, or runtime-state
rewriting. Nils-cli `d9ec40a0` and runtime-kit `828beef5` supply an
authenticated, session/incarnation-bound typed bootstrap authorization marker.
This keeps the initial visible prompt compact while making bootstrap admission
independent of terminal line wrapping or composer timing.

The first final field attempts safely exposed a post-stop cgroup cleanup
failure. Bounded private runtime evidence reduced it to
`provider-stop-canary-cgroup-remove-busy`. Signed nils-cli
`cbb31799212a35ab8735f190388d9c27e7d6aba2` fixes the lifecycle ordering:
stop exact pinned members, wait and reap every provider child, then remove the
exact cgroup. The regression and original scope-empty supervisor integration
are green; the complete local-fast gate passed 7,865/7,865 tests and 2/2
doctests.

The final fresh run
`a341c6a3-cedf-4fd3-9cc2-924db921408b`, assignment
`7c5a9e65-d6eb-48e1-a956-1e3adbd1dda1`, used exactly one scope-empty Codex
worker. It reached `working` readiness with
`proof:"authenticated-worker-checkpoint"`, then authoritative waiting with an
active exact claim, zero active or uncertain operations, and a clean
worktree. Typed stop returned:

```text
provider_process:"stopped"
tmux_wrapper:"running"
input_sent:false
```

Both `worker supervise` and `worker diagnose` returned
`provider_process_stopped_wrapper_live`. Typed release returned provider and
wrapper stopped with `input_sent:false`. Typed stopped reconciliation and
retirement removed the worker, and `main-agent closeout` proved the run
closed, workers absent, cleanup pending zero, controller claim absent and
inactive, provider session preserved, and handoff ready. The retained evidence
is under
`$AGENT_HOME/out/projects/sympoies__nils-cli/20260731-202402-b2-provider-stop-field-success-cbb31799/`.
The controller and worker test sessions were deleted only after typed closeout
and evidence verification. This satisfies the inventory's two-part B2 field
rule and closes B2.

#### Historical claim-absent canary evidence (2026-07-28)

The following results belong to the earlier cooperative-exit fixture and must
not be read as contradictory evidence for the 2026-07-29 live-claim run above.

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

Severity: recovery previously required stepping outside the CLI.
Candidate-source implementation closure is complete at signed nils-cli commit
`453b52c982d6160fcc93dce1b674e470bb612094`. Local-main integration,
release installation, and runtime deployment are complete at signed local-main
commit `452f3ccbe9bd270e5792a8e1c63f6b2fe5ebb731`; real-product field closure is
complete on 2026-07-29. The later F25/F36 repair and v5 lane close B5/B6
without altering this B3 evidence.
Area: `main_agent.rs` supervision, `session-coordination-guard.py` allowlist,
`agent-session` command surface.

A worker that launched but never received its prompt is durably recorded as
`submit_recovery.state: "failed"`, yet supervision classifies it
`claim_renewal_required` and prescribes `agent-session work-context renew`.
The exact projected `renew`, `release`, `show`, and `check` lifecycle shapes are
now admitted by the B4 repair, so allowlisting is no longer this blocker's root
cause. Renewal is simply the wrong recovery for terminal prompt-delivery
failure.

Before the candidate repair, the documented
`main-agent worker reconcile-recovery` path accepted only an unknown
`attempting` recovery and required the runtime to already be stopped.
`agent-session` exposed no typed stop-only command: `delete` killed the runtime
and removed session state. A terminal `failed` recovery with a live worker
therefore required raw `tmux kill-session`, and even then needed a guarded
classification/cancellation path rather than `reconcile-recovery`.

The 2026-07-28 B2 positive canary showed that an *idle, cooperative* provider
can be stopped through its own clean exit path, delivered by the released
`agent-session send` API, leaving durable state and the incarnation intact.
That is a legitimate claim-absent stopped-runtime fixture route, but it did not
remove or satisfy B2's live-claim field-closure requirement and is not a
substitute for B3: it needs a provider that is idle and still responsive to its
own exit command. B3's subject is a worker that is live, non-responsive, and
cannot be driven, which is exactly the case that route cannot reach.

Acceptance: an exhausted-readiness live worker returns an executable,
Main-owned typed stop action needing no raw terminal command. The stop is bound
to the exact incarnation, does not delete durable state, is idempotent and
revision-fenced, and is followed by a non-healthy stopped-runtime
classification plus guarded terminalization. An unknown `attempting` send
continues to use `reconcile-recovery`; a terminal `failed` send never resends
the prompt or injects another Enter.

Candidate result: `main-agent worker stop-runtime ASSIGNMENT
--worker-incarnation ... --if-revision ... --idempotency-key ...` now implements
that contract for an exhausted-readiness pre-claim worker. It requires the
durable `worker-checkpoint-timeout` proof, an exact live runtime, and no worker
claim, operation, submit recovery still `attempting` or `sent`, or account
handoff. It persists a session-owned runtime-stop fence before reserving the
assignment, blocks conflicting CLI/HTTP/maintenance resume plus
broker/claim/bootstrap/checkpoint paths, and stops the exact runtime without
provider input or durable-session deletion. Exact replay survives a crash after
the authority seal or process stop; a live successor Main can adopt the
immutable replay identity only after the prior controller becomes unavailable,
including repeated successor loss.
The v2 diagnose/supervise response shapes remain unchanged; v3 adds
`readiness_stop_required`, `readiness_stop_in_progress`, and the
account-handoff discriminator.

Regression evidence was captured before production edits as an unknown-command
failure. The final focused runtime-stop integration suite passed 10/10, v2/v3
contract and relevant unit coverage passed, and
`bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast` passed with 940
tests plus the documentation checks. API-contract, testing, security,
maintainability, and red-team specialist reviews all reported no findings after
the repair rounds.

#### Real-product field closure (2026-07-29)

Two fresh assignments on the exact user-authorized trusted Codex root
independently exhausted `worker start --await-ready 5m`. Each result preserved
a live, exact-incarnation worker in `starting`, reported
`delivery.state:"unverified"`, `proof:"worker-checkpoint-timeout"`,
runtime-owned submit-key recovery exhausted once, and
`automatic_retry_safe:false`. Neither worker acquired a claim, changed the
clean worktree, or produced quota/capacity evidence.

For both workers, v3 supervision returned
`classification:"readiness_stop_required"` and an executable
`exact_worker_runtime_stop` argv bound to assignment revision 3 and the exact
worker incarnation. Executing that argv returned:

```text
runtime_stopped:true
input_sent:false
session_state_preserved:true
worktree_preserved:true
proof.readiness:"worker-checkpoint-timeout"
proof.worker_runtime:"stopped"
proof.worker_claim_active_before:false
proof.operation_quiescent:true
```

Post-stop supervision on the first worker returned
`classification:"pre_claim_failure"`, `worker.status:"stopped"`,
`failed_preclaim:true`, and `cancel_then_reassign_safe:true`. The guarded
revision-3 cancel moved each assignment to revision 4 `cancelled` with claim
absent and operations quiescent. Typed retire then returned `retired:true`,
`deleted:true`, and `cleanup_pending:false`; a fresh session-list read proved
both worker sessions absent and the shared worktree remained clean. No prompt
was resent, no manual Enter or provider input was sent, and no raw tmux,
signal, direct session deletion, or force cleanup was used.

This satisfies B3's exact acceptance and closes its real-product field case.
The command is intentionally pre-claim, so this evidence cannot satisfy B2's
required `proof.worker_claim.observed_at_stage1:true` post-claim evidence.
The repeated launch timeout prevented either assignment from exercising B5,
B6, or F30 and is recorded separately under F25/readiness.

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

### Historical B3 design constraint

A partial fix was prototyped and deliberately reverted this session: adding
`submit_recovery_exhausted` to `worker_failed_preclaim` made the classification
`pre_claim_failure`, but its next action (`cancel`) still fails for a live
worker, so it would have shipped an unexecutable instruction. This rejection
is why the completed B3 candidate introduces dedicated readiness-stop
classifications plus the typed runtime-stop rather than extending the
pre-claim fact.

## Repair Log

Entries are dated. "This session" in any older paragraph below refers to the
2026-07-27 B1/B2 delivery session, not the latest entry.

### F25/F36 repair and v5 unattended field boundary, 2026-07-29

Signed nils-cli candidate `d74733072a1d0122f40eeaff3e94e4659af24282`
and governed local-main commit
`82ca3422eb7eca0dd38437a821726d77244a9ef9` repair F25 and F36.
F25 retains a definitive submit-key recovery failure as pending until the
same worker produces an authenticated checkpoint, its turn authoritatively
ends, or the original readiness deadline expires. Final receipt
reconciliation runs under the registry lock, so a late authenticated
checkpoint inside that deadline wins without a contradictory terminal return.
F36 safely hardens only the owned state root, `session-locks`, and `sessions`
ancestors to `0700`, then pins retained descriptors for session creation and
initial writes. Symlinked, foreign-owned, non-directory, unavailable, or
replaced ancestors fail early with typed causes; existing session contents are
not recursively mutated.

Focused F25 and F36 suites each passed 24 cases. All-target/all-feature clippy
with warnings denied, formatting, diff checks, and strict agent-docs passed.
The full repository gate was invoked once and stopped on the clean-baseline
publish-order failure that places `nils-claude-cli` before `nils-scrub`.
The later local-fast invocation exposed one repair-owned duplicated
`coordination/coordination` adapter path; that defect was corrected and its
two exact notification regressions, broker-recovery regression, and complete
24-case start suite passed. The full gate was not replayed. Security,
performance, API-contract, testing, maintainability, and adversarial
specialist review closed with no remaining findings.

The rebuilt installed binaries report
`1.25.11 (v1.25.9-87-g82ca3422)`. Installed Codex, Claude, and Hermes doctors
passed 84, 85, and 72 checks respectively; Codex/Claude hook doctors
converged.

Exactly one fresh unattended Codex lane then proved both repairs. Although
submit-key recovery failed, the authenticated bootstrap arrived inside the
original deadline and `worker start --await-ready` returned `ready`, with
durable recovery state `checkpoint_confirmed`. The state root,
`session-locks`, `sessions`, session leaf, and coordination directory were
`0700`; the checkpoint was `0600`. The worker changed exactly its two scoped
files, passed its focused test, checkpointed `submitted` through the ordinary
path, and released its claim through the pinned absolute lifecycle. This
closes F25, F36, B5, and B6 in the field.

After revision-fenced `request-changes`, the same assignment reached revision
6 `working` and one authenticated private guidance message was queued. Its
provider turn had authoritatively ended, worker auto-resume was unsupported,
and the message initially remained unread. A bounded typed wait timed out
without re-bootstrap or mutation, isolating F37. After the typed F37 re-entry
and compatibility repair were installed, the preserved worker consumed that
exact guidance, re-bootstrapped at revision 6 before mutation, acquired a new
claim, completed only the bounded two-file revision, passed validation,
released, resubmitted, was accepted, and retired. F30 and F37 field closure is
claimed from that later evidence, not from the initial timeout.

### Typed readiness truth and F36 field obstruction, 2026-07-29

The regression-backed nils-cli repair at signed local-main commit
`47671bfd5f50a3e3f617588904634d88dccbdbe0` distinguishes exact prompt
presence, composer transition, observation unavailability, bootstrap failure,
and checkpoint timeout on terminal readiness paths. Focused worker-start and
classifier coverage, security cases for the private prompt file, bounded
observation tests, formatting, and clippy are green. The final specialist
review reported no remaining actionable findings. The repository's full gate
was invoked once and stopped on the pre-existing clean-main failure
`publish-order places nils-claude-cli (#22) before dependency nils-scrub
(#32)`; the same selector fails on the clean baseline and the repair touches
only agent-session source, tests, and documentation. The installed
`main-agent`, `agent-session`, and `agent-hook` report
`1.25.11 (v1.25.9-86-g47671bfd)`.

The single fresh v4 Codex lane returned terminal
`readiness_recovery_failed`, but its typed observation proved the exact
generated prompt was present in the bound provider transcript and the composer
changed after paste. No prompt was resent and no provider input was supplied.
Typed supervision then observed the same worker at authenticated `working`
with an active assignment claim and advancing worktree progress. This is a
late-bootstrap verdict race: prompt delivery and bootstrap both succeeded
after the start command had already declared a terminal readiness failure.

The worker created only `src/field-f30.sh` and `tests/field-f30.sh`; its
assigned shell test passed. Both supported checkpoint writes were denied
because `$AGENT_SESSION_STATE_DIR` and its `sessions` ancestor were owner-owned
but mode `0775`. The issued checkpoint and leaf session/coordination
directories satisfied their `0600`/`0700` contracts. Nils-cli's session
creation uses `create_dir_all` for the two ancestors and applies `0700` only to
the leaf, so a `0002` caller umask produces the incompatible ancestor mode.
This new source boundary is F36.

Because no authenticated `submitted` checkpoint existed, the worker correctly
did not release its claim and F30 request-changes was not reached. After the
authoritative turn ended, typed supervision returned
`idle_claim_revocation_required`. The projected exact-worker action revoked
only that claim with `input_sent:false`, preserved the session and dirty
worktree, and cancelled the assignment. Typed retirement deleted the worker
with no pending cleanup; fresh list evidence proved it absent. Run
`87eca616-329d-4882-8be8-d542756213ba` closed at revision 2 and its controller
claim was separately released. This is a valid unattended field result, but
it is a blocked result, not B5/B6/F30 closure.

### B3 field closure and repeated B5/B6 readiness obstruction, 2026-07-29

Two distinct fresh assignments used an explicitly authorized trusted Codex
root and a clean worktree. Both live workers exhausted the five-minute
checkpoint wait before bootstrap with unverified delivery, no claim, no
worktree changes, no quota/capacity evidence, and runtime-owned submit-key
recovery already exhausted. No provider recovery input was supplied.

Each supervision projected the executable exact-incarnation, revision-3
`stop-runtime` action. Both typed stops preserved session state and the
worktree, sent no provider input, and proved stopped runtime plus quiescent
claim-absent coordination. Guarded cancel and typed retire succeeded; fresh
session-list reads proved both workers absent and the worktree clean. The
first post-stop supervision explicitly returned `pre_claim_failure` with the
worker stopped. This closes B3 implementation, deployment, and real-product
field acceptance.

Neither attempt reached bootstrap or a task checkpoint, so neither exercised
B5's pinned absolute lifecycle release, B6's ordinary checkpoint write, or
F30's orchestration-owned claim lifecycle. The identical outcome across fresh
sessions is a repeatable readiness obstruction. It is routed to F25
prompt/composer-presence investigation without claiming prompt absence as the
root cause; a third blind launch is not warranted.

### B2 defining live-claim branch closure, 2026-07-29

Signed nils-cli candidate `94719ffc` adds the revision/incarnation-fenced
post-claim `stop-claimed-runtime` action. It stops only the exact
authoritative-idle, quiescent worker runtime, sends no provider input, retains
the durable session and dirty worktree, and preserves the still-active claim
for B2 reconciliation. Regression-first focused coverage and the final
7,733-test combined-tree gate are green. The candidate initially remained on
its managed branch because nils-cli local `main` was already one governed
commit ahead of `origin/main`; after external alignment restored the allowed
delivery state, its identical tree landed at signed local-main commit
`2f440ecc392bbcf376ada245f2c73818a9fe742d` and the installed binaries were
rebuilt from that commit. No delivery guard was bypassed.

The field action left the assignment revision 4 `working` and its exact claim
active on TTL. After typed same-incarnation Main self-recovery restored broker
authority, `reconcile-stopped` returned revision 5 `cancelled`,
`proof.worker_claim.observed_at_stage1:true`,
`worker_claim_active_after:false`, `input_sent:false`, and
`worktree_preserved:true`. A fresh supervision read independently proved
worker `stopped` and claim absent. This closes the defining B2 live-claim
branch. The separately required process-dead/tmux-live classifier canary later
closed on 2026-07-31 as recorded in the B2 section above.

### B7/B8 field closure and B5/B6 non-closure, 2026-07-28

The exact B8 missing cwd failed
`assignment-launch-cwd-unavailable` before assignment/session side effects and
the same assignment id started after the managed worktree was created. The
exact B7 untrusted Codex root failed `provider-trust-required` before launch;
after the user authorized only that canonical worktree and its exact trust
entry was installed, the same assignment id and idempotency key started
successfully. B7/B8 field closure is complete.

The resulting worker changed its two declared fixture paths but emitted no
task checkpoint. Two later turns were initiated only under explicit
Main-session recovery authority, consumed bounded authenticated guidance, and
still emitted no checkpoint. Because the lane required provider input, it
cannot be unattended evidence; because it never checkpointed, it exercised
neither B6's natural write nor B5's pinned absolute release. B5/B6 field
closure remained unclaimed at this point; v5 closes it later. The worker,
claim, session, and worktree remain
preserved in the retained 2026-07-28 evidence. F31 later supplied and
field-validated the safe typed Main-owned revocation action on a distinct
preserved lane.

### F30 implementation and deployment closure, 2026-07-28

The failed field lane confirmed that free-form assignment text cannot safely
own claim lifecycle. Nils-cli local `main`
`46c00f18927cfcaea63559aa642cede18c668844` now keeps that authority in the
runtime-generated orchestration prompt: after each successful `submitted` or
`blocked` task checkpoint the worker releases its claim; after authenticated
Main `request-changes`, the worker re-runs exact absolute
`main-agent bootstrap` with a new stable current-revision idempotency key
before mutating.

Regression-first coverage captured the old contradictory prompt. The final
end-to-end regression proves initial release, request-changes reacquisition,
typed checkout-mismatch and claim-conflict failures that preserve the working
assignment without granting a claim, successful re-bootstrap, submitted
checkpoint, and final release. Historical persisted-start replay accepts
exactly the current prompt or the immediately prior known prompt. The focused
tests, 941/941 local-fast package tests, doctests, and testing,
maintainability, and security specialist reviews are green. The signed
candidate and signed governed local-main commit have the same tree; the
outside-repository receipt records no provider delivery. Rebuilt
`main-agent` and `agent-session` report `v1.25.9-82-g46c00f18`.

This implementation, integration, and deployment closure is now joined by
real-product field closure. The fresh v5 lane reached authenticated
request-changes, then the installed F37 typed re-entry woke that same exact
worker without provider input. Current-revision re-bootstrap preceded the
bounded mutation, resubmission, release, acceptance, and typed retirement. The
manually recovered prior lane remains historical evidence and is not
reclassified after the fact.

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
The repaired surface is on runtime-kit local `main` and deployed. The
real-product release/retire canary remains open, so field closure is not
claimed.

### B6 delivery and deployment closure, 2026-07-28

The paired checkpoint contract is now on local `main`: nils-cli `3106e959`
issues the exact private per-incarnation file and runtime-kit `63861eca`
admits only that reconstructed file through the bounded natural write shapes.
Both commits are signed and have outside-repository receipts. The nils binary
was rebuilt, all three runtime products were resynced from the durable
runtime-kit checkout, and their doctor/plugin/prompt gates passed. This closes
implementation and deployment only. No real-product worker has yet submitted
through ordinary `Write` or canonical `printf` without the legacy `perl`
workaround, so B6 field closure remains unclaimed.

### B7/B8 implementation and deployment closure, 2026-07-28

Nils-cli local `main` `391d3d4b` validates canonical launch cwd and exact Codex
project trust before durable side effects, pins the verified configuration
root through child launch and replay, and fences controller authority through
durable worker attachment. Its signed managed candidate and signed local-main
commit have the same tree. Focused regressions, the 201-case agent-session
integration suite, clippy with warnings denied, 7,684/7,684 workspace tests,
all doctests, and the selected specialist review set are green. Rebuilt
`main-agent` and `agent-session` report `v1.25.9-80-g391d3d4b`; runtime surface
sync and all post-install checks are green.

The first activation probe against the already-running Main Codex session
correctly failed `runtime-checkpoint-unavailable`, proving that a pre-B6
incarnation cannot cross the new readiness gate. A graceful `/quit` sent while
that same provider turn was active did not stop it before the bounded wait, so
the following `resume` was a live-session no-op and readiness remained false.
At the safe turn boundary the old session then stopped, and the recovered fresh
Codex session `20260728-161027-codex` passed
`main-agent self readiness`: `ready:true`, a new session incarnation, and an
absolute runtime-issued checkpoint file. This closes the B6 restart-readiness
probe only. It is not a B7/B8 worker field canary. B7 field closure requires a
trusted exact root to bootstrap without a trust dialog plus an untrusted exact
root returning `provider-trust-required` before durable launch side effects.
B8 field closure required a missing cwd to return
`assignment-launch-cwd-unavailable`, pre/post reads proving the assignment and
session absent, and a successful same-id retry after creating the managed
worktree. Those distinct B7/B8 cases later ran and are recorded in the newer
field-closure entry above; both are now closed.

### B1/B4 and B2 delivery, 2026-07-27 to 2026-07-28

B1/B4 remain deployed. At this historical delivery point, B2 nils-cli
implementation was at signed, clean head
`99ba960e914e58f2813ca1864044aa858759080b`, release-installed, and verified
against the installed binary; its signed current-main integration head was
`c64b52ee92bdd62b2f0c10786bbc6b1f87323561`, and the same tree was on local
`main` at `a3f9b2f3e7412cd47fae78ca95178f87e4f3675f`. The runtime-kit v2
contract's historical final signed, clean topic head is
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
| B2 post-claim stop plus live-claim reconcile (2026-07-29) | defining branch closed — typed exact-runtime stop retained the active TTL claim; reconcile observed it at stage 1, removed it, and a fresh read proved claim absent |
| B2 process-dead/tmux-live classifier (2026-07-31) | full B2 closure — signed installed build `cbb31799` returned provider stopped / wrapper running / no input, both supervision views classified `provider_process_stopped_wrapper_live`, and typed release through closeout completed |
| B3 exhausted-readiness typed stop (2026-07-29) | closed twice — both live exact-incarnation workers stopped without provider input, cancelled, retired, and were proven absent; the first post-stop supervision explicitly classified `pre_claim_failure` |
| B5/B6 unattended retries (2026-07-29) | closed by v5 — repaired readiness returned `ready`, repaired ancestors were `0700`, the ordinary issued-file checkpoint reached authenticated `submitted`, and the pinned absolute lifecycle left the claim absent without provider input |
| F30 request-changes cycle (2026-07-29) | closed — after typed F37 re-entry, the same v5 worker consumed exact guidance, re-bootstrapped at revision 6 before mutation, acquired and released its own claim, changed only two scoped files, passed validation, resubmitted, was accepted, retired, and proven absent without provider input |

Run `5f959c6d-e71d-4951-bf8e-059a50c1cdc1`, closed at revision 3. Lane commits
in the disposable fixture `graysurf/main-agent-b1-canary`: Claude `eb4f4cec`
and `37f8516d`; Codex `60d5abbd` and `32bce53f`; all signed and all confined to
their declared scopes.

## Remaining Friction

| ID | Problem | Suggested fix |
| --- | --- | --- |
| F22 | A worker between launch and bootstrap is classified `claim_renewal_required`, telling the manager to renew a claim that never existed | Give the pre-bootstrap window its own state |
| F24 | A packet whose `repository` is a path instead of `owner/name` is accepted by `worker start` and only fails at bootstrap, costing a launch, a readiness wait, and a reassign | Validate the identifier inside `worker start` before creating a session |
| F25 | Closed in implementation, deployment, and the field at nils-cli `82ca3422`. The v5 submit-key recovery failed, but the same worker authenticated inside the original deadline; `worker start` returned `ready` and durable recovery became `checkpoint_confirmed` rather than returning a contradictory terminal verdict | Keep the pending-verdict reconciliation and exact prompt/composer truth covered; do not regress to prompt-absence inference |
| F27 | In a checkout with no git remote, repository identity cannot resolve, and every scoped write plus the blocked-checkpoint escape hatch is denied with a generic identity error | Detect a remote-less checkout at claim or bootstrap time and fail with that specific cause |
| F28 | A worker told it had mailbox mail did not know the consumption command and searched the web for it. It also invented `main-agent checkpoint --revision --state --blocker-summary`; the real shape needs `--file <json>`. Still open: the 2026-07-28 closure canary tried to fix this by naming commands in the packet, but the named mailbox shapes were themselves wrong (missing `--session`, positional id for `show`), so a hand-written command list is not a reliable fix | Generate the exact commands from the CLI surface rather than hand-writing them into prompts or notifications |
| F29 | With identical packets, Claude's writes were admitted and Codex's were denied `shell-target-unresolved`, because Claude edits through a file-target tool and Codex writes through shell | Resolved by B1 for in-checkout targets; B6's runtime-issued out-of-checkout checkpoint is implemented, deployed, and field-closed by the v5 Codex ordinary write |
| F30 | Closed in implementation, deployment, and the field. V5 proved the initial authenticated checkpoint and release, then after F37 consumed guidance, re-bootstrapped at the current revision before mutation, reacquired and released its claim, made only the bounded revision, resubmitted, was accepted, retired, and proven absent | Keep the generated current-revision bootstrap and pinned absolute release lifecycle covered; do not substitute provider input or legacy argv |
| F31 | Closed in implementation and the field at nils-cli local `main` `7857fe76`. A typed v4 supervision action revoked only the exact authoritative-idle live worker's assignment-derived claim under revision, incarnation, runtime, activity, broker, and quiescence fences. The action sent no provider input, preserved the durable session and unchanged dirty worktree, quarantined resume, and left another worker's claim active | Keep the installed primitive deployed; do not count its live-worker evidence as B2 stopped-worker field closure |
| F32 | `main-agent checkpoint` rejected a worker packet with `invalid-checkpoint: coordination input is invalid` and named no field, the same discarded-serde-error shape as F13 | Surface the field path in checkpoint validation too |
| F33 | Codex reported "Selected model is at capacity" mid-lane and its turn ended without progress, yet supervision still classified `healthy_progress` | Treat a provider capacity failure as attention-required, per the documented capacity rule |
| F34 | A worker cannot clear a dangling operation lease on its own claim. `work-context complete` requires `--lease` plus `--execution-token-file`, and `work-context reconcile` requires `--lease` plus `--proof-file`; both the lease id and the execution token are minted by the hook layer at implicit admit time and never handed to the worker. The only correct worker behaviour left is to report and wait — the canary's Claude lane did exactly that, and explicitly refused to scavenge capability material out of `coordination/registry.json` to satisfy the guard checking it | Either return the lease id and execution token to the worker that owns the operation, or give the Main Agent a typed action to complete/reconcile a dangling lease on its own worker's claim |
| F35 | Closed in implementation and local deployment at nils-cli local `main` `9ebbc922` / installed `main-agent 1.25.11 (v1.25.9-94-g9ebbc922)`. The capability-gated, revision-fenced, idempotent `main-agent closeout` owns checkpoint, terminal-worker retirement, cleanup-pending resume, operation fencing, run close, exact bound-claim disposition, and final read-back while preserving the Main provider session. Runtime-kit adopts the macro-first contract in this local-main change; no public release or provider PR is claimed | Keep complete/partial exact-replay, cleanup-tombstone, active-operation, unrelated-successor, pre-provenance, and provider-session-preservation coverage green; retain a multi-worker real-product closeout as optional residual field evidence |
| F36 | Closed in implementation, deployment, and the field at nils-cli `82ca3422`. Session start validates, safely tightens, and descriptor-pins only the owned state root, `session-locks`, and `sessions` ancestors; unsafe ownership, type, symlink, unavailability, or replacement fails typed. V5 proved all ancestors `0700` and an ordinary authenticated checkpoint write | Keep the no-follow, ownership, replacement, and non-recursive mutation regressions; retain platform coverage for the descriptor-backed path |
| F37 | Closed in implementation, deployment, specialist review, and the field at nils-cli local `main` `1a3315df`. Typed `worker reenter` fences the exact revision, incarnation, notification generation, authoritative idle composer, live detached runtime, broker, claim, and operations; it creates no message or assignment prompt. A narrow receipt-bound pre-upgrade backfill fails closed on missing, corrupt, foreign, stale, or ambiguous evidence. The same v5 worker consumed guidance and re-bootstrapped before mutation without provider input | Keep exact-generation one-send, crash replay, app-server/terminal quiescence, and retained-receipt compatibility regressions; never generalize the backfill into mutable assignment-schema authority |
| F38 | Closed in implementation, specialist review, governed local-main integration, and installed deployment at nils-cli `02ac792b`. Exact active-run/current-worker selection and authority-locked rebind, init, admission, renewal, replay, and rollback remove historical-shadowing and split-transaction races | Keep the 18 focused continuity and ambiguous-stop regressions, exact receipt binding, expiry fencing, and direct-claim serialization green |
| F39 | Closed in implementation, governed local-main integration, installed deployment, and installed-product field contract at nils-cli `949b92c1` / installed `agent-hook` `4a282e1f`. Activity failure on terminal Stop degrades to one typed warning while nonterminal admission remains fail-closed and coordination remains authoritative | Retain one natural end-to-end provider-runner termination as optional residual evidence; never recreate it by corrupting a live session or disabling hooks |
| F13 | `worker start` rejects a packet with `invalid-assignment-packet: coordination input is invalid` and names no field; the serde error is discarded. The skill also names `exclusions` and `invariants`, which are not top-level schema fields | Surface the field path; align the skill with the schema |
| F18 | Read-only `semantic-commit` probes are denied when composed — `cd X && semantic-commit …`, or a trailing `2>&1` parsed as a CLI argument | Classify read-only subcommands and redirections before default-delivery analysis |
| F05 | `agent-session activity doctor` reports `configured:false` while the compatibility probe reports `configured:true` with `compatibility_owner:"agent-hook"` | Reconcile the doctor with agent-hook ownership |
| F20 | The tool shell is zsh, which sources neither `.profile` nor `.bashrc`, so `cargo` is absent; the natural `PATH=…` workaround is blocked by the governed-executable hook | Extend login-shell parity to zsh, or have the block name the sanctioned entrypoint |

## E2E Continuation Scope

Closed on both products: C01 activation, C02 startup, C03 supervision and
claims, C04 authenticated mailbox, C05 request-changes and same-session resume.
C09 acceptance and retirement is closed on both products with hand-supplied
release argv, and the v5 Codex lane now also closes the full unattended path.
B5's pinned absolute release boundary is field-closed in v5.
C08's B2 recovery boundary is closed in claim-absent,
claim-active-at-stage-1, and process-dead/tmux-live forms. Other recovery
classes remain.

Current execution matrix:

| Area | Status | Remaining acceptance | Execution boundary |
| --- | --- | --- | --- |
| C06 dependency wait | field-open; the dependency gate has deterministic integration coverage | Prove an intentional dependency wait, authenticated dependency delivery, and same-session continuation on both products | Previously provider-capacity blocked; do not launch a canary merely to probe capacity |
| C07 account behavior | field-open | Codex: typed account-next binding and same-worker continuation without logout. Claude: clear unsupported behavior without damaging recovery | Requires explicit account/provider authority and available capacity |
| residual C08 recovery | partly closed | Exercise the residual classifications enumerated below without reusing B2/B3 evidence | Local deterministic coverage may proceed; provider restart/resume canaries require explicit authority |
| Phase D parity | open | Repeat applicable A/B/C behavior on native Claude and disposition the remaining F-items | Prefer non-provider source/test work while provider capacity is unknown |

Residual C08 is now explicit. Closed and not to be rerun: B2 claim-absent
stopped terminalization, B2 active-claim-at-stage-1 terminalization, B2's
canary-authorized provider-process-stopped/tmux-wrapper-live release, B3's
exhausted-readiness pre-claim stop, and F31's authoritative-idle live-worker
claim revocation. Still requiring acceptance evidence:

- stale/lost controller broker recovery through exact-controller `self
  recover`, distinct from provider-session rebinding;
- provider-session or controller-incarnation mismatch through graceful
  stop/resume, revision-fenced `rebind`, and post-rebind ownership proof;
- generic `process_runtime_stopped_wrapper_live_contradiction` without canary
  authority, which must remain non-executable until identity evidence is
  reconciled;
- active or uncertain operation ownership (`uncertain_mutation`), including
  the F34 capability handoff needed to complete or reconcile the exact lease;
- missing, corrupt, or identity-mismatched worker evidence
  (`worker_unreachable` / `evidence_unavailable`) without inferring safe
  reassignment; and
- the pre-bootstrap/safe-reassignment boundary after F22 is corrected, without
  prompt replay or a second concurrent writer.

Phase D / F29-F34 disposition:

| Item | Status | Next action |
| --- | --- | --- |
| F29 | closed by B1/B6 | Retain cross-product file-write and issued-checkpoint coverage |
| F30 | field-closed with F37 | No rerun unless the generated re-bootstrap/release contract changes |
| F31 | field-closed | Keep its live-worker evidence separate from B2 stopped-worker evidence |
| F32 | open | Pair with F13 and surface the rejected field path instead of discarding serde detail |
| F33 | open | Pair with F22 so provider capacity and pre-bootstrap states become typed attention-required states rather than `healthy_progress` / `claim_renewal_required` |
| F34 | open | Give the exact operation owner a typed completion/reconciliation capability without registry scavenging |

After F22/F33, take F34, then F32/F13, then the F24/F28/F27 input and
guidance wave. F29-F31 and F37 are closed and must not be reopened by that
sequence.

C06 and C07 were not reached because both provider accounts hit their usage
ceilings during the closure session, not because of any product defect.

B2 reconcile and the final provider-stop classifier are release-installed;
checksum/version proof, the installed B1 coupled acceptance, the live-runtime
negative reconcile, both claim-absent and claim-active stopped-runtime
canaries, and the signed process-dead/tmux-live canary are green. The signed
post-claim stop-only repair is on nils-cli local `main` `2f440ecc`; the final
field build is signed at `cbb31799`, with paired runtime-kit authorization at
`828beef5`. B2 is fully closed under this inventory.
Historical runtime-kit B2 topic head
`d35f3960338bc4893dc0bb158e88c341cb15a44a` passed full CI and its rendered
surfaces were deployed from the durable checkout. The current squash landing
heads are runtime-kit `8b27d215c766dd13f39db67f8b0f3db5854f103b`
and nils-cli `7d0b63192eb856ec99f23eb0bacbaae005bc472e`; their local-only
receipts remain distinct from both the externally aligned upstream refs and
the retained installed field builds.

Next authoritative field order remains C06, C07, residual C08, then Phase D.
Until provider capacity and canary authority are affirmatively available, the
next executable non-provider item is the paired F22/F33 classifier repair with
regression-first coverage; it does not require reopening B2.
F25, F36, B5, B6, F30, and F37 are repaired, installed, and field-closed by
the single v5 lane; it
completed current-revision re-bootstrap, bounded mutation, resubmission,
release, acceptance, retirement, fresh-list absence, run close, and controller
claim release without provider input or a second worker. F31 and B3 are
field-closed; B7/B8 and B2 field closure are complete. Phase D remains the
final parity gate. Before provider delivery, restore governed GitHub access and
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
  first with `git-cli worktree add <slug> --from <base> --kind chore`. The
  repaired launch now fails `assignment-launch-cwd-unavailable` before
  persisting an assignment when the directory is missing (B8).
- A Codex lane still requires explicit trust for its exact canonical repository
  root. The repaired launch never mutates trust: absent trust fails
  `provider-trust-required`, and unverifiable configuration fails
  `provider-trust-unverified`, both before durable launch side effects (B7).
- Do not use the legacy B6 `perl` workaround during field validation; an
  ordinary `Write` or canonical `printf` must succeed against the
  runtime-issued checkpoint path. The exact historical pre-deployment
  workaround is retained only for interpreting older runs:
  `perl -e 'open(my $fh, ">", $ARGV[0]) or die; print $fh $ARGV[1], "\n"; close $fh or die; chmod 0600, $ARGV[0] or die;' <path> '<json>'`.
- Do not use the B5 bare-name workaround during field validation; the worker
  must invoke its runtime-pinned absolute `agent-session` lifecycle command.
  The exact historical bare-name release invocation is retained for older
  run interpretation:
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
