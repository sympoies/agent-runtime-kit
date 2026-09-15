#!/usr/bin/env bash
# Deterministic probes for PR/MR skills.
# Probe functions are invoked indirectly by `record_case`, which shellcheck
# cannot see, so it reports every line inside them as unreachable (SC2317) and
# the functions themselves as uncalled (SC2329). Both are false here.
# SC2016 is likewise intended: the single-quoted strings are literal needles
# searched for in skill bodies, so expanding them would defeat the assertion.
# shellcheck disable=SC2329,SC2317,SC2016

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/rendered-contract.sh
. "$SCRIPT_DIR/lib/rendered-contract.sh"

PR_ARTIFACTS_DIR="$ARTIFACTS_DIR/pr"
PR_WORKSPACE="$TMP_ROOT/workspaces/pr-basic-repo"
LABEL_CATALOG="$REPO_ROOT/manifests/forge-labels.yaml"
mkdir -p "$PR_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$PR_WORKSPACE"

require_pr_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke pr: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

init_pushed_branch_fixture() {
  local workspace="$1"
  local branch="$2"
  local remote_url="$3"
  local base_tree base_commit tree commit

  git -C "$workspace" init -q
  git -C "$workspace" config user.email runtime-smoke@example.invalid
  git -C "$workspace" config user.name "Runtime Smoke"
  printf 'runtime-smoke pr base\n' >"$workspace/pr-base.txt"
  git -C "$workspace" add .
  base_tree="$(git -C "$workspace" write-tree)"
  base_commit="$(printf 'runtime-smoke pr base\n' | git -C "$workspace" commit-tree "$base_tree")"
  git -C "$workspace" update-ref refs/heads/main "$base_commit"
  git -C "$workspace" update-ref refs/remotes/origin/main "$base_commit"
  printf 'runtime-smoke pr fixture\n' >"$workspace/pr-fixture.txt"
  git -C "$workspace" add .
  tree="$(git -C "$workspace" write-tree)"
  commit="$(printf 'runtime-smoke fixture\n' | git -C "$workspace" commit-tree "$tree" -p "$base_commit")"
  git -C "$workspace" update-ref "refs/heads/$branch" "$commit"
  git -C "$workspace" symbolic-ref HEAD "refs/heads/$branch"
  git -C "$workspace" remote add origin "$remote_url"
  git -C "$workspace" update-ref "refs/remotes/origin/$branch" "$commit"
  git -C "$workspace" branch --set-upstream-to "origin/$branch" "$branch" >/dev/null
}

write_pr_body() {
  local path="$1"
  cat >"$path" <<'BODY'
## Summary

Runtime smoke validates the forge-cli PR create dry-run contract.

## Test plan

- forge-cli dry-run (pass)
BODY
}

write_dispatch_session_record() {
  local path="$1"
  cat >"$path" <<'BODY'
## Dispatch Lane PR

- Lane: L1
- PR: https://github.com/graysurf/agent-runtime-kit/pull/123
- Status: draft PR created
- Validation: forge-cli dry-run (pass)
BODY
}

assert_provider_payload_local_path_gate() {
  local path="$1"
  local raw_path="$2"

  grep -q '"code":"local_path_present"' "$path" || return 1
  grep -q '[$]HOME/project' "$path" || return 1
  ! grep -q "$raw_path" "$path" || return 1
}

# Every retained PR/MR outcome that directly opens a feature/bug record must thread the
# forge-cli test-first gate flag (--test-first-evidence) into its documented
# create/deliver invocation. Without it, an operator with [test_first].require =
# true (repo or user-global) hits test_first_evidence_required at the documented
# gate even with a valid record (agent-runtime-kit#341). Assert the flag is
# present in each delivery skill body.
assert_delivery_skills_thread_test_first_evidence() {
  local rc=0 skill
  for skill in \
    core/skills/pr/deliver-pr/SKILL.md.tera \
    core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera \
    core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera; do
    if ! grep -q -- '--test-first-evidence' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits --test-first-evidence gate threading" >&2
      rc=1
    fi
  done
  return "$rc"
}

assert_delivery_skills_own_terminal_worktree_cleanup() {
  local rc=0 skill
  for skill in \
    core/skills/pr/deliver-pr/SKILL.md.tera \
    core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera \
    core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera; do
    if ! grep -q 'core/policies/git-delivery.md' "$REPO_ROOT/$skill" ||
      ! grep -q 'git-cli worktree remove <path-or-slug> --format json' "$REPO_ROOT/$skill" ||
      ! grep -q 'provider-confirmed delivered head' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits safe terminal worktree cleanup" >&2
      rc=1
    fi
    if ! grep -Eqi 'retain|do not force|never force' "$REPO_ROOT/$skill" ||
      ! grep -Eqi 'dirty|unsafe|ambiguous|unverifiable' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits unsafe-state retention" >&2
      rc=1
    fi
  done
  return "$rc"
}

