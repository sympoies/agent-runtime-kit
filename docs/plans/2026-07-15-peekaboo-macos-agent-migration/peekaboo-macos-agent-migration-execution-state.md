# Execution State: Replace the macOS automation engine with pinned Peekaboo

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-07-15-peekaboo-macos-agent-migration/peekaboo-macos-agent-migration-plan.md`
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/610>
- Current sprint: Sprint 5 activation and closeout on released nils-cli v1.22.7
- Status: complete at the plan-task boundary; implementation, release,
  fixed-fleet deployment, governed runtime-kit pin, managed-surface
  synchronization, live functional acceptance, recovery readiness, evidence
  review, defect routing, and strict tracker close-ready all passed
- Current gate: merge this final ledger update, then atomically write the
  provider closeout, verify its read-back, route the archive, and perform
  terminal worktree cleanup
- Current task: none; Tasks 1.1 through 5.2 are complete
- Next task: L2 tracker closeout and archive handoff
- Plan branches: `feat/peekaboo-macos-agent-adapter` (nils-cli), then `feat/peekaboo-macos-agent-cutover` (runtime-kit)
- Upstream candidate: Peekaboo `v3.9.3`, verified tag commit
  `3cfd612adbcb1b43e8431a7a1f3b02ec45d01269`; newly released v3.9.4 was
  freshness-reviewed and is not adopted for this delivery because the already
  reviewed v3.9.3 exact tuple remains the controlled candidate
- Release prerequisite: satisfied by nils-cli v1.22.7 release and fixed-fleet
  deploy verification
- Blockers: none at the implementation or active-GUI acceptance boundary. The
  v3.9.3 CLI notary failure is an approved exact-artifact waiver. Peekaboo's
  displayless element-ID snapshot rejection is an accepted environment-limited
  residual; it does not block the proven observed-coordinate fallback or the
  guarded no-replay contract.
- Last updated: 2026-07-16
- Branch/commit/PR: nils-cli PR
  <https://github.com/sympoies/nils-cli/pull/1234> merged signed head
  `75cc7d23b86e787b4582c027f1d99f39242fe8fb` through squash commit
  `2e55e376306f8d69894576c0a3ee9a844a115efd`; exact-head local/provider gates,
  testing follow-up, approval, and zero unresolved review threads passed, and
  the source branch was deleted; follow-up PR
  <https://github.com/sympoies/nils-cli/pull/1245> merged as `01e1993`; follow-up
  release <https://github.com/sympoies/nils-cli/releases/tag/v1.22.7> was cut
  from approved source `a75455c9`, and broker run
  <https://github.com/serenvia/sympoies-infra/actions/runs/29473807996>
  verified nils-cli 1.22.7 on the fixed fleet. Runtime-kit PR
  <https://github.com/graysurf/agent-runtime-kit/pull/630> merged as `ff0c975`
  with the exact v1.22.7 pin and refreshed surfaces; acceptance-contract PR
  <https://github.com/graysurf/agent-runtime-kit/pull/633> merged as `4fcd298`
  after current-head CI, API-contract, maintainability, testing, and native
  approval gates passed

## Validation Plan

- Per task: update this ledger with command/evidence paths, pass/fail/waiver,
  provider links, and residual gaps before advancing.
- Nils-cli deterministic floor: focused crate tests, completion/docs audits, and
  `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`.
- Nils-cli live floor: locked provenance; strict doctor; local/SSH capability
  matrix; journal/redaction/replay/MCP; stability and rollback.
- Runtime-kit floor: focused computer-use smoke, render/golden/install/prune,
  `bash scripts/ci/all.sh`, and `bash tests/hooks/run.sh` on the released pin.
- Delivery floor: verified test-first/docs-impact evidence, provider checks,
  specialist reviews, zero unresolved review threads/tasks, and merged PRs.
- Activation floor: merged-revision read-back, fresh product sessions, private
  privacy-minimized journals, significant-defect review, and rollback dry-run.

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | done | Review and freeze the Peekaboo candidate | Peekaboo v3.9.3 tag/commit, asset SHA256, architecture, signer, license, advisory, and archive review frozen | Candidate provenance frozen; live signer/notary confirmation continues in Task 3.2 |
| 1.2 | done | Declare test impacts and capture meaningful red | nils-cli and runtime-kit test-first v2 records bound to immutable baselines with meaningful red | Runtime-kit helper and routing red captured before any cutover production edit |
| 2.1 | done | Implement backend install, verification, doctor, and rollback | Backend lifecycle and strict failure-injection tests pass | Idempotent install, recovery, dry-run, ownership, strict verification, and verified rollback implemented |
| 2.2 | done | Implement local/SSH exec, scenario transport, and artifacts | Local/SSH transport, scenario, artifact, timeout, signal, and cleanup tests pass | Versioned stdin protocol; no shell interpolation; remote cleanup failure retained |
| 2.3 | done | Implement journal, redaction, guarded replay, and review | Journal v2, redaction, partial-tail, concurrency, permission, review, and guarded replay tests pass | Structural evidence is redacted before persistence |
| 2.4 | done | Implement stdio MCP/tool profiles and retire the old engine | MCP local/SSH profile tests, completion/docs audits, notices regeneration, and source inventory pass | Old UI engine source and private tests removed |
| 3.1 | done | Run deterministic, security, and release-readiness validation | Exact signed integration head `75cc7d23` passes all-feature clippy, 6187 nextest cases, doctests, docs, completions, third-party audits, and verified test-first/docs-impact records | Exact-waiver policy is machine-readable; reduced posture is visible; all unrelated trust gates remain hard |
| 3.2 | done | Run the private macOS capability and journal canary | Exact branch binary passes local and adapter-SSH launch/observe/click/type/postcondition, three no-retry runs, journal redaction/privacy scan, guarded never-replay refusal, and rollback to official 1.22.5 | Active-GUI contract accepted. With private Mac `display_count=0`, pinned snapshot element-ID clicks remain an explicit non-blocking residual; fresh observed global-coordinate fallback passed |
| 3.3 | done | Review, merge, release, and verify nils-cli | nils-cli PR #1234 merged as `2e55e376`; latest-main integration, 6187-case full local gate, exact-head provider CI, testing follow-up, approval, and zero unresolved threads pass; nils-cli v1.22.6 released from 01e1993 and fixed-fleet deploy verified by broker run 29465243199 | PR #1234 and prior-root follow-up PR #1245 are included in release tag v1.22.6; MacBook and sympoies both verified on 1.22.6 |
| 4.1 | done | Replace the computer-use skill and publish the capability matrix | Direct-adapter skill, setup, canonical capability matrix, helper removal, and new test-first red→2/2 focused green plus 37-skill matrix gate are implemented on the managed cutover branch; released v1.22.6 focused deterministic computer-use 2/2 and acceptance matrix 37 skills pass | Direct-adapter source and all Codex/Claude/Hermes goldens are on the released binary; Linux live GUI probes remain host-inapplicable by contract |
| 4.2 | done | Apply the governed nils-cli pin and deliver the cutover PR | Runtime-kit PR #621 merged as `0c3919f` with the cutover, CLI floors, and Codex/Claude/Hermes goldens; follow-up PR #630 merged as `ff0c975` with the exact v1.22.7 pin, digests, README/harness/surface mirrors, Docker fallback, and exact-version fixture; local CI positions 1-16 and current-head provider checks 4/4 pass | Independent testing and maintainability reviews pass after one stale release-wording repair; transient checkout-lease race CI failure was isolated, rerun green, and routed to ready follow-up issue #632 |
| 5.1 | done | Synchronize the runtime and run fresh-agent acceptance | Merged `main` synchronized to Codex, Claude, and Hermes with prune/doctor/prompt-input checks; strict backend verify, doctor, and capabilities pass through the private SSH transport; Calculator clear action succeeds and AX inspection observes display value `0` | Fresh install has no previous receipt: rollback dry-run deterministically refuses with exit 69 and a subsequent status read-back preserves Peekaboo v3.9.3 commit `3cfd612a` |
| 5.2 | done | Review retained evidence and close the L2 tracker | Required journals summarize cleanly; successful steps have no review candidates, the fail-closed selector mistake is non-significant, remote replay is correctly ineligible, PR #633 clarifies both recovery branches, issue #632 owns the only reproducible CI defect, and strict `tracking close-ready --expect-visible` returns `ready=true` with no blockers | Raw desktop evidence remains private. The exact-artifact notary/reduced-security waiver and displayless element-ID limitation remain disclosed non-blocking residuals; no privacy, wrong-target, false-success, or usability blocker remains. Provider `record close`, read-back, archive routing, and cleanup are the workflow finalizers after this ledger PR merges |

## Validation Log

- 2026-07-15: `plan-tooling validate` accepted the three-file bundle with 13
  tasks and no errors; `git diff --check` passed.
- 2026-07-15: On pinned nils-cli `v1.21.39`, `scripts/ci/all.sh` positions 1-7
  passed: plan/governance, version alignment, all product renders, support
  matrix, goldens, drift fixtures, and security hardening. Position 8 reached
  convergence acceptance and stopped only because that harness requires a
  committed clean source, while this plan-only authoring turn intentionally
  leaves the new bundle uncommitted. No clean-tree bypass or temporary commit
  was used.
- 2026-07-15: The remaining independently runnable on-pin gates passed:
  skill-surface doctor 21/21, sandbox install, deterministic runtime smoke
  99 pass / 1 declared host-capability skip / 0 fail, project-local smoke,
  hooks 178/178, version baseline 21/21, product leak audit, and memory-runtime
  policy/audit. The sole validation waiver is the clean-source convergence
  execution in position 8; it must run without waiver when the plan bundle is
  committed through the L2 delivery workflow.
- 2026-07-15: GitHub Actions run
  <https://github.com/graysurf/agent-runtime-kit/actions/runs/29405300885>
  exposed three clean-checkout `location-directory-missing` errors because
  Task 4.2 listed ignored generated build directories. PR
  <https://github.com/graysurf/agent-runtime-kit/pull/609> removed those
  invalid locations while retaining product rendering as required validation.
- 2026-07-15: On the committed repair and pinned nils-cli `v1.22.3`,
  `plan-tooling validate`, all 16 `scripts/ci/all.sh` positions, hooks
  178/178, required provider checks, CodeQL, testing review, and maintainability
  review passed. The prior clean-source convergence waiver is resolved.
- 2026-07-15: The nils-cli adapter's full deterministic floor passed: focused
  crate tests, affected clippy, all-feature workspace clippy, 6071 nextest
  cases, doctests, completions, docs, third-party audits, and the complete
  `--local-fast` entrypoint.
- 2026-07-15: Isolated live macOS verification matched both locked v3.9.3
  asset digests, architectures, and exact signing identities. Peekaboo.app was
  accepted as `Notarized Developer ID`; the official standalone CLI failed
  `codesign -R=notarized --check-notarization`. v3.9.3 remains latest and no
  existing upstream notarization issue or PR was found. Task 3.2 therefore
  remains blocked without a waiver.
- 2026-07-15: Upstream `main` at `18768aef` is preparing v3.9.4 but retains the
  defect: `scripts/release-binaries.sh` verifies the CLI signature and packages
  it into tar/npm outputs without a `notarytool` submission or notarization
  release gate. The app path separately submits a ZIP, staples its ticket, and
  verifies Gatekeeper. A deduplicated, provider-payload-validated upstream bug
  report is ready for explicit authorization.
- 2026-07-15: Draft nils-cli PR
  <https://github.com/sympoies/nils-cli/pull/1234> reached signed head
  `74a28ab97198aa3c625c34eba1b63b84327e09ac`. CI exposed and drove fixes for
  a macOS Bash fractional-timeout fixture, a redaction-canary collision, BSD
  `stat` portability, and five missing journal completion descriptions.
  Focused tests, 41 library + 1 binary + 42 integration tests, affected clippy,
  completion flag parity 47/47, repeated 6119-case pre-PR gates, and focused
  testing reviews all pass.
- 2026-07-15: Provider run
  <https://github.com/sympoies/nils-cli/actions/runs/29427715645> passes Linux,
  macOS, coverage, cargo-deny, CodeQL, and JUnit checks. `forge-cli pr deliver
  --no-merge` adopted the draft and reported all required checks successful;
  `state::do-not-merge` remains applied.
- 2026-07-15: Security and maintainability follow-up found that daemon
  retirement was deferred beyond the last immutable ownership proof and that
  rollback used an unverified mutable current receipt before cleanup. Focused
  red tests reproduced both defects. Transition-time retirement now verifies
  the outgoing receipt and exact CLI first, derives runtime identity from the
  locked digest, and fails before process or state mutation on tampering.
- 2026-07-15: The branch was rebased onto nils-cli v1.22.5. All nine adapter
  commits retain good GPG signatures. The final package suite passes 47 library,
  1 binary, and 51 integration tests; release-mode isolation, affected clippy,
  third-party audits, and the complete 6134-case `--local-fast` gate pass. The
  v2 test-first and docs-impact records verify against signed head `3e57a131`.
- 2026-07-15: SSH reachability to the private Mac is restored. Strict
  `macos-agent 1.22.3` preflight reports zero blockers or warnings and its
  Screen Recording, Accessibility, Automation, activation, input, and
  screenshot probes pass. A fresh v3.9.3 canary again matches both locked
  digests and the signer, but the standalone CLI still fails Apple's
  command-line notarization requirement. Runner availability is no longer a
  blocker; Task 3.2 remains blocked only on the official CLI artifact.
- 2026-07-15: Exact-head API and performance review drove bounded outstanding
  MCP state, correlated resource-limit responses, rollback dry-run parity,
  migration guidance, journal rotation, and timeout cleanup repairs. Final
  owner coverage independently reaches the 64 KiB metadata limit and the
  correlated 17th-request count limit.
- 2026-07-15: Red-team and security review drove full stable-app bundle
  verification before rollback/recovery finalization, a concurrency-safe
  16-root SSH session bound, and explicit cleanup uncertainty on every SSH MCP
  early-return path. A package-gate scheduling failure also exposed that the
  eight-slot writer queue could race the reviewed 16-request pending cap; the
  capacities are now coupled, and all 59 integration tests pass in five
  consecutive parallel-suite runs.
- 2026-07-15: Final signed nils-cli head
  `85ddf927d2b4a7e7bff6db4b3a21636840d2e4cb` passes 49 library, 2 binary, and
  59 integration tests, affected clippy, release-mode test isolation, and the
  complete 6145-case `--local-fast` workspace gate. Test-first v2 and
  docs-impact evidence verify against the exact head; exact-head API,
  performance, security, and red-team reviews report no actionable findings.
- 2026-07-15: Final provider run
  <https://github.com/sympoies/nils-cli/actions/runs/29441312873> passes Linux,
  macOS, coverage, cargo-deny, CodeQL, and both JUnit reports. All 27 review
  threads now contain closure notes and are resolved. PR #1234 remains draft,
  mergeable, `risk::high`, and `state::do-not-merge` solely because Task 3.2's
  official CLI notarization and live acceptance gate remains unwaived.
- 2026-07-15: Peekaboo v3.9.4 was published after the final PR gate, so Task
  1.1 freshness was re-evaluated immediately. On the private Mac, official
  archive digests match, the extracted universal CLI reports 3.9.4 and has a
  valid Developer ID signature, but the notarization requirement still fails
  with exit 3. The app passes strict signature, notarization, and Gatekeeper
  checks but changes signer to `OpenClaw Foundation (FWJYW4S8P8)`. v3.9.4 is
  therefore rejected as a lock update: it does not remove the blocker and
  would expand the trust set without enabling live acceptance.
- 2026-07-15: The maintainer reviewed the blocker as a distribution-assurance
  gap rather than evidence of a functional defect and approved a narrowly
  scoped v3.9.3 CLI notarization waiver. Task 3.1 is reopened: the waiver must
  be machine-readable and repeat the exact repository/tag/commit/archive and
  executable digests/signer/Team ID, strict output must expose `waived` and
  reduced posture, app notarization and every other trust check stay hard, and
  real production-path usability remains mandatory in Task 3.2. No fork is
  introduced.
- 2026-07-15: The exact waiver implementation now fails closed on timeout and
  any tuple drift, reports the reduced security posture through install,
  status, verify, and rollback, and retains hard signature, app Gatekeeper,
  and non-waived notarization failures. Exact-head security and red-team review
  report no findings.
- 2026-07-15: Private Mac acceptance installed the exact PR binary and exercised
  Calculator through fresh AX observation, an observed global-coordinate click,
  background typing, and explicit `0` then `3` postconditions. Three local runs
  and one controller-side adapter-SSH run passed without retry. A deliberately
  lineage-free mutation was refused with exit 78 and did not change state.
  Retained journal privacy scans found no host, home-directory, or typed-value
  leakage, Calculator was closed, and the official nils-cli 1.22.5 binary was
  restored.
- 2026-07-15: Acceptance exposed two distinct correctness issues. macOS CI's
  `coverage` job was functionally failing because Apple's fixed `/var` to
  `/private/var` alias was treated as an unsafe parent symlink; the repair
  admits only the exact Apple `/var`, `/tmp`, and `/etc` fixed aliases on macOS
  and keeps every other symlink fail-closed. `app list` and `window list` were
  also misclassified as mutations; they are now read-only while launch, move,
  and all other mutation families still require expected-state protection.
- 2026-07-15: In the private runner's `display_count=0` state, pinned Peekaboo
  v3.9.3 rejects a freshly captured element-ID snapshot as stale even when the
  window ID still matches `window list`. This is not reported as passing. The
  active-GUI contract does not promise displayless snapshot targeting, and the
  proven observed-coordinate fallback plus never-replay refusal makes it a
  non-blocking environment residual. No upstream issue was opened. A controlled
  Peekaboo fork remains feasible only if displayless element-ID targeting is
  later promoted to a required product contract; the current delivery stays
  entirely schedule-controlled in the nils-cli fork.
- 2026-07-15: Final signed nils-cli head
  `da5b4435740359335ca0dc67ce09bc1892481e80` passes the complete 6156-case
  `--local-fast` gate, all-feature clippy, doctests, docs, completion, owner
  tests, real-Mac acceptance, test-first/docs-impact verification, and exact-
  head red-team approval. Provider run
  <https://github.com/sympoies/nils-cli/actions/runs/29453556413> also passes
  Linux, macOS, coverage, cargo-deny, CodeQL, and both JUnit reports. The
  delivery-owner review outcome is the final pre-merge gate.
- 2026-07-15: Before merge, latest `main` added five non-overlapping
  `agent-session` commits. They were integrated through signed merge commit
  `2a2592b4`; `Cargo.lock` and all `crates/macos-agent` content remained byte-
  identical to the real-Mac acceptance head. The first integrated workspace
  run exposed a deterministic test-isolation defect: its missing-authority
  child inherited `AGENT_SESSION_ATTENTION_AUTHORITY=protocol` from a managed
  Codex parent. Test-only commit `d41e2fd7` explicitly removes that environment
  variable for the child. The focused test changed red to green, and the full
  integrated gate passes all-feature clippy, 6176/6176 nextest cases, and
  doctests. Test-first and docs-impact evidence verify against the signed head;
  provider CI and exact-head review were restarted.
- 2026-07-15: Exact-head testing review then found a functional contract gap,
  not a security-only residual: successful exact `app list` and `window list`
  observations executed as read-only but were journaled `never`, losing replay
  argv and replay-plan eligibility. Commit `08682a61` reuses the exact family-
  list policy predicate in replay classification and adds unit/integration
  ownership while keeping launch/move and remote replay guarded. Latest `main`
  was integrated at signed head `75cc7d23`; the serialized full gate passes
  all 6187 nextest cases and doctests, test-first/docs-impact records verify,
  the testing follow-up and combined exact-head approval pass, and all 33
  review threads are resolved. Provider run
  <https://github.com/sympoies/nils-cli/actions/runs/29456032903> passed Linux,
  macOS, coverage, cargo-deny, CodeQL, and JUnit gates. `forge-cli pr deliver`
  promoted and squash-merged PR #1234 as
  `2e55e376306f8d69894576c0a3ee9a844a115efd`, then deleted the source branch.
  Task 3.3 is now paused only at the repository-owned release workflow's
  mandatory explicit stable-version and two-stage consent boundary.
- 2026-07-15: The post-merge runtime-kit validation passed position 1 plan and
  skill governance, then stopped at the expected position 2 version-alignment
  gate because the host is nils-cli 1.22.5 while the retained runtime-kit pin
  is v1.22.3. This is not waived as a final cutover gate: Task 4.2 owns the
  released-version pin/surface refresh, after which the complete
  `scripts/ci/all.sh` and `tests/hooks/run.sh` sequence must pass.
- 2026-07-16: Runtime-kit Task 4.1 captured a new current-baseline test-first
  record. The new direct-adapter mechanics probe passed while the pre-cutover
  skill/capability contract failed, producing meaningful red before source
  edits. The implementation now calls released `macos-agent` directly,
  documents backend/doctor/exec/scenario/MCP/journal/replay choices, removes
  the duplicate Python and shell mechanics, and publishes the canonical
  supported/adapter/optional/disabled/unsupported matrix.
- 2026-07-16: Focused deterministic computer-use validation passes 2/2,
  including local/SSH journal parity, mutation postcondition refusal,
  sensitive suppression and `never` replay, seeded significant-failure review,
  all three MCP profiles, hard-denied tools, privacy scanning, helper absence,
  and Codex/Claude/Hermes source render checks. The acceptance-matrix contract
  passes with all 37 skill IDs. Exact merged adapter `capabilities` output also
  matches the declared transport, interface, runtime, profile, and disabled
  ceilings. Task 4.1 remains in progress solely because its acceptance requires
  the released v1.22.6 on-pin binary; Linux strict live probes correctly remain
  host-inapplicable rather than being counted as a pass.
- 2026-07-16: nils-cli v1.22.6 was released from approved source `01e1993`
  and fixed-fleet broker run
  <https://github.com/serenvia/sympoies-infra/actions/runs/29465243199>
  verified nils-cli 1.22.6 on both MacBook and sympoies. The runtime-kit pin now
  records the exact v1.22.6 Linux asset digests, raises the consumed
  `agent-runtime` and `macos-agent` floors to 1.22.6, updates README and all
  three harness mirrors, and refreshes Codex, Claude, and Hermes computer-use
  goldens.
- 2026-07-16: On the released v1.22.6 host, version-alignment doctor passes
  17/17 with zero warnings or blockers, skill governance passes for all 27
  active skills, focused deterministic computer-use validation passes 2/2,
  and the acceptance matrix covers all 37 expected skill IDs. Clean-source
  convergence and the full CI/hooks floor remain Task 4.2's next gates.
- 2026-07-16: The first clean-source full-CI run correctly failed on installed
  retired Python/helper symlinks. A dry-run-first managed surface sync exposed
  them as review-needed; released `prune-stale --owned-source-root` then proved
  exact ownership by the durable prior checkout and removed only six helper
  symlinks plus their six now-empty directories across Codex, Claude, and
  Hermes. Audit drift subsequently reported zero warnings or blockers.
- 2026-07-16: Later full-CI red exposed three pin ceremony omissions rather
  than adapter defects: the unsafe-content heuristic matched a line-leading
  sensitive keyword in replay guidance, Docker fallback defaults retained the
  prior release and digests, and the exact `agent-docs` runtime-smoke matcher
  retained 1.22.3. Each failure was reproduced, repaired without weakening its
  contract, and passed its focused gate.
- 2026-07-16: Signed head `827987d` passes all 16 `scripts/ci/all.sh`
  positions. Deterministic runtime smoke reports 100 pass, zero fail, and one
  declared Linux `screen-record` host-capability skip; computer-use and evidence
  cases pass, clean-source convergence passes the full upgrade/prune/rollback/
  re-upgrade/idempotence cycle, version baseline is 21/21, and security,
  product-leak, memory, install, render, drift, and governance gates are green.
  The separately required `tests/hooks/run.sh` also passes 178/178.
- 2026-07-16: Five newer `origin/main` commits, including the checkout-lease
  hook rollout, were integrated without conflict as signed merge `c46edf3`.
  Managed Codex, Claude, and Hermes surfaces were resynchronized from that exact
  head with `prune=ok`, `doctor=ok`, and verified Codex prompt input. Exact-head
  `scripts/ci/all.sh` again passes positions 1-16; deterministic runtime smoke
  remains 100 pass, zero fail, and one declared Linux host-capability skip. The
  expanded checkout-lease-aware hook suite passes 212/212 both inside full CI
  and in the separately required `tests/hooks/run.sh` invocation.
- 2026-07-16: Testing, maintainability, and API-contract review found functional
  false-green gaps rather than security-only residuals: six retired helper
  files remained in product goldens, normal sync could not forward a confirmed
  prior checkout root, one Claude floor example remained 1.21.13, and the
  deterministic fake invented journal/MCP/doctor fields that do not exist in
  released v1.22.6. New assertions reproduced all failures before repair.
  Signed commit `20823a5` deletes the stale files, compares exact rendered and
  golden inventories, forwards only explicit absolute prior roots, validates
  hard-coded CLI examples against active manifest pairs, binds capabilities to
  the installed released binary, and matches journal, MCP JSON-RPC, SSH replay,
  and doctor contracts. Focused computer-use passes 2/2, meta passes 46/46,
  and version baseline passes 24/24.
- 2026-07-16: Required red-team review found the skill's single-directory rule
  incompatible with v1.22.6 journal manifest homogeneity: exec-to-MCP and
  minimal-to-sensitive reuse are rejected by the adapter. The mixed-mode red
  reproduced both routing failures. Signed commit `347615a` defines sibling
  child run directories homogeneous by interface and `(runtime, transport,
  evidence_mode, tool_profile)`, and the deterministic fixture now rejects
  manifest mismatches before overwrite. Focused computer-use returns 2/2.
- 2026-07-16: Signed repair head `a36ba6e` passes
  `.agents/scripts/pre-pr.sh`: all 16 CI positions, deterministic runtime smoke
  101 pass / zero fail / one declared Linux screen-record host-capability skip,
  hooks 212/212, version baseline 24/24, computer-use 2/2, and meta 46/46.
  Test-first v2 and docs-impact records verify against the exact Git subject.
  Draft PR <https://github.com/graysurf/agent-runtime-kit/pull/621> passes all
  required provider checks plus CodeQL. Only final-head focused specialist
  follow-ups and provider-native review convergence remain before merge.
- 2026-07-16: Final follow-up maintainability and API-contract review found
  additional functional false-greens. The published scenario and MCP examples
  reused the exec child despite the homogeneous-interface rule; the fixture
  terminated a denied MCP request instead of returning JSON-RPC `-32001` and
  continuing; backend, doctor, exec, scenario, and manifest shapes remained
  incomplete; and the homogeneity tuple omitted `backend_digest`. New
  assertions drove both computer-use cases red before repair. The skill now
  allocates distinct exec/scenario/MCP children and rotates after backend
  change; the fixture matches exact released v1.22.6 result enums and required
  fields, closed manifests, policy-denial continuity, and backend-digest
  rejection. Those contracts were checked against release commit `71f42a3e`;
  its model, backend, journal, MCP, and scenario defining sources are
  byte-identical to the inspected release checkout. Focused computer-use
  returns 2/2; exact-head full validation and review closure remain.
- 2026-07-16: nils-cli v1.22.7 release request run
  <https://github.com/serenvia/sympoies-infra/actions/runs/29473796577>
  published <https://github.com/sympoies/nils-cli/releases/tag/v1.22.7> from
  approved source `a75455c930d8761b1ce9e735b7d74f7862225fa1`; broker run
  <https://github.com/serenvia/sympoies-infra/actions/runs/29473807996>
  deployed and verified 1.22.7 on the fixed fleet.
- 2026-07-16: Runtime-kit PR
  <https://github.com/graysurf/agent-runtime-kit/pull/630> merged as `ff0c975`.
  Local validation passed CI positions 1-16, deterministic runtime smoke 101
  pass / zero fail / one declared host-capability skip, hooks 218/218, baseline
  24/24, and focused evidence 7/7. Current-head provider CI and CodeQL passed
  4/4. A checkout-lease race reason-string flake preserved one-winner safety,
  passed 100 focused repetitions and the failed-job rerun, and is owned by
  ready follow-up issue <https://github.com/graysurf/agent-runtime-kit/issues/632>.
- 2026-07-16: Merged `main` synchronized Codex, Claude, and Hermes surfaces
  with prune, doctor, plugin activation, home-prompt wiring, and Codex
  prompt-input verification all green. On the private macOS role, strict
  backend verification, doctor, permissions, Bridge, and required capability
  probes pass. A freshly observed Calculator action clicked `All Clear`; a
  subsequent AX-tree inspection read the display value as `0`. Journal summary,
  review, redaction, and remote replay-ineligibility checks pass; the initial
  text-selector misuse failed before mutation and is non-significant.
- 2026-07-16: Recovery acceptance followed the fresh-install branch because
  `backend status` reported `previous=null`. Strict rollback dry-run refused
  deterministically with exit 69 and `no previous backend receipt exists`; a
  subsequent status read-back preserved current Peekaboo v3.9.3 commit
  `3cfd612adbcb1b43e8431a7a1f3b02ec45d01269`. Runtime-kit PR
  <https://github.com/graysurf/agent-runtime-kit/pull/633> encoded both the
  strict verified-previous and fresh-install refusal branches, passed local CI
  positions 1-16 and current-head remote checks 4/4, received API-contract,
  maintainability, testing, and final native approval, and merged as `4fcd298`.
- 2026-07-16: The final L2 run-state records phase `ready-for-close`, validation
  `pass`, linked implementation/acceptance PR #633, and its current-head native
  approval. A live `tracking checkpoint` posted state, session, validation, and
  review roles and repaired the #610 dashboard. Strict `tracking close-ready
  --expect-visible` then returned `ready=true`, `blockers=[]`, and complete
  visible-role coverage. Provider `record close`, closeout read-back, archive
  routing, and terminal worktree cleanup remain ordered lifecycle finalizers
  after this ledger update merges; they are not hidden plan-task gaps.

## Session Notes

- 2026-07-15: Classified as L2 because one outcome spans an upstream binary
  lock, a nils-cli replacement/release, a runtime-kit skill/pin cutover, private
  deployment, and retained acceptance evidence.
- 2026-07-15: Locked architecture: Peekaboo owns native UI behavior;
  `macos-agent` owns supply chain, transport, journaling, replay, and rollback;
  the skill owns intent, approvals, postconditions, privacy, and defect routing.
- 2026-07-15: Peekaboo latest changed from `v3.9.2` to `v3.9.3` during plan
  research. The plan therefore treats `v3.9.3` as an immutable candidate and
  requires an explicit freshness review rather than resolving `latest` at run
  time.
- 2026-07-15: The maintainer added execution journaling as a core requirement.
  Release is blocked until structural records, redaction, guarded replay,
  significant-defect clustering, owner routing, and private retention are
  proven.
- 2026-07-15: Browser MCP, AI, shell, audio, and permission mutation are
  intentionally disabled in the first release. Authenticated browser acceptance
  is read-only and does not create a real credential.
- 2026-07-15: User-approved scope adjustment: prioritize complete live
  functional evidence over waiting on an upstream CLI notary ticket, without
  generalizing the exception into a runtime flag or future-release precedent.
- 2026-07-15: User-approved acceptance adjustment: functional correctness and
  usability remain mandatory, while security-only residual coverage may be
  deferred. The accepted first-release contract therefore requires repeatable
  active-GUI operation, explicit postconditions, redacted journals, and guarded
  no-replay behavior; it records but does not block on displayless element-ID
  targeting or a generalized notarization guarantee beyond the locked waiver.
- 2026-07-16: Final closeout retained the exact-artifact CLI notary and
  displayless element-ID limitations as explicit non-blocking residuals. It did
  not weaken digest, signer, Team ID, architecture, version, app-notary,
  privacy, target, postcondition, journal, or replay gates. The only deferred
  reproducible product defect is the independently ready checkout-lease race
  classification issue #632.
