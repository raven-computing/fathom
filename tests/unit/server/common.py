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
"""Common unit test code for all unit tests of the server component."""

from tests.unit import TestCase as BaseTestCase
from tests.unit.server.mocks.dao import DataAccessMock


class TestCase(BaseTestCase):
    """Base class of server unit test cases.

    Resets the `DataAccessMock` state before each test to ensure
    test isolation.
    """

    def setUp(self):
        super().setUp()
        DataAccessMock.reset()
