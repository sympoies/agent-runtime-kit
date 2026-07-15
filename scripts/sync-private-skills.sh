#!/usr/bin/env bash
# scripts/sync-private-skills.sh - overlay private project-local skills into
# the live Codex and Claude runtime homes.
#
# This is a deliberately thin companion to sync-runtime-surfaces.sh. It does NOT
# render, install through nils-cli, or touch any runtime-kit manifest. It only
# symlinks already-native project-local skills (the create-project-skill layout:
# <home>/.agents/skills/<name>/SKILL.md) from a PRIVATE source tree into the
# global per-user skill directories that each declared product discovers:
#
#   Codex : $CODEX_HOME/skills/<name>      (default $HOME/.codex/skills/<name>)
#   Claude: $HOME/.claude/skills/<name>    (personal global skill namespace)
#   Hermes: $HOME/.hermes/external-skills/private/<name>
#
# A skill may opt into a product subset with <skill>/agents/products.txt. The
# file contains one exact product name (codex, claude, or hermes) per line. A
# missing file preserves the legacy all-product behavior. Existing metadata is
# validated for the whole catalog before any runtime directory, link, or prune
# mutation so a malformed declaration fails closed. The source root and every
# consumed path below each skill must be real paths inside the declared private
# home; symlinked or canonically escaped sources fail closed at the same boundary.
# Every selected product's skills target is also preflighted before the first
# product mutation, so a redirected target cannot receive links or prune data.
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

Each skill may declare a product subset in agents/products.txt, with one exact
codex, claude, or hermes entry per line. Missing metadata means all products
for backward compatibility. Existing metadata must be non-empty and contain no
blank, duplicate, or unknown entries; the full catalog is validated before any
runtime mutation.

The .agents/skills source root, each skill directory, and every resource below
each skill must be real paths contained by the declared private home. Symlinked
or canonically escaped sources are rejected before any runtime-home mutation.
Each selected product's skills target components must likewise be real,
canonical children of its configured runtime home. All selected targets are
preflighted before apply or prune starts, preventing partial multi-product work.

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
      Remove stale or newly excluded overlay symlinks: target-home entries that
      point to the exact expected private skill source but whose source skill no
      longer exists or no longer declares that product. Only ever removes
      symlinks this script owns; never touches real directories or links to a
      different private-home path.
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
    claude) printf '%s\n' "$(product_home_dir claude)/skills" ;;
    codex) printf '%s\n' "$(product_home_dir codex)/skills" ;;
    hermes) printf '%s\n' "$(product_home_dir hermes)/external-skills/private" ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

product_home_dir() {
  case "$1" in
    claude) printf '%s\n' "$HOME/.claude" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}" ;;
    hermes) hermes_home ;;
    *)
      err "unknown product: $1"
      exit 2
      ;;
  esac
}

join_path() {
  local parent="$1"
  local child="$2"
  case "$parent" in
    /) printf '/%s\n' "$child" ;;
    *) printf '%s/%s\n' "${parent%/}" "$child" ;;
  esac
}

# Resolve a directory path physically without creating it. Missing tail
# components are appended to the nearest existing physical parent, allowing the
# target preflight to verify the exact path that mkdir -p would create.
physical_path_allow_missing() {
  local path="$1"
  local parent base parent_physical

  if [ -d "$path" ]; then
    (cd "$path" && pwd -P)
    return
  fi
  if [ -e "$path" ] || [ -L "$path" ]; then
    return 1
  fi

  parent="$(dirname "$path")"
  base="$(basename "$path")"
  [ "$parent" != "$path" ] || return 1
  parent_physical="$(physical_path_allow_missing "$parent")" || return 1
  join_path "$parent_physical" "$base"
}

# The configured product home itself may be an operator-selected symlink. Each
# overlay-specific component below that resolved home must be a real directory
# at the exact expected physical path, or an as-yet-uncreated path whose nearest
# existing parent is exact. This prevents apply and prune from following a
# redirected skills root outside the selected runtime home.
validate_product_target_root() {
  local product="$1"
  local logical_path physical_path component actual_physical components

  logical_path="$(product_home_dir "$product")"
  physical_path="$(physical_path_allow_missing "$logical_path")" || {
    err "invalid [$product] runtime home: $logical_path must be a directory or creatable path"
    return 1
  }

  case "$product" in
    codex | claude) components="skills" ;;
    hermes) components="external-skills private" ;;
  esac

  for component in $components; do
    logical_path="$(join_path "$logical_path" "$component")"
    physical_path="$(join_path "$physical_path" "$component")"

    if [ -L "$logical_path" ]; then
      err "invalid [$product] skills target: $logical_path must not be a symlink"
      return 1
    fi
    if [ -e "$logical_path" ] && [ ! -d "$logical_path" ]; then
      err "invalid [$product] skills target: $logical_path must be a directory"
      return 1
    fi
    if [ -d "$logical_path" ]; then
      actual_physical="$(cd "$logical_path" && pwd -P)" || {
        err "invalid [$product] skills target: cannot resolve $logical_path"
        return 1
      }
      if [ "$actual_physical" != "$physical_path" ]; then
        err "invalid [$product] skills target: $logical_path escapes its canonical runtime-home location"
        return 1
      fi
    fi
  done
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
PRIVATE_HOME_PHYSICAL=""
SKILLS_SRC_PHYSICAL=""
resolve_private_home() {
  if [ -z "$PRIVATE_HOME" ]; then
    return 1
  fi
  if [ ! -d "$PRIVATE_HOME" ]; then
    err "private home does not exist: $PRIVATE_HOME"
    exit 2
  fi
  PRIVATE_HOME="$(abs_path "$PRIVATE_HOME")"
  PRIVATE_HOME_PHYSICAL="$(cd "$PRIVATE_HOME" && pwd -P)" || {
    err "cannot resolve private home: $PRIVATE_HOME"
    exit 2
  }
  SKILLS_SRC_DIR="$PRIVATE_HOME/.agents/skills"
  return 0
}