# Native-review timing and provider gate mechanics belong to released
# forge-cli. Active delivery parents still own the semantic read/disposition
# loop, but must not duplicate polling recipes or unconditional provider
# sweeps. Keep all three merge-owning outcomes on the same minimum surface and
# typed retry contract.
assert_delivery_skills_use_native_review_convergence() {
  local rc=0 skill gitlab_reviews_output gitlab_reviews_status
  local hyphen_comment_output hyphen_delete_output
  local capture_failure_output capture_failure_status
  local head_capture_failure_output head_capture_failure_status

  set +e
  gitlab_reviews_output="$(forge-cli --provider gitlab --repo fixture/project \
    --format json pr reviews 1 2>&1)"
  gitlab_reviews_status=$?
  set -e
  if [ "$gitlab_reviews_status" -ne 64 ] ||
    ! grep -q '"code":"provider_unsupported"' <<<"$gitlab_reviews_output"; then
    echo "runtime-smoke pr: GitLab pr reviews did not preserve its v1 provider boundary" >&2
    rc=1
  fi

  if ! hyphen_comment_output="$(
    forge-cli pr review validate --provider local --format json \
      --comment=--submit-review
  )" || ! grep -q 'cli.forge-cli.pr.review.validate.v1' \
    <<<"$hyphen_comment_output"; then
    echo "runtime-smoke pr: forge-cli rejected a hyphen-leading inline review body" >&2
    rc=1
  fi
  if ! hyphen_delete_output="$(
    forge-cli --provider github --repo fixture/project --format json \
      pr pending-review delete 1 \
      --review PRR_fixture \
      --expected-head 0000000000000000000000000000000000000000 \
      --expected-commit 0000000000000000000000000000000000000000 \
      --expected-body=--help \
      --confirm-abandoned \
      --dry-run
  )" || ! grep -q 'cli.forge-cli.pr.pending-review.delete.v1' \
    <<<"$hyphen_delete_output"; then
    echo "runtime-smoke pr: forge-cli rejected a hyphen-leading expected review body" >&2
    rc=1
  fi

  set +e
  capture_failure_output="$(
    bash -c 'set -e
      EXPECTED_REVIEW_BODY="$(false)" || exit $?
      readonly EXPECTED_REVIEW_BODY
      printf "sentinel reached\n"' 2>&1
  )"
  capture_failure_status=$?
  set -e
  if [ "$capture_failure_status" -eq 0 ] ||
    grep -q 'sentinel reached' <<<"$capture_failure_output"; then
    echo "runtime-smoke pr: fallible review capture reached its sentinel" >&2
    rc=1
  fi

  set +e
  head_capture_failure_output="$(
    bash -c 'set -e
      EXPECTED_REVIEW_HEAD="$(
        false
      )" || exit $?
      readonly EXPECTED_REVIEW_HEAD
      printf "head sentinel reached\n"' 2>&1
  )"
  head_capture_failure_status=$?
  set -e
  if [ "$head_capture_failure_status" -eq 0 ] ||
    grep -q 'head sentinel reached' <<<"$head_capture_failure_output"; then
    echo "runtime-smoke pr: multiline provider-head capture reached its sentinel" >&2
    rc=1
  fi

  for skill in \
    core/skills/pr/deliver-pr/SKILL.md.tera \
    core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera \
    core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera; do
    if ! grep -q 'forge-cli >=1.28.30' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill does not require forge-cli 1.28.30" >&2
      rc=1
    fi
    if ! grep -q 'forge-cli pr reviews' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits native review summary inspection" >&2
      rc=1
    fi
    if ! grep -q 'review_convergence_activity_changed' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits typed late-activity retry routing" >&2
      rc=1
    fi
    if ! grep -q 'github_pending_review_exists' "$REPO_ROOT/$skill" ||
      ! grep -q -- '--expected-head' "$REPO_ROOT/$skill" ||
      ! grep -q -- '--recover-pending' "$REPO_ROOT/$skill" ||
      ! grep -q 'pending_review_body_mismatch' "$REPO_ROOT/$skill" ||
      ! grep -q '^EXPECTED_REVIEW_HEAD=' "$REPO_ROOT/$skill" ||
      ! grep -q '^readonly EXPECTED_REVIEW_HEAD$' "$REPO_ROOT/$skill" ||
      ! grep -q '^EXPECTED_REVIEW_BODY=' "$REPO_ROOT/$skill" ||
      ! grep -q '^readonly EXPECTED_REVIEW_BODY$' "$REPO_ROOT/$skill" ||
      ! grep -q -- '--comment="$EXPECTED_REVIEW_BODY"' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits delegated pending-review recovery" >&2
      rc=1
    fi
    if ! grep -q 'review_convergence_head_changed' "$REPO_ROOT/$skill" ||
      ! grep -q 're-run validation and affected review' "$REPO_ROOT/$skill" ||
      ! grep -Eq 'requires rebinding (lane )?delivery' "$REPO_ROOT/$skill" ||
      ! grep -q 'the new head' "$REPO_ROOT/$skill" ||
      ! grep -q 'new owner outcome' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill can reuse stale validation or approval after head drift" >&2
      rc=1
    fi
    if ! grep -q 'summary_truncated' "$REPO_ROOT/$skill" ||
      ! grep -q 'full review body' "$REPO_ROOT/$skill" ||
      ! grep -q 'stop if it is unavailable' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill can semantically disposition a truncated review summary" >&2
      rc=1
    fi
    if ! grep -Fq '[ "$PROVIDER" = gitlab ] && REVIEW_CONVERGENCE_ARGS=(--review-convergence=false)' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill does not preserve GitLab delivery under a user-global GitHub convergence policy" >&2
      rc=1
    fi
    if ! grep -q 'do not require ledger artifacts' "$REPO_ROOT/$skill" ||
      ! grep -q 'outcome-note path' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill does not state the GitLab ledger alternative at the normative workflow boundary" >&2
      rc=1
    fi
    if ! grep -q '"${REVIEW_CONVERGENCE_ARGS\[@\]}"' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill does not pass its provider convergence override to merge" >&2
      rc=1
    fi
  done
  # The recovery recipe is destructive, so validate its executable ordering
  # and fail-closed semantics rather than merely checking marker tokens.
  if ! python3 - "$REPO_ROOT" \
    core/skills/pr/deliver-pr/SKILL.md.tera \
    core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera \
    core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera <<'PY'; then
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])

GENESIS_MARKER = "# Review-loop genesis: before any repair, with the CLI-owned preflight sweep."
CLOSING_MARKER = "# Review-loop closing observation: after repair/push and before merge."
LEDGER_GITHUB_MARKER = "# GitHub-only review-loop ledger: GitLab v1 has no ledger surface or merge gate."
LEDGER_CLOSING_GUARD = 'if [ "$PROVIDER" = github ] && [ "${REVIEW_LEDGER_OPEN_COUNT:-0}" -gt 0 ]; then'
CLOSING_DISPOSITIONS_REQUIREMENT = ': "${REVIEW_LEDGER_DISPOSITIONS:?set repaired/accepted finding dispositions}"'
GITLAB_CONVERGENCE_OVERRIDE = '[ "$PROVIDER" = gitlab ] && REVIEW_CONVERGENCE_ARGS=(--review-convergence=false)'
GITHUB_GUARD = 'if [ "$PROVIDER" = github ]; then'

# forge-cli >=1.28.30 owns the review-loop compare-and-swap and the
# pending-review recovery these skills used to hand-roll. What is pinned below
# is therefore no longer the shape of that machinery, but that the skills
# DELEGATE it and cannot quietly grow a second copy: the flags must be bound,
# and the primitives the old state machine drove must not reappear.
RECOVER_PENDING = "--recover-pending"
AUTO_STATE = "--auto-state"
PREFLIGHT = "--preflight"
# Re-implementing recovery in a skill means reaching for one of these again.
FORBIDDEN_RECOVERY_PRIMITIVES = (
    "pr pending-review delete",
    "PENDING_REVIEW_ID",
    ".data.pending_reviews[",
    "--confirm-abandoned",
)


def executable(line, token):
    stripped = line.strip()
    return token in line and "`" not in line and not stripped.startswith("#")


def observe_block(lines, start):
    end = next(
        index for index in range(start + 1, len(lines))
        if lines[index].strip() == ')" || exit $?'
    )
    return end, "\n".join(lines[start:end + 1])


