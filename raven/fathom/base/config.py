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
"""Provides an API to manage and access application configuration values.

All application configuration is stored in `Configuration` objects.
Configuration items are key-value pairs, mapping from a `ConfigurationKey[T]`
to its configuration value of generic type `T`. Each collection of
related configurations is grouped into a `ConfigurationSection` object, which
contains the actual items. A `ConfigurationSection` object is obtained from a
particular `Configuration` by its corresponding `ConfigurationSectionKey`.

To make it easier and safer for application code to obtain the correct
configuration value, the classes in this module can also be used by to define
a complete configuration unit. A unit is defined by creating a subclass
of `ConfigurationDefinition` and setting concrete `ConfigurationSectionKey`
objects as class attributes of that definition. In turn, each concrete
`ConfigurationSectionKey` defines all configuration keys it encompasses
as class attributes. As a result, application code can refer to specific
configurations in a safe and unambiguous manner by importing the
specific configuration unit class and then simply accessing the sections keys
and config keys hierarchy.

The following is an example of a possible configuration unit:

```
class UserRole(enum.StrEnum):
    REGULAR = "regular"
    VISITOR = "visitor"
    ADMIN = "admin"

class UserSection(ConfigurationSectionKey):

    USERNAME = ConfigurationKey[str]("username", str)

    ROLE = ConfigurationKey[UserRole]("role", UserRole)

    IS_SPECIAL = ConfigurationKey[bool]("special", bool)

class AppConfig(ConfigurationDefinition):

    USER = UserSection("User")
```

Application code can then access the configuration values using those defined
keys. Given a `Configuration` object, the values can be retrieved as follows:

```
app_config: Configuration = ...
name = app_config.value_of(AppConfig.USER.USERNAME)
role = app_config[AppConfig.USER.ROLE]
if name == "admin" and role == UserRole.ADMIN:
    ...
```

In the above example, the username is obtained via the `value_of()` method
while the user role is obtained via the equivalent subscript operator.
Furthermore, type checkers can validate that the variable `name` is
of type `str` and `role` is of type `UserRole`. Note that both could also
be `None` if the configuration is not set.

All `Configuration` objects can be stored to and loaded from a textual
representation using the `ConfigurationLoader` class. Typically, this is used
to load configuration values from a file or other text source at application
startup. However, the way that application code obtains access to those loaded
configuration values is up to the application's design. Applications could
define their own ConfigurationManager class to handle configuration-specific
setup and access logic. Application code would then import and query the
ConfigurationManager class to obtain the necessary configuration values. It is
up to the application developer to ensure testability of the code.

An alternatively suggested approach is to design application classes to accept
a `Configuration` object as a parameter of their initializer. That way an
application class only depends on the `Configuration` class and an instance
can be provided from the outside, which simplifies testing. For example:
```
class MyClass:

    def __init__(self, config: Configuration):
        self._config = config
    
    def some_method_using_a_config(self):
        special_usage = self._config[AppConfig.USER.IS_SPECIAL]
        print(special_usage)
        ...
```

In the above example, the application code that uses MyClass can provide the
production-enabled configuration directly upon initialization via the
application's ConfigurationManager, or similar. In unit tests, the test case
that tests the MyClass class can directly create a `Configuration` object with
the necessary values to steer the behaviour if the class-under-test,
fully in-memory.

When loading configuration files only the .config / .cfg style file format
is supported.


#### Classes:

* `Configuration`
* `ConfigurationSection`
* `ConfigurationLoader`
* `ConfigurationDefinition`
* `ConfigurationSectionKey`
* `ConfigurationKey`

#### Exceptions:

The following diagram illustrates the exception hierarchy:

```

ConfigurationException
      |
      |-- InvalidConfigurationKeyException
      |
      |-- MissingRequiredConfigurationException
      |
      |-- DuplicateConfigurationSectionException
      |
      |-- IllegalConfigurationValueException
      |         |
      |         |-- MalformedConfigurationValueException
      |         |
      |         |-- ConfigurationValueTypeException
      |
      |-- ConfigurationReadException
      |         |
      |         |-- InvalidConfigurationFormatException
      |         |
      |         |-- DuplicateConfigurationItemException
      |
      |-- ConfigurationWriteException


```

Author: Phil Gaiser
"""

import configparser
import re
import textwrap

from io import StringIO
from typing import Type, TypeAlias, Union, Optional, cast
from typing import Generic, TypeVar, overload
from collections.abc import MutableSequence

from raven.fathom.base.typing import TypeCheck
from raven.fathom.base.logging import Logger, LogLevel
from raven.fathom.base.exceptions import FathomBaseException
from raven.fathom.base.file import File, FileSize, FileIOException


# Type aliases
ExArgSpec: TypeAlias = Union[Type[Exception], Exception]


class ConfigurationException(FathomBaseException):
    """Base class for all configuration-related exceptions."""


class InvalidConfigurationKeyException(ConfigurationException):
    """An operation was requested with an invalid or unknown
    configuration key.
    """


class MissingRequiredConfigurationException(ConfigurationException):
    """A required configuration was not found."""


class DuplicateConfigurationSectionException(ConfigurationException):
    """An attempt was made to add a section to a configuration
    which already exists.
    """


class IllegalConfigurationValueException(ConfigurationException):
    """An attempt was made to read or assign an illegal configuration value."""


