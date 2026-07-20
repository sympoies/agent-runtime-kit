#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PYTHONDONTWRITEBYTECODE=1
python3 tests/agent-hook/test_policy_contract.py
python3 tests/agent-hook/test_cutover_contract.py

if [[ -n "${AGENT_HOOK_BIN:-}" ]]; then
  python3 tests/agent-hook/test_executable_contract.py
  python3 tests/agent-hook/test_setup_migration.py
elif command -v agent-hook >/dev/null 2>&1; then
  AGENT_HOOK_BIN="$(command -v agent-hook)" \
    python3 tests/agent-hook/test_executable_contract.py
  AGENT_HOOK_BIN="$(command -v agent-hook)" \
    python3 tests/agent-hook/test_setup_migration.py
fi
