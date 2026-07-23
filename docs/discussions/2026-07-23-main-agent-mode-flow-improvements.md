# Main Agent Mode Flow Improvements — Design Review

- **Status**: design review / decision-ready; no implementation started. Feeds
  the next decision cycle on making Main Agent Mode smoother to operate.
- **Date**: 2026-07-23
- **Author context**: source-grounded review across `agent-runtime-kit`,
  `nils-cli`, and `agent-console` at the HEADs recorded below, plus a bounded
  read-only live probe of the installed `main-agent` / `agent-session`
  `1.25.9 (v1.25.9-20-gdc974b51)` surface.
- **Prior art (read first)**:
  `docs/discussions/2026-07-22-main-agent-orchestration-runtime.md` — the
  implementation handoff that landed the runtime. This document is the follow-on
  flow review, not a re-plan of that work.

## Purpose

Main Agent Mode is functionally correct and the runtime has landed. The open
question is **usability / flow**: does the workflow get out of the way, or does
its ceremony slow the operating agent down? This review evaluates that, ignoring
security (explicitly deferred by the requester), grounds each suspected gap in
source (real gap vs. already-exists-unused), and proposes improvements with
trade-offs so the next step can decide.

Two requester steers frame the whole review and are treated as first-class:

1. **Collapse ceremony into high-level commands** so the main agent is pleasant
   to drive — while the process and validation stay exactly as strict. The
   question is what can be *further automated* without weakening correctness.
2. **Keep the low-level primitives**, and treat **fast-path** and **batch**
   operations as important working features, not nice-to-haves.

Both are endorsed by this review and map onto a clean **two-layer facade**
principle (below).

## Method And Evidence Base

- `agent-runtime-kit` @ `main` (this repo): skill/protocol/hooks.
- `nils-cli` @ `fe0602f6`: `main-agent` facade + `agent-session` primitives
  (both in `crates/agent-session/`; facade in `src/main_agent.rs`, orchestration
  types in `src/orchestration.rs`, spec in
  `crates/agent-session/docs/specs/main-agent-orchestration-v1.md`).
- `agent-console` @ `554fefe`: `packages/{shared,edge,ui}`.
- Live read-only probe: `agent-session activity doctor`, `main-agent
  self show/status/rehydrate/worker list`, full `--help` tree. No worker was
  launched (the local Claude provider is `classification:"partial"`,
  `configured:false`, so a live launch would stall at the readiness gate — a
  finding in itself, see T1).

Evidence is cited inline as `repo · path:line`. `nils-cli` line numbers are at
`fe0602f6`.

## What Already Works — Do Not Rebuild

These were suspected gaps but are **resolved in current source**. The next step
should not spend effort here.

- **Worker start is no longer the P0 blocker.** Both bugs the handoff doc
  flagged are fixed at `fe0602f6`, ahead of that doc's "still being finalized"
  note:
  - broker recursion → `nils-cli` commit `27fde619` (binds the coordination
    broker to the sibling `agent-session` executable, not `main-agent`).
  - resumed-worker incarnation continuity → `nils-cli` commit `f3bceec0`
    (revision-fenced worker checkpoint rebinds only when the prior incarnation is
    dead; guards terminal-state regression).
  - `main-agent worker start` launches a genuinely **interactive, attachable**
    tmux-backed managed session via the shared `start_session` path
    (`nils-cli · main_agent.rs:945-970`) and reuses a stable worker session on
    retry.
- **Operator console already has push + clean lifecycle UI.** SSE
  `/api/activity/events` pushes `turn_state` deltas sub-second; list-membership
  changes trigger an immediate reconcile refetch; the 4s poll
  (`agent-console · ui/src/Dashboard.tsx:148`) is only the degraded floor.
  Worker cards attach over the identical WS route as standalone sessions (no
  role branching, no blank-card residue). Orchestration fields (role, run,
  assignment, manager, counts) are explicitly allowlisted through
  shared→edge→UI. Tombstoned/cleanup-pending sessions leave the grid and appear
  only in a dedicated maintenance drawer.
