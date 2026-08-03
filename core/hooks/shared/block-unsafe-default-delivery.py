#!/usr/bin/env python3
"""PreToolUse hook: keep default-branch delivery on governed routes.

PR delivery remains the default. A maintainer-authorized L0 direct-main change
is authored as one signed commit on a non-default managed worktree and is
delivered through ``forge-cli repo push-default``. A separately authorized L0
default-branch task may use ``semantic-commit default-branch`` to author one
signed local-only commit in the primary checkout. This hook blocks raw shell
paths that would otherwise bypass either contract.

This is a mechanical guardrail, not a shell sandbox. Provider branch rules and
the forge-cli expected-base/signature/read-back contract remain authoritative.

Default-branch ``merge`` and ``pull`` are classified as ref-moving effects, not
merely by the branch name. Raw invocations remain refused even with
``--ff-only`` because remote-tracking refs and local pull sources cannot prove
publication. ``git-cli sync-default`` owns the remote-bound fast-forward.

A blocked verdict names what it resolved and what failed, because an agent that
cannot see the discriminator cannot fix the invocation. Every reason leads with
``[default-delivery: blocked]`` for a proven violation or
``[default-delivery: unverified]`` for one that could not be classified — only
the second is worth restating — and names the governed surface for the operation
that was actually attempted. ``semantic-commit`` is
classified against the repository it actually commits in: ``--repo`` binds that
target outright. A bare authoring invocation after any earlier shell command
fails closed because executable resolution may have changed; use a separate
tool call with the target checkout as its top-level workdir. Raw Git still fails closed after
any shell-context change. Where the target
remains unresolvable, one command may state a reason inline as
``AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER=<reason> semantic-commit ...``; that
admits only the unresolvable class, only for the governed CLI that re-verifies
worktree, branch, expected head, staging, and signing itself, and only for the
command it is written on. A proven default-branch target never waives.
"""

from __future__ import annotations

import fnmatch
import os
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    OPAQUE_NESTED_SHELL_COMMAND,
    OPAQUE_WRAPPER_COMMAND,
    command_from,
    effective_workdir,
    emit_block,
    env_split_expanded_tokens,
    invocation_is_unresolved_nested,
    invocation_tokens,
    is_managed_cli_home_bin,
    is_assignment,
    nested_shell_payload,
    opaque_invocation_candidates,
    read_payload,
    semantic_commit_invocation_effects,
    semantic_commit_invocation_state,
    simple_commands_with_nested_shells,
)

# A refusal is only actionable if the caller can tell "this is forbidden" from
# "restate this so it can be checked", because only the second is worth retrying
# with a different command shape. These markers lead every reason so that
# distinction survives truncation and is greppable.
MARK_BLOCKED = "[default-delivery: blocked]"
MARK_UNVERIFIED = "[default-delivery: unverified]"
POLICY = (
    "Do not author or push an agent change on the default branch through a raw "
    "shell path. PR delivery is the default. When the maintainer explicitly "
    "authorized direct-main delivery in the current task, author one signed "
    "commit in a non-default managed worktree and use `forge-cli repo "
    "push-default` with the expected base and reason file. When default-branch "
    "completion was explicitly authorized instead, use the exact governed "
    "`semantic-commit default-branch` receipt flow."
)
BLOCK_REASON = f"{MARK_BLOCKED} {POLICY}"
AMBIGUOUS_PREFIX = (
    f"{MARK_UNVERIFIED} Default-branch delivery target could not be resolved safely."
)
AMBIGUOUS_REASON = f"{AMBIGUOUS_PREFIX} {POLICY}"
# Remedies name the governed surface for the operation that was actually
# attempted. Offering `forge-cli repo push-default` for a feature-branch push is
# a non-substitute: it publishes the default branch, which is not what was asked.
REMEDY_FEATURE_PUSH = (
    "To publish a branch, use `git-cli push`: it pins the destination to "
    "`refs/heads/<branch>:refs/heads/<branch>`, so `push.default`, "
    "`remote.pushDefault`, and configured push refspecs cannot move it, and it "
    "refuses the default branch. Example: `git-cli push --format json`. A raw "
    "push is classifiable only when it spells the destination out, as in "
    "`git push origin feat/topic:feat/topic`. Publishing the default branch "
    "itself is `forge-cli repo push-default`, never a raw push."
)
REMEDY_SYNC_DEFAULT = (
    "To advance the local default branch onto a commit already on its remote, "
    "use `git-cli sync-default`. Example: `git-cli sync-default --format json`. "
    "Raw `git merge` and `git pull` cannot prove publication from local state "
    "and remain refused even with `--ff-only`."
)
REMEDY_SHELL_CONTEXT = (
    "A `cd`, `pushd`, `source`, or Git environment assignment earlier in this "
    "command line moves the Git context, so nothing after it can be classified. "
    "Run the Git command on its own with an explicit repository. Example: "
    "`git -C /absolute/path push origin feat/topic`."
)
# A one-shot waiver is spelled on the command it admits, never exported, so it
# cannot outlive that invocation and stays visible in the transcript. It admits
# only an unresolvable `semantic-commit` target, where the governed CLI still
# re-verifies the worktree, branch, expected head, staging, and signing.
WAIVER_ASSIGNMENT_NAME = "AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER"
# Must equal nils-cli's MIN_DELIVERY_WAIVER_LENGTH. A lower value here would
# admit a delivery whose reason the receipt then refuses to record.
MINIMUM_WAIVER_REASON_LENGTH = 12
CONTROL_CHARACTERS = frozenset(
    chr(codepoint)
    for start, stop in ((0x00, 0x20), (0x7F, 0xA0))
    for codepoint in range(start, stop)
)
WAIVER_HINT = (
    "When the target cannot be made resolvable, state a reason of at least "
    f"{MINIMUM_WAIVER_REASON_LENGTH} characters of text on this one command as "
    f"`{WAIVER_ASSIGNMENT_NAME}=<reason> semantic-commit ...`; an exported "
    "variable is not accepted, and the reason is recorded in the receipt as "
    "`data.delivery_waiver`."
)
REPO_HINT = (
    "Pass `--repo <absolute path>` when the target repository is not the tool "
    "workdir; it binds the target without depending on shell state."
)
GOVERNED_CONTEXT_EXECUTABLES = frozenset({"git", "semantic-commit"})
DIRECTORY_EXPANSION_CHARACTERS = "$`*?[]~"
GIT_OPTIONS_WITH_VALUE = frozenset(
    {"-C", "-c", "--config-env", "--exec-path", "--git-dir", "--namespace", "--work-tree"}
)
GIT_OPTIONS_WITH_VALUE_PREFIXES = (
    "--config-env=",
    "--exec-path=",
    "--git-dir=",
    "--namespace=",
    "--work-tree=",
)
GIT_REPOSITORY_CONTEXT_OPTIONS = frozenset(
    {"--git-dir", "--namespace", "--work-tree"}
)
GIT_REPOSITORY_CONTEXT_PREFIXES = (
    "--git-dir=",
    "--namespace=",
    "--work-tree=",
)
GIT_REPOSITORY_CONTEXT_FLAGS = frozenset({"--bare"})
GIT_CONFIG_ENVIRONMENT_NAMES = frozenset(
    {"HOME", "XDG_CONFIG_DIRS", "XDG_CONFIG_HOME"}
)
ENV_CONTEXT_OPTIONS = frozenset(
    {"-C", "-P", "-S", "--chdir", "--path", "--split-string"}
)
ENV_CONTEXT_OPTION_PREFIXES = (
    "--chdir=",
    "--path=",
    "--split-string=",
)
GIT_NON_DELIVERY_COMMANDS_BASELINE = frozenset(
    {
        "add",
        "am",
        "annotate",
        "apply",
        "archive",
        "bisect",
        "blame",
        "branch",
        "bundle",
        "cat-file",
        "checkout",
        "cherry",
        "cherry-pick",
        "clean",
        "clone",
        "commit",
        "config",
        "describe",
        "diff",
        "difftool",
        "fetch",
        "for-each-ref",
        "format-patch",
        "fsck",
        "gc",
        "grep",
        "hash-object",
        "help",
        "init",
        "log",
        "ls-files",
        "ls-remote",
        "ls-tree",
        "maintenance",
        "merge",
        "mergetool",
        "mv",
        "name-rev",
        "notes",
        "pull",
        "range-diff",
        "rebase",
        "reflog",
        "remote",
        "repack",
        "replace",
        "reset",
        "restore",
        "rev-list",
        "rev-parse",
        "revert",
        "rm",
        "shortlog",
        "show",
        "show-ref",
        "sparse-checkout",
        "stash",
        "status",
        "submodule",
        "switch",
        "symbolic-ref",
        "tag",
        "update-index",
        "update-ref",
        "verify-commit",
        "verify-tag",
        "whatchanged",
        "worktree",
    }
)
SHELL_CONTEXT_COMMANDS = frozenset({".", "cd", "popd", "pushd", "source"})
SHELL_BUILTIN_UNWRAP_LIMIT = 8
PUSH_OPTIONS_WITH_VALUE = frozenset(
    {"--exec", "--push-option", "--receive-pack", "--repo", "-o"}
)
PUSH_OPTIONS_WITH_VALUE_PREFIXES = (
    "--exec=",
    "--force-with-lease=",
    "--push-option=",
    "--receive-pack=",
    "--repo=",
    "--signed=",
)
GIT_PROBE_TIMEOUT_SECONDS = 4.0
GIT_PROBE_OUTPUT_LIMIT_BYTES = 1024 * 1024
GIT_PROBE_STATUS_TIMEOUT = "timeout"
GIT_DEFAULT_BRANCH_REWRITE_COMMANDS = frozenset(
    # `pull` is classified rather than skipped. Leaving the strictly broader
    # command unexamined while blocking `merge` admitted the more dangerous
    # shape: a bare `git pull` on the default branch can author a merge commit,
    # which is exactly what this guard exists to prevent.
    {"cherry-pick", "merge", "pull", "reset", "update-ref"}
)
GIT_EXPLICIT_RECOVERY_OPTIONS = frozenset(
    {"--abort", "--continue", "--quit", "--skip"}
)
def payload_base(payload: Mapping[str, Any]) -> Path:
    # Resolve the command's effective workdir (issue #601 P0-4) so default-branch
    # delivery is judged against the repository the command really targets, not
    # the hook process cwd.
    return effective_workdir(payload).resolve(strict=False)


