#!/usr/bin/env bash
# Deterministic probes for browser skills.
# shellcheck disable=SC2329

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"

BROWSER_ARTIFACTS_DIR="$ARTIFACTS_DIR/browser"
BROWSER_WORKSPACE="$TMP_ROOT/workspaces/browser-basic-repo"
mkdir -p "$BROWSER_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$BROWSER_WORKSPACE"

require_browser_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke browser: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_browser_session_probe() {
  local session_dir="$BROWSER_ARTIFACTS_DIR/browser-session"
  local artifact="$session_dir/local-artifact.txt"
  local init_out="$BROWSER_ARTIFACTS_DIR/browser-session.init.json"
  local step_out="$BROWSER_ARTIFACTS_DIR/browser-session.step.json"
  local verify_out="$BROWSER_ARTIFACTS_DIR/browser-session.verify.json"
  require_browser_bin browser-session || return 1
  mkdir -p "$session_dir"
  printf 'runtime smoke browser-session artifact\n' >"$artifact"
  (
    cd "$BROWSER_WORKSPACE"
    browser-session init \
      --out "$session_dir" \
      --target "file://runtime-smoke/basic-repo" \
      --goal "verify runtime smoke browser-session evidence" \
      --browser "none" \
      --format json
    browser-session record-step \
      --out "$session_dir" \
      --action "recorded deterministic local fixture evidence" \
      --expectation "session verifies without browser network access" \
      --status pass \
      --artifact "$artifact" \
      --format json
    browser-session verify --out "$session_dir" --format json
  ) >"$BROWSER_ARTIFACTS_DIR/browser-session.combined.json" 2>&1
  sed -n '1,/^}$/p' "$BROWSER_ARTIFACTS_DIR/browser-session.combined.json" >"$init_out"
  sed -n '/"schema_version": "cli.browser-session.record-step.v1"/,/^}$/p' "$BROWSER_ARTIFACTS_DIR/browser-session.combined.json" >"$step_out"
  sed -n '/"schema_version": "cli.browser-session.verify.v1"/,$p' "$BROWSER_ARTIFACTS_DIR/browser-session.combined.json" >"$verify_out"
  grep -q '"schema_version": "cli.browser-session.init.v1"' "$init_out"
  grep -q '"schema_version": "cli.browser-session.record-step.v1"' "$step_out"
  grep -q '"schema_version": "cli.browser-session.verify.v1"' "$verify_out"
  grep -q '"ok": true' "$verify_out"
  grep -q '"complete": true' "$verify_out"
}

run_canary_check_probe() {
  local pass_dir="$BROWSER_ARTIFACTS_DIR/canary-pass"
  local expected_fail_dir="$BROWSER_ARTIFACTS_DIR/canary-expected-failure"
  local pass_out="$BROWSER_ARTIFACTS_DIR/canary.pass.json"
  local pass_verify="$BROWSER_ARTIFACTS_DIR/canary.pass.verify.json"
  local expected_fail_out="$BROWSER_ARTIFACTS_DIR/canary.expected-failure.json"
  local expected_fail_verify="$BROWSER_ARTIFACTS_DIR/canary.expected-failure.verify.json"
  require_browser_bin canary-check || return 1
  (
    cd "$BROWSER_WORKSPACE"
    canary-check run \
      --out "$pass_dir" \
      --name runtime-smoke-pass \
      --command "printf runtime-smoke" \
      --format json
    canary-check verify --out "$pass_dir" --format json
    canary-check run \
      --out "$expected_fail_dir" \
      --name runtime-smoke-expected-nonzero \
      --command "exit 7" \
      --expect-exit 7 \
      --format json
    canary-check verify --out "$expected_fail_dir" --format json
  ) >"$BROWSER_ARTIFACTS_DIR/canary.combined.json" 2>&1
  sed -n '1,/^}$/p' "$BROWSER_ARTIFACTS_DIR/canary.combined.json" >"$pass_out"
  sed -n '/"schema_version": "cli.canary-check.verify.v1"/,/^}$/p' "$BROWSER_ARTIFACTS_DIR/canary.combined.json" >"$pass_verify"
  sed -n '/"name": "runtime-smoke-expected-nonzero"/,$p' "$BROWSER_ARTIFACTS_DIR/canary.combined.json" >"$expected_fail_out"
  sed -n '/"schema_version": "cli.canary-check.verify.v1"/,$p' "$BROWSER_ARTIFACTS_DIR/canary.combined.json" | tail -n 20 >"$expected_fail_verify"
  grep -q '"schema_version": "cli.canary-check.run.v1"' "$pass_out"
  grep -q '"schema_version": "cli.canary-check.verify.v1"' "$pass_verify"
  grep -q '"runtime-smoke"' "$pass_verify"
  grep -q '"name": "runtime-smoke-expected-nonzero"' "$expected_fail_out"
  grep -q '"exit_code": 7' "$expected_fail_out"
  grep -q '"expect_exit": 7' "$expected_fail_out"
  grep -q '"status": "pass"' "$expected_fail_verify"
}

run_browser_routing_contract_probe() {
  local policy="$REPO_ROOT/core/policies/browser-test-routing.md"
  grep -q 'Static HTTP success must not be reported' "$policy"
  grep -q 'Rendered page state' "$policy"
  grep -q 'Project Playwright/browser test harness' "$policy"
  grep -q 'macOS desktop Computer Use outcome' "$policy"
  grep -q 'Hermes can read this policy' "$policy"
  grep -q 'no runtime-kit hook or agent-docs injection path' "$policy"
}

failures=0
record_case "browser.browser-session" "browser-session init, step, and verify passed with local artifacts" run_browser_session_probe
record_case "browser.canary-check" "canary-check recorded passing and expected-nonzero local commands" run_canary_check_probe
record_case "browser.route-by-claim" "browser-test policy distinguishes HTTP, rendered browser, Playwright, and desktop claims" run_browser_routing_contract_probe

exit "$failures"
