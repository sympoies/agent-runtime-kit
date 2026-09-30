#!/usr/bin/env python3
"""Self-consistency of the tracker row grammar fixture corpus.

`core/skills/issue/issue-follow-up/references/program-mode.md` owns the grammar;
`tests/fixtures/tracker-row-grammar/` is the corpus that downstream parsers
vendor. A wrong fixture is copied into every consumer, so this test replays the
corpus through a small oracle written from the specification.

The oracle is test-only. It is not a product parser and nothing may import it:
the shipped implementations live in the repositories that vendor the corpus.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "core/skills/issue/issue-follow-up/references/program-mode.md"
CORPUS_PATH = "tests/fixtures/tracker-row-grammar"
CORPUS = ROOT / CORPUS_PATH
CODES = {
    "malformed-row",
    "duplicate-id",
    "unknown-dependency",
    "self-dependency",
    "cycle",
    "stale-graph",
}

ID = r"[A-Za-z][A-Za-z0-9]*"
ROW = re.compile(rf"^- \[([ xX])\] \*\*({ID})\*\*( .*)$")
AFTER = re.compile(r"^(.*) · after(?: (.*))?$")
AFTER_LIST = re.compile(rf"^{ID}(?: *, *{ID})*$")
REF = re.compile(r"^(.*): (?:([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+))?#([1-9][0-9]*)$")


def section(lines: list[str], heading: str) -> list[tuple[int, str]]:
    """Numbered lines of the first `## <heading>` section, heading excluded."""
    found: list[tuple[int, str]] | None = None
    for number, line in enumerate(lines, start=1):
        if found is None:
            if line.lower() == f"## {heading}":
                found = []
        elif line.startswith("## "):
            break
        else:
            found.append((number, line))
    return found or []


def parse_row(line: str) -> dict | None:
    match = ROW.match(line)
    if not match:
        return None
    text, after, notes, ref = match.group(3), [], None, None
    clause = AFTER.match(text)
    if clause:
        tail = (clause.group(2) or "").strip()
        after = [part.strip() for part in tail.split(",")]
        if not AFTER_LIST.match(tail) or len(set(after)) != len(after):
            return None
        text = clause.group(1)
    text = text.strip()
    if text.endswith(")"):
        depth, opening = 0, -1
        for index in range(len(text) - 1, -1, -1):
            depth += {")": 1, "(": -1}.get(text[index], 0)
            if depth == 0:
                opening = index
                break
        inner = text[opening + 1 : -1].strip()
        if opening > 0 and text[opening - 1] == " " and inner:
            notes, text = inner, text[:opening].rstrip()
    target = REF.match(text)
    if target:
        text = target.group(1).rstrip()
        ref = {
            "owner": target.group(2),
            "repo": target.group(3),
            "number": int(target.group(4)),
        }
    if not text:
        return None
    return {
        "id": match.group(2),
        "title": text,
        "ref": ref,
        "notes": notes,
        "after": after,
        "done": match.group(1) != " ",
    }


def generate(rows: list[dict]) -> str:
    lines = ["graph LR"]
    for row in rows:
        gate = "" if row["ref"] else "{{%s}}" % row["id"]
        lines.append(f"  {row['id']}{gate}")
    for row in rows:
        lines.extend(f"  {dependency} --> {row['id']}" for dependency in row["after"])
    return "\n".join(lines)


def lint(body: str) -> tuple[list[dict], list[dict]]:
    """Return (rows, findings) for one tracker body."""
    lines = [line.rstrip() for line in body.split("\n")]
    rows, findings, phase, line_of = [], [], None, {}

    def report(code: str, line: int | None, ids: list[str]) -> None:
        findings.append({"code": code, "line": line, "ids": ids})

    for number, line in section(lines, "phase table"):
        if line.startswith("### "):
            phase = line[4:].strip()
        elif re.match(r"^- \[[ xX]\]", line):
            row = parse_row(line)
            if row is None:
                report("malformed-row", number, [])
            elif row["id"] in line_of:
                report("duplicate-id", number, [row["id"]])
            else:
                line_of[row["id"]] = number
            if row is not None:
                rows.append({**row, "phase": phase, "line": number})

    edges: dict[str, set[str]] = {row_id: set() for row_id in line_of}
    for row in rows:
        for dependency in row["after"]:
            if dependency == row["id"]:
                report("self-dependency", row["line"], [row["id"]])
            elif dependency not in line_of:
                report("unknown-dependency", row["line"], [row["id"], dependency])
            else:
                edges[dependency].add(row["id"])

    def reachable(start: str) -> set[str]:
        seen: set[str] = set()
        stack = list(edges[start])
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(edges[node])
        return seen

    reach = {row_id: reachable(row_id) for row_id in line_of}
    grouped: set[str] = set()
    for row_id in line_of:  # insertion order is table order
        group = [
            other
            for other in line_of
            if other == row_id or (other in reach[row_id] and row_id in reach[other])
        ]
        if len(group) > 1 and row_id not in grouped:
            report("cycle", line_of[row_id], group)
            grouped.update(group)

    if not findings:
        block, inside = None, False
        for _, line in section(lines, "dependency graph"):
            if not inside and block is None and line == "```mermaid":
                block, inside = [], True
            elif inside and line == "```":
                inside = False
            elif inside:
                block.append(line)
        if block is None or inside or "\n".join(block) != generate(rows):
            report("stale-graph", None, [])

    for row in rows:
        del row["line"]
    return rows, findings


def fixtures(kind: str) -> list[Path]:
    return sorted((CORPUS / kind).glob("*.md"))


def expected(path: Path) -> dict:
    return json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))


def finding_key(finding: dict) -> str:
    return json.dumps(finding, sort_keys=True)


class TrackerRowGrammarFixtureTests(unittest.TestCase):
    def test_specification_names_the_corpus_and_every_finding_code(self) -> None:
        spec = SPEC.read_text(encoding="utf-8")
        readme = (CORPUS / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"`{CORPUS_PATH}/`", spec)
        for code in sorted(CODES):
            with self.subTest(code=code):
                self.assertIn(f"`{code}`", spec)
                self.assertIn(f"`{code}`", readme)

    def test_every_body_has_an_expectation_and_nothing_else_is_shipped(self) -> None:
        self.assertGreaterEqual(len(fixtures("valid")), 3)
        for kind in ("valid", "invalid"):
            names = sorted(path.name for path in (CORPUS / kind).iterdir())
            paired = sorted(
                name
                for body in fixtures(kind)
                for name in (body.name, body.with_suffix(".json").name)
            )
            self.assertEqual(names, paired, kind)

    def test_valid_bodies_parse_to_their_expected_rows_and_graph(self) -> None:
        row_keys = {"id", "title", "ref", "notes", "after", "done", "phase"}
        for body in fixtures("valid"):
            with self.subTest(fixture=body.name):
                want = expected(body)
                self.assertEqual(set(want), {"rows", "graph"})
                for row in want["rows"]:
                    self.assertEqual(set(row), row_keys)
                    if row["ref"] is not None:
                        self.assertEqual(set(row["ref"]), {"owner", "repo", "number"})
                # The expected graph must follow from the expected rows alone.
                self.assertEqual(want["graph"], generate(want["rows"]))
                rows, findings = lint(body.read_text(encoding="utf-8"))
                self.assertEqual(findings, [])
                self.assertEqual(rows, want["rows"])

    def test_invalid_bodies_report_exactly_their_expected_findings(self) -> None:
        covered: set[str] = set()
        for body in fixtures("invalid"):
            with self.subTest(fixture=body.name):
                want = expected(body)
                self.assertEqual(set(want), {"findings"})
                codes = {finding["code"] for finding in want["findings"]}
                self.assertTrue(codes and codes <= CODES, codes)
                self.assertTrue(
                    any(body.name.startswith(code) for code in codes), body.name
                )
                covered |= codes
                _, findings = lint(body.read_text(encoding="utf-8"))
                self.assertEqual(
                    sorted(map(finding_key, findings)),
                    sorted(map(finding_key, want["findings"])),
                )
        self.assertEqual(covered, CODES)

    def test_valid_corpus_covers_every_row_form(self) -> None:
        rows = [row for body in fixtures("valid") for row in expected(body)["rows"]]
        refs = [row["ref"] for row in rows if row["ref"] is not None]
        seen = [json.dumps(ref, sort_keys=True) for ref in refs]
        forms = {
            "gate": any(row["ref"] is None for row in rows),
            "notes": any(row["notes"] for row in rows),
            "phase": any(row["phase"] for row in rows),
            "no phase": any(row["phase"] is None for row in rows),
            "done": any(row["done"] for row in rows),
            "open": any(not row["done"] for row in rows),
            "own-repository ref": any(ref["owner"] is None for ref in refs),
            "cross-repository ref": any(ref["owner"] for ref in refs),
            "same issue twice": len(seen) != len(set(seen)),
            "several dependencies": any(len(row["after"]) > 1 for row in rows),
            "tracker without dependencies": any(
                not any(row["after"] for row in expected(body)["rows"])
                for body in fixtures("valid")
            ),
        }
        self.assertEqual([name for name, hit in forms.items() if not hit], [])


if __name__ == "__main__":
    unittest.main()
