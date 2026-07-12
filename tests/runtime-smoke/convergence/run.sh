#!/usr/bin/env bash
# Portable historical-upgrade/read-back/rollback and routing-contract acceptance.

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/runtime-home.sh"

CONVERGENCE_ARTIFACTS_DIR="$ARTIFACTS_DIR/convergence"
mkdir -p "$CONVERGENCE_ARTIFACTS_DIR"

validate_dirty_source_rejected() {
  local dirty_source="$TMP_ROOT/dirty-source"
  local rejected_snapshot="$TMP_ROOT/rejected-snapshot"

  git clone -q --no-hardlinks "$PORTABLE_SOURCE_ROOT" "$dirty_source"
  printf 'operator private material\n' >"$dirty_source/operator-note.txt"
  if runtime_prepare_portable_source "$dirty_source" "$rejected_snapshot" \
    >"$CONVERGENCE_ARTIFACTS_DIR/dirty-source.stdout" \
    2>"$CONVERGENCE_ARTIFACTS_DIR/dirty-source.stderr"; then
    return 1
  fi
  test ! -e "$rejected_snapshot"
  grep -q 'portable source must be clean' \
    "$CONVERGENCE_ARTIFACTS_DIR/dirty-source.stderr"
}

validate_snapshot_ref_boundary() {
  local source="$TMP_ROOT/ref-boundary-source"
  local snapshot="$TMP_ROOT/ref-boundary-snapshot"
  local base_revision private_commit dangling_blob

  base_revision="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  runtime_prepare_portable_source "$REPO_ROOT" "$source" >/dev/null
  git -C "$source" config user.name 'Portable Acceptance'
  git -C "$source" config user.email 'portable-acceptance@example.invalid'
  git -C "$source" switch -q -c private-sentinel
  printf 'private branch sentinel\n' >"$source/private-sentinel.txt"
  git -C "$source" add private-sentinel.txt
  git -C "$source" commit -q -m 'test: private sentinel'
  private_commit="$(git -C "$source" rev-parse HEAD)"
  git -C "$source" -c advice.detachedHead=false checkout -q --detach "$base_revision"
  dangling_blob="$(printf 'dangling private sentinel\n' | git -C "$source" hash-object -w --stdin)"

  runtime_prepare_portable_source "$source" "$snapshot" >/dev/null
  if git -C "$snapshot" cat-file -e "$private_commit^{commit}" 2>/dev/null; then
    return 1
  fi
  if git -C "$snapshot" cat-file -e "$dangling_blob^{blob}" 2>/dev/null; then
    return 1
  fi
  test -z "$(git -C "$snapshot" for-each-ref --format='%(refname)' | grep private-sentinel || true)"
  test "$(git -C "$snapshot" rev-parse HEAD)" = "$base_revision"
}

validate_routing_contract() {
  local product="$1"
  local plans="$CONVERGENCE_ARTIFACTS_DIR/$product/routing-contract.json"

  mkdir -p "$(dirname "$plans")"
  python3 - \
    "$REPO_ROOT" \
    "$SCRIPT_DIR/product/routing-contract-cases.json" \
    "$SCRIPT_DIR/product/prompts" \
    "$product" \
    "$plans" <<'PY'
import hashlib
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
cases = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
prompt_root = pathlib.Path(sys.argv[3])
product = sys.argv[4]
output = pathlib.Path(sys.argv[5])

assert cases["schema"] == "agent-runtime-kit.routing-contract.v1"
active_text = (root / "manifests/skills.yaml").read_text(encoding="utf-8")
active_ids = set(re.findall(r"^  - id: ([a-z0-9.-]+)$", active_text, re.M))
retired = json.loads(
    (root / "manifests/retired-skill-ids.json").read_text(encoding="utf-8")
)["skills"]
intent_text = (root / "AGENT_DOCS.toml").read_text(encoding="utf-8")
plans = []

for case in cases["cases"]:
    prompt = (prompt_root / case["prompt"]).read_text(encoding="utf-8")
    lowered = prompt.lower()
    for skill_id in retired:
        leaf = skill_id.split(".", 1)[1]
        assert skill_id not in prompt, (case["id"], skill_id)
        assert leaf not in lowered, (case["id"], leaf)
    route = case["expected_route"]
    if route.startswith("intent:"):
        assert f'context = "{route.split(":", 1)[1]}"' in intent_text, route
    else:
        assert route in active_ids, route
    plans.append(
        {
            "case": case["id"],
            "product": product,
            "contract_route": route,
            "fixture_contract": True,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        }
    )

output.write_text(
    json.dumps({"schema": "portable-routing-contract.v1", "plans": plans}, sort_keys=True) + "\n"
)
PY

  python3 - "$plans" <<'PY'
import json
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
data = json.loads(text)
assert data["plans"]
assert len({item["case"] for item in data["plans"]}) == len(data["plans"])
assert all(item["fixture_contract"] for item in data["plans"])
for forbidden in (r"/Users/", r"/home/", r"ssh://", r"@[0-9]", r"token"):
    assert re.search(forbidden, text, re.I) is None, forbidden
PY
  ROUTING_CONTRACT_COUNT="$(python3 - "$plans" <<'PY'
import json
import pathlib
import sys

print(len(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["plans"]))
PY
)"
}

