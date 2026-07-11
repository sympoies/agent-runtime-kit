#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import json
import hashlib
import re
import subprocess
import sys
from pathlib import Path


root = Path(sys.argv[1])
progress = json.loads(
    (root / "tests/skill-exposure-contract/expected-migration-progress.json").read_text()
)
assert progress["schema"] == "agent-runtime-kit.skill-migration-progress.v1"
assert progress["task"] == "3.1"
assert progress["advance_in_task"] == "complete"
skills_schema = json.loads((root / "core/docs/schemas/skills.schema.json").read_text())
disposition_schema_path = root / "core/docs/schemas/skill-dispositions.schema.json"
assert skills_schema["properties"]["schema_version"]["const"] == 2
assert disposition_schema_path.is_file()

skill_text = (root / "manifests/skills.yaml").read_text()
assert re.search(r"^schema_version: 2$", skill_text, re.M)
assert re.search(r"^migration:$", skill_text, re.M)
assert "pending_disposition: []" in skill_text

skill_ids = re.findall(r"^  - id: ([a-z0-9.-]+)$", skill_text, re.M)
pending_ids = re.findall(r"^    - ([a-z0-9.-]+)$", skill_text.split("skills:", 1)[0], re.M)
assert len(skill_ids) == len(set(skill_ids))
assert set(pending_ids).issubset(skill_ids)
assert pending_ids == [skill_id for skill_id in skill_ids if skill_id in set(pending_ids)]
assert pending_ids == progress["pending_ids"]
assert skill_ids == progress["retained_ids"]

disposition_text = (root / "manifests/skill-dispositions.yaml").read_text()
assert 'source_skill_ids_sha256: "16b2fc145c6d2a556360dc43cddd6a30ea79ad90837d5bcd647971aa84a34d60"' in disposition_text
disposition_ids = re.findall(r"^  - id: ([a-z0-9.-]+)$", disposition_text, re.M)
assert len(disposition_ids) == 66
assert len(disposition_ids) == len(set(disposition_ids))
pending_rows = []
reviewed_rows = []
dispositions = {}
for chunk in re.split(r"(?=^  - id: )", disposition_text, flags=re.M):
    row_id = re.match(r"^  - id: ([a-z0-9.-]+)$", chunk, re.M)
    status = re.search(r"^    status: ([a-z-]+)$", chunk, re.M)
    if row_id and status and status.group(1) == "pending":
        pending_rows.append(row_id.group(1))
    if row_id and status and status.group(1) == "reviewed":
        reviewed_rows.append(row_id.group(1))
        values = {}
        for field in ("example_request", "rationale"):
            match = re.search(rf"^    {field}: (.+)$", chunk, re.M)
            values[field] = match.group(1).strip('"\'') if match else None
        intents = re.search(r"^    parent_intents: \[(.*)\]$", chunk, re.M)
        values["parent_intents"] = [
            item.strip().strip('"\'')
            for item in (intents.group(1).split(",") if intents else [])
            if item.strip()
        ]
        dispositions[row_id.group(1)] = values
assert pending_rows == pending_ids
assert reviewed_rows == progress["reviewed_ids"]
assert len(reviewed_rows) == 66
assert len(pending_rows) == 0
assert progress["retired_ids"] == [
    skill_id for skill_id in reviewed_rows if skill_id not in set(skill_ids)
]

skill_chunks = {
    match.group(1): chunk
    for chunk in re.split(r"(?=^  - id: )", skill_text, flags=re.M)
    if (match := re.match(r"^  - id: ([a-z0-9.-]+)$", chunk, re.M))
}
for skill_id in progress["retained_ids"]:
    chunk = skill_chunks[skill_id]
    invocation = {
        "example_request": re.search(r"^      example_request: (.+)$", chunk, re.M).group(1).strip('"\''),
        "intents": [
            item.strip().strip('"\'')
            for item in re.search(r"^      intents: \[(.*)\]$", chunk, re.M).group(1).split(",")
            if item.strip()
        ],
        "admission_rationale": re.search(r"^      admission_rationale: (.+)$", chunk, re.M).group(1).strip('"\''),
    }
    for mapping in progress["reviewed_field_mapping"]:
        manifest_field = mapping["manifest"].removeprefix("invocation.")
        assert dispositions[skill_id][mapping["disposition"]] == invocation[manifest_field], (
            skill_id,
            mapping,
        )

