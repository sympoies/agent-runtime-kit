#!/usr/bin/env bash
# scripts/sync-private-skills.sh - overlay private project-local skills into
# the live Codex and Claude runtime homes.
#
# This is a deliberately thin companion to sync-runtime-surfaces.sh. It does NOT
# render, install through nils-cli, or touch any runtime-kit manifest. It only
# symlinks already-native project-local skills (the create-project-skill layout:
# <home>/.agents/skills/<name>/SKILL.md) from a PRIVATE source tree into the
# global per-user skill directories that Codex and Claude discover directly:
#
#   Codex : $CODEX_HOME/skills/<name>      (default $HOME/.codex/skills/<name>)
#   Claude: $HOME/.claude/skills/<name>    (personal global skill namespace)
#   Hermes: $HOME/.hermes/external-skills/private/<name>
#
# The Hermes target is presence-gated: it participates in the default product
# set only when $HOME/.hermes exists. Hermes does not read that directory by
# itself — it must be registered once as a read-only external skills root in
# each Hermes profile config (skills.external_dirs). The overlay checks the
# configs it can see and prints the registration snippet when missing. The
# external-dirs mount (rather than $HERMES_HOME/skills) matters: local Hermes
# skills are curated autonomously by the agent, and a symlinked local skill
# would let that maintenance write through into the private source repo.
# External dirs are Hermes's declared externally-owned, read-only boundary.
#
# None of the targets collide with the runtime-kit managed surface: runtime-kit
# installs Codex skills as domain dirs under $CODEX_HOME/skills and Claude skills
# under $HOME/.claude/plugins/<domain>/skills. The runtime-kit prune step is
# scoped to its own managed entries, so private overlay symlinks survive it.
#
# Private skill SOURCE lives OUTSIDE this repo (e.g. a private git checkout) and
# is located via $AGENT_PRIVATE_SKILLS_HOME. When that env is unset, every step
# is a no-op, so this script is a safe fallback on hosts with no private tree.
#
# Compatibility: must run on macOS (system bash 3.2) and Linux (bash 4+).
# Avoid associative arrays, mapfile, and `${var,,}` lowercasing.

set -euo pipefail

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

readonly PROG_NAME="sync-private-skills.sh"

APPLY=0
PRODUCT="all"
PRUNE=0
PRIVATE_HOME="${AGENT_PRIVATE_SKILLS_HOME:-}"
LINKED=0
SKIPPED=0
PRUNED=0

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------

print_help() {
  cat <<EOF
Usage: $PROG_NAME [--apply] [--product codex|claude|hermes|all] [--private-home PATH] [--prune]

Overlay private project-local skills into the live Codex, Claude, and Hermes
runtime homes by symlinking <private-home>/.agents/skills/<name> into each
product's skill directory.

The private source tree is located via \$AGENT_PRIVATE_SKILLS_HOME (a
create-project-skill root containing .agents/skills/). When that env is unset
and --private-home is not given, this script reports "no private home" and
exits 0 without touching anything.

By default this command is a dry-run: it prints the symlink / prune commands
without mutating runtime homes. Pass --apply to run them.

Options:
  --apply
      Execute the overlay. Without this flag, commands are printed only.
  --product codex|claude|hermes|all
      Limit the overlay to one product. Default: all. In the default set the
      hermes target is presence-gated (skipped unless \$HOME/.hermes exists);
      an explicit --product hermes on a host without \$HOME/.hermes is an
      error. "both" is accepted as a legacy alias for "all".
      Hermes links land in \$HOME/.hermes/external-skills/private/<name>; that
      root must be registered once per Hermes profile config under
      skills.external_dirs (the script prints the snippet when unregistered).
  --private-home PATH
      Use a specific private skills root, overriding \$AGENT_PRIVATE_SKILLS_HOME.
  --prune
      Remove stale overlay symlinks: target-home entries that are symlinks
      pointing into the private home but whose source skill no longer exists.
      Only ever removes symlinks this script owns; never touches real
      directories or foreign symlinks.
  -h, --help
      Print this help and exit.
EOF
}

# -----------------------------------------------------------------------------
# Logging helpers (mirrors sync-runtime-surfaces.sh house style)
# -----------------------------------------------------------------------------

