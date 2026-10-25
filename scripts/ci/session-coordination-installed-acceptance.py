#!/usr/bin/env python3
"""Opt-in installed-pair acceptance; stdout is a public-safe JSON receipt.

Run with python3. Only the two installed hook files are read from the runtime
home; execution uses byte-identical copies and fresh temporary authority/state.
The transport shim delegates every request to the real producer. Its sole fault
is discarding one successful admit reply, after the producer has committed it.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HOOK_FILES = ("session-coordination-guard.py", "hook_common.py")


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value) + "\n" if not isinstance(value, str) else value)
    path.chmod(0o600)


def verify_observation(value):
    """One oracle shared by real acceptance and deliberately unsafe fixtures."""
    counts = value["commands"]
    require(counts.get("broker prepare-admission-proof", 0) == 1, "preparation count")
    require(counts.get("broker proof", 0) == 1, "proof count")
    require(counts.get("work-context admit", 0) == 0, "admission replay")
    require(counts.get("work-context complete", 0) == 0, "unexpected completion")
    require(value["producer_unchanged"], "proof mutated producer state")
    require(value["initial_admit_count"] == 1, "lost reply lacks real committed admission")
    proofs = value["proofs"]
    case = value["case"]
    if case == "lost-reply":
        require(value["action"] == "allow", "committed active proof did not recover")
        require(value["phase"] == "active", "active record not recovered")
        require(value["executions"] == 1, "recovered tool execution count")
        require(any(p["kind"] == "admission" and p["status"] == "committed"
                    and p["state"] == "active" for p in proofs), "committed active proof missing")
    elif case == "terminal":
        require(value["action"] == "block", "pending Stop authorized execution")
        require(value["executions"] == 0, "terminal execution")
        require(value["terminal_retired"], "exact terminal bundle retained")
        require(value["active_preserved"], "active bundle over-deleted or changed")
        require(value["unrelated_preserved"], "unrelated data over-deleted or changed")
        require(any(p["state"] == "completed" and p["outcome"] == "pass" for p in proofs),
                "terminal proof missing")
        require(any(p["kind"] == "operation" and p["state"] == "active" for p in proofs),
                "active sibling proof missing")
    elif case == "unknown":
        require(value["action"] == "block", "unknown proof authorized execution")
        require(value["executions"] == 0, "unknown execution")
        require(value["phase"] == "admitting", "unknown proof promoted record")
        require(value["bundle_preserved"], "unknown bundle changed")
        require(any(p["kind"] == "admission" and p["status"] == "unknown" for p in proofs),
                "unknown producer proof missing")
    else:
        raise AssertionError("unknown acceptance case")


# No argv, stdin, raw output, tokens, paths, or digests of secret values are
# logged. Help/version probes are distinct from actual producer invocations.
TRANSPORT = '''#!{python}
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
words = [word for word in args if word in
         ("work-context", "broker", "admit", "complete", "show", "check",
          "status", "prepare-admission-proof", "proof")]
name = " ".join(words[:2]) if words else "probe"
if "--help" in args or "--version" in args:
    name = "probe"
result = subprocess.run([{producer!r}] + args, capture_output=True)
entry = {{"command": name, "exit_code": result.returncode}}
if name == "broker proof" and result.returncode == 0:
    body = json.loads(result.stdout)
    entry["proofs"] = [{{key: item.get("proof", {{}}).get(key)
                        for key in ("kind", "status", "state", "outcome", "provenance")}}
                       for item in body["data"]["proofs"]]
with open({log!r}, "a") as output:
    output.write(json.dumps(entry) + "\\n")
loss = pathlib.Path({loss!r})
if name == "work-context admit" and loss.exists() and result.returncode == 0:
    loss.unlink()
    sys.exit(1)
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
'''


class Fixture:
    def __init__(self, root, producer, hook, installed_hooks):
        self.root, self.producer, self.hook = root, producer, hook
        self.repo = root / "repo"
        self.repo.mkdir()
        self.state = root / "sessions-state"
        self.runtime = root / "runtime-state"
        self.log, self.loss = root / "commands.jsonl", root / "lose-reply"
        home = root / "home"
        hooks = home / ".codex/hooks"
        hooks.mkdir(parents=True)
        for name in HOOK_FILES:
            shutil.copy2(installed_hooks / name, hooks / name)
            require((hooks / name).read_bytes() == (ROOT / "core/hooks/shared" / name).read_bytes(),
                    "copied installed hook/source byte mismatch")
        bin_dir = root / "bin"
        bin_dir.mkdir()
        wrapper = bin_dir / "agent-session"
        wrapper.write_text(TRANSPORT.format(python=sys.executable, producer=str(producer),
                                           log=str(self.log), loss=str(self.loss)))
        wrapper.chmod(0o700)
        # Deliberately construct the environment: inherit no managed authority,
        # provider config, hook override, Git plumbing, or coordination root.
        self.env = {
            "PATH": str(bin_dir) + os.pathsep + os.defpath,
            "HOME": str(home), "CODEX_HOME": str(home / ".codex"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(root / "xdg-state"),
            "TMPDIR": str(root), "PYTHONDONTWRITEBYTECODE": "1",
            "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
            "AGENT_RUNTIME_STATE_HOME": str(self.runtime),
            "AGENT_SESSION_STATE_DIR": str(self.state),
            "AGENT_SESSION_ID": "fixture", "AGENT_SESSION_RUNTIME_ID": "incarnation-fixture",
            "AGENT_SESSION_COORDINATION_MODE": "enforce",
        }
        for args in (("init", "-q"),
                     ("remote", "add", "origin", "https://example.invalid/example/repository.git")):
            self.run(["git", *args])
        now = int(time.time())
        session_dir = self.state / "sessions/fixture"
        capability = secrets.token_hex(32)
        self.capability = session_dir / "coordination" / (
            "capability-" + digest(b"incarnation-fixture"))
        private(self.capability, capability)
        self.env["AGENT_SESSION_CAPABILITY_FILE"] = str(self.capability)
        private(session_dir / "coordination/heartbeat", f"incarnation-fixture:{now}\n")
        private(session_dir / "session.json", {
            "schema_version": "agent-session.session.v1", "id": "fixture", "agent": "codex",
            "mode": "interactive", "coordination_mode": "enforce", "title": "synthetic acceptance",
            "title_revision": 0, "cwd": str(self.repo), "tmux_session": "fixture",
            "prompt_file": None, "log_file": None,
            "created_at": "2030-01-01T00:00:00Z", "updated_at": "2030-01-01T00:00:00Z",
            "runtime": {"kind": "tmux", "tmux_session": "fixture", "generation": 1,
                        "started_at": "2030-01-01T00:00:00Z", "launch_id": "incarnation-fixture"},
            "delete_tmux_identity": {"launch_id": "incarnation-fixture", "session_id": "$94",
                                     "pane_id": "%94", "pane_pid": os.getpid(),
                                     "process_group_id": os.getpgrp(), "process_session_id": os.getsid(0)},
        })
        private(session_dir / "activity.json", {
            "schema_version": "agent-session.activity.v1", "runtime_id": "incarnation-fixture",
            "runtime_generation": 1, "pending_attention": [], "seen_event_count": 0,
            "state": {"schema_version": "agent-session.turn-state.v1", "phase": "working",
                      "phase_changed_at": "2030-01-01T00:00:00Z", "revision": 1,
                      "source": {"kind": "runtime", "provider": None, "confidence": "authoritative"},
                      "current_turn": {"provider_turn_id": "fixture-turn", "started_at": "2030-01-01T00:00:00Z"},
                      "last_turn": None},
        })
        self.registry = self.state / "coordination/registry.json"
        private(self.registry, {
            "schema_version": "agent-session.coordination-registry.v1", "fingerprint_epoch": 1,
            "fingerprint_key": secrets.token_hex(32),
            "brokers": {"fixture": {"session_id": "fixture", "incarnation": "incarnation-fixture",
                                     "capability_digest": digest(capability.encode()), "generation": 1,
                                     "coordination_mode": "enforce", "state": "ready",
                                     "heartbeat_at": "2030-01-01T00:00:00Z", "heartbeat_epoch": now}},
            "claims": [], "operations": [], "messages": [], "receipts": {}, "notifications": {},
        })
        claim = root / "claim.json"
        private(claim, {"schema_version": "agent-session.work-context-input.v1",
                        "intent": "implementation", "tier": "program/dispatch",
                        "repositories": ["example/repository"], "worktrees": [], "provider_refs": [],
                        "plan_refs": [], "scopes": [{"kind": "path-prefix", "repository": "example/repository",
                                                     "value": "src"}], "summary": "synthetic acceptance"})
        self.cli("work-context", "claim", "--file", str(claim), "--idempotency-key", "fixture-claim")
        self.policy = root / "policy.toml"
        private(self.policy, '''schema_version = "agent-hook.policy.v1"
bundle_id = "installed-pair-acceptance"
version = "2026.10.25.1"
[[rules]]
id = "fixture.coordination"
products = ["codex"]
events = ["PreToolUse", "Stop"]
priority = 10
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = { id = "agent-session.coordination.v1", reason_code = "coordination" }
''')
        self.config = root / "config.toml"
        private(self.config, 'schema_version = "agent-hook.config.v1"\n[policy]\n'
                f'path = {json.dumps(str(self.policy))}\ndigest = "sha256:{digest(self.policy.read_bytes())}"\n')
        self.namespace = self.runtime / "session-coordination" / digest(b"fixture")

    def run(self, command, payload=None):
        result = subprocess.run(command, cwd=self.repo, env=self.env, input=payload,
                                text=True, capture_output=True, timeout=60)
        if result.returncode != 0:
            try:
                body = json.loads(result.stdout)
                if (command[0] == str(self.hook) and result.returncode == 1
                        and body.get("ok") is True and body.get("data", {}).get("action") == "block"):
                    return result.stdout
                code = body.get("error", {}).get("code", "unknown")
            except ValueError:
                code = "non-json"
            safe_code = code if re.fullmatch(r"[a-z-]+", str(code)) else "unknown"
            require(False, f"fixture command failed (exit {result.returncode}, code {safe_code}); raw output suppressed")
        return result.stdout

    def cli(self, *args):
        return json.loads(self.run([str(self.producer), "--state-dir", str(self.state), *args,
                                   "--session", "fixture", "--capability-file", str(self.capability),
                                   "--format", "json"]))["data"]

    def dispatch(self, call="lost", event="PreToolUse"):
        payload = {"hook_event_name": event, "cwd": str(self.repo), "session_id": "provider-fixture",
                   "tool_use_id": call, "tool_name": "Write",
                   "tool_input": {"file_path": str(self.repo / "src/output.txt"), "content": "synthetic prompt canary"}}
        body = json.loads(self.run([str(self.hook), "--config", str(self.config), "--state-dir",
                                   str(self.root / "hook-state"), "dispatch", "--product", "codex",
                                   "--format", "json"], json.dumps(payload)))
        require(body.get("ok") is True, "dispatch service failure")
        return body["data"]["action"]

    def record_path(self, call):
        return self.namespace / (digest(call.encode()) + ".json")

    def bundle(self, call):
        path = self.record_path(call)
        record = json.loads(path.read_text())
        return [path] + [Path(record[key]) for key in ("token_file", "targets_file", "outcome_file")]

    def snapshot(self, paths):
        return {path: path.read_bytes() if path.exists() else None for path in paths}

    def lost_reply(self):
        self.loss.touch()
        require(self.dispatch() == "block", "lost reply authorized execution")
        require(not self.loss.exists(), "fault did not discard a real successful admission")
        record = json.loads(self.record_path("lost").read_text())
        require(record["phase"] == "admitting", "lost reply did not retain admission intent")
        operations = json.loads(self.registry.read_text())["operations"]
        require(len(operations) == 1 and operations[0]["state"] == "active", "real admission did not commit")
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        require(sum(row["command"] == "work-context admit" and row["exit_code"] == 0 for row in calls) == 1,
                "initial admission count")
        return record, operations[0]

    def observe(self, case):
        record, operation = self.lost_reply()
        if case == "terminal":
            self.cli("work-context", "complete", "--lease", operation["lease_id"],
                     "--if-revision", str(operation["revision"]), "--execution-token-file", record["token_file"],
                     "--outcome", "pass", "--idempotency-key", "fixture-terminal")
            # Create a second real active operation with distinct private proof
            # material. Seed only its consumer record; do not replay the lost one.
            active = dict(record)
            active_path = self.record_path("active")
            for key, suffix in (("token_file", ".token"), ("targets_file", ".targets.json"),
                                ("outcome_file", ".outcome")):
                target = active_path.with_name(active_path.stem + ".fixture" + suffix)
                if key != "outcome_file":
                    private(target, secrets.token_hex(20) if key == "token_file" else Path(record[key]).read_text())
                active[key] = str(target)
            active["admit_idempotency"] = "fixture-active"
            lease = self.cli("work-context", "admit", "--claim", active["claim_id"],
                             "--if-revision", str(active["claim_revision"]), "--targets-file", active["targets_file"],
                             "--operation", active["operation"], "--execution-token-file", active["token_file"],
                             "--idempotency-key", active["admit_idempotency"])
            active.update(phase="active", lease_id=lease["lease_id"], lease_revision=lease["revision"])
            private(active_path, active)
            unrelated = self.namespace / "unrelated.json"
            private(unrelated, {"schema_version": "fixture.unrelated.v1"})
            other = self.runtime / "session-coordination/other/unrelated.token"
            private(other, "synthetic unrelated canary")
            terminal_paths = self.bundle("lost")
            survivors = self.snapshot(self.bundle("active"))
            unrelated_before = self.snapshot([unrelated, other])
        elif case == "unknown":
            # Keep the committed operation, but query a never-submitted intent.
            # The actual producer, rather than a stub, must return unknown.
            record["admit_idempotency"] = "fixture-never-submitted"
            private(self.record_path("lost"), record)
            before_bundle = self.snapshot(self.bundle("lost"))
        self.log.write_text("")
        before = self.registry.read_bytes()
        action = self.dispatch(event="Stop" if case == "terminal" else "PreToolUse")
        # A harmless fixture-owned file stands in for the gated product tool.
        executions = int(action == "allow" and case != "terminal")
        if executions:
            private(self.root / "executed", "synthetic tool executed")
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        value = {"case": case, "commands": dict(Counter(row["command"] for row in calls)),
                 "initial_admit_count": 1,
                 "producer_unchanged": before == self.registry.read_bytes(),
                 "action": action, "executions": executions,
                 "proofs": [proof for row in calls for proof in row.get("proofs", [])]}
        if case == "terminal":
            value.update(terminal_retired=all(not path.exists() for path in terminal_paths),
                         active_preserved=survivors == self.snapshot(survivors),
                         unrelated_preserved=unrelated_before == self.snapshot(unrelated_before))
        else:
            value["phase"] = json.loads(self.record_path("lost").read_text())["phase"]
            if case == "unknown":
                value["bundle_preserved"] = before_bundle == self.snapshot(before_bundle)
        verify_observation(value)
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-session-bin", default=shutil.which("agent-session"))
    parser.add_argument("--agent-hook-bin", default=shutil.which("agent-hook"))
    parser.add_argument("--installed-hooks", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "hooks")
    args = parser.parse_args()
    binaries, versions, hashes = {}, {}, {}
    for name, raw in (("agent-session", args.agent_session_bin), ("agent-hook", args.agent_hook_bin)):
        require(raw and Path(raw).is_absolute(), "installed executable must be an absolute path")
        binary = Path(raw).resolve(strict=True)
        require(os.access(binary, os.X_OK), "installed binary is not executable")
        version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, check=True).stdout.strip()
        require(re.fullmatch(rf"{name} \d+\.\d+\.\d+ \([a-zA-Z0-9., ()-]+\)", version), "unrecognized released version")
        binaries[name], versions[name], hashes[name] = binary, version, digest(binary.read_bytes())
    require(versions["agent-session"].split(" ", 1)[1] == versions["agent-hook"].split(" ", 1)[1],
            "installed producer/dispatcher versions do not match")
    hooks = {}
    for name in HOOK_FILES:
        installed = (args.installed_hooks / name).read_bytes()
        require(installed == (ROOT / "core/hooks/shared" / name).read_bytes(), "installed hook/source byte mismatch")
        hooks[name] = digest(installed)
    observations = []
    with tempfile.TemporaryDirectory(prefix="installed-pair-") as temporary:
        for case in ("lost-reply", "terminal", "unknown"):
            root = Path(temporary) / case
            root.mkdir(mode=0o700)
            observations.append(Fixture(root, binaries["agent-session"], binaries["agent-hook"], args.installed_hooks).observe(case))
    print(json.dumps({"schema_version": "runtime-kit.installed-pair-acceptance.v1", "status": "pass",
                      "versions": versions, "binary_sha256": hashes, "installed_hook_sha256": hooks,
                      "observations": observations}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # Raw CLI output and exception paths may contain authority or prompt
        # material. Assertion messages above are fixed, public-safe strings.
        print("installed-pair acceptance failed: " + (str(error) if isinstance(error, AssertionError)
                                                    else type(error).__name__), file=sys.stderr)
        sys.exit(1)
