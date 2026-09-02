#!/usr/bin/env python3
"""PreToolUse hook: keep agent artifacts on the allocated route.

`agent-out` is the CLI that allocates a per-project run directory outside the
checkout. It is not a directory name. Agents that read the routing rule as a
directory hand-build `./agent-out/<topic>`, `$AGENT_HOME/agent-out/<topic>`, or
`~/agent-out/<topic>` instead, which leaks artifacts into checkouts and splits
the artifact tree across roots (sympoies/agent-runtime-kit#90).

Repo-local `.cache/` picks up the same spillover. `.cache/agent-validation/` is
the declared `agent-docs` validation marker root and stays allowed; everything
else under a checkout's `.cache/` is scratch that belongs on the allocated
route.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    bash_copy_style_write_targets,
    bash_write_operations,
    command_from,
    effective_workdir,
    emit_block,
    file_paths_from_payload,
    git_toplevel,
    read_payload,
)

FORBIDDEN_SEGMENT = "agent-out"
CACHE_SEGMENT = ".cache"
CACHE_MARKER_SEGMENT = "agent-validation"

ALLOCATION_ROUTE = """Allocate one, then write inside the returned path:
  agent-out project --topic <topic> --mkdir --format json
  -> $AGENT_HOME/out/projects/<owner>__<repo>/<YYYYMMDD-HHMMSS-topic>/

Do not hand-build $AGENT_HOME/out/<topic> or $AGENT_HOME/agent-out/<topic>;
`agent-out` is the command that owns the path, not the directory name.
Owner: core/policies/files-hooks-validation.md"""

AGENT_OUT_REASON = f"""[agent-artifact-routing] Blocked write to an `agent-out` directory: {{path}}
Agent artifacts must live outside the checkout, in an allocated run directory.

{ALLOCATION_ROUTE}"""

CACHE_REASON = f"""[agent-artifact-routing] Blocked scratch write to repo-local `.cache/`: {{path}}
Only `.cache/agent-validation/` is repo-local by design; it holds the
agent-docs validation marker declared in AGENT_DOCS.toml. Other scratch
belongs on the allocated artifact route.

{ALLOCATION_ROUTE}"""


def candidate_paths(payload: dict) -> list[str]:
    paths = file_paths_from_payload(payload)
    if str(payload.get("tool_name", "")) == "Bash":
        command = command_from(payload)
        paths.extend(path for path, _content in bash_write_operations(command))
        paths.extend(bash_copy_style_write_targets(command))
    return paths


def normalized(path: str, workdir: Path) -> Path:
    expanded = os.path.expanduser(path.replace("\\", "/"))
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = workdir / candidate
    return Path(os.path.normpath(str(candidate)))


def is_agent_out_path(path: Path) -> bool:
    return FORBIDDEN_SEGMENT in path.parts


def repo_local_cache_scratch(path: Path, repo_root: Path | None) -> bool:
    """True for a checkout's `.cache/` write outside the marker subtree.

    The XDG cache is not a checkout, so the rule is scoped to the repository
    root rather than matching a bare `.cache` segment anywhere.
    """
    if repo_root is None:
        return False
    cache_root = repo_root / CACHE_SEGMENT
    try:
        relative = path.relative_to(cache_root)
    except ValueError:
        return False
    return relative.parts[:1] != (CACHE_MARKER_SEGMENT,)


def main() -> int:
    payload = read_payload()
    paths = candidate_paths(payload)
    if not paths:
        return ALLOW

    workdir = effective_workdir(payload)
    resolved = [normalized(path, workdir) for path in paths]

    for path in resolved:
        if is_agent_out_path(path):
            emit_block(AGENT_OUT_REASON.format(path=path))
            return ALLOW

    # Only pay for the repository lookup when a `.cache` write is in play.
    if not any(CACHE_SEGMENT in path.parts for path in resolved):
        return ALLOW

    toplevel = git_toplevel(str(workdir))
    repo_root = Path(toplevel) if toplevel else None
    for path in resolved:
        if repo_local_cache_scratch(path, repo_root):
            emit_block(CACHE_REASON.format(path=path))
            return ALLOW

    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
