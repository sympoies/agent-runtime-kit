#!/usr/bin/env bash
# Audit loaded product artifacts for accidental cross-product prompt leakage.
#
# Compatibility: macOS system bash 3.2 and Linux bash.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ALLOW_FILE="${PRODUCT_LEAK_ALLOW_FILE:-$REPO_ROOT/scripts/ci/product-leak-allow.yaml}"
SELF_TEST=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/ci/product-leak-audit.sh [--self-test]

Scans rendered/loaded Codex, Claude, and Hermes artifacts for foreign product
sentinels (each product's artifacts must not name either of the other two, e.g.
`Claude` / `CLAUDE_` / `Hermes` / `HERMES_` in Codex artifacts), allowing only
documented entries in scripts/ci/product-leak-allow.yaml.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --self-test)
      SELF_TEST=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "product-leak-audit: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run_scan() {
  python3 - "$REPO_ROOT" "$ALLOW_FILE" "$@" <<'PY'
from __future__ import annotations

import fnmatch
import os
import re
import sys
from pathlib import Path


repo = Path(sys.argv[1]).resolve()
allow_file = Path(sys.argv[2]).resolve()
extra_args = sys.argv[3:]

# Each product's loaded artifacts must not name a foreign product. With three
# products, "foreign" is the other two; documented cross-product prose is
# allowlisted in scripts/ci/product-leak-allow.yaml.
_CODEX = ("Codex", re.compile(r"\bCodex\b"))
_CODEX_ENV = ("CODEX_", re.compile(r"CODEX_"))
_CLAUDE = ("Claude", re.compile(r"\bClaude\b"))
_CLAUDE_ENV = ("CLAUDE_", re.compile(r"CLAUDE_"))
_HERMES = ("Hermes", re.compile(r"\bHermes\b"))
_HERMES_ENV = ("HERMES_", re.compile(r"HERMES_"))

SENTINELS = {
    "codex": [_CLAUDE, _CLAUDE_ENV, _HERMES, _HERMES_ENV],
    "claude": [_CODEX, _CODEX_ENV, _HERMES, _HERMES_ENV],
    "hermes": [_CODEX, _CODEX_ENV, _CLAUDE, _CLAUDE_ENV],
}


