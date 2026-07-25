# agent-docs edit gate becomes unsatisfiable after mid-session nils-cli upgrade

## Status

- Status: promoted
- First observed: 2026-07-20
- Area: agent-docs
- Severity: high

## Signal

Homebrew upgraded `nils-cli` 1.25.5 to 1.25.6 underneath a live session. Every
`agent-docs session prepare` variant for the worktree then returned
`agent-docs-bootstrap-shape-mismatch`, so `pre-edit-intent-gate` blocked all
edits in that checkout. `sync-runtime-surfaces --apply` refreshed the on-disk
surfaces but could not re-align the in-session bootstrap; only a session restart
recovered, which cost an in-flight sprint a handoff document.

## Evidence

- Raw record: `evidence/task-1.2-handoff.md`
- Summary: redacted evidence ingested at creation time; raw logs and secrets were stripped before commit.
- Root cause, located in `core/hooks/shared/pre-edit-intent-gate.py`:
  `trusted_agent_docs_executable` admits *any* `Cellar/nils-cli/*/bin` sibling as
  governed, but `bootstrap_activation_intents` and
  `recoverable_prepare_parameters` compared the command against
  `activation_base_args`, whose first element is the exact current
  `os.path.realpath` of `agent-docs`. A Homebrew install version-pins that path,
  so an upgrade repointed the stable `bin/agent-docs` symlink and every replayed
  prepare command named a superseded — still trusted — path. The trust predicate
  and the bootstrap parser disagreed about the same binary.
- The block message enumerated every compared field *except* the executable, the
  one that actually mismatched, which is why the blocked session read the gate as
  unsatisfiable and tried `--phase` variants instead.

## Impact

A mid-session release upgrade could strand a live session with no in-place
recovery: the edit gate stayed unsatisfiable in the affected checkout until the
session restarted. Because the release manager (Homebrew) can upgrade at any
time, any long-running session was exposed.

## Current Workaround

No longer required. Before the fix, the recoverable path was to re-run the
canonical no-phase `session prepare` cue *regenerated in the current turn* (so it
carried the new Cellar path) rather than replaying an earlier command, or to
restart the session rooted at the affected checkout.

## Promotion Criteria

Met. `same_governed_release` now accepts a superseded release sibling that shares
the active release's package root and canonicalizes the admitted command onto the
release installed now, so the hook always probes the current binary. Every
argument after `argv[0]` is still matched exactly, and a different package root
or a repository-local shadow is still never a bootstrap. Covered by
`test_pre_edit_bootstrap_admits_prepare_from_superseded_release_path`, written
red first. Validated with `bash tests/hooks/run.sh` (336 tests) and
`bash scripts/ci/all.sh` (positions 1-17 OK).

## Next Action

None. Fixed in local `main` commit `d0eb97f2` (`fix(hooks): keep the trusted
bootstrap valid across a CLI upgrade`), delivered by authorized
`semantic-commit local-default`; provider reconciliation is still pending because
GitHub PR delivery was unavailable at the time.

## Archive

- Archived: 2026-07-25
- Reason: Completed entry archived out of the active error inbox.
