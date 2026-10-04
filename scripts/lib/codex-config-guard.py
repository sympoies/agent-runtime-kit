#!/usr/bin/env python3
"""Run a registry write without silently losing managed delimiter lines.

This conserves the census of all exact standalone managed marker lines, including
literal lines in TOML strings. It does not interpret, repair or whitelist owners;
agent-hook remains the authority for TOML-aware marker-layout validation.
Registry refresh must run with other provider-config writers idle.
"""

import collections
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile


def read_config(path):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None, None
    try:
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1 or metadata.st_mode & 0o022
                or metadata.st_size > 1024 * 1024):
            raise ValueError("unsafe-provider-config")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("unsafe-provider-config")
        return raw, (metadata.st_dev, metadata.st_ino, stat.S_IMODE(metadata.st_mode))
    finally:
        os.close(descriptor)


def census(raw):
    markers = collections.Counter()
    for line in (raw or b"").splitlines():
        for prefix, suffix in ((b"# >>> ", b" >>>"), (b"# <<< ", b" <<<")):
            if line.startswith(prefix) and line.endswith(suffix) and len(line) > len(prefix) + len(suffix):
                markers[line] += 1
    return markers


def digest(raw):
    return None if raw is None else "sha256:" + hashlib.sha256(raw).hexdigest()


def run(path, command):
    parent = os.path.dirname(os.path.abspath(path))
    parent_metadata = os.lstat(parent)
    if (not stat.S_ISDIR(parent_metadata.st_mode) or parent_metadata.st_uid != os.getuid()
            or parent_metadata.st_mode & 0o022):
        raise ValueError("unsafe-provider-directory")
    original, identity = read_config(path)
    before = census(original)
    snapshot = None
    retain = False
    if original is not None:
        descriptor, snapshot = tempfile.mkstemp(prefix=".codex-config-snapshot.", dir=parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(original)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            os.unlink(snapshot)
            raise
    try:
        # Recheck after snapshot creation, before admitting the external write.
        if read_config(path) != (original, identity):
            raise ValueError("provider-drift-before-command")
        status = subprocess.run(command, check=False).returncode
        retain = True  # An unreadable post-command target cannot justify cleanup.
        current, current_identity = read_config(path)
        after = census(current)
        receipt = {"schema_version": "agent-runtime-kit.codex-config-guard.v1",
                   "before_digest": digest(original), "after_digest": digest(current),
                   "before_markers": sum(before.values()), "after_markers": sum(after.values()),
                   "command_exit": status}
        if after == before:
            retain = False
            receipt["outcome"] = "preserved"
            print(json.dumps(receipt, sort_keys=True))
            return status
        # Do not reconstruct any owner block. Restore only this step's exact
        # snapshot, after a conventional identity/content recheck. This is not
        # a kernel fence against another config writer in the rename window.
        if snapshot is None:
            raise ValueError("marker-change-without-original")
        now_parent = os.lstat(parent)
        if (now_parent.st_dev, now_parent.st_ino, now_parent.st_mode) != (
                parent_metadata.st_dev, parent_metadata.st_ino, parent_metadata.st_mode):
            raise ValueError("provider-directory-drift")
        if read_config(path) != (current, current_identity):
            raise ValueError("provider-drift-before-restore")
        snapshot_raw, snapshot_identity = read_config(snapshot)
        if snapshot_raw != original or snapshot_identity[2] != 0o600:
            raise ValueError("provider-snapshot-drift")
        descriptor = os.open(snapshot, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(descriptor)
            if (metadata.st_dev, metadata.st_ino) != snapshot_identity[:2]:
                raise ValueError("provider-snapshot-drift")
            os.fchmod(descriptor, identity[2])
        finally:
            os.close(descriptor)
        os.replace(snapshot, path)
        snapshot = None
        directory = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        restored, restored_identity = read_config(path)
        if restored != original or restored_identity[2] != identity[2]:
            raise ValueError("provider-restore-readback-failed")
        receipt.update(outcome="restored-marker-loss", restored_digest=digest(original))
        print(json.dumps(receipt, sort_keys=True))
        return 65
    finally:
        if snapshot is not None and not retain:
            os.unlink(snapshot)
        elif snapshot is not None:
            print(json.dumps({"schema_version": "agent-runtime-kit.codex-config-guard.v1",
                              "outcome": "snapshot-retained"}), file=sys.stderr)


if __name__ == "__main__":
    try:
        if len(sys.argv) < 4 or sys.argv[2] != "--":
            raise ValueError("invalid-guard-arguments")
        result = run(sys.argv[1], sys.argv[3:])
    except (OSError, ValueError):
        print("Codex registry config preservation refused; inspect the retained state before retry.", file=sys.stderr)
        result = 65
    raise SystemExit(result)
