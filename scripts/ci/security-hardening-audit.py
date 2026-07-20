#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
USES_RE = re.compile(r"uses:\s*([^@\s#]+)@([^\s#]+)")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_workflow_action_pins(errors: list[str]) -> None:
    workflow_dir = ROOT / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.yml")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES_RE.search(line)
            if not match:
                continue
            action, ref = match.groups()
            if not HEX40_RE.fullmatch(ref):
                fail(
                    errors,
                    f"{path.relative_to(ROOT)}:{line_no}: action {action}@{ref} is not pinned to a 40-hex commit",
                )


def check_downloaded_surface_checkout_credentials(errors: list[str]) -> None:
    for relative in (
        ".github/workflows/ci.yml",
        ".github/workflows/nils-cli-latest-canary.yml",
    ):
        text = read(relative)
        checkout_count = 0
        for match in re.finditer(r"(?ms)^      - (?P<body>.*?)(?=^      - |\Z)", text):
            step = match.group(0)
            if "uses: actions/checkout@" not in step:
                continue
            checkout_count += 1
            if not re.search(
                r"^\s+persist-credentials:\s*false\s*(?:#.*)?$",
                step,
                re.MULTILINE,
            ):
                fail(
                    errors,
                    f"{relative}: actions/checkout before downloaded nils-cli execution must set persist-credentials: false",
                )
        if checkout_count == 0:
            fail(errors, f"{relative}: expected at least one actions/checkout step")


def check_dependabot(errors: list[str]) -> None:
    path = ROOT / ".github" / "dependabot.yml"
    if not path.is_file():
        fail(errors, ".github/dependabot.yml is missing")
        return
    text = path.read_text(encoding="utf-8")
    for ecosystem in ("github-actions", "docker", "npm"):
        if f"package-ecosystem: {ecosystem}" not in text:
            fail(errors, f".github/dependabot.yml missing {ecosystem} ecosystem")


