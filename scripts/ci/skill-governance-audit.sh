#!/usr/bin/env bash
# Validate repo-owned skill lifecycle invariants without adding another CLI
# implementation layer. The parser is intentionally scoped to this repo's
# manifests and fixture shapes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="repo"
SHAPE_PATHS=()

usage() {
  cat <<'USAGE'
Usage: bash scripts/ci/skill-governance-audit.sh [--check-counts|--update-counts] [--fixture create|remove|create-project|remove-project|count-refresh|codex-plugin|reviewer-profile|description-limit|exposure-contract] [--shape-only [paths...]]

Checks:
  default                   Validate active repo source/manifests/plugins/reminders/counts.
  --check-counts            Check maintained active skill-count references only.
  --update-counts           Refresh maintained active skill-count references.
  --fixture create          Validate the create-skill fixture completeness.
  --fixture remove          Validate the remove-skill dry-run fixture coverage.
  --fixture create-project  Validate the create-project-skill fixture completeness.
  --fixture remove-project  Validate the remove-project-skill dry-run fixture coverage.
  --fixture count-refresh   Validate stale count detection and whitelist updates.
  --fixture codex-plugin    Validate Codex plugin skill-list drift detection.
  --fixture reviewer-profile  Validate missing Codex reviewer profile fields fail closed.
  --fixture description-limit  Validate the >240-char and missing-description hard-fail paths.
  --fixture exposure-contract  Validate v2 admission, exposure, and disposition failure paths.
  --shape-only [paths...]   Lint H2 section shape on the given SKILL.md.tera paths
                            (fast pre-commit gate; consumes all remaining args).
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-counts)
      MODE="count-check"
      shift
      ;;
    --update-counts)
      MODE="count-update"
      shift
      ;;
    --fixture)
      if [ "$#" -lt 2 ]; then
        echo "skill-governance-audit: --fixture requires create|remove|create-project|remove-project|count-refresh|codex-plugin|reviewer-profile|description-limit|exposure-contract" >&2
        exit 2
      fi
      case "$2" in
        create | remove | create-project | remove-project)
          MODE="$2-fixture"
          ;;
        count-refresh)
          MODE="count-refresh-fixture"
          ;;
        codex-plugin)
          MODE="codex-plugin-fixture"
          ;;
        reviewer-profile)
          MODE="reviewer-profile-fixture"
          ;;
        description-limit)
          MODE="description-limit-fixture"
          ;;
        exposure-contract)
          MODE="exposure-contract-fixture"
          ;;
        *)
          echo "skill-governance-audit: unsupported fixture: $2" >&2
          exit 2
          ;;
      esac
      shift 2
      ;;
    --shape-only)
      MODE="shape-only"
      shift
      while [ "$#" -gt 0 ]; do
        SHAPE_PATHS+=("$1")
        shift
      done
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "skill-governance-audit: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

python3 - "$MODE" "$REPO_ROOT" ${SHAPE_PATHS[@]+"${SHAPE_PATHS[@]}"} <<'PY'
from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


MODE = sys.argv[1]
ROOT = Path(sys.argv[2])
SHAPE_ARG_PATHS = sys.argv[3:]


CANONICAL_SECTIONS = ("Contract", "Entrypoint", "Workflow", "Boundary")

# Frontmatter `description` is always-loaded context (every session, both
# products). Keep it minimal per core/skills/README.md "Skill Description
# Rubric"; this hard ceiling backstops the rubric against trigger-phrase bloat.
DESCRIPTION_MAX_CHARS = 240
INITIAL_DISPOSITION_COUNT = 66
INITIAL_DISPOSITION_IDS_SHA256 = "16b2fc145c6d2a556360dc43cddd6a30ea79ad90837d5bcd647971aa84a34d60"
SKILL_ID_RE = r"[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*"
MIGRATION_PROGRESS_PATH = Path(
    "tests/skill-exposure-contract/expected-migration-progress.json"
)


COUNT_TARGETS = [
    {
        "path": "docs/source/harness-shape-codex.md",
        "label": "Codex plugin-scoped skill declaration",
        "pattern": r"(?P<prefix>tree;\n  )(?P<count>\d+)(?P<suffix> Codex plugin-scoped skill\s+entries are declared)",
    },
    {
        "path": "docs/source/harness-shape-codex.md",
        "label": "Codex sandbox expected skill range",
        "pattern": r"(?P<prefix>tests/sandbox/codex/expected-skills\.txt:1-)(?P<count>\d+)(?P<suffix>)",
    },
    {
        "path": "tests/runtime-smoke/expected/install-summary.json",
        "label": "Codex install expected skill count",
        "pattern": r"(?P<prefix>\"id\":\"install\.codex\"[^}\n]*\"skill_count\":)(?P<count>\d+)(?P<suffix>)",
    },
    {
        "path": "tests/runtime-smoke/expected/install-summary.json",
        "label": "Claude install expected skill count",
        "pattern": r"(?P<prefix>\"id\":\"install\.claude\"[^}\n]*\"skill_count\":)(?P<count>\d+)(?P<suffix>)",
    },
    {
        "path": "tests/runtime-smoke/product/expected/product-summary.json",
        "label": "Codex product install expected skill count",
        "pattern": r"(?P<prefix>\"id\":\"product\.codex\.install\"[^}\n]*\"skill_count\":)(?P<count>\d+)(?P<suffix>)",
    },
    {
        "path": "tests/runtime-smoke/product/expected/product-summary.json",
        "label": "Claude product install expected skill count",
        "pattern": r"(?P<prefix>\"id\":\"product\.claude\.install\"[^}\n]*\"skill_count\":)(?P<count>\d+)(?P<suffix>)",
    },
]

STALE_ENDPOINT_COUNT_RE = re.compile(
    rf"\b(?:{INITIAL_DISPOSITION_COUNT}-to-\d+(?:-skill)?|\d+-skill manifest)\b"
)
MAINTAINED_TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".tera",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
HISTORICAL_RECORD_MARKERS = {
    ("docs", "discussions"),
    ("docs", "plans"),
}
GENERATED_OUTPUT_ROOTS = {"build"}