class GitProbe:
    """Run all Git discovery for one hook command under one bounded budget."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GIT_PROBE_TIMEOUT_SECONDS,
        output_limit_bytes: int = GIT_PROBE_OUTPUT_LIMIT_BYTES,
        executable: str = "git",
    ) -> None:
        self.deadline = time.monotonic() + max(timeout_seconds, 0.0)
        self.output_limit_bytes = max(output_limit_bytes, 0)
        self.executable = executable
        self._builtin_commands: frozenset[str] | None = None

    @staticmethod
    def _kill_group(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def run_with_status(
        self, cwd: Path, *args: str
    ) -> tuple[subprocess.CompletedProcess[str] | None, str]:
        """Run Git and distinguish a deadline timeout from other failures."""
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            return None, GIT_PROBE_STATUS_TIMEOUT
        command = [self.executable, *args]
        environment = dict(os.environ)
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except (OSError, ValueError):
            return None, "execution"
        assert process.stdout is not None and process.stderr is not None

        selected = selectors.DefaultSelector()
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        selected.register(process.stdout, selectors.EVENT_READ, "stdout")
        selected.register(process.stderr, selectors.EVENT_READ, "stderr")
        total = 0
        failure = ""
        try:
            while selected.get_map():
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    failure = GIT_PROBE_STATUS_TIMEOUT
                    break
                events = selected.select(remaining)
                if not events:
                    failure = GIT_PROBE_STATUS_TIMEOUT
                    break
                for key, _mask in events:
                    try:
                        chunk = os.read(key.fd, 65536)
                    except OSError:
                        failure = "read"
                        break
                    if not chunk:
                        selected.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    total += len(chunk)
                    if total > self.output_limit_bytes:
                        failure = "output-limit"
                        break
                    buffers[key.data].extend(chunk)
                if failure:
                    break
            if failure:
                self._kill_group(process)
                return None, failure
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                self._kill_group(process)
                return None, GIT_PROBE_STATUS_TIMEOUT
            try:
                returncode = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                self._kill_group(process)
                return None, GIT_PROBE_STATUS_TIMEOUT
            return (
                subprocess.CompletedProcess(
                    command,
                    returncode,
                    buffers["stdout"].decode("utf-8", errors="replace"),
                    buffers["stderr"].decode("utf-8", errors="replace"),
                ),
                "",
            )
        finally:
            selected.close()
            for stream in (process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()

    def run(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
        completed, _status = self.run_with_status(cwd, *args)
        return completed

    def builtin_commands(self, cwd: Path) -> frozenset[str]:
        """Return installed builtins plus retained non-delivery helper commands."""
        if self._builtin_commands is None:
            result = self.run(cwd, "--list-cmds=builtins")
            discovered = (
                frozenset(result.stdout.split())
                if result is not None and result.returncode == 0
                else frozenset()
            )
            self._builtin_commands = (
                GIT_NON_DELIVERY_COMMANDS_BASELINE | discovered
            )
        return self._builtin_commands


def git_context(
    arguments: list[str], base: Path
) -> tuple[Path, str, list[str], list[str], bool]:
    cwd = base
    config_arguments: list[str] = []
    context_valid = True
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == "--":
            index += 1
            break
        if token == "-C":
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            path = Path(arguments[index + 1]).expanduser()
            cwd = (path if path.is_absolute() else cwd / path).resolve(strict=False)
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            path = Path(token[2:]).expanduser()
            cwd = (path if path.is_absolute() else cwd / path).resolve(strict=False)
            index += 1
            continue
        if token == "-c":
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            value = arguments[index + 1]
            config_arguments.extend((token, value))
            if delivery_sensitive_config(value):
                context_valid = False
            index += 2
            continue
        if token.startswith("-c") and token != "-c":
            config_arguments.append(token)
            if delivery_sensitive_config(token[2:]):
                context_valid = False
            index += 1
            continue
        if token in {"--config-env"}:
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            value = arguments[index + 1]
            config_arguments.extend((token, value))
            if delivery_sensitive_config(value):
                context_valid = False
            index += 2
            continue
        if token.startswith("--config-env="):
            config_arguments.append(token)
            if delivery_sensitive_config(token.removeprefix("--config-env=")):
                context_valid = False
            index += 1
            continue
        if token in GIT_REPOSITORY_CONTEXT_OPTIONS:
            context_valid = False
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            index += 2
            continue
        if token.startswith(GIT_REPOSITORY_CONTEXT_PREFIXES):
            context_valid = False
            index += 1
            continue
        if token in GIT_REPOSITORY_CONTEXT_FLAGS:
            context_valid = False
            index += 1
            continue
        if token in GIT_OPTIONS_WITH_VALUE:
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            index += 2
            continue
        if token.startswith(GIT_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return cwd, token, arguments[index + 1 :], config_arguments, context_valid
    if index < len(arguments):
        return cwd, arguments[index], arguments[index + 1 :], config_arguments, context_valid
    return cwd, "", [], config_arguments, context_valid


def delivery_sensitive_config(value: str) -> bool:
    """Reject command-local Git config that can retarget a delivery."""
    key = value.split("=", 1)[0].strip().lower()
    if key in {"remote.pushdefault", "push.default", "include.path"}:
        return True
    if key.startswith("includeif.") and key.endswith(".path"):
        return True
    if key.startswith("remote."):
        return key.endswith((".url", ".pushurl", ".push", ".mirror"))
    if key.startswith("branch."):
        return key.endswith((".remote", ".pushremote", ".merge"))
    return key.startswith("url.") and key.endswith(
        (".insteadof", ".pushinsteadof")
    )


def config_environment_variables(arguments: list[str]) -> set[str]:
    """Return environment names referenced by Git ``--config-env`` options."""
    variables: set[str] = set()
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == "--config-env" and index + 1 < len(arguments):
            _name, separator, variable = arguments[index + 1].rpartition("=")
            if separator and variable:
                variables.add(variable)
            index += 2
            continue
        if token.startswith("--config-env="):
            _name, separator, variable = token.removeprefix(
                "--config-env="
            ).rpartition("=")
            if separator and variable:
                variables.add(variable)
        index += 1
    return variables


def command_local_git_environment_is_safe(
    simple_command: list[str], invocation: list[str]
) -> bool:
    """Reject command-local environment that can diverge from Git probes.

    ``semantic-commit`` is covered alongside ``git`` because the same overrides
    move where its commit lands, which would make this guard classify a
    different repository than the one the invocation mutates.
    """
    if not invocation:
        return True
    executable = PurePosixPath(invocation[0]).name
    if executable not in GOVERNED_CONTEXT_EXECUTABLES:
        return True
    referenced = config_environment_variables(invocation[1:])
    command_index = next(
        (
            index
            for index, token in enumerate(simple_command)
            if PurePosixPath(token).name == executable
        ),
        len(simple_command),
    )
    prefix = simple_command[:command_index]
    env_index = next(
        (
            index
            for index, token in enumerate(prefix)
            if PurePosixPath(token).name == "env"
        ),
        -1,
    )
    has_env_wrapper = env_index >= 0
    if has_env_wrapper:
        normalized = env_split_expanded_tokens(simple_command, env_index + 1)
        if (
            OPAQUE_WRAPPER_COMMAND in normalized
            or OPAQUE_NESTED_SHELL_COMMAND in normalized
        ):
            return False
        normalized_command_index = next(
            (
                index
                for index, token in enumerate(normalized)
                if PurePosixPath(token).name == executable
            ),
            len(normalized),
        )
        prefix = [*simple_command[:env_index], *normalized[:normalized_command_index]]

    def sensitive(name: str) -> bool:
        return (
            name.startswith("GIT_")
            or name in GIT_CONFIG_ENVIRONMENT_NAMES
            or name in referenced
        )

    for token in prefix:
        if is_assignment(token) and sensitive(token.split("=", 1)[0]):
            return False
    if not has_env_wrapper:
        return True
    index = 0
    while index < len(prefix):
        token = prefix[index]
        if token in {"-i", "--ignore-environment"}:
            return False
        if token in ENV_CONTEXT_OPTIONS or token.startswith(
            ENV_CONTEXT_OPTION_PREFIXES
        ):
            return False
        if (
            token.startswith("-")
            and not token.startswith("--")
            and any(option in token[1:] for option in "iCPS")
        ):
            return False
        if token in {"-u", "--unset"} and index + 1 < len(prefix):
            if sensitive(prefix[index + 1]):
                return False
            index += 2
            continue
        if token.startswith("--unset=") and sensitive(token.split("=", 1)[1]):
            return False
        if token.startswith("-u") and len(token) > 2 and sensitive(token[2:]):
            return False
        index += 1
    return True


def command_local_path_override(
    simple_command: list[str], invocation: list[str]
) -> bool:
    """Detect executable retargeting that must never receive a waiver.

    Scoped to the governed executables this hook classifies. This rule exists to
    stop `git` or `semantic-commit` being swapped for something else; applying it
    to every command blocked ordinary tooling — `PATH=... cargo test` — with a
    message claiming a governed executable was involved, while the strictly
    broader `export PATH=...; cargo test` passed. A nested governed invocation is
    still caught, because opaque candidates are classified against this same
    simple command.
    """
    if not invocation:
        return False
    executable = PurePosixPath(invocation[0]).name
    if executable not in GOVERNED_CONTEXT_EXECUTABLES:
        return False
    command_index = next(
        (
            index
            for index, token in enumerate(simple_command)
            if PurePosixPath(token).name == executable
        ),
        len(simple_command),
    )
    prefix = simple_command[:command_index]
    env_index = next(
        (
            index
            for index, token in enumerate(prefix)
            if PurePosixPath(token).name == "env"
        ),
        -1,
    )
    if env_index >= 0:
        normalized = env_split_expanded_tokens(simple_command, env_index + 1)
        normalized_command_index = next(
            (
                index
                for index, token in enumerate(normalized)
                if PurePosixPath(token).name == executable
            ),
            len(normalized),
        )
        prefix = [
            *simple_command[:env_index],
            *normalized[:normalized_command_index],
        ]
    return any(
        is_assignment(token) and token.split("=", 1)[0] == "PATH"
        for token in prefix
    )


def process_wrapper_hides_governed_invocation(
    simple_command: list[str], invocation: list[str]
) -> bool:
    """Fail closed when a process wrapper hides a governed authoring argv."""
    if not invocation or PurePosixPath(invocation[0]).name == "semantic-commit":
        return False
    for index, token in enumerate(simple_command[:-1]):
        if PurePosixPath(token).name != "semantic-commit":
            continue
        if simple_command[index + 1] in {
            "commit",
            "default-branch",
            "fixup",
            "local-default",
            "squash",
        }:
            return True
    return False


def executable_resolution_rejection(
    invocation: list[str], context_safe: bool
) -> str:
    """Reject a bare governed authoring CLI after shell resolution changed."""
    if context_safe or not invocation:
        return ""
    if (
        PurePosixPath(invocation[0]).name == "semantic-commit"
        and len(invocation) > 1
        and invocation[1]
        in {"commit", "default-branch", "fixup", "local-default", "squash"}
    ):
        return (
            "Blocked `semantic-commit` after an earlier shell command could "
            "have changed executable resolution. Use a separate tool call "
            "with the target checkout as its top-level workdir."
        )
    return ""


def shell_command_changes_git_context(simple_command: list[str]) -> bool:
    """Whether this command can alter later Git cwd/config interpretation."""
    invocation = invocation_tokens(simple_command)
    executable = ""
    arguments: list[str] = []
    if invocation:
        executable = (
            invocation[0]
            if invocation[0] == "."
            else PurePosixPath(invocation[0]).name
        )
        arguments = invocation[1:]
    for _depth in range(SHELL_BUILTIN_UNWRAP_LIMIT):
        if executable != "builtin":
            break
        if not arguments or "$" in arguments[0] or "`" in arguments[0]:
            return True
        executable = (
            arguments[0]
            if arguments[0] == "."
            else PurePosixPath(arguments[0]).name
        )
        arguments = arguments[1:]
    else:
        if executable == "builtin":
            return True
    if executable in SHELL_CONTEXT_COMMANDS:
        return True
    if not invocation:
        return any(
            is_assignment(token)
            and (
                token.split("=", 1)[0].startswith("GIT_")
                or token.split("=", 1)[0] in GIT_CONFIG_ENVIRONMENT_NAMES
            )
            for token in simple_command
        )
    if executable in {"export", "readonly", "declare", "typeset"}:
        return any(
            is_assignment(token)
            and (
                token.split("=", 1)[0].startswith("GIT_")
                or token.split("=", 1)[0] in GIT_CONFIG_ENVIRONMENT_NAMES
            )
            for token in simple_command
        )
    if executable == "unset":
        return any(
            token.startswith("GIT_") or token in GIT_CONFIG_ENVIRONMENT_NAMES
            for token in arguments
            if not token.startswith("-")
        )
    return False


def literal_directory_target(simple_command: list[str]) -> str | None:
    """Return the literal absolute directory a plain ``cd`` moves to.

    Only an unambiguous destination qualifies. A relative path depends on where
    the sequence started, and expansion, globbing, or `~` hides the target, so
    those keep the fail-closed verdict instead of resolving to a guess.
    """
    invocation = invocation_tokens(simple_command)
    if len(invocation) != 2 or PurePosixPath(invocation[0]).name != "cd":
        return None
    if simple_command[: len(invocation)] != invocation:
        return None
    target = invocation[1]
    if not target.startswith("/"):
        return None
    if any(character in target for character in DIRECTORY_EXPANSION_CHARACTERS):
        return None
    return target


def normalized_waiver_reason(value: str) -> str:
    """Normalize a waiver reason the way the receipt writer measures it.

    Admission and recording must agree on what counts as a stated reason. This
    mirrors ``normalized_delivery_waiver`` in nils-cli's
    ``default_branch_receipt``: control characters become spaces and whitespace
    runs collapse, so a reason cannot clear the minimum here through padding
    and then be dropped from the receipt, leaving an admitted delivery with no
    recorded reason. Keep both sides in step, including the minimum length.

    ``CONTROL_CHARACTERS`` is Unicode category Cc, which is exactly what Rust's
    ``char::is_control`` matches, so the two normalizations agree per codepoint.
    """
    return " ".join(
        "".join(
            " " if character in CONTROL_CHARACTERS else character
            for character in value
        ).split()
    )


def command_waiver_reason(simple_command: list[str]) -> str:
    """Return the waiver reason spelled on this command's own prefix."""
    for token in simple_command:
        if not is_assignment(token):
            break
        name, _, value = token.partition("=")
        if name == WAIVER_ASSIGNMENT_NAME:
            return normalized_waiver_reason(value)
    return ""


