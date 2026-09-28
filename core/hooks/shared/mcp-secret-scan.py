#!/usr/bin/env python3
"""Scan `.mcp.json` changes for secrets and absolute home paths."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    bash_copy_style_write_targets,
    bash_write_operations,
    command_from,
    emit_block,
    invocation_tokens,
    patch_text_candidates,
    read_payload,
    simple_commands_with_nested_shells,
    tool_input_dict,
)

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{16,}\b")),
    ("GitHub PAT", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("GitLab PAT", re.compile(r"\bglpat-[A-Za-z0-9_-]{16,}\b")),
    ("Slack bot token", re.compile(r"\bxoxb-[A-Za-z0-9-]{10,}\b")),
    ("Slack user token", re.compile(r"\bxoxp-[A-Za-z0-9-]{10,}\b")),
    ("xAI key", re.compile(r"\bxai-[A-Za-z0-9_-]{16,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # A bare 40-character run also matches git SHAs and hex digests, so an AWS
    # secret is recognized only next to its key name (the nils-scrub approach
    # of key/value context rather than a context-free run).
    (
        "AWS secret key",
        re.compile(
            r"(?i)(?:aws[_-]?secret[_-]?(?:access[_-]?)?key|secret[_-]?access[_-]?key)"
            # `:` / `=` separate a key from its value; `,` separates a CLI flag
            # from its value in a JSON args array (`"--flag", "<value>"`).
            r"[\"']?\s*[:=,]\s*[\"']?[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"
        ),
    ),
    ("Private key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("age secret key", re.compile(r"\bAGE-SECRET-KEY-1[0-9A-Z]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b")),
    ("Google OAuth token", re.compile(r"\bya29\.[A-Za-z0-9_-]{10,}\b")),
    ("Bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9\-_.=]{8,}")),
    ("macOS home path", re.compile(r"/Users/[^/\s\"']+/")),
    ("Linux home path", re.compile(r"/home/[^/\s\"']+/")),
)

BLOCK_TEMPLATE = (
    "MCP config change blocked for {paths}: detected secret or absolute-path pattern(s):\n"
    "{hits}\n\n"
    "rule: AGENTS.md requires MCP config to avoid secrets and machine-local "
    "absolute paths.\n"
    "fix: move machine-local values to ignored local config for the active "
    "tool.\n"
    "escape hatch: set SKIP_MCP_SCAN=1 only after verifying a false positive."
)
UNKNOWN_CONTENT_BLOCK_TEMPLATE = (
    "MCP config change blocked for {paths}: Bash-authored write target is protected, "
    "but the hook could not inspect the proposed content.\n\n"
    "rule: AGENTS.md requires MCP config to avoid secrets and machine-local "
    "absolute paths.\n"
    "fix: use Write/Edit for MCP config updates so the scanner can inspect the "
    "content, or scan the source file before copying it.\n"
    "escape hatch: set SKIP_MCP_SCAN=1 only after verifying a false positive."
)


def scan(content: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, pattern in PATTERNS:
        if name in seen:
            continue
        match = pattern.search(content)
        if match:
            seen.add(name)
            hits.append((name, match.group(0)))
    return hits


def masked_sample(sample: str) -> str:
    if sample.startswith("/Users/") or sample.startswith("/home/"):
        return "<absolute home path>"
    return "<redacted>"


def format_hits(hits: list[tuple[str, str]]) -> str:
    return "\n".join(f"  - {name}: {masked_sample(sample)}" for name, sample in hits)


def is_mcp_json(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    parts = PurePosixPath(normalized).parts
    if not parts:
        return False
    if parts[-1] == ".mcp.json":
        return True
    if parts == ("mcp.json",):
        return True
    return len(parts) >= 2 and parts[-2:] in {
        (".vscode", "mcp.json"),
        (".cursor", "mcp.json"),
    }


def display_mcp_path(file_path: str) -> str:
    normalized = file_path.replace("\\", "/")
    match = re.match(r"^(/Users|/home)/[^/]+(?P<tail>/.*)?$", normalized)
    if match:
        tail = match.group("tail") or ""
        normalized = "$HOME" + tail
    parts = PurePosixPath(normalized).parts
    if parts and parts[-1] == ".mcp.json":
        return ".mcp.json" if not normalized.startswith("$HOME/") else "$HOME/.../.mcp.json"
    if len(parts) >= 2 and parts[-2:] == (".vscode", "mcp.json"):
        return (
            ".vscode/mcp.json"
            if not normalized.startswith("$HOME/")
            else "$HOME/.../.vscode/mcp.json"
        )
    if len(parts) >= 2 and parts[-2:] == (".cursor", "mcp.json"):
        return (
            ".cursor/mcp.json"
            if not normalized.startswith("$HOME/")
            else "$HOME/.../.cursor/mcp.json"
        )
    if parts == ("mcp.json",):
        return "mcp.json"
    return normalized


def format_paths(paths: list[str]) -> str:
    seen: list[str] = []
    for path in paths:
        display = display_mcp_path(path)
        if display not in seen:
            seen.append(display)
    return ", ".join(seen)


def remote_name_target(url: str, output_dir: str | None = None) -> str | None:
    without_fragment = url.split("#", 1)[0]
    without_query = without_fragment.split("?", 1)[0].rstrip("/")
    name = PurePosixPath(without_query.replace("\\", "/")).name
    if not name:
        return None
    if output_dir:
        return f"{output_dir.rstrip('/')}/{name}"
    return name


def curl_unknown_mcp_write_targets(invocation: list[str]) -> list[str]:
    targets: list[str] = []
    explicit_targets: list[str] = []
    urls: list[str] = []
    remote_name = False
    output_dir: str | None = None
    index = 1
    while index < len(invocation):
        token = invocation[index]
        if token in {"-o", "--output"} and index + 1 < len(invocation):
            explicit_targets.append(invocation[index + 1])
            index += 2
        elif token.startswith("--output="):
            explicit_targets.append(token.split("=", 1)[1])
            index += 1
        elif token.startswith("-o") and token != "-o":
            explicit_targets.append(token[2:])
            index += 1
        elif token == "--output-dir" and index + 1 < len(invocation):
            output_dir = invocation[index + 1]
            index += 2
            continue
        elif token.startswith("--output-dir="):
            output_dir = token.split("=", 1)[1]
            index += 1
            continue
        elif token in {"-O", "--remote-name", "--remote-name-all"} or (
            token.startswith("-") and not token.startswith("--") and "O" in token[1:]
        ):
            remote_name = True
            index += 1
            continue
        elif token == "--url" and index + 1 < len(invocation):
            urls.append(invocation[index + 1])
            index += 2
        elif token.startswith("--url="):
            urls.append(token.split("=", 1)[1])
            index += 1
        elif token.startswith("-") and token != "-":
            index += 1
            continue
        else:
            urls.append(token)
            index += 1
    targets.extend(target for target in explicit_targets if is_mcp_json(target))
    if remote_name:
        for url in urls:
            target = remote_name_target(url, output_dir)
            if target and is_mcp_json(target):
                targets.append(target)
    return targets


def wget_unknown_mcp_write_targets(invocation: list[str]) -> list[str]:
    targets: list[str] = []
    explicit_target = False
    directory_prefix: str | None = None
    urls: list[str] = []
    spider = False
    index = 1
    while index < len(invocation):
        token = invocation[index]
        value: str | None = None
        if token in {"-O", "--output-document"} and index + 1 < len(invocation):
            value = invocation[index + 1]
            explicit_target = True
            index += 2
        elif token.startswith("--output-document="):
            value = token.split("=", 1)[1]
            explicit_target = True
            index += 1
        elif token.startswith("-O") and token != "-O":
            value = token[2:]
            explicit_target = True
            index += 1
        elif token in {"-P", "--directory-prefix"} and index + 1 < len(invocation):
            directory_prefix = invocation[index + 1]
            index += 2
            continue
        elif token.startswith("--directory-prefix="):
            directory_prefix = token.split("=", 1)[1]
            index += 1
            continue
        elif token.startswith("-P") and token != "-P":
            directory_prefix = token[2:]
            index += 1
            continue
        elif token == "--spider":
            spider = True
            index += 1
            continue
        elif token.startswith("-") and token != "-":
            index += 1
            continue
        else:
            urls.append(token)
            index += 1
        if value and is_mcp_json(value):
            targets.append(value)
    if not explicit_target and not spider:
        for url in urls:
            target = remote_name_target(url, directory_prefix)
            if target and is_mcp_json(target):
                targets.append(target)
    return targets


def bash_unknown_mcp_write_targets(command: str) -> list[str]:
    targets = [target for target in bash_copy_style_write_targets(command) if is_mcp_json(target)]
    for simple_command in simple_commands_with_nested_shells(command, strip_heredocs=True):
        invocation = invocation_tokens(simple_command)
        if not invocation:
            continue
        name = PurePosixPath(invocation[0]).name
        if name == "curl":
            targets.extend(curl_unknown_mcp_write_targets(invocation))
        elif name == "wget":
            targets.extend(wget_unknown_mcp_write_targets(invocation))
    return targets


def proposed_content(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name == "Write":
        return str(tool_input.get("content", ""))
    if tool_name == "Edit":
        return str(tool_input.get("new_string", ""))
    if tool_name == "NotebookEdit":
        return str(tool_input.get("new_source", ""))
    return ""


def added_mcp_lines_from_apply_patch(patch_text: str) -> list[str]:
    lines: list[str] = []
    current_is_mcp = False
    for line in patch_text.splitlines():
        if line.startswith("*** Add File: "):
            current_is_mcp = is_mcp_json(line.removeprefix("*** Add File: ").strip())
            continue
        if line.startswith("*** Update File: "):
            current_is_mcp = is_mcp_json(line.removeprefix("*** Update File: ").strip())
            continue
        if line.startswith("*** Delete File: "):
            current_is_mcp = False
            continue
        if line.startswith("*** Move to: "):
            current_is_mcp = is_mcp_json(line.removeprefix("*** Move to: ").strip())
            continue
        if current_is_mcp and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return lines


def hook_contents_to_scan(payload: dict[str, Any]) -> tuple[list[tuple[str, str]], list[str]]:
    contents: list[tuple[str, str]] = []
    unknown_paths: list[str] = []
    tool_name = str(payload.get("tool_name", ""))
    tool_input = tool_input_dict(payload)

    if tool_name == "Bash":
        for file_path, content in bash_write_operations(command_from(payload)):
            if not is_mcp_json(file_path):
                continue
            if content:
                contents.append((file_path, content))
            else:
                unknown_paths.append(file_path)
        unknown_paths.extend(bash_unknown_mcp_write_targets(command_from(payload)))
        return contents, unknown_paths

    file_path = str(tool_input.get("file_path", ""))
    if is_mcp_json(file_path):
        content = proposed_content(tool_name, tool_input)
        if content:
            contents.append((file_path, content))

    for candidate in patch_text_candidates(payload):
        added_lines = added_mcp_lines_from_apply_patch(candidate)
        if added_lines:
            contents.append((".mcp.json", "\n".join(added_lines)))

    return contents, unknown_paths


def run_hook_mode() -> int:
    payload = read_payload()
    hits: list[tuple[str, str]] = []
    paths: list[str] = []
    contents, unknown_paths = hook_contents_to_scan(payload)
    for file_path, content in contents:
        if file_path not in paths:
            paths.append(file_path)
        hits.extend(scan(content))
    if hits:
        reason = BLOCK_TEMPLATE.format(paths=format_paths(paths), hits=format_hits(hits))
        emit_block(reason)
    elif unknown_paths:
        reason = UNKNOWN_CONTENT_BLOCK_TEMPLATE.format(paths=format_paths(unknown_paths))
        emit_block(reason)
    return ALLOW


def staged_mcp_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        print(f"error: git diff failed: {stderr}", file=sys.stderr)
        return []
    names = [name for name in result.stdout.decode(errors="replace").split("\0") if name]
    return [name for name in names if is_mcp_json(name)]


def staged_content(file_path: str) -> str | None:
    result = subprocess.run(["git", "show", f":{file_path}"], capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        print(f"error: cannot read staged {file_path}: {stderr}", file=sys.stderr)
        return None
    return result.stdout.decode(errors="replace")


def run_staged_mode() -> int:
    files = staged_mcp_files()
    if not files:
        print("mcp-scan: no staged .mcp.json files")
        return 0

    exit_code = 0
    for file_path in files:
        content = staged_content(file_path)
        if content is None:
            exit_code = 2
            continue
        hits = scan(content)
        if hits:
            print(f"mcp-scan: secrets / absolute paths in staged {file_path}:")
            print(format_hits(hits))
            exit_code = 1
    if exit_code == 0:
        print(f"mcp-scan: scanned {len(files)} staged .mcp.json file(s), clean")
    return exit_code


def run_paths_mode(paths: list[str]) -> int:
    exit_code = 0
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            print(f"error: not a file: {raw_path}", file=sys.stderr)
            exit_code = 2
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"error: cannot read {raw_path}: {exc}", file=sys.stderr)
            exit_code = 2
            continue
        hits = scan(content)
        if hits:
            print(f"mcp-scan: secrets / absolute paths in {raw_path}:")
            print(format_hits(hits))
            exit_code = 1
    if exit_code == 0:
        print(f"mcp-scan: scanned {len(paths)} file(s), clean")
    return exit_code


def main() -> int:
    if os.environ.get("SKIP_MCP_SCAN") == "1":
        if len(sys.argv) > 1:
            print("[skipped:mcp-scan]", file=sys.stderr)
        return 0

    if len(sys.argv) == 1:
        return run_hook_mode()

    parser = argparse.ArgumentParser(
        description="Scan .mcp.json for secrets and absolute home paths.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="Scan staged .mcp.json files.")
    group.add_argument("--paths", nargs="+", metavar="FILE", help="Scan specific paths.")
    args = parser.parse_args()

    if args.staged:
        return run_staged_mode()
    paths: list[str] = args.paths
    return run_paths_mode(paths)


if __name__ == "__main__":
    sys.exit(main())
