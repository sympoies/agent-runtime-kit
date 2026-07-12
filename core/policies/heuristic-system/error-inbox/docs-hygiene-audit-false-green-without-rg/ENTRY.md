# docs-hygiene-audit false-greens when rg is absent (`rg ... || true` swallows a missing command)

## Status

- Status: open
- First observed: 2026-07-08
- Area: ci; nils-cli docs-hygiene audit + --docs-only validation lanes
- Severity: medium

## Signal

`scripts/ci/docs-hygiene-audit.sh` runs every keyword / reintroduction
guardrail through `rg ... || true` (e.g. the `\blegacy\b` scans at
`docs-hygiene-audit.sh:161` and `:171`, plus the removed-surface probes at
`:180,190,200,210`). The `|| true` exists so a legitimate no-match (ripgrep
exit 1) does not fail the audit — but it also swallows a **missing-command**
exit (127). When `rg` is not installed, every scan captures an empty string and
the audit prints `PASS: docs hygiene audit` while enforcing nothing.

The audit's callers do not backstop this:

- `scripts/ci/nils-cli-local-fast.sh` requires only `git` + `python3`.
- `project-verify-required-checks.sh` preflights `rg` only for the full
  (non-docs-only) run (`:79-82`); its `--docs-only` lane requires just
  `git` + `npx`, yet still invokes `docs-hygiene-audit.sh`.

So on a machine without `rg`, both the local-fast docs-only lane and the
`entrypoint --docs-only` lane can report a green docs-hygiene while silently
skipping the banned-keyword and removed-surface guardrails.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-08).
- Surfaced by a Codex review on `sympoies/nils-cli#1058`
  (discussion r3541536059) while closing the docs-hygiene-on-Rust-only-diffs
  gap (#1053). Verified against `docs-hygiene-audit.sh` (`rg ... || true`) and
  the caller preflights above.
- #1058 fixed only the newly-introduced local-fast **code-only** branch by
  adding `require_cmd rg` before the standalone `docs-hygiene-audit.sh` call;
  it did not harden the audit script itself or the `--docs-only` battery lanes.

## Impact

A false-green docs-hygiene audit hides reintroduced banned keywords (`legacy`)
and removed CLI/redirect/alias/websocket/image-op surfaces. GitHub CI currently
installs ripgrep, so CI is not affected today, but the audit script is not
self-protecting and the local `--docs-only` lanes can pass while checking
nothing — the same false-green class that #1053 fixed for Rust-only diffs, one
layer down.

## Current Workaround

Ensure `rg` (ripgrep) is installed before relying on any docs-hygiene result.
For the local-fast **code-only** path this is now enforced by #1058
(`require_cmd rg`).

## Promotion Criteria

Promote when `docs-hygiene-audit.sh` preflights `rg` (hard-fails with a clear
error if absent, rather than `rg ... || true` swallowing a missing binary), so
the audit cannot report PASS without actually running its scans — and/or the
`--docs-only` validation lanes preflight `rg` before invoking the audit. Link
the change here.

## Next Action

File a nils-cli issue proposing `docs-hygiene-audit.sh` require `rg` up front
(replace the blanket `rg ... || true` with a preflight plus explicit no-match
handling) and extend the `--docs-only` lanes' tool preflight to include `rg`.

Lifecycle link: `https://github.com/sympoies/nils-cli/issues/1130`
