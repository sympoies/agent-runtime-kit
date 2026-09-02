#!/usr/bin/env python3
"""Path policy for tool calls: portable doc paths, and agent artifact routing.

Two checks share this handler because a dispatch group has a hard
executable-capability budget and the Bash group was already at it. They are
carried together deliberately, not incidentally: both are path policy, and both
carry the same rule posture (`failure_posture = closed`, `timeout_posture =
warn`, `override_class = locked`), which is what a single rule can express.

- Portable paths: active repo docs and skill docs must not commit
  machine-local home paths. Also runs as a CLI over tracked/staged files.
- Artifact routing: writes must not land in an `agent-out` directory or in
  repo-local `.cache/` scratch outside the sanctioned marker subtree
  (sympoies/agent-runtime-kit#90). Hook mode only.

`SKIP_PORTABLE_PATH_SCAN` is an escape hatch for portable-path false positives.
It deliberately does NOT disable artifact routing: an escape hatch must not
silently switch off a guard it was never meant to cover.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    artifact_routing_block_reason,
    bash_write_operations,
    command_from,
    emit_block,
    patch_text_candidates,
    read_payload,
    tool_input_dict,
)

HOME_PATH_RE = re.compile(
    r"(?P<root>/Users|/home)/(?P<owner>[A-Za-z0-9._-]+)"
    r"(?P<tail>/[^\s`'\"<>)\]}]*)?"
)
TRAILING_PUNCTUATION = ".,;:)]}'\"`"
TEXT_SUFFIXES = {".md", ".mdx", ".rst", ".txt"}
ACTIVE_BASENAMES = {
    "AGENTS.md",
    "AGENT_HOME.md",
    "DEVELOPMENT.md",
    "HEURISTIC_SYSTEM.md",
    "README.md",
    "SKILL.md",
}
ARCHIVAL_PATH_MARKERS = {
    ("docs", "plans"),
    ("docs", "archive"),
    ("out",),
    ("tests",),
}
ALLOWED_LITERAL_PREFIXES = (
    "/home/agent",
    "/home/linuxbrew",
)
MAX_FORMATTED_HITS = 20
BLOCK_TEMPLATE = """portable-paths: machine-local home paths found
{hits}

rule: active repo docs and skill docs should not commit user-specific home paths.
fix: replace user home paths with $HOME/... when the path is intentionally user-relative.
     Use <workspace>/... for evidence paths, or add a narrow allowlist for literal container/runtime paths.
