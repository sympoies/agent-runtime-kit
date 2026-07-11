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
[#562](https://github.com/graysurf/agent-runtime-kit/issues/562) owns the
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

## Pending Disposition

The 66 skills present when schema v2 was introduced remain active and visible
while #562 reviews them. They are listed under
`migration.pending_disposition` and mirrored one-for-one as `status: pending`
rows in `manifests/skill-dispositions.yaml`.

Pending is migration debt, not an exposure class. Pending skills carry no
invented invocation or exposure metadata, and diagnostics report
`pending_disposition: true`. The baseline contains exactly 66 durable rows and
cannot grow or replace an original ID: governance pins the ordered baseline's
SHA-256 digest. New skills must pass normal admission immediately.

When #562 reviews a row, it becomes `status: reviewed` and records the user
outcome, destination layer, parent intents, migration path, cleanup need, and
current CLI/hook dependencies, enforcement point, compatibility need, and
rationale. The shared destination vocabulary is:

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
history cannot be silently replaced by a new pending ID.

## Lifecycle And Validation

- `meta.create-skill` requires v2 admission metadata and never adds a pending
  row.
- `meta.remove-skill` retains reviewed disposition history for baseline IDs.
- `scripts/ci/skill-governance-audit.sh` cross-checks active skills, the pending
  set, and the disposition ledger, including negative fixtures.
- `agent-runtime list-skills --format json` reports invocation, exposure, and
  pending state against the actual Codex, Claude, and Hermes install layouts.
- Render, install, drift, stale-prune, runtime-smoke, and hook gates continue to
  treat pending skills as active until #562 completes their replacement and
  cleanup work.
