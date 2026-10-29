#!/usr/bin/env bash
# Repository-only retention inventory; never rendered as consumer policy.
# Shell entrypoint supports macOS Bash 3.2; Python 3.11+ owns TOML and dates.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/lib/runtime-python.sh
. "$REPO_ROOT/scripts/lib/runtime-python.sh"
require_runtime_python
runtime_python - "$REPO_ROOT" "$@" <<'PY'
from __future__ import annotations
import argparse
import collections
import datetime as dt
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tomllib

parser = argparse.ArgumentParser(description="Audit this repository's retained obsolete contracts.")
parser.add_argument("--root", type=Path, default=Path(sys.argv[1]))
parser.add_argument("--baseline", type=Path)
parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
parser.add_argument("--release", help="Actual kit CalVer release being checked; fence is inclusive")
args = parser.parse_args(sys.argv[2:])
root = args.root.resolve()

# Immutable history / derived output are not active contract owners. Exact ban
# ledgers remain provenance rather than runtime readers. Tests otherwise scan.
EXCLUDED_PREFIXES = ("build/", "tests/golden/", "docs/source/devlog/", "docs/plans/",
                     "docs/archive/", "docs/discussions/", "vendor/", "third_party/")
EXCLUDED_FILES = {"scripts/ci/own-compat-audit.sh", "scripts/ci/own-compat-allowlist.toml",
                  "tests/ci/test_own_compat_audit.py", "manifests/retired-skill-ids.json",
                  "manifests/skill-dispositions.yaml"}
# These are constructs, identifiers, or retention declarations, not generic
# words such as alias/fallback/migrate. Matches never include profile values.
PATTERNS = [
    re.compile(r"\b[A-Za-z_]*(?:LEGACY|legacy|DEPRECATED|deprecated|OBSOLETE|obsolete)_[A-Za-z0-9_]+\b"),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*_ALIASES\b"),
    re.compile(r"\blegacy[A-Z][A-Za-z0-9_]+\b|\b(?:OLD|old|RETIRED|retired)_(?:FORMAT|format|SCHEMA|schema|VERSION|version|LAYOUT|layout|PATH|path)[A-Za-z0-9_]*\b"),
    re.compile(r"\b(?:cleanup_retired_managed_product_links|bootstrap_host_available|rollback_agent_hook_cutover|capture_agent_hook_cutover|restore_agent_hook_cutover)\b"),
    re.compile(r"agent-runtime-kit\.hook-rollback\.v[0-9]+|\bcompatibility hold\b", re.I),
    re.compile(r"\b(?:AGENT_DOCS_HOME|AGENT_DOCS_ROOT|minimum_supported_tag|DEFAULT_PROFILE)\b"),
    re.compile(r"--product[ =]+both\b|\bboth\)"),
    re.compile(r"\bbackwards?[- ]compatib(?:ility|le)\b|\bcompatibility (?:shim|alias|fallback)\b", re.I),
    re.compile(r"\b(?:retain|accept|support|read|restore)(?:s|ed|ing)? (?:the )?(?:old|legacy|retired) (?:format|schema|layout|version|shared.marker)\b", re.I),
    re.compile(r"#\[(?:serde|clap|command|arg)\([^\n]*(?:alias|aliases)\s*=[^\n]*\)\]"),
    re.compile(r"(?:\b(?:schema|format|state|wire)_version|\b[\w.]+(?:\.get\([\"'](?:schema|format|state|wire)_version[\"']\)|\[[\"'](?:schema|format|state|wire)_version[\"']\]))\s+in\s*(?:\([^\n)]*,[^\n)]*\)|\[[^\n\]]*,[^\n\]]*\])"),
    re.compile(r"^\s*(?:alias|visible_alias|hidden_alias)\s*=\s*[\"'][^\"']+[\"']"),
    re.compile(r"\b(?:add_argument|add_parser)\([^\n]*(?:argparse\.SUPPRESS|aliases\s*=)"),
]
# Narrow negative examples are declarations of refusal, not old-form support.
# A function merely named test_reject_* does not exempt its body or the file.
NEGATIVE = re.compile(
    r"^\s*(?:(?:#\s*)?(?:never\b|do not\b|must not\b|no backward\b)"
    r"|#.*\b(?:is|are) rejected\b|assert\s+not\b|raise\b)", re.I)
