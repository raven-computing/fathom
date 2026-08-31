# Copyright (C) 2026 Raven Computing
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Definitions for base test cases and test fixtures."""

import unittest


def run_test_program():
    """Runs the tests."""
    unittest.main()


class BaseTestCase(unittest.TestCase):
    """Base class for all test cases."""


class BaseTestFixture(unittest.TestCase):
    """Base class for all test fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.load_fixture()
        super().setUpClass()

    def setUp(self):
        self.set_up_fixture()
        super().setUp()

    @classmethod
    def load_fixture(cls):
        """Load method to be overridden by concrete test fixture classes.

        Will be called once before the first test method is executed.
        """

    def set_up_fixture(self):
        """Set up method to be overridden by concrete test fixture classes.

        Will be called before each test method is executed.
        """
