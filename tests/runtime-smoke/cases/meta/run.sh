#!/usr/bin/env bash
# Deterministic probes for meta skills.
# shellcheck disable=SC2329

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/rendered-contract.sh
. "$SCRIPT_DIR/lib/rendered-contract.sh"

META_ARTIFACTS_DIR="$ARTIFACTS_DIR/meta"
META_WORKSPACE="$TMP_ROOT/workspaces/meta-basic-repo"
mkdir -p "$META_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$META_WORKSPACE"
git -C "$META_WORKSPACE" init -q

require_meta_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke meta: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

assert_symlink_target() {
  local link="$1"
  local target="$2"
  test -L "$link"
  test "$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$link")" = \
    "$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$target")"
}

run_agent_docs_probe() {
  local out="$META_ARTIFACTS_DIR/agent-docs.preflight.txt"
  require_meta_bin agent-docs || return 1
  (
    cd "$META_WORKSPACE"
    agent-docs \
      --docs-home "$REPO_ROOT" \
      --project-path "$REPO_ROOT" \
      preflight --intent project-dev --strict
  ) >"$out" 2>&1
  grep -q 'missing_required=0' "$out"
}

run_home_prompt_render_probe() {
  local out="$META_ARTIFACTS_DIR/home-prompt-render.txt"
  local codex_home="$REPO_ROOT/build/codex/AGENT_HOME.md"
  local claude_home="$REPO_ROOT/build/claude/AGENT_HOME.md"
  local hermes_home="$REPO_ROOT/build/hermes/AGENT_HOME.md"
  local neutral_home="$REPO_ROOT/build/neutral/AGENT_HOME.md"
  require_meta_bin agent-runtime || return 1
  (
    cd "$REPO_ROOT"
    agent-runtime render --source-root "$REPO_ROOT" --target home-prompt
    agent-runtime render --source-root "$REPO_ROOT" --target home-prompt --product codex
    agent-runtime render --source-root "$REPO_ROOT" --target home-prompt --product claude
    agent-runtime render --source-root "$REPO_ROOT" --target home-prompt --product hermes
  ) >"$out" 2>&1

  test -f "$neutral_home"
  test -f "$codex_home"
  test -f "$claude_home"
  test -f "$hermes_home"
  grep -Fq "or directory \`AGENTS.md\` / \`CLAUDE.md\` can override or extend it." "$neutral_home"
  grep -q '## Code Review Delegation' "$codex_home"
  if grep -q '## Code Review Delegation' "$neutral_home"; then
    echo "runtime-smoke meta: neutral home prompt includes Codex-only delegation section" >&2
    return 1
  fi
  if grep -q '## Code Review Delegation' "$claude_home"; then
    echo "runtime-smoke meta: Claude home prompt includes Codex-only delegation section" >&2
    return 1
  fi
  if grep -Eq "resolved by \`agent-docs\`|\\(injected for|blocked by hook|finish-line gate|delegate_task" "$hermes_home"; then
    echo "runtime-smoke meta: Hermes home prompt includes unavailable hook, agent-docs, or delegation claims" >&2
    return 1
  fi
  if grep -Eq '\bClaude\b|CLAUDE_' "$codex_home"; then
    echo "runtime-smoke meta: Codex home prompt leaks Claude sentinel text" >&2
    return 1
  fi
  if grep -Eq '\bCodex\b|CODEX_' "$claude_home"; then
    echo "runtime-smoke meta: Claude home prompt leaks Codex sentinel text" >&2
    return 1
  fi
}