def validate(relative, text):
    lines = text.splitlines()
    if text.count(GITLAB_CONVERGENCE_OVERRIDE) != 1:
        raise ValueError("GitLab convergence override must use the exact provider selector once")
    if relative == "core/skills/pr/deliver-pr/SKILL.md.tera":
        released_enum = "(`open`, `fixed`, `accepted`, `preference`, `follow-up`)"
        if text.count(released_enum) != 1:
            raise ValueError("deliver-pr must document the exact released disposition set once")
        if "(`open`, `fixed`, `accepted`, `reopened`)" in text:
            raise ValueError("deliver-pr documents reopened as an input disposition")
    # Recovery is delegated, so re-growing a hand-rolled copy is the regression
    # this guards, not a missing one.
    for primitive in FORBIDDEN_RECOVERY_PRIMITIVES:
        reintroduced = [
            index for index, line in enumerate(lines)
            if executable(line, primitive)
        ]
        if reintroduced:
            raise ValueError(
                f"pending-review recovery is owned by --recover-pending; "
                f"{primitive!r} reappeared at line {reintroduced[0] + 1}"
            )
    recovers = [
        index for index, line in enumerate(lines)
        if executable(line, RECOVER_PENDING)
    ]
    if len(recovers) != 1:
        raise ValueError(
            f"expected one executable {RECOVER_PENDING} binding, found {len(recovers)}"
        )
    recover_index = recovers[0]
    merges = [
        index for index, line in enumerate(lines)
        if executable(line, "pr merge")
    ]
    if len(merges) != 1:
        raise ValueError(f"expected one executable pr merge, found {len(merges)}")
    merge_index = merges[0]

    genesis = [
        index for index, line in enumerate(lines)
        if line.strip() == GENESIS_MARKER
    ]
    closing = [
        index for index, line in enumerate(lines)
        if line.strip() == CLOSING_MARKER
    ]
    if len(genesis) != 1 or len(closing) != 1:
        raise ValueError("review-loop genesis and closing markers must each appear once")
    if not genesis[0] < closing[0] < merge_index:
        raise ValueError("review-loop order must be genesis, closing observation, merge")
    ledger_markers = [
        index for index, line in enumerate(lines)
        if line.strip() == LEDGER_GITHUB_MARKER
    ]
    if len(ledger_markers) != 1:
        raise ValueError("GitHub-only review-loop boundary marker must appear once")
    ledger_guard = ledger_markers[0] + 1
    if lines[ledger_guard].strip() != GITHUB_GUARD:
        raise ValueError("review-loop genesis is not guarded to GitHub")
    ledger_guard_end = next(
        index for index in range(ledger_guard + 1, len(lines))
        if lines[index].strip() == "fi"
    )
    if not ledger_guard < genesis[0] < ledger_guard_end:
        raise ValueError("review-loop genesis escapes the GitHub-only branch")
    findings_requirements = [
        index for index in range(ledger_guard + 1, ledger_guard_end)
        if 'REVIEW_LEDGER_FINDINGS:?set to delivery-mode' in lines[index]
    ]
    if len(findings_requirements) != 1:
        raise ValueError("GitHub ledger findings input must be required inside its provider branch")
    closing_guards = [
        index for index, line in enumerate(lines)
        if line.strip() == LEDGER_CLOSING_GUARD
    ]
    if len(closing_guards) != 1:
        raise ValueError("review-loop closing observation is not guarded to GitHub")
    closing_guard_end = next(
        index for index in range(closing_guards[0] + 1, len(lines))
        if lines[index].strip() == "fi"
    )
    if closing_guards[0] != closing[0] + 1:
        raise ValueError("review-loop closing GitHub guard must immediately follow its marker")
    genesis_observes = [
        index for index in range(genesis[0], closing[0])
        if executable(lines[index], "pr review-loop observe")
    ]
    closing_observes = [
        index for index in range(closing[0], merge_index)
        if executable(lines[index], "pr review-loop observe")
    ]
    if len(genesis_observes) != 1 or len(closing_observes) != 1:
        raise ValueError(
            "each review-loop phase must be exactly one observe; --preflight "
            "replaced the separate --dry-run call"
        )
    if not closing_guards[0] < closing_observes[0] < closing_guard_end:
        raise ValueError("review-loop closing observation escapes the GitHub-only branch")
    disposition_requirements = [
        index for index in range(closing_guards[0] + 1, closing_guard_end)
        if lines[index].strip() == CLOSING_DISPOSITIONS_REQUIREMENT
    ]
    if len(disposition_requirements) != 1:
        raise ValueError("GitHub ledger dispositions input must be required inside its closing branch")
    if disposition_requirements[0] >= closing_observes[0]:
        raise ValueError("GitHub ledger dispositions input must be required before the closing observation")
    genesis_block = observe_block(lines, genesis_observes[0])
    closing_block = observe_block(lines, closing_observes[0])
    # The two phases name the chain tip differently, and the asymmetry is the
    # point. Genesis has no digest from an earlier round, so --auto-state costs
    # nothing. The closing observation holds the digest the genesis append
    # returned — a claim about a tip this workflow already saw, and the only
    # thing that catches a resumed shell reusing genesis state. Swapping it for
    # --auto-state would re-read and silently accept an advanced chain, so the
    # forbidden token below is as load-bearing as the required ones.
    for label, block, required, forbidden in (
        (
            "genesis",
            genesis_block[1],
            (
                '--expected-head "$REVIEWED_HEAD"',
                AUTO_STATE,
                PREFLIGHT,
                '--findings-file "$REVIEW_LEDGER_FINDINGS"',
            ),
            ("--expected-state", "--dry-run"),
        ),
        (
            "closing",
            closing_block[1],
            (
                '--expected-head "$EXPECTED_REVIEW_HEAD"',
                '--expected-state "$REVIEW_LEDGER_STATE_TIP"',
                PREFLIGHT,
                '--findings-file "$REVIEW_LEDGER_DISPOSITIONS"',
            ),
            (AUTO_STATE, "--dry-run"),
        ),
    ):
        for token in required:
            if token not in block:
                raise ValueError(f"the {label} observation must bind {token}")
        for token in forbidden:
            if token in block:
                raise ValueError(f"the {label} observation must not carry {token}")
    genesis_after_live = "\n".join(lines[genesis_block[0] + 1:closing[0]])
    if ".data.state_tip_digest" not in genesis_after_live:
        raise ValueError("genesis append does not provide the closing state tip")
    closing_after_live = "\n".join(lines[closing_block[0] + 1:merge_index])
    if ".data.state_tip_digest" not in closing_after_live:
        raise ValueError("closing append does not refresh the state tip")

    merge_window = lines[merge_index:merge_index + 6]
    merge_head_bindings = [
        line for line in merge_window
        if executable(line, '--expected-head "$EXPECTED_REVIEW_HEAD"')
    ]
    if len(merge_head_bindings) != 1:
        raise ValueError("final merge must bind the reviewed provider head")

    # The skill must still SAY what it delegates and why a refusal is an answer
    # rather than an obstacle. Without this a future edit could keep the flag and
    # lose the instruction not to work around it by hand.
    required_contract = (
        "github_pending_review_exists",
        RECOVER_PENDING,
        "pending_review_body_mismatch",
        "binds the native review to the inspected head",
    )
    missing = [token for token in required_contract if token not in text]
    if missing:
        raise ValueError(f"missing fail-closed contract text: {', '.join(missing)}")
    if not re.search(
        r"(never|not|do not|never select).{0,120}by hand",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        raise ValueError("recovery contract does not forbid selecting a node by hand")

    # The submission is now one fallible call, so there is no status variable to
    # branch on and no retry to order. What remains worth pinning is that the
    # single call still propagates failure instead of swallowing it.
    submissions = [
        index for index, line in enumerate(lines)
        if executable(line, 'NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}"')
    ]
    if len(submissions) != 1:
        raise ValueError(
            f"expected one native review submission, found {len(submissions)}"
        )
    submission_index = submissions[0]
    if "|| exit $?" not in lines[submission_index]:
        raise ValueError("native review submission must propagate command failure")
    command_assemblies = [
        index for index, line in enumerate(lines)
        if executable(line, "NATIVE_REVIEW_CMD=(")
    ]
    if len(command_assemblies) != 1:
        raise ValueError("expected one native review command assembly")
    if not (recover_index < command_assemblies[0] < submission_index < merge_index):
        raise ValueError(
            "--recover-pending must be bound before the command is assembled and run"
        )
    provider_head_captures = [
        index for index in range(command_assemblies[0])
        if lines[index].strip() == "EXPECTED_REVIEW_HEAD=\"$("
    ]
    if len(provider_head_captures) != 1:
        raise ValueError("native review command must capture one provider head")
    provider_pr_captures = [
        index for index in range(provider_head_captures[0])
        if lines[index].strip() == 'PRE_SUBMIT_PR="$('
    ]
    if len(provider_pr_captures) != 1:
        raise ValueError("reviewed head must come from one provider PR snapshot")
    provider_head_assignments = [
        index for index in range(provider_head_captures[0], merge_index)
        if re.match(r"^EXPECTED_REVIEW_HEAD=", lines[index].strip())
    ]
    if provider_head_assignments != provider_head_captures:
        raise ValueError("reviewed provider head must have one assignment")
    provider_head_readonly = [
        index for index in range(provider_head_captures[0], merge_index)
        if lines[index].strip() == "readonly EXPECTED_REVIEW_HEAD"
    ]
    if len(provider_head_readonly) != 1:
        raise ValueError("reviewed provider head must become readonly once")
    provider_head_failure_guards = [
        index
        for index in range(
            provider_head_captures[0] + 1,
            provider_head_readonly[0],
        )
        if lines[index].strip() == ')" || exit $?'
    ]
    if provider_head_failure_guards != [provider_head_readonly[0] - 1]:
        raise ValueError(
            "provider-head assignment close must propagate failure immediately"
        )
    unguarded_provider_head_closes = [
        index
        for index in range(
            provider_head_captures[0] + 1,
            provider_head_readonly[0],
        )
        if lines[index].strip() == ')"'
    ]
    if unguarded_provider_head_closes:
        raise ValueError("provider-head assignment has an unguarded close")
    review_body_assignments = [
        index for index in range(provider_head_captures[0], merge_index)
        if re.match(r"^EXPECTED_REVIEW_BODY=", lines[index].strip())
    ]
    if len(review_body_assignments) != 1:
        raise ValueError("review body must have one captured assignment")
    if not lines[review_body_assignments[0]].strip().endswith(')" || exit $?'):
        raise ValueError("review-body capture must propagate command failure")
    review_body_readonly = [
        index for index in range(review_body_assignments[0] + 1, merge_index)
        if lines[index].strip() == "readonly EXPECTED_REVIEW_BODY"
    ]
    if len(review_body_readonly) != 1:
        raise ValueError("captured review body must become readonly once")
    if not (
        provider_head_failure_guards[0]
        < provider_head_readonly[0]
        < review_body_assignments[0]
        < review_body_readonly[0]
        < command_assemblies[0]
    ):
        raise ValueError("fallible captures must precede standalone readonly bindings")
    provider_pr_reads = [
        index for index in range(provider_pr_captures[0], provider_head_captures[0])
        if executable(lines[index], "pr view")
    ]
    if len(provider_pr_reads) != 1:
        raise ValueError("provider PR snapshot must read the reviewed head once")
    provider_head_parsers = [
        index for index in range(provider_head_captures[0], command_assemblies[0])
        if executable(lines[index], "| .data.head_sha")
    ]
    if len(provider_head_parsers) != 1:
        raise ValueError("provider PR snapshot head must be parsed once")
    provider_review_head_checks = [
        index for index in range(provider_head_captures[0], command_assemblies[0])
        if executable(lines[index], ".data.head_sha == $head")
    ]
    if len(provider_review_head_checks) != 1:
        raise ValueError("GitHub review snapshot must match the provider PR head")
    review_body_bindings = [
        index for index in range(provider_head_captures[0], submission_index)
        if executable(lines[index], '--comment="$EXPECTED_REVIEW_BODY"')
    ]
    if len(review_body_bindings) != 1:
        raise ValueError("native review command must bind one captured body value")
    # The submit-review flags are now a multi-line array, so the expected-head
    # binding and the array opener no longer share a line. Bound the search by
    # the assembly instead of matching them together.
    # Match only the populated opener: the same name is also initialised empty
    # (`SUBMIT_REVIEW=()`) above, and that line carries no flags.
    submit_review_arrays = [
        index for index in range(closing_observes[-1] + 1, command_assemblies[0])
        if executable(lines[index], "SUBMIT_REVIEW=(")
        and lines[index].strip().endswith("SUBMIT_REVIEW=(")
    ]
    if len(submit_review_arrays) != 1:
        raise ValueError("expected one native submit-review flag array")
    expected_head_bindings = [
        index for index in range(submit_review_arrays[0], command_assemblies[0])
        if executable(lines[index], '--expected-head "$EXPECTED_REVIEW_HEAD"')
    ]
    if len(expected_head_bindings) != 1:
        raise ValueError(
            "native review command must have one executable expected-head binding"
        )
    if not (submit_review_arrays[0] < recover_index < command_assemblies[0]):
        raise ValueError(
            "--recover-pending must be bound inside the native submit-review array"
        )


def replace_observe_flag(text, marker, token, replacement):
    """Rewrite one flag inside the observe block that follows `marker`."""
    lines = text.splitlines()
    marker_index = next(
        index for index, line in enumerate(lines)
        if line.strip() == marker
    )
    observe_index = next(
        index for index in range(marker_index + 1, len(lines))
        if executable(lines[index], "pr review-loop observe")
    )
    end, _ = observe_block(lines, observe_index)
    indexes = [
        index for index in range(observe_index, end + 1)
        if executable(lines[index], token)
    ]
    if len(indexes) != 1:
        raise ValueError(f"expected one {token!r} in the {marker!r} observe")
    lines[indexes[0]] = lines[indexes[0]].replace(token, replacement)
    return "\n".join(lines)


def replace_merge_binding(text, token, replacement):
    lines = text.splitlines()
    merge_index = next(
        index for index, line in enumerate(lines)
        if executable(line, "pr merge")
    )
    indexes = [
        index for index in range(merge_index, min(merge_index + 6, len(lines)))
        if executable(lines[index], token)
    ]
    if len(indexes) != 1:
        raise ValueError(f"expected one merge binding {token!r}")
    lines[indexes[0]] = lines[indexes[0]].replace(token, replacement)
    return "\n".join(lines)


def replace_expected_head_parser(text):
    marker = "EXPECTED_REVIEW_HEAD=\"$("
    start = text.index(marker)
    token = ".data.head_sha"
    index = text.index(token, start)
    return text[:index] + ".data.removed_head_sha" + text[index + len(token):]


def add_dry_run_to_observe(text, marker):
    lines = text.splitlines()
    marker_index = next(
        index for index, line in enumerate(lines)
        if line.strip() == marker
    )
    observe_index = next(
        index for index in range(marker_index + 1, len(lines))
        if executable(lines[index], "pr review-loop observe")
    )
    end, _ = observe_block(lines, observe_index)
    lines.insert(end, "      --dry-run")
    return "\n".join(lines)


def insert_before_executable(text, token, insertion):
    lines = text.splitlines()
    target = next(
        index for index, line in enumerate(lines)
        if executable(line, token)
    )
    lines.insert(target, insertion)
    return "\n".join(lines)


def remove_capture_failure_guard(text, variable):
    lines = text.splitlines()
    assignment_index = next(
        index for index, line in enumerate(lines)
        if line.strip().startswith(f'{variable}="$(')
    )
    readonly_index = next(
        index for index in range(assignment_index + 1, len(lines))
        if lines[index].strip() == f"readonly {variable}"
    )
    guards = [
        index for index in range(assignment_index, readonly_index)
        if "|| exit $?" in lines[index]
    ]
    if len(guards) != 1:
        raise ValueError(f"expected one failure guard for {variable}")
    lines[guards[0]] = lines[guards[0]].replace(" || exit $?", "")
    return "\n".join(lines)


def relocate_head_failure_guard(text):
    lines = text.splitlines()
    assignment_index = next(
        index for index, line in enumerate(lines)
        if line.strip() == 'EXPECTED_REVIEW_HEAD="$('
    )
    readonly_index = next(
        index for index in range(assignment_index + 1, len(lines))
        if lines[index].strip() == "readonly EXPECTED_REVIEW_HEAD"
    )
    guard_index = next(
        index for index in range(assignment_index, readonly_index)
        if "|| exit $?" in lines[index]
    )
    lines[guard_index] = lines[guard_index].replace(" || exit $?", "")
    lines.insert(
        readonly_index,
        'UNRELATED_CAPTURE="$(false)" || exit $?',
    )
    return "\n".join(lines)


for relative in sys.argv[2:]:
    text = (root / relative).read_text()
    try:
        validate(relative, text)
    except ValueError as error:
        raise SystemExit(f"{relative}: {error}") from error

    mutations = {
        "GitHub-only ledger guard": text.replace(
            f"{LEDGER_GITHUB_MARKER}\n{GITHUB_GUARD}",
            f"{LEDGER_GITHUB_MARKER}\nif [ \"$PROVIDER\" = gitlab ]; then",
            1,
        ),
        "closing ledger input guard": text.replace(
            f"{CLOSING_MARKER}\n{LEDGER_CLOSING_GUARD}\n  {CLOSING_DISPOSITIONS_REQUIREMENT}",
            f"{CLOSING_MARKER}\n{CLOSING_DISPOSITIONS_REQUIREMENT}\n{LEDGER_CLOSING_GUARD}",
            1,
        ),
        "GitLab convergence selector": text.replace(
            GITLAB_CONVERGENCE_OVERRIDE,
            GITLAB_CONVERGENCE_OVERRIDE.replace("gitlab", "github"),
            1,
        ),
        "genesis dry-run split": add_dry_run_to_observe(text, GENESIS_MARKER),
        "closing dry-run split": add_dry_run_to_observe(text, CLOSING_MARKER),
        "genesis auto-state": replace_observe_flag(
            text, GENESIS_MARKER, AUTO_STATE, '--expected-state "$OTHER_STATE_TIP"'
        ),
        "genesis preflight": replace_observe_flag(
            text, GENESIS_MARKER, PREFLIGHT, "--no-preflight"
        ),
        # The one a future edit is most likely to get wrong: the closing
        # observation asserts a tip this workflow already saw, and only that
        # catches a resumed shell reusing genesis state.
        "closing tip claim downgraded to a self-read": replace_observe_flag(
            text,
            CLOSING_MARKER,
            '--expected-state "$REVIEW_LEDGER_STATE_TIP"',
            AUTO_STATE,
        ),
        "closing preflight": replace_observe_flag(
            text, CLOSING_MARKER, PREFLIGHT, "--no-preflight"
        ),
        "genesis findings binding": text.replace(
            '--findings-file "$REVIEW_LEDGER_FINDINGS"',
            '--findings-file "$OTHER_FINDINGS"',
        ),
        "closing expected state": text.replace(
            '--expected-state "$REVIEW_LEDGER_STATE_TIP"',
            '--expected-state "$OTHER_STATE_TIP"',
        ),
        "closing findings binding": text.replace(
            '--findings-file "$REVIEW_LEDGER_DISPOSITIONS"',
            '--findings-file "$OTHER_DISPOSITIONS"',
        ),
        "github guard": text.replace(GITHUB_GUARD, "# removed github guard"),
        "recover-pending binding": text.replace(RECOVER_PENDING, "--no-recover-pending"),
        # Delegation is the contract, so hand-rolling it again must fail even
        # though the flag is still present.
        "hand-rolled recovery reintroduced": text.replace(
            'NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}")" || exit $?',
            'NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}")" || exit $?\n'
            '        forge-cli pr pending-review delete "$PR_NUMBER" \\\n'
            '          --review "$PENDING_REVIEW_ID" --confirm-abandoned',
            1,
        ),
        "by-hand prohibition": text.replace("by hand", "as needed"),
        "body-mismatch guidance": text.replace(
            "pending_review_body_mismatch", "some_other_code"
        ),
        "submission failure propagation": text.replace(
            'NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}")" || exit $?',
            'NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}")"',
        ),
        "native command array": text.replace("NATIVE_REVIEW_CMD=(", "REMOVED_CMD=("),
        "typed error gate": text.replace(
            "github_pending_review_exists",
            "github_other_error",
        ),
        "expected-head binding": text.replace(
            '--expected-head "$EXPECTED_REVIEW_HEAD"',
            '--expected-head "$OTHER_REVIEW_HEAD"',
        ),
        "provider PR snapshot": text.replace(
            'PRE_SUBMIT_PR="$(',
            'REMOVED_PRE_SUBMIT_PR="$(',
        ),
        "provider PR head read": text.replace(
            "pr view",
            "pr removed-view",
        ),
        "provider head parse": replace_expected_head_parser(text),
        "provider review-head comparison": text.replace(
            ".data.head_sha == $head",
            ".data.head_sha == $other",
            1,
        ),
        "hyphen-safe review body binding": text.replace(
            '--comment="$EXPECTED_REVIEW_BODY"',
            '--comment "$EXPECTED_REVIEW_BODY"',
        ),
        "final merge expected head": replace_merge_binding(
            text,
            '--expected-head "$EXPECTED_REVIEW_HEAD"',
            '--expected-head "$OTHER_REVIEW_HEAD"',
        ),
        "reviewed head reassignment": insert_before_executable(
            text,
            "pr merge",
            'EXPECTED_REVIEW_HEAD="$OTHER_REVIEW_HEAD"',
        ),
        "captured review body reassignment": insert_before_executable(
            text,
            'NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}")"',
            'EXPECTED_REVIEW_BODY="$OTHER_REVIEW_BODY"',
        ),
        "reviewed head readonly binding": text.replace(
            "readonly EXPECTED_REVIEW_HEAD",
            "REMOVED_READONLY EXPECTED_REVIEW_HEAD",
        ),
        "captured review body readonly binding": text.replace(
            "readonly EXPECTED_REVIEW_BODY",
            "REMOVED_READONLY EXPECTED_REVIEW_BODY",
        ),
        "provider head capture failure propagation": remove_capture_failure_guard(
            text,
            "EXPECTED_REVIEW_HEAD",
        ),
        "provider head relocated failure propagation": relocate_head_failure_guard(text),
        "review body capture failure propagation": remove_capture_failure_guard(
            text,
            "EXPECTED_REVIEW_BODY",
        ),
    }
    for mutation, candidate in mutations.items():
        try:
            validate(relative, candidate)
        except ValueError:
            continue
        raise SystemExit(f"{relative}: validator accepted missing {mutation}")
PY
    echo "runtime-smoke pr: delivery skills weaken guarded pending-review recovery" >&2
    rc=1
  fi

  if grep -q 'Sweep provider review threads immediately before merge' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"; then
    echo "runtime-smoke pr: deliver-pr still mandates an unconditional manual thread sweep" >&2
    rc=1
  fi
  if grep -q '# Disposition every review thread and task-list item before merge.' \
    "$REPO_ROOT/core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera"; then
    echo "runtime-smoke pr: tracking delivery still duplicates unconditional merge-gate reads" >&2
    rc=1
  fi
  return "$rc"
}