def fail(message: str) -> None:
    print(f"skill-governance-audit: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        fail(f"missing required file: {rel}")
    return path.read_text(encoding="utf-8")


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_skills(path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    product: str | None = None
    in_required = False
    for raw in read(path).splitlines():
        line = raw.rstrip()
        if line.startswith("  - id: "):
            if current is not None:
                entries.append(current)
            current = {
                "id": strip_quotes(line.split(": ", 1)[1]),
                "products": {},
                "required_clis": {},
            }
            product = None
            in_required = False
            continue
        if current is None:
            continue
        if line.startswith("    domain: "):
            current["domain"] = strip_quotes(line.split(": ", 1)[1])
            in_required = False
        elif line.startswith("    source: "):
            current["source"] = strip_quotes(line.split(": ", 1)[1])
            in_required = False
        elif line.startswith("    required_clis: {}"):
            current["required_clis"] = {}
            in_required = False
        elif line.startswith("    required_clis:"):
            current["required_clis"] = {}
            in_required = True
        elif in_required and line.startswith("      ") and ": " in line:
            key, value = line.strip().split(": ", 1)
            required = current["required_clis"]
            assert isinstance(required, dict)
            required[key] = strip_quotes(value)
        elif line.startswith("      codex:") or line.startswith("      claude:") or line.startswith("      hermes:"):
            product = line.strip().removesuffix(":")
            products = current["products"]
            assert isinstance(products, dict)
            products[product] = {}
            in_required = False
        elif product and line.startswith("        ") and ": " in line:
            key, value = line.strip().split(": ", 1)
            products = current["products"]
            assert isinstance(products, dict)
            product_data = products[product]
            assert isinstance(product_data, dict)
            product_data[key] = strip_quotes(value)
            in_required = False
        elif line and not line.startswith("      "):
            in_required = False
    if current is not None:
        entries.append(current)

    text = read(path)
    by_id = {str(entry["id"]): entry for entry in entries}
    chunks = re.split(r"(?=^  - id: )", text, flags=re.M)
    for chunk in chunks:
        id_match = re.match(rf"^  - id: ({SKILL_ID_RE})$", chunk, re.M)
        if not id_match:
            continue
        entry = by_id[id_match.group(1)]
        if re.search(r"^    invocation:$", chunk, re.M):
            role = re.search(r"^      role: ([a-z-]+)$", chunk, re.M)
            intents = re.search(r"^      intents: \[(.*)\]$", chunk, re.M)
            example = re.search(r"^      example_request: (.+)$", chunk, re.M)
            rationale = re.search(r"^      admission_rationale: (.+)$", chunk, re.M)
            entry["invocation"] = {
                "role": role.group(1) if role else "",
                "intents": [
                    strip_quotes(item.strip())
                    for item in (intents.group(1).split(",") if intents else [])
                    if item.strip()
                ],
                "example_request": strip_quotes(example.group(1)) if example else "",
                "admission_rationale": strip_quotes(rationale.group(1)) if rationale else "",
            }
        if re.search(r"^    exposure:$", chunk, re.M):
            profile = re.search(r"^      profile: ([a-z-]+)$", chunk, re.M)
            replacement = re.search(rf"^      replacement: ({SKILL_ID_RE})$", chunk, re.M)
            retire_after = re.search(r'^      retire_after: ["\']?([^"\']+)["\']?$', chunk, re.M)
            entry["exposure"] = {
                "profile": profile.group(1) if profile else "",
                "replacement": replacement.group(1) if replacement else None,
                "retire_after": retire_after.group(1) if retire_after else None,
            }
    return entries


def parse_agents(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    product: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("  - id: "):
            if current is not None:
                entries.append(current)
            current = {"id": strip_quotes(raw.split(": ", 1)[1])}
            product = None
            continue
        if current is None:
            continue
        if raw.startswith("    source: "):
            current["source"] = strip_quotes(raw.split(": ", 1)[1])
        elif re.match(r"^      [a-z]+:$", raw):
            product = raw.strip().removesuffix(":")
        elif product == "codex" and raw.startswith("        name: "):
            current["codex_name"] = strip_quotes(raw.split(": ", 1)[1])
        elif product == "codex" and raw.startswith("        render_to: "):
            current["codex_render_to"] = strip_quotes(raw.split(": ", 1)[1])
    if current is not None:
        entries.append(current)
    return entries


def toml_string(body: str, field: str) -> str | None:
    match = re.search(rf'^{re.escape(field)} = "([^"]+)"$', body, flags=re.MULTILINE)
    return match.group(1) if match else None


def codex_reviewer_profile_errors(root: Path) -> list[str]:
    manifest_path = root / "manifests" / "agents.yaml"
    if not manifest_path.is_file():
        return ["missing manifests/agents.yaml"]

    reviewers = [
        entry
        for entry in parse_agents(manifest_path)
        if entry["id"].startswith("code-review.reviewer-")
    ]
    errors: list[str] = []
    names = [entry.get("codex_name", "") for entry in reviewers]
    if not reviewers:
        errors.append("manifests/agents.yaml declares no code-review reviewers")
    if not all(names) or len(names) != len(set(names)):
        errors.append("Codex reviewer names are missing or duplicated")
    if "reviewer-quick" not in names:
        errors.append("manifest inventory is missing reviewer-quick")

    for entry in reviewers:
        reviewer_id = entry["id"]
        name = entry.get("codex_name", "")
        source = entry.get("source", "")
        expected_name = reviewer_id.split(".", 1)[1]
        if name != expected_name:
            errors.append(
                f"{reviewer_id}: Codex name {name!r} != canonical {expected_name!r}"
            )
        if entry.get("codex_render_to") != f"agents/{name}.toml":
            errors.append(f"{reviewer_id}: Codex render target must match {name!r}")
        template_path = root / source / "AGENT.md.tera"
        if not template_path.is_file():
            errors.append(f"{reviewer_id}: missing source template {source}/AGENT.md.tera")
            continue
        codex = template_path.read_text(encoding="utf-8").split("{%- else -%}", 1)[0]
        actual_name = toml_string(codex, "name")
        model = toml_string(codex, "model")
        effort = toml_string(codex, "model_reasoning_effort")
        sandbox = toml_string(codex, "sandbox_mode")
        if actual_name != name:
            errors.append(f"{reviewer_id}: template name {actual_name!r} != manifest {name!r}")
        if model is None or effort is None or sandbox is None:
            errors.append(
                f"{reviewer_id}: Codex template must explicitly set model, "
                "model_reasoning_effort, and sandbox_mode"
            )
            continue
        expected_model = "gpt-5.6-sol"
        expected_effort = "low" if name == "reviewer-quick" else "medium"
        if model != expected_model:
            errors.append(f"{reviewer_id}: model {model!r} != {expected_model!r}")
        if effort != expected_effort:
            errors.append(f"{reviewer_id}: effort {effort!r} != {expected_effort!r}")
        if sandbox != "read-only":
            errors.append(f"{reviewer_id}: sandbox {sandbox!r} != 'read-only'")

    skill_path = root / "core" / "skills" / "code-review" / "code-review-specialists" / "SKILL.md.tera"
    policy_path = root / "core" / "policies" / "code-review-delegation-codex.md"
    if not skill_path.is_file() or not policy_path.is_file():
        errors.append("Codex reviewer dispatch contract source is missing")
        return errors
    skill = skill_path.read_text(encoding="utf-8")
    policy = policy_path.read_text(encoding="utf-8")
    for name in names:
        if f"`{name}`" not in skill:
            errors.append(f"dispatch contract does not name manifest reviewer {name}")
        underscored = name.replace("-", "_")
        if underscored in skill:
            errors.append(f"dispatch contract uses non-canonical reviewer identity {underscored}")
    for needle in (
        "canonical custom-agent identity",
        "`agent_type`",
        "`task_name` is only a workflow label",
        "do not spawn a generic child",
        "inline fallback",
    ):
        if needle not in skill:
            errors.append(f"code-review skill missing dispatch contract phrase: {needle}")
    for needle in ("`agent_type`", "do not spawn a generic child", "inline fallback"):
        if needle not in policy:
            errors.append(f"Codex review policy missing fail-closed phrase: {needle}")
    return errors


def validate_codex_reviewer_profiles(root: Path) -> None:
    errors = codex_reviewer_profile_errors(root)
    if errors:
        fail("Codex reviewer profile contract failed: " + "; ".join(errors))


def parse_skill_migration(path: Path) -> dict[str, object]:
    prefix = read(path).split("\nskills:\n", 1)[0]
    version = re.search(r"^schema_version: (\d+)$", prefix, re.M)
    owner = re.search(r"^  owner: (.+)$", prefix, re.M)
    pending = re.findall(rf"^    - ({SKILL_ID_RE})$", prefix, re.M)
    return {
        "schema_version": int(version.group(1)) if version else 0,
        "owner": strip_quotes(owner.group(1)) if owner else "",
        "pending_disposition": pending,
    }


def parse_disposition_scalar(raw: str) -> object:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    return value


def parse_dispositions(path: Path) -> dict[str, object]:
    text = read(path)
    version = re.search(r"^schema_version: (\d+)$", text, re.M)
    owner = re.search(r"^owner: (.+)$", text, re.M)
    source_count = re.search(r"^source_skill_count: (\d+)$", text, re.M)
    source_ids_sha256 = re.search(r'^source_skill_ids_sha256: ["\']?([0-9a-f]{64})["\']?$', text, re.M)
    root_keys = set(re.findall(r"^([a-z_]+):", text, re.M))
    allowed_root_keys = {
        "schema_version",
        "owner",
        "source_skill_count",
        "source_skill_ids_sha256",
        "dispositions",
    }
    scalar_fields = {
        "status",
        "example_request",
        "user_outcome",
        "destination",
        "enforcement_point",
        "migration_path",
        "replacement",
        "compatibility_required",
        "live_cleanup_required",
        "rationale",
    }
    list_fields = {"parent_intents", "current_clis", "current_hooks"}
    rows: list[dict[str, object]] = []
    for chunk in re.split(r"(?=^  - id: )", text, flags=re.M):
        id_match = re.match(rf"^  - id: ({SKILL_ID_RE})$", chunk, re.M)
        if not id_match:
            continue
        row: dict[str, object] = {"id": id_match.group(1)}
        unknown_fields: list[str] = []
        parse_errors: list[str] = []
        lines = chunk.splitlines()
        for index, line in enumerate(lines):
            field = re.match(r"^    ([a-z_]+):(.*)$", line)
            if field is None:
                continue
            key = field.group(1)
            raw_value = field.group(2).strip()
            if key in scalar_fields:
                row[key] = parse_disposition_scalar(raw_value)
                continue
            if key not in list_fields:
                unknown_fields.append(key)
                continue

            values: list[object] = []
            if raw_value:
                if not (raw_value.startswith("[") and raw_value.endswith("]")):
                    parse_errors.append(f"{key} must be an inline or block array")
                    continue
                inner = raw_value[1:-1].strip()
                if inner:
                    values = [
                        parse_disposition_scalar(item)
                        for item in inner.split(",")
                    ]
            else:
                for continuation in lines[index + 1 :]:
                    item = re.match(r"^      - (.*)$", continuation)
                    if item is not None:
                        values.append(parse_disposition_scalar(item.group(1)))
                        continue
                    if not continuation.strip() or continuation.lstrip().startswith("#"):
                        continue
                    break
            row[key] = values
        if unknown_fields:
            row["__unknown_fields"] = sorted(set(unknown_fields))
        if parse_errors:
            row["__parse_errors"] = parse_errors
        rows.append(row)
    return {
        "schema_version": int(version.group(1)) if version else 0,
        "owner": strip_quotes(owner.group(1)) if owner else "",
        "source_skill_count": int(source_count.group(1)) if source_count else -1,
        "source_skill_ids_sha256": source_ids_sha256.group(1) if source_ids_sha256 else "",
        "unknown_fields": sorted(root_keys - allowed_root_keys),
        "rows": rows,
    }


def load_migration_progress(root: Path) -> dict[str, object]:
    progress = json.loads(read(root / MIGRATION_PROGRESS_PATH))
    if not isinstance(progress, dict):
        fail("migration progress contract must be an object")
    return progress


def exposure_contract_errors(root: Path) -> list[str]:
    errors: list[str] = []
    skills_path = root / "manifests" / "skills.yaml"
    dispositions_path = root / "manifests" / "skill-dispositions.yaml"
    skills_schema_path = root / "core" / "docs" / "schemas" / "skills.schema.json"
    dispositions_schema_path = root / "core" / "docs" / "schemas" / "skill-dispositions.schema.json"

    skills_schema = json.loads(read(skills_schema_path))
    disposition_schema = json.loads(read(dispositions_schema_path))
    if skills_schema.get("properties", {}).get("schema_version", {}).get("const") != 2:
        errors.append("skills schema version must be 2")
    if disposition_schema.get("properties", {}).get("schema_version", {}).get("const") != 1:
        errors.append("disposition schema version must be 1")

    migration = parse_skill_migration(skills_path)
    skills = parse_skills(skills_path)
    dispositions = parse_dispositions(dispositions_path)
    progress = load_migration_progress(root)
    skill_ids = [str(entry["id"]) for entry in skills]
    skill_id_set = set(skill_ids)
    pending = migration["pending_disposition"]
    assert isinstance(pending, list)
    pending_ids = [str(item) for item in pending]
    pending_set = set(pending_ids)
    rows = dispositions["rows"]
    assert isinstance(rows, list)
    disposition_ids = [str(row["id"]) for row in rows]
    expected_reviewed = progress.get("reviewed_ids", [])
    expected_pending = progress.get("pending_ids", [])
    reviewed_field_mapping = progress.get("reviewed_field_mapping", [])

    if progress.get("schema") != "agent-runtime-kit.skill-migration-progress.v1":
        errors.append("migration progress schema is invalid")
    if progress.get("task") != "3.1" or progress.get("advance_in_task") != "complete":
        errors.append("migration progress task lifecycle must be 3.1 -> complete")
    if not isinstance(expected_reviewed, list) or not all(
        isinstance(item, str) for item in expected_reviewed
    ):
        errors.append("migration progress reviewed_ids must be a string array")
        expected_reviewed = []
    if not isinstance(expected_pending, list) or not all(
        isinstance(item, str) for item in expected_pending
    ):
        errors.append("migration progress pending_ids must be a string array")
        expected_pending = []
    if not isinstance(reviewed_field_mapping, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("disposition"), str)
        and isinstance(item.get("manifest"), str)
        for item in reviewed_field_mapping
    ):
        errors.append("migration progress reviewed_field_mapping is invalid")
        reviewed_field_mapping = []

    if migration["schema_version"] != 2:
        errors.append("skills manifest schema version must be 2")
    if not migration["owner"]:
        errors.append("migration owner is required")
    if len(skill_ids) != len(skill_id_set):
        errors.append("active skill ids must be unique")
    if len(pending_ids) != len(pending_set):
        errors.append("pending disposition ids must be unique")
    unknown_pending = sorted(pending_set - skill_id_set)
    if unknown_pending:
        errors.append(f"pending disposition ids are not active: {unknown_pending}")

    if dispositions["schema_version"] != 1:
        errors.append("disposition manifest schema version must be 1")
    if dispositions["unknown_fields"]:
        errors.append(f"unknown disposition manifest fields: {dispositions['unknown_fields']}")
    if dispositions["owner"] != migration["owner"]:
        errors.append("migration and disposition owners must match")
    if dispositions["source_skill_count"] != INITIAL_DISPOSITION_COUNT:
        errors.append(f"source_skill_count must remain {INITIAL_DISPOSITION_COUNT}")
    if len(rows) != INITIAL_DISPOSITION_COUNT:
        errors.append(f"disposition ledger must retain {INITIAL_DISPOSITION_COUNT} rows")
    if len(disposition_ids) != len(set(disposition_ids)):
        errors.append("disposition ids must be unique")
    disposition_digest = hashlib.sha256(("\n".join(disposition_ids) + "\n").encode()).hexdigest()
    if dispositions["source_skill_ids_sha256"] != INITIAL_DISPOSITION_IDS_SHA256:
        errors.append("source_skill_ids_sha256 must remain the initial baseline digest")
    if disposition_digest != INITIAL_DISPOSITION_IDS_SHA256:
        errors.append("ordered disposition ids do not match the frozen baseline")

    pending_rows = [str(row["id"]) for row in rows if row.get("status") == "pending"]
    reviewed_rows = [str(row["id"]) for row in rows if row.get("status") == "reviewed"]
    if pending_ids != [skill_id for skill_id in skill_ids if skill_id in pending_set]:
        errors.append("pending disposition ids must follow active manifest order")
    if pending_rows != pending_ids:
        errors.append("pending disposition rows must exactly match the migration pending set")
    if reviewed_rows != expected_reviewed:
        errors.append("reviewed disposition rows do not match the final migration progress contract")
    if pending_rows != expected_pending:
        errors.append("pending disposition rows do not match the final migration progress contract")
    expected_partition = [*expected_reviewed, *expected_pending]
    if len(expected_partition) != len(set(expected_partition)):
        errors.append("migration progress ids must be unique across reviewed and pending sets")
    if set(expected_partition) != set(disposition_ids):
        errors.append("migration progress ids must partition the frozen disposition ledger")

    valid_destinations = {
        "entrypoint",
        "policy",
        "intent-doc",
        "hook-gate",
        "cli-only",
        "internal-workflow",
        "merge",
        "remove",
        "compatibility",
    }
    for row in rows:
        row_id = str(row["id"])
        unknown_fields = row.get("__unknown_fields", [])
        parse_errors = row.get("__parse_errors", [])
        if unknown_fields:
            errors.append(f"{row_id} unknown disposition fields: {unknown_fields}")
        for parse_error in parse_errors:
            errors.append(f"{row_id} {parse_error}")

        status = row.get("status")
        if status not in {"pending", "reviewed"}:
            errors.append(f"{row_id} disposition status is invalid")
            continue

        for field in (
            "example_request",
            "enforcement_point",
            "migration_path",
            "rationale",
        ):
            if field in row and (
                not isinstance(row[field], str) or not str(row[field]).strip()
            ):
                errors.append(f"{row_id} {field} must be a non-empty string")

        if "user_outcome" in row and row["user_outcome"] not in {"yes", "no", "advanced"}:
            errors.append(f"{row_id} user_outcome is invalid")
        if "destination" in row and row["destination"] not in valid_destinations:
            errors.append(f"{row_id} reviewed disposition destination is invalid")
        for field in ("parent_intents", "current_clis", "current_hooks"):
            if field not in row:
                continue
            values = row[field]
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                errors.append(f"{row_id} {field} must contain non-empty strings")
                continue
            if len(values) != len(set(values)):
                errors.append(f"{row_id} {field} must contain unique items")
            if field == "parent_intents" and not values:
                errors.append(f"{row_id} parent_intents must not be empty")
        for field in ("compatibility_required", "live_cleanup_required"):
            if field in row and type(row[field]) is not bool:
                errors.append(f"{row_id} {field} must be boolean")
        if "replacement" in row and (
            not isinstance(row["replacement"], str)
            or re.fullmatch(SKILL_ID_RE, str(row["replacement"])) is None
        ):
            errors.append(f"{row_id} replacement must be a skill id")

        if status == "pending":
            forbidden = {"user_outcome", "destination", "parent_intents", "rationale"}
            if forbidden.intersection(row):
                errors.append(f"{row_id} pending disposition cannot carry reviewed fields")
            continue
        required = {
            "user_outcome",
            "destination",
            "parent_intents",
            "current_clis",
            "current_hooks",
            "enforcement_point",
            "migration_path",
            "compatibility_required",
            "live_cleanup_required",
            "rationale",
        }
        missing = sorted(required - set(row))
        if missing:
            errors.append(f"{row_id} reviewed disposition is missing {missing}")

    from datetime import date

    def valid_date(value: object) -> bool:
        if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    disposition_by_id = {str(row["id"]): row for row in rows}
    for entry in skills:
        skill_id = str(entry["id"])
        invocation = entry.get("invocation")
        exposure = entry.get("exposure")
        if skill_id in pending_set:
            if invocation is not None or exposure is not None:
                errors.append(f"{skill_id} pending disposition must not carry retained metadata")
            continue
        if not isinstance(invocation, dict) or not isinstance(exposure, dict):
            errors.append(f"{skill_id} retained skill requires invocation and exposure metadata")
            continue
        role = invocation.get("role")
        if role not in {"workflow", "maintenance", "advanced", "compatibility"}:
            errors.append(f"{skill_id} invocation role is invalid")
        if role == "advanced":
            errors.append(f"{skill_id} advanced role has no supported opt-in exposure")
        if not invocation.get("intents") or not invocation.get("example_request") or not invocation.get("admission_rationale"):
            errors.append(f"{skill_id} retained admission metadata is incomplete")
        if exposure.get("profile") != "default":
            errors.append(f"{skill_id} exposure profile must be default")
        replacement = exposure.get("replacement")
        retire_after = exposure.get("retire_after")
        if role == "compatibility":
            if (
                not replacement
                or replacement == skill_id
                or replacement not in skill_id_set
                or replacement in pending_set
            ):
                errors.append(f"{skill_id} compatibility replacement must name another reviewed active skill")
            if not valid_date(retire_after):
                errors.append(f"{skill_id} compatibility retire_after must be YYYY-MM-DD")
        elif replacement is not None or retire_after is not None:
            errors.append(f"{skill_id} non-compatibility role cannot carry lifecycle metadata")

        row = disposition_by_id.get(skill_id)
        if row is None or row.get("status") != "reviewed":
            continue
        for mapping in reviewed_field_mapping:
            disposition_field = str(mapping["disposition"])
            manifest_path = str(mapping["manifest"])
            if not manifest_path.startswith("invocation."):
                errors.append(
                    f"reviewed field mapping target is unsupported: {manifest_path}"
                )
                continue
            manifest_field = manifest_path.removeprefix("invocation.")
            if row.get(disposition_field) != invocation.get(manifest_field):
                errors.append(
                    f"{skill_id} reviewed metadata mismatch: "
                    f"disposition.{disposition_field} != {manifest_path}"
                )

    return errors


def validate_exposure_contract(root: Path) -> None:
    errors = exposure_contract_errors(root)
    if errors:
        fail("skill exposure contract: " + "; ".join(errors))


def active_skill_count(root: Path) -> int:
    return len(parse_skills(root / "manifests" / "skills.yaml"))


def is_historical_record(path: Path) -> bool:
    parts = path.parts
    return any(
        parts[index : index + 2] in HISTORICAL_RECORD_MARKERS
        for index in range(len(parts) - 1)
    )


def stale_endpoint_count_claims(root: Path) -> list[str]:
    claims: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(root)
        if (
            not rel.parts
            or rel.parts[0] in GENERATED_OUTPUT_ROOTS
            or path.suffix not in MAINTAINED_TEXT_SUFFIXES
            or is_historical_record(rel)
        ):
            continue
        for line_number, line in enumerate(read(path).splitlines(), start=1):
            for match in STALE_ENDPOINT_COUNT_RE.finditer(line):
                claims.append(f"{rel}:{line_number}: {match.group(0)}")
    return claims


def validate_endpoint_count_claims(root: Path) -> None:
    claims = stale_endpoint_count_claims(root)
    if claims:
        fail(
            "stale exact endpoint-count claims outside historical records: "
            + "; ".join(claims)
        )


def apply_count_targets(root: Path, update: bool) -> tuple[int, list[str]]:
    count = active_skill_count(root)
    changes: list[str] = []

    for target in COUNT_TARGETS:
        rel = Path(str(target["path"]))
        if rel.parts[:2] == ("docs", "plans"):
            fail(f"count target is outside maintained whitelist: {rel}")

        path = root / rel
        text = read(path)
        pattern = re.compile(str(target["pattern"]))
        matches = list(pattern.finditer(text))
        label = str(target["label"])
        if len(matches) != 1:
            fail(
                f"count target pattern must match exactly once: "
                f"{rel} label={label!r} matches={len(matches)}"
            )

        match = matches[0]
        old = match.group("count")
        updated = pattern.sub(
            lambda item: f"{item.group('prefix')}{count}{item.group('suffix')}",
            text,
            count=1,
        )
        if updated != text:
            changes.append(f"{rel}: {label} {old}->{count}")
            if update:
                path.write_text(updated, encoding="utf-8")

    return count, changes


def validate_counts(root: Path) -> int:
    count, changes = apply_count_targets(root, update=False)
    if changes:
        fail("active skill count drift: " + "; ".join(changes))
    validate_endpoint_count_claims(root)
    return count


def update_counts(root: Path) -> None:
    count, changes = apply_count_targets(root, update=True)
    validate_endpoint_count_claims(root)
    if changes:
        print(
            "skill-governance-audit: counts updated "
            f"skills={count} targets={len(COUNT_TARGETS)}"
        )
    else:
        print(
            "skill-governance-audit: counts OK "
            f"skills={count} targets={len(COUNT_TARGETS)}"
        )


def parse_plugins(path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_contained = False
    in_product_manifests = False
    for raw in read(path).splitlines():
        line = raw.rstrip()
        if line.startswith("  - id: "):
            if current is not None:
                entries.append(current)
            current = {
                "id": strip_quotes(line.split(": ", 1)[1]),
                "contained_skills": [],
                "product_manifests": {},
            }
            in_contained = False
            in_product_manifests = False
            continue
        if current is None:
            continue
        if line.startswith("    domain: "):
            current["domain"] = strip_quotes(line.split(": ", 1)[1])
            in_contained = False
            in_product_manifests = False
        elif line.startswith("    contained_skills:"):
            in_contained = True
            in_product_manifests = False
        elif line.startswith("    product_manifests:"):
            in_product_manifests = True
            in_contained = False
        elif in_contained and line.startswith("      - "):
            contained = current["contained_skills"]
            assert isinstance(contained, list)
            contained.append(strip_quotes(line.split("- ", 1)[1]))
        elif in_product_manifests and line.startswith("      ") and ": " in line:
            key, value = line.strip().split(": ", 1)
            manifests = current["product_manifests"]
            assert isinstance(manifests, dict)
            manifests[key] = strip_quotes(value)
    if current is not None:
        entries.append(current)
    return entries


def skill_source_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for path in sorted((root / "core" / "skills").glob("*/*/SKILL.md.tera")):
        skill = path.parent.name
        domain = path.parent.parent.name
        ids.add(f"{domain}.{skill}")
    return ids


def matrix_skill_ids(root: Path) -> set[str]:
    path = root / "tests" / "runtime-smoke" / "acceptance-matrix.yaml"
    return set(re.findall(r"^\s+skill_id:\s+([a-z0-9-]+\.[a-z0-9-]+)\s*$", read(path), re.M))


def sandbox_skill_ids(root: Path, product: str) -> set[str]:
    path = root / "tests" / "sandbox" / product / "expected-skills.txt"
    return {line.strip() for line in read(path).splitlines() if line.strip()}


def codex_plugin_manifest_error(
    plugin_id: str,
    manifest_path: Path,
    contained: list[object],
    by_id: dict[str, dict[str, object]],
) -> str | None:
    try:
        rel = manifest_path.relative_to(ROOT)
    except ValueError:
        rel = manifest_path

    try:
        payload = json.loads(read(manifest_path))
    except json.JSONDecodeError as exc:
        return f"plugin {plugin_id} codex manifest is not valid JSON: {rel}: {exc}"

    actual_raw = payload.get("skills")
    if not isinstance(actual_raw, list):
        return f"plugin {plugin_id} codex manifest missing skills list: {rel}"

    expected: list[dict[str, str]] = []
    for raw_skill_id in contained:
        skill_id = str(raw_skill_id)
        entry = by_id.get(skill_id)
        if entry is None:
            return f"plugin {plugin_id} contains unknown skill {skill_id}"
        products = entry.get("products")
        if not isinstance(products, dict):
            return f"{skill_id} products must be a mapping"
        codex = products.get("codex")
        if not isinstance(codex, dict):
            return f"{skill_id} missing codex product declaration"
        name = str(codex.get("name", ""))
        source = str(entry.get("source", ""))
        expected.append({"id": name, "source": source})

    actual: list[dict[str, str]] = []
    for index, item in enumerate(actual_raw):
        if not isinstance(item, dict):
            return f"plugin {plugin_id} codex manifest skills[{index}] must be an object"
        skill_name = item.get("id")
        source = item.get("source")
        if not isinstance(skill_name, str) or not isinstance(source, str):
            return f"plugin {plugin_id} codex manifest skills[{index}] needs string id/source"
        actual.append({"id": skill_name, "source": source})

    if actual != expected:
        return (
            f"plugin {plugin_id} codex manifest skills drift: {rel} "
            f"expected={expected!r} actual={actual!r}"
        )
    return None


def validate_codex_plugin_manifest(
    plugin_id: str,
    manifest_path: Path,
    contained: list[object],
    by_id: dict[str, dict[str, object]],
) -> None:
    error = codex_plugin_manifest_error(plugin_id, manifest_path, contained, by_id)
    if error is not None:
        fail(error)


def parse_h2_sections(text: str) -> list[str]:
    headings: list[str] = []
    in_code_fence = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if line.startswith("## "):
            headings.append(line[3:].strip())
    return headings


def audit_skill_body_shape(skill_id: str, source: str) -> None:
    path = ROOT / source / "SKILL.md.tera"
    text = read(path)
    headings = parse_h2_sections(text)
    if not headings:
        fail(f"{skill_id} missing any H2 section in {source}/SKILL.md.tera")
    if headings[0] != "Contract":
        fail(
            f"{skill_id} first H2 must be `## Contract`, found `## {headings[0]}` "
            f"(see core/skills/meta/create-skill for the standard skill shape)"
        )
    last_canonical_index = -1
    last_canonical_name = "Contract"
    for heading in headings:
        if heading in CANONICAL_SECTIONS:
            position = CANONICAL_SECTIONS.index(heading)
            if position <= last_canonical_index:
                fail(
                    f"{skill_id} canonical H2 order must be "
                    f"Contract -> Entrypoint -> Workflow -> Boundary; "
                    f"found `## {heading}` after `## {last_canonical_name}`"
                )
            last_canonical_index = position
            last_canonical_name = heading


def audit_rendered_lifecycle_reference_packaging(root: Path) -> None:
    source_only_refs = re.compile(
        r"`(core/skills/(?:pr/pr-lifecycle|issue/issue-lifecycle)/README\.md)`"
    )
    packaged_lifecycle_refs = re.compile(
        r"`((?:\.\./[a-z0-9-]+/)?references/(?:pr-lifecycle|issue-lifecycle)\.md)`"
    )
    packaged_refs = [
        (
            "PR/MR lifecycle",
            root / "core" / "skills" / "pr" / "pr-lifecycle" / "README.md",
            root / "core" / "skills" / "pr" / "deliver-pr" / "references" / "pr-lifecycle.md",
            Path("plugins/pr/skills/deliver-pr/references/pr-lifecycle.md"),
            Path("plugins/pr/skills/deliver-pr/expected/references/pr-lifecycle.md"),
        ),
        (
            "issue lifecycle",
            root / "core" / "skills" / "issue" / "issue-lifecycle" / "README.md",
            root / "core" / "skills" / "issue" / "issue-follow-up" / "references" / "issue-lifecycle.md",
            Path("plugins/issue/skills/issue-follow-up/references/issue-lifecycle.md"),
            Path("plugins/issue/skills/issue-follow-up/expected/references/issue-lifecycle.md"),
        ),
    ]
    for label, canonical, source_packaged, rendered_rel, golden_rel in packaged_refs:
        if not source_packaged.is_file():
            fail(f"{label} packaged reference missing: {source_packaged.relative_to(root)}")
        if read(source_packaged) != read(canonical):
            fail(
                f"{label} packaged reference drifted from canonical source: "
                f"{source_packaged.relative_to(root)} != {canonical.relative_to(root)}"
            )
        for product in ("codex", "claude"):
            golden = root / "tests" / "golden" / product / golden_rel
            if not golden.is_file():
                fail(f"{label} golden reference missing: {golden.relative_to(root)}")
            if read(golden) != read(canonical):
                fail(
                    f"{label} golden reference drifted from canonical source: "
                    f"{golden.relative_to(root)} != {canonical.relative_to(root)}"
                )

    source_skill_bodies = sorted((root / "core" / "skills").glob("*/*/SKILL.md.tera"))
    golden_skill_bodies = [
        path
        for product in ("codex", "claude")
        for path in sorted((root / "tests" / "golden" / product / "plugins").glob("*/skills/*/expected/SKILL.md"))
    ]
    for path in source_skill_bodies + golden_skill_bodies:
        text = read(path)
        for match in source_only_refs.finditer(text):
            rel = path.relative_to(root)
            fail(
                f"{rel} references source-only lifecycle doc {match.group(1)!r}; "
                "rendered skills must point at packaged references/ files"
            )

    for product in ("codex", "claude"):
        plugins_root = root / "build" / product / "plugins"
        if not plugins_root.exists():
            continue
        for label, canonical, _source_packaged, rendered_rel, _golden_rel in packaged_refs:
            rendered = root / "build" / product / rendered_rel
            if not rendered.is_file():
                fail(f"{label} rendered reference missing: {rendered.relative_to(root)}")
            if read(rendered) != read(canonical):
                fail(
                    f"{label} rendered reference drifted from canonical source: "
                    f"{rendered.relative_to(root)} != {canonical.relative_to(root)}"
                )
        for path in sorted(plugins_root.glob("*/skills/*/SKILL.md")):
            text = read(path)
            for match in source_only_refs.finditer(text):
                rel = path.relative_to(root)
                fail(
                    f"{rel} references source-only lifecycle doc {match.group(1)!r}; "
                    "rendered skills must point at packaged references/ files"
                )
            for match in packaged_lifecycle_refs.finditer(text):
                target = (path.parent / match.group(1)).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError:
                    fail(
                        f"{path.relative_to(root)} lifecycle reference escapes repo: "
                        f"{match.group(1)!r}"
                    )
                if not target.is_file():
                    fail(
                        f"{path.relative_to(root)} lifecycle reference is not packaged: "
                        f"{match.group(1)!r}"
                    )


def shape_skill_id_from_path(path: Path) -> tuple[str, str] | None:
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if (
        len(parts) < 5
        or parts[0] != "core"
        or parts[1] != "skills"
        or parts[-1] != "SKILL.md.tera"
    ):
        return None
    domain = parts[2]
    skill = "/".join(parts[3:-1])
    return f"{domain}.{skill}", f"core/skills/{domain}/{skill}"


def validate_shape_only(raw_paths: list[str]) -> None:
    if not raw_paths:
        print("skill-governance-audit: shape OK files_checked=0")
        return
    checked = 0
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        if not path.is_file():
            # Files removed in this commit are not lintable; skip silently.
            continue
        ids = shape_skill_id_from_path(path)
        if ids is None:
            continue
        skill_id, source = ids
        audit_skill_body_shape(skill_id, source)
        checked += 1
    print(f"skill-governance-audit: shape OK files_checked={checked}")


# Folds a SKILL.md.tera frontmatter `description` back into a single string for
# length measurement. Assumes the repo's actual frontmatter shape: a `name`
# then `description` key, inline or YAML block scalars only, and no blank line
# inside the value. A `\n`-join matches YAML folded-scalar semantics under those
# conditions. If a future renderer emits a different shape, tighten this parser
# rather than trusting its measurement.
def skill_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if match is None:
        return ""
    lines = match.group(1).split("\n")
    for index, line in enumerate(lines):
        head = re.match(r"^description:\s*(.*)$", line)
        if head is None:
            continue
        parts: list[str] = []
        inline = head.group(1).strip()
        # Skip a block-scalar header (`>`, `|`, with optional indentation /
        # chomping indicators like `|-`, `>+`, `|2-`); anything else on the
        # `description:` line is real inline content.
        if inline and not re.match(r"^[>|][1-9+-]*$", inline):
            parts.append(strip_quotes(inline))
        if not inline:
            for cont in lines[index + 1 :]:
                if not cont.strip():
                    continue
                if re.match(r"^[A-Za-z_]", cont):  # next top-level key
                    break
                fail(
                    f"{path}: frontmatter description must be inline or use "
                    "a YAML block scalar marker (`>` or `|`)"
                )
        for cont in lines[index + 1 :]:
            if re.match(r"^[A-Za-z_]", cont):  # next top-level key
                break
            if cont.strip():
                parts.append(cont.strip())
        return " ".join(parts).strip()
    return ""


# Returns (longest, over_120, over_220). Only `> DESCRIPTION_MAX_CHARS` (240) is
# a hard fail; 120 / 220 are the README's advisory authoring targets, surfaced
# as non-blocking counts so drift toward the ceiling stays visible.
def validate_descriptions(root: Path) -> tuple[int, int, int]:
    longest = 0
    over_120 = 0
    over_220 = 0
    violations: list[str] = []
    for path in sorted((root / "core" / "skills").glob("*/*/SKILL.md.tera")):
        skill_id = f"{path.parent.parent.name}.{path.parent.name}"
        desc = skill_description(path)
        if not desc:
            fail(f"{skill_id} missing frontmatter description")
        length = len(desc)
        longest = max(longest, length)
        if length > 120:
            over_120 += 1
        if length > 220:
            over_220 += 1
        if length > DESCRIPTION_MAX_CHARS:
            violations.append(f"{skill_id} ({length} chars)")
    if violations:
        fail(
            f"skill description exceeds {DESCRIPTION_MAX_CHARS} chars "
            "(see core/skills/README.md 'Skill Description Rubric'): "
            + "; ".join(violations)
        )
    return longest, over_120, over_220


def validate_description_limit_fixture() -> None:
    # Negative coverage for validate_descriptions(): a synthetic catalog drives
    # both hard-fail branches (over the ceiling and a missing description), the
    # exact ceiling boundary (240 passes, 241 fails), and the happy path. Each
    # run captures the fail() message so the assertion pins WHICH branch fired,
    # not just the exit sign.
    import io

    def run(frontmatter: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory(prefix="desc-limit-") as tmp:
            skill_dir = Path(tmp) / "core" / "skills" / "fixture" / "sample"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md.tera").write_text(
                f"---\nname: sample\n{frontmatter}---\n\n# Sample\n",
                encoding="utf-8",
            )
            captured = io.StringIO()
            saved_stderr = sys.stderr
            sys.stderr = captured  # capture the expected fail() message
            try:
                validate_descriptions(Path(tmp))
            except SystemExit as exc:
                return int(exc.code or 0), captured.getvalue()
            finally:
                sys.stderr = saved_stderr
        return 0, captured.getvalue()

    def plain_continuation(text: str) -> str:
        return "description:\n  " + text + "\n"

    def block(text: str) -> str:
        return "description: >\n  " + text + "\n"

    invalid_yaml_code, invalid_yaml_msg = run(plain_continuation("Invalid YAML plain continuation."))
    if invalid_yaml_code == 0 or "YAML block scalar marker" not in invalid_yaml_msg:
        fail("description-limit fixture: plain continuation description did not hard-fail")

    # Boundary inputs are literal 240 / 241 so they pin the documented ceiling
    # itself: a 241-char input that stops failing (ceiling widened) trips this,
    # as does a 240-char input that starts failing (`>` regressed to `>=`). If
    # the rubric ceiling ever moves, update these literals deliberately.
    over_code, over_msg = run(block("X" * 241))
    if over_code == 0 or "exceeds 240 chars" not in over_msg:
        fail("description-limit fixture: a 241-char description did not hard-fail with the over-limit message")

    boundary_code, _ = run(block("X" * 240))
    if boundary_code != 0:
        fail("description-limit fixture: a 240-char description (at the ceiling) unexpectedly failed")

    empty_code, empty_msg = run(block(""))
    if empty_code == 0 or "missing frontmatter description" not in empty_msg:
        fail("description-limit fixture: an empty description did not hard-fail with the missing-description message")

    missing_code, missing_msg = run("")
    if missing_code == 0 or "missing frontmatter description" not in missing_msg:
        fail("description-limit fixture: a missing description key did not hard-fail with the missing-description message")

    valid_code, _ = run(block("A short valid description."))
    if valid_code != 0:
        fail("description-limit fixture: a valid description unexpectedly failed")

    print(
        "skill-governance-audit: description-limit fixture OK "
        f"ceiling={DESCRIPTION_MAX_CHARS} over_exit={over_code} "
        f"boundary_exit={boundary_code} missing_exit={missing_code}"
    )


def validate_exposure_contract_fixture() -> None:
    def copy_contract_tree(destination: Path) -> None:
        (destination / "manifests").mkdir(parents=True)
        (destination / "core" / "docs" / "schemas").mkdir(parents=True)
        (destination / MIGRATION_PROGRESS_PATH.parent).mkdir(parents=True)
        for name in ("skills.yaml", "skill-dispositions.yaml"):
            shutil.copy2(ROOT / "manifests" / name, destination / "manifests" / name)
        for name in ("skills.schema.json", "skill-dispositions.schema.json"):
            shutil.copy2(
                ROOT / "core" / "docs" / "schemas" / name,
                destination / "core" / "docs" / "schemas" / name,
            )
        shutil.copy2(
            ROOT / MIGRATION_PROGRESS_PATH,
            destination / MIGRATION_PROGRESS_PATH,
        )

    def write_positive_retained(root: Path) -> str | None:
        skills_path = root / "manifests" / "skills.yaml"
        dispositions_path = root / "manifests" / "skill-dispositions.yaml"
        progress_path = root / MIGRATION_PROGRESS_PATH
        before_pending = [
            str(item)
            for item in parse_skill_migration(skills_path)["pending_disposition"]
        ]
        if not before_pending:
            return None

        promoted_id = before_pending[0]
        skills = read(skills_path).replace(f"    - {promoted_id}\n", "", 1)
        marker = f"  - id: {promoted_id}\n"
        before, after = skills.split(marker, 1)
        semantics = """    invocation:
      role: workflow
      intents: [fixture-transition]
      example_request: "Exercise the migration transition fixture"
      admission_rationale: "Exercises one deterministic pending-to-reviewed transition."
    exposure:
      profile: default
"""
        after = after.replace("    products:\n", semantics + "    products:\n", 1)
        skills_path.write_text(before + marker + after, encoding="utf-8")

        reviewed = f"""  - id: {promoted_id}
    status: reviewed
    example_request: "Exercise the migration transition fixture"
    user_outcome: yes
    destination: entrypoint
    parent_intents: [fixture-transition]
    current_clis: []
    current_hooks: []
    enforcement_point: "Migration fixture admission governance."
    migration_path: "Promote one pending fixture row."
    compatibility_required: false
    live_cleanup_required: false
    rationale: "Exercises one deterministic pending-to-reviewed transition."
"""
        chunks = re.split(
            r"(?=^  - id: )",
            read(dispositions_path),
            flags=re.M,
        )
        for index, chunk in enumerate(chunks):
            if chunk.startswith(marker):
                if "    status: pending\n" not in chunk:
                    fail(
                        "exposure-contract fixture selected a non-pending row: "
                        f"{promoted_id}"
                    )
                chunks[index] = reviewed
                break
        else:
            fail(
                "exposure-contract fixture could not find pending row: "
                f"{promoted_id}"
            )
        dispositions_path.write_text("".join(chunks), encoding="utf-8")

        progress = load_migration_progress(root)
        rows = parse_dispositions(dispositions_path)["rows"]
        assert isinstance(rows, list)
        progress["reviewed_ids"] = [
            str(row["id"]) for row in rows if row.get("status") == "reviewed"
        ]
        progress["pending_ids"] = [
            str(row["id"]) for row in rows if row.get("status") == "pending"
        ]
        progress_path.write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")

        after_pending = [
            str(item)
            for item in parse_skill_migration(skills_path)["pending_disposition"]
        ]
        unrelated_pending = [
            skill_id for skill_id in before_pending if skill_id != promoted_id
        ]
        if after_pending != unrelated_pending:
            fail(
                "exposure-contract fixture did not preserve unrelated pending rows"
            )
        return promoted_id

    def write_replacement_retained(root: Path) -> None:
        skills_path = root / "manifests" / "skills.yaml"
        dispositions_path = root / "manifests" / "skill-dispositions.yaml"
        replacement_id = "reporting.project-retro"
        skills = read(skills_path).replace(f"    - {replacement_id}\n", "", 1)
        marker = f"  - id: {replacement_id}\n"
        before, after = skills.split(marker, 1)
        semantics = """    invocation:
      role: workflow
      intents: [project-retro]
      example_request: "Prepare a project implementation retrospective"
      admission_rationale: "Produces a distinct user-requested report."
    exposure:
      profile: default
"""
        after = after.replace("    products:\n", semantics + "    products:\n", 1)
        skills_path.write_text(before + marker + after, encoding="utf-8")

        reviewed = """  - id: reporting.project-retro
    status: reviewed
    example_request: "Prepare a project implementation retrospective"
    user_outcome: yes
    destination: entrypoint
    parent_intents: [project-retro]
    current_clis: [repo-retro]
    current_hooks: []
    enforcement_point: "Skill admission and product render governance."
    migration_path: "Retain the existing entrypoint."
    compatibility_required: false
    live_cleanup_required: false
    rationale: "Produces a distinct user-requested report."
"""
        dispositions = read(dispositions_path).replace(
            "  - id: reporting.project-retro\n    status: pending\n",
            reviewed,
            1,
        )
        dispositions_path.write_text(dispositions, encoding="utf-8")

    def write_reviewed_without_active_metadata(root: Path) -> None:
        skills_path = root / "manifests" / "skills.yaml"
        dispositions_path = root / "manifests" / "skill-dispositions.yaml"
        disposition_ids = set(
            re.findall(
                rf"^  - id: ({SKILL_ID_RE})$",
                read(dispositions_path),
                flags=re.M,
            )
        )
        active_id = next(
            (
                str(entry["id"])
                for entry in parse_skills(skills_path)
                if str(entry["id"]) in disposition_ids
            ),
            None,
        )
        if active_id is None:
            fail("exposure-contract fixture has no active baseline skill")

        skill_chunks = re.split(
            r"(?=^  - id: )",
            read(skills_path),
            flags=re.M,
        )
        active_marker = f"  - id: {active_id}\n"
        rewritten_skill = False
        for index, chunk in enumerate(skill_chunks):
            if not chunk.startswith(active_marker):
                continue
            kept: list[str] = []
            skipping_semantics = False
            for line in chunk.splitlines(keepends=True):
                if line.startswith("    invocation:") or line.startswith(
                    "    exposure:"
                ):
                    skipping_semantics = True
                    continue
                if skipping_semantics and line.startswith("      "):
                    continue
                skipping_semantics = False
                kept.append(line)
            skill_chunks[index] = "".join(kept)
            rewritten_skill = True
            break
        if not rewritten_skill:
            fail(
                "exposure-contract fixture could not find active skill "
                f"{active_id}"
            )

        skills = "".join(skill_chunks).replace(
            f"    - {active_id}\n",
            "",
            1,
        )
        skills_path.write_text(skills, encoding="utf-8")

        reviewed = f"""  - id: {active_id}
    status: reviewed
    example_request: "Run the fixture user outcome"
    user_outcome: yes
    destination: entrypoint
    parent_intents: [fixture]
    current_clis: []
    current_hooks: []
    enforcement_point: "Fixture admission governance."
    migration_path: "Retain the fixture entrypoint."
    compatibility_required: false
    live_cleanup_required: false
    rationale: "Represents a direct fixture user outcome."
"""
        disposition_chunks = re.split(
            r"(?=^  - id: )",
            read(dispositions_path),
            flags=re.M,
        )
        rewritten_disposition = False
        for index, chunk in enumerate(disposition_chunks):
            if chunk.startswith(active_marker):
                disposition_chunks[index] = reviewed
                rewritten_disposition = True
                break
        if not rewritten_disposition:
            fail(
                "exposure-contract fixture could not find disposition row "
                f"{active_id}"
            )
        dispositions_path.write_text(
            "".join(disposition_chunks),
            encoding="utf-8",
        )

    def expect_error(root: Path, needle: str) -> None:
        errors = exposure_contract_errors(root)
        if not any(needle in error for error in errors):
            fail(f"exposure-contract fixture expected {needle!r}, got {errors}")

    with tempfile.TemporaryDirectory(prefix="skill-exposure-contract-") as tmp:
        base = Path(tmp) / "base"
        copy_contract_tree(base)
        if exposure_contract_errors(base):
            fail("exposure-contract fixture base catalog is not valid")

        retained = Path(tmp) / "retained"
        shutil.copytree(base, retained)
        before_pending = [
            str(item)
            for item in parse_skill_migration(
                retained / "manifests" / "skills.yaml"
            )["pending_disposition"]
        ]
        promoted_id = write_positive_retained(retained)
        if before_pending and promoted_id != before_pending[0]:
            fail("exposure-contract fixture did not promote a pending row")
        retained_errors = exposure_contract_errors(retained)
        if retained_errors:
            fail(f"exposure-contract fixture valid retained entry failed: {retained_errors}")

        zero_pending = Path(tmp) / "zero-pending"
        shutil.copytree(base, zero_pending)
        zero_skills_path = zero_pending / "manifests" / "skills.yaml"
        zero_skills = read(zero_skills_path)
        for pending_id in before_pending:
            zero_skills = zero_skills.replace(f"    - {pending_id}\n", "", 1)
        zero_skills_path.write_text(zero_skills, encoding="utf-8")
        if write_positive_retained(zero_pending) is not None:
            fail("exposure-contract fixture zero-pending state must be a no-op")

        block_lists = Path(tmp) / "block-lists"
        shutil.copytree(retained, block_lists)
        dispositions_path = block_lists / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path)
            .replace("    parent_intents: [daily-brief]\n", "    parent_intents:\n      - daily-brief\n", 1)
            .replace("    current_clis: [agent-out]\n", "    current_clis:\n      - agent-out\n", 1),
            encoding="utf-8",
        )
        block_list_errors = exposure_contract_errors(block_lists)
        if block_list_errors:
            fail(f"exposure-contract fixture valid block lists failed: {block_list_errors}")

        invalid_user_outcome = Path(tmp) / "invalid-user-outcome"
        shutil.copytree(retained, invalid_user_outcome)
        dispositions_path = invalid_user_outcome / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace("    user_outcome: yes\n", "    user_outcome: maybe\n", 1),
            encoding="utf-8",
        )
        expect_error(invalid_user_outcome, "user_outcome is invalid")

        invalid_boolean = Path(tmp) / "invalid-boolean"
        shutil.copytree(retained, invalid_boolean)
        dispositions_path = invalid_boolean / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace(
                "    compatibility_required: false\n",
                '    compatibility_required: "false"\n',
                1,
            ),
            encoding="utf-8",
        )
        expect_error(invalid_boolean, "compatibility_required must be boolean")

        duplicate_array = Path(tmp) / "duplicate-array"
        shutil.copytree(retained, duplicate_array)
        dispositions_path = duplicate_array / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace(
                "    current_clis: [agent-out]\n",
                "    current_clis: [agent-out, agent-out]\n",
                1,
            ),
            encoding="utf-8",
        )
        expect_error(duplicate_array, "current_clis must contain unique items")

        empty_parent_intents = Path(tmp) / "empty-parent-intents"
        shutil.copytree(retained, empty_parent_intents)
        dispositions_path = empty_parent_intents / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace(
                "    parent_intents: [daily-brief]\n",
                "    parent_intents: []\n",
                1,
            ),
            encoding="utf-8",
        )
        expect_error(empty_parent_intents, "parent_intents must not be empty")

        unknown_field = Path(tmp) / "unknown-field"
        shutil.copytree(retained, unknown_field)
        dispositions_path = unknown_field / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace(
                "    status: reviewed\n",
                "    status: reviewed\n    surprise_field: true\n",
                1,
            ),
            encoding="utf-8",
        )
        expect_error(unknown_field, "unknown disposition fields")

        missing_metadata = Path(tmp) / "missing-metadata"
        shutil.copytree(base, missing_metadata)
        write_reviewed_without_active_metadata(missing_metadata)
        expect_error(missing_metadata, "requires invocation and exposure metadata")

        metadata_mismatch = Path(tmp) / "metadata-mismatch"
        shutil.copytree(retained, metadata_mismatch)
        dispositions_path = metadata_mismatch / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace(
                '    rationale: "Produces a distinct report directly requested by a user."\n',
                '    rationale: "Fixture metadata mismatch."\n',
                1,
            ),
            encoding="utf-8",
        )
        expect_error(
            metadata_mismatch,
            "reviewed metadata mismatch: disposition.rationale != invocation.admission_rationale",
        )

        advanced = Path(tmp) / "advanced"
        shutil.copytree(retained, advanced)
        skills_path = advanced / "manifests" / "skills.yaml"
        skills_path.write_text(read(skills_path).replace("role: workflow", "role: advanced", 1), encoding="utf-8")
        expect_error(advanced, "advanced role has no supported opt-in exposure")

        opt_in = Path(tmp) / "opt-in"
        shutil.copytree(retained, opt_in)
        skills_path = opt_in / "manifests" / "skills.yaml"
        skills_path.write_text(read(skills_path).replace("profile: default", "profile: opt-in", 1), encoding="utf-8")
        expect_error(opt_in, "exposure profile must be default")

        compatibility = Path(tmp) / "compatibility"
        shutil.copytree(retained, compatibility)
        skills_path = compatibility / "manifests" / "skills.yaml"
        skills_path.write_text(read(skills_path).replace("role: workflow", "role: compatibility", 1), encoding="utf-8")
        expect_error(compatibility, "compatibility replacement must name another reviewed active skill")

        bounded_compatibility = Path(tmp) / "bounded-compatibility"
        shutil.copytree(retained, bounded_compatibility)
        write_replacement_retained(bounded_compatibility)
        skills_path = bounded_compatibility / "manifests" / "skills.yaml"
        skills = read(skills_path).replace("role: workflow", "role: compatibility", 1)
        skills = skills.replace(
            "      profile: default\n",
            """      profile: default
      replacement: reporting.project-retro
      retire_after: "2026-12-31"
""",
            1,
        )
        skills_path.write_text(skills, encoding="utf-8")
        bounded_errors = exposure_contract_errors(bounded_compatibility)
        if bounded_errors:
            fail(f"exposure-contract fixture valid compatibility failed: {bounded_errors}")

        invalid_date = Path(tmp) / "invalid-date"
        shutil.copytree(bounded_compatibility, invalid_date)
        skills_path = invalid_date / "manifests" / "skills.yaml"
        skills_path.write_text(
            read(skills_path).replace("2026-12-31", "2026-99-99", 1),
            encoding="utf-8",
        )
        expect_error(invalid_date, "compatibility retire_after must be YYYY-MM-DD")

        growth = Path(tmp) / "growth"
        shutil.copytree(base, growth)
        skills_path = growth / "manifests" / "skills.yaml"
        skills_path.write_text(
            read(skills_path).replace(
                "  pending_disposition: []\n",
                "  pending_disposition:\n    - fixture.new-skill\n",
                1,
            ),
            encoding="utf-8",
        )
        expect_error(growth, "pending disposition ids are not active")

        replaced_baseline = Path(tmp) / "replaced-baseline"
        shutil.copytree(base, replaced_baseline)
        dispositions_path = replaced_baseline / "manifests" / "skill-dispositions.yaml"
        dispositions_path.write_text(
            read(dispositions_path).replace(
                "  - id: reporting.daily-brief\n",
                "  - id: fixture.replacement\n",
                1,
            ),
            encoding="utf-8",
        )
        expect_error(replaced_baseline, "ordered disposition ids do not match the frozen baseline")

    progress = load_migration_progress(ROOT)
    reviewed_count = len(progress["reviewed_ids"])
    pending_count = len(progress["pending_ids"])
    print(
        "skill-governance-audit: exposure-contract fixture OK "
        f"reviewed={reviewed_count} pending={pending_count} retained=true "
        "advanced=false opt_in=false compatibility_bounded=true schema_types=true "
        "block_lists=true metadata_mismatch=false growth=false"
    )


