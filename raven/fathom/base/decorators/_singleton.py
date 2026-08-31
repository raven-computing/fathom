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
"""Provides the `@singleton` class decorator."""

from typing import TypeVar, Type
from threading import Lock


class _SingletonAllocator(type):
    """Metaclass to handle the allocation of singleton class instances.

    Keeps track of all instantiated singleton classes within the underlying
    application process and ensures that subsequent instantiations return
    the previously allocated instance.
    """

    _INSTANCES = dict()
    _LOCK = Lock()

    @classmethod
    def _singleton_purge(mcs):
        """Clears all singleton instances, allowing them to be re-instantiated.

        WARNING:
        This method should be used with caution as it can lead to unexpected
        behaviour if any code holds references to the previously allocated
        singleton instances. It is intended to only be called in a testing
        environment.
        """
        with mcs._LOCK:
            mcs._INSTANCES.clear()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._INSTANCES:
            with cls._LOCK:
                if cls not in cls._INSTANCES:
                    instance = super(_SingletonAllocator, cls).__call__(
                        *args, **kwargs
                    )
                    cls._INSTANCES[cls] = instance

        return cls._INSTANCES[cls]


T = TypeVar("T")


def singleton(cls: Type[T]) -> Type[T]:
    """Class decorator marking a class definition as a singleton.

    Classes decorated with `@singleton` are guaranteed to only ever be
    instantiated at most once. Users of such a class can still instantiate
    it with regular syntax, i.e. by calling the class object:

    ```
    @singleton
    class MySingletonClass:
        pass

    my_instance = MySingletonClass()
    other_instance = MySingletonClass()

    assert my_instance is other_instance  # True
    ```

    However, a singleton class will have its instantiation intercepted so that
    the very first instantiation is executed normally but subsequent attempts
    to instantiate the class will always return the first instance.
    Thus, please note that singletons are never finalized.
    """
    class _SingletonType(cls, metaclass=_SingletonAllocator):
        pass

    _SingletonType.__name__ = cls.__name__
    _SingletonType.__qualname__ = cls.__qualname__
    _SingletonType.__module__ = cls.__module__
    _SingletonType.__doc__ = cls.__doc__
    _SingletonType.__annotations__ = cls.__annotations__
    return _SingletonType # type: ignore