write_test_first_gate_records() {
  local v2_dir="$1"
  local v1_dir="$2"
  local owner="$3"
  mkdir -p "$v2_dir" "$v1_dir"
  test-first-evidence init \
    --out "$v2_dir" \
    --classification behavior-change \
    --production-path src/lib.rs \
    --changed-behavior "runtime smoke exercises strict v2 $owner" \
    --format json >/dev/null
  test-first-evidence record-impact \
    --out "$v2_dir" \
    --none \
    --reason "the isolated fixture has no pre-existing test surface" \
    --format json >/dev/null
  test-first-evidence record-failing \
    --out "$v2_dir" \
    --command "false" \
    --exit-code 1 \
    --test-name "runtime-smoke-test-first-v2-$owner" \
    --expected-failure "the fixture behavior is absent before implementation" \
    --observed-failure "the focused fixture command returned exit 1" \
    --summary "strict v2 red fixture" \
    --format json >/dev/null
  test-first-evidence record-final \
    --out "$v2_dir" \
    --command "true" \
    --status pass \
    --scope focused \
    --summary "focused fixture validation passed" \
    --format json >/dev/null
  test-first-evidence record-gap --out "$v2_dir" --none --format json >/dev/null
  test-first-evidence verify --out "$v2_dir" --format json >/dev/null

  printf '%s\n' \
    '{"schema_version":"test-first-evidence.record.v1","change_classification":"behavior-change","failing_test":{"command":"false","exit_code":1,"summary":"red","artifacts":[]},"final_validation":{"command":"true","status":"pass","artifacts":[]}}' \
    >"$v1_dir/test-first-evidence.json"
}

