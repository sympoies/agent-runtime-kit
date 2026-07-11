#!/usr/bin/env bash
# scripts/sync-runtime-surfaces.sh - refresh managed surfaces into local runtimes.
#
# Compatibility: must run on macOS (system bash 3.2) and Linux (bash 4+).
# Avoid associative arrays, mapfile, and `${var,,}` lowercasing.

set -euo pipefail

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

readonly PROG_NAME="sync-runtime-surfaces.sh"

APPLY=0
PRODUCT="both"
NO_PULL=0
NO_VERIFY=0
NO_PRUNE=0
SOURCE_ROOT=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_PROMPT_STATUS="not-run"
HOME_PROMPT_STATUS="not-run"
CLAUDE_PLUGIN_STATUS="not-run"
CODEX_PLUGIN_STATUS="not-run"
PRUNE_SKIPPED_TOTAL=0
PRUNE_LAST_SKIPPED=0
CLAUDE_PLUGIN_PREFLIGHT_DONE=0
CLAUDE_PREFLIGHT_MARKETPLACE=""
CLAUDE_PREFLIGHT_INSTALLED_REFS=""
CLAUDE_PREFLIGHT_MARKETPLACES_JSON=""
CODEX_PLUGIN_PREFLIGHT_DONE=0
CODEX_PREFLIGHT_MARKETPLACE=""
CODEX_PREFLIGHT_INSTALLED_REFS=""
CODEX_PREFLIGHT_MARKETPLACES_JSON=""

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------

print_help() {
  cat <<EOF
Usage: $PROG_NAME [--apply] [--product codex|claude|both] [--source-root PATH] [--no-pull] [--no-prune] [--no-verify] [--codex-plugin-activation]

Refresh graysurf/agent-runtime-kit managed runtime surfaces into local Codex
and Claude runtime homes. This is the daily runtime surface refresh entrypoint
after source changes land. For first-time host setup, run scripts/setup.sh
first.

By default, this command is a dry-run: it prints the pull, home-prompt render /
rewire, product render, install, prune, doctor, and optional Codex prompt-input
commands without mutating runtime homes. Pass --apply to run the commands.

Options:
  --apply
      Execute the refresh. Without this flag, commands are printed only.
  --product codex|claude|hermes|both
      Limit the refresh to one product. Default: both.
  --source-root PATH
      Use a specific agent-runtime-kit checkout. Defaults to this script's
      repository root. For --apply, this must be a durable primary checkout;
      linked git worktrees and Codex transient worktrees are refused.
  --no-pull
      Skip git pull --ff-only and refresh the current checkout state.
  --no-prune
      Skip stale managed-surface pruning. With --apply, stale runtime surfaces
      may remain until a later refresh runs without this flag.
  --no-verify
      Skip post-install skill-surface doctor and Codex prompt-input probes.
  --codex-plugin-activation
      Deprecated compatibility flag. Codex plugin marketplace activation is now
      the default runtime-kit skill-discovery path.
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
  if [ "$APPLY" = "0" ]; then
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
# Arg parsing and path resolution
# -----------------------------------------------------------------------------

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --apply)
        APPLY=1
        shift
        ;;
      --dry-run)
        APPLY=0
        shift
        ;;
      --product)
        if [ "$#" -lt 2 ]; then
          err "--product requires a value"
          exit 2
        fi
        PRODUCT="$2"
        shift 2
        ;;
      --product=*)
        PRODUCT="${1#--product=}"
        shift
        ;;
      --source-root)
        if [ "$#" -lt 2 ]; then
          err "--source-root requires a value"
          exit 2
        fi
        SOURCE_ROOT="$2"
        shift 2
        ;;
      --source-root=*)
        SOURCE_ROOT="${1#--source-root=}"
        shift
        ;;
      --no-pull)
        NO_PULL=1
        shift
        ;;
      --no-prune)
        NO_PRUNE=1
        shift
        ;;
      --no-verify)
        NO_VERIFY=1
        shift
        ;;
      --codex-plugin-activation)
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

  case "$PRODUCT" in
    codex | claude | hermes | both) ;;
    *)
      err "invalid --product value: $PRODUCT (expected codex|claude|both)"
      exit 2
      ;;
  esac
}

resolve_source_root() {
  local root_candidate
  local top_level

  if [ -n "$SOURCE_ROOT" ]; then
    root_candidate="$SOURCE_ROOT"
  else
    root_candidate="$SCRIPT_DIR/.."
  fi

  if [ ! -d "$root_candidate" ]; then
    err "source root does not exist: $root_candidate"
    exit 2
  fi

  if ! top_level="$(git -C "$root_candidate" rev-parse --show-toplevel 2>/dev/null)"; then
    err "source root is not inside a git checkout: $root_candidate"
    exit 2
  fi

  SOURCE_ROOT="$(cd "$top_level" && pwd)"
}