def validate_repo() -> None:
    validate_exposure_contract(ROOT)
    validate_codex_reviewer_profiles(ROOT)
    skills = parse_skills(ROOT / "manifests" / "skills.yaml")
    plugins = parse_plugins(ROOT / "manifests" / "plugins.yaml")
    by_id = {str(entry["id"]): entry for entry in skills}
    source_ids = skill_source_ids(ROOT)

    if set(by_id) != source_ids:
        missing = sorted(source_ids - set(by_id))
        stale = sorted(set(by_id) - source_ids)
        fail(f"source/manifest mismatch missing={missing} stale={stale}")

    desc_max, desc_over_120, desc_over_220 = validate_descriptions(ROOT)

    contained_counts: dict[str, int] = {}
    plugin_domains: dict[str, str] = {}
    for plugin in plugins:
        plugin_id = str(plugin["id"])
        plugin_domains[plugin_id] = str(plugin["domain"])
        manifests = plugin["product_manifests"]
        assert isinstance(manifests, dict)
        contained = plugin["contained_skills"]
        assert isinstance(contained, list)
        for product, manifest in manifests.items():
            if not (ROOT / str(manifest)).is_file():
                fail(f"plugin {plugin_id} missing {product} manifest: {manifest}")
        codex_manifest = manifests.get("codex")
        if codex_manifest is not None:
            validate_codex_plugin_manifest(plugin_id, ROOT / str(codex_manifest), contained, by_id)
        for skill_id in contained:
            contained_counts[str(skill_id)] = contained_counts.get(str(skill_id), 0) + 1

    matrix_ids = matrix_skill_ids(ROOT)
    codex_ids = sandbox_skill_ids(ROOT, "codex")
    claude_ids = sandbox_skill_ids(ROOT, "claude")
    semver = re.compile(r"^>=\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?$")
    lifecycle_ids = {
        "meta.create-skill",
        "meta.create-project-skill",
        "meta.remove-skill",
        "meta.remove-project-skill",
    }
    repo_lifecycle_ids = {"meta.create-skill", "meta.remove-skill"}
    project_lifecycle_ids = {
        "meta.create-project-skill",
        "meta.remove-project-skill",
    }

    for skill_id, entry in sorted(by_id.items()):
        domain, skill = skill_id.split(".", 1)
        if entry.get("domain") != domain:
            fail(f"{skill_id} domain does not match id")
        source = str(entry.get("source", ""))
        expected_source = f"core/skills/{domain}/{skill}"
        if source != expected_source:
            fail(f"{skill_id} source={source!r} expected={expected_source!r}")
        if not (ROOT / source / "SKILL.md.tera").is_file():
            fail(f"{skill_id} missing source SKILL.md.tera")
        audit_skill_body_shape(skill_id, source)
        if contained_counts.get(skill_id, 0) != 1:
            fail(f"{skill_id} plugin containment count={contained_counts.get(skill_id, 0)}")
        if skill_id not in matrix_ids:
            fail(f"{skill_id} missing runtime-smoke acceptance matrix row")
        if skill_id not in codex_ids:
            fail(f"{skill_id} missing codex sandbox expected skill")
        if skill_id not in claude_ids:
            fail(f"{skill_id} missing claude sandbox expected skill")
        products = entry["products"]
        assert isinstance(products, dict)
        for product, product_data in products.items():
            assert isinstance(product_data, dict)
            render_to = str(product_data.get("render_to", ""))
            expected_render = f"plugins/{domain}/skills/{skill}/SKILL.md"
            if render_to != expected_render:
                fail(f"{skill_id} {product} render_to={render_to!r} expected={expected_render!r}")

        required = entry["required_clis"]
        assert isinstance(required, dict)
        for cli, floor in required.items():
            if "<TBD" in floor or not semver.match(floor):
                fail(f"{skill_id} required_clis {cli} has invalid floor {floor!r}")

        if skill_id in repo_lifecycle_ids:
            body = read(ROOT / source / "SKILL.md.tera")
            for needle in ("core/skills", "manifests/skills.yaml", "manifests/plugins.yaml", "agent-runtime"):
                if needle not in body:
                    fail(f"{skill_id} missing lifecycle contract phrase: {needle}")
        if skill_id in project_lifecycle_ids:
            body = read(ROOT / source / "SKILL.md.tera")
            for needle in (".agents/skills", ".agents/scripts", "git rev-parse --show-toplevel"):
                if needle not in body:
                    fail(f"{skill_id} missing project lifecycle contract phrase: {needle}")

    reminders = json.loads(read(ROOT / "core" / "hooks" / "shared" / "skill-usage-reminder.skills.json"))
    retired = set(
        json.loads(read(ROOT / "manifests" / "retired-skill-ids.json"))["skills"]
    )
    active_short_ids = {skill_id.split(".", 1)[1] for skill_id in by_id}
    explicit_external = {
        "browser-qa",
        "find-and-fix-bugs",
        "fix-bug-pr",
        "gh-fix-ci",
        "release-workflow",
        "semgrep-find-and-fix",
    }
    for entry in reminders:
        reminder_id = str(entry.get("skill", ""))
        qualified_matches = {
            skill_id
            for skill_id in retired
            if skill_id == reminder_id or skill_id.endswith(f".{reminder_id}")
        }
        if qualified_matches:
            fail(
                "skill-usage reminder exposes retired skill id "
                f"{reminder_id}: {sorted(qualified_matches)}"
            )
        if reminder_id not in active_short_ids:
            if entry.get("surface") != "external" or reminder_id not in explicit_external:
                fail(f"skill-usage reminder has ungoverned non-active id: {reminder_id}")

    retired_short_ids = {skill_id.split(".", 1)[1] for skill_id in retired}
    for agent_path in sorted((ROOT / "core" / "agents").glob("**/AGENT.md.tera")):
        body = read(agent_path)
        stale_refs = sorted(
            retired_id for retired_id in retired_short_ids if retired_id in body
        )
        if stale_refs:
            fail(
                "active agent template references retired skills "
                f"{agent_path.relative_to(ROOT)}: {stale_refs}"
            )
    exact = {
        entry.get("skill")
        for entry in reminders
        if entry.get("tier") == "exact-only"
    }
    expected_exact = {
        "create-skill",
        "create-project-skill",
        "remove-skill",
        "remove-project-skill",
    }
    if not expected_exact.issubset(exact):
        fail(f"missing lifecycle exact-only reminder entries: {sorted(expected_exact - exact)}")
    if "skill-governance" in exact:
        fail("skill-governance is a repo governance tool, not a user-facing skill")

    audit_rendered_lifecycle_reference_packaging(ROOT)

    count = validate_counts(ROOT)
    print(
        "skill-governance-audit: repo OK "
        f"skills={len(skills)} plugins={len(plugins)} lifecycle={len(lifecycle_ids)} "
        f"count_targets={len(COUNT_TARGETS)} active_count={count} "
        f"desc_max={desc_max}/{DESCRIPTION_MAX_CHARS} "
        f"desc_over120={desc_over_120} desc_over220={desc_over_220}"
    )