def waiver_admits(invocation: list[str], reason: str, waiver: str) -> bool:
    """Whether a stated one-shot waiver may admit this blocked invocation."""
    if len(waiver) < MINIMUM_WAIVER_REASON_LENGTH:
        return False
    if not reason.startswith(AMBIGUOUS_PREFIX):
        return False
    return bool(invocation) and PurePosixPath(invocation[0]).name == "semantic-commit"


def unresolved(detail: str) -> str:
    return f"{AMBIGUOUS_REASON} {detail}" if detail else AMBIGUOUS_REASON


def resolve_git_alias(
    probe: GitProbe,
    cwd: Path,
    subcommand: str,
    action: list[str],
    config_arguments: list[str],
) -> tuple[str, list[str]] | None:
    seen: set[str] = set()
    for _depth in range(8):
        # Git aliases cannot override a built-in command. In particular, an
        # alias named `push` must never hide the real push classifier.
        if subcommand == "push":
            return subcommand, action
        alias_name = subcommand.casefold()
        if alias_name in seen:
            return None
        seen.add(alias_name)
        result = probe.run(
            cwd, *config_arguments, "config", "--get", f"alias.{subcommand}"
        )
        if result is None or result.returncode not in {0, 1}:
            return None
        if result.returncode == 1:
            return subcommand, action
        value = result.stdout.rstrip("\n")
        if not value or value.lstrip().startswith("!"):
            return None
        try:
            expanded = shlex.split(value)
        except ValueError:
            return None
        if not expanded or expanded[0].startswith("-"):
            return None
        subcommand, action = expanded[0], [*expanded[1:], *action]
    return None


