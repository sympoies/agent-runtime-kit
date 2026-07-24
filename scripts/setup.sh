#!/usr/bin/env bash
# scripts/setup.sh — host bootstrap for agent-runtime-kit.
#
# Compatibility: must run on macOS (system bash 3.2) and Linux (bash 4+).
# Avoid associative arrays, mapfile, and `${var,,}` lowercasing.
#
# References:
#   - DEVELOPMENT.md (`## Setup`) — host bootstrap and brew-first install
#   - manifests/cli-tools.yaml (third-party CLI catalog this script installs)

set -euo pipefail

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

readonly PROG_NAME="setup.sh"
readonly REPO_HOME_DEFAULT="$HOME/.config/agent-runtime-kit"
readonly REPO_REMOTE_DEFAULT="https://github.com/graysurf/agent-runtime-kit.git"
readonly TAP_SPEC="sympoies/tap"
readonly TAP_FORMULA="sympoies/tap/nils-cli"

PROFILE="core"
SKIP_HOMEBREW_INSTALL=0
SKIP_CLI_TOOLS=0
DRY_RUN=0
BREW_PREFIX=""
BOOTSTRAP_SURFACE="phase commands"
CLAUDE_PLUGIN_REGISTRY_SURFACE="not-run"
CODEX_PLUGIN_REGISTRY_SURFACE="not-run"
DOCS_PREFLIGHT_SUMMARY="not-run"
SCRIPT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_TOOLS_MANIFEST="$SCRIPT_REPO_ROOT/manifests/cli-tools.yaml"

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------

