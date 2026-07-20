# nils-cli Version Policy Implementation Handoff

- Status: approved for L2 execution
- Date: 2026-07-19
- Source: maintainer discussion after the nils-cli v1.24.3 runtime-kit closeout
- Intended next step: reconcile the linked L2 plan in a fresh session, finish
  its plan-bundle commit, then begin test-first implementation; do not change the
  installed runtime or dependency pin during this authoring session

## Execution

- Recommended plan: docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-plan.md
- Recommended execution state: docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-execution-state.md

## Purpose

Separate three meanings currently collapsed into one exact `pinned_tag`:

1. the oldest nils-cli release runtime-kit promises to support;
2. the exact release against which runtime-kit snapshots, checksums, images,
   and formal validation are produced; and
3. a newer local or canary release used to detect forward incompatibility.

The current exact gate correctly prevents unreviewed toolchain drift, but it
also makes an otherwise compatible newer local nils-cli block the complete
development gate before downstream tests run. The replacement must allow a
developer host at or above the supported floor while preserving exact,
reproducible validation and packaging lanes.

## Confirmed Facts

- [U1] The maintainer wants newer nils-cli releases to be usable for local
  development and testing when they satisfy a declared minimum version, with CI
  still detecting incompatibility and retaining a way to test the minimum.
- [U2] The maintainer selected L2 plan tracking and asked that implementation be
  handed to the next session.
- [F1] `docs/source/nils-cli-pin.yaml` schema v1 defines only
  `nils_cli.pinned_tag` and explicitly requires exact host equality; its release
  SHA256 values are coupled to that same tag.
- [F2] `scripts/ci/all.sh` Position 2 invokes `agent-runtime doctor --class
  version-alignment` and aborts the remaining stack when the ambient host is
  ahead or behind the pin.
- [F3] `.github/workflows/ci.yml` downloads the exact `pinned_tag` and runs the
  complete gate through that release surface.
- [F4] `.github/workflows/publish-image.yml`, `docker/build.sh`, and
  `docker/Dockerfile` use the same tag and SHA256 pair as an exact distributable
  artifact identity.
- [F5] `docs/source/nils-cli-version-workflows.md` currently requires off-pin
  development to run content gates individually because the complete gate stops
  at Position 2.
- [F6] `scripts/ci/version-baseline-audit.py`, README, surface docs, and harness
  shape docs mirror a single pin and have no vocabulary for a compatibility
  floor versus a validated release.
- [F7] Archived plan `2026-05-24-nils-cli-version-alignment` and its adoption
  follow-up deliberately chose exact equality after silent host drift caused
  fixtures and generated surfaces to be exercised by an unreviewed binary.
- [A1] On 2026-07-19, the installed `agent-runtime 1.24.4` produced 16 ok, zero
  warn, and one block against the v1.24.3 manifest; every declared per-binary
  floor passed, and the only blocker was `version-alignment.host`.
- [A2] The deterministic version-baseline audit passed 24/24 while still
  mirroring the single v1.24.3 pin, confirming that the current documentation is
  internally consistent but cannot express the desired split.
- [A3] Plan-archive search found the completed exact-gate plans above and no
  active plan that owns this compatibility-floor redesign. Live open-issue
  read-back found adjacent hook/session plans but no duplicate version-policy
  tracker.

## Decisions

1. Replace the single semantic role of `pinned_tag` with a schema-v2 contract
   containing `minimum_supported_tag` and `validated_tag`. Do not encode a raw
   comparison expression such as `">=v1.24.3"` as the sole source of truth.
2. Bind release SHA256 values, Docker defaults, published images, and reproducible
   snapshots to `validated_tag`, never to the ambient host version.
3. Admit an installed development host when its nils-cli version is greater than
   or equal to `minimum_supported_tag` and all `required_clis` floors pass.
   Below-minimum remains a block. Above-validated is visible as a warning, not a
   block; it is not represented as formally validated merely because it is
   admitted.
4. Keep schema-v1 manifests backward compatible with exact-equality behavior.
   A v1 consumer must never silently reinterpret `pinned_tag` as a floor.
5. Add three validation roles:
   - minimum lane: blocking, exact `minimum_supported_tag`;
   - validated lane: blocking, exact `validated_tag`, owning render/golden/full
     gate and package reproducibility;
   - latest-stable canary: scheduled/manual and initially non-required, but
     failure must be visible and actionable rather than discarded.
6. Keep the ordinary local full gate on the ambient admitted host so a developer
   running a newer release reaches the behavioral tests. CI remains authoritative
   for minimum and validated coverage.