absolute_git_dir() {
  local path="$1"
  local candidate

  case "$path" in
    /*) candidate="$path" ;;
    *) candidate="$SOURCE_ROOT/$path" ;;
  esac

  if [ ! -d "$candidate" ]; then
    err "git directory does not exist: $candidate"
    exit 2
  fi

  (cd "$candidate" && pwd -P)
}

source_root_is_linked_worktree() {
  local git_dir
  local common_dir
  local git_dir_abs
  local common_dir_abs

  git_dir="$(git -C "$SOURCE_ROOT" rev-parse --git-dir)"
  common_dir="$(git -C "$SOURCE_ROOT" rev-parse --git-common-dir)"
  git_dir_abs="$(absolute_git_dir "$git_dir")"
  common_dir_abs="$(absolute_git_dir "$common_dir")"

  [ "$git_dir_abs" != "$common_dir_abs" ]
}

source_root_is_codex_transient_worktree() {
  local source_physical
  local codex_home
  local codex_worktrees

  source_physical="$(cd "$SOURCE_ROOT" && pwd -P)"
  case "$source_physical" in
    */.codex/worktrees | */.codex/worktrees/*)
      return 0
      ;;
  esac

  codex_home="${CODEX_HOME:-$HOME/.codex}"
  if [ -d "$codex_home" ]; then
    codex_worktrees="$(cd "$codex_home" && pwd -P)/worktrees"
    case "$source_physical" in
      "$codex_worktrees" | "$codex_worktrees"/*)
        return 0
        ;;
    esac
  fi

  return 1
}

validate_live_sync_source_root() {
  if [ "$APPLY" = "0" ]; then
    return 0
  fi

  if source_root_is_linked_worktree; then
    err "refusing live sync from a git worktree: $SOURCE_ROOT"
    err "sync-runtime-surfaces --apply installs runtime-home symlinks; run it from a durable primary checkout or pass --source-root to one."
    exit 2
  fi

  if source_root_is_codex_transient_worktree; then
    err "refusing live sync from a Codex transient worktree: $SOURCE_ROOT"
    err "sync-runtime-surfaces --apply installs runtime-home symlinks; use a durable primary checkout outside runtime scratch worktrees."
    exit 2
  fi
}

selected_products() {
  case "$PRODUCT" in
    codex) printf '%s\n' codex ;;
    claude) printf '%s\n' claude ;;
    hermes) printf '%s\n' hermes ;;
    both)
      printf '%s\n' codex
      printf '%s\n' claude
      printf '%s\n' hermes
      ;;
  esac
}

product_label() {
  case "$PRODUCT" in
    codex) printf '%s\n' codex ;;
    claude) printf '%s\n' claude ;;
    hermes) printf '%s\n' hermes ;;
    both) printf '%s\n' codex+claude+hermes ;;
  esac
}

selected_includes_codex() {
  case "$PRODUCT" in
    codex | both) return 0 ;;
    claude | hermes) return 1 ;;
  esac
}

product_live_home() {
  case "$1" in
    claude) printf '%s\n' "$HOME/.claude" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}" ;;
    hermes) printf '%s\n' "${HERMES_HOME:-$HOME/.hermes}" ;;
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
    hermes) printf '%s\n' "${HERMES_HOME:-$HOME/.hermes}" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

agent_home_raw_source() {
  printf '%s\n' "$SOURCE_ROOT/AGENT_HOME.md"
}

agent_home_source() {
  case "$1" in
    claude | codex | hermes) printf '%s\n' "$SOURCE_ROOT/build/$1/AGENT_HOME.md" ;;
    neutral) printf '%s\n' "$SOURCE_ROOT/build/neutral/AGENT_HOME.md" ;;
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
    hermes) printf '%s\n' "${HERMES_HOME:-$HOME/.hermes}/skills/development-policy/SKILL.md" ;;
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

is_managed_runtime_kit_checkout_root() {
  local candidate_root="$1"
  local top_level
  local candidate_head
  local source_head
  local source_origin
  local source_origin_path

  [ -f "$candidate_root/AGENT_HOME.md" ] || return 1
  [ -f "$candidate_root/manifests/skills.yaml" ] || return 1
  [ -f "$candidate_root/scripts/sync-runtime-surfaces.sh" ] || return 1
  top_level="$(git -C "$candidate_root" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [ "$(canonical_path "$top_level")" = "$(canonical_path "$candidate_root")" ] || return 1
  git -C "$candidate_root" ls-files --error-unmatch -- \
    AGENT_HOME.md manifests/skills.yaml scripts/sync-runtime-surfaces.sh \
    >/dev/null 2>&1 || return 1
  candidate_head="$(git -C "$candidate_root" rev-parse HEAD 2>/dev/null)" || return 1
  source_head="$(git -C "$SOURCE_ROOT" rev-parse HEAD 2>/dev/null)" || return 1
  git -C "$SOURCE_ROOT" cat-file -e "$candidate_head^{commit}" 2>/dev/null || return 1
  if git -C "$SOURCE_ROOT" merge-base --is-ancestor "$candidate_head" "$source_head" 2>/dev/null ||
    git -C "$SOURCE_ROOT" merge-base --is-ancestor "$source_head" "$candidate_head" 2>/dev/null; then
    return 0
  fi

  # A durable independent clone may be on a branch that diverged from the
  # primary checkout. Its local origin still provides an exact ownership link
  # to that checkout; accept only that canonical path relation.
  if source_origin="$(python3 - "$SOURCE_ROOT" <<'PY'
import subprocess
import sys

root = sys.argv[1]
proc = subprocess.run(
    ["git", "-C", root, "config", "--local", "--null", "--get-all", "remote.origin.url"],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    check=False,
)
if proc.returncode != 0:
    raise SystemExit(1)
records = proc.stdout.split(b"\0")
if not records or records[-1] != b"":
    raise SystemExit(1)
records.pop()
if len(records) != 1:
    raise SystemExit(1)
try:
    value = records[0].decode("utf-8")
except UnicodeDecodeError:
    raise SystemExit(1)
if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
    raise SystemExit(1)
sys.stdout.write(value)
PY
  )"; then
    :
  else
    source_origin=""
  fi
  case "$source_origin" in
    /*) source_origin_path="$source_origin" ;;
    ./* | ../*) source_origin_path="$SOURCE_ROOT/$source_origin" ;;
    *) source_origin_path="" ;;
  esac
  if [ -n "$source_origin_path" ] && [ -d "$source_origin_path" ] &&
    [ "$(cd "$source_origin_path" && pwd -P)" = "$(cd "$candidate_root" && pwd -P)" ]; then
    return 0
  fi
  return 1
}

is_managed_rendered_home_prompt_target() {
  local product="$1"
  local existing="$2"
  local suffix="/build/$product/AGENT_HOME.md"
  local candidate_root

  case "$existing" in
    *"$suffix") candidate_root="${existing%"$suffix"}" ;;
    *) return 1 ;;
  esac
  [ -f "$existing" ] || return 1
  is_managed_runtime_kit_checkout_root "$candidate_root"
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
      canonical_path "$raw_target"
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

# -----------------------------------------------------------------------------
# Refresh steps
# -----------------------------------------------------------------------------

pull_source() {
  if [ "$NO_PULL" = "1" ]; then
    log "git pull skipped (--no-pull)"
    return 0
  fi
  run_cmd git -C "$SOURCE_ROOT" pull --ff-only
}

check_source_counts() {
  local audit_script="$SOURCE_ROOT/scripts/ci/skill-governance-audit.sh"

  if [ ! -f "$audit_script" ]; then
    err "source root is missing skill governance audit: $audit_script"
    exit 2
  fi

  log "checking source skill counts"
  print_cmd bash "$audit_script" --check-counts
  bash "$audit_script" --check-counts
}

render_home_prompt_base() {
  log "rendering home prompt product=neutral"
  if [ "$APPLY" = "1" ]; then
    HOME_PROMPT_STATUS="rendered"
  else
    HOME_PROMPT_STATUS="planned"
  fi
  run_cmd agent-runtime render \
    --source-root "$SOURCE_ROOT" \
    --target home-prompt
}

render_home_prompt_product() {
  local product="$1"

  log "rendering home prompt product=$product"
  if [ "$APPLY" = "1" ]; then
    HOME_PROMPT_STATUS="rendered"
  else
    HOME_PROMPT_STATUS="planned"
  fi
  run_cmd agent-runtime render \
    --source-root "$SOURCE_ROOT" \
    --target home-prompt \
    --product "$product"
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

  if [ "$APPLY" = "1" ] && [ ! -f "$expected" ]; then
    err "missing home policy source: $expected"
    exit 1
  fi

  if [ -L "$target" ]; then
    existing="$(resolve_symlink_target "$target")"
    if [ "$existing" = "$expected" ]; then
      log "home prompt already wired product=$product target=$target"
      if [ "$APPLY" = "1" ]; then
        HOME_PROMPT_STATUS="wired"
      fi
      return 0
    fi
    if [ "$existing" = "$old_expected" ] ||
      is_managed_rendered_home_prompt_target "$product" "$existing"; then
      log "rewiring managed home prompt product=$product target=$target"
      run_cmd rm "$target"
      run_cmd ln -s "$expected" "$target"
      if [ "$APPLY" = "1" ]; then
        HOME_PROMPT_STATUS="wired"
      fi
      return 0
    fi
    if [ "$APPLY" = "0" ]; then
      warn "$target is a symlink to $existing; apply would require $expected"
      return 0
    fi
    err "$target is a symlink to $existing; expected $expected"
    exit 1
  fi

  if [ -e "$target" ]; then
    if [ "$APPLY" = "0" ]; then
      warn "$target exists and is not a symlink to $expected; apply would refuse to overwrite"
      return 0
    fi
    err "$target exists and is not a symlink to $expected; refusing to overwrite"
    exit 1
  fi

  log "wiring home prompt product=$product target=$target"
  run_cmd mkdir -p "$target_dir"
  run_cmd ln -s "$expected" "$target"
  if [ "$APPLY" = "1" ]; then
    HOME_PROMPT_STATUS="wired"
  fi
}

render_product() {
  local product="$1"
  log "rendering product=$product"
  run_cmd agent-runtime render \
    --source-root "$SOURCE_ROOT" \
    --product "$product"
}

install_product() {
  local product="$1"
  local live_home
  local state_home
  local mode_flag="--dry-run"

  if [ "$APPLY" = "1" ]; then
    mode_flag="--apply"
  fi

  live_home="$(product_live_home "$product")"
  state_home="$(product_state_home "$product")"

  log "installing product=$product live_home=$live_home"
  run_cmd agent-runtime install \
    --source-root "$SOURCE_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    "$mode_flag"
}

sync_claude_settings_hooks() {
  local live_home="$1"
  local fragment="$SOURCE_ROOT/core/hooks/claude/settings.hooks.jsonc"
  local settings_path="$live_home/settings.json"

  if [ ! -f "$fragment" ]; then
    err "missing Claude settings hook fragment: $fragment"
    exit 2
  fi

  log "syncing Claude settings hooks live_home=$live_home"
  print_cmd python3 - "$fragment" "$settings_path" "$APPLY"
  python3 - "$fragment" "$settings_path" "$APPLY" <<'PY'
import copy
import json
import os
import stat
import sys

fragment_path, settings_path, apply_flag = sys.argv[1:4]


def strip_line_comments(text):
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("//"):
            continue
        lines.append(line)
    return "\n".join(lines)


def load_fragment(path):
    with open(path, encoding="utf-8") as handle:
        wrapped = "{\n" + strip_line_comments(handle.read()) + "\n}\n"
    data = json.loads(wrapped)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        raise SystemExit(f"Claude hook fragment must contain an object hooks block: {path}")
    return hooks


def load_settings(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"Claude settings root must be a JSON object: {path}")
    return data


def is_managed_hook(hook):
    if not isinstance(hook, dict):
        return False
    command = hook.get("command")
    status = hook.get("statusMessage")
    if isinstance(status, str) and status.startswith("agent-runtime-kit:"):
        return True
    return (
        isinstance(command, str)
        and "AGENT_RUNTIME_PRODUCT=claude" in command
        and "$HOME/.claude/hooks/" in command
    )


def remove_managed_hooks(settings_hooks):
    for event in list(settings_hooks):
        groups = settings_hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            kept_hooks = [hook for hook in group["hooks"] if not is_managed_hook(hook)]
            if kept_hooks:
                next_group = copy.deepcopy(group)
                next_group["hooks"] = kept_hooks
                kept_groups.append(next_group)
        if kept_groups:
            settings_hooks[event] = kept_groups
        else:
            settings_hooks.pop(event, None)


def append_source_hooks(settings_hooks, source_hooks):
    managed_count = 0
    for event, source_groups in source_hooks.items():
        if not isinstance(source_groups, list):
            raise SystemExit(f"Claude hook fragment event must be a list: {event}")
        target_groups = settings_hooks.setdefault(event, [])
        if not isinstance(target_groups, list):
            raise SystemExit(f"Claude settings hooks.{event} must be a list")
        for source_group in source_groups:
            if not isinstance(source_group, dict) or not isinstance(source_group.get("hooks"), list):
                raise SystemExit(f"Claude hook fragment group must contain hooks list: {event}")
            matcher = source_group.get("matcher", "")
            target_group = None
            for group in target_groups:
                if (
                    isinstance(group, dict)
                    and group.get("matcher", "") == matcher
                    and isinstance(group.get("hooks"), list)
                ):
                    target_group = group
                    break
            if target_group is None:
                target_group = copy.deepcopy(source_group)
                target_group["hooks"] = []
                target_groups.append(target_group)
            for hook in source_group["hooks"]:
                target_group["hooks"].append(copy.deepcopy(hook))
                managed_count += 1
    return managed_count


source_hooks = load_fragment(fragment_path)
settings = load_settings(settings_path)
settings_hooks = settings.setdefault("hooks", {})
if not isinstance(settings_hooks, dict):
    raise SystemExit(f"Claude settings hooks block must be a JSON object: {settings_path}")

remove_managed_hooks(settings_hooks)
managed_count = append_source_hooks(settings_hooks, source_hooks)

if apply_flag != "1":
    print(f"claude settings hooks dry-run: managed_hooks={managed_count} target={settings_path}")
    raise SystemExit(0)

settings_dir = os.path.dirname(settings_path)
os.makedirs(settings_dir, exist_ok=True)
tmp_path = settings_path + ".tmp"
with open(tmp_path, "w", encoding="utf-8") as handle:
    json.dump(settings, handle, indent=2)
    handle.write("\n")
if os.path.exists(settings_path):
    os.chmod(tmp_path, stat.S_IMODE(os.stat(settings_path).st_mode))
else:
    os.chmod(tmp_path, 0o600)
os.replace(tmp_path, settings_path)
print(f"claude settings hooks synced: managed_hooks={managed_count} target={settings_path}")
PY
}

claude_marketplace_json_path() {
  local live_home="$1"
  local live_marketplace="$live_home/.claude-plugin/marketplace.json"
  local source_marketplace="$SOURCE_ROOT/targets/claude/.claude-plugin/marketplace.json"

  if [ -f "$source_marketplace" ]; then
    printf '%s\n' "$source_marketplace"
    return 0
  fi

  if [ -f "$live_marketplace" ]; then
    printf '%s\n' "$live_marketplace"
    return 0
  fi

  err "missing Claude marketplace manifest: $live_marketplace (or source fallback $source_marketplace)"
  return 1
}

claude_marketplace_name() {
  local marketplace_json="$1"
  python3 - "$marketplace_json" <<'PY'
import json
import re
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
name = data.get("name")
if not isinstance(name, str) or not name:
    raise SystemExit(f"Claude marketplace manifest missing non-empty name: {sys.argv[1]}")
print(name)
PY
}

claude_marketplace_plugins() {
  local marketplace_json="$1"
  python3 - "$marketplace_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
plugins = data.get("plugins")
if not isinstance(plugins, list):
    raise SystemExit(f"Claude marketplace manifest plugins must be a list: {sys.argv[1]}")
for entry in plugins:
    if not isinstance(entry, dict):
        raise SystemExit(f"Claude marketplace plugin entry must be an object: {sys.argv[1]}")
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"Claude marketplace plugin entry missing non-empty name: {sys.argv[1]}")
    print(name)
PY
}

claude_materialized_marketplace_home() {
  local state_home="$1"
  local marketplace="$2"

  case "$marketplace" in
    "" | *[!A-Za-z0-9._-]*)
      err "unsafe Claude marketplace name for state path: $marketplace"
      return 1
      ;;
  esac

  printf '%s\n' "$state_home/plugin-marketplaces/$marketplace"
}

materialize_claude_plugin_marketplace() {
  local marketplace_json="$1"
  local materialized_home="$2"

  log "materializing Claude plugin marketplace source=$marketplace_json target=$materialized_home"
  print_cmd python3 - "$SOURCE_ROOT" "$marketplace_json" "$materialized_home" "$APPLY"
  python3 - "$SOURCE_ROOT" "$marketplace_json" "$materialized_home" "$APPLY" <<'PY'
import json
import os
import shutil
import sys

source_root, marketplace_json, materialized_home, apply_flag = sys.argv[1:5]


def load_marketplace(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        raise SystemExit(f"Claude marketplace manifest plugins must be a list: {path}")
    names = []
    for entry in plugins:
        if not isinstance(entry, dict):
            raise SystemExit(f"Claude marketplace plugin entry must be an object: {path}")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"Claude marketplace plugin entry missing non-empty name: {path}")
        if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in name):
            raise SystemExit(f"Claude marketplace plugin entry has unsafe name: {name}")
        names.append(name)
    return names


plugin_names = load_marketplace(marketplace_json)
if apply_flag != "1":
    print(f"claude plugin marketplace materialize dry-run: target={materialized_home} plugins={len(plugin_names)}")
    raise SystemExit(0)

tmp_home = materialized_home + ".tmp"
if os.path.exists(tmp_home):
    shutil.rmtree(tmp_home)
os.makedirs(os.path.join(tmp_home, ".claude-plugin"), exist_ok=True)
os.makedirs(os.path.join(tmp_home, "plugins"), exist_ok=True)
shutil.copy2(marketplace_json, os.path.join(tmp_home, ".claude-plugin", "marketplace.json"))

for plugin in plugin_names:
    build_plugin = os.path.join(source_root, "build", "claude", "plugins", plugin)
    target_manifest = os.path.join(source_root, "targets", "claude", "plugins", plugin, ".claude-plugin")
    dest_plugin = os.path.join(tmp_home, "plugins", plugin)
    dest_manifest = os.path.join(dest_plugin, ".claude-plugin")

    if not os.path.isdir(build_plugin):
        raise SystemExit(f"missing rendered Claude plugin tree: {build_plugin}")
    if not os.path.isdir(target_manifest):
        raise SystemExit(f"missing Claude plugin manifest tree: {target_manifest}")

    shutil.copytree(build_plugin, dest_plugin, symlinks=False)
    if os.path.exists(dest_manifest):
        shutil.rmtree(dest_manifest)
    shutil.copytree(target_manifest, dest_manifest, symlinks=False)

for root, dirs, files in os.walk(tmp_home):
    for name in dirs + files:
        path = os.path.join(root, name)
        if os.path.islink(path):
            raise SystemExit(f"materialized Claude marketplace contains symlink: {path}")

os.makedirs(os.path.dirname(materialized_home), exist_ok=True)
if os.path.exists(materialized_home):
    shutil.rmtree(materialized_home)
os.replace(tmp_home, materialized_home)
print(f"claude plugin marketplace materialized: target={materialized_home} plugins={len(plugin_names)}")
PY
}

claude_marketplace_registered() {
  local marketplaces_json="$1"
  local marketplace="$2"

  python3 - "$marketplaces_json" "$marketplace" <<'PY'
import json
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit(1)
marketplace = sys.argv[2]
for entry in data:
    if isinstance(entry, dict) and entry.get("name") == marketplace:
        raise SystemExit(0)
raise SystemExit(1)
PY
}

claude_installed_plugin_refs_for_marketplace() {
  local installed_json="$1"
  local marketplace="$2"

  python3 - "$installed_json" "$marketplace" <<'PY'
import json
import re
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit(1)
marketplace = sys.argv[2]
name_re = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")
if name_re.fullmatch(marketplace) is None:
    raise SystemExit("managed Claude marketplace name has invalid syntax")
suffix = "@" + marketplace
for entry in data:
    if not isinstance(entry, dict) or entry.get("scope") != "user":
        continue
    plugin_ref = entry.get("id")
    if not isinstance(plugin_ref, str) or not plugin_ref.endswith(suffix):
        continue
    plugin_name, separator, plugin_marketplace = plugin_ref.rpartition("@")
    if (
        separator != "@"
        or plugin_marketplace != marketplace
        or name_re.fullmatch(plugin_name) is None
    ):
        raise SystemExit("installed Claude plugin id for managed marketplace has invalid syntax")
    print(plugin_ref)
PY
}

validate_claude_marketplace_registry_json() {
  local marketplaces_json="$1"

  python3 - "$marketplaces_json" <<'PY'
import json
import re
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit("Claude marketplace registry returned invalid JSON")
if not isinstance(data, list):
    raise SystemExit("Claude marketplace registry must be a list")
name_re = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")
for entry in data:
    if not isinstance(entry, dict):
        raise SystemExit("Claude marketplace registry entry must be an object")
    name = entry.get("name")
    if not isinstance(name, str) or name_re.fullmatch(name) is None:
        raise SystemExit("Claude marketplace registry entry has invalid name")
PY
}

preflight_claude_plugin_registry() {
  local live_home="$1"
  local marketplace_json
  local marketplace
  local installed_json
  local installed_refs
  local marketplaces_json

  [ "$APPLY" = "1" ] || return 0
  if ! command -v claude >/dev/null 2>&1; then
    CLAUDE_PLUGIN_STATUS="skipped"
    CLAUDE_PLUGIN_PREFLIGHT_DONE=1
    log "claude plugin registry preflight skipped (claude binary not on PATH)"
    return 0
  fi

  marketplace_json="$(claude_marketplace_json_path "$live_home")"
  marketplace="$(claude_marketplace_name "$marketplace_json")"
  installed_json="$(claude plugins list --json)"
  if ! installed_refs="$(claude_installed_plugin_refs_for_marketplace "$installed_json" "$marketplace")"; then
    CLAUDE_PLUGIN_STATUS="failed-invalid-installed-ref"
    err "Claude plugin registry returned an invalid installed plugin id for the managed marketplace; refusing refresh."
    return 1
  fi
  marketplaces_json="$(claude plugin marketplace list --json)"
  if ! validate_claude_marketplace_registry_json "$marketplaces_json"; then
    CLAUDE_PLUGIN_STATUS="failed-invalid-marketplace-registry"
    err "Claude plugin registry returned invalid marketplace data; refusing refresh."
    return 1
  fi

  CLAUDE_PREFLIGHT_MARKETPLACE="$marketplace"
  CLAUDE_PREFLIGHT_INSTALLED_REFS="$installed_refs"
  CLAUDE_PREFLIGHT_MARKETPLACES_JSON="$marketplaces_json"
  CLAUDE_PLUGIN_PREFLIGHT_DONE=1
  log "claude plugin registry preflight passed marketplace=$marketplace"
}

sync_claude_plugin_registry() {
  local live_home="$1"
  local state_home="$2"
  local marketplace_json
  local marketplace
  local materialized_home
  local marketplaces_json=""
  local installed_json=""
  local installed_refs=""
  local plugin_ref
  local plugin
  local plugin_count=0
  local refresh_count=0

  marketplace_json="$(claude_marketplace_json_path "$live_home")"
  marketplace="$(claude_marketplace_name "$marketplace_json")"
  materialized_home="$(claude_materialized_marketplace_home "$state_home" "$marketplace")"

  if [ "$APPLY" = "1" ] && ! command -v claude >/dev/null 2>&1; then
    CLAUDE_PLUGIN_STATUS="skipped"
    log "claude plugin registry skipped (claude binary not on PATH)"
    return 0
  fi

  if [ "$APPLY" = "1" ] && {
    [ "$CLAUDE_PLUGIN_PREFLIGHT_DONE" != "1" ] ||
      [ "$CLAUDE_PREFLIGHT_MARKETPLACE" != "$marketplace" ]
  }; then
    preflight_claude_plugin_registry "$live_home" || return $?
  fi

  materialize_claude_plugin_marketplace "$marketplace_json" "$materialized_home"

  log "syncing Claude plugin registry marketplace=$marketplace source=$materialized_home"
  if [ "$APPLY" = "1" ]; then
    installed_refs="$CLAUDE_PREFLIGHT_INSTALLED_REFS"
    while IFS= read -r plugin_ref; do
      [ -n "$plugin_ref" ] || continue
      run_cmd claude plugin uninstall "$plugin_ref" --scope user --keep-data
      refresh_count=$((refresh_count + 1))
    done <<EOF_REFRESH_PLUGINS
$installed_refs
EOF_REFRESH_PLUGINS

    marketplaces_json="$CLAUDE_PREFLIGHT_MARKETPLACES_JSON"
    if claude_marketplace_registered "$marketplaces_json" "$marketplace"; then
      run_cmd claude plugin marketplace remove "$marketplace" --scope user
    fi
  else
    run_cmd claude plugin marketplace remove "$marketplace" --scope user
  fi
  run_cmd claude plugin marketplace add "$materialized_home" --scope user

  while IFS= read -r plugin; do
    [ -n "$plugin" ] || continue
    plugin_ref="$plugin@$marketplace"
    run_cmd claude plugin install "$plugin_ref" --scope user
    plugin_count=$((plugin_count + 1))
  done <<EOF_PLUGINS
$(claude_marketplace_plugins "$marketplace_json")
EOF_PLUGINS

  if [ "$APPLY" = "1" ]; then
    CLAUDE_PLUGIN_STATUS="installed"
  else
    CLAUDE_PLUGIN_STATUS="planned"
  fi
  log "claude plugin registry ${CLAUDE_PLUGIN_STATUS}: marketplace=$marketplace source=$materialized_home plugins=$plugin_count refreshed=$refresh_count"
}

codex_marketplace_json_path() {
  local live_home="$1"
  local live_marketplace="$live_home/.agents/plugins/marketplace.json"
  local source_marketplace="$SOURCE_ROOT/targets/codex/.agents/plugins/marketplace.json"

  if [ -f "$source_marketplace" ]; then
    printf '%s\n' "$source_marketplace"
    return 0
  fi

  if [ -f "$live_marketplace" ]; then
    printf '%s\n' "$live_marketplace"
    return 0
  fi

  err "missing Codex marketplace manifest: $live_marketplace (or source fallback $source_marketplace)"
  return 1
}

codex_marketplace_name() {
  local marketplace_json="$1"
  python3 - "$marketplace_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
name = data.get("name")
if not isinstance(name, str) or not name:
    raise SystemExit(f"Codex marketplace manifest missing non-empty name: {sys.argv[1]}")
print(name)
PY
}

codex_marketplace_plugins() {
  local marketplace_json="$1"
  python3 - "$marketplace_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
plugins = data.get("plugins")
if not isinstance(plugins, list):
    raise SystemExit(f"Codex marketplace manifest plugins must be a list: {sys.argv[1]}")
for entry in plugins:
    if not isinstance(entry, dict):
        raise SystemExit(f"Codex marketplace plugin entry must be an object: {sys.argv[1]}")
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"Codex marketplace plugin entry missing non-empty name: {sys.argv[1]}")
    source = entry.get("source")
    if not isinstance(source, dict):
        raise SystemExit(f"Codex marketplace plugin {name} source must be an object: {sys.argv[1]}")
    if source.get("source") != "local":
        raise SystemExit(f"Codex marketplace plugin {name} source.source must be local: {sys.argv[1]}")
    expected_path = f"./plugins/{name}"
    if source.get("path") != expected_path:
        raise SystemExit(f"Codex marketplace plugin {name} source.path must be {expected_path}: {sys.argv[1]}")
    policy = entry.get("policy")
    if not isinstance(policy, dict):
        raise SystemExit(f"Codex marketplace plugin {name} policy must be an object: {sys.argv[1]}")
    if policy.get("installation") != "AVAILABLE":
        raise SystemExit(f"Codex marketplace plugin {name} policy.installation must be AVAILABLE: {sys.argv[1]}")
    if policy.get("authentication") != "ON_INSTALL":
        raise SystemExit(f"Codex marketplace plugin {name} policy.authentication must be ON_INSTALL: {sys.argv[1]}")
    category = entry.get("category")
    if not isinstance(category, str) or not category:
        raise SystemExit(f"Codex marketplace plugin {name} category must be a non-empty string: {sys.argv[1]}")
    print(name)
PY
}

codex_materialized_marketplace_home() {
  local state_home="$1"
  local marketplace="$2"

  case "$marketplace" in
    "" | *[!A-Za-z0-9._-]*)
      err "unsafe Codex marketplace name for state path: $marketplace"
      return 1
      ;;
  esac

  printf '%s\n' "$state_home/plugin-marketplaces/$marketplace"
}

materialize_codex_plugin_marketplace() {
  local marketplace_json="$1"
  local materialized_home="$2"

  log "materializing Codex plugin marketplace source=$marketplace_json target=$materialized_home"
  print_cmd python3 - "$SOURCE_ROOT" "$marketplace_json" "$materialized_home" "$APPLY"
  python3 - "$SOURCE_ROOT" "$marketplace_json" "$materialized_home" "$APPLY" <<'PY'
import json
import os
import shutil
import sys

source_root, marketplace_json, materialized_home, apply_flag = sys.argv[1:5]


def load_marketplace(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        raise SystemExit(f"Codex marketplace manifest plugins must be a list: {path}")
    names = []
    for entry in plugins:
        if not isinstance(entry, dict):
            raise SystemExit(f"Codex marketplace plugin entry must be an object: {path}")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"Codex marketplace plugin entry missing non-empty name: {path}")
        if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in name):
            raise SystemExit(f"Codex marketplace plugin entry has unsafe name: {name}")
        source = entry.get("source")
        if not isinstance(source, dict):
            raise SystemExit(f"Codex marketplace plugin {name} source must be an object: {path}")
        if source.get("source") != "local":
            raise SystemExit(f"Codex marketplace plugin {name} source.source must be local: {path}")
        expected_path = f"./plugins/{name}"
        if source.get("path") != expected_path:
            raise SystemExit(f"Codex marketplace plugin {name} source.path must be {expected_path}: {path}")
        policy = entry.get("policy")
        if not isinstance(policy, dict):
            raise SystemExit(f"Codex marketplace plugin {name} policy must be an object: {path}")
        if policy.get("installation") != "AVAILABLE":
            raise SystemExit(f"Codex marketplace plugin {name} policy.installation must be AVAILABLE: {path}")
        if policy.get("authentication") != "ON_INSTALL":
            raise SystemExit(f"Codex marketplace plugin {name} policy.authentication must be ON_INSTALL: {path}")
        category = entry.get("category")
        if not isinstance(category, str) or not category:
            raise SystemExit(f"Codex marketplace plugin {name} category must be a non-empty string: {path}")
        names.append(name)
    return names


plugin_names = load_marketplace(marketplace_json)
if apply_flag != "1":
    print(f"codex plugin marketplace materialize dry-run: target={materialized_home} plugins={len(plugin_names)}")
    raise SystemExit(0)

tmp_home = materialized_home + ".tmp"
if os.path.exists(tmp_home):
    shutil.rmtree(tmp_home)
os.makedirs(os.path.join(tmp_home, ".agents", "plugins"), exist_ok=True)
os.makedirs(os.path.join(tmp_home, "plugins"), exist_ok=True)
shutil.copy2(marketplace_json, os.path.join(tmp_home, ".agents", "plugins", "marketplace.json"))

for plugin in plugin_names:
    build_plugin = os.path.join(source_root, "build", "codex", "plugins", plugin)
    target_manifest = os.path.join(source_root, "targets", "codex", "plugins", plugin, ".codex-plugin")
    dest_plugin = os.path.join(tmp_home, "plugins", plugin)
    dest_manifest = os.path.join(dest_plugin, ".codex-plugin")

    if not os.path.isdir(build_plugin):
        raise SystemExit(f"missing rendered Codex plugin tree: {build_plugin}")
    if not os.path.isdir(target_manifest):
        raise SystemExit(f"missing Codex plugin manifest tree: {target_manifest}")

    shutil.copytree(build_plugin, dest_plugin, symlinks=False)
    if os.path.exists(dest_manifest):
        shutil.rmtree(dest_manifest)
    shutil.copytree(target_manifest, dest_manifest, symlinks=False)

for root, dirs, files in os.walk(tmp_home):
    for name in dirs + files:
        path = os.path.join(root, name)
        if os.path.islink(path):
            raise SystemExit(f"materialized Codex marketplace contains symlink: {path}")

os.makedirs(os.path.dirname(materialized_home), exist_ok=True)
if os.path.exists(materialized_home):
    shutil.rmtree(materialized_home)
os.replace(tmp_home, materialized_home)
print(f"codex plugin marketplace materialized: target={materialized_home} plugins={len(plugin_names)}")
PY
}

codex_marketplace_registered() {
  local marketplaces_json="$1"
  local marketplace="$2"

  python3 - "$marketplaces_json" "$marketplace" <<'PY'
import json
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit(1)
marketplace = sys.argv[2]
entries = data.get("marketplaces", []) if isinstance(data, dict) else []
for entry in entries:
    if isinstance(entry, dict) and entry.get("name") == marketplace:
        raise SystemExit(0)
raise SystemExit(1)
PY
}

codex_installed_plugin_refs_for_marketplace() {
  local installed_json="$1"
  local marketplace="$2"

  python3 - "$installed_json" "$marketplace" <<'PY'
import json
import re
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit(1)
marketplace = sys.argv[2]
name_re = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")
if name_re.fullmatch(marketplace) is None:
    raise SystemExit("managed Codex marketplace name has invalid syntax")
suffix = "@" + marketplace
entries = data.get("installed", []) if isinstance(data, dict) else []
for entry in entries:
    if not isinstance(entry, dict):
        continue
    plugin_id = entry.get("pluginId")
    if not isinstance(plugin_id, str):
        plugin_id = entry.get("plugin_id")
    if not isinstance(plugin_id, str) or not plugin_id.endswith(suffix):
        continue
    plugin_name, separator, plugin_marketplace = plugin_id.rpartition("@")
    if (
        separator != "@"
        or plugin_marketplace != marketplace
        or name_re.fullmatch(plugin_name) is None
    ):
        raise SystemExit("installed Codex plugin id for managed marketplace has invalid syntax")
    print(plugin_id)
PY
}

validate_codex_marketplace_registry_json() {
  local marketplaces_json="$1"

  python3 - "$marketplaces_json" <<'PY'
import json
import re
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit("Codex marketplace registry returned invalid JSON")
entries = data.get("marketplaces") if isinstance(data, dict) else None
if not isinstance(entries, list):
    raise SystemExit("Codex marketplace registry marketplaces must be a list")
name_re = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")
for entry in entries:
    if not isinstance(entry, dict):
        raise SystemExit("Codex marketplace registry entry must be an object")
    name = entry.get("name")
    if not isinstance(name, str) or name_re.fullmatch(name) is None:
        raise SystemExit("Codex marketplace registry entry has invalid name")
PY
}

require_codex_plugin_cli() {
  if ! command -v codex >/dev/null 2>&1; then
    CODEX_PLUGIN_STATUS="missing-codex"
    err "codex plugin registry requires Codex CLI >= 0.141.0 on PATH; install or expose the codex binary before running --apply."
    return 127
  fi

  if ! codex plugin --help >/dev/null 2>&1 ||
    ! codex plugin marketplace --help >/dev/null 2>&1; then
    CODEX_PLUGIN_STATUS="unsupported-codex"
    err "codex plugin registry requires Codex CLI >= 0.141.0 with 'codex plugin marketplace' support; upgrade Codex CLI before running --apply."
    return 1
  fi
}

preflight_codex_plugin_registry() {
  local live_home="$1"
  local marketplace_json
  local marketplace
  local installed_json
  local installed_refs
  local marketplaces_json

  [ "$APPLY" = "1" ] || return 0
  require_codex_plugin_cli || return $?

  marketplace_json="$(codex_marketplace_json_path "$live_home")"
  marketplace="$(codex_marketplace_name "$marketplace_json")"
  installed_json="$(codex plugin list --json)"
  if ! installed_refs="$(codex_installed_plugin_refs_for_marketplace "$installed_json" "$marketplace")"; then
    CODEX_PLUGIN_STATUS="failed-invalid-installed-ref"
    err "Codex plugin registry returned an invalid installed plugin id for the managed marketplace; refusing refresh."
    return 1
  fi
  marketplaces_json="$(codex plugin marketplace list --json)"
  if ! validate_codex_marketplace_registry_json "$marketplaces_json"; then
    CODEX_PLUGIN_STATUS="failed-invalid-marketplace-registry"
    err "Codex plugin registry returned invalid marketplace data; refusing refresh."
    return 1
  fi

  CODEX_PREFLIGHT_MARKETPLACE="$marketplace"
  CODEX_PREFLIGHT_INSTALLED_REFS="$installed_refs"
  CODEX_PREFLIGHT_MARKETPLACES_JSON="$marketplaces_json"
  CODEX_PLUGIN_PREFLIGHT_DONE=1
  log "codex plugin registry preflight passed marketplace=$marketplace"
}

# Mirror of sync_claude_plugin_registry for Codex, adapted to the Codex plugin
# CLI (`codex plugin add` / `remove`, `codex plugin marketplace add` / `remove`,
# no `--scope`) and the `{installed:[...],available:[...]}` /
# `{marketplaces:[...]}` JSON shapes. Codex discovers each installed plugin's
# bundled skills/<skill>/SKILL.md and ignores the `.codex-plugin/plugin.json`
# `skills` field, so the audit array stays as-is.
sync_codex_plugin_registry() {
  local live_home="$1"
  local state_home="$2"
  local marketplace_json
  local marketplace
  local materialized_home
  local marketplaces_json=""
  local installed_json=""
  local installed_refs=""
  local plugin_ref
  local plugin
  local plugin_count=0
  local refresh_count=0

  marketplace_json="$(codex_marketplace_json_path "$live_home")"
  marketplace="$(codex_marketplace_name "$marketplace_json")"
  materialized_home="$(codex_materialized_marketplace_home "$state_home" "$marketplace")"

  if [ "$APPLY" = "1" ]; then
    if [ "$CODEX_PLUGIN_PREFLIGHT_DONE" != "1" ] ||
      [ "$CODEX_PREFLIGHT_MARKETPLACE" != "$marketplace" ]; then
      preflight_codex_plugin_registry "$live_home" || return $?
    fi
  fi

  materialize_codex_plugin_marketplace "$marketplace_json" "$materialized_home"

  log "syncing Codex plugin registry marketplace=$marketplace source=$materialized_home"
  if [ "$APPLY" = "1" ]; then
    installed_refs="$CODEX_PREFLIGHT_INSTALLED_REFS"
    while IFS= read -r plugin_ref; do
      [ -n "$plugin_ref" ] || continue
      run_cmd codex plugin remove "$plugin_ref"
      refresh_count=$((refresh_count + 1))
    done <<EOF_REFRESH_CODEX_PLUGINS
$installed_refs
EOF_REFRESH_CODEX_PLUGINS

    marketplaces_json="$CODEX_PREFLIGHT_MARKETPLACES_JSON"
    if codex_marketplace_registered "$marketplaces_json" "$marketplace"; then
      run_cmd codex plugin marketplace remove "$marketplace"
    fi
  else
    run_cmd codex plugin marketplace remove "$marketplace"
  fi
  run_cmd codex plugin marketplace add "$materialized_home"

  while IFS= read -r plugin; do
    [ -n "$plugin" ] || continue
    plugin_ref="$plugin@$marketplace"
    run_cmd codex plugin add "$plugin_ref"
    plugin_count=$((plugin_count + 1))
  done <<EOF_CODEX_PLUGINS
$(codex_marketplace_plugins "$marketplace_json")
EOF_CODEX_PLUGINS

  if [ "$APPLY" = "1" ]; then
    CODEX_PLUGIN_STATUS="installed"
  else
    CODEX_PLUGIN_STATUS="planned"
  fi
  log "codex plugin registry ${CODEX_PLUGIN_STATUS}: marketplace=$marketplace source=$materialized_home plugins=$plugin_count refreshed=$refresh_count"
}

sync_product_activation() {
  local product="$1"
  local live_home
  local state_home

  case "$product" in
    claude)
      live_home="$(product_live_home "$product")"
      state_home="$(product_state_home "$product")"
      sync_claude_settings_hooks "$live_home"
      sync_claude_plugin_registry "$live_home" "$state_home"
      ;;
    codex)
      live_home="$(product_live_home "$product")"
      state_home="$(product_state_home "$product")"
      sync_codex_plugin_registry "$live_home" "$state_home"
      ;;
    hermes)
      log "hermes: no plugin registry to sync; runtime-kit skills are linked under ~/.hermes/external-skills/agent-runtime-kit/"
      ;;
    *)
      err "unknown product: $product"
      exit 2
      ;;
  esac
}

preflight_selected_product_activation() {
  local product
  local live_home

  [ "$APPLY" = "1" ] || return 0
  for product in $(selected_products); do
    live_home="$(product_live_home "$product")"
    case "$product" in
      claude) preflight_claude_plugin_registry "$live_home" ;;
      codex) preflight_codex_plugin_registry "$live_home" ;;
      hermes) : ;;
      *)
        err "unknown product: $product"
        return 2
        ;;
    esac
  done
}

# Read the skipped count from one prune-stale JSON blob, accumulate it into the
# run-wide total, and surface the skipped rel_paths so the operator sees exactly
# which stale candidates prune-stale could not auto-remove. prune-stale only
# removes provably owned symlinks and empty directories; a retired recursive-file
# managed skill directory (real files, non-empty dir) is reported as skipped and
# left in place, so a blind prune=ok is misleading. See the inbox case
# core/policies/heuristic-system/error-inbox/sync-runtime-surfaces-prune-stale-dir-gap.
# Sets PRUNE_LAST_SKIPPED and bumps PRUNE_SKIPPED_TOTAL.
account_prune_skipped() {
  local product="$1"
  local json="$2"
  local skipped

  skipped="$(printf '%s\n' "$json" | json_number skipped)"
  : "${skipped:=0}"
  PRUNE_LAST_SKIPPED="$skipped"

  if [ "$skipped" -gt 0 ]; then
    PRUNE_SKIPPED_TOTAL=$((PRUNE_SKIPPED_TOTAL + skipped))
    local phrase="left stale candidate for review"
    if [ "$product" = "hermes" ]; then
      phrase="left non-kit-managed path untouched"
    fi
    printf '%s\n' "$json" |
      sed -n 's/.*"rel_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/  ? prune-stale '"$phrase"' (product='"$product"'): \1/p'
  fi
}

retired_managed_skill_ids() {
  python3 - \
    "$SOURCE_ROOT/manifests/retired-skill-ids.json" \
    "$SOURCE_ROOT/manifests/retired-hermes-skill-copies.json" <<'PY'
import json
import re
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    hermes = json.load(handle)
if data.get("schema") != "agent-runtime-kit.retired-skill-ids.v1":
    raise SystemExit("retired managed skill manifest has unsupported schema")
skills = data.get("skills")
if not isinstance(skills, list) or not skills or len(skills) != len(set(skills)):
    raise SystemExit("retired managed skill manifest has invalid skills list")
if hermes.get("schema") != "agent-runtime-kit.retired-hermes-skill-copies.v1":
    raise SystemExit("retired Hermes copy manifest has unsupported schema")
digests = hermes.get("skills")
if not isinstance(digests, dict) or list(digests) != skills:
    raise SystemExit("retired Hermes copy manifest IDs differ from canonical retired skill IDs")
for skill_id in skills:
    if re.fullmatch(
        r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?",
        skill_id,
    ) is None:
        raise SystemExit("retired managed skill manifest has invalid skill id")
    print(skill_id)
PY
}

retired_skill_link_tree_is_owned() {
  local product="$1"
  local domain="$2"
  local skill="$3"
  local skill_dir="$4"
  local suffix="/build/$product/plugins/$domain/skills/$skill"
  local link_path
  local target_path
  local candidate_root
  local rel_link
  local rel_target
  local link_count=0

  if find "$skill_dir" -mindepth 1 ! -type d ! -type l -print -quit | grep -q .; then
    return 1
  fi
  while IFS= read -r link_path; do
    [ -n "$link_path" ] || continue
    target_path="$(resolve_symlink_target "$link_path")" || return 1
    case "$target_path" in
      *"$suffix" | *"$suffix"/*) ;;
      *) return 1 ;;
    esac
    candidate_root="${target_path%%"$suffix"*}"
    [ -n "$candidate_root" ] || return 1
    rel_link="${link_path#"$skill_dir"}"
    rel_link="${rel_link#/}"
    rel_target="${target_path#"$candidate_root$suffix"}"
    rel_target="${rel_target#/}"
    [ "$rel_link" = "$rel_target" ] || return 1
    is_managed_runtime_kit_checkout_root "$candidate_root" || return 1
    link_count=$((link_count + 1))
  done < <(find "$skill_dir" -type l -print)
  [ "$link_count" -gt 0 ]
}

retired_plugin_link_tree_is_owned() {
  local product="$1"
  local domain="$2"
  local plugin_dir="$3"
  local link_path
  local target_path
  local candidate_root
  local suffix
  local rel_link
  local rel_target
  local link_count=0

  if find "$plugin_dir" -mindepth 1 ! -type d ! -type l -print -quit | grep -q .; then
    return 1
  fi
  while IFS= read -r link_path; do
    [ -n "$link_path" ] || continue
    target_path="$(resolve_symlink_target "$link_path")" || return 1
    suffix=""
    case "$target_path" in
      *"/build/$product/plugins/$domain" | *"/build/$product/plugins/$domain"/*)
        suffix="/build/$product/plugins/$domain"
        ;;
      *"/targets/$product/plugins/$domain" | *"/targets/$product/plugins/$domain"/*)
        suffix="/targets/$product/plugins/$domain"
        ;;
      *) return 1 ;;
    esac
    candidate_root="${target_path%%"$suffix"*}"
    [ -n "$candidate_root" ] || return 1
    rel_link="${link_path#"$plugin_dir"}"
    rel_link="${rel_link#/}"
    rel_target="${target_path#"$candidate_root$suffix"}"
    rel_target="${rel_target#/}"
    [ "$rel_link" = "$rel_target" ] || return 1
    is_managed_runtime_kit_checkout_root "$candidate_root" || return 1
    link_count=$((link_count + 1))
  done < <(find "$plugin_dir" -type l -print)
  [ "$link_count" -gt 0 ]
}

quarantine_validate_and_remove_retired_tree() {
  local tree_path="$1"
  local live_home="$2"
  local kind="$3"
  local product="$4"
  local domain="$5"
  local skill="${6:-}"

  python3 - "$SOURCE_ROOT" "$live_home" "$tree_path" "$kind" "$product" "$domain" "$skill" <<'PY'
import os
import pathlib
import stat
import subprocess
import sys

source_root, live_home, tree_path, kind, product, domain, skill = sys.argv[1:8]
open_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
fault_at = os.environ.get("AGENT_RUNTIME_KIT_TEST_RETIRE_CLEANUP_FAIL_AT", "")


class ReviewNeeded(Exception):
    pass


def git(root, *args):
    return subprocess.run(
        ["git", "-C", root, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def same_checkout(candidate):
    candidate = os.path.realpath(candidate)
    required = ("AGENT_HOME.md", "manifests/skills.yaml", "scripts/sync-runtime-surfaces.sh")
    if not all(os.path.isfile(os.path.join(candidate, item)) for item in required):
        return False
    top = git(candidate, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or os.path.realpath(top.stdout.decode().strip()) != candidate:
        return False
    if git(candidate, "ls-files", "--error-unmatch", "--", *required).returncode != 0:
        return False
    candidate_head = git(candidate, "rev-parse", "HEAD")
    source_head = git(source_root, "rev-parse", "HEAD")
    if candidate_head.returncode != 0 or source_head.returncode != 0:
        return False
    candidate_sha = candidate_head.stdout.decode().strip()
    source_sha = source_head.stdout.decode().strip()
    if git(source_root, "cat-file", "-e", candidate_sha + "^{commit}").returncode != 0:
        return False
    if (
        git(source_root, "merge-base", "--is-ancestor", candidate_sha, source_sha).returncode == 0
        or git(source_root, "merge-base", "--is-ancestor", source_sha, candidate_sha).returncode == 0
    ):
        return True
    origin = git(source_root, "config", "--local", "--null", "--get-all", "remote.origin.url")
    if origin.returncode != 0:
        return False
    records = origin.stdout.split(b"\0")
    if not records or records[-1] != b"":
        return False
    records.pop()
    if len(records) != 1:
        return False
    try:
        value = records[0].decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    if os.path.isabs(value):
        origin_path = value
    elif value.startswith(("./", "../")):
        origin_path = os.path.join(source_root, value)
    else:
        return False
    return os.path.isdir(origin_path) and os.path.realpath(origin_path) == candidate


def validate_link(raw_target, relative_link):
    original_parent = os.path.dirname(os.path.join(tree_path, relative_link))
    target = os.path.normpath(
        raw_target if os.path.isabs(raw_target) else os.path.join(original_parent, raw_target)
    )
    suffixes = (
        [f"/build/{product}/plugins/{domain}/skills/{skill}"]
        if kind == "skill"
        else [f"/build/{product}/plugins/{domain}", f"/targets/{product}/plugins/{domain}"]
    )
    for suffix in suffixes:
        marker = target.rfind(suffix)
        if marker <= 0:
            continue
        remainder = target[marker + len(suffix):]
        if remainder and not remainder.startswith("/"):
            continue
        if remainder.lstrip("/") != relative_link.replace(os.sep, "/"):
            continue
        if same_checkout(target[:marker]):
            return
    raise ReviewNeeded("symlink target is not an owned runtime-kit path")


def maybe_fail(point):
    if fault_at == point:
        raise OSError(f"injected retired cleanup failure at {point}")


def snapshot_dir(descriptor, relative=()):
    snapshot = []
    links = 0
    for name in sorted(os.listdir(descriptor)):
        metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        child_relative = relative + (name,)
        if stat.S_ISDIR(metadata.st_mode):
            snapshot.append((child_relative, "d", stat.S_IMODE(metadata.st_mode), None))
            child = os.open(name, open_flags, dir_fd=descriptor)
            try:
                child_snapshot, child_links = snapshot_dir(child, child_relative)
                snapshot.extend(child_snapshot)
                links += child_links
            finally:
                os.close(child)
        elif stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(name, dir_fd=descriptor)
            validate_link(target, "/".join(child_relative))
            snapshot.append((child_relative, "l", None, target))
            links += 1
        else:
            raise ReviewNeeded("retired managed tree contains a non-symlink object")
    return snapshot, links


def delete_dir(descriptor):
    for name in sorted(os.listdir(descriptor)):
        metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            child = os.open(name, open_flags, dir_fd=descriptor)
            try:
                delete_dir(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=descriptor)
            maybe_fail("during-delete")
        elif stat.S_ISLNK(metadata.st_mode):
            os.unlink(name, dir_fd=descriptor)
            maybe_fail("during-delete")
        else:
            raise ReviewNeeded("quarantined tree changed after validation")


def open_snapshot_dir(root_fd, parts):
    descriptor = os.dup(root_fd)
    try:
        for part in parts:
            child = os.open(part, open_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def restore_snapshot(root_fd, snapshot):
    directories = [entry for entry in snapshot if entry[1] == "d"]
    links = [entry for entry in snapshot if entry[1] == "l"]
    for relative, _, mode, _ in sorted(directories, key=lambda entry: len(entry[0])):
        parent = open_snapshot_dir(root_fd, relative[:-1])
        try:
            name = relative[-1]
            try:
                metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                os.mkdir(name, mode=mode, dir_fd=parent)
                metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(metadata.st_mode):
                raise OSError("rollback directory path changed type")
        finally:
            os.close(parent)
    for relative, _, _, target in links:
        parent = open_snapshot_dir(root_fd, relative[:-1])
        try:
            name = relative[-1]
            try:
                metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                os.symlink(target, name, dir_fd=parent)
            else:
                if not stat.S_ISLNK(metadata.st_mode) or os.readlink(name, dir_fd=parent) != target:
                    raise OSError("rollback symlink path changed")
        finally:
            os.close(parent)
    for relative, _, mode, _ in sorted(
        directories, key=lambda entry: len(entry[0]), reverse=True
    ):
        descriptor = open_snapshot_dir(root_fd, relative)
        try:
            os.fchmod(descriptor, mode)
        finally:
            os.close(descriptor)


def restore_and_rename(parent_fd, leaf, quarantine, candidate_fd, root_mode, snapshot):
    descriptor = candidate_fd
    if descriptor is None:
        descriptor = os.open(quarantine, open_flags, dir_fd=parent_fd)
    try:
        if snapshot is not None:
            restore_snapshot(descriptor, snapshot)
        os.fchmod(descriptor, root_mode)
    finally:
        os.close(descriptor)
    try:
        os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise OSError("rollback destination already exists")
    os.rename(quarantine, leaf, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    print("restored retired managed tree after cleanup failure", file=sys.stderr)


live = pathlib.Path(live_home)
tree = pathlib.Path(tree_path)
try:
    relative = tree.relative_to(live)
except ValueError:
    raise SystemExit(1)
if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
    raise SystemExit(1)

descriptors = []
quarantine_name = f".{relative.name}.agent-runtime-kit-retired.{os.getpid()}"
renamed = False
tree_fd = None
original_mode = None
snapshot = None
try:
    current = os.open(live_home, open_flags)
    descriptors.append(current)
    for component in relative.parts[:-1]:
        current = os.open(component, open_flags, dir_fd=current)
        descriptors.append(current)
    parent_fd = current
    leaf = relative.parts[-1]
    candidate_metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(candidate_metadata.st_mode):
        raise ReviewNeeded("candidate is not a directory")
    original_mode = stat.S_IMODE(candidate_metadata.st_mode)
    try:
        os.stat(quarantine_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise ReviewNeeded("quarantine collision")
    os.rename(leaf, quarantine_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    renamed = True
    maybe_fail("after-rename")
    tree_fd = os.open(quarantine_name, open_flags, dir_fd=parent_fd)
    os.fchmod(tree_fd, 0o700)
    snapshot, link_count = snapshot_dir(tree_fd)
    if link_count == 0:
        raise ReviewNeeded("retired managed tree contains no symlinks")
    delete_dir(tree_fd)
    maybe_fail("before-rmdir")
    os.close(tree_fd)
    tree_fd = None
    os.rmdir(quarantine_name, dir_fd=parent_fd)
    renamed = False
except ReviewNeeded as exc:
    print(f"review-needed descriptor-bound retired tree: {exc}", file=sys.stderr)
    if renamed:
        try:
            restore_and_rename(
                descriptors[-1], relative.parts[-1], quarantine_name,
                tree_fd, original_mode, snapshot,
            )
            tree_fd = None
            renamed = False
        except OSError as rollback_exc:
            tree_fd = None
            print(f"retired managed cleanup rollback failed: {rollback_exc}", file=sys.stderr)
            raise SystemExit(1)
    raise SystemExit(3)
except OSError as exc:
    print(f"retired managed descriptor cleanup failed: {exc}", file=sys.stderr)
    if renamed:
        try:
            restore_and_rename(
                descriptors[-1], relative.parts[-1], quarantine_name,
                tree_fd, original_mode, snapshot,
            )
            tree_fd = None
            renamed = False
        except OSError as rollback_exc:
            tree_fd = None
            print(f"retired managed cleanup rollback failed: {rollback_exc}", file=sys.stderr)
    raise SystemExit(1)
finally:
    if tree_fd is not None:
        os.close(tree_fd)
    for descriptor in reversed(descriptors):
        os.close(descriptor)
PY
}

cleanup_retired_managed_product_links() {
  local product="$1"
  local live_home="$2"
  local managed_root
  local skill_id
  local domain
  local skill
  local skill_dir
  local domain_dir
  local removed_skills=0
  local removed_plugins=0
  local review_needed=0
  local retired_ids
  local retired_domains

  case "$product" in
    codex | claude) managed_root="$live_home/plugins" ;;
    hermes) managed_root="$live_home/external-skills/agent-runtime-kit" ;;
    *)
      err "unknown product for retired managed link cleanup: $product"
      return 2
      ;;
  esac
  [ -d "$managed_root" ] || return 0

  if ! retired_ids="$(retired_managed_skill_ids)" || [ -z "$retired_ids" ]; then
    err "retired managed skill manifest preflight failed; refusing cleanup"
    return 1
  fi

  while IFS= read -r skill_id; do
    [ -n "$skill_id" ] || continue
    domain="${skill_id%%.*}"
    skill="${skill_id#*.}"
    case "$product" in
      codex | claude) skill_dir="$managed_root/$domain/skills/$skill" ;;
      hermes) skill_dir="$managed_root/$domain/$skill" ;;
    esac
    [ -d "$skill_dir" ] || continue
    if [ "$APPLY" = "0" ]; then
      if retired_skill_link_tree_is_owned "$product" "$domain" "$skill" "$skill_dir"; then
        log "would remove retired managed skill link tree product=$product path=$skill_dir"
        removed_skills=$((removed_skills + 1))
      else
        log "review-needed retired managed skill link tree product=$product path=$skill_dir"
        review_needed=$((review_needed + 1))
      fi
    elif quarantine_validate_and_remove_retired_tree \
      "$skill_dir" "$live_home" skill "$product" "$domain" "$skill"; then
      log "removed retired managed skill link tree product=$product path=$skill_dir"
      removed_skills=$((removed_skills + 1))
    else
      log "review-needed retired managed skill link tree product=$product path=$skill_dir"
      review_needed=$((review_needed + 1))
    fi
  done <<EOF_RETIRED_MANAGED_SKILLS
$retired_ids
EOF_RETIRED_MANAGED_SKILLS

  if [ "$product" = "codex" ] || [ "$product" = "claude" ]; then
    retired_domains="$(printf '%s\n' "$retired_ids" | sed 's/\..*//' | sort -u)"
    while IFS= read -r domain; do
      [ -n "$domain" ] || continue
      domain_dir="$managed_root/$domain"
      [ -d "$domain_dir" ] || continue
      if find "$SOURCE_ROOT/targets/$product/plugins/$domain" -type f -print -quit 2>/dev/null | grep -q .; then
        continue
      fi
      if [ "$APPLY" = "0" ]; then
        if retired_plugin_link_tree_is_owned "$product" "$domain" "$domain_dir"; then
          log "would remove retired managed plugin link tree product=$product path=$domain_dir"
          removed_plugins=$((removed_plugins + 1))
        elif find "$domain_dir" -mindepth 1 -print -quit | grep -q .; then
          log "review-needed retired managed plugin link tree product=$product path=$domain_dir"
          review_needed=$((review_needed + 1))
        fi
      elif quarantine_validate_and_remove_retired_tree \
        "$domain_dir" "$live_home" plugin "$product" "$domain"; then
        log "removed retired managed plugin link tree product=$product path=$domain_dir"
        removed_plugins=$((removed_plugins + 1))
      elif find "$domain_dir" -mindepth 1 -print -quit | grep -q .; then
        log "review-needed retired managed plugin link tree product=$product path=$domain_dir"
        review_needed=$((review_needed + 1))
      fi
    done <<EOF_RETIRED_PLUGIN_DOMAINS
$retired_domains
EOF_RETIRED_PLUGIN_DOMAINS
  else
    for domain_dir in "$managed_root"/*; do
      [ -d "$domain_dir" ] || continue
      if ! find "$domain_dir" -mindepth 1 -print -quit | grep -q .; then
        run_cmd rmdir "$domain_dir"
      fi
    done
  fi

  log "retired managed link cleanup product=$product skills=$removed_skills plugins=$removed_plugins review_needed=$review_needed"
  if [ "$review_needed" -gt 0 ] && [ "$APPLY" = "1" ]; then
    return 3
  fi
  return 0
}

cleanup_codex_legacy_flat_skill_root() {
  local live_home="$1"
  local legacy_root="$live_home/skills"

  if [ ! -d "$legacy_root" ]; then
    return 0
  fi

  log "cleaning retired Codex flat skill root live_home=$live_home"
  print_cmd python3 - "$SOURCE_ROOT" "$legacy_root" "$APPLY"
  python3 - "$SOURCE_ROOT" "$legacy_root" "$APPLY" <<'PY'
import os
import pathlib
import sys

source_root = pathlib.Path(sys.argv[1]).resolve()
legacy_root = pathlib.Path(sys.argv[2])
apply = sys.argv[3] == "1"
build_plugins = (source_root / "build" / "codex" / "plugins").resolve()
removed_symlinks = 0
candidate_dirs = set()

if not legacy_root.exists():
    sys.exit(0)

for domain_dir in sorted(legacy_root.iterdir()):
    if domain_dir.is_symlink() or not domain_dir.is_dir():
        continue
    for skill_path in sorted(domain_dir.iterdir()):
        if not skill_path.is_symlink():
            continue
        target_raw = os.readlink(skill_path)
        if os.path.isabs(target_raw):
            target_path = pathlib.Path(target_raw)
        else:
            target_path = skill_path.parent / target_raw
        target_path = target_path.resolve(strict=False)
        try:
            rel_target = target_path.relative_to(build_plugins)
        except ValueError:
            continue
        if len(rel_target.parts) != 3 or rel_target.parts[1] != "skills":
            continue
        if domain_dir.name != rel_target.parts[0] or skill_path.name != rel_target.parts[2]:
            continue

        rel_live = skill_path.relative_to(legacy_root.parent)
        if apply:
            skill_path.unlink()
            print(f"removed legacy Codex flat skill symlink {rel_live}")
        else:
            print(f"would remove legacy Codex flat skill symlink {rel_live}")
        removed_symlinks += 1
        candidate_dirs.add(domain_dir)

for domain_dir in sorted(candidate_dirs):
    try:
        is_empty = not any(domain_dir.iterdir())
    except FileNotFoundError:
        continue
    if not is_empty:
        continue
    rel_live = domain_dir.relative_to(legacy_root.parent)
    if apply:
        domain_dir.rmdir()
        print(f"removed empty legacy Codex flat skill directory {rel_live}")
    else:
        print(f"would remove empty legacy Codex flat skill directory {rel_live}")

status = "removed" if apply else "planned"
print(f"legacy Codex flat skill cleanup {status}: symlinks={removed_symlinks}")
PY
}

cleanup_hermes_legacy_runtime_kit_skill_root() {
  local live_home="$1"
  local legacy_root="$live_home/skills"

  if [ ! -d "$legacy_root" ]; then
    return 0
  fi

  log "cleaning retired Hermes local runtime-kit skill links live_home=$live_home"
  print_cmd python3 - "$SOURCE_ROOT" "$legacy_root" "$APPLY"
python3 - "$SOURCE_ROOT" "$legacy_root" "$APPLY" <<'PY'
import os
import hashlib
import json
import pathlib
import shutil
import sys

source_root = pathlib.Path(sys.argv[1]).resolve()
legacy_root = pathlib.Path(sys.argv[2])
apply = sys.argv[3] == "1"
build_plugins = (source_root / "build" / "hermes" / "plugins").resolve()
retired_manifest_path = source_root / "manifests" / "retired-hermes-skill-copies.json"
retired_ids_path = source_root / "manifests" / "retired-skill-ids.json"
try:
    retired_manifest = json.loads(retired_manifest_path.read_text(encoding="utf-8"))
    retired_ids_manifest = json.loads(retired_ids_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"cannot read retired Hermes copy manifest: {exc}")
if retired_manifest.get("schema") != "agent-runtime-kit.retired-hermes-skill-copies.v1":
    raise SystemExit("retired Hermes copy manifest has unsupported schema")
if retired_ids_manifest.get("schema") != "agent-runtime-kit.retired-skill-ids.v1":
    raise SystemExit("retired skill ID manifest has unsupported schema")
retired_ids = retired_ids_manifest.get("skills")
if not isinstance(retired_ids, list) or not retired_ids or len(retired_ids) != len(set(retired_ids)):
    raise SystemExit("retired skill ID manifest has invalid skills list")
retired_copy_digests = retired_manifest.get("skills")
if not isinstance(retired_copy_digests, dict):
    raise SystemExit("retired Hermes copy manifest has invalid skills map")
if list(retired_copy_digests) != retired_ids:
    raise SystemExit("retired Hermes copy manifest IDs differ from canonical retired skill IDs")
removed_symlinks = 0
removed_copies = 0
review_needed = 0
candidate_dirs = set()
copy_removal_roots = []
review_needed_roots = []

if not legacy_root.exists():
    sys.exit(0)


def remember_cleanup_dirs(path, stop):
    cleanup_dir = path
    while cleanup_dir != legacy_root and cleanup_dir != legacy_root.parent:
        candidate_dirs.add(cleanup_dir)
        if cleanup_dir == stop:
            break
        cleanup_dir = cleanup_dir.parent


def trees_match(left, right):
    for root, dirnames, filenames in os.walk(left):
        current = pathlib.Path(root)
        rel = current.relative_to(left)
        expected_current = right / rel
        if not expected_current.is_dir():
            return False

        if any((current / name).is_symlink() for name in dirnames + filenames):
            return False

        expected_dirs = sorted(path.name for path in expected_current.iterdir() if path.is_dir())
        expected_files = sorted(path.name for path in expected_current.iterdir() if path.is_file())
        if sorted(dirnames) != expected_dirs or sorted(filenames) != expected_files:
            return False

        for filename in filenames:
            actual_file = current / filename
            expected_file = expected_current / filename
            if actual_file.read_bytes() != expected_file.read_bytes():
                return False
    return True


def tree_digest(root):
    entries = []
    for path in root.rglob("*"):
        if path.is_symlink():
            return None
        if path.is_dir():
            entry_type = "d"
            content = None
        elif path.is_file():
            entry_type = "f"
            content = path.read_bytes()
        else:
            return None
        entries.append(
            (
                path.relative_to(root).as_posix(),
                entry_type,
                "0755"
                if entry_type == "d" or path.stat().st_mode & 0o111
                else "0644",
                content,
            )
        )
    digest = hashlib.sha256()
    for relative, entry_type, mode, content in sorted(entries):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry_type.encode("ascii"))
        digest.update(b"\0")
        digest.update(mode.encode("ascii"))
        digest.update(b"\0")
        if content is not None:
            digest.update(str(len(content)).encode("ascii"))
            digest.update(b"\0")
            digest.update(content)
    return digest.hexdigest()


# Classify each complete skill tree before any apply-mode deletion. In
# particular, a managed active/retired tree containing a local symlink is a
# modified copy and must remain byte-for-byte and link-for-link untouched for
# operator review.
for domain_dir in sorted(legacy_root.iterdir()):
    if domain_dir.is_symlink() or not domain_dir.is_dir():
        continue
    for skill_dir in sorted(domain_dir.iterdir()):
        if skill_dir.is_symlink() or not skill_dir.is_dir():
            continue
        # A tree made only of managed symlinks is the old link layout handled
        # by the targeted traversal below, not a copied skill tree. Any real
        # file makes this a copy whose complete contents must be classified.
        if not any(
            path.is_file() and not path.is_symlink()
            for path in skill_dir.rglob("*")
        ):
            continue
        expected_skill_dir = build_plugins / domain_dir.name / "skills" / skill_dir.name
        skill_id = f"{domain_dir.name}.{skill_dir.name}"
        exact_active_copy = expected_skill_dir.is_dir() and trees_match(skill_dir, expected_skill_dir)
        retired_digest = retired_copy_digests.get(skill_id)
        exact_retired_copy = (
            not expected_skill_dir.is_dir()
            and isinstance(retired_digest, str)
            and tree_digest(skill_dir) == retired_digest
        )
        if exact_active_copy or exact_retired_copy:
            copy_removal_roots.append((skill_dir, domain_dir))
            continue
        if expected_skill_dir.is_dir() or isinstance(retired_digest, str):
            review_needed += 1
            review_needed_roots.append(skill_dir)
            rel_live = skill_dir.relative_to(legacy_root.parent)
            print(f"review-needed legacy Hermes runtime-kit skill copy {rel_live}")


for domain_dir in sorted(legacy_root.iterdir()):
    if domain_dir.is_symlink() or not domain_dir.is_dir():
        continue
    for dirpath, dirnames, filenames in os.walk(domain_dir):
        current = pathlib.Path(dirpath)
        for filename in sorted(filenames):
            link_path = current / filename
            if not link_path.is_symlink():
                continue
            target_raw = os.readlink(link_path)
            if os.path.isabs(target_raw):
                target_path = pathlib.Path(target_raw)
            else:
                target_path = link_path.parent / target_raw
            target_path = target_path.resolve(strict=False)
            try:
                rel_target = target_path.relative_to(build_plugins)
            except ValueError:
                continue
            if len(rel_target.parts) < 4 or rel_target.parts[1] != "skills":
                continue
            if domain_dir.name != rel_target.parts[0]:
                continue
            if any(
                review_root == link_path or review_root in link_path.parents
                for review_root in review_needed_roots
            ):
                continue

            rel_live = link_path.relative_to(legacy_root.parent)
            if apply:
                link_path.unlink()
                print(f"removed legacy Hermes runtime-kit skill symlink {rel_live}")
            else:
                print(f"would remove legacy Hermes runtime-kit skill symlink {rel_live}")
            removed_symlinks += 1
            remember_cleanup_dirs(link_path.parent, domain_dir)

for skill_dir, domain_dir in copy_removal_roots:
    rel_live = skill_dir.relative_to(legacy_root.parent)
    if apply:
        shutil.rmtree(skill_dir)
        print(f"removed legacy Hermes runtime-kit skill copy {rel_live}")
    else:
        print(f"would remove legacy Hermes runtime-kit skill copy {rel_live}")
    removed_copies += 1
    remember_cleanup_dirs(skill_dir, domain_dir)

for path in sorted(candidate_dirs, key=lambda item: len(item.parts), reverse=True):
    if path == legacy_root or not path.exists() or path.is_symlink():
        continue
    try:
        is_empty = not any(path.iterdir())
    except FileNotFoundError:
        continue
    if not is_empty:
        continue
    rel_live = path.relative_to(legacy_root.parent)
    if apply:
        path.rmdir()
        print(f"removed empty legacy Hermes runtime-kit skill directory {rel_live}")
    else:
        print(f"would remove empty legacy Hermes runtime-kit skill directory {rel_live}")

status = "removed" if apply else "planned"
print(
    f"legacy Hermes runtime-kit skill cleanup {status}: "
    f"symlinks={removed_symlinks} copies={removed_copies} review_needed={review_needed}"
)
if review_needed:
    raise SystemExit(3)
PY
}

cleanup_hermes_legacy_runtime_kit_profile_roots() {
  local live_home="$1"
  local profiles_root="$live_home/profiles"
  local profile_home

  if [ ! -d "$profiles_root" ]; then
    return 0
  fi

  for profile_home in "$profiles_root"/*; do
    if [ -d "$profile_home/skills" ]; then
      cleanup_hermes_legacy_runtime_kit_skill_root "$profile_home"
    fi
  done
}

prune_product() {
  local product="$1"
  local live_home
  local prune_json
  local code
  local changes

  live_home="$(product_live_home "$product")"

  if [ "$NO_PRUNE" = "1" ]; then
    if [ "$APPLY" = "1" ]; then
      log "warning: prune skipped (--no-prune) for product=$product; stale managed runtime surfaces may remain"
    else
      log "prune skipped (--no-prune) for product=$product"
    fi
    return 0
  fi

  log "pruning stale managed surfaces product=$product live_home=$live_home"
  cleanup_retired_managed_product_links "$product" "$live_home"

  if [ "$APPLY" = "0" ]; then
    run_cmd agent-runtime prune-stale \
      --source-root "$SOURCE_ROOT" \
      --product "$product" \
      --live-home "$live_home" \
      --dry-run
    if [ "$product" = "codex" ]; then
      cleanup_codex_legacy_flat_skill_root "$live_home"
    fi
    if [ "$product" = "hermes" ]; then
      cleanup_hermes_legacy_runtime_kit_skill_root "$live_home"
      cleanup_hermes_legacy_runtime_kit_profile_roots "$live_home"
    fi
    return 0
  fi

  print_cmd agent-runtime prune-stale \
    --source-root "$SOURCE_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --apply --format json

  set +e
  prune_json="$(agent-runtime prune-stale \
    --source-root "$SOURCE_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --apply --format json 2>&1)"
  code=$?
  set -e

  if [ "$code" -ne 0 ]; then
    printf '%s\n' "$prune_json" >&2
    err "prune-stale failed for product=$product (exit=$code); run agent-runtime prune-stale --product $product --live-home $live_home --apply for details"
    return 1
  fi

  changes="$(printf '%s\n' "$prune_json" | json_number changes)"
  account_prune_skipped "$product" "$prune_json"
  if [ "$product" = "codex" ]; then
    cleanup_codex_legacy_flat_skill_root "$live_home"
  fi
  if [ "$product" = "hermes" ]; then
    cleanup_hermes_legacy_runtime_kit_skill_root "$live_home"
    cleanup_hermes_legacy_runtime_kit_profile_roots "$live_home"
  fi
  log "prune product=$product changes=${changes:-0} skipped=${PRUNE_LAST_SKIPPED:-0}"
}

json_number() {
  local key="$1"
  sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\\([0-9][0-9]*\\).*/\\1/p" | head -n 1
}