for skill_id in progress["retired_ids"]:
    domain, skill = skill_id.split(".", 1)
    source = root / "core" / "skills" / domain / skill
    assert not any(path.is_file() for path in source.rglob("*")), skill_id

retired_ids = json.loads(
    (root / "manifests/retired-skill-ids.json").read_text()
)
assert retired_ids["schema"] == "agent-runtime-kit.retired-skill-ids.v1"
assert retired_ids["skills"] == progress["retired_ids"]

retired_hermes = json.loads(
    (root / "manifests/retired-hermes-skill-copies.json").read_text()
)
assert retired_hermes["schema"] == "agent-runtime-kit.retired-hermes-skill-copies.v1"
assert list(retired_hermes["skills"]) == retired_ids["skills"]

source_revision = retired_hermes["source_revision"]
subprocess.run(
    ["git", "cat-file", "-e", f"{source_revision}^{{commit}}"],
    cwd=root,
    check=True,
)


def baseline_tree_digest(skill_id: str) -> str:
    domain, skill = skill_id.split(".", 1)
    prefix = f"tests/golden/hermes/plugins/{domain}/skills/{skill}/expected"
    raw = subprocess.check_output(
        ["git", "ls-tree", "-r", "-t", "-z", source_revision, "--", prefix],
        cwd=root,
    )
    entries = []
    for record in raw.rstrip(b"\0").split(b"\0") if raw else []:
        metadata, path_raw = record.split(b"\t", 1)
        mode_raw, entry_type_raw, object_id_raw = metadata.split(b" ", 2)
        path = path_raw.decode()
        if not path.startswith(prefix + "/"):
            continue
        relative = Path(path).relative_to(prefix).as_posix()
        if relative == ".":
            continue
        entry_type = "d" if entry_type_raw == b"tree" else "f"
        mode = "0755" if entry_type == "d" or mode_raw == b"100755" else "0644"
        content = None
        if entry_type == "f":
            content = subprocess.check_output(
                ["git", "cat-file", "blob", object_id_raw.decode()], cwd=root
            )
        entries.append((relative, entry_type, mode, content))
    assert entries, skill_id
    digest = hashlib.sha256()
    for relative, entry_type, mode, content in sorted(entries):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(entry_type.encode())
        digest.update(b"\0")
        digest.update(mode.encode())
        digest.update(b"\0")
        if content is not None:
            digest.update(str(len(content)).encode())
            digest.update(b"\0")
            digest.update(content)
    return digest.hexdigest()


for skill_id, expected_digest in retired_hermes["skills"].items():
    assert baseline_tree_digest(skill_id) == expected_digest, skill_id

fixture_root = root / "tests/fixtures/retired-hermes-skill-copies"
for skill_file in fixture_root.glob("*/*/SKILL.md"):
    skill_dir = skill_file.parent
    domain = skill_dir.parent.name
    skill = skill_dir.name
    digest = hashlib.sha256()
    entries = []
    for path in skill_dir.rglob("*"):
        relative = path.relative_to(skill_dir).as_posix()
        entry_type = "d" if path.is_dir() else "f"
        mode = "0755" if entry_type == "d" or path.stat().st_mode & 0o111 else "0644"
        content = path.read_bytes() if path.is_file() else None
        entries.append((relative, entry_type, mode, content))
    for relative, entry_type, mode, content in sorted(entries):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(entry_type.encode())
        digest.update(b"\0")
        digest.update(mode.encode())
        digest.update(b"\0")
        if content is not None:
            digest.update(str(len(content)).encode())
            digest.update(b"\0")
            digest.update(content)
    assert digest.hexdigest() == retired_hermes["skills"][f"{domain}.{skill}"]

policy_paths = [
    root / "AGENT_HOME.md",
    root / "AGENT_DOCS.toml",
    root / "core/policies/work-tier-levels.md",
    root / "core/policies/git-delivery.md",
    root / "core/policies/review-thread-convergence.md",
]
for path in policy_paths:
    text = path.read_text()
    for skill_id in progress["retired_ids"]:
        domain, skill = skill_id.split(".", 1)
        for forbidden in (
            skill_id,
            f"{domain}:{skill}",
            f"${skill}",
            f"core/skills/{domain}/{skill}",
        ):
            assert forbidden not in text, (path, forbidden)
        for line_number, line in enumerate(text.splitlines(), 1):
            if re.search(r"(?<![-\w])skills?(?![-\w])", line, re.I):
                assert f"`{skill}`" not in line, (path, line_number, skill, line)
