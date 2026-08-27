#!/usr/bin/env bash
# scripts/ci/sandbox-install-rehearsal.sh — CI gate sandbox install rehearsal.
#
# Uses `agent-runtime list-skills --format json` (cli.agent-runtime.list-skills.v1)
# as the preferred source of truth for the per-product skill list, then diffs
# against the committed `tests/sandbox/<product>/expected-skills.txt` pin. Falls
# back to the dry-run-text parser when `list-skills` is unavailable or returns an
# empty product result, so this script keeps working against released binaries
# whose list-skills surface predates Codex plugin-scoped discovery.
#
# It also diffs the installed reviewer subagent surfaces (the `agents-tree`
# link-map entry, parsed from the dry-run plan) against the committed
# `tests/sandbox/<product>/expected-agents.txt` pin, so a missing or renamed
# reviewer agent fails the gate in both product homes.
#
# The two products install that entry differently on purpose. Claude reads a
# symlinked `~/.claude/agents/<name>.md` fine, so it keeps `recursive: true`
# and one symlink per profile. codex-cli refuses to dispatch a profile whose
# directory entry is a symlink even though it still advertises that identity in
# the `spawn_agent` `agent_type` schema (sympoies/agent-runtime-kit#58), so
# Codex installs `$CODEX_HOME/agents` as a single directory symlink and every
# leaf stays a regular file. This gate pins that shape per product: a Codex
# plan that reverts to per-profile symlinks fails here instead of shipping an
# advertised-but-undispatchable reviewer.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/agent-runtime-kit-sandbox.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

cd "$REPO_ROOT"

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "sandbox-install-rehearsal.sh: required binary not on PATH: $bin" >&2
    exit 127
  fi
}

validate_expected_file() {
  local expected="$1"
  local sorted="$TMP_ROOT/expected.sorted"
  if [ ! -s "$expected" ]; then
    echo "sandbox-install-rehearsal.sh: expected skill pin missing or empty: $expected" >&2
    exit 1
  fi
  if grep -n '^$' "$expected" >/tmp/sandbox-install-empty-lines.txt 2>&1; then
    echo "sandbox-install-rehearsal.sh: blank line(s) in $expected:" >&2
    cat /tmp/sandbox-install-empty-lines.txt >&2
    exit 1
  fi
  sort -u "$expected" >"$sorted"
  if ! diff -u "$expected" "$sorted" >/tmp/sandbox-install-expected-sort.diff 2>&1; then
    echo "sandbox-install-rehearsal.sh: expected skill pin is not sorted/unique: $expected" >&2
    cat /tmp/sandbox-install-expected-sort.diff >&2
    exit 1
  fi
}

# Probe whether the installed agent-runtime exposes the `list-skills`
# subcommand. Returns 0 when available, 1 otherwise. This keeps the
# rehearsal compatible with pre-0.22.0 binaries during release rollout.
has_list_skills() {
  agent-runtime list-skills --help >/dev/null 2>&1
}

extract_skill_ids_via_list_skills() {
  local product="$1"
  local out="$2"
  local live_home="$3"
  require_bin jq
  agent-runtime list-skills \
    --source-root "$REPO_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --format json \
    >"$TMP_ROOT/${product}.list-skills.json"
  jq -r '.skills[].id' "$TMP_ROOT/${product}.list-skills.json" | sort -u >"$out"
}

extract_skill_ids_via_dry_run_regex() {
  local product="$1"
  local dry_run_output="$2"
  local out="$3"

  case "$product" in
    codex)
      sed -n 's#.*plugins/\([^/][^/]*\)/skills/\([^/][^/]*\)/SKILL\.md.*#\1.\2#p' "$dry_run_output" | sort -u >"$out"
      ;;
    *)
      sed -n 's#.*plugins/\([^/][^/]*\)/skills/\([^/][^/]*\)/SKILL\.md.*#\1.\2#p' "$dry_run_output" | sort -u >"$out"
      ;;
  esac
}

# Capture the per-profile `agents-tree` symlinks a plan installs, one agent
# name per line (basename without the product-specific .toml / .md extension).
extract_agent_leaf_symlinks() {
  local dry_run_output="$1"
  local out="$2"
  sed -n 's#.*/agents/\([^/]*\)\.[a-z][a-z]* -> .*(agents-tree)#\1#p' "$dry_run_output" | sort -u >"$out"
}

# Codex must install `agents` as ONE directory symlink into the rendered
# `build/codex/agents` tree. Per-profile symlinks are the sympoies/agent-runtime-kit#58
# regression: codex-cli advertises each `agent_type` from the directory listing
# but refuses to dispatch a profile whose directory entry is itself a symlink.
assert_codex_agents_directory_symlink() {
  local dry_run_output="$1"
  local live_home="$2"
  local leaf_symlinks="$TMP_ROOT/codex.leaf-agent-symlinks.txt"

  extract_agent_leaf_symlinks "$dry_run_output" "$leaf_symlinks"
  if [ -s "$leaf_symlinks" ]; then
    echo "sandbox-install-rehearsal.sh: codex installed per-profile agent symlinks; codex-cli advertises but cannot dispatch those identities (agent-runtime-kit#58). Use a single directory symlink (drop \`recursive: true\` from the codex \`agents-tree\` entry). Offending profiles:" >&2
    cat "$leaf_symlinks" >&2
    exit 1
  fi

  if ! grep -Fq "directory symlink $live_home/agents -> $REPO_ROOT/build/codex/agents (agents-tree)" "$dry_run_output"; then
    echo "sandbox-install-rehearsal.sh: codex plan did not install \`agents\` as one directory symlink into build/codex/agents (agents-tree)" >&2
    grep -F "(agents-tree)" "$dry_run_output" >&2 || true
    exit 1
  fi
}