materialize_hermes_retired_copies() {
  local baseline_root="$1"
  local current_root="$2"
  local live_home="$3"
  local skill_id domain skill source destination

  while IFS= read -r skill_id; do
    domain="${skill_id%%.*}"
    skill="${skill_id#*.}"
    source="$baseline_root/build/hermes/plugins/$domain/skills/$skill"
    destination="$live_home/skills/$domain/$skill"
    test -d "$source" || return 1
    mkdir -p "$(dirname "$destination")"
    cp -a "$source" "$destination"
  done < <(python3 - "$current_root/manifests/retired-skill-ids.json" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print("\n".join(data["skills"]))
PY
  )
}

collect_hermes_active_ids() {
  local live_home="$1"
  {
    find "$live_home/external-skills/agent-runtime-kit" \
      -mindepth 3 -maxdepth 3 -path '*/SKILL.md' -print 2>/dev/null |
      sed "s#^$live_home/external-skills/agent-runtime-kit/##" |
      sed 's#/#.#g' |
      sed 's#\.SKILL\.md$##'
    find "$live_home/skills" -mindepth 3 -maxdepth 3 -path '*/SKILL.md' -print 2>/dev/null |
      sed "s#^$live_home/skills/##" |
      sed 's#/#.#g' |
      sed 's#\.SKILL\.md$##'
  } | sort -u
}

collect_hermes_legacy_ids() {
  local live_home="$1"
  find "$live_home/skills" -mindepth 3 -maxdepth 3 -path '*/SKILL.md' -print 2>/dev/null |
    sed "s#^$live_home/skills/##" |
    sed 's#/#.#g' |
    sed 's#\.SKILL\.md$##' |
    sort -u
}

write_hermes_retired_ids() {
  local repo_root="$1"
  local output="$2"
  python3 - "$repo_root/manifests/retired-skill-ids.json" "$output" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
pathlib.Path(sys.argv[2]).write_text(
    "".join(f"{skill_id}\n" for skill_id in sorted(data["skills"])),
    encoding="utf-8",
)
PY
}

