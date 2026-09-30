#!/usr/bin/env python3
"""Validate current installs and explicit historical plan-retirement diagnostics."""

import json
import pathlib
import sys

RETIRED = {"plan-archive", "plan-issue", "plan-tooling"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(report, product, policy, exit_code):
    require(policy in ("strict", "historical"), "unknown doctor policy")
    require(report["schema_version"] == "agent-runtime-cli.doctor.v1", "doctor schema mismatch")
    require(report["product"] == product, "doctor product mismatch")
    block, warn = report["block"], report["warn"]
    require(type(block) is int and block >= 0, "invalid block count")
    require(type(warn) is int and warn >= 0, "invalid warning count")
    require(report["exit_code"] == exit_code == (2 if block else 1 if warn else 0), "doctor exit mismatch")
    findings = [item for item in report["findings"] if item["severity"] == "block"]
    require(len(findings) == block, "blocking finding count mismatch")
    if policy == "strict":
        require(block == 0, "current source has blocking doctor findings")
    else:
        # This frozen fixture's old workflows are intentionally not executable.
        # Verify only their known retirement diagnostics; every other block fails.
        require(block == 3 and exit_code == 2, "historical retirement count mismatch")
        require({(item["check"], item["entry_id"]) for item in findings} == {
            ("required-cli", binary) for binary in RETIRED
        }, "unexpected historical blocking finding")
        require(all(item["product"] == product for item in findings), "historical finding product mismatch")
        require(all(item["message"].startswith("status=missing ") for item in findings), "historical command is not missing")


if __name__ == "__main__":
    path, product, policy, observed_exit = sys.argv[1:]
    verify(json.loads(pathlib.Path(path).read_text()), product, policy, int(observed_exit))
