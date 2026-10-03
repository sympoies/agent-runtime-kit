#!/usr/bin/env bash
# Structural validation belongs to devlog, including pending fragments.
set -euo pipefail
if [ ! -f docs/devlog/README.md ] && [ ! -f docs/source/devlog/README.md ]; then
  exit 0
fi
if [ -n "${DEVLOG_CHECK_BASE:-}" ]; then
  exec devlog check --base "$DEVLOG_CHECK_BASE" "$@"
fi
exec devlog check "$@"
