#!/usr/bin/env python3
"""Guide or require durable project-dev activation at edit boundaries.

Direct-edit targets are canonicalized and checked per repository. Bash is
checked against one provenance-aware command context: a pre-tool hook cannot
observe shell-expanded filesystem destinations reliably, so cross-repository
shell mutations need a host-attested target workdir. Project-dev is advisory by
default, explicitly fail-closed under ``enforce``, and solely bypassed by
``off``. Only an explicitly versioned pre-session ``agent-docs`` release
receives compatibility behavior.

Enforcement is scoped to the boundary that owns the risk. In enforce mode,
repository mutation (direct edits and mutation-capable shell) requires prepared
``project-dev``; advisory mode attempts preparation and preserves work.
Two narrow lanes are admitted without that activation because they cannot mutate
tracked content: an audited read-only inspection allowlist, and trusted
``agent-docs`` preparation/read commands for any declared intent (so a session
that only needs ``memory``/``task-tools``/``browser-test`` is not forced through
unrelated ``project-dev`` policy first). Both lanes fail closed: anything that is
not an exact recognized shape falls through to the mutation gate. The read-only
allowlist is a workflow convenience, not a security sandbox; its residual limits
are documented at ``read_only_general_invocation``.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    SHELL_EFFECT_READ_ONLY,
    SHELL_EFFECT_UNKNOWN,
    apply_patch_paths,
    audited_text_read_invocation,
    classify_shell_effect,
    command_from,
    command_context,
    effective_workdir,
    emit_block,
    env_target_tokens,
    git_toplevel,
    invocation_is_opaque,
    invocation_tokens,
    is_git_recovery_argv,
    patch_text_candidates,
    read_payload,
    session_id_from_payload,
    simple_commands_with_nested_shells,
    tool_input_dict,
)

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"}
COMMAND_TOOLS = {"Bash"}
SESSION_FLOOR = (1, 21, 17)
# Workflow-phase scoping (issue #601 P1 slice 3d). A mutation is verified against
# the phase-scoped project-dev doc subset instead of the whole intent, so an edit
# no longer forces the delivery/review runbooks. Direct edits and generic
# mutation-capable shell are content work (the `edit` phase); the governed
# delivery CLIs are the `delivery` phase. `review` is not gated here (review is
# dispatched through the agent tool, which this hook does not observe); its docs
# are reached through explicit `--phase review` preflight. The flag is only ever
# threaded when the trusted CLI advertises it (see `phase_supported`); otherwise
# the hook falls back to full, no-phase project-dev verification -- and a full
# preparation satisfies every phase-scoped verify, so the fallback is always safe.
PHASE_EDIT = "edit"
PHASE_DELIVERY = "delivery"
# Basenames of the governed delivery CLIs whose invocation is a delivery-phase
# mutation. Everything else (builds, validation runs, generic file writes, and
# any command the shell parser cannot reduce to a simple argv) is edit-phase.
DELIVERY_TOOLS = frozenset({"semantic-commit", "forge-cli", "git-cli"})
# Include Bash pathname expansion and Zsh extended-glob operators so the shell
# cannot execute a different argv than the literal tokens validated below.
UNQUOTED_SHELL_CONTROL = frozenset(";&|<>`$(){}#*?[]^~")
DOUBLE_QUOTED_SHELL_CONTROL = frozenset("`$")

# --- Read-only inspection allowlist -------------------------------------------
#
# Commands here are admitted without project-dev because they cannot mutate
# tracked repository content. Every candidate is first reduced to a single simple
# command by ``simple_shell_words`` (which returns None on ANY shell control:
# pipes, redirections, command/arithmetic substitution, globbing, chaining, or
# quoting it cannot model). That removes the shell-driven write vectors, so the
# remaining audit only has to reject argument-driven writes/exec for each tool.
# The lists stay deliberately tight; an unlisted read-only command is a safe
# false negative (it just falls through to the mutation gate), while an
# over-broad entry would be an unsafe bypass.

# git subcommands with no write mode at all. Excluded on purpose: branch/tag/
# config/remote/stash/notes/worktree/reflog/symbolic-ref (each has a write form),
# and anything under MUTATING_GIT_SUBCOMMANDS elsewhere.
READ_ONLY_GIT_SUBCOMMANDS = frozenset(
    {
        "status",
        "log",
        "show",
        "diff",
        "diff-tree",
        "diff-index",
        "diff-files",
        "rev-parse",
        "rev-list",
        "ls-files",
        "ls-tree",
        "cat-file",
        "blame",
        "describe",
        "show-ref",
        "for-each-ref",
        "shortlog",
        "merge-base",
        "name-rev",
        "whatchanged",
        "count-objects",
        "var",
    }
)
GIT_DIFF_DRIVER_SUBCOMMANDS = frozenset(
    {
        "log",
        "show",
        "diff",
        "diff-tree",
        "diff-index",
        "diff-files",
        "whatchanged",
    }
)
# git global options consumed before the subcommand. Value options take the next
# token; ``-c``/``--config-env``/``--exec-path`` are excluded (config/pager exec
# vectors) so an unknown global option fails closed.
GIT_GLOBAL_VALUE_OPTIONS = frozenset({"-C", "--git-dir", "--work-tree", "--namespace"})
GIT_GLOBAL_FLAG_OPTIONS = frozenset(
    {
        "-P",
        "--no-pager",
        "--paginate",
        "--bare",
        "--no-replace-objects",
        "--literal-pathspecs",
        "--no-literal-pathspecs",
        "--no-optional-locks",
    }
)
# Subcommand flags that write a file (`--output`) or run a pager on matches
# (`-O`/`--open-files-in-pager`, an exec vector for ``git grep``).
GIT_WRITE_OR_EXEC_FLAGS = frozenset(
    {
        "-o",
        "--output",
        "-O",
        "--open-files-in-pager",
        "--ext-diff",
        "--textconv",
    }
)

# gh read-only command groups. `gh api` is excluded: it mutates with
# `-X`/`--method`/`-f`/`--input`. Only view/list-shaped reads are admitted.
GH_READ_ONLY_SUBCOMMANDS: dict[str, frozenset[str]] = {
    "issue": frozenset({"view", "list", "status"}),
    "pr": frozenset({"view", "list", "diff", "checks", "status"}),
    "repo": frozenset({"view", "list"}),
    "run": frozenset({"view", "list"}),
    "workflow": frozenset({"view", "list"}),
    "release": frozenset({"view", "list"}),
    "label": frozenset({"list"}),
    "gist": frozenset({"view", "list"}),
    "cache": frozenset({"list"}),
    "search": frozenset({"issues", "prs", "repos", "code", "commits"}),
}
GH_READ_ONLY_TOPLEVEL = frozenset({"status"})

# Trusted agent-docs preparation/read surface. `session activate` is NOT here: it
# writes activation state and travels the trusted bootstrap path instead.
AGENT_DOCS_GLOBAL_VALUE_OPTIONS = frozenset(
    {"--docs-home", "--project-path", "--worktree-fallback"}
)
AGENT_DOCS_READ_ONLY_SUBCOMMANDS = frozenset(
    {"preflight", "status", "explain", "list", "catalog"}
)
AGENT_DOCS_READ_ONLY_SESSION_SUBCOMMANDS = frozenset({"status", "verify"})
AGENT_DOCS_WRITE_FLAGS = frozenset({"-o", "--output"})
TRUSTED_HELP_EXECUTABLES = frozenset({"agent-docs", "forge-cli"})
HELP_FLAGS = frozenset({"-h", "--help"})
VERSION_FLAGS = frozenset({"-V", "--version"})
DYNAMIC_WORKDIR_CHARACTERS = frozenset("$`*?[{(")
PROJECT_DEV_MODE_ENV = "AGENT_RUNTIME_PROJECT_DEV_MODE"
PROJECT_DEV_MODES = frozenset({"advisory", "enforce", "off"})


def project_dev_mode() -> tuple[str, str | None]:
    """Return explicit mode and a stable warning for invalid launch input."""
    raw = os.environ.get(PROJECT_DEV_MODE_ENV, "").strip()
    if not raw:
        return "advisory", None
    if raw in PROJECT_DEV_MODES:
        return raw, None
    return (
        "advisory",
        "Invalid AGENT_RUNTIME_PROJECT_DEV_MODE; defaulting to advisory. ",
    )


def emit_advisory(message: str, *, mode_warning: str | None = None) -> None:
    """Emit non-blocking provider guidance without retaining private bodies."""
    prefix = mode_warning or ""
    sys.stdout.write(json.dumps({"systemMessage": prefix + message}))
    sys.stdout.write("\n")


def tool_name(payload: Mapping[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def runtime_kit_source_checkout(repo_root: str) -> bool:
    required = (
        "AGENT_DOCS.toml",
        "AGENT_HOME.md",
        os.path.join("manifests", "skills.yaml"),
        os.path.join("scripts", "sync-runtime-surfaces.sh"),
    )
    return all(os.path.isfile(os.path.join(repo_root, path)) for path in required)


def agent_docs_args(repo_root: str, executable: str) -> list[str]:
    args = [executable]
    docs_home = os.environ.get("AGENT_RUNTIME_DOCS_HOME") or os.environ.get(
        "AGENT_DOCS_HOME"
    )
    if not docs_home and runtime_kit_source_checkout(repo_root):
        docs_home = repo_root
    if docs_home:
        args += ["--docs-home", os.path.realpath(docs_home)]
    return args + ["--project-path", repo_root]


def state_home(product: str) -> str:
    override = os.environ.get("AGENT_RUNTIME_STATE_HOME", "").strip()
    if override:
        return os.path.realpath(override)
    product_override = {
        "codex": "CODEX_AGENT_STATE_HOME",
        "claude": "CLAUDE_KIT_STATE_HOME",
    }.get(product, "")
    if product_override:
        value = os.environ.get(product_override, "").strip()
        if value:
            return os.path.realpath(value)
    root = os.environ.get("XDG_STATE_HOME", "").strip()
    if not root:
        root = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.realpath(os.path.join(root, "agent-runtime-kit", product))


def probe_timeout() -> float:
    raw = os.environ.get("AGENT_RUNTIME_AGENT_DOCS_TIMEOUT_SECONDS", "3")
    try:
        return min(max(float(raw), 0.01), 10.0)
    except ValueError:
        return 3.0


def run_probe(args: list[str]) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    try:
        return (
            subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=probe_timeout(),
            ),
            "completed",
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, "crash"


def parsed_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)\.(\d+)(?:\s|$|\()", text)
    if not match:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def session_capability(base_args: list[str]) -> tuple[str, str]:
    completed, outcome = run_probe(base_args + ["session", "--help"])
    if completed is None:
        return "unavailable", f"session-probe-{outcome}"
    if completed.returncode == 0 and "verify" in completed.stdout:
        return "supported", "session-verify-present"

    version_probe, version_outcome = run_probe([base_args[0], "--version"])
    if version_probe is None:
        return "unavailable", f"version-probe-{version_outcome}"
    if version_probe.returncode != 0:
        return "unavailable", "version-probe-nonzero"
    version = parsed_version(version_probe.stdout + "\n" + version_probe.stderr)
    if version is None:
        return "unavailable", "version-probe-malformed"
    if version < SESSION_FLOOR:
        return "legacy", ".".join(str(part) for part in version)
    return "unavailable", "required-session-surface-missing"


def phase_supported(base_args: list[str]) -> bool:
    """Whether the trusted agent-docs advertises the ``--phase`` filter.

    Phase-scoped resolution (issue #601 P1 slice 3d) arrived in a specific
    agent-docs release. Rather than couple the hook to a version number, this
    feature-probes the verify surface: a CLI that lists ``--phase`` under
    ``session verify --help`` supports phase-scoped verification. A
    session-capable but pre-phase release returns ``False`` here, so the hook
    keeps threading the full, no-phase intent and phase-scoping stays inert --
    never a hard error on an older governed runtime.
    """
    completed, _ = run_probe(base_args + ["session", "verify", "--help"])
    if completed is None or completed.returncode != 0:
        return False
    return "--phase" in completed.stdout


def phase_for(tool: str, command_words: list[str] | None) -> str | None:
    """Map an observed mutation to its workflow phase (issue #601 P1 slice 3d).

    Direct edits are content work (``edit``). A shell command that reduces to a
    simple argv is ``delivery`` when its executable basename is a governed
    delivery CLI and ``edit`` otherwise (a build, a validation run, a generic
    file write). A shell command the parser could NOT reduce to a simple argv
    (``command_words is None`` -- pipes, redirection, command substitution, or a
    heredoc) is uninspectable, so it returns ``None`` to fall back to the full,
    no-phase project-dev set. Failing toward the superset -- not the lightest
    edit phase -- is the safe direction when the command cannot be classified: a
    delivery CLI wrapped in a ``$(...)``/heredoc message would otherwise be
    silently under-gated to ``edit`` and skip the delivery runbooks.
    """
    if tool in EDIT_TOOLS:
        return PHASE_EDIT
    if command_words is None:
        return None
    if os.path.basename(command_words[0]) in DELIVERY_TOOLS:
        return PHASE_DELIVERY
    return PHASE_EDIT


def payload_base(payload: Mapping[str, Any]) -> Path:
    # Resolve the command's effective workdir (issue #601 P0-4) so shell
    # enforcement gates the repository the command really runs in, not the hook
    # process cwd. Direct-edit verification stays target-based via edit_paths.
    return effective_workdir(payload).resolve(strict=False)


def nested_edit_paths(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in {"file_path", "path", "filename", "notebook_path"}:
                if isinstance(nested, str) and nested:
                    yield nested
            else:
                yield from nested_edit_paths(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            yield from nested_edit_paths(nested)


def edit_paths(payload: Mapping[str, Any]) -> list[str]:
    paths = list(nested_edit_paths(tool_input_dict(payload)))
    for candidate in patch_text_candidates(payload):
        paths.extend(apply_patch_paths(candidate))
    return list(dict.fromkeys(paths))


def canonical_path(raw: str, base: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def containing_repo(path: Path) -> str | None:
    probe = path if path.is_dir() else path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return git_toplevel(str(probe))


def contains_active_shell_control(command: str) -> bool:
    quote = ""
    escaped = False
    for char in command:
        if quote == "'":
            if char == "'":
                quote = ""
            continue
        if char in "\r\n":
            if quote == '"' and not escaped:
                continue
            return True
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote == '"':
            if char == '"':
                quote = ""
            elif char in DOUBLE_QUOTED_SHELL_CONTROL:
                return True
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in UNQUOTED_SHELL_CONTROL:
            return True
    return False


def simple_shell_words(command: str) -> list[str] | None:
    if not command.strip() or contains_active_shell_control(command):
        return None
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return None
    return words or None


def literal_claim_bootstrap_words(
    command: str, *, current_session: str, capability_file: str
) -> list[str] | None:
    """Expand only the two exact quoted variables in the claim recovery shape."""
    if not current_session or not capability_file:
        return None
    replacements = (
        ('"$AGENT_SESSION_ID"', "__AGENT_SESSION_LITERAL_ID_7F3A__", current_session),
        (
            '"$AGENT_SESSION_CAPABILITY_FILE"',
            "__AGENT_SESSION_LITERAL_CAPABILITY_7F3A__",
            capability_file,
        ),
    )
    sanitized = command
    for literal, sentinel, _value in replacements:
        if sanitized.count(literal) != 1 or sentinel in sanitized:
            return None
        sanitized = sanitized.replace(literal, sentinel)
    words = simple_shell_words(sanitized)
    if not words or words[:3] != ["agent-session", "work-context", "claim"]:
        return None
    values = {sentinel: value for _literal, sentinel, value in replacements}
    return [values.get(word, word) for word in words]


def _skip_value_options(
    tokens: list[str], value_options: frozenset[str]
) -> int:
    """Index of the first token that is not a leading option.

    Consumes value-taking options (``opt value`` and ``opt=value``) and bare
    flag options. Returns ``len(tokens)`` when everything is optional. An
    unrecognized value option is treated as a single token, which is safe here:
    callers reject a non-allowlisted subcommand, so a mis-split only fails
    closed.
    """
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in value_options:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in value_options):
            index += 1
            continue
        if token.startswith("-") and token != "--":
            index += 1
            continue
        break
    return index


def git_read_only_invocation(args: list[str]) -> bool:
    """Whether ``git <args>`` is an audited read-only inspection command."""
    index = 0
    while index < len(args):
        token = args[index]
        if token in GIT_GLOBAL_VALUE_OPTIONS:
            index += 2
            continue
        if any(
            token.startswith(f"{option}=") for option in GIT_GLOBAL_VALUE_OPTIONS
        ):
            index += 1
            continue
        if token in GIT_GLOBAL_FLAG_OPTIONS:
            index += 1
            continue
        if token.startswith("-"):
            # Unknown global option (e.g. -c/--config-env/--exec-path): fail closed.
            return False
        break
    if index >= len(args) or args[index] not in READ_ONLY_GIT_SUBCOMMANDS:
        return False
    subcommand = args[index]
    subcommand_args = args[index + 1 :]
    if subcommand in GIT_DIFF_DRIVER_SUBCOMMANDS and not {
        "--no-ext-diff",
        "--no-textconv",
    }.issubset(subcommand_args):
        return False
    for token in subcommand_args:
        if token == "--":
            break  # remaining tokens are pathspecs, not options
        if token in GIT_WRITE_OR_EXEC_FLAGS:
            return False
        # Reject the `--flag=value` spelling of every write/exec flag. This is
        # not just `--output=<file>`: `--open-files-in-pager=<cmd>` runs an
        # attacker-controlled command through a shell against matched files, so
        # the `=value` form must fail closed exactly like the bare flag.
        if any(token.startswith(f"{flag}=") for flag in GIT_WRITE_OR_EXEC_FLAGS):
            return False
        if token.startswith("-O"):  # -O / -O<pager> short forms
            return False
    return True


def gh_read_only_invocation(args: list[str]) -> bool:
    """Whether ``gh <args>`` is an audited read-only view/list command."""
    if not args or args[0].startswith("-"):
        return False
    group = args[0]
    if group in GH_READ_ONLY_TOPLEVEL:
        return True
    subcommands = GH_READ_ONLY_SUBCOMMANDS.get(group)
    if subcommands is None:
        return False
    return len(args) >= 2 and args[1] in subcommands


def cli_help_or_version_arguments(arguments: list[str]) -> bool:
    """Whether argv can only select a CLI help/version early exit.

    Version is top-level only. Help may follow a positional subcommand path,
    but it must be the final argument; any option before it or argument after it
    stays outside the read-only lane. This admits shapes such as
    ``forge-cli issue create --help`` without treating a merely-present help
    flag as proof that an otherwise operational invocation cannot run.
    """
    if len(arguments) == 1 and arguments[0] in HELP_FLAGS | VERSION_FLAGS:
        return True
    return bool(arguments) and arguments[-1] in HELP_FLAGS and all(
        argument and not argument.startswith("-") and "/" not in argument
        for argument in arguments[:-1]
    )


def _agent_run_exec_workdir(words: list[str]) -> tuple[bool, str | None]:
    """Return ``(has_cwd, static_target)`` for an agent-run exec argv.

    ``static_target`` is ``None`` when a cwd option exists but is duplicated,
    dynamic, malformed, or otherwise unprovable. The caller must fail closed in
    that case rather than verifying the hook-visible repository.
    """
    if (
        len(words) < 3
        or os.path.basename(words[0]) != "agent-run"
        or words[1] != "exec"
    ):
        return False, None
    # Inspect only the wrapper-option prefix. A child command may legitimately
    # own an option named ``--cwd``; arguments after the explicit ``--`` or the
    # first child-command positional cannot change agent-run's own workdir.
    wrapper_end = 2
    while wrapper_end < len(words):
        token = words[wrapper_end]
        if token == "--":
            break
        if token in {"--cwd", "--direnv"}:
            wrapper_end += 2
            continue
        if token.startswith(("--cwd=", "--direnv=")):
            wrapper_end += 1
            continue
        if token in HELP_FLAGS or token.startswith("-"):
            wrapper_end += 1
            continue
        break
    has_cwd = any(
        token == "--cwd" or token.startswith("--cwd=")
        for token in words[2:wrapper_end]
    )
    if not has_cwd:
        return False, None
    target = ""
    index = 2
    while index < len(words):
        token = words[index]
        if token == "--":
            break
        if token == "--cwd":
            if target or index + 1 >= len(words):
                return True, None
            target = words[index + 1]
            index += 2
            continue
        if token.startswith("--cwd="):
            if target:
                return True, None
            target = token.split("=", 1)[1]
            if not target:
                return True, None
            index += 1
            continue
        if token == "--direnv":
            if index + 1 >= len(words):
                return True, None
            index += 2
            continue
        if token.startswith("--direnv="):
            index += 1
            continue
        if token in HELP_FLAGS or token.startswith("-"):
            return True, None
        break
    if not target or any(
        character in target for character in DYNAMIC_WORKDIR_CHARACTERS
    ):
        return True, None
    return True, target


def _agent_run_is_invocation_at(words: list[str], index: int) -> bool:
    """Whether a token is the command reached through supported wrappers."""
    synthetic = words[:index] + [words[index], "--help"]
    invocation = invocation_tokens(synthetic)
    return bool(invocation) and os.path.basename(invocation[0]) == "agent-run"


def _agent_run_workdirs_in_words(words: list[str]) -> list[str | None]:
    targets: list[str | None] = []
    for index, token in enumerate(words):
        if (
            os.path.basename(token) != "agent-run"
            or words[index + 1 : index + 2] != ["exec"]
            or not _agent_run_is_invocation_at(words, index)
        ):
            continue
        has_cwd, target = _agent_run_exec_workdir(words[index:])
        if has_cwd:
            targets.append(target)
    return targets


def _command_changes_workdir(command: str) -> bool:
    """Whether observable wrapper/shell context changes relative-path base."""
    for words in simple_commands_with_nested_shells(command):
        invocation = invocation_tokens(words)
        if invocation and os.path.basename(invocation[0]) in {
            "cd",
            "pushd",
            "popd",
        }:
            return True
        if not any(os.path.basename(token) == "env" for token in words):
            continue
        for token in words:
            if token in {"-C", "--chdir"} or token.startswith(
                ("-C", "--chdir=")
            ):
                return True
    return False


def agent_run_exec_workdirs(command: str) -> list[str | None]:
    """Find statically targeted and unprovable agent-run cwd wrappers.

    Shared shell traversal exposes nested ``bash -c`` payloads. A synthetic
    help invocation reuses the shared wrapper parser to distinguish an actual
    ``env``/``time``/``command``/``exec`` target from text merely passed to
    ``echo``. Opaque split-string forms that mention both the wrapper and cwd
    are conservatively returned as unprovable.
    """
    targets: list[str | None] = []
    relative_base_changed = _command_changes_workdir(command)

    def record(detected: list[str | None]) -> None:
        for target in detected:
            if (
                target is not None
                and relative_base_changed
                and not Path(target).expanduser().is_absolute()
            ):
                targets.append(None)
            else:
                targets.append(target)

    for words in simple_commands_with_nested_shells(command):
        detected = _agent_run_workdirs_in_words(words)
        record(detected)
        # ``env -S '<split string>'`` is parsed by the shared env grammar into
        # a real argv. Inspect that expansion so a string-carried agent-run cwd
        # cannot disappear when the wrapper is reduced to its final command.
        if words and os.path.basename(words[0]) == "env":
            expanded = env_target_tokens(words, 1)
            if expanded and expanded != words:
                record(_agent_run_workdirs_in_words(expanded))
        invocation = invocation_tokens(words)
        if (
            not detected
            and invocation_is_opaque(invocation)
            and "agent-run" in " ".join(words)
            and "--cwd" in " ".join(words)
        ):
            targets.append(None)
    return targets


def read_only_general_invocation(words: list[str]) -> bool:
    """Whether ``words`` is an audited read-only inspection command.

    ``words`` must already be a single simple command (``simple_shell_words``).
    Residual limits, documented deliberately: this function classifies one argv
    stage; the shared effect classifier admits pipe-only composites only when
    every stage passes. Redirections, ``&&``, globbing, unaudited ``rg``/general
    ``sed``/``find``/``sort``/``env`` and other write-or-exec-capable shapes are
    NOT admitted and still require project-dev. The executable must be a bare
    command name resolved via PATH: any path separator (``./grep``, ``bin/ls``)
    is rejected. The caller also resolves a bare name and rejects candidates
    located inside any target repository, so repository-local executable
    shadows cannot enter this lane.
    """
    if not words:
        return False
    # Bare command name only — a path separator means a repo-local executable
    # could run as arbitrary code, so refuse and fall through to the gate.
    if "/" in words[0]:
        return False
    name = words[0]
    args = words[1:]
    if audited_text_read_invocation(words):
        return True
    if name in TRUSTED_HELP_EXECUTABLES:
        return cli_help_or_version_arguments(args)
    if name == "git":
        return git_read_only_invocation(args)
    if name == "gh":
        return gh_read_only_invocation(args)
    return False


def repository_safe_read_only_invocation(
    words: list[str], repositories: list[str]
) -> bool:
    """Apply the read-only argv audit and reject repository-local shadows."""
    if not read_only_general_invocation(words):
        return False
    candidate = shutil.which(words[0])
    if not candidate or not os.path.isabs(candidate):
        return False
    lexical = os.path.abspath(candidate)
    resolved = os.path.realpath(candidate)
    if any(
        path_within(lexical, repository) or path_within(resolved, repository)
        for repository in repositories
    ):
        return False
    if words[0] in TRUSTED_HELP_EXECUTABLES:
        agent_docs = resolved_executable("agent-docs")
        if not agent_docs or not trusted_agent_docs_executable(
            agent_docs, repositories
        ):
            return False
        # nils-cli ships these governed CLIs as one release surface. Requiring
        # the same resolved bin directory prevents an earlier unrelated PATH
        # entry from inheriting the trusted help-only bypass.
        return os.path.dirname(resolved) == os.path.dirname(agent_docs)
    return True


def trusted_release_companion(
    name: str, *, agent_docs_executable: str, repositories: list[str]
) -> str | None:
    """Resolve one nils-cli companion beside the trusted ``agent-docs``.

    Trust has two independent path components: the PATH-selected lexical entry
    must come from the same bin directory as the PATH-selected ``agent-docs``,
    and both entries must resolve into the same release bin directory.  This
    keeps Homebrew's shared ``bin`` symlink surface working while rejecting a
    repository shadow or a foreign directory that merely aliases a trusted
    release binary.
    """
    candidate = shutil.which(name)
    agent_docs_candidate = shutil.which("agent-docs")
    if (
        not candidate
        or not os.path.isabs(candidate)
        or not agent_docs_candidate
        or not os.path.isabs(agent_docs_candidate)
    ):
        return None
    lexical = os.path.abspath(candidate)
    resolved = os.path.realpath(candidate)
    agent_docs_lexical = os.path.abspath(agent_docs_candidate)
    agent_docs_resolved = os.path.realpath(agent_docs_executable)
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return None
    if any(
        path_within(lexical, repository) or path_within(resolved, repository)
        for repository in repositories
    ):
        return None
    if os.path.dirname(lexical) != os.path.dirname(agent_docs_lexical):
        return None
    if os.path.dirname(resolved) != os.path.dirname(agent_docs_resolved):
        return None
    if not trusted_agent_docs_executable(resolved, repositories):
        return None
    return resolved


def trusted_private_input_file(raw: str, repositories: list[str]) -> bool:
    """Accept a canonical absolute regular file outside governed repositories."""
    if not raw or not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        return False
    if os.path.islink(raw) or not os.path.isfile(raw):
        return False
    return not any(path_within(raw, repository) for repository in repositories)


def trusted_private_packet(raw: str, repositories: list[str]) -> bool:
    if not raw.endswith(".json") or not trusted_private_input_file(raw, repositories):
        return False
    try:
        metadata = os.stat(raw, follow_symlinks=False)
    except OSError:
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
    )


def companion_versions_match(first: str, second: str) -> bool:
    first_probe, _ = run_probe([first, "--version"])
    second_probe, _ = run_probe([second, "--version"])
    if (
        first_probe is None
        or second_probe is None
        or first_probe.returncode != 0
        or second_probe.returncode != 0
    ):
        return False
    first_version = parsed_version(first_probe.stdout + "\n" + first_probe.stderr)
    second_version = parsed_version(second_probe.stdout + "\n" + second_probe.stderr)
    return first_version is not None and first_version == second_version


def lifecycle_identifier(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value) is not None


def lifecycle_revision(value: str) -> bool:
    if re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is None:
        return False
    return int(value) <= (2**64 - 1)


def lifecycle_idempotency_key(value: str) -> bool:
    return 8 <= len(value) <= 128 and all(
        character.isascii() and character.isprintable() for character in value
    )


def main_agent_readiness_invocation(
    words: list[str],
    *,
    repositories: list[str],
    agent_docs_executable: str,
    current_session: str,
) -> bool:
    """Admit only the exact non-repository Main Agent Mode bootstrap shapes."""
    if not words:
        return False

    if words[0] == "main-agent":
        main_agent = trusted_release_companion(
            "main-agent",
            agent_docs_executable=agent_docs_executable,
            repositories=repositories,
        )
        agent_session = trusted_release_companion(
            "agent-session",
            agent_docs_executable=agent_docs_executable,
            repositories=repositories,
        )
        capability_file = os.environ.get(
            "AGENT_SESSION_CAPABILITY_FILE", ""
        ).strip()
        if (
            not main_agent
            or not agent_session
            or not companion_versions_match(main_agent, agent_session)
            or not current_session
            or not trusted_private_input_file(capability_file, repositories)
        ):
            return False
        if words == ["main-agent", "--version"]:
            return True
        if words in (
            ["main-agent", "self", "show", "--format", "json"],
            ["main-agent", "rehydrate", "--format", "json"],
            ["main-agent", "rehydrate", "--format", "markdown"],
            ["main-agent", "status", "--format", "json"],
            ["main-agent", "worker", "list", "--format", "json"],
        ):
            return True
        if words[:3] == ["main-agent", "worker", "show"]:
            return (
                len(words) == 6
                and lifecycle_identifier(words[3])
                and words[4:] == ["--format", "json"]
            )
        if words[:2] == ["main-agent", "rebind"]:
            return (
                len(words) == 8
                and words[2] == "--if-revision"
                and lifecycle_revision(words[3])
                and words[4] == "--idempotency-key"
                and lifecycle_idempotency_key(words[5])
                and words[6:] == ["--format", "json"]
            )
        if words[:2] == ["main-agent", "quick"]:
            # quick acquires the work-context claim as its first durable act
            # (like init), so its exact pre-claim shape is admitted here. --tier
            # is optional (default L0).
            if (
                len(words) < 4
                or words[2] != "--assignment-file"
                or not trusted_private_packet(words[3], repositories)
            ):
                return False
            if len(words) == 8:
                return (
                    words[4] == "--idempotency-key"
                    and lifecycle_idempotency_key(words[5])
                    and words[6:] == ["--format", "json"]
                )
            return (
                len(words) == 10
                and words[4] == "--tier"
                and words[5] in ("L0", "L1", "L2", "L3")
                and words[6] == "--idempotency-key"
                and lifecycle_idempotency_key(words[7])
                and words[8:] == ["--format", "json"]
            )
        if (
            len(words) < 4
            or words[:3] != ["main-agent", "init", "--packet-file"]
            or not trusted_private_packet(words[3], repositories)
        ):
            return False
        if len(words) == 9:
            return (
                words[4:6] == ["--if-absent", "--idempotency-key"]
                and lifecycle_idempotency_key(words[6])
                and words[7:] == ["--format", "json"]
            )
        return (
            len(words) == 10
            and words[4] == "--if-revision"
            and lifecycle_revision(words[5])
            and words[6] == "--idempotency-key"
            and lifecycle_idempotency_key(words[7])
            and words[8:] == ["--format", "json"]
        )

    if words[0] == "agent-session":
        if trusted_release_companion(
            "agent-session",
            agent_docs_executable=agent_docs_executable,
            repositories=repositories,
        ) is None:
            return False
        if words == ["agent-session", "--version"]:
            return True
        if words in (
            [
                "agent-session",
                "activity",
                "doctor",
                "--agent",
                "codex",
                "--format",
                "json",
            ],
            [
                "agent-session",
                "activity",
                "doctor",
                "--agent",
                "claude",
                "--format",
                "json",
            ],
            [
                "agent-session",
                "activity",
                "setup",
                "--agent",
                "codex",
                "--repair",
                "--dry-run",
                "--format",
                "json",
            ],
            [
                "agent-session",
                "activity",
                "setup",
                "--agent",
                "claude",
                "--repair",
                "--dry-run",
                "--format",
                "json",
            ],
        ):
            return True
        if words[:3] != [
            "agent-session",
            "work-context",
            "claim",
        ]:
            return False
        tail_index = 7
        if words[7:8] == ["--if-revision"]:
            if len(words) != 15 or not lifecycle_revision(words[8]):
                return False
            tail_index = 9
        elif len(words) != 13:
            return False
        if (
            words[3] != "--session"
            or words[4] != current_session
            or not current_session
            or words[5] != "--file"
            or words[tail_index] != "--capability-file"
            or words[tail_index + 2] != "--idempotency-key"
            or words[tail_index + 4 :] != ["--format", "json"]
        ):
            return False
        capability_file = os.environ.get(
            "AGENT_SESSION_CAPABILITY_FILE", ""
        ).strip()
        if words[tail_index + 1] != capability_file or not trusted_private_input_file(
            capability_file, repositories
        ):
            return False
        if not words[6].endswith(".json") or not trusted_private_input_file(
            words[6], repositories
        ):
            return False
        return (
            re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", words[tail_index + 3]
            )
            is not None
        )

    if words[:2] != ["builtin", "command"] or len(repositories) != 1:
        return False
    agent_run_executable = trusted_release_companion(
        "agent-run",
        agent_docs_executable=agent_docs_executable,
        repositories=repositories,
    )
    if not agent_run_executable:
        return False
    prefix = [
        "builtin",
        "command",
        agent_run_executable,
        "inspect",
        "--cwd",
        os.path.realpath(repositories[0]),
        "--",
    ]
    # ``agent-run inspect`` owns child safety.  This readiness lane validates
    # only the exact trusted outer command and requires a nonempty child argv.
    return len(words) > len(prefix) and words[: len(prefix)] == prefix


def agent_docs_near_miss_invocation(words: list[str]) -> bool:
    """Whether argv resembles a non-writing agent-docs read/preparation call."""
    if not words or os.path.basename(words[0]) != "agent-docs":
        return False
    if any(
        token in AGENT_DOCS_WRITE_FLAGS or token.startswith("--output=")
        for token in words[1:]
    ):
        return False
    if "preflight" in words:
        return True
    return "session" in words and any(
        token in {"prepare", "activate", "verify"} for token in words
    )


def agent_docs_read_only_invocation(words: list[str], executable: str) -> bool:
    """Whether ``words`` is a trusted read-only ``agent-docs`` command.

    Only the resolved trusted executable is admitted (a bare ``agent-docs`` or a
    repo-local shadow is rejected), and only preparation/read subcommands that
    print to stdout. ``session activate`` writes state and is handled by the
    trusted bootstrap path instead.
    """
    if not words or not os.path.isabs(words[0]):
        return False
    if os.path.realpath(words[0]) != os.path.realpath(executable):
        return False
    rest = words[1:]
    if cli_help_or_version_arguments(rest):
        return True
    index = _skip_value_options(rest, AGENT_DOCS_GLOBAL_VALUE_OPTIONS)
    if cli_help_or_version_arguments(rest[index:]):
        return True
    if index < len(rest) and rest[index].startswith("-"):
        # Unknown global option before the subcommand: fail closed.
        return False
    if index >= len(rest):
        return False
    subcommand = rest[index]
    tail = rest[index + 1 :]
    if subcommand == "session":
        if not tail or tail[0] not in AGENT_DOCS_READ_ONLY_SESSION_SUBCOMMANDS:
            return False
        tail = tail[1:]
    elif subcommand not in AGENT_DOCS_READ_ONLY_SUBCOMMANDS:
        return False
    for token in tail:
        if token in AGENT_DOCS_WRITE_FLAGS or token.startswith("--output="):
            return False
    return True


def resolved_executable(name: str) -> str | None:
    candidate = shutil.which(name)
    if not candidate or not os.path.isabs(candidate):
        return None
    resolved = os.path.realpath(candidate)
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return None
    return resolved


def path_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((os.path.realpath(path), os.path.realpath(root))) == os.path.realpath(root)
    except ValueError:
        return False


def release_package_root(executable: str) -> str | None:
    """The versioned release package root of a governed CLI path, if any.

    A Homebrew install version-pins each release under
    ``<prefix>/Cellar/<package>/<version>/bin/<name>``. The package root
    (``<prefix>/Cellar/<package>``) is the identity that survives an upgrade;
    the full path is not.
    """
    resolved = os.path.realpath(executable)
    bin_dir = os.path.dirname(resolved)
    if os.path.basename(bin_dir) != "bin":
        return None
    version_dir = os.path.dirname(bin_dir)
    package_root = os.path.dirname(version_dir)
    if not os.path.basename(version_dir) or not os.path.basename(package_root):
        return None
    return package_root


def same_governed_release(candidate: str, executable: str, repo_root: str) -> bool:
    """Whether ``candidate`` is the active ``executable`` or a superseded sibling.

    The trusted bootstrap prefix embeds the *resolved* agent-docs path, which is
    version-pinned. A mid-session release upgrade repoints the stable
    ``bin/agent-docs`` symlink, so a preparation command replayed from earlier in
    the session still names the superseded release directory. That command is
    the same governed CLI, and rejecting it makes every prepare variant report
    ``agent-docs-bootstrap-shape-mismatch`` -- leaving the edit gate
    unsatisfiable until the session restarts. It is therefore accepted when it
    shares the active release's package root, which is exactly the sibling set
    ``trusted_agent_docs_executable`` already admits. A repository-local shadow
    or a different package is still never a bootstrap.
    """
    if not candidate or not os.path.isabs(candidate):
        return False
    active = os.path.realpath(executable)
    resolved = os.path.realpath(candidate)
    if resolved == active:
        return True
    if os.path.basename(resolved) != os.path.basename(active):
        return False
    if path_within(resolved, repo_root):
        return False
    package_root = release_package_root(candidate)
    return package_root is not None and package_root == release_package_root(
        executable
    )


def activation_base_args(
    *,
    repo_root: str,
    executable: str,
    current_session: str,
    product: str,
    subcommand: str = "activate",
) -> list[str]:
    return agent_docs_args(repo_root, executable) + [
        "session",
        subcommand,
        "--session-id",
        current_session,
        "--product",
        product,
        "--state-home",
        state_home(product),
    ]


def recovery_command(
    *,
    repo_root: str,
    executable: str,
    current_session: str,
    product: str,
    intents: tuple[str, ...] = ("project-dev",),
    phase: str | None = None,
) -> str:
    """Single atomic ``session prepare`` recovery command for the mutation gate.

    P0-3 structured recovery: one command that activates and strict-preflights,
    instead of the older activate-then-separate-preflight pair. When ``phase`` is
    set (issue #601 P1 slice 3d) the recovery is phase-scoped so an edit is told
    to prepare only the edit doc set; the bootstrap parser accepts the trailing
    ``--phase`` so this exact command is recognized and consumed on re-run.
    """
    args = activation_base_args(
        repo_root=repo_root,
        executable=executable,
        current_session=current_session,
        product=product,
        subcommand="prepare",
    )
    for intent in intents:
        args += ["--intent", intent]
    if phase:
        args += ["--phase", phase]
    # `session prepare` defaults to human-readable text, while the hook consumes
    # its stable JSON envelope. Keep the generated recovery executable by making
    # the output contract explicit.
    args += ["--format", "json"]
    return shlex.join(args)


def contract_preflight_command(
    *,
    repo_root: str,
    executable: str,
    intent: str = "project-dev",
    phase: str | None = None,
) -> str:
    """Exact read-only command for the contract a preparation just activated."""
    args = agent_docs_args(repo_root, executable) + [
        "preflight",
        "--intent",
        intent,
    ]
    if phase:
        args += ["--phase", phase]
    return shlex.join(args)


def literal_prepare_target(
    command_words: list[str] | None, *, agent_docs_executable: str
) -> str | None:
    """Canonical project target named by a literal trusted prepare command.

    This bounded extraction intentionally happens before ordinary shell workdir
    selection. It does not admit the command; ``bootstrap_activation_intents``
    still validates the complete identity tuple and exact ordered tail before
    execution. Relative paths, symlink aliases, duplicate project flags, bare or
    shadow executables, and non-prepare commands have no trusted target.
    """
    if (
        not command_words
        or not os.path.isabs(command_words[0])
        or os.path.realpath(command_words[0])
        != os.path.realpath(agent_docs_executable)
        or command_words.count("--project-path") != 1
        or any(word.startswith("--project-path=") for word in command_words)
    ):
        return None
    index = command_words.index("--project-path")
    if index + 1 >= len(command_words):
        return None
    raw = command_words[index + 1]
    if not os.path.isabs(raw) or os.path.realpath(raw) != raw:
        return None
    if command_words[index + 2 : index + 4] != ["session", "prepare"]:
        return None
    repo = git_toplevel(raw)
    if (
        not repo
        or os.path.realpath(repo) != raw
        or not os.path.isfile(os.path.join(raw, "AGENT_DOCS.toml"))
    ):
        return None
    return raw


def recoverable_prepare_parameters(
    command_words: list[str],
    *,
    current_session: str,
    product: str,
    repo_root: str,
    agent_docs_executable: str,
) -> tuple[tuple[str, ...], str | None] | None:
    """Recover intent/phase only from a current-context stale prepare.

    A safely recoverable command has the exact trusted `session prepare`
    prefix for this executable, repository, session, product, and state home.
    Its tail contains only intent pairs, at most one recognized workflow phase,
    and at most one non-JSON format pair (or no format pair). These parameters
    only rebuild the canonical JSON prepare. Enforce mode blocks the mismatched
    command; advisory mode describes the mismatch and lets it execute normally.
    """
    base = activation_base_args(
        repo_root=repo_root,
        executable=agent_docs_executable,
        current_session=current_session,
        product=product,
        subcommand="prepare",
    )
    if not command_words or not same_governed_release(
        command_words[0], agent_docs_executable, repo_root
    ):
        return None
    if command_words[1 : len(base)] != base[1:]:
        return None

    intents: list[str] = []
    phase: str | None = None
    format_seen = False
    index = len(base)
    while index < len(command_words):
        token = command_words[index]
        if token == "--intent" and index + 1 < len(command_words):
            intents.append(command_words[index + 1])
            index += 2
            continue
        if (
            token == "--phase"
            and index + 1 < len(command_words)
            and phase is None
        ):
            candidate = command_words[index + 1]
            if candidate not in {PHASE_EDIT, PHASE_DELIVERY}:
                return None
            phase = candidate
            index += 2
            continue
        if (
            token == "--format"
            and index + 1 < len(command_words)
            and not format_seen
        ):
            if command_words[index + 1] == "json":
                return None
            format_seen = True
            index += 2
            continue
        return None

    if not intents:
        return None
    return tuple(intents), phase


def bootstrap_activation_intents(
    command: str,
    *,
    current_session: str,
    product: str,
    repo_root: str,
    agent_docs_executable: str,
) -> tuple[list[str], list[str], str] | None:
    """Parse a trusted ``session prepare``/``activate`` command for its intents.

    ``session prepare`` is the preferred atomic primitive (activate + strict
    preflight + stable JSON result); ``session activate`` stays recognized for
    backward compatibility. The command must equal the exact expected preparation
    prefix (executable, docs-home/project-path, session-id, product, state-home)
    for one of those subcommands, followed only by one or more ``--intent
    <value>`` pairs, an optional phase, and (for ``prepare``) the required
    ``--format json`` output contract. Any extra flag, reordering, wrong
    session/product/repo/state, bare executable, or shell control makes it not a
    bootstrap, so it falls through to the mutation gate. Undeclared intent
    values are rejected downstream by ``agent-docs`` itself when executed.

    Returns ``(words, intents, subcommand)`` on a match, else ``None``.
    """
    words = simple_shell_words(command)
    if not words:
        return None
    for subcommand in ("prepare", "activate"):
        base = activation_base_args(
            repo_root=repo_root,
            executable=agent_docs_executable,
            current_session=current_session,
            product=product,
            subcommand=subcommand,
        )
        if not same_governed_release(words[0], agent_docs_executable, repo_root):
            continue
        if words[1 : len(base)] != base[1:]:
            continue
        tail = words[len(base) :]
        intents: list[str] = []
        index = 0
        while tail[index : index + 1] == ["--intent"] and index + 1 < len(tail):
            intent = tail[index + 1]
            if not intent or intent in intents:
                break
            intents.append(intent)
            index += 2
        if not intents:
            continue
        if tail[index : index + 1] == ["--phase"]:
            if (
                index + 1 >= len(tail)
                or tail[index + 1] not in {PHASE_EDIT, PHASE_DELIVERY}
            ):
                continue
            index += 2
        if subcommand == "prepare":
            if tail[index:] != ["--format", "json"]:
                continue
        elif index != len(tail):
            continue
        # Canonicalize a superseded release path onto the release installed now,
        # so the hook always probes the current binary even when the command was
        # replayed from before a mid-session upgrade.
        return [agent_docs_executable] + words[1:], intents, subcommand
    return None


def target_repositories(payload: Mapping[str, Any], tool: str) -> list[str]:
    base = payload_base(payload)
    repos: set[str] = set()
    if tool in EDIT_TOOLS:
        paths = edit_paths(payload)
        for raw in paths:
            repo = containing_repo(canonical_path(raw, base))
            if repo:
                repos.add(os.path.realpath(repo))
        if not paths:
            cwd_repo = containing_repo(base)
            if cwd_repo:
                repos.add(os.path.realpath(cwd_repo))
    elif tool in COMMAND_TOOLS:
        cwd_repo = containing_repo(base)
        if cwd_repo:
            repos.add(os.path.realpath(cwd_repo))
    return sorted(
        repo for repo in repos if os.path.isfile(os.path.join(repo, "AGENT_DOCS.toml"))
    )


def trusted_agent_docs_executable(executable: str, repos: list[str]) -> bool:
    executable = os.path.realpath(executable)
    candidate = shutil.which("agent-docs")
    if not candidate or not os.path.isabs(candidate):
        return False
    candidate = os.path.abspath(candidate)
    if any(path_within(candidate, repo_root) for repo_root in repos):
        return False
    configured = os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "")
    if configured:
        roots = [os.path.realpath(item) for item in configured.split(os.pathsep) if item]
        return os.path.realpath(os.path.dirname(candidate)) in roots and not any(
            path_within(executable, repo_root) for repo_root in repos
        )
    for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
        if os.path.dirname(candidate) != os.path.join(prefix, "bin"):
            continue
        if os.path.dirname(executable) == os.path.dirname(candidate):
            return True
        cellar = os.path.join(prefix, "Cellar", "nils-cli")
        if path_within(executable, cellar) and os.path.basename(
            os.path.dirname(executable)
        ) == "bin":
            return True
    return os.path.dirname(candidate) == "/usr/bin" and os.path.dirname(
        executable
    ) == "/usr/bin"


def verify_intent(
    base_args: list[str],
    *,
    current_session: str,
    product: str,
    required_intents: tuple[str, ...] = ("project-dev",),
    phase: str | None = None,
) -> tuple[bool, str]:
    probe_args = base_args + [
        "session",
        "verify",
        "--session-id",
        current_session,
        "--product",
        product,
        "--state-home",
        state_home(product),
    ]
    for intent in required_intents:
        probe_args += ["--require-intent", intent]
    # Phase-scope the verify to the observed mutation's phase (issue #601 P1 slice
    # 3d). agent-docs passes a phase-scoped verify when the matching phase was
    # prepared OR when a full, no-phase preparation exists, so this never blocks
    # an already-fully-prepared session.
    if phase:
        probe_args += ["--phase", phase]
    probe_args += ["--format", "json"]
    completed, outcome = run_probe(probe_args)
    if completed is None:
        return False, f"intent-verification-{outcome}"
    if completed.returncode == 0:
        try:
            body = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return False, "intent-verification-malformed"
        if (
            not isinstance(body, dict)
            or body.get("schema_version") != "cli.agent-docs.session.verify.v1"
            or body.get("ok") is not True
        ):
            return False, "intent-verification-invalid-response"
        data = body.get("data")
        active_intents = data.get("active_intents") if isinstance(data, dict) else None
        if (
            not isinstance(data, dict)
            or data.get("product") != product
            or not isinstance(active_intents, list)
            or any(not isinstance(intent, str) for intent in active_intents)
            or not all(intent in active_intents for intent in required_intents)
            or data.get("verified") is not True
        ):
            return False, "intent-verification-not-verified"
        return True, "verified"
    try:
        body = json.loads(completed.stdout or completed.stderr)
        error = body.get("error") if isinstance(body, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        if isinstance(code, str) and code:
            return False, code
    except (json.JSONDecodeError, TypeError):
        pass
    return False, "intent-not-active-or-stale"


def consume_prepare_result(
    completed: subprocess.CompletedProcess[str],
    *,
    product: str,
    required_intents: tuple[str, ...],
) -> tuple[bool, str]:
    """Validate a trusted ``session prepare`` JSON envelope.

    ``session prepare`` activates and strict-preflights atomically and reports a
    stable ``cli.agent-docs.session.prepare.v1`` result, so a valid ``ok`` +
    ``verified`` envelope on a zero exit means the intents are prepared without a
    second ``session verify`` probe. Returns ``(ok, reason_code)``: on failure the
    code is the CLI's own ``error.code`` when present (e.g. ``preflight-unsatisfied``,
    ``undeclared-intent``) so structured recovery can name the real cause. The
    success path additionally requires a zero exit code, matching the
    ``returncode == 0`` gate on ``verify_intent``'s success path so an anomalous
    ``ok`` envelope on a nonzero exit fails closed.
    """
    try:
        body = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False, "prepare-malformed"
    if (
        not isinstance(body, dict)
        or body.get("schema_version") != "cli.agent-docs.session.prepare.v1"
    ):
        return False, "prepare-invalid-schema"
    if body.get("ok") is not True:
        error = body.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        return False, code if isinstance(code, str) and code else "prepare-not-ok"
    data = body.get("data")
    active_intents = data.get("active_intents") if isinstance(data, dict) else None
    if (
        completed.returncode != 0
        or not isinstance(data, dict)
        or data.get("product") != product
        or not isinstance(active_intents, list)
        or any(not isinstance(intent, str) for intent in active_intents)
        or not all(intent in active_intents for intent in required_intents)
        or data.get("verified") is not True
    ):
        return False, "prepare-not-verified"
    return True, "prepared"


def main() -> int:
    payload = read_payload()
    tool = tool_name(payload)
    if tool not in EDIT_TOOLS | COMMAND_TOOLS:
        return ALLOW
    product = os.environ.get("AGENT_RUNTIME_PRODUCT", "").strip()
    if product not in {"codex", "claude"}:
        return ALLOW
    mode, mode_warning = project_dev_mode()
    if mode == "off":
        return ALLOW

    command = command_from(payload) if tool in COMMAND_TOOLS else ""
    current_session = session_id_from_payload(payload)
    command_words = simple_shell_words(command) if tool in COMMAND_TOOLS else None
    if tool in COMMAND_TOOLS and command_words is None:
        command_words = literal_claim_bootstrap_words(
            command,
            current_session=current_session,
            capability_file=os.environ.get(
                "AGENT_SESSION_CAPABILITY_FILE", ""
            ).strip(),
        )

    agent_docs_executable = resolved_executable("agent-docs")
    prepare_target = (
        literal_prepare_target(
            command_words, agent_docs_executable=agent_docs_executable
        )
        if tool in COMMAND_TOOLS and agent_docs_executable
        else None
    )
    context = command_context(payload) if tool in COMMAND_TOOLS else None
    repos = (
        [prepare_target]
        if prepare_target is not None
        else target_repositories(payload, tool)
    )
    if not repos:
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW

    if tool in COMMAND_TOOLS and len(repos) == 1:
        for nested_workdir in agent_run_exec_workdirs(command):
            if nested_workdir is None:
                message = (
                    "This agent-run exec --cwd target cannot be resolved and attested "
                    "as one typed command context. Run the original command from a "
                    "target-rooted session; no project-dev activation was changed. "
                    "[reason: cross-repository-target-unsupported]"
                )
                if mode == "enforce":
                    emit_block(message)
                else:
                    emit_advisory(
                        message + " Work remains allowed because project-dev is advisory.",
                        mode_warning=mode_warning,
                    )
                return ALLOW
            target_path = canonical_path(nested_workdir, payload_base(payload))
            target_repo = containing_repo(target_path)
            if (
                target_repo
                and os.path.isfile(os.path.join(target_repo, "AGENT_DOCS.toml"))
                and os.path.realpath(target_repo) != os.path.realpath(repos[0])
            ):
                message = (
                    "This shell-embedded agent-run route cannot supply one typed target "
                    "to every mutation-sensitive guard. In Codex, resubmit the original "
                    "command as a standalone tool call whose top-level `workdir` is "
                    f"`{os.path.realpath(target_repo)}`. Do not use shell `cd`, raw "
                    "`git -C`, or nested `agent-run exec --cwd` to retarget it. If the "
                    "host cannot attest that workdir, start or run the original command "
                    f"from a managed session rooted at `{os.path.realpath(target_repo)}`. "
                    "No project-dev activation was changed. "
                    "[reason: cross-repository-target-unsupported]"
                )
                if mode == "enforce":
                    emit_block(message)
                else:
                    emit_advisory(
                        message + " Work remains allowed because project-dev is advisory.",
                        mode_warning=mode_warning,
                    )
                return ALLOW
    # A sole `git <op> --abort`/`--quit` recovery command restores the clean
    # pre-operation state and authors no content, so it must run even when
    # project-dev activation is stale or missing — otherwise a stuck
    # mid-operation checkout cannot be aborted to recover in place.
    # `simple_shell_words` returns None on any shell control, so this stays as
    # exact-match narrow as the activation bootstrap: no operators, pipes,
    # redirections, or nested shells slip through.
    if command_words and is_git_recovery_argv(command_words):
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW
    # Read-only exploration is not a repository mutation. An audited single
    # simple command from the inspection allowlist is admitted without
    # project-dev so pure discussion, diagnosis, and reading do not force
    # implementation policy. This fails closed: anything unrecognized falls
    # through to the mutation gate below.
    read_effect = (
        classify_shell_effect(
            command,
            read_only_invocation=lambda words: repository_safe_read_only_invocation(
                words, repos
            ),
        )
        if tool in COMMAND_TOOLS
        else None
    )
    if read_effect is not None and read_effect.kind == SHELL_EFFECT_READ_ONLY:
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW

    if tool in EDIT_TOOLS and not edit_paths(payload):
        message = (
            "Repository edit target extraction did not produce a canonical target. "
            "Retry with an explicit path. [reason: workdir-attestation-missing]"
        )
        if mode == "enforce":
            emit_block(message)
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW

    # A shell mutation without call-attested workdir metadata cannot be used as
    # a cross-repository verification target. Exact trusted prepare commands are
    # exempt because their literal canonical --project-path is independently
    # bound above before ordinary workdir selection.
    if (
        tool in COMMAND_TOOLS
        and prepare_target is None
        and context is not None
        and not context.attested
    ):
        message = (
            "The shell target lacks matching host workdir attestation. Do not retry "
            "the unchanged Bash call. In Codex, resubmit it as a standalone tool call "
            "whose top-level `workdir` is the target repository. For staging, run "
            "`git add -- <owned-paths>` there, then invoke `semantic-commit` separately. "
            "Do not use shell `cd`, raw `git -C`, or nested `agent-run exec --cwd` to "
            "retarget it. In Codex or Claude, continue from a managed session rooted at "
            "the intended repository when the host cannot attest a target workdir; an "
            "exact-path Edit/Write remains the supported cross-repository file route. "
            "[reason: workdir-attestation-missing]"
        )
        if mode == "enforce":
            emit_block(message)
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW

    if not agent_docs_executable:
        message = (
            "agent-docs capability is unavailable. Restore the governed runtime or "
            "continue from a target-rooted worker. "
            "[reason: project-dev-advisory-unavailable]"
        )
        if mode == "enforce":
            emit_block(
                "agent-docs capability is unavailable for enforced repository mutation; "
                "restore the governed runtime before retrying. "
                "[reason: project-dev-required]"
            )
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW
    if not trusted_agent_docs_executable(agent_docs_executable, repos):
        if command_words and agent_docs_near_miss_invocation(command_words):
            message = (
                "This command resembles an agent-docs read or intent preparation, but "
                "the resolved executable is not a trusted managed agent-docs binary. "
                "Preparing task-tools, memory, browser-test, or another declared intent "
                "does not require project-dev. Use the exact absolute-path command from "
                "the latest intent cue. [reason: agent-docs-command-untrusted]"
            )
            if mode == "enforce":
                emit_block(message)
            else:
                emit_advisory(
                    message + " Work remains allowed because project-dev is advisory.",
                    mode_warning=mode_warning,
                )
            return ALLOW
        message = (
            "A trusted agent-docs executable is unavailable; restore the managed CLI "
            "path or use a target-rooted worker. "
            "[reason: project-dev-advisory-unavailable]"
        )
        if mode == "enforce":
            emit_block(
                "A trusted agent-docs executable is unavailable for this enforced "
                "repository mutation; restore the managed runtime CLI path before "
                "retrying. [reason: project-dev-required]"
            )
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW

    if command_words and main_agent_readiness_invocation(
        command_words,
        repositories=repos,
        agent_docs_executable=agent_docs_executable,
        current_session=current_session,
    ):
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW

    if (
        command_words
        and agent_docs_near_miss_invocation(command_words)
        and (
            not os.path.isabs(command_words[0])
            or os.path.realpath(command_words[0])
            != os.path.realpath(agent_docs_executable)
        )
    ):
        message = (
            "This command resembles an agent-docs read or intent preparation, but "
            "it did not use the resolved trusted agent-docs executable and exact "
            "session context. Preparing task-tools, memory, browser-test, or another "
            "declared intent does not require project-dev. Use the exact absolute-path "
            "command from the latest intent cue. "
            "[reason: agent-docs-command-untrusted]"
        )
        if mode == "enforce":
            emit_block(message)
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW

    # Trusted agent-docs preparation and read commands are admitted for ANY
    # declared intent, without first activating project-dev. This removes the
    # false coupling where a memory/task-tools/browser-test session had to
    # activate and read unrelated project-dev policy before it could prepare its
    # own intent. `session activate` writes state and is handled by the trusted
    # bootstrap below; the read subcommands here only print to stdout.
    if command_words and agent_docs_read_only_invocation(
        command_words, agent_docs_executable
    ):
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW

    primary_agent_docs_args = agent_docs_args(repos[0], agent_docs_executable)
    capability, detail = session_capability(primary_agent_docs_args)
    if capability == "legacy":
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW
    if capability != "supported":
        message = (
            "agent-docs session capability could not be verified "
            f"({detail}). [reason: project-dev-advisory-unavailable]"
        )
        if mode == "enforce":
            emit_block(
                "agent-docs session capability could not be verified and enforced "
                f"repository mutation fails closed ({detail}). "
                "[reason: project-dev-required]"
            )
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW

    if not current_session:
        message = (
            "The mutation payload has no session id; retry from a target-rooted Codex "
            "or Claude session to prepare project-dev. "
            "[reason: project-dev-advisory-unavailable]"
        )
        if mode == "enforce":
            emit_block(
                "Selective intent enforcement is available, but this mutation payload "
                "has no session id. Retry from a Codex or Claude session with session "
                "context. [reason: project-dev-required]"
            )
        else:
            emit_advisory(
                message + " Work remains allowed because project-dev is advisory.",
                mode_warning=mode_warning,
            )
        return ALLOW

    if tool in COMMAND_TOOLS and len(repos) == 1:
        bootstrap = bootstrap_activation_intents(
            command_from(payload),
            current_session=current_session,
            product=product,
            repo_root=repos[0],
            agent_docs_executable=agent_docs_executable,
        )
        if bootstrap is not None:
            bootstrap_args, intents, subcommand = bootstrap
            prepared = ", ".join(intents)
            completed, outcome = run_probe(bootstrap_args)
            if completed is None:
                emit_block(
                    f"Trusted {prepared} preparation failed inside the hook "
                    f"({outcome}); the shell command was consumed and not executed. "
                    "[reason: preparation-run-failed]"
                )
                return ALLOW
            if subcommand == "prepare":
                # Atomic primitive: the prepare envelope already reports
                # activation + strict-preflight verification, so trust it without
                # firing a second `session verify` probe. A failing envelope
                # surfaces the CLI's own error code for structured recovery.
                ok, code = consume_prepare_result(
                    completed, product=product, required_intents=tuple(intents)
                )
                if not ok:
                    emit_block(
                        f"Trusted {prepared} preparation did not verify inside the "
                        f"hook (exit={completed.returncode}); the shell command was "
                        f"consumed and not executed. [reason: {code}]"
                    )
                    return ALLOW
                emit_block(
                    f"Prepared {prepared} inside the hook (verified); the preparation "
                    "command was consumed and completed successfully. Do not run this "
                    "preparation command again. Retry the original command that produced "
                    "the preparation cue. [reason: prepared] [action: retry-original]"
                )
                return ALLOW
            # Backward-compatible `session activate`: run, then verify separately.
            verified, code = verify_intent(
                agent_docs_args(repos[0], agent_docs_executable),
                current_session=current_session,
                product=product,
                required_intents=tuple(intents),
            )
            if completed.returncode != 0 or not verified:
                emit_block(
                    f"Trusted {prepared} activation did not verify inside the hook "
                    f"(exit={completed.returncode}, verification={code}); the shell "
                    "command was consumed and not executed. "
                    "[reason: activation-verify-failed]"
                )
                return ALLOW
            preflight = contract_preflight_command(
                repo_root=repos[0],
                executable=agent_docs_executable,
                intent=intents[0],
            )
            emit_block(
                f"Prepared {prepared} inside the hook (verified); the activation command "
                "was consumed, not re-dispatched. Prefer `session prepare` next time. "
                f"Run `{preflight}` to read the contract, then re-run your command. "
                "[reason: prepared]"
            )
            return ALLOW
        if command_words and agent_docs_near_miss_invocation(command_words):
            recovered = recoverable_prepare_parameters(
                command_words,
                current_session=current_session,
                product=product,
                repo_root=repos[0],
                agent_docs_executable=agent_docs_executable,
            )
            intents, phase = (
                recovered if recovered is not None else (("project-dev",), None)
            )
            if phase is not None and not phase_supported(primary_agent_docs_args):
                phase = None
            canonical_recovery = recovery_command(
                repo_root=repos[0],
                executable=agent_docs_executable,
                current_session=current_session,
                product=product,
                intents=intents,
                phase=phase,
            )
            mismatch = (
                "This trusted agent-docs preparation did not match the exact "
                "executable, repository, session, product, state-home, phase, and "
                "JSON output shape required by the bootstrap and is not treated as "
                "a trusted bootstrap. "
            )
            if mode == "enforce":
                emit_block(
                    mismatch
                    + "The mismatched command was blocked before execution. Retry "
                    f"with `{canonical_recovery}`. "
                    "[reason: agent-docs-bootstrap-shape-mismatch]"
                )
            else:
                emit_advisory(
                    mismatch
                    + "It will execute normally as an ordinary advisory command. To "
                    "submit it as a trusted bootstrap, use "
                    f"`{canonical_recovery}`. Work remains allowed because "
                    "project-dev is advisory. "
                    "[reason: agent-docs-bootstrap-shape-mismatch]",
                    mode_warning=mode_warning,
                )
            return ALLOW

    # Phase-scope the verification to the observed mutation (issue #601 P1 slice
    # 3d) when the trusted CLI advertises `--phase`; otherwise -- or for a shell
    # command the parser cannot inspect (`phase_for` returns None) -- fall back to
    # full, no-phase project-dev. Edits and inspectable generic shell verify the
    # `edit` set; the governed delivery CLIs verify the `delivery` set. A full
    # preparation satisfies every phase verify, so the fallback and an
    # already-fully-prepared session both stay unblocked.
    phase = (
        phase_for(tool, command_words)
        if phase_supported(primary_agent_docs_args)
        else None
    )
    failures: list[tuple[str, str]] = []
    for repo_root in repos:
        verified, code = verify_intent(
            agent_docs_args(repo_root, agent_docs_executable),
            current_session=current_session,
            product=product,
            phase=phase,
        )
        if not verified:
            failures.append((os.path.realpath(repo_root), code))
    if not failures:
        if mode_warning:
            emit_advisory("Work remains allowed.", mode_warning=mode_warning)
        return ALLOW

    if mode == "advisory":
        remaining: list[tuple[str, str]] = []
        prepared_targets: list[str] = []
        for repo_root, verification_code in failures:
            prepare_args = shlex.split(
                recovery_command(
                    repo_root=repo_root,
                    executable=agent_docs_executable,
                    current_session=current_session,
                    product=product,
                    phase=phase,
                )
            )
            completed, outcome = run_probe(prepare_args)
            if completed is None:
                remaining.append((repo_root, f"prepare-{outcome}"))
                continue
            ok, code = consume_prepare_result(
                completed, product=product, required_intents=("project-dev",)
            )
            if ok:
                prepared_targets.append(repo_root)
            else:
                remaining.append((repo_root, code or verification_code))
        if not remaining:
            targets = ", ".join(f"`{target}`" for target in sorted(prepared_targets))
            next_actions = " ".join(
                f"For `{target}`, run `"
                + contract_preflight_command(
                    repo_root=target,
                    executable=agent_docs_executable,
                    phase=phase,
                )
                + "` to read the prepared contract."
                for target in sorted(prepared_targets)
            )
            emit_advisory(
                f"Prepared project-dev for {targets}; the original work remains allowed. "
                f"{next_actions} [reason: prepared] [action: read-contract]",
                mode_warning=mode_warning,
            )
            return ALLOW
        details = "; ".join(
            f"`{repo_root}` ({code})" for repo_root, code in sorted(remaining)
        )
        recoveries = " ".join(
            f"For `{repo_root}`, run `"
            + recovery_command(
                repo_root=repo_root,
                executable=agent_docs_executable,
                current_session=current_session,
                product=product,
                phase=phase,
            )
            + "`."
            for repo_root, _code in sorted(remaining)
        )
        emit_advisory(
            "Project-dev advisory preparation was unavailable for "
            f"{details}. {recoveries} Work remains allowed because project-dev is "
            "advisory. [reason: project-dev-advisory-unavailable]",
            mode_warning=mode_warning,
        )
        return ALLOW

    if (
        read_effect is not None
        and read_effect.kind == SHELL_EFFECT_UNKNOWN
        and len(repos) == 1
    ):
        agent_run_executable = trusted_release_companion(
            "agent-run",
            agent_docs_executable=agent_docs_executable,
            repositories=repos,
        )
        if agent_run_executable:
            inspect_route = (
                "builtin command "
                + shlex.quote(agent_run_executable)
                + " inspect --cwd "
                + shlex.quote(os.path.realpath(repos[0]))
                + " -- <argv...>"
            )
            prepare_route = recovery_command(
                repo_root=repos[0],
                executable=agent_docs_executable,
                current_session=current_session,
                product=product,
                phase=phase,
            )
            emit_block(
                "This shell effect is unknown, so choose exactly one finite route. "
                f"Route 1 (local exploration): `{inspect_route}`. "
                f"Route 2 (exact-target project-dev): run `{prepare_route}`, then "
                "rerun the exact original command. No legacy read-only allowlist "
                "entry was added. [reason: project-dev-required] "
                f"Verification code: {failures[0][1]}."
            )
            return ALLOW
    reason = (
        "This command was not admitted by the audited read-only classifier; no "
        "repository mutation was observed, but this shell shape could not be proven "
        "read-only. Prepare project-dev before retrying. Read-only inspection "
        "and trusted agent-docs preparation for any declared intent are admitted "
        "without project-dev. "
        "Bare agent-docs invocations are intentionally rejected; use the resolved trusted "
        "executable and complete session context. If a Git operation is stuck mid-run, a "
        "sole `git <op> --abort` recovers in place without preparation. "
    )
    for repo_root, code in sorted(failures):
        reason += (
            f"Target `{repo_root}` failed with `{code}`. Run `"
            + recovery_command(
                repo_root=repo_root,
                executable=agent_docs_executable,
                current_session=current_session,
                product=product,
                phase=phase,
            )
            + "`. "
        )
    reason += (
        "Shell enforcement is command-context scoped; use a host-attested workdir for "
        "cross-repository shell work. [reason: project-dev-required]"
    )
    emit_block(reason)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
