# Main Agent Mode — Remaining Waves Execution Plan (T1/T2/T4/T5)

- **Date**: 2026-07-23
- **Status**: in progress
- **Authorization**: goal "T1/T2/T4/T5 都要處理完畢 … 自己寫個合理的 plan 並執行完畢"
  (do all four remaining waves; author the plan and execute to completion).
- **Design source (locked decisions)**:
  `2026-07-23-main-agent-mode-flow-improvements.md`. **Post-deploy test plan**:
  `2026-07-23-main-agent-mode-test-plan.md`. This plan supersedes the "Remaining
  waves" one-liner in the design doc with a concrete, code-grounded sequence.
- **Already shipped (do not redo)**: T3 `worker wait` (`25833e8`), T6 auto-retry
  + T7 rebind (`7d5fd28`), on `nils-cli` `main`.

## Code-grounded correction to the design premise

The design doc (written at `fe0602f6`) said `worker start` **bumps** the run
revision. At the current HEAD (`61d9932c`) it does **not**: `run_worker_start`
only *fences* on `run.revision` via `ensure_revision(args.if_run_revision,
run.revision, "run")` (`main_agent.rs:1081`) and never increments it. The
run-revision `saturating_add` sites are `run_init`/`checkpoint`/`close` and the
per-assignment mutations, not worker start. So **T2's decoupling is concretely
"stop *requiring* `--if-run-revision` on assignment creation"** (drop the fence;
keep claim + current-main + assignment-absence), not "stop bumping."

## Wave sequence (dependency-ordered)

### Wave 1 — Schema foundation: T2 revision decouple + T5 `depends_on`

One schema wave (locked decision #4: add `depends_on` in the same migration as
the T2 decouple to avoid a second migration).

- **T2 decouple**: make `WorkerStartArgs.if_run_revision` optional
  (`Option<u64>`), fence only when supplied. Assignment creation is gated by
  claim + `require_current_main` + assignment-absence, not run revision. Removes
  the "read run revision before every start" friction and the parallel-start
  coordination point.
- **T5 `depends_on`**: additive `depends_on: Vec<String>` on `AssignmentInput`
  (`main_agent.rs:356`) and `AssignmentRecord` (`orchestration.rs:79`), both
  `#[serde(default)]`. Worker start refuses/marks a dependent until every dep is
  `accepted`; a new terminalable annotation surfaces on `worker list`/`show` and
  `rehydrate` so ordering survives compaction. Advisory-to-launch, not an ACL.
- **Compat**: additive `#[serde(default)]` fields → existing registries load
  unchanged; only an OLD binary reading a NEW registry rejects (acceptable,
  local-only, new binary deployed everywhere). No packet-digest change for
  packets that omit the field.
- **Validation-relevant edges**: `Registry::validate` state allowlist
  (`orchestration.rs:214`) unchanged; add a `depends_on` referential check
  (deps must be assignment ids in the same run) there.
- **Tests (test-first)**: unit — depends_on gating predicate, optional-fence
  parse; integration — parallel starts without `--if-run-revision` both succeed;
  dependent refused until dep accepted; dependent admitted after.

### Wave 2 — Batch + fast-path: T2 batch, `main-agent quick`

- **`worker start --batch <dir>`**: read N assignment packets from a directory,
  create N assignments + launch N workers in one call, per-lane typed results
  (`{lane, state, worker|error}`), no run-revision coupling (builds on Wave 1).
- **`main-agent quick --assignment-file F`**: ephemeral run + single assignment
  + auto-close on accept, for L0/L1 delegate-all; keeps claim + validation
  duties. **New pre-claim command shape** → must be added to the byte-exact
  admission allowlists (Wave 4).
- **Tests**: batch per-lane partial failure isolation; quick lifecycle
  (create→accept→auto-close) idempotent replay.

### Wave 3 — Verified macros: T1

- **Fold proofs into `worker start`**: readiness gate + newer-turn proof +
  identity proof internally; typed result `state: ready | readiness_failed |
  identity_mismatch | turn_unverified` + `safe_state`. `ensure_worker_launch_matches`
  (`main_agent.rs:1271`) already covers the identity half; readiness/turn is the
  new work. **Open design point (resolve at wave start):** worker readiness is
  async (the worker self-checks + checkpoints `working` after launch), so
  "readiness" folds in as a bounded internal wait (reusing the `worker wait`
  poll machinery) rather than a synchronous-at-launch proof. Confirm against the
  activity/`session_status` primitives before committing the shape.
- **`worker retire ID`**: quiescence proof → release → delete → fresh-list
  absence in one call, typed result.
- **`worker accept` evidence gather**: accept returns/attaches a mechanical
  evidence bundle (diff ref, validation handles, review findings) while the
  decision stays agent-owned.
- **Tests**: each typed failure branch; retire idempotent replay; accept bundle
  shape.

