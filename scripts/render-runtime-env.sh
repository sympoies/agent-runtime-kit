#!/usr/bin/env bash
# Render the shared launch environment; source its output before any harness.
# Off deliberately emits no environment mutation, including for older nils-cli.
set -euo pipefail
case "${AGENT_RUNTIME_DEVLOG_FRAGMENTS:-0}" in
  0) printf ':\n' ;;
  1)
    if ! devlog fold --help >/dev/null 2>&1; then
      echo 'Fragment enablement requires released nils-cli >=1.31.14 with devlog fold' >&2
      exit 69
    fi
    printf 'export DEVLOG_LAYOUT=fragments\n'
    ;;
  *) echo 'AGENT_RUNTIME_DEVLOG_FRAGMENTS must be 0 or 1' >&2; exit 64 ;;
esac
