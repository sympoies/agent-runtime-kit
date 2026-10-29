#!/usr/bin/env python3
"""Installed home policy must outlive disposable build output, and its loss must be detectable.

Drives the real sync owner against a disposable source checkout and live home:
ordinary wiring, removal of only the rendered `build/` output, then the owner's
read-only `--check-home-policy` probe. A stub `agent-runtime` stands in for the
renderer; every path, home, and state directory is fixture-owned.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYNC = ROOT / "scripts/sync-runtime-surfaces.sh"
PRODUCTS = ("codex", "claude")

RENDER_STUB = """#!/usr/bin/env bash
set -euo pipefail
root=""; product="neutral"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-root) root="$2"; shift 2 ;;
    --product) product="$2"; shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$root/build/$product"
printf '# rendered %s home policy\\n' "$product" >"$root/build/$product/AGENT_HOME.md"
"""

BREW_STUB = """#!/usr/bin/env bash
case "${1:-}" in
  --prefix) printf '/opt/homebrew\n' ;;
  list) exit 1 ;;
  *) printf 'stub brew %s\n' "$*" ;;
esac
"""

SETUP_RENDER_STUB = """#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-}"; shift || true
root=""; product=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-root) root="$2"; shift 2 ;;
    --product) product="$2"; shift 2 ;;
    *) shift ;;
  esac
done
case "$cmd" in
  render)
    name="${product:-neutral}"
    mkdir -p "$root/build/$name"
    printf '# rendered %s home policy\n' "$name" >"$root/build/$name/AGENT_HOME.md"
    ;;
  install | prune-stale | doctor) mkdir -p "$root/build/$product" ;;
  *) exit 64 ;;
