#!/usr/bin/env bash
#
# SessionStart hook: surface evidence-archive wiring problems once per day,
# only when the user has opted in via $AGENT_EVIDENCE_ARCHIVE_HOME, a
# machine-local config, or a default clone: clone presence, local config
# validity, and hosts.yaml validity. Stamped once per day per product.
#
# The hook is product-neutral. Product activation sets AGENT_RUNTIME_PRODUCT so
# cache keys and labels stay readable. A user who has not opted into the
# evidence-archive is never nagged about it.

set -uo pipefail

if [[ "${AGENT_RUNTIME_SUPPRESS_HEALTH:-0}" == "1" ||
  "${AGENT_KIT_SUPPRESS_HEALTH:-0}" == "1" ||
  "${CLAUDE_KIT_SUPPRESS_HEALTH:-0}" == "1" ]]; then
  exit 0
fi

python_bin="$(command -v python3 || true)"
[[ -z "$python_bin" ]] && exit 0

product="${AGENT_RUNTIME_PRODUCT:-agent-runtime}"
stamp_dir="$HOME/.cache/agent-runtime-kit"
stamp_day="$(date +%Y%m%d)"
evidence_stamp="$stamp_dir/health-${product}-evidence-${stamp_day}.stamp"
evidence_due=0
[[ ! -f "$evidence_stamp" ]] && evidence_due=1
[[ "$evidence_due" -eq 0 ]] && exit 0

# --- opt-in detection for the evidence-archive lane -------------------------

evidence_config_path() {
  printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/agent-evidence-archive/config.yaml"
}

archive_has_git_marker() {
  # OPT-IN signal only: the user set up a clone here if a `.git` marker exists at
  # all (a real `.git` directory or a worktree's `.git` file), even a stale one.
  # Staleness/invalidity is a problem to REPORT (see `archive_is_git_repo`), not
  # a reason to treat the user as not opted in — otherwise the very stale-archive
  # case the report exists to surface is silently skipped.
  [[ -d "$1/.git" || -f "$1/.git" ]]
}

