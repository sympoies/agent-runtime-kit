#!/usr/bin/env python3
"""Focused contract tests for the split nils-cli version policy."""

from __future__ import annotations

import re
import json
import hashlib
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def load_workflow(relative: str) -> dict:
    result = subprocess.run(
        [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "puts JSON.generate(YAML.safe_load(File.read(ARGV.fetch(0)), aliases: true))",
            str(ROOT / relative),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def yaml_scalar(text: str, key: str) -> str:
    match = re.search(rf'^\s*{re.escape(key)}:\s*"?([^"#\s]+)"?', text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"missing YAML scalar: {key}")
    return match.group(1)


class NilsCliVersionPolicyTest(unittest.TestCase):
    def assert_gate_run_executes(
        self,
        run_block: str,
        replacements: dict[str, str],
        expected_probes: list[str],
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            helper = root / "with-nils-version.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "case \"$1\" in release:v*) ;; *) exit 90 ;; esac\n"
                "test \"$2\" = --\n"
                "printf '%s\\n' \"$1\" >>\"$HELPER_CALLS\"\n"
                "shift 2\n"
                "exec \"$@\"\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            for binary in ("agent-runtime", "plan-tooling"):
                probe = bin_dir / binary
                probe.write_text(
                    "#!/usr/bin/env bash\n"
                    f"printf '%s\\n' {binary} >>\"$VERSION_PROBES\"\n",
                    encoding="utf-8",
                )
                probe.chmod(0o755)
            downstream = root / "downstream.sh"
            downstream.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf 'reached\\n' >\"$DOWNSTREAM_PROOF\"\n",
                encoding="utf-8",
            )

            executable = run_block.replace(
                "scripts/dev/with-nils-version.sh", str(helper)
            ).replace("bash scripts/ci/all.sh", 'bash "$DOWNSTREAM_SCRIPT"')
            for source, replacement in replacements.items():
                executable = executable.replace(source, replacement)

            helper_calls = root / "helper-calls"
            version_probes = root / "version-probes"
            downstream_proof = root / "downstream-proof"
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}:{env['PATH']}",
                    "HELPER_CALLS": str(helper_calls),
                    "VERSION_PROBES": str(version_probes),
                    "DOWNSTREAM_SCRIPT": str(downstream),
                    "DOWNSTREAM_PROOF": str(downstream_proof),
                    "GITHUB_STEP_SUMMARY": str(root / "step-summary"),
                }
            )
            subprocess.run(
                ["bash", "-c", executable],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(len(helper_calls.read_text().splitlines()), 1)
            observed_probes = (
                version_probes.read_text().splitlines()
                if version_probes.exists()
                else []
            )
            self.assertEqual(observed_probes, expected_probes)
            self.assertEqual(downstream_proof.read_text(), "reached\n")

    def test_manifest_separates_minimum_from_validated(self) -> None:
        manifest = read("docs/source/nils-cli-pin.yaml")

        self.assertEqual(yaml_scalar(manifest, "schema_version"), "2")
        self.assertEqual(yaml_scalar(manifest, "minimum_supported_tag"), "v1.25.8")
        self.assertEqual(yaml_scalar(manifest, "validated_tag"), "v1.25.8")
        self.assertNotIn("pinned_tag:", manifest)
        self.assertEqual(
            yaml_scalar(manifest, "linux_amd64"),
            "8c2cb292383e1dcedac630f9d6f4dc542fbb64cb813a00d6464c784bdbfe49ad",
        )
        self.assertEqual(
            yaml_scalar(manifest, "linux_arm64"),
            "b1656e6435c347826965e4b315e3b3edb261d7fac06185d3a317e1e2b8251db5",
        )
        minimum_manifest = read("docs/source/nils-cli-minimum-digest.yaml")
        self.assertEqual(yaml_scalar(minimum_manifest, "schema_version"), "1")
        self.assertEqual(
            yaml_scalar(minimum_manifest, "minimum_supported_tag"), "v1.25.8"
        )
        self.assertEqual(
            yaml_scalar(minimum_manifest, "linux_amd64"),
            "8c2cb292383e1dcedac630f9d6f4dc542fbb64cb813a00d6464c784bdbfe49ad",
        )
        self.assertEqual(
            yaml_scalar(minimum_manifest, "linux_arm64"),
            "b1656e6435c347826965e4b315e3b3edb261d7fac06185d3a317e1e2b8251db5",
        )

    def test_blocking_ci_builds_deduplicated_minimum_validated_matrix(self) -> None:
        workflow_text = read(".github/workflows/ci.yml")
        workflow = load_workflow(".github/workflows/ci.yml")
        checkout_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        self.assertTrue(checkout_steps)
        for step in checkout_steps:
            self.assertIs(step.get("with", {}).get("persist-credentials"), False)
        policy = workflow["jobs"]["nils-cli-policy"]
        self.assertEqual(
            set(policy["outputs"]),
            {"matrix", "minimum_supported_tag", "validated_tag"},
        )
        gate = workflow["jobs"]["gate-stack"]
        self.assertIn("fromJSON", gate["strategy"]["matrix"])
        steps = gate["steps"]
        cache = next(step for step in steps if step.get("name") == "Cache nils-cli release archive")
        self.assertRegex(cache["uses"], r"^actions/cache@[0-9a-f]{40}$")
        self.assertIn(
            "nils-versions/${{ matrix.tag }}/*.tar.gz", cache["with"]["path"]
        )
        self.assertIn("${{ matrix.tag }}-${{ matrix.sha256 }}", cache["with"]["key"])
        run_step = next(
            step
            for step in steps
            if step.get("name") == "Print toolchain versions and run scripts/ci/all.sh"
        )
        self.assertEqual(run_step["env"]["NILS_RELEASE_SHA256"], "${{ matrix.sha256 }}")
        self.assertEqual(run_step["env"]["HOOKS_TEST_JOBS"], "1")
        self.assertNotIn("pinned_tag", workflow_text)
        self.assert_gate_run_executes(
            run_step["run"],
            {
                "${{ matrix.lane }}": "validated",
                "${{ matrix.roles }}": "validated",
                "${{ matrix.tag }}": "v1.25.8",
            },
            ["agent-runtime", "plan-tooling"],
        )

        gate_stack = read("scripts/ci/all.sh")
        self.assertLess(
            gate_stack.index("agent-runtime doctor --class version-alignment"),
            gate_stack.index("plan-tooling validate --format text --explain"),
        )

    def test_matrix_builder_covers_equal_and_distinct_roles(self) -> None:
        script = ROOT / "scripts/ci/nils-cli-policy-matrix.py"

        cases = (
            (
                "v1.25.0",
                "v1.25.0",
                [("minimum+validated", "v1.25.0", "minimum,validated", "a" * 64)],
            ),
            (
                "v1.25.0",
                "v1.26.0",
                [
                    ("minimum", "v1.25.0", "minimum", "a" * 64),
                    ("validated", "v1.26.0", "validated", "b" * 64),
                ],
            ),
        )
        for minimum, validated, expected in cases:
            with self.subTest(minimum=minimum, validated=validated), tempfile.TemporaryDirectory() as tmp:
                manifest = Path(tmp) / "policy.yaml"
                minimum_manifest = Path(tmp) / "minimum-digest.yaml"
                validated_digest = "a" * 64 if minimum == validated else "b" * 64
                manifest.write_text(
                    "schema_version: 2\nnils_cli:\n"
                    f'  minimum_supported_tag: "{minimum}"\n'
                    f'  validated_tag: "{validated}"\n'
                    "  release_sha256:\n"
                    f'    linux_amd64: "{validated_digest}"\n'
                    f'    linux_arm64: "{"d" * 64}"\n',
                    encoding="utf-8",
                )
                minimum_manifest.write_text(
                    "schema_version: 1\n"
                    f'minimum_supported_tag: "{minimum}"\n'
                    "release_sha256:\n"
                    f'  linux_amd64: "{"a" * 64}"\n'
                    f'  linux_arm64: "{"c" * 64}"\n',
                    encoding="utf-8",
                )
                output = subprocess.run(
                    [
                        "python3",
                        str(script),
                        "--manifest",
                        str(manifest),
                        "--minimum-digest-manifest",
                        str(minimum_manifest),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                observed = [
                    (item["lane"], item["tag"], item["roles"], item["sha256"])
                    for item in json.loads(output)["include"]
                ]
                self.assertEqual(observed, expected)

    def test_candidate_version_must_be_stable_and_not_older_than_validated(self) -> None:
        script = ROOT / "scripts/ci/nils-cli-policy-matrix.py"
        for candidate in ("v1.25.8", "v1.26.0"):
            with self.subTest(candidate=candidate):
                subprocess.run(
                    ["python3", str(script), "--assert-candidate-at-least-validated", candidate],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
        for candidate in (
            "v1.24.9",
            "v1.26.0-rc.1",
            "v01.26.0",
            "v1２.26.0",
            "v18446744073709551616.0.0",
        ):
            with self.subTest(candidate=candidate):
                result = subprocess.run(
                    ["python3", str(script), "--assert-candidate-at-least-validated", candidate],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)

        selected = subprocess.run(
            ["python3", str(script), "--select-newest-stable"],
            cwd=ROOT,
            input=(
                "v1.25.0\n"
                "v01.99.0\n"
                "v1２.99.0\n"
                "v18446744073709551616.0.0\n"
                "v1.27.0-rc.1\n"
                "v1.26.0\n"
            ),
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(selected.stdout.strip(), "v1.26.0")

    def test_matrix_builder_rejects_inverted_or_out_of_range_policy(self) -> None:
        script = ROOT / "scripts/ci/nils-cli-policy-matrix.py"
        invalid_ranges = (
            ("v2.0.0", "v1.0.0"),
            ("v18446744073709551616.0.0", "v2.0.0"),
            ("v1.0.0", "v18446744073709551616.0.0"),
        )

        for minimum, validated in invalid_ranges:
            with self.subTest(minimum=minimum, validated=validated), tempfile.TemporaryDirectory() as tmp:
                manifest = Path(tmp) / "policy.yaml"
                minimum_manifest = Path(tmp) / "minimum-digest.yaml"
                manifest.write_text(
                    "schema_version: 2\nnils_cli:\n"
                    f'  minimum_supported_tag: "{minimum}"\n'
                    f'  validated_tag: "{validated}"\n'
                    "  release_sha256:\n"
                    f'    linux_amd64: "{"b" * 64}"\n'
                    f'    linux_arm64: "{"d" * 64}"\n',
                    encoding="utf-8",
                )
                minimum_manifest.write_text(
                    "schema_version: 1\n"
                    f'minimum_supported_tag: "{minimum}"\n'
                    "release_sha256:\n"
                    f'  linux_amd64: "{"a" * 64}"\n'
                    f'  linux_arm64: "{"c" * 64}"\n',
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [
                        "python3",
                        str(script),
                        "--manifest",
                        str(manifest),
                        "--minimum-digest-manifest",
                        str(minimum_manifest),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)

    def test_latest_canary_is_scheduled_manual_and_not_a_pr_gate(self) -> None:
        workflow_text = read(".github/workflows/nils-cli-latest-canary.yml")
        workflow = load_workflow(".github/workflows/nils-cli-latest-canary.yml")

        for marker in (
            "schedule:",
            "workflow_dispatch:",
            "gh api --paginate",
            ".prerelease",
            "--select-newest-stable",
            "--assert-candidate-at-least-validated",
            "sympoies/nils-cli",
            "if: ${{ always() }}",
            "Remediation",
            "job.status",
        ):
            self.assertIn(marker, workflow_text)
        self.assertNotIn("pull_request:", workflow_text)
        steps = workflow["jobs"]["latest-stable"]["steps"]
        checkout_steps = [
            step
            for step in steps
            if str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        self.assertTrue(checkout_steps)
        for step in checkout_steps:
            self.assertIs(step.get("with", {}).get("persist-credentials"), False)
        cache = next(step for step in steps if step.get("name") == "Cache nils-cli release archive")
        self.assertRegex(cache["uses"], r"^actions/cache@[0-9a-f]{40}$")
        self.assertIn(
            "nils-versions/${{ steps.latest.outputs.tag }}/*.tar.gz",
            cache["with"]["path"],
        )
        self.assertIn(
            "${{ steps.latest.outputs.tag }}-${{ steps.latest.outputs.sha256 }}",
            cache["with"]["key"],
        )
        run_step = next(
            step for step in steps if step.get("name") == "Run full downstream behavior gate"
        )
        self.assertEqual(
            run_step["env"]["NILS_RELEASE_SHA256"],
            "${{ steps.latest.outputs.sha256 }}",
        )
        self.assertEqual(run_step["env"]["HOOKS_TEST_JOBS"], "1")
        self.assert_gate_run_executes(
            run_step["run"],
            {"${{ steps.latest.outputs.tag }}": "v1.26.0"},
            [],
        )

    def test_ahead_runtime_smoke_reaches_and_can_fail_a_real_downstream_gate(self) -> None:
        smoke = read("tests/runtime-smoke/cases/meta/run.sh")
        self.assertIn("incompatible-newer-surface", smoke)
        self.assertIn("run_downstream_nils_contract_probe", smoke)
        self.assertIn("downstream gate rejected incompatible newer surface", smoke)
        self.assertNotIn("printf 'downstream sentinel reached\\n' >>\"$ahead\"", smoke)

    def test_release_helper_verifies_archive_reextracts_cache_and_drops_tokens(self) -> None:
        helper = ROOT / "scripts/dev/with-nils-version.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "payload"
            payload.mkdir()
            agent_runtime = payload / "agent-runtime"
            agent_runtime.write_text(
                "#!/usr/bin/env bash\n"
                "if [ \"${1:-}\" = marker ]; then echo GOOD; else echo 'agent-runtime 1.25.0'; fi\n",
                encoding="utf-8",
            )
            agent_runtime.chmod(0o755)
            archive = root / "nils-cli-v1.25.0-x86_64-unknown-linux-gnu.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(agent_runtime, arcname="bin/agent-runtime")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()

            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake_gh = fake_bin / "gh"
            fake_gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf called > \"$GH_CALLED\"\n"
                "if [ \"$1 $2\" = 'release view' ]; then\n"
                "  printf '%s.sha256\\n%s\\n' \"$(basename \"$FAKE_ARCHIVE\")\" \"$(basename \"$FAKE_ARCHIVE\")\"\n"
                "  exit 0\n"
                "fi\n"
                "if [ \"$1 $2\" = 'release download' ]; then\n"
                "  while [ $# -gt 0 ]; do\n"
                "    if [ \"$1\" = --dir ]; then shift; cp \"$FAKE_ARCHIVE\" \"$1/\"; exit 0; fi\n"
                "    shift\n"
                "  done\n"
                "fi\n"
                "exit 2\n",
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}:{env['PATH']}",
                    "XDG_STATE_HOME": str(root / "state"),
                    "FAKE_ARCHIVE": str(archive),
                    "GH_CALLED": str(root / "gh-called"),
                    "NILS_RELEASE_SHA256": digest,
                    "GH_TOKEN": "must-not-leak",
                    "GITHUB_TOKEN": "must-not-leak",
                }
            )
            command = [
                str(helper),
                "release:v1.25.0",
                "--",
                "bash",
                "-c",
                'test -z "${GH_TOKEN+x}" && test -z "${GITHUB_TOKEN+x}" && '
                'test "$(agent-runtime marker)" = GOOD',
            ]

            cache_dir = (
                root / "state" / "agent-runtime-kit" / "out" /
                "nils-versions" / "v1.25.0"
            )
            cache_dir.mkdir(parents=True)
            cache_only_symlink = cache_dir / "only.tgz"
            cache_only_symlink.symlink_to(archive)
            nonregular_command = root / "nonregular-command-ran"
            nonregular_env = env.copy()
            nonregular_env["RAN_PATH"] = str(nonregular_command)
            rejected_nonregular = subprocess.run(
                [
                    str(helper),
                    "release:v1.25.0",
                    "--",
                    "bash",
                    "-c",
                    'printf ran > "$RAN_PATH"',
                ],
                env=nonregular_env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(rejected_nonregular.returncode, 0)
            self.assertFalse((root / "gh-called").exists())
            self.assertFalse(nonregular_command.exists())
            cache_only_symlink.unlink()

            subprocess.run(command, env=env, check=True, capture_output=True, text=True)

            bad_payload = root / "bad-payload"
            bad_payload.mkdir()
            bad_agent_runtime = bad_payload / "agent-runtime"
            bad_agent_runtime.write_text(
                "#!/usr/bin/env bash\necho BAD\n",
                encoding="utf-8",
            )
            bad_agent_runtime.chmod(0o755)
            bad_archive = root / "unverified.tgz"
            with tarfile.open(bad_archive, "w:gz") as bundle:
                bundle.add(bad_agent_runtime, arcname="bin/agent-runtime")
            cached_archive = next((root / "state").rglob("*.tar.gz"))
            extra_archive = cached_archive.parent / "extra.tgz"
            extra_archive.symlink_to(bad_archive)
            ran_path = root / "unverified-command-ran"
            bypass_env = env.copy()
            bypass_env["RAN_PATH"] = str(ran_path)
            rejected_extra = subprocess.run(
                [
                    str(helper),
                    "release:v1.25.0",
                    "--",
                    "bash",
                    "-c",
                    'agent-runtime marker > "$RAN_PATH"',
                ],
                env=bypass_env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(rejected_extra.returncode, 0)
            self.assertFalse(ran_path.exists())
            extra_archive.unlink()

            cached_binary = next((root / "state").rglob("extract/bin/agent-runtime"))
            cached_binary.write_text("#!/usr/bin/env bash\necho BAD\n", encoding="utf-8")
            cached_binary.chmod(0o755)
            subprocess.run(command, env=env, check=True, capture_output=True, text=True)

            env["NILS_RELEASE_SHA256"] = "0" * 64
            rejected = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)

            for invalid_tag in (
                "../../outside",
                "v01.26.0",
                "v1.26.0-rc.1",
                "v1２.26.0",
                "v18446744073709551616.0.0",
            ):
                with self.subTest(invalid_tag=invalid_tag):
                    rejected_tag = subprocess.run(
                        [str(helper), f"release:{invalid_tag}", "--", "true"],
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(rejected_tag.returncode, 0)
                    self.assertIn("release tag must be stable", rejected_tag.stderr)

    def test_source_helper_hardens_self_trusting_binaries(self) -> None:
        helper = ROOT / "scripts/dev/with-nils-version.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "nils-cli"
            (repo / ".git").mkdir(parents=True)
            worktree = Path(f"{repo}-worktrees") / "wnv-fixture-ref"
            worktree.mkdir(parents=True)
            (worktree / ".git").write_text("gitdir: fixture\n", encoding="utf-8")
            bin_dir = worktree / "target" / "debug"
            bin_dir.mkdir(parents=True)
            for binary in ("agent-runtime", "git-cli"):
                path = bin_dir / binary
                path.write_text(
                    "#!/usr/bin/env bash\n"
                    "if [ \"${1:-}\" = --version ]; then echo fixture; fi\n",
                    encoding="utf-8",
                )
                path.chmod(0o775)

            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            cargo = fake_bin / "cargo"
            cargo.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            cargo.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "NILS_CLI_REPO": str(repo),
                    "PATH": f"{fake_bin}:{env['PATH']}",
                }
            )

            subprocess.run(
                [str(helper), "src:fixture-ref", "--", "true"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            for binary in ("agent-runtime", "git-cli"):
                with self.subTest(binary=binary):
                    self.assertEqual((bin_dir / binary).stat().st_mode & 0o022, 0)

    def test_packaging_is_bound_to_validated_tag_and_release_digests(self) -> None:
        publish = read(".github/workflows/publish-image.yml")
        build = read("docker/build.sh")
        dockerfile = read("docker/Dockerfile")

        for surface in (publish, build):
            self.assertIn("validated_tag", surface)
            self.assertNotIn("pinned_tag", surface)
            self.assertIn("linux_amd64", surface)
            self.assertIn("linux_arm64", surface)
        self.assertIn("ARG NILS_CLI_VERSION=v1.25.8", dockerfile)

    def test_audits_and_maintenance_skill_understand_both_roles(self) -> None:
        bump_skill = read("core/skills/meta/nils-cli-bump/SKILL.md.tera")
        surfaces = (
            read("scripts/ci/security-hardening-audit.py"),
            read("scripts/ci/version-baseline-audit.py"),
            bump_skill,
            read(".agents/skills/project-version-baseline/SKILL.md"),
        )

        for surface in surfaces:
            self.assertIn("minimum_supported_tag", surface)
            self.assertIn("validated_tag", surface)
        self.assertNotIn(
            "Codex/Claude/Hermes",
            bump_skill,
        )
        self.assertIn("target-platform-archive-sha256", bump_skill)
        self.assertNotIn("target-linux-amd64-sha256", bump_skill)
        self.assertIn(
            "remote-canary bootstrap exception",
            read("docs/source/nils-cli-version-workflows.md"),
        )
        self.assertNotIn(
            "plugins/meta/skills/nils-cli-bump/SKILL.md",
            read("scripts/ci/product-leak-allow.yaml"),
        )

    def test_runtime_smoke_tracks_the_active_exact_ci_lane(self) -> None:
        smoke = read("tests/runtime-smoke/cases/evidence/run.sh")
        hooks = read("tests/hooks/test_shared_hooks.py")

        self.assertIn("matches_agent_docs_version", smoke)
        self.assertIn("agent-runtime --version", smoke)
        self.assertNotIn("matches_pinned_agent_docs_version", smoke)
        self.assertNotIn("agent-docs 1.24.3", smoke)
        self.assertIn('[agent_runtime, "--version"]', hooks)
        self.assertNotIn('["git-cli", "1.24.3"]', hooks)

    def test_repository_ignores_python_bytecode_caches(self) -> None:
        self.assertIn("__pycache__/", read(".gitignore").splitlines())


if __name__ == "__main__":
    unittest.main()
