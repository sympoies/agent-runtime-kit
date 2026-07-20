# Execution State: Separate nils-cli compatibility floor from validated pin

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-plan.md`
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/688>
- Current sprint: Sprint 3 consume the released version policy in runtime-kit
- Status: in progress; nils-cli v1.25.0 released and deployed, runtime-kit
  independent review findings repaired with focused green evidence
- Current gate: commit review repairs, rerun commit-bound full validation and
  affected specialist follow-up, then governed PR delivery and provider CI
- Current task: Task 3.4 review, deliver, merge, and verify runtime-kit
- Next task: Task 4.1 run post-merge acceptance and authorized activation
- Planned implementation branches: `feat/issue-688-version-policy` in nils-cli
  and `feat/issue-688-nils-cli-policy` in runtime-kit
- Plan-authoring branch: `feat/issue-688-nils-cli-policy` in runtime-kit
- Release prerequisite: explicitly authorized by the maintainer's active goal;
  choose and publish the exact version only through the release workflow
- Installed-surface activation: explicitly authorized for M4 sympoies after
  both repositories merge and release/read-back gates pass
- Blockers: none
- Last updated: 2026-07-19
- Branch/commit/PR: runtime-kit implementation branch
  `feat/issue-688-nils-cli-policy` at `10718eb`; nils-cli PR
  <https://github.com/sympoies/nils-cli/pull/1307> reviewed at final head
  `dff0624cd61a7eee0b4d0c2f6d4c373feda4e43d` and squash-merged to provider
  main as `7d9f7dfa9bf42948dd0beab564df241f3cb3614b`; release
  <https://github.com/sympoies/nils-cli/releases/tag/v1.25.0> published and
  fixed-fleet broker run 29703330495 succeeded

## Validation Plan

- Plan authoring: `plan-tooling validate`, `git diff --check`, committed bundle
  identity, visible tracking status, and provider issue read-back.
- Nils-cli: test-first meaningful red, focused schema/doctor/parser/snapshot
  coverage, affected suite, clippy/docs/completion checks, full repository gate,
  independent pre-merge review, and released-binary read-back.
- Runtime-kit: test-first meaningful red; version-policy scenario matrix;
  security/baseline/packaging audits; render/golden/skill governance; runtime
  smoke; `scripts/ci/all.sh`; `tests/hooks/run.sh`; independent pre-merge review;
  provider checks and merge read-back.
- Post-merge: admitted-ahead, exact-minimum, exact-validated, canary, and
  packaging identity probes; live apply only if separately authorized.
- Closeout: complete ledger, strict close-ready, closed issue audit, archive
  discovery/dry-run, optional authorized migration, and provider-proven local
  cleanup.

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | done | Commit the plan bundle and initialize the L2 tracker | Issue #688; visible source/plan/state/session lifecycle; plan validation, Markdown lint, and dirty-hash opening passed; signed runtime-kit plan commit ad62ec0afd0c from current origin/main; byte-identical provider snapshot hashes; plan-tooling, rumdl, and git diff checks passed | Governed clean-worktree recovery completed; old lease-blocked worktree preserved unchanged |
| 1.2 | done | Freeze schema-v2 behavior and capture nils-cli meaningful red | pending; tracker reconciled; clean nils-cli worktree and test-first record next; nils-cli baseline 09aafbe36059; feature contract and affected tests recorded; meaningful red exit 101 proved schema-v2 ahead-host admission absent; pre-edit check passed | Production edits admitted only after the recorded red |
| 2.1 | done | Implement manifest parsing, comparison, and typed diagnostics | pending; clean managed nils-cli branch feat/issue-688-version-policy at 09aafbe36059; nils-cli commit 1f5ab15421b9; schema-v1 exact and schema-v2 minimum/validated parsing; 16 focused integration cases; local-fast 439 package tests; full release gate 6921 nextest tests plus doctests; docs-impact and subject-bound test-first evidence verified | Strict stable tags, v1 compatibility, v2 range diagnostics, digest requirements, and duplicate-policy validation implemented |
| 2.2 | done | Review, deliver, merge, and release nils-cli capability | PR #1307; final head dff0624cd61a; squash merge 7d9f7dfa9bf4; release v1.25.0; request run 29703324928; broker run 29703330495; released agent-runtime 1.25.0 schema-v2 read-back 2 ok / 0 warn / 0 block; 14 native threads resolved; owner approval and five specialist no-findings passes; all provider checks green | Canonical two-stage release-and-deploy completed; fixed fleet converged |
| 3.1 | done | Capture runtime-kit meaningful red and migrate the manifest | released schema-v2 binary verified at v1.25.0; authoritative Linux release digests resolved; focused owner test failed meaningfully against schema-v1/exact-pin production state; schema-v2 manifest and eight focused owner tests green | Initial migration sets minimum and validated to v1.25.0 because older binaries cannot parse schema v2; later ordinary bumps move validated only |
| 3.2 | done | Add ambient, minimum, validated, and canary execution paths | de-duplicated exact-role matrix; 102-pass deterministic runtime-smoke with below-minimum, exact-role, admitted-ahead, and malformed-range cases; scheduled/manual latest-stable canary | Minimum and validated are blocking roles; equal tags share one physical lane while preserving both labels |
| 3.3 | done | Preserve validated packaging and update policy mirrors | Docker/publish inputs use validated tag and release digests; baseline 29/29; product-leak 234 files with 14 active allow entries; render/golden and docs mirrors green | Ordinary bump leaves minimum unchanged; `__pycache__/` is ignored to keep direct Python test runs from dirtying the checkout |
| 3.4 | in-progress | Review, deliver, merge, and verify runtime-kit | API/maintainability, testing, and security/red-team reviewed exact head 4ae3fba; five medium findings (one overlapping) repaired; focused policy 11/11, security audit, strict v1.25.0 digest execution, and deterministic smoke 102/0/1 green | Commit-bound full gate and affected follow-up review next; no live sync implied by merge alone |
| 4.1 | pending | Run post-merge acceptance and optional authorized activation | pending | Record explicit no-apply when activation is not approved |
| 4.2 | pending | Audit, close, archive, and clean local worktrees | pending | Strict close-ready and provider proof required |

## Validation Log

- 2026-07-19: Maintainer approved creating an L2 plan for the nils-cli pin
  redesign and explicitly deferred implementation to the next session.
- 2026-07-19: Project `project-dev` and `task-tools` intents were activated and
  required policy documents plus the plan-tracking, implementation-source, and
  project-version-baseline skills were read before authoring.
- 2026-07-19: Plan-archive search found the completed exact version-alignment
  plan and adoption history. Their silent-drift rationale is retained through
  exact validated/minimum CI and packaging roles rather than discarded.
- 2026-07-19: Live issue read-back found no duplicate tracker. #686 owns hook
  policy/break-glass and #676 owns session coordination; neither owns dependency
  version semantics.
- 2026-07-19: Ambient `agent-runtime 1.24.4` against manifest v1.24.3 reported
  16 ok, zero warn, one block, exit 2. All per-binary floors passed; only exact
  host equality blocked. Version baseline remained internally green at 24/24.
- 2026-07-19: A clean managed runtime-kit worktree and
  `feat/nils-cli-version-policy` branch were created from main
  `0bb5ab1229574268da61e43fc86e8c38e4876169`. No runtime, pin, product code,
  provider issue, release, or installed home had been mutated at that point.
- 2026-07-19: `plan-tooling validate`, `rumdl`, and `git diff --check` passed for
  the three-file bundle. The lease file for this exact checkout names the
  current Codex thread digest and expires after the configured eight-hour TTL,
  but Bash mutation still reports a foreign owner. `git add` was blocked before
  mutation, and dirty adoption is disabled in the launch environment.
- 2026-07-19: `plan-issue record open --dry-run --allow-dirty` accepted the
  bundle with immutable per-file `dirty-sha256` identities and privacy-clean
  provider payloads. This sanctioned fallback can establish the tracker while
  Task 1.1 remains in progress; it does not waive the pre-implementation commit.
- 2026-07-19: L2 tracker
  <https://github.com/graysurf/agent-runtime-kit/issues/688> opened with
  `state::blocked`. Run `20260719T175800Z-issue-688` selected Task 1.1;
  `tracking status --expect-visible` recognized source, plan, state, and session
  roles and returned `RECORD_BLOCKED` with the commit-admission blocker visible
  in the current session checkpoint.
- 2026-07-19: Final provider/base read-back found clean durable local main,
  `origin/main`, and provider `refs/heads/main` all at
  `5501aa05265add1516805f4346d3a11f218304a5`. This was an external advance
  during authoring; the managed plan worktree remains at its original clean base
  `0bb5ab1229574268da61e43fc86e8c38e4876169` plus the three untracked plan
  files. No attempt was made to rebase a dirty, lease-blocked worktree.
- 2026-07-19: Preserved the lease-blocked worktree unchanged and recreated the
  byte-identical three-file bundle in a clean managed worktree from current
  provider main. Validation and Markdown lint passed, and signed commit
  `ad62ec0afd0c4a15470a7a7b58f99565c801e1e6` completed Task 1.1 without
  deleting lease state or adopting the dirty checkout.
- 2026-07-19: The maintainer's active goal explicitly authorizes completing and
  releasing the plan and activating the result on M4 sympoies; release and live
  activation remain ordered after review, merge, and released-artifact proof.
- 2026-07-19: Task 1.2 test-first evidence bound nils-cli baseline
  `09aafbe36059`, recorded the v1/v2 contract and affected test owners, and
  captured meaningful red in
  `doctor_version_alignment::version_alignment_schema_v2_ahead_warns_without_blocking`.
  The focused test exited 101 because the exact-only parser required
  `pinned_tag`; the pre-edit check passed before production code changed.
- 2026-07-19: Task 2.1 implemented the frozen schema-v2 contract in signed
  nils-cli commit `1f5ab15421b96c01543fe6f4884514ec460863ba` while retaining schema-v1
  exact alignment. Sixteen focused doctor integration cases, the local-fast
  affected gate (439 package tests), and the full release-quality gate (6,921
  nextest tests plus doctests) passed. Docs-impact and delivery-bound
  test-first evidence both verified with no residual gaps.
- 2026-07-19: Nils-cli PR
  <https://github.com/sympoies/nils-cli/pull/1307> completed the governed review
  loop at exact head `dff0624cd61a7eee0b4d0c2f6d4c373feda4e43d`.
  Fourteen native review threads were answered and resolved; the final owner
  review approved, and testing, maintainability, API-contract, security, and
  red-team specialist follow-ups reported no findings. Linux, macOS, coverage,
  CodeQL, cargo-deny, and JUnit provider checks all passed.
- 2026-07-19: Provider read-back confirmed PR #1307 squash-merged at
  `2026-07-19T20:14:59Z` as main commit
  `7d9f7dfa9bf42948dd0beab564df241f3cb3614b`. Task 2.2 remains in progress
  solely for the canonical two-stage stable release and released-binary proof;
  the exact version is a required maintainer decision and was not inferred.
- 2026-07-19: The maintainer selected `v1.25.0` and separately authorized the
  exact `release-and-deploy` command after its non-mutating consent preview.
  Request run <https://github.com/serenvia/sympoies-infra/actions/runs/29703324928>
  and broker run
  <https://github.com/serenvia/sympoies-infra/actions/runs/29703330495>
  succeeded. The broker published
  <https://github.com/sympoies/nils-cli/releases/tag/v1.25.0> from approved
  source `7d9f7dfa9bf42948dd0beab564df241f3cb3614b` and completed fixed-fleet
  convergence.
- 2026-07-19: Installed released binary read-back reported
  `agent-runtime 1.25.0`. A schema-v2 policy with minimum `v1.24.3` and
  validated `v1.25.0` returned two ok, zero warnings, zero blocks, and exit 0.
  The public release is stable and exposes authoritative Linux tarball SHA256
  values `787c7978…d64223` (amd64) and `731a3549…f9227` (arm64).
- 2026-07-19: Runtime-kit focused owner test failed before production edits:
  the manifest remained schema v1, CI and packaging still read `pinned_tag`,
  and no latest-stable canary existed. Pre-implementation analysis also proved
  `v1.24.3` cannot be the executable schema-v2 minimum because that binary
  predates the parser. The initial migration therefore sets minimum and
  validated to `v1.25.0`, exercises equal-tag lane de-duplication, and leaves
  future ordinary release uptake to move validated only.
- 2026-07-19: Runtime-kit implementation commit `10718eb0d0b6` migrated the
  manifest to schema v2, added de-duplicated minimum/validated CI roles and an
  advisory latest-stable canary, kept Docker/publish bound to validated release
  digests, refreshed maintenance skills/docs/goldens, and added focused/runtime
  owner coverage. Full validation found and removed two legacy `1.24.3`
  test-string couplings so `agent-docs` and `git-cli` now follow the active
  exact CI lane.
- 2026-07-19: The final local gate passed all 17 `scripts/ci/all.sh` positions,
  including deterministic runtime-smoke 102 pass / 0 fail / 1 expected host
  skip, hooks 295/295, version baseline 29/29, and product-leak audit over 234
  files with 14 active exceptions. The standalone hook suite also passed
  295/295. Test-first evidence is delivery-bound with no residual gaps and
  docs-impact verifies against `origin/main`.
- 2026-07-19: Maintainer-requested Python cache hygiene added `__pycache__/` to
  `.gitignore`; a focused owner assertion and `git check-ignore --no-index`
  prove direct Python test runs no longer dirty the checkout.
- 2026-07-19: Independent review at exact head `4ae3fba503d2` found five
  medium items across three reports: blocking lanes did not verify downloaded
  archives or isolate provider tokens; canary selection trusted GitHub's
  mutable Latest designation and lacked an actionable failure summary;
  version admission ran after nils-cli-dependent plan validation; and the
  ahead-host smoke appended a synthetic sentinel without a deliberately
  incompatible downstream fixture. Testing and API reviewers independently
  identified the last gap.
- 2026-07-19: Reviewer-driven owner tests failed meaningfully before repair.
  The repair gives each exact CI role a manifest-owned SHA256, verifies and
  re-extracts cached release archives, removes provider tokens before executing
  downloaded bytes, makes admission Position 1, resolves the greatest strict
  non-draft/non-prerelease stable canary tag with a validated-floor freshness
  check, always publishes remediation, and propagates a controlled downstream
  incompatibility as exit 42. Focused policy tests passed 11/11, security audit
  and strict schema-v2 doctor passed, real v1.25.0 archive execution matched
  `787c7978…d64223`, and deterministic runtime smoke passed 102/0/1.
- 2026-07-19: Released v1.25.0 schema parsing correctly rejected an attempted
  unknown minimum-digest field. The retained minimum-lane identity therefore
  lives in strict separate manifest
  `docs/source/nils-cli-minimum-digest.yaml`; matrix and security audits require
  its tag to equal the schema-v2 policy's `minimum_supported_tag`.
- 2026-07-19: First focused follow-up cleared the original testing findings,
  then API/security review found two additional edge cases: the bump skill's
  rehearsal placeholder named Linux/amd64 even though the helper selects the
  current platform, and the bootstrap tag selector accepted noncanonical
  leading-zero/overflow versions that released doctor rejects. The repaired
  skill now requires the selected platform archive digest. The canary matrix
  and helper share canonical non-leading-zero u64 component bounds, with
  `v01.26.0` and overflow regressions; docs constrain this as the pre-download
  remote-canary bootstrap exception while doctor retains host-policy ordering.
  A final security edge-case follow-up also replaced Python Unicode `\d` with
  explicit ASCII digits after proving a full-width digit tag could otherwise
  displace the valid canary candidate; helper parity coverage also names the
  semver-suffix rejection path.

## Decision Log

- 2026-07-19: Selected a two-role manifest rather than a raw `>=` string:
  minimum governs admission, validated governs reproducibility.
- 2026-07-19: Selected above-validated warning plus continued downstream tests,
  not block and not silent success.
- 2026-07-19: Selected blocking minimum and validated CI roles plus an initially
  non-required scheduled/manual latest-stable canary.
- 2026-07-19: Kept schema-v1 manifests exact for backward compatibility.
- 2026-07-19: Kept Docker, checksums, release provenance, and generated snapshots
  bound to the validated tag.
- 2026-07-19: Kept the released schema-v2 policy strict; retained the independent
  minimum-lane archive digest in a runtime-kit-owned companion manifest and
  made ordinary validated uptake preserve it.
- 2026-07-19: Selected serial L2 rather than L3 because upstream implementation,
  release, and downstream consumption are hard dependencies.

## Session Notes

- Managed worktree identity:
  `agent-runtime-kit-228a9c3a/issue-688-nils-cli-policy`
  under the runtime-kit worktree root; omit the machine-local absolute prefix
  from provider-visible records.
- Current runtime-kit branch contains the complete schema-v2 consumption change
  plus repaired independent-review findings; commit-bound full validation and
  affected follow-up review remain before provider delivery.
- The existing exact-gate validation limitation is the subject of this plan; do
  not claim an ambient ahead host is formally validated.
- Do not rerun the prior #672 live runtime synchronization as part of this plan.

## Handoff

1. Read the discussion source, plan, and this execution state completely.
2. Run `plan-issue tracking status --expect-visible --format json` against the
   retained run state and reconcile the selected task.
3. Complete Tasks 3.1 through 3.4 test-first, including independent review,
   provider CI, merge, and provider-main read-back.
4. Run Task 4 acceptance and the explicitly authorized M4/sympoies activation,
   then close the tracker through the strict closeout gates.
