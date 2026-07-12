---
name: test-first-evidence
description: >
  Govern testable change as a durable contract/test lifecycle — contract
  delta, affected-test decisions, meaningful red, scoped validation, and
  residual gaps — using released test-first-evidence v2 for forge delivery.
---

# Test-First Evidence

## Contract

Use this skill for testable production behavior changes even when the delivery
gate is disabled. The skill owns engineering judgment; the released CLI owns
deterministic record structure and objective completeness checks.

Prereqs:

- `test-first-evidence` from the repository-pinned nils-cli release is on
  `PATH`.
- The evidence directory is explicit and allocated through `agent-out`.
- Production behavior has not been edited. Tests and fixtures may be changed
  first to express the intended contract.

Inputs:

- The production change, retained invariants, changed/removed/added behavior,
  affected test surfaces, done criteria, risk, and project validation contract.
- Before-fix failure evidence or a justified waiver.

Outputs:

- A deterministic `test-first-evidence.record.v2` contract/test-impact ledger.
- Verified evidence suitable for `forge-cli --test-first-evidence <dir>`.
- An explicit account of final validation and residual gaps.

Failure modes:

- Production behavior changes before meaningful red or a complete waiver.
- Existing tests are weakened, deleted, or duplicated without an explicit
  disposition and invariant rationale.
- Compilation, setup, environment, fixture, or unrelated failures are claimed
  as red evidence.
- Retry-only green, an unowned quarantine, broad snapshots, or coverage count
  are treated as proof of behavior.
- Required validation scopes or residual-gap declarations are missing.

## Durable lifecycle

1. **Classify the production change.** Treat bugs, features, parsers, state
   machines, APIs, workflows, and user-visible behavior as testable by default.
   Use a waiver only for genuinely non-testable work or explicit deferred debt.
2. **Contract delta.** Declare retained behavior and invariants, behavior being
   changed or removed, and behavior being added. Do not infer a new contract
   only from the implementation diff.
3. **Impact scan.** Inspect materially affected existing tests, fixtures,
   snapshots, mocks, contract consumers, and higher-level journeys before
   choosing what to add. Group a parameter family, fixture family, snapshot
   group, suite, or journey when it shares one decision and rationale; do not
   create ceremony per individual case.
4. **Disposition every affected target.** Use:
   - `keep` when the target already protects a retained invariant unchanged;
   - `update-spec` when a valuable old-spec test should express the intentional
     new contract. Change its expectation first and use that expected failure
     as red; this is specification migration, not weakening;
   - `remove-superseded` only when the protected behavior is retired or a named
     owner test preserves every still-valid invariant. Deletion alone is not
     red evidence;
   - `add-missing` when no current target owns a distinct behavior or risk;
   - `refactor-only` when structure changes without changing the assertion.
5. **Choose the primary owner.** Put the contract at the lowest stable
   behavioral boundary that proves it directly. Unit/property, integration,
   contract, and E2E tests are all valid; do not force unit-first when a shared
   boundary or user journey is the durable owner.
6. **Meaningful red.** Run the focused owner before production edits. Record
   the command/scenario, non-zero result, test identity, expected failure, and
   observed failure. They must agree at engineering-review level; compilation,
   setup, environment, fixture, and unrelated failures do not qualify.
7. **Implement narrowly.** Make the smallest production change that satisfies
   the declared contract while preserving retained invariants. Do not overfit
   assertions to private implementation details.
8. **Add only distinct-risk coverage.** Prefer table-driven, parameterized, or
   property-based coverage for input spaces. Add another example only for a
   distinct partition, boundary, integration, or failure mode—not to increase
   case count or a percentage.
9. **Converge the suite.** Remove redundant ownership and keep assertions on
   observable outcomes/invariants. Private call order, broad snapshots, hidden
   state, excessive mocks, and real time/random/network dependencies are
   presumed brittle and need an explicit reason. Fixtures must be isolated,
   deterministic, and cleaned up.
