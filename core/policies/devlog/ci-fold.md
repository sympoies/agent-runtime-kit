# Devlog CI fold recipe

## Shared switch and launch environment

The maintainer owns one setting, `AGENT_RUNTIME_DEVLOG_FRAGMENTS`, in the managed
launch environment. Unset or `0` is off; `1` selects fragments. The kit renders
that setting into the portable `DEVLOG_LAYOUT` environment before a harness or
session launcher runs:

```bash
bash "$AGENT_KIT_SRC/scripts/render-runtime-env.sh" > "$AGENT_HOME/runtime.env"
# Source this at shell/service startup, including non-interactive shells.
. "$AGENT_HOME/runtime.env"
# Or apply the exact same render at the launch boundary:
bash "$AGENT_KIT_SRC/scripts/with-runtime-env.sh" agent-session start --agent codex
```

Use the same wrapper for Claude, Hermes, and direct harness launches. Environment
inheritance covers child tools and managed sessions. Regenerate the shared
snippet and restart launch services/sessions when the setting changes; an
existing process cannot receive a new parent environment. Do not set a layout
in individual repositories or change provider-owned configuration files.

For GitHub Actions, provision the same setting as an organization variable
named `AGENT_RUNTIME_DEVLOG_FRAGMENTS` for managed repositories. Repository
variables must not override it; an explicitly isolated acceptance repository
may override it while testing. A deployment owner must reconcile host/service
and organization values before enablement. This PR does not set either value.
The off render is `:` and leaves inherited environment unchanged; the fold job
is skipped before checkout or token minting. Existing month writing and delivery
remain active while off, including compatibility with older supported tools.

## Scheduled caller

`.github/workflows/devlog-fold.yml` is the reusable kit workflow. Pin its reference
to a reviewed immutable kit commit. The job resolves the actual called workflow
revision from GitHub's authenticated OIDC `job_workflow_sha` claim and checks out
that exact source; callers cannot select a different executable kit revision. In a repository with an
indexed log, add this default-branch caller (replace `KIT_COMMIT` with that SHA):

```yaml
name: Scheduled devlog fold
on:
  schedule:
    - cron: '17 3 * * *'
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
jobs:
  fold:
    uses: sympoies/agent-runtime-kit/.github/workflows/devlog-fold.yml@KIT_COMMIT
    with:
      log-dir: docs/devlog  # docs/source/devlog for a source/render split
    secrets:
      BOT_APP_ID: ${{ secrets.BOT_APP_ID }}
      BOT_APP_PRIVATE_KEY: ${{ secrets.BOT_APP_PRIVATE_KEY }}
```

Provision a repository-scoped installation of the approved GitHub App with
Contents: write and Metadata: read. The token action explicitly requests only
Contents: write for this repository and fails if that permission is unavailable.
Do not print tokens or store credential material in source or artifacts.

The fold runs released nils-cli 1.31.14 from its checksum-pinned Linux archive,
independently of the kit's unchanged compatibility and packaging pins. The trusted
Python fold owner changes only the indexed log, uses `devlog fold` plus ordinary
`devlog check`, and makes no commit on an empty fold. It creates tree/commit
objects via GitHub's Git database API without custom author, committer, or
signature fields, then requires `verification.verified=true` before a
non-force ref update. GitHub documents this
[bot signature contract](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)
and [fast-forward ref update](https://docs.github.com/en/rest/git/refs).
Private-repository fetches receive the repository-scoped token through a
non-persistent Git configuration environment; credential values never enter
Git argv or repository config. Downloaded `devlog` subprocesses receive no
provider credentials. A rejection retries only when the default tip changed: refetch, check out the
fresh parent in the disposable CI checkout, rerun fold, and publish again, up to
three attempts. Permission/protection failures on an unchanged tip stop.

Keep required PRs, required checks, and required signatures on the default branch.
The maintainer provisions the App as the only narrowly scoped bypass actor for
the fold exception in `git-delivery.md`; the job still requires provider-verified
commits. Other actors retain every protection. The job has one concurrency
owner per repository and never force-updates a ref. Do not run this script in
a developer checkout or with untrusted PR code and an App token.

## Fragment-aware PR validation

Replace month-only shell or Markdown parsing with `devlog check`. Fetch enough
history to resolve the default baseline; for example use full checkout history
and pass the branch through an environment variable rather than shell text:

```bash
git fetch --no-tags origin "refs/heads/$DEFAULT_BRANCH:refs/remotes/origin/$DEFAULT_BRANCH"
DEVLOG_CHECK_BASE="origin/$DEFAULT_BRANCH" bash "$AGENT_KIT_SRC/scripts/ci/devlog-check.sh"
```

The kit check entrypoint does nothing without a recognized log index and delegates
all log validation to the released tool. Both directory conventions work.
`check --base` currently enforces merged-fragment immutability, not the ban on
month edits in PRs. Adopt the tool-owned fragment-only mode after
[nils-cli #2082](https://github.com/sympoies/nils-cli/issues/2082) is released;
that dependency blocks production enablement. Do not implement a competing
kit-side check or claim that ordinary `check` already enforces this policy.

## Acceptance before enablement

Run the pinned agent-sandbox devlog scenario against the candidate kit render
and check wiring. It must retain both merge orders, a no-op without a commit,
normal deterministic folding, a rejected update with refetch/retry, and immutable
merged fragments. Record its result and exact candidate revision in the kit PR;
a scenario change needs its own small sandbox PR.

Provider acceptance is separate and must run the actual reusable workflow in an
approved public test repository. Record both entry-PR merge orders, a no-op run,
a normal fold, a real stale-parent rejection and rerun, the exact protected
ruleset, App permission evidence, and each resulting commit's provider verification.
Offline Git results and fake transport tests do not prove these conditions.
The maintainer approves repository creation and protection changes. Keep the
fixture for independent verification; do not delete it as cleanup.
