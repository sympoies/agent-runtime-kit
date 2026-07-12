#!/usr/bin/env bash
# Runtime skill smoke harness.
# Sourced helpers intentionally mutate their own globals inside subshells.
# shellcheck disable=SC2031

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$REPO_ROOT/tests/runtime-smoke"
MATRIX_FILE="$SCRIPT_DIR/acceptance-matrix.yaml"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/runtime-home.sh
. "$SCRIPT_DIR/lib/runtime-home.sh"

MODE=""
FORMAT="text"
PRODUCT=""
DOMAIN=""
PROBE_ONLY=0
KEEP_ARTIFACTS=0
ARTIFACTS_DIR=""

usage() {
  cat <<'USAGE'
Usage: tests/runtime-smoke/run.sh --mode <matrix|install|deterministic|product|convergence> [options]

Options:
  --mode <mode>           Smoke mode to run.
  --format <text|json>    Output format. Default: text.
  --product <product>     Product for install/product/convergence mode: codex or claude. Default: both.
  --domain <domain>       Deterministic smoke domain. Default: all available domains.
  --probe-only            Product mode only: run isolation probes without product prompt assertions.
  --artifacts-dir <path>  Write run logs and observed files to this directory.
  --keep-artifacts        Keep the temporary runtime root after the run.
  -h, --help              Show this help.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --format)
      FORMAT="${2:-}"
      shift 2
      ;;
    --product)
      PRODUCT="${2:-}"
      shift 2
      ;;
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --probe-only)
      PROBE_ONLY=1
      shift
      ;;
    --artifacts-dir)
      ARTIFACTS_DIR="${2:-}"
      shift 2
      ;;
    --keep-artifacts)
      KEEP_ARTIFACTS=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "runtime-smoke: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$MODE" ]; then
  echo "runtime-smoke: --mode is required" >&2
  usage >&2
  exit 2
fi

case "$MODE" in
  matrix | install | deterministic | product | convergence)
    ;;
  *)
    echo "runtime-smoke: unsupported mode: $MODE" >&2
    exit 2
    ;;
esac

case "$FORMAT" in
  text | json)
    ;;
  *)
    echo "runtime-smoke: unsupported format: $FORMAT" >&2
    exit 2
    ;;
esac

case "$PRODUCT" in
  "" | codex | claude)
    ;;
  *)
    echo "runtime-smoke: unsupported product: $PRODUCT" >&2
    exit 2
    ;;
esac

case "$DOMAIN" in
  "" | browser | code-review | computer-use | conversation | dispatch | evidence | issue | media | meta | pr | reporting)
    ;;
  *)
    echo "runtime-smoke: unsupported domain: $DOMAIN" >&2
    exit 2
    ;;
esac

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/agent-runtime-kit-runtime-smoke.XXXXXX")"
if [ -z "$ARTIFACTS_DIR" ]; then
  ARTIFACTS_DIR="$TMP_ROOT/artifacts"
fi
mkdir -p "$ARTIFACTS_DIR"
RESULTS_FILE="$ARTIFACTS_DIR/results.tsv"

# Isolate child tools (notably forge-cli) from the operator's ~/.config so
# user-global config never leaks into probe behaviour. Without this, a host
# that opts into the forge-cli test-first gate
# ($XDG_CONFIG_HOME/forge-cli/config.toml `[test_first] require = true`) makes
# the `pr create --kind feature` dry-run probes fail with
# test_first_evidence_required, even though that config is absent on CI runners.
# Probes must exercise the documented default surface, not host gate settings.
export XDG_CONFIG_HOME="$TMP_ROOT/xdg-config"
mkdir -p "$XDG_CONFIG_HOME"

cleanup() {
  if [ "$KEEP_ARTIFACTS" -eq 1 ]; then
    echo "runtime-smoke: kept temp root: $TMP_ROOT" >&2
  else
    rm -rf "$TMP_ROOT"
  fi
}
trap cleanup EXIT

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke: required binary not on PATH: $bin" >&2
    exit 127
  fi
}

count_lines() {
  wc -l <"$1" | tr -d ' '
}

