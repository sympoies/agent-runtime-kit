# Main Agent Mode — Post-Deploy Test Plan (T6/T7/T3)

- **Date**: 2026-07-23
- **Purpose**: Confirm two things about the landed flow features, per the
  requester steer — **(A) the CLI is correct end-to-end**, and **(B) the flow is
  *smooth*: the operating agent should not hand-run ceremony that belongs inside
  the tool.** Companion to
  `2026-07-23-main-agent-mode-flow-improvements.md` (design review) — this
  validates what shipped.
- **Deployed baseline under test**: `main-agent v1.25.9-25-g61d9932c`
  (local workspace install at `~/.local/nils-cli/bin/main-agent`, shadows the
  brew Cellar `dc974b51` via PATH). Includes T6 auto-retry, T7 rebind, T3
  `worker wait`. `agent-session` sibling: `v1.25.9-24-g62bc5228` (registry schema
  unchanged across the gap → compatible).
- **Legend**: ✅ done/passing · 🟡 partial / needs a real worker or human · ⛔
  blocked by a not-yet-landed wave.

## Part A — E2E CLI correctness

Each case lists how it is exercised: **auto** (Rust integration test drives the
compiled binary), **live** (ran against the deployed binary this session), or
**manual** (needs a real tmux worker / human review).

| # | Feature | Case | Method | Expected | Status |
| --- | --- | --- | --- | --- | --- |
| A1 | T3 wait | `--assignment ID`, target already in state | auto | `{outcome: transitioned, assignment}` immediately (level-triggered) | ✅ |
| A2 | T3 wait | `--any`, one lane in target state | auto | returns that assignment | ✅ |
| A3 | T3 wait | target unreachable within `--timeout` | auto | `{outcome: timeout}`, exit 0 | ✅ |
| A4 | T3 wait | unknown assignment id | auto | error `assignment-not-found` | ✅ |
| A5 | T3 wait | neither id nor `--any`; both together | auto+live | error `worker-wait-target` | ✅ |
| A6 | T3 wait | `--timeout` 0 / >60s / garbage | live+unit | `worker-wait-timeout` / `invalid-duration` | ✅ |
| A7 | T3 wait | invalid `--until` value | live | clap rejects `invalid value` | ✅ |
| A8 | T3 wait | valid args, caller is not the live controller | live | graceful `controller-rebind-required` | ✅ |
| A9 | T3 wait | `--until blocked` returns on a blocked lane | auto-extend | `{outcome: transitioned}` | 🟡 add case |
| A10 | T6 retry | transient `orchestration-store-busy` retried, converges | unit | bounded linear backoff, then success | ✅ |
| A11 | T6 retry | non-transient error not retried; exhaustion surfaces | unit | immediate error / last error after N | ✅ |
| A12 | T7 rebind | resumed incarnation rebinds via **stored** packet (no file) | auto (init parity) + live-reachable | run rebinds, revision fenced | 🟡 add dedicated rebind case |
| A13 | T7 rebind | ABA (delete/recreate) refused; live prior incarnation refused | unit/spec | refusal codes | 🟡 |
| A14 | lifecycle | `init → worker start → wait → accept → release → delete` | manual | interactive worker attachable; transitions fence | 🟡 needs tmux |
| A15 | reads | `status` / `rehydrate` / `worker list` / `show` unaffected | auto | unchanged | ✅ |

**A-summary**: the T3 surface is fully covered (auto + live); T6 is unit-covered;
T7's dedicated rebind e2e and the full interactive lifecycle (A12–A14) are the
open coverage gaps — cheap follow-ups (A9/A12/A13 are small test additions;
A14 needs a real tmux worker).

## Part B — Flow smoothness (ceremony audit)

The real bar: for each canonical flow, is the proof/choreography **inside the
command** (typed result the agent branches on) or **hand-run prose** the agent
executes turn-by-turn? Fewer agent steps = smoother.