7. Keep every `required_clis[]` floor independent and blocking. The new top-level
   floor does not replace per-binary consumed-surface floors.
8. Change the bump ceremony so `validated_tag` and checksums move on ordinary
   release uptake, while `minimum_supported_tag` moves only after an explicit
   compatibility-floor decision backed by a green minimum lane.
9. Implement stable manifest parsing, semver comparison, doctor envelopes, and
   compatibility behavior in `sympoies/nils-cli`. Runtime-kit owns its manifest,
   CI lane orchestration, bootstrap extraction, packaging choices, documentation,
   skills, and acceptance fixtures.
10. Keep this work serial L2 rather than L3: upstream schema support must exist
    before runtime-kit can consume it, and a release boundary separates those
    stages.

## Scope

- nils-cli schema-v2 support in `agent-runtime doctor --class
  version-alignment`, with typed checks for minimum, validated, required CLI,
  and malformed policy relationships.
- Runtime-kit migration of the machine-readable manifest and every parser,
  mirror, workflow, Docker consumer, bump skill, and test fixture that assumes
  one `pinned_tag`.
- Blocking minimum and validated CI lanes plus a visible latest-stable canary.
- Documentation of local ambient-host development, explicit minimum testing,
  formal validated testing, release promotion, and rollback/reproduction.
- Test-first evidence, governed PR delivery, independent review, strict L2
  closeout, and archive handoff.

## Non-Scope

- Accepting a version below the minimum or bypassing a failing `required_clis`
  floor.
- Treating every future nils-cli release as proven compatible.
- Removing exact checksums or allowing Docker/image builds to use an ambient
  Homebrew version.
- Auto-moving the minimum whenever `validated_tag` advances.
- Auto-releasing nils-cli, changing Homebrew, or applying live runtime surfaces
  without the later owning workflow's explicit authorization.
- Fixing the unrelated `agent-runtime audit-drift` identical-content false
  positives or the finish-line hook's blocked-edit marker behavior; route those
  separately by owner.
- Expanding hook-control-plane or session-coordination work from #686 or #676.

## Implementation Boundaries

### Upstream nils-cli

- Define schema-v2 parsing and validation while retaining schema-v1 exact
  behavior.
- Compare stable semantic versions without repo-local shell semver logic.
- Emit stable JSON/text checks that distinguish below-minimum block,
  minimum/validated success, above-validated warning, required-CLI failure, and
  invalid manifest relationships.
- Add fixtures for prerelease/build metadata, missing fields, minimum greater
  than validated, and v1 compatibility.

### agent-runtime-kit

- Migrate `docs/source/nils-cli-pin.yaml` and its human-facing mirrors.
- Keep bootstrap parsing small and deterministic where nils-cli is not yet
  available, while avoiding duplicate version-comparison logic.
- Run the ambient local stack after admission; run exact minimum and validated
  surfaces in CI; preserve validated tag/digest pairing in Docker and release
  workflows.
- Update `meta:nils-cli-bump` and `project-version-baseline` so their language
  and checks reflect both roles.

## Requirements

### Manifest contract

The final schema may refine field nesting, but it must expose these stable
semantic roles:

```yaml
schema_version: 2
nils_cli:
  minimum_supported_tag: "v1.24.3"
  validated_tag: "v1.24.3"
  release_sha256:
    linux_amd64: "<digest for validated_tag>"
    linux_arm64: "<digest for validated_tag>"
required_clis:
  - bin: git-cli
    min: "1.24.1"
```

The strict released schema remains unchanged. Runtime-kit retains the minimum
lane's tag and digest pair separately in
`docs/source/nils-cli-minimum-digest.yaml`; CI/audits require its tag to equal
`minimum_supported_tag`. Validation must reject
`minimum_supported_tag > validated_tag`, missing or malformed stable tags,
missing role-owned release digests, and duplicate or invalid required CLI
entries. Ordinary validated uptake preserves the minimum digest manifest;
explicit floor retirement moves it.

### Doctor behavior

| Observed host | Result |
| --- | --- |
| below minimum | block |
| equal to minimum | ok |
| between minimum and validated | ok |
| equal to validated | ok |
| above validated | warn, with compatibility-not-validated wording |
| any required CLI below its floor | block |
| schema v1 differs from `pinned_tag` | block, preserving v1 exact semantics |

Warnings do not suppress downstream content validation. Exit behavior must
continue to block only when `block > 0`.

### CI and packaging

- Pull-request and main CI run the full gate at both the exact minimum and exact
  validated release. When both tags are equal, the workflow may de-duplicate the
  identical execution while reporting both semantic roles.
