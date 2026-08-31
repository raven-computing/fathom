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
"""Typing-related classes and utilities for type checking.

This module provides foundational abstractions and helper classes to support
type checking and interface-based programming patterns. It includes:

* A marker `Interface` base class for declaring interfaces with an injectable
implementation, enabling dependency injection and decoupling of code.

* The `TypeCheck` utility class, which offers static methods for enforcing
type constraints on objects, arguments, and properties, raising informative
errors when type requirements are not met.

These utilities help ensure type safety and consistency across the codebase,
while providing clear and standardized error messages.
"""

from typing import Any, Optional

from raven.fathom.base._inject import InjectableInterfaceType


class Interface(InjectableInterfaceType):
    """Base class for interface type declarations.

    This is a marker class. It is used to indicate that a user-defined class is
    a pure abstract base class, fulfilling the role of an interface.
    An interface class should not expose any fields, neither public nor
    private, and should only consist of public abstract methods. All methods of
    an interface declaration should be decorated with the `@abstractmethod`
    decorator from the standard library `abc` module.

    The `Interface` class works in conjunction with the `@inject` decorator.
    Concrete implementations of user-defined interfaces can be injected
    dynamically at runtime. Application code depends on the abstraction
    provided by an interface, while being decoupled from any concrete
    implementation. To enable this capability, the user-defined interface class
    must be decorated with the `@inject` decorator, although, this is not
    strictly necessary as users are generally free to create their own
    mechanisms of providing an implementation. Application code can then
    request an instance of a class implementing the interface by calling the
    `instance()` classmethod of the injectable interface class that the
    application code depends on.
    Please note that while it is technically possible to directly instantiate
    the interface class (which injects the implementation at the call site),
    it is recommended to use the `instance()` classmethod on the interface
    class instead. Since an interface is an `ABC`, the regular syntax looks
    like a user is trying to instantiate an abstract class, which can
    be confusing. On top of that, many linters will flag this as an error
    as they do not understand what will actually happen at runtime.

    Implementation classes must implement all methods declared by the
    interface. They do not necessarily need to provide an initialiser, however,
    if they define one it must be a default no-args initialiser.
    Implementation classes must not use custom metaclasses as this might
    conflict with the dependency injection machinery.
    """


class TypeCheck:
    """Type checking utilities."""

    @staticmethod
    def require(obj: Any, types: Any, message: Optional[str] = None):
        """Ensures that the specified object has one of the specified types.

        Args:
            obj (any): The object to check, as any object.
            types: The types to check for. May be a tuple of types.
            message (str): An optional message to use for the
                raised `TypeError` if the required type cannot be satisfied.
                May be `None`.

        Raises:
            TypeError: If the specified object is not of the required type.
        """
        if not isinstance(obj, types):
            raise TypeError(
                message or f"Expected {types} but found {type(obj)}"
            )

    @staticmethod
    def require_subclass(clazz, classes, message: Optional[str] = None):
        """Ensures that the specified class is a subclass
        of one of the specified classes.

        Args:
            clazz: The class to check, as a class type.
            classes: The classes to check for. May be a tuple of classes.
            message (str): An optional message to use for the
                raised `TypeError` if the required condition cannot be
                satisfied. May be `None`.

        Raises:
            TypeError: If the specified class is not a sublass of
                any of the specified subclasses.
        """
        if not issubclass(clazz, classes):
            raise TypeError(
                message or f"The class {clazz} is not a subclass of {classes}"
            )

    @staticmethod
    def require_arg(arg: Any, types: Any, message: Optional[str] = None):
        """Ensures that the specified object has one of the specified types.

        This method can be used by arbitrary methods throughout the code base
        to ensure that a given argument is of a specific type, or a set
        of allowed types.

        Args:
            arg (any): The object of the argument to check, as any object.
            types: The types to check for. May be a tuple of types.
            message (str): An optional message to use for the
                raised `TypeError` if the required type cannot be satisfied.
                May be `None`.

        Raises:
            TypeError: If the specified argument object is not
                of the required type.
        """
        if not isinstance(arg, types):
            raise TypeError(
                message or (
                    "Invalid argument. "
                    f"Expected {types} but found {type(arg)}"
                )
            )

    @staticmethod
    def require_prop(
        arg: Any,
        types,
        prop_name: str,
        message: Optional[str] = None
    ):
        """Ensures that the specified object has one of the specified types.

        This method can be used by property setter methods throughout the code
        base to ensure that a property value attempted to be set on an object
        is of a specific type, or a set of allowed types.

        Args:
            arg (any): The object of the argument to check, as any object.
            types: The types to check for. May be a tuple of types.
            prop_name (str): The name of the property, in
                the format `Class.property`.
            message (str): An optional message to use for the
                raised `TypeError` if the required type cannot be satisfied.
                May be `None`.

        Raises:
            TypeError: If the specified argument object is not
                of the required type.
        """
        if not isinstance(arg, types):
            raise TypeError(
                message or (
                    f"Invalid value for property {prop_name}: "
                    f"Expected {types} but found {type(arg)}"
                )
            )