path_is_within() {
  local candidate="$1"
  local root="$2"
  case "$candidate" in
    "$root" | "$root"/*) return 0 ;;
    *) return 1 ;;
  esac
}

# Validate the source-root boundary before any product runtime path is created,
# linked, or pruned. PRIVATE_HOME itself may be reached through an
# operator-selected symlink, but .agents and .agents/skills must be real paths
# at their canonical location below that resolved home.
validate_skills_source_root() {
  local expected_physical

  if [ -L "$PRIVATE_HOME/.agents" ]; then
    err "invalid private skills source: $PRIVATE_HOME/.agents must not be a symlink"
    return 1
  fi
  if [ -L "$SKILLS_SRC_DIR" ]; then
    err "invalid private skills source: $SKILLS_SRC_DIR must not be a symlink"
    return 1
  fi
  if [ ! -d "$SKILLS_SRC_DIR" ]; then
    return 0
  fi

  SKILLS_SRC_PHYSICAL="$(cd "$SKILLS_SRC_DIR" && pwd -P)" || {
    err "cannot resolve private skills source: $SKILLS_SRC_DIR"
    return 1
  }
  expected_physical="$PRIVATE_HOME_PHYSICAL/.agents/skills"
  if ! path_is_within "$SKILLS_SRC_PHYSICAL" "$PRIVATE_HOME_PHYSICAL" ||
    [ "$SKILLS_SRC_PHYSICAL" != "$expected_physical" ]; then
    err "invalid private skills source: $SKILLS_SRC_DIR escapes its canonical private-home location"
    return 1
  fi
}

# Validate one optional per-skill product declaration. Metadata is deliberately
# strict: exact lowercase product names, one per line, with no blank or
# duplicate entries. A missing file retains the all-product legacy behavior.
validate_products_file() {
  local src="$1"
  local metadata="$src/agents/products.txt"
  local agents_dir="$src/agents"
  local agents_physical src_physical
  local line count=0
  local seen_codex=0 seen_claude=0 seen_hermes=0

  if [ ! -e "$metadata" ] && [ ! -L "$metadata" ]; then
    return 0
  fi
  if [ -L "$metadata" ] || [ ! -f "$metadata" ]; then
    err "invalid products metadata: $metadata must be a regular file"
    return 1
  fi
  if [ -L "$agents_dir" ]; then
    err "invalid products metadata: $agents_dir must not be a symlink"
    return 1
  fi
  agents_physical="$(cd "$agents_dir" && pwd -P)" || {
    err "invalid products metadata: cannot resolve $agents_dir"
    return 1
  }
  src_physical="$(cd "$src" && pwd -P)" || {
    err "invalid products metadata: cannot resolve $src"
    return 1
  }
  if ! path_is_within "$agents_physical" "$SKILLS_SRC_PHYSICAL" ||
    [ "$agents_physical" != "$src_physical/agents" ]; then
    err "invalid products metadata: $metadata escapes its skill source"
    return 1
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    count=$((count + 1))
    case "$line" in
      codex)
        if [ "$seen_codex" = "1" ]; then
          err "invalid products metadata: $metadata contains duplicate entry 'codex'"
          return 1
        fi
        seen_codex=1
        ;;
      claude)
        if [ "$seen_claude" = "1" ]; then
          err "invalid products metadata: $metadata contains duplicate entry 'claude'"
          return 1
        fi
        seen_claude=1
        ;;
      hermes)
        if [ "$seen_hermes" = "1" ]; then
          err "invalid products metadata: $metadata contains duplicate entry 'hermes'"
          return 1
        fi
        seen_hermes=1
        ;;
      "")
        err "invalid products metadata: $metadata contains a blank line"
        return 1
        ;;
      *)
        err "invalid products metadata: $metadata contains unknown entry '$line' (expected codex|claude|hermes)"
        return 1
        ;;
    esac
  done <"$metadata"

  if [ "$count" = "0" ]; then
    err "invalid products metadata: $metadata is empty (expected codex|claude|hermes)"
    return 1
  fi
}

# Validate the complete private catalog before overlay or prune has a chance to
# mutate a runtime home. This is intentionally separate from per-product work.
validate_skill_catalog() {
  local entry name skill_physical expected_physical linked_resource
  for entry in "$SKILLS_SRC_DIR"/*; do
    [ -e "$entry" ] || [ -L "$entry" ] || continue
    if [ -L "$entry" ]; then
      err "invalid private skill source: $entry must not be a symlink"
      return 1
    fi
    [ -d "$entry" ] || continue

    name="$(basename "$entry")"
    skill_physical="$(cd "$entry" && pwd -P)" || {
      err "cannot resolve private skill source: $entry"
      return 1
    }
    expected_physical="$SKILLS_SRC_PHYSICAL/$name"
    if ! path_is_within "$skill_physical" "$SKILLS_SRC_PHYSICAL" ||
      [ "$skill_physical" != "$expected_physical" ]; then
      err "invalid private skill source: $entry escapes the private skills root"
      return 1
    fi
    if [ -L "$entry/SKILL.md" ]; then
      err "invalid private skill source: $entry/SKILL.md must not be a symlink"
      return 1
    fi
    linked_resource="$(find "$entry" -type l -print | sed -n '1p')" || {
      err "cannot inspect private skill source: $entry"
      return 1
    }
    if [ -n "$linked_resource" ]; then
      err "invalid private skill source: $linked_resource must not be a symlink"
      return 1
    fi
    validate_products_file "$entry" || return 1
  done
}

skill_targets_product() {
  local src="$1"
  local product="$2"
  local metadata="$src/agents/products.txt"

  if [ ! -e "$metadata" ] && [ ! -L "$metadata" ]; then
    return 0
  fi
  grep -Fxq "$product" "$metadata"
}

# -----------------------------------------------------------------------------
# Overlay
# -----------------------------------------------------------------------------

# Is $1 a symlink that resolves to the exact expected source in $2?
is_owned_overlay() {
  local target="$1"
  local expected_source="$2"
  local resolved expected_resolved
  if [ ! -L "$target" ]; then
    return 1
  fi
  # Resolve the symlink's stored destination to an absolute path.
  resolved="$(cd "$(dirname "$target")" 2>/dev/null && abs_path "$(readlink "$target")" 2>/dev/null)" || return 1
  expected_resolved="$(abs_path "$expected_source" 2>/dev/null)" || return 1
  [ "$resolved" = "$expected_resolved" ]
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
    if is_owned_overlay "$target" "$src"; then
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

  for entry in "$SKILLS_SRC_DIR"/*; do
    [ -d "$entry" ] || continue
    name="$(basename "$entry")"
    src="$entry"

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

    if ! skill_targets_product "$src" "$product"; then
      log "skip-target [$product]: $name (not declared in agents/products.txt)"
      continue
    fi

    link_one "$name" "$src" "$product"
  done
}

prune_product() {
  local product="$1"
  local skills_dir entry name expected_src

  skills_dir="$(product_skills_dir "$product")"
  [ -d "$skills_dir" ] || return 0

  for entry in "$skills_dir"/*; do
    [ -L "$entry" ] || continue
    name="$(basename "$entry")"
    expected_src="$SKILLS_SRC_DIR/$name"
    is_owned_overlay "$entry" "$expected_src" || continue
    if [ ! -d "$SKILLS_SRC_DIR/$name" ] ||
      [ ! -f "$SKILLS_SRC_DIR/$name/SKILL.md" ]; then
      log "prune [$product]: stale overlay $name"
      run_cmd rm -f "$entry"
      PRUNED=$((PRUNED + 1))
    elif ! skill_targets_product "$SKILLS_SRC_DIR/$name" "$product"; then
      log "prune [$product]: excluded overlay $name"
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
  require_commands ln basename dirname find grep readlink sed

  if ! resolve_private_home; then
    log "$PROG_NAME: no private home (AGENT_PRIVATE_SKILLS_HOME unset, no --private-home); nothing to do."
    exit 0
  fi

  if ! validate_skills_source_root; then
    err "private skill source validation failed; no runtime changes were made"
    exit 2
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

  if ! validate_skill_catalog; then
    err "private skill catalog validation failed; no runtime changes were made"
    exit 2
  fi

  local product selected_product_list
  selected_product_list="$(selected_products)"
  for product in $selected_product_list; do
    if ! validate_product_target_root "$product"; then
      err "product skills target validation failed; no runtime changes were made"
      exit 2
    fi
  done

  local mode="dry-run"
  [ "$APPLY" = "1" ] && mode="apply"
  log "$PROG_NAME: mode=$mode product=$PRODUCT private-home=$PRIVATE_HOME"
  log "source: $SKILLS_SRC_DIR"
  if [ "$PRODUCT" = "all" ] && ! hermes_available; then
    log "hermes: $(hermes_home) not present; skipping hermes overlay"
  fi
  log ""

  for product in $selected_product_list; do
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