write_hermes_quarantine_inventory() {
  local repo_root="$1"
  local live_home="$2"
  local generations="$3"
  local output="$4"
  python3 - \
    "$repo_root/manifests/retired-hermes-skill-copies.json" \
    "$live_home/.agent-runtime-kit-quarantine/hermes-retired-skills" \
    "$generations" "$output" <<'PY'
import hashlib
import json
import os
import pathlib
import re
import stat
import sys

manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
retired = sorted(manifest["skills"])
expected_digests = manifest["skills"]
root = pathlib.Path(sys.argv[2])
generations = int(sys.argv[3])

def tree_digest(tree):
    metadata = tree.lstat()
    assert stat.S_ISDIR(metadata.st_mode) and not tree.is_symlink(), tree
    entries = []
    for directory, dirnames, filenames in os.walk(tree, followlinks=False):
        current = pathlib.Path(directory)
        for name in sorted(dirnames + filenames):
            path = current / name
            item = path.lstat()
            relative = path.relative_to(tree).as_posix()
            if stat.S_ISLNK(item.st_mode):
                raise AssertionError(path)
            if stat.S_ISDIR(item.st_mode):
                entries.append((relative, "d", "0755", None))
            elif stat.S_ISREG(item.st_mode):
                mode = "0755" if item.st_mode & 0o111 else "0644"
                entries.append((relative, "f", mode, path.read_bytes()))
            else:
                raise AssertionError(path)
    digest = hashlib.sha256()
    for relative, kind, mode, content in sorted(entries):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(mode.encode("ascii"))
        digest.update(b"\0")
        if content is not None:
            digest.update(str(len(content)).encode("ascii"))
            digest.update(b"\0")
            digest.update(content)
    return digest.hexdigest()

expected = []
for skill_id in retired:
    domain, skill = skill_id.split(".", 1)
    expected.append((skill_id, 1, root / domain / skill))
    for generation in range(2, generations + 1):
        expected.append((
            skill_id,
            generation,
            root / domain / f"{skill}.generation-{generation:06d}",
        ))
for skill_id, _, path in expected:
    assert tree_digest(path) == expected_digests[skill_id], path

observed = []
pattern = re.compile(r"(.+)\.generation-([0-9]{6})$")
for domain in sorted(root.iterdir()):
    if not domain.is_dir():
        raise AssertionError(domain)
    for entry in sorted(domain.iterdir()):
        metadata = entry.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or entry.is_symlink():
            raise AssertionError(entry)
        match = pattern.fullmatch(entry.name)
        if match:
            skill = match.group(1)
            generation = int(match.group(2))
        else:
            skill = entry.name
            generation = 1
        skill_id = f"{domain.name}.{skill}"
        digest = tree_digest(entry)
        assert digest == expected_digests[skill_id], entry
        observed.append((skill_id, generation, digest, entry))
assert [(skill_id, generation) for skill_id, generation, _, _ in observed] == [
    (skill_id, generation) for skill_id, generation, _ in sorted(expected)
]
pathlib.Path(sys.argv[4]).write_text(
    "".join(
        f"{skill_id} generation-{generation:06d} sha256:{digest}\n"
        for skill_id, generation, digest, _ in observed
    ),
    encoding="utf-8",
)
PY
}