10. **Validate by risk.** Re-run the focused owner, the materially affected
    suite, and shared contract consumers. Add full/manual validation only when
    blast radius requires it. Record each scope and declare residual gaps
    explicitly.

Coverage is a diagnostic signal for finding unexercised risk. It is not an
objective by itself, and never justifies a duplicate case. Targeted mutation
testing can strengthen critical decision logic, but is not a universal gate.

Flaky tests are defects. A retry does not turn a failure into evidence. A
quarantine is allowed only as deferred debt with an owner/follow-up,
expiry/removal condition, and substitute validation; otherwise fix the
determinism problem before delivery.

## Waivers

- `non-testable`: explain why meaningful red cannot exist and record substitute
  validation.
- `deferred-debt`: additionally record a durable follow-up and expiry/removal
  condition. Use this for time-bounded harness or flake debt, not convenience.

A waiver does not erase contract-delta, affected-test, final-validation, or
residual-gap decisions required by the record.

## Entrypoint

Use the released CLI directly. The following is a representative testable
change; adapt the behavior, targets, and validation scopes to the actual risk:

```bash
test-first-evidence init --out "$EVIDENCE_DIR" \
  --classification behavior-change \
  --production-path src/lib.rs \
  --retained-behavior "existing callers keep their result" \
  --changed-behavior "invalid input returns a typed error" \
  --invariant "valid input behavior is unchanged"

test-first-evidence record-impact --out "$EVIDENCE_DIR" \
  --target "tests::invalid_input" \
  --disposition update-spec \
  --protected-behavior "invalid-input contract" \
  --reason "the old expectation represents the intentionally replaced spec" \
  --validation-scope focused \
  --validation-scope affected-suite

test-first-evidence record-failing --out "$EVIDENCE_DIR" \
  --command "cargo test invalid_input" \
  --exit-code 101 \
  --test-name "tests::invalid_input" \
  --expected-failure "expected typed error, received old fallback" \
  --observed-failure "assertion shows old fallback" \
  --summary "new contract fails before production edit"

test-first-evidence check --out "$EVIDENCE_DIR" --phase pre-edit \
  --project-path . --path src/lib.rs --format json

# Edit production behavior only after the pre-edit check.

test-first-evidence record-final --out "$EVIDENCE_DIR" \
  --command "cargo test invalid_input" --status pass --scope focused
test-first-evidence record-final --out "$EVIDENCE_DIR" \
  --command "cargo test affected_module" --status pass --scope affected-suite
test-first-evidence record-gap --out "$EVIDENCE_DIR" --none
test-first-evidence verify --out "$EVIDENCE_DIR" --format json
```

Repeated failing and final-validation records append deterministically. A later
validation attempt for the same command/scope supersedes the earlier attempt
for effective status without deleting history; every other latest failure still
blocks verification.

## Delivery gate

When `[test_first].require` resolves true, `forge-cli pr create` and `pr
deliver` require `--test-first-evidence <dir>` for feature/bug records across
create, adopt, dry-run, and deliver paths. The gate remains opt-in; docs,
chore, CI, and refactor kinds remain exempt.

The directory must contain a strict-verification-clean v2 record with a
testable classification, actual contract delta, affected-test decision,
meaningful-red fields or a complete waiver, scoped passing validation, and a
residual-gap declaration. Record v1 remains readable with `show`, but feature
or bug delivery requires deliberate v2 re-recording because missing maintenance
facts cannot be inferred safely.

## Boundary

The CLI can reject missing/unknown fields, unsafe removal/deferred-waiver
shapes, duplicate identities, unresolved latest failures, and v1 delivery. It
cannot decide whether expected and observed red agree semantically, whether a
test is at the right boundary, or whether cases are redundant. Those remain
engineering and testing-review judgments defined here.

## Labels

- Follow the active repository's label catalog and
  `core/policies/forge-label-taxonomy.md` when provider delivery is in scope.
