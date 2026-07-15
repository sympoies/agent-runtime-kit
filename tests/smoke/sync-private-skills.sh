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

set_skill_products() {
  local private_home="$1"
  local name="$2"
  shift 2
  mkdir -p "$private_home/.agents/skills/$name/agents"
  if [ "$#" -eq 0 ]; then
    : >"$private_home/.agents/skills/$name/agents/products.txt"
    return
  fi
  printf '%s\n' "$@" >"$private_home/.agents/skills/$name/agents/products.txt"
}

run_sync() {
  local home="$1"
  shift
  env -u AGENT_PRIVATE_SKILLS_HOME -u CODEX_HOME HOME="$home" \
    bash "$SCRIPT" "$@"
}

# Capture one complete tree with path kinds and symlink targets. The overlay
# mutates only directories and symlinks, so exact snapshot equality proves that
# fail-closed validation did not create, refresh, prune, or redirect anything.
snapshot_tree() {
  local root="$1"
  local label="$2"
  local path suffix relative_path

  if [ ! -e "$root" ] && [ ! -L "$root" ]; then
    return 0
  fi
  find "$root" -print | LC_ALL=C sort | while IFS= read -r path; do
    suffix="${path#"$root"}"
    suffix="${suffix#/}"
    relative_path="$label"
    [ -n "$suffix" ] && relative_path="$label/$suffix"
    if [ -L "$path" ]; then
      printf 'link\t%s\t%s\n' "$relative_path" "$(readlink "$path")"
    elif [ -d "$path" ]; then
      printf 'dir\t%s\n' "$relative_path"
    elif [ -f "$path" ]; then
      printf 'file\t%s\n' "$relative_path"
    else
      printf 'other\t%s\n' "$relative_path"
    fi
  done
}

