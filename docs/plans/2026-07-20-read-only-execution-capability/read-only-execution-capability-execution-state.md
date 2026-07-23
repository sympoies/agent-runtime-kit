# Execution State: Deliver a real read-only execution capability

## Execution State

- Source document: `docs/plans/2026-07-20-read-only-execution-capability/read-only-execution-capability-plan.md`
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/670>
- Current sprint: Sprint 4
- Status: in-progress
- Current task: 4.1 Cut over and delete the legacy classifier
- Next task: 4.2 Deliver, review, and merge the cutover PR
- Implementation branch/worktree: fresh managed worktree from provider-verified
  main after PR #720 merge
- Current gate: test-first cutover, exact v1.25.9 validation, and one focused
  final-head review
- Integration dependency: #686 is closed complete; its single `agent-hook`
  ingress is available
- Review-convergence baseline: #673 complete
- Blockers: none
- Last updated: 2026-07-21

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Attach and initialize the L2 tracker | done | #670 accepted design checkpoint; [plan snapshot](https://github.com/graysurf/agent-runtime-kit/issues/670#issuecomment-5023974778) | Tracker attached and run state initialized; resume at Task 1.2 |
| 1.2 | Capture contract-first red for capability verification | done | pending; v2 test-first record; meaningful red in agent-hook, agent-docs, and forge-cli; pre-edit check passed | Production edits may begin on feat/read-only-capability-schema |
| 1.3 | Implement the capability in shadow mode | done | [nils-cli PR #1335](https://github.com/sympoies/nils-cli/pull/1335); merge `7ac3e54e` | Shadow-only verifier cannot change admission |
| 1.4 | Add tool-owned operation effect descriptors | done | [nils-cli PR #1335](https://github.com/sympoies/nils-cli/pull/1335); 1,620 affected tests | Typed `agent-docs` and `forge-cli` owners |
| 1.5 | Deliver the capability/descriptor PR | done | [review outcome](https://github.com/sympoies/nils-cli/pull/1335#issuecomment-5024864708); five threads resolved | One focused gate plus one affected-only blocker follow-up |
| 2.1 | Freeze the common runner and conformance contract | done | [test-first evidence](https://github.com/sympoies/nils-cli/pull/1337); 14 Linux conformance cases | Meaningful red captured before implementation and rebound to exact delivery head |
| 2.2 | Implement and deliver the Linux backend | done | [nils-cli PR #1337](https://github.com/sympoies/nils-cli/pull/1337); merge `f5ed1f4e`; [CI](https://github.com/sympoies/nils-cli/actions/runs/29780137168); [review outcome](https://github.com/sympoies/nils-cli/pull/1337#pullrequestreview-4739230309) | Three P1 fingerprints repaired; two P2 threads resolved; bounded local-fast waiver retained |
| 2.3 | Validate and deliver typed fail-closed macOS behavior | done | macOS 26.5.1 launchd/Seatbelt probe; Apple `sandbox-exec`, `launchd.plist`, and XNU contracts; maintainer-approved macOS typed fail-closed plan amendment; [nils-cli issue #1343](https://github.com/sympoies/nils-cli/issues/1343); [nils-cli PR #1344](https://github.com/sympoies/nils-cli/pull/1344); merge `0a3c85af`; [CI 29799919732](https://github.com/sympoies/nils-cli/actions/runs/29799919732); [owner outcome](https://github.com/sympoies/nils-cli/pull/1344#issuecomment-5030098187); exact-head test-first evidence; [strict-backend follow-up #1343](https://github.com/sympoies/nils-cli/issues/1343) | Same CLI; macOS returns typed unavailable with no descriptor; strict backend deferred to #1343 |
| 2.4 | Prove end-to-end nils capability behavior | done | [PR #1335](https://github.com/sympoies/nils-cli/pull/1335); [PR #1337](https://github.com/sympoies/nils-cli/pull/1337); [PR #1344](https://github.com/sympoies/nils-cli/pull/1344); Linux 14/14, macOS 2/2, hook 8/8, agent-docs 17/17, forge-cli 713/713; cross-platform provider CI | Linux os_enforced, macOS unavailable, and cross-platform tool_contract behavior are bound without runtime-kit cutover |
| 3.1 | Reconcile the #686 ingress dependency | done | [#686 final dashboard](https://github.com/graysurf/agent-runtime-kit/issues/686); closed complete; single agent-hook ingress merged through runtime-kit PR #708 and nils-cli v1.25.6 | No competing provider registration or legacy sibling writer introduced |
| 3.2 | Release the complete nils-cli surface and advance the pin | done | [nils-cli v1.25.9](https://github.com/sympoies/nils-cli/releases/tag/v1.25.9); release commit `884f072c`; [public release run](https://github.com/sympoies/nils-cli/actions/runs/29817492126); [fixed-fleet broker run](https://github.com/serenvia/sympoies-infra/actions/runs/29816013549) | v1.25.9 includes #1349 and is installed on the live host |
| 3.3 | Add the runtime-kit rule in shadow mode | done | [PR #720](https://github.com/graysurf/agent-runtime-kit/pull/720); exact head `ae5dad4649d945f25ae1a7f503c47a648c0c6d80`; exact v1.25.8 validation | Shadow evidence only; legacy admission remains authoritative |
| 3.4 | Deliver the runtime-kit shadow PR | done | [PR #720 checks](https://github.com/graysurf/agent-runtime-kit/actions/runs/29819903782); [final review outcome](https://github.com/graysurf/agent-runtime-kit/pull/720#pullrequestreview-4743407661); all threads resolved | One focused final-head review plus required red-team; no implementation re-review |
| 4.1 | Cut over and delete the legacy classifier | pending | pending | remove four legacy surfaces and decision path |
| 4.2 | Deliver, review, and merge the cutover PR | pending | pending | fifth reviewable implementation PR |
| 4.3 | Prove deploy readiness without live activation | pending | pending | live apply needs fresh approval |
| 4.4 | Strict tracker closeout and archive handoff | pending | pending | close only after `close-ready` succeeds |

## Validation Log

- 2026-07-20: The maintainer approved graduating #670 from its completed L1
  design checkpoint into one L2 plan tracker. This planning turn does not
  authorize code implementation, a nils-cli public release, or live runtime
  activation.
- 2026-07-20: Plan archive catalog contained no plan referencing #670. A broad
  `read-only` search returned only unrelated historical plans; no duplicate
  tracker was found.
- 2026-07-20: Live #670 read-back found one ordinary accepted-design comment
  and no source/plan/state lifecycle roles, so `record attach --profile
  tracking` is the correct one-time conversion path.
- 2026-07-20: Live #686 dashboard reported Task 2.3 in progress, Task 2.4 next,
  and no blockers. The dependency is deferred to Task 3.1; nils-cli Sprints 1-2
  can proceed independently.
- 2026-07-20: #673 is closed and complete. Its review idempotency, stale-thread
  disposition, and reviewable-size policy are the convergence baseline for
  every #670 implementation PR.
- 2026-07-20: Released `plan-issue`, `plan-tooling`, and `forge-cli` v1.25.5
  satisfy the L2 workflow floors.
- 2026-07-20: `plan-tooling validate`, `rumdl check`, and `git diff --check`
  passed. `record attach --profile tracking --allow-dirty` posted the source,
  plan, and initial state snapshots to #670, and tracking run
  `20260720T152551Z-issue-670` initialized successfully. Task 1.1 is complete;
  implementation resumes at Task 1.2.
- 2026-07-20: `bash tests/hooks/run.sh` passed all 313 tests across 16 shards.
  `bash scripts/ci/all.sh` passed positions 1-6, then stopped at position 7
  because the existing ignored `build/claude` surface reports 206 rendered-
  drift/unsafe warnings against pre-existing policy and heuristic sources.
  No #670 plan file was named in that failure. Planning validation is recorded
  as partial; implementation closeout must rerun the full gate against the
  then-current released pin and clean rendered baseline.
- 2026-07-20: nils-cli PR #1335 merged as `7ac3e54e`. Test-first evidence
  verified against head `83f1e09a`; affected Clippy, format, diff checks, a
  real producer-consumer shadow receipt, and all 1,620 affected tests passed.
  One coordinated review gate fixed the shared shadow deadline, request-cwd
  binding, and typed nested-query findings. All five threads resolved; the
  positive cross-platform matrix and signed package provenance remain their
  planned Tasks 2.4 and 3.2 instead of restarting broad review.
- 2026-07-21: nils-cli PR #1337 merged as `f5ed1f4e` from exact reviewed head
  `ac38b70e`. The Linux backend passed 14 adversarial conformance cases, 8
  hook verifier tests, direct seccomp ownership coverage, affected Clippy, and
  the complete Linux/macOS/coverage/cargo-deny/CodeQL provider matrix. The
  single affected-only follow-up closed pathname Unix sockets, writable nested
  mounts, producer dispatch shadowing, and the `io_uring_setup` coverage gap.
  All non-outdated threads resolved. One unchanged local timing fixture remains
  a bounded residual because affected suites and provider CI pass.
- 2026-07-21: Task 2.3 platform feasibility was checked against Apple-owned
  contracts and a narrowly-scoped fixture on the project macOS peer (Darwin
  26.5.1). `sandbox-exec` remains present but deprecated. launchd documents
  cleanup only for processes that retain the job process-group ID; its
  `NumberOfProcesses` limit is UID-wide, and `ResidentSetSize` is advisory.
  The fixture forked a child, called `setsid`, and proved that the child
  survived both job exit and `launchctl remove`; the fixture then killed the
  child and removed its cache directory. XNU also marks recursive kqueue
  `NOTE_TRACK` descendant tracking unsupported since macOS 10.5. Therefore the
  current public, unprivileged primitives cannot truthfully emit strict v1
  evidence. No production code was changed and the common contract was not
  weakened.
- 2026-07-21: The maintainer explicitly amended #670 so macOS keeps the same
  `agent-run inspect` CLI but remains typed fail-closed. Linux remains the only
  `os_enforced` backend in this plan; a separate follow-up owns any future
  privileged/dedicated-user or VM-backed macOS implementation. Live runtime
  application remains unauthorized.
- 2026-07-21: nils-cli PR #1344 merged as `0a3c85af` from exact reviewed head
  `0c272699`. The final head passed native macOS 2/2 fail-closed contract tests,
  the affected 204-test local-fast gate, Linux/macOS/coverage/cargo-deny/CodeQL
  provider CI, and testing, maintainability, and API-contract lenses. The one
  API-contract finding was repaired test-first; strict macOS enforcement stays
  in #1343. Tasks 2.3 and 2.4 are complete.
- 2026-07-21: Live #686 read-back reported a closed, complete final dashboard.
  Its single `agent-hook` ingress is merged and released in nils-cli v1.25.6,
  so Task 3.1 is complete without reopening its design or branch.

## Decision Log

- Reuse #670 as the sole tracking issue; do not open a second tracker.
- Keep this as sequential L2 execution. Multiple reviewable PRs do not by
  themselves require L3 dispatch.
- Use exactly two v1 capability producer families: OS-enforced local inspection
  and same-release tool-owned query contracts.
- Treat #686 as a single-ingress landing dependency only at Task 3.1.
- Split delivery by owner boundary and platform; never combine nils capability,
  both OS backends, release/pin, shadow migration, and cutover into one PR.
- Apply one focused review gate per PR, at most one affected-only re-review
  after a blocking repair, and no broad review restart for P2 preferences.
- Keep public release and live runtime application as fresh-authorization
  boundaries owned by their release/deployment workflows.
- Do not represent same-process-group cleanup, UID-wide `RLIMIT_NPROC`, or an
  advisory RSS preference as strict job-local descendant/process/memory
  enforcement on macOS.
- Retain one CLI across platforms: Linux may return `os_enforced`; macOS must
  return typed `unavailable` and route safely to exact-target `project-dev`
  preparation until the linked strict-backend follow-up is delivered.
- Track the deferred strict macOS backend in
  <https://github.com/sympoies/nils-cli/issues/1343>; #670 will not install or
  implement a privileged/dedicated-user or VM boundary.

## Handoff

Task 3.2 is blocked only on the exact stable-version decision required by the
canonical two-stage nils-cli release skill. After the user confirms a version
and `release-and-deploy`, render the Stage 1 command and stop for its separately
bound execution consent. After release, advance the runtime-kit validated pin
without moving the compatibility minimum unless a separate retirement is
approved. Do not apply anything to live runtime homes.