run_create_test_first_v2_gate_probe() {
  local workspace="$PR_WORKSPACE/create-test-first-v2-gate"
  local body="$PR_ARTIFACTS_DIR/create-test-first-v2-body.md"
  local v2_dir="$PR_ARTIFACTS_DIR/create-test-first-v2-record"
  local v1_dir="$PR_ARTIFACTS_DIR/create-test-first-v1-record"
  local accepted_out="$PR_ARTIFACTS_DIR/create-test-first-v2-accepted.json"
  local rejected_out="$PR_ARTIFACTS_DIR/create-test-first-v1-rejected.json"
  local rc
  require_pr_bin forge-cli || return 1
  require_pr_bin test-first-evidence || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  printf '[test_first]\nrequire = true\n' >"$workspace/.forge-cli.toml"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-create-test-first-v2" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$body"
  write_test_first_gate_records "$v2_dir" "$v1_dir" "create"

  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr create \
      --kind feature \
      --base main \
      --title "Runtime smoke strict v2 PR" \
      --body-file "$body" \
      --test-first-evidence "$v2_dir" \
      --no-draft
  ) >"$accepted_out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$accepted_out"
  grep -q '"provider":"github"' "$accepted_out"

  set +e
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr create \
      --kind feature \
      --base main \
      --title "Runtime smoke rejected v1 PR" \
      --body-file "$body" \
      --test-first-evidence "$v1_dir" \
      --no-draft
  ) >"$rejected_out" 2>&1
  rc="$?"
  set -e
  test "$rc" -eq 65
  grep -q '"code":"test_first_evidence_v1"' "$rejected_out"
}

