#!/usr/bin/env bash
# Deterministic probes for media skills.
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

MEDIA_ARTIFACTS_DIR="$ARTIFACTS_DIR/media"
MEDIA_WORKSPACE="$TMP_ROOT/workspaces/media-basic-repo"
SAMPLE_SVG="$SCRIPT_DIR/fixtures/sample.svg"
mkdir -p "$MEDIA_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$MEDIA_WORKSPACE"

require_media_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke media: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_image_processing_probe() {
  local out_json="$MEDIA_ARTIFACTS_DIR/image-processing.validate.json"
  local out_svg="$MEDIA_ARTIFACTS_DIR/image-processing.validated.svg"
  local out_stderr="$MEDIA_ARTIFACTS_DIR/image-processing.stderr.txt"
  require_media_bin image-processing || return 1
  test -s "$SAMPLE_SVG"
  (
    cd "$MEDIA_WORKSPACE"
    image-processing svg-validate \
      --in "$SAMPLE_SVG" \
      --out "$out_svg" \
      --json
  ) >"$out_json" 2>"$out_stderr"
  grep -q '"operation":"svg-validate"' "$out_json"
  grep -q '"status":"ok"' "$out_json"
  test -s "$out_svg"
}

run_screen_record_probe() {
  local out="$MEDIA_ARTIFACTS_DIR/screen-record.preflight.txt"
  local err="$MEDIA_ARTIFACTS_DIR/screen-record.preflight.stderr.txt"
  require_media_bin screen-record || return 1
  (
    cd "$MEDIA_WORKSPACE"
    screen-record --preflight
  ) >"$out" 2>"$err"
}

run_media_outcome_routing_probe() {
  local image_skill="$REPO_ROOT/core/skills/media/image-processing/SKILL.md.tera"
  local capture_skill="$REPO_ROOT/core/skills/media/screen-record/SKILL.md.tera"
  local skills_manifest="$REPO_ROOT/manifests/skills.yaml"

  grep -Fq '## Outcome Routing' "$image_skill"
  grep -Fq 'artifact allocation is' "$image_skill"
  grep -Fq 'internal bookkeeping' "$image_skill"
  grep -Fq '## Outcome Routing' "$capture_skill"
  grep -Fq 'evidence' "$capture_skill"
  grep -Fq 'metadata and diagnostics are internal bookkeeping' "$capture_skill"
  grep -Fq 'RUN_DIR="$(agent-out project --topic screen-record --repo "$PWD" --mkdir)"' "$capture_skill"
  awk '
    /RUN_DIR="\$\(agent-out project/ { allocation_line = NR }
    /--path "\$RUN_DIR\/window.png"/ { use_line = NR }
    END { exit !(allocation_line && allocation_line < use_line) }
  ' "$capture_skill"
  awk '
    /^  - id: media\.screen-record$/ { in_skill = 1 }
    in_skill && /^    required_clis:$/ { in_required = 1 }
    in_skill && in_required && /^      agent-out:/ { agent_out = 1 }
    in_skill && /^    state_out_mode:/ { exit !agent_out }
  ' "$skills_manifest"

  rendered_contract_assert_skill media image-processing
  rendered_contract_assert_skill media screen-record
  rendered_contract_assert_all_contain media image-processing '## Outcome Routing'
  rendered_contract_assert_all_contain media screen-record '## Outcome Routing'
  rendered_contract_assert_all_contain media screen-record 'RUN_DIR="$(agent-out project --topic screen-record --repo "$PWD" --mkdir)"'
}

failures=0
record_case "media.image-processing" "image-processing validated committed SVG fixture in temp workspace" run_image_processing_probe

if run_screen_record_probe; then
  results_add "media.screen-record" "shared-cli" "pass" "1" "screen-record host preflight passed"
else
  results_add "media.screen-record" "shared-cli" "skip-host-capability" "0" "screen-record host preflight unavailable; see media artifacts"
fi
record_case "media.outcome-routing" "media outcomes allocate and retain artifacts without exposing bookkeeping choices" run_media_outcome_routing_probe

exit "$failures"