PY

fixture_output="$(bash "$REPO_ROOT/scripts/ci/skill-governance-audit.sh" --fixture exposure-contract)"
echo "$fixture_output"
python3 - "$REPO_ROOT" "$fixture_output" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
output = sys.argv[2]
progress = json.loads(
    (root / "tests/skill-exposure-contract/expected-migration-progress.json").read_text()
)
assert f"reviewed={len(progress['reviewed_ids'])}" in output, output
assert f"pending={len(progress['pending_ids'])}" in output, output
PY

for product in codex claude hermes; do
  agent-runtime render --source-root "$REPO_ROOT" --product "$product" >/dev/null
  report="$(agent-runtime list-skills --source-root "$REPO_ROOT" --product "$product" --format json)"
  python3 - "$product" "$report" "$REPO_ROOT/manifests/skills.yaml" <<'PY'
import json
import re
import sys
from pathlib import Path

product = sys.argv[1]
report = json.loads(sys.argv[2])
assert report["schema"] == "cli.agent-runtime.list-skills.v1", (product, report.get("schema"))
assert report["product"] == product, (product, report.get("product"))
skills = report["skills"]
manifest = Path(sys.argv[3]).read_text()
active_ids = re.findall(r"^  - id: ([a-z0-9.-]+)$", manifest, re.M)
pending_ids = set(
    re.findall(r"^    - ([a-z0-9.-]+)$", manifest.split("skills:", 1)[0], re.M)
)
reported = {item["id"]: item for item in skills}
assert set(reported) == set(active_ids), (product, set(active_ids) - set(reported), set(reported) - set(active_ids))
assert len(active_ids) == 26, (product, len(active_ids))
assert not pending_ids, (product, pending_ids)

manifest_semantics = {}
for chunk in re.split(r"(?=^  - id: )", manifest, flags=re.M):
    id_match = re.match(r"^  - id: ([a-z0-9.-]+)$", chunk, re.M)
    if not id_match or not re.search(r"^    invocation:$", chunk, re.M):
        continue
    role = re.search(r"^      role: ([a-z-]+)$", chunk, re.M).group(1)
    intents = re.search(r"^      intents: \[(.*)\]$", chunk, re.M).group(1)
    example = re.search(r"^      example_request: (.+)$", chunk, re.M).group(1)
    rationale = re.search(r"^      admission_rationale: (.+)$", chunk, re.M).group(1)
    profile = re.search(r"^      profile: ([a-z-]+)$", chunk, re.M).group(1)
    replacement = re.search(r"^      replacement: ([a-z0-9.-]+)$", chunk, re.M)
    retire_after = re.search(r'^      retire_after: ["\']?([^"\']+)["\']?$', chunk, re.M)
    manifest_semantics[id_match.group(1)] = {
        "invocation": {
            "role": role,
            "intents": [item.strip().strip('"\'') for item in intents.split(",") if item.strip()],
            "example_request": example.strip('"\''),
            "admission_rationale": rationale.strip('"\''),
        },
        "exposure": {
            "profile": profile,
            "replacement": replacement.group(1) if replacement else None,
            "retire_after": retire_after.group(1) if retire_after else None,
        },
    }

for skill_id in active_ids:
    item = reported[skill_id]
    if skill_id in pending_ids:
        assert item["pending_disposition"] is True, (product, skill_id)
        assert item["invocation"] is None, (product, skill_id)
        assert item["exposure"] is None, (product, skill_id)
    else:
        assert item["pending_disposition"] is False, (product, skill_id)
        expected = manifest_semantics[skill_id]
        assert item["invocation"] == expected["invocation"], (product, skill_id, item["invocation"], expected["invocation"])
        assert item["exposure"] == expected["exposure"], (product, skill_id, item["exposure"], expected["exposure"])
        if expected["invocation"]["role"] != "compatibility":
            assert item["exposure"]["replacement"] is None, (product, skill_id)
            assert item["exposure"]["retire_after"] is None, (product, skill_id)
PY
done

echo "skill-exposure-contract: PASS"