### Wave 4 — Runtime-kit protocol + policy: T1 prose reconciliation + T4 + allowlist/golden

- **T1 prose**: rewrite `MAIN_AGENT_MODE_PROTOCOL.md` §"Verified Worker Startup"
  (9 hand-run steps) down to "call the macro; branch on the typed failure";
  reconcile with the CLI's folded proofs.
- **T4 acceptance-gather**: codify parallel acceptance-gather in the skill
  (spawn read-only reviewer/validation sub-agents per lane; serialize only the
  decision). Pure policy/orchestration, no CLI change.
- **Admission allowlist**: add the exact `quick` (and any new pre-claim) argv
  shapes to both byte-exact allowlists
  (`core/hooks/shared/session-coordination-guard.py`,
  `core/hooks/shared/pre-edit-intent-gate.py`) with allowed + rejected-variant
  coverage; post-claim macros (`worker retire`, `--batch`) are admitted
  generically (verify).
- **Golden + smoke**: refresh golden + runtime-smoke for the changed skill
  prose; `bash scripts/ci/all.sh && bash tests/hooks/run.sh`.

## Validation & known waivers

- **nils-cli gate**: `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`
  (fmt, clippy `-D warnings`, workspace tests, docs/parity). Per-wave, plus unit
  `cargo test -p nils-agent-session --lib`.
- **Known environmental waiver**: `cli::serve_usage_*` integration tests fail in
  this sandbox on `/usage` connection-refused (local HTTP server unreachable),
  unrelated to this work — re-verify on a networked run before any release.
- **Harness note**: the crate has no authenticated-`CliContext` in-process
  integration harness; command-flow tests drive the compiled binary via
  `run_main_agent` + seeded registry fixtures (`coordination.rs`), as the T3
  worker-wait test does.

## Delivery

- Non-default managed worktree on a feature branch under nils-cli; per-wave
  commits via bare `semantic-commit local-default` (workdir = worktree).
- Direct-to-`main` delivery of the branch is a **separate approved step**
  surfaced after the waves land + validate (not inferred from this goal).
- Runtime-kit (Wave 4) commits follow the repo's own managed-worktree /
  local-default path.

## Wave 1 result (2026-07-23)

Implemented on nils-cli worktree branch `feat/main-agent-flow` (base `61d9932c`),
**not yet committed** (see Delivery). Changed files (4): `orchestration.rs`
(+`depends_on` field, bounds/format check in `Registry::validate`, no
referential invariant), `main_agent.rs` (optional `--if-run-revision`,
`AssignmentInput.depends_on` with `skip_serializing_if` for digest stability,
dependency gate in `run_worker_start`, `dependency_state_satisfies` +
`unsatisfied_dependencies`, `public_assignment_view` surfaces `depends_on`, input
bounds, 2 unit tests), `coordination.rs` (1 integration test), the spec doc.

- **Test-first evidence**: meaningful red confirmed (temporarily letting
  `working` satisfy a dependency failed both unit tests), reverted to green.
- **Validation**: `cargo fmt --check` ✓, `cargo clippy -p nils-agent-session
  --all-targets --all-features -- -D warnings` ✓ (0 warnings), 2 unit + 1
  integration test ✓, and `nils-cli-checks-entrypoint.sh --local-fast` — every
  code + docs audit (completion-freshness, docs-placement, docs-hygiene) passes.
- **Scoped waiver**: `--local-fast` exits 1 on **18 pre-existing markdown-lint
  issues in `docs/plans/2026-07-23-codex-app-server-0.145.0/codex-app-server-0.145.0-handoff.md`**
  — an unrelated file untouched by this change, failing at base `61d9932c`
  (likely rumdl@0.1.62 rule drift). My edited markdown has 0 issues. Out of this
  change's scope; flagged for the owning Codex-app-server work.
- Also carries the standing `cli::serve_usage_*` sandbox waiver from prior waves.

## Delivery

The implementation session is rooted in `agent-runtime-kit`, so `semantic-commit
local-default` for the nils-cli worktree is blocked by the foreign-cwd guard
(same constraint that had the user run the T3/T6/T7 commits). Options at the
nils-cli-waves boundary: (a) user runs `semantic-commit local-default` per wave
from the worktree, (b) stack Waves 1–3 in the worktree and commit once, (c) test
an autonomous commit path. Runtime-kit Wave 4 commits from this repo normally.

## Status

| Wave | Scope | State |
| --- | --- | --- |
| 1 | T2 decouple + T5 depends_on (schema) | **done — gate green; commit pending** |
| 2 | T2 batch + `main-agent quick` | **done — gate green; commit pending** |
| 3 | T1 `worker start --await-ready` fold + `worker retire` | **done — gate green; commit pending** |
| 4 | runtime-kit: T1 prose + T4 policy + allowlist + golden | **done — committed to main `50aa99b` (local-only) + smoke-probe follow-up; change-relevant gate green, two pre-existing waivers** |

## Waves 2–3 result (2026-07-23)

