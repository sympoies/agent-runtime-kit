#!/usr/bin/env python3
"""Flag new hard-coded agent state directories (write-location contract, #302).

`core/policies/write-locations.md` declares where agent-produced writes go. A
tool that hard-codes `~/.local/state/<dir>`, `$AGENT_HOME/<dir>`, or a fixed
`/tmp/<name>` root creates state no cleaner recognizes. This audit scans tracked
tool sources and runbooks for such literals and passes a literal only when it
names a declared class root or an allowlisted entry in
`scripts/ci/write-location-allow.toml`. Every allowlist entry carries a reason,
and an entry that no longer matches fails the gate so the list cannot rot.

Exit codes: 0 clean, 1 findings or stale entries, 2 invalid allowlist.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = "core/policies/write-locations.md"

# Derived output, tests, and historical records are not tool sources or active
# runbooks; the contract and this audit name the literals they forbid.
EXCLUDED_PREFIXES = (
    "build/",
    "tests/",
    "docs/source/devlog/",
    "docs/plans/",
    "docs/archive/",
    "docs/discussions/",
)
EXCLUDED_FILES = {
    POLICY,
    "scripts/ci/write-location-audit.py",
    "scripts/ci/write-location-allow.toml",
}

NAME = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
# `~/.local/state/<name>`, `$HOME/...`, `${HOME}/...`, and the closing brace of
# `${XDG_STATE_HOME:-$HOME/.local/state}/<name>` or `${AGENT_HOME:-...kit}/<sub>`.
STATE_RE = re.compile(
    r"(?:~|\$HOME|\$\{HOME\})/\.local/state\}?/(?P<name>" + NAME + r")"
    r"\}*(?:/(?P<sub>" + NAME + r"))?(?:/(?P<leaf>" + NAME + r"))?"
)
AGENT_HOME_RE = re.compile(
    r"\$\{?AGENT_HOME\}?/(?P<sub>" + NAME + r")(?:/(?P<leaf>" + NAME + r"))?"
)
TMP_RE = re.compile(r"(?<![\w.$}/-])/tmp/(?P<name>" + NAME + r")")

KIT_ROOT = "agent-runtime-kit"
AGENT_HOME_CLASSES = {"out", "build", "tmp", "worktrees"}
OUT_CLASSES = {"projects", "scratch"}

TOOL_STATE_FIX = (
    "tool state: use a tool env override with an ${XDG_STATE_HOME}/<tool> "
    "fallback, or a class under $AGENT_HOME"
)
AGENT_HOME_FIX = (
    "use a declared class: out/projects (evidence), out/scratch, build, tmp, "
    "or worktrees"
)
OUT_FIX = "out/ holds only evidence (out/projects) and scratch (out/scratch); build output uses build/"
TMP_FIX = "tmp: derive from $TMPDIR (mktemp) instead of a fixed /tmp name"


@dataclass(frozen=True)
class Finding:
    path: str
    line_no: int
    literal: str
    fix: str


@dataclass
class AllowEntry:
    path: str
    literal: str | None
    reason: str
    used: bool = False

    def covers(self, finding: Finding) -> bool:
        if not fnmatch.fnmatchcase(finding.path, self.path):
            return False
        return self.literal is None or self.literal == finding.literal


def agent_home_finding(sub: str, leaf: str | None) -> tuple[str, str] | None:
    if sub not in AGENT_HOME_CLASSES:
        return f"$AGENT_HOME/{sub}", AGENT_HOME_FIX
    if sub == "out" and leaf is not None and leaf not in OUT_CLASSES:
        return f"$AGENT_HOME/out/{leaf}", OUT_FIX
    return None


def scan_line(line: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for match in STATE_RE.finditer(line):
        name, sub, leaf = match.group("name", "sub", "leaf")
        if name != KIT_ROOT:
            hits.append((f"~/.local/state/{name}", TOOL_STATE_FIX))
        elif sub is not None:
            hit = agent_home_finding(sub, leaf)
            if hit:
                hits.append(hit)
    for match in AGENT_HOME_RE.finditer(line):
        hit = agent_home_finding(match.group("sub"), match.group("leaf"))
        if hit:
            hits.append(hit)
    for match in TMP_RE.finditer(line):
        hits.append((f"/tmp/{match.group('name')}", TMP_FIX))
    return hits


def tracked_files(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return sorted(
        path
        for path in output.split("\0")
        if path
        and path not in EXCLUDED_FILES
        and not path.startswith(EXCLUDED_PREFIXES)
    )


def scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for relative in tracked_files(root):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            seen: set[str] = set()
            for literal, fix in scan_line(line):
                if literal not in seen:
                    seen.add(literal)
                    findings.append(Finding(relative, line_no, literal, fix))
    return findings


def load_allow(path: Path) -> list[AllowEntry]:
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    entries: list[AllowEntry] = []
    for index, raw in enumerate(data.get("allow", []), start=1):
        glob = raw.get("path")
        reason = str(raw.get("reason", "")).strip()
        literal = raw.get("literal")
        if not isinstance(glob, str) or not glob:
            raise ValueError(f"allow entry {index}: missing path")
        if not reason:
            raise ValueError(f"allow entry {index} ({glob}): missing reason")
        if literal is not None and not isinstance(literal, str):
            raise ValueError(f"allow entry {index} ({glob}): literal must be a string")
        entries.append(AllowEntry(glob, literal, reason))
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--allow-file", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    allow_file = args.allow_file or root / "scripts/ci/write-location-allow.toml"

    try:
        entries = load_allow(allow_file)
    except (ValueError, tomllib.TOMLDecodeError) as error:
        print(f"write-location-audit: invalid allowlist {allow_file}: {error}", file=sys.stderr)
        return 2

    blocked: list[Finding] = []
    for finding in scan(root):
        covering = [entry for entry in entries if entry.covers(finding)]
        for entry in covering:
            entry.used = True
        if not covering:
            blocked.append(finding)
    stale = [entry for entry in entries if not entry.used]

    if not blocked and not stale:
        print(f"write-location-audit: ok ({len(entries)} allowlisted entries)")
        return 0
    print(f"write-location-audit: undeclared agent write locations (see {POLICY})")
    for finding in blocked:
        print(f"  - {finding.path}:{finding.line_no}: {finding.literal}")
        print(f"    fix: {finding.fix}")
    for entry in stale:
        literal = entry.literal or "*"
        print(f"  - stale allowlist entry: {entry.path} {literal}; remove it")
    print(
        "rule: declare a class and an env override instead of a hard-coded path; "
        "allowlist only pre-contract or out-of-scope literals, with a reason."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
