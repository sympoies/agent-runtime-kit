#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SOURCE_BIN="${AGENT_SESSION_SOURCE_BIN:-}"

case "$SOURCE_BIN" in
  /*) ;;
  *)
    echo "session-coordination-coupled-acceptance: AGENT_SESSION_SOURCE_BIN must be an absolute path" >&2
    exit 64
    ;;
esac

if [[ ! -f "$SOURCE_BIN" || ! -x "$SOURCE_BIN" ]]; then
  echo "session-coordination-coupled-acceptance: source binary is not an executable regular file: $SOURCE_BIN" >&2
  exit 64
fi

AGENT_SESSION_COUPLED_ACCEPTANCE=1 \
AGENT_SESSION_SOURCE_BIN="$SOURCE_BIN" \
PYTHONDONTWRITEBYTECODE=1 \
  python3 "$ROOT/tests/hooks/test_shared_hooks.py" \
    --tests test_session_coordination_source_linked_cross_product_acceptance
