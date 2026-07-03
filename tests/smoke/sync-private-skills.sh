#!/usr/bin/env bash
# Offline smoke coverage for scripts/sync-private-skills.sh.
#
# Exercises the private-skill overlay against throwaway HOME/CODEX_HOME roots:
# codex/claude per-skill symlinks, the presence-gated hermes external-skills
# overlay, the hermes config registration hint, prune, and collision refusal.
# No network, no real runtime homes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/sync-private-skills.sh"

ARTIFACTS_DIR="${ARTIFACTS_DIR:-${CLAUDE_KIT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/out/tests/sync-private-skills-smoke}"
rm -rf "$ARTIFACTS_DIR"
mkdir -p "$ARTIFACTS_DIR"

FAILURES=0

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  FAILURES=$((FAILURES + 1))
}

pass() {
  printf 'ok: %s\n' "$*"
}

make_private_home() {
  local root="$1"
  local name
  shift
  for name in "$@"; do
    mkdir -p "$root/.agents/skills/$name"
    cat >"$root/.agents/skills/$name/SKILL.md" <<EOF
---
name: $name
description: smoke fixture skill $name
---

# $name
EOF
  done
}

run_sync() {
  local home="$1"
  shift
  env -u AGENT_PRIVATE_SKILLS_HOME -u CODEX_HOME HOME="$home" \
    bash "$SCRIPT" "$@"
}

# ── Case 1: hermes host — apply links codex + claude + hermes ─────────────
CASE1="$ARTIFACTS_DIR/case1"
PRIV1="$CASE1/private"
HOME1="$CASE1/home"
make_private_home "$PRIV1" private-alpha private-beta
mkdir -p "$HOME1/.hermes"

OUT1="$(run_sync "$HOME1" --private-home "$PRIV1" --apply 2>&1)" ||
  fail "case1: apply run exited non-zero: $OUT1"

for product_dir in \
  "$HOME1/.codex/skills" \
  "$HOME1/.claude/skills" \
  "$HOME1/.hermes/external-skills/private"; do
  for name in private-alpha private-beta; do
    if [ -L "$product_dir/$name" ] &&
      [ -f "$product_dir/$name/SKILL.md" ]; then
      pass "case1: $product_dir/$name overlay symlink resolves"
    else
      fail "case1: expected overlay symlink at $product_dir/$name"
    fi
  done
done

# The hermes overlay must warn when no hermes config registers the
# external-skills root.
if printf '%s' "$OUT1" | grep -q "external_dirs"; then
  pass "case1: unregistered hermes config produces external_dirs hint"
else
  fail "case1: missing external_dirs registration hint in output: $OUT1"
fi

# ── Case 2: registered hermes config — no hint ────────────────────────────
cat >"$HOME1/.hermes/config.yaml" <<EOF
skills:
  external_dirs:
    - ~/.hermes/external-skills
EOF
OUT2="$(run_sync "$HOME1" --private-home "$PRIV1" --apply 2>&1)" ||
  fail "case2: re-apply run exited non-zero: $OUT2"
if printf '%s' "$OUT2" | grep -q "external_dirs:"; then
  fail "case2: hint still printed after config registration: $OUT2"
else
  pass "case2: registered config suppresses external_dirs hint"
fi

# ── Case 3: prune removes stale overlays in every product ─────────────────
rm -rf "$PRIV1/.agents/skills/private-beta"
OUT3="$(run_sync "$HOME1" --private-home "$PRIV1" --apply --prune 2>&1)" ||
  fail "case3: prune run exited non-zero: $OUT3"
for product_dir in \
  "$HOME1/.codex/skills" \
  "$HOME1/.claude/skills" \
  "$HOME1/.hermes/external-skills/private"; do
  if [ -e "$product_dir/private-beta" ] || [ -L "$product_dir/private-beta" ]; then
    fail "case3: stale overlay survived prune at $product_dir/private-beta"
  else
    pass "case3: stale overlay pruned from $product_dir"
  fi
  if [ -L "$product_dir/private-alpha" ]; then
    pass "case3: live overlay kept at $product_dir/private-alpha"
  else
    fail "case3: live overlay missing after prune at $product_dir/private-alpha"
  fi
done

# ── Case 4: host without ~/.hermes — default run skips hermes ─────────────
CASE4="$ARTIFACTS_DIR/case4"
PRIV4="$CASE4/private"
HOME4="$CASE4/home"
make_private_home "$PRIV4" private-alpha
mkdir -p "$HOME4"

OUT4="$(run_sync "$HOME4" --private-home "$PRIV4" --apply 2>&1)" ||
  fail "case4: apply run exited non-zero: $OUT4"
if [ -e "$HOME4/.hermes" ]; then
  fail "case4: default run created ~/.hermes on a hermes-less host"
else
  pass "case4: hermes-less host untouched by default product set"
fi
if [ -L "$HOME4/.claude/skills/private-alpha" ]; then
  pass "case4: claude overlay still applied on hermes-less host"
else
  fail "case4: claude overlay missing on hermes-less host"
fi

# ── Case 5: explicit --product hermes without ~/.hermes fails loudly ──────
if OUT5="$(run_sync "$HOME4" --private-home "$PRIV4" --apply --product hermes 2>&1)"; then
  fail "case5: explicit --product hermes succeeded without ~/.hermes: $OUT5"
else
  pass "case5: explicit --product hermes fails without ~/.hermes"
fi

# ── Case 6: collision refusal — foreign dir at hermes target survives ─────
CASE6="$ARTIFACTS_DIR/case6"
PRIV6="$CASE6/private"
HOME6="$CASE6/home"
make_private_home "$PRIV6" private-alpha
mkdir -p "$HOME6/.hermes/external-skills/private/private-alpha"
touch "$HOME6/.hermes/external-skills/private/private-alpha/keep"

OUT6="$(run_sync "$HOME6" --private-home "$PRIV6" --apply 2>&1)" ||
  fail "case6: apply run exited non-zero: $OUT6"
if [ -L "$HOME6/.hermes/external-skills/private/private-alpha" ]; then
  fail "case6: foreign directory clobbered by hermes overlay"
elif [ -f "$HOME6/.hermes/external-skills/private/private-alpha/keep" ]; then
  pass "case6: foreign directory at hermes target left intact"
else
  fail "case6: foreign directory contents lost"
fi
if printf '%s' "$OUT6" | grep -q "collision \[hermes\]"; then
  pass "case6: collision reported for hermes product"
else
  fail "case6: expected hermes collision report in output: $OUT6"
fi

# ── Summary ────────────────────────────────────────────────────────────────
if [ "$FAILURES" -gt 0 ]; then
  printf '%s failure(s)\n' "$FAILURES" >&2
  exit 1
fi
printf 'sync-private-skills smoke: all cases passed\n'
