#!/usr/bin/env python3
"""Out-of-band controller for the declared validation contract.

`sympoies/nils-cli#1409` recorded a deadlock with no way out from inside the
session: a code edit left validation outstanding, `PreToolUse` rejected Bash
because the activity capability had failed closed, the Stop finish-line gate
refused to release because the declared validation had not run, and the
documented `AGENT_RUNTIME_VALIDATION_WAIVER=1` escape was itself unreachable
because setting it required the blocked shell.

This controller is the recovery lane. It is invoked out-of-band — by an operator
or by Agent Console — so it never passes through the hook that is failing. It
deliberately exposes exactly four verbs and no general shell escape:

* ``status``  inspect the declared contract, what is outstanding, and any waiver
* ``run``     execute **only** the declared command shape and record the outcome
* ``waive``   record a structured waiver bound to this edit generation
* ``revoke``  withdraw a waiver

``run`` cannot be pointed at an arbitrary command: ``--command`` selects among
the strings the repository itself declared in ``AGENT_DOCS.toml`` and anything
else is refused. The waiver requires a reason and binds to the repository,
contract, product, session, and current edit generation, so it expires the moment
another edit lands instead of leaking across turns the way the ambient
environment variable does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "core" / "hooks" / "shared"))

from hook_common import (  # noqa: E402
    VALIDATION_WAIVER_SCHEMA,
    VALIDATION_WAIVER_MAX_REASON_CHARS,
    acquire_validation_state_lock,
    command_failed_marker,
    command_ran_marker,
    git_toplevel,
    read_validation_waiver,
    touch_marker,
    validation_contracts,
    validation_edit_generation,
    validation_marker_set,
    validation_waiver_marker,
)

SCHEMA_PREFIX = "cli.validation-recovery"
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 64
EXIT_DATA = 65


def emit(command: str, ok: bool, body: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(
            json.dumps(
                {
                    "schema_version": f"{SCHEMA_PREFIX}.{command}.v1",
                    "ok": ok,
                    ("data" if ok else "error"): body,
                },
                sort_keys=True,
            )
        )
        return
    if not ok:
        print(f"validation-recovery: {body.get('code')}: {body.get('message')}", file=sys.stderr)
        return
    print(render_text(command, body), end="")


def render_text(command: str, body: dict[str, Any]) -> str:
    if command == "status":
        lines = [f"outstanding: {'yes' if body['outstanding'] else 'no'}\n"]
        for contract in body["contracts"]:
            lines.append(f"contract {contract['context']}:\n")
            for declared in contract["commands"]:
                state = (
                    "outstanding"
                    if declared in contract["outstanding_commands"]
                    else "satisfied"
                )
                lines.append(f"  [{state}] {declared}\n")
            waiver = contract["waiver"]
            if waiver:
                lines.append(f"  waiver: {waiver['reason']}\n")
        return "".join(lines)
    if command == "run":
        lines = []
        for entry in body["commands"]:
            lines.append(
                f"[{entry['status']}] {entry['command']}"
                + (
                    f" (exit {entry['exit_code']})\n"
                    if entry["exit_code"] is not None
                    else "\n"
                )
            )
        return "".join(lines)
    if command == "waive":
        return f"waiver recorded for {body['context']}: {body['reason']}\n"
    if command == "revoke":
        return f"waiver revoked for {len(body['revoked'])} contract(s)\n"
    return ""


def resolve_repo(argument: str | None) -> str:
    candidate = os.path.realpath(argument or os.getcwd())
    root = git_toplevel(candidate)
    if not root:
        raise SystemExit(
            _fail("repository-unresolved", "path is not inside a git repository")
        )
    return os.path.realpath(root)


def _fail(code: str, message: str) -> int:
    print(
        json.dumps(
            {
                "schema_version": f"{SCHEMA_PREFIX}.error.v1",
                "ok": False,
                "error": {"code": code, "message": message},
            },
            sort_keys=True,
        )
    )
    return EXIT_DATA


def selected_contracts(repo_root: str, context: str | None) -> list[dict[str, Any]]:
    contracts = validation_contracts(repo_root)
    if context:
        contracts = [
            contract for contract in contracts if contract.get("context") == context
        ]
    return contracts


def session_key(argument: str | None) -> str:
    """Derive the marker namespace the target session's hooks actually read.

    The gate namespaces validation state by `sha256(session identity)`, where the
    identity is the managed `AGENT_SESSION_ID` when present and a provider payload
    id otherwise. A managed session therefore always reads `session-<key>/`, so a
    controller that only ever wrote the shared namespace would put its waiver
    where that gate never looks — silently failing in exactly the deadlock this
    lane exists for.

    `--session` names the target explicitly (Agent Console knows it), and an
    ambient `AGENT_SESSION_ID` is honored so a controller invoked inside the same
    managed context matches without extra arguments. Neither present means the
    shared namespace, which is what an unidentified delivery reads.
    """
    identity = (argument or os.environ.get("AGENT_SESSION_ID", "")).strip()
    if not identity:
        return ""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def marker_state(
    repo_root: str, contract: dict[str, Any], session: str | None
) -> tuple[dict[str, str], list[tuple[int, str]]]:
    markers = validation_marker_set(
        repo_root, contract["marker"], session_key=session_key(session)
    )
    generation = validation_edit_generation(markers)
    outstanding: list[tuple[int, str]] = []
    for index, declared in enumerate(contract["commands"]):
        if generation == 0:
            continue
        ran = command_ran_marker(markers, index)
        try:
            ran_ns = os.stat(ran, follow_symlinks=False).st_mtime_ns
        except OSError:
            outstanding.append((index, declared))
            continue
        if ran_ns < generation:
            outstanding.append((index, declared))
    return markers, outstanding


def command_status(args: argparse.Namespace) -> int:
    repo_root = resolve_repo(args.repo)
    contracts = selected_contracts(repo_root, args.context)
    rendered = []
    any_outstanding = False
    for contract in contracts:
        markers, outstanding = marker_state(repo_root, contract, args.session)
        waiver = read_validation_waiver(markers, repo_root)
        if outstanding and waiver is None:
            any_outstanding = True
        rendered.append(
            {
                "context": contract["context"],
                "commands": list(contract["commands"]),
                "marker": contract["marker"],
                "outstanding_commands": [declared for _index, declared in outstanding],
                "edit_generation_ns": validation_edit_generation(markers),
                "waiver": (
                    None
                    if waiver is None
                    else {
                        "reason": waiver["reason"],
                        "recorded_at": waiver.get("recorded_at", ""),
                    }
                ),
            }
        )
    emit(
        "status",
        True,
        {
            "repository": repo_root,
            "session_namespace": session_key(args.session) or "shared",
            "outstanding": any_outstanding,
            "contracts": rendered,
        },
        args.format,
    )
    return EXIT_OK


def command_run(args: argparse.Namespace) -> int:
    repo_root = resolve_repo(args.repo)
    contracts = selected_contracts(repo_root, args.context)
    if not contracts:
        return _fail("contract-undeclared", "no validation contract is declared")

    declared_everywhere = {
        declared for contract in contracts for declared in contract["commands"]
    }
    if args.command is not None and args.command not in declared_everywhere:
        # The lane runs the repository's own declared shape and nothing else.
        return _fail(
            "command-undeclared",
            "the requested command is not declared by this repository's validation contract",
        )

    results: list[dict[str, Any]] = []
    overall = EXIT_OK
    for contract in contracts:
        markers, _outstanding = marker_state(repo_root, contract, args.session)
        for index, declared in enumerate(contract["commands"]):
            if args.command is not None and declared != args.command:
                continue
            completed = subprocess.run(
                declared,
                shell=True,
                cwd=repo_root,
                check=False,
            )
            passed = completed.returncode == 0
            if passed:
                try:
                    lock = acquire_validation_state_lock(repo_root)
                except OSError:
                    return _fail(
                        "state-unwritable",
                        "validation state could not be locked for the outcome record",
                    )
                with lock:
                    if not touch_marker(command_ran_marker(markers, index)):
                        return _fail(
                            "state-unwritable",
                            "the declared command passed but its outcome could not be recorded",
                        )
                    try:
                        os.unlink(command_failed_marker(markers, index))
                    except OSError:
                        pass
            else:
                overall = EXIT_FAILED
            results.append(
                {
                    "context": contract["context"],
                    "command": declared,
                    "status": "passed" if passed else "failed",
                    "exit_code": None if passed else completed.returncode,
                }
            )
    if not results:
        return _fail("command-unmatched", "no declared command matched the selection")
    emit(
        "run",
        overall == EXIT_OK,
        {"repository": repo_root, "commands": results}
        if overall == EXIT_OK
        else {
            "code": "declared-validation-failed",
            "message": "a declared validation command failed",
            "repository": repo_root,
            "commands": results,
        },
        args.format,
    )
    return overall


def command_waive(args: argparse.Namespace) -> int:
    reason = (args.reason or "").strip()
    if not reason:
        return _fail("reason-required", "a waiver requires a recorded reason")
    if len(reason) > VALIDATION_WAIVER_MAX_REASON_CHARS:
        return _fail("reason-too-long", "the waiver reason exceeds its length budget")
    repo_root = resolve_repo(args.repo)
    contracts = selected_contracts(repo_root, args.context)
    if not contracts:
        return _fail("contract-undeclared", "no validation contract is declared")

    recorded = []
    for contract in contracts:
        markers, _outstanding = marker_state(repo_root, contract, args.session)
        body = {
            "schema_version": VALIDATION_WAIVER_SCHEMA,
            "recorded_at": _timestamp(),
            "reason": reason,
            "repository": repo_root,
            "context": contract["context"],
            "contract_key": markers["contract_key"],
            "target_stem": markers.get("target_stem", markers["stem"]),
            "product": markers.get("product", "shared"),
            "session_key": markers.get("session_key", ""),
            "edit_generation_ns": validation_edit_generation(markers),
        }
        if not _write_private_json(validation_waiver_marker(markers), body):
            return _fail("state-unwritable", "the waiver record could not be written")
        recorded.append(contract["context"])
    emit(
        "waive",
        True,
        {
            "schema_version": VALIDATION_WAIVER_SCHEMA,
            "repository": repo_root,
            "context": ", ".join(recorded),
            "reason": reason,
            "session_namespace": session_key(args.session) or "shared",
        },
        args.format,
    )
    return EXIT_OK


def command_revoke(args: argparse.Namespace) -> int:
    repo_root = resolve_repo(args.repo)
    revoked = []
    for contract in selected_contracts(repo_root, args.context):
        markers, _outstanding = marker_state(repo_root, contract, args.session)
        path = validation_waiver_marker(markers)
        try:
            os.unlink(path)
        except FileNotFoundError:
            continue
        except OSError:
            return _fail("state-unwritable", "the waiver record could not be removed")
        revoked.append(contract["context"])
    emit("revoke", True, {"repository": repo_root, "revoked": revoked}, args.format)
    return EXIT_OK


def _timestamp() -> str:
    import datetime

    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _write_private_json(path: str, body: dict[str, Any]) -> bool:
    import tempfile

    descriptor = -1
    temporary = ""
    try:
        directory = os.path.dirname(path)
        os.makedirs(directory, mode=0o700, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(body, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.replace(temporary, path)
        return True
    except OSError:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            if temporary:
                os.unlink(temporary)
        except OSError:
            pass
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validation-recovery",
        description=(
            "Out-of-band controller for a repository's declared validation "
            "contract. Exposes no general shell escape."
        ),
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)
    subparsers.add_parser("status", help="show the contract and what is outstanding")
    run = subparsers.add_parser("run", help="execute only the declared command shape")
    run.add_argument(
        "--command",
        help="run one exact declared command instead of every declared command",
    )
    waive = subparsers.add_parser("waive", help="record a structured waiver")
    waive.add_argument("--reason", help="why validation is being waived (required)")
    subparsers.add_parser("revoke", help="withdraw a recorded waiver")

    for subparser in subparsers.choices.values():
        subparser.add_argument(
            "--format", choices=("text", "json"), default="text"
        )
        subparser.add_argument(
            "--repo", help="repository path (default: current directory)"
        )
        subparser.add_argument("--context", help="limit to one declared intent")
        subparser.add_argument(
            "--session",
            help=(
                "target session identity whose marker namespace the gate reads "
                "(defaults to AGENT_SESSION_ID, then the shared namespace)"
            ),
        )

    arguments = parser.parse_args(argv)

    handlers = {
        "status": command_status,
        "run": command_run,
        "waive": command_waive,
        "revoke": command_revoke,
    }
    try:
        return handlers[arguments.verb](arguments)
    except SystemExit as error:
        code = error.code
        return code if isinstance(code, int) else EXIT_USAGE
    except ValueError as error:
        return _fail("unsafe-validation-state", str(error))


if __name__ == "__main__":
    sys.exit(main())