snapshot_runtime_home() {
  local home="$1"
  local relative_root

  for relative_root in .codex .claude .hermes; do
    snapshot_tree "$home/$relative_root" "$relative_root"
  done
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

# ── Case 7: per-skill products metadata narrows only that skill ───────────
CASE7="$ARTIFACTS_DIR/case7"
PRIV7="$CASE7/private"
HOME7="$CASE7/home"
make_private_home "$PRIV7" private-alpha private-beta
set_skill_products "$PRIV7" private-alpha hermes
mkdir -p "$HOME7/.hermes"

OUT7="$(run_sync "$HOME7" --private-home "$PRIV7" --apply 2>&1)" ||
  fail "case7: targeted apply exited non-zero: $OUT7"

if [ -L "$HOME7/.hermes/external-skills/private/private-alpha" ] &&
  [ ! -e "$HOME7/.codex/skills/private-alpha" ] &&
  [ ! -L "$HOME7/.codex/skills/private-alpha" ] &&
  [ ! -e "$HOME7/.claude/skills/private-alpha" ] &&
  [ ! -L "$HOME7/.claude/skills/private-alpha" ]; then
  pass "case7: hermes-only skill linked only into hermes"
else
  fail "case7: hermes-only skill leaked into another product: $OUT7"
fi
for product_dir in \
  "$HOME7/.codex/skills" \
  "$HOME7/.claude/skills" \
  "$HOME7/.hermes/external-skills/private"; do
  if [ -L "$product_dir/private-beta" ]; then
    pass "case7: metadata-free skill retained all-product compatibility at $product_dir"
  else
    fail "case7: metadata-free skill missing from $product_dir"
  fi
done

# ── Case 8: every invalid metadata class preserves the exact runtime tree ──
for invalid_kind in unknown unknown-no-newline empty duplicate blank-line symlink directory; do
  for operation in apply apply-prune; do
    CASE8="$ARTIFACTS_DIR/case8-$invalid_kind-$operation"
    PRIV8="$CASE8/private"
    HOME8="$CASE8/home"
    FOREIGN8="$CASE8/foreign/private-foreign"
    make_private_home "$PRIV8" private-alpha private-beta
    set_skill_products "$PRIV8" private-alpha codex
    case "$invalid_kind" in
      unknown) set_skill_products "$PRIV8" private-beta codex vscode ;;
      unknown-no-newline)
        mkdir -p "$PRIV8/.agents/skills/private-beta/agents"
        printf 'codex\nvscode' \
          >"$PRIV8/.agents/skills/private-beta/agents/products.txt"
        ;;
      empty) set_skill_products "$PRIV8" private-beta ;;
      duplicate) set_skill_products "$PRIV8" private-beta claude claude ;;
      blank-line)
        mkdir -p "$PRIV8/.agents/skills/private-beta/agents"
        printf 'hermes\n\n' >"$PRIV8/.agents/skills/private-beta/agents/products.txt"
        ;;
      symlink)
        mkdir -p "$PRIV8/.agents/skills/private-beta/agents"
        printf 'codex\n' >"$CASE8/products.txt"
        ln -s "$CASE8/products.txt" \
          "$PRIV8/.agents/skills/private-beta/agents/products.txt"
        ;;
      directory)
        mkdir -p "$PRIV8/.agents/skills/private-beta/agents/products.txt"
        printf 'codex\n' \
          >"$PRIV8/.agents/skills/private-beta/agents/products.txt/entry"
        ;;
    esac

    mkdir -p \
      "$HOME8/.codex/skills/private-neighbor" \
      "$HOME8/.claude/skills" \
      "$HOME8/.hermes/external-skills/private" \
      "$FOREIGN8"
    printf 'keep\n' >"$HOME8/.codex/skills/private-neighbor/keep"
    for product_dir in \
      "$HOME8/.codex/skills" \
      "$HOME8/.claude/skills" \
      "$HOME8/.hermes/external-skills/private"; do
      ln -s "$PRIV8/.agents/skills/private-alpha" "$product_dir/private-alpha"
      ln -s "$PRIV8/.agents/skills/private-stale" "$product_dir/private-stale"
      ln -s "$FOREIGN8" "$product_dir/private-foreign"
    done

    BEFORE8="$(snapshot_runtime_home "$HOME8")"
    if [ "$operation" = "apply-prune" ]; then
      if OUT8="$(run_sync "$HOME8" --private-home "$PRIV8" --apply --prune 2>&1)"; then
        fail "case8-$invalid_kind-$operation: invalid products metadata succeeded: $OUT8"
      else
        pass "case8-$invalid_kind-$operation: invalid products metadata failed closed"
      fi
    elif OUT8="$(run_sync "$HOME8" --private-home "$PRIV8" --apply 2>&1)"; then
      fail "case8-$invalid_kind-$operation: invalid products metadata succeeded: $OUT8"
    else
      pass "case8-$invalid_kind-$operation: invalid products metadata failed closed"
    fi
    AFTER8="$(snapshot_runtime_home "$HOME8")"
    if [ "$AFTER8" = "$BEFORE8" ]; then
      pass "case8-$invalid_kind-$operation: exact runtime-home tree preserved"
    else
      fail "case8-$invalid_kind-$operation: runtime-home tree changed\nbefore:\n$BEFORE8\nafter:\n$AFTER8"
    fi
  done
done

# ── Case 9: prune removes owned links from newly excluded products ────────
CASE9="$ARTIFACTS_DIR/case9"
PRIV9="$CASE9/private"
HOME9="$CASE9/home"
make_private_home "$PRIV9" private-alpha
mkdir -p "$HOME9/.hermes"
run_sync "$HOME9" --private-home "$PRIV9" --apply >/dev/null
set_skill_products "$PRIV9" private-alpha hermes

OUT9="$(run_sync "$HOME9" --private-home "$PRIV9" --apply --prune 2>&1)" ||
  fail "case9: selective prune exited non-zero: $OUT9"
if [ ! -e "$HOME9/.codex/skills/private-alpha" ] &&
  [ ! -L "$HOME9/.codex/skills/private-alpha" ] &&
  [ ! -e "$HOME9/.claude/skills/private-alpha" ] &&
  [ ! -L "$HOME9/.claude/skills/private-alpha" ] &&
  [ -L "$HOME9/.hermes/external-skills/private/private-alpha" ]; then
  pass "case9: selective prune converged owned links to products metadata"
else
  fail "case9: selective prune left an excluded owned link: $OUT9"
fi

# ── Case 10: invalid metadata blocks prune of existing owned links ────────
CASE10="$ARTIFACTS_DIR/case10"
PRIV10="$CASE10/private"
HOME10="$CASE10/home"
make_private_home "$PRIV10" private-alpha private-beta
mkdir -p "$HOME10/.hermes"
run_sync "$HOME10" --private-home "$PRIV10" --apply >/dev/null
rm -rf "$PRIV10/.agents/skills/private-beta"
set_skill_products "$PRIV10" private-alpha codex invalid-product

