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
"""Provides the `@inject` class decorator."""

from typing import TypeVar, Type
from abc import ABCMeta

from raven.fathom.base.provider import Dependencies, Context
from raven.fathom.base._inject import InjectableInterfaceType


class _Injectable(ABCMeta):
    """Metaclass to handle dependency injection.

    Inherits from `ABCMeta` to allow an injectable definition to be
    an implementation of an abstract base class.
    """

    def __call__(cls, *args, **kwargs):
        return Dependencies.inject_class_instance(
            cls, Context.get_calling_context(), *args, **kwargs # type: ignore
        )


I = TypeVar("I", bound=InjectableInterfaceType)


def inject(cls: Type[I]) -> Type[I]:
    """Class decorator enabling a class implementation injection.

    Class declarations decorated with `@inject` will have their implementations
    injected at runtime. This allows the user of a class to use the syntax of
    class instantiation directly with the declaration he wishes to use, while
    automatically being provided with an appropriate implementation of that
    interface. This enables the use of dependency injection.

    Classes decorated with `@inject` must be abstract base classes,
    specifically by inheriting from the `Interface` class.
    """
    if not issubclass(cls, InjectableInterfaceType):
        raise TypeError(
            f"Injectable {cls} must be an interface type"
        )

    # Here we don't actually check that cls is itself abstract. A concrete
    # subclass of Interface (one that has implemented all abstract methods)
    # would be successfully decorated, which makes no semantic sense. Should
    # this be allowed nonetheless? Should the decorator also assert that cls
    # is itself abstract?

    class _InjectableType(cls, metaclass=_Injectable):
        pass

    _InjectableType.__name__ = cls.__name__
    _InjectableType.__qualname__ = cls.__qualname__
    _InjectableType.__module__ = cls.__module__
    _InjectableType.__doc__ = cls.__doc__
    _InjectableType.__annotations__ = cls.__annotations__
    return _InjectableType # type: ignore
