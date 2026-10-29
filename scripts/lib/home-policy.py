#!/usr/bin/env python3
"""Durable home-policy copy and its bounded health probe.

The Claude and Codex home-policy links point at an owner-managed copy under the
product state home instead of the disposable `build/<product>/AGENT_HOME.md`
render output, so cleaning build output cannot orphan an installed link.

  publish  atomically refresh the owner-managed copy and its source record
  check    read-only probe of each home link; one JSON envelope on stdout,
           exit 0 only when every link is healthy
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

POLICY_NAME = "AGENT_HOME.md"
RECORD_NAME = "source.json"
SCHEMA = "agent-runtime-kit.home-policy.v1"
SYNC_SCRIPT = "scripts/sync-runtime-surfaces.sh"


def canon(path):
    return os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))


def link_target(link):
    raw = os.readlink(link)
    return canon(raw if os.path.isabs(raw) else os.path.join(os.path.dirname(link), raw))


def source_commit(source_root):
    proc = subprocess.run(["git", "-C", source_root, "rev-parse", "HEAD"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return proc.stdout.decode().strip() or None if proc.returncode == 0 else None


def write_atomic(path, data):
    tmp = "%s.tmp.%d" % (path, os.getpid())
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def publish(args):
    with open(args.source, "rb") as handle:
        data = handle.read()
    if not data.strip():
        sys.exit("home policy source is empty: %s" % args.source)
    if os.path.islink(args.store_dir):
        sys.exit("home policy store is a symlink; refusing to write through it: %s" % args.store_dir)
    os.makedirs(args.store_dir, exist_ok=True)
    write_atomic(os.path.join(args.store_dir, POLICY_NAME), data)
    record = {"schema_version": SCHEMA, "product": args.product,
              "source_root": args.source_root, "source_commit": source_commit(args.source_root),
              "sha256": hashlib.sha256(data).hexdigest()}
    write_atomic(os.path.join(args.store_dir, RECORD_NAME),
                 (json.dumps(record, sort_keys=True) + "\n").encode())


def read_state(target):
    """Classify a link target that the owner would accept."""
    if not os.path.exists(target):
        return "dangling"
    try:
        with open(target, "rb") as handle:
            data = handle.read()
    except OSError:
        return "unreadable"
    return "ok" if data.strip() else "empty"


def installed_record(store_dir):
    try:
        with open(os.path.join(store_dir, RECORD_NAME), encoding="utf-8") as handle:
            record = json.load(handle)
        return {"source_commit": record.get("source_commit"), "sha256": record.get("sha256")}
    except (OSError, ValueError, AttributeError):
        return None


def probe(product, link, store_dir, source_root):
    owned = canon(os.path.join(store_dir, POLICY_NAME))
    target = None
    if not os.path.lexists(link):
        state = "absent"
    elif not os.path.islink(link):
        state = "foreign"
    else:
        target = link_target(link)
        if target == owned:
            state = read_state(target)
            state = "healthy" if state == "ok" else state
        elif not os.path.exists(target):
            state = "dangling"
        else:
            state = "foreign"
    sync = "bash %s --apply --product %s" % (os.path.join(source_root, SYNC_SCRIPT), product)
    manual = state == "foreign" or (target is not None and target != owned)
    remediation = ("review the link and move it aside manually, then run: " + sync
                   if manual else sync)
    return {"product": product, "state": state, "healthy": state == "healthy", "link": link,
            "target": target, "expected_target": owned,
            "source": {"root": source_root, "installed": installed_record(store_dir)},
            "remediation": None if state == "healthy" else remediation}


def check(args):
    products = [probe(p, link, store, args.source_root) for p, link, store in args.entry]
    ok = all(item["healthy"] for item in products)
    print(json.dumps({"schema_version": SCHEMA, "ok": ok, "products": products}, sort_keys=True))
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pub = sub.add_parser("publish")
    pub.add_argument("--product", required=True)
    pub.add_argument("--source", required=True)
    pub.add_argument("--store-dir", required=True)
    pub.add_argument("--source-root", required=True)
    chk = sub.add_parser("check")
    chk.add_argument("--source-root", required=True)
    chk.add_argument("--entry", nargs=3, action="append", required=True,
                     metavar=("PRODUCT", "LINK", "STORE_DIR"))
    args = parser.parse_args()
    if args.command == "publish":
        publish(args)
        return 0
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
