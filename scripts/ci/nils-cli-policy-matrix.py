#!/usr/bin/env python3
"""Render exact CI lanes and bootstrap canonical remote canary selection.

The canary selector is deliberately narrow: it runs before a candidate
agent-runtime binary exists and mirrors the released doctor's canonical u64
stable-tag round-trip contract. Focused regressions guard that exception.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TAG_RE = re.compile(
    r"^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
U64_MAX = 2**64 - 1


def scalar(text: str, key: str) -> str:
    match = re.search(rf'^\s*{re.escape(key)}:\s*"([^"#]+)"\s*$', text, re.MULTILINE)
    if match is None:
        raise ValueError(f"missing nils-cli policy field: {key}")
    return match.group(1)


def mapping_scalar(text: str, mapping: str, key: str) -> str:
    match = re.search(
        rf"^\s{{2}}{re.escape(mapping)}:\s*$\n(?P<body>(?:^\s{{4}}.*(?:\n|$))+)",
        text,
        re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"missing nils-cli policy mapping: {mapping}")
    return scalar(match.group("body"), key)


def semver(tag: str, label: str = "candidate") -> tuple[int, int, int]:
    if TAG_RE.fullmatch(tag) is None:
        raise ValueError(f"{label} must be a stable vMAJOR.MINOR.PATCH tag: {tag}")
    parts = tuple(int(part) for part in tag[1:].split("."))
    if any(part > U64_MAX for part in parts):
        raise ValueError(f"{label} exceeds the canonical u64 version range: {tag}")
    return parts  # type: ignore[return-value]


def build_matrix(
    manifest: Path, minimum_digest_manifest: Path
) -> tuple[dict[str, list[dict[str, str]]], str, str]:
    text = manifest.read_text(encoding="utf-8")
    minimum_digest_text = minimum_digest_manifest.read_text(encoding="utf-8")
    if not re.search(r"^schema_version:\s*2\s*$", text, re.MULTILINE):
        raise ValueError("nils-cli policy must use schema_version 2")
    minimum_supported_tag = scalar(text, "minimum_supported_tag")
    validated_tag = scalar(text, "validated_tag")
    minimum_version = semver(minimum_supported_tag, "minimum_supported_tag")
    validated_version = semver(validated_tag, "validated_tag")
    if minimum_version > validated_version:
        raise ValueError("minimum_supported_tag must not be newer than validated_tag")

    if not re.search(r"^schema_version:\s*1\s*$", minimum_digest_text, re.MULTILINE):
        raise ValueError("minimum digest manifest must use schema_version 1")
    retained_minimum_tag = scalar(minimum_digest_text, "minimum_supported_tag")
    if retained_minimum_tag != minimum_supported_tag:
        raise ValueError(
            "minimum digest manifest tag must equal nils-cli minimum_supported_tag"
        )
    minimum_sha256 = scalar(minimum_digest_text, "linux_amd64")
    validated_sha256 = mapping_scalar(text, "release_sha256", "linux_amd64")
    for key, digest in (
        ("minimum digest release_sha256.linux_amd64", minimum_sha256),
        ("release_sha256.linux_amd64", validated_sha256),
    ):
        if SHA256_RE.fullmatch(digest) is None:
            raise ValueError(f"{key} must be a lowercase 64-hex SHA256")

    if minimum_supported_tag == validated_tag:
        if minimum_sha256 != validated_sha256:
            raise ValueError("equal minimum/validated tags must use the same linux_amd64 digest")
        include = [
            {
                "lane": "minimum+validated",
                "tag": minimum_supported_tag,
                "roles": "minimum,validated",
                "sha256": minimum_sha256,
            }
        ]
    else:
        include = [
            {
                "lane": "minimum",
                "tag": minimum_supported_tag,
                "roles": "minimum",
                "sha256": minimum_sha256,
            },
            {
                "lane": "validated",
                "tag": validated_tag,
                "roles": "validated",
                "sha256": validated_sha256,
            },
        ]
    return {"include": include}, minimum_supported_tag, validated_tag


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/source/nils-cli-pin.yaml"),
    )
    parser.add_argument(
        "--minimum-digest-manifest",
        type=Path,
        default=Path("docs/source/nils-cli-minimum-digest.yaml"),
    )
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument(
        "--assert-candidate-at-least-validated",
        metavar="TAG",
        help="fail unless TAG is stable semver and is not older than validated_tag",
    )
    parser.add_argument(
        "--select-newest-stable",
        action="store_true",
        help="read release tags from stdin, ignore noncanonical tags, and print the greatest stable tag",
    )
    args = parser.parse_args()

    try:
        matrix, minimum, validated = build_matrix(
            args.manifest, args.minimum_digest_manifest
        )
        if args.assert_candidate_at_least_validated:
            candidate = args.assert_candidate_at_least_validated
            if semver(candidate) < semver(validated):
                raise ValueError(f"candidate {candidate} is older than validated_tag {validated}")
        if args.select_newest_stable:
            candidates = []
            for raw in sys.stdin:
                tag = raw.strip()
                try:
                    version = semver(tag)
                except ValueError:
                    continue
                candidates.append((version, tag))
            if not candidates:
                raise ValueError("no canonical stable release tags were provided")
            print(max(candidates)[1])
            return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if args.assert_candidate_at_least_validated:
        print(args.assert_candidate_at_least_validated)
        return 0

    encoded = json.dumps(matrix, separators=(",", ":"))
    if args.github_output:
        print(f"matrix={encoded}")
        print(f"minimum_supported_tag={minimum}")
        print(f"validated_tag={validated}")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
