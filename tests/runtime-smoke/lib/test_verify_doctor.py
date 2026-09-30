#!/usr/bin/env python3
"""Behavioral boundaries for the historical doctor retirement exception."""

import copy
import importlib.util
import pathlib
import json
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("verify_doctor", pathlib.Path(__file__).with_name("verify-doctor.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def report(retired=False, warn=0):
    findings = [{"product": "codex", "severity": "block", "check": "required-cli",
                 "entry_id": binary, "message": f"status=missing command=`{binary}`"}
                for binary in sorted(module.RETIRED)] if retired else []
    return {"schema_version": "agent-runtime-cli.doctor.v1", "product": "codex",
            "block": len(findings), "warn": warn,
            "exit_code": 2 if findings else 1 if warn else 0, "findings": findings}


class DoctorPolicyTest(unittest.TestCase):
    def test_current_admits_clean_or_warning_only_reports(self):
        for warnings in (0, 2):
            data = report(warn=warnings)
            module.verify(data, "codex", "strict", data["exit_code"])

    def test_current_rejects_retired_command_requirements(self):
        with self.assertRaises(ValueError):
            module.verify(report(retired=True), "codex", "strict", 2)

    def test_historical_accepts_exact_missing_retired_set(self):
        module.verify(report(retired=True, warn=2), "codex", "historical", 2)

    def test_historical_rejects_extra_changed_or_wrongly_typed_blocks(self):
        original = report(retired=True)
        variants = []
        extra = copy.deepcopy(original)
        extra["findings"].append({"product": "codex", "severity": "block", "check": "required-cli", "entry_id": "agent-out", "message": "status=missing command=`agent-out`"})
        extra["block"] += 1
        variants.append(extra)
        for field, value in (("check", "installed-runtime-source"), ("entry_id", "agent-out"), ("message", "status=outdated command=`plan-issue`")):
            data = copy.deepcopy(original)
            data["findings"][0][field] = value
            variants.append(data)
        variants.append(report())
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                module.verify(data, "codex", "historical", data["exit_code"])

    def test_optimized_subprocess_still_rejects_unexpected_blocks(self):
        strict = report(retired=True)
        historical = copy.deepcopy(strict)
        historical["findings"][0]["entry_id"] = "agent-out"
        for policy, data in (("strict", strict), ("historical", historical)):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as tmp:
                fixture = pathlib.Path(tmp) / "doctor.json"
                fixture.write_text(json.dumps(data))
                result = subprocess.run(
                    [sys.executable, "-O", str(pathlib.Path(__file__).with_name("verify-doctor.py")),
                     str(fixture), "codex", policy, "2"], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schema_product_and_exit_must_match(self):
        for field, value in (("schema_version", "invalid"), ("product", "claude"), ("exit_code", 0)):
            data = report(retired=True)
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.verify(data, "codex", "historical", 2)


if __name__ == "__main__":
    unittest.main()
