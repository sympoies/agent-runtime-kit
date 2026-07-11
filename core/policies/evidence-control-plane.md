# Evidence Control Plane

## Purpose

Evidence commands are deterministic workflow primitives, not user outcomes.
The parent intent or outcome workflow decides whether evidence is warranted,
allocates one workflow-owned artifact root, invokes the primitive, verifies the
record, and carries only the useful result into delivery or closeout.

Direct CLI calls remain supported for diagnostics. Normal collaboration should
not require a user to select `test-first-evidence`, `docs-impact`,
`review-evidence`, `skill-usage`, `web-evidence`, or `model-cross-check` as a
separate task.

## Ownership And Ordering

| Need | Owner | Required ordering and completion boundary |
| --- | --- | --- |
| Test-first discipline | Implementation parent | Classify before production edits; record a failing test or explicit waiver; run `test-first-evidence check --phase pre-edit` for known changed paths when the repository declares `[path_classes]`; verify at delivery. |
| Documentation impact | Implementation or delivery parent | After the complete change exists, run `docs-impact record` with `docs-updated`, `no-docs-needed`, or `pending`; `docs-impact verify` must pass against the current Git state before delivery. |
| Review findings | Review parent | Create one `review-evidence` record only when retained findings or validation evidence are useful; reviewer observations remain inputs, not automatic decisions. |
| Workflow usage | Outermost outcome workflow | Create at most one `skill-usage.record.v2` with `--owner-kind workflow` or `--owner-kind intent`; link verified child records instead of opening nested usage records for each primitive. |
| Static HTTP capture | External-fact, browser-test, or validation parent | `web-evidence` supports an HTTP claim only; it never proves rendered JavaScript, visual state, or desktop interaction. |
| Model cross-check | Parent that requested a checker | Provider calls happen outside the primitive; record both observations and verify once. Do not create a cross-check merely because the recorder exists. |
| Session closeout | Outermost session workflow | Finalize the existing workflow record, preserve warranted follow-up, then archive/prune through the governed closeout path. Do not create a duplicate closeout-owned usage record. |

Allocate records through `agent-out` unless an active workflow already owns a
project-defined artifact directory. Serialize writes to each record directory.
Verify child records before linking them and never commit raw runtime evidence
into a working repository.

## Test-First Paths

For testable behavior, initialize the record before production edits and make
the pre-edit decision explicit:

```bash
test-first-evidence init --out "$EVIDENCE_DIR" \
  --classification behavior-change --production-path src/example
test-first-evidence record-failing --out "$EVIDENCE_DIR" \
  --command "<focused test>" --exit-code 1 --summary "<observed failure>"
test-first-evidence check --out "$EVIDENCE_DIR" --phase pre-edit \
  --project-path . --path src/example --format json
```

Docs-only and generated-only work may record an explicit waiver. An unavailable
test harness may also use a waiver only when the parent states why no failing
test is practical and names substitute validation. Unknown or overlapping path
classes fail closed; a repository without `[path_classes]` reports
`not-configured` and leaves judgment with the parent rather than inventing
language-specific rules.

The observable enforcement points stay narrow:

- Codex and Claude pre-edit hooks verify that `project-dev` is active for the
  current session in every canonical direct-edit target repository. Shell
  commands are verified against their working repository only; a pre-tool hook
  cannot reliably observe destinations assembled by shell expansion. Therefore
  cross-repository shell mutations must run with each target repository as CWD,
  and hooks do not claim target-level authorization for dynamic shell paths.
- `test-first-evidence check` verifies classified/pre-edit/delivery phases; the
  parent invokes it because a hook cannot discover an arbitrary evidence
  directory safely.

The hook layer is a mechanical workflow guardrail rather than a security
sandbox. The agent product's launch environment, managed runtime home, and
resolved executable `PATH` are trusted host inputs; a process that can replace
those inputs can also replace the hook itself.
- `forge-cli` enforces a complete test-first record at feature/bug PR creation
  when the repository or user config enables that gate.
- The finish-line hook enforces declared validation commands after code edits.
- Hooks do not decide whether a test, docs update, review finding, web source,
  or second model is semantically necessary.

## Durable Delivery Records

After the complete Git change exists, the implementation or delivery parent
records one current docs disposition and verifies it immediately before PR
delivery:

```bash
docs_dir="$(agent-out project --topic docs-impact --mkdir)"
docs-impact record --out "$docs_dir" --repo . --base origin/main \
  --disposition no-docs-needed --rationale "<grounded reason>"
docs-impact verify --out "$docs_dir" --repo . --format json
```

Use `docs-updated` when the matching source docs changed and `pending` only as a
non-terminal state. A later Git change makes the record stale and requires a
new disposition; a scan result alone is not the human decision.

When retained workflow evidence is warranted, the parent opens one v2 usage
record and links already-verified child records:

```bash
usage_dir="$(agent-out project --topic skill-usage --mkdir)"
skill-usage init --out "$usage_dir" --owner-kind workflow \
  --owner-id "<parent-outcome>" --intent "<why it ran>" \
  --user-request-summary "<concise request>"
skill-usage link-record --out "$usage_dir" --type "<record-type>" \
  --path "<verified-child-record>"
skill-usage record-validation --out "$usage_dir" --command "<command>" \
  --status pass --summary "<result>"
skill-usage record-outcome --out "$usage_dir" --status pass \
  --summary "<outcome>"
skill-usage verify --out "$usage_dir" --format json
```

Use `--owner-kind intent` when no narrower outcome workflow owns the operation.
Compatibility releases without v2 owners may write one v1 parent-skill record,
but must not represent child evidence primitives as separate user outcomes.

## Product Capability Ceiling

Codex and Claude share the same runtime-kit hook decisions and nils-cli record
verification. An explicitly recognized `agent-docs` version older than the
durable-session floor keeps legacy compatibility behavior and does not claim
activation was enforced; direct preflight remains the fallback. Missing
binaries and timeout, crash, malformed-version, or required-capability failures
are not legacy signals and block supported-host repository mutations.

Hermes receives shared policy and can run the same released CLI verification,
but runtime-kit does not install an agent-docs hook runner into Hermes. A Hermes
record therefore proves explicit CLI activation/verification only, never
product-native hook invocation.
