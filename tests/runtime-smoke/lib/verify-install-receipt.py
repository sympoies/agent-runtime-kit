#!/usr/bin/env python3
"""Independently rebuild an agent-runtime install receipt from a link map."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import stat
import sys


def digest(parts: list[bytes]) -> str:
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part)
    return f"sha256:{hasher.hexdigest()}"


def parse_link_map(path: pathlib.Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, object]] = []
    index = 0
    current: dict[str, object] | None = None
    while index < len(lines):
        line = lines[index]
        if line.startswith("  - id: "):
            current = {"id": line.removeprefix("  - id: ")}
            entries.append(current)
        elif current is not None and line.startswith("    "):
            field = line[4:]
            if field == "body_template: |-":
                body: list[str] = []
                index += 1
                while index < len(lines):
                    body_line = lines[index]
                    if body_line.startswith("      "):
                        body.append(body_line[6:])
                    elif body_line == "":
                        body.append("")
                    else:
                        index -= 1
                        break
                    index += 1
                current["body_template"] = "\n".join(body)
            elif ": " in field:
                key, value = field.split(": ", 1)
                current[key] = value == "true" if value in ("true", "false") else value
        index += 1
    if not entries or any("kind" not in item for item in entries):
        raise AssertionError(f"could not parse link-map entries: {path}")
    return entries


def recursive_files(root: pathlib.Path) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []

    def visit(directory: pathlib.Path) -> None:
        for entry in os.scandir(directory):
            metadata = entry.stat(follow_symlinks=False)
            path = pathlib.Path(entry.path)
            if stat.S_ISDIR(metadata.st_mode):
                visit(path)
            else:
                files.append(path.relative_to(root))

    visit(root)
    return sorted(files)


def expected_receipt(
    source_root: pathlib.Path, product: str
) -> tuple[list[dict[str, str]], str]:
    entries = parse_link_map(source_root / "targets" / product / "link-map.yaml")
    action_parts: dict[str, list[bytes]] = {}
    for entry in entries:
        entry_id = str(entry["id"])
        parts = action_parts.setdefault(entry_id, [])
        if entry["kind"] == "managed-block":
            canonical = f"managed-block:{entry['destination']}:{entry['surface']}"
            parts.extend((canonical.encode(), str(entry["body_template"]).encode()))
            continue

        source_rel = pathlib.Path(str(entry["source"]))
        destination = pathlib.Path(str(entry["destination"]))
        source = source_root / source_rel
        if entry.get("recursive") is True:
            actions = [
                (source_rel / relative, destination / relative, "recursive file symlink")
                for relative in recursive_files(source)
            ]
        else:
            metadata = source.stat()
            mode = "directory symlink" if stat.S_ISDIR(metadata.st_mode) else "file symlink"
            actions = [(source_rel, destination, mode)]
        for action_source, action_dest, mode in actions:
            absolute_source = source_root / action_source
            content = absolute_source.read_bytes() if absolute_source.is_file() else b""
            canonical = f"symlink:{action_source.as_posix()}:{action_dest.as_posix()}:{mode}"
            parts.extend((canonical.encode(), content))

    managed_entries = [
        {"id": entry_id, "digest": digest(action_parts[entry_id])}
        for entry_id in sorted(action_parts)
    ]
    plan_parts = [product.encode()]
    for entry in managed_entries:
        plan_parts.extend((entry["id"].encode(), entry["digest"].encode()))
    return managed_entries, digest(plan_parts)


def main() -> int:
    doctor_path, summary_path, source_arg, product, revision = sys.argv[1:6]
    source_root = pathlib.Path(source_arg)
    data = json.loads(pathlib.Path(doctor_path).read_text(encoding="utf-8"))
    installed = data["installed_runtime"]
    receipt = installed["receipt"]
    managed_entries, install_plan_digest = expected_receipt(source_root, product)

    assert data["schema_version"] == "agent-runtime-cli.doctor.v1"
    assert data["product"] == product
    assert data["block"] == 0 and data["exit_code"] == 0
    assert installed["verified"] is True
    assert installed["source_match"] is True
    assert installed["plan_match"] is True
    assert installed["source_clean"] is True
    assert receipt["schema"] == "agent-runtime.install-receipt.v1"
    assert receipt["product"] == product
    assert receipt["source_revision"] == revision
    assert receipt["source_dirty"] is False
    assert receipt["managed_entries"] == managed_entries
    assert receipt["install_plan_digest"] == install_plan_digest

    summary = {
        "schema": "portable-installed-runtime-summary.v1",
        "product": product,
        "source_revision": revision,
        "verified": True,
        "managed_entry_count": len(managed_entries),
        "install_plan_digest": install_plan_digest,
    }
    pathlib.Path(summary_path).write_text(
        json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