class MalformedConfigurationValueException(IllegalConfigurationValueException):
    """A found concrete configuration value could not be converted from its
    textual representation to an object of the type declared by the associated
    configuration key.
    """


class ConfigurationValueTypeException(IllegalConfigurationValueException):
    """A given configuration value was specified as an object of a different
    type than the declared type of the associated configuration key.
    """


class ConfigurationReadException(ConfigurationException):
    """A configuration textual representation, either from an in-memory string
    or a file, could not be read, for whatever reason.
    """


class InvalidConfigurationFormatException(ConfigurationReadException):
    """A configuration textual representation could not be read because it
    has an invalid text format.
    """


class DuplicateConfigurationItemException(ConfigurationReadException):
    """A configuration textual representation could not be read because it
    has a duplicate configuration key within a read section, or a duplicate
    section key.
    """


class ConfigurationWriteException(ConfigurationException):
    """A configuration could not be written to a destination."""


T = TypeVar("T")


class ConfigurationDefinition:
    """A definition of a configuration unit.

    Serves as a base for defining concrete application-specific configurations.
    A configuration definition is a collection of configuration section keys,
    each of which has a unique name and contains configuration keys.
    Each section is defined by a `ConfigurationSectionKey` instance, defined
    in the scope of the concrete class. Each configuration key within each
    section is defined by a `ConfigurationKey` instance, also defined in the
    class scope.
    """

    def __init__(self, name: str):
        """Initializes a new `ConfigurationDefinition` instance.

        Args:
            name (str): The name of the configuration definition.
        """
        self._name = name

    @property
    def name(self) -> str:
        """The name of this configuration definition."""
        return self._name

    @classmethod
    def all_sections(cls) -> list["ConfigurationSectionKey"]:
        """Returns a list of all configuration section keys defined in this
        configuration definition.
        """
        return [
            attr for attr in cls.__dict__.values()
            if isinstance(attr, ConfigurationSectionKey)
        ]

    def __str__(self):
        return self._name


class _SectionKeyMeta(type):
    """Metaclass for `ConfigurationSectionKey`.

    Automatically assigns the corresponding section instance to
    all `ConfigurationKey` instances defined in the class scope.
    Many API methods of the `Configuration` class can work with only
    a `ConfigurationKey` object as a parameter, without requiring the caller
    to explicitly state the section a particular key belongs to. Internally,
    the code relies on the section being assigned to the key so that a query
    is always unambiguous. Additionally, this metaclass ensures that each
    `ConfigurationSectionKey` instance has a copy of all `ConfigurationKey`
    instances, to enable the use case of reusable configuration section keys.
    """

    def __call__(cls, *args, **kwargs):
        section_instance = super().__call__(*args, **kwargs)
        for attr_name, attr_value in cls.__dict__.items():
            if isinstance(attr_value, ConfigurationKey):
                config_key_instance = attr_value.copy()
                setattr(section_instance, attr_name, config_key_instance)
                if config_key_instance._section is not None:
                    raise ConfigurationException(
                        f"ConfigurationKey '{attr_name}' "
                        "already has a section assigned"
                    )

                config_key_instance._section = section_instance

        return section_instance


class ConfigurationSectionKey(metaclass=_SectionKeyMeta):
    """A key mapping to a `ConfigurationSection`.

    A concrete `ConfigurationSectionKey` is defined by application-specific
    code to represent a specific section of a configuration unit, including
    all the keys within that section.
    A `ConfigurationSectionKey` is usually defined as a class attribute
    of a `ConfigurationDefinition` subclass and acts as an identifier for
    a specific section.

    By default, configuration sections can only occur once within a
    configuration unit. However, when passing `repeatable` as `True` to the
    initializer of a `ConfigurationSectionKey`, it allows the section to be
    repeated multiple times within the same configuration unit.
    """

    def __init__(
        self,
        name: str,
        repeatable: bool = False,
        description: Optional[str] = None
    ):
        """Initializes a new `ConfigurationSectionKey` instance.

        Args:
            name (str): The name of the configuration section. This is used as
                the text representation of the section when reading/writing
                configuration files.
            repeatable (bool): Specifies whether the section can be repeated
                and thus occur multiple times within a configuration unit.
            description (str): A human-readable description of the
                configuration section that this key represents.
        """
        self._name = name
        self._repeatable = repeatable
        self._description = description

    @property
    def name(self) -> str:
        """The name of this configuration section."""
        return self._name

    @property
    def is_repeatable(self) -> bool:
        """Indicates whether this configuration section can be repeated
        in a configuration unit or whether it can only occur once.
        """
        return self._repeatable

    @property
    def description(self) -> Optional[str]:
        """A human-readable description of this configuration section."""
        return self._description

    @classmethod
    def all_keys(cls) -> list["ConfigurationKey"]:
        """Returns a list of all configuration keys defined in this
        configuration section.
        """
        return [
            attr for attr in cls.__dict__.values()
            if isinstance(attr, ConfigurationKey)
        ]

    def __str__(self):
        return self.name