def validate_create_fixture() -> None:
    fixture = ROOT / "tests" / "runtime-smoke" / "fixtures" / "skill-lifecycle" / "create-skill"
    expected = [
        "core/skills/fixture/sample-prose/SKILL.md.tera",
        "manifests/skills.yaml",
        "manifests/plugins.yaml",
        "tests/runtime-smoke/acceptance-matrix.yaml",
        "tests/sandbox/codex/expected-skills.txt",
        "tests/sandbox/claude/expected-skills.txt",
    ]
    for rel in expected:
        if not (fixture / rel).is_file():
            fail(f"create fixture missing {rel}")
    skill_id = "fixture.sample-prose"
    entries = parse_skills(fixture / "manifests" / "skills.yaml")
    if skill_id not in {str(entry["id"]) for entry in entries}:
        fail("create fixture missing skill manifest entry")
    entry = next(item for item in entries if item["id"] == skill_id)
    if not isinstance(entry.get("invocation"), dict) or not isinstance(entry.get("exposure"), dict):
        fail("create fixture missing v2 invocation/exposure admission")
    plugins = parse_plugins(fixture / "manifests" / "plugins.yaml")
    if not any(skill_id in plugin.get("contained_skills", []) for plugin in plugins):
        fail("create fixture missing plugin containment")
    if skill_id not in matrix_skill_ids(fixture):
        fail("create fixture missing acceptance matrix row")
    for product in ("codex", "claude"):
        if skill_id not in sandbox_skill_ids(fixture, product):
            fail(f"create fixture missing {product} sandbox expected skill")
    print("skill-governance-audit: create fixture OK skill=fixture.sample-prose")