- **Retry is *safe* even though it is not automatic.** Idempotency keys give
  exactly-once replay keyed by `session:incarnation:key` + request digest
  (`nils-cli · main_agent.rs:1943-1963`), and `worker start`/`worker delete`
  persist **pending receipts** so a retry resumes a mid-op side effect rather
  than duplicating it (`main_agent.rs:825-840, 1204-1218`). This is the
  foundation T6 builds on.

## Design Principle: Two-Layer Facade

Keep the current granular verbs (`init`, `worker start/accept/release/delete`,
`collaborate`, `borrow`, `handoff`, `adopt`, `close`) as the **primitive layer**
for strict automation and recovery. Add a **macro layer** on top that collapses
verified multi-step choreography into intent-level commands whose proofs run
*inside* the command and return one typed result. Validation strength is
unchanged; it simply stops being hand-choreographed by the agent. This matches
the runtime's own stated intent that "ordinary Main Agent operation uses the
facade so required proofs are not accidentally omitted" — the review's finding is
that the facade does not yet go far enough up the abstraction ladder.

## Locked Decisions (2026-07-23)

Confirmed with the requester before implementation. These supersede the "Open
Decisions" section below (kept for rationale).

1. **T1 macro shape** — **Fold the verified proofs into `worker start`** (not a
   separate `worker launch`). `worker start` gains readiness + newer-turn +
   identity proofs internally and returns a typed result
   (`ready | readiness_failed | identity_mismatch | turn_unverified` + safe
   state). Consequence: `worker start` is no longer a pure spawn primitive; a raw
   spawn, if ever needed, goes through `agent-session` directly.
2. **T2 revision model** — **Decouple** assignment revision from run revision.
   Assignments are fenced on their own revision; assignment creation no longer
   bumps the run revision. This removes the parallel/batch collision at the
   source. Accepts one schema/migration change.
3. **T3 completion awareness** — **`worker wait`** bounded long-poll over
   assignment-state transitions (facade/client loop), not an SSE event-bus
   extension.
4. **T5 lane dependency** — **Add `depends_on` now**, in the same schema wave as
   the T2 decoupling, to avoid a second migration.
5. **Fast-path** — a separate **`main-agent quick`** command (ephemeral
   run + single assignment + auto-close on accept), not a `--fast` flag smeared
   across verbs.
6. **Scope/sequencing** — implement in **waves**, nils-cli first (version skew);
   P0 first. The runtime-kit-side P0 (protocol↔skill reconciliation) is the first
   completed+validated slice; nils-cli P0 (T6 auto-retry, T7 lightweight rebind)
   is the next wave.

## Themes

Each theme: current state (grounded) → flow cost → options with trade-offs →
recommendation → open decision.

### T1 — Ceremony → verified high-level macros (highest leverage)

**Current state.** `worker start` already does more than a primitive: it creates
the assignment, asserts the main's active claim, stores a pending receipt,
launches the interactive session, delivers a **bootstrap** prompt (the worker
self-recovers its real packet via the facade), and binds the worker ref
atomically (`nils-cli · main_agent.rs:803-1002`). **But** it returns immediately
after launch — it does **not** internally perform the readiness gate,
paste-count verification, activity baseline, or the "newer provider-hook turn"
proof. Those live only as **prose the agent hand-runs** in
`core/skills/conversation/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md`
(§"Verified Worker Startup And Prompt Delivery", 9 steps). There are also **no**
macros for teardown (cleanup = hand-run `release` → `delete` → fresh-list
absence) or for the mechanical half of acceptance.

Net: **two overlapping, unreconciled choreographies** — the CLI's internal
launch flow and the skill's manual verification sequence — with partial overlap
(paste) and partial gaps (turn-proof).

**Flow cost.** The agent spends many turns hand-choreographing and re-verifying;
every "uncertain" sub-step is a hard stop; the prose and the CLI behavior can
drift apart over releases.

