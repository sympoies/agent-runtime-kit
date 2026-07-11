#!/usr/bin/env bash
# Product-in-the-loop isolation probes.
# shellcheck disable=SC2329

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"
: "${PROBE_ONLY:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/runtime-home.sh
. "$SCRIPT_DIR/lib/runtime-home.sh"

PRODUCT_ARTIFACTS_DIR="$ARTIFACTS_DIR/product"
PRODUCT_WORKSPACE="$TMP_ROOT/workspaces/product-basic-repo"

mkdir -p "$PRODUCT_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$PRODUCT_WORKSPACE"

require_product_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke product: required binary not on PATH: $bin" >&2
    return 2
  fi
}

record_product_case() {
  local id="$1"
  local product="$2"
  local status="$3"
  local skill_count="$4"
  local note="$5"
  results_add "$id" "$product" "$status" "$skill_count" "$note"
}

run_codex_probe() {
  local root="$PRODUCT_ARTIFACTS_DIR/codex/probe"
  local home="$root/home"
  local codex_home="$root/codex-home"
  local xdg="$root/xdg"
  local version_out="$root/codex.version.txt"
  local help_out="$root/codex.help.txt"
  local exec_help_out="$root/codex.exec-help.txt"
  local prompt_out="$root/codex.prompt.stdout.jsonl"
  local prompt_err="$root/codex.prompt.stderr.txt"
  local prompt_exit="$root/codex.prompt.exit"
  local files_out="$root/files.txt"
  local exit_code

  require_product_bin codex || return "$?"
  mkdir -p "$home" "$codex_home" "$xdg"

  HOME="$home" CODEX_HOME="$codex_home" XDG_CONFIG_HOME="$xdg" \
    codex --version >"$version_out" 2>&1
  HOME="$home" CODEX_HOME="$codex_home" XDG_CONFIG_HOME="$xdg" \
    codex --help >"$help_out" 2>&1
  HOME="$home" CODEX_HOME="$codex_home" XDG_CONFIG_HOME="$xdg" \
    codex exec --help >"$exec_help_out" 2>&1

  grep -q 'Run Codex non-interactively' "$exec_help_out"
  grep -q -- '--ephemeral' "$exec_help_out"
  grep -q -- '--ignore-user-config' "$exec_help_out"

  set +e
  HOME="$home" CODEX_HOME="$codex_home" XDG_CONFIG_HOME="$xdg" \
    codex --ask-for-approval never exec \
    --ignore-user-config \
    --ephemeral \
    --skip-git-repo-check \
    --sandbox read-only \
    --oss \
    --local-provider "${RUNTIME_SMOKE_CODEX_LOCAL_PROVIDER:-ollama}" \
    --model "${RUNTIME_SMOKE_CODEX_MODEL:-llama3.2}" \
    -C "$PRODUCT_WORKSPACE" \
    --json \
    "Reply with ok." >"$prompt_out" 2>"$prompt_err"
  exit_code="$?"
  set -e

  printf '%s\n' "$exit_code" >"$prompt_exit"
  find "$root" -maxdepth 5 \( -type f -o -type d \) | sort >"$files_out"

  if [ "$exit_code" -eq 0 ]; then
    return 0
  fi

  grep -Eq 'No running Ollama server detected|OSS setup failed|Failed to connect to Ollama' "$prompt_err"
}