esac
"""

# Stands in for the sync owner's external operations only (plugin and hook activation);
# home-policy wiring is the real owner function from scripts/sync-runtime-surfaces.sh.
SYNC_WRAPPER = """#!/usr/bin/env bash
set -euo pipefail
export SYNC_RUNTIME_SURFACES_LIB=1
. "$REAL_SYNC"
parse_args "$@"
require_runtime_python
resolve_source_root
render_home_prompt_product "$PRODUCT"
ensure_home_prompt "$PRODUCT"
"""


class HomePolicyLifetimeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.source = base / "source"
        self.home = base / "home"
        self.bin = base / "bin"
        for path in (self.source / "scripts", self.source / "manifests", self.home / ".claude",
                     self.home / ".codex", self.bin):
            path.mkdir(parents=True)
        (self.source / "AGENT_HOME.md").write_text("# raw policy\n")
        (self.source / "manifests/skills.yaml").write_text("skills: []\n")
        (self.source / "scripts/sync-runtime-surfaces.sh").write_text("#!/usr/bin/env bash\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgSign=false", "commit", "-qm", "fixture identity")
        stub = self.bin / "agent-runtime"
        stub.write_text(RENDER_STUB)
        stub.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.home), "CODEX_HOME": str(self.home / ".codex"),
                    "XDG_STATE_HOME": str(self.home / "state"),
                    "PATH": "%s:%s" % (self.bin, os.environ["PATH"])}
        for name in ("CLAUDE_KIT_STATE_HOME", "CODEX_AGENT_STATE_HOME", "AGENT_RUNTIME_PYTHON"):
            self.env.pop(name, None)
        self.links = {"codex": self.home / ".codex/AGENTS.md", "claude": self.home / ".claude/CLAUDE.md"}
        self.store = {p: self.home / "state/agent-runtime-kit" / p / "home-policy/AGENT_HOME.md"
                      for p in PRODUCTS}

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.source), *args], check=True,
                              stdout=subprocess.PIPE).stdout.decode().strip()

    def owner(self, body):
        """Run owner functions from the real sync script as a library."""
        script = 'SYNC_RUNTIME_SURFACES_LIB=1 . "$SYNC"\nSOURCE_ROOT="$SRC"; APPLY=1\n' + body
        return subprocess.run(["bash", "-c", script], env={**self.env, "SYNC": str(SYNC), "SRC": str(self.source)},
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def wire(self, *products):
        body = "".join("render_home_prompt_product %s\nensure_home_prompt %s\n" % (p, p) for p in products)
        return self.owner(body)

    def probe(self, product="both"):
        proc = subprocess.run(["bash", str(SYNC), "--source-root", str(self.source), "--product", product,
                               "--check-home-policy"], env=self.env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
        return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else None

    def states(self):
        _, report = self.probe()
        return {item["product"]: item["state"] for item in report["products"]}

    def test_installed_policy_survives_build_cleanup(self):
        proc = self.wire(*PRODUCTS)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        shutil.rmtree(self.source / "build")  # only the fixture's rebuildable render output
        for product in PRODUCTS:
            with self.subTest(product=product):
                self.assertIn("rendered %s home policy" % product, self.links[product].read_text())
        code, report = self.probe()
        self.assertEqual(code, 0, report)
        self.assertTrue(report["ok"])
        self.assertEqual({item["product"] for item in report["products"]}, set(PRODUCTS))
        for item in report["products"]:
            self.assertEqual(item["state"], "healthy")
            self.assertEqual(item["source"]["root"], str(self.source))
            self.assertEqual(item["source"]["installed"]["source_commit"], self.git("rev-parse", "HEAD"))

    def test_probe_distinguishes_each_loss_from_healthy(self):
        foreign = self.home / "foreign.md"
        foreign.write_text("someone else's policy\n")

        def lose(kind, product):
            link, store = self.links[product], self.store[product]
            if kind == "absent":
                link.unlink()
            elif kind == "dangling":
                store.unlink()
            elif kind == "empty":
                store.write_text("")
            elif kind == "unreadable":
                store.chmod(0)
            elif kind == "foreign":
                link.unlink()
                link.symlink_to(foreign)

        for kind in ("absent", "dangling", "empty", "unreadable", "foreign"):
            with self.subTest(kind=kind):
                if kind == "unreadable" and os.geteuid() == 0:
                    self.skipTest("root bypasses file modes")
                self.assertEqual(self.wire(*PRODUCTS).returncode, 0)
                lose(kind, "codex")
                code, report = self.probe()
                self.assertEqual(code, 1)
                self.assertFalse(report["ok"])
                by_product = {item["product"]: item for item in report["products"]}
                self.assertEqual(by_product["claude"]["state"], "healthy")
                broken = by_product["codex"]
                self.assertEqual(broken["state"], kind)
                self.assertFalse(broken["healthy"])
                self.assertIn("--product codex", broken["remediation"])
                self.assertIn("sync-runtime-surfaces.sh", broken["remediation"])
                if self.store["codex"].exists():
                    self.store["codex"].chmod(0o644)
                for link in self.links.values():
                    if link.is_symlink() or link.exists():
                        link.unlink()

    def test_sync_never_adopts_foreign_links_and_wires_after_removal(self):
        # The former layout (a link into build output) is never re-adopted by steady-state
        # sync, even after sync re-renders that file; it is reported and the operator removes
        # it once. Links to unrelated paths are treated the same way.
        former = self.source / "build/codex/AGENT_HOME.md"
        self.links["codex"].symlink_to(former)
        self.assertEqual(self.states()["codex"], "dangling")
        refused = self.wire("codex")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(os.readlink(self.links["codex"]), str(former))
        self.assertEqual(self.states()["codex"], "foreign")
        _, report = self.probe("codex")
        self.assertIn("manually", report["products"][0]["remediation"])
        user_file = self.links["claude"]
        user_file.write_text("my own claude rules\n")

        self.links["codex"].unlink()
        self.assertEqual(self.wire("codex").returncode, 0)
        self.assertEqual(self.states()["codex"], "healthy")
        self.assertEqual(os.path.realpath(self.links["codex"]), str(self.store["codex"].resolve()))

        refused = self.wire("claude")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(user_file.read_text(), "my own claude rules\n")
        self.assertFalse(user_file.is_symlink())
        self.assertEqual(self.states()["claude"], "foreign")

    def test_apply_verification_gate_fails_when_a_link_loses_its_policy(self):
        self.assertEqual(self.wire(*PRODUCTS).returncode, 0)
        shutil.rmtree(self.source / "build")
        self.assertEqual(self.owner("PRODUCT=both; verify_home_policy\n").returncode, 0)
        self.store["claude"].unlink()
        proc = self.owner("PRODUCT=both; verify_home_policy\n")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("claude", proc.stdout)

    def run_setup(self, home):
        """Run the real scripts/setup.sh against a fixture home whose sync is the real owner wiring."""
        checkout = home / ".config/agent-runtime-kit"
        (checkout / "scripts").mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(checkout), "init", "-q"], check=True)
        (checkout / "AGENT_HOME.md").write_text("# raw policy\n")
        wrapper = checkout / "scripts/sync-runtime-surfaces.sh"
        wrapper.write_text(SYNC_WRAPPER)
        wrapper.chmod(0o755)
        for name, body in (("brew", BREW_STUB), ("agent-runtime", SETUP_RENDER_STUB)):
            stub = self.bin / name
            stub.write_text(body)
            stub.chmod(0o755)
        env = {**self.env, "HOME": str(home), "CODEX_HOME": str(home / ".codex"), "REAL_SYNC": str(SYNC),
               "XDG_STATE_HOME": str(home / "state")}
        proc = subprocess.run(["bash", str(ROOT / "scripts/setup.sh"), "--profile", "core",
                               "--skip-homebrew-install", "--skip-cli-tools"], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return checkout, env, proc

    def test_fresh_setup_hands_home_wiring_to_sync_and_ends_healthy(self):
        home = Path(self._tmp.name).resolve() / "setup-home"
        (home / ".codex").mkdir(parents=True)
        (home / ".claude").mkdir(parents=True)
        checkout, env, proc = self.run_setup(home)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        report = json.loads(subprocess.run(
            ["bash", str(SYNC), "--source-root", str(checkout), "--product", "both", "--check-home-policy"],
            env=env, stdout=subprocess.PIPE, text=True, check=True).stdout)
        self.assertTrue(report["ok"], report)
        for link in (home / ".codex/AGENTS.md", home / ".claude/CLAUDE.md"):
            self.assertTrue(link.read_text().strip())
            self.assertNotIn("/build/", os.readlink(link))

    def test_setup_still_refuses_and_preserves_a_users_own_policy_file(self):
        home = Path(self._tmp.name).resolve() / "setup-collision-home"
        (home / ".codex").mkdir(parents=True)
        (home / ".claude").mkdir(parents=True)
        (home / ".codex/AGENTS.md").write_text("manual codex policy\n")
        _, _, proc = self.run_setup(home)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual((home / ".codex/AGENTS.md").read_text(), "manual codex policy\n")
        self.assertFalse((home / ".codex/AGENTS.md").is_symlink())


if __name__ == "__main__":
    unittest.main()
