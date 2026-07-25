# Docs Placement And Retention Policy V1

## Purpose

This policy defines where documentation belongs in `agent-runtime-kit`, how long
it should be retained, and what contributors should read before adding or
changing Markdown files.

Read this policy when adding, promoting, moving, indexing, or cleaning durable
documentation, or when placement/retention is unclear. It is optional canonical
`project-dev` context in `AGENT_DOCS.toml`; ordinary edits to an existing
document do not force-load it. Inspect or audit it directly with:

```bash
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  preflight --intent project-dev --strict --format json
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  audit --target project --strict
```

## Placement Rules

Use the narrowest owner that can maintain the document.

| Location | Use for | Retention |
| --- | --- | --- |
| `README.md` | Short repository orientation and stable entrypoints | Canonical |
| `DEVELOPMENT.md` | Current setup, edit preflight, validation, and release boundaries | Canonical |
| `docs/source/` | Repository-wide, cross-cutting architecture, specs, source-of-truth references, and policies — not a single domain's feature definition (those live with the owning domain; see the `core/skills/<domain>/<shared-spec>/` row) | Canonical until superseded |
| `docs/plans/<YYYY-MM-DD>-<slug>/` | L2 plan bundles that will be executed and archived: discussion/review source, plan, and execution state. New bundles use the date prefix; pre-v1 `docs/plans/<slug>/` folders remain valid (see Naming) | Coordination; `plan-archive` retires after execution unless promoted |
| `docs/discussions/<YYYY-MM-DD>-<slug>.md` | Captured discussion / implementation-readiness specs that are not (yet) an executed-and-archived plan bundle — the `discussion-to-implementation-doc` default | Coordination; cleanup-eligible after the described work ships or is abandoned; promote to canon if authoritative |
| `core/docs/` | Product-independent schemas, ADRs, contributor guides, and policy explainers used by runtime source | Canonical source content |
| `core/policies/` | Portable agent/runtime policy consumed by product adapters | Canonical source content |
| `core/skills/<domain>/<skill>/` | Skill-owned docs, examples, references, assets, and local helper notes | Domain-local |
| `core/skills/<domain>/<shared-spec>/` | A spec or rule set referenced by several skills in one domain but owned by no single skill — a non-skill folder (no `SKILL.md`), so skill discovery and render ignore it. Example: `core/skills/dispatch/plan-issue-spec/` | Domain-local |
| `targets/<product>/` | Product adapter docs, templates, link maps, and activation notes | Product-local |
| `manifests/` | Machine-checkable runtime inventory; narrative belongs in adjacent source docs | Canonical data |
| `tests/**` | Fixture-local documentation required to understand or validate a test fixture | Test-local |

Do not add a new root-level Markdown file unless it is a recognized entrypoint
loaded by tools or humans at the repository root. Prefer `docs/source/` for
repo-wide durable material and the owning folder for domain-local material.

## Ownership Classes

- `repo-wide`: Material that explains cross-domain architecture, repository
  policy, runtime roots, validation, release boundaries, or source inventory.
- `domain-local`: Material owned by one skill, hook area, script area, target
  adapter, manifest family, or test fixture.
- `coordination`: Temporary planning, execution, handoff, or status material.
- `retained-record`: Evidence, audit, or curated history that remains useful
  after execution and should not be treated as stale coordination material.

## Lifecycle Classes

- `canonical`: Current source of truth. Keep it updated when behavior changes.
- `coordination`: Useful while planning or execution is active. Revisit after
  completion.
- `promoted`: Former coordination material rewritten into a maintained canonical
  document.
- `retained-record`: Preserved for audit, evidence, or historical context.
- `rehome`: Move to a narrower owner when a clearer owner exists.
- `delete`: Remove after reference checks when the material is stale and not a
  retained record.

Historical cleanup should be a separate change from policy landing or feature
work unless the user explicitly asks for a cleanup pass.

## Naming

- New topic Markdown under `docs/**` should use lowercase kebab-case.
- Plan bundle folders created after this policy lands use
  `docs/plans/<YYYY-MM-DD>-<slug>/`, where `<YYYY-MM-DD>` is the UTC
  date the folder was first created in this repository and `<slug>`
  is the kebab-case plan slug (three to six words). The date prefix
  gives chronological ordering at a glance and matches the archive
  path used by the plan-archive workflow, so migration never has to
  rename or recompute the date.
- All pre-existing plan bundle folders were normalized to the
  `<YYYY-MM-DD>-<slug>/` form on 2026-05-27, using the UTC date each
  folder was first created in this repository. No slug-only
  `docs/plans/<slug>/` bundles remain; intra-repo references point at
  the dated paths.
- Plan bundle files should use the plan slug prefix when possible:
  `<slug>-discussion-source.md`, `<slug>-plan.md`, and
  `<slug>-execution-state.md`. The file slug stays unchanged when the
  enclosing folder adopts a date prefix.
- Discussion captures use `docs/discussions/<YYYY-MM-DD>-<slug>.md` — a single
  dated file (no bundle, and no `-discussion-source` suffix, since there are no
  plan siblings). The date prefix gives the same chronological ordering as plan
  bundles. These files are not scanned by `plan-tooling` / `plan-archive`.
- Root entrypoints may keep established uppercase names such as `README.md` and
  `DEVELOPMENT.md`.
- Generated or fixture files may follow the naming required by the renderer,
  product, or test scenario.

## Agent-Docs Reminder

`agent-docs` declares this policy as optional `project-dev` context. Load it
before choosing a new docs path, promotion, index entry, or retention action;
do not add it to every edit's required context.

If the correct placement is unclear, document the assumption in the change
summary rather than adding another top-level document.