escape hatch: set SKIP_PORTABLE_PATH_SCAN=1 only after verifying a false positive."""


@dataclass(frozen=True)
class Hit:
    file_path: str
    line_no: int | None
    label: str
    sample: str
    suggestion: str


def normalize_slashes(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def path_parts(path: str) -> tuple[str, ...]:
    return tuple(part for part in PurePosixPath(normalize_slashes(path)).parts if part not in ("", "."))


def has_marker(parts: tuple[str, ...], marker: tuple[str, ...]) -> bool:
    if len(parts) < len(marker):
        return False
    for idx in range(0, len(parts) - len(marker) + 1):
        if parts[idx : idx + len(marker)] == marker:
            return True
    return False


def is_active_text_surface(file_path: str) -> bool:
    parts = path_parts(file_path)
    if not parts:
        return False
    if any(has_marker(parts, marker) for marker in ARCHIVAL_PATH_MARKERS):
        return False

    basename = parts[-1]
    if basename in ACTIVE_BASENAMES:
        return True

    suffix = Path(basename).suffix.lower()
    if suffix not in TEXT_SUFFIXES:
        return False
    return any(part in {"docs", "skills", "docker"} for part in parts[:-1])


def is_allowed_literal(sample: str) -> bool:
    return any(sample == prefix or sample.startswith(f"{prefix}/") for prefix in ALLOWED_LITERAL_PREFIXES)


def cleaned_match(raw: str) -> str:
    return raw.rstrip(TRAILING_PUNCTUATION)


def suggestion_for(sample: str) -> str:
    match = HOME_PATH_RE.match(sample)
    if not match:
        return "$HOME/..."
    tail = match.group("tail") or ""
    return f"$HOME{tail}"


def label_for(sample: str) -> str:
    return "macOS home path" if sample.startswith("/Users/") else "Linux home path"


def scan_content(file_path: str, content: str) -> list[Hit]:
    if not is_active_text_surface(file_path):
        return []

    hits: list[Hit] = []
    seen: set[tuple[int, str]] = set()
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in HOME_PATH_RE.finditer(line):
            sample = cleaned_match(match.group(0))
            if not sample or is_allowed_literal(sample):
                continue
            key = (line_no, sample)
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                Hit(
                    file_path=file_path,
                    line_no=line_no,
                    label=label_for(sample),
                    sample=sample,
                    suggestion=suggestion_for(sample),
                )
            )
    return hits


def format_location(hit: Hit) -> str:
    if hit.line_no is None:
        return hit.file_path
    return f"{hit.file_path}:{hit.line_no}"


def format_hits(hits: list[Hit]) -> str:
    lines: list[str] = []
    for hit in hits[:MAX_FORMATTED_HITS]:
        lines.append(f"  - {format_location(hit)}: {hit.label}: {hit.sample}")
        lines.append(f"    fix: use {hit.suggestion}")
    extra = len(hits) - MAX_FORMATTED_HITS
    if extra > 0:
        lines.append(f"  - ... {extra} additional hit(s) omitted")
    return "\n".join(lines)


def emit_hits(hits: list[Hit]) -> None:
    print(BLOCK_TEMPLATE.format(hits=format_hits(hits)))


def proposed_content(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name == "Write":
        return str(tool_input.get("content", ""))
    if tool_name == "Edit":
        return str(tool_input.get("new_string", ""))
    if tool_name == "NotebookEdit":
        return str(tool_input.get("new_source", ""))
    return ""


def added_lines_from_apply_patch(patch_text: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    current_path = ""
    current_is_active = False
    for line in patch_text.splitlines():
        if line.startswith("*** Add File: "):
            current_path = line.removeprefix("*** Add File: ").strip()
            current_is_active = is_active_text_surface(current_path)
            continue
        if line.startswith("*** Update File: "):
            current_path = line.removeprefix("*** Update File: ").strip()
            current_is_active = is_active_text_surface(current_path)
            continue
        if line.startswith("*** Delete File: "):
            current_path = ""
            current_is_active = False
            continue
        if line.startswith("*** Move to: "):
            current_path = line.removeprefix("*** Move to: ").strip()
            current_is_active = is_active_text_surface(current_path)
            continue
        if current_is_active and line.startswith("+") and not line.startswith("+++"):
            lines.append((current_path, line[1:]))
    return lines


def hook_contents_to_scan(payload: dict[str, Any]) -> list[tuple[str, str]]:
    contents: list[tuple[str, str]] = []
    tool_name = str(payload.get("tool_name", ""))
    tool_input = tool_input_dict(payload)

    if tool_name == "Bash":
        for file_path, content in bash_write_operations(command_from(payload)):
            if content and is_active_text_surface(file_path):
                contents.append((file_path, content))
        return contents

    file_path = str(tool_input.get("file_path", ""))
    if file_path and is_active_text_surface(file_path):
        content = proposed_content(tool_name, tool_input)
        if content:
            contents.append((file_path, content))

    for candidate in patch_text_candidates(payload):
        by_path: dict[str, list[str]] = {}
        for file_path, line in added_lines_from_apply_patch(candidate):
            by_path.setdefault(file_path, []).append(line)
        for path, lines in by_path.items():
            contents.append((path, "\n".join(lines)))

    return contents


def run_hook_mode(payload: dict[str, Any], *, skip_portable_paths: bool) -> int:
    # Artifact routing runs first and is not covered by the portable-paths
    # escape hatch; the two checks only share a process, not a switch.
    reason = artifact_routing_block_reason(payload)
    if reason is not None:
        emit_block(reason)
        return ALLOW

    if skip_portable_paths:
        return ALLOW

    hits: list[Hit] = []
    for file_path, content in hook_contents_to_scan(payload):
        hits.extend(scan_content(file_path, content))
    if hits:
        emit_block(BLOCK_TEMPLATE.format(hits=format_hits(hits)))
    return ALLOW


def git_output(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], capture_output=True, check=False)


def tracked_files() -> tuple[int, list[str]]:
    result = git_output(["ls-files", "-z"])
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace").strip(), file=sys.stderr)
        return result.returncode, []
    files = [name for name in result.stdout.decode(errors="replace").split("\0") if name]
    return 0, [name for name in files if is_active_text_surface(name)]


def staged_files() -> tuple[int, list[str]]:
    result = git_output(["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"])
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace").strip(), file=sys.stderr)
        return result.returncode, []
    files = [name for name in result.stdout.decode(errors="replace").split("\0") if name]
    return 0, [name for name in files if is_active_text_surface(name)]


def tracked_content(file_path: str) -> str | None:
    try:
        return Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"error: cannot read {file_path}: {exc}", file=sys.stderr)
        return None


def staged_content(file_path: str) -> str | None:
    result = git_output(["show", f":{file_path}"])
    if result.returncode != 0:
        print(f"error: cannot read staged {file_path}", file=sys.stderr)
        stderr = result.stderr.decode(errors="replace").strip()
        if stderr:
            print(stderr, file=sys.stderr)
        return None
    return result.stdout.decode(errors="replace")


def scan_named_files(files: list[str], *, staged: bool = False) -> tuple[int, list[Hit]]:
    hits: list[Hit] = []
    exit_code = 0
    for file_path in files:
        if not is_active_text_surface(file_path):
            continue
        content = staged_content(file_path) if staged else tracked_content(file_path)
        if content is None:
            exit_code = 2
            continue
        hits.extend(scan_content(file_path, content))
    return exit_code, hits


def run_tracked_mode() -> int:
    rc, files = tracked_files()
    if rc != 0:
        return 2
    scan_rc, hits = scan_named_files(files)
    if hits:
        emit_hits(hits)
        return 1
    if scan_rc != 0:
        return scan_rc
    print(f"portable-paths: scanned {len(files)} active tracked file(s), clean")
    return 0


def run_staged_mode() -> int:
    rc, files = staged_files()
    if rc != 0:
        return 2
    scan_rc, hits = scan_named_files(files, staged=True)
    if hits:
        emit_hits(hits)
        return 1
    if scan_rc != 0:
        return scan_rc
    print(f"portable-paths: scanned {len(files)} active staged file(s), clean")
    return 0


def run_paths_mode(paths: list[str]) -> int:
    scan_rc, hits = scan_named_files(paths)
    if hits:
        emit_hits(hits)
        return 1
    if scan_rc != 0:
        return scan_rc
    print(f"portable-paths: scanned {len(paths)} file(s), clean")
    return 0


def main() -> int:
    skip_portable_paths = os.environ.get("SKIP_PORTABLE_PATH_SCAN") == "1"

    # Hook mode is entered before the escape hatch can short-circuit, because
    # artifact routing is not what that hatch exists to waive.
    if len(sys.argv) == 1:
        return run_hook_mode(read_payload(), skip_portable_paths=skip_portable_paths)

    if skip_portable_paths:
        print("[skipped:portable-paths]", file=sys.stderr)
        return 0

    parser = argparse.ArgumentParser(
        description="Scan active docs and skill docs for machine-local home paths.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tracked", action="store_true", help="Scan active tracked files.")
    group.add_argument("--staged", action="store_true", help="Scan active staged files.")
    group.add_argument("--paths", nargs="+", metavar="FILE", help="Scan specific files.")
    args = parser.parse_args()

    if args.tracked:
        return run_tracked_mode()
    if args.staged:
        return run_staged_mode()
    paths: list[str] = args.paths
    return run_paths_mode(paths)


if __name__ == "__main__":
    sys.exit(main())
