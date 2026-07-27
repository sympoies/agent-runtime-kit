#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PYTHONDONTWRITEBYTECODE=1

SOURCE_HOOK_PYCACHE="$REPO_ROOT/core/hooks/shared/__pycache__"

assert_source_hook_cache_absent() {
  if [[ -e "$SOURCE_HOOK_PYCACHE" ]]; then
    echo "hook tests: source bytecode cache is not allowed: $SOURCE_HOOK_PYCACHE" >&2
    echo "hook tests: remove the generated directory before retrying" >&2
    return 1
  fi
}

assert_source_hook_cache_absent
test_status=0
python3 tests/hooks/test_shared_hooks.py "$@" || test_status=$?
assert_source_hook_cache_absent
exit "$test_status"