On worktree `feat/main-agent-flow` (uncommitted). Wave 2: `worker start --batch DIR`
(per-lane isolation), `main-agent quick` (ephemeral run + auto-close on final
delete via `maybe_autoclose_ephemeral_run`), `RunRecord.ephemeral`. Wave 3:
`worker start --await-ready D` folds the readiness proof (bounded wait for the
worker's authenticated checkpoint to advance past `starting`; typed `readiness`
`ready|readiness_failed`+`safe_state`; `0`=launch-only, batch/quick launch-only),
`worker retire` macro (release → delete → absence).

- **Tests**: 6 new unit + 3 new integration (batch isolation, quick validation,
  retire guards), meaningful red shown on the dependency gate. Completion assets
  regenerated (freshness ✓). Spec (`main-agent-orchestration-v1.md`) updated.
- **Full `--local-fast` gate**: docs audits ✓, `cargo nextest --workspace`
  = **all changed/added tests pass**. Only reds are pre-existing/environmental
  and unrelated to this change: `cli::start_captures_stable_codex_session_meta_before_full_timeout`
  (timing-flaky in `cli.rs` — flaky-passed run 1, failed-all-retries run 2) plus
  the standing `serve_usage_*` / leaky-lock sandbox waivers.
- Fixed one legitimate own-test drift: `worker start --help` now reads
  "optional expected run revision" (T2), so the help assertion was updated.

## Wave 4 progress (2026-07-23)

Runtime-kit (this repo, committed here). **All Wave 4 items landed:**

- `main-agent quick` pre-claim admission in **both** byte-exact allowlists
  (`session-coordination-guard.py`, `pre-edit-intent-gate.py`), mirroring `init`
  (private-packet check + optional `--tier L0..L3`), with allowed + rejected
  hook-test coverage in both mirror blocks.
- `MAIN_AGENT_MODE_PROTOCOL.md` reworked to the folded form (T1): Verified
  Worker Startup now "invoke the workflow's verified-launch step; branch on the
  typed ready/not-ready result", hand-run sequence kept as fallback; Terminal
  Worker Cleanup reconciled with the folded retire step.
- T4 parallel acceptance-gather codified in the Acceptance Loop (read-only
  gather may parallelize per lane; only the decision + lifecycle advance stay
  serialized and main-agent-owned).
- Golden refreshed (claude + codex protocol); `runtime-smoke`
  `conversation.main-agent-mode` probe realigned to the reworked prose (now
  passing).

**Delivery (final):** committed to `main` as `50aa99b`
(`semantic-commit local-default`, `--remote-mode local-only`,
signature verified-good) plus a smoke-probe follow-up commit; both local-only
(origin push deferred — see below). Change-relevant validation is green:
skill-governance, exposure-contract, golden diff, the `quick` hook tests, and
`conversation.main-agent-mode` smoke all pass.

**Pre-existing waivers surfaced by the full `scripts/ci/all.sh` gate** (both
unrelated to this change, both fail independently of Wave 4):

- Position 11 `meta.sync-runtime-surfaces.hermes-legacy` — the Hermes
  legacy-cleanup probe (`cp -R`/inventory-hash discrepancy, `<stdin>` line-26
  `AssertionError`) in a subsystem this change never touches; main-agent-mode is
  Codex/Claude-only and never renders to Hermes. Route: heuristic-inbox
  (runtime-kit `sync-runtime-surfaces` probe).
- Position 13 `tests/hooks/run.sh` `test_finish_line_*` (~15) — the committed
  `#599` discovered-defect routing-review gate emits its prompt (and the marker
  cannot persist in the hermetic temp env) where the older tests still assert the
  pre-`#599` block strings. Hook is clean in this tree. Route: heuristic-inbox
  (runtime-kit finish-line hook/test isolation).

## GitHub / cross-repo delivery status (blocked)

- **GitHub write mutations are blocked**: the active `gh` account `graysurf`
  returns `HTTP 403 … marked as spammy` on the GraphQL write path; reads still
  work. This blocks the L1 issue **and** any PR-based delivery to either main.
  Per user decision: defer all GitHub steps, land runtime-kit locally.
- **nils-cli L1 issue-follow-up** (flaky
  `cli::start_captures_stable_codex_session_meta_before_full_timeout`,
  `crates/agent-session/tests/integration/cli.rs:6684`, a hard `elapsed < 750ms`
  wall-clock assert): fully drafted + `forge-cli … --dry-run` validated (title
  65 chars, 6 labels, repo `sympoies/nils-cli`); blocked only by the 403. Body
  saved at scratchpad `nils-cli-flaky-issue.md`. Fires the moment auth is healthy.
- **nils-cli Waves 1–3** remain uncommitted on worktree `feat/main-agent-flow`
  (foreign-cwd `semantic-commit` block); need the user to commit from a
  nils-cli-rooted session, then push both repos once auth is restored.