print_help() {
  cat <<EOF
Usage: $PROG_NAME [--profile core|recommended|full] [--skip-homebrew-install] [--skip-cli-tools] [--dry-run]

Bootstrap a host so it can run graysurf/agent-runtime-kit. Installs Homebrew
when missing, taps sympoies/tap, installs nils-cli (which ships the
agent-runtime binary), installs the profile-selected third-party CLI tools
from manifests/cli-tools.yaml, clones agent-runtime-kit into
\$HOME/.config/agent-runtime-kit when missing, wires the home prompt docs
symlinks, verifies declared agent docs, and then uses
\`agent-runtime bootstrap-host\` for the runtime surface bootstrap when the
installed nils-cli surface provides it. Older nils-cli pins fall back to the
manual render / install / prune-stale phase commands. It then delegates to
\`scripts/sync-runtime-surfaces.sh\` to activate the plugin registries and the
\`agent-hook\`-owned provider hook ingress. The script finishes with
\`agent-runtime doctor\` for both products.

For daily runtime surface refreshes, see \`scripts/sync-runtime-surfaces.sh\`.

Options:
  --profile core|recommended|full
      Pick the third-party CLI install set defined in manifests/cli-tools.yaml.
      core         minimum daily-use floor (7 tools).
      recommended  productivity tools every author touches (~17 tools).
      full         everything from core/policies/cli-tools.md.
      Default: core.
  --skip-homebrew-install
      Skip the \`brew\` install step (useful for CI runners and Linuxbrew
      hosts that pre-install brew separately).
  --skip-cli-tools
      Skip third-party CLI formula installation from manifests/cli-tools.yaml.
  --dry-run
      Print every command that WOULD run, without executing brew / git /
      agent-runtime.
  -h, --help
      Print this help and exit.
EOF
}

# -----------------------------------------------------------------------------
# Logging helpers
# -----------------------------------------------------------------------------

log() { printf '%s\n' "$*"; }
warn() { printf 'warn: %s\n' "$*" >&2; }
err() { printf 'error: %s\n' "$*" >&2; }

print_cmd() {
  printf '+'
  while [ "$#" -gt 0 ]; do
    printf ' %q' "$1"
    shift
  done
  printf '\n'
}

run_cmd() {
  print_cmd "$@"
  if [ "$DRY_RUN" = "1" ]; then
    return 0
  fi
  "$@"
}

require_commands() {
  local missing=""
  local cmd
  for cmd in "$@"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing="${missing}${cmd}
"
    fi
  done
  if [ -n "$missing" ]; then
    err "missing required command(s):"
    printf '%s' "$missing" | sed 's/^/  - /' >&2
    exit 127
  fi
}

# -----------------------------------------------------------------------------
# Arg parsing
# -----------------------------------------------------------------------------

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --profile)
        if [ "$#" -lt 2 ]; then
          err "--profile requires a value"
          exit 2
        fi
        PROFILE="$2"
        shift 2
        ;;
      --profile=*)
        PROFILE="${1#--profile=}"
        shift
        ;;
      --skip-homebrew-install)
        SKIP_HOMEBREW_INSTALL=1
        shift
        ;;
      --skip-cli-tools)
        SKIP_CLI_TOOLS=1
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      -h | --help)
        print_help
        exit 0
        ;;
      --)
        shift
        break
        ;;
      *)
        err "unknown argument: $1"
        echo
        print_help
        exit 2
        ;;
    esac
  done

  case "$PROFILE" in
    core | recommended | full) ;;
    *)
      err "invalid --profile value: $PROFILE (expected core|recommended|full)"
      exit 2
      ;;
  esac
}

# -----------------------------------------------------------------------------
# Phase implementations
# -----------------------------------------------------------------------------

ensure_homebrew() {
  if [ "$SKIP_HOMEBREW_INSTALL" = "1" ]; then
    log "skipping homebrew install (--skip-homebrew-install)"
    if [ "$DRY_RUN" = "0" ]; then
      require_commands brew
    fi
    return 0
  fi
  if command -v brew >/dev/null 2>&1; then
    log "brew already on PATH"
    return 0
  fi
  if [ "$DRY_RUN" = "1" ]; then
    log "+ /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    return 0
  fi
  log "+ NONINTERACTIVE=1 /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  require_commands brew
}

detect_brew_prefix() {
  if command -v brew >/dev/null 2>&1; then
    BREW_PREFIX="$(brew --prefix)"
    log "detected brew prefix: $BREW_PREFIX"
  elif [ "$DRY_RUN" = "1" ]; then
    log "detected platform: $(uname -s) (brew prefix unavailable during dry-run)"
  else
    require_commands brew
  fi
}

tap_and_install_nils_cli() {
  run_cmd brew tap "$TAP_SPEC"
  if command -v brew >/dev/null 2>&1 && brew list --versions nils-cli >/dev/null 2>&1; then
    run_cmd brew upgrade "$TAP_FORMULA"
  else
    run_cmd brew install "$TAP_FORMULA"
  fi
  if [ "$DRY_RUN" = "0" ]; then
    require_commands agent-runtime agent-docs
  fi
}

profile_keys() {
  local profile="$1"
  awk -v profile="$profile" '
    /^profiles:/ { in_profiles = 1; next }
    /^formulas:/ { in_profiles = 0; in_profile = 0 }
    in_profiles && $0 ~ ("^  " profile ":") { in_profile = 1; next }
    in_profiles && in_profile && /^  [A-Za-z0-9_-]+:/ { exit }
    in_profiles && in_profile && /^    - / {
      sub(/^    - /, "")
      print
    }
  ' "$CLI_TOOLS_MANIFEST"
}

formula_field_for_key() {
  local key="$1"
  local field="$2"
  awk -v key="$key" -v field="$field" '
    /^formulas:/ { in_formulas = 1; next }
    in_formulas && $0 ~ ("^  " key ":") { in_key = 1; next }
    in_formulas && in_key && /^  [A-Za-z0-9_-]+:/ { exit }
    in_formulas && in_key && $0 ~ ("^    " field ": ") {
      sub("^    " field ": ", "")
      print
      exit
    }
  ' "$CLI_TOOLS_MANIFEST"
}

skip_formula_for_host() {
  local key="$1"
  case "$key" in
    hammerspoon | im-select)
      [ "$(uname -s)" != "Darwin" ]
      ;;
    *)
      return 1
      ;;
  esac
}

install_cli_tools_profile() {
  local key
  local brew_formula
  local command_name
  local missing=""
  local profile_list

  if [ "$SKIP_CLI_TOOLS" = "1" ]; then
    log "skipping third-party CLI tools (--skip-cli-tools)"
    return 0
  fi
  if [ ! -f "$CLI_TOOLS_MANIFEST" ]; then
    err "missing CLI tools manifest: $CLI_TOOLS_MANIFEST"
    exit 1
  fi

  log "installing third-party CLI tools for profile=$PROFILE from manifests/cli-tools.yaml"
  profile_list="$(profile_keys "$PROFILE")"
  if [ -z "$profile_list" ]; then
    err "profile $PROFILE has no entries in $CLI_TOOLS_MANIFEST"
    exit 1
  fi
  while IFS= read -r key; do
    [ -n "$key" ] || continue
    if skip_formula_for_host "$key"; then
      log "skipping $key on non-Darwin host"
      continue
    fi
    brew_formula="$(formula_field_for_key "$key" brew)"
    command_name="$(formula_field_for_key "$key" command)"
    if [ -z "$brew_formula" ] || [ -z "$command_name" ]; then
      err "manifest entry missing brew/command field for profile key: $key"
      exit 1
    fi
    run_cmd brew install "$brew_formula"
    if [ "$DRY_RUN" = "0" ] && ! command -v "$command_name" >/dev/null 2>&1; then
      missing="${missing}${key} (${command_name})
"
    fi
  done <<EOF_KEYS
$profile_list
EOF_KEYS

  if [ -n "$missing" ]; then
    err "installed profile=$PROFILE but command(s) are still unavailable:"
    printf '%s' "$missing" | sed 's/^/  - /' >&2
    exit 127
  fi
}

ensure_repo_clone() {
  if [ -d "$REPO_HOME_DEFAULT/.git" ]; then
    log "agent-runtime-kit already cloned at $REPO_HOME_DEFAULT"
    return 0
  fi
  if [ -e "$REPO_HOME_DEFAULT" ]; then
    err "$REPO_HOME_DEFAULT exists but is not a git checkout"
    exit 1
  fi
  if [ "$DRY_RUN" = "0" ]; then
    require_commands git
  fi
  run_cmd git clone "$REPO_REMOTE_DEFAULT" "$REPO_HOME_DEFAULT"
}

product_live_home() {
  case "$1" in
    claude) printf '%s\n' "$HOME/.claude" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

product_state_home() {
  local state_root="${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit"
  case "$1" in
    claude) printf '%s\n' "${CLAUDE_KIT_STATE_HOME:-$state_root/claude}" ;;
    codex) printf '%s\n' "${CODEX_AGENT_STATE_HOME:-$state_root/codex}" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

agent_home_raw_source() {
  printf '%s\n' "$REPO_HOME_DEFAULT/AGENT_HOME.md"
}

agent_home_source() {
  case "$1" in
    claude | codex) printf '%s\n' "$REPO_HOME_DEFAULT/build/$1/AGENT_HOME.md" ;;
    neutral) printf '%s\n' "$REPO_HOME_DEFAULT/build/neutral/AGENT_HOME.md" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

product_home_prompt_path() {
  case "$1" in
    claude) printf '%s\n' "$HOME/.claude/CLAUDE.md" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/AGENTS.md" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

canonical_path() {
  local path="$1"
  local dir
  local base
  dir="$(dirname "$path")"
  base="$(basename "$path")"
  if (
    cd "$dir" 2>/dev/null &&
      printf '%s/%s\n' "$(pwd -P)" "$base"
  ); then
    return 0
  fi
  printf '%s\n' "$path"
}

resolve_symlink_target() {
  local link_path="$1"
  local raw_target
  local link_dir
  local target_dir
  local target_base

  raw_target="$(readlink "$link_path")" || return 1
  case "$raw_target" in
    /*)
      printf '%s\n' "$raw_target"
      ;;
    *)
      link_dir="$(dirname "$link_path")"
      target_dir="$(dirname "$raw_target")"
      target_base="$(basename "$raw_target")"
      (
        cd "$link_dir" &&
          cd "$target_dir" 2>/dev/null &&
          printf '%s/%s\n' "$(pwd -P)" "$target_base"
      ) || printf '%s/%s\n' "$link_dir" "$raw_target"
      ;;
  esac
}

ensure_home_prompt() {
  local product="$1"
  local target
  local target_dir
  local expected
  local old_expected
  local existing

  target="$(product_home_prompt_path "$product")"
  target_dir="$(dirname "$target")"
  expected="$(canonical_path "$(agent_home_source "$product")")"
  old_expected="$(canonical_path "$(agent_home_raw_source)")"

  if [ "$DRY_RUN" = "0" ] && [ ! -f "$expected" ]; then
    err "missing home policy source: $expected"
    exit 1
  fi

  if [ -L "$target" ]; then
    existing="$(resolve_symlink_target "$target")"
    if [ "$existing" = "$expected" ]; then
      log "home prompt already wired product=$product target=$target"
      return 0
    fi
    if [ "$existing" = "$old_expected" ]; then
      log "rewiring managed home prompt product=$product target=$target"
      run_cmd rm "$target"
      run_cmd ln -s "$expected" "$target"
      return 0
    fi
    if [ "$DRY_RUN" = "1" ]; then
      warn "$target is a symlink to $existing; apply would require $expected"
      return 0
    fi
    err "$target is a symlink to $existing; expected $expected"
    exit 1
  fi

  if [ -e "$target" ]; then
    if [ "$DRY_RUN" = "1" ]; then
      warn "$target exists and is not a symlink to $expected; apply would refuse to overwrite"
      return 0
    fi
    err "$target exists and is not a symlink to $expected; refusing to overwrite"
    exit 1
  fi

  log "wiring home prompt product=$product target=$target"
  run_cmd mkdir -p "$target_dir"
  run_cmd ln -s "$expected" "$target"
}

render_home_prompts() {
  log "rendering home prompts"
  run_cmd agent-runtime render \
    --source-root "$REPO_HOME_DEFAULT" \
    --target home-prompt
  run_cmd agent-runtime render \
    --source-root "$REPO_HOME_DEFAULT" \
    --target home-prompt \
    --product codex
  run_cmd agent-runtime render \
    --source-root "$REPO_HOME_DEFAULT" \
    --target home-prompt \
    --product claude
}

ensure_home_prompts() {
  local product
  for product in codex claude; do
    ensure_home_prompt "$product"
  done
}

run_agent_docs_preflight() {
  local list_output
  local list_status
  local intents
  local parse_status
  local intent
  local summary=""
  local list_docs_home="$REPO_HOME_DEFAULT"

  log "verifying agent docs preflight"

  print_cmd agent-docs list \
    --docs-home "$REPO_HOME_DEFAULT" \
    --project-path "$REPO_HOME_DEFAULT" \
    --format json
  if ! command -v agent-docs >/dev/null 2>&1; then
    if [ "$DRY_RUN" = "1" ]; then
      warn "agent-docs is not on PATH during dry-run; apply will enumerate declared intents after nils-cli install"
      DOCS_PREFLIGHT_SUMMARY="planned via agent-docs list --docs-home $REPO_HOME_DEFAULT --project-path $REPO_HOME_DEFAULT --format json"
      return 0
    fi
    require_commands agent-docs
  fi
  require_commands python3
  if [ "$DRY_RUN" = "1" ] && [ ! -f "$list_docs_home/AGENT_DOCS.toml" ] && [ -f "$SCRIPT_REPO_ROOT/AGENT_DOCS.toml" ]; then
    list_docs_home="$SCRIPT_REPO_ROOT"
    warn "using $list_docs_home to enumerate agent-docs intents during dry-run because $REPO_HOME_DEFAULT is not cloned yet"
  fi
  set +e
  list_output="$(
    agent-docs list \
      --docs-home "$list_docs_home" \
      --project-path "$list_docs_home" \
      --format json 2>&1
  )"
  list_status=$?
  set -e
  if [ "$list_status" -ne 0 ]; then
    err "agent-docs list failed"
    printf '%s\n' "$list_output" >&2
    exit "$list_status"
  fi

  set +e
  intents="$(printf '%s\n' "$list_output" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    raise SystemExit(2)
for intent in data.get("intents", []):
    if isinstance(intent, str) and intent:
        print(intent)
')"
  parse_status=$?
  set -e
  if [ "$parse_status" -ne 0 ]; then
    err "agent-docs list returned invalid JSON"
    printf '%s\n' "$list_output" >&2
    exit "$parse_status"
  fi
  if [ -z "$intents" ]; then
    err "agent-docs list returned no declared intents"
    exit 1
  fi

  while IFS= read -r intent; do
    [ -n "$intent" ] || continue
    run_cmd agent-docs preflight \
      --docs-home "$REPO_HOME_DEFAULT" \
      --project-path "$REPO_HOME_DEFAULT" \
      --intent "$intent" \
      --strict
    if [ -n "$summary" ]; then
      summary="${summary}; "
    fi
    summary="${summary}agent-docs preflight --docs-home $REPO_HOME_DEFAULT --project-path $REPO_HOME_DEFAULT --intent $intent --strict"
  done <<EOF_INTENTS
$intents
EOF_INTENTS

  DOCS_PREFLIGHT_SUMMARY="$summary"
}

bootstrap_host_available() {
  if ! command -v agent-runtime >/dev/null 2>&1; then
    return 1
  fi
  agent-runtime bootstrap-host --help >/dev/null 2>&1
}

run_bootstrap_host() {
  local mode_flag="--apply"
  if [ "$DRY_RUN" = "1" ]; then
    mode_flag="--dry-run"
  fi
  BOOTSTRAP_SURFACE="agent-runtime bootstrap-host"
  log "delegating runtime surface bootstrap to agent-runtime bootstrap-host"
  run_cmd agent-runtime bootstrap-host \
    --source-root "$REPO_HOME_DEFAULT" \
    --profile "$PROFILE" \
    --product both \
    --skip-homebrew-install \
    --skip-cli-tools \
    "$mode_flag"
}

activate_products() {
  local product
  local live_home
  local state_home
  local mode_flag="--apply"
  if [ "$DRY_RUN" = "1" ]; then
    mode_flag="--dry-run"
  fi
  for product in claude codex; do
    live_home="$(product_live_home "$product")"
    state_home="$(product_state_home "$product")"
    run_cmd agent-runtime install \
      --source-root "$REPO_HOME_DEFAULT" \
      --product "$product" \
      --live-home "$live_home" \
      --state-home "$state_home" \
      "$mode_flag"
  done
}

prune_products() {
  local product
  local live_home
  local mode_flag="--apply"
  if [ "$DRY_RUN" = "1" ]; then
    mode_flag="--dry-run"
  fi
  for product in claude codex; do
    live_home="$(product_live_home "$product")"
    run_cmd agent-runtime prune-stale \
      --source-root "$REPO_HOME_DEFAULT" \
      --product "$product" \
      --live-home "$live_home" \
      "$mode_flag"
  done
}

render_products() {
  local product
  for product in codex claude; do
    log "rendering product=$product"
    run_cmd agent-runtime render \
      --source-root "$REPO_HOME_DEFAULT" \
      --product "$product"
  done
}

run_surface_bootstrap() {
  if bootstrap_host_available; then
    run_bootstrap_host
    return 0
  fi

  BOOTSTRAP_SURFACE="phase commands"
  warn "agent-runtime bootstrap-host is unavailable; using render/install/prune fallback"
  render_products
  activate_products
  prune_products
}

sync_claude_plugin_registry_activation() {
  local mode_flag="--apply"
  local script="$REPO_HOME_DEFAULT/scripts/sync-runtime-surfaces.sh"

  if [ "$DRY_RUN" = "1" ]; then
    mode_flag="--dry-run"
  elif [ ! -f "$script" ]; then
    err "missing sync-runtime-surfaces script for Claude plugin activation: $script"
    exit 1
  fi

  CLAUDE_PLUGIN_REGISTRY_SURFACE="sync-runtime-surfaces.sh"
  log "activating Claude plugin registry through sync-runtime-surfaces"
  run_cmd bash "$script" \
    --source-root "$REPO_HOME_DEFAULT" \
    --product claude \
    --no-pull \
    --no-prune \
    --no-verify \
    "$mode_flag"
}

sync_codex_plugin_registry_activation() {
  local mode_flag="--apply"
  local script="$REPO_HOME_DEFAULT/scripts/sync-runtime-surfaces.sh"

  if [ "$DRY_RUN" = "1" ]; then
    mode_flag="--dry-run"
  elif [ ! -f "$script" ]; then
    err "missing sync-runtime-surfaces script for Codex plugin activation: $script"
    exit 1
  fi

  CODEX_PLUGIN_REGISTRY_SURFACE="sync-runtime-surfaces.sh"
  log "activating Codex plugin registry through sync-runtime-surfaces"
  run_cmd bash "$script" \
    --source-root "$REPO_HOME_DEFAULT" \
    --product codex \
    --no-pull \
    --no-verify \
    "$mode_flag"
}

run_doctor() {
  local product
  local live_home
  local state_home
  local doctor_exit=0
  local code=0

  for product in claude codex; do
    live_home="$(product_live_home "$product")"
    state_home="$(product_state_home "$product")"
    if [ "$DRY_RUN" = "1" ]; then
      run_cmd agent-runtime doctor \
        --source-root "$REPO_HOME_DEFAULT" \
        --product "$product" \
        --live-home "$live_home" \
        --state-home "$state_home" \
        --profile "$PROFILE"
      continue
    fi
    print_cmd agent-runtime doctor \
      --source-root "$REPO_HOME_DEFAULT" \
      --product "$product" \
      --live-home "$live_home" \
      --state-home "$state_home" \
      --profile "$PROFILE"
    set +e
    agent-runtime doctor \
      --source-root "$REPO_HOME_DEFAULT" \
      --product "$product" \
      --live-home "$live_home" \
      --state-home "$state_home" \
      --profile "$PROFILE"
    code=$?
    set -e
    if [ "$code" -gt "$doctor_exit" ]; then
      doctor_exit="$code"
    fi
  done

  return "$doctor_exit"
}

print_summary() {
  cat <<EOF

Summary
- repo_home: $REPO_HOME_DEFAULT
- brew_prefix: ${BREW_PREFIX:-unavailable}
- profile: $PROFILE
- runtime_surface_bootstrap: $BOOTSTRAP_SURFACE
- claude_live_home: $(product_live_home claude)
- codex_live_home: $(product_live_home codex)
- claude_home_prompt: $(product_home_prompt_path claude) -> $(agent_home_source claude)
- codex_home_prompt: $(product_home_prompt_path codex) -> $(agent_home_source codex)
- claude_plugin_registry_activation: $CLAUDE_PLUGIN_REGISTRY_SURFACE
- codex_plugin_registry_activation: $CODEX_PLUGIN_REGISTRY_SURFACE
- docs_audit: not-run (legacy key retained; rendered home prompts use source-root docs_preflight)
- docs_preflight: $DOCS_PREFLIGHT_SUMMARY
EOF
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
  local doctor_code=0

  parse_args "$@"

  log "$PROG_NAME starting (profile=$PROFILE skip_homebrew=$SKIP_HOMEBREW_INSTALL skip_cli_tools=$SKIP_CLI_TOOLS dry_run=$DRY_RUN)"

  ensure_homebrew
  detect_brew_prefix
  tap_and_install_nils_cli
  install_cli_tools_profile
  ensure_repo_clone
  render_home_prompts
  ensure_home_prompts
  run_agent_docs_preflight
  run_surface_bootstrap
  sync_claude_plugin_registry_activation
  sync_codex_plugin_registry_activation
  print_summary
  set +e
  run_doctor
  doctor_code=$?
  set -e
  if [ "$doctor_code" -ne 0 ]; then
    err "$PROG_NAME completed with doctor exit=$doctor_code"
    exit "$doctor_code"
  fi

  log "$PROG_NAME complete"
}

main "$@"
