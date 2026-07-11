# Git, Commits, And Delivery

## Purpose

This policy holds the detailed mechanics behind agent-owned Git work and how it
reaches a provider: the commit body gate, managed worktree paths, branch
naming, label selection, and PR/MR body format.

It is declared as a `project-dev` document in `AGENT_DOCS.toml` (home scope),
so the harness surfaces it through the hook preflight when implementation work
starts. `AGENT_HOME.md` carries the always-on hard gates — use `semantic-commit`,
use `git-cli worktree`, use `forge-cli` for provider records, keep signing on,
and never force-push `main`. Those gates are also enforced mechanically by hooks,
but hooks do not replace policy: this file is the intent and the procedural
detail behind the one-line gates.

## Commits

- The `semantic-commit` body gate enforces 1-2 bullets on non-trivial commits;
  trivial commits may omit the body.
- Each body bullet must start with a dash, one following space, and an uppercase
  ASCII letter, or a two-space continuation line. A lowercase word, a
  backticked identifier, or a leading double-dash flag is rejected as the opener;
  auto-fix capitalizes a lowercase opening word but cannot rescue a flag or
  backtick start, so lead with a capitalized verb or noun there. The
  `semantic-commit --help` output carries exact flag examples and error strings.
- Draft an accurate 1-2 sentence summary grounded in the actual diff before
  committing or opening a record; never derive a title or body from
  `git log -1`.

## Worktrees

- `git-cli worktree` is the managed lifecycle surface; direct mutating
  `git worktree` is blocked by hook so paths, branch names, JSON contracts, and
  cleanup behavior stay consistent across sessions.
- Managed agent worktrees live under the runtime-kit state worktree tree
  (`${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/worktrees/<repo-key>/<branch-slug>`);
  the sibling `.../agent-runtime-kit/out/` tree stays owned by `agent-out` for
  workflow artifacts.
- `git-cli worktree remove` reclaims the working tree but intentionally leaves
  the branch ref in place; delete a merged throwaway branch explicitly, or use
  `meta:worktree-triage` to batch-clean stale worktrees and branches.

## Branches

- Branch names carry a Conventional-Commits-style prefix matching the eventual
  PR kind, since `forge-cli pr deliver/create --kind` enforces the pairing
  (`feature->feat/`, `bug->fix/`, `chore->chore/`, `docs->docs/`, `ci->ci/`,
  `refactor->refactor/`). Slugs are lowercase, hyphenated, three to six words; a
  ticket id `ABC-123` becomes `feat/abc-123-<slug>`.
- `git-cli worktree add <slug>` derives the branch from the base ref
  automatically. It defaults to `feat/<slug>`; pass
  `--kind <feature|bug|chore|docs|ci|refactor>` to select the matching prefix
  (e.g. `--kind bug` -> `fix/<slug>`) so the worktree branch already satisfies
  the `forge-cli --kind` rule at delivery — no rename step. The kind→prefix
  mapping is shared with `forge-cli` via `nils_common::git::PrKind` (nils-cli
  `>= v1.0.4`), so the two surfaces cannot drift. Manual branch creation in a
  shared checkout is rarely needed.

## Issues, PRs, And MRs

- For agent-owned provider issues, PRs, and MRs, use the active workflow or
  `forge-cli` surface instead of raw provider commands. Direct `gh pr create`
  or `glab mr create` are blocked by hook; PR/MR delivery goes through the
  active delivery skill.
- PR/MR bodies come from the active delivery skill / `agent-runtime pr-body
  render` (the canonical formatter; minimum `## Summary` + `## Test plan`). Do
  not hand-write body scaffolding or copy the formatter's section table into
  policy files.

## Parent Workflow Routing

Commit mutation and repository pre-PR validation are internal phases of the
implementation and governed PR outcome. Parent workflows stage only their owned
changes and invoke `semantic-commit`; they do not ask the user to select a commit
helper. Before provider mutation, the PR parent runs the repository-owned
`.agents/scripts/pre-pr.sh` dispatcher when present and stops on failure. Keep
the deterministic CLI and repository dispatcher directly callable for
diagnostics without exposing either as a separate delivery outcome.

## Labels

- Labels describe the record's type, area, state or size, and workflow for
  triage and automation.
- When the active project provides `manifests/forge-labels.yaml`, select labels
  from that catalog and follow `core/policies/forge-label-taxonomy.md`; current
  CLI / skill surfaces handle ensure, validation, and application details.

## Test-First Evidence Gate

- The test-first gate is enforced in the released `forge-cli` surface, not a
  client-side hook: when `[test_first].require` resolves true, `forge-cli pr
  create` / `pr deliver` require `--test-first-evidence <dir>` for `--kind
  feature` / `bug` records (both the create and adopt paths, and the
  `--dry-run` preflight). `docs` / `chore` / `ci` / `refactor` are exempt.
- The retained PR and plan parent outcomes (`deliver-pr`,
  `deliver-plan-tracking-issue`, and `deliver-dispatch-plan`) thread that flag
  through their internal create/deliver phases for `--kind feature` / `bug` and
  omit it for exempt kinds. Point it at the `verify`-clean directory produced
  by the policy-owned `test-first-evidence` CLI flow.
- The gate is **off by default**. It is opt-in via `[test_first] require =
  true` in either a repo `.forge-cli.toml` or the user-global
  `${XDG_CONFIG_HOME:-$HOME/.config}/forge-cli/config.toml`. Precedence: explicit
  flag > repo config > global config > default (off). A global opt-in turns the
  gate on for every repo without a per-repo file.
- The evidence directory must hold a record that `test-first-evidence verify`
  accepts: a failing test **or** an explicit waiver, plus a passing final
  validation. The parent workflow owns classification and waiver judgment;
  `core/policies/evidence-control-plane.md` owns routing and the CLI owns record
  mechanics.
- A waiver is the sanctioned path when a change is not testable production
  behavior (docs-only, generated-only, no usable harness, emergency hotfix); it
  still records substitute validation. Waivers are expected and legitimate — the
  gate requires a *recorded decision*, not a test on every PR.
- Failures surface as `test_first_evidence_required` / `_incomplete` /
  `_unreadable` (exit `DATA`). Pin and consumed-surface detail live in
  `docs/source/nils-cli-surface.md`; record mechanics live in the
  `test-first-evidence` CLI.