log() { printf '%s\n' "$*"; }
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
# Arg parsing
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
      --private-home)
        if [ "$#" -lt 2 ]; then
          err "--private-home requires a value"
          exit 2
        fi
        PRIVATE_HOME="$2"
        shift 2
        ;;
      --private-home=*)
        PRIVATE_HOME="${1#--private-home=}"
        shift
        ;;
      --prune)
        PRUNE=1
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
    both)
      # Legacy alias from the two-product era.
      PRODUCT="all"
      ;;
    codex | claude | hermes | all) ;;
    *)
      err "invalid --product value: $PRODUCT (expected codex|claude|hermes|all)"
      exit 2
      ;;
  esac
}

# -----------------------------------------------------------------------------
# Path resolution
# -----------------------------------------------------------------------------

# Portable absolute-path resolver (no realpath/readlink -f on macOS bash 3.2).
abs_path() {
  local path="$1"
  if [ -d "$path" ]; then
    (cd "$path" && pwd)
  else
    local dir base
    dir="$(dirname "$path")"
    base="$(basename "$path")"
    printf '%s/%s\n' "$(cd "$dir" && pwd)" "$base"
  fi
}

# The Hermes base is deliberately fixed to $HOME/.hermes: Hermes gateway
# processes export HERMES_HOME pointing at per-profile subdirectories, so
# honoring that env here would scatter the shared external root per profile.
hermes_home() {
  printf '%s\n' "$HOME/.hermes"
}

hermes_available() {
  [ -d "$(hermes_home)" ]
}

selected_products() {
  case "$PRODUCT" in
    codex) printf '%s\n' codex ;;
    claude) printf '%s\n' claude ;;
    hermes) printf '%s\n' hermes ;;
    all)
      printf '%s\n' codex
      printf '%s\n' claude
      if hermes_available; then
        printf '%s\n' hermes
      fi
      ;;
  esac
}

product_skills_dir() {
  case "$1" in
    claude) printf '%s\n' "$HOME/.claude/skills" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    hermes) printf '%s\n' "$(hermes_home)/external-skills/private" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

# Hermes only reads the external-skills root when a profile config registers
# it under skills.external_dirs. Best-effort check: look for the literal root
# name in every profile config we can see and print the snippet when any is
# missing it. Read-only, so it runs in dry-run mode too.
hermes_config_hint() {
  local base cfg missing=""
  base="$(hermes_home)"
  # The base profile config is always expected; per-profile configs are only
  # checked when they exist (an unexpanded glob is skipped by the -f test).
  if [ ! -f "$base/config.yaml" ] || ! grep -q "external-skills" "$base/config.yaml"; then
    missing="${missing}  - ${base}/config.yaml
"
  fi
  for cfg in "$base"/profiles/*/config.yaml; do
    [ -f "$cfg" ] || continue
    if ! grep -q "external-skills" "$cfg"; then
      missing="${missing}  - ${cfg}
"
    fi
  done
  [ -n "$missing" ] || return 0
  log ""
  log "note [hermes]: the external-skills root is not registered in:"
  printf '%s' "$missing"
  log "  add to each profile's config.yaml:"
  log "    skills:"
  log "      external_dirs:"
  log "        - ~/.hermes/external-skills"
}

# Resolve the private skills root and the .agents/skills source dir.
SKILLS_SRC_DIR=""
resolve_private_home() {
  if [ -z "$PRIVATE_HOME" ]; then
    return 1
  fi
  if [ ! -d "$PRIVATE_HOME" ]; then
    err "private home does not exist: $PRIVATE_HOME"
    exit 2
  fi
  PRIVATE_HOME="$(abs_path "$PRIVATE_HOME")"
  SKILLS_SRC_DIR="$PRIVATE_HOME/.agents/skills"
  return 0
}

# -----------------------------------------------------------------------------
# Overlay
# -----------------------------------------------------------------------------

# Is $1 a symlink that resolves into the private home? (an overlay we own)
is_owned_overlay() {
  local target="$1"
  local resolved
  if [ ! -L "$target" ]; then
    return 1
  fi
  # Resolve the symlink's stored destination to an absolute path.
  resolved="$(cd "$(dirname "$target")" 2>/dev/null && abs_path "$(readlink "$target")" 2>/dev/null)" || return 1
  case "$resolved" in
    "$PRIVATE_HOME"/*) return 0 ;;
    *) return 1 ;;
  esac
}

ensure_skills_dir() {
  local dir="$1"
  if [ -d "$dir" ]; then
    return 0
  fi
  log "creating skills dir: $dir"
  run_cmd mkdir -p "$dir"
}

link_one() {
  local name="$1"
  local src="$2"
  local product="$3"
  local skills_dir target

  skills_dir="$(product_skills_dir "$product")"
  target="$skills_dir/$name"

  # Refuse to clobber anything we do not own: a real directory or a foreign
  # symlink at the target path is a collision (e.g. a runtime-kit domain dir
  # such as $CODEX_HOME/skills/meta). Skip it loudly.
  if [ -e "$target" ] || [ -L "$target" ]; then
    if is_owned_overlay "$target"; then
      : # ours; refresh below (ln -sfn is idempotent)
    else
      err "collision [$product]: $target exists and is not a private overlay; skipping '$name'"
      SKIPPED=$((SKIPPED + 1))
      return 0
    fi
  fi

  log "link [$product]: $name -> $src"
  run_cmd ln -sfn "$src" "$target"
  LINKED=$((LINKED + 1))
}

overlay_product() {
  local product="$1"
  local entry name src

  ensure_skills_dir "$(product_skills_dir "$product")"

  for entry in "$SKILLS_SRC_DIR"/*/; do
    [ -d "$entry" ] || continue
    name="$(basename "$entry")"
    src="${entry%/}"

    if [ ! -f "$src/SKILL.md" ]; then
      err "skip [$product]: $name has no SKILL.md (not a project-local skill)"
      SKIPPED=$((SKIPPED + 1))
      continue
    fi

    case "$name" in
      [a-z0-9]*) ;;
      *)
        err "skip [$product]: invalid skill dir name '$name' (must start lowercase/digit)"
        SKIPPED=$((SKIPPED + 1))
        continue
        ;;
    esac

    link_one "$name" "$src" "$product"
  done
}

