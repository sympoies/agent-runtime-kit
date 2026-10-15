#!/usr/bin/env python3
"""Owner tests for the devlog default agent capability (#120).

The capability rests on one routing fact: a repository that has a development
log routes agents to `core/policies/devlog-capability.md`, and a repository that
has none does not need it. Both directory conventions count, and neither
repository is expected to move its log to satisfy the other. The always-on home
prompt names the policy and both conventions; the policy carries the trigger.
"""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = "devlog-capability.md"
HOME_PRODUCTS = ("codex", "claude", "hermes", "neutral")


def words(relative: str) -> str:
    return " ".join((REPO_ROOT / relative).read_text().split())


class DevlogCapabilityRoutingTests(unittest.TestCase):
    def test_every_home_prompt_routes_to_the_policy_for_both_conventions(self) -> None:
        for product in HOME_PRODUCTS:
            with self.subTest(product=product):
                home = words(f"tests/golden/{product}/AGENT_HOME.md")
                self.assertIn(f"`{POLICY}`", home)
                self.assertIn("`docs/devlog/`", home)
                self.assertIn("`docs/source/devlog/`", home)

    def test_this_kit_source_render_split_log_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "docs/source/devlog/README.md").is_file())


class DevlogCapabilityReadHalfTests(unittest.TestCase):
    """The trigger is load-bearing, not decoration.

    Nothing resolves the policy into context automatically, so its trigger must
    state when to open it. Removing it would silently strip the read half.
    """

    def test_the_policy_carries_the_read_trigger(self) -> None:
        policy = words(f"core/policies/{POLICY}")

        for required in (
            "docs/devlog/",
            "docs/source/devlog/",
            "search the log before changing a contract",
        ):
            with self.subTest(required=required):
                self.assertIn(required, policy)


class DevlogEnablementTests(unittest.TestCase):
    """Detection failing closed is an answer, not a gap to fill.

    `test_a_repository_without_a_log_is_unaffected` pins the routing half: the
    policy is not required reading in a repository with no log. That leaves the
    behavioral half, which routing cannot express — an agent that reads the
    policy anyway, or that carries its trigger into a repository without a log,
    must not respond to the absence by creating one. Enabling a log is the
    user's call for their repository. Nothing else in this kit says so, so
    losing these sentences would quietly turn a conditional capability into a
    mandate to add `docs/devlog/` everywhere it is not found.
    """

    def test_the_policy_refuses_to_create_a_log_and_names_its_owner(self) -> None:
        policy = " ".join((REPO_ROOT / "core/policies" / POLICY).read_text().split())

        for required in (
            "do not create a log directory",
            # The clause that stops the realistic failure: not creating the log
            # but filing its absence as work to be done.
            "do not raise either as a follow-up or a finding",
            "Add one only when the user asks",
        ):
            with self.subTest(required=required):
                self.assertIn(required, policy)

    def test_the_half_built_log_stays_carved_out(self) -> None:
        # A log directory with no index is a log someone already decided to
        # have. Naming its missing index is right there and wrong everywhere
        # else, so the two cases have to stay distinguishable in the prose.
        policy = " ".join((REPO_ROOT / "core/policies" / POLICY).read_text().split())

        self.assertIn("This section is about a repository with neither log directory", policy)
        self.assertIn("It is not the case the next section is about", policy)

    def test_the_trigger_carries_the_same_refusal(self) -> None:
        card = words(f"core/policies/{POLICY}")

        for required in (
            "create a log in a repository that has none",
            "report its absence as a gap",
            "enabling one is the user's call",
        ):
            with self.subTest(required=required):
                self.assertIn(required, card)


class DevlogRepairTests(unittest.TestCase):
    """The repair half of the mechanism.

    Thirteen repositories in this organization kept a log before the contract
    existed, and every one of them fails `devlog check` on adoption. Without a
    named command the reader's options are to hand-edit months of history or to
    leave the log permanently failing its own checker, and the second teaches
    everyone to ignore the exit code. What the section must keep saying is both
    halves: that the repair exists, and that it stops where guessing would
    start.
    """

    def test_the_policy_names_the_repair_and_its_limit(self) -> None:
        policy = " ".join((REPO_ROOT / "core/policies" / POLICY).read_text().split())

        self.assertIn("devlog fix", policy)
        for required in (
            # The limit matters more than the capability: a repair that guessed
            # would put invented history into a log meant to be trusted.
            "Everything else it reports and leaves alone",
            "belongs to whoever owns the repository",
            # Repair must not become a way around the enablement decision.
            "does not create a log, and does not create an index",
            # Adoption, not the write path. `new` already emits the right shape.
            "It is not part of the write path",
        ):
            with self.subTest(required=required):
                self.assertIn(required, policy)

    def test_repair_is_carved_out_of_the_never_rewrite_rule(self) -> None:
        # Without this, the rule against rewriting an older entry reads as a
        # ban on the repair, and a reader following the policy literally would
        # leave thirteen logs broken.
        policy = " ".join((REPO_ROOT / "core/policies" / POLICY).read_text().split())

        self.assertIn("never alters what an entry says", policy)

    def test_the_trigger_routes_a_broken_log_to_the_repair(self) -> None:
        # An agent that hits a failing `check` and has not been told the repair
        # exists will reach for an editor, which is the behaviour this whole
        # crate was built to remove.
        card = words(f"core/policies/{POLICY}")

        self.assertIn("hand-edit a log into shape when `devlog fix` would repair it", card)

    def test_the_shapes_fix_refuses_are_named(self) -> None:
        # Each of these is a case where `fix` writes nothing and reports
        # instead. A reader who does not know that reads a non-zero exit on a
        # log `fix` just ran over as a failure of the command rather than as
        # the log telling them something.
        policy = " ".join((REPO_ROOT / "core/policies" / POLICY).read_text().split())

        for required in (
            "an entry whose fence is never closed",
            "a file that mixes line endings",
            "a month file or index that is a symlink",
        ):
            with self.subTest(required=required):
                self.assertIn(required, policy)

    def test_fenced_examples_are_named_as_not_structure(self) -> None:
        # The entry documenting this format quotes headings and labels. If the
        # policy did not say they are examples, a reader would expect `check`
        # to report them and `fix` to rewrite them.
        policy = " ".join((REPO_ROOT / "core/policies" / POLICY).read_text().split())

        self.assertIn("Nothing inside a fenced code block is structure", policy)


if __name__ == "__main__":
    unittest.main()