if OUT10="$(run_sync "$HOME10" --private-home "$PRIV10" --apply --prune 2>&1)"; then
  fail "case10: invalid metadata allowed prune: $OUT10"
else
  pass "case10: invalid metadata blocked prune"
fi
for product_dir in \
  "$HOME10/.codex/skills" \
  "$HOME10/.claude/skills" \
  "$HOME10/.hermes/external-skills/private"; do
  if [ -L "$product_dir/private-beta" ]; then
    pass "case10: fail-closed validation preserved pre-existing link at $product_dir"
  else
    fail "case10: invalid metadata pruned pre-existing link at $product_dir"
  fi
done

# ── Case 11: foreign symlinks survive targeting and prune ─────────────────
CASE11="$ARTIFACTS_DIR/case11"
PRIV11="$CASE11/private"
HOME11="$CASE11/home"
FOREIGN11="$CASE11/foreign/private-alpha"
make_private_home "$PRIV11" private-alpha
set_skill_products "$PRIV11" private-alpha hermes
mkdir -p "$HOME11/.hermes" "$HOME11/.codex/skills" "$FOREIGN11"
ln -s "$FOREIGN11" "$HOME11/.codex/skills/private-alpha"

OUT11="$(run_sync "$HOME11" --private-home "$PRIV11" --apply --prune 2>&1)" ||
  fail "case11: foreign-link apply exited non-zero: $OUT11"
if [ -L "$HOME11/.codex/skills/private-alpha" ] &&
  [ "$(readlink "$HOME11/.codex/skills/private-alpha")" = "$FOREIGN11" ]; then
  pass "case11: foreign symlink survived selective prune"
else
  fail "case11: foreign symlink was replaced or removed"
fi
if [ ! -e "$HOME11/.claude/skills/private-alpha" ] &&
  [ ! -L "$HOME11/.claude/skills/private-alpha" ] &&
  [ -L "$HOME11/.hermes/external-skills/private/private-alpha" ]; then
  pass "case11: foreign collision did not widen targeted product exposure"
else
  fail "case11: targeted skill leaked while preserving foreign link: $OUT11"
fi

# ── Case 12: retained source without SKILL.md is pruned ownership-safely ──
CASE12="$ARTIFACTS_DIR/case12"
PRIV12="$CASE12/private"
HOME12="$CASE12/home"
FOREIGN12="$CASE12/foreign/private-foreign"
make_private_home "$PRIV12" private-live
mkdir -p \
  "$PRIV12/.agents/skills/private-retained" \
  "$HOME12/.codex/skills" \
  "$HOME12/.claude/skills" \
  "$HOME12/.hermes/external-skills/private" \
  "$FOREIGN12"
for product_dir in \
  "$HOME12/.codex/skills" \
  "$HOME12/.claude/skills" \
  "$HOME12/.hermes/external-skills/private"; do
  ln -s "$PRIV12/.agents/skills/private-retained" \
    "$product_dir/private-retained"
  ln -s "$FOREIGN12" "$product_dir/private-foreign"
done

OUT12="$(run_sync "$HOME12" --private-home "$PRIV12" \
  --product all --apply --prune 2>&1)" ||
  fail "case12: retained-source prune exited non-zero: $OUT12"
for product_dir in \
  "$HOME12/.codex/skills" \
  "$HOME12/.claude/skills" \
  "$HOME12/.hermes/external-skills/private"; do
  if [ -e "$product_dir/private-retained" ] ||
    [ -L "$product_dir/private-retained" ]; then
    fail "case12: missing-SKILL.md owned overlay survived at $product_dir"
  else
    pass "case12: missing-SKILL.md owned overlay pruned from $product_dir"
  fi
  if [ -L "$product_dir/private-foreign" ] &&
    [ "$(readlink "$product_dir/private-foreign")" = "$FOREIGN12" ]; then
    pass "case12: foreign neighbor preserved at $product_dir"
  else
    fail "case12: foreign neighbor changed at $product_dir"
  fi
  if [ -L "$product_dir/private-live" ]; then
    pass "case12: valid selected-product overlay retained at $product_dir"
  else
    fail "case12: valid selected-product overlay missing at $product_dir: $OUT12"
  fi
