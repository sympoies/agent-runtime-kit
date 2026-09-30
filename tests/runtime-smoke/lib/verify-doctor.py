#!/usr/bin/env python3
"""Validate current installs and explicit historical plan-retirement diagnostics."""

import json
import pathlib
import sys

RETIRED = {"plan-archive", "plan-issue", "plan-tooling"}


def verify(report, product, policy, exit_code):
    assert policy in ("strict", "historical"), "unknown doctor policy"
    assert report["schema_version"] == "agent-runtime-cli.doctor.v1"
    assert report["product"] == product
    block, warn = report["block"], report["warn"]
    assert type(block) is int and block >= 0
    assert type(warn) is int and warn >= 0
    assert report["exit_code"] == exit_code == (2 if block else 1 if warn else 0)
    findings = [item for item in report["findings"] if item["severity"] == "block"]
    assert len(findings) == block
    if policy == "strict":
        assert block == 0, "current source has blocking doctor findings"
    else:
        # This frozen fixture's old workflows are intentionally not executable.
        # Verify only their known retirement diagnostics; every other block fails.
        assert block == 3 and exit_code == 2
        assert {(item["check"], item["entry_id"]) for item in findings} == {
            ("required-cli", binary) for binary in RETIRED
        }
        assert all(item["product"] == product for item in findings)
        assert all(item["message"].startswith("status=missing ") for item in findings)


if __name__ == "__main__":
    path, product, policy, observed_exit = sys.argv[1:]
    verify(json.loads(pathlib.Path(path).read_text()), product, policy, int(observed_exit))