run_deliver_test_first_v2_gate_probe() {
  local workspace="$PR_WORKSPACE/deliver-test-first-v2-gate"
  local body="$PR_ARTIFACTS_DIR/deliver-test-first-v2-body.md"
  local v2_dir="$PR_ARTIFACTS_DIR/deliver-test-first-v2-record"
  local v1_dir="$PR_ARTIFACTS_DIR/deliver-test-first-v1-record"
  local accepted_out="$PR_ARTIFACTS_DIR/deliver-test-first-v2-accepted.json"
  local rejected_out="$PR_ARTIFACTS_DIR/deliver-test-first-v1-rejected.json"
  require_pr_bin forge-cli || return 1
  require_pr_bin test-first-evidence || return 1
  require_pr_bin jq || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  printf '[test_first]\nrequire = true\n' >"$workspace/.forge-cli.toml"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-deliver-test-first-v2" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$body"
  write_test_first_gate_records "$v2_dir" "$v1_dir" "deliver"

  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr deliver \
      --kind feature \
      --base main \
      --title "Runtime smoke strict v2 delivery" \
      --body-file "$body" \
      --test-first-evidence "$v2_dir" \
      --no-merge
  ) >"$accepted_out" 2>&1
  jq -e '
    .schema_version == "cli.forge-cli.pr.deliver.v1" and
    (.data.local_preflight[] | select(.rule == "test_first" and .ok == true))
  ' "$accepted_out" >/dev/null

  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr deliver \
      --kind feature \
      --base main \
      --title "Runtime smoke rejected v1 delivery" \
      --body-file "$body" \
      --test-first-evidence "$v1_dir" \
      --no-merge
  ) >"$rejected_out" 2>&1
  jq -e '
    .schema_version == "cli.forge-cli.pr.deliver.v1" and
    (.data.local_preflight[] |
      select(.rule == "test_first" and .ok == false and
        .code == "test_first_evidence_v1"))
  ' "$rejected_out" >/dev/null
}

run_pr_comment_provider_payload_privacy_gate_probe() {
  local body="$PR_ARTIFACTS_DIR/pr-comment-local-path.md"
  local out="$PR_ARTIFACTS_DIR/pr-comment-local-path-gate.json"
  local raw_path="/U""sers/example/project"
  local rc
  require_pr_bin forge-cli || return 1
  printf 'Runtime smoke should not publish %s\n' "$raw_path" >"$body"

  set +e
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr comment 123 \
    --body-file "$body" >"$out" 2>&1
  rc="$?"
  set -e

  [ "$rc" -ne 0 ] || return 1
  assert_provider_payload_local_path_gate "$out" "$raw_path"
}

run_specialist_scope_probe() {
  local workspace="$1"
  local out="$2"
  shift 2
  require_pr_bin review-specialists || return 1
  review-specialists scope \
    --repo "$workspace" \
    --base main \
    "$@" \
    --format json >"$out" 2>&1
  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$out"
}

run_create_github_probe() {
  local workspace="$PR_WORKSPACE/create-github"
  local body="$PR_ARTIFACTS_DIR/create-github-body.md"
  local out="$PR_ARTIFACTS_DIR/create-github.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-github" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base main \
      --title "Runtime smoke GitHub PR" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::s \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels \
      --no-draft
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::s"' "$out"
  grep -Eq '"/?([^"/]+/)*gh"' "$out"
}

run_create_gitlab_probe() {
  local workspace="$PR_WORKSPACE/create-gitlab"
  local body="$PR_ARTIFACTS_DIR/create-gitlab-body.md"
  local out="$PR_ARTIFACTS_DIR/create-gitlab.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-gitlab" \
    "git@gitlab.com:group/project.git"
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider gitlab --repo group/project \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base main \
      --title "Runtime smoke GitLab MR" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::s \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$out"
  grep -q '"provider":"gitlab"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::s"' "$out"
  grep -Eq '"/?([^"/]+/)*glab"' "$out"
}

