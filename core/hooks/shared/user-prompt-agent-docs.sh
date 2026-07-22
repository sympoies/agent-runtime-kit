#!/usr/bin/env bash
#
# UserPromptSubmit hook: inject a short, language-agnostic agent-docs awareness
# cue for repos that declare intents in AGENT_DOCS.toml.
#
# On a released agent-docs with durable session state, the cue expands only
# active intents and lists inactive routes without injecting their runbooks.
# The agent classifies the natural-language request and activates the relevant
# intent; no English-keyword matching or evidence-skill selection is required.
# Older agent-docs releases keep the compatibility behavior of resolving every
# declared intent and do not claim selective activation was enforced.
#
set -uo pipefail

if [[ "${AGENT_RUNTIME_SUPPRESS_PREFLIGHT:-0}" == "1" ||
  "${AGENT_KIT_SUPPRESS_PREFLIGHT:-0}" == "1" ||
  "${CLAUDE_KIT_SUPPRESS_PREFLIGHT:-0}" == "1" ]]; then
  exit 0
fi

command -v git >/dev/null 2>&1 || exit 0
python_bin="$(command -v python3 || true)"
[[ -z "$python_bin" ]] && exit 0
agent_docs_candidate="$(command -v agent-docs 2>/dev/null || true)"
[[ "$agent_docs_candidate" == /* && -x "$agent_docs_candidate" ]] || exit 0

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -z "$repo_root" ]] && exit 0
[[ -f "$repo_root/AGENT_DOCS.toml" ]] || exit 0
agent_docs_bin="$(
  "$python_bin" - "$agent_docs_candidate" "$repo_root" <<'PY' 2>/dev/null || true
import os
import pathlib
import sys

candidate_path = pathlib.Path(sys.argv[1]).absolute()
candidate = candidate_path.resolve()
repo = pathlib.Path(sys.argv[2]).resolve()
configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "")
try:
    candidate_path.relative_to(repo)
except ValueError:
    pass
else:
    raise SystemExit(0)
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
if trusted and candidate.is_file() and os.access(candidate, os.X_OK):
    print(candidate)
PY
)"
[[ "$agent_docs_bin" == /* && -x "$agent_docs_bin" ]] || exit 0

runtime_kit_source_checkout() {
  local root="$1"
  [[ -f "$root/AGENT_DOCS.toml" &&
    -f "$root/AGENT_HOME.md" &&
    -f "$root/manifests/skills.yaml" &&
    -f "$root/scripts/sync-runtime-surfaces.sh" &&
    -d "$root/core/policies" ]]
}

payload="$(cat)"

# Dedupe: at most one cue per session per repo (fall back to per-day when no
# session id is present), so the cue stays a start-of-task nudge.
session_id="$(
  "$python_bin" -c '
import json, os, sys
managed = os.environ.get("AGENT_SESSION_ID", "").strip()
if managed:
    print(managed)
    raise SystemExit(0)
try:
    p = json.load(sys.stdin)
except Exception:
    p = {}
for k in ("session_id", "sessionId", "session", "conversation_id"):
    v = p.get(k) if isinstance(p, dict) else None
    if isinstance(v, str) and v:
        print(v)
        break
' <<<"$payload" 2>/dev/null || true
)"
product="${AGENT_RUNTIME_PRODUCT:-agent-runtime}"
product_args=()
case "$product" in
  codex | claude) ;;
  *) product="" ;;
esac
repo_hash="$(printf '%s' "$repo_root" | cksum 2>/dev/null | awk '{print $1}' || true)"
key="${session_id:-$(date +%Y%m%d)}"
stamp_dir="$HOME/.cache/agent-runtime-kit"
stamp_product="${product:-agent-runtime}"
stamp_base="$stamp_dir/preflight-cue-${stamp_product}-${repo_hash}-${key}"
# Announced-intent memory persists across activation_key changes (unlike the
# per-fingerprint stamp) so a later cue lists only newly-active intents' docs.
announced_file="$stamp_dir/preflight-announced-${stamp_product}-${repo_hash}-${key}"

docs_home="${AGENT_RUNTIME_DOCS_HOME:-${AGENT_DOCS_HOME:-}}"
if [[ -z "$docs_home" ]] && runtime_kit_source_checkout "$repo_root"; then
  docs_home="$repo_root"
fi
dh_args=()
[[ -n "$docs_home" ]] && dh_args=(--docs-home "$docs_home")

require_declared_args=()
if "$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
  preflight --help 2>/dev/null | grep -q -- "--require-declared-intent"; then
  require_declared_args=(--require-declared-intent)
fi
if [[ -n "$product" ]] && "$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
  preflight --help 2>/dev/null | grep -q -- "--product"; then
  product_args=(--product "$product")
fi

# Enumerate every declared intent, newest catalog wins. No hard-coded intent.
# Keep a canonical identity separate from display order so even a session with
# no active intent invalidates its cue when the declared catalog changes.
catalog_json="$(
  "$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" list --format json 2>/dev/null || true
)"
intents="$(
  printf '%s' "$catalog_json" | "$python_bin" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
for intent in d.get("intents", []):
    if isinstance(intent, str) and intent:
        print(intent)
' 2>/dev/null || true
)"
[[ -z "$intents" ]] && exit 0
catalog_identity="$(
  printf '%s' "$catalog_json" | "$python_bin" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
intents = sorted({x for x in d.get("intents", []) if isinstance(x, str) and x})
print(json.dumps(intents, separators=(",", ":")))
' 2>/dev/null || true
)"

runtime_state_home() {
  if [[ -n "${AGENT_RUNTIME_STATE_HOME:-}" ]]; then
    printf '%s\n' "$AGENT_RUNTIME_STATE_HOME"
    return
  fi
  case "$product" in
    codex)
      printf '%s\n' "${CODEX_AGENT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/codex}"
      ;;
    claude)
      printf '%s\n' "${CLAUDE_KIT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/claude}"
      ;;
  esac
}

session_supported=0
active_intents=""
state_home=""
status_json=""
verify_json=""
activation_stale=0
if [[ -n "$product" ]] && "$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
  session --help 2>/dev/null | grep -q -- "status" &&
  "$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
    session --help 2>/dev/null | grep -q -- "verify"; then
  session_supported=1
  state_home="$(runtime_state_home)"
  if [[ -n "$session_id" && -n "$state_home" ]]; then
    status_json="$("$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
      session status --session-id "$session_id" --product "$product" \
      --state-home "$state_home" --format json 2>/dev/null || true)"
    active_intents="$(
      printf '%s' "$status_json" | "$python_bin" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
data = d.get("data") if isinstance(d, dict) else None
for intent in (data or {}).get("active_intents", []):
    if isinstance(intent, str) and intent:
        print(intent)
' 2>/dev/null || true
    )"
    if [[ -n "$active_intents" ]]; then
      verify_args=()
      while IFS= read -r active_intent; do
        [[ -n "$active_intent" ]] && verify_args+=(--require-intent "$active_intent")
      done <<<"$active_intents"
      verify_json="$("$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
        session verify --session-id "$session_id" --product "$product" \
        --state-home "$state_home" "${verify_args[@]}" --format json 2>/dev/null || true)"
      verified="$(printf '%s' "$verify_json" | "$python_bin" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
data = d.get("data") if isinstance(d, dict) else None
if d.get("ok") is True and isinstance(data, dict) and data.get("verified") is True:
    print("yes")
' 2>/dev/null || true)"
      if [[ "$verified" != "yes" ]]; then
        activation_stale=1
        active_intents=""
      fi
    fi
  fi
fi

selected_intents="$intents"
if [[ "$session_supported" == "1" ]]; then
  selected_intents="$active_intents"
fi

# Resolve only selected intents. With durable session state this means active
# intents; with an older CLI it preserves the previous all-intents fallback.
preflights=()
while IFS= read -r intent; do
  [[ -z "$intent" ]] && continue
  pf="$(
    "$agent_docs_bin" "${dh_args[@]}" --project-path "$repo_root" \
      preflight --intent "$intent" "${require_declared_args[@]}" \
      "${product_args[@]}" \
      --format json 2>/dev/null
  )"
  status=$?
  if [[ $status -ne 0 ]]; then
    if [[ ${#require_declared_args[@]} -gt 0 ]]; then
      printf 'agent-runtime-kit: agent-docs preflight failed for declared intent %s (exit %s)\n' \
        "$intent" "$status" >&2
      exit 2
    fi
    continue
  fi
  [[ -z "$pf" ]] && continue
  preflights+=("$pf")
done <<<"$selected_intents"

preflight_identity="$(printf '%s\n' "${preflights[@]}" | cksum 2>/dev/null || true)"
# The session record's raw bytes are intentionally NOT part of this key: a
# same-name reactivation that only rewrites the record (e.g. a no-op `session
# prepare` that refreshes activated_at) with unchanged active intents, documents,
# and catalog must not re-emit the cue (P0-2 bullet 4). Meaningful changes still
# invalidate via active_intents / status / verify / preflight / catalog.
activation_key="$(printf '%s\n%s\n%s\n%s\n%s\n%s\n%s' \
  "$session_supported" "$active_intents" "$activation_stale" "$status_json" \
  "$verify_json" "$preflight_identity" "$catalog_identity" |
  cksum | awk '{print $1}' || true)"
stamp="${stamp_base}-${activation_key:-legacy}.stamp"
[[ -f "$stamp" ]] && exit 0

# Delta cue: intents active now but not previously announced for this
# session/repo. Only these carry their required-doc list in the cue below; the
# announced set is updated only after a cue is actually emitted.
new_active_intents=""
if [[ "$session_supported" == "1" && -n "$active_intents" ]]; then
  prev_announced=""
  [[ -f "$announced_file" ]] && prev_announced="$(cat "$announced_file" 2>/dev/null || true)"
  while IFS= read -r _active_intent; do
    [[ -z "$_active_intent" ]] && continue
    if ! printf '%s\n' "$prev_announced" | grep -qxF -- "$_active_intent" 2>/dev/null; then
      new_active_intents+="${_active_intent}"$'\n'
    fi
  done <<<"$active_intents"
fi

# Compose one cue across active intents and include a concise route to inactive
# intents without loading their document bodies.
cue="$(
  AGENT_RUNTIME_DECLARED_INTENTS="$intents" \
    AGENT_RUNTIME_ACTIVE_INTENTS="$active_intents" \
    AGENT_RUNTIME_NEW_ACTIVE_INTENTS="$new_active_intents" \
    AGENT_RUNTIME_SESSION_SUPPORTED="$session_supported" \
    AGENT_RUNTIME_SESSION_ID="$session_id" \
    AGENT_RUNTIME_SESSION_PRODUCT="$product" \
    AGENT_RUNTIME_SESSION_STATE_HOME="$state_home" \
    AGENT_RUNTIME_SESSION_STALE="$activation_stale" \
    AGENT_RUNTIME_RESOLVED_AGENT_DOCS="$agent_docs_bin" \
    AGENT_RUNTIME_RESOLVED_DOCS_HOME="$docs_home" \
    AGENT_RUNTIME_RESOLVED_PROJECT_PATH="$repo_root" \
    "$python_bin" - "${preflights[@]}" <<'PY' 2>/dev/null || true
import json, os, shlex, sys
lines = []
val_cmds = []
home_roots = set()
project_roots = set()
preflight_docs = []
declared = [x for x in os.environ.get("AGENT_RUNTIME_DECLARED_INTENTS", "").splitlines() if x]
active = [x for x in os.environ.get("AGENT_RUNTIME_ACTIVE_INTENTS", "").splitlines() if x]
new_active = [x for x in os.environ.get("AGENT_RUNTIME_NEW_ACTIVE_INTENTS", "").splitlines() if x]
session_supported = os.environ.get("AGENT_RUNTIME_SESSION_SUPPORTED") == "1"
session_id = os.environ.get("AGENT_RUNTIME_SESSION_ID", "")
product = os.environ.get("AGENT_RUNTIME_SESSION_PRODUCT", "")
state_home = os.environ.get("AGENT_RUNTIME_SESSION_STATE_HOME", "")
activation_stale = os.environ.get("AGENT_RUNTIME_SESSION_STALE") == "1"
resolved_docs_home = os.environ.get("AGENT_RUNTIME_RESOLVED_DOCS_HOME", "")
resolved_project_path = os.environ.get("AGENT_RUNTIME_RESOLVED_PROJECT_PATH", "")
resolved_agent_docs = os.environ.get("AGENT_RUNTIME_RESOLVED_AGENT_DOCS", "")


def rel_under(path, root):
    if not path or not root:
        return path
    try:
        abs_path = os.path.abspath(path)
        abs_root = os.path.abspath(root)
        if os.path.commonpath([abs_path, abs_root]) == abs_root:
            return os.path.relpath(abs_path, abs_root)
    except Exception:
        return path
    return path


def doc_owner(doc):
    scope = doc.get("scope")
    if scope in ("home", "project"):
        return scope
    source = doc.get("source")
    if source in ("home", "project"):
        return source
    return None


def doc_label(doc, preflight):
    path = str(doc.get("path") or "")
    if not path:
        return "(unknown)"
    owner = doc_owner(doc)
    if owner == "home":
        return "home:" + rel_under(path, preflight.get("docs_home") or "")
    if owner == "project":
        return "project:" + rel_under(path, preflight.get("project_path") or "")
    return path


for raw in sys.argv[1:]:
    try:
        d = json.loads(raw)
    except Exception:
        continue
    intent = d.get("intent") or "?"
    docs = [x for x in d.get("documents", []) if x.get("required")]
    preflight_docs.append((d, intent, docs))
    if d.get("docs_home") and any(doc_owner(x) == "home" for x in docs):
        home_roots.add(str(d.get("docs_home")))
    if d.get("project_path") and any(doc_owner(x) == "project" for x in docs):
        project_roots.add(str(d.get("project_path")))
    val = d.get("validation") or {}
    for cmd in (val.get("commands") or []):
        if cmd not in val_cmds:
            val_cmds.append(cmd)

root_parts = []
if home_roots:
    root_parts.append("home=" + " | ".join(sorted(home_roots)))
if project_roots:
    root_parts.append("project=" + " | ".join(sorted(project_roots)))
if root_parts:
    lines.append("Doc roots: " + ", ".join(root_parts) + ".")

if session_supported:
    if activation_stale:
        lines.append("The prior agent-docs activation is stale or unverifiable; re-prepare it before writing.")
    if new_active:
        lines.append("Newly active agent-docs intents: " + ", ".join(new_active) + ".")
    inactive = [intent for intent in declared if intent not in active]
    if inactive:
        lines.append("Inactive available intents: " + ", ".join(inactive) + ".")
        if session_id and product:
            context_args = []
            if resolved_docs_home:
                context_args += ["--docs-home", resolved_docs_home]
            context_args += ["--project-path", resolved_project_path]
            prefix = shlex.quote(resolved_agent_docs) + " " + " ".join(
                shlex.quote(value) for value in context_args
            )
            lines.append(
                "Classify the request, then prepare only relevant inactive intents before writing: "
                f"{prefix} session prepare --session-id {shlex.quote(session_id)} "
                f"--product {product} --state-home {shlex.quote(state_home)} "
                "--intent <intent> --format json."
            )
        else:
            lines.append(
                "Selective preparation is supported but this hook lacks session/product context; "
                "do not claim intent preparation was verified."
            )

for d, intent, docs in preflight_docs:
    if session_supported and intent not in new_active:
        # Delta cue: only the newly-active intent's required docs are listed;
        # already-announced intents are not re-emitted on later prompts.
        continue
    if docs:
        names = ", ".join(doc_label(x, d) for x in docs)
        lines.append(
            f"Required {intent} docs ({len(docs)}): {names}. Read them before writing."
        )
# P0-2 bullet 6: the durable-session delta cue does not expand the full
# validation command list on ordinary prompts (the finish-line gate still
# enforces it). The legacy all-intents fallback keeps the cue for older CLIs.
if val_cmds and not session_supported:
    lines.append(
        "Before declaring this task done, run the declared validation: "
        + " && ".join(val_cmds)
        + " (the finish-line gate enforces this; state a waiver to override)."
    )
if not lines:
    raise SystemExit(0)
print("\n".join(lines))
PY
)"
[[ -z "$cue" ]] && exit 0

reminder="[agent-runtime-kit:${stamp_product}] This repo declares agent-docs intent contracts.
${cue}"

CTX="$reminder" "$python_bin" -c '
import json
import os

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": os.environ["CTX"],
    }
}))
'

mkdir -p "$stamp_dir"
: >"$stamp"
# Record the active set as announced only after a cue was emitted, so the next
# cue's delta lists only intents that become active afterwards.
if [[ "$session_supported" == "1" && -n "$active_intents" ]]; then
  printf '%s\n' "$active_intents" >"$announced_file" 2>/dev/null || true
fi
