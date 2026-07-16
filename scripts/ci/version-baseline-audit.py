#!/usr/bin/env python3
"""Audit the version-baseline mirrors for internal consistency.

The "version baseline" lives in several files with different owners and
update rules:

  * Product floor (codex / claude) — source of truth is
    ``manifests/runtime-roots.yaml`` (``min_version`` /
    ``recommended_version`` / ``min_version_effective_from``). It is mirrored,
    by hand, in the ``README.md`` "Version baseline" table and the
    "Version Floors" statement of ``docs/source/harness-shape-<product>.md``.
  * nils-cli surface pin — source of truth is
    ``docs/source/nils-cli-pin.yaml`` (``pinned_tag``). It is mirrored in the
    README table row, the ``docs/source/nils-cli-surface.md`` snapshot, and the
    "pinned snapshot" line of each ``harness-shape`` doc. (The pin itself is
    owned by the ``meta:nils-cli-bump`` skill; this audit only checks that the
    prose mirrors agree with the pin.)

Hand-edited mirrors drift. ``check`` is a deterministic, network-free gate that
fails closed on any mismatch so CI catches the drift. ``report`` additionally
probes installed and latest-available versions (best effort, network) and is
always advisory (exit 0).

Per-surface ``min_product`` values in ``manifests/surfaces.yaml`` are
intentionally NOT checked here: they are per-surface historical minimums,
independent of the product floor (see PR #344), and move only when a surface
gains a real dependency on a newer release.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RUNTIME_ROOTS = "manifests/runtime-roots.yaml"
README = "README.md"
NILS_PIN = "docs/source/nils-cli-pin.yaml"
NILS_SURFACE = "docs/source/nils-cli-surface.md"
SKILLS_MANIFEST = "manifests/skills.yaml"
HARNESS = {
    "codex": "docs/source/harness-shape-codex.md",
    "claude": "docs/source/harness-shape-claude.md",
    "hermes": "docs/source/harness-shape-hermes.md",
}

# Map a product key to how it is labelled in the README table row.
README_PRODUCT_LABEL = {
    "codex": "Codex CLI",
    "claude": "Claude Code",
    "hermes": "Hermes Agent",
}

# npm package per product, for the advisory `report` mode. Hermes has no npm
# distribution, so it is excluded from the npm availability probe below.
NPM_PACKAGE = {
    "codex": "@openai/codex",
    "claude": "@anthropic-ai/claude-code",
}


def _read(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), "r", encoding="utf-8") as handle:
        return handle.read()


def _search(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise LookupError("could not locate %s" % label)
    return match.group(1)


# --- source-of-truth extractors ---------------------------------------------


def runtime_roots_floor():
    """Return {product: {min, recommended, effective}} from runtime-roots."""
    text = _read(RUNTIME_ROOTS)
    out = {}
    for product in ("codex", "claude", "hermes"):
        # Scope to the product's block: from `  <product>:` to the next
        # top-level-ish `  <key>:` product or end of file.
        block = re.search(
            r"\n  %s:\n(.*?)(?=\n  [a-z_]+:\n|\Z)" % re.escape(product),
            text,
            re.DOTALL,
        )
        if not block:
            raise LookupError("runtime-roots: missing %s block" % product)
        body = block.group(1)
        out[product] = {
            "min": _search(r'min_version:\s*"([^"]+)"', body, "%s.min_version" % product),
            "recommended": _search(
                r'recommended_version:\s*"([^"]+)"', body, "%s.recommended_version" % product
            ),
            "effective": _search(
                r'min_version_effective_from:\s*"([^"]+)"',
                body,
                "%s.min_version_effective_from" % product,
            ),
        }
    return out


def pinned_tag() -> str:
    return _search(r'pinned_tag:\s*"([^"]+)"', _read(NILS_PIN), "nils-cli-pin.pinned_tag")


# --- mirror extractors -------------------------------------------------------


def readme_rows():
    """Return {'codex':(floor,effective), 'claude':(floor,effective), 'nils':tag}."""
    text = _read(README)
    rows = {}
    for product, label in README_PRODUCT_LABEL.items():
        floor = _search(
            r"\|\s*%s\s*\(`[^`]+`\)\s*\|\s*`([^`]+)`\s*\(effective [^)]+\)" % re.escape(label),
            text,
            "README %s floor" % product,
        )
        effective = _search(
            r"\|\s*%s\s*\(`[^`]+`\)\s*\|\s*`[^`]+`\s*\(effective ([^)]+)\)" % re.escape(label),
            text,
            "README %s effective" % product,
        )
        rows[product] = (floor, effective)
    rows["nils"] = _search(
        r"\|\s*`nils-cli`\s*surface\s*\(`[^`]+`\)\s*\|\s*`([^`]+)`\s*\|",
        text,
        "README nils-cli surface tag",
    )
    return rows


def harness_values(product: str):
    """Return {'floor', 'effective', 'pin'} mirrored in a harness-shape doc."""
    text = _read(HARNESS[product])
    floor = _search(
        r"product `min_version` / `recommended_version`:\s*\*\*([^*]+)\*\*",
        text,
        "harness-shape %s floor" % product,
    )
    effective = _search(
        r"`min_version_effective_from`:\s*\*\*([^*]+)\*\*",
        text,
        "harness-shape %s effective" % product,
    )
    pin = _search(
        r"pinned snapshot\s*\*\*([^*]+)\*\*",
        text,
        "harness-shape %s pinned snapshot" % product,
    )
    return {"floor": floor, "effective": effective, "pin": pin}


def harness_required_cli_examples(product: str):
    """Return the documented ``required_clis`` examples as (name, floor)."""
    text = _read(HARNESS[product])
    match = re.search(
        r"Per-skill nils-cli floors come from .*?These gate skill\n"
        r"\s*bodies, not the harness load path\.",
        text,
        re.DOTALL,
    )
    if not match:
        return []
    return re.findall(r'`([a-z][a-z0-9-]*): \">=([^\"]+)\"`', match.group(0))


def manifest_required_cli_pairs():
    """Return every exact CLI floor declared by a skill manifest entry."""
    return set(
        re.findall(
            r'^      ([a-z][a-z0-9-]*): \">=([^\"]+)\"$',
            _read(SKILLS_MANIFEST),
            re.MULTILINE,
        )
    )


def surface_describe() -> str:
    return _search(
        r"Active `git describe --tags` output:\s*`([^`]+)`",
        _read(NILS_SURFACE),
        "nils-cli-surface active describe",
    )


def surface_pinned_tag() -> str:
    """The ``pinned_tag: <tag>`` prose cue in the surface snapshot doc.

    Operators copy this line into the pin manifest, so it must not drift from
    the active-describe line or the real pin.
    """
    return _search(
        r"pinned_tag:\s*(v?\d+\.\d+\.\d+)",
        _read(NILS_SURFACE),
        "nils-cli-surface pinned_tag prose",
    )


# --- checks ------------------------------------------------------------------


class Result:
    def __init__(self):
        self.checks = []  # (ok: bool, name: str, detail: str)

    def add(self, ok: bool, name: str, detail: str):
        self.checks.append((ok, name, detail))

    def expect(self, name: str, expected: str, observed: str, observed_label: str):
        ok = expected == observed
        detail = "expected=%s %s=%s" % (expected, observed_label, observed)
        self.add(ok, name, detail)

    @property
    def failed(self):
        return [c for c in self.checks if not c[0]]


def run_check() -> Result:
    res = Result()
    roots = runtime_roots_floor()
    pin = pinned_tag()
    readme = readme_rows()
    manifest_cli_pairs = manifest_required_cli_pairs()

    # Product floor: runtime-roots is the source of truth.
    for product in ("codex", "claude", "hermes"):
        truth = roots[product]
        rd_floor, rd_eff = readme[product]
        hs = harness_values(product)
        res.expect("product-floor.%s.readme" % product, truth["min"], rd_floor, "readme")
        res.expect("product-floor.%s.harness" % product, truth["min"], hs["floor"], "harness-shape")
        res.expect("effective.%s.readme" % product, truth["effective"], rd_eff, "readme")
        res.expect("effective.%s.harness" % product, truth["effective"], hs["effective"], "harness-shape")
        # The README and harness-shape mirrors document min_version and
        # recommended_version as one value, so guard that invariant: a future
        # bump that diverges them in runtime-roots must not pass silently.
        res.expect(
            "product-floor.%s.min-eq-recommended" % product,
            truth["min"],
            truth["recommended"],
            "runtime-roots-recommended",
        )

    # nils-cli pin: nils-cli-pin.yaml is the source of truth.
    res.expect("nils-pin.readme", pin, readme["nils"], "readme")
    res.expect("nils-pin.surface-describe", pin, surface_describe(), "nils-cli-surface")
    res.expect("nils-pin.surface-prose", pin, surface_pinned_tag(), "nils-cli-surface-prose")
    for product in ("codex", "claude", "hermes"):
        res.expect(
            "nils-pin.harness-%s" % product,
            pin,
            harness_values(product)["pin"],
            "harness-shape",
        )
        for cli, floor in harness_required_cli_examples(product):
            res.add(
                (cli, floor) in manifest_cli_pairs,
                "required-cli-example.%s.%s" % (product, cli),
                "documented=>=%s manifest-pair=%s"
                % (floor, "present" if (cli, floor) in manifest_cli_pairs else "missing"),
            )
    return res


# --- advisory report ---------------------------------------------------------


def _probe(cmd):
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20, check=False
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def _semver_tuple(value):
    nums = re.findall(r"\d+", value or "")
    return tuple(int(n) for n in nums[:3]) if nums else None


def run_report() -> int:
    roots = runtime_roots_floor()
    pin = pinned_tag()

    print("version baseline — availability report (advisory)\n")
    header = "  %-10s %-12s %-12s %-12s %s" % (
        "component", "floor/pin", "installed", "latest", "verdict",
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for product in ("codex", "claude"):
        floor = roots[product]["min"]
        installed_raw = _probe([product, "--version"])
        installed = None
        if installed_raw:
            m = re.search(r"\d+\.\d+\.\d+", installed_raw)
            installed = m.group(0) if m else installed_raw
        latest = _probe(["npm", "view", NPM_PACKAGE[product], "version"])

        verdict = "—"
        ft, lt = _semver_tuple(floor), _semver_tuple(latest)
        it = _semver_tuple(installed)
        if ft and lt:
            verdict = "update available" if lt > ft else "current"
        if it and ft and it < ft:
            verdict = "HOST BELOW FLOOR"
        print("  %-10s %-12s %-12s %-12s %s" % (
            product, floor, installed or "?", latest or "?", verdict,
        ))

    nils_installed = _probe(["agent-runtime", "--version"])
    if nils_installed:
        m = re.search(r"v?\d+\.\d+\.\d+", nils_installed)
        nils_installed = m.group(0) if m else nils_installed
    print("  %-10s %-12s %-12s %-12s %s" % (
        "nils-cli", pin, nils_installed or "?", "(meta:nils-cli-bump)",
        "owned by nils-cli-bump",
    ))

    print("\nLatest lookups are best-effort (network). Consistency gate result:")
    res = run_check()
    _emit(res)
    return 0  # report is always advisory


# --- output ------------------------------------------------------------------


def _emit(res: Result):
    for ok, name, detail in res.checks:
        print("  %s %s %s" % ("ok  " if ok else "FAIL", name, detail))
    failed = res.failed
    print(
        "\nversion-baseline-audit: %d checks, %d ok, %d fail"
        % (len(res.checks), len(res.checks) - len(failed), len(failed))
    )
    if failed:
        print(
            "\nDrift detected. The source of truth is manifests/runtime-roots.yaml "
            "(product floor) and docs/source/nils-cli-pin.yaml (pin); update the "
            "mirrors to match, or use the project-version-baseline skill."
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "report"],
        help="check: deterministic consistency gate (default). "
        "report: advisory availability probe + gate.",
    )
    args = parser.parse_args(argv)

    if args.mode == "report":
        return run_report()

    res = run_check()
    _emit(res)
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
