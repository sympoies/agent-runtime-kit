#!/usr/bin/env bash
#
# UserPromptSubmit hook: inject a short, language-agnostic agent-docs awareness
# cue for repos that declare intents in AGENT_DOCS.toml.
#
# The cue covers EVERY declared intent (for example project-dev and task-tools),
# enumerated from `agent-docs list` and resolved per intent via `agent-docs
# preflight --intent` (with the declared-intent guard when the installed
# agent-docs supports it). There is no English-keyword gating: the cue is driven
# by what the repo declares, so a non-English prompt in a policy repo still gets
# the cue, and declaring a new intent in AGENT_DOCS.toml activates it
# automatically.
# It fires at most once per session per repo (falling back to once per day) so it
# is a start-of-task nudge, not a per-prompt reminder.
#
set -uo pipefail

if [[ "${AGENT_RUNTIME_SUPPRESS_PREFLIGHT:-0}" == "1" ||
  "${AGENT_KIT_SUPPRESS_PREFLIGHT:-0}" == "1" ||
  "${CLAUDE_KIT_SUPPRESS_PREFLIGHT:-0}" == "1" ]]; then
  exit 0
fi

command -v git >/dev/null 2>&1 || exit 0
command -v agent-docs >/dev/null 2>&1 || exit 0
python_bin="$(command -v python3 || true)"
[[ -z "$python_bin" ]] && exit 0

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -z "$repo_root" ]] && exit 0
[[ -f "$repo_root/AGENT_DOCS.toml" ]] || exit 0

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
import json, sys
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
stamp="$stamp_dir/preflight-cue-${stamp_product}-${repo_hash}-${key}.stamp"
[[ -f "$stamp" ]] && exit 0

docs_home="${AGENT_RUNTIME_DOCS_HOME:-${AGENT_DOCS_HOME:-}}"
if [[ -z "$docs_home" ]] && runtime_kit_source_checkout "$repo_root"; then
  docs_home="$repo_root"
fi
dh_args=()
[[ -n "$docs_home" ]] && dh_args=(--docs-home "$docs_home")

require_declared_args=()
if agent-docs "${dh_args[@]}" --project-path "$repo_root" \
  preflight --help 2>/dev/null | grep -q -- "--require-declared-intent"; then
  require_declared_args=(--require-declared-intent)
fi
if [[ -n "$product" ]] && agent-docs "${dh_args[@]}" --project-path "$repo_root" \
  preflight --help 2>/dev/null | grep -q -- "--product"; then
  product_args=(--product "$product")
fi

# Enumerate every declared intent, newest catalog wins. No hard-coded intent.
intents="$(
  agent-docs "${dh_args[@]}" --project-path "$repo_root" list --format json 2>/dev/null |
    "$python_bin" -c '
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

# Resolve each intent's document set + validation contract (preflight honors the
# per-document `when` conditions; `list` alone does not).
preflights=()
while IFS= read -r intent; do
  [[ -z "$intent" ]] && continue
  pf="$(
    agent-docs "${dh_args[@]}" --project-path "$repo_root" \
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
done <<<"$intents"
[[ ${#preflights[@]} -eq 0 ]] && exit 0

# Compose one cue across all intents: per-intent required docs, plus the union
# of declared validation commands (the finish-line gate enforces those).
cue="$(
  "$python_bin" - "${preflights[@]}" <<'PY' 2>/dev/null || true
import json, os, sys
lines = []
val_cmds = []
home_roots = set()
project_roots = set()
preflight_docs = []


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

for d, intent, docs in preflight_docs:
    if docs:
        names = ", ".join(doc_label(x, d) for x in docs)
        lines.append(
            f"Required {intent} docs ({len(docs)}): {names}. Read them before writing."
        )
if val_cmds:
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