def strip_value(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
        return raw[1:-1]
    return raw


def parse_allow(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"product-leak-audit: missing allowlist: {path}")
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "allow:":
            continue
        if stripped.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if stripped and ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip()] = strip_value(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = strip_value(value)
    if current is not None:
        entries.append(current)
    for idx, entry in enumerate(entries, 1):
        for required in ("path", "reason"):
            if not entry.get(required):
                raise SystemExit(
                    f"product-leak-audit: allow entry {idx} missing {required}"
                )
        product = entry.get("product", "any")
        if product not in {"any", "codex", "claude", "hermes"}:
            raise SystemExit(
                f"product-leak-audit: allow entry {idx} has invalid product={product!r}"
            )
    return entries


ALLOW = parse_allow(allow_file)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def add_existing(files: list[Path], path: Path) -> None:
    if path.is_file():
        files.append(path)


def add_tree(files: list[Path], path: Path) -> None:
    if not path.exists():
        return
    for candidate in path.rglob("*"):
        if candidate.is_file():
            files.append(candidate)


def product_files() -> dict[str, list[Path]]:
    files: dict[str, list[Path]] = {"codex": [], "claude": [], "hermes": []}

    for product in ("codex", "claude", "hermes"):
        add_existing(files[product], repo / "build" / product / "AGENT_HOME.md")
        add_tree(files[product], repo / "build" / product / "plugins")
        add_tree(files[product], repo / "build" / product / "agents")

    add_existing(files["codex"], repo / "targets/codex/.agents/plugins/marketplace.json")
    add_tree(files["codex"], repo / "targets/codex/plugins")

    add_existing(files["claude"], repo / "targets/claude/.claude-plugin/marketplace.json")
    add_tree(files["claude"], repo / "targets/claude/plugins")
    add_tree(files["claude"], repo / "targets/claude/commands")
    add_tree(files["claude"], repo / "targets/claude/scripts")

    # Hermes has no marketplace, agents tree, commands, or scripts; its loaded
    # surface is the rendered home prompt + skills plus the plugin manifests.
    add_tree(files["hermes"], repo / "targets/hermes/plugins")

    for raw in extra_args:
        if ":" not in raw:
            raise SystemExit(f"product-leak-audit: invalid extra file spec: {raw}")
        product, file_path = raw.split(":", 1)
        if product not in files:
            raise SystemExit(f"product-leak-audit: invalid extra product: {product}")
        files[product].append(Path(file_path))

    return files


used_allow_indices: set[int] = set()


def is_allowed(product: str, rel_path: str, sentinel: str) -> bool:
    for idx, entry in enumerate(ALLOW):
        entry_product = entry.get("product", "any")
        if entry_product not in {"any", product}:
            continue
        entry_sentinel = entry.get("sentinel")
        if entry_sentinel and entry_sentinel != sentinel:
            continue
        if fnmatch.fnmatch(rel_path, entry["path"]):
            used_allow_indices.add(idx)
            return True
    return False


files_by_product = product_files()
failures: list[tuple[str, str, int, str, str]] = []
scanned = 0
for product, files in files_by_product.items():
    seen: set[Path] = set()
    for file_path in files:
        resolved = file_path.resolve()
        if resolved in seen or not file_path.is_file():
            continue
        seen.add(resolved)
        rel_path = rel(file_path)
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for line_no, line in enumerate(text.splitlines(), 1):
            for sentinel, pattern in SENTINELS[product]:
                if pattern.search(line) and not is_allowed(product, rel_path, sentinel):
                    failures.append((product, rel_path, line_no, sentinel, line.strip()))

unused_allow = [
    (idx + 1, entry)
    for idx, entry in enumerate(ALLOW)
    if idx not in used_allow_indices
]
if unused_allow:
    print("product-leak-audit: unused allow entry", file=sys.stderr)
    for idx, entry in unused_allow:
        print(
            f"  - entry={idx} product={entry.get('product', 'any')} path={entry['path']} sentinel={entry.get('sentinel', 'any')}",
            file=sys.stderr,
        )
    sys.exit(1)

if failures:
    print("product-leak-audit: foreign product sentinel found", file=sys.stderr)
    for product, path, line_no, sentinel, line in failures[:50]:
        print(
            f"  - product={product} path={path}:{line_no} sentinel={sentinel} line={line}",
            file=sys.stderr,
        )
    if len(failures) > 50:
        print(f"  ... {len(failures) - 50} more", file=sys.stderr)
    sys.exit(1)

print(f"product-leak-audit: OK files_checked={scanned} allow_entries={len(ALLOW)}")
PY
}

if [ "$SELF_TEST" = "1" ]; then
  out_root="${AGENT_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/out/product-leak-audit"
  self_test_dir="$out_root/self-test-$$"
  mkdir -p "$self_test_dir"
  leak_file="$self_test_dir/codex-loaded.txt"
  printf 'Unexpected Claude sentinel in a Codex loaded artifact\n' >"$leak_file"
  set +e
  run_scan "codex:$leak_file" >"$self_test_dir/stdout.txt" 2>"$self_test_dir/stderr.txt"
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    echo "product-leak-audit: self-test failed; injected leak passed" >&2
    cat "$self_test_dir/stdout.txt" >&2
    exit 1
  fi
  if ! grep -q "sentinel=Claude" "$self_test_dir/stderr.txt"; then
    echo "product-leak-audit: self-test failed; expected sentinel not reported" >&2
    cat "$self_test_dir/stderr.txt" >&2
    exit 1
  fi
  echo "product-leak-audit: self-test OK artifact=$self_test_dir"
  exit 0
fi

run_scan
