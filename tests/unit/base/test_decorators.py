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
"""Unit tests for the decorators defined in the decorators package."""

import io
import contextlib

from raven.fathom.base.decorators import noexcept
from raven.fathom.base.decorators import singleton
from raven.fathom.base.decorators import inject
from raven.fathom.base.typing import Interface

from tests.unit import TestCase


FLAG_SINGLETON_CLASS_INSTANTIATED = False


@singleton
class _SingletonClass:

    def __init__(self):
        # pylint: disable=global-statement
        global FLAG_SINGLETON_CLASS_INSTANTIATED
        if FLAG_SINGLETON_CLASS_INSTANTIATED:
            raise AssertionError(
                "SingletonClass must only be instantiated once"
            )

        self.attribute = 1
        FLAG_SINGLETON_CLASS_INSTANTIATED = True


class TestSingleton(TestCase):
    """Tests for the singleton class decorator."""

    def setUp(self):
        pass

    def test_singleton_class_can_be_instantiated(self):
        instance = _SingletonClass()
        self.assertEqual(instance.attribute, 1)

    def test_can_be_instantiated_only_once(self):
        instance_a = _SingletonClass()
        instance_b = _SingletonClass()
        instance_c = _SingletonClass()
        instance_d = _SingletonClass()
        self.assertTrue(instance_a is instance_b is instance_c is instance_d)
        self.assertEqual(instance_a.attribute, 1)
        self.assertEqual(instance_b.attribute, 1)
        self.assertEqual(instance_c.attribute, 1)
        self.assertEqual(instance_d.attribute, 1)

    def test_deleting_all_instance_refs(self):
        instance_a = _SingletonClass()
        instance_a_id = id(instance_a)
        del instance_a
        instance_b = _SingletonClass()
        instance_b_id = id(instance_b)
        del instance_b
        instance_c = _SingletonClass()
        instance_c_id = id(instance_c)
        del instance_c
        instance_d = _SingletonClass()
        instance_d_id = id(instance_d)
        del instance_d
        self.assertTrue(instance_a_id == instance_b_id)
        self.assertTrue(instance_b_id == instance_c_id)
        self.assertTrue(instance_c_id == instance_d_id)


class TestNoexcept(TestCase):
    """Tests for the noexcept function decorator."""

    def test_custom_handler_is_called(self):
        state = {
            "called": False,
            "func_name": None,
            "error": None,
        }

        def custom_handler(func, ex):
            state["called"] = True
            state["func_name"] = func.__name__
            state["error"] = str(ex)
            raise ValueError("custom-handler-called")

        @noexcept(handler=custom_handler)
        def a_decorated_function():
            raise RuntimeError("test-error")

        with self.assertRaises(ValueError) as raised:
            result = a_decorated_function()

            self.assertIsNone(result)
            self.assertTrue(state["called"])
            self.assertEqual(state["func_name"], "a_decorated_function")
            self.assertEqual(state["error"], "test-error")


        self.assertIsInstance(raised.exception, ValueError)
        self.assertIn("custom-handler-called", str(raised.exception))

    def test_default_handler_exits_on_exception(self):

        @noexcept
        def _raises():
            raise RuntimeError("test-error")

        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            with self.assertRaises(SystemExit) as raised:
                _raises()

        self.assertEqual(str(raised.exception), "126")
        self.assertIn(
            "Error: Function _raises() raised an unexpected exception "
            "of type RuntimeError",
            stderr_buffer.getvalue()
        )
        self.assertIn("test-error", stderr_buffer.getvalue())


class TestInject(TestCase):
    """Tests for the inject class decorator."""

    def test_inject_on_non_interface_raises_type_error(self):
        with self.assertRaises(TypeError):
            @inject # type: ignore
            class _NotAnInterface:
                pass

    def test_inject_on_interface_succeeds(self):
        @inject
        class _MyTestInterface(Interface):
            pass

        self.assertEqual("_MyTestInterface", _MyTestInterface.__name__)
        self.assertTrue(issubclass(_MyTestInterface, Interface))


if __name__ == "__main__":
    TestCase.run_tests()