KINDS = {"scheduled", "external", "rollback-window", "current-default", "provenance", "rejection", "guidance"}
ISSUE = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*\Z")
COMMON = {"path", "match", "count", "kind", "reason", "issue", "expires"}
WINDOW = {"previous_release", "current_release", "remove_before_release", "transport"}


def release(value):
    if not isinstance(value, str) or not re.fullmatch(r"v?\d{4}\.\d{2}\.\d{2}", value):
        raise ValueError("release must be an actual CalVer YYYY.MM.DD")
    return dt.datetime.strptime(value.removeprefix("v"), "%Y.%m.%d").date()


def scan_text(text):
    for number, line in enumerate(text.splitlines(), 1):
        if NEGATIVE.search(line):
            continue
        spans = []
        for pattern in PATTERNS:
            for match in pattern.finditer(line):
                if any(a <= match.start() and match.end() <= b for a, b in spans):
                    continue
                spans.append(match.span())
                yield number, match.group()


def scan():
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True,
                             capture_output=True).stdout.decode().split("\0")
    hits = collections.Counter()
    lines = {}
    for path in sorted(set(tracked)):
        if not path or path in EXCLUDED_FILES or path.startswith(EXCLUDED_PREFIXES):
            continue
        target = root / path
        if target.resolve() == (args.baseline or root / "scripts/ci/own-compat-allowlist.toml").resolve():
            continue
        if target.is_symlink() or not target.is_file():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, matched in scan_text(text):
            key = path, matched
            hits[key] += 1
            lines.setdefault(key, number)
    return hits, lines


def ratchet(rows):
    # Use fetched main, never a moving row counter, to prove baseline additions
    # existed before this change. Shallow release snapshots may lack main; their
    # reviewed baseline still enforces exact counts and both expiry checks.
    base = subprocess.run(["git", "rev-parse", "--verify", "refs/remotes/origin/main"],
                          cwd=root, capture_output=True, text=True)
    if base.returncode:
        return []
    base = base.stdout.strip()
    cache = {}
    errors = []
    previous = subprocess.run(["git", "show", f"{base}:scripts/ci/own-compat-allowlist.toml"],
                              cwd=root, capture_output=True, text=True)
    prior = {}
    if previous.returncode == 0:
        prior = {(row["path"], row["match"]): row
                 for row in tomllib.loads(previous.stdout).get("allow", [])}
    for row in rows:
        path = row["path"]
        if path not in cache:
            content = subprocess.run(["git", "show", f"{base}:{path}"], cwd=root,
                                     capture_output=True, text=True)
            cache[path] = collections.Counter(matched for _, matched in scan_text(content.stdout))
        key = path, row["match"]
        old = prior.get(key)
        limit = old["count"] if old else cache[path][row["match"]]
        if row["count"] > limit:
            errors.append(f"ratchet: {path} {row['match']} adds occurrences beyond fetched main")
        if old and old["kind"] == "scheduled" and (
            row["kind"] != "scheduled" or row["issue"] != old["issue"]
            or row["expiry"] > dt.date.fromisoformat(old["expires"])
        ):
            errors.append(f"ratchet: {path} {row['match']} weakens scheduled removal ownership/deadline")
    return errors