| Flow | Before | After landed features | Ceremony now | Owner of remaining gap |
| --- | --- | --- | --- | --- |
| **Wait for a lane to finish** | agent polls `worker list`/`status` on a self-chosen cadence, re-reads the full capsule, diffs in-context to see which lane moved | `worker wait --any --until submitted` blocks and returns *which* lane changed + its state | **Low ✅** — one call, typed outcome | — (T3 landed) |
| **Transient store blip** | agent sees exit 69 / `store-busy`, decides to hand-retry with the same idempotency key | facade auto-retries the two transient codes with bounded backoff; primitives stay pure | **Low ✅** — invisible to the agent | — (T6 landed) |
| **Resume after compaction** | every main command fails `controller-rebind-required`; agent must re-run `init` with the **original packet file** it must still hold | `main-agent rebind --if-revision N` rebinds from the **stored** packet; one call | **Low ✅** | — (T7 landed) |
| **Launch a worker** | — | `worker start` creates+launches, but readiness gate + newer-turn proof + paste verification are **9 hand-run steps** in the protocol prose | **High ⛔** | **T1** (fold proofs into `worker start`, typed result) |
| **Launch N lanes** | — | N serial `worker start` calls, each bumping run-revision → collisions force serialization | **High ⛔** | **T2** (decouple assignment/run revision + batch) |
| **Accept a result** | — | mechanical gather (diff, validation rerun, review synth) is main-serial and hand-run before the decision | **Medium ⛔** | **T4** (parallel acceptance-gather; decision stays main-owned) |
| **Order dependent lanes** | — | ordering lives only in the agent's head / checkpoint prose; lost across compaction | **Medium ⛔** | **T5** (`depends_on` edges that survive rehydrate) |
| **Teardown a worker** | — | `release → delete → confirm fresh-list absence` hand-run | **Medium** | T1 (`worker retire` macro) |

**B-summary**: the three landed features each collapsed a *specific* ceremony
(polling, transient-retry, resume-rebind) into the tool — those flows are now
smooth. The **remaining ceremony is concentrated in worker startup (T1) and
batch launch (T2)**, then acceptance (T4) and ordering (T5). The flow is "usable"
today but not yet "smooth" end-to-end until T1/T2 land; that is the correct next
target for the "先好用" goal.

**Ceremony acceptance check (run per flow):** count the agent's turn-by-turn
steps and manual proofs. A flow passes the smoothness bar when the agent issues
**one command and branches on a typed result**, with no hand-run verification
that the tool could prove itself.

## Part C — Results executed this session

- **Unit** (`cargo test -p nils-agent-session --lib`): **554 passed, 0 failed**.
  Includes `WaitUntil::matches` inclusion/exclusion, `parse_wait_timeout` bounds
  + suffixes. Test-first **verified red** (relaxed the 60s bound → `61s` wrongly
  accepted → failing test → reverted).
- **Integration** (binary-driven): `worker wait` case passes (level-trigger,
  `--any`, timeout outcome, `assignment-not-found`, `worker-wait-target`). Full
  crate integration = **137/139**; the only 2 failures are `cli::serve_usage_*`,
  which fail on `/usage` **connection-refused** (sandbox cannot bind/reach a
  localhost HTTP server) — in `cli.rs`, unrelated to this diff; a networked CI
  passes them.
- **fmt** `--check` clean · **clippy** `-p nils-agent-session --all-targets
  --all-features -- -D warnings` = 0 warnings.
- **Deployed-binary live smoke** (`~/.local/.../main-agent`
  `v1.25.9-25-g61d9932c`): `worker wait --help` args correct; error paths return
  `worker-wait-target`, `worker-wait-timeout`, clap enum rejection, and
  `controller-rebind-required` on real state — all as specified.

## Part D — Open items

1. **A-coverage gaps** (cheap): add integration cases A9 (`--until blocked`),
   A12/A13 (dedicated T7 rebind + ABA refusal e2e). A14 (interactive lifecycle)
   needs a real tmux worker.
2. **Flow-smoothness backlog** = the pending waves, in priority order for the
   usability goal: **T1** (fold worker-start proofs + `worker retire`) →
   **T2** (revision decouple + batch/fast-path) → **T4** (parallel
   acceptance-gather) → **T5** (`depends_on`).
3. **serve_usage** environmental failures are a sandbox limitation, not a defect;
   re-verify in a networked run before any release.
4. **Deploy note**: this is a local workspace install for testing only. A real
   release (which would put these in the runtime for all sessions) remains
   deferred under the local-only restriction; `main-agent`/`agent-session`
   sibling versions differ by one commit today (schema-compatible).