run_create_dispatch_lane_probe() {
  local workspace="$PR_WORKSPACE/create-dispatch"
  local body="$PR_ARTIFACTS_DIR/create-dispatch-body.md"
  local out="$PR_ARTIFACTS_DIR/create-dispatch.json"
  local session="$PR_ARTIFACTS_DIR/create-dispatch-session.md"
  local session_payload="$PR_ARTIFACTS_DIR/create-dispatch-session-payload.json"
  local post_out="$PR_ARTIFACTS_DIR/create-dispatch-session-post.json"
  require_pr_bin forge-cli || return 1
  require_pr_bin plan-issue || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/dispatch-lane-runtime-smoke" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base plan/issue-26 \
      --title "Runtime smoke dispatch lane" \
      --body-file "$body" \
      --label type::feature \
      --label area::skills \
      --label size::s \
      --label workflow::dispatch \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels
  ) >"$out" 2>&1
  write_dispatch_session_record "$session"
  cat >"$session_payload" <<'JSON'
{"summary":"Runtime smoke dispatch lane PR created"}
JSON
  plan-issue record post \
    --dry-run \
    --issue 50 \
    --profile dispatch \
    --kind session \
    --payload-file "$session_payload" \
    --summary-file "$session" \
    --format json >"$post_out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"workflow::dispatch"' "$out"
  grep -q '"size::s"' "$out"
  grep -q '"schema_version":"plan-issue.record.post.v2"' "$post_out"
  grep -q '<!-- plan-issue-record:v2 role=session profile=dispatch -->' "$post_out"
}

run_close_github_probe() {
  local workspace="$PR_WORKSPACE/close-github"
  local out="$PR_ARTIFACTS_DIR/close-github.jsonl"
  local review_out="$PR_ARTIFACTS_DIR/close-github-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-close-github" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  run_specialist_scope_probe "$workspace" "$review_out"
  (
    cd "$workspace"
    {
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr checks 123
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr ready 123
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr merge 123 --method merge
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr close 123
    } >"$out" 2>&1
  )
  grep -q '"schema_version":"cli.forge-cli.pr.checks.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.ready.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.merge.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.close.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"suggested_specialists"' "$review_out"
}

run_close_gitlab_probe() {
  local workspace="$PR_WORKSPACE/close-gitlab"
  local out="$PR_ARTIFACTS_DIR/close-gitlab.jsonl"
  local review_out="$PR_ARTIFACTS_DIR/close-gitlab-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-close-gitlab" \
    "git@gitlab.com:group/project.git"
  run_specialist_scope_probe "$workspace" "$review_out"
  (
    cd "$workspace"
    {
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr checks 123
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr ready 123
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr merge 123 --method merge
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr close 123
    } >"$out" 2>&1
  )
  grep -q '"schema_version":"cli.forge-cli.pr.checks.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.ready.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.merge.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.close.v1"' "$out"
  grep -q '"provider":"gitlab"' "$out"
  grep -q '"suggested_specialists"' "$review_out"
}

run_deliver_github_probe() {
  local workspace="$PR_WORKSPACE/deliver-github"
  local body="$PR_ARTIFACTS_DIR/deliver-github-body.md"
  local review_body="$PR_ARTIFACTS_DIR/deliver-github-review.md"
  local review_threads="$PR_ARTIFACTS_DIR/deliver-github-review-threads.json"
  local out="$PR_ARTIFACTS_DIR/deliver-github.json"
  local provider_review_out="$PR_ARTIFACTS_DIR/deliver-github-provider-review.json"
  local quick_review_out="$PR_ARTIFACTS_DIR/deliver-github-quick-review.json"
  local review_out="$PR_ARTIFACTS_DIR/deliver-github-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-deliver-github" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  run_specialist_scope_probe "$workspace" "$review_out" --testing --maintainability
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr deliver \
      --kind feature \
      --base main \
      --title "Runtime smoke GitHub delivery" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::m \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels \
      --no-merge
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.deliver.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"wait_checks"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::m"' "$out"
  grep -q '"gh"' "$out"
  grep -q '"forced_specialists"' "$review_out"
  grep -q '"maintainability"' "$review_out"
  grep -q '"testing"' "$review_out"
  grep -q 'lifecycle readiness is also a pre-merge gate' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'plan-issue --format json record audit' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'role=session' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  printf 'Runtime smoke deliver-pr specialist review.\n' >"$review_body"
  printf '[{"path":"pr-fixture.txt","line":1,"body":"Runtime smoke deliver-pr actionable finding thread."}]\n' >"$review_threads"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr review 123 \
      --decision comments-only \
      --submit-review \
      --expected-head "$(git rev-parse HEAD)" \
      --thread-file "$review_threads" \
      --comment-file "$review_body" \
      --lens testing
  ) >"$provider_review_out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$provider_review_out"
  grep -q '"decision":"comments-only"' "$provider_review_out"
  grep -q '"planned_review_threads"' "$provider_review_out"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr review 123 \
      --decision approve \
      --comment-file "$review_body" \
      --lens quick
  ) >"$quick_review_out" 2>&1
  jq -e '
    .schema_version == "cli.forge-cli.pr.review.v1" and
    .ok == true and
    .data.decision == "approve" and
    .data.submitted_review == false and
    .data.lenses == ["quick"] and
    (.data.plan | length > 0)
  ' "$quick_review_out" >/dev/null
}

run_deliver_gitlab_probe() {
  local workspace="$PR_WORKSPACE/deliver-gitlab"
  local body="$PR_ARTIFACTS_DIR/deliver-gitlab-body.md"
  local out="$PR_ARTIFACTS_DIR/deliver-gitlab.json"
  local review_out="$PR_ARTIFACTS_DIR/deliver-gitlab-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-deliver-gitlab" \
    "git@gitlab.com:group/project.git"
  run_specialist_scope_probe "$workspace" "$review_out" --testing --maintainability
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider gitlab --repo group/project \
      --dry-run --format json \
      pr deliver \
      --kind feature \
      --base main \
      --title "Runtime smoke GitLab delivery" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::m \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels \
      --no-merge
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.deliver.v1"' "$out"
  grep -q '"provider":"gitlab"' "$out"
  grep -q '"wait_checks"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::m"' "$out"
  grep -q '"glab"' "$out"
  grep -q '"forced_specialists"' "$review_out"
  grep -q '"maintainability"' "$review_out"
  grep -q '"testing"' "$review_out"
  grep -q 'lifecycle readiness is also a pre-merge gate' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'plan-issue --format json record audit' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'role=session' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
}

# The provider-neutral deliver-pr outcome covers the complete lifecycle for both
# providers, so each case exercises the GitHub and GitLab probe and fails if
# either provider regresses.
run_create_pr_probe() {
  local rc=0
  run_create_github_probe || rc=1
  run_create_gitlab_probe || rc=1
  run_create_test_first_v2_gate_probe || rc=1
  return "$rc"
}

run_close_pr_probe() {
  local rc=0
  run_close_github_probe || rc=1
  run_close_gitlab_probe || rc=1
  return "$rc"
}

run_deliver_pr_probe() {
  local rc=0
  run_deliver_github_probe || rc=1
  run_deliver_gitlab_probe || rc=1
  run_pr_comment_provider_payload_privacy_gate_probe || rc=1
  assert_delivery_skills_thread_test_first_evidence || rc=1
  assert_delivery_skills_own_terminal_worktree_cleanup || rc=1
  assert_delivery_skills_use_native_review_convergence || rc=1
  run_deliver_test_first_v2_gate_probe || rc=1
  return "$rc"
}