def load_baseline(path):
    data = tomllib.loads(path.read_text())
    if set(data) - {"schema", "allow", "release_sequence"} or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("baseline requires schema = 1 and known keys only")
    sequence = [release(value) for value in data.get("release_sequence", [])]
    if sequence != sorted(set(sequence)):
        raise ValueError("release_sequence must list distinct ordered actual adjacent releases")
    rows = data.get("allow", [])
    if not isinstance(rows, list):
        raise ValueError("allow must be an array of tables")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not COMMON <= set(row):
            raise ValueError("incomplete baseline row")
        kind = row["kind"]
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError("unknown kind")
        extra = {"external"} if kind == "external" else WINDOW if kind == "rollback-window" else set()
        if set(row) != COMMON | extra:
            raise ValueError("malformed kind fields")
        if any(not isinstance(row[key], str) or not row[key].strip()
               for key in COMMON - {"count"}):
            raise ValueError("baseline string fields must be nonempty")
        path_value = PurePosixPath(row["path"])
        if path_value.is_absolute() or ".." in path_value.parts or any(c in row["path"] for c in "*?[]\\"):
            raise ValueError("path must be exact and repository relative")
        if "\n" in row["match"] or type(row["count"]) is not int or row["count"] < 1:
            raise ValueError("match/count must bind existing occurrences")
        if not ISSUE.fullmatch(row["issue"]):
            raise ValueError("issue must name an actual public removal/classification issue")
        if kind == "scheduled" and row["issue"] not in {
            f"https://github.com/sympoies/agent-runtime-kit/issues/{n}" for n in (327, 328, 329, 330, 331, 332)
        }:
            raise ValueError("scheduled debt must be owned by its K2-K6 or profile removal slice")
        row["expiry"] = dt.date.fromisoformat(row["expires"])
        if kind == "external" and (not isinstance(row["external"], str) or not re.search(r"[A-Za-z].*\bv?\d+(?:\.\d+)*(?:\.x)?\b", row["external"])):
            raise ValueError("external row must name provider/OS/tool and supported version")
        if kind == "current-default" and not re.fullmatch(r"DEFAULT_[A-Z_]+|[A-Z_]+_ALIASES|minimum_supported_tag", row["match"]):
            raise ValueError("current-default only classifies canonical default declarations")
        if kind == "rollback-window":
            pair = [release(row[key]) for key in ("previous_release", "current_release", "remove_before_release")]
            if not any(sequence[i:i+3] == pair for i in range(len(sequence)-2)):
                raise ValueError("rollback window requires coordinator-supplied adjacent release sequence and concrete next fence")
            if not isinstance(row["transport"], str) or not row["transport"].startswith("Cross-host wire/state:") or len(row["transport"]) < 55:
                raise ValueError("only concrete cross-host wire/state qualifies; local restore/layout/labels do not")
        key = row["path"], row["match"]
        if key in seen:
            raise ValueError("duplicate baseline identity")
        seen.add(key)
    return rows


try:
    baseline = args.baseline or root / "scripts/ci/own-compat-allowlist.toml"
    rows = load_baseline(baseline)
    candidate = args.release
    if not candidate and os.environ.get("GITHUB_REF_TYPE") == "tag":
        candidate = os.environ.get("GITHUB_REF_NAME", "")
    release_date = release(candidate) if candidate is not None else None
    hits, lines = scan()
    ratchet_errors = ratchet(rows)
except (ValueError, TypeError, OSError, subprocess.CalledProcessError) as error:
    print(f"own-compat-audit: malformed input: {error}", file=sys.stderr)
    sys.exit(2)

errors = ratchet_errors
listed = set()
for row in rows:
    key = row["path"], row["match"]
    listed.add(key)
    count = hits.get(key, 0)
    if not count:
        errors.append(f"stale: {row['path']} {row['match']}")
    elif count != row["count"]:
        errors.append(f"count changed: {row['path']} {row['match']} expected={row['count']} actual={count}")
    if args.today >= row["expiry"]:
        errors.append(f"expired: {row['path']} {row['match']} {row['expires']}")
    if row["kind"] == "rollback-window" and release_date is not None and release_date >= release(row["remove_before_release"]):
        errors.append(f"release-expired: {row['path']} {row['match']} remove before {row['remove_before_release']}")
for key in sorted(hits.keys() - listed):
    errors.append(f"unlisted: {key[0]}:{lines[key]}: {key[1]} (count={hits[key]})")
for error in errors:
    print(f"own-compat-audit: {error}")
if errors:
    sys.exit(1)
print(f"own-compat-audit: ok ({len(rows)} exact baseline rows; {sum(hits.values())} occurrences)")
PY