def current_branch(
    probe: GitProbe, cwd: Path, config_arguments: list[str] | None = None
) -> str:
    result = probe.run(
        cwd,
        *(config_arguments or []),
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
    )
    return result.stdout.strip() if result and result.returncode == 0 else ""


def cached_default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str,
    config_arguments: list[str],
) -> str:
    cached = probe.run(
        cwd,
        *config_arguments,
        "symbolic-ref",
        "--quiet",
        "--short",
        f"refs/remotes/{remote}/HEAD",
    )
    if not cached or cached.returncode != 0 or not cached.stdout.strip():
        return ""
    remote_ref = cached.stdout.strip()
    prefix = f"{remote}/"
    return remote_ref[len(prefix) :] if remote_ref.startswith(prefix) else ""


def primary_worktree_branch(
    probe: GitProbe,
    cwd: Path,
    config_arguments: list[str],
) -> str:
    """Return the primary worktree branch from Git's local worktree inventory."""
    worktrees = probe.run(
        cwd,
        *config_arguments,
        "worktree",
        "list",
        "--porcelain",
    )
    if not worktrees or worktrees.returncode != 0:
        return ""
    branch_prefix = "branch refs/heads/"
    for line in worktrees.stdout.splitlines():
        if not line:
            break
        if line.startswith(branch_prefix):
            return line.removeprefix(branch_prefix)
    return ""