archive_is_git_repo() {
  # VALIDITY check: the path is an actual working Git checkout, not just any
  # `.git` marker. A stale or invalid worktree leaves a `.git` file whose
  # `gitdir:` target is gone or is not a real Git directory (e.g. an empty
  # admin dir), so later `git -C "$archive" …` operations still fail with "not a
  # git repository". Ask Git itself to resolve the repository; only when Git is
  # unavailable fall back to a structural check (a `.git` directory, or a `.git`
  # file whose `gitdir:` target path exists).
  #
  # Two subtleties when asking Git: (a) `git -C "$archive" rev-parse` would
  # succeed for a SUBDIRECTORY of an enclosing checkout by resolving the OUTER
  # repo, but the evidence archive must be a standalone clone — so require the
  # resolved work-tree top level to BE `$archive`; (b) an inherited `GIT_DIR` /
  # `GIT_WORK_TREE` (e.g. a session launched from a Git context) would redirect
  # discovery away from `$archive` — so scrub those for this probe.
  local archive="$1" marker="$1/.git" gitdir toplevel resolved_archive
  if command -v git >/dev/null 2>&1; then
    toplevel="$(env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE \
      git -C "$archive" rev-parse --show-toplevel 2>/dev/null)" || return 1
    [[ -n "$toplevel" ]] || return 1
    # Compare canonical paths so a trailing slash / symlink does not spuriously
    # differ. A linked worktree's top level is the worktree itself, so a valid
    # worktree archive still matches.
    resolved_archive="$(cd "$archive" 2>/dev/null && pwd -P)" || return 1
    toplevel="$(cd "$toplevel" 2>/dev/null && pwd -P)" || return 1
    [[ "$resolved_archive" == "$toplevel" ]]
    return
  fi
  if [[ -d "$marker" ]]; then
    return 0
  fi
  if [[ -f "$marker" ]]; then
    gitdir="$(sed -n 's/^gitdir:[[:space:]]*//p' "$marker" | head -1)"
    [[ -n "$gitdir" ]] || return 1
    [[ "$gitdir" == /* ]] || gitdir="$archive/$gitdir"
    [[ -e "$gitdir" ]] && return 0
    return 1
  fi
  return 1
}

unquote_yaml_scalar() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "$value" == \"*\" && "$value" == *\" && "${#value}" -ge 2 ]]; then
    value="${value:1:${#value}-2}"
    value="${value//\\\"/\"}"
    value="${value//\\\\/\\}"
  elif [[ "$value" == \'*\' && "$value" == *\' && "${#value}" -ge 2 ]]; then
    value="${value:1:${#value}-2}"
    value="${value//\'\'/\'}"
  fi
  printf '%s\n' "$value"
}

evidence_opted_in() {
  [[ -n "${AGENT_EVIDENCE_ARCHIVE_HOME:-}" ]] && return 0
  [[ -f "$(evidence_config_path)" ]] && return 0
  archive_has_git_marker "${XDG_DATA_HOME:-$HOME/.local/share}/agent-evidence-archive" && return 0
  return 1
}

resolve_archive_path() {
  # Mirrors the documented precedence: env > local config > XDG default.
  if [[ -n "${AGENT_EVIDENCE_ARCHIVE_HOME:-}" ]]; then
    printf '%s\n' "$AGENT_EVIDENCE_ARCHIVE_HOME"
    return
  fi
  local cfg p
  cfg="$(evidence_config_path)"
  if [[ -f "$cfg" ]]; then
    p="$(sed -n 's/^archive_clone_path:[[:space:]]*//p' "$cfg" | head -1)"
    if [[ -n "$p" ]]; then
      p="$(unquote_yaml_scalar "$p")"
      printf '%s\n' "$p"
      return
    fi
  fi
  printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/agent-evidence-archive"
}

evidence_problems() {
  # Caller guarantees the user has opted in. Emits one problem per line.
  if ! command -v evidence >/dev/null 2>&1; then
    printf '%s\n' "- evidence-archive is opted in but the \`evidence\` CLI is not on PATH (install the nils-cli evidence surface)."
    return
  fi
  local out="" cfg archive hosts
  cfg="$(evidence_config_path)"
  if [[ -f "$cfg" ]] && ! evidence validate-local --input "$cfg" >/dev/null 2>&1; then
    out="${out}- local config is invalid: ${cfg}
"
  fi
  archive="$(resolve_archive_path)"
  if ! archive_is_git_repo "$archive"; then
    out="${out}- archive clone not found or not a valid git repo at: ${archive}
"
  else
    hosts="$archive/config/hosts.yaml"
    if [[ ! -f "$hosts" ]]; then
      out="${out}- hosts.yaml missing at: ${hosts}
"
    elif ! evidence validate-hosts --input "$hosts" >/dev/null 2>&1; then
      out="${out}- hosts.yaml is invalid: ${hosts}
"
    fi
  fi
  printf '%s' "$out"
}

# --- decide whether the lane can run today -----------------------------------

opted_in=0
[[ "$evidence_due" -eq 1 ]] && evidence_opted_in && opted_in=1

# Stamp the lane only when it actually runs, so a session with nothing to
# check leaves it due for a later session.
stamp_lane() {
  mkdir -p "$stamp_dir" && : >"$1"
}

# --- evidence-archive wiring (opt-in) ---------------------------------------

evid_block=""
if [[ "$opted_in" -eq 1 ]]; then
  stamp_lane "$evidence_stamp"
  evid_problems="$(evidence_problems)"
  if [[ -n "$evid_problems" ]]; then
    evid_block="evidence-archive wiring problems (you have opted in via \$AGENT_EVIDENCE_ARCHIVE_HOME, a local config, or a local clone):

${evid_problems}"
  fi
fi

# --- emit ---------------------------------------------------------------

if [[ -z "$evid_block" ]]; then
  exit 0
fi

context="[agent-runtime-kit:${product} health]

${evid_block}"

CTX="$context" "$python_bin" -c '
import json
import os

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": os.environ["CTX"],
    }
}))
'