runtime_convergence_hermes() {
  local repo_root="$1"
  local baseline_root="$2"
  local tmp_root="$3"
  local artifacts_dir="$4"
  local live_home state_home observed expected_retired external_ids legacy_ids
  local quarantine_first quarantine_second quarantine_after_idempotent

  live_home="$(runtime_live_home "$tmp_root" hermes)"
  state_home="$(runtime_state_home "$tmp_root" hermes)"
  mkdir -p "$live_home" "$state_home" "$artifacts_dir"
  expected_retired="$artifacts_dir/hermes.expected-retired.txt"
  external_ids="$artifacts_dir/hermes.external.txt"
  legacy_ids="$artifacts_dir/hermes.legacy.txt"
  quarantine_first="$artifacts_dir/hermes.quarantine-first.txt"
  quarantine_second="$artifacts_dir/hermes.quarantine-second.txt"
  quarantine_after_idempotent="$artifacts_dir/hermes.quarantine-after-idempotent.txt"
  write_hermes_retired_ids "$repo_root" "$expected_retired"

  runtime_install_product "$baseline_root" "$tmp_root" hermes \
    "$artifacts_dir/baseline" || return 1
  materialize_hermes_retired_copies "$baseline_root" "$repo_root" "$live_home" || return 1
  runtime_collect_installed_skills "$live_home" hermes >"$external_ids"
  diff -u "$baseline_root/tests/sandbox/hermes/expected-skills.txt" "$external_ids" || return 1
  collect_hermes_legacy_ids "$live_home" >"$legacy_ids"
  diff -u "$expected_retired" "$legacy_ids" || return 1
  observed="$artifacts_dir/hermes.baseline-active.txt"
  collect_hermes_active_ids "$live_home" >"$observed"
  diff -u "$baseline_root/tests/sandbox/hermes/expected-skills.txt" "$observed" || return 1
  test "$(wc -l <"$observed" | tr -d '[:space:]')" = 66 || return 1

  agent-runtime render --source-root "$repo_root" --product hermes \
    >"$artifacts_dir/hermes.upgrade-first-render.log" 2>&1 || return 1
  agent-runtime install --source-root "$repo_root" --product hermes \
    --live-home "$live_home" --state-home "$state_home" --no-overlay --apply \
    >"$artifacts_dir/hermes.upgrade-first-install.log" 2>&1 || return 1
  runtime_remove_retired_surface "$repo_root" hermes "$live_home" \
    >"$artifacts_dir/hermes.external-cleanup-first.log" 2>&1 || return 1
  agent-runtime prune-stale --source-root "$repo_root" --product hermes \
    --live-home "$live_home" --no-overlay --apply --format json \
    >"$artifacts_dir/hermes.prune-first.json" 2>&1 || return 1
  (
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$repo_root/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$repo_root"
    APPLY=1
    cleanup_hermes_legacy_runtime_kit_skill_root "$live_home"
  ) >"$artifacts_dir/hermes.cleanup-first.log" 2>&1 || return 1
  runtime_install_product "$repo_root" "$tmp_root" hermes \
    "$artifacts_dir/upgrade-first" || return 1
  runtime_collect_installed_skills "$live_home" hermes >"$external_ids"
  diff -u "$repo_root/tests/sandbox/hermes/expected-skills.txt" "$external_ids" || return 1
  collect_hermes_legacy_ids "$live_home" >"$legacy_ids"
  test ! -s "$legacy_ids" || return 1
  write_hermes_quarantine_inventory "$repo_root" "$live_home" 1 "$quarantine_first" || return 1
  observed="$artifacts_dir/hermes.upgrade-first-active.txt"
  collect_hermes_active_ids "$live_home" >"$observed"
  diff -u "$repo_root/tests/sandbox/hermes/expected-skills.txt" "$observed" || return 1
  test "$(wc -l <"$observed" | tr -d '[:space:]')" = 26 || return 1

  runtime_install_product "$baseline_root" "$tmp_root" hermes \
    "$artifacts_dir/rollback" || return 1
  materialize_hermes_retired_copies "$baseline_root" "$repo_root" "$live_home" || return 1
  runtime_collect_installed_skills "$live_home" hermes >"$external_ids"
  diff -u "$baseline_root/tests/sandbox/hermes/expected-skills.txt" "$external_ids" || return 1
  collect_hermes_legacy_ids "$live_home" >"$legacy_ids"
  diff -u "$expected_retired" "$legacy_ids" || return 1
  observed="$artifacts_dir/hermes.rollback-active.txt"
  collect_hermes_active_ids "$live_home" >"$observed"
  diff -u "$baseline_root/tests/sandbox/hermes/expected-skills.txt" "$observed" || return 1
  test "$(wc -l <"$observed" | tr -d '[:space:]')" = 66 || return 1

  agent-runtime install --source-root "$repo_root" --product hermes \
    --live-home "$live_home" --state-home "$state_home" --no-overlay --apply \
    >"$artifacts_dir/hermes.upgrade-second-install.log" 2>&1 || return 1
  runtime_remove_retired_surface "$repo_root" hermes "$live_home" \
    >"$artifacts_dir/hermes.external-cleanup-second.log" 2>&1 || return 1
  agent-runtime prune-stale --source-root "$repo_root" --product hermes \
    --live-home "$live_home" --no-overlay --apply --format json \
    >"$artifacts_dir/hermes.prune-second.json" 2>&1 || return 1
  (
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$repo_root/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$repo_root"
    APPLY=1
    cleanup_hermes_legacy_runtime_kit_skill_root "$live_home"
  ) >"$artifacts_dir/hermes.cleanup-second.log" 2>&1 || return 1
  runtime_install_product "$repo_root" "$tmp_root" hermes \
    "$artifacts_dir/upgrade-second" || return 1
  runtime_collect_installed_skills "$live_home" hermes >"$external_ids"
  diff -u "$repo_root/tests/sandbox/hermes/expected-skills.txt" "$external_ids" || return 1
  collect_hermes_legacy_ids "$live_home" >"$legacy_ids"
  test ! -s "$legacy_ids" || return 1
  write_hermes_quarantine_inventory "$repo_root" "$live_home" 2 "$quarantine_second" || return 1
  observed="$artifacts_dir/hermes.upgrade-second-active.txt"
  collect_hermes_active_ids "$live_home" >"$observed"
  diff -u "$repo_root/tests/sandbox/hermes/expected-skills.txt" "$observed" || return 1
  test "$(wc -l <"$observed" | tr -d '[:space:]')" = 26 || return 1
  test -d "$live_home/.agent-runtime-kit-quarantine/hermes-retired-skills/conversation/orchestrator-first"
  test -d "$live_home/.agent-runtime-kit-quarantine/hermes-retired-skills/conversation/orchestrator-first.generation-000002"

  agent-runtime install --source-root "$repo_root" --product hermes \
    --live-home "$live_home" --state-home "$state_home" --no-overlay --apply \
    >"$artifacts_dir/hermes.idempotent-install.log" 2>&1 || return 1
  grep -q 'changes=0' "$artifacts_dir/hermes.idempotent-install.log" || return 1
  (
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$repo_root/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$repo_root"
    APPLY=1
    cleanup_hermes_legacy_runtime_kit_skill_root "$live_home"
  ) >"$artifacts_dir/hermes.idempotent-cleanup.log" 2>&1 || return 1
  write_hermes_quarantine_inventory \
    "$repo_root" "$live_home" 2 "$quarantine_after_idempotent" || return 1
  cmp "$quarantine_second" "$quarantine_after_idempotent" || return 1
  runtime_collect_installed_skills "$live_home" hermes >"$external_ids"
  diff -u "$repo_root/tests/sandbox/hermes/expected-skills.txt" "$external_ids" || return 1
  collect_hermes_legacy_ids "$live_home" >"$legacy_ids"
  test ! -s "$legacy_ids" || return 1

  python3 - "$artifacts_dir/hermes.portable-summary.json" <<'PY'
import json
import pathlib
import sys

pathlib.Path(sys.argv[1]).write_text(json.dumps({
    "schema": "portable-convergence-summary.v1",
    "product": "hermes",
    "baseline_skill_count": 66,
    "skill_count": 26,
    "rollback_verified": True,
    "upgrade_verified": True,
    "retired_pruned": True,
    "retained_generations": True,
    "idempotent": True,
}, sort_keys=True) + "\n", encoding="utf-8")
PY
  RUNTIME_SMOKE_SKILL_COUNT=26
}

