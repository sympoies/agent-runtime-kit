#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PYTHONDONTWRITEBYTECODE=1
python3 tests/agent-hook/test_policy_contract.py
python3 tests/agent-hook/test_cutover_contract.py

run_executable_contract_tests() {
  local hook_bin="$1"
  local test_output_root
  local repo_agent_out_absent=0

  if [[ ! -e "$REPO_ROOT/agent-out" ]]; then
    repo_agent_out_absent=1
  fi

  test_output_root="$(
    agent-out project --topic agent-hook-tests --repo "$REPO_ROOT" --mkdir
  )"
  case "$test_output_root" in
    "$REPO_ROOT" | "$REPO_ROOT"/*)
      echo "agent-hook tests: agent-out allocated inside the repository: $test_output_root" >&2
      return 1
      ;;
  esac

  AGENT_HOOK_BIN="$hook_bin" \
    AGENT_HOOK_TEST_OUTPUT_ROOT="$test_output_root" \
    python3 tests/agent-hook/test_executable_contract.py
  AGENT_HOOK_BIN="$hook_bin" python3 tests/agent-hook/test_setup_migration.py

  if [[ "$repo_agent_out_absent" -eq 1 && -e "$REPO_ROOT/agent-out" ]]; then
    echo "agent-hook tests: official route created forbidden repo-root ./agent-out/" >&2
    return 1
  fi
}

if [[ -n "${AGENT_HOOK_BIN:-}" ]]; then
  run_executable_contract_tests "$AGENT_HOOK_BIN"
elif command -v agent-hook >/dev/null 2>&1; then
  run_executable_contract_tests "$(command -v agent-hook)"
fi