**Options.**
- **A (recommended).** Make one command the single verified macro — either
  extend `worker start` or add `worker launch` — that folds the readiness gate +
  newer-turn proof + identity proof *inside* and returns a typed result
  (`state: ready | readiness_failed | identity_mismatch | turn_unverified`, plus
  `safe_state`). Add `worker retire` (quiescence proof → release → delete →
  fresh-list absence in one call) and an `accept` that *gathers* mechanical
  evidence (diff ref, validation handles, review findings) while leaving the
  decision to the agent. Reduce the protocol to "call the macro; branch on the
  typed failure."
- **B.** Leave the CLI as-is; only rewrite the protocol prose to stop
  duplicating what `worker start` already does. Cheap and immediate, but the
  turn-proof gap and the missing retire/accept macros remain.
- **C.** Add a runtime-kit workflow/skill script that choreographs the steps.
  Keeps nils-cli untouched but puts orchestration logic in the wrong layer and
  re-introduces drift; rejected.

**Recommendation.** A, phased: first do B's prose reconciliation as an immediate
low-risk win, then land `worker launch` (typed verified result) and
`worker retire`.

**Open decision.** Fold the proofs into `worker start` (changes its contract) or
introduce a separate `worker launch` wrapper that composes start + proofs?

### T2 — Fast-path (low-gear) + batch multi-lane

**Current state.** Every operation is strictly one-per-invocation: `init` one
packet, `worker start` one `--assignment-file`, `accept/release/delete/show/
message` one `<ASSIGNMENT_ID>`. Critically, each `worker start` **bumps the run
revision** via `--if-run-revision` (`nils-cli · main_agent.rs:853-854`), so
naive parallel or looped starts **collide on run revision** and must serialize.
There is no lightweight path for L0/L1 `delegate-all`.

**Flow cost.** Launching N lanes = N serial invocations, each re-reading the new
run revision; setup is slow and fiddly. Small delegated work pays full L3-shaped
ceremony.

**Options.**
- **A (batch under one bump).** `worker start --batch <dir|array>` creates N
  assignments and launches N workers under a **single** run-revision transition,
  returning per-lane typed results. Directly resolves the revision collision;
  smaller change.
- **B (decouple revisions).** Stop bumping the *run* revision on assignment
  creation; fence each assignment on its own revision only. Parallel single
  starts then never collide, and batch becomes a convenience wrapper. Cleaner
  data model, larger change, needs migration care.
- **Fast-path.** Either a `--fast` preset or a `main-agent quick
  --assignment-file F` that, for L0/L1 `delegate-all`, spins an ephemeral
  run+single-assignment, keeps the claim + validation duties, and auto-closes on
  accept — skipping durable-run scaffolding.

**Recommendation.** B is the more durable fix (removes an entire class of
friction and is the precondition for smooth parallelism); batch (A) layered on
top; fast-path as a thin preset over whichever revision model is chosen.

**Open decision.** Decouple assignment revision from run revision (B, bigger,
cleaner) vs. batch-under-single-bump only (A, smaller)?

### T3 — Completion awareness for the *agent* (not just the console)

**Current state.** The operator console has push (above). The orchestrating
**main agent is a CLI consumer and is poll-only**: `worker list` / `status` /
`rehydrate` read `orchestration/registry.json`
(`nils-cli · main_agent.rs:1074, 647, 600`). The daemon SSE `/activity/events`
carries per-session `turn_state` only — not assignment lifecycle
(`serve.rs` has zero orchestration references;
`collect_activity_stream_sessions` returns `{id, turn_state}`).
`agent-session message wait` is a bounded long-poll over **one already-known**
message revision (`nils-cli · mailbox.rs:461-540`), not "any new event."

So the asymmetry that matters: **the human gets push; the agent does not.**

**Flow cost.** The main agent must poll on some cadence and re-read a full
capsule each cycle, then diff it in-context to notice which lane moved — latency
plus wasted reasoning between polls.