prune_product() {
  local product="$1"
  local skills_dir entry name

  skills_dir="$(product_skills_dir "$product")"
  [ -d "$skills_dir" ] || return 0

  for entry in "$skills_dir"/*; do
    [ -L "$entry" ] || continue
    is_owned_overlay "$entry" || continue
    name="$(basename "$entry")"
    if [ ! -d "$SKILLS_SRC_DIR/$name" ]; then
      log "prune [$product]: stale overlay $name"
      run_cmd rm -f "$entry"
      PRUNED=$((PRUNED + 1))
    fi
  done
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
  parse_args "$@"
  require_commands ln basename dirname

  if ! resolve_private_home; then
    log "$PROG_NAME: no private home (AGENT_PRIVATE_SKILLS_HOME unset, no --private-home); nothing to do."
    exit 0
  fi

  if [ ! -d "$SKILLS_SRC_DIR" ]; then
    log "$PROG_NAME: no skills source at $SKILLS_SRC_DIR; nothing to overlay."
    log "  author private skills there with the create-project-skill layout:"
    log "    cd \"$PRIVATE_HOME\" && /create-project-skill --target codex <name>"
    exit 0
  fi

  if [ "$PRODUCT" = "hermes" ] && ! hermes_available; then
    err "--product hermes requested but $(hermes_home) does not exist"
    exit 2
  fi

  local mode="dry-run"
  [ "$APPLY" = "1" ] && mode="apply"
  log "$PROG_NAME: mode=$mode product=$PRODUCT private-home=$PRIVATE_HOME"
  log "source: $SKILLS_SRC_DIR"
  if [ "$PRODUCT" = "all" ] && ! hermes_available; then
    log "hermes: $(hermes_home) not present; skipping hermes overlay"
  fi
  log ""

  local product
  for product in $(selected_products); do
    overlay_product "$product"
    if [ "$PRUNE" = "1" ]; then
      prune_product "$product"
    fi
    if [ "$product" = "hermes" ]; then
      hermes_config_hint
    fi
  done

  log ""
  log "summary: mode=$mode linked=$LINKED skipped=$SKIPPED pruned=$PRUNED"
  if [ "$APPLY" = "0" ]; then
    log "dry-run only; re-run with --apply to write symlinks."
  fi
}

main "$@"
