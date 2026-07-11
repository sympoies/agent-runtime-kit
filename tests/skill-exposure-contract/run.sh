#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1])
skills_schema = json.loads((root / "core/docs/schemas/skills.schema.json").read_text())
disposition_schema_path = root / "core/docs/schemas/skill-dispositions.schema.json"
assert skills_schema["properties"]["schema_version"]["const"] == 2
assert disposition_schema_path.is_file()

skill_text = (root / "manifests/skills.yaml").read_text()
assert re.search(r"^schema_version: 2$", skill_text, re.M)
assert re.search(r"^migration:$", skill_text, re.M)
assert "pending_disposition:" in skill_text

skill_ids = re.findall(r"^  - id: ([a-z0-9.-]+)$", skill_text, re.M)
pending_ids = re.findall(r"^    - ([a-z0-9.-]+)$", skill_text.split("skills:", 1)[0], re.M)
assert len(skill_ids) == len(set(skill_ids))
assert set(pending_ids).issubset(skill_ids)
assert pending_ids == [skill_id for skill_id in skill_ids if skill_id in set(pending_ids)]

disposition_text = (root / "manifests/skill-dispositions.yaml").read_text()
assert 'source_skill_ids_sha256: "16b2fc145c6d2a556360dc43cddd6a30ea79ad90837d5bcd647971aa84a34d60"' in disposition_text
disposition_ids = re.findall(r"^  - id: ([a-z0-9.-]+)$", disposition_text, re.M)
assert len(disposition_ids) == 66
assert len(disposition_ids) == len(set(disposition_ids))
pending_rows = []
for chunk in re.split(r"(?=^  - id: )", disposition_text, flags=re.M):
    row_id = re.match(r"^  - id: ([a-z0-9.-]+)$", chunk, re.M)
    status = re.search(r"^    status: ([a-z-]+)$", chunk, re.M)
    if row_id and status and status.group(1) == "pending":
        pending_rows.append(row_id.group(1))
assert pending_rows == pending_ids
PY

bash "$REPO_ROOT/scripts/ci/skill-governance-audit.sh" --fixture exposure-contract

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
skills = report["skills"]
manifest = Path(sys.argv[3]).read_text()
active_ids = re.findall(r"^  - id: ([a-z0-9.-]+)$", manifest, re.M)
pending_ids = set(
    re.findall(r"^    - ([a-z0-9.-]+)$", manifest.split("skills:", 1)[0], re.M)
)
reported = {item["id"]: item for item in skills}
assert set(reported) == set(active_ids), (product, set(active_ids) - set(reported), set(reported) - set(active_ids))
for skill_id, item in reported.items():
    if skill_id in pending_ids:
        assert item["pending_disposition"] is True, (product, skill_id)
        assert item["invocation"] is None, (product, skill_id)
        assert item["exposure"] is None, (product, skill_id)
    else:
        assert item["pending_disposition"] is False, (product, skill_id)
        assert item["invocation"] is not None, (product, skill_id)
        assert item["exposure"] is not None, (product, skill_id)
PY
done

echo "skill-exposure-contract: PASS"