def pin_value(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*\"?([0-9a-f]{{64}})\"?\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def mapped_pin_value(text: str, mapping: str, key: str) -> str | None:
    block = re.search(
        rf"^\s{{2}}{re.escape(mapping)}:\s*$\n(?P<body>(?:^\s{{4}}.*(?:\n|$))+)",
        text,
        re.MULTILINE,
    )
    return pin_value(block.group("body"), key) if block else None


def version_tag_value(text: str, key: str) -> str | None:
    match = re.search(
        rf'^\s*{re.escape(key)}:\s*"(v\d+\.\d+\.\d+)"\s*$',
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def arg_value(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*ARG\s+{re.escape(key)}=([0-9a-f]{{64}})\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def arg_text_value(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*ARG\s+{re.escape(key)}=([^\s#]+)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def runtime_recommended_version(text: str, product: str) -> str | None:
    match = re.search(
        rf"^\s{{2}}{re.escape(product)}:\n(?P<body>.*?)(?=^\s{{2}}\w+:|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return None
    version_match = re.search(
        r'^\s*recommended_version:\s*"([^"]+)"\s*$',
        match.group("body"),
        re.MULTILINE,
    )
    return version_match.group(1) if version_match else None


def workflow_step(text: str, name: str) -> str | None:
    marker = f"      - name: {name}"
    start = text.find(marker)
    if start == -1:
        return None
    end = text.find("\n      - name:", start + 1)
    return text[start:] if end == -1 else text[start:end]


def check_nils_pin_manifest(errors: list[str]) -> None:
    text = read("docs/source/nils-cli-pin.yaml")
    minimum_digest_text = read("docs/source/nils-cli-minimum-digest.yaml")
    if not re.search(r"^schema_version:\s*2\s*$", text, re.MULTILINE):
        fail(errors, "docs/source/nils-cli-pin.yaml must use schema_version 2")
    for key in ("minimum_supported_tag", "validated_tag"):
        if not version_tag_value(text, key):
            fail(errors, f"docs/source/nils-cli-pin.yaml missing nils_cli.{key}")
    for key in ("linux_amd64", "linux_arm64"):
        if not mapped_pin_value(text, "release_sha256", key):
            fail(errors, f"docs/source/nils-cli-pin.yaml missing nils_cli.release_sha256.{key}")
        if not pin_value(minimum_digest_text, key):
            fail(errors, f"docs/source/nils-cli-minimum-digest.yaml missing release_sha256.{key}")
    minimum = version_tag_value(text, "minimum_supported_tag")
    retained = version_tag_value(minimum_digest_text, "minimum_supported_tag")
    if minimum != retained:
        fail(errors, "nils-cli minimum digest tag does not match minimum_supported_tag")


def check_dockerfile(errors: list[str]) -> None:
    dockerfile = read("docker/Dockerfile")
    for line_no, line in enumerate(dockerfile.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("FROM ") and "@sha256:" not in stripped:
            fail(errors, f"docker/Dockerfile:{line_no}: FROM line is not digest-pinned")

    required_args = (
        "NILS_CLI_SHA256_AMD64",
        "NILS_CLI_SHA256_ARM64",
        "GH_SHA256_AMD64",
        "GH_SHA256_ARM64",
        "GLAB_SHA256_AMD64",
        "GLAB_SHA256_ARM64",
        "YQ_SHA256_AMD64",
        "YQ_SHA256_ARM64",
    )
    for arg in required_args:
        if not arg_value(dockerfile, arg):
            fail(errors, f"docker/Dockerfile missing 64-hex ARG {arg}")

    pin_text = read("docs/source/nils-cli-pin.yaml")
    expected_nils_cli_version = version_tag_value(pin_text, "validated_tag")
    docker_nils_cli_version = arg_text_value(dockerfile, "NILS_CLI_VERSION")
    if expected_nils_cli_version and docker_nils_cli_version != expected_nils_cli_version:
        fail(
            errors,
            "docker/Dockerfile NILS_CLI_VERSION default does not match nils_cli.validated_tag",
        )
    manifest_pairs = {
        "NILS_CLI_SHA256_AMD64": mapped_pin_value(pin_text, "release_sha256", "linux_amd64"),
        "NILS_CLI_SHA256_ARM64": mapped_pin_value(pin_text, "release_sha256", "linux_arm64"),
    }
    for arg, manifest_value in manifest_pairs.items():
        docker_value = arg_value(dockerfile, arg)
        if docker_value != manifest_value:
            fail(errors, f"docker/Dockerfile {arg} default does not match docs/source/nils-cli-pin.yaml")

    runtime_roots = read("manifests/runtime-roots.yaml")
    product_version_pairs = {
        "CLAUDE_CODE_VERSION": runtime_recommended_version(runtime_roots, "claude"),
        "CODEX_VERSION": runtime_recommended_version(runtime_roots, "codex"),
    }
    for arg, expected in product_version_pairs.items():
        value = arg_text_value(dockerfile, arg)
        if value in {None, "", "latest"}:
            fail(errors, f"docker/Dockerfile {arg} must be pinned, not latest")
        elif expected and value != expected:
            fail(errors, f"docker/Dockerfile {arg}={value} does not match manifests/runtime-roots.yaml recommended_version={expected}")

    required_fragments = (
        "test \"$expected\" = \"$published\"",
        "test \"$gh_sha\" = \"$gh_published\"",
        "test \"$glab_sha\" = \"$glab_published\"",
        "echo \"${yq_sha}  /tmp/${yq_file}\" | sha256sum -c -",
    )
    for fragment in required_fragments:
        if fragment not in dockerfile:
            fail(errors, f"docker/Dockerfile missing checksum verification fragment: {fragment}")

    if "COPY docker/npm-cli-pins/package.json docker/npm-cli-pins/package-lock.json /opt/npm-cli-pins/" not in dockerfile:
        fail(errors, "docker/Dockerfile must install AI CLIs from docker/npm-cli-pins lockfile")
    if "npm ci --omit=dev" not in dockerfile:
        fail(errors, "docker/Dockerfile must use npm ci for AI CLI lockfile install")


def check_npm_cli_lockfile(errors: list[str]) -> None:
    try:
        package_json = json.loads(read("docker/npm-cli-pins/package.json"))
        package_lock = json.loads(read("docker/npm-cli-pins/package-lock.json"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(errors, f"docker/npm-cli-pins lockfile parse failed: {exc}")
        return

    dockerfile = read("docker/Dockerfile")
    runtime_roots = read("manifests/runtime-roots.yaml")
    expected = {
        "@anthropic-ai/claude-code": (
            "CLAUDE_CODE_VERSION",
            runtime_recommended_version(runtime_roots, "claude"),
        ),
        "@openai/codex": (
            "CODEX_VERSION",
            runtime_recommended_version(runtime_roots, "codex"),
        ),
    }
    dependencies = package_json.get("dependencies")
    lock_packages = package_lock.get("packages")
    if not isinstance(dependencies, dict):
        fail(errors, "docker/npm-cli-pins/package.json missing dependencies object")
        return
    if not isinstance(lock_packages, dict):
        fail(errors, "docker/npm-cli-pins/package-lock.json missing packages object")
        return

    for package_name, (arg_name, recommended_version) in expected.items():
        docker_version = arg_text_value(dockerfile, arg_name)
        expected_version = recommended_version or docker_version
        if not expected_version:
            fail(errors, f"could not resolve expected version for {package_name}")
            continue
        if docker_version != expected_version:
            fail(errors, f"docker/Dockerfile {arg_name}={docker_version} does not match expected {expected_version}")
        if dependencies.get(package_name) != expected_version:
            fail(errors, f"docker/npm-cli-pins/package.json {package_name} must be pinned to {expected_version}")
        package_entry = lock_packages.get(f"node_modules/{package_name}")
        if not isinstance(package_entry, dict):
            fail(errors, f"docker/npm-cli-pins/package-lock.json missing {package_name}")
            continue
        if package_entry.get("version") != expected_version:
            fail(errors, f"docker/npm-cli-pins/package-lock.json {package_name} version does not match {expected_version}")
        integrity = package_entry.get("integrity")
        if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
            fail(errors, f"docker/npm-cli-pins/package-lock.json {package_name} missing sha512 integrity")


def check_docker_build_entrypoint(errors: list[str]) -> None:
    script = read("docker/build.sh")
    if "validated_tag" not in script or "pinned_tag" in script:
        fail(errors, "docker/build.sh must source nils_cli.validated_tag, never pinned_tag")
    for key in ("NILS_CLI_VERSION", "NILS_CLI_SHA256_AMD64", "NILS_CLI_SHA256_ARM64"):
        if f'--build-arg "{key}=' not in script:
            fail(errors, f"docker/build.sh does not pass {key} from docs/source/nils-cli-pin.yaml")


def check_publish_workflow(errors: list[str]) -> None:
    workflow = read(".github/workflows/publish-image.yml")
    if "validated_tag" not in workflow or "pinned_tag" in workflow:
        fail(errors, ".github/workflows/publish-image.yml must source nils_cli.validated_tag")
    for fragment in (
        "id-token: write",
        "attestations: write",
        "provenance: true",
        "sbom: true",
        "actions/attest-build-provenance@",
    ):
        if fragment not in workflow:
            fail(errors, f".github/workflows/publish-image.yml missing {fragment}")
    for step_name in ("Build amd64 for smoke test", "Build and push multi-arch"):
        step = workflow_step(workflow, step_name)
        if step is None:
            fail(errors, f".github/workflows/publish-image.yml missing step {step_name}")
            continue
        for fragment in (
            "NILS_CLI_VERSION=${{ steps.pin.outputs.nils_cli }}",
            "NILS_CLI_SHA256_AMD64=${{ steps.pin.outputs.nils_cli_sha256_amd64 }}",
            "NILS_CLI_SHA256_ARM64=${{ steps.pin.outputs.nils_cli_sha256_arm64 }}",
        ):
            if fragment not in step:
                fail(errors, f".github/workflows/publish-image.yml step {step_name} missing {fragment}")
    push_step = workflow_step(workflow, "Build and push multi-arch") or ""
    for fragment in ("id: push", "push: true"):
        if fragment not in push_step:
            fail(errors, f".github/workflows/publish-image.yml final publish step missing {fragment}")
    for line_no, line in enumerate(workflow.splitlines(), 1):
        if "actions/attest-build-provenance@" in line:
            ref = line.split("@", 1)[1].split()[0]
            if not HEX40_RE.fullmatch(ref):
                fail(errors, f".github/workflows/publish-image.yml:{line_no}: attestation action is not SHA-pinned")


def main() -> int:
    errors: list[str] = []
    check_workflow_action_pins(errors)
    check_downloaded_surface_checkout_credentials(errors)
    check_dependabot(errors)
    check_nils_pin_manifest(errors)
    check_dockerfile(errors)
    check_npm_cli_lockfile(errors)
    check_docker_build_entrypoint(errors)
    check_publish_workflow(errors)

    if errors:
        print("security-hardening-audit: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("security-hardening-audit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
