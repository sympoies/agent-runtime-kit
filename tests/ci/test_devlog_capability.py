#!/usr/bin/env python3
"""Owner tests for the devlog default agent capability (#120).

The capability rests on one routing fact: a repository that has a development
log gets `core/policies/devlog-capability.md` as required project-dev delivery
reading, and a repository that has none does not. Both directory conventions
count, and neither repository is expected to move its log to satisfy the other.

The `edit` phase is deliberately excluded. `test_policy_simplification.py` pins
that phase to a single required document, and that budget belongs to the edit
contract; the read half is routed by the `project-dev` intent card instead.

`when` is declared in `AGENT_DOCS.toml` and resolved by `agent-docs` against the
*project* root even though the document itself is home-scoped. That is the part
worth pinning: if it were resolved against the docs home instead, every
repository would inherit the capability whether or not it had a log, and the
detection clause in the policy would silently mean nothing.
"""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = "devlog-capability.md"


def preflight(project_path: Path, phase: str = "delivery") -> dict:
    """Resolve project-dev docs for `project_path` against this kit."""
    completed = subprocess.run(
        [
            "agent-docs",
            "preflight",
            "--intent",
            "project-dev",
            "--phase",
            phase,
            "--docs-home",
            str(REPO_ROOT),
            "--project-path",
            str(project_path),
            "--product",
            "claude",
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    # agent-docs reports why it failed in the JSON payload, not in the exit
    # status, so surface both rather than letting a CalledProcessError hide the
    # reason behind a bare exit code.
    detail = f"exit={completed.returncode}\n{completed.stdout}{completed.stderr}"
    assert completed.returncode == 0, detail
    payload = json.loads(completed.stdout)
    assert payload.get("ok") is not False, detail
    return payload


def capability_row(payload: dict) -> dict:
    for document in payload.get("documents", []):
        if Path(document["path"]).name == POLICY:
            return document
    raise AssertionError(f"{POLICY} is not declared for project-dev/delivery at all")


class DevlogCapabilityRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("agent-docs") is None:
            raise unittest.SkipTest("agent-docs is not installed")

    def assert_required(self, project_path: Path, expected: bool) -> None:
        row = capability_row(preflight(project_path))
        self.assertEqual(
            row["when_satisfied"],
            expected,
            f"when_satisfied for {project_path}: {row['when']}",
        )
        self.assertEqual(row["required"], expected)

    def test_the_policy_is_delivery_scoped_and_leaves_the_edit_phase_alone(
        self,
    ) -> None:
        row = capability_row(preflight(REPO_ROOT))
        self.assertEqual(row["scope"], "home")
        self.assertEqual(row["phases"], ["delivery"])
        self.assertTrue(row["declared_required"])

        # Without this the declaration can name a file that does not exist and
        # every gate stays green.
        self.assertEqual(row["status"], "present")
        self.assertTrue(row["validation"]["valid"])

        edit = preflight(REPO_ROOT, phase="edit")
        self.assertNotIn(
            POLICY,
            [Path(document["path"]).name for document in edit.get("documents", [])],
            "the edit phase is pinned to one required document; see "
            "tests/ci/test_policy_simplification.py",
        )

    def test_this_kit_source_render_split_log_is_detected(self) -> None:
        self.assertTrue((REPO_ROOT / "docs" / "source" / "devlog").is_dir())
        self.assert_required(REPO_ROOT, True)

    def test_each_convention_is_detected_on_its_own(self) -> None:
        for convention in ("docs/devlog", "docs/source/devlog"):
            with self.subTest(convention=convention):
                with tempfile.TemporaryDirectory() as raw:
                    project = Path(raw)
                    log = project / convention
                    log.mkdir(parents=True)
                    (log / "README.md").write_text("# Development log\n")
                    self.assert_required(project, True)

    def test_a_repository_without_a_log_is_unaffected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            # Enough to look like an ordinary project-dev repository, but with
            # no log: detection has to fail closed to "no log here".
            (project / "Cargo.toml").write_text("[package]\nname = \"x\"\n")
            self.assert_required(project, False)

    def test_a_devlog_directory_without_its_index_is_not_a_log(self) -> None:
        # The index is what the policy points a reader at; a bare directory is
        # not yet a log, and claiming otherwise would route an agent to
        # conventions that do not exist.
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "docs" / "devlog").mkdir(parents=True)
            self.assert_required(project, False)


class DevlogCapabilityReadHalfTests(unittest.TestCase):
    """The intent card is load-bearing, not decoration.

    Excluding the `edit` phase is only defensible because the `project-dev`
    card carries the read trigger. Removing the card would silently strip the
    read half without failing anything else.
    """

    def test_the_project_dev_card_carries_the_read_trigger(self) -> None:
        card = " ".join((REPO_ROOT / "core/policies/intent-cards.md").read_text().split())

        for required in (
            "docs/devlog/",
            "docs/source/devlog/",
            "search the log before changing a contract",
            "core/policies/devlog-capability.md",
        ):
            with self.subTest(required=required):
                self.assertIn(required, card)


if __name__ == "__main__":
    unittest.main()