doctor_product() {
  local product="$1"
  local live_home
  local state_home
  local doctor_json
  local code
  local block
  local checks
  local exit_code

  live_home="$(product_live_home "$product")"
  state_home="$(product_state_home "$product")"

  if [ "$APPLY" = "0" ]; then
    run_cmd agent-runtime doctor \
      --source-root "$SOURCE_ROOT" \
      --product "$product" \
      --live-home "$live_home" \
      --state-home "$state_home" \
      --class skill-surface \
      --format json
    return 0
  fi

  print_cmd agent-runtime doctor \
    --source-root "$SOURCE_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --class skill-surface \
    --format json

  set +e
  doctor_json="$(agent-runtime doctor \
    --source-root "$SOURCE_ROOT" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --class skill-surface \
    --format json 2>&1)"
  code=$?
  set -e

  block="$(printf '%s\n' "$doctor_json" | json_number block)"
  checks="$(printf '%s\n' "$doctor_json" | json_number checks)"
  exit_code="$(printf '%s\n' "$doctor_json" | json_number exit_code)"

  if [ "$code" -ne 0 ] || [ -z "$block" ] || [ "$block" -gt 0 ]; then
    printf '%s\n' "$doctor_json" >&2
    err "doctor failed for product=$product (exit=$code block=${block:-unknown}); run agent-runtime doctor --product $product --class skill-surface --format json for details"
    return 1
  fi

  log "doctor product=$product ok (checks=${checks:-unknown} block=$block exit=${exit_code:-$code})"
}