validate_matrix_contract() {
  local matrix="$1"
  local expected_codex="$REPO_ROOT/tests/sandbox/codex/expected-skills.txt"
  local expected_claude="$REPO_ROOT/tests/sandbox/claude/expected-skills.txt"
  local case_ids="$ARTIFACTS_DIR/matrix.case-ids.txt"
  local case_ids_unique="$ARTIFACTS_DIR/matrix.case-ids.unique"
  local skill_ids="$ARTIFACTS_DIR/matrix.skill-ids.txt"
  local skill_ids_unique="$ARTIFACTS_DIR/matrix.skill-ids.unique"
  local dispositions="$ARTIFACTS_DIR/matrix.dispositions.txt"
  local case_count key key_count

  if [ ! -s "$matrix" ]; then
    echo "runtime-smoke: matrix missing or empty: $matrix" >&2
    return 1
  fi

  sed -n 's/^  - id:[[:space:]]*//p' "$matrix" >"$case_ids"
  case_count="$(count_lines "$case_ids")"
  if [ "$case_count" -eq 0 ]; then
    echo "runtime-smoke: matrix has no cases" >&2
    return 1
  fi
  sort -u "$case_ids" >"$case_ids_unique"
  if [ "$(count_lines "$case_ids_unique")" != "$case_count" ]; then
    echo "runtime-smoke: matrix case id values must be unique" >&2
    return 1
  fi

  for key in id product domain skill_id mode fixture_workspace setup invocation expected_exit_code expected_artifacts cleanup expected_disposition skip_policy; do
    if [ "$key" = "id" ]; then
      key_count="$(sed -n 's/^  - id:[[:space:]]*//p' "$matrix" | wc -l | tr -d ' ')"
    else
      key_count="$(sed -n "s/^    $key:[[:space:]]*//p" "$matrix" | wc -l | tr -d ' ')"
    fi
    if [ "$key_count" != "$case_count" ]; then
      echo "runtime-smoke: matrix key '$key' count mismatch: got=$key_count expected=$case_count" >&2
      return 1
    fi
  done

  sed -n 's/^    skill_id:[[:space:]]*//p' "$matrix" >"$skill_ids"
  sort -u "$skill_ids" >"$skill_ids_unique"
  if [ "$(count_lines "$skill_ids_unique")" != "$(count_lines "$expected_codex")" ]; then
    echo "runtime-smoke: matrix skill_id unique set count does not match expected skills" >&2
    return 1
  fi
  if ! diff -u "$expected_codex" "$skill_ids_unique" >"$ARTIFACTS_DIR/matrix.codex-skills.diff" 2>&1; then
    echo "runtime-smoke: matrix skill_id set does not match codex expected skills" >&2
    cat "$ARTIFACTS_DIR/matrix.codex-skills.diff" >&2
    return 1
  fi
  if ! diff -u "$expected_claude" "$skill_ids_unique" >"$ARTIFACTS_DIR/matrix.claude-skills.diff" 2>&1; then
    echo "runtime-smoke: matrix skill_id set does not match claude expected skills" >&2
    cat "$ARTIFACTS_DIR/matrix.claude-skills.diff" >&2
    return 1
  fi

  sed -n 's/^    expected_disposition:[[:space:]]*//p' "$matrix" >"$dispositions"
  while IFS= read -r disposition; do
    case "$disposition" in
      pass | fail | skip-host-capability | blocked-design)
        ;;
      *)
        echo "runtime-smoke: unknown disposition: $disposition" >&2
        return 1
        ;;
    esac
  done <"$dispositions"

  if ! awk '
    /^  - id:/ {
      if (case_id != "" && domain != "" && skill_id !~ "^" domain "\\.") {
        printf "case %s has domain=%s but skill_id=%s\n", case_id, domain, skill_id > "/dev/stderr"
        bad = 1
      }
      case_id = $0
      sub(/^  - id:[[:space:]]*/, "", case_id)
      domain = ""
      skill_id = ""
    }
    /^    domain:/ {
      domain = $0
      sub(/^    domain:[[:space:]]*/, "", domain)
    }
    /^    skill_id:/ {
      skill_id = $0
      sub(/^    skill_id:[[:space:]]*/, "", skill_id)
    }
    END {
      if (case_id != "" && domain != "" && skill_id !~ "^" domain "\\.") {
        printf "case %s has domain=%s but skill_id=%s\n", case_id, domain, skill_id > "/dev/stderr"
        bad = 1
      }
      exit bad
    }
  ' "$matrix"; then
    return 1
  fi

  RUNTIME_SMOKE_MATRIX_COUNT="$case_count"
  return 0
}

run_matrix_mode() {
  results_init "$RESULTS_FILE"
  if validate_matrix_contract "$MATRIX_FILE"; then
    results_add "matrix.contract" "shared-cli" "pass" "$RUNTIME_SMOKE_MATRIX_COUNT" "acceptance matrix covers expected skill ids"
  else
    results_add "matrix.contract" "shared-cli" "fail" "0" "acceptance matrix validation failed"
  fi
}

