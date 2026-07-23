# Main Agent Mode — Simplified-Flow Acceptance Test Plan (T1/T2/T4/T5 + hook admission)

- **Date**: 2026-07-23
- **Purpose**: Final-acceptance test plan for the *now-installed* main-agent-mode
  simplification. Validates two bars, per the standing steer:
  - **(A) Correctness** — every landed command behaves to spec end-to-end
    (typed results, exit codes, state transitions, fail-closed paths).
  - **(B) Smoothness** — the flow ceremony that used to be hand-run prose is now
    *inside the tool* (one call → typed result the agent branches on). This plan
    **re-audits** the flows that were rated "High ⛔" in the companion doc and
    checks whether the landed folds actually collapsed them.
  - Not just correctness: **Part F requires improvement proposals to be written
    after execution** — anything that is correct-but-still-clunky becomes a
    ranked change list.
- **Baseline under test (installed 2026-07-24, this runtime)**:
  - `main-agent` / `agent-session` = **`v1.25.9-39-g662b5479`**
    (`~/.local/nils-cli/bin/`, shadows brew via PATH). Includes Waves 1–3
    (`a8b83732`) + T3/T6/T7 + 14 intervening fixes.
  - Runtime-kit live hooks synced to `main` (`50aa99b`+): `pre-edit-intent-gate.py`
    and `session-coordination-guard.py` admit `main-agent quick` / `rebind`;
    byte-identical to source; all `agent-runtime`/`agent-hook` doctors
    `converged`/`verified`.
- **Companion docs** (do not duplicate):
  - `2026-07-23-main-agent-mode-test-plan.md` — T3/T6/T7 post-deploy plan (old
    baseline `g61d9932c`). Its A1–A15 (`wait`/retry/rebind) stay valid; **this
    plan supersedes its Part B ceremony ⛔ rows**, which those waves now close.
  - `2026-07-23-main-agent-mode-flow-improvements.md` — design review (the "why").
  - `2026-07-23-main-agent-mode-remaining-waves-plan.md` — wave execution record.
  - `conversation/skills/.../references/MAIN_AGENT_MODE_PROTOCOL.md` — the folded
    protocol prose that Part D scores.
- **Legend**: ✅ done/passing · 🟢 pre-verified this session (install acceptance)
  · 🟡 needs execution (auto/live) · 🔴 needs a real interactive worker (manual)
  · ⛔ blocked.
- **Test tiers**: **auto** = Rust integration/unit drives the compiled binary
  (`nils-cli`); **hook** = runtime-kit hook mirror tests
  (`tests/hooks`, `tests/agent-hook`); **smoke** = runtime-kit runtime-smoke
  probe; **live** = ran against the deployed binary directly; **manual** = real
  tmux worker / human review.

---

## Part 0 — Preconditions (pre-verified this session)

These gate the rest of the plan; all are green as of install.

| # | Precondition | Method | Evidence | Status |
| --- | --- | --- | --- | --- |
| P1 | Deployed binaries are the new baseline | live | `main-agent --version` = `v1.25.9-39-g662b5479` (was `-36-gb6abfa35`) | 🟢 |
| P2 | Simplified commands resolve | live | `quick`, `worker start --await-ready`/`--batch`, `worker retire` all present in `--help` | 🟢 |
| P3 | Live hooks admit `quick`/`rebind` | live | `grep -c '"quick"'` on the 4 live hook files = `1/1/1/1` (was `0/0/0/0`); byte-identical to `main` | 🟢 |
| P4 | Runtime doctors clean | smoke | `agent-runtime doctor` installed-runtime verified (codex 83, claude 84, block=0); `agent-hook doctor` `converged` (codex+claude) | 🟢 |
| P5 | Source landed, tree clean | auto | Waves 1–3 = `a8b83732` on nils-cli `main`; runtime-kit tree clean | 🟢 |

**Gate**: if any of P1–P5 regress, stop and re-run the install (`scripts/install-local-release-binaries.sh`, `scripts/sync-runtime-surfaces.sh --apply --no-pull`) before continuing.

---

## Execution results — 2026-07-24 run (agent-executed)

Full run executed against the installed baseline. Summary:

| Tier | Command | Result |
| --- | --- | --- |
| **auto** | `cargo test -p nils-agent-session` | **721 passed / 0 failed** (577 lib @24.5s + 144 integration @4.6s). Previously-waived `serve_usage_*` now pass (sandbox off → loopback binds). |
| **hook + smoke + docs + golden** | `scripts/ci/all.sh` | **positions 1–17 OK** (exit 0). Hook mirror (quick/rebind), main-agent-mode smoke probe, golden, docs-hygiene for the new doc all green. AGENT_HOME budget rows are documented waivers (#601). |
| **live** | arg/error paths on the deployed binary | mutual-exclusion, required-arg, and await-ready fold contract all confirmed (see A2/A3). |
| **Part C (interactive)** | `main-agent init` (bootstrap probe) | **environment-blocked**: `coordination-unauthorized`. Not a defect — the surface correctly refuses an unauthorized coordination write from a non-managed session (see Part C verdict). |

**Waves 1–3 behaviors proven by named auto tests**: `main_agent_quick_validates_before_launch`,
`maybe_autoclose_closes_only_ephemeral_runs_with_terminal_work`,
`parse_await_ready_treats_zero_as_launch_only`,
`main_agent_worker_start_batch_isolates_per_lane_results`,
`main_agent_worker_retire_rejects_non_terminal_and_missing`,
`unsatisfied_dependencies_clears_on_accepted_and_flags_the_rest`.

**Overall**: correctness bar **met** for every tier automatable from this session;
the one gap is the live interactive-worker loop (Part C), blocked by an
architectural precondition, with the underlying state machine already proven by
the auto integration tests. Improvement proposals: **Part F**.

---

## Part A — Functional correctness matrix

Each row: how it is exercised, the expected typed contract, and the pass
criterion. `auto` cases map to existing/added cases in
`crates/agent-session/tests/integration/coordination.rs`.

### A.1 `main-agent quick` (fast-path: ephemeral run + 1 assignment + auto-close)

| # | Case | Method | Expected (contract) | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A1a | `quick --assignment-file P --idempotency-key K` on no active run | auto+live | creates ephemeral run (`RunRecord.ephemeral=true`) + 1 assignment + launches; result names run id, assignment id, lane | run + assignment exist; `worker list` shows the lane | 🟡 |
| A1b | final `worker delete` of the quick lane | auto | run auto-closes via `maybe_autoclose_ephemeral_run` | `status`/run shows closed; no orphan run | 🟡 |
| A1c | `quick` re-run with the **same** idempotency key | auto | idempotent: returns the same run/assignment, no duplicate | one run only | 🟡 |
| A1d | `quick` while a non-ephemeral run is already active | auto | rejected or scoped per spec (no silent hijack of the active run) | typed error, active run untouched | 🟡 |
| A1e | `quick --help` documents fast-path + required args | live | help states ephemeral + auto-close; requires `--assignment-file` + `--idempotency-key` | matches spec | 🟢 |

### A.2 `worker start --await-ready` (T1 readiness fold)

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A2a | `--await-ready 30s`, worker checkpoints past `starting` in time | auto | `readiness: ready` + `safe_state` | typed `ready`, exit 0 | 🟡 |
| A2b | `--await-ready 5s`, worker never advances | auto | `readiness: readiness_failed` + `safe_state` (not a bare error) | typed `readiness_failed`, safe_state present, exit 0 | 🟡 |
| A2c | `--await-ready 0` | auto+live | launch-only (no readiness poll), same as pre-fold | no poll; result is launch-only | 🟡 |
| A2d | `parse_await_ready`: `30`, `30s`, `2m`, `1h`, garbage, negative | unit+live | valid → Duration; `0`+suffix → launch-only; garbage → `invalid-duration` | bounds enforced | 🟡 |
| A2e | batch/quick + await-ready | auto | launch-only (readiness fold is single-lane per spec) | no per-lane readiness poll | 🟡 |

### A.3 `worker start --batch DIR` (T2 batch + per-lane isolation)

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A3a | dir of N valid packets | auto | N assignments created + N workers launched; array of typed per-lane results | N lanes in `worker list`; N results | 🟡 |
| A3b | one packet invalid among N | auto | that lane fails to its **own** typed result; the other N-1 still launch | failure isolates; batch not aborted | 🟡 |
| A3c | `--batch` + `--assignment-file` together | live | rejected: "takes either --assignment-file or --batch, not both" | typed arg error | 🟡 |
| A3d | neither `--batch` nor `--assignment-file` | live | rejected: "requires --assignment-file or --batch" | typed arg error | 🟢 |
| A3e | parallel batch starts do **not** collide on run revision (T2 decouple) | auto | assignment creation gated on claim + current-main + assignment-absence, not run revision | concurrent starts converge, no revision thrash | 🟡 |

### A.4 `worker retire` (T1 teardown fold)

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A4a | retire an **accepted** assignment | auto | folds release → delete → confirm fresh-list absence; typed success | lane gone from fresh list | 🟡 |
| A4b | retire a **non-accepted** / working lane | auto | typed guard failure (not a partial teardown) | fails closed; lane intact | 🟡 |
| A4c | retire when delete leaves residue | auto | typed **failure** surfaced (not bare success) | non-success result on incomplete teardown | 🟡 |
| A4d | retire re-run after success (idempotency) | auto | idempotent or clean `already-absent`, never a hard crash | deterministic result | 🟡 |

### A.5 `depends_on` (T5 dependency edges)

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A5a | start a dependent whose deps are all accepted/released | auto | allowed | assignment created | 🟡 |
| A5b | start a dependent with an unsatisfied dep | auto | refused; reports `unsatisfied_dependencies` | typed refusal, names the blockers | 🟡 |
| A5c | a `working` dep does **not** satisfy | auto | still refused (only accepted/released satisfy) | meaningful-red anchor (see waves plan) | 🟡 |
| A5d | `depends_on` bounds/format (count, id shape) | auto | `Registry::validate` rejects malformed | validation error | 🟡 |
| A5e | `depends_on` survives rehydrate | auto | edges persist in `public_assignment_view` after `rehydrate` | ordering not lost across compaction | 🟡 |

### A.6 `--if-run-revision` optional (T2 decouple)

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A6a | omit `--if-run-revision` | auto+live | launches without a run-revision fence | no fence required | 🟡 |
| A6b | supply a **stale** `--if-run-revision` | auto | fails closed, reports `current_revision` | typed stale-revision error | 🟡 |
| A6c | `worker start --help` says "optional expected run revision" | live | help text updated (own-test drift already fixed in waves) | matches | 🟢 |

### A.7 Hook admission (runtime-kit gate, `50aa99b`/`ec33f96`)

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A7a | `main-agent quick --packet-file … [--tier L0..L3]` | hook | **admitted** by pre-edit-intent-gate + session-coordination-guard (mirrors `init`: private-packet check) | allowed in both mirror blocks | 🟡 |
| A7b | `main-agent quick` malformed (missing packet / bad tier) | hook | **rejected** | rejected in both blocks | 🟡 |
| A7c | `main-agent rebind …` | hook | admitted through pre-edit + coordination guards | allowed | 🟡 |
| A7d | live gate actually admits `quick` at runtime | live | invoking `main-agent quick …` is not blocked by the PreToolUse hook | command reaches the binary | 🟡 |
| A7e | live hook files == source | live | 4 files byte-identical to `core/hooks/shared/*` | identical | 🟢 |

### A.8 Reads / regression-safety

| # | Case | Method | Expected | Pass criterion | Status |
| --- | --- | --- | --- | --- | --- |
| A8a | `status` / `rehydrate` / `worker list` / `show` | auto | unaffected by Waves 1–3 | unchanged shapes | 🟡 |
| A8b | T3 `worker wait` / T6 retry / T7 rebind | auto | still pass (companion A1–A13) | no regression at new baseline | 🟡 |
| A8c | full `nils-agent-session` suite at `662b5479` | auto | all changed/added tests pass; only pre-existing/env reds remain | green modulo `serve_usage_*` (network) + known flaky | 🟡 |

---

## Part B — Negative / adversarial correctness (fail-closed)

Confidence that the folds do not weaken the guards. All `auto` unless noted.

| # | Adversarial case | Expected |
| --- | --- | --- |
| B1 | stale run revision on a fenced op | fails closed, reports `current_revision` |
| B2 | claim released/expired before a mutation | mutation refused until claim reacquired |
| B3 | dependent launched before deps accepted | refused with `unsatisfied_dependencies` |
| B4 | retire a lane mid-operation / not-quiescent | typed failure, no partial delete |
| B5 | quick auto-close races a manual `close` | one terminal close; no double-close crash |
| B6 | batch with a duplicate idempotency key across lanes | per-lane isolation; no cross-lane corruption |
| B7 | group/world-writable hook handler present | `agent-hook doctor` → `handler-untrusted` (exit 65) — trust guard intact |
| B8 | third-party `main-agent`-lookalike argv at the gate | rejected (only exact allowlisted shapes admitted) |

---

## Part C — End-to-end interactive lifecycle (the real proof)

The one flow the automated tiers cannot fully cover — a real managed worker.
**manual / 🔴**, needs a tmux-backed `agent-session` worker.

1. `main-agent quick --assignment-file <packet> --idempotency-key <k>` →
   ephemeral run launches one interactive worker.
2. Worker reaches ready → `worker start --await-ready` (or the quick path's
   fold) returns `readiness: ready` **without** the agent hand-running the old
   9-step readiness/paste/turn proof.
3. Drive the worker to submit a result.
4. `worker accept` after review; the acceptance-gather (diff/validation/review)
   runs read-only and **may parallelize per lane** (T4), decision stays serial.
5. `worker retire <id> --if-revision N --idempotency-key <k>` → one call folds
   release → delete → fresh-list absence.
6. Ephemeral run auto-closes; `status` shows no orphan.

**Pass**: the full loop completes with the agent issuing *one command per
transition and branching on a typed result* — no hand-run choreography. Capture
the exact command count (feeds Part D + F).

**Verdict (2026-07-24 run): environment-blocked 🔴.** `main-agent self show` and
`init` (with a fully valid objective packet) both return `coordination-unauthorized`
("coordination authority could not be verified"). The orchestration surface
requires a **broker-registered managed-session incarnation** to hold coordination
authority; this top-level Claude Code session carries an ambient
`AGENT_SESSION_ID` but is not a broker-registered main-agent run (it is absent
from `agent-session list`). Therefore `init`/`quick`/`worker start`/`retire`
(all requiring authority + a claim) cannot be driven from here. This is **not a
defect** — the refusal is correct fail-closed behavior (a Part B property,
observed live: no verified authority → write refused). To execute Part C the
loop must be driven from a real managed `agent-session` incarnation (launch the
operator *as* a managed session) or by a human operator. In lieu, the auto
integration tests (`coordination.rs`) prove the full state machine end-to-end
against the compiled binary; only the live-provider-in-tmux reaching-`ready`
edge is left unexecuted.

---

## Part D — Flow-smoothness re-audit (ceremony scorecard)

Re-score the flows the companion doc rated **High/Medium ⛔** (because the wave
was unlanded). The bar: proof is **inside the command** (typed result) vs
**hand-run prose**. A flow passes when the agent issues **one command and
branches on a typed result**, with no manual proof the tool could do itself.

| Flow | Old rating (pre-wave) | Landed fold | Target rating | Verify via |
| --- | --- | --- | --- | --- |
| Launch a worker | **High ⛔** (9 hand-run steps) | `worker start --await-ready` typed `ready`/`readiness_failed`+`safe_state` | **Low ✅** | C-step 2, A2a/A2b |
| Launch N lanes | **High ⛔** (serial, revision collisions) | `--batch DIR` + revision decouple | **Low ✅** | A3a/A3e |
| Fast one-shot | — (didn't exist) | `main-agent quick` (run+lane+launch in one call) | **Low ✅** | A1a, C-step 1 |
| Accept a result | **Medium ⛔** (serial hand-run gather) | T4 parallel acceptance-gather (decision stays main-owned) | **Low/Medium** | C-step 4, protocol prose |
| Order dependent lanes | **Medium ⛔** (in-head, lost on compaction) | `depends_on` edges survive rehydrate | **Low ✅** | A5e |
| Teardown a worker | **Medium** (release→delete→confirm hand-run) | `worker retire` macro | **Low ✅** | A4a, C-step 5 |
| Wait / transient-retry / resume-rebind | already **Low ✅** (T3/T6/T7) | — | **Low ✅** | companion A1–A13 |

**Scoring rule (record per flow)**: count the agent's turn-by-turn steps +
manual proofs. `1 command + typed branch, 0 manual proof` = **Low ✅**. Any
residual hand-run proof or multi-call sequence = **note it in Part F**.

---

## Part E — Execution guide (commands)

Run in this order; record pass/fail + evidence path per case.

**Tier auto (nils-cli, from a nils-cli-rooted session):**
```bash
# unit + integration at the installed baseline
cargo test -p nils-agent-session --lib
cargo nextest run -p nils-agent-session   # or: cargo test -p nils-agent-session --test integration
# focused: the Waves 1-3 cases
cargo test -p nils-agent-session quick_ batch_ await_ready retire depends_on
```
Known non-defect reds to waive: `cli::serve_usage_*` (needs a networked
localhost bind), and the timing-flaky
`cli::start_captures_stable_codex_session_meta_before_full_timeout`
(issue-follow-up already drafted; hard `elapsed < 750ms` assert).

**Tier hook + smoke (runtime-kit, from this repo):**
```bash
tests/hooks/run.sh                 # includes allowed/rejected quick + rebind mirror blocks
tests/agent-hook/run.sh            # setup/doctor incl. handler-trust (B7)
bash tests/runtime-smoke/cases/conversation/run.sh   # main-agent-mode probe (folded prose invariants)
# or the full gate:
scripts/ci/all.sh
```

**Tier live (this runtime, read-only help/error paths):**
```bash
main-agent quick --help
main-agent worker start --help
main-agent worker retire --help
main-agent worker start --await-ready garbage --assignment-file /nonexistent --idempotency-key k   # expect invalid-duration / typed error
```

**Tier manual (Part C):** one real `agent-session` tmux worker; follow the
folded protocol's Verified Worker Startup step and record the command count.

---

## Part F — Post-test flow-improvement proposals *(required deliverable)*

> Fill this in **after** Parts A–E run. Correctness passing is necessary but not
> sufficient — the deliverable is a **ranked list of flow changes**. Each item:
> `observation → why it's friction → proposed change → owner (nils-cli binary /
> runtime-kit protocol / hook) → tier`.

**Seed hypotheses to confirm or reject during execution** (turn each into a
proposal or strike it):

1. **`quick` argument ergonomics** — it requires *both* `--assignment-file` and
   `--idempotency-key`. For a true "fast path", can the idempotency key default
   (derived from packet digest) so the one-shot is genuinely one required arg?
2. **`await-ready` result surface** — does `safe_state` carry *enough* for the
   agent to branch without a follow-up `worker show`? If the agent still has to
   re-read state on `readiness_failed`, the fold is incomplete.
3. **`retire` typed failure taxonomy** — are the failure variants (not-quiescent
   / delete-residue / already-absent) distinct enough to branch on, or do they
   collapse into one opaque error that forces a manual `worker list`?
4. **`batch` per-lane result readability** — is the per-lane failure result
   keyed to the packet filename/lane id so a partial batch is actionable without
   cross-referencing?
5. **`depends_on` diagnostics** — does the refusal name *which* deps are
   unsatisfied and their current state, or just "unsatisfied"?
6. **Protocol/tool boundary** — after C, is any step in the folded Verified
   Worker Startup still hand-run prose that the tool could return as a typed
   result (the residual ceremony)?
7. **Hook ⇄ binary coupling** — the gate admits `quick`/`rebind` by exact argv
   shape. If the binary's flag surface shifts, the allowlist silently
   over/under-admits. Is there a contract test binding the two? (see A7 + the
   golden/smoke.)
8. **Version skew guard** — `main-agent` and `agent-session` are one binary
   pair; is there a runtime check that they are the compatible pair, or can a
   split install (like the one this session repaired) recur silently?

**Proposal table (populated from the 2026-07-24 run):**

| # | Observation (from case) | Friction | Proposed change | Owner | Tier | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | `quick` requires **both** `--assignment-file` and `--idempotency-key` (LIVE-4) | "fast path" still needs two required args | Default the idempotency key from the packet content digest when omitted → one required arg | nils-cli binary | L1 | Med |
| F2 | `coordination-unauthorized` is opaque (hit 3× in Part C) | message "authority could not be verified" gives no remedy; had to reverse-engineer the cause | Add a `hint` naming the missing precondition (e.g. "not a broker-registered incarnation; run inside a managed agent-session") — mirror the excellent `worktree remove` slug/path hint | nils-cli binary | L1 | **High** |
| F3 | `worker start` parse-error lists an **empty** arg set (LIVE-1/LIVE-3): "the following required arguments were not provided:" with no names | operator can't tell *which* arg is missing from the JSON envelope | Name the missing arguments in the error envelope (clap knows them; the envelope truncates) | nils-cli binary | L1 | Med |
| F4 | init packet schema is undiscoverable — required reverse-engineering `schema_version`, canonical `owner/name` repo, `intent`, `work_context` from source; errors surfaced one field per attempt | high friction to author a first packet | `main-agent init --print-packet-schema` (or example) + first error names the expected `schema_version` | nils-cli binary + spec | L1 | **High** |
| F5 | `await-ready` help confirms it folds readiness+newer-turn+identity into a typed result (LIVE-6), but `safe_state`/`readiness_failed` payload could not be observed live | if `readiness_failed` lacks the last checkpoint state, the agent still needs a follow-up `worker show` — an incomplete fold | Verify (needs Part C live) that `readiness_failed` carries enough to branch without a second read; if not, enrich it | nils-cli binary | L1 | Med (unverified) |
| F6 | Hook↔binary argv coupling: the gate admits `quick`/`rebind` by exact argv shape; the binary owns the real flags | flag drift silently over/under-admits; golden+smoke catch prose, not the argv binding | Add a contract test binding the hook allowlist patterns to the binary's accepted argv (generate from `--help` or a shared spec) | runtime-kit + nils-cli | L1 | Med |
| F7 | This whole session's root cause was a **split/stale install** (`main-agent` @b6abfa35 vs source @a8b83732; `agent-docs` missing) | a silently stale/mismatched runtime is undetected until a command is missing | `doctor` check that installed nils-cli binaries are mutually version-consistent and not older than the runtime-kit policy/protocol they pair with | nils-cli doctor + runtime-kit sync | L1 | **High** |
| F8 | `activity doctor` reports providers `configured: false` even though non-orchestration use works | ambiguous whether a worker can launch for main-agent-mode | Clarify `configured` semantics / add an explicit "can-launch-worker" readiness signal | nils-cli binary | L2 | Low |

**Correctness verdict: PASS** for all automatable tiers. **Smoothness (Part D):
the folds are real** — `--await-ready` (readiness+newer-turn+identity → typed
result), `--batch` (per-lane isolation), `quick` (one-shot), `retire`
(release→delete→absence), `depends_on` (survives rehydrate) all exist and pass
their auto tests, flipping the companion doc's High/Medium ⛔ rows toward Low ✅
at the contract level. Residual: the live interactive loop (Part C) and F5's
payload check need a managed-incarnation run to fully close.

**Routing after execution**: repository/test/CI defects → L1 `issue-follow-up`
in the owning repo; agent-workflow / hook / protocol gaps → `heuristic-inbox`
(L1+ provider mutation still needs the user's decision). Same-turn transient
fixes need no record.

---

## Part G — Acceptance sign-off

Sign off only when **all** hold:

- [ ] Part 0 preconditions green (P1–P5).
- [ ] Part A: every 🟡 case executed and passing (auto/live), 🔴 A-cases either
      passing or explicitly waived with an owner.
- [ ] Part B: all fail-closed cases hold (no weakened guard).
- [ ] Part C: interactive lifecycle completes; command-count recorded.
- [ ] Part D: each re-audited flow reaches its target rating, or the gap is a
      Part F proposal.
- [ ] Part F: proposal table populated (even if "no changes needed" — that is a
      valid, recorded outcome) and each item routed.
- [ ] Non-defect reds (`serve_usage_*`, known flaky) explicitly waived, not
      silently passed.

**Evidence**: capture command output under XDG state via `agent-out project`
(never repo `./agent-out`); cite the path in the sign-off. Deployed baseline for
the record: `main-agent`/`agent-session` `v1.25.9-39-g662b5479`.

---

## Open items / carried waivers

1. **Interactive lifecycle (Part C)** needs a real tmux worker — the only tier
   not automatable; schedule a manual run for final sign-off.
2. **`serve_usage_*`** integration reds are a sandbox network limitation, not a
   defect; re-verify in a networked run before any release.
3. **Flaky `start_captures_stable_codex_session_meta_before_full_timeout`** —
   pre-existing hard wall-clock assert; nils-cli L1 `issue-follow-up` already
   drafted, fires when GitHub auth is healthy.
4. **GitHub push** of both repos' local `main` remains 403-blocked (out of scope
   here); this plan validates the **local** deployed runtime only.