PORTABLE_SOURCE_ROOT="$(runtime_prepare_portable_source "$REPO_ROOT" "$TMP_ROOT/portable-source")"
BASELINE_REVISION="$(python3 - "$PORTABLE_SOURCE_ROOT/manifests/retired-hermes-skill-copies.json" <<'PY'
import json
import pathlib
import sys

print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["source_revision"])
PY
)"
BASELINE_SOURCE_ROOT="$(runtime_prepare_revision_source \
  "$PORTABLE_SOURCE_ROOT" "$BASELINE_REVISION" "$TMP_ROOT/baseline-source")"
products="${PRODUCT:-codex claude hermes}"
failures=0
if validate_dirty_source_rejected && validate_snapshot_ref_boundary; then
  results_add "convergence.portable-source-boundary" shared-cli pass 1 \
    "dirty content and unrelated refs or objects were excluded from portable snapshots"
else
  results_add "convergence.portable-source-boundary" shared-cli fail 0 \
    "dirty source rejection boundary failed"
  failures=1
fi
for product in $products; do
  lifecycle_status=0
  if [ "$product" = hermes ]; then
    runtime_convergence_hermes \
      "$PORTABLE_SOURCE_ROOT" "$BASELINE_SOURCE_ROOT" "$TMP_ROOT" \
      "$CONVERGENCE_ARTIFACTS_DIR/$product" || lifecycle_status=$?
  else
    runtime_convergence_product \
      "$PORTABLE_SOURCE_ROOT" "$BASELINE_SOURCE_ROOT" "$TMP_ROOT" "$product" \
      "$CONVERGENCE_ARTIFACTS_DIR/$product" || lifecycle_status=$?
  fi
  if [ "$lifecycle_status" -eq 0 ] &&
    python3 - "$CONVERGENCE_ARTIFACTS_DIR/$product/$product.portable-summary.json" <<'PY'
import json
import pathlib
import sys

summary = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert summary["baseline_skill_count"] == 66
assert summary["skill_count"] == 26
PY
  then
    results_add "convergence.$product.lifecycle" "$product" pass \
      "$RUNTIME_SMOKE_SKILL_COUNT" \
      "historical upgrade, rollback rehearsal, retired prune, exact registry activation, receipt transition, and idempotent apply passed"
  else
    results_add "convergence.$product.lifecycle" "$product" fail 0 \
      "portable lifecycle acceptance failed"
    failures=1
  fi

  original_repo_root="$REPO_ROOT"
  REPO_ROOT="$PORTABLE_SOURCE_ROOT"
  if validate_routing_contract "$product"; then
    results_add "convergence.$product.routing-contract" "$product" pass \
      "$ROUTING_CONTRACT_COUNT" \
      "$ROUTING_CONTRACT_COUNT generic prompt/route fixtures validated; behavioral routing remains live acceptance"
  else
    results_add "convergence.$product.routing-contract" "$product" fail 0 \
      "prompt/route contract validation failed"
    failures=1
  fi
  REPO_ROOT="$original_repo_root"
done

exit "$failures"
