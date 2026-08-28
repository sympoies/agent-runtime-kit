# nils-cli Surface Snapshot

- Snapshot date: 2026-08-28 (refreshed for `v1.27.22`)
- Source repo: [`sympoies/nils-cli`](https://github.com/sympoies/nils-cli) (main)
- Source command: `ls crates/` and `bash scripts/workspace-bins.sh` in the
  `sympoies/nils-cli` release worktree
- Active `git describe --tags` output: `v1.27.22`
- Machine-readable version policy for CI and packaging:
  `docs/source/nils-cli-pin.yaml` (`minimum_supported_tag: v1.27.16`,
  `validated_tag: v1.27.22`), consumed by `scripts/ci/all.sh` Position 1 via
  `agent-runtime doctor --class version-alignment`. Keep both role cues in
  lock-step with that manifest; the active describe mirrors validated.
- Head commit: `5ffcf3c0`
  (`chore(release): bump cli versions to 1.27.22`)
- Release:
  [`v1.27.22`](https://github.com/sympoies/nils-cli/releases/tag/v1.27.22),
  Homebrew tap formula at `Formula/nils-cli.rb` on `sympoies/homebrew-tap`
  `main`
- `v1.27.22` is the validated release; `v1.27.16` remains the compatibility
  minimum. It lets audited read-only and trusted advisory/off startup hooks
  continue through typed activity-helper faults while preserving fail-closed
  mutation, incomplete managed-session identity, and later authoritative DSH
  decisions ([#1554](https://github.com/sympoies/nils-cli/pull/1554)). It also
  adds bounded retry guidance to unclassifiable shell-effect denials without
  changing their policy reason codes
  ([#1555](https://github.com/sympoies/nils-cli/pull/1555)). These are compatible
  repairs to the existing `agent-hook` contract, so no `required_clis[]` floor
  moves and the minimum remains v1.27.16.
- `v1.27.21` was the previous validated release; `v1.27.16` remains the compatibility
  minimum. It adds privacy-safe handler identity, capability-cause, doctor, and
  owner-repair guidance to existing `agent-hook` fail-posture errors
  ([#1550](https://github.com/sympoies/nils-cli/pull/1550)), and admits the
  fixed system Git executable when strict Linux user-namespace evidence proves
  host root is represented by the unmapped overflow UID
  ([#1552](https://github.com/sympoies/nils-cli/pull/1552)). These are compatible
  diagnostics and trust-proof repairs to existing contracts, so no
  `required_clis[]` floor moves and the minimum remains v1.27.16.
- `v1.27.19` was the previous validated release; `v1.27.16` remains the
  compatibility minimum. It adds `git-cli push --bootstrap`, which publishes the first branch
  of a remote proven empty by `ls-remote` and carries a create-only lease so a
  branch appearing between the emptiness check and the push is rejected rather
  than fast-forwarded
  ([#1540](https://github.com/sympoies/nils-cli/pull/1540)). It also removes
  `git-cli push --expect-default`, whose conventional-name guard only ever
  stopped a caller who named the branch truthfully
  ([#1544](https://github.com/sympoies/nils-cli/pull/1544)). Runtime-kit
  consumes neither surface directly, so no `required_clis[]` floor moves and the
  minimum stays where it is: a host at the floor still has `--expect-default`
  and lacks `--bootstrap`, which is why the delivery guard's empty-remote
  refusal describes the bootstrap route in general terms instead of naming the
  flag.
- `v1.27.16` is the compatibility minimum. Runtime-kit
  now consumes exact requested-base binding across `forge-cli` PR lookup,
  adoption, create readback, ready, and merge, plus `git-cli sync-branch` for
  same-name-upstream, fast-forward-only synchronization of persistent
  non-default integration branches
  ([#1533](https://github.com/sympoies/nils-cli/pull/1533)). The `forge-cli`
  and `git-cli` consumer floors therefore move to `>=1.27.16`; because the old
  `v1.27.3` minimum cannot provide either required contract, this adoption
  explicitly retires it and moves the retained minimum digests to `v1.27.16`.
  Minimum and validated share one physical CI lane while preserving both role
  labels. The release commit is [#1534](https://github.com/sympoies/nils-cli/pull/1534).
- `v1.27.13` was the previous validated release while `v1.27.3` remained the compatibility
  minimum. It preserves tmux-backed session liveness under a C locale by using
  a printable snapshot delimiter while accepting the historical tab form
  ([#1523](https://github.com/sympoies/nils-cli/pull/1523)), bounds contained
  finish-line unit teardown without weakening cgroup termination
  ([#1522](https://github.com/sympoies/nils-cli/pull/1522)), and makes
  `forge-cli` review-loop merge-gate failures name their exact remedy
  ([#1519](https://github.com/sympoies/nils-cli/pull/1519)). The remaining
  release change retargets an existing nextest retry comment to its live
  follow-up ([#1525](https://github.com/sympoies/nils-cli/pull/1525)). These are
  compatible fixes to already-admitted contracts, so this ordinary
  validated-role uptake does not move the global compatibility minimum or any
  `required_clis[]` floor.
- `v1.27.12` was the previous validated release while `v1.27.3` remains the
  compatibility minimum. Runtime-kit consumes its body-free authenticated coordination
  checkpoint notification, which lets long-running agents inspect mailbox
  metadata promptly at safe boundaries without interrupting an atomic mutation
  ([#1509](https://github.com/sympoies/nils-cli/pull/1509)). Releases
  `v1.27.4` through `v1.27.12` also carry compatible DSH lifecycle,
  workspace-lease, advisory coordination, transactional prerequisite, graceful
  session deletion, Git-version inspection, and macOS refusal-classification
  hardening. These changes preserve the existing contracts admitted by
  `v1.27.3`, so this ordinary validated-role uptake does not move the global
  compatibility minimum or any `required_clis[]` floor.
- `v1.27.3` was the previous validated release and remains the compatibility
  minimum. Runtime-kit
  consumes the breaking `macos-agent` adapter v3 contract:
  official Peekaboo v4.2.2 provenance, a remote wire/schema bump, transition-only
  authentication of installed v3.9.3 backends, individually reviewed exec flows
  in place of the removed scenario runner, and the v4 action/press/verification
  surfaces ([#1478](https://github.com/sympoies/nils-cli/pull/1478)). The
  `macos-agent` floor therefore moves to `>=1.27.3`. Because the previous
  `v1.26.4` minimum cannot provide this required adapter contract, this adoption
  explicitly retires that floor and moves the retained minimum digests to
  `v1.27.3`; no other per-binary floor moves. The intervening v1.27.1 DSH
  coordination changes and v1.27.2 authenticated recovery-ingress fix are
  compatible hardening rather than separate runtime-kit requirements.
- `v1.27.0` was the previous validated release while `v1.26.4` remained the
  compatibility minimum. The release adds the nils-native DeepSeek Harness ingress,
  main-agent provider, and finish-line engine
  ([#1465](https://github.com/sympoies/nils-cli/pull/1465),
  [#1467](https://github.com/sympoies/nils-cli/pull/1467),
  [#1468](https://github.com/sympoies/nils-cli/pull/1468)). The legacy
  runtime-kit does not consume those new DSH contracts, so this ordinary
  validated-role uptake does not move the compatibility minimum or any
  `required_clis[]` floor.
- `v1.26.4` was the previous validated release and compatibility minimum until
  the breaking macos-agent v3 adoption above.
  Runtime-kit consumes its provider-native aggregate-context
  preservation in `agent-hook`, plus the 768-byte startup default, exact
  optional agent recall scope, trusted agent-root checks, and frontmatter-aware
  candidate previews in `agent-memory`
  ([#1460](https://github.com/sympoies/nils-cli/pull/1460)). The `agent-hook` and
  `agent-memory` consumer floors therefore move to `>=1.26.4`. Because the
  exact-minimum lane admits every `required_clis[]` floor before running the
  behavior stack, retaining `v1.25.13` would make the declared contract
  impossible to execute; this explicitly retires that compatibility floor and
  moves its retained release digests to `v1.26.4`. No other per-binary floor
  moves. The intervening
  `v1.26.3` release-pipeline and dependency changes are not consumed runtime
  contracts in this repository.
- `v1.26.2` was the previous validated release. It carries the whole `v1.26.1`
  uptake — an upgrade-safe
  `agent-session` binary pin for newly created tmux sessions, the `agent-hook`
  degradation and centralized observation lanes with `agent-session diagnose`
  and richer `/healthz` projection, no-agent-attribution guards on commit and
  PR writers, visible and consolidated review-ledger comments, and capability
  success based on process exit status rather than stdin closure
  ([#1415](https://github.com/sympoies/nils-cli/pull/1415),
  [#1416](https://github.com/sympoies/nils-cli/pull/1416),
  [#1418](https://github.com/sympoies/nils-cli/pull/1418),
  [#1421](https://github.com/sympoies/nils-cli/pull/1421),
  [#1424](https://github.com/sympoies/nils-cli/pull/1424)) — and adds
  `agent-session` bootstrap / capacity attention classification and
  retained-claim recovery during retire replay
  ([#1431](https://github.com/sympoies/nils-cli/pull/1431),
  [#1432](https://github.com/sympoies/nils-cli/pull/1432)), plus the
  `forge-cli` changes below. It also fixes `agent-hook` Stop re-entry so typed
  `NotRun`, `Clean`, `Pending`, and `Unavailable` coordination results preserve
  their observed state; only a typed pending transaction now prescribes broker
  reconciliation ([#1448](https://github.com/sympoies/nils-cli/pull/1448)).
  This corrects misleading recovery advice without changing runtime-kit's
  compatibility floor or any per-binary floor.
- **One `forge-cli` change in `v1.26.1` is a tightening, not an addition, and is
  the only item here that can turn a previously passing delivery into a typed
  failure.** `pr merge` and `pr deliver` previously treated a head with *no*
  registered required checks as satisfying the check gate, so an empty snapshot
  read as green. It now fails closed with `checks_not_registered`, and
  `pr wait-checks` no longer treats an unchecked head as terminal
  ([#1440](https://github.com/sympoies/nils-cli/pull/1440)). Repositories that
  genuinely configure no checks must pass `--allow-no-checks`. Runtime-kit's
  delivery targets all register required checks, so this is expected to be
  inert here; it is called out because the failure mode is a *new* refusal
  rather than a missing feature.
- `v1.26.1` also adds the offline `forge-cli pr review-loop validate` verb and
  corrects `operation-effect` classification for the `review-loop` family, which
  had defaulted to `network_write`; `validate` now reports `read_only` /
  `local_read` ([#1441](https://github.com/sympoies/nils-cli/pull/1441)).
  Runtime-kit does not consume `review-loop validate` yet, so no per-binary
  floor moves for it. The remainder of the release is test-only hardening
  ([#1429](https://github.com/sympoies/nils-cli/pull/1429),
  [#1430](https://github.com/sympoies/nils-cli/pull/1430),
  [#1433](https://github.com/sympoies/nils-cli/pull/1433),
  [#1435](https://github.com/sympoies/nils-cli/pull/1435),
  [#1437](https://github.com/sympoies/nils-cli/pull/1437)). No compatibility or
  per-binary floor moves.
- `v1.25.13` was the previous compatibility minimum and validated release. Its
  adoption was an explicit compatibility retirement: current
  `semantic-commit`, `agent-session`, and `main-agent` contracts introduced in
  v1.25.11, while v1.25.8 does not ship `main-agent` at all. The old exact
  minimum lane therefore could not execute the repository's declared runtime
  contract. v1.25.13 is the first stable release that also contains the
  governed default-branch push and faithful review-loop dry-run prerequisites
  consumed by the in-flight runtime-kit delivery fixes
  ([nils-cli #1404](https://github.com/sympoies/nils-cli/pull/1404),
  [nils-cli #1406](https://github.com/sympoies/nils-cli/pull/1406)).
- `v1.25.8` was the previous compatibility minimum and validated release. The
  release uptake initially moved only the validated role, but runtime-kit's
  subsequent read-only shadow integration consumes `execution.read-only.v1`.
  `agent-hook` v1.25.5 cannot parse that capability, so PR #720 explicitly
  retires the old minimum ([failed minimum job](https://github.com/graysurf/agent-runtime-kit/actions/runs/29815639931/job/88586262640),
  [current-head review](https://github.com/graysurf/agent-runtime-kit/pull/720#pullrequestreview-4742842523)).
  The `agent-hook` consumer floor was `>=1.25.8` at that point; the `v1.26.4`
  adoption above supersedes it. v1.25.9 was reserved for the later enforce
  cutover and was not adopted there:
  - `agent-hook doctor` now validates policy-backed handler trust before it
    reports activation convergence ([#1342](https://github.com/sympoies/nils-cli/pull/1342)).
    Runtime-kit's disposable setup-migration fixture materializes regular
    handler files into both product homes so this stronger validated-role check
    exercises a trusted runtime shape.
  - The release also includes read-only operation descriptors and shadow
    evaluation, resumable review transactions, bounded review delivery,
    Linux `agent-run inspect`, typed fail-closed macOS inspection, and Codex
    prompt recovery. The versioned runtime-kit policy now consumes the
    shadow-only evaluator at its existing Bash ingress; production admission
    remains the legacy decision.
- `v1.25.5` introduced the required setup-owned provider ingress, but it is now
  below the supported minimum. It passes the earlier schema and ingress gates
  yet rejects the committed policy because `execution.read-only.v1` is an
  unknown capability:
  - `agent-hook setup` owns one exact provider ingress for Codex and Claude,
    migrates compatible legacy registrations through an operation-bound
    preview/apply digest, and preserves unrelated provider hooks
    ([#1314](https://github.com/sympoies/nils-cli/pull/1314)).
  - `agent-hook` sequences the locked
    `agent-session.coordination.v1` capability after aggregate allow and
    completes or reconciles terminal lifecycle events
    ([#1330](https://github.com/sympoies/nils-cli/pull/1330)). That ingress set
    the historical `agent-hook >=1.25.5` floor; the read-only shadow consumer
    above superseded it with `>=1.25.8` and made v1.25.8 the global
    compatibility minimum at that time. The active v1.26.4 retirement above
    supersedes that historical policy.
  - Codex notification ownership composes and restores foreign or Computer
    Use notifier state without dropping either consumer
    ([#1329](https://github.com/sympoies/nils-cli/pull/1329)).
- `v1.25.0` establishes the schema-v2 compatibility floor and validated-role
  policy:
  - `agent-runtime doctor --class version-alignment` accepts separate
    `minimum_supported_tag` and `validated_tag` fields, blocks below minimum,
    warns above validated, preserves schema-v1 exact behavior, and validates
    the release digest relationship
    ([#1307](https://github.com/sympoies/nils-cli/pull/1307)).
  - Runtime-kit raises its `agent-runtime` floor to `>=1.25.0` because older
    binaries cannot parse the schema-v2 manifest.
  - Blocking minimum and validated CI lanes verify independent manifest-owned
    archive digests before extraction. Ordinary adoption moves only the
    validated digest pair; compatibility retirement owns the retained minimum
    pair.
- `v1.24.5` advanced the prior exact pin from `v1.24.3`, folding in `v1.24.4`:
  - `agent-session` adds authenticated atomic work-context claims, conflict
    evaluation, covered mutation admission/completion/reconcile leases, a
    bounded private mailbox, and fixed body-free notifications
    ([#1308](https://github.com/sympoies/nils-cli/pull/1308)). Runtime-kit now
    consumes this surface through the `session-coordination` intent and shared
    guard, so the `agent-session` floor moves to `>=1.24.5`.
  - `agent-session` also hardens Codex hook repair/trust convergence and marker
    ownership ([#1300](https://github.com/sympoies/nils-cli/pull/1300),
    [#1306](https://github.com/sympoies/nils-cli/pull/1306)), and schedules
    Claude session-limit recovery from authoritative reset metadata
    ([#1301](https://github.com/sympoies/nils-cli/pull/1301)).
  - `git-cli` aligns dirty-adoption lease lock waits with the bounded
    transaction deadline ([#1303](https://github.com/sympoies/nils-cli/pull/1303));
    no additional runtime-kit `required_clis[]` floor moves for that fix.
- `v1.24.3` advanced the prior exact pin from `v1.24.1`, folding in `v1.24.2`:
  - `agent-session` adds `codex_usage_account` launch-profile routing for
    Codex-account auto-resume in Claude profiles
    ([#1295](https://github.com/sympoies/nils-cli/pull/1295)).
  - `agent-session` exposes the last user prompt through
    `SessionView.last_prompt` and advertises
    `data.capabilities.last_prompt=true`
    ([#1297](https://github.com/sympoies/nils-cli/pull/1297)), then converges
    Codex lifecycle hooks across supported config representations
    ([#1298](https://github.com/sympoies/nils-cli/pull/1298)).
  - Runtime-kit does not consume `agent-session`; no `required_clis[]` or hook
    minimum floor moves for these additive releases.
- `v1.24.1` advances the pin from `v1.24.0`:
  - `forge-cli` converges the deliver-pr review loop
    ([#1292](https://github.com/sympoies/nils-cli/pull/1292)): `pr review`
    cross-run idempotent native posting (skips creating a duplicate
    `(path, body)` thread that already has a live non-resolved, non-outdated
    thread on the current head, reports `data.threads_skipped_idempotent`, and
    never sweeps prior reviews); `pr merge` auto-dispositions outdated
    unresolved threads as `stale` (`data.stale_thread_dispositions`) so only
    non-outdated threads block; and `--allow-unresolved-threads` now requires a
    paired `--allow-unresolved-threads-reason`
    (`data.unresolved_threads_override_reason`). Additive JSON (all
    `skip_serializing_if`); the `pr.review.v1` / `pr.merge.v1` schema versions
    are unchanged. Consumed by the review-loop convergence work tracked in
    [#673](https://github.com/graysurf/agent-runtime-kit/issues/673); the
    dirty-checkout integration does not independently raise the `forge-cli`
    floor.
  - `agent-docs` adds private project configuration
    ([#1274](https://github.com/sympoies/nils-cli/pull/1274)); additive and not
    yet consumed by runtime-kit.
  - `git-cli` adds governed dirty checkout adoption
    ([#1272](https://github.com/sympoies/nils-cli/pull/1272)).
  - `plan-issue` repairs terminal dashboard lifecycle state
    ([#1288](https://github.com/sympoies/nils-cli/pull/1288)); `agent-session`
    fixes Claude turn reactivation and profile-aware resume context
    ([#1284](https://github.com/sympoies/nils-cli/pull/1284),
    [#1287](https://github.com/sympoies/nils-cli/pull/1287)).
- `v1.24.0` advances the pin from `v1.23.0`:
  - `agent-docs` adds a `phase` dimension: an optional `phase` field on
    `[[document]]` (string or array; a doc with no phase applies to every
    phase) and an optional `--phase` filter on `preflight` and
    `session activate|prepare|verify`. Resolution and preparation can scope to
    one workflow phase; verify passes on a matching phase-scoped or a full
    prep, with new codes `phase-unsatisfied` / `invalid-phase`
    ([#1282](https://github.com/sympoies/nils-cli/pull/1282)). Additive and
    backward-compatible (skip-serialized fields, unchanged schema versions);
    runtime-kit's phase-scoped `project-dev` consumer is a separate follow-up
    (graysurf/agent-runtime-kit#601 P1 slice 3d), so the `agent-docs` floor
    does not move yet.
- `v1.23.0` advances the pin from `v1.22.12`:
  - `agent-docs` adds `session prepare`, an atomic intent-preparation primitive
    that runs the same strict preflight + activation as `session activate` and
    reports a stable `cli.agent-docs.session.prepare.v1` result
    (`prepared_intents` plus a `prepared` / `already-current` reason code) so a
    runtime hook can prepare an intent in one trusted invocation
    ([#1273](https://github.com/sympoies/nils-cli/pull/1273)). Additive;
    runtime-kit does not consume it yet (planned in the intent-hook consumer
    refactor), so the `agent-docs` floor does not move.
- `v1.22.12` advances the pin from `v1.22.11`:
  - GitHub direct merge now accepts an expected provider head, while
    `pr pending-review delete` requires the expected PR head, draft commit,
    exact body, and explicit abandonment confirmation. The delete primitive
    rereads and revalidates those values immediately before mutation, bounds
    review bodies to 64 KiB, and completes bounded pagination before selecting
    the target. Runtime-kit's three merge-owning delivery workflows bind the
    final merge to the provider head already inspected and reviewed, and use
    one immutable captured review body for initial submission, guarded
    compare-and-delete recovery, and retry. They therefore consume both the
    merge-head compare-and-swap and hardened compare-and-delete contracts, so
    their `forge-cli` floor and the global floor move to `>= 1.22.12`
    ([#1269](https://github.com/sympoies/nils-cli/pull/1269)).
  - `agent-session` adds server-owned launch profiles
    ([#1268](https://github.com/sympoies/nils-cli/pull/1268)). Runtime-kit does
    not consume `agent-session`, so no floor row is added.
  - Lockstep version changes do not alter other runtime-kit-consumed CLI
    contracts, so no other `required_clis[]` floor moves.
- `v1.22.11` advances the pin from `v1.22.10`:
  - GitHub `forge-cli pr review --submit-review` now requires
    `--expected-head <sha>`, rejects provider-head drift before mutation, and
    binds direct and threaded writes to that reviewed head. A viewer-owned
    pending draft is detected by the complete preflight snapshot and returned
    as `github_pending_review_exists`; other viewers' drafts remain
    non-blocking. Runtime-kit's three merge-owning delivery workflows consume
    the trusted-head binding and typed exact-node recovery contract, so their
    `forge-cli` floor and the global floor move to `>= 1.22.11`
    ([#1266](https://github.com/sympoies/nils-cli/pull/1266)).
  - Test-harness isolation and lockstep version changes do not alter other
    runtime-kit-consumed CLI contracts, so no other `required_clis[]` floor
    moves.
- `v1.22.10` advances the pin from `v1.22.9`:
  - `forge-cli pr reviews` now separates provider-valid pending drafts into
    `data.pending_reviews[]`, and GitHub gains `pr pending-review delete` for
    one exact pending node after PR membership, state, current-viewer
    authorship, and delete permission are verified. Runtime-kit's three
    merge-owning delivery workflows consume that fail-closed recovery path, so
    their `forge-cli` floor and the global floor move to `>= 1.22.10`
    ([#1259](https://github.com/sympoies/nils-cli/pull/1259)).
  - Release-pipeline latency, documentation, Bash 3.2 compatibility, dependency,
    and lockstep version changes do not add or alter other runtime-kit-consumed
    CLI contracts, so no other `required_clis[]` floor moves.
- `v1.22.9` advances the pin from `v1.22.7`, folding in `v1.22.8`:
  - `forge-cli repo push-default` adds the governed, fail-closed direct-main
    exception consumed by runtime-kit's always-on delivery policy. It binds one
    actual push destination to provider metadata, rejects second-stage URL
    rewrites, validates one signed fast-forward commit from an exact base, uses
    an internal exact-old-object compare-and-swap, and verifies the remote head.
    The global `forge-cli` floor therefore moved to `>= 1.22.9`; at this
    historical snapshot the PR, L2, and L3 skill floors remained at their
    independently consumed `>= 1.21.34` surface
    ([#1251](https://github.com/sympoies/nils-cli/pull/1251)).
  - `agent-session` adds safe maintenance recovery for orphaned session state
    ([#1249](https://github.com/sympoies/nils-cli/pull/1249)). Runtime-kit does
    not consume `agent-session`, so no floor row is added.
  - All other changes are lockstep release-version metadata; no other
    `required_clis[]` floor moves.
- `v1.22.7` advances the pin from `v1.22.6`:
  - `macos-agent doctor` now binds permission and Bridge-readiness probes to
    one stable app socket, so a stale default runtime cannot create a false
    strict-doctor blocker. Runtime-kit consumes the existing strict doctor
    contract; no flag or JSON envelope was added, retired, or renamed, so the
    `macos-agent` floor remains `>= 1.22.6`
    ([#1247](https://github.com/sympoies/nils-cli/pull/1247)).
  - All other changes are lockstep release-version and generated third-party
    metadata updates; no other `required_clis[]` floor moves.
- `v1.22.6` advances the pin from `v1.22.3`, folding in
  `v1.22.4`–`v1.22.5`:
  - `macos-agent` replaces the custom native automation engine with a guarded
    adapter around locked Peekaboo `v3.9.3`. Runtime-kit now consumes backend
    install/verify/rollback, strict doctor and capabilities, local/SSH exec and
    scenarios, stdio MCP profiles, and journal/redaction/guarded-replay v2, so
    the `macos-agent` floor moves to `>= 1.22.6`
    ([#1234](https://github.com/sympoies/nils-cli/pull/1234)).
  - `agent-runtime prune-stale` adds repeatable
    `--owned-source-root <ABSOLUTE_PATH>` ownership authorities with fail-closed
    root/link-map validation and additive JSON v1 reporting. Runtime-kit's
    portable convergence flow consumes this flag for relocated-checkout stale
    helper cleanup, so the `agent-runtime` floor moves to `>= 1.22.6`
    ([#1245](https://github.com/sympoies/nils-cli/pull/1245)).
  - `agent-session` deletion and exact provider-attention handling,
    `agent-memory` promotion-frontmatter repair, and atomic encrypted `secrets`
    staging are additive or unconsumed by this repo's governed public surfaces;
    no other `required_clis[]` floor moves.
- `v1.22.3` advances the pin from `v1.21.39`, folding in
  `v1.22.0`–`v1.22.2`:
  - `agent-session` makes session deletion fail closed unless termination is
    verified, adds structured title state, corrects title-reference token
    boundaries, freezes pane cgroups before deletion, and handles blank
    stopped-tmux probes
    ([#1218](https://github.com/sympoies/nils-cli/pull/1218),
    [#1221](https://github.com/sympoies/nils-cli/pull/1221),
    [#1225](https://github.com/sympoies/nils-cli/pull/1225),
    [#1224](https://github.com/sympoies/nils-cli/pull/1224),
    [#1228](https://github.com/sympoies/nils-cli/pull/1228)). Runtime-kit does
    not consume `agent-session`, so no `required_clis[]` floor moves.
  - All other crate changes are lockstep release-version or CI metadata
    updates; no runtime-kit-consumed flag or JSON envelope was retired or
    renamed.
- `v1.21.39` advances the pin from `v1.21.34`, folding in
  `v1.21.35`–`v1.21.38`:
  - `agent-session` adds durable startup-failure reporting and per-session
    Codex account binding, then hardens audited-runtime compatibility, bound
    thread selection, launch arguments, and account-bound create timing
    ([#1204](https://github.com/sympoies/nils-cli/pull/1204),
    [#1206](https://github.com/sympoies/nils-cli/pull/1206),
    [#1207](https://github.com/sympoies/nils-cli/pull/1207),
    [#1209](https://github.com/sympoies/nils-cli/pull/1209),
    [#1211](https://github.com/sympoies/nils-cli/pull/1211),
    [#1213](https://github.com/sympoies/nils-cli/pull/1213),
    [#1215](https://github.com/sympoies/nils-cli/pull/1215)). Runtime-kit does
    not consume `agent-session`, so no `required_clis[]` floor moves.
  - All other crate changes are lockstep release-version updates; no
    runtime-kit-consumed flag or JSON envelope was retired or renamed.
- `v1.21.34` advances the pin from `v1.21.24`, folding in
  `v1.21.25`–`v1.21.33`:
  - `forge-cli` adds the read-only `pr reviews` snapshot and config-gated
    observed review convergence to `pr merge` and `pr deliver`. The gate reads
    native current- and stale-head reviews, treats summaries as evidence rather
    than verdicts, enforces native change requests plus existing thread/task
    gates, waits only after a configured observed bot appears, performs a final
    recheck, and binds merge to the provider head. Runtime-kit's three
    merge-owning delivery outcomes now consume the read surface and typed retry
    contract, so their `forge-cli` floor moves to `>= 1.21.34`
    ([#1201](https://github.com/sympoies/nils-cli/pull/1201)).
  - `macos-agent` reconciles its screenshot preflight probe with the installed
    helper contract ([#1194](https://github.com/sympoies/nils-cli/pull/1194)).
    The Computer Use skill already consumes that command, and no flag or output
    envelope changed, so its floor remains `>= 1.21.13`.
  - `codex-cli` and `claude-cli` stop rendering expired quota-cache values
    ([#1177](https://github.com/sympoies/nils-cli/pull/1177)); `fzf-cli` can
    index configurable definition roots
    ([#1196](https://github.com/sympoies/nils-cli/pull/1196)); and the folded
    releases harden provider resume, fresh-thread prompt submission, release
    preparation, and agent-session input/capability bounds. Runtime-kit does
    not consume a new command or envelope from those changes, so no other
    `required_clis[]` floor moves.
- `v1.21.24` advances the pin from `v1.21.23`:
  - `plan-issue record close` now preflights repository label catalogs,
    normalizes lifecycle state labels with provider-aware identity rules,
    verifies label read-back, and compensates pre-close failures without
    erasing concurrent automation labels. `forge-cli label list` now honors
    GitLab's provider page cap while satisfying larger total limits
    ([#1170](https://github.com/sympoies/nils-cli/pull/1170)). Runtime-kit
    consumes these existing closeout and label-list contracts, but no flag or
    JSON envelope was retired or renamed, so their floors do not move.
  - `agent-session` fixes fresh Codex app-server session creation
    ([#1172](https://github.com/sympoies/nils-cli/pull/1172)). Runtime-kit does
    not consume `agent-session`, so no `required_clis[]` row is added.
- `v1.21.23` advances the pin from `v1.21.22`:
  - `plan-issue` structurally parses visible review dispositions, aligns
    dispatch closeout headings and close-ready validation, verifies provider
    label mutations, and synchronizes terminal execution state. `plan-tooling`
    hardens terminal section bounds and completion writeback. Runtime-kit
    consumes these existing lifecycle contracts, but no flag or JSON envelope
    was retired or renamed, so their floors do not move.
  - `agent-session` adds private Codex app-server auto-resume and revisioned
    title updates, while `codex-cli` accepts optional rate-limit windows and
    preserves no-window fallback state. Runtime-kit does not consume a new
    command from either surface, so no `required_clis[]` row is added.
- `v1.21.22` advances the pin from `v1.21.21`:
  - `agent-memory archive` adds a dry-run-first inactive-memory archive with
    atomic writes, source/provenance validation, stale-recovery refusal, and
    active-recall separation
    ([#1155](https://github.com/sympoies/nils-cli/pull/1155)). Runtime-kit does
    not consume this new command yet, so the `agent-memory` floor remains
    `>= 1.21.21`.
  - `forge-cli` now validates strict delivery labels before any preview or live
    provider operation; `plan-issue tracking run init --dry-run` is fully
    non-mutating and rejects unsafe run/repository identifiers; and
    `heuristic-inbox` ignores generated manual placeholders when checking
    duplicate identities. These harden existing contracts without retiring or
    renaming any runtime-kit-consumed flag or JSON envelope, so no
    `required_clis[]` floor moves.
- `v1.21.21` advances the pin from `v1.21.19`, folding in `v1.21.20`:
  - `agent-memory` adds bounded `recall startup`, curated
    `recall on-demand`, explicitly untrusted candidate recall, producer-isolated
    candidate add/list, and dry-run-first rollback-safe promotion. Strict
    checks add index-byte budgets and caller-owned forbidden-term files
    ([#1143](https://github.com/sympoies/nils-cli/pull/1143)). Runtime-kit now
    consumes startup recall in the Codex hook and the generic retired-memory
    audit, so the `agent-memory` floor moves to `>= 1.21.21`.
  - The release preserves the human CLI and adds versioned JSON runtime-error
    envelopes, required promotion provenance, supported global symlink
    compatibility, metadata-injection guards, and native candidate-index
    cleanup. No consumed surface was retired.
  - Folded `v1.21.20` changes agent-session and forge/test-first subject
    binding; runtime-kit does not consume a new flag or envelope from those
    changes, so no other `required_clis[]` floor moves.
- `v1.21.19` advances the pin from `v1.21.15`, folding in `v1.21.16`–`v1.21.18`:
  - `test-first-evidence` replaces the v1 red/green minimum with a durable v2
    contract: contract delta, grouped affected-test dispositions, meaningful
    expected/observed red, typed waivers, ordered scoped final-validation
    attempts, explicit residual gaps, and strict pre-edit/delivery checks.
    Record v1 remains readable but is rejected by strict delivery. `forge-cli`
    feature/bug create, adopt, dry-run, and deliver consume strict v2 while the
    opt-in config precedence and exempt kinds remain unchanged
    ([#1125](https://github.com/sympoies/nils-cli/pull/1125)). Runtime-kit's
    implementation and delivery parents consume the `test-first-evidence` CLI,
    so that binary and the retained parent delivery outcomes' `forge-cli`
    floors move to `>= 1.21.19` without re-exposing an evidence skill.
  - The folded releases add provider failure classification and agent-session
    control-plane/activity correctness. Runtime-kit does not consume those
    provider/agent-session surfaces, so no other floor moves.
- `v1.21.17` advances the pin from `v1.21.15` for the durable agent control
  plane ([#1117](https://github.com/sympoies/nils-cli/pull/1117)):
  - `agent-docs session activate/status/verify` persists selective intent state
    by repository, product, and opaque session identifier; shared path classes
    provide deterministic pre-edit classification.
  - `docs-impact` gains durable record/show/verify flows,
    `test-first-evidence check` gains classified/pre-edit/delivery phases, and
    `skill-usage` v2 generalizes ownership to skills, workflows, and intents
    while preserving v1 readers.
  - `evidence` migration and `heuristic-inbox` promotion accept mixed v1/v2
    usage owners, and runtime installation receipts gain focused doctor
    verification. Runtime-kit consumes the first two groups and the mixed-owner
    archive/closeout path in the Browser/Evidence control plane.
- `v1.21.15` advances the pin from `v1.21.14`:
  - `agent-runtime` accepts skills manifest schema v2 while preserving v1,
    validates invocation role, exposure, compatibility, and pending-disposition
    metadata, and reports that metadata through deterministic three-product
    `list-skills --format json` output
    ([#1111](https://github.com/sympoies/nils-cli/pull/1111)). Runtime-kit now
    consumes this parser for its active catalog, so the `agent-runtime` floor
    and the three product skill-render surface floors move to `>= 1.21.15`.
  - The remaining release change adjusts `agent-session` Claude prompt and
    usage-deadline handling ([#1109](https://github.com/sympoies/nils-cli/pull/1109));
    runtime-kit does not consume `agent-session`, so no additional floor moves.
- `v1.21.14` advances the pin from `v1.21.13`: `plan-issue tracking
  close-ready` and `record close` now share the same strict review-finding
  evaluation, so a residual blocker or major finding returns
  `review-unresolved-findings` before the mutating close step. Runtime-kit
  consumes both lifecycle gates, but the fix aligns their existing contracts
  and retires or renames no consumed flag or JSON envelope
  ([#1105](https://github.com/sympoies/nils-cli/pull/1105)). No
  `required_clis[]` floor changes.
- `v1.21.13` advances the pin from `v1.21.11`, folding in `v1.21.12`:
  - `macos-agent` adds standalone `input key`, pointer `move`, bounded `drag`,
    and horizontal/vertical `scroll`, plus modifier-assisted click/drag/scroll,
    correct named-key AppleScript key codes, absolute negative coordinates for
    secondary displays, one-process repeated keypresses, bounded drag timeout
    validation, and best-effort held-input cleanup on backend failure
    ([#1106](https://github.com/sympoies/nils-cli/pull/1106)). The new
    `computer-use.macos-desktop` skill consumes these surfaces, so
    `required_clis[]` adds `macos-agent >=1.21.13`.
  - `v1.21.12` changes only `agent-session` provider turn-signal handling.
    Runtime-kit does not consume `agent-session`, and no other consumed flag or
    JSON envelope was retired or renamed.
- `v1.21.11` advances the pin from `v1.21.9` (folding in the version-only
  `v1.21.10`): the `agent-session` Claude provider-hook adapter drops the
  `approval` attention when the hook payload `permission_mode` is
  `bypassPermissions`, so a bypass session no longer latches `needs_input` on an
  approval that has no clear event (sympoies/nils-cli#1101). No
  downstream-consumed CLI surface changed.
- `v1.21.9` advances the pin from `v1.21.0`, folding in the `v1.21.1`–`v1.21.9`
  releases:
  - `codex-cli` and `claude-cli` each gain `agent resume <SESSION_ID> [--cd <dir>]`,
    a foreground wrapper that resolves the recorded working directory from local
    session metadata and relaunches the provider there (`codex resume <id> --cd
    <cwd> --no-alt-screen`; `claude --resume <id>` launched in `<cwd>`). The
    bounded session-history scan, `session_meta` / transcript parsing, scan
    budgets, and structured resolve outcomes are shared through a new
    `nils-provider-resume` library crate that `agent-session` also delegates to
    (sympoies/nils-cli#1094, #1096).
  - `agent-session` adds terminal-activity timestamps, Claude input-attention
    correlation, and durable provider turn state to its session / serve surfaces
    (sympoies/nils-cli#1091, #1093, and follow-ups).
  - The remaining changes (`codex-cli diag rate-limits --all` and its auth.json
    diagnostics contract, a `git-cli` internal `open` change, a `claude-cli`
    usage prompt segment, and nils-cli-internal test / CI wiring) touch no
    consumed surface.
  Runtime-kit does not consume `agent-session`, `codex-cli`, or `claude-cli` in
  required skill flows, and the `git-cli` / `forge-cli` changes retire or rename
  no consumed flag or JSON envelope, so no `required_clis[]` floor changes. The
  new `nils-provider-resume` crate is library-only and never appears in
  `required_clis[]`.
- `v1.21.0` advances the pin from `v1.20.20`:
  - `forge-cli` now routes every GraphQL-backed op through a single
    rate-limit-gated runner factory (`default_runner()`), extending the
    v1.20.20 rate-limit gate (#1061) from the PR-lifecycle verbs to all
    GraphQL-backed calls and closing the classifier-vs-wiring drift that
    per-op runner construction allowed (sympoies/nils-cli#1063).
  The change is internal hardening of `forge-cli`: it retires or renames no
  consumed flag or JSON envelope, so no `required_clis[]` floor changes. The
  remaining v1.21.0 changes are nils-cli-internal (project skill test/CI
  wiring, dead-test removal) and touch no consumed surface.
- `v1.20.20` advances the pin from `v1.20.19`:
  - `forge-cli pr deliver` adds a best-effort post-merge `issue_closeout` step
    that deterministically closes any still-open issue referenced by a
    `Closes/Fixes #N` closing keyword, instead of depending on GitHub's
    asynchronous merge auto-close (confirmed latency, not a linkage gap).
    `pr view` now exposes `closing_issue_refs` (GitHub `closingIssuesReferences`;
    empty on GitLab / for non-closing `Refs #N`), a new `--no-issue-closeout`
    flag opts out, and a new `cli.forge-cli.issue.closeout.v1` envelope reports
    per-issue `closed` / `already_closed` / `error` outcomes
    (sympoies/nils-cli#1060).
  - `forge-cli` gates GraphQL-backed calls on the rate-limit budget so tight CI
    polling no longer trips GitHub secondary limits (sympoies/nils-cli#1061).
  The `deliver-pr` skill consumes `forge-cli pr deliver`, but every change is
  purely additive (an optional post-merge step, a new field, a new opt-out
  flag, a new envelope) and retires or renames no consumed flag or JSON
  envelope, so no `required_clis[]` floor changes. Non-closing `Refs #N`
  plan-tracking flows are untouched (empty `closingIssuesReferences`).
- `v1.20.19` advances the pin from `v1.20.17`, folding in `v1.20.18` and
  `v1.20.19`:
  - `agent-session` adds optional `last_terminal_activity_at` to session view
    and glance JSON output by deriving tmux `window_activity`, so clients can
    distinguish terminal activity freshness from control-plane updates without
    storing terminal bytes (sympoies/nils-cli#1043).
  - `forge-cli pr checks` / `pr wait-checks` handles GitHub App
    `statusCheckRollup` permission failures by avoiding the unreadable GraphQL
    rollup projection and falling back to REST check-runs/statuses for the PR
    head commit, with fail-closed handling for truncated pages
    (sympoies/nils-cli#1044).
  Runtime-kit does not consume `agent-session`, and the `forge-cli` change
  hardens existing PR checks behavior without retiring or renaming a consumed
  flag or JSON envelope, so no `required_clis[]` floor changes.
- `v1.20.17` advances the pin from `v1.20.16`:
  - `agent-session serve` gains a read-only `GET /sessions/{id}/buffer` that
    returns the session server's tmux paste buffer (`tmux show-buffer`), so a
    browser edge can copy the on-screen selection a live mouse-reporting TUI
    never exposes to the DOM (sympoies/nils-cli#1037).
  Runtime-kit still does not consume `agent-session`, and the new endpoint is
  purely additive, so no `required_clis[]` floor changes.
- `v1.20.16` advances the pin from `v1.20.14`, folding in the `v1.20.15` and
  `v1.20.16` releases:
  - `agent-session` gains an opt-in `AGENT_SESSION_TMUX_SCOPE` that launches each
    tmux server inside its own transient systemd user scope
    (`systemd-run --user --scope`) so it escapes the serve service cgroup and
    survives a daemon restart or cgroup-wide kill (sympoies/nils-cli#1035), plus
    a fix that backfills late Codex resume metadata (sympoies/nils-cli#1033).
  - `forge-cli` hardens PR check polling and head validation
    (sympoies/nils-cli#1032).
  Runtime-kit still does not consume `agent-session`, and the `forge-cli` change
  is a behavior hardening that neither retired nor renamed a consumed flag or
  JSON envelope, so no `required_clis[]` floor changes.
- `v1.20.13` advances the pin from `v1.20.7`, folding in the `v1.20.8` through
  `v1.20.13` releases. The release burst expands the new `agent-session` binary
  with send/glance, Hermes interactive sessions, the authenticated serve
  daemon, WebSocket attach, workdir search, title and attachment routes, curated
  repo picker results, and durable resume metadata
  (sympoies/nils-cli#1013, #1015, #1017, #1019, #1021, #1023), plus dependency,
  completion, third-party-artifact, and routine version-bump commits
  (sympoies/nils-cli#1008, #1011, #1012, #1014, #1016, #1018, #1020, #1022,
  #1024). Runtime-kit still does not consume `agent-session`; no consumed
  runtime-kit flag or JSON envelope moved, so no `required_clis[]` floor
  changes.
- `v1.20.7` advances the pin from `v1.20.6`. It fixes `plan-issue` closeout
  writeback autolinking for linked PR URLs (sympoies/nils-cli#1007), adds the
  new `agent-session` tmux-backed helper binary (sympoies/nils-cli#1009), and
  carries the routine version bump (sympoies/nils-cli#1010). Runtime-kit does
  not consume the new `agent-session` surface and no existing consumed flag or
  JSON envelope moved, so no `required_clis[]` floor changes.
- `v1.20.6` advances the pin from `v1.20.5` (same-day release burst). The change
  is `agent-memory` / `secrets` dynamic completion (sympoies/nils-cli#1004) plus
  the routine version bump; no runtime-kit-consumed surface moved — byte-identical
  render, zero golden churn, no `required_clis[]` floor change.
- `v1.20.5` advances the runtime-kit host pin from `v1.20.1`, folding in the
  `v1.20.2`–`v1.20.5` releases. The headline change is `git-cli` dynamic
  worktree completion via `CompleteEnv` (sympoies/nils-cli#999, #1002); the rest
  are routine cli version bumps and dependency / licensing housekeeping. No
  runtime-kit-consumed surface (flags or JSON envelopes) changed: the `v1.20.5`
  render output is byte-identical to `v1.20.1` (zero golden churn) and no
  `required_clis[]` floor moved.
- `v1.20.1` advances the runtime-kit host pin from `v1.20.0`. It completes the
  hermes product target across the remaining subcommands —
  `list-skills --product hermes` and `prune-stale --product hermes` previously
  rejected the product, which blocked `sync-runtime-surfaces --product hermes`
  (its prune step) and the sandbox-install rehearsal's hermes arm — adds
  **Hermes** to the `SUPPORT_MATRIX` header, and bumps `anyhow` to clear
  `RUSTSEC-2026-0190` (sympoies/nils-cli#993).
- `v1.20.0` advances the runtime-kit host pin from `v1.19.3` and adds **hermes**
  as a third render product target: `agent-runtime render --product hermes`,
  `render --target support-matrix` with a hermes column, and `doctor` /
  `gc-backups` product handling (sympoies/nils-cli#991). The
  surfaces / skills / runtime-roots / product-capabilities deserializers accept
  a `hermes` product key; `surfaces` keeps it optional, the others require it.
  (`list-skills` / `prune-stale` hermes handling landed in `v1.20.1`.)
- `v1.19.3` advances the runtime-kit host pin from `v1.19.2` and adds the
  reviewed `agent-out cleanup plan/apply` workflow for cleaning stale
  `agent-out` data without deleting retained evidence or project artifacts by
  accident. Consumer-visible changes:
  - `agent-out cleanup plan [--include-projects] --format text|json` scans the
    `agent-out` root, classifies entries as `delete`, `preserve`, or
    `needs-policy`, emits `cli.agent-out.cleanup.plan.v1`, and includes a
    `plan_digest` for review handoff.
  - `agent-out cleanup apply --plan-file <path> --confirm-digest <digest>`
    verifies the plan digest, agent home / out root, containment, safe delete
    shape, and evidence markers before deleting only eligible rows; it emits
    `cli.agent-out.cleanup.apply.v1`.
  - Runtime-kit consumes this surface through policy-owned artifact cleanup
    and deterministic runtime smoke, so the `agent-out` floor moves to
    `>=1.19.3` ([#987](https://github.com/sympoies/nils-cli/pull/987)).
- `v1.19.2` advances the runtime-kit host pin from `v1.19.1` and restores the
  `agent-out path-for` compatibility command generated by runtime-kit
  `state_out(...)` helpers. Reporting skills already render `agent-out
  path-for` instructions, so their `agent-out` floor moves to `>=1.19.2`, and
  `agent-out` is now part of the required CLI surface.
  Consumer-visible changes:
  - `agent-out path-for --domain <domain> [--topic <topic>]` returns canonical
    project-scoped artifact paths through the existing `agent-out project`
    allocator, supports `path` / `json` / `env` output, accepts repo paths or
    `owner/repo` slugs, and emits `cli.agent-out.path-for.v1` JSON
    ([#984](https://github.com/sympoies/nils-cli/pull/984)).
  - Codex auth integration tests and completion flag parity audits changed
    upstream in the same release range, but runtime-kit consumes no additional
    CLI surface from those changes
    ([#980](https://github.com/sympoies/nils-cli/pull/980),
    [#981](https://github.com/sympoies/nils-cli/pull/981),
    [#982](https://github.com/sympoies/nils-cli/pull/982),
    [#983](https://github.com/sympoies/nils-cli/pull/983)).
- `v1.19.1` advances the runtime-kit host pin from `v1.18.8` and restores a
  monotonic released host baseline after the `v1.19.0` / `v1.18.8` release
  ordering overlap. The CLI surface diff from `v1.18.8` to `v1.19.1` is
  release metadata only, so no `required_clis[]` floor moves; the exact
  `pinned_tag` gate now covers host alignment with `v1.19.1`. Consumer-visible
  changes retained by this pin:
  - `codex-cli prompt-segment` now retries target auth after a rate-limit HTTP
    401 when `CODEX_AUTO_REFRESH_ENABLED` is enabled, suppresses auth-refresh
    chatter in prompt output, and detaches the Unix background refresh worker
    from the prompt shell process group so Starship shell teardown does not
    kill cache writeback
    ([#972](https://github.com/sympoies/nils-cli/pull/972),
    [#976](https://github.com/sympoies/nils-cli/pull/976)). This restores
    stale prompt rendering as a one-prompt event: the stale render schedules a
    background refresh, and a later prompt can read the fresh cache.
  - `forge-cli pr review validate` adds additive preflight coverage for review
    summaries, thread-file shape, and GitHub diff coordinates
    ([#973](https://github.com/sympoies/nils-cli/pull/973)). Runtime-kit still
    consumes the native review `--thread-file` posting surface introduced in
    `v1.17.0`; it does not consume the new validate subcommand, so the
    `forge-cli` floor stays at `>= 1.17.0`.
- `v1.18.6` advances the runtime-kit host pin from `v1.17.0` through the
  `v1.18.x` Codex auth hardening releases. Runtime-kit does not consume a new
  CLI flag or JSON envelope from this range, so no `required_clis[]` floor
  moves; the exact `pinned_tag` gate now covers host alignment with `v1.18.6`.
  Consumer-visible changes:
  - `codex-cli` remote auth sync is now target-aware for the active auth file
    or secret-file target before falling back to `CODEX_AUTH_REMOTE_NAME`,
    rate-limit 401 retries use access-only remote exports, and `codex-cli
    agent` preflights remote auth before invoking the upstream `codex exec`
    ([#953](https://github.com/sympoies/nils-cli/pull/953),
    [#956](https://github.com/sympoies/nils-cli/pull/956),
    [#959](https://github.com/sympoies/nils-cli/pull/959),
    [#965](https://github.com/sympoies/nils-cli/pull/965),
    [#968](https://github.com/sympoies/nils-cli/pull/968)). This supports
    background prompt/rate-limit sync for active stale tokens without changing
    runtime-kit templates or golden render outputs.
  - `forge-cli pr review` classifies GitHub native review HTTP 422 responses
    as typed actionable errors while preserving backend detail
    ([#962](https://github.com/sympoies/nils-cli/pull/962)). Runtime-kit
    already consumes the native review/thread-file surface from `v1.17.0`; this
    release hardens failure reporting only.
- `v1.17.0` is a lock-step minor over `v1.16.0`. Runtime-kit now consumes the
  GitHub-only `forge-cli pr review --thread-file` surface for actionable review
  findings ([#951](https://github.com/sympoies/nils-cli/pull/951)). With
  `--submit-review`, a JSON spec array creates native, resolvable GitHub review
  threads (`path`, optional `line` / `startLine`, `side`, `subjectType`, and
  `body`) under the same pull-request review event as the summary body. Agents
  should use this only for findings that require a code/doc change and can be
  resolved after the owner handles them; clean or informational reviews keep the
  existing summary-only review body with no `--thread-file`.
  The CLI enforces pre-mutation validation (`invalid_review_thread_spec` for
  malformed, empty, oversized, or too-many specs), privacy guards, and
  best-effort cleanup of pending GitHub reviews after thread or submit failures.
  Runtime-kit provider-writing review workflows consume this surface, so the
  `forge-cli` floor moves to `>= 1.17.0`; the exact `pinned_tag` gate now covers
  host alignment with `v1.17.0`.
- `v1.16.0` is a lock-step minor over `v1.15.0`. It adds
  `forge-cli pr review --submit-review`, which posts a native GitHub
  pull-request review event (`#pullrequestreview-`) authored by the active
  provider identity — mapping `--decision` to a `COMMENT` / `APPROVE` /
  `REQUEST_CHANGES` review event — instead of an issue-style outcome comment
  (GitHub-only; GitLab keeps the outcome-note form)
  ([#947](https://github.com/sympoies/nils-cli/pull/947)). The review posting
  contract and portable identity boundary that consume this flag land in a separate
  runtime-kit change, so this pin bump moves no `required_clis[]` floor — the
  `forge-cli` floor still records the minimum currently-consumed surface and
  the exact `pinned_tag` gate (now `v1.16.0`) covers the host.
- `v1.15.0` is a lock-step minor over `v1.14.0`. It adds the `agent-memory`
  `check`, `add`, `list --json`/`--type`, and `search` subcommands
  ([#941](https://github.com/sympoies/nils-cli/pull/941),
  [#942](https://github.com/sympoies/nils-cli/pull/942)). Runtime-kit does not
  consume these yet (the memory cue hook still only runs `agent-memory index
  global`), so no `required_clis[]` floor moves — the exact `pinned_tag` gate
  (now `v1.15.0`) covers the host.
- `v1.14.0` is a lock-step minor over `v1.13.0`. Runtime-kit does not consume
  a new CLI flag or JSON envelope from this release, so no `required_clis[]`
  floor moves — the exact `pinned_tag` gate (now `v1.14.0`) covers the host.
  Consumer-visible changes:
  - `forge-cli pr review` keeps the `v1.13.0` outcome-posting surface but
    hardens guard, dry-run, issue-mirror, and GitLab fallback behavior across
    GitHub/GitLab providers ([#922](https://github.com/sympoies/nils-cli/pull/922),
    [#923](https://github.com/sympoies/nils-cli/pull/923),
    [#924](https://github.com/sympoies/nils-cli/pull/924),
    [#925](https://github.com/sympoies/nils-cli/pull/925)).
  - `agent-runtime render` swaps the internal template engine from Tera to
    Minijinja while preserving the existing runtime-kit render contract
    ([#931](https://github.com/sympoies/nils-cli/pull/931)).
  - REST/websocket/gRPC test helpers, `github-app-cli`, dependency policy,
    crate-standard docs, and CI retry behavior changed upstream but do not add
    a runtime-kit-consumed surface ([#926](https://github.com/sympoies/nils-cli/pull/926),
    [#927](https://github.com/sympoies/nils-cli/pull/927),
    [#929](https://github.com/sympoies/nils-cli/pull/929),
    [#930](https://github.com/sympoies/nils-cli/pull/930),
    [#932](https://github.com/sympoies/nils-cli/pull/932),
    [#933](https://github.com/sympoies/nils-cli/pull/933),
    [#935](https://github.com/sympoies/nils-cli/pull/935)).
- `v1.13.0` is a lock-step minor over `v1.12.1`. Runtime-kit now consumes the
  `forge-cli pr review` outcome-posting primitive, so the `forge-cli` floor
  moves to `>= 1.13.0`; the exact `pinned_tag` gate (now `v1.13.0`) remains
  the primary host gate. Consumer-visible changes:
  - `forge-cli`: `pr review <id>` posts a PR/MR review outcome comment with
    `--decision comments-only|approve|request-changes`, `--comment` or
    `--comment-file`, repeatable `--lens`, and optional `--issue
    --mirror-issue` for a compact issue activity breadcrumb. The primitive
    intentionally records outcome comments only; native provider approve /
    request-changes state mutation stays out of scope ([#920](https://github.com/sympoies/nils-cli/pull/920)).
- `v1.12.1` is a lock-step patch over `v1.12.0`. Runtime-kit now consumes the
  product-scoped agent-docs resolver and the per-product home-prompt render
  target, so the `agent-docs` and `agent-runtime` floors move to `>= 1.12.1`;
  the exact `pinned_tag` gate (now `v1.12.1`) remains the primary host gate.
  Consumer-visible changes:
  - `agent-docs`: `[[document]]` and `[[validation]]` entries accept
    `product = "codex"` / `"claude"` or a product list; `preflight`, `audit`,
    `explain`, and `list` accept `--product codex|claude`; the resolver filters
    documents and validation contracts consistently; and preflight JSON now
    reports `agent-docs.preflight.v2` plus product scope
    ([#918](https://github.com/sympoies/nils-cli/pull/918)).
  - `agent-runtime`: `render --target home-prompt` writes
    `build/<product-or-neutral>/AGENT_HOME.md`, enabling runtime-kit to symlink
    Codex and Claude home prompts to product-specific rendered outputs instead
    of the raw source file ([#918](https://github.com/sympoies/nils-cli/pull/918)).
- `v1.12.0` is a lock-step minor over `v1.11.2`. Runtime-kit now consumes the
  new `evidence prune-source` source-cleanup surface, so the `evidence` floor
  moves to `>= 1.12.0`; the exact `pinned_tag` gate (now `v1.12.0`) remains the
  primary host gate. Consumer-visible change:
  - `v1.12.0`: `evidence prune-source --archived-only` scans agent-out
    `skill-usage.record.json` source run directories, computes each raw source
    digest, and prunes only records whose digest already exists in the archive
    `catalog.json`; dry-run is default, and `--apply` deletes the local source
    run directory while leaving the archive read-only
    ([#916](https://github.com/sympoies/nils-cli/pull/916)). The new
    policy-owned evidence cleanup owns direct dry-run/confirmation usage and
    session closeout runs it after retention so archived local source records
    do not accumulate indefinitely.
- `v1.11.2` is a lock-step patch over `v1.11.1`. No consumed flag or JSON
  envelope changed, but runtime-kit skills invoke `forge-cli` with explicit
  provider selection and rely on the release's fork-safe remote-derived repo
  targeting. The `forge-cli` floor moves to `>= 1.11.2`; the exact
  `pinned_tag` gate (now `v1.11.2`) remains the primary host gate.
  Consumer-visible change:
  - `v1.11.2`: `forge-cli` now derives the repo slug from the detected remote
    and pins `--repo <owner/name>` on backend calls by default
    ([#912](https://github.com/sympoies/nils-cli/pull/912)). Previously it
    omitted `--repo`, letting `gh`/`glab` re-derive the repo from the cwd, which
    silently retargeted a fork clone to its upstream parent. An explicit
    `--repo` still wins. Side effect: GitLab `pr checks` for a branch now prefers
    the structured `glab api` merge-requests path (fork-safe) over the text
    `glab ci status` parser, falling back to text when no MR exists.
- `v1.11.1` is a lock-step patch over `v1.11.0`. No consumed flag or JSON
  envelope changed, so no `required_clis[]` floor moves — the exact
  `pinned_tag` gate (was `v1.11.1`) covers the `agent-runtime` host.
  Consumer-visible change:
  - `v1.11.1`: `github-app-cli token` regression fix,
    [#910](https://github.com/sympoies/nils-cli/pull/910). jsonwebtoken 10's
    split crypto backend left RS256 App-JWT signing with no provider selected
    (`default-features = false`), so `github-app-cli token` panicked at runtime
    on `v1.11.0` and every bot-routed forge-cli op silently fell back to the
    user. Enabling the `rust_crypto` backend restores App installation-token
    minting. `github-app-cli` is not a `required_clis[]` entry (the bot
    identity layer lives in local-scripts, not this kit), so no floor moves.
- `v1.11.0` is a lock-step host bump over `v1.10.0`. No consumed flag or JSON
  envelope was retired or renamed, so no `required_clis[]` floor moves — the
  exact `pinned_tag` gate (was `v1.11.0`) covers the `agent-runtime` host.
  Consumer-visible changes:
  - `v1.11.0`: `forge-cli issue close` gains an optional
    `--reason completed|"not planned"` flag (GitHub backend; GitLab / Local
    ignore it), [#908](https://github.com/sympoies/nils-cli/pull/908). Purely
    additive — it closes the `deliver-closeout-cli-surface-drift` inbox gap
    where `forge-cli issue close` lacked `--reason` and closeout fell back to
    `gh issue close --reason`. The `forge-cli` floor stays `>= 1.9.1` (no
    consumer requires the new flag yet).
  - `v1.11.0`: `plan-issue` consolidated all GitHub provider ops onto
    `forge-cli`, retiring its in-crate `gh` client
    (`crates/plan-issue/src/github.rs`). `forge-cli` is now the single
    provider gateway for GitHub, GitLab, and Local. plan-issue's external CLI
    surface (`record` / `tracking` / `start-*` commands) is unchanged, so the
    `plan-issue` floor stays `>= 1.1.0`. One behavior change: plan-issue
    `--force` no longer bypasses the escaped-control markdown guard on the
    GitHub write path (stricter, not looser); the never-bypassed local-path
    guard is unchanged.
- `v1.10.0` is a lock-step host bump over `v1.9.6`. It adds one new crate and
  carries the routine all-crates version bump; no consumed flag or JSON
  envelope was retired or renamed, so no `required_clis[]` floor moves — the
  exact `pinned_tag` gate (now `v1.10.0`) covers the `agent-runtime` host. The
  one consumer-visible change:
  - `v1.10.0`: adds the `secrets` binary (new `nils-secrets` crate, binary
    `secrets`, [#907](https://github.com/sympoies/nils-cli/pull/907)) — a thin
    wrapper over `sops` + `git` that pulls / pushes a repo's `.env` from the
    central `graysurf/secrets` SOPS store (`pull` / `add` / `list` / `which` /
    `edit` / `completion`), mapping the repo's `origin` to a store entry.
    stdout and the JSON envelope (`cli.secrets.<command>.v1`) carry only
    metadata; decrypted values are written to `./.env` (mode 600) and never
    echoed. Not consumed by any runtime-kit skill flow — driven out-of-band by
    the private `private-secrets` skill — so it never appears in
    `required_clis`.
- `v1.9.6` is a lock-step host bump over `v1.9.1` (covers `v1.9.2`–`v1.9.6`).
  No consumed flag or JSON envelope was retired or renamed, so no
  `required_clis[]` floor moves — the exact `pinned_tag` gate (now `v1.9.6`)
  covers the `agent-runtime` host. Consumer-visible changes across the span:
  - `v1.9.2`: `forge-cli` review-thread commands hardened (behavioral; the
    `pr review-threads list` / `resolve` / `reply` shape from `v1.9.1` is
    unchanged, so the `forge-cli` floor stays `>= 1.9.1`). `codex-cli auth`
    auto-refresh is now gated behind an env opt-in (`CODEX_AUTO_REFRESH_ENABLED`).
  - `v1.9.3`: `codex-cli auth` gains remote pull over SSH (additive subcommand).
  - `v1.9.4`: `codex-cli auth` remote-pull JSON-error hardening.
  - `v1.9.5`: docs-only (genericize example fixtures); no surface change.
  - `v1.9.6`: adds the `github-app-cli` binary (new `nils-github-app-cli`
    crate, [#903](https://github.com/sympoies/nils-cli/pull/903)) for minting
    GitHub App installation access tokens. Not consumed by any runtime-kit
    skill flow — used out-of-band by a local `forge-cli` bot-identity wrapper —
    so no `required_clis[]` floor moves.
- `v1.9.1` is a lock-step host bump over `v1.8.0`. It restructures one surface
  this repo consumes:
  - `forge-cli pr review-threads` becomes a subcommand group. The read surface
    moves from the bare `pr review-threads <id>` form to `pr review-threads
    list <id>` (the bare positional is now rejected), and two GitHub-only write
    subcommands are added: `pr review-threads resolve <pr> --thread <id>`
    (optionally `--note` to reply before resolving, idempotent) and `pr
    review-threads reply <pr> --thread <id>` (reply without resolving); both
    return
    `provider_unsupported` on GitLab / Local. The `deliver-pr` and `close-pr`
    skills and the `review-thread-convergence` policy rewrite their discovery
    invocation to `pr review-threads list`, so the `forge-cli` floor moves to
    `>= 1.9.1` ([#883](https://github.com/sympoies/nils-cli/pull/883),
    [#885](https://github.com/sympoies/nils-cli/pull/885)). v1.9.0 was tagged
    but never published — a `completion-flag-parity-audit --strict` gap in the
    initial subcommand shape was fixed in #885 and superseded by this release.
- `v1.8.0` is a lock-step host bump over `v1.7.1`. It refreshes two surfaces
  this repo consumes:
  - `evidence migrate` tightens cwd/origin and slug matching for repo identity:
    nested source rescue, repointed / ambiguous cwd guards, refined
    cwd-vs-slug matching, and one uniform slug rule across direct and nested
    workspaces. `evidence purge --apply` also hardens destructive-operation
    safety. Policy-owned evidence migration and session closeout consume those
    guarantees, so the `evidence` floor moves to `1.8.0`
    ([#873](https://github.com/sympoies/nils-cli/pull/873),
    [#874](https://github.com/sympoies/nils-cli/pull/874),
    [#877](https://github.com/sympoies/nils-cli/pull/877),
    [#878](https://github.com/sympoies/nils-cli/pull/878),
    [#879](https://github.com/sympoies/nils-cli/pull/879),
    [#880](https://github.com/sympoies/nils-cli/pull/880)).
  - `heuristic-inbox` gains operation-record archive support and keeps retained
    lifecycle status transitions in the CLI primitive. The Heuristic System
    policy and closeout skill now consume operation-record archival through the
    CLI, so the `heuristic-inbox` floor and the heuristic-system
    `min_nils_cli` move to `1.8.0`
    ([#875](https://github.com/sympoies/nils-cli/pull/875)).
  The release bump and hygiene PRs
  ([#881](https://github.com/sympoies/nils-cli/pull/881),
  [#882](https://github.com/sympoies/nils-cli/pull/882)) carry no additional
  consumed surface change.
- `v1.7.1` is a lock-step host bump over `v1.7.0`. One consumed `evidence` fix:
  - `evidence migrate` now home-relativizes an absolute `skill` path before it
    is slugged, so a rollup's `id`, on-disk directory name, and `skill` field
    no longer leak the machine home (an absolute `/Users/<user>/…/SKILL.md`
    previously slugged to `users-<user>-…` in the committed id/dir). An absolute
    path under `$HOME` becomes `~/…`; outside `$HOME` it redacts; a bare id or
    relative render path is unchanged. Policy-owned evidence migration produces
    the archive, so a leak-free archive requires this floor — the `evidence`
    floor moves to `1.7.1` ([#869](https://github.com/sympoies/nils-cli/pull/869)).
  No surface was retired or renamed; the change is internal to rollup
  construction (no new flags), so no other floor moves.
- `v1.7.0` is a lock-step host bump over `v1.6.1`. It extends the `evidence`
  surface the kit's evidence migration and archive policies consume,
  with one newly-required guarantee and one new retention command:
  - `evidence migrate` now **blocks** any record whose resolved host is absent
    from `config/hosts.yaml` (added to the dry-run `blocked` list with a
    "classify it (personal or employer)" reason) instead of silently writing it
    under an unclassified host. This is the implementation half of the kit's
    gamania-safety guarantee — an employer host that has not been classified is
    never archived — so the `evidence` floor moves to `1.7.0`
    ([#865](https://github.com/sympoies/nils-cli/pull/865)).
  - `evidence migrate` gains a `working_repo_roots` identity rescue: a record
    whose recorded `cwd` no longer exists (e.g. a removed agent worktree) is
    recovered by matching its `<owner__repo>` slug against a configured local
    checkout and reading that checkout's `origin`. Only `Unresolvable`
    identities are rescued; `working_repo_roots` is read from the machine-local
    config (empty disables it) ([#866](https://github.com/sympoies/nils-cli/pull/866)).
  - New `evidence purge` subcommand — the retention counterpart to `migrate`.
    Deletes archived evidence for a named scope (`--host` repeatable and/or
    `--class personal|employer`), dry-run by default; `--apply` removes the
    `evidence/<host>/` trees, regenerates the catalog, and commits + pushes. A
    scope is required (no implicit whole-archive purge) and `--apply` refuses a
    dirty archive tree. The primary use is employer `delete-on-termination`
    ([#866](https://github.com/sympoies/nils-cli/pull/866)).
  No consumed surface was retired or renamed (all additive); the `--deep`
  hygiene-audit / completion regen commits ([#859](https://github.com/sympoies/nils-cli/pull/859),
  [#861](https://github.com/sympoies/nils-cli/pull/861),
  [#862](https://github.com/sympoies/nils-cli/pull/862),
  [#867](https://github.com/sympoies/nils-cli/pull/867)) are internal CI / asset
  hardening with no consumer floor move.
- `v1.6.1` is a lock-step host bump over `v1.6.0`. It hardens the
  `evidence migrate` surface the kit's evidence-control-plane policy consumes:
  - `migrate` tightens scrub/path handling and fixes query/catalog/XDG gaps, so
    malformed or partially resolvable records stay in the blocked/skipped
    report instead of aborting the batch, and archive lookup stays consistent
    across the read-only evidence surfaces
    ([#854](https://github.com/sympoies/nils-cli/pull/854)).
  - Resolved cwd identity now wins over an explicit `--host` vouch, preserving
    operator-supplied host overrides for slug-only records without letting them
    override records that already identify their repo from `cwd`
    ([#856](https://github.com/sympoies/nils-cli/pull/856)).
  - Evidence completion text was regenerated for the `--deep` help reword
    ([#857](https://github.com/sympoies/nils-cli/pull/857)), and publish-order
    CI now treats only path dependencies as publish-order edges
    ([#858](https://github.com/sympoies/nils-cli/pull/858)).
  No consumer rewrite is required and no consumed floor moves to `1.6.1`; this
  bump records the already-declared `evidence >= 1.6.0` floor in
  `docs/source/nils-cli-pin.yaml` so the pin manifest matches
  `manifests/skills.yaml`.
- `v1.6.0` is a lock-step host bump over `v1.5.0`. It finalizes the
  `evidence migrate` surface adopted by the evidence-control-plane policy
  (agent-runtime-kit#352) consumes, plus internal release-tooling hardening:
  - `evidence migrate` (dry-run and apply) no longer aborts the batch on a
    single bad record: per-record read / parse / identity / rollup-preparation
    failures are collected in a `blocked` list (`record_path` + `reason`) and
    skipped, so the resolvable records still archive and an all-blocked run is
    a successful no-op. `migrate` also gains `--host <fqdn>`, letting the
    operator vouch for the host of a slug-only record under a multi-host
    `config/hosts.yaml` (validated against it) instead of a `cwd`->`origin`
    derivation that fails for ephemeral worktree cwds
    ([#853](https://github.com/sympoies/nils-cli/pull/853)). The
    evidence migration workflow depends on both the dry-run `blocked` review and the
    `--host` vouch, so the kit's first `evidence` consumer pins
    `evidence >= 1.6.0` (the runtime-kit skill declares the floor; the pin
    manifest mirrors it in the `v1.6.1` bump).
  - Internal release-tooling only, no consumer floor moves: a
    `plan_archive::scrub` compatibility shim re-exports the shared `nils-scrub`
    crate at its original label-free signatures and the crates-io publish order
    lists `nils-scrub` / `nils-evidence` before their dependents
    ([#849](https://github.com/sympoies/nils-cli/pull/849)); a new
    `scripts/ci/publish-order-audit.sh` guards publish-order completeness from
    `cargo metadata` ([#852](https://github.com/sympoies/nils-cli/pull/852)).
  The `nils-evidence` (binary `evidence`) and `nils-scrub` (library only) crate
  rows are added to the Crate → binary table below in this refresh, alongside
  the `evidence` migrate-surface note.
- `v1.5.0` is a lock-step host bump over `v1.4.0`. It ships two new crates for
  the skill-usage evidence archive lifecycle:
  - `nils-evidence` (binary `evidence`): the query/migrate CLI over a durable,
    scrubbed skill-usage evidence archive (migrate / discover / query / search /
    catalog / validate-*), consumed by policy-owned evidence migration
    ([#848](https://github.com/sympoies/nils-cli/pull/848)).
  - `nils-scrub`: the shared secret-scrub library extracted from `plan-archive`
    so both `plan-archive refresh` and `evidence migrate` reuse one v1 pattern
    set + a labelled scrub-log format
    ([#846](https://github.com/sympoies/nils-cli/pull/846)).
  No existing consumed surface was retired or renamed (a new binary plus an
  internal extraction), so no consumer rewrite; the `evidence` floor lands with
  the consuming evidence policy and is mirrored into the pin manifest in
  the `v1.6.1` bump.
- `v1.4.0` is a lock-step host bump over `v1.3.1`, carrying one consumed
  additive surface change plus pre-released fixes:
  - `skill-usage` records now carry an additive `producer` block
    (`{tool, nils_cli_version}`), stamped at `init` from the producing crate
    version, so archived skill-usage evidence records the producing nils-cli
    version independent of this host pin
    ([#844](https://github.com/sympoies/nils-cli/pull/844)). The field is
    backward compatible — older records deserialize with `producer` absent and
    still verify — so no consumer rewrite is required. The runtime-kit closeout
    surfacing and the planned evidence archive (agent-runtime-kit#352) read it.
  - `test-first-evidence` now rejects a `failing_test` recorded with
    `exit_code: 0` and no waiver, and `forge-cli` scopes the rule-10 keep-branch
    conflict to the repo config layer so an explicit `--keep-branch` no longer
    collides with a global `[merge] delete_branch = true`
    ([#841](https://github.com/sympoies/nils-cli/pull/841)). Both are behavior
    refinements, not surface retirements — runtime-kit already records non-zero
    failing exit codes — so no consumer rewrite is required.
  No `required_clis[]` floor moves — `agent-runtime` has no floor row (its
  `pinned_tag` is the gate), and no consumed flag or JSON envelope was retired
  or renamed.
- `v1.3.1` is a lock-step host pin over `v1.3.0`. It is a single-fix patch:
  `agent-runtime audit-drift`'s `rendered-target` class now skips the agents
  render cache scratchpad (`.render-cache-agents.json`) the same way it already
  skipped `.render-cache.json`, so a `build/<product>/` tree that lacks the
  agents cache file — a drift fixture predating the v1.3.0 agents surface, or a
  stale consumer build — no longer reports a spurious `rendered-target` drift
  warn ([#842](https://github.com/sympoies/nils-cli/pull/842)). Runtime-kit
  consumes the fix directly: the four `tests/drift/*` fixtures that #338 had to
  refresh with the spurious cache-warn lines revert to their clean form in the
  same PR that moves this pin. No `required_clis[]` floor moves — `agent-runtime`
  has no floor row (its `pinned_tag` is the gate), and no consumed flag or JSON
  envelope changed.
- `v1.3.0` is a lock-step host pin over `v1.2.0`. It ships an optional
  `agent-runtime` agents render surface
  ([#839](https://github.com/sympoies/nils-cli/pull/839)): an absent
  `manifests/agents.yaml` resolves to an empty manifest, so every existing
  source tree renders byte-identically, and when present each
  `core/agents/<id>/AGENT.md.tera` renders per product into `build/<product>/`
  at the product `render_to` — `product` and `id` are exposed as Tera
  variables so one canonical source branches to Codex TOML vs Claude Markdown.
  A separate agents cache file (`.render-cache-agents.json`) keeps the skills
  and agents surfaces from reconciling away each other's outputs, and
  `--update-golden` / `audit-drift` cover agents with no extra wiring. The
  exact `pinned_tag` gate covers the `agent-runtime` host; no `required_clis[]`
  floor moves — `agent-runtime` has no floor row (its `pinned_tag` is the
  gate), and the runtime-kit consumer that adopts this surface (managed
  reviewer subagents, agent-runtime-kit#330) lands in a separate PR.
- `v1.2.0` is a lock-step host pin over `v1.1.0`. It ships the `forge-cli`
  test-first evidence gate and rolls up plan-issue / heuristic validation
  hardening, neither of which requires a consumer rewrite to adopt the pin:
  `forge-cli pr create` / `pr deliver` gain `--test-first-evidence <dir>` and a
  config-gated gate — when `[test_first].require` resolves true (from a repo
  `.forge-cli.toml` or the new user-global
  `${XDG_CONFIG_HOME:-~/.config}/forge-cli/config.toml` layer), a feature/bug
  PR must carry a verified `test-first-evidence` record (failing test or
  explicit waiver plus a passing final validation); docs/chore/ci/refactor are
  exempt. The same release routes `forge-cli`'s existing `[merge]` / `[inbox]`
  consumers through that layered loader and exports
  `agent_workflow_primitives::test_first_evidence::verify_dir` for the gate
  ([#836](https://github.com/sympoies/nils-cli/pull/836)). `plan-issue` and the
  heuristic records path get validation hardening
  ([#835](https://github.com/sympoies/nils-cli/pull/835)). Runtime-kit consumes
  the test-first gate surface — the policy-owned `test-first-evidence` CLI flow
  produces the record and `core/policies/git-delivery.md` documents the
  delivery-side gate —
  so the `forge-cli` floor moves to `>= 1.2.0`.
- `v1.1.0` is a lock-step host pin over `v1.0.17`. It ships delivery and
  lifecycle hardening that runtime-kit benefits from without requiring a
  consumer rewrite: `forge-cli pr deliver` can adopt an existing open PR for
  the resolved head branch ([#823](https://github.com/sympoies/nils-cli/pull/823))
  and forced-provider detection now adopts the remote host when compatible
  ([#822](https://github.com/sympoies/nils-cli/pull/822)); `plan-issue` can
  compose `record post --execution-state-file` with `--summary-file`
  ([#824](https://github.com/sympoies/nils-cli/pull/824)), accepts waived /
  deferred terminal task rows consistently across closeout gates
  ([#825](https://github.com/sympoies/nils-cli/pull/825)), and hardens summary
  carrier linting ([#830](https://github.com/sympoies/nils-cli/pull/830));
  `skill-usage` and `heuristic-inbox` fix local record/slug races
  ([#828](https://github.com/sympoies/nils-cli/pull/828),
  [#829](https://github.com/sympoies/nils-cli/pull/829)); and generated
  completion freshness is now audited in nils-cli CI
  ([#831](https://github.com/sympoies/nils-cli/pull/831)). Runtime-kit already
  consumes the affected `forge-cli`, `plan-issue`, and `heuristic-inbox`
  behavior in PR delivery, plan closeout, and heuristic records closeout, so
  those targeted `required_clis[]` floors and the heuristic-system surface
  floor move to `>= 1.1.0`.
- `v1.0.17` ships the `forge-cli` task-list surface
  ([#814](https://github.com/sympoies/nils-cli/issues/814),
  [#815](https://github.com/sympoies/nils-cli/pull/815)): a new
  `pr tasks <id>` atom (GFM task-list items parsed from the PR/MR
  description with checked state, text, and line) and merge lock-down
  rule 13 — `pr merge` and the `pr deliver` merge step fail closed with
  `unchecked_task_items` while unchecked `- [ ]` items remain, with
  `--allow-unchecked-tasks` + required `--allow-unchecked-tasks-reason`
  as the recorded bypass. The `deliver-pr` outcome consumes both surfaces in
  its pre-merge sweeps, so the `forge-cli` floor moves
  to `>= 1.0.17`.
- `v1.0.16` ships the `forge-cli` review-thread surface
  ([#808](https://github.com/sympoies/nils-cli/issues/808),
  [#809](https://github.com/sympoies/nils-cli/pull/809)): a new
  `pr review-threads <id>` atom (normalized resolved state from the GitHub
  `reviewThreads` GraphQL connection / GitLab resolvable discussions) and
  merge lock-down rule 12 — `pr merge` and the `pr deliver` merge step fail
  closed with `unresolved_review_threads` while unresolved threads exist,
  with `--allow-unresolved-threads` as the explicit bypass. The `deliver-pr`
  skill's pre-merge sweep consumes both surfaces (the gap that motivated
  them is inbox case `deliver-pr-merge-misses-bot-review-threads`), so the
  `forge-cli` floor moves to `>= 1.0.16`.
- `v1.0.15` tightens the `agent-runtime pr-body render` input contract
  ([#806](https://github.com/sympoies/nils-cli/pull/806)): `--issues-file`
  now renders for every kind (required for `bug` as `## Issues Found`,
  optional otherwise as `## Issues` after `## Summary`), and kind-specific
  section files hard-error under a non-owning kind (exit 2) instead of being
  silently dropped. Runtime-kit `pr:deliver-pr` and its lifecycle docs adopted
  the surface in agent-runtime-kit commit
  `99e3e81`. The exact `pinned_tag` gate covers the `agent-runtime` host, and
  no `required_clis[]` floor moves: the remaining changes are test-only
  refactors ([#801](https://github.com/sympoies/nils-cli/pull/801),
  [#802](https://github.com/sympoies/nils-cli/pull/802),
  [#803](https://github.com/sympoies/nils-cli/pull/803),
  [#805](https://github.com/sympoies/nils-cli/pull/805)) and the additive
  `forge-cli` activity feed
  ([#800](https://github.com/sympoies/nils-cli/pull/800)), which no
  runtime-kit consumer depends on yet.
- `v1.0.14` hardens `forge-cli` GitLab merge request delivery: numeric MR
  `checks`, `wait-checks`, and `merge` now use structured GitLab API calls
  when project context is available, including pipeline job allow-failure
  handling, while the branch-only legacy status fallback remains documented
  ([#798](https://github.com/sympoies/nils-cli/pull/798),
  [#799](https://github.com/sympoies/nils-cli/pull/799)). Runtime-kit PR/MR
  close, deliver, plan-tracking delivery, and dispatch-lane merge surfaces
  rely on those provider lifecycle paths, so `forge-cli` moves to
  `>= 1.0.14`. The coverage-focused changes in #795 and #796 do not move
  consumer floors.
- `v1.0.13` promotes a local, issue/profile-scoped lifecycle mutation lock in
  `plan-issue` for live provider comment streams. Concurrent `record post` and
  `tracking checkpoint --live` mutations against the same provider, repo,
  issue, and profile now fail fast with
  `plan-issue-lifecycle-lock-busy` instead of racing provider comments
  ([#793](https://github.com/sympoies/nils-cli/pull/793),
  [#794](https://github.com/sympoies/nils-cli/pull/794)). Runtime-kit dispatch
  and plan-tracking skills consume those live lifecycle paths, so
  `plan-issue` moves to `>= 1.0.13`.
- `v1.0.12` migrates several local helper surfaces into native nils-cli crates:
  `claude-cli`, `docker-tools`, `opencode-cli`, plus new `fzf-cli` and
  `zsh-kit` helper subcommands
  ([#789](https://github.com/sympoies/nils-cli/pull/789),
  [#791](https://github.com/sympoies/nils-cli/pull/791)). Runtime-kit does not
  consume those new helper command contracts in required skill surfaces yet, so
  no `required_clis[]` floor moves for that release.
- `v1.0.11` promotes the provider payload privacy gate for `forge-cli`
  provider bodies/comments and `plan-issue` provider lifecycle records. Live
  mutations now fail closed when provider-visible payloads contain raw
  machine-local home paths, returning `local_path_present` with a `$HOME/...`
  rewrite hint and without echoing the raw path
  ([#788](https://github.com/sympoies/nils-cli/pull/788),
  [#790](https://github.com/sympoies/nils-cli/pull/790)). Runtime-kit consumes
  that gate in issue/PR/dispatch skill guidance and runtime smoke, so
  `plan-issue` and `forge-cli` `required_clis[]` floors move to `>= 1.0.11`.
- `v1.0.10` promotes the post-`v1.0.9` `agent-runtime bootstrap-host`
  surface into the active pin, removes `git-scope`'s external `tree`
  dependency, and fixes plan-tracking review evidence so decision-bearing
  review checkpoints include lenses, outcome evidence, or finding rows
  ([#780](https://github.com/sympoies/nils-cli/pull/780),
  [#781](https://github.com/sympoies/nils-cli/pull/781),
  [#782](https://github.com/sympoies/nils-cli/pull/782),
  [#784](https://github.com/sympoies/nils-cli/pull/784),
  [#785](https://github.com/sympoies/nils-cli/pull/785)). Runtime-kit now
  consumes the new `plan-issue tracking run update --review-lens`,
  `--review-outcome-comment`, and `--review-findings-file` surface in the
  plan-tracking delivery / closeout and dispatch-lane review skills, so the
  `plan-issue` `required_clis[]` floor moves to `>= 1.0.10`.
- `v1.0.9` is a **patch** over `zsh-kit setup --write-zshenv`: the managed
  `$HOME/.zshenv` now preserves requested `ZSH_FEATURES` and sources
  `$ZDOTDIR/.zshenv`, so first-run Docker shells receive repo-owned environment
  wiring without the image entrypoint duplicating bootstrap generation
  ([#770](https://github.com/sympoies/nils-cli/pull/770),
  [#771](https://github.com/sympoies/nils-cli/pull/771)). This repo's Docker
  entrypoint consumes that released behavior, so the `zsh-kit` floor moves to
  `>= 1.0.9`.
- `v1.0.8` is a **patch** over `fzf-cli def` on Linux: the generated preview
  script temp file is flushed and converted to a closed `TempPath` before fzf's
  preview shell executes it, avoiding `zsh: text file busy` in container TTYs
  ([#768](https://github.com/sympoies/nils-cli/pull/768),
  [#769](https://github.com/sympoies/nils-cli/pull/769)). Additive runtime
  bug fix only — no consumed flag or JSON envelope changed and no
  `required_clis[]` floor moves.
- `v1.0.7` ships the new `zsh-kit` binary, whose `setup` subcommand clones or
  updates an operator-supplied Zsh repo URL/path and dispatches that repo's
  public setup hook (`bootstrap/zsh-kit-setup.zsh` or `.zsh-kit/setup.zsh`) in
  dry-run or apply mode
  ([#763](https://github.com/sympoies/nils-cli/pull/763),
  [#765](https://github.com/sympoies/nils-cli/pull/765)). This repo's Docker
  surface consumes it for runtime shell setup, so `zsh-kit >= 1.0.7` is added
  to `required_clis[]`.
- `v1.0.6` is a **patch** over `git-cli worktree remove`: when the remove
  target is not found but exactly matches a live linked worktree branch name,
  `git-cli` now returns a recovery hint pointing at the managed slug and full
  path, and text-mode errors print hints on stderr instead of hiding them in
  JSON-only output
  ([#760](https://github.com/sympoies/nils-cli/pull/760)). Additive — this
  repo's consumers already remove managed worktrees by slug or path, so no
  `required_clis[]` floor moves.
- `v1.0.4` adds a `--kind <feature|bug|chore|docs|ci|refactor>` flag to
  `git-cli worktree add` (default `feature`, so the prior `feat/<slug>` behavior
  is unchanged), deriving the branch as `<prefix>/<slug>` where the prefix is
  the one `forge-cli pr deliver/create --kind` already enforces
  (`feature->feat/`, `bug->fix/`, `chore->chore/`, `docs->docs/`, `ci->ci/`,
  `refactor->refactor/`). The kind set and its prefix mapping now live once in
  `nils_common::git::PrKind`; `forge-cli`'s `branch_kind` rule re-exports that
  type and compares `branch_prefix()` instead of a duplicate pairing, so the two
  tools can no longer drift. A worktree opened with `--kind bug` now delivers
  cleanly under `--kind bug` with no rename step
  ([#751](https://github.com/sympoies/nils-cli/pull/751)). This repo documents
  the flag in `core/policies/git-delivery.md`; it is policy guidance, not yet an
  automated skill invocation, so the `git-cli` `required_clis[]` floor does not
  move.
- `v1.0.3` adds a repeatable `--label` flag to `heuristic-inbox deliver`
  ([#748](https://github.com/sympoies/nils-cli/pull/748)), forwarded verbatim to
  `forge-cli pr create --label`, so records-branch PRs can carry taxonomy
  labels. Policy-owned session closeout consumes it with
  `--label workflow::heuristic-records` plus a fixed title, so the
  `heuristic-inbox >= 1.0.3` `required_clis[]` floor and the `heuristic-system`
  surface `min_nils_cli` (`v1.0.3`) are set.
- `v1.0.2` adds the **`heuristic-inbox deliver`** subcommand: a cwd-independent
  records-branch PR writeback for uncommitted heuristic-system records (fetch
  `origin/<base>` → managed worktree on a `<prefix>/<slug>` branch matching
  `--kind` → stage only the heuristic-system root → `semantic-commit` → push →
  `forge-cli pr create`), returning `branch` / `pr_url` / `committed_paths` /
  `worktree_path` in a `cli.heuristic-inbox.deliver.v1` envelope with `--dry-run`
  plan rendering. This is the deterministic replacement for the
  former prose-owned closeout writeback delivered in #237; policy-owned
  closeout now consumes it, so the `heuristic-inbox >= 1.0.2`
  `required_clis[]` floor and the `heuristic-system` surface `min_nils_cli`
  (`v1.0.2`) are set
  ([#745](https://github.com/sympoies/nils-cli/pull/745)).
- `v1.0.1` adds the **execution-state synchronization** surface consumed by the
  plan-tracking outcome: `plan-issue record open` writes the tracking issue URL
  into the bundle `*-execution-state.md`; `record close --bundle` writes the
  terminal state back; `tracking checkpoint --live` reconciles and self-heals
  the `Tracking issue` bullet while `tracking close-ready` gates it
  (`execution-state-issue-missing` / `-mismatch`); and `plan-tooling
  exec-state-sync` repairs existing bundles offline
  ([#741](https://github.com/sympoies/nils-cli/pull/741)).
- `v1.0.0` is the **major** naming-convention milestone: the workspace
  finalizes the `crate dir == binary base` / `package == nils-<dir>`
  convention and drops the `-cli` suffix from three crate directories.
  `agent-runtime-cli` → `agent-runtime`, `memo-cli` → `memo` (crate, binary,
  and the `cli.memo.*` JSON contract), and `plan-issue-cli` → `plan-issue`
  (crate, package, library, and the JSON output contract namespace — now
  `plan-issue.*`, renamed from the prior `plan-issue-cli.*` with no backward
  compatibility). Binary names are unchanged (`agent-runtime`, `memo`,
  `plan-issue` / `plan-issue-local`). This repo consumes the renamed
  `plan-issue.*` envelope in its runtime-smoke `dispatch` / `pr` cases; the
  `agent-runtime` doctor envelope (`agent-runtime-cli.doctor.v1`) was **not**
  renamed and is unchanged
  ([#735](https://github.com/sympoies/nils-cli/pull/735),
  [#736](https://github.com/sympoies/nils-cli/pull/736)).
- `v0.31.8` is a **patch** that adds the `plugin-manifest-skills` block-tier
  drift class to `agent-runtime audit-drift`: for every Codex
  `targets/codex/plugins/<domain>/.codex-plugin/plugin.json` whose domain has a
  `plugins.yaml` plugin, the advertised `skills[]` entries must mirror that
  plugin's `contained_skills` and each entry's `source` must match
  `skills.yaml` and resolve to a directory on disk. This repo consumes
  `agent-runtime audit-drift` in `scripts/ci/all.sh`; the class closes the gap
  that let `#220`'s renamed-skill `plugin.json` entry ship green (this repo's
  `#225`). Additive — no flag or envelope changed and no `required_clis[]`
  floor moves
  ([#725](https://github.com/sympoies/nils-cli/pull/725),
  [#726](https://github.com/sympoies/nils-cli/pull/726)).
- `v0.31.7` is a **patch** that ships the `forge-cli search` surface —
  `search issues` / `search prs` (GitHub full-text via `gh search`) and
  `search refs-to <ref>` (cross-reference events via `gh api graphql`), all
  GitHub-only behind the provider seam, single-repo scoped, with three
  versioned envelopes (`cli.forge-cli.search.{issues,prs,refs-to}.v1`) — and
  the `forge-cli activity` discovery surface from `v0.31.6`'s follow-up. Both
  are additive: this repo's skills consume the unchanged `forge-cli`
  `pr` / `issue` / `inbox` surfaces, so no `required_clis[]` floor moves. No
  surface was retired or renamed
  ([#721](https://github.com/sympoies/nils-cli/pull/721),
  [#722](https://github.com/sympoies/nils-cli/pull/722),
  [#723](https://github.com/sympoies/nils-cli/pull/723),
  [#724](https://github.com/sympoies/nils-cli/pull/724)).
- `v0.31.6` is a **patch** that adds an opt-in fail-closed `agent-docs
  preflight --require-declared-intent` guard for callers that already know the
  requested intent must be declared. Guarded undeclared intents return exit 65
  with a stable `undeclared-intent` JSON error envelope; unguarded preflight
  keeps the compatible document-only fallback. This repo consumes that surface
  in the prompt preflight and finish-line hooks, so the `agent-docs`
  `required_clis[]` floor moves to `0.31.6`. No surface was retired or renamed
  ([#719](https://github.com/sympoies/nils-cli/pull/719),
  [#720](https://github.com/sympoies/nils-cli/pull/720)).
- `v0.31.5` is a **patch** that publishes the Sprint 1 `git-cli worktree`
  surface: `git-cli worktree add/list/remove/prune` manages repo-scoped
  worktrees under `$AGENT_HOME/worktrees/<repo-key>/<branch-slug>` with text
  and JSON output, shares the worktree parser/removal path with
  `branch cleanup --remove-worktrees`, and includes completion coverage. This
  repo consumes that surface through the worktree policy and hook exception
  shipped in agent-runtime-kit#213, so the `git-cli` `required_clis[]` floor
  moves to `0.31.5`. No surface was retired or renamed
  ([#715](https://github.com/sympoies/nils-cli/pull/715),
  [#718](https://github.com/sympoies/nils-cli/pull/718)).
- `v0.31.4` is a **patch** that fixes the canonical `plan-issue tracking
  checkpoint --post state` bundle-backed ledger path: `tracking run init` stores
  absolute bundle / execution-state refs, state readers resolve the full
  `## Task Ledger` from the bundle when `execution_state_file` is absent, and a
  recorded-but-unreadable ledger now blocks with `state-ledger-unresolved`
  instead of silently rendering a synthesized single-row baseline. The
  plan-tracking workflows depend on this repaired state checkpoint behavior, so
  the `plan-issue` `required_clis[]` floor moves to `0.31.4`. No flag or JSON
  envelope was retired or renamed
  ([#713](https://github.com/sympoies/nils-cli/pull/713),
  [#714](https://github.com/sympoies/nils-cli/pull/714)).
- `v0.31.3` is a **patch** with two additive surface changes and no retired or
  renamed surfaces, so no consumer floor moves: `repo-retro` now auto-discovers
  the heuristic-system root (`heuristic-system/` then
  `core/policies/heuristic-system/`, with a new `--heuristic-root` override) and
  summarizes nested `<slug>/ENTRY.md` inbox cases, so the `## HEURISTIC_SYSTEM`
  report section is correct for `core/policies`-nested roots like this repo
  ([#706](https://github.com/sympoies/nils-cli/pull/706)); and `forge-cli`
  `--provider` gains a `local` file-backed backend value plus a `--store-root`
  flag (and the `FORGE_CLI_LOCAL_STORE` env var), with the `github` / `gitlab`
  provider surfaces unchanged
  ([#705](https://github.com/sympoies/nils-cli/pull/705),
  [#707](https://github.com/sympoies/nils-cli/pull/707)).
- `v0.31.2` is a **patch** fixing plan-tracking dashboard/state staleness:
  `tracking checkpoint` now derives the state payload's `current` /
  `next_action` / `target_scope` from the durable `## Task Ledger` plus the
  authored scope, and re-renders the visible Execution State header from that
  payload, so a completed plan's Final Dashboard and state comment no longer
  show pre-flight values. Internal rendering only — no surface retired or
  renamed, no consumer floor moves
  ([#702](https://github.com/sympoies/nils-cli/pull/702),
  [#703](https://github.com/sympoies/nils-cli/pull/703)).
- `v0.31.1` is a **patch** fixing `repo-retro` path classification: generated
  Markdown fixtures under `tests/golden/**` (and test-tree files) now classify
  as `tests` instead of `productDocs`, so a single skill edit is no longer
  triple-counted across `source` + `productDocs` in `churnByClass` /
  `fileHotspots`; `docs/specs` stays `productDocs`. Additive — no surface
  retired or renamed, no consumer floor moves
  ([#698](https://github.com/sympoies/nils-cli/pull/698)).
- `v0.31.0` is a **minor** that ships `repo-retro report` **schema v2**
  (`cli.repo-retro.report.v2` / `repo-retro.report.v2`): a deterministic
  pre-digestion layer — `git.churnByClass` (source / tests / productDocs /
  processArtifacts / other, reconciling to the summary total), `git.archival`
  (net-deletion as the primary signal), and commit-frequency
  `fileHotspots.topFiles` carrying `class` / `netDeleted` — plus a
  `--path-class-config` override. The analysis layer now reads that class split
  and never nominates a net-deleted file for review. The v1 envelope was
  removed (breaking), so the `project-retro` consumer moves to v2 in lock-step;
  no `required_clis[]` floor moves (`repo-retro` is not a floored binary)
  ([#694](https://github.com/sympoies/nils-cli/pull/694)).
- `v0.30.2` is a **patch** that extends the `plan-archive` body / full-text
  search surface: `catalog --deep` extends `--grep` to also match issue / PR /
  MR body and comment text (via each ref's latest snapshot), and a new
  `plan-archive search <term>` subcommand returns hit-level results (owning plan
  slug + ref URL + matched field + snippet) in a versioned JSON envelope. Both
  are additive — no surface was retired or renamed, so no consumer floor moves
  ([#690](https://github.com/sympoies/nils-cli/pull/690),
  [#691](https://github.com/sympoies/nils-cli/pull/691)).
- `v0.30.1` is a **patch** over the `v0.30.0` `agent-docs` redesign: a docs-home
  catalog's `scope = "project"` documents and its (scopeless, repo-local)
  `[[validation]]` contracts are now scoped to the declaring repository — they
  no longer leak into unrelated projects' `preflight` / `audit` / `explain`
  ([#685](https://github.com/sympoies/nils-cli/pull/685),
  [#686](https://github.com/sympoies/nils-cli/pull/686)). The finish-line
  validation gate in agent-runtime-kit#181 depends on this scoping, so the
  `agent-docs` `required_clis` floor moves to `0.30.1`.
- `v0.30.0` was a **breaking** bump: the `agent-docs` engine was redesigned to be
  fully data-driven. It retires the `resolve` / `baseline` / `scaffold-*` /
  `add` / `contexts` commands and the `startup` per-task context, and removes
  all hardcoded builtin requirements; required docs plus the per-repo validation
  contract are declared in `AGENT_DOCS.toml` (`[[document]]` + `[[validation]]`,
  with real `when` predicates and content validation). The new surface is
  `audit` / `preflight --intent X` (versioned `agent-docs.preflight.v1` JSON) /
  `init` / `explain` / `list` / `remove`, with docs-home derived from the
  install symlink. This is the surface adopted in agent-runtime-kit#181
  ([#671](https://github.com/sympoies/nils-cli/pull/671),
  [#674](https://github.com/sympoies/nils-cli/pull/674)).
- Prior pin: `v0.29.0` at `0f757df` (`chore(release): bump cli versions to
  0.29.0 (#661)`). `v0.29.1` is a patch bump hardening the same
  `git-cli branch cleanup --squash` path: branches with no merge-base against
  base (unrelated / orphan history) are now skipped instead of aborting the
  whole sweep, so a repo with orphan fixture branches can be cleaned
  ([#668](https://github.com/sympoies/nils-cli/pull/668)). No consumed flag or
  JSON envelope changed; `required_clis[]` floors are unchanged. The `v0.29.1`
  tag sits on `9681bb8`: the `0.29.1` bump (#669) was re-tagged after a docs
  table-alignment fix (#670). Further prior pin: `v0.28.6` at `67cb08b`
  (`chore(release): bump cli versions to 0.28.6 (#659)`). `v0.29.0` is a minor
  bump with one consumed-surface change:
  `git-cli branch cleanup --squash` (and `--remove-worktrees`, which only acts
  on detected branches) now detects multi-commit provider squash-merges by
  synthesizing the branch's diff as a single commit on its merge-base and
  patch-comparing against base, where a per-commit `git cherry` previously
  missed them
  ([#660](https://github.com/sympoies/nils-cli/pull/660)). No consumed surface
  was retired or renamed and no flags or JSON envelopes changed;
  `required_clis[]` floors are unchanged because no agent-runtime-kit consumer
  depends on the new behavior. Further prior pin: `v0.28.5` at `49f925b`
  (`chore(release): bump cli versions to 0.28.5 (#656)`). `v0.28.6` is an
  additive patch bump with one consumed
  surface: `agent-docs` now lets a project opt out of a non-`startup` built-in
  requirement by declaring a matching `[[document]]` entry with
  `required = false` for the built-in's own `(context, scope, path)` key in
  its `AGENT_DOCS.toml`; the built-in is downgraded to optional in `resolve`
  and `baseline --check` with `source = builtin-opt-out` (so it drops out of
  `missing_required` while staying auditable). `startup` cannot be opted out
  and a home catalog cannot opt an unrelated project out
  ([#658](https://github.com/sympoies/nils-cli/pull/658)). No consumed surface
  was retired or renamed; `required_clis[]` floors are unchanged because no
  agent-runtime-kit consumer depends on the new surface yet. Further prior pin:
  `v0.28.4` at `6335148` (`chore(release): bump cli versions to
  0.28.4 (#654)`). `v0.28.5` is an additive patch bump with one consumed
  surface: `plan-archive migrate` now reconciles an archived plan's
  `*-execution-state.md` `## Execution State` header to a terminal "archived"
  status that defers to the issue/PR ref (rewrites the `Status` / `Current
  task` / `Next task` bullets and drops their wrapped continuation lines; all
  other bundle files copy verbatim), and the apply report gains
  `execution_state_reconciled`
  ([#655](https://github.com/sympoies/nils-cli/pull/655)). No consumed surface
  was retired or renamed; `required_clis[]` floors are unchanged because the
  policy-owned plan-archive migration needs no new surface. `v0.28.4` was an
  additive patch bump adding two consumed
  surfaces: `plan-issue record restore` re-materializes a tracking issue's
  `source` / `plan` snapshot comments back into bundle files (latest-per-role,
  online or offline `--comments-json`, non-destructive unless `--force`), the
  inverse of `record open`
  ([#652](https://github.com/sympoies/nils-cli/pull/652)); and `forge-cli pr
  deliver --dry-run` now runs the non-mutating lock-down rules and reports each
  verdict in an additive `data.local_preflight[]` block (no provider backend),
  body-section validation aggregates into one `body_missing_sections` error
  when both are missing, and `agent-runtime pr-body render --kind` covers all
  six deliver kinds with a scaffold pointer in the body-missing errors
  ([#653](https://github.com/sympoies/nils-cli/pull/653)). No consumed surface
  was retired or renamed; `required_clis[]` floors are unchanged because no
  agent-runtime-kit consumer depends on the new surfaces yet. `v0.28.3` was an
  additive patch bump for the dispatch
  `tracking checkpoint` lifecycle: `tracking checkpoint --live` now inherits
  `repo`/`issue` from the run-state when `--provider-repo`/`--issue` are
  omitted, so the documented dispatch entrypoint posts instead of silently
  no-opping ([#644](https://github.com/sympoies/nils-cli/pull/644)); and
  `tracking checkpoint --post session` synthesizes the session summary from
  run-state activity (selected task, branch, linked PRs, validation, phase)
  when no explicit note exists, instead of dropping the role
  ([#645](https://github.com/sympoies/nils-cli/pull/645)). The release tooling
  also re-pins only workspace versions in the lockfile refresh
  ([#646](https://github.com/sympoies/nils-cli/pull/646), not a consumed
  surface). No consumed surface was retired or renamed. `v0.28.2` made the
  dispatch-profile dashboard name every lane PR: `plan-issue` accumulates each
  lane's linked PR into the state-checkpoint payload `prs[]`, so the dispatch
  dashboard's Linked PRs field lists every lane PR instead of `none yet`
  ([#642](https://github.com/sympoies/nils-cli/pull/642)). `v0.28.1` added the
  `plan-issue record post --task-ledger-display open` mode plus the
  `record open` open-fold default for the first Execution State
  ([#640](https://github.com/sympoies/nils-cli/pull/640)), `profile=dispatch`
  markers on dispatch `tracking checkpoint` lifecycle comments
  ([#639](https://github.com/sympoies/nils-cli/pull/639)), and the new
  `agent-memory` CLI ([#638](https://github.com/sympoies/nils-cli/pull/638)).
  At that snapshot runtime-kit consumed `agent-memory index global`
  opportunistically in the Codex UserPromptSubmit hook. `v1.21.21` supersedes
  that startup path with bounded `recall startup` and producer candidates;
  the earlier release history remains below.
  `v0.25.8` at `4d0d621`
  (`chore(release): bump cli versions to 0.25.8 (#608)`). `v0.28.0` spans the
  v0.25.9–v0.28.0 releases and adds: the
  `agent-runtime doctor --class version-alignment` surface
  ([#636](https://github.com/sympoies/nils-cli/pull/636)) — now consumed by
  this repo's `scripts/ci/all.sh` Position 1 through
  `docs/source/nils-cli-pin.yaml`; build metadata in the `agent-runtime
  --version` output (#625); the new `nils-build-info` library crate; and the
  `plan-issue` accumulative state payload tasks ledger (#633). Earlier release
  history retained below. `v0.25.7` at `0c070f8` (`feat(plan-tooling):
  per-task ledger durability (0.25.7) (#607)`); `v0.25.8` is a workspace-wide
  lock-step bump that catches the 31 crates skipped by the v0.25.7 partial release
  (`agent-runtime-cli`, `forge-cli`, `semantic-commit`, the `api-*` and
  `git-*` families, the rest) up to the workspace floor, restoring the
  convention from `1edf007` that every release tag matches every crate's
  `Cargo.toml` version. No new consumed surface relative to v0.25.7. The
  v0.25.7 entry remains the source of the `plan-tooling ledger-update`
  and `plan-tooling ledger-sync --from-issue` subcommands plus the
  `ledger-rows-pending` blocker on `plan-issue tracking close-ready`
  (read-mostly drift reconciliation against issue lifecycle evidence;
  one-call row patching for the canonical `*-execution-state.md`
  ledger; refuses ready handoff while a ledger row remains `pending`
  or `in-progress` at `phase=ready_for_close`). Consumed by the four
  active tracking outcome plus the `conversation:handoff-session-prompt`
  guidance. `v0.25.6` lands live posting in `plan-issue tracking
  checkpoint --live --post <roles> --repair-dashboard` (one provider
  comment per role, fixture-mode parity for deterministic tests, abort
  on first per-role failure) consumed by the
  `dispatch:deliver-plan-tracking-issue` close-ready and internal closeout
  phases.
  `v0.25.5` adds the `plan-archive discover` read-only candidate
  scanner consumed by policy-owned archive routing. `v0.25.0`
  introduced the `plan-archive` binary with the `migrate`, `refresh`, and
  `query` subcommands (plus the `validate-hosts`, `validate-local`,
  `validate-metadata` validators) consumed by the
  plan delivery and archive-maintenance workflows directly.

This file is the human-readable pin source for `required_clis` placeholders
in `manifests/skills.yaml` and `manifests/plugins.yaml`. Manifest authors
should reference binary names from the **Binary** column when declaring
`required_clis`, and refresh this snapshot at every nils-cli release that
changes a consumed surface. The machine-readable pin the CI gate enforces
lives in `docs/source/nils-cli-pin.yaml`; the `meta:nils-cli-bump` skill
keeps both in sync on a release bump.

As of `v1.21.17`, the consumed rows below have these additive floors:
`agent-docs` supplies durable selective-intent session state and path
classification; `agent-workflow-primitives` supplies durable `docs-impact`,
phase-aware `test-first-evidence`, and v2 `skill-usage` ownership; and
`nils-evidence` plus the `heuristic-inbox` binary accept those mixed v1/v2
owners during archive and closeout promotion. No Browser/Evidence command was
retired or renamed in this release.

Notes on derivation:

- The **Crate** column lists every directory currently under
  `crates/` in the source repo (44 entries).
- The **Binary** column lists every binary the crate produces. Library
  crates show `(library only)`. Crates that ship more than one binary
  enumerate them comma-separated.
- The **Notes** column captures intent: stub status, multi-binary
  fanout, library-only role, or other manifest-author-facing context.

## Crate → binary table

| Crate                       | Binary                                                                                                              | Notes                                                                                                                                                                                                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent-docs`                | `agent-docs`                                                                                                        | Data-driven required-doc resolver and auditor; no hardcoded builtins. As of `v0.30.0` the surface is `audit` (repo health: install-symlink wiring + declared-doc presence/validity + catalog validity), `preflight --intent X` (resolve the doc set plus the per-repo validation contract as versioned JSON for hooks to inject and enforce), and `init` / `explain` / `list` / `remove`. Policy is declared in `AGENT_DOCS.toml` (`[[document]]` + `[[validation]]`, `when` predicates, content validation); docs-home is derived from the install symlink. As of `v0.30.1`, a docs-home catalog's `scope = "project"` documents and its `[[validation]]` contracts are scoped to the declaring repository, so they never leak into unrelated projects. As of `v0.31.6`, `preflight --require-declared-intent` lets known-intent callers fail closed for undeclared intent names while preserving the unguarded compatibility fallback. As of `v1.12.1`, catalog documents and validation contracts can declare `product`, and `preflight` / `audit` / `explain` / `list` accept `--product codex|claude`; `preflight` now emits `agent-docs.preflight.v2` with product scope. The `resolve` / `baseline` / `scaffold-*` / `add` / `contexts` commands and the `startup` per-task context were retired in the redesign. As of `v1.23.0`, `session prepare` adds an atomic intent-preparation primitive that mirrors `session activate`'s strict preflight + activation and reports a stable `cli.agent-docs.session.prepare.v1` result (`prepared_intents` plus a `prepared` / `already-current` reason code) for runtime hooks ([#1273](https://github.com/sympoies/nils-cli/pull/1273)); additive and not yet consumed by runtime-kit. As of `v1.24.0`, an optional `phase` field on `[[document]]` (string or array) and a `--phase` filter on `preflight` / `session activate|prepare|verify` scope resolution and preparation to a workflow phase (no-phase docs apply to all phases; new codes `phase-unsatisfied` / `invalid-phase`, [#1282](https://github.com/sympoies/nils-cli/pull/1282)); additive and not yet consumed by runtime-kit.                                                                                                  |
| `agent-memory`              | `agent-memory`                                                                                                      | Agent memory helper. Runtime-kit consumes bounded `recall startup` in the Codex and Claude `startup|resume|clear` SessionStart policy groups and `check --max-index-bytes --forbid-terms-file` in the retired-memory audit. The shared hook is stateless, fails open, and never falls back to the full global index or candidate roots, so a blocked aggregate cannot consume a later startup-memory delivery. As of `v1.26.4`, runtime-kit also consumes the 768-byte startup default and exact optional `recall on-demand --agent <id>` scope; that release adds trusted agent-root checks and frontmatter-aware candidate previews ([#1460](https://github.com/sympoies/nils-cli/pull/1460)), so the floor is `>=1.26.4`. The CLI also owns producer-isolated untrusted candidates, dry-run-first promotion, and dry-run-first inactive archive retirement. Policy requires live verification and explicit user approval before curated promotion. |
| `agent-out`                 | `agent-out`                                                                                                         | Agent output / artifact helper. As of `v1.19.2`, runtime-kit consumes `agent-out path-for --domain <domain> [--topic <topic>]` as the compatibility allocator for rendered `state_out(...)` skill instructions; it delegates to the canonical project allocator, supports `path` / `json` / `env`, and emits `cli.agent-out.path-for.v1` JSON ([#984](https://github.com/sympoies/nils-cli/pull/984)). As of `v1.19.3`, runtime-kit consumes `agent-out cleanup plan/apply` for reviewed cleanup of stale cache and noncanonical output entries: plans emit `cli.agent-out.cleanup.plan.v1` with a digest, and apply emits `cli.agent-out.cleanup.apply.v1` after digest, containment, delete-shape, and evidence-marker checks ([#987](https://github.com/sympoies/nils-cli/pull/987)). |
| `agent-runtime`         | `agent-runtime`                                                                                                     | Runtime kit CLI. As of `v0.20.0`, this repo consumes released `render`, `install`, `uninstall`, `doctor` (including `--class skill-surface --product codex`), `audit-drift`, `gc-backups`, `restore-backups`, `purge-state`, and `pr-body render` bodies through Homebrew. The `pr-body render` surface renders standardized feature / bug PR and MR bodies before `forge-cli pr create` / `forge-cli pr deliver`. As of `v0.22.4`, `sync-runtime-surfaces` consumes `agent-runtime prune-stale` to remove stale managed Codex and Claude skill surfaces after install. As of `v0.28.0`, ships `doctor --class version-alignment --pin <manifest>` (the surface-pin drift gate this repo's Position 1 consumes via `docs/source/nils-cli-pin.yaml`) and adds build metadata to the `agent-runtime --version` output. As of `v1.0.5`, `render` reconciles `build/<product>/` for retired skills — a skill removed from the manifest has its outputs and `.render-cache.json` entry dropped on the next render, so `sync-runtime-surfaces` + `prune-stale` no longer leave the retired skill in the live home ([#755](https://github.com/sympoies/nils-cli/pull/755)); `audit-drift` also gains `--json` / `--fail-on` and skips path/slug runs in entropy ([#754](https://github.com/sympoies/nils-cli/pull/754)). As of `v1.0.10`, `bootstrap-host` adds a single dry-run/apply wrapper over render, install, prune-stale, and skill-surface doctor plus a checkpoint/report schema; runtime-kit setup feature-detects it and keeps a phase-command fallback for older hosts ([#780](https://github.com/sympoies/nils-cli/pull/780), [#781](https://github.com/sympoies/nils-cli/pull/781)). As of `v1.3.0`, `render` adds an optional agents surface: an absent `manifests/agents.yaml` is a no-op, and when present each `core/agents/<id>/AGENT.md.tera` renders per product into `build/<product>/` at `render_to` (Codex TOML / Claude Markdown selected via the `product` Tera variable), cached in a separate `.render-cache-agents.json` and covered by `--update-golden` / `audit-drift` ([#839](https://github.com/sympoies/nils-cli/pull/839)). As of `v1.3.1`, `audit-drift`'s `rendered-target` class skips the `.render-cache-agents.json` agents render cache scratchpad (matching the existing `.render-cache.json` skip), so a `build/<product>/` tree lacking that cache file no longer produces a spurious `rendered-target` drift warn ([#842](https://github.com/sympoies/nils-cli/pull/842)). As of `v1.12.1`, `render --target home-prompt` renders `AGENT_HOME.md` to `build/<product-or-neutral>/AGENT_HOME.md`, which runtime-kit setup consumes for per-product home prompt symlinks. As of `v1.21.15`, the skills manifest loader supports schema v2 independently of other manifest families, and `list-skills --format json` reports invocation, exposure, and pending-disposition metadata for Codex, Claude, and Hermes ([#1111](https://github.com/sympoies/nils-cli/pull/1111)). As of `v1.22.6`, `prune-stale` accepts repeatable explicit prior source roots, validates each as a non-empty runtime-kit link-map owner, preserves foreign links, and reports the normalized authorities additively in JSON v1. Portable convergence consumes this surface for relocated-checkout stale-helper cleanup, so the floor moves to `>= 1.22.6` ([#1245](https://github.com/sympoies/nils-cli/pull/1245)). |
| `agent-scope-lock`          | `agent-scope-lock`                                                                                                  | Workspace scope-lock helper.                                                                                                                                                                                                                                           |
| `agent-session`             | `agent-session`                                                                                                     | Tmux-backed local agent session helper. New binary as of `v1.20.7` ([#1009](https://github.com/sympoies/nils-cli/pull/1009)). As of `v1.20.13`, it has send/glance, serve/WebSocket attach, workdir search, title/attachment, repo-picker, and durable-resume surfaces ([#1013](https://github.com/sympoies/nils-cli/pull/1013), [#1015](https://github.com/sympoies/nils-cli/pull/1015), [#1019](https://github.com/sympoies/nils-cli/pull/1019), [#1021](https://github.com/sympoies/nils-cli/pull/1021), [#1023](https://github.com/sympoies/nils-cli/pull/1023)). Later releases add private resume, title, startup, profile, deletion, and maintenance hardening. As of `v1.24.5`, runtime-kit consumes authenticated `work-context show|check|admit|complete|reconcile` for managed-session mutation admission and retains the private mailbox/fixed-notification policy boundary ([#1308](https://github.com/sympoies/nils-cli/pull/1308)); `required_clis[]` therefore pins `agent-session >=1.24.5`. |
| `agent-workflow-primitives` | `agent-run`, `browser-session`, `canary-check`, `docs-impact`, `heuristic-inbox`, `model-cross-check`, `review-evidence`, `review-specialists`, `repo-retro`, `skill-usage`, `test-first-evidence` | Multi-binary crate. Each binary is its own clap CLI; manifests should pin individual binary names, not the crate. As of `v0.20.0`, `agent-run exec` normalizes project command execution through explicit `.envrc` / `.env` decisions. As of `v0.31.0`, `repo-retro report` emits schema v2 (`cli.repo-retro.report.v2` / `repo-retro.report.v2`): a deterministic pre-digestion layer (`git.churnByClass`, `git.archival`, commit-frequency `fileHotspots` with `class` / `netDeleted`) plus a `--path-class-config` override; the v1 envelope was removed (breaking). As of `v0.31.3`, `repo-retro report` auto-discovers the heuristic-system root (`heuristic-system/` then `core/policies/heuristic-system/`) with a `--heuristic-root` override and summarizes nested `<slug>/ENTRY.md` inbox cases, so the `## HEURISTIC_SYSTEM` section reports `present` with real counts for `core/policies`-nested roots like this repo (additive). As of `v1.0.2`, `heuristic-inbox` gains a `deliver` subcommand: a cwd-independent records-branch PR writeback for uncommitted heuristic-system records (`--root` / `--kind` / `--base` / `--dry-run`, `cli.heuristic-inbox.deliver.v1` envelope with `branch` / `pr_url` / `committed_paths` / `worktree_path`), replacing prose-owned records-branch writeback (#237). As of `v1.0.3`, `deliver` gains a repeatable `--label` flag (forwarded to `forge-cli pr create --label`); policy-owned session closeout consumes `deliver --label workflow::heuristic-records` with a fixed title, so the `heuristic-system` surface `min_nils_cli` is `v1.0.3`. As of `v1.1.0`, default `heuristic-inbox deliver` slugs auto-suffix when same-day records branches or managed worktrees already exist ([#829](https://github.com/sympoies/nils-cli/pull/829)); policy-owned closeout relies on that records-branch writeback behavior, so the `heuristic-system` surface `min_nils_cli` moves to `>= 1.1.0`. As of `v1.8.0`, `heuristic-inbox archive` accepts operation-record folders and retained-record status transitions stay in the CLI primitive; policy-owned closeout and inbox routing consume operation-record archival, so the `heuristic-system` surface `min_nils_cli` moves to `>= 1.8.0` ([#875](https://github.com/sympoies/nils-cli/pull/875)). |
| `api-gql`                   | `api-gql`                                                                                                           | GraphQL API testing CLI.                                                                                                                                                                                                                                               |
| `api-grpc`                  | `api-grpc`                                                                                                          | gRPC API testing CLI.                                                                                                                                                                                                                                                  |
| `api-rest`                  | `api-rest`                                                                                                          | REST API testing CLI.                                                                                                                                                                                                                                                  |
| `api-test`                  | `api-test`                                                                                                          | API testing orchestrator.                                                                                                                                                                                                                                              |
| `api-testing-core`          | (library only)                                                                                                      | Shared core for the `api-*` CLIs; never appears in `required_clis`.                                                                                                                                                                                                    |
| `api-websocket`             | `api-websocket`                                                                                                     | WebSocket API testing CLI.                                                                                                                                                                                                                                             |
| `claude-cli`                | `claude-cli`                                                                                                        | Claude runtime helper. As of `v1.0.12`, ships native prompt-segment auth/cache/render/status helpers plus generated completions. As of `v1.21.25`, expired quota-cache values are omitted from prompt rendering ([#1177](https://github.com/sympoies/nils-cli/pull/1177)). Runtime-kit does not consume this surface in required skill flows today. |
| `cli-template`              | `cli-template`                                                                                                      | Internal template/example crate. Marked `excluded` in `docs/specs/completion-coverage-matrix-v1.md`; manifests should not pin against it.                                                                                                                              |
| `codex-cli`                 | `codex-cli`                                                                                                         | Codex runtime helper. Alias family `cx*` ships in `aliases.zsh` / `aliases.bash`. As of `v1.21.23`, optional rate-limit windows and no-window fallback harden the prompt/usage surface; runtime-kit consumes no new command from this binary ([#1165](https://github.com/sympoies/nils-cli/pull/1165)). As of `v1.21.25`, expired quota-cache values are omitted from prompt rendering ([#1177](https://github.com/sympoies/nils-cli/pull/1177)); the command shape remains unconsumed. |
| `docker-tools`              | `docker-tools`                                                                                                      | Docker helper CLI. As of `v1.0.12`, ships native container, compose-down, and run-zsh helpers plus generated completions. Runtime-kit does not consume this surface in required skill flows today. |
| `forge-cli`                 | `forge-cli`                                                                                                         | Forge runtime helper. As of `v0.20.0`, this repo consumes released PR create/deliver/check/merge/comment and general issue create/view/comment/list surfaces. Issue-backed plan-record lifecycle mutation is owned by `plan-issue record`, not by composing `forge-cli issue` calls in dispatch skills. `v0.20.1` adds `forge-cli label list`, `label audit`, and `label ensure` for GitHub/GitLab label catalogs, plus repeatable `--label`, `--label-catalog`, and `--strict-labels` on `pr create` and `pr deliver` so create/deliver macros preserve selected taxonomy labels. `v0.21.0` extends the `plan-issue record` surface with `--label` on `record open`, and `--add-label` / `--remove-label` on `record post` and `record close` so v3 lifecycle commands can apply taxonomy labels alongside issue creation, state transitions, and closeout. As of `v0.31.3`, `--provider` gains a `local` file-backed backend value plus a `--store-root` flag (and the `FORGE_CLI_LOCAL_STORE` env var) for offline rehearsal; the `github` / `gitlab` lifecycle surfaces are unchanged (additive). As of `v0.31.7`, `forge-cli` gains a GitHub-only `activity` discovery surface (`activity commits` / `events` / `summary`) and a `search` surface (`search issues` / `search prs` full-text via `gh search`, plus `search refs-to` cross-reference via `gh api graphql`), both behind the provider seam — GitLab / Local return `provider_unsupported`. As of `v1.0.11`, provider-visible bodies/comments fail closed with `local_path_present` when raw machine-local home paths are present, and diagnostics suggest `$HOME/...` without echoing the raw path. Runtime-kit issue and PR outcomes plus runtime smoke consume that privacy gate. As of `v1.0.14`, GitLab MR checks, wait-checks, and merge use structured GitLab API calls when project context is available, so PR/MR delivery and close surfaces that wait or merge MRs require `forge-cli >=1.0.14`; provider-mutating create-only workflows remain satisfied by their narrower floors. As of `v1.1.0`, `forge-cli pr deliver` adopts an existing open PR for the resolved head branch before falling back to create ([#823](https://github.com/sympoies/nils-cli/pull/823)); `deliver-pr` and `deliver-plan-tracking-issue` consume that split create -> iterate -> deliver path, so their `forge-cli` floor moves to `>= 1.1.0`. As of `v1.9.1`, `pr review-threads` is a subcommand group: the read surface is `pr review-threads list <id>` (the bare `pr review-threads <id>` positional is rejected), plus GitHub-only `pr review-threads resolve <pr> --thread <id>` (optional `--note` replies before resolving, idempotent) and `pr review-threads reply <pr> --thread <id>`; GitLab / Local return `provider_unsupported`. `deliver-pr` and the `review-thread-convergence` policy consume the `list` form, so the `forge-cli` floor moves to `>= 1.9.1` ([#883](https://github.com/sympoies/nils-cli/pull/883), [#885](https://github.com/sympoies/nils-cli/pull/885)). As of `v1.11.2`, provider context derives the repo slug from the configured remote and pushes `--repo <owner/name>` into backend calls by default ([#912](https://github.com/sympoies/nils-cli/pull/912)); runtime-kit skills rely on that fork-safe targeting when they pass `--provider` without an explicit `--repo`, so all `forge-cli`-consuming skill floors move to `>= 1.11.2`. As of `v1.17.0`, GitHub `pr review --submit-review --thread-file <path>` creates native, resolvable review threads for actionable findings while keeping summary-only review bodies for clean or informational reviews. `deliver-pr` and the internal review phase of `deliver-dispatch-plan` consume this provider-writing review surface, so their `forge-cli` floor moves to `>= 1.17.0` ([#951](https://github.com/sympoies/nils-cli/pull/951)). As of `v1.21.24`, GitLab `label list --limit` paginates beyond the provider's 100-item page cap while preserving the existing command and `cli.forge-cli.label.list.v1` envelope; runtime-kit consumes this behavior through plan closeout, but the floor does not move ([#1170](https://github.com/sympoies/nils-cli/pull/1170)). As of `v1.21.34`, GitHub gains `pr reviews` plus config-gated observed review convergence for merge-capable paths, with complete/final snapshot reads, native change-request enforcement, quiet timing after observation, thread/task gates, and provider-head binding. The three merge-owning delivery outcomes consume this surface, so their floor moves to `>= 1.21.34` ([#1201](https://github.com/sympoies/nils-cli/pull/1201)). As of `v1.22.9`, `repo push-default` provides the sole governed direct-main exception: one provider-bound push URL with no second-stage rewrite, one signed fast-forward commit from an exact base, an internal exact-old-object lease, bounded inputs/processes, and verified remote-head receipt. Runtime-kit's always-on delivery policy consumes it, so the global `forge-cli` floor moves to `>= 1.22.9` ([#1251](https://github.com/sympoies/nils-cli/pull/1251)). As of `v1.22.10`, `pr reviews` separates pending drafts into `data.pending_reviews[]`, and GitHub-only `pr pending-review delete` removes one exact provider-verified pending node. The three merge-owning delivery outcomes consume this guarded recovery path, so their floor and the global `forge-cli` floor move to `>= 1.22.10` ([#1259](https://github.com/sympoies/nils-cli/pull/1259)). As of `v1.22.11`, `pr review --submit-review` requires `--expected-head`, rejects head drift before mutation, binds provider writes to that reviewed commit, and reports a viewer-owned draft as `github_pending_review_exists`. Runtime-kit's three merge-owning delivery outcomes consume that trusted-head and typed-recovery contract, so their floor and the global `forge-cli` floor move to `>= 1.22.11` ([#1266](https://github.com/sympoies/nils-cli/pull/1266)). As of `v1.22.12`, direct merge accepts an expected provider head and `pr pending-review delete` requires exact expected-head, expected-commit, expected-body, and abandonment confirmation, with bounded bodies and complete bounded pagination before mutation. The three merge-owning delivery outcomes consume this compare-and-delete contract, so their floor and the global `forge-cli` floor move to `>= 1.22.12` ([#1269](https://github.com/sympoies/nils-cli/pull/1269)). |
| `fzf-cli`                   | `fzf-cli`                                                                                                           | fzf wrapper. Alias family `fx*` ships in `aliases.zsh` / `aliases.bash`. As of `v1.0.8`, `fzf-cli def` closes the generated preview script temp file before fzf executes it, avoiding Linux `text file busy` failures in container TTYs. As of `v1.0.12`, native `open-changed-files`, `kill-process`, and `kill-port` helpers replace local shell-helper behavior. As of `v1.21.32`, definition indexing accepts configurable roots ([#1196](https://github.com/sympoies/nils-cli/pull/1196)); runtime-kit does not consume these helper commands in required skill flows today. |
| `gemini-cli`                | `gemini-cli`                                                                                                        | Gemini runtime helper.                                                                                                                                                                                                                                                 |
| `git-cli`                   | `git-cli`                                                                                                           | git workflow helper. Alias family `gx*` ships in `aliases.zsh` / `aliases.bash`. As of `v0.31.5`, this repo consumes `git-cli worktree add/list/remove/prune` for managed worktrees under `$AGENT_HOME/worktrees/<repo-key>/<branch-slug>` with text and JSON output. As of `v1.0.4`, `worktree add` gains `--kind <feature\|bug\|chore\|docs\|ci\|refactor>` (default `feature`), deriving `<prefix>/<slug>` from the shared `nils_common::git::PrKind` mapping that `forge-cli`'s `branch_kind` rule also consumes, so a non-feature worktree matches the prefix `forge-cli pr deliver --kind` expects without a manual rename. As of `v1.0.6`, `worktree remove` detects when a not-found target exactly matches a linked worktree branch name and returns a hint pointing at the slug and full path; text-mode errors now print hints as well. Both changes are additive; the `v1.0.4` flag remains policy guidance rather than an automated skill invocation, and the `v1.0.6` hint is an ergonomic recovery path, so no `required_clis[]` floor moves. As of `v1.24.1`, `worktree dirty-snapshot`, `worktree adopt-dirty`, and `worktree revoke-dirty` provide the governed dirty-checkout transaction consumed by `checkout-lease-guard.py`: private v1 challenge and receipt envelopes bind exact repository, checkout, session, snapshot, and expiry provenance while revocation invalidates the adopted lease. This integration raises the runtime-kit `git-cli` floor to `>= 1.24.1` ([#1272](https://github.com/sympoies/nils-cli/pull/1272)). |
| `git-lock`                  | `git-lock`                                                                                                          | git lock helper.                                                                                                                                                                                                                                                       |
| `git-scope`                 | `git-scope`                                                                                                         | git scope summariser. Alias family `gs*` ships in `aliases.zsh` / `aliases.bash`. As of `v1.0.10`, `git-scope` renders directory trees internally and no longer depends on an external `tree` binary. Additive ergonomic fix; no runtime-kit `required_clis[]` floor moves. |
| `git-summary`               | `git-summary`                                                                                                       | git diff summariser.                                                                                                                                                                                                                                                   |
| `github-app-cli`            | `github-app-cli`                                                                                                    | GitHub App installation-token minter (`token`, `installations`, `completion`). Signs the App JWT in-process (`jsonwebtoken`, RS256) and calls the GitHub REST API directly (`reqwest`); text mode prints only the raw `ghs_` token for `GH_TOKEN=$(github-app-cli token …)`, JSON mode emits non-secret metadata only and never the token. New crate as of `v1.9.6` ([#903](https://github.com/sympoies/nils-cli/pull/903)). Not consumed by this repo's runtime surfaces; used out-of-band by a local `forge-cli` bot-identity wrapper, so it never appears in `required_clis`. |
| `image-processing`          | `image-processing`                                                                                                  | User-facing image-processing CLI.                                                                                                                                                                                                                                      |
| `macos-agent`               | `macos-agent`                                                                                                       | macOS automation helper. As of `v1.21.13`, runtime-kit consumes app/window discovery, AX selectors/actions, screenshots, waits, scenarios, key/type/hotkey, pointer click/move/bounded drag, horizontal/vertical scroll, modifier-assisted mouse actions, secondary-display absolute coordinates, and held-input cleanup through the `computer-use.macos-desktop` skill ([#1106](https://github.com/sympoies/nils-cli/pull/1106)). As of `v1.21.32`, screenshot preflight recognizes the installed screen-record compatibility probe without changing flags or envelopes ([#1194](https://github.com/sympoies/nils-cli/pull/1194)). As of `v1.22.6`, the native engine is replaced by a guarded adapter around immutable Peekaboo `v3.9.3`; runtime-kit consumes locked backend lifecycle, strict doctor/capabilities, local/SSH exec and scenario transport, stdio MCP tool profiles, and journal/redaction/guarded-replay v2, so the floor moves to `>= 1.22.6` ([#1234](https://github.com/sympoies/nils-cli/pull/1234)). As of `v1.22.7`, strict doctor probes permissions and Bridge readiness through one stable app socket, preventing stale default-runtime selection from reporting a false blocker; the existing command and envelopes are unchanged, so the floor remains `>= 1.22.6` ([#1247](https://github.com/sympoies/nils-cli/pull/1247)). As of `v1.27.3`, runtime-kit adopts adapter v3 and immutable Peekaboo `v4.2.2`: the scenario surface is retired in favor of individually reviewed chained `exec` calls, the remote wire schema advances to v3, active CLI/app artifacts require full notarization posture, and v3.9.3 remains transition-only for authenticated in-place upgrade and interrupted-upgrade recovery. The compatibility floor therefore moves to `>= 1.27.3` ([#1478](https://github.com/sympoies/nils-cli/pull/1478)). |
| `memo`                  | `memo`                                                                                                          | Memo storage CLI.                                                                                                                                                                                                                                                      |
| `nils-build-info`           | (library only)                                                                                                      | Build metadata helper for the workspace `--version` output; consumed transitively, never appears in `required_clis`. New crate as of `v0.28.0` (#625).                                                                                                                 |
| `nils-common`               | (library only)                                                                                                      | Shared workspace utilities; never appears in `required_clis`.                                                                                                                                                                                                          |
| `nils-evidence`             | `evidence`                                                                                                          | Query/migrate CLI over the durable, secret-scrubbed skill-usage evidence archive (`migrate` / `discover` / `query` / `search` / `catalog` / `validate-*` / `prune-source`). New crate as of `v1.5.0`; consumed by policy-owned evidence migration, which sets the `evidence >= 1.6.0` floor mirrored in `docs/source/nils-cli-pin.yaml`. As of `v1.6.1`, `migrate` hardens scrub/path handling, query/catalog/XDG behavior, and host-vouch precedence so `--host` resolves slug-only records without overriding records that already resolve a cwd identity ([#854](https://github.com/sympoies/nils-cli/pull/854), [#856](https://github.com/sympoies/nils-cli/pull/856)). As of `v1.8.0`, `migrate` hardens cwd/origin and slug identity matching for nested source rescue, repointed or ambiguous cwd guards, refined cwd-vs-slug matching, and one uniform slug rule; `purge --apply` also hardens destructive-operation safety. Policy-owned evidence migration and session closeout consume those guarantees, so the `evidence` floor moves to `>= 1.8.0` ([#873](https://github.com/sympoies/nils-cli/pull/873), [#874](https://github.com/sympoies/nils-cli/pull/874), [#877](https://github.com/sympoies/nils-cli/pull/877), [#878](https://github.com/sympoies/nils-cli/pull/878), [#879](https://github.com/sympoies/nils-cli/pull/879), [#880](https://github.com/sympoies/nils-cli/pull/880)). As of `v1.12.0`, `prune-source --archived-only` is the source-cleanup counterpart to copy-only migration: it reads archive `catalog.json` source digests, dry-runs by default, and `--apply` deletes only already-archived local source run directories. Policy-owned source pruning and session closeout consume that surface, so the `evidence` floor moves to `>= 1.12.0` ([#916](https://github.com/sympoies/nils-cli/pull/916)). |
| `nils-markdown`             | `md-render`                                                                                                         | Shared Tera-backed Markdown template layer. Ships the `md-render` binary behind the `bin-cli` cargo feature (enumerated by `workspace-bins.sh`); library role otherwise, not consumed by any skill today. Present since before `v0.25.8`; the prior snapshot omitted it. |
| `nils-provider-resume`      | (library only)                                                                                                      | Shared provider session-resume resolver (bounded Codex/Claude session-history scan, `session_meta` / transcript parsing, scan budgets, and structured resolve outcomes) extracted for `codex-cli` / `claude-cli` / `agent-session`. New crate as of `v1.21.9` ([#1096](https://github.com/sympoies/nils-cli/pull/1096)); never appears in `required_clis`.|
| `nils-scrub`                | (library only)                                                                                                      | Shared secret-scrub pattern set plus labelled scrub-log format, extracted from `plan-archive` so both `plan-archive refresh` and `evidence migrate` reuse one v1 implementation. New crate as of `v1.5.0`; never appears in `required_clis`.                            |
| `nils-term`                 | (library only)                                                                                                      | Terminal / TTY helpers; never appears in `required_clis`.                                                                                                                                                                                                              |
| `nils-test-support`         | (library only)                                                                                                      | Integration-test harness; test-only, never appears in `required_clis`.                                                                                                                                                                                                 |
| `opencode-cli`              | `opencode-cli`                                                                                                      | OpenCode runtime helper. As of `v1.0.12`, ships native prompt, advice, knowledge, and commit-agent command helpers plus generated completions. Runtime-kit does not consume this surface in required skill flows today. |
| `plan-archive`              | `plan-archive`                                                                                                      | Plan-archive workflow CLI. As of `v0.25.0`, ships `validate-hosts` / `validate-local` / `validate-metadata` validators, `migrate` (dry-run default, `--apply`), `refresh` (forge-cli payload fetch + secret-scrub + append-only `_index/` snapshots, holds commit for scrub-log review), and `query` (single-ref / cross-host aggregate / plan-link traversal). As of `v0.25.5`, adds `discover` (read-only candidate scanner that classifies plan folders as eligible / blocked / unknown and emits one combined `suggested_migrate_command` per eligible folder). As of `v0.28.5`, `migrate` reconciles an archived plan's `*-execution-state.md` `## Execution State` header (`Status` / `Current task` / `Next task`) to a terminal "archived" status deferring to the issue/PR ref, and the apply report adds `execution_state_reconciled`. As of `v0.30.2`, `catalog` gains `--deep` (extends `--grep` to also match issue/PR/MR body + comment text via each ref's latest snapshot, composing with `--area` / `--refs-to`) and a new `search <term>` subcommand returns hit-level matches (owning plan slug + ref URL + matched field + snippet) in a versioned JSON envelope; both are additive. Consumed directly by plan delivery and policy-owned archive maintenance. |
| `plan-issue`            | `plan-issue`, `plan-issue-local`                                                                                    | Multi-binary crate. `plan-issue` is the GitHub-backed orchestrator; `plan-issue-local` is the local rehearsal pair. Manifests pin individual binary names. As of `v0.20.0`, issue-backed records use the provider-backed `record open`, `record post`, `record audit`, `record repair-dashboard`, and `record close` surface. The current marker is `plan-issue-record:v2 role=<source|plan|state|session|validation|review|closeout> profile=<tracking|dispatch>`. As of `v0.22.3`, state lifecycle comments can render canonical execution-state markdown through `record post --kind state --execution-state-file <path>`, support `--task-ledger-display auto|collapsed|expanded|open`, and render validation, review, session, and closeout evidence visibly alongside hidden payload carriers. As of `v0.25.6`, ships `record template --kind <role> --shape markdown|json` for non-mutating skeleton preview, `record audit --expect-visible` for visible-completeness lint, and the `tracking` controller surface (`tracking status`, `tracking run init`, `tracking run update`, `tracking checkpoint`, `tracking close-ready`) backed by `plan-issue.execution-run.v1` run state and `plan-issue.execution-event.v1` events. `tracking checkpoint --live --post <roles> --repair-dashboard` posts one provider lifecycle comment per role in declaration order, aborts on the first per-role failure with a `tracking-checkpoint-live-post-failed` blocker, and only refreshes the dashboard once every role succeeds; combine with `--fixture DIR` to exercise the live path deterministically (synthesized `fixture://issue/N/role` URLs and no provider mutation). As of `v0.25.7`, `tracking close-ready` emits a `ledger-rows-pending` blocker (one entry per stuck row) when `phase ∈ {ready_for_close, closed}` and the run-state's `bundle` resolves to a `*-execution-state.md` whose ledger still carries `Status ∈ {pending, in-progress}`; the silent-skip path keeps older run-states without a `bundle` field working. The `open` task-ledger-display mode renders an open `<details open>` fold (toggle present, rows visible by default), and `record open` posts the first Execution State with it so the full Task Ledger is visible on load while `expanded` stays raw rows for the final pre-closeout state. As of `v0.28.3`, `tracking checkpoint --live` inherits `repo`/`issue` from the run-state when `--provider-repo`/`--issue` are omitted (consistent with `tracking status` / `close-ready`), and `tracking checkpoint --post session` synthesizes the session summary from run-state activity (selected task, branch, linked PRs, validation, phase) when no explicit `--note` exists instead of silently dropping the role ([#644](https://github.com/sympoies/nils-cli/pull/644), [#645](https://github.com/sympoies/nils-cli/pull/645)). As of `v0.31.4`, bundle-backed state checkpoints resolve the full `## Task Ledger` from the recorded bundle when `execution_state_file` is absent, and recorded-but-unreadable ledgers block with `state-ledger-unresolved` instead of degrading silently. As of `v1.0.0`, the crate (`plan-issue`), package (`nils-plan-issue`), library, and the JSON output contract namespace dropped the `-cli` suffix — the contract is now `plan-issue.*` (for example `plan-issue.record.post.v2`, `plan-issue.start.plan.v2`, `plan-issue.tracking.status.v1`), renamed from `plan-issue-cli.*` with no backward compatibility. The run-state / event schemas (`plan-issue.execution-run.v1`, `plan-issue.execution-event.v1`) were already `-cli`-free and are unchanged. As of `v1.0.10`, `tracking run update` records review lenses, retained outcome evidence, and optional finding rows with `--review-lens`, `--review-outcome-comment`, and `--review-findings-file`; `tracking checkpoint` renders that context into Review Evidence, and visible lint rejects decision-only review comments with `review-missing-context`. As of `v1.0.11`, provider-bound lifecycle comments and dashboards fail closed with `local_path_present` when raw machine-local home paths are present, and diagnostics suggest `$HOME/...` without echoing the raw path. Runtime-kit plan outcomes and smoke consume both surfaces. As of `v1.0.13`, the live lifecycle mutation lock serializes same issue/profile comment streams with `plan-issue-lifecycle-lock-busy`, so `plan-issue >=1.0.13` is the floor for plan issue outcomes. As of `v1.1.0`, `record close` and `tracking close-ready` share the same terminal task-row contract (`done` / `deferred` / `waived`) ([#825](https://github.com/sympoies/nils-cli/pull/825)); `deliver-pr` and the internal closeout phases of both plan outcomes consume that closeout behavior, so their `plan-issue` floors move to `>= 1.1.0`. As of `v1.21.23`, structural review parsing, dispatch closeout headings, close-ready validation, provider-label readback, and terminal writeback harden existing lifecycle contracts without changing the consumed command shape ([#1153](https://github.com/sympoies/nils-cli/pull/1153), [#1158](https://github.com/sympoies/nils-cli/pull/1158), [#1160](https://github.com/sympoies/nils-cli/pull/1160), [#1163](https://github.com/sympoies/nils-cli/pull/1163), [#1166](https://github.com/sympoies/nils-cli/pull/1166)). As of `v1.21.24`, `record close` preflights and normalizes provider lifecycle labels before close, confirms read-back, and rolls back only its owned delta on pre-close failure; the existing flags and output envelope remain stable, so the floor does not move ([#1170](https://github.com/sympoies/nils-cli/pull/1170)). |
| `plan-tooling`              | `plan-tooling`                                                                                                      | Plan bundle linter / validator. As of `v0.25.7`, adds `ledger-update` (atomic one-call row patch for the canonical `*-execution-state.md` `## Task Ledger` table; stable error codes `ledger-row-not-found`, `ledger-row-ambiguous`, `ledger-table-malformed`, `ledger-status-invalid`) and `ledger-sync --from-issue` (read-mostly drift reconciliation against issue body + comments; `--write` patches only empty Evidence cells via the empty-cell preference rule). Both are consumed by the active plan outcomes and by the `plan-issue tracking close-ready` `ledger-rows-pending` blocker. As of `v1.21.23`, terminal execution-state completion handles EOF and heading-only section bounds while preserving the existing consumed commands ([#1166](https://github.com/sympoies/nils-cli/pull/1166)). |
| `screen-record`             | `screen-record`                                                                                                     | Screen-recording helper (macOS).                                                                                                                                                                                                                                       |
| `secrets`                   | `secrets`                                                                                                           | Thin `sops` + `git` wrapper that pulls / pushes a repo's `.env` from the central `graysurf/secrets` SOPS store (`pull`, `add`, `list`, `which`, `edit`, `completion`), mapping the repo's `origin` remote (or a `repos/<o>/<r>` / `stacks/<x>` name) to a store entry. stdout and the JSON envelope (`cli.secrets.<command>.v1`) carry only metadata (store paths, entry names, counts); decrypted secret values are written to `./.env` (mode `600`) and never echoed. Requires `git` + `sops` on PATH; `SECRETS_REPO` overrides the store path. New crate as of `v1.10.0` ([#907](https://github.com/sympoies/nils-cli/pull/907)). Not consumed by this repo's runtime surfaces; driven out-of-band by the private `private-secrets` skill, so it never appears in `required_clis`. |
| `semantic-commit`           | `semantic-commit`                                                                                                   | Semantic commit message validator and committer.                                                                                                                                                                                                                       |
| `web-evidence`              | `web-evidence`                                                                                                      | Web evidence capture helper.                                                                                                                                                                                                                                           |
| `zsh-kit`                   | `zsh-kit`                                                                                                           | Zsh setup helper. As of `v1.0.7`, this repo's Docker surface consumes `zsh-kit setup --repo <URL_OR_PATH> --dry-run|--apply` for operator-supplied runtime shell setup, with `--features`, `--install-tools`, and optional `.zshenv` management. As of `v1.0.9`, this repo depends on `--write-zshenv` preserving `ZSH_FEATURES` and sourcing `$ZDOTDIR/.zshenv` so first-run container shells get repo-owned environment wiring. As of `v1.0.12`, native plugin fetch/update/maybe-update/status helpers are available; runtime-kit does not consume those helper commands in required skill flows today. |

## Refresh procedure

When `sympoies/nils-cli` cuts a new release that consumers should pin against:

1. Pull the latest `main` of `sympoies/nils-cli`.
2. Re-run `ls ~/Project/sympoies/nils-cli/crates/` to verify the crate list.
3. Re-run `bash scripts/workspace-bins.sh` (in the nils-cli checkout) to
   verify the binary list.
4. Re-run `git describe --tags` and update the header.
5. Replace any row whose binary set changed; add new rows alphabetically.
6. Bump the snapshot date and head commit pointer.
7. Manifest authors then refresh `required_clis` pins in
   `manifests/skills.yaml` / `manifests/plugins.yaml` against the new surface.