def validate_remove_fixture() -> None:
    fixture = ROOT / "tests" / "runtime-smoke" / "fixtures" / "skill-lifecycle" / "remove-skill"
    expected_classes = {
        "source",
        "skills-manifest",
        "plugin-containment",
        "product-render",
        "golden",
        "sandbox",
        "runtime-smoke",
        "reminder",
        "maintained-doc",
        "historical-doc-retained",
    }
    dry_run = read(fixture / "expected-dry-run.txt")
    present = {
        line.split(":", 1)[0].removeprefix("- ").strip()
        for line in dry_run.splitlines()
        if line.startswith("- ")
    }
    missing = sorted(expected_classes - present)
    if missing:
        fail(f"remove fixture missing dry-run classes: {missing}")
    for rel in [
        "core/skills/fixture/removable-skill/SKILL.md.tera",
        "manifests/skills.yaml",
        "manifests/plugins.yaml",
        "targets/codex/plugins/fixture/.codex-plugin/plugin.json",
        "targets/claude/plugins/fixture/.claude-plugin/plugin.json",
        "tests/golden/codex/plugins/fixture/skills/removable-skill/SKILL.md",
        "tests/golden/claude/plugins/fixture/skills/removable-skill/SKILL.md",
        "tests/runtime-smoke/acceptance-matrix.yaml",
        "tests/sandbox/codex/expected-skills.txt",
        "tests/sandbox/claude/expected-skills.txt",
        "core/hooks/shared/skill-usage-reminder.skills.json",
        "docs/source/removable-skill.md",
        "docs/plans/removable-skill-history.md",
    ]:
        if not (fixture / rel).is_file():
            fail(f"remove fixture missing {rel}")
    entries = parse_skills(fixture / "manifests" / "skills.yaml")
    entry = next((item for item in entries if item["id"] == "fixture.removable-skill"), None)
    if entry is None or not isinstance(entry.get("invocation"), dict) or not isinstance(entry.get("exposure"), dict):
        fail("remove fixture missing v2 invocation/exposure admission")
    print("skill-governance-audit: remove fixture OK classes=10 retained_history=true")


