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
"""Unit tests for the config module."""

import platform

from raven.fathom.base import Configuration, ConfigurationKey
from raven.fathom.base import ConfigurationSection, ConfigurationSectionKey
from raven.fathom.base import ConfigurationDefinition
from raven.fathom.base import ConfigurationLoader
from raven.fathom.base import ConfigurationValueTypeException
from raven.fathom.base import MissingRequiredConfigurationException
from raven.fathom.base import DuplicateConfigurationSectionException
from raven.fathom.base import ConfigurationReadException
from raven.fathom.base import ConfigurationWriteException
from raven.fathom.base import DuplicateConfigurationItemException
from raven.fathom.base import InvalidConfigurationKeyException
from raven.fathom.base import InvalidConfigurationFormatException
from raven.fathom.base import Logger, LogLevel
from raven.fathom.base import File, FileIOException

from tests.unit import TestCase
from tests.unit.mocks import Mock


FILE_PATH_ENTRY = (
    "path\\to\\default"
    if platform.system() == "Windows"
    else "path/to/default"
)


class FakeConfigSectionA(ConfigurationSectionKey):
    """Configuration section (A) for testing purposes."""

    CONFIG_KEY_A = ConfigurationKey[str](
        "my.config.key.a", str
    )

    CONFIG_KEY_B = ConfigurationKey[bool](
        "my.config.key.b", bool
    )


class FakeConfigSectionB(ConfigurationSectionKey):
    """Configuration section (B) for testing purposes."""

    CONFIG_KEY_A = ConfigurationKey[int](
        "my.config.key.a", int, default=42,
        description="Description for my.config.key.a",
    )

    CONFIG_KEY_B = ConfigurationKey[str](
        "my.config.key.b", str, default="my_default_value",
        description="Description for my.config.key.b",
    )


class FakeConfigSectionC(ConfigurationSectionKey):
    """Configuration section (C) for testing purposes."""

    CONFIG_KEY_A = ConfigurationKey[File](
        "my.config.key.a", File, default=File(FILE_PATH_ENTRY),
    )


class FakeTestConfig(ConfigurationDefinition):
    """Configuration definition for testing purposes."""

    SECTION_A = FakeConfigSectionA(
        name="My-Section-A", description="Description for My-Section-A"
    )

    SECTION_B = FakeConfigSectionB(
        "My-Section-B", description="Description for My-Section-B"
    )

    SECTION_C = FakeConfigSectionC("My-Section-C", repeatable=True)


# The ground truth configuration text equivalent
# to the `FakeTestConfig` definition.
TEST_CONFIG_TEXT = f"""
[My-Section-A]
# Description for My-Section-A

my.config.key.a=Some string value
my.config.key.b=true

[My-Section-B]
# Description for My-Section-B

# Description for my.config.key.a
my.config.key.a=42

# Description for my.config.key.b
my.config.key.b=my_default_value

[My-Section-C]

my.config.key.a={FILE_PATH_ENTRY}

"""


class TestConfigurationDefinition(TestCase):
    """Unit tests for the `ConfigurationDefinition` class."""

    def test_definition_name(self):
        name = "My-Test-Configuration-Name"
        definition = FakeTestConfig(name)
        self.assertEqual(definition.name, name)

    def test_definition_str(self):
        name = "My-Test-Configuration-Name"
        definition = FakeTestConfig(name)
        self.assertEqual(str(definition), name)

    def test_definition_get_all_sections(self):
        sections = FakeTestConfig.all_sections()
        self.assertIsInstance(sections, list)
        self.assertEqual(len(sections), 3)
        self.assertIs(sections[0], FakeTestConfig.SECTION_A)
        self.assertIs(sections[1], FakeTestConfig.SECTION_B)
        self.assertIs(sections[2], FakeTestConfig.SECTION_C)


class TestConfigurationSectionKey(TestCase):
    """Unit tests for the `ConfigurationSectionKey` class."""

    def test_section_key_name(self):
        key = FakeTestConfig.SECTION_A
        self.assertEqual(key.name, "My-Section-A")

    def test_section_key_repeatable_default(self):
        key = FakeTestConfig.SECTION_A
        self.assertFalse(key.is_repeatable)

    def test_section_key_repeatable_true(self):
        key = FakeTestConfig.SECTION_C
        self.assertTrue(key.is_repeatable)

    def test_section_key_description(self):
        key = FakeTestConfig.SECTION_A
        self.assertEqual(key.description, "Description for My-Section-A")
        key = FakeTestConfig.SECTION_B
        self.assertEqual(key.description, "Description for My-Section-B")

    def test_section_key_description_none(self):
        key = FakeTestConfig.SECTION_C
        self.assertIsNone(key.description)

    def test_get_all_keys_from_section(self):
        section = FakeTestConfig.SECTION_A
        keys = section.all_keys()
        self.assertIsInstance(keys, list)
        self.assertEqual(len(keys), 2)
        self.assertIs(keys[0], FakeConfigSectionA.CONFIG_KEY_A)
        self.assertIsNot(keys[0], section.CONFIG_KEY_A)
        self.assertIs(keys[1], FakeConfigSectionA.CONFIG_KEY_B)
        self.assertIsNot(keys[1], section.CONFIG_KEY_B)
        # Check different identities
        section = FakeTestConfig.SECTION_B
        keys = section.all_keys()
        self.assertIsInstance(keys, list)
        self.assertEqual(len(keys), 2)
        self.assertIs(keys[0], FakeConfigSectionB.CONFIG_KEY_A)
        self.assertIsNot(keys[0], section.CONFIG_KEY_A)
        self.assertIs(keys[1], FakeConfigSectionB.CONFIG_KEY_B)
        self.assertIsNot(keys[1], section.CONFIG_KEY_B)
        keys = FakeConfigSectionC.all_keys()
        self.assertIsInstance(keys, list)
        self.assertEqual(len(keys), 1)
        self.assertIs(keys[0], FakeConfigSectionC.CONFIG_KEY_A)

    def test_all_keys_returns_empty_list_for_section_without_keys(self):
        class _EmptySection(ConfigurationSectionKey):
            pass

        keys = _EmptySection.all_keys()
        self.assertIsInstance(keys, list)
        self.assertEqual(keys, [])


