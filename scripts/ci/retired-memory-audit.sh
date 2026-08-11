#!/usr/bin/env bash
# Audit memory scopes for references derived from retired runtime-kit skill IDs.
# Compatible with macOS Bash 3.2 and Linux Bash.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$REPO_ROOT/manifests/retired-skill-ids.json"
STORE="${AGENT_MEMORY_HOME:-}"
SELF_TEST=0
OUT_ROOT="${AGENT_RUNTIME_MEMORY_AUDIT_OUT:-}"

usage() {
  cat <<'USAGE'
Usage: scripts/ci/retired-memory-audit.sh [--store <path>] [--self-test]

Options:
  --store <path>  Memory store root. Defaults to AGENT_MEMORY_HOME.
  --self-test     Exercise one synthetic failing store and one clean store.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --store)
      STORE="${2:-}"
      shift 2
      ;;
    --self-test)
      SELF_TEST=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "retired-memory-audit: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

command -v agent-memory >/dev/null 2>&1 || {
  echo "retired-memory-audit: agent-memory is required" >&2
  exit 127
}
command -v python3 >/dev/null 2>&1 || {
  echo "retired-memory-audit: python3 is required" >&2
  exit 127
}

if [ -z "$OUT_ROOT" ]; then
  if command -v agent-out >/dev/null 2>&1; then
    agent_home="${AGENT_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}"
    OUT_ROOT="$(
      agent-out project --agent-home "$agent_home" --repo "$REPO_ROOT" \
        --topic retired-memory-audit --mkdir --format path
    )"
  else
    OUT_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/out/retired-memory-audit"
    mkdir -p "$OUT_ROOT"
  fi
fi
mkdir -p "$OUT_ROOT"
TERMS_FILE="$OUT_ROOT/retired-memory-terms.txt"

python3 - "$MANIFEST" "$TERMS_FILE" <<'PY'
import json
import pathlib
import sys

manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
terms: set[str] = set()
for skill_id in manifest["skills"]:
    domain, skill = skill_id.split(".", 1)
    terms.update(
        {
            skill_id,
            f"{domain}:{skill}",
            f"core/skills/{domain}/{skill}",
            f"build/codex/plugins/{domain}/skills/{skill}",
            f"build/claude/plugins/{domain}/skills/{skill}",
            f"build/hermes/plugins/{domain}/skills/{skill}",
        }
    )
pathlib.Path(sys.argv[2]).write_text(
    "".join(f"{term}\n" for term in sorted(terms)),
    encoding="utf-8",
)
PY

run_audit() {
  local store="$1"
  local status=0
  AGENT_MEMORY_HOME="$store" agent-memory check global --strict --max-index-bytes 8192 --forbid-terms-file "$TERMS_FILE" || status=$?
  AGENT_MEMORY_HOME="$store" agent-memory check profiles/startup --strict --max-index-bytes 768 --forbid-terms-file "$TERMS_FILE" || status=$?
  return "$status"
}

write_fixture() {
  local root="$1"
  local body="$2"
  mkdir -p "$root/global" "$root/profiles/startup"
  {
    printf '%s\n' '---'
    printf '%s\n' 'name: fixture-memory'
    printf '%s\n' 'description: "Synthetic retired-memory audit fixture"'
    printf '%s\n' 'metadata:'
    printf '%s\n' '  node_type: memory'
    printf '%s\n' '  type: reference'
    printf '%s\n' '  originSessionId: 00000000-0000-0000-0000-000000000000'
    printf '%s\n' '---'
    printf '%s\n' "$body"
  } >"$root/global/fixture-memory.md"
  printf '%s\n' '- [Fixture memory](fixture-memory.md) — synthetic audit fixture' >"$root/global/MEMORY.md"
  printf '%s\n' '- [Fixture memory](../../global/fixture-memory.md) — synthetic startup route' >"$root/profiles/startup/MEMORY.md"
}

write_startup_budget_fixture() {
  local root="$1"
  local size="$2"
  write_fixture "$root" 'Current memory contains no retired runtime surface.'
  python3 - "$root/profiles/startup/MEMORY.md" "$size" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
size = int(sys.argv[2])
content = path.read_bytes()
if len(content) > size:
    raise SystemExit(f"startup fixture base exceeds requested size: {len(content)} > {size}")
path.write_bytes(content + b" " * (size - len(content)))
PY
}

if [ "$SELF_TEST" -eq 1 ]; then
  fixture_root="$OUT_ROOT/self-test"
  bad_store="$fixture_root/bad"
  clean_store="$fixture_root/clean"
  boundary_store="$fixture_root/startup-768"
  oversized_store="$fixture_root/startup-769"
  rm -rf "$fixture_root"
  write_fixture "$bad_store" 'Retired reference: browser.browser-session'
  write_fixture "$clean_store" 'Current memory contains no retired runtime surface.'
  write_startup_budget_fixture "$boundary_store" 768
  write_startup_budget_fixture "$oversized_store" 769

  if run_audit "$bad_store" >"$OUT_ROOT/self-test-bad.txt" 2>&1; then
    echo "retired-memory-audit: failing fixture unexpectedly passed" >&2
    exit 1
  fi
  grep -q 'forbidden-term' "$OUT_ROOT/self-test-bad.txt"
  run_audit "$clean_store" >"$OUT_ROOT/self-test-clean.txt" 2>&1
  run_audit "$boundary_store" >"$OUT_ROOT/self-test-startup-768.txt" 2>&1
  if run_audit "$oversized_store" >"$OUT_ROOT/self-test-startup-769.txt" 2>&1; then
    echo "retired-memory-audit: oversized startup fixture unexpectedly passed" >&2
    exit 1
  fi
  grep -q 'index-byte-budget-exceeded' "$OUT_ROOT/self-test-startup-769.txt"
  echo "retired-memory-audit: self-test passed"
  exit 0
fi

if [ -z "$STORE" ]; then
  echo "retired-memory-audit: --store or AGENT_MEMORY_HOME is required" >&2
  exit 2
fi

run_audit "$STORE"
echo "retired-memory-audit: global and startup scopes are clean"
