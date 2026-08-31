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
"""Unit tests for the context module."""

from unittest.mock import patch

from raven.fathom.base import ApplicationContext
from raven.fathom.base import ApplicationMode
from raven.fathom.base import File
from raven.fathom.base.testing import TestEnvironment
from raven.fathom.base.context import (
    ApplicationInitializationException,
    UninitializedApplicationException,
    determine_application_mode,
    determine_working_directory,
    _ENV_VAR_ENABLED,
    _ENV_VAR_DISABLED,
    _ENV_VAR_FATHOM_TEST_MODE,
)

from tests.unit import TestCase


class TestApplicationModeDetection(TestCase):
    """Tests for top-level application mode determination."""

    def test_returns_testing_mode_when_test_env_var_is_enabled(self):
        env = TestEnvironment()
        env.env_vars[_ENV_VAR_FATHOM_TEST_MODE] = _ENV_VAR_ENABLED

        with patch(
            "raven.fathom.base.context.get_project_source_root",
            return_value=None
        ):
            mode = determine_application_mode(env)

        self.assertEqual(ApplicationMode.TESTING, mode)

    def test_returns_development_mode_when_source_root_exists(self):
        env = TestEnvironment()
        env.env_vars[_ENV_VAR_FATHOM_TEST_MODE] = _ENV_VAR_DISABLED

        with patch(
            "raven.fathom.base.context.get_project_source_root",
            return_value=File("/project"),
        ):
            mode = determine_application_mode(env)

        self.assertEqual(ApplicationMode.DEVELOPMENT, mode)

    def test_returns_production_mode_when_not_testing_and_no_source_root(self):
        env = TestEnvironment()
        env.env_vars[_ENV_VAR_FATHOM_TEST_MODE] = _ENV_VAR_DISABLED

        with patch(
            "raven.fathom.base.context.get_project_source_root",
            return_value=None
        ):
            mode = determine_application_mode(env)

        self.assertEqual(ApplicationMode.PRODUCTION, mode)


class TestWorkingDirectoryDetection(TestCase):
    """Tests for working-directory resolution by application mode."""

    def test_testing_mode_uses_build_testing_directory(self):
        src_root = File("/repo")

        with patch(
            "raven.fathom.base.context.get_project_source_root",
            return_value=src_root
        ):
            work_dir = determine_working_directory(
                TestEnvironment(),
                ApplicationMode.TESTING
            )

        expected_dir = File("/repo") / File("build/testing")
        self.assertEqual(expected_dir, work_dir)

    def test_development_mode_uses_build_devel_directory(self):
        src_root = File("/repo")

        with patch(
            "raven.fathom.base.context.get_project_source_root",
            return_value=src_root
        ):
            work_dir = determine_working_directory(
                TestEnvironment(),
                ApplicationMode.DEVELOPMENT
            )

        expected_dir = File("/repo") / File("build/devel")
        self.assertEqual(expected_dir, work_dir)

    def test_production_mode_returns_current_working_directory(self):
        env = TestEnvironment()
        work_dir = determine_working_directory(env, ApplicationMode.PRODUCTION)
        test_work_dir = env.get_current_working_directory()
        self.assertEqual(File(test_work_dir), work_dir)


class TestApplicationContext(TestCase):
    """Tests for ApplicationContext singleton and initialization behavior."""

    def setUp(self):
        super().setUp()
        ApplicationContext.delete()

    def tearDown(self):
        ApplicationContext.delete()
        super().tearDown()

    def test_create_instance_and_instance_return_same_object(self):
        created = ApplicationContext.create_instance()
        fetched = ApplicationContext.instance()

        self.assertIs(created, fetched)

    def test_create_instance_raises_when_instance_already_exists(self):
        ApplicationContext.create_instance()

        with self.assertRaises(ApplicationInitializationException) as raised:
            ApplicationContext.create_instance()

        self.assertIn("instance already exists", str(raised.exception))

    def test_instance_raises_when_no_instance_exists(self):
        with self.assertRaises(UninitializedApplicationException) as raised:
            ApplicationContext.instance()

        self.assertIn(
            "No ApplicationContext instance exists",
            str(raised.exception)
        )

    def test_initialize_sets_mode_and_working_directory(self):
        ctx = ApplicationContext.create_instance()
        work_dir = File("/context/work")

        ctx.initialize(ApplicationMode.TESTING, work_dir)

        self.assertEqual(ApplicationMode.TESTING, ctx.get_application_mode())
        self.assertEqual(File("/context/work"), ctx.get_working_directory())

    def test_initialize_twice_with_same_mode_returns_same_instance(self):
        ctx = ApplicationContext.create_instance()

        initialized = ctx.initialize(ApplicationMode.TESTING, File("/first"))
        same = ctx.initialize(ApplicationMode.TESTING, File("/second"))

        self.assertIs(initialized, same)
        self.assertEqual(File("/first"), ctx.get_working_directory())

    def test_initialize_twice_with_different_mode_raises(self):
        ctx = ApplicationContext.create_instance()
        ctx.initialize(ApplicationMode.TESTING, File("/work"))

        with self.assertRaises(ApplicationInitializationException) as raised:
            ctx.initialize(ApplicationMode.DEVELOPMENT, File("/other"))

        self.assertIn(
            "Application was already initialized",
            str(raised.exception)
        )

    def test_getters_raise_when_context_is_uninitialized(self):
        ctx = ApplicationContext.create_instance()

        with self.assertRaises(UninitializedApplicationException):
            ctx.get_application_mode()

        with self.assertRaises(UninitializedApplicationException):
            ctx.get_working_directory()

    def test_context_manager_deletes_global_instance_on_exit(self):
        with ApplicationContext.create_instance().initialize(
            ApplicationMode.TESTING,
            File("/work"),
        ):
            self.assertIsNotNone(ApplicationContext.instance())

        with self.assertRaises(UninitializedApplicationException):
            ApplicationContext.instance()


if __name__ == "__main__":
    TestCase.run_tests()
