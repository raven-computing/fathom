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
"""Unit tests for the UpdateManager class."""

from unittest.mock import patch

from raven.fathom.server.version import Version
from raven.fathom.server.updates.manager import (
    UpdateManager,
    FailedApplicationUpdateException,
)

from tests.unit import TestCase
from tests.unit.mocks import Mock

# pylint: disable=W0212


def v(major: int, minor: int, patch_num: int):
    """Helper: Create a Version instance."""
    return Version(major, minor, patch_num)


def _yield(procedures):
    yield from procedures


class TestUpdateManagerDetection(TestCase):
    """Tests for update and first-start detection logic."""

    def setUp(self):
        super().setUp()
        self.manager = UpdateManager()

    def test_detects_update_when_versions_differ(self):
        self.manager._current_version = v(1, 2, 0)
        self.manager._previous_version = v(1, 1, 0)
        self.assertTrue(self.manager.application_update_detected())

    def test_no_update_when_versions_are_equal(self):
        self.manager._current_version = v(1, 2, 0)
        self.manager._previous_version = v(1, 2, 0)
        self.assertFalse(self.manager.application_update_detected())

    def test_no_update_when_previous_is_greater(self):
        """Downgrade scenario: no update should be reported."""
        self.manager._current_version = v(1, 1, 0)
        self.manager._previous_version = v(1, 2, 0)
        self.assertFalse(self.manager.application_update_detected())

    def test_no_update_when_no_previous_version(self):
        """Fresh install: previous version is None, so no update."""
        self.manager._current_version = v(1, 0, 0)
        self.manager._previous_version = None
        with patch.object(
            self.manager, "determine_previous_version", return_value=None
        ):
            self.assertFalse(self.manager.application_update_detected())

    def test_detects_first_start_when_no_previous_version(self):
        with patch.object(
            self.manager, "determine_previous_version", return_value=None
        ):
            self.assertTrue(self.manager.application_first_start_detected())

    def test_no_first_start_when_previous_version_exists(self):
        with patch.object(
            self.manager,
            "determine_previous_version",
            return_value=v(1, 0, 0),
        ):
            self.assertFalse(self.manager.application_first_start_detected())

    def test_determine_current_version_raises_when_version_unavailable(self):
        with patch(
            "raven.fathom.server.updates.manager.Version.current",
            return_value=None,
        ):
            with self.assertRaises(FailedApplicationUpdateException):
                self.manager.determine_current_version()

    def test_determine_current_version_returns_cached_value(self):
        cached = v(2, 0, 0)
        self.manager._current_version = cached
        result = self.manager.determine_current_version()
        self.assertIs(result, cached)


class TestUpdateManagerFilterApplicable(TestCase):
    """Tests for the _filter_applicable version range logic."""

    def setUp(self):
        super().setUp()
        self.manager = UpdateManager()

    def _make_procedure(self, major, minor, patch_num):
        mock = Mock()
        mock.target_version = v(major, minor, patch_num)
        return mock

    def test_applies_only_procedures_in_version_range(self):
        previous = v(1, 0, 0)
        current = v(1, 3, 0)
        procedures = (
            self._make_procedure(1, 0, 0),  # excluded: not > previous
            self._make_procedure(1, 1, 0),  # included
            self._make_procedure(1, 2, 0),  # included
            self._make_procedure(1, 3, 0),  # included (boundary)
            self._make_procedure(1, 4, 0),  # excluded: > current
        )
        result = list(
            self.manager._filter_applicable(
                _yield(procedures), previous, current
            )
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].target_version, v(1, 1, 0))
        self.assertEqual(result[1].target_version, v(1, 2, 0))
        self.assertEqual(result[2].target_version, v(1, 3, 0))

    def test_procedure_at_exact_previous_boundary_is_excluded(self):
        previous = v(1, 1, 0)
        current = v(1, 2, 0)
        procedures = [self._make_procedure(1, 1, 0)]
        result = list(
            self.manager._filter_applicable(
                _yield(procedures), previous, current
            )
        )
        self.assertEqual(len(result), 0)

    def test_procedure_at_exact_current_boundary_is_included(self):
        previous = v(1, 0, 0)
        current = v(1, 1, 0)
        procedures = [self._make_procedure(1, 1, 0)]
        result = list(
            self.manager._filter_applicable(
                _yield(procedures), previous, current
            )
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_version, v(1, 1, 0))

    def test_empty_procedures_list_yields_no_results(self):
        result = list(
            self.manager._filter_applicable(
                _yield([]), v(1, 0, 0), v(1, 2, 0)
            )
        )
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    TestCase.run_tests()
