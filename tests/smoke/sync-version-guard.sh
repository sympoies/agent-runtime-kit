#!/usr/bin/env bash
# F7-sync behavioral smoke: verify_nils_cli_version_alignment gates a --apply
# sync on the agent-runtime version-alignment doctor. Like the other
# tests/smoke/* sync checks, this is not wired into scripts/ci/all.sh; run it
# manually (see DEVELOPMENT.md). The CI-gated static wiring assertion lives in
# tests/ci/test_nils_cli_version_policy.py.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"

fail() {
  echo "sync-version-guard: FAIL: $1" >&2
  exit 1
}

# Source the sync script as a library: defines helpers without running main.
# shellcheck source=/dev/null
SYNC_RUNTIME_SURFACES_LIB=1 . "$SCRIPT"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# Stub agent-runtime on PATH; its exit code is driven by AR_EXIT.
mkdir -p "$work/bin"
cat >"$work/bin/agent-runtime" <<'STUB'
#!/usr/bin/env bash
exit "${AR_EXIT:-0}"
STUB
chmod +x "$work/bin/agent-runtime"
PATH="$work/bin:$PATH"

# A source root carrying the pin manifest the guard reads.
mkdir -p "$work/root/docs/source"
: >"$work/root/docs/source/nils-cli-pin.yaml"
SOURCE_ROOT="$work/root"

# 1. doctor admits the host -> guard passes.
export AR_EXIT=0
verify_nils_cli_version_alignment >/dev/null 2>&1 ||
  fail "guard rejected an aligned install"

# 2. doctor blocks (below minimum) -> guard fails.
export AR_EXIT=2
if verify_nils_cli_version_alignment >/dev/null 2>&1; then
  fail "guard admitted a below-minimum install"
fi

# 3. pin manifest absent -> guard skips cleanly (does not even call the doctor).
SOURCE_ROOT="$work/empty"
mkdir -p "$SOURCE_ROOT"
export AR_EXIT=2
verify_nils_cli_version_alignment >/dev/null 2>&1 ||
  fail "guard did not skip cleanly when the pin manifest is absent"

echo "sync-version-guard: OK"
