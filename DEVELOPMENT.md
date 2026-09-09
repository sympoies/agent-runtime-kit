# Development

Contributor guide for maintaining `agent-runtime-kit`. Repository purpose,
runtime architecture, and the directory map live in [`README.md`](README.md).
Setup recipes, render commands, hook details, targeted test matrices, coupled
`nils-cli` work, and release procedures live in
[`docs/source/development-reference.md`](docs/source/development-reference.md).

## Before editing

- Read [`AGENTS.md`](AGENTS.md), the canonical repository policy.
  [`CLAUDE.md`](CLAUDE.md) imports it for Claude Code.
- Identify the source owner and every rendered, manifest, fixture, golden, and
  product-adapter surface affected by the change.
- Inspect the active edit contract and declared finish-line:

  ```bash
  agent-docs preflight --docs-home "$PWD" --intent project-dev \
    --phase edit --strict
  ```

- Read the optional documentation placement policy before adding, moving,
  promoting, indexing, or deleting durable docs.

## Maintenance principles

- This repository owns shared runtime content; `sympoies/nils-cli` owns stable
  CLI behavior, parsers, exit codes, and machine-readable contracts.
- Edit canonical source under `core/`, `targets/`, and `manifests/`; treat
  `build/` and `tests/golden/` as derived output that must agree with it.
- Keep Codex, Claude, and Hermes as adapters of one shared source. Update every
  declared product surface when a portable contract changes.
- Keep install, link, render, overlay, and drift-audit operations dry-run first.
  Never read or commit auth, sessions, logs, caches, runtime state, or secrets.
- Keep top-level shell glue compatible with macOS Bash 3.2 and Linux Bash.
  Move shared or semver-sensitive behavior into `nils-cli`.
- Use the managed skill lifecycle workflows for skill creation or removal; do
  not hand-maintain only part of the source, manifest, render, sandbox, and
  smoke-test contract.
- Do not advance a released `nils-cli` requirement from an unreleased debug
  binary. Compatibility and validated pins move only through their owning
  release workflow.

## Change workflow

1. Define the observable contract delta and list the canonical and derived
   surfaces that must remain aligned.
2. For testable behavior, capture a meaningful regression failure at the
   lowest stable owner before editing when practical. Record a concise waiver
   for documentation-only or mechanical work.
3. Make the smallest source change, then refresh only the affected generated
   output, manifests, fixtures, and current documentation.
4. Run focused checks while iterating. Review generated diffs rather than
   accepting them mechanically.
5. Run the repository-owned finish-line exactly once against the final tree:

   ```bash
   bash scripts/ci/all.sh
   ```

6. Deliver from a managed non-default worktree through `semantic-commit` and
   `forge-cli`. Release or live-runtime mutation requires its separate owner
   and explicit authority.

## Change routing

| Change | Canonical guidance |
| --- | --- |
| Host setup, runtime sync, private overlays, hooks | [`Development reference`](docs/source/development-reference.md#setup) |
| Skill creation or removal | Managed `meta:create-skill` / `meta:remove-skill` workflows and [`Skill lifecycle changes`](docs/source/development-reference.md#skill-lifecycle-changes) |
| Coupled or pinned `nils-cli` work | [`nils-cli version workflows`](docs/source/nils-cli-version-workflows.md) |
| Render and golden refresh | [`Build and render`](docs/source/development-reference.md#build-and-render) |
| Targeted validation and smoke modes | [`Validation reference`](docs/source/development-reference.md#validation) |
| Container publication | [`RELEASING.md`](RELEASING.md) |
| Documentation placement and retention | [`Docs placement policy`](docs/source/docs-placement-retention-policy-v1.md) |
| Durable outcome history | [`Development log`](docs/source/devlog/README.md) |

## Documentation ownership

- Keep `README.md` focused on repository purpose, runtime model, supported
  surfaces, and stable entrypoints.
- Keep this file focused on contributor principles, the routine workflow, and
  validation/release boundaries.
- Keep cross-cutting architecture, policies, and detailed maintenance
  references under `docs/source/`; keep domain-specific material with its
  owning skill, hook, target, script, or fixture.
- Update current documentation before appending a newest-first, public-safe
  devlog entry for a non-trivial durable outcome.

All committed repository content is written in English.