class ConfigurationKey(Generic[T]):
    """A configuration key definition.

    A `ConfigurationKey` maps to a specific configuration value of type `T`.
    A concrete `ConfigurationKey` is usually defined by application-specific
    code as part of a `ConfigurationSectionKey` definition to represent a
    configuration key-value mapping that is semantically specific to
    the application. As such an identifier, it is usually defined as a class
    attribute of a `ConfigurationSectionKey` subclass, which automatically
    registers the key with that section. That key instance can then subsequently
    be used to access the configuration value from a `Configuration` object
    without having to explicitly reference the section. On the other hand, it
    is also possible to instantiate a `ConfigurationKey` directly on demand,
    although this is less common and less practical since not all API methods
    of the `Configuration` class support such keys when passed as an argument.

    Every type `T` is supported as a key type if `T` can be converted to and
    from `str`. The converted string value is used when writing a configuration
    to a text representation or a file. The conversion is done by passing a
    configuration value of type `T` to the initializer of the `str` class.
    Thus, user-defined types may add conversion support by implementing
    the special `__str__()` method. Conversely, a text representation of
    a configuration value is converted to the type `T` by passing the `str`
    value as an argument to the type's initializer. As an exception to this
    rule, using `FileSize` as a key type is also supported, conversions are
    handled automatically.
    """

    def __init__(
        self,
        name: str,
        key_type: Type[T],
        default: Optional[T] = None,
        description: Optional[str] = None
    ):
        """Initializes a new `ConfigurationKey` instance.

        Args:
            name (str): The name of the configuration key. This is used as
                the text representation of the key when reading/writing
                configuration files.
            key_type (Type[T]): The type of the configuration key. Must be
                convertible to/from `str`.
            default (Optional[T]): The default value of the key if queried at
                runtime and no value is present in the underlying
                configuration object. Must be an instance of `key_type`.
            description (Optional[str]): A human-readable description of the
                configuration that this key represents.
        """
        if default is not None and not isinstance(default, key_type):
            raise TypeError(
                "Argument 'default' must be an instance of 'key_type'"
            )

        self._name = name
        self._type: Type[T] = key_type
        self._default: Optional[T] = default
        self._description: Optional[str] = description
        self._section: Optional[ConfigurationSectionKey] = None

    @property
    def name(self) -> str:
        """The name of this configuration key."""
        return self._name

    @property
    def key_type(self) -> Type[T]:
        """The type of this configuration key.

        The type is the class object as specified in its declaration.
        """
        return self._type

    @property
    def default_value(self) -> Optional[T]:
        """The default value of this configuration key.

        The default value is the value that is used if no value
        is specified for this key in a configuration file or
        in a configuration section.
        May be `None` if no default value is set.
        """
        return self._default

    @property
    def description(self) -> Optional[str]:
        """The description of this configuration key.

        The description is human-readable text that describes
        the purpose of the configuration associated with this key.
        May be `None` if no description is provided.
        """
        return self._description

    @property
    def section(self) -> Optional[ConfigurationSectionKey]:
        """The section this configuration key belongs to.

        This property may be `None` if the key is not assigned to any section.
        The assignment is done automatically by the configuration
        infrastructure if the concrete `ConfigurationKey` subclass was defined
        as a class attribute of a `ConfigurationSectionKey` subclass
        definition.
        """
        return self._section

    def copy(self):
        """Creates a copy of this configuration key object."""
        return ConfigurationKey(
            name=self._name,
            key_type=self._type,
            default=self._default,
            description=self._description
        )

    def __str__(self):
        return self.name