done

# ── Case 13: same-private-home wrong-target links remain operator-owned ──
CASE13="$ARTIFACTS_DIR/case13"
PRIV13="$CASE13/private"
HOME13="$CASE13/home"
OPERATOR13="$PRIV13/operator-notes"
make_private_home "$PRIV13" private-alpha
mkdir -p "$HOME13/.hermes" "$HOME13/.codex/skills" "$OPERATOR13"
ln -s "$OPERATOR13" "$HOME13/.codex/skills/private-alpha"

OUT13_APPLY="$(run_sync "$HOME13" --private-home "$PRIV13" --apply 2>&1)" ||
  fail "case13: wrong-target apply exited non-zero: $OUT13_APPLY"
if [ -L "$HOME13/.codex/skills/private-alpha" ] &&
  [ "$(readlink "$HOME13/.codex/skills/private-alpha")" = "$OPERATOR13" ]; then
  pass "case13: refresh preserved same-private-home wrong-target symlink"
else
  fail "case13: refresh replaced same-private-home wrong-target symlink"
fi
if [ -L "$HOME13/.claude/skills/private-alpha" ] &&
  [ -L "$HOME13/.hermes/external-skills/private/private-alpha" ]; then
  pass "case13: non-colliding products received the expected overlay"
else
  fail "case13: collision prevented valid product overlays: $OUT13_APPLY"
fi

set_skill_products "$PRIV13" private-alpha hermes
OUT13_PRUNE="$(run_sync "$HOME13" --private-home "$PRIV13" --apply --prune 2>&1)" ||
  fail "case13: wrong-target prune exited non-zero: $OUT13_PRUNE"
if [ -L "$HOME13/.codex/skills/private-alpha" ] &&
  [ "$(readlink "$HOME13/.codex/skills/private-alpha")" = "$OPERATOR13" ]; then
  pass "case13: prune preserved same-private-home wrong-target symlink"
else
  fail "case13: prune removed same-private-home wrong-target symlink"
fi
if [ ! -e "$HOME13/.claude/skills/private-alpha" ] &&
  [ ! -L "$HOME13/.claude/skills/private-alpha" ] &&
  [ -L "$HOME13/.hermes/external-skills/private/private-alpha" ]; then
  pass "case13: prune converged only exact-source owned overlays"
else
  fail "case13: exact-source product convergence failed: $OUT13_PRUNE"
fi

# ── Case 14: final metadata line without newline is retained ─────────────
CASE14="$ARTIFACTS_DIR/case14"
PRIV14="$CASE14/private"
HOME14="$CASE14/home"
make_private_home "$PRIV14" private-alpha
mkdir -p "$PRIV14/.agents/skills/private-alpha/agents" "$HOME14/.hermes"
printf 'codex\nhermes' \
  >"$PRIV14/.agents/skills/private-alpha/agents/products.txt"

OUT14="$(run_sync "$HOME14" --private-home "$PRIV14" --apply 2>&1)" ||
  fail "case14: no-final-newline apply exited non-zero: $OUT14"
if [ -L "$HOME14/.codex/skills/private-alpha" ] &&
  [ -L "$HOME14/.hermes/external-skills/private/private-alpha" ] &&
  [ ! -e "$HOME14/.claude/skills/private-alpha" ] &&
  [ ! -L "$HOME14/.claude/skills/private-alpha" ]; then
  pass "case14: final metadata line without newline retained its product"
else
  fail "case14: final metadata line without newline was dropped: $OUT14"
fi