def resolve_default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str = "origin",
    config_arguments: list[str] | None = None,
) -> tuple[str, bool]:
    """Resolve an authoritative local default branch without network I/O."""
    if not remote or "/" in remote or ":" in remote:
        return "", False
    git_config = config_arguments or []
    cached = cached_default_branch(probe, cwd, remote, git_config)
    primary = primary_worktree_branch(probe, cwd, git_config)
    if not cached or not primary or cached != primary:
        return "", False
    return cached, False


def default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str = "origin",
    config_arguments: list[str] | None = None,
) -> str:
    expected, cached_timeout = resolve_default_branch(
        probe, cwd, remote, config_arguments
    )
    return "" if cached_timeout else expected


def semantic_commit_repo(
    arguments: list[str], base: Path, base_source: str
) -> tuple[Path, str]:
    """Return the repository this invocation commits in, and how it resolved."""
    _read_only, value = semantic_commit_invocation_state(arguments)
    if value:
        path = Path(value).expanduser()
        resolved = (path if path.is_absolute() else base / path).resolve(strict=False)
        return resolved, "`--repo`"
    return base, base_source


def semantic_commit_block_reason(
    probe: GitProbe, arguments: list[str], base: Path, base_source: str
) -> str:
    """Classify a governed ``semantic-commit`` invocation by its own repository."""
    if arguments and arguments[0] == "local-default":
        return BLOCK_REASON
    if arguments and arguments[0] == "default-branch":
        cwd, source = semantic_commit_repo(arguments, base, base_source)
        location = f"Resolved repository: {cwd} (from {source})."
        rejection = default_branch_rejection(probe, arguments, cwd)
        if not rejection:
            return ""
        return f"{location} {rejection} {BLOCK_REASON} {REPO_HINT}"
    authors_commit, _writes_files, _repo = semantic_commit_invocation_effects(
        arguments
    )
    if not arguments or not authors_commit:
        return ""
    cwd, source = semantic_commit_repo(arguments, base, base_source)
    location = f"Resolved repository: {cwd} (from {source})."
    if arguments[0] not in {"commit", "fixup", "squash"}:
        return ""
    branch = current_branch(probe, cwd)
    expected = default_branch(probe, cwd)
    if not branch or not expected:
        return unresolved(
            f"{location} Its checked-out branch or cached default branch could "
            f"not be read. {REPO_HINT}"
        )
    return BLOCK_REASON if branch == expected else ""


def update_ref_target(arguments: list[str]) -> str | None:
    """Return the single ref target, or None for an ambiguous update-ref shape."""
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"-h", "--help"}:
            return ""
        if token in {"-m", "--message"}:
            index += 2
            continue
        if token.startswith("--message="):
            index += 1
            continue
        if token in {"--create-reflog", "-d", "--delete", "-z"}:
            index += 1
            continue
        if token in {"--stdin", "--no-deref"}:
            return None
        if token.startswith("-"):
            return None
        return token
    return None


def git_default_branch_rewrite_targets_default(
    probe: GitProbe,
    subcommand: str,
    arguments: list[str],
    cwd: Path,
    config_arguments: list[str],
) -> bool | None:
    """Classify raw ref/commit-producing Git paths that could bypass delivery."""
    if subcommand not in GIT_DEFAULT_BRANCH_REWRITE_COMMANDS:
        return False
    if any(argument in GIT_EXPLICIT_RECOVERY_OPTIONS for argument in arguments):
        return False
    if any(argument in {"-h", "--help"} for argument in arguments):
        return False
    if subcommand == "reset":
        if not arguments:
            return False
        if "--" in arguments and arguments.index("--") < len(arguments) - 1:
            return False

    expected = default_branch(probe, cwd, config_arguments=config_arguments)
    if not expected:
        return None

    current = current_branch(probe, cwd, config_arguments)
    if subcommand != "update-ref":
        if not current:
            return None
        if current != expected:
            return False
        # Raw merge/pull cannot prove publication from local state alone:
        # remote-tracking refs are locally writable and pull accepts local
        # repository paths. The governed sync-default owner performs the
        # remote-bound verification before moving the local default branch.
        return True

    target = update_ref_target(arguments)
    if target is None:
        return None
    if not target:
        return False
    if target in {"HEAD", "@"}:
        if not current:
            return None
        return current == expected
    if target.startswith("refs/heads/"):
        return target.removeprefix("refs/heads/") == expected
    if target.startswith("heads/"):
        return target.removeprefix("heads/") == expected
    if target.startswith("refs/"):
        return False
    return target == expected