class ConfigurationSection:
    """A section of a configuration object.

    A section has an immutable key/name and maps configuration keys to
    configuration values. Values can be queried via `value_of()` and
    mutated via `set_value()`. A section is iterable over raw key-values pairs.
    The length of a section as indicated by using the `len()` function is the
    number of configuration keys it contains.
    Implements the `in` and `[]` operators.
    """

    def __init__(
        self,
        key: ConfigurationSectionKey,
        sequence_number: Optional[int] = None
    ):
        """Initializes a new `ConfigurationSection` instance.

        The new instance is empty and has no configuration values.

        Args:
            key (ConfigurationSectionKey): The key of the new section.
            sequence_number (int): The sequence number of the
                section. Can only be set if the specified section key
                is repeatable. May be `None`.

        Raises:
            InvalidConfigurationKeyException: If the sequence number is set
                for a non-repeatable section.
        """
        TypeCheck.require_arg(key, ConfigurationSectionKey)
        self._key = key
        self._sequence_number = sequence_number
        if sequence_number is not None and not key.is_repeatable:
            raise InvalidConfigurationKeyException(
                "Cannot set sequence number "
                f"for non-repeatable section '{key.name}'"
            )

        self._configs: dict[str, str] = {}

    @property
    def key(self) -> ConfigurationSectionKey:
        """The key of this section, as a `ConfigurationSectionKey` value."""
        return self._key

    @property
    def name(self) -> str:
        """The name of this section, as a `str`."""
        return self._key.name

    @property
    def sequence_number(self) -> Optional[int]:
        """The sequence number of this section, if applicable.

        May be `None`.
        """
        return self._sequence_number

    def contains(self, key: ConfigurationKey) -> bool:
        """Indicates whether this configuration section contains an item with
        the specified key.

        Args:
            key (ConfigurationKey): The key of the configuration to check.

        Returns:
            bool: `True` if this configuration has an item with the given key,
                `False` if no such item can be found.
        """
        return key.name in self._configs

    def value_of(self, key: ConfigurationKey[T]) -> Optional[T]:
        """Obtains the configuration value associated with the specified key.

        Args:
            key (ConfigurationKey[T]): The key of the configuration
                value of type `T` to obtain.

        Returns:
            T: The configuration value associated with the specified key,
                converted to its declared type `T`. Returns the default value
                declared by the specified key if no such configuration value
                can be found, or `None` if no configuration value can be found
                for the given key and there is also no default value specified
                by that key.

        Raises:
            MalformedConfigurationValueException: If the value exists in this
                configuration but cannot be converted to the
                corresponding type `T`.
        """
        value = self.raw_value_of(key)
        if value is not None:
            value = self._convert_raw_value(key, value)

        return value if value is not None else key.default_value

    def raw_value_of(self, key: ConfigurationKey) -> Optional[str]:
        """Obtains the raw configuration value for the specified key.

        The configuration value is returned as is, without any
        type conversions. A default value as specified by the given key
        is ignored. If the key is not found, `None` is returned instead.

        Args:
            key (ConfigurationKey): The key of the raw configuration
                value to obtain.

        Returns:
            str: The raw configuration value associated with the specified key,
                as a `str`. Returns `None` if no configuration value can be
                found for the given key.
        """
        return self._configs.get(key.name)

    def set_value(self, key: ConfigurationKey[T], value: Union[str, T]):
        """Assigns a configuration value to an associated configuration key.

        Subsequent queries for the specified key will return the
        specified value. The value must be convertible to a `str`. If it is not
        passed as a `str` directly, it is checked that the value is of the
        type `T` as declared by the associated key and then converted to
        a `str`. Therefore, please note that subsequent queries for the same
        key will not receive the identical value instance back.

        The configuration value to set must not be an empty `str` or `None`.

        Args:
            key (ConfigurationKey[T]): The key of the configuration value of
                the `T` to set.
            value (T | str): The configuration value to set, either as a `str`
                or as an object of the corresponding type `T` as declared by
                the specified `ConfigurationKey`. In any case, the value must
                be convertible to a `str` object.

        Raises:
            ConfigurationValueTypeException: If `value` is neither
                a non-empty `str` nor of the type `T` as declared by
                the specified key.
        """
        if not isinstance(value, str):
            if not isinstance(value, key.key_type):
                opt_type = (
                    f"or {key.key_type.__name__} "
                    if key.key_type != str
                    else ""
                )
                raise ConfigurationValueTypeException(
                    f"Cannot assign configuration value with key '{key}'. "
                    f"Expected value of type str {opt_type}"
                    f"but found {type(value)}"
                )

            value = self._convert_to_raw(value)

        self._assign_raw_value(key, value)

    def remove(self, key: ConfigurationKey):
        """Removes the configuration value associated with the specified key.

        If the specified key does not exist in this section, this method
        has no effect.

        Args:
            key (ConfigurationKey): The key of the configuration
                key-value pair to remove.
        """
        self._configs.pop(key.name, None)

    def clear(self):
        """Removes all items from this configuration section.

        After this method is called, this `ConfigurationSection` object
        will be empty.
        """
        self._configs.clear()

    def is_empty(self) -> bool:
        """Indicates whether this configuration section is empty.
        
        Returns:
            bool: `True` if this section contains no key-value pairs,
                `False` if it contains at least one such pair.
        """
        return len(self) == 0

    def check_is_convertible_raw(
        self,
        key: ConfigurationKey,
        value: str
    ) -> bool:
        """Checks if the given raw value can be converted to the key's type.

        Args:
            key (ConfigurationKey): The key to check against.
            value (str): The string value to check.

        Returns:
            bool: `True` if the value can be converted to the key's type,
                `False` otherwise.
        """
        try:
            self._convert_raw_value(key, value)
            return True
        except MalformedConfigurationValueException:
            return False

    def copy(self) -> "ConfigurationSection":
        """Creates a full copy of this `ConfigurationSection` object.

        Returns:
            ConfigurationSection: A copy of this configuration section.
        """
        section = ConfigurationSection(self._key, self._sequence_number)
        # pylint: disable=W0212
        section._configs = self._configs.copy()
        return section

    def to_string(self, include_descriptions: bool = False) -> str:
        """Creates a string representing this configuration section.

        Args:
            include_descriptions (bool): Whether to include the section and
                key descriptions if that information is being provided by
                the corresponding key declaration.

        Returns:
            str: A string containing the data of this section
                in a configuration file format.
        """
        buffer = StringIO()
        section_name = self.name
        if self.sequence_number is not None:
            section_name += f"-{self.sequence_number}"

        buffer.write(f"[{section_name}]\n")
        if include_descriptions and self._key.description:
            descr = self._wrap_lines(self._key.description)
            buffer.write(f"# {descr}\n")

        buffer.write("\n")
        keys = self._key.all_keys()
        i = 0
        for key, value in self:
            if include_descriptions:
                self._add_description(buffer, key, keys, i > 0)

            buffer.write(f"{key}={value}\n")
            i += 1

        buffer.write("\n")
        return buffer.getvalue()

    def _add_description(self, buffer, key, config_keys, extra_nl):
        key_obj = [k for k in config_keys if k.name == key]
        if len(key_obj) == 1:
            key_obj = key_obj[0]
            if key_obj.description:
                if extra_nl:
                    buffer.write("\n")

                descr = self._wrap_lines(key_obj.description)
                buffer.write(f"# {descr}\n")

    def _wrap_lines(self, text):
        """Wraps the given text into lines with a maximum length."""
        if not text:
            return ""

        return "\n# ".join(textwrap.wrap(text, width=80))

    def _convert_raw_value(
        self,
        key: ConfigurationKey[T],
        raw_value: str
    ) -> T:
        value_type = key.key_type
        if value_type == bool:
            return cast(T, self._convert_raw_bool_value(key, raw_value))

        if value_type == FileSize:
            return cast(T, self._convert_raw_file_size_value(key, raw_value))

        try:
            return value_type(raw_value) # type: ignore
        except (TypeError, ValueError) as error:
            raise MalformedConfigurationValueException(
                f"Invalid configuration value with key '{key}'. "
                f"Cannot be converted to type {value_type.__name__}: "
                f"'{raw_value}' (Error: {error})"
            ) from None

    def _convert_raw_bool_value(self, key, raw_value):
        value = raw_value.lower()
        if value in ("true", "1", "t", "on", "yes"):
            return True
        if value in ("false", "0", "f", "off", "no"):
            return False

        raise MalformedConfigurationValueException(
            f"Invalid configuration value with key '{key}'. "
            f"Cannot be converted to bool type: "
            f"'{raw_value}' (Error: Is not a valid bool. "
            "Expected 'true' or 'false')"
        ) from None

    def _convert_raw_file_size_value(self, key, raw_value):
        try:
            return FileSize.from_string_value(raw_value)
        except ValueError as error:
            raise MalformedConfigurationValueException(
                f"Invalid configuration value with key '{key}'. "
                f"Cannot be converted to FileSize type: "
                f"'{raw_value}' (Error: {error})"
            ) from None

    def _convert_to_raw(self, value):
        if isinstance(value, bool):
            return "true" if value else "false"

        return str(value)

    def _assign_raw_value(self, key, raw_value):
        if raw_value == "":
            raise ConfigurationValueTypeException(
                f"Cannot assign configuration value with key '{key}'. "
                "Empty values of type str are illegal"
            )

        self._configs[key.name] = raw_value

    def __len__(self):
        """Returns the number of key-value pairs in this section."""
        return len(self._configs)

    def __getitem__(self, key: ConfigurationKey[T]) -> Optional[T]:
        """Same as lhs.value_of(rhs)."""
        return self.value_of(key)

    def __setitem__(self, key: ConfigurationKey[T], value: T):
        """Same as lhs.set_value(rhs)."""
        self.set_value(key, value)

    def __iter__(self):
        """Returns an iterator over all raw key-value pairs in this section.
        
        The keys are of type `str` and the values are raw values of type `str`.
        """
        return iter(self._configs.items())

    def __contains__(self, key: ConfigurationKey):
        """Same as `rhs.contains(lhs)`."""
        return self.contains(key)


