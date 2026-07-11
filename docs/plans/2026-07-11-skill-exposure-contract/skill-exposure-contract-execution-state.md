# Execution State: Implement the Intent-Level Skill Exposure Contract

## Execution State

- Source document: docs/plans/2026-07-11-skill-exposure-contract/skill-exposure-contract-discussion-source.md
- Plan document: docs/plans/2026-07-11-skill-exposure-contract/skill-exposure-contract-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/563>
- Current sprint: Sprint 4
- Status: in-progress
- Current task: 4.3
- Next task: complete final provider sweeps, merge PR #565, then run strict tracker closeout
- Branch: feat/skill-exposure-contract
- PR: https://github.com/graysurf/agent-runtime-kit/pull/565
- Last updated: 2026-07-11

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Open and initialize the runtime-kit plan tracker | done | pending; tracker #563; source/plan/state audit visible-clean | Plan bundle committed; tracker opened and run state reconciled |
| 1.2 | Open the linked nils-cli follow-up | done | sympoies/nils-cli#1110 | Public-safe deterministic primitive issue opened and read back |
| 2.1 | Capture failing parser and contract tests | done | nils-cli test-first record; runtime-kit test-first record | Both implementations started from observed contract failures |
| 2.2 | Add per-manifest versioning and typed v2 validation | done | sympoies/nils-cli#1111; commits 88d0faab, e9110b5d | Skills v1/v2 coexist; public error compatibility preserved |
| 2.3 | Add deterministic metadata reporting and compatibility coverage | done | sympoies/nils-cli#1111; commit 767818ab | Current Codex/Claude/Hermes layouts report all 66 skills |
| 2.4 | Validate, review, deliver, and release nils-cli | done | PR #1111; release PR #1113; v1.21.15; release run 29147306800 | Local-fast 419/419, provider CI, specialist review, release artifacts, tap update, and local Homebrew install passed |
| 3.1 | Add runtime-kit v2 and disposition schemas | done | commits 801788a, 2af4f82 | No hidden internal or fake opt-in shape |
| 3.2 | Migrate live manifests and seed the #562 ledger | done | commits 801788a, b3082e7 | 66 ordered pending IDs and rows are count- and digest-frozen |
| 3.3 | Enforce retained-skill admission and migration integrity | done | commits 801788a, 2af4f82, b3082e7 | Retained, advanced, opt-in, compatibility, calendar bound, growth, and replacement paths covered |
| 3.4 | Refresh product diagnostics, docs, renders, and goldens | done | released v1.21.15; three-product contract test; surface snapshot and golden refresh | Exact pin, release SHA256, CLI floor, and product surface floors updated |
| 4.1 | Run declared validation | done | `bash scripts/ci/all.sh`; test-first evidence verified | Positions 1-15 passed on released v1.21.15; shared hook contract 97/97 |
| 4.2 | Run mandatory specialist review and converge findings | done | PR #565 native reviews; outcome review 4677447098 | One API-contract major fixed in 869e7d3; follow-ups pass; thread resolved; testing, maintainability, data-migration, and red-team complete |
| 4.3 | Merge, close the tracker, and complete #561 | in-progress | PR #565 checks pass; threads=0; tasks=0 | Final head sweep, merge, strict close-ready, and canonical closeout remain |
| 4.4 | Reassess #562 against the landed contract | pending | pending | Final handoff decision |

## Blockers

- None.

## Validation

| Command | Status | Evidence |
| --- | --- | --- |
| `plan-tooling validate --file docs/plans/2026-07-11-skill-exposure-contract/skill-exposure-contract-plan.md --format text --explain` | pass | Position 1 of `bash scripts/ci/all.sh` |
| `bash scripts/ci/all.sh` | pass | positions 1-15 OK on released nils-cli v1.21.15 |
| `bash tests/hooks/run.sh` | pass | 97 tests passed in 23.766s |

## Session Log

- 2026-07-11: #561 was refined against #562. Filesystem-based discovery proved
  that a portable installed-but-hidden skill class does not exist. The L2 plan
  chooses an honest default-only active exposure contract, a frozen pending
  baseline for #562, and a released nils-cli v2 parser dependency.
- 2026-07-11: Opened tracker #563 and linked nils-cli issue #1110. The upstream
  worktree starts from current `origin/main`; unrelated dirty work in the
  primary nils-cli checkout remains untouched.
- 2026-07-11: Downstream test-first consumption found that nils-cli fixtures
  modeled older Codex and Hermes paths. PR #1111 now covers the current Codex
  plugin and Hermes external-skill layouts while preserving old source roots.
- 2026-07-11: Runtime-kit schema v2, the 66-row #562 ledger, admission
  governance, lifecycle fixtures, product diagnostics, and contract docs are
  implemented locally. Final validation waits for the released nils-cli pin.
- 2026-07-11: nils-cli PR #1111 and release PR #1113 merged. Release v1.21.15,
  four-platform artifacts, Homebrew tap update, and local host upgrade passed.
  Runtime-kit now pins the released parser, artifact checksums, and the exact
  product skill-render floors that consume skills manifest v2.
- 2026-07-11: Final runtime-kit validation passed all 15 CI positions on the
  released host, including 89 deterministic runtime-smoke cases (88 pass, one
  host-capability skip), 97 shared hook tests, 21 version mirrors, and product
  leakage audit. The test-first record now verifies complete.
- 2026-07-11: PR #565 completed the mandatory testing, maintainability,
  api-contract, data-migration, and red-team reviews. One major disposition
  schema/parser gap was fixed in 869e7d3 with fail-first block-list evidence and
  enum/boolean/list/unknown-field coverage; affected follow-ups passed and the
  native thread was resolved. Combined outcome is proceed-to-merge.