run_agent_out_probe() {
  local out="$META_ARTIFACTS_DIR/agent-out.json"
  local cleanup_plan="$META_ARTIFACTS_DIR/agent-out.cleanup-plan.json"
  local cleanup_apply="$META_ARTIFACTS_DIR/agent-out.cleanup-apply.json"
  local cleanup_bad_digest="$META_ARTIFACTS_DIR/agent-out.cleanup-bad-digest.json"
  local cleanup_bad_digest_stderr="$META_ARTIFACTS_DIR/agent-out.cleanup-bad-digest.stderr"
  local agent_home="$TMP_ROOT/meta-agent-home"
  local path physical_agent_home physical_path cleanup_digest
  require_meta_bin agent-out || return 1
  mkdir -p "$agent_home"
  (
    cd "$META_WORKSPACE"
    AGENT_HOME="$agent_home" agent-out project \
      --repo "$META_WORKSPACE" \
      --topic runtime-smoke-meta \
      --mkdir \
      --format json
  ) >"$out" 2>&1
  grep -q '"ok": true' "$out"
  path="$(sed -n 's/.*"path": "\([^"]*\)".*/\1/p' "$out" | head -1)"
  physical_agent_home="$(cd "$agent_home" && pwd -P)"
  physical_path="$(cd "$path" && pwd -P)"
  case "$physical_path" in
    "$physical_agent_home"/out/*)
      test -d "$path"
      ;;
    *)
      echo "runtime-smoke meta: agent-out path outside temp AGENT_HOME: $path" >&2
      return 1
      ;;
  esac

  mkdir -p "$agent_home/out/nils-versions/v-old" "$agent_home/out/loose-debug" "$agent_home/out/late-debug"
  printf 'old cache\n' >"$agent_home/out/nils-versions/v-old/file.txt"
  printf 'debug artifact\n' >"$agent_home/out/loose-debug/file.txt"
  printf 'late debug artifact\n' >"$agent_home/out/late-debug/file.txt"

  (
    cd "$META_WORKSPACE"
    AGENT_HOME="$agent_home" agent-out cleanup plan \
      --agent-home "$agent_home" \
      --format json
  ) >"$cleanup_plan" 2>&1
  cleanup_digest="$(
    python3 - "$cleanup_plan" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert doc["schema_version"] == "cli.agent-out.cleanup.plan.v1"
assert doc["ok"] is True
result = doc["result"]
items = {item["name"]: item for item in result["items"]}
assert items["nils-versions"]["category"] == "cache"
assert items["nils-versions"]["action"] == "delete"
assert items["loose-debug"]["category"] == "top-level-noncanonical"
assert items["loose-debug"]["action"] == "needs-policy"
assert items["late-debug"]["category"] == "top-level-noncanonical"
assert items["late-debug"]["action"] == "needs-policy"
print(result["plan_digest"])
PY
  )"

  if (
    cd "$META_WORKSPACE"
    AGENT_HOME="$agent_home" agent-out cleanup apply \
      --agent-home "$agent_home" \
      --plan-file "$cleanup_plan" \
      --confirm-digest "sha256:not-the-plan" \
      --format json
  ) >"$cleanup_bad_digest" 2>"$cleanup_bad_digest_stderr"; then
    echo "runtime-smoke meta: cleanup apply accepted a mismatched plan digest" >&2
    return 1
  fi
  python3 - "$cleanup_bad_digest" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert doc["ok"] is False
assert doc["error"]["code"] == "cleanup-digest-mismatch"
PY
  test -e "$agent_home/out/nils-versions"
  test -e "$agent_home/out/loose-debug"
  test -e "$agent_home/out/late-debug"

  (
    cd "$META_WORKSPACE"
    AGENT_HOME="$agent_home" agent-out cleanup apply \
      --agent-home "$agent_home" \
      --plan-file "$cleanup_plan" \
      --confirm-digest "$cleanup_digest" \
      --format json
  ) >"$cleanup_apply" 2>&1
  python3 - "$cleanup_apply" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert doc["schema_version"] == "cli.agent-out.cleanup.apply.v1"
assert doc["ok"] is True
result = doc["result"]
assert result["applied"] is True
# nils-cli >= v1.20.0 (sympoies/nils-cli#990) hardened cleanup apply: only
# delete-action entries (the nils-versions cache) are removed automatically;
# top-level-noncanonical dirs are `needs-policy` and survive apply until a
# human records a policy decision, so neither loose-debug nor late-debug is
# touched here.
assert result["summary"]["deleted"] == 1
assert result["summary"]["skipped"] == 0
statuses = {entry["status"] for entry in result["entries"]}
assert statuses == {"deleted"}
deleted = [
    entry for entry in result["entries"]
    if entry["status"] == "deleted" and entry["path"].endswith("/nils-versions")
]
assert len(deleted) == 1
PY
  test ! -e "$agent_home/out/nils-versions"
  test -e "$agent_home/out/loose-debug"
  test -e "$agent_home/out/late-debug"
  test -d "$path"
}

run_agent_scope_lock_probe() {
  local create_out="$META_ARTIFACTS_DIR/agent-scope-lock.create.json"
  local validate_out="$META_ARTIFACTS_DIR/agent-scope-lock.validate.json"
  require_meta_bin agent-scope-lock || return 1
  mkdir -p "$META_WORKSPACE/tests/runtime-smoke"
  printf 'scope-lock fixture\n' >"$META_WORKSPACE/tests/runtime-smoke/scope-lock.txt"
  (
    cd "$META_WORKSPACE"
    agent-scope-lock create \
      --path README.md \
      --path tests/runtime-smoke \
      --owner runtime-smoke \
      --format json
    agent-scope-lock validate --changes all --format json
  ) >"$create_out" 2>&1
  sed -n '/"schema_version": "cli.agent-scope-lock.validate.v1"/,$p' "$create_out" >"$validate_out"
  grep -q '"schema_version": "cli.agent-scope-lock.create.v1"' "$create_out"
  grep -q '"schema_version": "cli.agent-scope-lock.validate.v1"' "$create_out"
  grep -q '"ok": true' "$validate_out"
}

run_heuristic_inbox_probe() {
  local shared_root="$REPO_ROOT/core/policies/heuristic-system"
  local inbox_dir="$shared_root/error-inbox"
  local archived_case="$inbox_dir/archive/2026/deliver-gitlab-mr-skipped-pipeline-and-cleanup"
  local operation_record="$shared_root/operation-records/ci-watch-exact-commit-keying"
  local archived_record="$shared_root/operation-records/archive/2026/github-pr-required-check-gating"
  local product out
  require_meta_bin heuristic-inbox || return 1
  test -f "$shared_root/HEURISTIC_SYSTEM.md"
  test -d "$inbox_dir"
  test -d "$archived_case"
  test -d "$operation_record"
  test -d "$archived_record"

  for product in codex claude; do
    out="$META_ARTIFACTS_DIR/heuristic-inbox.${product}.json"
    (
      cd "$META_WORKSPACE"
      export AGENT_RUNTIME_PRODUCT="$product"
      export AGENT_RUNTIME_HEURISTIC_SYSTEM_ROOT="$shared_root"
      heuristic-inbox list \
        --inbox-dir "$AGENT_RUNTIME_HEURISTIC_SYSTEM_ROOT/error-inbox" \
        --include-archived \
        --format json
    ) >"$out" 2>&1
    grep -q '"schema_version": "cli.heuristic-inbox.list.v1"' "$out"
    grep -q '"ok": true' "$out"
    grep -q 'Deliver GitLab MR Skipped Pipeline And Cleanup Gaps' "$out"
  done

  heuristic-inbox verify "$archived_case" --strict --format json \
    >"$META_ARTIFACTS_DIR/heuristic-inbox.archived-case.verify.json"
  grep -q '"ok": true' "$META_ARTIFACTS_DIR/heuristic-inbox.archived-case.verify.json"

  heuristic-inbox verify "$operation_record" --strict --format json \
    >"$META_ARTIFACTS_DIR/heuristic-inbox.operation-record.verify.json"
  grep -q '"ok": true' "$META_ARTIFACTS_DIR/heuristic-inbox.operation-record.verify.json"

  heuristic-inbox verify "$archived_record" --strict --format json \
    >"$META_ARTIFACTS_DIR/heuristic-inbox.archived-record.verify.json"
  grep -q '"ok": true' "$META_ARTIFACTS_DIR/heuristic-inbox.archived-record.verify.json"
}

run_heuristic_session_closeout_probe() {
  local body="$REPO_ROOT/core/skills/meta/heuristic-session-closeout/SKILL.md.tera"
  local shared_root="$REPO_ROOT/core/policies/heuristic-system"
  local out="$META_ARTIFACTS_DIR/heuristic-session-closeout.contract.txt"

  test -f "$body"
  test -d "$shared_root/error-inbox"
  test -d "$shared_root/operation-records"
  grep -q "session's goal has been achieved" "$body"
  grep -q "heuristic-inbox verify" "$body"
  grep -q "heuristic-inbox deliver" "$body"
  grep -q "workflow::heuristic-records" "$body"
  grep -q "forge-cli pr ready" "$body"
  grep -q "forge-cli pr merge" "$body"
  grep -q "never a direct push to \`main\`" "$body"
  grep -q "git checkout -- core/policies/heuristic-system" "$body"
  {
    printf 'body=%s\n' "$body"
    printf 'shared_root=%s\n' "$shared_root"
    printf 'verified=session-goal-trigger commit-boundary retained-record-routing\n'
  } >"$out"
}

run_lifecycle_skill_probe() {
  local skill="$1"
  local fixture="$2"
  local out="$META_ARTIFACTS_DIR/${skill}.governance.txt"
  local body="$REPO_ROOT/core/skills/meta/$skill/SKILL.md.tera"

  test -f "$body"
  test -f "$REPO_ROOT/build/codex/plugins/meta/skills/$skill/SKILL.md"
  test -f "$REPO_ROOT/build/claude/plugins/meta/skills/$skill/SKILL.md"
  grep -q 'core/skills' "$body"
  grep -q 'manifests/skills.yaml' "$body"
  grep -q 'manifests/plugins.yaml' "$body"
  grep -q 'agent-runtime' "$body"

  bash "$REPO_ROOT/scripts/ci/skill-governance-audit.sh" --fixture "$fixture" >"$out" 2>&1
  grep -q "skill-governance-audit: ${fixture} fixture OK" "$out"
}

run_create_skill_probe() {
  run_lifecycle_skill_probe create-skill create
}

run_remove_skill_probe() {
  run_lifecycle_skill_probe remove-skill remove
}

run_project_lifecycle_skill_probe() {
  local skill="$1"
  local fixture="$2"
  local out="$META_ARTIFACTS_DIR/${skill}.governance.txt"
  local body="$REPO_ROOT/core/skills/meta/$skill/SKILL.md.tera"

  test -f "$body"
  test -f "$REPO_ROOT/build/codex/plugins/meta/skills/$skill/SKILL.md"
  test -f "$REPO_ROOT/build/claude/plugins/meta/skills/$skill/SKILL.md"
  grep -q '.agents/skills' "$body"
  grep -q 'git rev-parse --show-toplevel' "$body"
  grep -q '.agents/scripts' "$body"

  bash "$REPO_ROOT/scripts/ci/skill-governance-audit.sh" --fixture "$fixture" >"$out" 2>&1
  grep -q "skill-governance-audit: ${fixture} fixture OK" "$out"
}

run_create_project_helper_probe() {
  local helper="$REPO_ROOT/core/skills/meta/create-project-skill/scripts/create-project-skill.sh"
  local default_root="$TMP_ROOT/workspaces/create-project-default"
  local codex_root="$TMP_ROOT/workspaces/create-project-codex"
  local bridge_root="$TMP_ROOT/workspaces/create-project-bridge"
  local bridge_no_name_root="$TMP_ROOT/workspaces/create-project-bridge-no-name"
  local reject_root="$TMP_ROOT/workspaces/create-project-reject"

  test -x "$helper"

  rm -rf "$default_root" "$codex_root" "$bridge_root" "$bridge_no_name_root" "$reject_root"
  mkdir -p "$default_root" "$codex_root" "$bridge_root" "$bridge_no_name_root" "$reject_root"
  git -C "$default_root" init -q
  git -C "$codex_root" init -q
  git -C "$bridge_root" init -q
  git -C "$bridge_no_name_root" init -q
  git -C "$reject_root" init -q

  (
    cd "$default_root"
    "$helper" project-sample-skill \
      --description "Sample project skill." \
      --with-script \
      --with-tests \
      --with-wrapper project-sample-skill \
      >"$META_ARTIFACTS_DIR/create-project-default.txt" 2>&1
  )
  test -f "$default_root/.agents/skills/project-sample-skill/SKILL.md"
  test -x "$default_root/.agents/skills/project-sample-skill/scripts/project-sample-skill.sh"
  test -x "$default_root/.agents/scripts/project-sample-skill.sh"
  test -L "$default_root/.claude/skills"
  test "$(readlink "$default_root/.claude/skills")" = "../.agents/skills"
  grep -q '^\.claude/$' "$default_root/.gitignore"
  test ! -e "$default_root/.agents/scripts/pre-pr.sh"

  (
    cd "$codex_root"
    "$helper" project-codex-only-skill \
      --description "Codex only skill." \
      --codex-only \
      >"$META_ARTIFACTS_DIR/create-project-codex.txt" 2>&1
  )
  test -f "$codex_root/.agents/skills/project-codex-only-skill/SKILL.md"
  test ! -e "$codex_root/.claude"

  (
    cd "$bridge_root"
    "$helper" project-existing-bridge-skill \
      --description "Existing bridge skill." \
      --codex-only \
      --with-script \
      >"$META_ARTIFACTS_DIR/create-project-bridge-create.txt" 2>&1
    "$helper" project-existing-bridge-skill \
      --bridge-only \
      --with-wrapper project-existing-bridge-skill \
      >"$META_ARTIFACTS_DIR/create-project-bridge-only.txt" 2>&1
  )
  test -L "$bridge_root/.claude/skills"
  test "$(readlink "$bridge_root/.claude/skills")" = "../.agents/skills"
  test -x "$bridge_root/.agents/scripts/project-existing-bridge-skill.sh"

  mkdir -p "$bridge_no_name_root/.agents/skills"
  if (cd "$bridge_no_name_root" && "$helper" --bridge-only --with-wrapper missing-name >"$META_ARTIFACTS_DIR/create-project-reject-bridge-wrapper-no-name.txt" 2>&1); then
    return 1
  fi
  test ! -e "$bridge_no_name_root/.claude"

  if (cd "$reject_root" && "$helper" rejected-skill --claude-only >"$META_ARTIFACTS_DIR/create-project-reject-claude-only.txt" 2>&1); then
    return 1
  fi
  if (cd "$reject_root" && "$helper" rejected-skill --target claude >"$META_ARTIFACTS_DIR/create-project-reject-target-claude.txt" 2>&1); then
    return 1
  fi
  if (cd "$reject_root" && "$helper" --link-only >"$META_ARTIFACTS_DIR/create-project-reject-link-only.txt" 2>&1); then
    return 1
  fi
  if (cd "$reject_root" && "$helper" unprefixed-skill --description "Unprefixed." >"$META_ARTIFACTS_DIR/create-project-reject-unprefixed.txt" 2>&1); then
    return 1
  fi
}

run_create_project_skill_probe() {
  run_project_lifecycle_skill_probe create-project-skill create-project
  run_create_project_helper_probe
}

run_remove_project_skill_probe() {
  run_project_lifecycle_skill_probe remove-project-skill remove-project
}

run_repo_retro_probe() {
  local out="$META_ARTIFACTS_DIR/repo-retro.json"
  require_meta_bin repo-retro || return 1
  (
    cd "$META_WORKSPACE"
    repo-retro report \
      --repo "$META_WORKSPACE" \
      --from 2026-05-01 \
      --to 2026-05-02 \
      --format json
  ) >"$out" 2>&1
  grep -q '"schema_version": "cli.repo-retro.report.v2"' "$out"
  grep -q '"ok": true' "$out"
}

run_semantic_commit_probe() {
  local out="$META_ARTIFACTS_DIR/semantic-commit.dry-run.txt"
  local msg="$META_ARTIFACTS_DIR/semantic-commit-message.txt"
  require_meta_bin semantic-commit || return 1
  printf 'semantic fixture\n' >"$META_WORKSPACE/semantic-fixture.txt"
  printf '%s\n' \
    'test(runtime-smoke): validate semantic commit probe' \
    '' \
    '- Adds a staged temp fixture for dry-run validation.' >"$msg"
  (
    cd "$META_WORKSPACE"
    git add semantic-fixture.txt
    semantic-commit commit --repo "$META_WORKSPACE" --message-file "$msg" --dry-run --summary none
    ! git rev-parse --verify HEAD >/dev/null 2>&1
  ) >"$out" 2>&1
}

run_sync_runtime_surfaces_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.dry-run.txt"

  (
    cd "$REPO_ROOT"
    bash scripts/sync-runtime-surfaces.sh \
      --source-root "$REPO_ROOT" \
      --product codex \
      --no-pull
  ) >"$out" 2>&1

  grep -q "git pull skipped (--no-pull)" "$out"
  grep -q "skill-governance-audit.sh --check-counts" "$out"
  grep -q "skill-governance-audit: counts OK" "$out"
  grep -q "agent-runtime render" "$out"
  grep -q -- "--target home-prompt" "$out"
  grep -q -- "--target home-prompt --product codex" "$out"
  grep -q "agent-runtime install" "$out"
  grep -q "agent-runtime prune-stale" "$out"
  grep -q -- "--dry-run" "$out"
  grep -q "agent-runtime doctor" "$out"
  grep -Eq "(\\+ codex debug prompt-input|codex prompt-input skipped)" "$out"
  grep -q "summary: synced surfaces for codex; mode=dry-run; prune=planned; doctor=planned" "$out"
  grep -q "codex plugin marketplace materialize dry-run" "$out"
  grep -q "codex plugin registry planned: marketplace=codex-kit" "$out"
  grep -q "codex plugins=planned" "$out"
  grep -q "home-prompt=planned" "$out"
  grep -q "codex plugin marketplace add" "$out"
}

run_sync_runtime_surfaces_home_prompt_apply_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.home-prompt-apply.txt"
  local collision_out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.home-prompt-collision.txt"
  local root="$TMP_ROOT/sync-home-prompt-apply"
  local source_root="$root/source"
  local home="$root/home"
  local codex_home="$home/.codex"
  local collision_home="$root/collision-home"
  local collision_codex_home="$collision_home/.codex"
  local state_home="$root/state"
  local stub_bin="$root/bin"
  local stub_log="$root/codex.log"
  local status

  rm -rf "$root"
  mkdir -p "$source_root/scripts/ci" \
    "$source_root/targets/codex/.agents/plugins" \
    "$source_root/targets/codex/plugins/meta/.codex-plugin" \
    "$codex_home" "$collision_codex_home" "$stub_bin"
  git -C "$source_root" init -q

  printf '# raw AGENT_HOME fixture\n' >"$source_root/AGENT_HOME.md"
  ln -s "$source_root/AGENT_HOME.md" "$codex_home/AGENTS.md"
  printf 'manual codex policy\n' >"$collision_codex_home/AGENTS.md"

  cat >"$source_root/scripts/ci/skill-governance-audit.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  --check-counts)
    printf 'skill-governance-audit: counts OK skills=1 targets=1\n'
    ;;
  *)
    printf 'unexpected skill-governance-audit args: %s\n' "$*" >&2
    exit 64
    ;;
esac
SH
  chmod +x "$source_root/scripts/ci/skill-governance-audit.sh"

  cat >"$source_root/targets/codex/.agents/plugins/marketplace.json" <<'JSON'
{
  "name": "codex-kit",
  "plugins": [
    {
      "name": "meta",
      "version": "0.1.0",
      "source": { "source": "local", "path": "./plugins/meta" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
JSON
  cat >"$source_root/targets/codex/plugins/meta/.codex-plugin/plugin.json" <<'JSON'
{"name":"meta","version":"0.1.0","description":"meta fixture","skills":[{"id":"demo","source":"core/skills/meta/demo"}]}
JSON

  cat >"$stub_bin/agent-runtime" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

command_name="${1:-}"
shift || true
source_root=""
product=""
target="product"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-root)
      source_root="$2"
      shift 2
      ;;
    --target)
      target="$2"
      shift 2
      ;;
    --product)
      product="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

case "$command_name" in
  render)
    if [ "$target" = "home-prompt" ]; then
      render_product="${product:-neutral}"
      mkdir -p "$source_root/build/$render_product"
      printf '# AGENT_HOME %s fixture\n' "$render_product" >"$source_root/build/$render_product/AGENT_HOME.md"
      printf 'render home-prompt %s\n' "$render_product"
    else
      mkdir -p "$source_root/build/$product/plugins/meta/skills/demo"
      printf '# Demo skill\n' >"$source_root/build/$product/plugins/meta/skills/demo/SKILL.md"
      printf 'render %s\n' "$product"
    fi
    ;;
  install)
    test -d "$source_root/build/$product"
    printf 'install %s\n' "$product"
    ;;
  *)
    printf 'unexpected agent-runtime command: %s\n' "$command_name" >&2
    exit 64
    ;;
esac
SH
  cat >"$stub_bin/codex" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$CODEX_STUB_LOG"
case "$*" in
  "plugin list --json")
    printf '{"installed":[],"available":[]}\n'
    ;;
  "plugin marketplace list --json")
    printf '{"marketplaces":[]}\n'
    ;;
esac
SH
  chmod +x "$stub_bin/agent-runtime" "$stub_bin/codex"
  : >"$stub_log"

  (
    cd "$REPO_ROOT"
    PATH="$stub_bin:$PATH" HOME="$home" CODEX_HOME="$codex_home" \
      CODEX_AGENT_STATE_HOME="$state_home" CODEX_STUB_LOG="$stub_log" \
      bash scripts/sync-runtime-surfaces.sh \
      --source-root "$source_root" \
      --product codex \
      --no-pull \
      --no-prune \
      --no-verify \
      --apply
  ) >"$out" 2>&1

  assert_symlink_target "$codex_home/AGENTS.md" "$source_root/build/codex/AGENT_HOME.md"
  grep -q "rewiring managed home prompt product=codex" "$out"
  grep -q "home-prompt=wired" "$out"
  grep -q "codex plugin registry installed: marketplace=codex-kit" "$out"
  grep -q "plugin marketplace add $state_home/plugin-marketplaces/codex-kit" "$stub_log"
  grep -q "plugin add meta@codex-kit" "$stub_log"

  set +e
  (
    cd "$REPO_ROOT"
    PATH="$stub_bin:$PATH" HOME="$collision_home" CODEX_HOME="$collision_codex_home" \
      CODEX_AGENT_STATE_HOME="$state_home-collision" CODEX_STUB_LOG="$stub_log" \
      bash scripts/sync-runtime-surfaces.sh \
      --source-root "$source_root" \
      --product codex \
      --no-pull \
      --no-prune \
      --no-verify \
      --apply
  ) >"$collision_out" 2>&1
  status=$?
  set -e
  [ "$status" -ne 0 ]
  grep -q "refusing to overwrite" "$collision_out"
}

run_setup_render_before_install_probe() {
  local out="$META_ARTIFACTS_DIR/setup.render-before-install.dry-run.txt"
  local apply_out="$META_ARTIFACTS_DIR/setup.render-before-install.apply.txt"
  local home="$TMP_ROOT/setup-render-home"
  local apply_home="$TMP_ROOT/setup-render-apply-home"
  local stub_bin="$TMP_ROOT/setup-render-bin"
  local source_root="$apply_home/.config/agent-runtime-kit"
  local collision_out="$META_ARTIFACTS_DIR/setup.home-prompt-collision.txt"
  local collision_home="$TMP_ROOT/setup-render-collision-home"
  local collision_source_root="$collision_home/.config/agent-runtime-kit"
  local status

  mkdir -p "$home"
  (
    cd "$REPO_ROOT"
    HOME="$home" CODEX_HOME="$home/.codex" \
      bash scripts/setup.sh \
      --profile core \
      --skip-homebrew-install \
      --skip-cli-tools \
      --dry-run
  ) >"$out" 2>&1

  python3 - "$out" <<'PY'
import sys

path = sys.argv[1]
lines = open(path, encoding="utf-8").read().splitlines()
render_lines = [
    (idx, line)
    for idx, line in enumerate(lines, 1)
    if line.startswith("+ agent-runtime render ")
]
install_lines = [
    (idx, line)
    for idx, line in enumerate(lines, 1)
    if line.startswith("+ agent-runtime install ")
]
bootstrap_lines = [
    (idx, line)
    for idx, line in enumerate(lines, 1)
    if line.startswith("+ agent-runtime bootstrap-host ")
]
sync_lines = [
    (idx, line)
    for idx, line in enumerate(lines, 1)
    if line.startswith("+ bash ") and "scripts/sync-runtime-surfaces.sh" in line
]
link_lines = [
    (idx, line)
    for idx, line in enumerate(lines, 1)
    if line.startswith("+ ln -s ")
]
preflight_lines = [
    (idx, line)
    for idx, line in enumerate(lines, 1)
    if line.startswith("+ agent-docs preflight --docs-home ")
]

assert len(link_lines) == 2, link_lines
assert len(preflight_lines) == 2, preflight_lines
assert len(sync_lines) == 2, sync_lines
sync_products = []
for _, sync_line in sync_lines:
    if "--product claude" in sync_line:
        sync_products.append("claude")
    elif "--product codex" in sync_line:
        sync_products.append("codex")
    else:
        raise AssertionError(sync_line)
    assert "--no-pull" in sync_line, sync_line
    if sync_products[-1] == "claude":
        assert "--no-prune" in sync_line, sync_line
    else:
        assert "--no-prune" not in sync_line, sync_line
    assert "--no-verify" in sync_line, sync_line
    assert "--dry-run" in sync_line, sync_line
assert sync_products == ["claude", "codex"], sync_products
assert max(idx for idx, _ in link_lines) < min(idx for idx, _ in preflight_lines), lines
if bootstrap_lines:
    assert len(bootstrap_lines) == 1, bootstrap_lines
    bootstrap_line = bootstrap_lines[0][1]
    assert "--product both" in bootstrap_line, bootstrap_line
    assert "--dry-run" in bootstrap_line, bootstrap_line
    assert "--skip-homebrew-install" in bootstrap_line, bootstrap_line
    assert "--skip-cli-tools" in bootstrap_line, bootstrap_line
    assert max(idx for idx, _ in preflight_lines) < bootstrap_lines[0][0], lines
    assert bootstrap_lines[0][0] < min(idx for idx, _ in sync_lines), lines
else:
    home_render_lines = [
        (idx, line) for idx, line in render_lines if "--target home-prompt" in line
    ]
    product_render_lines = [
        (idx, line) for idx, line in render_lines if "--target home-prompt" not in line
    ]
    assert len(home_render_lines) == 3, home_render_lines
    assert len(product_render_lines) == 2, product_render_lines
    assert any("--target home-prompt --product codex" in line for _, line in home_render_lines), home_render_lines
    assert any("--target home-prompt --product claude" in line for _, line in home_render_lines), home_render_lines
    assert len(install_lines) == 2, install_lines
    assert any("--product codex" in line for _, line in product_render_lines), product_render_lines
    assert any("--product claude" in line for _, line in product_render_lines), product_render_lines
    assert max(idx for idx, _ in home_render_lines) < min(idx for idx, _ in link_lines), lines
    assert max(idx for idx, _ in preflight_lines) < min(idx for idx, _ in product_render_lines), lines
    assert max(idx for idx, _ in product_render_lines) < min(idx for idx, _ in install_lines), lines
    assert max(idx for idx, _ in install_lines) < min(idx for idx, _ in sync_lines), lines
PY

  mkdir -p "$stub_bin" "$source_root/.git" "$source_root/scripts"
  printf '# AGENT_HOME fixture\n' >"$source_root/AGENT_HOME.md"
  cat >"$source_root/scripts/sync-runtime-surfaces.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'sync-runtime-surfaces %s\n' "$*"
SH
  cat >"$stub_bin/brew" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  --prefix)
    printf '/opt/homebrew\n'
    ;;
  list)
    exit 1
    ;;
  tap | install | upgrade)
    printf 'stub brew %s\n' "$*"
    ;;
  *)
    printf 'stub brew %s\n' "$*"
    ;;
esac
SH
  cat >"$stub_bin/agent-runtime" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

command_name="${1:-}"
shift || true
source_root=""
product=""
target="product"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-root)
      source_root="$2"
      shift 2
      ;;
    --target)
      target="$2"
      shift 2
      ;;
    --product)
      product="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

case "$command_name" in
  render)
    if [ "$target" = "home-prompt" ]; then
      render_product="${product:-neutral}"
      mkdir -p "$source_root/build/$render_product"
      printf '# AGENT_HOME %s fixture\n' "$render_product" >"$source_root/build/$render_product/AGENT_HOME.md"
      printf 'render home-prompt %s\n' "$render_product"
    else
      mkdir -p "$source_root/build/$product"
      printf 'render %s\n' "$product"
    fi
    ;;
  install)
    test -d "$source_root/build/$product"
    printf 'install %s\n' "$product"
    ;;
  prune-stale)
    printf 'prune-stale %s\n' "$product"
    ;;
  doctor)
    printf 'doctor %s\n' "$product"
    ;;
  *)
    printf 'unexpected agent-runtime command: %s\n' "$command_name" >&2
    exit 64
    ;;
esac
SH
  cat >"$stub_bin/agent-docs" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

command_name="${1:-}"
shift || true

case "$command_name" in
  list)
    printf '%s\n' '{"intents":["project-dev","task-tools","setup-extra"]}'
    ;;
  preflight)
    printf 'agent-docs preflight %s\n' "$*"
    ;;
  *)
    printf 'unexpected agent-docs command: %s\n' "$command_name" >&2
    exit 64
    ;;
esac
SH
  chmod +x "$stub_bin/brew" "$stub_bin/agent-runtime" "$stub_bin/agent-docs"

  (
    cd "$REPO_ROOT"
    PATH="$stub_bin:$PATH" HOME="$apply_home" CODEX_HOME="$apply_home/.codex" \
      bash scripts/setup.sh \
      --profile core \
      --skip-homebrew-install \
      --skip-cli-tools
  ) >"$apply_out" 2>&1

  assert_symlink_target "$apply_home/.codex/AGENTS.md" "$source_root/build/codex/AGENT_HOME.md"
  assert_symlink_target "$apply_home/.claude/CLAUDE.md" "$source_root/build/claude/AGENT_HOME.md"
  grep -q "+ agent-docs preflight --docs-home $source_root --project-path $source_root --intent project-dev --strict" "$apply_out"
  grep -q "+ agent-docs preflight --docs-home $source_root --project-path $source_root --intent task-tools --strict" "$apply_out"
  grep -q "+ agent-docs preflight --docs-home $source_root --project-path $source_root --intent setup-extra --strict" "$apply_out"
  grep -q "docs_audit: not-run (legacy key retained; rendered home prompts use source-root docs_preflight)" "$apply_out"
  grep -q "docs_preflight: .*--intent setup-extra --strict" "$apply_out"
  grep -q "+ bash $source_root/scripts/sync-runtime-surfaces.sh --source-root $source_root --product claude --no-pull --no-prune --no-verify --apply" "$apply_out"
  grep -q "+ bash $source_root/scripts/sync-runtime-surfaces.sh --source-root $source_root --product codex --no-pull --no-verify --apply" "$apply_out"
  grep -q "sync-runtime-surfaces --source-root $source_root --product claude --no-pull --no-prune --no-verify --apply" "$apply_out"
  grep -q "sync-runtime-surfaces --source-root $source_root --product codex --no-pull --no-verify --apply" "$apply_out"
  grep -q "codex_home_prompt:" "$apply_out"
  grep -q "claude_home_prompt:" "$apply_out"
  grep -q "claude_plugin_registry_activation: sync-runtime-surfaces.sh" "$apply_out"
  grep -q "codex_plugin_registry_activation: sync-runtime-surfaces.sh" "$apply_out"

  python3 - "$apply_out" <<'PY'
import sys

events = [
    line
    for line in open(sys.argv[1], encoding="utf-8").read().splitlines()
    if line.startswith(("render ", "install "))
]
assert events == [
    "render home-prompt neutral",
    "render home-prompt codex",
    "render home-prompt claude",
    "render codex",
    "render claude",
    "install claude",
    "install codex",
], events
PY

  mkdir -p "$collision_home/.codex" "$collision_source_root/.git"
  printf '# AGENT_HOME fixture\n' >"$collision_source_root/AGENT_HOME.md"
  printf 'manual codex policy\n' >"$collision_home/.codex/AGENTS.md"
  set +e
  (
    cd "$REPO_ROOT"
    PATH="$stub_bin:$PATH" HOME="$collision_home" CODEX_HOME="$collision_home/.codex" \
      bash scripts/setup.sh \
      --profile core \
      --skip-homebrew-install \
      --skip-cli-tools
  ) >"$collision_out" 2>&1
  status=$?
  set -e
  [ "$status" -ne 0 ]
  grep -q "refusing to overwrite" "$collision_out"
}

run_sync_runtime_surfaces_no_prune_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.no-prune.txt"

  (
    cd "$REPO_ROOT"
    bash scripts/sync-runtime-surfaces.sh \
      --source-root "$REPO_ROOT" \
      --product codex \
      --no-pull \
      --no-prune
  ) >"$out" 2>&1

  grep -q "prune skipped (--no-prune) for product=codex" "$out"
  grep -q "summary: synced surfaces for codex; mode=dry-run; prune=skipped; doctor=planned" "$out"
  ! grep -q "agent-runtime prune-stale" "$out"
}

run_sync_runtime_surfaces_worktree_guard_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.worktree-guard.txt"
  local worktree_root="$TMP_ROOT/workspaces/sync-runtime-surfaces-linked-worktree"
  local status

  rm -rf "$worktree_root"
  git -C "$REPO_ROOT" worktree add --detach "$worktree_root" HEAD >"$out" 2>&1
  set +e
  bash "$REPO_ROOT/scripts/sync-runtime-surfaces.sh" \
    --source-root "$worktree_root" \
    --apply \
    --product codex \
    --no-pull \
    --no-verify >>"$out" 2>&1
  status=$?
  set -e
  git -C "$REPO_ROOT" worktree remove --force "$worktree_root" >>"$out" 2>&1 || true
  git -C "$REPO_ROOT" worktree prune >>"$out" 2>&1 || true

  [ "$status" -ne 0 ]
  grep -q "refusing live sync from a git worktree" "$out"
  grep -q "durable primary checkout" "$out"
}

run_sync_runtime_surfaces_prune_fixture_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.prune-fixture.txt"
  local codex_home="$TMP_ROOT/sync-prune/codex-home"
  local claude_home="$TMP_ROOT/sync-prune/claude-home"
  local codex_legacy_stale="$codex_home/skills/meta/removed-skill"
  local codex_legacy_foreign="$codex_home/skills/meta/foreign-skill"
  local codex_legacy_alias="$codex_home/skills/meta/agent-docs-alias"
  local codex_legacy_regular="$codex_home/skills/meta/user-note"
  local codex_stale_dir="$codex_home/plugins/meta/skills/removed-skill"
  local codex_foreign="$codex_home/plugins/meta/skills/foreign-skill/SKILL.md"
  local codex_regular="$codex_home/plugins/meta/skills/user-note/SKILL.md"
  local claude_stale_dir="$claude_home/plugins/meta/skills/removed-skill"
  local claude_foreign="$claude_home/plugins/meta/skills/foreign-skill/SKILL.md"
  local claude_regular="$claude_home/plugins/meta/skills/user-note/SKILL.md"

  require_meta_bin agent-runtime || return 1
  mkdir -p "$codex_home/skills/meta" "$codex_stale_dir/scripts" \
    "$codex_home/plugins/meta/skills/foreign-skill" \
    "$codex_home/plugins/meta/skills/user-note" \
    "$claude_stale_dir/scripts" \
    "$claude_home/plugins/meta/skills/foreign-skill" \
    "$claude_home/plugins/meta/skills/user-note"

  ln -s "$REPO_ROOT/build/codex/plugins/meta/skills/removed-skill" "$codex_legacy_stale"
  ln -s /var/empty/foreign-skill "$codex_legacy_foreign"
  ln -s "$REPO_ROOT/build/codex/plugins/meta/skills/agent-docs" "$codex_legacy_alias"
  printf 'user note\n' >"$codex_legacy_regular"
  ln -s "$REPO_ROOT/build/codex/plugins/meta/skills/removed-skill/SKILL.md" "$codex_stale_dir/SKILL.md"
  ln -s "$REPO_ROOT/build/codex/plugins/meta/skills/removed-skill/scripts/tool.sh" "$codex_stale_dir/scripts/tool.sh"
  ln -s /var/empty/foreign-skill "$codex_foreign"
  printf 'user note\n' >"$codex_regular"
  ln -s "$REPO_ROOT/build/claude/plugins/meta/skills/removed-skill/SKILL.md" "$claude_stale_dir/SKILL.md"
  ln -s "$REPO_ROOT/build/claude/plugins/meta/skills/removed-skill/scripts/tool.sh" "$claude_stale_dir/scripts/tool.sh"
  ln -s /var/empty/foreign-skill "$claude_foreign"
  printf 'user note\n' >"$claude_regular"

  {
    agent-runtime prune-stale \
      --source-root "$REPO_ROOT" \
      --product codex \
      --live-home "$codex_home" \
      --apply
    agent-runtime prune-stale \
      --source-root "$REPO_ROOT" \
      --product claude \
      --live-home "$claude_home" \
      --apply
  } >"$out" 2>&1

  (
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$REPO_ROOT"
    APPLY=1
    cleanup_codex_legacy_flat_skill_root "$codex_home"
  ) >>"$out" 2>&1

  grep -q "removed legacy Codex flat skill symlink skills/meta/removed-skill" "$out"
  grep -q "removed symlink plugins/meta/skills/removed-skill/SKILL.md" "$out"
  grep -q "removed empty directory plugins/meta/skills/removed-skill" "$out"
  grep -q "skip foreign symlink" "$out"
  grep -q "skip regular file" "$out"
  test ! -L "$codex_legacy_stale"
  test -L "$codex_legacy_foreign"
  test -L "$codex_legacy_alias"
  test -f "$codex_legacy_regular"
  test ! -d "$codex_stale_dir"
  test -L "$codex_foreign"
  test -f "$codex_regular"
  test ! -d "$claude_stale_dir"
  test -L "$claude_foreign"
  test -f "$claude_regular"
}

run_sync_runtime_surfaces_hermes_legacy_cleanup_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.hermes-legacy-cleanup.txt"
  local hermes_home="$TMP_ROOT/sync-prune/hermes-home"
  local stale_skill="$hermes_home/skills/meta/agent-docs/SKILL.md"
  local stale_ref="$hermes_home/skills/conversation/actionable-advice/references/prompts/actionable-advice.md"
  local copied_skill="$hermes_home/skills/meta/semantic-commit"
  local modified_copy="$hermes_home/skills/meta/agent-out"
  local foreign="$hermes_home/skills/meta/foreign-skill/SKILL.md"
  local regular="$hermes_home/skills/meta/user-note/SKILL.md"
  local development_policy="$hermes_home/skills/development-policy/SKILL.md"

  require_meta_bin agent-runtime || return 1
  rm -rf "$hermes_home"
  mkdir -p "$(dirname "$stale_skill")" "$(dirname "$stale_ref")" \
    "$(dirname "$foreign")" "$(dirname "$regular")" "$(dirname "$development_policy")"
  ln -s "$REPO_ROOT/build/hermes/plugins/meta/skills/agent-docs/SKILL.md" "$stale_skill"
  ln -s "$REPO_ROOT/build/hermes/plugins/conversation/skills/actionable-advice/references/prompts/actionable-advice.md" "$stale_ref"
  cp -R "$REPO_ROOT/build/hermes/plugins/meta/skills/semantic-commit" "$copied_skill"
  cp -R "$REPO_ROOT/build/hermes/plugins/meta/skills/agent-out" "$modified_copy"
  printf 'local note\n' >"$modified_copy/local-note.txt"
  ln -s /var/empty/foreign-skill "$foreign"
  printf 'user note\n' >"$regular"
  ln -s "$REPO_ROOT/build/hermes/AGENT_HOME.md" "$development_policy"

  (
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$REPO_ROOT"
    APPLY=1
    cleanup_hermes_legacy_runtime_kit_skill_root "$hermes_home"
  ) >"$out" 2>&1

  grep -q "removed legacy Hermes runtime-kit skill symlink skills/meta/agent-docs/SKILL.md" "$out"
  grep -q "removed legacy Hermes runtime-kit skill symlink skills/conversation/actionable-advice/references/prompts/actionable-advice.md" "$out"
  grep -q "removed legacy Hermes runtime-kit skill copy skills/meta/semantic-commit" "$out"
  grep -q "removed empty legacy Hermes runtime-kit skill directory skills/conversation/actionable-advice" "$out"
  grep -q "legacy Hermes runtime-kit skill cleanup removed: symlinks=2 copies=1" "$out"
  test ! -e "$stale_skill"
  test ! -d "$hermes_home/skills/conversation/actionable-advice"
  test ! -d "$copied_skill"
  test -d "$modified_copy"
  test -f "$modified_copy/local-note.txt"
  test -L "$foreign"
  test -f "$regular"
  test -L "$development_policy"
}

# Characterizes the upstream nils-cli limitation tracked in inbox case
# sync-runtime-surfaces-prune-stale-dir-gap: a retired *recursive-file* managed
# skill directory (real files, non-empty dir) is detected as a stale candidate
# but conservatively SKIPPED, not removed, because prune-stale only removes
# provably owned symlinks and empty directories. When nils-cli learns to remove
# a provably owned managed directory tree, this probe will flip and the inbox
# case can be promoted.
run_sync_runtime_surfaces_prune_recursive_stale_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.prune-recursive-stale.txt"
  local claude_home="$TMP_ROOT/sync-prune-recursive/claude-home"
  local stale_dir="$claude_home/plugins/meta/skills/removed-recursive-skill"

  require_meta_bin agent-runtime || return 1
  rm -rf "$claude_home"
  mkdir -p "$stale_dir/scripts"
  printf '# removed recursive skill\n' >"$stale_dir/SKILL.md"
  printf 'echo hi\n' >"$stale_dir/scripts/tool.sh"

  agent-runtime prune-stale \
    --source-root "$REPO_ROOT" \
    --product claude \
    --live-home "$claude_home" \
    --apply --format json >"$out" 2>&1

  grep -q "skipped-non-empty-directory" "$out" &&
    grep -q "skipped-regular-file" "$out" &&
    grep -q "removed-recursive-skill" "$out" &&
    test -d "$stale_dir" &&
    test -f "$stale_dir/SKILL.md"
}

# Regression for the misleading finish signal in inbox case
# sync-runtime-surfaces-prune-stale-dir-gap: when prune-stale reports skipped>0,
# the sync summary must report prune=review-needed (not prune=ok) and surface the
# skipped rel_paths. Sources the script as a library to exercise the reporting
# helpers directly, avoiding the --apply worktree guard and render/install.
run_sync_runtime_surfaces_prune_review_reporting_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.prune-review-reporting.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"

  # APPLY/PRODUCT are consumed by the sourced print_summary, and the source path
  # is dynamic; shellcheck cannot see either through the dynamic source.
  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    set +e
    APPLY=1
    PRODUCT=claude
    PRUNE_SKIPPED_TOTAL=0
    account_prune_skipped claude '{
  "schema_version": "cli.agent-runtime.prune-stale.v1",
  "ok": true,
  "data": {
    "skipped": 2,
    "changes": 0,
    "records": [
      { "kind": "skipped-non-empty-directory", "rel_path": "plugins/meta/skills/removed-recursive-skill" },
      { "kind": "skipped-regular-file", "rel_path": "plugins/meta/skills/removed-recursive-skill/SKILL.md" }
    ]
  }
}'
    echo "PRUNE_SKIPPED_TOTAL=$PRUNE_SKIPPED_TOTAL"
    print_summary
  ) >"$out" 2>&1

  grep -q "PRUNE_SKIPPED_TOTAL=2" "$out" &&
    grep -q "prune-stale left stale candidate for review" "$out" &&
    grep -q "removed-recursive-skill" "$out" &&
    grep -q "prune=review-needed" "$out" &&
    ! grep -q "prune=ok" "$out"
}

# Hermes runtime-kit skills now live under external-skills/agent-runtime-kit, so
# any prune-skipped local skill path is either Hermes-native or historical
# content. The sync must surface that with review-first wording instead of the
# codex/claude "remove ... by hand" imperative.
run_sync_runtime_surfaces_prune_review_hermes_wording_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.prune-review-hermes.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"

  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    set +e
    APPLY=1
    PRODUCT=hermes
    PRUNE_SKIPPED_TOTAL=0
    account_prune_skipped hermes '{
  "schema_version": "cli.agent-runtime.prune-stale.v1",
  "ok": true,
  "data": {
    "skipped": 2,
    "changes": 0,
    "records": [
      { "kind": "skipped-non-empty-directory", "rel_path": "skills/media/gif-search" },
      { "kind": "skipped-regular-file", "rel_path": "skills/media/gif-search/SKILL.md" }
    ]
  }
}'
    echo "PRUNE_SKIPPED_TOTAL=$PRUNE_SKIPPED_TOTAL"
    print_summary
  ) >"$out" 2>&1

  grep -q "PRUNE_SKIPPED_TOTAL=2" "$out" &&
    grep -q "prune-stale left non-kit-managed path untouched (product=hermes)" "$out" &&
    grep -q "gif-search" "$out" &&
    grep -q "prune=review-needed" "$out" &&
    grep -q "Hermes runtime-kit skills are expected under external-skills/agent-runtime-kit" "$out" &&
    grep -q "must be reviewed before deletion" "$out" &&
    grep -q "do not remove them blindly" "$out" &&
    ! grep -q "Review the paths above and remove any retired managed skill directory by hand" "$out" &&
    ! grep -q "prune=ok" "$out"
}

run_sync_runtime_surfaces_claude_settings_hooks_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.claude-settings-hooks.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
  local claude_home="$TMP_ROOT/sync-claude-settings/claude-home"
  local settings="$claude_home/settings.json"

  rm -rf "$claude_home"
  mkdir -p "$claude_home"
  cat >"$settings" <<'JSON'
{
  "theme": "dark",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo custom",
            "statusMessage": "custom hook"
          },
          {
            "type": "command",
            "command": "AGENT_RUNTIME_PRODUCT=claude \"$HOME/.claude/hooks/retired-managed-hook.py\"",
            "statusMessage": "agent-runtime-kit: Retired hook"
          }
        ]
      }
    ]
  }
}
JSON

  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    set +e
    SOURCE_ROOT="$REPO_ROOT"
    APPLY=1
    sync_claude_settings_hooks "$claude_home"
    sync_claude_settings_hooks "$claude_home"
  ) >"$out" 2>&1

  python3 - "$settings" <<'PY'
import json
import sys

settings = json.load(open(sys.argv[1], encoding="utf-8"))
assert settings["theme"] == "dark", settings
bash_groups = [
    group
    for group in settings["hooks"]["PreToolUse"]
    if group.get("matcher") == "Bash"
]
assert len(bash_groups) == 1, bash_groups
commands = [hook.get("command") for hook in bash_groups[0]["hooks"]]
assert "echo custom" in commands, commands
assert not any("retired-managed-hook.py" in command for command in commands), commands
assert any("block-direct-git-worktree.py" in command for command in commands), commands
assert len(commands) == len(set(commands)), commands
assert "UserPromptSubmit" in settings["hooks"], settings["hooks"]
PY
  grep -q "claude settings hooks synced" "$out"
}

run_sync_runtime_surfaces_claude_plugin_registry_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.claude-plugin-registry.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
  local claude_home="$TMP_ROOT/sync-claude-plugin-registry/claude-home"
  local source_root="$TMP_ROOT/sync-claude-plugin-registry/source"
  local state_home="$TMP_ROOT/sync-claude-plugin-registry/state"
  local materialized_home="$state_home/plugin-marketplaces/claude-kit"
  local stub_bin="$TMP_ROOT/sync-claude-plugin-registry/bin"
  local stub_log="$TMP_ROOT/sync-claude-plugin-registry/claude.log"

  rm -rf "$TMP_ROOT/sync-claude-plugin-registry"
  mkdir -p "$claude_home" "$source_root/targets/claude/.claude-plugin" \
    "$source_root/targets/claude/plugins/meta/.claude-plugin" \
    "$source_root/targets/claude/plugins/evidence/.claude-plugin" \
    "$source_root/build/claude/plugins/meta/skills/demo-symlink" \
    "$source_root/build/claude/plugins/evidence/skills/demo" \
    "$stub_bin"
  cat >"$source_root/targets/claude/.claude-plugin/marketplace.json" <<'JSON'
{
  "name": "claude-kit",
  "plugins": [
    {
      "name": "meta",
      "version": "0.1.0",
      "source": "./plugins/meta"
    },
    {
      "name": "evidence",
      "version": "0.1.0",
      "source": "./plugins/evidence"
    }
  ]
}
JSON
  cat >"$source_root/targets/claude/plugins/meta/.claude-plugin/plugin.json" <<'JSON'
{"name":"meta","version":"0.1.0","description":"meta fixture"}
JSON
  cat >"$source_root/targets/claude/plugins/evidence/.claude-plugin/plugin.json" <<'JSON'
{"name":"evidence","version":"0.1.0","description":"evidence fixture"}
JSON
  printf '# Demo symlink skill\n' >"$source_root/meta-skill.md"
  ln -s "$source_root/meta-skill.md" "$source_root/build/claude/plugins/meta/skills/demo-symlink/SKILL.md"
  printf '# Demo evidence skill\n' >"$source_root/build/claude/plugins/evidence/skills/demo/SKILL.md"
  cat >"$stub_bin/claude" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$CLAUDE_STUB_LOG"
case "$*" in
  "plugin marketplace list --json")
    printf '[{"name":"claude-kit","source":"directory","path":"/old-live-home"}]\n'
    ;;
  "plugins list --json")
    printf '[{"id":"meta@claude-kit","scope":"user","enabled":true}]\n'
    ;;
esac
SH
  chmod +x "$stub_bin/claude"

  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    APPLY=1
    SOURCE_ROOT="$source_root"
    PATH="$stub_bin:$PATH" CLAUDE_STUB_LOG="$stub_log" \
      sync_claude_plugin_registry "$claude_home" "$state_home"
  ) >"$out" 2>&1

  grep -q "materializing Claude plugin marketplace" "$out"
  grep -q "syncing Claude plugin registry marketplace=claude-kit source=$materialized_home" "$out"
  grep -q "plugin marketplace remove claude-kit --scope user" "$stub_log"
  grep -q "plugin marketplace add $materialized_home --scope user" "$stub_log"
  grep -q "plugin uninstall meta@claude-kit --scope user --keep-data" "$stub_log"
  grep -q "plugin install meta@claude-kit --scope user" "$stub_log"
  grep -q "plugin install evidence@claude-kit --scope user" "$stub_log"
  test -f "$materialized_home/plugins/meta/skills/demo-symlink/SKILL.md"
  test ! -L "$materialized_home/plugins/meta/skills/demo-symlink/SKILL.md"
  test -f "$materialized_home/plugins/meta/.claude-plugin/plugin.json"
  test -f "$materialized_home/.claude-plugin/marketplace.json"
}

run_sync_runtime_surfaces_codex_marketplace_shape_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.codex-marketplace-shape.txt"
  local marketplace="$REPO_ROOT/targets/codex/.agents/plugins/marketplace.json"

  python3 - "$marketplace" >"$out" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

plugins = data.get("plugins")
if not isinstance(plugins, list) or not plugins:
    raise SystemExit(f"Codex marketplace manifest plugins must be a non-empty list: {path}")

for entry in plugins:
    if not isinstance(entry, dict):
        raise SystemExit(f"Codex marketplace plugin entry must be an object: {path}")
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"Codex marketplace plugin entry missing non-empty name: {path}")

    source = entry.get("source")
    if not isinstance(source, dict):
        raise SystemExit(f"Codex marketplace plugin {name} source must be an object")
    if source.get("source") != "local":
        raise SystemExit(f"Codex marketplace plugin {name} source.source must be local")
    if source.get("path") != f"./plugins/{name}":
        raise SystemExit(f"Codex marketplace plugin {name} source.path must be ./plugins/{name}")

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        raise SystemExit(f"Codex marketplace plugin {name} policy must be an object")
    if policy.get("installation") != "AVAILABLE":
        raise SystemExit(f"Codex marketplace plugin {name} policy.installation must be AVAILABLE")
    if policy.get("authentication") != "ON_INSTALL":
        raise SystemExit(f"Codex marketplace plugin {name} policy.authentication must be ON_INSTALL")
    if not isinstance(entry.get("category"), str) or not entry["category"]:
        raise SystemExit(f"Codex marketplace plugin {name} category must be a non-empty string")

print(f"validated {len(plugins)} Codex marketplace plugin entries")
PY
}

run_sync_runtime_surfaces_codex_plugin_registry_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.codex-plugin-registry.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
  local codex_home="$TMP_ROOT/sync-codex-plugin-registry/codex-home"
  local source_root="$TMP_ROOT/sync-codex-plugin-registry/source"
  local state_home="$TMP_ROOT/sync-codex-plugin-registry/state"
  local materialized_home="$state_home/plugin-marketplaces/codex-kit"
  local stub_bin="$TMP_ROOT/sync-codex-plugin-registry/bin"
  local stub_log="$TMP_ROOT/sync-codex-plugin-registry/codex.log"

  rm -rf "$TMP_ROOT/sync-codex-plugin-registry"
  mkdir -p "$codex_home" "$source_root/targets/codex/.agents/plugins" \
    "$source_root/targets/codex/plugins/meta/.codex-plugin" \
    "$source_root/targets/codex/plugins/evidence/.codex-plugin" \
    "$source_root/build/codex/plugins/meta/skills/demo-symlink" \
    "$source_root/build/codex/plugins/evidence/skills/demo" \
    "$stub_bin"
  cat >"$source_root/targets/codex/.agents/plugins/marketplace.json" <<'JSON'
{
  "name": "codex-kit",
  "plugins": [
    {
      "name": "meta",
      "version": "0.1.0",
      "source": { "source": "local", "path": "./plugins/meta" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    },
    {
      "name": "evidence",
      "version": "0.1.0",
      "source": { "source": "local", "path": "./plugins/evidence" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
JSON
  cat >"$source_root/targets/codex/plugins/meta/.codex-plugin/plugin.json" <<'JSON'
{"name":"meta","version":"0.1.0","description":"meta fixture","skills":[{"id":"demo-symlink","source":"core/skills/meta/demo-symlink"}]}
JSON
  cat >"$source_root/targets/codex/plugins/evidence/.codex-plugin/plugin.json" <<'JSON'
{"name":"evidence","version":"0.1.0","description":"evidence fixture","skills":[{"id":"demo","source":"core/skills/evidence/demo"}]}
JSON
  printf '# Demo symlink skill\n' >"$source_root/codex-skill.md"
  ln -s "$source_root/codex-skill.md" "$source_root/build/codex/plugins/meta/skills/demo-symlink/SKILL.md"
  printf '# Demo evidence skill\n' >"$source_root/build/codex/plugins/evidence/skills/demo/SKILL.md"
  cat >"$stub_bin/codex" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$CODEX_STUB_LOG"
case "$*" in
  "plugin list --json")
    printf '{"installed":[{"pluginId":"meta@codex-kit"},{"pluginId":"legacy@codex-kit"},{"pluginId":"outside@other-kit"}],"available":[]}\n'
    ;;
  "plugin marketplace list --json")
    printf '{"marketplaces":[{"name":"codex-kit","root":"/old-state-home"}]}\n'
    ;;
esac
SH
  chmod +x "$stub_bin/codex"

  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    APPLY=1
    SOURCE_ROOT="$source_root"
    PATH="$stub_bin:$PATH" CODEX_STUB_LOG="$stub_log" \
      sync_codex_plugin_registry "$codex_home" "$state_home"
  ) >"$out" 2>&1

  grep -q "materializing Codex plugin marketplace" "$out"
  grep -q "syncing Codex plugin registry marketplace=codex-kit source=$materialized_home" "$out"
  grep -q "plugin marketplace remove codex-kit" "$stub_log"
  grep -q "plugin marketplace add $materialized_home" "$stub_log"
  grep -q "plugin remove meta@codex-kit" "$stub_log"
  grep -q "plugin remove legacy@codex-kit" "$stub_log"
  grep -q "plugin add meta@codex-kit" "$stub_log"
  grep -q "plugin add evidence@codex-kit" "$stub_log"
  # The refresh removes installed codex-kit entries, including stale ones, but
  # must not remove plugins from other marketplaces or plugins that are not
  # installed.
  if grep -q "plugin remove evidence@codex-kit" "$stub_log"; then
    echo "refresh removed evidence@codex-kit which was not installed" >&2
    exit 1
  fi
  if grep -q "plugin remove outside@other-kit" "$stub_log"; then
    echo "refresh removed an unrelated marketplace plugin" >&2
    exit 1
  fi
  test -f "$materialized_home/plugins/meta/skills/demo-symlink/SKILL.md"
  test ! -L "$materialized_home/plugins/meta/skills/demo-symlink/SKILL.md"
  test -f "$materialized_home/plugins/meta/.codex-plugin/plugin.json"
  test -f "$materialized_home/.agents/plugins/marketplace.json"
}

run_sync_runtime_surfaces_codex_plugin_registry_missing_cli_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.codex-plugin-registry-missing-cli.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
  local codex_home="$TMP_ROOT/sync-codex-plugin-missing-cli/codex-home"
  local source_root="$TMP_ROOT/sync-codex-plugin-missing-cli/source"
  local state_home="$TMP_ROOT/sync-codex-plugin-missing-cli/state"
  local status

  rm -rf "$TMP_ROOT/sync-codex-plugin-missing-cli"
  mkdir -p "$codex_home" "$state_home" "$source_root/targets/codex/.agents/plugins"
  cat >"$source_root/targets/codex/.agents/plugins/marketplace.json" <<'JSON'
{"name":"codex-kit","plugins":[]}
JSON

  set +e
  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    APPLY=1
    SOURCE_ROOT="$source_root"
    PATH="/usr/bin:/bin" \
      sync_codex_plugin_registry "$codex_home" "$state_home"
  ) >"$out" 2>&1
  status=$?
  set -e

  [ "$status" -ne 0 ]
  grep -q "codex plugin registry requires Codex CLI >= 0.141.0 on PATH" "$out"
  ! grep -q "codex plugin registry skipped" "$out"
}

run_sync_runtime_surfaces_codex_plugin_registry_planned_probe() {
  local out="$META_ARTIFACTS_DIR/sync-runtime-surfaces.codex-plugin-registry-planned.txt"
  local script="$REPO_ROOT/scripts/sync-runtime-surfaces.sh"
  local codex_home="$TMP_ROOT/sync-codex-plugin-planned/codex-home"
  local source_root="$TMP_ROOT/sync-codex-plugin-planned/source"
  local state_home="$TMP_ROOT/sync-codex-plugin-planned/state"
  local materialized_home="$state_home/plugin-marketplaces/codex-kit"
  local stub_bin="$TMP_ROOT/sync-codex-plugin-planned/bin"
  local stub_log="$TMP_ROOT/sync-codex-plugin-planned/codex.log"

  rm -rf "$TMP_ROOT/sync-codex-plugin-planned"
  mkdir -p "$codex_home" "$source_root/targets/codex/.agents/plugins" "$stub_bin"
  cat >"$source_root/targets/codex/.agents/plugins/marketplace.json" <<'JSON'
{
  "name": "codex-kit",
  "plugins": [
    {
      "name": "meta",
      "version": "0.1.0",
      "source": { "source": "local", "path": "./plugins/meta" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
JSON
  cat >"$stub_bin/codex" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$CODEX_STUB_LOG"
SH
  chmod +x "$stub_bin/codex"
  : >"$stub_log"

  # Dry-run (APPLY=0): the activation commands are printed as a plan, but
  # nothing is executed and nothing is materialized live. Status is `planned`.
  # shellcheck disable=SC1090,SC2034
  (
    SYNC_RUNTIME_SURFACES_LIB=1 . "$script"
    APPLY=0
    SOURCE_ROOT="$source_root"
    PATH="$stub_bin:$PATH" CODEX_STUB_LOG="$stub_log" \
      sync_codex_plugin_registry "$codex_home" "$state_home"
  ) >"$out" 2>&1

  grep -q "codex plugin marketplace materialize dry-run" "$out"
  grep -q "+ codex plugin marketplace add $materialized_home" "$out"
  grep -q "+ codex plugin add meta@codex-kit" "$out"
  grep -q "codex plugin registry planned: marketplace=codex-kit" "$out"
  # No live invocation and no materialized tree in dry-run.
  if [ -s "$stub_log" ]; then
    echo "dry-run unexpectedly invoked the codex binary" >&2
    exit 1
  fi
  test ! -e "$materialized_home"
}

run_project_local_shim_probe() {
  local name="$1"
  local script="$REPO_ROOT/tests/projects/project-local-smoke/.agents/scripts/${name}.sh"
  local out_dir="$META_ARTIFACTS_DIR/project-local-shims"
  local stdout="$out_dir/${name}.stdout"

  if [ ! -x "$script" ]; then
    echo "runtime-smoke meta: project-local shim is not executable: $script" >&2
    return 1
  fi

  mkdir -p "$out_dir"
  (
    cd "$REPO_ROOT/tests/projects/project-local-smoke"
    PROJECT_LOCAL_SMOKE_OUT="$out_dir" "$script" --runtime-smoke "$name"
  ) >"$stdout" 2>&1
  grep -q "project-local-smoke:${name}:called" "$stdout"
  test -f "$out_dir/${name}.invoked"
}

run_setup_project_probe() {
  local helper="$REPO_ROOT/core/skills/meta/setup-project/scripts/setup-project.sh"
  local out_dir="$META_ARTIFACTS_DIR/setup-project"
  local unadopted="$TMP_ROOT/workspaces/setup-project-unadopted"
  local partial="$TMP_ROOT/workspaces/setup-project-partial"
  local apply_root="$TMP_ROOT/workspaces/setup-project-apply"
  local status

  test -x "$helper"
  mkdir -p "$out_dir"

  mkdir -p "$unadopted"
  git -C "$unadopted" init -q
  "$helper" --repo "$unadopted" --dry-run >"$out_dir/unadopted.txt" 2>&1
  grep -q "setup-project: adoption=unadopted" "$out_dir/unadopted.txt"
  test ! -e "$unadopted/.agents"

  mkdir -p "$partial/.agents/scripts"
  git -C "$partial" init -q
  set +e
  "$helper" --repo "$partial" --dry-run >"$out_dir/partial.txt" 2>&1
  status=$?
  set -e
  [ "$status" -ne 0 ]
  grep -q "setup-project: adoption=partial" "$out_dir/partial.txt"
  grep -q "setup-project: block adopted repo missing executable .agents/scripts/pre-pr.sh" "$out_dir/partial.txt"

  mkdir -p "$apply_root/scripts/ci"
  git -C "$apply_root" init -q
  cat >"$apply_root/scripts/ci/all.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'setup-project fixture validation:%s\n' "$*"
: > setup-project-validation.invoked
SH
  chmod +x "$apply_root/scripts/ci/all.sh"
  "$helper" \
    --repo "$apply_root" \
    --apply \
    --pre-pr-command "bash scripts/ci/all.sh" >"$out_dir/apply.txt" 2>&1
  grep -q "setup-project: wrote .agents/scripts/pre-pr.sh" "$out_dir/apply.txt"
  test -x "$apply_root/.agents/scripts/pre-pr.sh"
  (
    cd "$apply_root"
    ./.agents/scripts/pre-pr.sh --fixture
  ) >"$out_dir/apply-pre-pr.txt" 2>&1
  grep -q "setup-project fixture validation:--fixture" "$out_dir/apply-pre-pr.txt"
  test -f "$apply_root/setup-project-validation.invoked"

  # A compound --pre-pr-command (&&) must run every stage, not just the first,
  # and a failing first stage must abort rather than report a green gate.
  local compound="$TMP_ROOT/workspaces/setup-project-compound"
  mkdir -p "$compound"
  git -C "$compound" init -q
  "$helper" \
    --repo "$compound" \
    --apply \
    --pre-pr-command "echo stage-one >stage-one.ran && echo stage-two >stage-two.ran" \
    >"$out_dir/compound-apply.txt" 2>&1
  grep -q "setup-project: wrote .agents/scripts/pre-pr.sh" "$out_dir/compound-apply.txt"
  if grep -Eq '^exec ' "$compound/.agents/scripts/pre-pr.sh"; then
    echo "meta.setup-project: dispatcher exec-binds the first command of a compound gate" >&2
    return 1
  fi
  (
    cd "$compound"
    ./.agents/scripts/pre-pr.sh
  ) >"$out_dir/compound-run.txt" 2>&1
  test -f "$compound/stage-one.ran"
  test -f "$compound/stage-two.ran"

  rm -rf "$compound"
  mkdir -p "$compound"
  git -C "$compound" init -q
  "$helper" \
    --repo "$compound" \
    --apply \
    --pre-pr-command "false && echo reached >tail.ran" \
    >"$out_dir/compound-fail-apply.txt" 2>&1
  set +e
  (
    cd "$compound"
    ./.agents/scripts/pre-pr.sh
  ) >"$out_dir/compound-fail-run.txt" 2>&1
  status=$?
  set -e
  [ "$status" -ne 0 ]
  test ! -e "$compound/tail.ran"
}

run_plan_archive_migrate_probe() {
  local out="$META_ARTIFACTS_DIR/plan-archive-migrate.dry-run.json"
  require_meta_bin plan-archive || return 1
  local root="$META_ARTIFACTS_DIR/plan-archive-migrate"
  local src="$root/source"
  local archive="$root/archive"
  rm -rf "$root"
  mkdir -p "$src" "$archive/config"
  (
    cd "$src"
    git init -q -b main
    git remote add origin git@github.com:graysurf/agent-runtime-kit.git
    mkdir -p docs/plans/2026-05-27-smoke-plan
    printf '# smoke plan\n' >docs/plans/2026-05-27-smoke-plan/PLAN.md
    git add docs/plans
    git -c user.name=smoke -c user.email=smoke@example.com commit -q -m "seed plan"
  )
  printf 'version: 1\nhosts:\n  github.com:\n    class: personal\n    primary_identity: graysurf\n' \
    >"$archive/config/hosts.yaml"
  plan-archive migrate \
    --plan docs/plans/2026-05-27-smoke-plan \
    --source-repo "$src" \
    --archive "$archive" \
    --hosts "$archive/config/hosts.yaml" \
    --issue https://github.com/graysurf/agent-runtime-kit/issues/126 \
    --format json >"$out" 2>&1
  grep -q '"schema_version":"cli.plan-archive.migrate.v1"' "$out"
  grep -q 'plans/github.com/graysurf/agent-runtime-kit/2026-05-27-smoke-plan' "$out"
}

run_plan_archive_query_probe() {
  local out="$META_ARTIFACTS_DIR/plan-archive-query.single.json"
  require_meta_bin plan-archive || return 1
  local archive="$META_ARTIFACTS_DIR/plan-archive-query/archive"
  local dir="$archive/_index/github.com/graysurf/agent-runtime-kit/issues/126"
  rm -rf "$archive"
  mkdir -p "$dir"
  printf '{"title":"smoke"}' >"$dir/20260527T010000Z.json"
  plan-archive query \
    --ref https://github.com/graysurf/agent-runtime-kit/issues/126 \
    --archive "$archive" \
    --format json >"$out" 2>&1
  grep -q '"schema_version":"cli.plan-archive.query.v1"' "$out"
  grep -q '"fetched_at":"2026-05-27T01:00:00Z"' "$out"
}

run_plan_archive_discover_probe() {
  local out="$META_ARTIFACTS_DIR/plan-archive-discover.scan.json"
  require_meta_bin plan-archive || return 1
  local root="$META_ARTIFACTS_DIR/plan-archive-discover"
  local src="$root/source"
  local archive="$root/archive"
  rm -rf "$root"
  mkdir -p "$src" "$archive/config"
  (
    cd "$src"
    git init -q -b main
    git remote add origin git@github.com:graysurf/agent-runtime-kit.git
    mkdir -p docs/plans/2026-05-27-discover-smoke
    printf '# discover smoke plan\n' >docs/plans/2026-05-27-discover-smoke/PLAN.md
    git add docs/plans
    git -c user.name=smoke -c user.email=smoke@example.com commit -q -m "seed plan"
  )
  printf 'version: 1\nhosts:\n  github.com:\n    class: personal\n    primary_identity: graysurf\n' \
    >"$archive/config/hosts.yaml"
  plan-archive discover \
    --source-repo "$src" \
    --archive "$archive" \
    --hosts "$archive/config/hosts.yaml" \
    --format json >"$out" 2>&1
  grep -q '"schema_version":"cli.plan-archive.discover.v1"' "$out"
  grep -q '"status":"blocked"' "$out"
  grep -q '"code":"no-provider-refs"' "$out"
}

run_evidence_migrate_probe() {
  local out="$META_ARTIFACTS_DIR/evidence-migrate.dry-run.json"
  require_meta_bin evidence || return 1
  local root="$META_ARTIFACTS_DIR/evidence-migrate"
  local src="$root/out/projects"
  local archive="$root/archive"
  local good="$src/graysurf__agent-runtime-kit/20260614-100000-skill-usage"
  local bad="$src/graysurf__agent-runtime-kit/20260614-110000-skill-usage"
  rm -rf "$root"
  mkdir -p "$good" "$bad" "$archive/config" "$archive/evidence"
  # One valid record: a single-host archive resolves the slug-only dir to the
  # sole host, so it is eligible for migration.
  printf '%s' '{"schema":"skill-usage.record.v1","producer":{"tool":"skill-usage","nils_cli_version":"1.6.0"},"skill":"deliver-pr","started_at":"2026-06-14T10:00:00Z","ended_at":"2026-06-14T10:30:00Z","cwd":"/Users/tester/Project/kit","trigger":"user_explicit","intent":"deliver a PR","inputs":{"user_request_summary":"x","referenced_files":[],"external_sources":[]},"outcome":{"status":"pass","summary":"done"},"artifacts":[],"linked_records":[],"validation":[],"failures":[]}' \
    >"$good/skill-usage.record.json"
  # One malformed record the dry-run must skip and report (the #853 behavior),
  # not abort the batch.
  printf '%s' '{ "schema": "skill-usage.record.v1" TRAILING GARBAGE' \
    >"$bad/skill-usage.record.json"
  printf 'version: 1\nhosts:\n  github.com:\n    class: personal\n    primary_identity: graysurf\n' \
    >"$archive/config/hosts.yaml"
  evidence migrate \
    --source-out "$src" \
    --archive "$archive" \
    --hosts "$archive/config/hosts.yaml" \
    --format json >"$out" 2>&1
  grep -q '"schema_version":"cli.evidence.migrate.v1"' "$out"
  grep -q 'evidence/github.com/graysurf/agent-runtime-kit' "$out"
  grep -q 'parse failed' "$out"
}

run_evidence_prune_source_probe() {
  local out="$META_ARTIFACTS_DIR/evidence-prune-source.dry-run.json"
  require_meta_bin evidence || return 1
  require_meta_bin python3 || return 1
  local root="$META_ARTIFACTS_DIR/evidence-prune-source"
  local src="$root/out/projects"
  local archive="$root/archive"
  local archived="$src/graysurf__agent-runtime-kit/20260620-010000-skill-usage"
  local retained="$src/graysurf__agent-runtime-kit/20260620-020000-skill-usage"
  local archived_body archived_digest
  rm -rf "$root"
  mkdir -p "$archived" "$retained" "$archive"
  archived_body='{"schema":"skill-usage.record.v1","producer":{"tool":"skill-usage","nils_cli_version":"1.12.0"},"skill":"evidence-migrate","started_at":"2026-06-20T01:00:00Z","ended_at":"2026-06-20T01:05:00Z","cwd":"/Users/tester/Project/kit","trigger":"user_explicit","intent":"archive evidence","inputs":{"user_request_summary":"x","referenced_files":[],"external_sources":[]},"outcome":{"status":"pass","summary":"done"},"artifacts":[],"linked_records":[],"validation":[],"failures":[]}'
  printf '%s' "$archived_body" >"$archived/skill-usage.record.json"
  printf '%s' '{"schema":"skill-usage.record.v1","producer":{"tool":"skill-usage","nils_cli_version":"1.12.0"},"skill":"code-review","started_at":"2026-06-20T02:00:00Z","ended_at":"2026-06-20T02:05:00Z","cwd":"/Users/tester/Project/kit","trigger":"user_explicit","intent":"review","inputs":{"user_request_summary":"x","referenced_files":[],"external_sources":[]},"outcome":{"status":"pass","summary":"done"},"artifacts":[],"linked_records":[],"validation":[],"failures":[]}' \
    >"$retained/skill-usage.record.json"
  archived_digest="sha256:$(printf '%s' "$archived_body" | python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())')"
  printf '{"schema_version":"evidence.catalog.v1","records":[{"source_digest":"%s"}]}\n' "$archived_digest" \
    >"$archive/catalog.json"
  evidence prune-source \
    --source-out "$src" \
    --archive "$archive" \
    --archived-only \
    --format json >"$out" 2>&1
  grep -q '"schema_version":"cli.evidence.prune-source.v1"' "$out"
  grep -q '"prunable":1' "$out"
  grep -q '"kept":1' "$out"
  grep -q '"deleted":0' "$out"
  grep -q '"reason":"already archived"' "$out"
  grep -q '"reason":"not archived"' "$out"
  [ -d "$archived" ]
  [ -d "$retained" ]
}

run_nils_cli_bump_probe() {
  local drift="$META_ARTIFACTS_DIR/nils-cli-bump.drift.json"
  local aligned="$META_ARTIFACTS_DIR/nils-cli-bump.aligned.json"
  local pin_dir="$META_ARTIFACTS_DIR/nils-cli-bump"
  local host_tag status
  require_meta_bin agent-runtime || return 1
  mkdir -p "$pin_dir"

  # Drift path: an impossible pinned_tag must block (exit 2). Host-version
  # independent, so the probe stays deterministic across host bumps.
  printf 'schema_version: 1\nnils_cli:\n  pinned_tag: "v0.0.0"\n' >"$pin_dir/drift.yaml"
  set +e
  agent-runtime doctor --class version-alignment \
    --pin "$pin_dir/drift.yaml" --format json >"$drift" 2>&1
  status=$?
  set -e
  [ "$status" -eq 2 ]
  grep -q '"schema_version": "agent-runtime-cli.doctor.v1"' "$drift"
  grep -q '"check": "version-alignment.host"' "$drift"
  grep -q 'drifted from pinned v0.0.0' "$drift"

  # Aligned path: pinning to the host's own tag must pass (block=0, exit 0).
  host_tag="$(agent-runtime --version | awk 'NR==1 {print $2}')"
  case "$host_tag" in v*) : ;; *) host_tag="v$host_tag" ;; esac
  printf 'schema_version: 1\nnils_cli:\n  pinned_tag: "%s"\n' "$host_tag" >"$pin_dir/aligned.yaml"
  agent-runtime doctor --class version-alignment \
    --pin "$pin_dir/aligned.yaml" --format json >"$aligned" 2>&1
  grep -q '"block": 0' "$aligned"
}

run_worktree_triage_probe() {
  local out="$META_ARTIFACTS_DIR/worktree-triage.scan.json"
  local all_out="$META_ARTIFACTS_DIR/worktree-triage.all-managed.json"
  local root="$META_ARTIFACTS_DIR/worktree-triage"
  local managed="$root/managed"
  local repo="$root/repo"
  local repo2="$root/repo2"
  local helper="$REPO_ROOT/core/skills/meta/worktree-triage/bin/worktree_triage.py"
  require_meta_bin python3 || return 1
  rm -rf "$root"
  mkdir -p "$repo"
  (
    cd "$repo"
    git init -q -b main
    git config user.email smoke@example.com
    git config user.name smoke
    printf 'base\n' >f.txt
    git add f.txt
    git commit -q -m "base"
    git update-ref refs/remotes/origin/main HEAD
    # safe-merged: branch worktree at base, nothing ahead.
    git worktree add -q wt-merged -b merged-branch main
    # safe-superseded: super-branch adds g.txt; the base independently gains the
    # same change as a DIFFERENT commit (the real "landed via another PR"
    # case). The branch is ahead by SHA but patch-equivalent to the base, so
    # git cherry reports its commit as already-applied.
    git worktree add -q wt-super -b super-branch main
    (cd wt-super && printf 'super\n' >g.txt && git add g.txt && git commit -q -m "add g")
    printf 'super\n' >g.txt
    git add g.txt
    git commit -q -m "add g (base route)"
    git update-ref refs/remotes/origin/main HEAD
    # rescue-candidate: a unique commit not represented on the base.
    git worktree add -q wt-real -b real-work main
    (cd wt-real && printf 'unique\n' >h.txt && git add h.txt && git commit -q -m "unique work")
  )
  python3 "$helper" --repo "$repo" --base origin/main --format json >"$out" 2>&1
  python3 - "$out" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
assert data["schema_version"] == "worktree-triage.scan.v1", data
by = {w.get("branch"): w["disposition"] for w in data["worktrees"]}
assert by.get("merged-branch") == "safe-merged", by
assert by.get("super-branch") == "safe-superseded", by
assert by.get("real-work") == "rescue-candidate", by
PY

  mkdir -p "$managed/repo-one" "$managed/repo-two" "$repo2"
  (
    cd "$repo"
    git worktree add -q "$managed/repo-one/repo-one-safe" -b repo-one-safe main
    git worktree add -q "$root/unmanaged-safe" -b unmanaged-safe main
  )
  (
    cd "$repo2"
    git init -q -b main
    git config user.email smoke@example.com
    git config user.name smoke
    printf 'repo2\n' >r.txt
    git add r.txt
    git commit -q -m "base"
    git update-ref refs/remotes/origin/main HEAD
    git worktree add -q "$managed/repo-two/repo-two-safe" -b repo-two-safe main
  )
  python3 "$helper" --all-managed --worktree-root "$managed" --base origin/main --format json >"$all_out" 2>&1
  python3 - "$all_out" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
assert data["schema_version"] == "worktree-triage.scan.v1", data
assert data["scope"] == "all-managed", data
assert len(data["repos"]) == 2, data["repos"]
by = {w.get("branch"): w["disposition"] for w in data["worktrees"]}
assert by.get("repo-one-safe") == "safe-merged", by
assert by.get("repo-two-safe") == "safe-merged", by
for branch in ("merged-branch", "super-branch", "real-work", "unmanaged-safe"):
    assert branch not in by, by
PY
}

run_meta_outcome_routing_probe() {
  local files_policy="$REPO_ROOT/core/policies/files-hooks-validation.md"
  local git_policy="$REPO_ROOT/core/policies/git-delivery.md"
  local heuristic_policy="$REPO_ROOT/core/policies/heuristic-system/HEURISTIC_SYSTEM.md"
  local evidence_policy="$REPO_ROOT/core/policies/evidence-archive/EVIDENCE_ARCHIVE.md"

  grep -Fq '## Parent Workflow Routing' "$files_policy" || {
    echo "runtime-smoke meta: files policy missing parent routing" >&2
    return 1
  }
  grep -Fq '`agent-docs` preflight and `agent-out` allocation are parent workflow' "$files_policy" &&
    grep -Fq 'responsibilities, not user-selected outcomes' "$files_policy" || {
    echo "runtime-smoke meta: files policy missing parent-owned preflight/allocation" >&2
    return 1
  }
  grep -Fq '## Parent Workflow Routing' "$git_policy" || {
    echo "runtime-smoke meta: git policy missing parent routing" >&2
    return 1
  }
  grep -Fq '`.agents/scripts/pre-pr.sh`' "$git_policy" || {
    echo "runtime-smoke meta: git policy missing pre-PR dispatcher routing" >&2
    return 1
  }
  grep -Fq '## Session Closeout Procedure' "$heuristic_policy" || {
    echo "runtime-smoke meta: heuristic policy missing session closeout procedure" >&2
    return 1
  }
  grep -Fq 'invoke `heuristic-inbox` directly' "$heuristic_policy" || {
    echo "runtime-smoke meta: heuristic policy missing direct inbox routing" >&2
    return 1
  }
  grep -Fq 'session closeout procedure' "$evidence_policy" &&
    grep -Fq 'invokes `evidence migrate`' "$evidence_policy" &&
    grep -Fq '`evidence prune-source` directly' "$evidence_policy" || {
    echo "runtime-smoke meta: evidence policy missing direct closeout routing" >&2
    return 1
  }

  rendered_contract_assert_skill meta heuristic-session-closeout
  rendered_contract_assert_skill meta semantic-commit
  rendered_contract_assert_skill reporting project-retro
}

failures=0
record_case "meta.agent-docs" "project-dev docs preflight passed from fixture workspace" run_agent_docs_probe
record_case "meta.home-prompt-render" "home prompt render isolates Codex-only delegation and product sentinel text" run_home_prompt_render_probe
record_case "meta.agent-out" "agent-out allocated a temp project path and applied a reviewed cleanup plan" run_agent_out_probe
record_case "meta.agent-scope-lock" "scope lock create and validate passed in temp git workspace" run_agent_scope_lock_probe
record_case "meta.bootstrap" "project-local bootstrap shim executed fixture script" run_project_local_shim_probe bootstrap
record_case "meta.deploy" "project-local deploy shim executed fixture script" run_project_local_shim_probe deploy
record_case "meta.heuristic-inbox" "heuristic inbox shared-root list and strict verification passed" run_heuristic_inbox_probe
record_case "meta.heuristic-session-closeout" "session closeout contract preserves retained heuristic records on main" run_heuristic_session_closeout_probe
record_case "meta.create-skill" "skill lifecycle create surface and governance fixture passed" run_create_skill_probe
record_case "meta.create-project-skill" "project skill lifecycle create surface and fixture passed" run_create_project_skill_probe
record_case "meta.remove-skill" "skill lifecycle removal surface and governance fixture passed" run_remove_skill_probe
record_case "meta.remove-project-skill" "project skill lifecycle removal surface and fixture passed" run_remove_project_skill_probe
record_case "meta.pre-pr" "project-local pre-pr shim executed fixture script" run_project_local_shim_probe pre-pr
record_case "meta.release" "project-local release shim executed fixture script" run_project_local_shim_probe release
record_case "meta.repo-retro" "repo-retro JSON report probe passed against temp git workspace" run_repo_retro_probe
record_case "meta.semantic-commit" "semantic-commit dry-run validated staged temp change without commit" run_semantic_commit_probe
record_case "meta.setup-project" "setup-project dry-run/apply adoption probes passed" run_setup_project_probe
record_case "meta.plan-archive-migrate" "plan-archive migrate dry-run JSON probe resolved archive target" run_plan_archive_migrate_probe
record_case "meta.plan-archive-query" "plan-archive query single-ref JSON probe surfaced fetched_at" run_plan_archive_query_probe
record_case "meta.plan-archive-discover" "plan-archive discover JSON probe classified blocked candidate" run_plan_archive_discover_probe
record_case "meta.evidence-migrate" "evidence migrate dry-run JSON probe resolved an archive target and reported a blocked malformed record" run_evidence_migrate_probe
record_case "meta.evidence-prune-source" "evidence prune-source dry-run JSON probe retained unarchived source and marked archived source prunable" run_evidence_prune_source_probe
record_case "meta.outcome-routing" "meta primitives route through parent policy, delivery, and session-closeout procedures" run_meta_outcome_routing_probe
record_case "meta.nils-cli-bump" "version-alignment doctor probe blocked v0.0.0 drift and passed host-aligned pin" run_nils_cli_bump_probe
record_case "meta.worktree-triage" "worktree triage scan classified safe-merged, safe-superseded, and rescue-candidate worktrees" run_worktree_triage_probe
record_case "meta.setup" "setup dry-run renders codex and claude before install and delegates Claude plugin activation" run_setup_render_before_install_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces dry-run planned codex refresh without mutation" run_sync_runtime_surfaces_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces apply rewires managed home prompt symlinks" run_sync_runtime_surfaces_home_prompt_apply_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces no-prune flag reports skipped prune" run_sync_runtime_surfaces_no_prune_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces apply refuses linked git worktree source roots" run_sync_runtime_surfaces_worktree_guard_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces prune fixture removes stale owned surfaces only" run_sync_runtime_surfaces_prune_fixture_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces removes legacy Hermes runtime-kit local skill symlinks only" run_sync_runtime_surfaces_hermes_legacy_cleanup_probe
record_case "meta.sync-runtime-surfaces" "prune-stale skips retired recursive-file managed skill directory (upstream gap characterization)" run_sync_runtime_surfaces_prune_recursive_stale_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces reports prune=review-needed when prune-stale leaves stale candidates" run_sync_runtime_surfaces_prune_review_reporting_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces uses neutral non-destructive wording for hermes prune-skipped paths" run_sync_runtime_surfaces_prune_review_hermes_wording_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces merges Claude settings hooks without dropping custom hooks" run_sync_runtime_surfaces_claude_settings_hooks_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces materializes and installs Claude plugins for skill visibility" run_sync_runtime_surfaces_claude_plugin_registry_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces ships Codex marketplace entries with required policy metadata" run_sync_runtime_surfaces_codex_marketplace_shape_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces materializes and installs Codex plugins by default" run_sync_runtime_surfaces_codex_plugin_registry_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces fails Codex plugin activation when the Codex CLI is unavailable" run_sync_runtime_surfaces_codex_plugin_registry_missing_cli_probe
record_case "meta.sync-runtime-surfaces" "sync-runtime-surfaces prints a Codex activation plan without executing it under dry-run" run_sync_runtime_surfaces_codex_plugin_registry_planned_probe

exit "$failures"
