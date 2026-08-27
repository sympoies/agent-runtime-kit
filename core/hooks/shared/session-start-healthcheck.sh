#!/usr/bin/env bash
#
# SessionStart hook: surface health problems once per day.
#
# Two independent, opt-in-aware checks share one daily nudge:
#   1. agent-docs repo preflight health (when `agent-docs` is installed and the
#      current repo declares `AGENT_DOCS.toml`): strict preflight for every
#      declared intent. Runtime-kit source checkouts self-anchor docs-home;
#      other project catalogs inherit the active managed docs-home.
#   2. evidence-archive wiring (only when the user has opted in via
#      $AGENT_EVIDENCE_ARCHIVE_HOME, a machine-local config, or a default clone):
#      clone presence, local config validity, and hosts.yaml validity.
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
stamp="$stamp_dir/health-${product}-$(date +%Y%m%d).stamp"
[[ -f "$stamp" ]] && exit 0
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"

trusted_cli_path() {
  local candidate
  candidate="$(command -v "$1" 2>/dev/null || true)"
  [[ "$candidate" == /* && -x "$candidate" ]] || return 1
  "$python_bin" - "$candidate" "$repo_root" <<'PY' 2>/dev/null
import os
import pathlib
import sys

candidate_path = pathlib.Path(sys.argv[1]).absolute()
candidate = candidate_path.resolve()
repo_raw = sys.argv[2]
configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "")
if repo_raw:
    try:
        candidate_path.relative_to(pathlib.Path(repo_raw).resolve())
    except ValueError:
        pass
    else:
        raise SystemExit(1)
trusted = False
if configured:
    roots = [
        pathlib.Path(item).resolve()
        for item in configured.split(os.pathsep)
        if item
    ]
    trusted = candidate_path.parent.resolve() in roots
else:
    for prefix_raw in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
        prefix = pathlib.Path(prefix_raw)
        if candidate_path.parent != prefix / "bin":
            continue
        if candidate.parent == candidate_path.parent:
            trusted = True
            break
        try:
            relative = candidate.relative_to(prefix / "Cellar" / "nils-cli")
        except ValueError:
            continue
        trusted = len(relative.parts) >= 3 and candidate.parent.name == "bin"
        if trusted:
            break
if candidate_path.parent == pathlib.Path("/usr/bin") and candidate.parent == candidate_path.parent:
    trusted = True
# Per-user managed install (NILS_WRAPPER_INSTALL_PREFIX). Regular files live
# here, so it is paired with the same lexical == resolved check as /usr/bin.
if candidate_path.parent == pathlib.Path("~/.local/nils-cli/bin").expanduser() and (
    candidate.parent == candidate_path.parent
):
    trusted = True
if not trusted or not candidate.is_file() or not os.access(candidate, os.X_OK):
    raise SystemExit(1)
print(candidate)
PY
}

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

runtime_kit_source_checkout() {
  local root="$1"
  [[ -f "$root/AGENT_DOCS.toml" &&
    -f "$root/AGENT_HOME.md" &&
    -f "$root/manifests/skills.yaml" &&
    -f "$root/scripts/sync-runtime-surfaces.sh" &&
    -d "$root/core/policies" ]]
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

# --- decide whether either lane can run today -------------------------------

have_agent_docs=0
agent_docs_bin="$(trusted_cli_path agent-docs || true)"
[[ -n "$agent_docs_bin" ]] && have_agent_docs=1
opted_in=0
evidence_opted_in && opted_in=1

# Nothing to check today: do not stamp, so a later session can re-check.
if [[ "$have_agent_docs" -eq 0 && "$opted_in" -eq 0 ]]; then
  exit 0
fi

mkdir -p "$stamp_dir"
: >"$stamp"

# --- lane 1: agent-docs repo health -----------------------------------------

docs_block=""
if [[ "$have_agent_docs" -eq 1 && -n "$repo_root" && -f "$repo_root/AGENT_DOCS.toml" ]]; then
  # Prefer an explicit docs-home override. The runtime-kit source checkout
  # self-anchors so rendered home-prompt symlinks cannot resolve home-scoped
  # docs under build/<product>/. Other project catalogs inherit docs-home.
  docs_home="${AGENT_RUNTIME_DOCS_HOME:-${AGENT_DOCS_HOME:-}}"
  if [[ -z "$docs_home" ]] && runtime_kit_source_checkout "$repo_root"; then
    docs_home="$repo_root"
  fi
  dh_args=()
  [[ -n "$docs_home" ]] && dh_args=(--docs-home "$docs_home")
  project_args=()
  project_args=(--project-path "$repo_root")
  product_args=()
  if [[ "$product" == "codex" || "$product" == "claude" ]]; then
    if "$agent_docs_bin" ${dh_args[@]+"${dh_args[@]+"${dh_args[@]}"}"} ${project_args[@]+"${project_args[@]+"${project_args[@]}"}"} \
      preflight --help 2>/dev/null | grep -q -- "--product"; then
      product_args=(--product "$product")
    fi
  fi

  list_output="$(
    "$agent_docs_bin" ${dh_args[@]+"${dh_args[@]+"${dh_args[@]}"}"} ${project_args[@]+"${project_args[@]+"${project_args[@]}"}"} list --format json 2>&1
  )"
  list_status=$?
  intents=""
  parse_status=0
  if [[ "$list_status" -eq 0 ]]; then
    intents="$(printf '%s\n' "$list_output" | "$python_bin" -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    raise SystemExit(2)
for intent in data.get("intents", []):
    if isinstance(intent, str) and intent:
        print(intent)
' 2>/dev/null)"
    parse_status=$?
  fi
  preflight_output=""
  preflight_failed=0
  if [[ "$list_status" -ne 0 ]]; then
    preflight_failed=1
    preflight_output="agent-docs list failed:
${list_output}
"
  elif [[ "$parse_status" -ne 0 ]]; then
    preflight_failed=1
    preflight_output="agent-docs list returned invalid JSON:
${list_output}
"
  elif [[ -z "$intents" ]]; then
    preflight_failed=1
    preflight_output="agent-docs list returned no declared intents for ${repo_root}.
"
  else
    while IFS= read -r intent; do
      [[ -z "$intent" ]] && continue
      out="$(
        "$agent_docs_bin" ${dh_args[@]+"${dh_args[@]+"${dh_args[@]}"}"} ${project_args[@]+"${project_args[@]+"${project_args[@]}"}"} \
          preflight --intent "$intent" ${product_args[@]+"${product_args[@]+"${product_args[@]}"}"} --strict --format text 2>&1
      )"
      status=$?
      preflight_output="${preflight_output}intent ${intent}:
${out}

"
      if [[ "$status" -ne 0 ]]; then
        preflight_failed=1
      fi
    done <<<"$intents"
  fi

  if [[ "$preflight_failed" -ne 0 ]]; then
    docs_block="agent-docs preflight found repo-health problems in the current workspace:

${preflight_output}"
  fi
fi

# --- lane 2: evidence-archive wiring (opt-in) -------------------------------

evid_block=""
if [[ "$opted_in" -eq 1 ]]; then
  evid_problems="$(evidence_problems)"
  if [[ -n "$evid_problems" ]]; then
    evid_block="evidence-archive wiring problems (you have opted in via \$AGENT_EVIDENCE_ARCHIVE_HOME, a local config, or a local clone):

${evid_problems}"
  fi
fi

# --- combine + emit ---------------------------------------------------------

if [[ -z "$docs_block" && -z "$evid_block" ]]; then
  exit 0
fi

context="[agent-runtime-kit:${product} health]"
[[ -n "$docs_block" ]] && context="${context}

${docs_block}"
[[ -n "$evid_block" ]] && context="${context}

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
