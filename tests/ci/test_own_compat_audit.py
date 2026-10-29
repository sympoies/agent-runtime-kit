#!/usr/bin/env python3
"""Repository retention audit acceptance: admission, baseline and release fences."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts/ci/own-compat-audit.sh"


class OwnCompatAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.write("scripts/example.py", "LEGACY_FORMAT = 1\n")
        self.baseline = self.root / "baseline.toml"
        self.baseline.write_text("schema = 1\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.track()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def track(self):
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)

    def run_audit(self, *args):
        self.track()
        return subprocess.run(
            ["bash", str(AUDIT), "--root", str(self.root), "--baseline", str(self.baseline),
             "--today", "2026-10-29", *args], capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=20,
        )

    def allow(self, sequence=None, **updates):
        row = dict(path="scripts/example.py", match="LEGACY_FORMAT", count=1,
                   kind="scheduled", reason="Remove the superseded format reader.",
                   issue="https://github.com/sympoies/agent-runtime-kit/issues/328",
                   expires="2026-12-31")
        row.update(updates)
        header = "schema = 1\n"
        if sequence:
            header += "release_sequence = " + json.dumps(sequence) + "\n"
        self.baseline.write_text(header + "[[allow]]\n" + "\n".join(
            f"{key} = {json.dumps(value)}" for key, value in row.items()) + "\n")

    def test_gate_rejects_new_retention_identifier(self):
        # Exercise the compatibility admission commands the real gate declares.
        # Before K1 there are none: the injected declaration is silently admitted.
        commands = re.findall(r"^bash scripts/ci/own-compat-audit\.sh(.*)$",
                              (ROOT / "scripts/ci/all.sh").read_text(), re.M)
        statuses = [self.run_audit().returncode for _ in commands]
        self.assertIn(1, statuses, "canonical admission accepted LEGACY_FORMAT = 1")

    def test_unlisted_constructs(self):
        cases = ["legacy_reader = load()", '#[serde(alias = "prior")]',
                 '#[command(visible_alias = "prior")]',
                 'parser.add_argument("--prior", help=argparse.SUPPRESS)',
                 'if schema_version in (1, 2): pass',
                 'if payload.get("schema_version") in ("kit.v1", "kit.v2"): pass',
                 'if payload["schema_version"] in ("kit.v1", "kit.v2"): pass',
                 '#[serde(\n  alias = "prior"\n)]',
                 'FORMAT_ALIASES = {"prior": "current"}',
                 'legacyReader = load()', 'old_schema = load()',
                 'legacy_reader = load() # is rejected later',
                 '# Retain backward compatibility for the prior format.']
        for source in cases:
            with self.subTest(source=source):
                self.write("scripts/example.py", source + "\n")
                result = self.run_audit()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("unlisted", result.stdout)

    def test_exact_baseline_accepts_and_rejects_new_occurrence(self):
        self.allow()
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write("scripts/example.py", "LEGACY_FORMAT = 1\nuse(LEGACY_FORMAT)\n")
        result = self.run_audit()
        self.assertEqual(result.returncode, 1)
        self.assertIn("count", result.stdout)

    def test_baseline_cannot_grow_or_extend_scheduled_debt(self):
        self.allow()
        self.track()
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgSign=false",
                        "commit", "-qm", "Fixture baseline"], check=True)
        subprocess.run(["git", "-C", str(self.root), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
        self.write("scripts/example.py", "LEGACY_FORMAT = 1\nuse(LEGACY_FORMAT)\n")
        self.allow(count=2)
        result = self.run_audit()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("ratchet", result.stdout)
        # Canonical baseline ownership/deadlines cannot be silently extended.
        self.write("scripts/example.py", "LEGACY_FORMAT = 1\n")
        self.write("scripts/ci/own-compat-allowlist.toml", self.baseline.read_text())
        self.track()
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgSign=false",
                        "commit", "-qm", "Fixture canonical baseline"], check=True)
        subprocess.run(["git", "-C", str(self.root), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
        self.allow(expires="2027-01-01")
        result = self.run_audit()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("deadline", result.stdout)

    def test_stale_row(self):
        self.allow()
        self.write("scripts/example.py", "CURRENT_FORMAT = 2\n")
        result = self.run_audit()
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale", result.stdout)

    def test_malformed_rows(self):
        for update in ({"reason": ""}, {"issue": "https://example.invalid/1"},
                       {"expires": "someday"}, {"kind": "forever"},
                       {"path": "scripts/*"}, {"count": 0}, {"extra": True}):
            with self.subTest(update=update):
                self.allow(**update)
                result = self.run_audit()
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_calendar_expiry_is_inclusive(self):
        self.allow(expires="2026-10-29")
        result = self.run_audit()
        self.assertEqual(result.returncode, 1)
        self.assertIn("expired", result.stdout)

    def test_external_support_requires_named_version(self):
        self.allow(kind="external", external="Bash 3.2")
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for external in ("", "provider"):
            self.allow(kind="external", external=external)
            self.assertEqual(self.run_audit().returncode, 2)

    def test_rollback_window_requires_concrete_cross_host_release_fence(self):
        self.allow(kind="rollback-window")
        self.assertEqual(self.run_audit().returncode, 2)
        pair = dict(previous_release="2026.10.27", current_release="2026.10.28",
                    remove_before_release="2026.10.29",
                    transport="Cross-host wire/state: sender and receiver exchange schema envelopes.")
        self.allow(kind="rollback-window", sequence=["2026.10.27", "2026.10.28", "2026.10.29"], **pair)
        result = self.run_audit("--release", "2026.10.28")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_audit("--release", "2026.10.29")
        self.assertEqual(result.returncode, 1)
        self.assertIn("release-expired", result.stdout)
        self.allow(kind="rollback-window", sequence=["2026.10.27", "2026.10.28", "2026.10.29"], **{**pair, "transport": "Local restore snapshot"})
        self.assertEqual(self.run_audit().returncode, 2)

    def test_generic_negative_and_history_non_hits(self):
        self.write("scripts/example.py", '''fallback = default_value
alias = current_name
migrate(data)
# Never add backward compatibility for retired formats.
assert not accepts("legacy_schema")
raise ValueError("legacy_schema is rejected")
DEFAULT_TIMEOUT = 30
''')
        self.write("docs/source/devlog/2026-10.md", "LEGACY_HISTORY = 1\n")
        self.write("manifests/retired-skill-ids.json", '{"legacy_id": "retired"}\n')
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_default_classification(self):
        self.write("scripts/example.py", "DEFAULT_PROFILE = generic_profile\n")
        self.allow(match="DEFAULT_PROFILE", kind="current-default",
                   reason="Current generic default; no retired form is accepted.")
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.allow(kind="current-default")
        self.write("scripts/example.py", "LEGACY_FORMAT = 1\n")
        self.assertEqual(self.run_audit().returncode, 2)

    def test_release_fence_blocks_before_publication(self):
        # Fixture identity/signing options apply only to this disposable Git repo.
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgSign=false",
                        "commit", "--allow-empty", "-qm", "Fixture baseline"], check=True)
        self.write("scripts/release.sh", (ROOT / "scripts/release.sh").read_text())
        self.write("scripts/ci/own-compat-audit.sh",
                   '#!/bin/sh\nprintf "%s\\n" "$*" > "$AUDIT_PROBE"\nexit 73\n')
        self.write("bin/gh", '#!/bin/sh\nif [ "$1" = repo ]; then echo fixture/repository; exit 0; fi\n'
                            'if [ "$2" = view ]; then exit 1; fi\ntouch "$PUBLICATION_PROBE"\n')
        (self.root / "bin/gh").chmod(0o755)
        env = {**os.environ, "PATH": str(self.root / "bin") + os.pathsep + os.environ["PATH"],
               "AUDIT_PROBE": str(self.root / "audit-probe"),
               "PUBLICATION_PROBE": str(self.root / "publication-probe")}
        for mode in ("--dry-run", "--execute"):
            with self.subTest(mode=mode):
                result = subprocess.run(
                    ["bash", "scripts/release.sh", mode, "--version", "2026.10.29",
                     "--skip-main-check", "--skip-clean-check", "--skip-public-verify", "--no-wait"],
                    cwd=self.root, env=env, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0,
                                    "release proceeds without consulting the retirement fence")
                self.assertTrue((self.root / "audit-probe").exists(), result.stdout + result.stderr)
                self.assertEqual((self.root / "audit-probe").read_text().strip(), "--release 2026.10.29")
                self.assertFalse((self.root / "publication-probe").exists())

    def test_image_workflow_checks_actual_tag_before_build(self):
        source = (ROOT / ".github/workflows/publish-image.yml").read_text()
        guard = re.search(r"- name: Audit compatibility release fences\n(.*?)(?=\n      - name:)", source, re.S)
        self.assertIsNotNone(guard, "published-release image path has no retirement guard")
        self.assertLess(guard.start(), source.index("- name: Build amd64"))
        self.assertIn("${{ github.event.release.tag_name }}", guard.group(1))
        command = re.search(r"^        run: (.+)$", guard.group(1), re.M).group(1)
        self.write("scripts/ci/own-compat-audit.sh",
                   '#!/bin/sh\ntest "$1 $2" = "--release 2026.10.29" || exit 99\nexit 73\n')
        result = subprocess.run(["bash", "-c", command], cwd=self.root,
                                env={**os.environ, "KIT_RELEASE_TAG": "v2026.10.29"},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)

    def test_owner_preference_stays_repo_only(self):
        sentinel = "Repository current-contract rule"
        self.assertIn(sentinel, (ROOT / "DEVELOPMENT.md").read_text())
        paths = [ROOT / "AGENT_HOME.md"]
        for directory in ("core", "targets", "build"):
            paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file() and not p.is_symlink())
        for path in paths:
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            self.assertNotIn(sentinel, text, str(path.relative_to(ROOT)))
            normalized = " ".join(text.split())
            for directive in ("Do not introduce old-form aliases, fallback readers, dual writes",
                              "Only actual cross-host wire/state spanning two named adjacent releases"):
                self.assertNotIn(directive, normalized, str(path.relative_to(ROOT)))
            self.assertNotIn("maintain only the current version", text.lower(), str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