def validate_create_project_fixture() -> None:
    fixture = ROOT / "tests" / "runtime-smoke" / "fixtures" / "skill-lifecycle" / "create-project-skill"
    helper = ROOT / "core" / "skills" / "meta" / "create-project-skill" / "scripts" / "create-project-skill.sh"
    if not helper.is_file() or not os.access(helper, os.X_OK):
        fail("create-project helper missing or not executable")
    expected = [
        ".agents/skills/project-sample-skill/SKILL.md",
        ".agents/skills/project-sample-skill/scripts/project-sample-skill.sh",
        ".agents/scripts/project-sample-skill.sh",
        ".claude/skills",
        ".gitignore",
        "expected-created-paths.txt",
    ]
    for rel in expected:
        path = fixture / rel
        if rel == ".claude/skills":
            if not path.is_symlink() or os.readlink(path) != "../.agents/skills":
                fail("create-project fixture missing .claude/skills bridge")
        elif not path.is_file():
            fail(f"create-project fixture missing {rel}")
    body = read(fixture / ".agents" / "skills" / "project-sample-skill" / "SKILL.md")
    for needle in ("name: project-sample-skill", "## Contract", "## Workflow"):
        if needle not in body:
            fail(f"create-project fixture SKILL.md missing {needle!r}")
    created = {
        line.strip()
        for line in read(fixture / "expected-created-paths.txt").splitlines()
        if line.strip()
    }
    for rel in expected[:-1]:
        if rel not in created:
            fail(f"create-project fixture expected-created-paths missing {rel}")
    if ".agents/scripts/pre-pr.sh" in created or (fixture / ".agents" / "scripts" / "pre-pr.sh").exists():
        fail("create-project fixture must not create pre-pr by default")
    print("skill-governance-audit: create-project fixture OK skill=project-sample-skill")


