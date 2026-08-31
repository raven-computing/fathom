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
"""Mocks for the provider tests.

Contains a mock implementation of the `Provider` ABC and a fake interface
declaration and two fake interface implementations used for testing puroses.
"""

from abc import abstractmethod
from typing import Optional, TypeVar, TypeAlias, Type, Union, Final

from raven.fathom.base import AbstractProvider, Namespace
from raven.fathom.base.typing import Interface


I = TypeVar("I", bound=Interface)

InterfaceType: TypeAlias = Type[I]


class FakeInterface(Interface):
    """A fake interface."""

    @abstractmethod
    def something(self) -> str:
        """Does something very useful."""


class FakeInterfaceImplementation(FakeInterface):
    """A fake interface implementation."""

    def __init__(self, return_value="FakeReturnValue"):
        super().__init__()
        self.return_value = return_value

    def something(self):
        return self.return_value


class FakeInterfaceImplementation2(FakeInterface):
    """An alternative fake interface implementation."""

    def something(self):
        return "FakeReturnValue2"


class DefaultMappingBehaviour:
    """Sentinel class to indicate usage of the default mapping
    behaviour in the MockProvider.
    """


DEFAULT_MAPPING_BEHAVIOUR: Final = DefaultMappingBehaviour()


class MockProvider(AbstractProvider):
    """A mock `Provider` implementation for a given fake namespace."""

    def __init__(
        self,
        namespace: Optional[str] = None,
        impl_class: Optional[
            Union[InterfaceType, DefaultMappingBehaviour]
        ] = DEFAULT_MAPPING_BEHAVIOUR,
        binding: Union[str, tuple[str, ...]] = "default"
    ):
        super().__init__()
        self.ns = Namespace(namespace) if namespace else None
        self.impl_class = impl_class
        self.binding = (binding,) if isinstance(binding, str) else binding
        self.get_implementation_class_called = False
        self.reusable_classes = []

    def namespace(self):
        return self.ns

    def reusables(self):
        return self.reusable_classes

    def initialize_bindings(self):
        if "default" in self.binding:
            self.bind(FakeInterface, FakeInterfaceImplementation)
        if "export" in self.binding:
            self.bind_export(FakeInterface, FakeInterfaceImplementation)
        if "override" in self.binding:
            self.bind_override(FakeInterface, FakeInterfaceImplementation2)

    def get_implementation_class(self, interface, exported, *args, **kwargs):
        result = super().get_implementation_class(
            interface, exported, *args, **kwargs
        )
        self.get_implementation_class_called = True
        return (
            self.impl_class
            if not isinstance(self.impl_class, DefaultMappingBehaviour)
            else result
        )