def default_branch_rejection(
    probe: GitProbe, arguments: list[str], cwd: Path
) -> str:
    """Return why this is not the exact governed default-branch shape, else ""."""
    value_options = {
        "-m",
        "--message",
        "-F",
        "--message-file",
        "--expect-head",
        "--receipt-out",
        "--repo",
        "--format",
        "--type",
        "--scope",
        "--subject",
        "--body-bullet",
        "--bullet",
        "--trailer",
        "--max-header-width",
    }
    flag_options = {
        "--json",
        "--dry-run",
        "--automation",
        "--non-interactive",
        "--signoff",
        "--auto-fix",
    }
    unsupported = {
        "--amend",
        "--allow-empty",
        "--message-only",
        "--no-edit",
        "--message-out",
        "--no-progress",
        "--quiet",
        "--expected-branch",
        "--remote-mode",
    }
    values: dict[str, list[str]] = {}
    flags: set[str] = set()
    index = 1
    while index < len(arguments):
        token = arguments[index]
        if token in {"-h", "--help"}:
            return ""
        if token in unsupported:
            return f"default-branch does not support `{token}`."
        if token in flag_options:
            canonical = "--automation" if token == "--non-interactive" else token
            if canonical in flags and canonical not in {"--dry-run"}:
                return f"`{canonical}` is duplicated."
            flags.add(canonical)
            index += 1
            continue
        if token in value_options:
            if index + 1 >= len(arguments):
                return f"`{token}` has no value."
            canonical = {
                "-m": "--message",
                "-F": "--message-file",
                "--bullet": "--body-bullet",
            }.get(token, token)
            values.setdefault(canonical, []).append(arguments[index + 1])
            index += 2
            continue
        return f"`{token}` is not a supported default-branch argument."

    for singleton in (
        "--message",
        "--message-file",
        "--expect-head",
        "--receipt-out",
        "--repo",
        "--format",
        "--type",
        "--scope",
        "--subject",
        "--max-header-width",
    ):
        if len(values.get(singleton, [])) > 1:
            return f"`{singleton}` is duplicated."
    if values.get("--message") and values.get("--message-file"):
        return "`--message` and `--message-file` are mutually exclusive."
    if (
        values.get("--message") or values.get("--message-file")
    ) and any(
        values.get(option)
        for option in (
            "--type",
            "--scope",
            "--subject",
            "--body-bullet",
        )
    ):
        return (
            "A complete `--message` or `--message-file` cannot be combined "
            "with structured message fields."
        )
    if "--json" in flags and values.get("--format"):
        return "`--json` and `--format` are duplicate output formats."
    output_format = values.get("--format", ["text"])[0]
    if output_format not in {"text", "json"}:
        return f"`--format {output_format}` is not supported."

    expected_head = values.get("--expect-head", [""])[0]
    if len(expected_head) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in expected_head
    ):
        return "Its `--expect-head` is not a full lowercase object id."

    repo = values.get("--repo", [""])[0]
    if not repo:
        return "It carries no explicit `--repo`."
    repo_path = Path(repo).expanduser()
    if not repo_path.is_absolute():
        return "Its `--repo` is not an absolute path."
    try:
        if repo_path.resolve(strict=True) != cwd.resolve(strict=True):
            return "Its explicit `--repo` did not resolve to the classified repository."
    except OSError:
        return "Its explicit `--repo` could not be resolved."

    dry_run = "--dry-run" in flags
    receipt = values.get("--receipt-out", [""])[0]
    if dry_run and receipt:
        return "`--receipt-out` is not accepted with `--dry-run`."
    if dry_run:
        receipt_path = None
    elif not receipt:
        return "It carries no mutation `--receipt-out`."
    else:
        receipt_path = Path(receipt).expanduser()
    if receipt_path is not None and (
        not receipt_path.is_absolute() or not receipt_path.parent.exists()
    ):
        return (
            "Its `--receipt-out` is not an absolute path with an existing parent."
        )
    if receipt_path is not None and receipt_path.exists():
        return "Its `--receipt-out` does not name a new file."
    if receipt_path is not None and receipt_path.parent.is_symlink():
        return "Its `--receipt-out` parent is a symlink."
    try:
        repository = cwd.resolve(strict=True)
        receipt_parent = (
            receipt_path.parent.resolve(strict=True)
            if receipt_path is not None
            else None
        )
    except OSError:
        return "The repository or the receipt directory could not be read."
    if receipt_parent is not None and (
        receipt_parent == repository or repository in receipt_parent.parents
    ):
        return (
            "Its `--receipt-out` is inside the repository; allocate the receipt "
            "outside it through `agent-out`."
        )
    head = probe.run(repository, "rev-parse", "--verify", "HEAD")
    git_dir = probe.run(
        repository, "rev-parse", "--path-format=absolute", "--git-dir"
    )
    common_dir = probe.run(
        repository, "rev-parse", "--path-format=absolute", "--git-common-dir"
    )
    if not all(
        result is not None and result.returncode == 0
        for result in (head, git_dir, common_dir)
    ):
        return "The repository did not answer the required Git reads."
    assert head is not None and git_dir is not None and common_dir is not None
    try:
        git_directory = Path(git_dir.stdout.strip()).resolve(strict=True)
        common_directory = Path(common_dir.stdout.strip()).resolve(strict=True)
        primary = git_directory == common_directory
    except OSError:
        return "The repository's Git directories could not be compared."
    if not primary:
        return "The repository is a linked worktree, not the primary checkout."
    branch = current_branch(probe, repository)
    if not branch:
        return "The repository has no attached branch."
    actual_head = head.stdout.strip()
    if actual_head != expected_head:
        return (
            f"Its HEAD is {actual_head[:12]}, not the `--expect-head` "
            f"{expected_head[:12]}."
        )
    staged = probe.run(
        repository,
        "diff",
        "--cached",
        "--name-only",
        "-z",
        "--diff-filter=ACDMRTUXB",
    )
    if (
        staged is None
        or staged.returncode != 0
        or not any(path for path in staged.stdout.split("\0") if path)
    ):
        return "The repository has no staged changes."
    status = probe.run(repository, "status", "--porcelain", "--untracked-files=all")
    if status is None or status.returncode != 0:
        return "The repository status could not be read."
    if any(
        line.startswith("??")
        or (len(line) > 1 and line[1] != " ")
        for line in status.stdout.splitlines()
    ):
        return "The repository has unstaged or untracked changes."
    for marker in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "BISECT_LOG",
        "rebase-merge",
        "rebase-apply",
    ):
        if (git_directory / marker).exists():
            return f"The repository has a Git operation in progress ({marker})."
    remotes = probe.run(repository, "remote")
    if remotes is None or remotes.returncode != 0:
        return "The repository's configured remotes could not be read."
    configured = [line for line in remotes.stdout.splitlines() if line.strip()]
    branch_remote = probe.run(
        repository, "config", "--get", f"branch.{branch}.remote"
    )
    branch_merge = probe.run(
        repository, "config", "--get", f"branch.{branch}.merge"
    )
    remote_value = (
        branch_remote.stdout.strip()
        if branch_remote is not None and branch_remote.returncode == 0
        else ""
    )
    merge_value = (
        branch_merge.stdout.strip()
        if branch_merge is not None and branch_merge.returncode == 0
        else ""
    )
    if not configured:
        if remote_value or merge_value:
            return "Remote-free default identity has stale upstream metadata."
        return ""
    if remote_value not in configured or remote_value == ".":
        return "Its configured upstream remote is not authoritative."
    if merge_value != f"refs/heads/{branch}":
        return "Its configured upstream branch does not match the checked-out branch."
    upstream = probe.run(
        repository,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )
    expected_upstream = f"{remote_value}/{branch}"
    if (
        upstream is None
        or upstream.returncode != 0
        or upstream.stdout.strip() != expected_upstream
    ):
        return "Its configured upstream cached ref is not authoritative."
    cached_default = probe.run(
        repository,
        "symbolic-ref",
        "--quiet",
        "--short",
        f"refs/remotes/{remote_value}/HEAD",
    )
    if (
        cached_default is None
        or cached_default.returncode != 0
        or cached_default.stdout.strip() != expected_upstream
    ):
        return "Its checked-out branch is not the authoritative cached default branch."
    upstream_head = probe.run(
        repository, "rev-parse", "--verify", "@{upstream}^{commit}"
    )
    if (
        upstream_head is None
        or upstream_head.returncode != 0
        or upstream_head.stdout.strip() != actual_head
    ):
        return "Its current HEAD is not aligned with the cached default-branch upstream."
    return ""


def trusted_managed_cli_invocation(raw: str, name: str) -> bool:
    """Require an exact invocation of the active trusted managed CLI."""
    candidate = shutil.which(name)
    if not candidate or not os.path.isabs(candidate):
        return False
    if raw == name:
        invoked = candidate
    elif os.path.isabs(raw):
        invoked = raw
    else:
        return False
    try:
        lexical = os.path.abspath(candidate)
        resolved = os.path.realpath(candidate)
        if os.path.realpath(invoked) != resolved:
            return False
    except OSError:
        return False
    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        return False

    trusted_roots = {
        os.path.realpath(item)
        for item in os.environ.get("AGENT_RUNTIME_TRUSTED_CLI_ROOT", "").split(
            os.pathsep
        )
        if item.strip()
    }
    session_bin = os.environ.get("AGENT_SESSION_BIN", "").strip()
    if (
        session_bin
        and os.path.isabs(session_bin)
        and os.path.basename(session_bin) == "agent-session"
        and os.path.isfile(os.path.realpath(session_bin))
        and os.access(os.path.realpath(session_bin), os.X_OK)
    ):
        trusted_roots.add(os.path.realpath(os.path.dirname(session_bin)))
    lexical_dir = os.path.realpath(os.path.dirname(lexical))
    if lexical_dir in trusted_roots:
        return True
    if lexical_dir == "/usr/bin" and resolved == lexical:
        return True
    if is_managed_cli_home_bin(lexical_dir) and resolved == lexical:
        return True
    for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
        if os.path.dirname(lexical) != os.path.join(prefix, "bin"):
            continue
        cellar = os.path.join(prefix, "Cellar", "nils-cli")
        try:
            return resolved == lexical or os.path.commonpath(
                (resolved, cellar)
            ) == cellar
        except ValueError:
            return False
    return False