# Reviewer names a product actually exposes. Claude installs one symlink per
# profile, so its plan lists them. Codex links the whole directory, so the
# exposed set is exactly the rendered tree the directory symlink points at.
extract_agent_names() {
  local product="$1"
  local dry_run_output="$2"
  local out="$3"

  if [ "$product" = "codex" ]; then
    # `-printf` is GNU-only; BSD find rejects it, and `2>/dev/null` plus
    # `pipefail` turned that into a silent `set -e` abort on macOS. `-print`
    # with the directory prefix stripped is portable and says the same thing.
    find "$REPO_ROOT/build/codex/agents" -maxdepth 1 -type f -name '*.toml' -print 2>/dev/null |
      sed -e 's#^.*/##' -e 's#\.toml$##' | sort -u >"$out"
    return 0
  fi
  extract_agent_leaf_symlinks "$dry_run_output" "$out"
}

run_product() {
  local product="$1"
  # Whether this product installs reviewer subagents (`agents-tree`). Hermes
  # ships none (subagent-definitions is not-applicable), so it is invoked with
  # 0 and must produce zero agent surfaces.
  local expect_agents="${2:-1}"
  local expected="tests/sandbox/${product}/expected-skills.txt"
  local live_home="$TMP_ROOT/${product}-home"
  local state_home="$TMP_ROOT/state/${product}"
  local dry_run_output="$TMP_ROOT/${product}.dry-run.txt"
  local observed="$TMP_ROOT/${product}.observed-skills.txt"

  validate_expected_file "$expected"

  echo "sandbox install rehearsal: $product"
  if ! agent-runtime install \
    --source-root "$REPO_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --dry-run >"$dry_run_output" 2>&1; then
    echo "sandbox-install-rehearsal.sh: dry-run install failed for $product" >&2
    cat "$dry_run_output" >&2
    exit 1
  fi

  if [[ "${USE_LIST_SKILLS:-1}" = "1" ]] && has_list_skills; then
    extract_skill_ids_via_list_skills "$product" "$observed" "$live_home"
    if [ ! -s "$observed" ]; then
      extract_skill_ids_via_dry_run_regex "$product" "$dry_run_output" "$observed"
    fi
  else
    extract_skill_ids_via_dry_run_regex "$product" "$dry_run_output" "$observed"
  fi

  if [ ! -s "$observed" ]; then
    echo "sandbox-install-rehearsal.sh: no SKILL.md surfaces found in dry-run output for $product" >&2
    cat "$dry_run_output" >&2
    exit 1
  fi

  if ! diff -u "$expected" "$observed" >/tmp/sandbox-install-"${product}".diff 2>&1; then
    echo "sandbox-install-rehearsal.sh: skill pin mismatch for $product:" >&2
    cat /tmp/sandbox-install-"${product}".diff >&2
    exit 1
  fi

  # Reviewer subagent surfaces: the `agents-tree` link-map entry. Claude
  # installs one symlink per profile; Codex installs the directory itself.
  local observed_agents="$TMP_ROOT/${product}.observed-agents.txt"
  if [ "$product" = "codex" ]; then
    assert_codex_agents_directory_symlink "$dry_run_output" "$live_home"
  fi
  extract_agent_names "$product" "$dry_run_output" "$observed_agents"

  if [ "$expect_agents" = "0" ]; then
    # Products without an `agents-tree` (e.g. Hermes) must install no reviewer
    # agents; a surface appearing here is an unexpected regression.
    if [ -s "$observed_agents" ]; then
      echo "sandbox-install-rehearsal.sh: $product ships no reviewer agents but the dry-run installed:" >&2
      cat "$observed_agents" >&2
      exit 1
    fi
    return 0
  fi

  local expected_agents="tests/sandbox/${product}/expected-agents.txt"
  validate_expected_file "$expected_agents"
  if [ ! -s "$observed_agents" ]; then
    echo "sandbox-install-rehearsal.sh: no reviewer agent surfaces found in dry-run output for $product" >&2
    cat "$dry_run_output" >&2
    exit 1
  fi
  if ! diff -u "$expected_agents" "$observed_agents" >/tmp/sandbox-install-"${product}"-agents.diff 2>&1; then
    echo "sandbox-install-rehearsal.sh: reviewer agent pin mismatch for $product:" >&2
    cat /tmp/sandbox-install-"${product}"-agents.diff >&2
    exit 1
  fi
}

require_bin agent-runtime

run_product claude
run_product codex
run_product hermes 0

echo "sandbox-install-rehearsal.sh: OK"
