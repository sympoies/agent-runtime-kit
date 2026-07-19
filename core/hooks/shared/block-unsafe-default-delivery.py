#!/usr/bin/env python3
"""PreToolUse hook: keep default-branch delivery on governed routes.

PR delivery remains the default. A maintainer-authorized L0 direct-main change
is authored as one signed commit on a non-default managed worktree and is
delivered through ``forge-cli repo push-default``. This hook blocks the two raw
shell paths that would otherwise bypass that contract: authoring with
``semantic-commit`` on the checked-out default branch and targeting the remote
default branch with a live ``git push``.

This is a mechanical guardrail, not a shell sandbox. Provider branch rules and
the forge-cli expected-base/signature/read-back contract remain authoritative.
"""

from __future__ import annotations

import fnmatch
import os
import selectors
import shlex
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
    is_assignment,
    opaque_invocation_candidates,
    read_payload,
    semantic_commit_invocation_effects,
    semantic_commit_invocation_state,
    simple_commands_with_nested_shells,
)

BLOCK_REASON = (
    "Do not author or push an agent change on the default branch through a raw "
    "shell path. PR delivery is the default. When the maintainer explicitly "
    "authorized direct-main delivery in the current task, author one signed "
    "commit in a non-default managed worktree and use `forge-cli repo "
    "push-default` with the expected base and reason file."
)
AMBIGUOUS_REASON = (
    "Default-branch delivery target could not be resolved safely. " + BLOCK_REASON
)
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
            config_arguments.extend((token, arguments[index + 1]))
            index += 2
            continue
        if token.startswith("-c") and token != "-c":
            config_arguments.append(token)
            index += 1
            continue
        if token in {"--config-env"}:
            if index + 1 >= len(arguments):
                return cwd, "", [], config_arguments, False
            config_arguments.extend((token, arguments[index + 1]))
            index += 2
            continue
        if token.startswith("--config-env="):
            config_arguments.append(token)
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
    """Reject command-local environment that can diverge from Git probes."""
    if not invocation or PurePosixPath(invocation[0]).name != "git":
        return True
    referenced = config_environment_variables(invocation[1:])
    git_index = next(
        (
            index
            for index, token in enumerate(simple_command)
            if PurePosixPath(token).name == "git"
        ),
        len(simple_command),
    )
    prefix = simple_command[:git_index]
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
        normalized_git_index = next(
            (
                index
                for index, token in enumerate(normalized)
                if PurePosixPath(token).name == "git"
            ),
            len(normalized),
        )
        prefix = [*simple_command[:env_index], *normalized[:normalized_git_index]]

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


def resolve_default_branch(
    probe: GitProbe,
    cwd: Path,
    remote: str = "origin",
    config_arguments: list[str] | None = None,
) -> tuple[str, bool]:
    """Return the default branch and whether it came from timeout fallback."""
    if not remote or "/" in remote or ":" in remote:
        return "", False
    git_config = config_arguments or []
    push_urls = probe.run(
        cwd, *git_config, "remote", "get-url", "--push", "--all", remote
    )
    if not push_urls or push_urls.returncode != 0:
        return "", False
    urls = [line for line in push_urls.stdout.splitlines() if line]
    if len(urls) != 1:
        return "", False
    cached_before_live = cached_default_branch(probe, cwd, remote, git_config)
    authoritative, status = probe.run_with_status(
        cwd, *git_config, "ls-remote", "--symref", urls[0], "HEAD"
    )
    if not authoritative:
        if status == GIT_PROBE_STATUS_TIMEOUT and cached_before_live:
            return cached_before_live, True
        return "", False
    if authoritative.returncode != 0:
        return "", False
    expected = ""
    for line in authoritative.stdout.splitlines():
        if not line.startswith("ref: refs/heads/"):
            continue
        reference, separator, name = line.partition("\t")
        if separator and name == "HEAD":
            expected = reference[len("ref: refs/heads/") :]
            break
    if not expected:
        return "", False
    cached_after_live = cached_default_branch(probe, cwd, remote, git_config)
    cached = cached_after_live or cached_before_live
    if cached and cached != expected:
        return "", False
    return expected, False


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


def semantic_commit_repo(arguments: list[str], base: Path) -> Path:
    _read_only, value = semantic_commit_invocation_state(arguments)
    if value:
        path = Path(value).expanduser()
        return (path if path.is_absolute() else base / path).resolve(strict=False)
    return base


def semantic_commit_targets_default(
    probe: GitProbe, arguments: list[str], base: Path
) -> bool | None:
    authors_commit, _writes_files, _repo = semantic_commit_invocation_effects(
        arguments
    )
    if (
        not arguments
        or arguments[0] not in {"commit", "fixup", "squash"}
        or not authors_commit
    ):
        return False
    cwd = semantic_commit_repo(arguments, base)
    branch = current_branch(probe, cwd)
    expected = default_branch(probe, cwd)
    if not branch or not expected:
        return None
    return branch == expected


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


def invocation_block_reason(
    probe: GitProbe,
    invocation: list[str],
    base: Path,
    *,
    environment_safe: bool = True,
) -> str:
    if not invocation:
        return ""
    executable = PurePosixPath(invocation[0]).name
    if executable == OPAQUE_NESTED_SHELL_COMMAND:
        return AMBIGUOUS_REASON
    if executable == "semantic-commit":
        target = semantic_commit_targets_default(probe, invocation[1:], base)
        return BLOCK_REASON if target is True else AMBIGUOUS_REASON if target is None else ""
    if executable == "git":
        cwd, subcommand, action, config_arguments, context_valid = git_context(
            invocation[1:], base
        )
        if subcommand != "push" and subcommand in probe.builtin_commands(cwd):
            return ""
        if subcommand == "push" and push_shape(action)[0]:
            return ""
        if not environment_safe or not context_valid:
            return AMBIGUOUS_REASON
        resolved = resolve_git_alias(
            probe, cwd, subcommand, action, config_arguments
        )
        if resolved is None:
            return AMBIGUOUS_REASON
        subcommand, action = resolved
        if subcommand != "push":
            return ""
        if push_shape(action)[0]:
            return ""
        target = push_targets_default(probe, action, cwd, config_arguments)
        return BLOCK_REASON if target is True else AMBIGUOUS_REASON if target is None else ""
    return ""


def command_block_reason(command: str, base: Path) -> str:
    probe = GitProbe()
    shell_context_safe = True
    for simple_command in simple_commands_with_nested_shells(command):
        invocation = invocation_tokens(simple_command)
        environment_safe = command_local_git_environment_is_safe(
            simple_command, invocation
        ) and shell_context_safe
        reason = invocation_block_reason(
            probe, invocation, base, environment_safe=environment_safe
        )
        if reason:
            return reason
        if invocation_is_unresolved_nested(invocation):
            return AMBIGUOUS_REASON
        for candidate in opaque_invocation_candidates(
            invocation, {"git", "semantic-commit"}
        ):
            if invocation_is_unresolved_nested(candidate):
                return AMBIGUOUS_REASON
            candidate_environment_safe = command_local_git_environment_is_safe(
                simple_command, candidate
            ) and shell_context_safe
            reason = invocation_block_reason(
                probe,
                candidate,
                base,
                environment_safe=candidate_environment_safe,
            )
            if reason:
                return reason
        if shell_command_changes_git_context(simple_command):
            shell_context_safe = False
    return ""


def main() -> int:
    payload = read_payload()
    command = command_from(payload)
    if command:
        reason = command_block_reason(command, payload_base(payload))
        if reason:
            emit_block(reason)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
