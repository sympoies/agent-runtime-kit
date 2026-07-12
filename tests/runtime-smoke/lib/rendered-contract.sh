#!/usr/bin/env bash
# Assertions shared by deterministic source-to-product contract probes.

rendered_contract_prepare_product() {
  local product="$1"
  local ready_dir="$ARTIFACTS_DIR/rendered-contract"
  local ready_file="$ready_dir/$product.ready"
  local render_log="$ready_dir/$product.render.log"

  if [ -s "$ready_file" ]; then
    return 0
  fi

  mkdir -p "$ready_dir"
  if ! agent-runtime render --source-root "$REPO_ROOT" --product "$product" \
    >"$render_log" 2>&1; then
    echo "runtime-smoke: rendered-contract bootstrap failed for $product" >&2
    cat "$render_log" >&2
    return 1
  fi
  printf '%s\n' "$REPO_ROOT" >"$ready_file"
}

rendered_contract_set_paths() {
  local domain="$1"
  local skill="$2"
  local product="$3"

  rendered_contract_prepare_product "$product"
  RENDERED_CONTRACT_BUILD="$REPO_ROOT/build/$product/plugins/$domain/skills/$skill/SKILL.md"
  RENDERED_CONTRACT_GOLDEN="$REPO_ROOT/tests/golden/$product/plugins/$domain/skills/$skill/expected/SKILL.md"
}

rendered_contract_assert_skill() {
  local domain="$1"
  local skill="$2"
  local product

  for product in codex claude hermes; do
    rendered_contract_set_paths "$domain" "$skill" "$product"
    test -s "$RENDERED_CONTRACT_BUILD"
    test -s "$RENDERED_CONTRACT_GOLDEN"
    cmp -s "$RENDERED_CONTRACT_BUILD" "$RENDERED_CONTRACT_GOLDEN"
    ! grep -Eq '/home/terry|/Users/terry|\.local/state/agent-runtime-kit/worktrees' \
      "$RENDERED_CONTRACT_BUILD" "$RENDERED_CONTRACT_GOLDEN"
  done
}

rendered_contract_assert_product_contains() {
  local domain="$1"
  local skill="$2"
  local product="$3"
  local needle="$4"

  rendered_contract_set_paths "$domain" "$skill" "$product"
  grep -Fq -- "$needle" "$RENDERED_CONTRACT_BUILD"
  grep -Fq -- "$needle" "$RENDERED_CONTRACT_GOLDEN"
}

rendered_contract_assert_product_omits() {
  local domain="$1"
  local skill="$2"
  local product="$3"
  local needle="$4"

  rendered_contract_set_paths "$domain" "$skill" "$product"
  ! grep -Fq -- "$needle" "$RENDERED_CONTRACT_BUILD"
  ! grep -Fq -- "$needle" "$RENDERED_CONTRACT_GOLDEN"
}

rendered_contract_assert_all_contain() {
  local domain="$1"
  local skill="$2"
  local needle="$3"
  local product

  for product in codex claude hermes; do
    rendered_contract_assert_product_contains "$domain" "$skill" "$product" "$needle"
  done
}

rendered_contract_assert_all_omit() {
  local domain="$1"
  local skill="$2"
  local needle="$3"
  local product

  for product in codex claude hermes; do
    rendered_contract_assert_product_omits "$domain" "$skill" "$product" "$needle"
  done
}

rendered_contract_assert_reference() {
  local domain="$1"
  local skill="$2"
  local relative_path="$3"
  local source="$REPO_ROOT/core/skills/$domain/$skill/$relative_path"
  local product rendered golden

  test -s "$source"
  for product in codex claude hermes; do
    rendered="$REPO_ROOT/build/$product/plugins/$domain/skills/$skill/$relative_path"
    golden="$REPO_ROOT/tests/golden/$product/plugins/$domain/skills/$skill/expected/$relative_path"
    test -s "$rendered"
    test -s "$golden"
    cmp -s "$source" "$rendered"
    cmp -s "$source" "$golden"
  done
}