def validate_remove_project_fixture() -> None:
    fixture = ROOT / "tests" / "runtime-smoke" / "fixtures" / "skill-lifecycle" / "remove-project-skill"
    expected_classes = {
        "project-skill-source",
        "skill-owned-script",
        "project-command-wrapper",
        "maintained-doc",
        "historical-doc-retained",
    }
    dry_run = read(fixture / "expected-dry-run.txt")
    present = {
        line.split(":", 1)[0].removeprefix("- ").strip()
        for line in dry_run.splitlines()
        if line.startswith("- ")
    }
    missing = sorted(expected_classes - present)
    if missing:
        fail(f"remove-project fixture missing dry-run classes: {missing}")
    for rel in [
        ".agents/skills/removable-project-skill/SKILL.md",
        ".agents/skills/removable-project-skill/scripts/removable-project-skill.sh",
        ".agents/scripts/removable-project-skill.sh",
        "docs/source/removable-project-skill.md",
        "docs/plans/removable-project-skill-history.md",
    ]:
        if not (fixture / rel).is_file():
            fail(f"remove-project fixture missing {rel}")
    print("skill-governance-audit: remove-project fixture OK classes=5 retained_history=true")


def validate_count_refresh_fixture() -> None:
    fixture = ROOT / "tests" / "runtime-smoke" / "fixtures" / "skill-lifecycle" / "count-refresh"
    expected_root = fixture / "expected"
    history_rel = Path("docs/plans/stale-skill-count-history.md")

    with tempfile.TemporaryDirectory(prefix="skill-count-refresh-") as tmp:
        work_root = Path(tmp) / "fixture"
        shutil.copytree(fixture, work_root)

        history_path = work_root / history_rel
        stale_claim = f"66-to-{active_skill_count(work_root) - 1}-skill"
        history_path.write_text(
            read(history_path) + f"\nHistorical endpoint claim: {stale_claim}.\n",
            encoding="utf-8",
        )
        history_before = read(history_path)
        maintained_claim_path = work_root / "docs" / "source" / "convergence.md"
        maintained_claim_path.write_text(
            f"Maintained endpoint claim: {stale_claim}.\n",
            encoding="utf-8",
        )
        generated_claim_path = work_root / "build" / "shared" / "SUPPORT_MATRIX.md"
        generated_claim_path.parent.mkdir(parents=True, exist_ok=True)
        generated_claim_path.write_text(
            f"Generated endpoint claim: {stale_claim}.\n",
            encoding="utf-8",
        )
        stale_claims = stale_endpoint_count_claims(work_root)
        expected_claim = f"docs/source/convergence.md:1: {stale_claim}"
        if stale_claims != [expected_claim]:
            fail(
                "count-refresh fixture did not isolate the maintained stale claim: "
                + repr(stale_claims)
            )
        maintained_claim_path.write_text(
            "Maintained endpoint claim: 66-to-current-skill.\n",
            encoding="utf-8",
        )
        if stale_endpoint_count_claims(work_root):
            fail("count-refresh fixture retained a stale exact endpoint claim")

        _, drift = apply_count_targets(work_root, update=False)
        if not drift:
            fail("count-refresh fixture did not start with stale maintained counts")

        apply_count_targets(work_root, update=True)
        _, remaining = apply_count_targets(work_root, update=False)
        if remaining:
            fail("count-refresh fixture still has drift after update: " + "; ".join(remaining))

        for rel in [
            Path("docs/source/harness-shape-codex.md"),
            Path("tests/runtime-smoke/expected/install-summary.json"),
            Path("tests/runtime-smoke/product/expected/product-summary.json"),
        ]:
            actual = read(work_root / rel)
            expected = read(expected_root / rel)
            if actual != expected:
                fail(f"count-refresh fixture mismatch after update: {rel}")

        if read(work_root / history_rel) != history_before:
            fail("count-refresh fixture rewrote historical docs/plans content")

    print(
        "skill-governance-audit: count-refresh fixture OK "
        f"updated_targets={len(COUNT_TARGETS)} historical_docs_retained=true "
        "stale_endpoint_claim_guard=true"
    )


