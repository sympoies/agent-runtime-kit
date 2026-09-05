# Observed divergences between the documented local loop and the authoritative gate

Both entries are transcript-verified from the 2026-09-05 delivery session, not reconstructed.

## 1. nils-cli — `--local-fast` does not run the completion-freshness audit

Change: appended `Required for --profile provider-review and --profile pr-comment.` to four clap
flag doc comments in `crates/agent-workflow-primitives/src/review_specialists.rs`.

Local, as documented by `AGENTS.md` ("Default local development and pre-PR check"):

    bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast
    -> exit=0
       Summary 262 tests run: 262 passed, 0 skipped
       Summary 1415 tests run: 1415 passed, 0 skipped
       ok: local-fast package checks passed (2 package(s))

CI on the same tree:

    test        :: failure
    test_macos  :: failure

Reproduced locally only after running the FULL entrypoint:

    NILS_CLI_TEST_RUNNER=nextest bash scripts/ci/nils-cli-checks-entrypoint.sh
    -> FAIL: review-specialists: stale zsh completion asset: completions/zsh/_review-specialists
       FAIL: completion freshness audit (required=49, snapshots_checked=66, failures=1)

Repair: regenerate `completions/{zsh/_review-specialists,bash/review-specialists}` from the built
binary and syntax-check with `zsh -n` / `bash -n`. Full entrypoint then passed:
`ok: all nils-cli checks passed`.

Note the guidance conflict: the same `AGENTS.md` says to run the full parity checks "only when
debugging CI, preparing release-quality verification, or explicitly asked" — i.e. after the failure
has already happened.

## 2. agent-runtime-kit — `ci/all.sh` positions 8+ require a committed tree

`runtime-smoke --mode convergence`, invoked from position 8 via
`validate-surfaces-manifest`, refuses to run against a dirty checkout:

    runtime-smoke: mode=convergence total=0 pass=0 fail=0
    runtime-smoke: portable source must be clean; commit or stash reviewed changes
    validate-surfaces-manifest: runtime-state.codex.acceptance[0]: command
      "bash tests/runtime-smoke/run.sh --mode convergence" exited 1, expected 0

Observed on three separate first runs in one session (PR #96, #101 twice). Each time the resolution
was to commit and re-run, after which all 17 positions passed. The failure text names tree state
rather than the change, so it is distinguishable on a careful read — but it is the same red signal
shape as a genuine failure.

## Why these are one case

In both, the check is correct and the loop is the problem: the fast/edit-cycle command does not
cover what the authoritative gate covers, and nothing in its output says so. The first produces a
false green, the second a false red. The false green is the expensive one, because it gets
reported.
