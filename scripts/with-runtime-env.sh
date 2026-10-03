#!/usr/bin/env bash
# The same environment owner wraps Codex, Claude, Hermes, and session launchers.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rendered="$(bash "$root/scripts/render-runtime-env.sh")"
eval "$rendered" # Renderer emits only a fixed no-op or a fixed export.
exec "$@"
