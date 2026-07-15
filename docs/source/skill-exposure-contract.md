# Skill Exposure Contract

## Purpose

`manifests/skills.yaml` describes active, renderable skills. A skill is admitted
to normal product discovery only when it represents a distinct outcome a user
might request directly. Natural-language collaboration remains the default
interface; skills are routing and workflow aids, not a menu of every internal
agent operation.

Agent bookkeeping, deterministic records, policy judgment, hooks, intent docs,
and one-command CLI primitives do not become user-facing skills merely because
an agent needs their instructions. Issue
[#562](https://github.com/graysurf/agent-runtime-kit/issues/562) records the
catalog-wide migration of those capabilities to the correct layer.

## Invocation Roles

Every retained, non-pending skill declares one role:

| Role | Admission meaning |
| --- | --- |
| `workflow` | A distinct user-requested outcome with meaningful orchestration. |
| `maintenance` | A direct repository or runtime maintenance outcome a user may intentionally request. |
| `advanced` | A real but non-default user outcome. It cannot be retained until products implement an honest opt-in exposure path. |
| `compatibility` | A time-bounded alias or migration entrypoint with a canonical replacement and retirement date. |

Retained entries also declare parent `intents`, one realistic
`example_request`, and an `admission_rationale`. Missing metadata fails
governance; descriptive wording does not override the user-outcome rule.

## Exposure

Invocation role and product exposure are separate facts. Schema v2 currently
allows only:

```yaml
exposure:
  profile: default
```

This means the skill is installed and discoverable in each declared product.
There is no cross-product hidden/internal profile and no metadata-only opt-in
profile. `advanced` plus `default`, `internal`, and `opt-in` therefore fail
closed until an actual installer and discovery mechanism exists for every
supported product.

A `compatibility` entry additionally requires:

```yaml
exposure:
  profile: default
  replacement: domain.canonical-skill
  retire_after: "YYYY-MM-DD"
```

Governance verifies that the replacement is another reviewed, non-pending
active skill and that the retirement condition is bounded.

## Completed Disposition

The schema-v2 baseline contains exactly 66 immutable disposition rows. #562
reviewed every row: 26 distinct user outcomes remain active and renderable,
40 agent-only entrypoints are retired from source and product discovery, and
`migration.pending_disposition` is empty.

Pending was migration debt, never an exposure class. Governance still pins the
ordered baseline's SHA-256 digest so no original ID can be removed, replaced,
or reintroduced as a new pending row. New skills must pass normal admission
immediately.

Every row is `status: reviewed` and records the user outcome, destination
layer, parent intents, migration path, cleanup need, current CLI/hook
dependencies, enforcement point, compatibility need, and rationale. The shared
destination vocabulary is:

- `entrypoint`
- `policy`
- `intent-doc`
- `hook-gate`
- `cli-only`
- `internal-workflow`
- `merge`
- `remove`
- `compatibility`

Rows remain in the ledger after active removal so migration and live cleanup
history cannot be silently replaced. Retired IDs may appear in this immutable
ledger, the migration-progress fixture, explicit negative tests, and historical
plan records; active manifests, policy routing, source skills, and product
surfaces must not expose them as callable skills.

## Lifecycle And Validation

- `meta.create-skill` requires v2 admission metadata and never adds a pending
  row.
- `meta.remove-skill` retains reviewed disposition history for baseline IDs.
- `scripts/ci/skill-governance-audit.sh` cross-checks active skills, the pending
  set, and the disposition ledger, including negative fixtures.
- `agent-runtime list-skills --format json` reports invocation, exposure, and
  pending state against the actual Codex, Claude, and Hermes install layouts.
- Render, install, drift, stale-prune, runtime-smoke, and hook gates require the
  current admitted active set, zero pending rows, retained 66-row migration
  history, and negative cleanup of retired product surfaces. The frozen
  migration retained 26 outcomes; newly admitted skills do not alter its
  disposition ledger.
