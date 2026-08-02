#!/usr/bin/env bash
# Controlled PR delivery smoke.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIXTURE_ROOT="$REPO_ROOT/tests/runtime-smoke/workspaces/basic-repo"

SCRATCH_FORK=""
SCRATCH_BRANCH=""
ARTIFACTS_DIR=""
EXECUTE_LIVE=0

usage() {
  cat <<'USAGE'
Usage: tests/smoke/deliver-lifecycle.sh --scratch-fork <owner/repo> --scratch-branch <branch> [options]

Options:
  --scratch-fork <owner/repo>  Required scratch GitHub repository.
  --scratch-branch <branch>    Required throwaway branch name. "feat/" is added when absent.
  --artifacts-dir <path>       Artifact directory. Default: temp directory.
  --execute-live               Push and invoke forge-cli live. Default: dry-run only.
  -h, --help                   Show this help.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scratch-fork)
      SCRATCH_FORK="${2:-}"
      shift 2
      ;;
    --scratch-branch)
      SCRATCH_BRANCH="${2:-}"
      shift 2
      ;;
    --artifacts-dir)
      ARTIFACTS_DIR="${2:-}"
      shift 2
      ;;
    --execute-live)
      EXECUTE_LIVE=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "deliver-lifecycle: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$SCRATCH_FORK" ] || [ -z "$SCRATCH_BRANCH" ]; then
  echo "deliver-lifecycle: --scratch-fork and --scratch-branch are required" >&2
  usage >&2
  exit 2
fi

if [ "$SCRATCH_FORK" = "sympoies/agent-runtime-kit" ]; then
  echo "deliver-lifecycle: canonical repository is not an allowed scratch target" >&2
  exit 2
fi

case "$SCRATCH_BRANCH" in
  main | master | origin/main | origin/master)
    echo "deliver-lifecycle: scratch branch must not be main/master" >&2
    exit 2
    ;;
esac