**Options.**
- **A (recommended).** `main-agent worker wait [--assignment ID | --any]
  --until submitted|blocked|terminal --timeout D` — a bounded long-poll over
  assignment-state transitions, returning which assignment changed and its new
  state. Even a client-side loop inside the facade removes the agent's manual
  cadence; pairs naturally with T1/T2 ("launch N, then wait until any
  submitted"). Cheapest, self-contained.
- **B.** Extend the daemon SSE to emit orchestration/assignment deltas and give
  the agent a subscribe path. Richer and reusable (the console is already wired
  to consume orchestration on the stream), but a larger surface and more
  moving parts.

**Recommendation.** A now; B later if a richer event bus is independently
wanted.

**Open decision.** Bounded `worker wait` long-poll (A) vs. extend the SSE event
bus (B)?

### T4 — Acceptance throughput (owned mostly by runtime-kit)

**Current state.** The protocol makes the entire acceptance loop main-serial and
non-delegable (`MAIN_AGENT_MODE_PROTOCOL.md` §"Main-Agent Acceptance Loop" and
§"Main Agent Ownership"). `code-review-specialists` already fans out, but
full-diff inspection + validation rerun + synthesis + decision all run in the
single main context.

**Flow cost.** Workers finishing near-simultaneously queue behind one serial
acceptor; throughput is capped by the main's per-result serial work.

**Options.**
- **A (recommended).** Keep the *decision* main-owned, but let the mechanical
  *gather* fan out: spawn read-only reviewer/validation sub-agents per lane in
  parallel and present the main a per-lane "acceptance evidence bundle" (diff
  ref, validation results, review findings) it can decide on quickly. This is a
  skill/protocol shape, not a CLI change.
- **B.** Allow a trusted pre-screening worker — crosses the "worker never
  accepts" boundary; deferred as risky.

**Recommendation.** A — codify parallel acceptance-gather in the skill;
serialize only the decision. Low risk, pure policy + orchestration.

### T5 — Lane dependency / ordering primitive

**Current state.** No ordering fields exist. `AssignmentRecord`
(`nils-cli · orchestration.rs:77-112`) and `AssignmentInput`
(`main_agent.rs:297-317`) have no `depends_on` / `blocked_by` / `sequence` /
`after`. `blocked` is a self-reported worker state, not an inter-assignment
edge. Ordering lives only in the main's head and checkpoint prose, and is lost
across compaction (rehydrate returns assignments + prose, no edges).

**Flow cost.** Cross-lane sequencing for real L3 work is manual and
non-durable.

**Options.**
- **A (recommended).** Add optional `depends_on: [assignment_id]` to the
  assignment input/record. The facade marks a dependent `blocked-by-dependency`
  (or refuses launch) until its deps reach `accepted`, and rehydrate surfaces the
  edges so ordering survives compaction. Advisory-to-launch, not an ACL.
- **B.** Keep ordering external; document a convention. Cheapest, durability gap
  remains.

**Recommendation.** A — small schema addition, large durability/flow payoff.

### T6 — Auto-retry / self-heal on transient failures

**Current state.** No facade retry loop; the contract pushes retry onto the
caller (`main-agent --help`: "Retry an ambiguous outcome with the identical
request and idempotency key"). Transient conditions surface as exit `69` /
`orchestration-store-busy` / `retryable:true`
(`nils-cli · orchestration.rs:449-454, 644-650`). Idempotency + pending receipts
already make retry safe (see "What Already Works").

**Flow cost.** Transient blips (lock contention, brief unavailability) surface
as "blocked, needs human" rather than self-healing.

**Options.**
- **A (recommended).** Bounded auto-retry with backoff on exit `69` /
  `retryable:true`, reusing the **same** idempotency key (safe by construction).
  Place it in the macro layer (or a thin facade wrapper) so the granular
  primitives stay pure for strict automation. Cap attempts; surface clearly
  after exhaustion.

**Recommendation.** A — cheap, safe, immediate flow win.

### T7 — Recovery ergonomics: lightweight rebind + rehydrate delta

**Current state.** A resumed main session (new incarnation) makes **every**
main-side command fail `controller-rebind-required`
(`nils-cli · main_agent.rs:2108-2114`, funneled through `require_current_main`
at `:1801-1812`). Rebind requires re-supplying the **original private packet**
(digest must match), `--if-revision`, and proof the prior incarnation is dead
(`main_agent.rs:474-522`). There is no lightweight or automatic rebind.
`rehydrate` returns a full capsule only — no `--since`/delta
(`main_agent.rs:600-645`).

**Flow cost.** A mere session resume hard-stops all orchestration until a full
`init`-with-original-packet round-trip, and requires the agent to still hold the
exact packet file. Every monitoring poll re-reads and re-reasons the full
capsule.

**Options.**
- **rebind A (recommended).** A lightweight continuity rebind (`init --rebind`
  or `adopt-self`) that, when the same public session id authenticates at a new
  incarnation and the prior incarnation is proven dead, rebinds using the
  **stored** packet digest — the server already holds the packet, so require
  only `--if-revision` + a confirmation token, not the reconstructed original
  file. Keeps the ABA (delete/recreate) refusal.
- **delta A.** Add `rehydrate --since <revision>` / `status --since` (or
  `worker list --changed-since N`) returning only changed assignments.

**Recommendation.** Both; lightweight rebind is higher priority because it is a
hard stop on every resume.

### Out of scope for "先好用": single-host federation

Confirmed V1 limitation — a run's participants share one `agent-session` state
root (single `orchestration/registry.json`; `machine` is advisory only). No
cross-host federation. Revisit alongside provider-native subagents; not a
near-term flow fix.

## Proposed High-Level Command Surface (sketch)

Illustrative, to anchor the decisions — not a committed API. All existing
granular verbs are retained underneath.

```text
# Verified macros (proofs inside; typed result) — per Locked Decision #1/#2:
main-agent worker start --assignment-file F --idempotency-key K   # proofs folded in; no run-revision bump (#2)
    -> { state: ready|readiness_failed|identity_mismatch|turn_unverified, worker:{...}, safe_state }
main-agent worker start --batch DIR --idempotency-key K           # N assignments, independently fenced (#2)
main-agent worker wait  [--assignment ID | --any] --until submitted|terminal --timeout D
main-agent worker retire ID --if-revision N --idempotency-key K   # quiescence -> release -> delete -> absence

# Recovery ergonomics:
main-agent init --rebind --idempotency-key K   # stored-packet continuity rebind, no original file
main-agent rehydrate --since N                  # delta capsule

# Fast-path (L0/L1 delegate-all):
main-agent quick --assignment-file F           # ephemeral run+assignment, auto-close on accept
```

## Cross-Cutting Constraints Any Design Must Respect

- **Revision fencing is real.** Batch/parallel must not naively collide on run
  revision (T2). Prefer decoupling assignment revision from run revision, or a
  single-bump batch transition.
- **Idempotency + pending receipts already make retry safe** — reuse the same
  key; do not invent a parallel retry mechanism (T6).
- **Claim boundary is invariant.** `init` acquires/confirms the target-owned
  claim before its first durable write; every macro must preserve this and the
  worker-self-check + claim handoff.
- **Admission allowlist is byte-exact.** The pre-claim allowlists in
  `core/hooks/shared/session-coordination-guard.py:952-996` and
  `core/hooks/shared/pre-edit-intent-gate.py:905-996` hard-code exact argv
  shapes. **Any new pre-claim command shape** (e.g. `init --rebind`) must be
  added there or `enforce`-mode bootstrap breaks; post-claim macros run under an
  active claim and are admitted generically (verify per command).
- **Product-neutral + graceful degradation.** The runtime-kit skill must keep
  working (degraded) where `main-agent` is absent; macros are host-specific
  mechanics that stay out of the portable protocol contract.
- **Local-only delivery** remains in force while the GitHub restriction holds —
  no provider artifacts for this work yet.

## Prioritized Roadmap

| Priority | Items | Rationale | Owning repo |
| --- | --- | --- | --- |
| **P0 — immediate flow, low risk** | T1 protocol↔CLI reconciliation (prose); T6 auto-retry on `69`; T7 lightweight rebind | Removes the most painful hand-choreography and the hard stop on resume with little/no schema change | runtime-kit (T1 prose); nils-cli (T6, T7) |
| **P1 — the flagged core features** | T1 `worker launch`/`worker retire` verified macros; T2 batch + fast-path; T3 `worker wait` | Ceremony-collapse + batch/fast-path + completion awareness — the requester's named priorities | nils-cli (+ runtime-kit skill rewrite + allowlist) |
| **P2 — durable parallel correctness** | T5 `depends_on`; T2 assignment/run revision decoupling; T4 acceptance-gather fan-out; T7 rehydrate delta | Makes multi-lane L3 durable and higher-throughput | nils-cli (schema); runtime-kit (T4 policy) |
| **Deferred** | single-host federation | Tied to provider-native subagents | nils-cli (future) |

## Execution Status

- **T6 auto-retry — implemented + validated + committed 2026-07-23 (`7d5fd28`, folded with T7).**
  In `nils-cli` (`crates/agent-session/src/main_agent.rs`, +191/−30 on a clean
  working tree at `6af12242`): a facade-level `retry_transient_store` wrapper at
  `dispatch` re-runs the resolved command (via a new `run_command`) with bounded
  linear backoff, gated strictly on the two transient store codes
  (`orchestration-store-busy`, `orchestration-store-unavailable`); the low-level
  primitives are unchanged. Re-run safety rests on the existing idempotency
  replay + pending start/delete receipts. The command arg structs gained
  `#[derive(Clone)]` so the command can be re-executed. Test-first: 4 unit tests
  (`main_agent::tests`) added with a verified red (no-retry stub) → green.
  Validation to the CI bar: `cargo fmt --all -- --check` (pass),
  `cargo clippy -p nils-agent-session --all-targets --all-features -- -D warnings`
  (exit 0, 0 warnings), `cargo test -p nils-agent-session --lib` (549 passed,
  0 failed). Not committed; no runtime-kit consumption needed (behavioral, no
  new command shape, no admission-allowlist change).
- **T7 lightweight rebind — implemented + validated + committed 2026-07-23 (`7d5fd28`, folded with T6).**
  Shape decision: a dedicated `main-agent rebind --if-revision N
  --idempotency-key K --format json` subcommand (not `init --rebind`), keeping
  `init` single-purpose and the allowlist entry simple.
  - **nils-cli** (`crates/agent-session/src/main_agent.rs`, clean tree at
    `6af12242`): new `Rebind(RunMutationArgs)` variant + `run_rebind`, wired
    through `dispatch`/`run_command`/`command_name`/`command_output_format`.
    `run_rebind` recovers the run's **stored** objective packet via
    `orchestration::read_packet` to re-acquire the work-context claim (no packet
    file), then mirrors `run_init`'s continuity-rebind preconditions
    (revision fence + prior-incarnation-dead refusal) under the registry lock.
    Validated: `fmt --check` ✓, `clippy -D warnings` exit 0 ✓,
    `cargo test -p nils-agent-session --lib` 549 passed ✓, plus a
    `rebind --help` surface smoke.
  - **agent-runtime-kit**: the exact pre-claim `rebind` argv shape added to both
    byte-exact allowlists (`core/hooks/shared/session-coordination-guard.py`,
    `core/hooks/shared/pre-edit-intent-gate.py`) with allowed + rejected-variant
    coverage in both mirror tests; `bash tests/hooks/run.sh` → 329 passed ✓.
    Shared hooks are not rendered/golden-pinned, so no golden refresh.
  - **Scoped test waiver**: no command-flow integration harness exists in the
    `nils-agent-session` crate (no test builds an authenticated `CliContext`;
    `nils-test-support` offers only git/env fixtures), so a full end-to-end
    `run_rebind` integration test is waived for this slice. Justification: the
    rebind branch mirrors the already-shipped `run_init` continuity path and the
    new logic is a straight-line `read_packet` + `ensure_or_acquire_claim`; the
    hook allowlist (the security-relevant surface) is fully unit-covered.
- **T3 `worker wait` — implemented + validated + committed 2026-07-23 (`25833e8`).**
  In `nils-cli` (`crates/agent-session/src/main_agent.rs`, +233, on `main` at
  `7d5fd28`): a new read-only `worker wait [ASSIGNMENT_ID | --any]
  --until submitted|blocked|terminal [--timeout D]` — a bounded (1-60s),
  level-triggered long-poll over assignment state. It mirrors `worker show`
  (`authenticated_self` → `load_registry_readonly` → `require_current_main`),
  takes **no** registry lock (side-stepping lock contention and any T6
  auto-retry deadline reset), needs no claim/idempotency key, and returns
  `{outcome: transitioned, assignment}` or `{outcome: timeout}` — a deliberate
  ergonomic divergence from the mailbox `message wait` Err-timeout, since the
  consumer is the orchestrating agent (documented in the spec). Wired through
  `run_worker` / `run_command` / `command_name` / `command_output_format`; the
  worker arg structs were already `Clone` from the T6 diff. Spec updated (facade
  list + read-only / level-trigger / never-acceptance note). Test-first: 5 unit
  tests (`WaitUntil::matches` inclusion+exclusion, `parse_wait_timeout` bounds +
  suffixes; **verified red** by relaxing the 60s bound → `61s` wrongly accepted →
  fail → revert) + 1 binary-driven integration test (level-trigger
  `transitioned`, `--any`, `timeout` outcome, `assignment-not-found`,
  `worker-wait-target`). Scoped validation green: `cargo fmt --check`,
  `cargo clippy -p nils-agent-session --all-targets --all-features -- -D warnings`
  (0 warnings), `cargo test -p nils-agent-session --lib` (554 passed) + the
  worker-wait integration test. **Scoped waiver**: the crate's
  `cli::serve_usage_*` integration tests fail in this sandbox on `/usage`
  connection-refused (local HTTP server unreachable), unrelated to this diff, so
  a full `--local-fast` cannot pass here. No runtime-kit admission-allowlist
  change: `worker wait` runs post-`init` and is admitted generically like
  `worker list`/`show`. Committed 2026-07-23 (`25833e8`) on top of `7d5fd28`.
- **Remaining waves** (nils-cli-led): T1 fold verified proofs into
  `worker start` (behavioral) · T2 assignment/run revision decouple + batch
  (schema/migration) · T5 `depends_on` (schema, same wave as T2) ·
  `main-agent quick` fast-path.

## Open Decisions For The Next Step

**Resolved 2026-07-23 — see "Locked Decisions" above. Retained for rationale.**

1. **T1 shape** — proofs folded into `worker start` (contract change) vs. a new
   `worker launch` wrapper?
2. **T2 revision model** — decouple assignment revision from run revision
   (bigger, cleaner) vs. batch-under-single-bump only (smaller)?
3. **T3 mechanism** — bounded `worker wait` long-poll (cheap) vs. extend the SSE
   event bus (richer)?
4. **T5** — add `depends_on` now vs. keep ordering external for V1?
5. **Fast-path shape** — `--fast` preset vs. a separate `main-agent quick`?
6. **First-cut scope** — land the P0 quick wins as a standalone pass first, or
   bundle P0+P1?

## Validation Implications (when work is authorized)

- **nils-cli**: test-first reds for each new command (macro typed outcomes,
  batch revision handling, `worker wait` timeout/transition, `depends_on`
  gating, auto-retry exhaustion, lightweight rebind ABA refusal), plus the
  repository gate `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`.
- **agent-runtime-kit**: rewrite the protocol/skill for the macro layer;
  add/adjust the byte-exact admission allowlist entries and their hook tests;
  update golden + runtime-smoke for the changed skill prose; gate with
  `bash scripts/ci/all.sh && bash tests/hooks/run.sh`.
- **agent-console**: no change unless T3 chooses the SSE-extension option, in
  which case exercise the already-wired orchestration-on-stream consumption.

## Retention Intent

Coordination / decision-input artifact. Cleanup-eligible once the decisions
above are made and the resulting work ships or is abandoned; promote any durable
architecture into the owning canonical spec
(`nils-cli · crates/agent-session/docs/specs/main-agent-orchestration-v1.md`)
rather than leaving a stale duplicate here.
