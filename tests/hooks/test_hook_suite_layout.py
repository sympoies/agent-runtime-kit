#!/usr/bin/env python3
"""Keep hook test modules within the provider input budget."""
from pathlib import Path
import importlib
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))


def iter_cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_cases(item)
        else:
            yield item


class HookSuiteLayoutTests(unittest.TestCase):
    def test_hook_test_modules_fit_provider_input_budget(self) -> None:
        for path in Path(__file__).parent.glob("*.py"):
            with self.subTest(module=path.name):
                self.assertLess(path.stat().st_size, 1024 * 1024)

    def test_entrypoint_collects_every_domain_case_once(self) -> None:
        entrypoint = importlib.import_module("test_shared_hooks")
        loader = unittest.TestLoader()
        domain_names = []
        for path in Path(__file__).parent.glob("shared_hook_*.py"):
            module = importlib.import_module(path.stem)
            for value in vars(module).values():
                if (isinstance(value, type) and issubclass(value, unittest.TestCase)
                        and value.__module__ == module.__name__):
                    domain_names.extend(case._testMethodName for case in
                                        iter_cases(loader.loadTestsFromTestCase(value)))
        aggregate = list(iter_cases(loader.loadTestsFromTestCase(entrypoint.SharedHookTests)))
        discovered = list(iter_cases(loader.loadTestsFromModule(entrypoint)))
        self.assertTrue(domain_names)
        self.assertEqual(len(domain_names), len(set(domain_names)))
        self.assertEqual(sorted(domain_names), sorted(case._testMethodName for case in aggregate))
        self.assertEqual([case.id() for case in discovered], [case.id() for case in aggregate])


if __name__ == "__main__":
    unittest.main()