# ── Case 15: private source escapes fail closed before apply or prune ─────
for escape_kind in source-root parent-component skill-directory skill-file; do
  for operation in apply apply-prune; do
    CASE15="$ARTIFACTS_DIR/case15-$escape_kind-$operation"
    PRIV15="$CASE15/private"
    EXTERNAL15="$CASE15/external"
    HOME15="$CASE15/home"
    FOREIGN15="$CASE15/foreign/private-foreign"
    make_private_home "$EXTERNAL15" private-escape

    case "$escape_kind" in
      source-root)
        mkdir -p "$PRIV15/.agents"
        ln -s "$EXTERNAL15/.agents/skills" "$PRIV15/.agents/skills"
        ;;
      parent-component)
        mkdir -p "$PRIV15"
        ln -s "$EXTERNAL15/.agents" "$PRIV15/.agents"
        ;;
      skill-directory)
        mkdir -p "$PRIV15/.agents/skills"
        ln -s "$EXTERNAL15/.agents/skills/private-escape" \
          "$PRIV15/.agents/skills/private-escape"
        ;;
      skill-file)
        make_private_home "$PRIV15" private-escape
        rm "$PRIV15/.agents/skills/private-escape/SKILL.md"
        ln -s "$EXTERNAL15/.agents/skills/private-escape/SKILL.md" \
          "$PRIV15/.agents/skills/private-escape/SKILL.md"
        ;;
    esac

    mkdir -p \
      "$HOME15/.codex/skills/private-neighbor" \
      "$HOME15/.claude/skills" \
      "$HOME15/.hermes/external-skills/private" \
      "$FOREIGN15"
    printf 'keep\n' >"$HOME15/.codex/skills/private-neighbor/keep"
    for product_dir in \
      "$HOME15/.codex/skills" \
      "$HOME15/.claude/skills" \
      "$HOME15/.hermes/external-skills/private"; do
      ln -s "$PRIV15/.agents/skills/private-stale" \
        "$product_dir/private-stale"
      ln -s "$FOREIGN15" "$product_dir/private-foreign"
    done

    BEFORE15="$(snapshot_runtime_home "$HOME15")"
    if [ "$operation" = "apply-prune" ]; then
      if OUT15="$(run_sync "$HOME15" --private-home "$PRIV15" \
        --apply --prune 2>&1)"; then
        fail "case15-$escape_kind-$operation: source escape succeeded: $OUT15"
      else
        pass "case15-$escape_kind-$operation: source escape rejected"
      fi
    elif OUT15="$(run_sync "$HOME15" --private-home "$PRIV15" --apply 2>&1)"; then
      fail "case15-$escape_kind-$operation: source escape succeeded: $OUT15"
    else
      pass "case15-$escape_kind-$operation: source escape rejected"
    fi
    AFTER15="$(snapshot_runtime_home "$HOME15")"
    if [ "$AFTER15" = "$BEFORE15" ]; then
      pass "case15-$escape_kind-$operation: exact runtime-home tree preserved"
    else
      fail "case15-$escape_kind-$operation: runtime-home tree changed\nbefore:\n$BEFORE15\nafter:\n$AFTER15"
    fi
  done
done

# ── Case 16: subordinate source symlinks fail closed before mutation ──────
for escape_kind in script-file agents-directory; do
  for operation in apply apply-prune; do
    CASE16="$ARTIFACTS_DIR/case16-$escape_kind-$operation"
    PRIV16="$CASE16/private"
    EXTERNAL16="$CASE16/external"
    HOME16="$CASE16/home"
    FOREIGN16="$CASE16/foreign/private-foreign"
    make_private_home "$PRIV16" private-escape
    mkdir -p "$EXTERNAL16"

    case "$escape_kind" in
      script-file)
        mkdir -p "$PRIV16/.agents/skills/private-escape/scripts"
        printf '#!/usr/bin/env bash\n' >"$EXTERNAL16/tool.sh"
        ln -s "$EXTERNAL16/tool.sh" \
          "$PRIV16/.agents/skills/private-escape/scripts/tool.sh"
        ;;
      agents-directory)
        mkdir -p "$EXTERNAL16/agents"
        printf 'interface:\n  display_name: External\n' \
          >"$EXTERNAL16/agents/openai.yaml"
        ln -s "$EXTERNAL16/agents" \
          "$PRIV16/.agents/skills/private-escape/agents"
        ;;
    esac

    mkdir -p \
      "$HOME16/.codex/skills/private-neighbor" \
      "$HOME16/.claude/skills" \
      "$HOME16/.hermes/external-skills/private" \
      "$FOREIGN16"
    printf 'keep\n' >"$HOME16/.codex/skills/private-neighbor/keep"
    for product_dir in \
      "$HOME16/.codex/skills" \
      "$HOME16/.claude/skills" \
      "$HOME16/.hermes/external-skills/private"; do
      ln -s "$PRIV16/.agents/skills/private-stale" \
        "$product_dir/private-stale"
      ln -s "$FOREIGN16" "$product_dir/private-foreign"
    done

    BEFORE16="$(snapshot_runtime_home "$HOME16")"
    if [ "$operation" = "apply-prune" ]; then
      if OUT16="$(run_sync "$HOME16" --private-home "$PRIV16" \
        --apply --prune 2>&1)"; then
        fail "case16-$escape_kind-$operation: subordinate source escape succeeded: $OUT16"
      else
        pass "case16-$escape_kind-$operation: subordinate source escape rejected"
      fi
    elif OUT16="$(run_sync "$HOME16" --private-home "$PRIV16" --apply 2>&1)"; then
      fail "case16-$escape_kind-$operation: subordinate source escape succeeded: $OUT16"
    else
      pass "case16-$escape_kind-$operation: subordinate source escape rejected"
    fi
    AFTER16="$(snapshot_runtime_home "$HOME16")"
    if [ "$AFTER16" = "$BEFORE16" ]; then
      pass "case16-$escape_kind-$operation: exact runtime-home tree preserved"
    else
      fail "case16-$escape_kind-$operation: runtime-home tree changed\nbefore:\n$BEFORE16\nafter:\n$AFTER16"
    fi
  done
