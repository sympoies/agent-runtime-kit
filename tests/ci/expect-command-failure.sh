#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HELPER="$REPO_ROOT/scripts/ci/expect-command-failure.sh"
EXPECTED_MESSAGE="ci/all.sh: invalid surface acceptance fixture rejected as expected"
UNEXPECTED_MESSAGE="ci/all.sh: invalid surface acceptance fixture unexpectedly passed"
VALIDATOR_DIAGNOSTIC="validate-surfaces-manifest: invalid acceptance fixture"
failures=0

assert_contains() {
  local output="$1"
  local expected="$2"
  local context="$3"

  case "$output" in
    *"$expected"*) ;;
    *)
      printf 'FAIL: %s: missing %s\n' "$context" "$expected" >&2
      failures=$((failures + 1))
      ;;
  esac
}

set +e
rejection_output="$(
  bash "$HELPER" "$EXPECTED_MESSAGE" "$UNEXPECTED_MESSAGE" \
    bash -c 'printf "%s\n" "$1" >&2; exit 2' _ "$VALIDATOR_DIAGNOSTIC" \
    2>&1
)"
rejection_status=$?
set -e

if [ "$rejection_status" -ne 0 ]; then
  printf 'FAIL: expected rejection returned status %s, want 0\n' \
    "$rejection_status" >&2
  failures=$((failures + 1))
fi
assert_contains "$rejection_output" "$VALIDATOR_DIAGNOSTIC" \
  "expected rejection diagnostic"
assert_contains "$rejection_output" "$EXPECTED_MESSAGE" \
  "expected rejection message"

set +e
unexpected_output="$(
  bash "$HELPER" "$EXPECTED_MESSAGE" "$UNEXPECTED_MESSAGE" \
    bash -c 'exit 0' \
    2>&1
)"
unexpected_status=$?
set -e

if [ "$unexpected_status" -eq 0 ]; then
  printf 'FAIL: unexpected command success returned status 0\n' >&2
  failures=$((failures + 1))
fi
assert_contains "$unexpected_output" "$UNEXPECTED_MESSAGE" \
  "unexpected success message"

if [ "$failures" -ne 0 ]; then
  printf 'expect-command-failure test: %s failure(s)\n' "$failures" >&2
  exit 1
fi

echo "expect-command-failure test: OK"
