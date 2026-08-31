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
"""Common unit test code."""

from raven.fathom.base import Dependencies
from raven.fathom.base import ApplicationMode
from raven.fathom.base import ApplicationContext
from raven.fathom.base import File

from tests.common import FathomTestCase, FathomTestFixture


class TestCase(FathomTestCase):
    """Base class of unit test cases."""

    def setUp(self):
        Dependencies.enable_object_store()
        Dependencies.flush_object_store()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        Dependencies.disable_object_store()


class TestFixture(FathomTestFixture):
    """Base class for all test fixtures used in unit tests."""

    def setUp(self):
        super().setUp()
        File.get_file_system().flush_system()
        self.app_context = ApplicationContext.create_instance()
        self.app_context.initialize(ApplicationMode.TESTING, File("/"))

    def tearDown(self):
        super().tearDown()
        ApplicationContext.delete()