verify_codex_prompt_input() {
  if ! selected_includes_codex; then
    CODEX_PROMPT_STATUS="skipped"
    log "codex prompt-input skipped (product=$PRODUCT)"
    return 0
  fi

  if ! command -v codex >/dev/null 2>&1; then
    CODEX_PROMPT_STATUS="skipped"
    log "codex prompt-input skipped (binary not on PATH)"
    return 0
  fi

  if [ "$APPLY" = "0" ]; then
    CODEX_PROMPT_STATUS="planned"
    run_cmd codex debug prompt-input
    return 0
  fi

  CODEX_PROMPT_STATUS="verified"
  run_cmd codex debug prompt-input
}

run_verification() {
  local product

  if [ "$NO_VERIFY" = "1" ]; then
    CODEX_PROMPT_STATUS="skipped"
    log "verification skipped (--no-verify)"
    return 0
  fi

  for product in $(selected_products); do
    doctor_product "$product"
  done

  verify_codex_prompt_input
}

print_summary() {
  local mode="dry-run"
  local doctor_status="planned"
  local prune_status="planned"

  if [ "$APPLY" = "1" ]; then
    mode="apply"
    doctor_status="ok"
    prune_status="ok"
    if [ "$PRUNE_SKIPPED_TOTAL" -gt 0 ]; then
      prune_status="review-needed"
    fi
  fi
  if [ "$NO_PRUNE" = "1" ]; then
    prune_status="skipped"
  fi
  if [ "$NO_VERIFY" = "1" ]; then
    doctor_status="skipped"
  fi

  log "summary: synced surfaces for $(product_label); mode=$mode; prune=$prune_status; doctor=$doctor_status; codex prompt-input=$CODEX_PROMPT_STATUS; codex plugins=$CODEX_PLUGIN_STATUS; claude plugins=$CLAUDE_PLUGIN_STATUS; home-prompt=$HOME_PROMPT_STATUS"

  if [ "$prune_status" = "review-needed" ]; then
    case "$PRODUCT" in
      hermes | both)
        log "note: prune-stale left $PRUNE_SKIPPED_TOTAL path(s) it does not own (real files / non-empty dirs that are not kit-owned symlinks); they were left untouched. Hermes runtime-kit skills are expected under external-skills/agent-runtime-kit. Any leftover local skills/<domain> entries are Hermes-native or historical content and must be reviewed before deletion; do not remove them blindly. Background: heuristic-system case sync-runtime-surfaces-prune-stale-dir-gap (archived)."
        ;;
      *)
        log "note: prune-stale left $PRUNE_SKIPPED_TOTAL path(s) it does not own (real files / non-empty dirs that are not kit-owned symlinks); they were left untouched. Review the paths above and remove any retired managed skill directory by hand. Background: heuristic-system case sync-runtime-surfaces-prune-stale-dir-gap (archived)."
        ;;
    esac
  fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
  local product

  parse_args "$@"
  require_commands git python3
  resolve_source_root
  validate_live_sync_source_root

  if [ "$APPLY" = "1" ]; then
    require_commands agent-runtime
  fi

  log "$PROG_NAME starting (source_root=$SOURCE_ROOT product=$PRODUCT apply=$APPLY no_pull=$NO_PULL no_prune=$NO_PRUNE no_verify=$NO_VERIFY)"

  pull_source
  check_source_counts
  preflight_selected_product_activation
  render_home_prompt_base
  for product in $(selected_products); do
    render_home_prompt_product "$product"
    ensure_home_prompt "$product"
    render_product "$product"
    install_product "$product"
    prune_product "$product"
    sync_product_activation "$product"
  done
  run_verification
  print_summary
}

# Allow tests to source this script as a library (to exercise helpers like
# account_prune_skipped / print_summary in isolation) without running main.
if [ "${SYNC_RUNTIME_SURFACES_LIB:-0}" != "1" ]; then
  main "$@"
fi
