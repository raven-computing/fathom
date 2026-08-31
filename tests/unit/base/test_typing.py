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
"""Unit tests for the base typing module."""

from raven.fathom.base import TypeCheck

from tests.unit import TestCase


class TestTypeCheck(TestCase):
    """Unit tests for the `TypeCheck` class."""

    def test_require(self):
        TypeCheck.require("hello", str)
        TypeCheck.require(123, int)
        TypeCheck.require(123.45, float)
        TypeCheck.require([1, 2], list)
        TypeCheck.require((1, 2), tuple)
        TypeCheck.require({1, 2}, set)
        TypeCheck.require({"a": 1}, dict)
        TypeCheck.require(True, bool)

        TypeCheck.require("hello", (str, int))
        TypeCheck.require(123, (str, int))

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require(123, str)

        self.assertIn(
            "Expected <class 'str'> but found <class 'int'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require("hello", (int, float))

        self.assertIn(
            "Expected (<class 'int'>, <class 'float'>) "
            "but found <class 'str'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require(123, str, message="Custom message")

        self.assertEqual("Custom message", str(raised.exception))

    def test_require_subclass(self):
        class _A:
            pass

        class _B(_A):
            pass

        class _C:
            pass

        TypeCheck.require_subclass(_B, _A)
        TypeCheck.require_subclass(_B, (_A, _C))
        TypeCheck.require_subclass(_A, object)

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_subclass(_C, _A)

        self.assertIn("The class ", str(raised.exception))
        self.assertIn(
            "TestTypeCheck.test_require_subclass.<locals>._C'> ",
            str(raised.exception)
        )
        self.assertIn("is not a subclass of ", str(raised.exception))
        self.assertIn(
            "TestTypeCheck.test_require_subclass.<locals>._A'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_subclass(_C, (_B,))

        self.assertIn("The class ", str(raised.exception))
        self.assertIn(
            "TestTypeCheck.test_require_subclass.<locals>._C'> ",
            str(raised.exception)
        )
        self.assertIn("is not a subclass of ", str(raised.exception))
        self.assertIn(
            "TestTypeCheck.test_require_subclass.<locals>._B'>,)",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_subclass(_C, _A, message="Custom message")

        self.assertEqual("Custom message", str(raised.exception))

    def test_require_arg(self):
        TypeCheck.require_arg("hello", str)
        TypeCheck.require_arg(123, int)

        TypeCheck.require_arg("hello", (str, int))
        TypeCheck.require_arg(123, (str, int))

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_arg(123, str)

        self.assertIn(
            "Invalid argument. "
            "Expected <class 'str'> but found <class 'int'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_arg("hello", (int, float))

        self.assertIn(
            "Invalid argument. "
            "Expected (<class 'int'>, <class 'float'>) "
            "but found <class 'str'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_arg(123, str, message="Custom message")

        self.assertEqual("Custom message", str(raised.exception))

    def test_require_prop(self):
        TypeCheck.require_prop("hello", str, "MyClass.my_prop")
        TypeCheck.require_prop(123, int, "MyClass.my_prop")

        TypeCheck.require_prop("hello", (str, int), "MyClass.my_prop")
        TypeCheck.require_prop(123, (str, int), "MyClass.my_prop")

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_prop(123, str, "MyClass.my_prop")

        self.assertIn(
            "Invalid value for property MyClass.my_prop: "
            "Expected <class 'str'> but found <class 'int'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_prop("hello", (int, float), "MyClass.my_prop")

        self.assertIn(
            "Invalid value for property MyClass.my_prop: "
            "Expected (<class 'int'>, <class 'float'>) "
            "but found <class 'str'>",
            str(raised.exception)
        )

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_prop(
                123,
                str,
                "MyClass.my_prop",
                message="Custom message"
            )

        self.assertEqual("Custom message", str(raised.exception))

        with self.assertRaises(TypeError) as raised:
            TypeCheck.require_prop(123, str, "MyClass.my_prop")

        self.assertIn(
            "Invalid value for property MyClass.my_prop",
            str(raised.exception)
        )


if __name__ == "__main__":
    TestCase.run_tests()