run_install_mode() {
  local products product status note skill_count portable_source_root
  require_bin agent-runtime
  results_init "$RESULTS_FILE"
  portable_source_root="$(runtime_prepare_portable_source "$REPO_ROOT" "$TMP_ROOT/install-portable-source")"

  if [ -n "$PRODUCT" ]; then
    products="$PRODUCT"
  else
    products="codex claude"
  fi

  for product in $products; do
    if runtime_install_product "$portable_source_root" "$TMP_ROOT" "$product" "$ARTIFACTS_DIR"; then
      status="pass"
      note="install apply, active IDs, and installed-runtime receipt verified"
      skill_count="$RUNTIME_SMOKE_SKILL_COUNT"
    else
      status="fail"
      note="install, active-ID, or receipt validation failed"
      skill_count="0"
    fi
    results_add "install.$product" "$product" "$status" "$skill_count" "$note"
  done
}

run_deterministic_mode() {
  local failures
  failures=0
  results_init "$RESULTS_FILE"
  export REPO_ROOT SCRIPT_DIR TMP_ROOT ARTIFACTS_DIR RESULTS_FILE

  case "$DOMAIN" in
    "")
      bash "$SCRIPT_DIR/cases/meta/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/media/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/browser/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/computer-use/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/conversation/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/evidence/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/issue/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/code-review/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/pr/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/dispatch/run.sh" || failures=1
      bash "$SCRIPT_DIR/cases/reporting/run.sh" || failures=1
      ;;
    browser)
      bash "$SCRIPT_DIR/cases/browser/run.sh" || failures=1
      ;;
    code-review)
      bash "$SCRIPT_DIR/cases/code-review/run.sh" || failures=1
      ;;
    conversation)
      bash "$SCRIPT_DIR/cases/conversation/run.sh" || failures=1
      ;;
    computer-use)
      bash "$SCRIPT_DIR/cases/computer-use/run.sh" || failures=1
      ;;
    dispatch)
      bash "$SCRIPT_DIR/cases/dispatch/run.sh" || failures=1
      ;;
    evidence)
      bash "$SCRIPT_DIR/cases/evidence/run.sh" || failures=1
      ;;
    issue)
      bash "$SCRIPT_DIR/cases/issue/run.sh" || failures=1
      ;;
    media)
      bash "$SCRIPT_DIR/cases/media/run.sh" || failures=1
      ;;
    meta)
      bash "$SCRIPT_DIR/cases/meta/run.sh" || failures=1
      ;;
    pr)
      bash "$SCRIPT_DIR/cases/pr/run.sh" || failures=1
      ;;
    reporting)
      bash "$SCRIPT_DIR/cases/reporting/run.sh" || failures=1
      ;;
  esac

  return "$failures"
}

run_product_mode() {
  results_init "$RESULTS_FILE"
  RUNTIME_SMOKE_SOURCE_ROOT="$(runtime_prepare_portable_source "$REPO_ROOT" "$TMP_ROOT/product-portable-source")"
  export REPO_ROOT RUNTIME_SMOKE_SOURCE_ROOT SCRIPT_DIR TMP_ROOT ARTIFACTS_DIR RESULTS_FILE PRODUCT PROBE_ONLY
  bash "$SCRIPT_DIR/product/run.sh"
}

run_convergence_mode() {
  results_init "$RESULTS_FILE"
  export REPO_ROOT SCRIPT_DIR TMP_ROOT ARTIFACTS_DIR RESULTS_FILE PRODUCT
  bash "$SCRIPT_DIR/convergence/run.sh"
}

RUN_STATUS=0
case "$MODE" in
  matrix)
    run_matrix_mode || RUN_STATUS=$?
    ;;
  install)
    run_install_mode || RUN_STATUS=$?
    ;;
  deterministic)
    run_deterministic_mode || RUN_STATUS=$?
    ;;
  product)
    run_product_mode || RUN_STATUS=$?
    ;;
  convergence)
    run_convergence_mode || RUN_STATUS=$?
    ;;
esac

if ! results_validate_unique_ids; then
  RUN_STATUS=1
fi

if [ "$FORMAT" = "json" ]; then
  results_print_json "$MODE"
else
  results_print_text "$MODE"
fi

if results_has_failures || [ "$RUN_STATUS" -ne 0 ]; then
  exit 1
fi