def validate_codex_plugin_fixture() -> None:
    by_id = {
        "meta.sync-runtime-surfaces": {
            "source": "core/skills/meta/sync-runtime-surfaces",
            "products": {
                "codex": {
                    "name": "sync-runtime-surfaces",
                    "render_to": "plugins/meta/skills/sync-runtime-surfaces/SKILL.md",
                },
                "claude": {
                    "name": "sync-runtime-surfaces",
                    "render_to": "plugins/meta/skills/sync-runtime-surfaces/SKILL.md",
                },
            },
        }
    }
    contained = ["meta.sync-runtime-surfaces"]
    with tempfile.TemporaryDirectory(prefix="codex-plugin-skills-") as tmp:
        manifest = Path(tmp) / "plugin.json"
        manifest.write_text(
            json.dumps(
                {
                    "name": "meta",
                    "version": "0.1.0",
                    "skills": [
                        {
                            "id": "sync-runtime-skills",
                            "source": "core/skills/meta/sync-runtime-skills",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        stale = codex_plugin_manifest_error("meta", manifest, contained, by_id)
        if stale is None or "skills drift" not in stale:
            fail("codex-plugin fixture did not detect stale id/source drift")

        manifest.write_text(
            json.dumps(
                {
                    "name": "meta",
                    "version": "0.1.0",
                    "skills": [
                        {
                            "id": "sync-runtime-surfaces",
                            "source": "core/skills/meta/sync-runtime-surfaces",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        validate_codex_plugin_manifest("meta", manifest, contained, by_id)

    print("skill-governance-audit: codex-plugin fixture OK stale_skill_detected=true")


def validate_reviewer_profile_fixture() -> None:
    with tempfile.TemporaryDirectory(prefix="reviewer-profile-") as tmp:
        fixture = Path(tmp)
        (fixture / "manifests").mkdir(parents=True)
        shutil.copy2(ROOT / "manifests" / "agents.yaml", fixture / "manifests" / "agents.yaml")
        shutil.copytree(
            ROOT / "core" / "agents" / "code-review",
            fixture / "core" / "agents" / "code-review",
        )
        skill_target = fixture / "core" / "skills" / "code-review" / "code-review-specialists"
        skill_target.mkdir(parents=True)
        shutil.copy2(
            ROOT / "core" / "skills" / "code-review" / "code-review-specialists" / "SKILL.md.tera",
            skill_target / "SKILL.md.tera",
        )
        policy_target = fixture / "core" / "policies"
        policy_target.mkdir(parents=True)
        shutil.copy2(
            ROOT / "core" / "policies" / "code-review-delegation-codex.md",
            policy_target / "code-review-delegation-codex.md",
        )

        baseline_errors = codex_reviewer_profile_errors(fixture)
        if baseline_errors:
            fail(f"reviewer-profile fixture baseline failed: {baseline_errors}")

        template = fixture / "core" / "agents" / "code-review" / "reviewer-testing" / "AGENT.md.tera"
        template.write_text(
            template.read_text(encoding="utf-8").replace(
                'model_reasoning_effort = "medium"\n', "", 1
            ),
            encoding="utf-8",
        )
        missing_field_errors = codex_reviewer_profile_errors(fixture)
        if not any("must explicitly set model" in error for error in missing_field_errors):
            fail("reviewer-profile fixture did not reject a missing explicit profile field")

        shutil.copy2(
            ROOT / "core" / "agents" / "code-review" / "reviewer-testing" / "AGENT.md.tera",
            template,
        )
        skill_fixture = skill_target / "SKILL.md.tera"
        skill_fixture.write_text(
            skill_fixture.read_text(encoding="utf-8").replace(
                "do not spawn a generic child", "generic fallback is unspecified"
            ),
            encoding="utf-8",
        )
        fallback_errors = codex_reviewer_profile_errors(fixture)
        if not any(
            "missing dispatch contract phrase: do not spawn a generic child" in error
            for error in fallback_errors
        ):
            fail("reviewer-profile fixture did not reject a silent generic fallback")

    print(
        "skill-governance-audit: reviewer-profile fixture OK "
        "manifest_inventory=true missing_field_rejected=true "
        "generic_fallback_rejected=true"
    )


if MODE == "repo":
    validate_repo()
elif MODE == "count-check":
    count = validate_counts(ROOT)
    print(
        "skill-governance-audit: counts OK "
        f"skills={count} targets={len(COUNT_TARGETS)}"
    )
elif MODE == "count-update":
    update_counts(ROOT)
elif MODE == "shape-only":
    validate_shape_only(SHAPE_ARG_PATHS)
elif MODE == "create-fixture":
    validate_create_fixture()
elif MODE == "remove-fixture":
    validate_remove_fixture()
elif MODE == "create-project-fixture":
    validate_create_project_fixture()
elif MODE == "remove-project-fixture":
    validate_remove_project_fixture()
elif MODE == "count-refresh-fixture":
    validate_count_refresh_fixture()
elif MODE == "codex-plugin-fixture":
    validate_codex_plugin_fixture()
elif MODE == "reviewer-profile-fixture":
    validate_reviewer_profile_fixture()
elif MODE == "description-limit-fixture":
    validate_description_limit_fixture()
elif MODE == "exposure-contract-fixture":
    validate_exposure_contract_fixture()
else:
    fail(f"unknown mode: {MODE}")
PY