class TestConfigurationKey(TestCase):
    """Unit tests for the `ConfigurationKey` class."""

    def test_init_with_valid_args(self):
        key = ConfigurationKey[str](
            name="test.key",
            key_type=str,
            default="abc",
            description="desc"
        )
        self.assertEqual(key.name, "test.key")
        self.assertIs(key.key_type, str)
        self.assertEqual(key.default_value, "abc")
        self.assertEqual(key.description, "desc")
        self.assertIsNone(key.section)

    def test_init_without_default_and_description(self):
        key = ConfigurationKey[int]("test.key", int)
        self.assertEqual(key.name, "test.key")
        self.assertIs(key.key_type, int)
        self.assertIsNone(key.default_value)
        self.assertIsNone(key.description)
        self.assertIsNone(key.section)

    def test_init_with_wrong_default_type_raises(self):
        with self.assertRaises(TypeError) as raised:
            ConfigurationKey("test.key", int, default="not-an-int")

        self.assertIn(
            "Argument 'default' must be an instance of 'key_type'",
            str(raised.exception)
        )

    def test_copy_returns_new_instance_with_same_values(self):
        key = ConfigurationKey(
            "test.key", str,
            default="abc", description="desc"
        )
        key_copy = key.copy()
        self.assertIsNot(key, key_copy)
        self.assertEqual(key_copy.name, key.name)
        self.assertIs(key_copy.key_type, key.key_type)
        self.assertEqual(key_copy.default_value, key.default_value)
        self.assertEqual(key_copy.description, key.description)
        self.assertIsNone(key_copy.section)

    def test_str_returns_name(self):
        key = ConfigurationKey("test.key", str)
        self.assertEqual(str(key), "test.key")

    def test_can_get_section_from_config_key(self):
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_B
        section = key.section
        self.assertIsInstance(section, ConfigurationSectionKey)
        self.assertIs(section, FakeTestConfig.SECTION_B)

    def test_getting_section_from_non_assigned_key_returns_none(self):
        key = ConfigurationKey("test.key", str)
        self.assertIsNone(key.section)