class Configuration:
    """An application configuration object.

    A configuration is a collection of key-value pairs grouped
    into configuration sections. Configuration values are stored as plain
    strings but when queried are automatically converted to the correct type as
    declared by the associated key. Sections can be repeated in a concrete
    `Configuration` object, however, by default they only occur once.
    Repeatable sections are explicitly marked as such. Each section can contain
    only one value for each configuration key, but different sections can
    contain values associated with the same configuration key.

    A configuration is iterable over its sections.
    The length of a configuration as indicated by using the `len()` function
    is the number of sections it contains.
    Implements the `in` and `[]` operators.
    """

    def __init__(self):
        """Initializes a new `Configuration` instance.

        The new instance is empty and has no configuration sections.
        """
        self._sections: MutableSequence[ConfigurationSection] = []

    def has_section(self, key: ConfigurationSectionKey) -> bool:
        """Indicates whether this configuration contains the specified section.

        Args:
            key (ConfigurationSectionKey): The key of the configuration section
                to check.

        Returns:
            bool: `True` if this configuration has a section with the specified
                key, `False` if it contains no such section.
        """
        return any(section.name == key.name for section in self._sections)

    def has_value(self, key: ConfigurationKey) -> bool:
        """Indicates whether this configuration contains an item with the
        specified key.

        All sections with the same name as the section set in the specified
        config key are searched for a configuration item with
        the specified key.

        Args:
            key (ConfigurationKey): The key of the configuration to check.

        Returns:
            bool: `True` if this configuration has an item with the given key,
                in any section. `False` if no such item
                can be found in any section.

        Raises:
            InvalidConfigurationKeyException: If the key is not assigned to
                any section.
        """
        if key.section is None:
            raise InvalidConfigurationKeyException(
                f"Cannot check configuration value with key '{key}'. "
                "The key does not belong to any section"
            )

        section_name = key.section.name
        return any(
            section.name == section_name and section.contains(key)
            for section in self._sections
        )

    def contains(
        self,
        key: Union[ConfigurationSectionKey, ConfigurationKey]
    ) -> bool:
        """Indicates whether this configuration contains a given key.

        Both `ConfigurationSectionKey` items as well as `ConfigurationKey`
        items can be handled. Former is equivalent to a call to the
        `has_section()` method, latter is equivalent to a call
        to the `has_value()` method.

        Args:
            key (ConfigurationSectionKey | ConfigurationKey): The key to check.

        Returns:
            bool: `True` if this configuration has an item, either a section or
                a value within any section, with the given key.
                Returns `False` if no such item can be found anywhere.

        Raises:
            InvalidConfigurationKeyException: If the key is specified as
                a `ConfigurationKey` but is not assigned to any section.
        """
        if isinstance(key, ConfigurationSectionKey):
            return self.has_section(key)
        if isinstance(key, ConfigurationKey):
            return self.has_value(key)

        raise TypeError(
            "Invalid type for argument 'key'. "
            "Expected ConfigurationSectionKey or ConfigurationKey "
            f"but found {type(key)}"
        )

    def get_section(
        self,
        key: ConfigurationSectionKey
    ) -> ConfigurationSection:
        """Gets the section which has the specified key.

        This method will never return `None`. If this configuration does not
        contain a section with the specified key, then such a section is
        created and added to this configuration and then returned.

        Args:
            key (ConfigurationSectionKey): The key of the configuration section
                to return.

        Returns:
            ConfigurationSection: A configuration section that is part of this
                configuration object and has the specified section key.
                Never `None`.
        """
        name = key.name
        for section in self._sections:
            if section.name == name:
                return section

        section = ConfigurationSection(key)
        self.add_section(section)
        return section

    def get_repeatable_sections(
        self,
        key: ConfigurationSectionKey
    ) -> list[ConfigurationSection]:
        """Gets the section that has the specified key.

        If this configuration does not contain a section with the
        specified key, then an empty list is returned.

        Args:
            key (ConfigurationSectionKey): The key of the configuration section
                to return.

        Returns:
            list[ConfigurationSection]: A list of configuration sections that
                are part of this configuration object and have the specified
                section key. Never `None`.
        """
        name = key.name
        return [section for section in self._sections if section.name == name]

    def add_section(self, section: ConfigurationSection):
        """Adds the given section to this configuration.

        Args:
            section (ConfigurationSection): The configuration section to add.

        Raises:
            DuplicateConfigurationSectionException: If this configuration
                already contains a section with the same section key and that
                key is not marked as repeatable.
        """
        TypeCheck.require_arg(section, ConfigurationSection)
        if section.key.is_repeatable:
            if any(
                sec.sequence_number == section.sequence_number
                for sec in self.get_repeatable_sections(section.key)
            ):
                raise DuplicateConfigurationSectionException(
                    "Cannot add repeatable section to configuration: "
                    f"Section with key '{section.key}' and sequence number "
                    f"{section.sequence_number} already exists"
                )
        else:
            if self.has_section(section.key):
                raise DuplicateConfigurationSectionException(
                    "Cannot add non-repeatable section to configuration: "
                    f"Section with key '{section.key}' already exists"
                )

        self._sections.append(section)

    def remove_section(self, key: ConfigurationSectionKey):
        """Removes the section with the specified key from this configuration.

        If no such section exists in this configuration, this method
        has no effect. If the key is marked as repeatable, then all sections
        with that key are removed.

        Args:
            key (ConfigurationSectionKey): The key of the section to remove.
        """
        if self.has_section(key):
            self._sections = [
                section for section in self._sections
                if section.name != key.name
            ]

    def get_required_value(
        self,
        key: ConfigurationKey[T],
        or_raise: ExArgSpec = MissingRequiredConfigurationException
    ) -> T:
        """Gets the configuration value with the specified key.

        If the specified key has no configuration section associated with it,
        it is not automatically created and added to this `Configuration`
        object and an exception is raised instead.

        It is assumed that the specified configuration value is mandatory
        and raises the exception denoted by the `or_raise` argument if the
        configuration value or section cannot be found. If customised, the
        given `Exception` class is instantiated and its initializer must accept
        a single `str` argument as the exception message. If it is specified as
        an `Exception` instance, it is raised as is.

        Args:
            key (ConfigurationKey[T]): The key of the config value to get.
            or_raise (Exception): The type of exception to raise if the
                specified section or configuration cannot be found.
                May also be an instance of `Exception`.
                Defaults to `MissingRequiredConfigurationException`

        Returns:
            T: The configuration value of declared type `T`.

        Raises:
            InvalidConfigurationKeyException: If the specified key does not
                belong to any section.
            Exception: An exception of the specified type if the configuration
                cannot be found.
        """
        section_key = key.section
        if section_key is None:
            raise InvalidConfigurationKeyException(
                f"Cannot get required configuration value with key '{key}'. "
                "The key does not belong to any section"
            )

        if section_key.is_repeatable:
            raise InvalidConfigurationKeyException(
                f"Cannot get required configuration value with key '{key}'. "
                "The key belongs to a repeatable section, "
                "which is not supported"
            )

        config_exception = or_raise
        if not self.has_section(section_key):
            self._handle_missing_required_config(
                config_exception,
                f"Missing required configuration value with key '{key}': "
                f"Section '{section_key}' not found"
            )

        try:
            config_value = self.get_section(section_key).value_of(key)
        except MalformedConfigurationValueException as ex:
            self._handle_missing_required_config(
                config_exception,
                f"Required configuration value in section '{section_key}'"
                f" with key '{key}' has an invalid format: {ex}"
            )

        if config_value is None:
            self._handle_missing_required_config(
                config_exception,
                "Missing required configuration value "
                f"in section '{section_key}' with key '{key}'"
            )

        return config_value

    def value_of(
        self,
        key: ConfigurationKey[T],
    ) -> Optional[T]:
        """Gets the configuration value with the specified key.

        If the configuration section with the specified key cannot be found,
        it is not automatically created and added to this `Configuration`
        object and `None` is returned instead.

        Args:
            key (ConfigurationKey[T]): The key of the configuration
                value to get.

        Returns:
            T: The configuration value, converted to its declared type.
                Returns the key's default value if no configuration value can
                be found, or `None` if no configuration value can be found
                for the given key and there is also no default value specified
                by that key.

        Raises:
            InvalidConfigurationKeyException: If the specified key does not
                belong to any section.
        """
        section_key = key.section
        if section_key is None:
            raise InvalidConfigurationKeyException(
                f"Cannot get configuration value with key '{key}'. "
                "The key does not belong to any section"
            )

        if section_key.is_repeatable:
            raise InvalidConfigurationKeyException(
                f"Cannot get configuration value with key '{key}'. "
                "The key belongs to a repeatable section, "
                "which is not supported"
            )

        if not self.has_section(section_key):
            return None

        return self.get_section(section_key).value_of(key)

    def set_value(self, key: ConfigurationKey[T], value: Union[str, T]):
        """Sets the configuration value with the specified key.

        If the configuration section with the specified key cannot be found,
        it is not automatically created and added to this `Configuration`
        object and an exception is raised instead.

        Args:
            key (ConfigurationKey[T]): The key of the configuration value
                to set.
            value (T | str): The configuration value to set, either
                as a `str` or of the key's type `T`.

        Raises:
            InvalidConfigurationKeyException: If the key does not belong to
                any section, or if the associated section does not exist.
        """
        section_key = key.section
        if section_key is None:
            raise InvalidConfigurationKeyException(
                f"Cannot set configuration value with key '{key}'. "
                "The key does not belong to any section"
            )

        if section_key.is_repeatable:
            raise InvalidConfigurationKeyException(
                f"Cannot set configuration value with key '{key}'. "
                "The key belongs to a repeatable section, "
                "which is not supported"
            )

        if not self.has_section(section_key):
            raise InvalidConfigurationKeyException(
                f"Cannot set configuration value with key '{key}'. "
                f"The associated section '{section_key.name}' does not exist"
            )

        self.get_section(section_key).set_value(key, value)

    def clear(self):
        """Removes all sections from this configuration.

        After this method is called, this `Configuration` object will be empty.
        """
        self._sections.clear()

    def is_empty(self) -> bool:
        """Indicates whether this configuration is empty.

        Returns:
            bool: `True` if this configuration contains no sections,
                `False` if it contains at least one section, regardless whether
                that section is empty or not.
        """
        return len(self) == 0

    def copy(self) -> "Configuration":
        """Creates a full copy of this `Configuration` object.

        Returns:
            Configuration: A copy of this configuration.
        """
        config = Configuration()
        for section in self:
            config.add_section(section.copy())

        return config

    def to_string(self, include_descriptions: bool = False) -> str:
        """Returns a string representation of this configuration.

        Args:
            include_descriptions (bool): Whether to include descriptions of
                sections and configuration keys in the string representation
                if that information is being provided by the corresponding
                key declaration.

        Returns:
            str: A string containing the data of this `Configuration` object
                in a configuration file format.
        """
        buffer = StringIO()
        for section in self:
            buffer.write(section.to_string(include_descriptions))

        buffer.write("\n")
        return buffer.getvalue()

    def _handle_missing_required_config(self, missing_config_exception, msg):
        if isinstance(missing_config_exception, Exception):
            raise missing_config_exception from None

        raise missing_config_exception(msg) from None

    def __len__(self):
        """Returns the number of sections in this configuration."""
        return len(self._sections)

    @overload
    def __getitem__(
        self,
        key: ConfigurationSectionKey
    ) -> Optional[ConfigurationSection]:
        ...
    @overload
    def __getitem__(
        self,
        key: ConfigurationKey[T]
    ) -> Optional[T]:
        ...
    def __getitem__(self, key):
        """Same as either:

        `(lhs.has_section(rhs) and lhs.get_section(rhs)) or None`

        or:

        `lhs.value_of(rhs)`

        depending on the type of the `key` argument.
        """
        if isinstance(key, ConfigurationSectionKey):
            if not self.has_section(key):
                return None

            return self.get_section(key)

        if isinstance(key, ConfigurationKey):
            return self.value_of(key)

        raise TypeError(
            "Invalid type for argument 'key'. "
            "Expected ConfigurationSectionKey or ConfigurationKey "
            f"but found {type(key)}"
        )

    def __setitem__(self, key: ConfigurationKey[T], value: T):
        """Same as lhs.set_value(rhs) but only accepts values that are
        of the key's type, not `str` values."""
        self.set_value(key, value)

    def __iter__(self):
        """Returns an iterator over all sections in this configuration."""
        return iter(self._sections)

    def __contains__(
        self,
        key: Union[ConfigurationSectionKey, ConfigurationKey]
    ) -> bool:
        """Same as `rhs.contains(lhs)`."""
        return self.contains(key)