done

# ── Case 17: every selected product target root is preflighted atomically ─
for target_product in codex claude hermes; do
  for operation in apply apply-prune; do
    CASE17="$ARTIFACTS_DIR/case17-$target_product-$operation"
    PRIV17="$CASE17/private"
    HOME17="$CASE17/home"
    EXTERNAL17="$CASE17/external-target"
    FOREIGN17="$CASE17/foreign/private-foreign"
    make_private_home "$PRIV17" private-alpha
    mkdir -p \
      "$HOME17/.codex/skills" \
      "$HOME17/.claude/skills" \
      "$HOME17/.hermes/external-skills/private" \
      "$EXTERNAL17" \
      "$FOREIGN17"

    case "$target_product" in
      codex)
        rmdir "$HOME17/.codex/skills"
        ln -s "$EXTERNAL17" "$HOME17/.codex/skills"
        ;;
      claude)
        rmdir "$HOME17/.claude/skills"
        ln -s "$EXTERNAL17" "$HOME17/.claude/skills"
        ;;
      hermes)
        rmdir "$HOME17/.hermes/external-skills/private"
        ln -s "$EXTERNAL17" "$HOME17/.hermes/external-skills/private"
        ;;
    esac

    for product_dir in \
      "$HOME17/.codex/skills" \
      "$HOME17/.claude/skills" \
      "$HOME17/.hermes/external-skills/private"; do
      ln -s "$PRIV17/.agents/skills/private-stale" \
        "$product_dir/private-stale"
      ln -s "$FOREIGN17" "$product_dir/private-foreign"
    done
    printf 'keep\n' >"$EXTERNAL17/keep"

    BEFORE17="$(
      snapshot_runtime_home "$HOME17"
      snapshot_tree "$EXTERNAL17" external-target
    )"
    if [ "$operation" = "apply-prune" ]; then
      if OUT17="$(run_sync "$HOME17" --private-home "$PRIV17" \
        --apply --prune 2>&1)"; then
        fail "case17-$target_product-$operation: symlinked target root succeeded: $OUT17"
      else
        pass "case17-$target_product-$operation: symlinked target root rejected"
      fi
    elif OUT17="$(run_sync "$HOME17" --private-home "$PRIV17" --apply 2>&1)"; then
      fail "case17-$target_product-$operation: symlinked target root succeeded: $OUT17"
    else
      pass "case17-$target_product-$operation: symlinked target root rejected"
    fi
    AFTER17="$(
      snapshot_runtime_home "$HOME17"
      snapshot_tree "$EXTERNAL17" external-target
    )"
    if [ "$AFTER17" = "$BEFORE17" ]; then
      pass "case17-$target_product-$operation: runtime and external trees preserved"
    else
      fail "case17-$target_product-$operation: runtime or external tree changed\nbefore:\n$BEFORE17\nafter:\n$AFTER17"
    fi
  done
done

# ── Summary ───────────────────────────────────────────────────────────────
if [ "$FAILURES" -gt 0 ]; then
  printf '%s failure(s)\n' "$FAILURES" >&2
  exit 1
fi
printf 'sync-private-skills smoke: all cases passed\n'
