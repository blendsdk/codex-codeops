#!/usr/bin/env python3
from __future__ import annotations

import importlib
import unittest


DECLARED_MODULES = (
    "tests.conformance.test_state_v1_compat_spec",
    "tests.conformance.test_state_v2_spec",
    "tests.conformance.test_state_v2_impl",
    "tests.conformance.test_state_migration_spec",
    "tests.conformance.test_state_migration_impl",
)

IMPLEMENTED_ST_CASES = set(range(1, 28)) | {35, 36, 37, 38, 39, 42, 43, 44, 45, 46, 47, 48, 49}


def flatten(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class StateTestCollectionGuard(unittest.TestCase):
    def test_every_declared_module_imports_and_collects(self) -> None:
        loader = unittest.defaultTestLoader
        for module_name in DECLARED_MODULES:
            module = importlib.import_module(module_name)
            tests = list(flatten(loader.loadTestsFromModule(module)))
            self.assertTrue(tests, f"{module_name} collected no tests")

    def test_implemented_st_cases_have_exactly_one_specification_test(self) -> None:
        names = []
        for module_name in DECLARED_MODULES:
            module = importlib.import_module(module_name)
            names.extend(
                test._testMethodName
                for test in flatten(unittest.defaultTestLoader.loadTestsFromModule(module))
            )
        for case in IMPLEMENTED_ST_CASES:
            matches = [name for name in names if name.startswith(f"test_st_{case}_")]
            self.assertEqual(matches, [matches[0]] if matches else [], f"ST-{case} ownership")
            self.assertEqual(len(matches), 1, f"ST-{case} must have exactly one implementation")


if __name__ == "__main__":
    unittest.main()