# review-thread-cleanup wraps the forge-cli `pr review-threads` group: `list`
# (provider-aware read) plus the GitHub-only `resolve` / `reply` write surfaces.
# The probe exercises the GitHub write-surface dry-runs (which plan offline),
# asserts GitLab resolve fails closed with provider_unsupported, and asserts the
# shared skill documents the read + write invocations and cites the convergence
# policy as its judgment contract.
#
# NB: `pr review-threads list --dry-run` is intentionally NOT probed here. In
# forge-cli v1.9.1 the `list` dry-run still issues a live `gh` PR-view call
# before reaching the dry-run plan branch, so probing it would make this
# deterministic smoke depend on network / `gh` auth / a live PR (it would fail
# closed on a host without them). Tracked upstream (nils-cli); restore the `list`
# dry-run assertion once it plans offline like `resolve` / `reply`.
run_review_thread_cleanup_github_probe() {
  local workspace="$PR_WORKSPACE/review-thread-cleanup-github"
  local resolve_out="$PR_ARTIFACTS_DIR/review-thread-cleanup-resolve.json"
  local reply_out="$PR_ARTIFACTS_DIR/review-thread-cleanup-reply.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-review-thread-cleanup" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr review-threads resolve 123 \
      --thread PRRT_runtimesmoke --note "Resolved per convergence policy." >"$resolve_out" 2>&1
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr review-threads reply 123 \
      --thread PRRT_runtimesmoke --body "Acknowledged." >"$reply_out" 2>&1
  )
  grep -q '"schema_version":"cli.forge-cli.pr.review-threads.resolve.v1"' "$resolve_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review-threads.reply.v1"' "$reply_out"
  grep -q 'resolveReviewThread' "$resolve_out"
  grep -q 'addPullRequestReviewThreadReply' "$reply_out"
}

run_review_thread_cleanup_gitlab_probe() {
  local workspace="$PR_WORKSPACE/review-thread-cleanup-gitlab"
  local out="$PR_ARTIFACTS_DIR/review-thread-cleanup-gitlab-resolve.json"
  local rc
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-review-thread-cleanup-gitlab" \
    "git@gitlab.com:group/project.git"
  set +e
  (
    cd "$workspace"
    forge-cli --provider gitlab --repo group/project \
      --dry-run --format json pr review-threads resolve 123 --thread PRRT_x
  ) >"$out" 2>&1
  rc="$?"
  set -e
  [ "$rc" -ne 0 ] || return 1
  grep -q '"code":"provider_unsupported"' "$out"
}

assert_review_thread_cleanup_skill_documents_surface() {
  local skill="$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  local rc=0
  if [ ! -f "$skill" ]; then
    echo "runtime-smoke pr: missing $skill" >&2
    return 1
  fi
  grep -q 'pr review-threads list' "$skill" || rc=1
  grep -q 'reply and' "$skill" || rc=1
  grep -q 'resolve' "$skill" || rc=1
  grep -q 'review-thread-convergence' "$skill" || rc=1
  if [ "$rc" -ne 0 ]; then
    echo "runtime-smoke pr: $skill omits read/write surface or convergence policy reference" >&2
  fi
  return "$rc"
}

run_review_thread_cleanup_probe() {
  local rc=0
  run_review_thread_cleanup_github_probe || rc=1
  run_review_thread_cleanup_gitlab_probe || rc=1
  assert_review_thread_cleanup_skill_documents_surface || rc=1
  return "$rc"
}

run_pr_outcome_routing_probe() {
  local skill="$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  local rendered_helper="$REPO_ROOT/tests/runtime-smoke/lib/rendered-contract.sh"

  grep -Fq '## Lifecycle Mode Selection' "$skill"
  grep -Fq '## Review Profile Selection' "$skill"
  grep -Fq '**Create only**' "$skill"
  grep -Fq '**Deliver**' "$skill"
  grep -Fq '**Review repair**' "$skill"
  grep -Fq '**Merge**' "$skill"
  grep -Fq '**Close unmerged**' "$skill"
  grep -Fq '**Quick merge**' "$skill"
  grep -Fq 'L0 or L1' "$skill"
  grep -Fq 'L2 or L3' "$skill"
  grep -Fq 'scope suggests or forces no risk' "$skill"
  grep -Fq 'A clean `pass` is terminal' "$skill"
  grep -Fq 'review evidence for the current head' "$skill"
  grep -Fq 'routes to the full pre-merge profile without changing the work tier' "$skill"
  grep -Fq '.agents/scripts/pre-pr.sh' "$skill"
  grep -Fq 'semantic-commit' "$skill"
  grep -Fq 'The user requests the PR/MR outcome, not a lifecycle helper.' "$skill"
  awk '
    /^## Workflow/ { in_workflow = 1; next }
    /^## Boundary/ { in_workflow = 0 }
    in_workflow && /close-unmerged mode/ { close_line = NR }
    in_workflow && /\.agents\/scripts\/pre-pr\.sh/ { pre_pr_line = NR }
    END { exit !(close_line && pre_pr_line && close_line < pre_pr_line) }
  ' "$skill"

  # Every rendered assertion must be able to bootstrap its product surface in
  # a standalone deterministic domain run from a clean checkout.
  grep -Fq 'rendered_contract_prepare_product "$product"' "$rendered_helper"

  rendered_contract_assert_skill pr deliver-pr
  rendered_contract_assert_all_contain pr deliver-pr '## Lifecycle Mode Selection'
  rendered_contract_assert_all_contain pr deliver-pr '## Review Profile Selection'
  rendered_contract_assert_all_contain pr deliver-pr '## Review-Loop Ledger'
  rendered_contract_assert_all_contain pr deliver-pr '(`open`, `fixed`, `accepted`, `preference`, `follow-up`)'
  rendered_contract_assert_all_omit pr deliver-pr '(`open`, `fixed`, `accepted`, `reopened`)'
  rendered_contract_assert_all_contain pr deliver-pr '`review_finding_reopened`'
  rendered_contract_assert_all_contain pr deliver-pr 'faithful non-mutating `review-loop observe --preflight` sweep'
  rendered_contract_assert_all_contain pr deliver-pr 'GitLab has neither the ledger'
  rendered_contract_assert_all_contain pr deliver-pr '`--review-convergence=false` without calling `pr review-loop`'
  rendered_contract_assert_all_contain pr deliver-pr '**Quick merge**'
  rendered_contract_assert_all_contain pr deliver-pr '**Close unmerged**'
  rendered_contract_assert_all_contain pr deliver-pr 'run `forge-cli pr close` and stop before delivery'
}

failures=0
record_case "pr.outcome-routing.create" "forge-cli GitHub+GitLab pr create dry-run passed" run_create_pr_probe
record_case "pr.outcome-routing.dispatch-lane" "forge-cli dispatch lane pr create dry-run passed" run_create_dispatch_lane_probe
record_case "pr.outcome-routing.close" "forge-cli GitHub+GitLab close dry-runs and optional specialist scope passed" run_close_pr_probe
record_case "pr.deliver-pr" "forge-cli GitHub+GitLab delivery macro and full-review scope passed" run_deliver_pr_probe
record_case "pr.outcome-routing.review-threads" "forge-cli review-threads resolve/reply offline dry-runs, GitLab fail-closed, and documented shared skill surface" run_review_thread_cleanup_probe
record_case "pr.outcome-routing.contract" "one governed PR/MR outcome selects lifecycle mode plus quick or full review" run_pr_outcome_routing_probe

exit "$failures"