run_claude_probe() {
  local root="$PRODUCT_ARTIFACTS_DIR/claude/probe"
  local home="$root/home"
  local claude_config_dir="$root/claude-config"
  local xdg="$root/xdg"
  local version_out="$root/claude.version.txt"
  local help_out="$root/claude.help.txt"
  local prompt_out="$root/claude.prompt.stdout.json"
  local prompt_err="$root/claude.prompt.stderr.txt"
  local prompt_exit="$root/claude.prompt.exit"
  local files_out="$root/files.txt"
  local exit_code

  require_product_bin claude || return "$?"
  mkdir -p "$home" "$claude_config_dir" "$xdg"

  HOME="$home" CLAUDE_CONFIG_DIR="$claude_config_dir" XDG_CONFIG_HOME="$xdg" \
    claude --version >"$version_out" 2>&1
  HOME="$home" CLAUDE_CONFIG_DIR="$claude_config_dir" XDG_CONFIG_HOME="$xdg" \
    claude --help >"$help_out" 2>&1

  grep -q -- '--bare' "$help_out"
  grep -q -- '--no-session-persistence' "$help_out"
  grep -q -- '--print' "$help_out"

  set +e
  env -u ANTHROPIC_API_KEY \
    HOME="$home" \
    CLAUDE_CONFIG_DIR="$claude_config_dir" \
    XDG_CONFIG_HOME="$xdg" \
    claude -p \
    --bare \
    --no-session-persistence \
    --setting-sources project \
    --settings '{}' \
    --tools '' \
    --model "${RUNTIME_SMOKE_CLAUDE_MODEL:-sonnet}" \
    --output-format json \
    --max-budget-usd "${RUNTIME_SMOKE_CLAUDE_MAX_BUDGET_USD:-0.01}" \
    "Reply with ok." >"$prompt_out" 2>"$prompt_err"
  exit_code="$?"
  set -e

  printf '%s\n' "$exit_code" >"$prompt_exit"
  find "$root" -maxdepth 5 \( -type f -o -type d \) | sort >"$files_out"

  if [ "$exit_code" -eq 0 ]; then
    return 0
  fi

  grep -q 'Not logged in' "$prompt_out"
}

run_product_probe() {
  local product="$1"
  local status note rc

  case "$product" in
    codex)
      run_codex_probe
      rc="$?"
      ;;
    claude)
      run_claude_probe
      rc="$?"
      ;;
    *)
      echo "runtime-smoke product: unsupported product: $product" >&2
      record_product_case "product.$product.probe" "$product" "fail" "0" "unsupported product"
      return 1
      ;;
  esac

  if [ "$rc" -eq 0 ]; then
    status="pass"
    case "$product" in
      codex)
        note="isolation=supported via CODEX_HOME and ephemeral exec; prompt execution is outside product mode"
        ;;
      claude)
        note="isolation=supported via CLAUDE_CONFIG_DIR and bare print; prompt execution is outside product mode"
        ;;
    esac
  elif [ "$rc" -eq 2 ]; then
    status="skip-host-capability"
    note="$product CLI not available on PATH"
  else
    status="blocked-design"
    note="$product CLI isolation probe failed; see product artifacts"
  fi

  record_product_case "product.$product.probe" "$product" "$status" "1" "$note"
  [ "$status" != "blocked-design" ]
}

install_product_surface() {
  local product="$1"
  local install_artifacts="$PRODUCT_ARTIFACTS_DIR/$product/install"

  if ! command -v agent-runtime >/dev/null 2>&1; then
    record_product_case "product.$product.install" "$product" "fail" "0" "agent-runtime missing; cannot install temp product surface"
    return 1
  fi

  if runtime_install_product "$REPO_ROOT" "$TMP_ROOT" "$product" "$install_artifacts"; then
    record_product_case "product.$product.install" "$product" "pass" "$RUNTIME_SMOKE_SKILL_COUNT" "installed current skills into temp product live_home"
    return 0
  fi

  record_product_case "product.$product.install" "$product" "fail" "0" "install or doctor validation failed for temp product live_home"
  return 1
}

if [ -n "${PRODUCT:-}" ]; then
  products="$PRODUCT"
else
  products="codex claude"
fi

failures=0
for product in $products; do
  if ! run_product_probe "$product"; then
    failures=1
    continue
  fi

  if [ "$PROBE_ONLY" -eq 1 ]; then
    continue
  fi

  if ! install_product_surface "$product"; then
    failures=1
    continue
  fi

done

exit "$failures"