class TestConfigurationSection(TestCase):
    """Unit tests for the `ConfigurationSection` class."""

    def setUp(self):
        self.section_key = FakeTestConfig.SECTION_A
        self.config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        self.config_key_b = FakeTestConfig.SECTION_A.CONFIG_KEY_B

    def test_create_new_configuration_section(self):
        key = self.section_key
        section = ConfigurationSection(key)
        self.assertEqual(section.key, key)
        self.assertEqual(section.name, key.name)
        self.assertIsNone(section.sequence_number)
        self.assertTrue(section.is_empty())

    def test_create_new_repeatable_configuration_section(self):
        key = FakeTestConfig.SECTION_C
        section = ConfigurationSection(key, sequence_number=2)
        self.assertEqual(section.key, key)
        self.assertEqual(section.name, key.name)
        self.assertEqual(section.sequence_number, 2)
        self.assertTrue(section.is_empty())

    def test_creating_non_repeatable_section_with_seq_number_raises_ex(self):
        key = self.section_key
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            ConfigurationSection(key, sequence_number=2)

        self.assertIn(
            "Cannot set sequence number for non-repeatable section",
            str(raised.exception)
        )

    def test_creating_new_configuration_section_with_wrong_arg_raises_ex(self):
        str_key_name = self.section_key.name
        with self.assertRaises(TypeError) as raised:
            ConfigurationSection(str_key_name) # type: ignore

        self.assertIn(
            "Invalid argument",
            str(raised.exception)
        )
        self.assertIn(
            "Expected "
            "<class 'raven.fathom.base.config.ConfigurationSectionKey'> "
            "but found <class 'str'>",
            str(raised.exception)
        )

    def test_section_contains_key(self):
        key = self.section_key
        section = ConfigurationSection(key)
        self.assertFalse(section.contains(self.config_key_a))
        section.set_value(
            key=self.config_key_a,
            value="/testing/work-dir"
        )
        self.assertTrue(section.contains(self.config_key_a))

    def test_contains_operator(self):
        key = self.section_key
        section = ConfigurationSection(key)
        self.assertFalse(self.config_key_a in section)
        section.set_value(self.config_key_a, "my-dir")
        self.assertTrue(self.config_key_a in section)

    def test_value_of(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        self.assertIsNone(section.value_of(key))
        value = "my-dir"
        section.set_value(key, value)
        self.assertIsInstance(section.value_of(key), str)
        self.assertEqual(section.value_of(key), value)

    def test_value_of_returns_default_of_key_if_no_value_set(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_B)
        key = FakeConfigSectionB.CONFIG_KEY_A
        self.assertIsInstance(section.value_of(key), int)
        self.assertEqual(section.value_of(key), key.default_value)

    def test_raw_value_of(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        self.assertIsNone(section.raw_value_of(key))
        value = "/testing/my/work-dir"
        section.set_value(key, value)
        self.assertIsInstance(section.raw_value_of(key), str)
        self.assertEqual(section.raw_value_of(key), value)
        section.set_value(key, str(File(value)))
        self.assertIsInstance(section.raw_value_of(key), str)

    def test_raw_value_of_returns_none_if_no_value_set(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_B)
        key = FakeConfigSectionB.CONFIG_KEY_A
        self.assertIsNone(section.raw_value_of(key))

    def test_set_initial_value_from_str(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        str_value = "/testing/my/work-dir"
        section.set_value(key, str_value)
        self.assertEqual(section.raw_value_of(key), str_value)

    def test_set_initial_value_from_custom_type(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_B)
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_A
        value = 555
        section.set_value(key, value)
        self.assertEqual(section.value_of(key), value)
        self.assertEqual(section.raw_value_of(key), str(value))

    def test_assign_new_value_to_existing_key_from_str(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        initial_value = str(File("/testing/my/work-dir"))
        section.set_value(key, initial_value)
        new_value = str(File("/something/else"))
        section.set_value(key, new_value)
        self.assertEqual(section.raw_value_of(key), new_value)
        self.assertEqual(section.value_of(key), File(new_value))

    def test_assign_new_value_to_existing_key_from_custom_type(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_B)
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_A
        initial_value = 888
        section.set_value(key, initial_value)
        new_value = 999
        section.set_value(key, new_value)
        self.assertEqual(section.raw_value_of(key), str(new_value))
        self.assertEqual(section.value_of(key), new_value)

    def test_setting_value_of_wrong_type_raises_exception(self):
        section = ConfigurationSection(self.section_key)
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_A
        float_value = 12.345
        with self.assertRaises(ConfigurationValueTypeException) as raised:
            section.set_value(key, float_value) # type: ignore

        self.assertIn(
            "Cannot assign configuration value with key 'my.config.key.a'. "
            "Expected value of type str or int "
            "but found <class 'float'>",
            str(raised.exception)
        )

    def test_setting_empty_str_value_raises_exception(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        empty_str_value = ""
        with self.assertRaises(ConfigurationValueTypeException) as raised:
            section.set_value(key, empty_str_value)

        self.assertIn(
            "Cannot assign configuration value with key 'my.config.key.a'. "
            "Empty values of type str are illegal",
            str(raised.exception)
        )

    def test_setting_none_value_raises_exception(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        with self.assertRaises(ConfigurationValueTypeException) as raised:
            section.set_value(key, None) # type: ignore

        self.assertIn(
            "Cannot assign configuration value with key 'my.config.key.a'. "
            "Expected value of type str but found <class 'NoneType'>",
            str(raised.exception)
        )

    def test_remove_existing_key(self):
        section = ConfigurationSection(self.section_key)
        section.set_value(self.config_key_a, "testing")
        section.set_value(self.config_key_b, True)
        self.assertTrue(section.contains(self.config_key_a))
        self.assertTrue(section.contains(self.config_key_b))
        section.remove(self.config_key_a)
        self.assertFalse(section.contains(self.config_key_a))
        self.assertTrue(section.contains(self.config_key_b))

    def test_remove_nonexistent_key_does_nothing(self):
        section = ConfigurationSection(self.section_key)
        section.set_value(self.config_key_a, "testing")
        section.remove(self.config_key_b)
        self.assertTrue(section.contains(self.config_key_a))
        self.assertFalse(section.is_empty())
        self.assertEqual(len(section), 1)

    def test_remove_key_twice_is_idempotent(self):
        section = ConfigurationSection(self.section_key)
        section.set_value(self.config_key_a, "testing")
        section.set_value(self.config_key_b, True)
        section.remove(self.config_key_b)
        section.remove(self.config_key_b)
        self.assertTrue(section.contains(self.config_key_a))
        self.assertFalse(section.is_empty())
        self.assertEqual(len(section), 1)

    def test_clear(self):
        section = ConfigurationSection(self.section_key)
        section.set_value(self.config_key_a, "/testing/my/work-dir")
        self.assertFalse(section.is_empty())
        section.clear()
        self.assertTrue(section.is_empty())
        self.assertEqual(len(section), 0)

    def test_is_empty(self):
        section = ConfigurationSection(self.section_key)
        self.assertTrue(section.is_empty())
        key = self.config_key_a
        section.set_value(key, "/testing/my/work-dir")
        self.assertFalse(section.is_empty())

    def test_check_is_convertible_raw_valid_int(self):
        section = ConfigurationSection(self.section_key)
        key_int = ConfigurationKey[int]("test.config.key", int)
        self.assertTrue(section.check_is_convertible_raw(key_int, "1234"))

    def test_check_is_convertible_raw_invalid_int(self):
        section = ConfigurationSection(self.section_key)
        key_int = ConfigurationKey[int]("test.config.key", int)
        self.assertFalse(
            section.check_is_convertible_raw(key_int, "not-an-int")
        )

    def test_check_is_convertible_raw_valid_str(self):
        section = ConfigurationSection(self.section_key)
        key_str = ConfigurationKey[str]("test.config.key", str)
        self.assertTrue(
            section.check_is_convertible_raw(key_str, "some string")
        )

    def test_check_is_convertible_raw_empty_str(self):
        # Empty string is convertible to str, but may be illegal for set_value
        section = ConfigurationSection(self.section_key)
        key_str = ConfigurationKey[str]("test.config.key", str)
        self.assertTrue(section.check_is_convertible_raw(key_str, ""))

    def test_check_is_convertible_raw_valid_bool_true(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_A)
        key_bool = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        self.assertTrue(section.check_is_convertible_raw(key_bool, "true"))
        self.assertTrue(section.check_is_convertible_raw(key_bool, "Yes"))
        self.assertTrue(section.check_is_convertible_raw(key_bool, "1"))

    def test_check_is_convertible_raw_valid_bool_false(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_A)
        key_bool = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        self.assertTrue(section.check_is_convertible_raw(key_bool, "false"))
        self.assertTrue(section.check_is_convertible_raw(key_bool, "No"))
        self.assertTrue(section.check_is_convertible_raw(key_bool, "0"))

    def test_check_is_convertible_raw_invalid_bool(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_A)
        key_bool = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        self.assertFalse(
            section.check_is_convertible_raw(key_bool, "notabool")
        )
        self.assertFalse(section.check_is_convertible_raw(key_bool, "123"))

    def test_check_is_convertible_raw_valid_custom_type(self):
        section = ConfigurationSection(self.section_key)
        key_file = ConfigurationKey[File]("test.config.key", File)
        self.assertTrue(
            section.check_is_convertible_raw(key_file, "/tmp/testfile")
        )

    def test_check_is_convertible_raw_invalid_float_type(self):
        section = ConfigurationSection(self.section_key)
        key_float = ConfigurationKey[float]("test.config.key", float)
        self.assertFalse(section.check_is_convertible_raw(key_float, "12,45"))

    def test_check_is_convertible_raw_valid_float_for_int(self):
        section = ConfigurationSection(self.section_key)
        key_int = ConfigurationKey[int]("test.config.key", int)
        self.assertFalse(section.check_is_convertible_raw(key_int, "1.23"))

    def test_copy_section_obj(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        value = "/testing/my/work-dir"
        section.set_value(key, value)
        clone = section.copy()
        self.assertIsNot(section, clone)
        self.assertEqual(len(section), len(clone))
        self.assertTrue(key in clone)
        self.assertEqual(clone.raw_value_of(key), value)
        section.set_value(key, "/a/different/value")
        self.assertEqual(clone.raw_value_of(key), value)
        new_value = "/something/else"
        clone.set_value(key, new_value)
        self.assertEqual(clone.raw_value_of(key), new_value)

    def test_copy_preserves_sequence_number_for_repeatable_section(self):
        section_key = FakeTestConfig.SECTION_C
        section = ConfigurationSection(section_key, sequence_number=7)
        key = FakeTestConfig.SECTION_C.CONFIG_KEY_A
        value = File("/tmp/testfile")
        section.set_value(key, value)

        clone = section.copy()

        self.assertIsNot(section, clone)
        self.assertEqual(clone.key, section_key)
        self.assertEqual(clone.sequence_number, 7)
        self.assertEqual(clone.raw_value_of(key), str(value))

    def test_section_to_string(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        value = "/testing/my/work-dir"
        section.set_value(key, value)
        string = section.to_string()
        self.assertEqual(
            string,
            "[My-Section-A]\n\nmy.config.key.a=/testing/my/work-dir\n\n"
        )

    def test_section_to_string_with_comments(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_B)
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_A
        value = "some-string-value"
        section.set_value(key, value)
        string = section.to_string(include_descriptions=True)
        self.assertEqual(
            string,
            "[My-Section-B]\n"
            "# Description for My-Section-B\n\n"
            "# Description for my.config.key.a\n"
            "my.config.key.a=some-string-value\n\n"
        )

    def test_section_to_string_with_long_comments_and_line_wrap(self):
        char_a = "A "
        char_b = "B "
        key = ConfigurationKey[int](
            name="my.key",
            key_type=int,
            description=f"{char_b}" * 125
        )
        class _MySectionKey(ConfigurationSectionKey):
            K = key

        sec_key = _MySectionKey(
            name="My-Section-Key",
            description=f"{char_a}" * 120
        )
        section = ConfigurationSection(sec_key)
        value = 42
        section.set_value(key, value)
        string = section.to_string(include_descriptions=True)
        self.assertEqual(
            string,
            "[My-Section-Key]\n"
            f"# {char_a * 39}A\n"
            f"# {char_a * 39}A\n"
            f"# {char_a * 39}A\n"
            "\n"
            f"# {char_b * 39}B\n"
            f"# {char_b * 39}B\n"
            f"# {char_b * 39}B\n"
            f"# {char_b * 4}B\n"
            "my.key=42\n\n"
        )

    def test_len(self):
        section = ConfigurationSection(self.section_key)
        self.assertEqual(len(section), 0)
        key = self.config_key_a
        section.set_value(key, "/testing/my/work-dir")
        self.assertEqual(len(section), 1)
        section.set_value(key, "different/value")
        self.assertEqual(len(section), 1)
        section.remove(key)
        self.assertEqual(len(section), 0)

    def test_getitem(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        self.assertIsNone(section[key])
        value = "/testing/my/work-dir"
        section.set_value(key, value)
        self.assertEqual(section[key], value)
        key = self.config_key_b
        value = True
        section.set_value(key, value)
        self.assertEqual(section[key], value)

    def test_setitem(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        self.assertIsNone(section.raw_value_of(key))
        value = "/testing/my/work-dir"
        section[key] = value
        self.assertEqual(section.raw_value_of(key), value)
        value = "different/value"
        section[key] = value
        self.assertEqual(section.raw_value_of(key), value)

    def test_iterator(self):
        section = ConfigurationSection(self.section_key)
        key = self.config_key_a
        raw_value = "/testing/my/work-dir"
        section.set_value(key, raw_value)
        for iter_key, iter_value in section:
            self.assertEqual(iter_key, key.name)
            self.assertEqual(iter_value, raw_value)


class TestConfiguration(TestCase):
    """Unit tests for the `Configuration` class."""

    def setUp(self):
        self.section_key_a = FakeTestConfig.SECTION_A
        self.section_key_b = FakeTestConfig.SECTION_B
        self.config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        self.config_value = "/testing/my/work/dir"
        self.empty_section = ConfigurationSection(self.section_key_a)
        self.section_1 = self.empty_section.copy()
        self.section_1.set_value(self.config_key_a, self.config_value)
        self.section_2 = ConfigurationSection(self.section_key_b)

    def test_create_new_empty_configuration(self):
        config = Configuration()
        self.assertTrue(config.is_empty())

    def test_has_section(self):
        config = Configuration()
        self.assertFalse(config.has_section(self.section_key_a))
        config.add_section(self.section_1)
        self.assertTrue(config.has_section(self.section_key_a))

    def test_has_value(self):
        config = Configuration()
        self.assertFalse(config.has_value(self.config_key_a))
        config.add_section(self.section_1)
        self.assertTrue(config.has_value(self.config_key_a))

    def test_contains_configuration_section_key(self):
        config = Configuration()
        self.assertFalse(config.contains(self.section_key_a))
        self.assertFalse(config.contains(self.config_key_a))
        config.add_section(self.empty_section)
        self.assertTrue(config.contains(self.section_key_a))
        self.assertFalse(config.contains(self.config_key_a))

    def test_contains_configuration_key(self):
        config = Configuration()
        self.assertFalse(config.contains(self.section_key_a))
        self.assertFalse(config.contains(self.config_key_a))
        config.add_section(self.section_1)
        self.assertTrue(config.contains(self.config_key_a))

    def test_in_operator_section_key(self):
        config = Configuration()
        self.assertFalse(self.section_key_a in config)
        self.assertFalse(self.config_key_a in config)
        config.add_section(self.empty_section)
        self.assertTrue(self.section_key_a in config)
        self.assertFalse(self.config_key_a in config)

    def test_in_operator_configuration_key(self):
        config = Configuration()
        self.assertFalse(self.section_key_a in config)
        self.assertFalse(self.config_key_a in config)
        config.add_section(self.section_1)
        self.assertTrue(self.config_key_a in config)

    def test_contains_invalid_arg_raises_exception(self):
        config = Configuration()
        with self.assertRaises(TypeError) as raised:
            config.contains("Test") # type: ignore

        self.assertIn(
            "Invalid type for argument 'key'. "
            "Expected ConfigurationSectionKey or ConfigurationKey "
            "but found <class 'str'>",
            str(raised.exception)
        )

    def test_get_existing_section(self):
        config = Configuration()
        config.add_section(self.empty_section)
        section = config.get_section(self.section_key_a)
        self.assertIs(section, self.empty_section)

    def test_get_nonexistent_section_adds_new_section(self):
        config = Configuration()
        section = config.get_section(self.section_key_a)
        self.assertIsNotNone(section)
        self.assertIsInstance(section, ConfigurationSection)
        self.assertEqual(section.key, self.section_key_a)
        self.assertTrue(section.is_empty())

    def test_get_repeatable_sections_returns_empty_list_when_no_sections(self):
        config = Configuration()
        section_key = FakeTestConfig.SECTION_C
        sections = config.get_repeatable_sections(section_key)
        self.assertIsInstance(sections, list)
        self.assertEqual(sections, [])

    def test_get_repeatable_sections_returns_all_sec_with_matching_name(self):
        config = Configuration()
        section_key = FakeTestConfig.SECTION_C
        section1 = ConfigurationSection(section_key, sequence_number=1)
        section2 = ConfigurationSection(section_key, sequence_number=2)
        config.add_section(section1)
        config.add_section(section2)
        sections = config.get_repeatable_sections(section_key)
        self.assertIsInstance(sections, list)
        self.assertEqual(len(sections), 2)
        self.assertIn(section1, sections)
        self.assertIn(section2, sections)

    def test_get_repeatable_sections_returns_only_sec_with_matching_name(self):
        config = Configuration()
        section_key = FakeTestConfig.SECTION_C
        non_repeatable_key = FakeTestConfig.SECTION_A
        section1 = ConfigurationSection(section_key, sequence_number=1)
        section2 = ConfigurationSection(section_key, sequence_number=2)
        other_section = ConfigurationSection(non_repeatable_key)
        config.add_section(section1)
        config.add_section(section2)
        config.add_section(other_section)
        sections = config.get_repeatable_sections(section_key)
        self.assertIsInstance(sections, list)
        self.assertEqual(len(sections), 2)
        self.assertIn(section1, sections)
        self.assertIn(section2, sections)
        self.assertNotIn(other_section, sections)

    def test_get_repeatable_sections_ret_empty_list_when_key_not_found(self):
        config = Configuration()
        fake_key = FakeConfigSectionC(
            "Nonexistent-Section", repeatable=True
        )
        sections = config.get_repeatable_sections(fake_key)
        self.assertIsInstance(sections, list)
        self.assertEqual(sections, [])

    def test_add_section(self):
        config = Configuration()
        config.add_section(self.empty_section)
        self.assertEqual(len(config), 1)
        self.assertTrue(config.has_section(self.section_key_a))

    def test_adding_section_that_already_exists_raises_exception(self):
        config = Configuration()
        config.add_section(self.empty_section)
        with self.assertRaises(
            DuplicateConfigurationSectionException
        ) as raised:
            config.add_section(self.section_1)

        self.assertIn(
            "Cannot add non-repeatable section to configuration: "
            f"Section with key '{self.section_1.key}' already exists",
            str(raised.exception)
        )

    def test_adding_section_of_invalid_type_raises_exception(self):
        config = Configuration()
        with self.assertRaises(TypeError) as raised:
            config.add_section("Test") # type: ignore

        self.assertIn(
            "Invalid argument. "
            f"Expected {ConfigurationSection} but found <class 'str'>",
            str(raised.exception)
        )

    def test_can_add_repeatable_section_with_unique_sequence(self):
        repeatable_key = FakeTestConfig.SECTION_C
        section1 = ConfigurationSection(repeatable_key, sequence_number=1)
        section2 = ConfigurationSection(repeatable_key, sequence_number=2)
        config = Configuration()
        config.add_section(section1)
        config.add_section(section2)
        sections = config.get_repeatable_sections(repeatable_key)
        self.assertIsInstance(sections, list)
        self.assertEqual(len(sections), 2)
        self.assertIn(section1, sections)
        self.assertIn(section2, sections)

    def test_add_repeatable_section_with_duplicate_sequence_raises(self):
        repeatable_key = FakeTestConfig.SECTION_C
        section1 = ConfigurationSection(repeatable_key, sequence_number=1)
        config = Configuration()
        config.add_section(section1)
        duplicate = ConfigurationSection(repeatable_key, sequence_number=1)
        with self.assertRaises(
            DuplicateConfigurationSectionException
        ) as raised:
            config.add_section(duplicate)

        self.assertIn(
            "Cannot add repeatable section to configuration",
            str(raised.exception)
        )
        self.assertIn(
            f"Section with key '{section1.key}' and sequence number "
            "1 already exists",
            str(raised.exception)
        )

    def test_remove_existing_section(self):
        config = Configuration()
        config.add_section(self.section_1)
        self.assertTrue(config.has_section(self.section_key_a))
        config.remove_section(self.section_key_a)
        self.assertFalse(config.has_section(self.section_key_a))
        self.assertEqual(len(config), 0)

    def test_remove_nonexistent_section_does_nothing(self):
        config = Configuration()
        config.add_section(self.section_1)
        self.assertTrue(config.has_section(self.section_key_a))
        # Remove a section that does not exist
        config.remove_section(self.section_key_b)
        self.assertTrue(config.has_section(self.section_key_a))
        self.assertEqual(len(config), 1)

    def test_remove_section_when_multiple_sections_are_present(self):
        config = Configuration()
        config.add_section(self.section_1)
        config.add_section(self.section_2)
        config.remove_section(self.section_key_a)
        self.assertFalse(config.has_section(self.section_key_a))
        self.assertTrue(config.has_section(self.section_key_b))
        self.assertEqual(len(config), 1)

    def test_remove_section_with_invalid_type_raises(self):
        config = Configuration()
        config.add_section(self.section_1)
        with self.assertRaises(AttributeError):
            config.remove_section("should-not-be-a-string") # type: ignore

    def test_get_required_value(self):
        config = Configuration()
        config.add_section(self.section_1)
        value = config.get_required_value(self.config_key_a)
        self.assertIsInstance(value, str)
        self.assertEqual(value, self.config_value)

    def test_get_required_value_with_missing_section_raises_default_ex(self):
        config = Configuration()
        with self.assertRaises(
            MissingRequiredConfigurationException
        ) as raised:
            config.get_required_value(self.config_key_a)

        self.assertIn(
            "Missing required configuration value "
            f"with key '{self.config_key_a}': "
            f"Section '{self.section_key_a}' not found",
            str(raised.exception)
        )

    def test_get_required_val_with_missing_section_raises_custom_ex_type(self):
        config = Configuration()
        with self.assertRaises(ValueError) as raised:
            config.get_required_value(self.config_key_a, or_raise=ValueError)

        self.assertIn(
            "Missing required configuration value "
            f"with key '{self.config_key_a}': "
            f"Section '{self.section_key_a}' not found",
            str(raised.exception)
        )

    def test_get_req_val_with_missing_section_raises_custom_ex_instance(self):
        config = Configuration()
        with self.assertRaises(ValueError) as raised:
            config.get_required_value(
                self.config_key_a,
                or_raise=ValueError("My Custom Message")
            )

        self.assertIn("My Custom Message", str(raised.exception))

    def test_get_required_value_with_missing_key_raises_default_ex(self):
        config = Configuration()
        config.add_section(self.empty_section)
        with self.assertRaises(
            MissingRequiredConfigurationException
        ) as raised:
            config.get_required_value(self.config_key_a)

        self.assertIn(
            "Missing required configuration value "
            f"in section '{self.section_key_a}' "
            f"with key '{self.config_key_a}'",
            str(raised.exception)
        )

    def test_get_required_value_with_missing_key_raises_custom_ex_type(self):
        config = Configuration()
        config.add_section(self.empty_section)
        with self.assertRaises(ValueError) as raised:
            config.get_required_value(self.config_key_a, or_raise=ValueError)

        self.assertIn(
            "Missing required configuration value "
            f"in section '{self.section_key_a}' "
            f"with key '{self.config_key_a}'",
            str(raised.exception)
        )

    def test_get_req_value_with_missing_key_raises_custom_ex_instance(self):
        config = Configuration()
        config.add_section(self.empty_section)
        with self.assertRaises(ValueError) as raised:
            config.get_required_value(
                self.config_key_a,
                or_raise=ValueError("My Custom Message")
            )

        self.assertIn("My Custom Message", str(raised.exception))

    def test_get_malformed_required_value_raises_default_exception(self):
        config = Configuration()
        key = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        invalid_bool = "Not-a-Valid-Bool"
        self.empty_section.set_value(key, invalid_bool)
        config.add_section(self.empty_section)
        with self.assertRaises(
            MissingRequiredConfigurationException
        ) as raised:
            config.get_required_value(key)

        self.assertIn(
            f"Required configuration value in section '{self.section_key_a}' "
            f"with key '{key}' has an invalid format: "
            f"Invalid configuration value with key '{key}'. "
            "Cannot be converted to bool type: "
            f"'{invalid_bool}' (Error: Is not a valid bool. "
            "Expected 'true' or 'false')",
            str(raised.exception)
        )

    def test_get_malformed_req_value_raises_custom_ex_type(self):
        config = Configuration()
        key = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        invalid_bool = "Not-a-Valid-Bool"
        self.empty_section.set_value(key, invalid_bool)
        config.add_section(self.empty_section)
        with self.assertRaises(ValueError) as raised:
            config.get_required_value(key, or_raise=ValueError)

        self.assertIn(
            f"Required configuration value in section '{self.section_key_a}' "
            f"with key '{key}' has an invalid format: "
            f"Invalid configuration value with key '{key}'. "
            "Cannot be converted to bool type: "
            f"'{invalid_bool}' (Error: Is not a valid bool. "
            "Expected 'true' or 'false')",
            str(raised.exception)
        )

    def test_get_malformed_req_value_raises_custom_ex_instance(self):
        config = Configuration()
        key = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        self.empty_section.set_value(key, "Not-a-Valid-Bool")
        config.add_section(self.empty_section)
        with self.assertRaises(ValueError) as raised:
            config.get_required_value(
                key, or_raise=ValueError("My Custom Message")
            )

        self.assertIn("My Custom Message", str(raised.exception))

    def test_get_required_value_raises_if_key_has_no_section(self):
        config = Configuration()
        key = ConfigurationKey("test.key", str)
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.get_required_value(key)

        self.assertIn(
            "The key does not belong to any section",
            str(raised.exception)
        )

    def test_get_required_value_raises_if_section_is_repeatable(self):
        config = Configuration()
        key = FakeTestConfig.SECTION_C.CONFIG_KEY_A
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.get_required_value(key)

        self.assertIn(
            "The key belongs to a repeatable section, which is not supported",
            str(raised.exception)
        )

    def test_value_of_returns_none_when_is_section_not_present(self):
        key = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        config = Configuration()
        value = config.value_of(key)
        self.assertIsNone(value)

    def test_value_of_returns_value_when_present(self):
        section_key = FakeTestConfig.SECTION_A
        config_key = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        value = "/testing/my/work-dir"
        config = Configuration()
        section.set_value(config_key, value)
        config.add_section(section)
        result = config.value_of(config_key)
        self.assertEqual(result, value)

    def test_value_of_raises_if_key_has_no_section(self):
        config = Configuration()
        key = ConfigurationKey("test.key", str)
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.value_of(key)

        self.assertIn(
            "The key does not belong to any section",
            str(raised.exception)
        )

    def test_value_of_raises_if_section_is_repeatable(self):
        config = Configuration()
        key = FakeTestConfig.SECTION_C.CONFIG_KEY_A
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.value_of(key)

        self.assertIn(
            "The key belongs to a repeatable section, which is not supported",
            str(raised.exception)
        )

    def test_value_of_returns_default_if_no_value_set(self):
        section = ConfigurationSection(FakeTestConfig.SECTION_B)
        config = Configuration()
        config.add_section(section)
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_A
        value = config.value_of(key)
        self.assertEqual(value, key.default_value)

    def test_set_value_sets_value_when_section_exists(self):
        section_key = FakeTestConfig.SECTION_A
        config_key = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        config_value = "/testing/my/work/dir"
        section = ConfigurationSection(section_key)
        config = Configuration()
        config.add_section(section)
        config.set_value(config_key, config_value)
        self.assertEqual(
            config.get_section(section_key).raw_value_of(config_key),
            config_value
        )

    def test_set_value_raises_exception_when_section_does_not_exist(self):
        section_key = FakeTestConfig.SECTION_A
        config_key = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        config_value = "/testing/my/work/dir"
        config = Configuration()
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.set_value(config_key, config_value)

        self.assertIn(
            f"Cannot set configuration value with key '{config_key.name}'. "
            f"The associated section '{section_key.name}' does not exist",
            str(raised.exception)
        )

    def test_set_value_raises_if_key_has_no_section(self):
        config = Configuration()
        key = ConfigurationKey("test.key", str)
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.set_value(key, "value")

        self.assertIn(
            "The key does not belong to any section",
            str(raised.exception)
        )

    def test_set_value_raises_if_section_is_repeatable(self):
        config = Configuration()
        key = FakeTestConfig.SECTION_C.CONFIG_KEY_A
        with self.assertRaises(InvalidConfigurationKeyException) as raised:
            config.set_value(key, File("/tmp/test"))

        self.assertIn(
            "The key belongs to a repeatable section, which is not supported",
            str(raised.exception)
        )

    def test_clear(self):
        config = Configuration()
        config.add_section(self.section_1)
        config.clear()
        self.assertEqual(len(config), 0)
        self.assertTrue(config.is_empty())

    def test_is_empty(self):
        config = Configuration()
        self.assertTrue(config.is_empty())
        config.add_section(self.empty_section)
        self.assertFalse(config.is_empty())

    def test_copy_configuration_obj(self):
        config = Configuration()
        config.add_section(self.section_1)
        clone = config.copy()
        self.assertIsNot(config, clone)
        self.assertEqual(len(config), len(clone))
        self.assertTrue(self.section_key_a in clone)
        section = clone.get_section(self.section_key_a)
        self.assertEqual(
            section.value_of(self.config_key_a),
            self.config_value
        )
        new_value = "/a/different/value"
        section.set_value(self.config_key_a, new_value)
        self.assertEqual(section.value_of(self.config_key_a), new_value)
        section = config.get_section(self.section_key_a)
        new_value = "/something/else"
        section.set_value(self.config_key_a, new_value)
        self.assertEqual(section.raw_value_of(self.config_key_a), new_value)

    def test_copy_preserves_sequence_numbers_for_repeatable_sections(self):
        config = Configuration()
        section_key = FakeTestConfig.SECTION_C
        key = FakeTestConfig.SECTION_C.CONFIG_KEY_A
        section_1 = ConfigurationSection(section_key, sequence_number=1)
        section_1.set_value(key, File("/tmp/file1"))
        section_2 = ConfigurationSection(section_key, sequence_number=2)
        section_2.set_value(key, File("/tmp/file2"))
        config.add_section(section_1)
        config.add_section(section_2)

        clone = config.copy()

        copied_sections = clone.get_repeatable_sections(section_key)
        self.assertEqual(len(copied_sections), 2)
        self.assertEqual(copied_sections[0].sequence_number, 1)
        self.assertEqual(copied_sections[1].sequence_number, 2)
        self.assertEqual(
            copied_sections[0].raw_value_of(key),
            str(File("/tmp/file1"))
        )
        self.assertEqual(
            copied_sections[1].raw_value_of(key),
            str(File("/tmp/file2"))
        )

    def test_configuration_to_string(self):
        config = Configuration()
        config.add_section(self.section_1)
        section_2 = ConfigurationSection(FakeTestConfig.SECTION_B)
        section_2.set_value(
            FakeTestConfig.SECTION_B.CONFIG_KEY_A, 123
        )
        config.add_section(section_2)
        string = config.to_string()
        self.assertEqual(
            string,
            "[My-Section-A]\n\nmy.config.key.a=/testing/my/work/dir\n\n"
            "[My-Section-B]\n\nmy.config.key.a=123\n\n\n"
        )

    def test_configuration_to_string_with_comments(self):
        config = Configuration()
        config.add_section(self.section_1)
        section_2 = ConfigurationSection(FakeTestConfig.SECTION_B)
        section_2.set_value(
            FakeTestConfig.SECTION_B.CONFIG_KEY_A, 123
        )
        config.add_section(section_2)
        string = config.to_string(include_descriptions=True)
        self.assertEqual(
            string,
            "[My-Section-A]\n"
            "# Description for My-Section-A\n"
            "\n"
            "my.config.key.a=/testing/my/work/dir\n"
            "\n"
            "[My-Section-B]\n"
            "# Description for My-Section-B\n"
            "\n"
            "# Description for my.config.key.a\n"
            "my.config.key.a=123\n\n\n"
        )

    def test_len(self):
        config = Configuration()
        self.assertEqual(len(config), 0)
        config.add_section(self.empty_section)
        self.assertEqual(len(config), 1)
        config.clear()
        self.assertEqual(len(config), 0)

    def test_getitem_for_sections(self):
        config = Configuration()
        self.assertIsNone(config[self.section_key_a])
        config.add_section(self.empty_section)
        self.assertIsInstance(config[self.section_key_a], ConfigurationSection)
        config.clear()
        config.add_section(self.section_1)
        self.assertIs(config[self.section_key_a], self.section_1)

    def test_getitem_for_config_keys(self):
        config = Configuration()
        self.assertIsNone(config[self.config_key_a])
        config.add_section(self.section_1)
        self.assertIsInstance(config[self.config_key_a], str)
        self.assertEqual(config[self.config_key_a], self.config_value)
        key = FakeTestConfig.SECTION_B.CONFIG_KEY_A
        config.add_section(
            ConfigurationSection(FakeTestConfig.SECTION_B)
        )
        self.assertIsInstance(config[key], int)
        self.assertEqual(config[key], key.default_value)

    def test_getitem_invalid_type_raises_ex(self):
        config = Configuration()
        with self.assertRaises(TypeError):
            _ = config[123]  # type: ignore

    def test_setitem_sets_value_of_correct_type(self):
        section_key = FakeTestConfig.SECTION_A
        config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        value = "testing_value"
        section[config_key_a] = value
        self.assertEqual(section.raw_value_of(config_key_a), value)
        self.assertEqual(section[config_key_a], value)

    def test_setitem_sets_bool_value(self):
        section_key = FakeTestConfig.SECTION_A
        config_key_b = FakeTestConfig.SECTION_A.CONFIG_KEY_B
        section = ConfigurationSection(section_key)
        section[config_key_b] = True
        self.assertEqual(section[config_key_b], True)
        section[config_key_b] = False
        self.assertEqual(section[config_key_b], False)

    def test_setitem_overwrites_existing_value(self):
        section_key = FakeTestConfig.SECTION_A
        config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        section[config_key_a] = "testing_value_1"
        section[config_key_a] = "testing_value_2"
        self.assertEqual(section[config_key_a], "testing_value_2")

    def test_setitem_raises_for_wrong_type(self):
        section_key = FakeTestConfig.SECTION_A
        config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        with self.assertRaises(ConfigurationValueTypeException):
            section[config_key_a] = 123  # type: ignore

    def test_setitem_raises_for_none(self):
        section_key = FakeTestConfig.SECTION_A
        config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        with self.assertRaises(ConfigurationValueTypeException):
            section[config_key_a] = None  # type: ignore

    def test_setitem_raises_for_empty_str(self):
        section_key = FakeTestConfig.SECTION_A
        config_key_a = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        with self.assertRaises(ConfigurationValueTypeException):
            section[config_key_a] = ""

    def test_setitem_with_custom_type(self):
        section_key = FakeTestConfig.SECTION_C
        key = FakeTestConfig.SECTION_C.CONFIG_KEY_A
        section = ConfigurationSection(section_key)
        value = File("/tmp/testfile")
        section[key] = value
        self.assertEqual(section[key], value)

    def test_iterator(self):
        config = Configuration()
        config.add_section(self.section_1)
        for section in config:
            self.assertIs(section, self.section_1)


class TestConfigurationLoader(TestCase):
    """Unit tests for the `ConfigurationLoader` class."""

    def setUp(self):
        cfg = Configuration()
        cfg.add_section(ConfigurationSection(FakeTestConfig.SECTION_A))
        cfg[FakeTestConfig.SECTION_A.CONFIG_KEY_A] = "Some string value"
        cfg[FakeTestConfig.SECTION_A.CONFIG_KEY_B] = True
        cfg.add_section(ConfigurationSection(FakeTestConfig.SECTION_B))
        cfg[FakeTestConfig.SECTION_B.CONFIG_KEY_A] = 42
        cfg[FakeTestConfig.SECTION_B.CONFIG_KEY_B] = "my_default_value"
        sec_c = ConfigurationSection(FakeTestConfig.SECTION_C)
        sec_c[FakeTestConfig.SECTION_C.CONFIG_KEY_A] = File("path/to/default")
        cfg.add_section(sec_c)
        self.config_obj = cfg
        self.config_text = TEST_CONFIG_TEXT
        self.config_file = File("/tmp/test_config_file.config")
        self.config_file.write_all(self.config_text)
        self.logger_mock = Mock(spec_set=Logger)

    def assert_configuration_equal(
        self,
        config_1: Configuration,
        config_2: Configuration
    ):
        """Asserts that two `Configuration` objects have the same content."""
        self.assertIsInstance(config_1, Configuration)
        self.assertIsInstance(config_2, Configuration)
        self.assertEqual(len(config_1), len(config_2))
        for section_1 in config_1:
            self.assertTrue(config_2.has_section(section_1.key))
            section_2 = config_2.get_section(section_1.key)
            self.assertEqual(len(section_1), len(section_2))
            section_1_values = dict(section_1)
            section_2_values = dict(section_2)
            self.assertDictEqual(section_1_values, section_2_values)

    def test_load_from_text(self):
        loader = ConfigurationLoader()
        config = loader.load(self.config_text)
        self.assertIsInstance(config, Configuration)
        self.assert_configuration_equal(config, self.config_obj)

    def test_load_from_file(self):
        loader = ConfigurationLoader()
        config = loader.load(self.config_file)
        self.assertIsInstance(config, Configuration)
        self.assert_configuration_equal(config, self.config_obj)

    def test_load_invalid_type_raises(self):
        loader = ConfigurationLoader()
        with self.assertRaises(TypeError):
            loader.load(123)  # type: ignore

    def test_load_and_store(self):
        loader = ConfigurationLoader(FakeTestConfig)
        config = loader.load(self.config_text)
        out_file = self.config_file.with_suffix(".out")
        loader.store(config, out_file)
        written = out_file.read_all_text()
        self.assertEqual(written.strip(), self.config_text.strip())

    def test_write_returns_string(self):
        loader = ConfigurationLoader()
        config = loader.load(self.config_text)
        result = loader.write(config)
        self.assertIsInstance(result, str)
        self.assertIn("[My-Section-A]", result)

    def test_store_wraps_file_io_exception(self):
        loader = ConfigurationLoader()
        file_mock = Mock(spec_set=File)
        file_mock.write_all.side_effect = FileIOException(None, "write failed")

        with self.assertRaises(ConfigurationWriteException) as raised:
            loader.store(self.config_obj, file_mock)

        self.assertIn(
            "Failed to write configuration to file",
            str(raised.exception)
        )

    def test__read_config_from_file_reads(self):
        loader = ConfigurationLoader()
        config = loader.load(self.config_file)
        self.assertIsInstance(config, Configuration)
        section = config.get_section(ConfigurationSectionKey("My-Section-A"))
        self.assertEqual(
            section.raw_value_of(ConfigurationKey("my.config.key.b", str)),
            "true"
        )

    def test_trying_to_load_nonexistent_file_raises_exception(self):
        loader = ConfigurationLoader()
        file = File("/tmp/does_not_exist.config")
        with self.assertRaises(ConfigurationReadException) as raised:
            loader.load(file)

        self.assertIn(
            "Failed to read configuration file",
            str(raised.exception)
        )

    def test_loading_config_with_unknown_key_is_logged(self):
        self.config_obj.clear()
        section = ConfigurationSection(FakeTestConfig.SECTION_A)
        section[ConfigurationKey("unknown.key", str)] = "value"
        self.config_obj.add_section(section)
        config_text = ConfigurationLoader().write(self.config_obj)
        loader = ConfigurationLoader(
            definition=FakeTestConfig,
            logger=self.logger_mock
        )
        config_obj = loader.load(config_text)
        self.assertIsInstance(config_obj, Configuration)
        self.assertEqual(len(config_obj), 1)
        self.assertTrue(config_obj.has_section(FakeTestConfig.SECTION_A))
        self.assertTrue(
            config_obj.get_section(FakeTestConfig.SECTION_A).is_empty()
        )
        self.logger_mock.log.assert_called_once()
        log_lvl = self.logger_mock.log.call_args.args[0]
        log_msg = self.logger_mock.log.call_args.args[1]
        self.assertIsInstance(log_lvl, LogLevel)
        self.assertEqual(log_lvl, LogLevel.WARNING)
        self.assertIsInstance(log_msg, str)
        self.assertIn("Unknown configuration key", log_msg)

    def test_loading_config_with_unknown_section_key_is_logged(self):
        self.config_obj.clear()
        known_section_key = FakeTestConfig.SECTION_A
        known_config_key = FakeTestConfig.SECTION_A.CONFIG_KEY_A
        known_section = ConfigurationSection(known_section_key)
        known_section[known_config_key] = "value"
        self.config_obj.add_section(known_section)
        unknown_section = ConfigurationSection(
            ConfigurationSectionKey("Unknown.Section")
        )
        unknown_section[ConfigurationKey(known_config_key.name, str)] = "value"
        self.config_obj.add_section(unknown_section)
        config_text = ConfigurationLoader().write(self.config_obj)
        loader = ConfigurationLoader(
            definition=FakeTestConfig,
            logger=self.logger_mock
        )
        config_obj = loader.load(config_text)
        self.assertIsInstance(config_obj, Configuration)
        self.assertEqual(len(config_obj), 1)
        self.assertTrue(config_obj.has_section(known_section_key))
        self.assertEqual(config_obj.value_of(known_config_key), "value")
        self.logger_mock.log.assert_called_once()
        log_lvl = self.logger_mock.log.call_args.args[0]
        log_msg = self.logger_mock.log.call_args.args[1]
        self.assertIsInstance(log_lvl, LogLevel)
        self.assertEqual(log_lvl, LogLevel.WARNING)
        self.assertIsInstance(log_msg, str)
        self.assertIn("Unknown configuration section", log_msg)

    def test_validating_config_with_invalid_value_is_logged(self):
        self.config_obj.clear()
        section = ConfigurationSection(FakeTestConfig.SECTION_A)
        section.set_value(FakeTestConfig.SECTION_A.CONFIG_KEY_A, "valid-value")
        section.set_value(FakeTestConfig.SECTION_A.CONFIG_KEY_B, "not-a-bool")
        self.config_obj.add_section(section)
        config_text = ConfigurationLoader().write(self.config_obj)
        loader = ConfigurationLoader(
            definition=FakeTestConfig,
            logger=self.logger_mock,
            enable_validation=True,
        )
        config_obj = loader.load(config_text)
        self.assertIsInstance(config_obj, Configuration)
        self.assertEqual(len(config_obj), 1)
        self.assertTrue(config_obj.has_section(FakeTestConfig.SECTION_A))
        self.assertEqual(
            len(config_obj.get_section(FakeTestConfig.SECTION_A)), 1
        )
        self.assertEqual(
            config_obj.value_of(FakeTestConfig.SECTION_A.CONFIG_KEY_A),
            "valid-value"
        )
        self.assertGreaterEqual(self.logger_mock.log.call_count, 2)
        log_call_1 = self.logger_mock.log.call_args_list[0]
        log_call_2 = self.logger_mock.log.call_args_list[1]
        log_lvl = log_call_1.args[0]
        log_msg = log_call_1.args[1]
        self.assertIsInstance(log_lvl, LogLevel)
        self.assertEqual(log_lvl, LogLevel.WARNING)
        self.assertIsInstance(log_msg, str)
        self.assertIn("Malformed configuration value", log_msg)
        log_lvl = log_call_2.args[0]
        log_msg = log_call_2.args[1]
        self.assertIsInstance(log_lvl, LogLevel)
        self.assertEqual(log_lvl, LogLevel.WARNING)
        self.assertIsInstance(log_msg, str)
        self.assertIn("Expected value of type bool", log_msg)

    def test_logger_uses_set_log_level_when_logging(self):
        self.config_obj.clear()
        section = ConfigurationSection(FakeTestConfig.SECTION_A)
        section[ConfigurationKey("unknown.key", str)] = "value"
        self.config_obj.add_section(section)
        config_text = ConfigurationLoader().write(self.config_obj)
        loader = ConfigurationLoader(
            definition=FakeTestConfig,
            logger=self.logger_mock,
            log_level=LogLevel.ERROR
        )
        loader.load(config_text)
        self.logger_mock.log.assert_called_once()
        log_lvl = self.logger_mock.log.call_args.args[0]
        log_msg = self.logger_mock.log.call_args.args[1]
        self.assertIsInstance(log_lvl, LogLevel)
        self.assertEqual(log_lvl, LogLevel.ERROR)
        self.assertIsInstance(log_msg, str)
        self.assertIn("Unknown configuration key", log_msg)

    def test_loading_config_with_duplicate_config_key_raises_exception(self):
        config_text = r"""
[My-Section-A]
my.config.key.b=true
my.config.key.b=false
"""
        loader = ConfigurationLoader(
            definition=FakeTestConfig
        )
        with self.assertRaises(DuplicateConfigurationItemException) as raised:
            loader.load(config_text)

        self.assertIn(
            "Duplicate configuration key found",
            str(raised.exception)
        )

    def test_loading_config_with_duplicate_section_key_raises_exception(self):
        config_text = r"""
[My-Section-A]
my.config.key.b=true

[My-Section-A]
my.config.key.b=false
"""
        loader = ConfigurationLoader(
            definition=FakeTestConfig
        )
        with self.assertRaises(DuplicateConfigurationItemException) as raised:
            loader.load(config_text)

        self.assertIn(
            "Duplicate configuration section found",
            str(raised.exception)
        )

    def test_loading_malformed_config_missing_section_raises_exception(self):
        config_text = r"""
my.config.key.b=true

[My-Section-A]
my.config.key.b=false
"""
        loader = ConfigurationLoader()
        with self.assertRaises(InvalidConfigurationFormatException) as raised:
            loader.load(config_text)

        self.assertIn(
            "Failed to read configuration data",
            str(raised.exception)
        )

    def test_loading_malformed_config_key_raises_exception(self):
        config_text = r"""
[My-Section-A]
my.config.key.a=value
=false
"""
        loader = ConfigurationLoader()
        with self.assertRaises(InvalidConfigurationFormatException) as raised:
            loader.load(config_text)

        self.assertIn(
            "Failed to read configuration data",
            str(raised.exception)
        )


if __name__ == "__main__":
    TestCase.run_tests()