- A scheduled/manual latest-stable canary runs the relevant full/content gate,
  records the resolved tag and failure output, and does not silently change the
  manifest.
- Local `scripts/ci/all.sh` accepts the ambient host at or above minimum and
  proceeds through render, drift, smoke, hook, and baseline checks.
- Docker, GHCR publishing, checksum audit, and release provenance always resolve
  `validated_tag` and its matching digests.
- No workflow infers `validated_tag` from the latest release at execution time.

### Bump and rollback workflow

- Ordinary uptake updates `validated_tag`, its digests, surface snapshot, and
  affected consumer floors; it leaves the minimum unchanged by default.
- A minimum-floor move is a separate explicit decision and requires proof that
  the old floor is intentionally retired.
- Reproduction and rollback helpers can run either declared exact role without
  mutating Homebrew or the manifest.
- A newer ambient developer host can run the complete local gate; developers no
  longer need to hand-enumerate every content position solely because they are
  above the validated release.

## Acceptance Criteria

- A fixture at one patch below minimum blocks before content gates.
- Exact minimum and exact validated lanes pass and are provider-visible.
- An ambient host one patch above validated produces a warning, not a block,
  then reaches a downstream sentinel test.
- A deliberately incompatible newer fixture is caught by downstream validation,
  proving that `>=` is admission rather than blind success.
- Schema-v1 exact behavior remains covered and unchanged.
- Minimum greater than validated, mismatched checksum ownership, and malformed
  tags fail closed.
- CI de-duplicates equal minimum/validated tags without losing role reporting.
- Latest canary failure is visible with the resolved version and remediation,
  and never rewrites the manifest automatically.
- Docker dry-run and publish-workflow tests prove use of validated tag/digests.
- Version baseline, README, surface docs, harness shape docs, bump skill, and
  version-workflow docs agree on both roles.
- Full runtime-kit CI and hook suites pass on the released schema-v2 nils-cli.
- No live runtime sync, Homebrew mutation, or release occurs without its own
  explicit authorization.

## Validation Plan

- Nils-cli: meaningful-red doctor fixtures, focused unit/integration tests,
  schema/CLI snapshot tests, clippy/docs/completion checks, then repository CI.
- Runtime-kit: plan validation; version-policy parser fixtures; minimum,
  validated, ahead-warning, below-floor, malformed-manifest, and equal-tag
  cases; security-hardening audit; baseline audit; runtime smoke; full
  `scripts/ci/all.sh`; and `tests/hooks/run.sh`.
- Packaging: `docker/build.sh --dry-run`, publish-workflow static audit, and
  checksum/tag binding fixtures.
- Delivery: exact-head provider checks, independent testing and maintainability
  review plus risk-selected lenses, no unresolved actionable threads, merged
  revision read-back, and strict L2 close-ready audit.

## Risks And Guardrails

- Risk: `>=` can be mistaken for a compatibility guarantee. Guardrail: doctor
  warns above validated, and only exact CI lanes carry validated status.
- Risk: the minimum lane rots while development follows latest. Guardrail: it is
  blocking and runs on every PR/main workflow.
- Risk: two version fields drift. Guardrail: reject minimum greater than
  validated and audit every mirror and packaging consumer.
- Risk: latest canary availability or upstream breakage blocks unrelated work.
  Guardrail: keep it scheduled/manual and visible but initially non-required.
- Risk: bootstrap parsing diverges from nils-cli semantics. Guardrail: bootstrap
  code only extracts declared exact tags; nils-cli owns all comparisons.
- Risk: a schema migration weakens existing users. Guardrail: schema v1 remains
  exact and tested until its explicit retirement.

## Read First References

- `docs/source/nils-cli-pin.yaml`
- `docs/source/nils-cli-version-workflows.md`
- `docs/source/nils-cli-surface.md`
- `scripts/ci/all.sh`
- `.github/workflows/ci.yml`
- `.github/workflows/publish-image.yml`
- `docker/build.sh`
- `scripts/ci/security-hardening-audit.py`
- `scripts/ci/version-baseline-audit.py`
- `.agents/skills/project-version-baseline/SKILL.md`
- `core/skills/meta/nils-cli-bump/SKILL.md.tera`
- archived plan `2026-05-24-nils-cli-version-alignment`

## Retention Intent

This is coordination material. Keep it with the active L2 bundle, then migrate
the complete plan through `plan-archive` after strict closeout unless a portion
is deliberately promoted into canonical version-policy documentation.