class ConfigurationLoader:
    """Loads configuration data from text or file sources.

    Can also be used to store configuration data back to text or file sources.
    Loading can be conducted against a known `ConfigurationDefinition` with
    optional validation and logging.
    """
    def __init__(
        self,
        definition: Optional[Type[ConfigurationDefinition]] = None,
        logger: Optional[Logger] = None,
        log_level: LogLevel = LogLevel.WARNING,
        enable_validation: bool = False
    ):
        """Initialize a new `ConfigurationLoader` instance.

        Args:
            definition (Type[ConfigurationDefinition]): The
                configuration definition to use for validation of
                the text structure, i.e. check for known sections and keys.
            logger (Logger): The logger to use for logging messages when a
                configuration contains an invalid section, key, values etc.
            log_level (LogLevel): The log level to use when logging messages.
            enable_validation (bool): Whether to enable the validation of
                configuration values against the key definition. If this is
                disabled, then a malformed config value will cause an exception
                to be raised when it is first accessed.
        """
        self._definition = definition
        self._logger = logger
        self._log_level = log_level
        self._enable_validation = enable_validation
        self._known_section_keys = None
        if self._definition is not None:
            self._known_section_keys = {
                section_key.name: section_key
                for section_key in self._definition.all_sections()
            }

    def load(self, source: Union[str, File]) -> Configuration:
        """Loads a configuration from the specified source.

        The source can be either a `str` containing the textual representation
        of the configuration or a `File` object that contains the configuration
        data in text format.

        Args:
            source (str | File): The source from which to load the
                configuration, either as a configuration text object
                or a File object.

        Returns:
            Configuration: A `Configuration` object loaded from the specified
                source.

        Raises:
            InvalidConfigurationFormatException: If the configuration source is
                formatted incorrectly.
            DuplicateConfigurationItemException: If the configuration contains
                duplicate sections or keys.
            ConfigurationReadException: If the configuration cannot be read.
        """
        if isinstance(source, str):
            return self._read_config_from_text(source)

        if isinstance(source, File):
            return self._read_config_from_file(source)

        raise TypeError(
            "Invalid type for argument 'source'. "
            f"Expected str or File but found {type(source)}"
        )

    def store(self, config: Configuration, file: File):
        """Writes the given configuration to the specified file.

        Args:
            config (Configuration): The configuration to store.
            file (File): The target file to store the configuration to.

        Raises:
            ConfigurationWriteException: If the configuration cannot be stored.
        """
        try:
            file.write_all(self.write(config))
        except FileIOException as ex:
            raise ConfigurationWriteException(
                f"Failed to write configuration to file '{file}'"
            ) from ex

    def write(self, config: Configuration) -> str:
        """Writes the given configuration to a text string.

        Args:
            config (Configuration): The configuration to write.

        Returns:
            str: The textual representation of the configuration.

        Raises:
            ConfigurationWriteException: If the configuration cannot be stored.
        """
        return config.to_string(include_descriptions=True)

    def _read_config_from_file(self, file):
        """Reads the given text file and creates a configuration from it."""
        try:
            return self._read_config_from_text(file.read_all_text())
        except FileIOException as ex:
            raise ConfigurationReadException(
                f"Failed to read configuration file '{file}'"
            ) from ex

    def _read_config_from_text(self, text):
        """Parses a text string and creates a configuration object from it."""
        try:
            parser = configparser.ConfigParser(strict=True)
            parser.read_string(text)
            return self._read_from_config_parser(parser)
        except configparser.DuplicateSectionError as error:
            raise DuplicateConfigurationItemException(
                "Duplicate configuration section found: "
                f"'{error.section}' (line {error.lineno})"
            ) from None
        except configparser.DuplicateOptionError as error:
            raise DuplicateConfigurationItemException(
                "Duplicate configuration key found "
                f"in section '{error.section}': "
                f"'{error.option}' (line {error.lineno})"
            ) from None
        except configparser.Error as error:
            raise InvalidConfigurationFormatException(
                f"Failed to read configuration data: {error}"
            ) from None

    def _read_from_config_parser(self, parser):
        config = Configuration()
        for section_name in parser.sections():
            section = self._create_section_obj(section_name)
            if section is None:
                continue

            self._read_section_data_into(parser, section)
            config.add_section(section)

        return config

    def _create_section_obj(self, section_name):
        section_key = None
        is_repeatable = False
        sequence_number = None
        seq = re.match(r"^.*-(\d+)$", section_name)
        if seq is not None:
            section_name = section_name.split("-")[0]
            sequence_number = int(seq.group(1))
            is_repeatable = True

        if self._known_section_keys is not None:
            if section_name not in self._known_section_keys:
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        f"Unknown configuration section '{section_name}' "
                        "found in configuration file. "
                        "Ignoring it."
                    )
                    return None

            section_key = self._known_section_keys[section_name]

        return ConfigurationSection(
            section_key
            if section_key is not None
            else ConfigurationSectionKey(section_name, is_repeatable),
            sequence_number
        )

    def _read_section_data_into(self, parser, section):
        section_name = section.name
        if section.sequence_number is not None:
            section_name = f"{section_name}-{section.sequence_number}"

        for key_name, value in parser.items(section_name, raw=True):
            self._read_section_value(section, key_name, value)

    def _read_section_value(self, section, key, value):
        config_key = None
        known_keys = None
        if self._definition is not None:
            known_keys = {k.name: k for k in section.key.all_keys()}
            if key not in known_keys:
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        f"Unknown configuration key '{key}' found in section "
                        f"'{section.name}'. Ignoring it."
                    )
                return
            config_key = known_keys[key]
        else:
            config_key = ConfigurationKey(key, str)

        if self._enable_validation:
            if not section.check_is_convertible_raw(config_key, value):
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        f"Malformed configuration value with key '{key}' "
                        f"in section '{section.name}': '{value}'"
                    )
                    key_type = config_key.key_type
                    self._logger.log(
                        self._log_level,
                        f"Expected value of type {key_type.__name__}"
                    )
                return

        section.set_value(config_key, value)
