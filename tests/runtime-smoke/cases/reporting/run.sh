#!/usr/bin/env bash
# Deterministic regression probes for reporting skills.
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

REPORTING_ARTIFACTS_DIR="$ARTIFACTS_DIR/reporting"
REPORTING_WORKSPACE="$TMP_ROOT/workspaces/reporting-basic-repo"
TOPIC_RADAR_SCRIPT="$REPO_ROOT/core/skills/reporting/topic-radar/scripts/topic-radar.sh"
mkdir -p "$REPORTING_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$REPORTING_WORKSPACE"

require_reporting_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke reporting: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_daily_brief_probe() {
  local out_json="$REPORTING_ARTIFACTS_DIR/daily-brief.topic-radar-sample.json"
  require_reporting_bin python3 || return 1
  test -x "$TOPIC_RADAR_SCRIPT"
  "$TOPIC_RADAR_SCRIPT" \
    --preset ai-news \
    --sample \
    --format json >"$out_json"
  grep -q '"ok": true' "$out_json"
  grep -q '"sample": true' "$out_json"
  grep -q '"brief": {' "$out_json"
  grep -q '"clusters": \[' "$out_json"
  grep -q '"preset": "ai-news"' "$out_json"
}

run_project_retro_probe() {
  local retro_workspace="$TMP_ROOT/workspaces/project-retro-repo"
  local out_json="$REPORTING_ARTIFACTS_DIR/project-retro.repo-retro.json"
  require_reporting_bin repo-retro || return 1
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$retro_workspace"
  git -C "$retro_workspace" init -q
  git -C "$retro_workspace" config user.email runtime-smoke@example.invalid
  git -C "$retro_workspace" config user.name "Runtime Smoke"
  git -C "$retro_workspace" add README.md
  git -C "$retro_workspace" commit -q -m "Initial fixture"
  repo-retro report \
    --repo "$retro_workspace" \
    --from 2026-05-01 \
    --to 2026-05-02 \
    --mode team \
    --format json >"$out_json"
  grep -q '"schema_version": "cli.repo-retro.report.v2"' "$out_json"
  grep -q '"ok": true' "$out_json"
}

run_topic_radar_probe() {
  local out_json="$REPORTING_ARTIFACTS_DIR/topic-radar.sample.json"
  local out_markdown="$REPORTING_ARTIFACTS_DIR/topic-radar.sample.md"
  require_reporting_bin python3 || return 1
  test -x "$TOPIC_RADAR_SCRIPT"
  "$TOPIC_RADAR_SCRIPT" \
    --preset radar \
    --sample \
    --format json >"$out_json"
  "$TOPIC_RADAR_SCRIPT" \
    --preset radar \
    --sample \
    --format markdown >"$out_markdown"
  grep -q '"ok": true' "$out_json"
  grep -q '"sample": true' "$out_json"
  grep -q '"sources": \[' "$out_json"
  grep -q '# AI/Tech Topic Radar' "$out_markdown"
  grep -q '## Top Signals' "$out_markdown"
}

run_topic_radar_security_probe() {
  require_reporting_bin python3 || return 1
  PYTHONDONTWRITEBYTECODE=1 python3 "$REPO_ROOT/tests/reporting/test_topic_radar_security.py"
}

run_reporting_outcome_routing_probe() {
  local daily="$REPO_ROOT/core/skills/reporting/daily-brief/SKILL.md.tera"
  local retro="$REPO_ROOT/core/skills/reporting/project-retro/SKILL.md.tera"

  grep -Fq '## Outcome Routing' "$daily"
  grep -Fq 'invokes `topic-radar` as its' "$daily"
  grep -Fq 'internal collection engine' "$daily"
  grep -Fq '## Outcome Routing' "$retro"
  grep -Fq 'canonical repository-retrospective outcome. Legacy' "$retro"
  grep -Fq '`meta.repo-retro` requests route here' "$retro"
  grep -Fq 'artifact allocation and CLI collection are internal bookkeeping' "$retro"

  rendered_contract_assert_skill reporting daily-brief
  rendered_contract_assert_skill reporting project-retro
  rendered_contract_assert_all_contain reporting daily-brief '## Outcome Routing'
  rendered_contract_assert_all_contain reporting project-retro '## Outcome Routing'
}

failures=0
record_case "reporting.daily-brief" "daily-brief backend topic-radar sample JSON exposes brief clusters" run_daily_brief_probe
record_case "reporting.project-retro" "project-retro repo-retro JSON report passed against temp git workspace" run_project_retro_probe
record_case "reporting.topic-radar" "topic-radar sample JSON and markdown probes passed without network" run_topic_radar_probe
record_case "reporting.topic-radar-security" "topic-radar rejects oversized bodies, unsafe XML, and cross-host redirects" run_topic_radar_security_probe
record_case "reporting.outcome-routing" "report outcomes select collection and artifact bookkeeping internally" run_reporting_outcome_routing_probe

exit "$failures"
