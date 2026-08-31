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
"""Common test code."""

# pylint: disable=C0103

from unittest import skip

from raven.fathom.base import Configuration

from raven.fathom.base._env import HostSystemEnvironment, OperatingSystem
from raven.fathom.base.testing import BaseTestCase, BaseTestFixture
from raven.fathom.base.testing import run_test_program


class FathomTestCase(BaseTestCase):
    """Base class for all Fathom test cases."""

    @staticmethod
    def run_tests():
        """Starts the test execution and runs all available tests."""
        run_test_program()


class FathomTestFixture(BaseTestFixture):
    """Base class for all Fathom test fixtures."""

    def setUp(self):
        super().setUp()
        self.app_config = Configuration()


def skipIfNotOnLinux(reason=None):
    """Skips the test if the underlying OS
    is not `OperatingSystem.GNU_LINUX`.

    Apply this decorator to platform-specific test methods.

    Args:
        reason (str): The reason text informing why
            the decorated method was skipped.
    """
    def decorator(wrapped):
        return wrapped

    operating_system = HostSystemEnvironment().get_operating_system()
    if operating_system != OperatingSystem.GNU_LINUX:
        return skip(reason or "")

    return decorator


def skipIfNotOnWindows(reason=None):
    """Skips the test if the underlying OS
    is not `OperatingSystem.MS_WINDOWS`.

    Apply this decorator to platform-specific test methods.

    Args:
        reason (str): The reason text informing why
            the decorated method was skipped.
    """
    def decorator(wrapped):
        return wrapped

    operating_system = HostSystemEnvironment().get_operating_system()
    if operating_system != OperatingSystem.MS_WINDOWS:
        return skip(reason or "")

    return decorator