def normalized_branch(value: str, current: str) -> str:
    value = value.lstrip("+")
    if value in {"HEAD", "@"}:
        return current
    for prefix in ("refs/heads/", "heads/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def refspec_targets_default(refspec: str, default: str, current: str) -> bool:
    refspec = refspec.lstrip("+")
    # A lone colon is Git's "matching branches" refspec. It can update the
    # default branch alongside every other same-named local/remote branch.
    if refspec == ":":
        return True
    if ":" in refspec:
        source, destination = refspec.split(":", 1)
        target = normalized_branch(destination, current)
    else:
        source = refspec
        target = normalized_branch(source, current)
    if not target and source:
        return False
    if "*" in target:
        return fnmatch.fnmatch(default, target)
    return target == default


def explicit_branch_refspec_target(refspec: str) -> str:
    """Return one exact destination branch that needs no current-branch lookup."""
    value = refspec.lstrip("+")
    if not value or "*" in value or value == ":":
        return ""
    if ":" in value:
        source, destination = value.split(":", 1)
        if not source or not destination:
            return ""
    else:
        destination = value
    if destination in {"HEAD", "@"}:
        return ""
    for prefix in ("refs/heads/", "heads/"):
        if destination.startswith(prefix):
            return destination[len(prefix) :]
    if destination.startswith("refs/") or destination.startswith("tags/"):
        return ""
    return destination


def push_shape(arguments: list[str]) -> tuple[bool, bool, bool, bool, str, list[str]]:
    """Return dry-run, all/mirror, delete, tags-only, remote, and refspecs."""
    dry_run = False
    all_or_mirror = False
    delete = False
    tags_only = False
    repository = ""
    positionals: list[str] = []
    options_done = False
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if not options_done and token == "--":
            options_done = True
            index += 1
            continue
        if not options_done and token.startswith("-") and token != "-":
            if token == "--dry-run":
                dry_run = True
            if token in {"--all", "--mirror"}:
                all_or_mirror = True
            if token == "--tags":
                tags_only = True
            if token == "--delete":
                delete = True
            if token == "--repo" and index + 1 < len(arguments):
                repository = arguments[index + 1]
                index += 2
                continue
            if token.startswith("--repo="):
                repository = token.split("=", 1)[1]
                index += 1
                continue
            if token in PUSH_OPTIONS_WITH_VALUE:
                index += 2
                continue
            if token.startswith(PUSH_OPTIONS_WITH_VALUE_PREFIXES):
                index += 1
                continue
            if not token.startswith("--"):
                cluster = token[1:]
                consumed_next = False
                for position, option in enumerate(cluster):
                    if option == "n":
                        dry_run = True
                    elif option == "d":
                        delete = True
                    elif option == "o":
                        consumed_next = position + 1 == len(cluster)
                        break
                index += 2 if consumed_next and index + 1 < len(arguments) else 1
                continue
            index += 1
            continue
        positionals.append(token)
        index += 1
    if repository:
        return dry_run, all_or_mirror, delete, tags_only, repository, positionals
    if positionals:
        return (
            dry_run,
            all_or_mirror,
            delete,
            tags_only,
            positionals[0],
            positionals[1:],
        )
    return dry_run, all_or_mirror, delete, tags_only, "origin", []


def push_targets_default(
    probe: GitProbe,
    arguments: list[str],
    cwd: Path,
    config_arguments: list[str],
) -> bool | None:
    dry_run, all_or_mirror, delete, tags_only, remote, refspecs = push_shape(arguments)
    if dry_run:
        return False
    if tags_only and not refspecs:
        return False
    default, cached_timeout = resolve_default_branch(
        probe, cwd, remote, config_arguments
    )
    if not default:
        return None
    if cached_timeout:
        if all_or_mirror or delete or tags_only or not refspecs:
            return None
        targets = [explicit_branch_refspec_target(refspec) for refspec in refspecs]
        if any(not target for target in targets):
            return None
        return any(target == default for target in targets)
    if all_or_mirror:
        return True
    current = current_branch(probe, cwd, config_arguments)
    if delete:
        if not refspecs:
            return None
        return any(
            normalized_branch(refspec, current) == default for refspec in refspecs
        )
    if refspecs:
        return any(
            refspec_targets_default(refspec, default, current) for refspec in refspecs
        )
    # With no explicit refspec, Git may select a destination from
    # remote.<name>.push, branch pushRemote/upstream, remote.pushDefault, and
    # push.default. The checked-out branch alone cannot prove the destination
    # is non-default, so require callers to spell out a safe feature refspec.
    return None


def rewrite_verdict_reason(subcommand: str, target: bool | None) -> str:
    """Name what a default-branch rewrite verdict resolved, and its remedy."""
    if target is False:
        return ""
    # `merge` and `pull` on the default branch are almost always an attempt to
    # sync it, so name the surface that does exactly that. The general policy
    # stays, because the command really would move the default branch.
    remedy = f"{POLICY} {REMEDY_SYNC_DEFAULT}" if subcommand in {
        "merge",
        "pull",
    } else POLICY
    if target is True:
        return (
            f"{MARK_BLOCKED} `git {subcommand}` would move the checked-out "
            f"default branch. {remedy}"
        )
    return (
        f"{AMBIGUOUS_PREFIX} `git {subcommand}` was not classified: the default "
        f"branch or the checked-out branch could not be read. {remedy}"
    )


def push_verdict_reason(target: bool | None) -> str:
    """Name what a push verdict resolved, with a remedy for that push."""
    if target is False:
        return ""
    if target is True:
        return (
            f"{MARK_BLOCKED} This push resolves to the remote's default branch. "
            f"{POLICY}"
        )
    return (
        f"{AMBIGUOUS_PREFIX} The destination branch of this push could not be "
        f"resolved from its arguments and configuration. {REMEDY_FEATURE_PUSH}"
    )


def invocation_block_reason(
    probe: GitProbe,
    invocation: list[str],
    base: Path,
    *,
    environment_safe: bool = True,
    target_resolved: bool = True,
    base_source: str = "the tool workdir",
    context_note: str = "",
) -> str:
    def unclassifiable(detail: str) -> str:
        """An unverified verdict, preferring the concrete tripped condition."""
        return f"{AMBIGUOUS_PREFIX} {context_note or detail}"

    if not invocation:
        return ""
    executable = PurePosixPath(invocation[0]).name
    if executable == OPAQUE_NESTED_SHELL_COMMAND:
        return unclassifiable(
            "A nested shell hides the command that would run. " + POLICY
        )
    if executable == "semantic-commit":
        if not trusted_managed_cli_invocation(
            invocation[0], "semantic-commit"
        ):
            return (
                "Blocked an untrusted `semantic-commit` executable. Invoke the "
                "active managed CLI by its exact command name or trusted absolute "
                "path."
            )
        if not target_resolved:
            return unresolved(
                "Command-local Git context can move where this commit lands, so "
                f"its repository was not classified. {REPO_HINT}"
            )
        return semantic_commit_block_reason(probe, invocation[1:], base, base_source)
    if executable == "git":
        cwd, subcommand, action, config_arguments, context_valid = git_context(
            invocation[1:], base
        )
        if subcommand != "push" and subcommand in probe.builtin_commands(cwd):
            if subcommand in GIT_DEFAULT_BRANCH_REWRITE_COMMANDS:
                if not environment_safe or not context_valid:
                    return unclassifiable(
                        f"Command-local Git context can move where `git "
                        f"{subcommand}` applies. {POLICY}"
                    )
                return rewrite_verdict_reason(
                    subcommand,
                    git_default_branch_rewrite_targets_default(
                        probe, subcommand, action, cwd, config_arguments
                    ),
                )
            return ""
        if subcommand == "push" and push_shape(action)[0]:
            return ""
        if not environment_safe or not context_valid:
            return unclassifiable(
                f"Command-local Git context can move where `git {subcommand}` "
                f"applies. {POLICY}"
            )
        resolved = resolve_git_alias(
            probe, cwd, subcommand, action, config_arguments
        )
        if resolved is None:
            return unclassifiable(
                f"The Git alias `{subcommand}` could not be expanded to a "
                f"classifiable command. {POLICY}"
            )
        subcommand, action = resolved
        if subcommand != "push":
            if subcommand in GIT_DEFAULT_BRANCH_REWRITE_COMMANDS:
                return rewrite_verdict_reason(
                    subcommand,
                    git_default_branch_rewrite_targets_default(
                        probe, subcommand, action, cwd, config_arguments
                    ),
                )
            return ""
        if push_shape(action)[0]:
            return ""
        reason = push_verdict_reason(
            push_targets_default(probe, action, cwd, config_arguments)
        )
        if reason.startswith(AMBIGUOUS_PREFIX) and context_note:
            return f"{AMBIGUOUS_PREFIX} {context_note}"
        return reason
    return ""


def candidate_block_reason(
    probe: GitProbe,
    simple_command: list[str],
    cwd: Path,
    candidate: list[str],
    *,
    shell_context_safe: bool,
    directory_resolved: bool,
    base_source: str,
) -> str:
    """Classify one invocation shape of a simple command in its own context."""
    if command_local_path_override(simple_command, candidate):
        return (
            "Blocked a command-local `PATH` override around a governed "
            "executable. Invoke the active managed CLI without executable "
            "retargeting."
        )
    command_safe = command_local_git_environment_is_safe(simple_command, candidate)
    return invocation_block_reason(
        probe,
        candidate,
        cwd,
        environment_safe=command_safe and shell_context_safe,
        target_resolved=command_safe and (shell_context_safe or directory_resolved),
        base_source=base_source,
        # When an earlier command moved the shell context, that — not the Git
        # command itself — is the discriminator, so it is what the message names.
        context_note="" if shell_context_safe else REMEDY_SHELL_CONTEXT,
    )


def command_block_reason(command: str, base: Path) -> str:
    probe = GitProbe()
    shell_context_safe = True
    executable_resolution_safe = True
    simple_commands = simple_commands_with_nested_shells(command)
    # A nested shell hides where its own `cd` stops applying, so a resolved
    # directory is only trustworthy across a flat command sequence.
    resolves_directories = not any(
        nested_shell_payload(invocation_tokens(tokens)) for tokens in simple_commands
    )
    directory_resolved = True
    cwd = base
    base_source = "the tool workdir"
    for simple_command in simple_commands:
        invocation = invocation_tokens(simple_command)
        waiver = command_waiver_reason(simple_command)
        if invocation and invocation[0] == OPAQUE_WRAPPER_COMMAND:
            return AMBIGUOUS_REASON
        if process_wrapper_hides_governed_invocation(
            simple_command, invocation
        ):
            return (
                "Blocked a governed `semantic-commit` authoring invocation "
                "behind a process wrapper. Invoke the active managed CLI "
                "directly so its executable and argv can be verified."
            )
        def classify(candidate: list[str]) -> str:
            return executable_resolution_rejection(
                candidate, executable_resolution_safe
            ) or candidate_block_reason(
                probe,
                simple_command,
                cwd,
                candidate,
                shell_context_safe=shell_context_safe,
                directory_resolved=directory_resolved,
                base_source=base_source,
            )

        reason = classify(invocation)
        if reason and not waiver_admits(invocation, reason, waiver):
            return reason
        if invocation_is_unresolved_nested(invocation):
            return AMBIGUOUS_REASON
        for candidate in opaque_invocation_candidates(
            invocation, {"git", "semantic-commit"}
        ):
            if invocation_is_unresolved_nested(candidate):
                return AMBIGUOUS_REASON
            reason = classify(candidate)
            if reason and not waiver_admits(candidate, reason, waiver):
                return reason
        # A preceding shell command can alter PATH, zsh/bash command tables,
        # aliases, functions, hashes, or sourced state in ways this hook cannot
        # prove exhaustively. No later authoring invocation retains executable
        # identity; use a separate tool call with an attested top-level workdir.
        executable_resolution_safe = False
        if not shell_command_changes_git_context(simple_command):
            continue
        # Raw Git keeps failing closed after any context change. Only the
        # governed CLI, which re-verifies its own repository, follows a literal
        # destination this guard can name.
        shell_context_safe = False
        target = (
            literal_directory_target(simple_command) if resolves_directories else None
        )
        if target is not None and Path(target).is_dir():
            cwd = Path(target)
            base_source = "a literal `cd` in the same command"
            continue
        directory_resolved = False
    return ""


def normalize_refusal_reason(reason: str) -> str:
    """Put one stable classification marker at byte zero of every refusal."""
    if reason.startswith((MARK_BLOCKED, MARK_UNVERIFIED)):
        return reason
    if MARK_UNVERIFIED in reason:
        return f"{MARK_UNVERIFIED} {reason.replace(MARK_UNVERIFIED, '', 1).strip()}"
    if MARK_BLOCKED in reason:
        return f"{MARK_BLOCKED} {reason.replace(MARK_BLOCKED, '', 1).strip()}"
    return f"{MARK_BLOCKED} {reason}"


def main() -> int:
    payload = read_payload()
    command = command_from(payload)
    if command:
        reason = command_block_reason(command, payload_base(payload))
        if reason:
            emit_block(normalize_refusal_reason(reason))
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