case "$SCRATCH_BRANCH" in
  feat/* | fix/*)
    HEAD_BRANCH="$SCRATCH_BRANCH"
    ;;
  *)
    HEAD_BRANCH="feat/$SCRATCH_BRANCH"
    ;;
esac

command -v git >/dev/null 2>&1 || {
  echo "deliver-lifecycle: git is required" >&2
  exit 127
}
command -v forge-cli >/dev/null 2>&1 || {
  echo "deliver-lifecycle: forge-cli is required" >&2
  exit 127
}

if [ -z "$ARTIFACTS_DIR" ]; then
  ARTIFACTS_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agent-runtime-kit-deliver-lifecycle.XXXXXX")"
fi
WORKSPACE="$ARTIFACTS_DIR/workspace"
BODY_FILE="$ARTIFACTS_DIR/body.md"
OUT_FILE="$ARTIFACTS_DIR/forge-cli-output.json"
SUMMARY_FILE="$ARTIFACTS_DIR/summary.txt"
mkdir -p "$WORKSPACE"

if [ "$EXECUTE_LIVE" -eq 1 ]; then
  command -v gh >/dev/null 2>&1 || {
    echo "deliver-lifecycle: gh is required for live smoke" >&2
    exit 127
  }
  gh repo view "$SCRATCH_FORK" --json nameWithOwner,isArchived,defaultBranchRef \
    >"$ARTIFACTS_DIR/repo-probe.json" 2>/dev/null || {
    echo "deliver-lifecycle: scratch repository is unavailable: $SCRATCH_FORK" >&2
    exit 3
  }
fi

if [ "$EXECUTE_LIVE" -eq 1 ]; then
  git clone -q --depth=1 --branch main "git@github.com:$SCRATCH_FORK.git" "$WORKSPACE"
  git -C "$WORKSPACE" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
  git -C "$WORKSPACE" switch -c "$HEAD_BRANCH" >/dev/null
else
  git -C "$WORKSPACE" init -q
  git -C "$WORKSPACE" remote add origin "git@github.com:$SCRATCH_FORK.git"
fi

cp -R "$FIXTURE_ROOT/." "$WORKSPACE"
git -C "$WORKSPACE" config user.email runtime-smoke@example.invalid
git -C "$WORKSPACE" config user.name "Runtime Smoke"
printf 'deliver lifecycle smoke\n' >"$WORKSPACE/deliver-lifecycle.txt"
git -C "$WORKSPACE" add .
TREE="$(git -C "$WORKSPACE" write-tree)"
if [ "$EXECUTE_LIVE" -eq 1 ]; then
  COMMIT="$(printf 'deliver lifecycle smoke\n' | git -C "$WORKSPACE" commit-tree "$TREE" -p HEAD)"
else
  COMMIT="$(printf 'deliver lifecycle smoke\n' | git -C "$WORKSPACE" commit-tree "$TREE")"
fi
git -C "$WORKSPACE" update-ref "refs/heads/$HEAD_BRANCH" "$COMMIT"
git -C "$WORKSPACE" symbolic-ref HEAD "refs/heads/$HEAD_BRANCH"
if [ "$EXECUTE_LIVE" -eq 0 ]; then
  git -C "$WORKSPACE" update-ref "refs/remotes/origin/$HEAD_BRANCH" "$COMMIT"
  git -C "$WORKSPACE" branch --set-upstream-to "origin/$HEAD_BRANCH" "$HEAD_BRANCH" >/dev/null
fi

# Isolate only the forge-cli test-first gate for this smoke (#345). A repo-scoped
# `.forge-cli.toml` with `[test_first] require = false` overrides a repo or
# user-global `[test_first].require = true` (precedence: explicit flag > repo
# .forge-cli.toml > global config), so a host with the gate enabled neither fails
# the live `pr deliver` create step nor flags the dry-run preflight for a smoke
# that legitimately carries no test-first evidence. forge-cli runs from
# `cd "$WORKSPACE"`, so this workspace config wins without redirecting
# $XDG_CONFIG_HOME (which would break live `gh` auth). It is written after the
# workspace commit and git-ignored locally, so it never enters the scratch PR tree
# nor trips the `worktree_clean` preflight (untracked files count as dirty).
printf '.forge-cli.toml\n' >>"$WORKSPACE/.git/info/exclude"
cat >"$WORKSPACE/.forge-cli.toml" <<'FORGECFG'
[test_first]
require = false
FORGECFG

cat >"$BODY_FILE" <<'BODY'
## Summary

Runtime smoke validates the forge-cli PR delivery macro on a scratch target.

## Test plan

- deliver-lifecycle smoke
BODY

if [ "$EXECUTE_LIVE" -eq 1 ]; then
  (
    cd "$WORKSPACE"
    remote_oid="$(git ls-remote --heads origin "$HEAD_BRANCH" | awk '{print $1}')"
    if [ -n "$remote_oid" ]; then
      git push -u --force-with-lease="refs/heads/$HEAD_BRANCH:$remote_oid" origin "$HEAD_BRANCH"
    else
      git push -u origin "$HEAD_BRANCH"
    fi
    git fetch origin "refs/heads/$HEAD_BRANCH:refs/remotes/origin/$HEAD_BRANCH" >/dev/null
    git branch --set-upstream-to "origin/$HEAD_BRANCH" "$HEAD_BRANCH" >/dev/null
    forge-cli pr deliver \
      --provider github \
      --repo "$SCRATCH_FORK" \
      --format json \
      --kind feature \
      --base main \
      --title "Runtime delivery smoke" \
      --body-file "$BODY_FILE" \
      --method squash
  ) >"$OUT_FILE" 2>&1
else
  (
    cd "$WORKSPACE"
    forge-cli pr deliver \
      --provider github \
      --repo "$SCRATCH_FORK" \
      --dry-run \
      --format json \
      --kind feature \
      --base main \
      --title "Runtime delivery smoke" \
      --body-file "$BODY_FILE" \
      --method squash \
      --no-merge
  ) >"$OUT_FILE" 2>&1
fi

grep -q '"schema_version":"cli.forge-cli.pr.deliver.v1"' "$OUT_FILE"
grep -q '"provider":"github"' "$OUT_FILE"
grep -q '"wait_checks"' "$OUT_FILE"

# The test-first gate must not fire — proves the .forge-cli.toml gate isolation
# above held on a test-first-enabled host (#345). The greps above pass even when
# the dry-run preflight reports `test_first_evidence_required`, so assert its
# absence explicitly rather than trust a top-level "ok".
if grep -q 'test_first_evidence_required' "$OUT_FILE"; then
  echo "deliver-lifecycle: test-first gate fired; .forge-cli.toml gate isolation failed" >&2
  exit 1
fi

{
  printf 'scratch_fork=%s\n' "$SCRATCH_FORK"
  printf 'scratch_branch=%s\n' "$HEAD_BRANCH"
  printf 'execute_live=%s\n' "$EXECUTE_LIVE"
  printf 'output=%s\n' "$OUT_FILE"
} >"$SUMMARY_FILE"

printf 'deliver-lifecycle: OK artifacts=%s\n' "$ARTIFACTS_DIR"
