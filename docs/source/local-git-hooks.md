# Local Git Hooks

Date: 2026-05-21
Status: retained record

## Purpose

This repository uses `lefthook.yml` as the tracked local Git hook entrypoint.
The hook setup is intentionally small:

- `pre-commit` catches fast mechanical issues on staged files.
- `pre-push` runs the current full repository gate, `bash scripts/ci/all.sh`.
- CI remains the authoritative enforcement point because local Git hooks can be
  bypassed with `--no-verify` or left uninstalled.

## Install

Install the local hook runner and the small tools used by `pre-commit`:

```bash
brew install lefthook shellcheck yamllint jq
```

The formatter is qualified separately: the hook supports **shfmt 3.14.1**.
Download the matching OS/architecture asset from the
[official v3.14.1 release](https://github.com/mvdan/sh/releases/tag/v3.14.1),
verify its published SHA-256 asset digest, and place that binary on `PATH`.
`shfmt --version` must print `v3.14.1`. The hook rejects missing or different
versions before formatting and names the required version and acquisition URL.

Install hooks into this clone:

```bash
lefthook install
```

## What Runs

`pre-commit` runs:

```text
git diff --check --cached
shellcheck <staged *.sh files>
bash scripts/ci/check-shfmt.sh <staged *.sh files>
yamllint <staged *.yml/*.yaml files>
jq empty <staged *.json files>
```

The YAML hook disables style rules that do not match this repository's existing
fixtures (`document-start`, `line-length`, and `truthy`). It is used as a syntax
and low-cost sanity check, not as a formatting policy.

The formatter wrapper records the actual version and keeps the existing
`shfmt -i 2 -ci -d` options and failure status. Version qualification is exact
because 3.8.0 and 3.14.1 disagree on the Python heredoc layout in
`tests/runtime-smoke/cases/pr/run.sh`. Run the same wrapper for manual checks;
it never rewrites files. The canonical gate runs its version/argument/failure
regressions through `tests/ci/test_shfmt_qualification.py`.

`pre-push` runs:

```bash
bash scripts/ci/all.sh
```

`lefthook.yml` marks this invocation with
`AGENT_RUNTIME_KIT_HOOK_PHASE=pre-push`. When that marked run is executing from
a linked git worktree, `scripts/ci/all.sh` keeps all normal source/rendered
drift failures strict but allows `agent-runtime audit-drift` `extra/warn`
findings from live install roots. This avoids blocking skill-removal branches
whose source tree is correct while the user's live Codex / Claude homes still
point at the primary checkout until the removal merges. Direct local runs and
GitHub Actions CI do not set the hook marker and remain fully strict.

The `pre-push` entry uses `README.md` as a stable file sentinel in
`lefthook.yml` so Lefthook does not skip the full gate when the hook is run
manually without a real push file list.

## Manual Runs

Run the lightweight hook manually:

```bash
lefthook run pre-commit
```

Run the full gate manually:

```bash
lefthook run pre-push
```

For CI parity without Git hook plumbing, run the script directly:

```bash
bash scripts/ci/all.sh
```

## Design Notes

Do not put the full gate stack in `pre-commit`. Render, golden, and drift-audit
checks are valuable but too heavy for every local commit. Keeping `pre-commit`
fast makes it more likely to stay enabled, while `pre-push` and CI keep the
complete validation boundary.

Do not add Node-only hook tooling such as Husky unless the repository later
adopts a Node toolchain for other reasons.
