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
"""Dependency provision and injection framework.

This module defines the concept of a `Provider`, which provides implementation
classes to `Interface` declarations. A provider class is responsible for a
given `Namespace`, its so called purview. Upon registration of a `Provider`
object, it binds implementation classes to their corresponding
`Interface` class such that code depending on a specific interface can be
provided with a concrete implementation dynamically at runtime.

Application packages should use the API of the `Dependencies` class to register
their `Provider` implementation, usually during the package initialization, but
practically it can be done at any time throughout the application lifecycle.
Code in packages that use dependency injection can declare arbitrary interfaces
by creating classes that inherit from `Interface`. An interface only consists
of abstract methods. By using the `@inject` decorator on the interface class,
the implementation classes are enabled for dependency injection. The `Provider`
implementation of the application package will then be responsible to provide
the corresponding interface implementation class at runtime. There can be
multiple implementation classes for a given interface.

Provider implementations should usually inherit from `AbstractProvider`, which
has default implementations for most methods, and then simply implement
the `initialize_bindings()` method to register the bindings for the underlying
package code.

Author: Phil Gaiser
"""

import string
import inspect

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePath
from typing import Optional, TypeVar, TypeAlias, Type, Union, Final, Any, cast
from threading import RLock

from raven.fathom.base.typing import Interface, TypeCheck
from raven.fathom.base.exceptions import FathomBaseException


class DependencyProvisionException(FathomBaseException):
    """Base exception for all errors in the dependency provision mechanism."""


class ImplementationAlreadyBoundException(DependencyProvisionException):
    """A provider cannot bind a given implementation because
    such an implementation for the corresponding interface already exists.
    """


class NoSuchBindingException(DependencyProvisionException):
    """Code refers to a provider binding which does not exist."""


class ProviderContextAlreadyBoundException(DependencyProvisionException):
    """A provider cannot be registered because another provider
    implementation already exists within the same context.
    """


class IndeterminableContextException(DependencyProvisionException):
    """The context for a provider or a related operation
    cannot be determined.
    """


class ProviderNotFoundException(DependencyProvisionException):
    """A provider was requested but no such registered object satisfying the
    search conditions could be found.
    """


class ProviderRegistrationException(DependencyProvisionException):
    """A provider implementation cannot be registered."""


# Interface type
I = TypeVar("I", bound=Interface)


def _new(interface, implementation, *args, **kwargs):
    """Instantiates the target class implementing the specified interface.

    Further arguments are forwarded to the class initializer.
    """
    return super(
        type(interface),
        implementation
    ).__call__(*args, **kwargs) # type: ignore


class Namespace:
    """A provider namespace.

    A namespace is represented by a hierarchy of packages. A string can be used
    to denote such a namespace by concatenating package levels with
    a dot ('.') character.

    Attributes:
        value (str): The namespace value as a `str`.
    """

    SEPARATOR = "."

    ALLOWED_CHARS = (
        set(string.ascii_lowercase) | set(string.digits) | {"_", "-", "."}
    )

    def __init__(self, value: str):
        """Initializes a new `Namespace` instance.

        Args:
            value (str): A namespace value in dot notation.

        Raises:
            ValueError: If the specified namespace value is invalid.
        """
        if not set(value).issubset(Namespace.ALLOWED_CHARS):
            raise ValueError(
                "Invalid namespace value: "
                f"Namespace string contains invalid characters: '{value}'"
            )

        if value.startswith(Namespace.SEPARATOR):
            raise ValueError(
                "Invalid namespace value: "
                "A namespace must not start "
                f"with a separator ('{Namespace.SEPARATOR}') character"
            )

        if value.endswith(Namespace.SEPARATOR):
            raise ValueError(
                "Invalid namespace value: "
                "A namespace must not end "
                f"with a separator ('{Namespace.SEPARATOR}') character"
            )

        self._ns = value
        self._is_toplvl = Namespace.SEPARATOR not in value

    @property
    def value(self) -> str:
        """The namespace as a string in dot notation."""
        return self._ns

    def parent(self) -> Optional["Namespace"]:
        """Gets the parent namespace of this namespace.

        Returns:
            Namespace: The enclosing namespace of this namespace object,
                or `None` if this namespace is a top-level namespace, i.e. it
                does not have a parent.
        """
        parent_ns = Namespace.SEPARATOR.join(
            self._ns.split(Namespace.SEPARATOR)[:-1]
        )
        if not parent_ns:
            return None

        return Namespace(parent_ns)

    def is_top_level(self) -> bool:
        """Indicates whether this namespace is a top-level namespace.

        Returns:
            bool: `True` if this instance is a top-level namespace,
                `False` if it has an enclosing parent namespace.
        """
        return self._is_toplvl

    def is_enclosed_by(self, namespace: "Namespace") -> bool:
        """Indicates whether this namespace is a child of the
        specified namespace.

        If the specified namespace is equal to this namespace, then
        this method returns `False`.

        Args:
            namespace (Namespace): The namespace object to check against.

        Returns:
            bool: `True` if this object is a namespace which is located inside
                the specified namespace, `False` if this namespace is not
                enclosed by the specified namespace.
        """
        if self == namespace:
            return False

        ns = self
        while (ns := ns.parent()) is not None:
            if ns == namespace:
                return True

        return False

    def __str__(self):
        return self._ns

    def __repr__(self):
        return self.__str__()

    def __eq__(self, namespace):
        return self._ns == namespace

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self._ns)


class VariableImplementation(ABC):
    """Abstract base class for a variable implementation binding.

    `Provider` instances may use implementations of this ABC to dynamically
    bind one or more implementations to an interface. If a `Provider` instance
    provides at least one implementation for a given interface, then
    the `provide()` method is called by the infrastructure to let the provider
    determine which concrete implementation class, if any, should be provided
    to the code that is requesting it.
    """

    @abstractmethod
    def provide(self, *args, **kwargs) -> Optional[Type[Interface]]:
        """Provides an implementation class for an existing interface binding.

        The values in `*args` and `**kwargs` are the arguments used in the
        request for the underlying interface implementation. These arguments
        are not passed to the initializer of the concrete implementation class
        upon instantiation, unless explicitly forwarded by means of
        the `forward_arguments()` method.

        If it is decided that a `VariableImplementation` object cannot provide
        an implementation to a bound interface, this method must either
        return `None` or raise a `NotImplementedError`.

        Returns:
            A class implementing a bound interface. May be `None`.

        Raises:
            NotImplementedError: If no implementation class can be provided.
        """

    def forward_arguments(self, *args, **kwargs) -> Optional[tuple]:
        """Forwards arguments to an implementation class instance.

        This method can be overridden by subclasses to customize the
        argument forwarding behaviour. By default, arguments specified by the
        caller who is requesting an interface implementation class are not
        forwarded to the implementation class' initializer.

        Returns:
            tuple: A tuple of positional arguments to be passed to the
                implementation class' initializer. May be `None` if no
                arguments should be forwarded.
        """
        return None  # Default implementation


class DirectImplementation(VariableImplementation):
    """Implementation of the `VariableImplementation` ABC which always
    provides the same implementation class.
    """

    def __init__(self, implementation: Type[I]):
        """Initializes a new `DirectImplementation` instance.

        Args:
            implementation: A class implementing an interface.
        """
        super().__init__()
        self._implementation_class = implementation

    def provide(self, *args, **kwargs):
        return self._implementation_class


# Type alias for binding declarations in the bind*() family of methods.
BindingDecl: TypeAlias = Union[Type[I], VariableImplementation]


class Provider(ABC):
    """Abstract base class for a dependency provider.

    Implementations of this class map interface classes to
    one or more implementation classes. Such a mapping is called a binding.
    Each provider is responsible for the provision of implementation classes
    within a specific namespace. There is two ways to look at it: Either a
    specific provider creates a binding because the interface is declared in
    the namespace of the provider (e.g. this is used to provide default
    implementations for an interface), or it creates a binding to a
    concrete implementation class because the code in its namespace should use
    that specific implementation of the interface (where the interface may be
    declared in a different namespace).

    Bindings can be exported to make them available to code residing in
    other namespaces. Bindings can be overridden to change the behaviour of
    the program, e.g. this may be useful for testing purposes or when creating
    an application plugin architecture.
    """

    @abstractmethod
    def namespace(self) -> Optional[Namespace]:
        """Returns the namespace of the provider.

        Implementations are allowed to return `None`, which is interpreted by
        the framework infrastructure to indicate that the package where the
        provider is defined should be used as the namespace.

        Returns:
            Namespace: The namespace that provider is responsible for.
                May be `None`.
        """

    @abstractmethod
    def reusables(self) -> Optional[list[Type[Interface]]]:
        """Returns a list of classes with reusable objects.

        Implementations of this method may return a list of classes for which
        a requested instance should be stored for later reuse.
        If this method returns `None`, then the provider does not support
        storing instances, and any time a consumer requests an instance a
        new instance is created on demand.

        Returns:
            list: A list of classes implementing interfaces which can be
                reused by the provider system. May be `None`
                or an empty `list`.
        """

    @abstractmethod
    def initialize_bindings(self):
        """Initializes the provider bindings.

        This method is called by the infrastructure when the provider
        is registered. It should be used by concrete implementations to
        set up the initial bindings for the provider.
        """

    @abstractmethod
    def bind(self, interface: Type[I], implementation: BindingDecl):
        """Binds the given implementation to the specified interface.

        The given implementation class will not be exported and is thus only
        available to code in a namespace that the provider is responsible for.

        Args:
            interface: The interface type to bind.
            implementation: The implementation to bind to the interface.
                Must be a concrete (non-abstract) subclass of `interface`,
                or a `VariableImplementation` instance.

        Raises:
            ImplementationAlreadyBoundException: If the interface is already
                bound to an implementation.
        """

    @abstractmethod
    def bind_export(self, interface: Type[I], implementation: BindingDecl):
        """Binds the given exported implementation to the specified interface.

        Exporting an implementation class allows code from other packages
        to consume that implementation.

        Args:
            interface: The interface to bind to.
            implementation: The implementation to bind to the interface
                and to export. Must be a concrete (non-abstract) subclass
                of `interface`, or a `VariableImplementation` instance.

        Raises:
            ImplementationAlreadyBoundException: If the interface is already
                bound to an implementation.
        """

    @abstractmethod
    def bind_override(self, interface: Type[I], implementation: BindingDecl):
        """Binds the given override implementation to the interface.

        A binding for the given interface must already exist.

        Args:
            interface: The interface to bind.
            implementation: The implementation to bind to the interface,
                overriding an existing implementation class that is already
                bound to the specified interface. Must be a concrete
                (non-abstract) subclass of `interface`, or a
                `VariableImplementation` instance.

        Raises:
            NoSuchBindingException: If the implementation has no binding set
                so it cannot be overridden.
        """

    @abstractmethod
    def get_implementation_class(
        self,
        interface: Type[I],
        exported: bool,
        *args,
        **kwargs
    ) -> Optional[Type[I]]:
        """Returns the suitable class which implements the given interface.

        The values in `*args` and `**kwargs` are the arguments which are
        given to each `VariableImplementation` object upon invocation of
        the `provide()` method.

        If this provider cannot provide an implementation of `I`, it
        must either return `None` or raise a `NotImplementedError`.

        Args:
            interface: The interface for which an implementation class
                is requested.
            exported (bool): A flag indicating whether the implementation class
                must be marked as exported or not in order to be allowed to
                provide it to a caller.

        Returns:
            A class which implements the interface `I`. May be `None`.

        Raises:
            NotImplementedError: If the provider cannot provide an
                implementation class for the target interface.
        """

    @abstractmethod
    def instantiate_class(
        self,
        interface: Type[I],
        implementation: Type[I],
        *args,
        **kwargs
    ) -> I:
        """Instantiates the implementation class for the given interface.

        Args:
            interface: The interface which is to be implemented.
            implementation: The implementation class.

        Returns:
            An instance of the implementation class.
        """


@dataclass
class _ImplCls:
    """Container holding an implementation class and associated metadata."""

    implementation: VariableImplementation

    exported: bool


class AbstractProvider(Provider):
    """Subclass of the `Provider` ABC with some default implementations.

    Provides default implementations of most methods but does not bind any
    implementation classes to interfaces. Concrete providers can inherit from
    this class instead of `Provider` to not have to implement all methods
    required by the ABC. Concrete providers can instead simply use these
    methods to create their bindings. Implementation classes must implement
    at least the `initialize_bindings()` method.
    """

    def __init__(self):
        super().__init__()
        self._impls: dict[Type[Interface], _ImplCls] = dict()

    def namespace(self) -> Optional[Namespace]:
        return None

    def reusables(self) -> Optional[list[Type[Interface]]]:
        return None

    def bind(self, interface: Type[I], implementation: BindingDecl):
        self._bind_impl(
            interface,
            implementation,
            export=False,
            override=False
        )

    def bind_export(self, interface: Type[I], implementation: BindingDecl):
        self._bind_impl(
            interface,
            implementation,
            export=True,
            override=False
        )

    def bind_override(self, interface: Type[I], implementation: BindingDecl):
        self._bind_impl(
            interface,
            implementation,
            export=False,
            override=True
        )

    def get_implementation_class(self, interface, exported, *args, **kwargs):
        impl_class = self._impls.get(interface)
        if impl_class is not None:
            if exported and not impl_class.exported:
                return None

            return impl_class.implementation.provide(*args, **kwargs)

        return None

    def instantiate_class(self, interface, implementation, *args, **kwargs):
        impl_class = self._impls.get(interface)
        assert impl_class is not None
        forwarded_args = impl_class.implementation.forward_arguments(
            *args,
            **kwargs
        )
        if forwarded_args is not None:
            return _new(interface, implementation, *forwarded_args)

        return _new(interface, implementation)

    def _bind_impl(self, interface, implementation, export, override):
        # Check here that interface actually inherits from Interface class?
        inherit_export = False
        existing_impl = self._impls.get(interface)
        if existing_impl is not None:
            if not override:
                existing_impl_class = existing_impl.implementation.provide()
                existing_impl_class = (
                    f"'{existing_impl_class.__name__}'"
                    if existing_impl_class
                    else "an existing implementation class"
                )
                raise ImplementationAlreadyBoundException(
                    f"Interface '{interface.__name__}' already bound to "
                    f"'{existing_impl_class}'"
                )

            inherit_export = existing_impl.exported

        if not isinstance(implementation, VariableImplementation):
            if not issubclass(implementation, interface):
                raise TypeError(
                    f"Implementation class '{implementation.__name__}' "
                    f"does not implement interface '{interface.__name__}'"
                )

            # Should we check here if implementation is in fact not abstract?

            implementation = DirectImplementation(implementation)

        self._impls[interface] = _ImplCls(
            implementation,
            export or inherit_export
        )


class Context:
    """A dependency provision context.

    A `Context` is a container used to pass contextual information to
    a `ProviderMapping` object so that it can determine which `Provider` object
    to use based on a given request.
    """

    _INTERNAL_INJECTION_MODS: Final[list[str]] = [
        "raven.fathom.base._inject",
        "raven.fathom.base.decorators._inject",
    ]

    def __init__(
        self,
        purview: Optional[Namespace] = None,
        caller: Optional[Namespace] = None
    ):
        """Initializes a new `Context` instance.

        Args:
            purview (Namespace): The namespace to be used as the purview.
                May be `None`.
            caller (Namespace): The namespace to be used as the calling
                context. May be `None`.
        """
        self._ns_purview = purview
        self._ns_calling = caller

    def purview_namespace(self) -> Optional[Namespace]:
        """Returns the namespace of the purview.

        Returns:
            Namespace: The purview namespace. May be `None`.
        """
        return self._ns_purview

    def set_purview_namespace(self, purview: Namespace):
        """Sets the purview namespace of this context.

        Args:
            purview (Namespace): The namespace to be used for the purview.
        """
        self._ns_purview = purview

    def calling_namespace(self) -> Optional[Namespace]:
        """Returns the namespace of the calling context.

        Returns:
            Namespace: The calling context namespace. May be `None`.
        """
        return self._ns_calling

    def set_calling_namespace(self, caller: Namespace):
        """Sets the calling context namespace of this context.

        Args:
            caller (Namespace): The namespace to be used for the calling
                context.
        """
        self._ns_calling = caller

    @classmethod
    def get_calling_context(cls) -> "Context":
        """Obtains the provider context for the calling scope.

        Returns:
            Context: A `Context` object containing information about
                the calling scope.

        Raises:
            IndeterminableContextException: If the calling context cannot
                be determined, e.g. if the current frame is not available.
        """
        # Only CPython is strictly supported
        current_frame = inspect.currentframe()
        if current_frame is None:
            raise IndeterminableContextException(
                "Cannot determine calling context: No stack frame found"
            )

        target_frame = None
        try:
            frame_to_check = current_frame.f_back
            while target_frame is None and frame_to_check is not None:
                name = frame_to_check.f_globals.get("__name__")
                if name not in Context._INTERNAL_INJECTION_MODS:
                    target_frame = frame_to_check
                    break

                frame_to_check = frame_to_check.f_back
        except AttributeError:
            raise IndeterminableContextException(
                "Cannot determine calling context: Unavailable stack frame"
            )

        if target_frame is None:
            raise IndeterminableContextException(
                "Cannot determine calling context: No target frame found"
            )

        package_name = target_frame.f_globals.get("__package__")
        if not package_name:
            if target_frame.f_globals.get("__name__", "") == "__main__":
                src_file = PurePath(target_frame.f_code.co_filename)
                src_file_parts = src_file.parts
                executed_file_name = src_file_parts[-1]
                if (executed_file_name.startswith("test_")
                    and executed_file_name.endswith(".py")):
                    try:
                        package_name = ".".join(
                            src_file_parts[src_file_parts.index("tests"):-1]
                        )
                    except ValueError:
                        pass

        if package_name is None:
            raise IndeterminableContextException(
                "Cannot determine calling context: No package name found"
            )

        return Context(purview=None, caller=Namespace(package_name))

    @classmethod
    def get_purview_context(cls, obj: Any) -> "Context":
        """Obtains the provider context for the purview of the given object.

        Args:
            obj (Any): An object for which to determine the purview.
                May be a class object or instance.

        Returns:
            Context: A `Context` object containing information about
                the provider purview applicable to the specified object.
        """
        if isinstance(obj, type):  # obj is a class object
            class_module = obj.__module__
        else:  # obj is an instance of a class
            class_module = obj.__class__.__module__

        if class_module is not None:
            package_name = ".".join(class_module.split(".")[:-1])
            if package_name:
                return Context(purview=Namespace(package_name))

        qualname = obj.__class__.__qualname__
        package_name = ".".join(qualname.split(".")[:-2])
        if package_name:
            return Context(purview=Namespace(package_name))

        return Context(purview=Namespace(qualname))


ObjectStoreType = Optional[dict[Type[Interface], Optional[Interface]]]


class ProviderMapping:
    """Stores and queries application providers.

    `ProviderMapping` objects map namespaces to `Provider` objects, where the
    namespace is a contextual key. The term contextual means that there are
    multiple reasons why a provider is searched by a given namespace.
    For example, given an interface declaration within a namespace, a provider
    implementation registered for that same namespace may get queried whether
    it can supply an implementation class for that interface. Another example
    would be that a provider is queried because the request for an
    implementation class for an interface originates from application code
    within the same namespace of that provider.
    """

    def __init__(self):
        """Initializes a new `ProviderMapping` instance.

        The initialized mapping will be empty.
        """
        self._providers: dict[Namespace, Provider] = dict()
        self._object_store: ObjectStoreType = None
        self._lock = RLock()

    def enable_object_store(self):
        """Enables the object store of this mapping.

        The object store is used to cache instances of interface implementations
        that have been created by the `find_implementation_instance()` method.
        If the object store is enabled, instances of interface implementations
        will be cached in the object store and reused for subsequent calls to
        `find_implementation_instance()`.
        """
        with self._lock:
            if self._object_store is None:
                self._object_store = dict()
                for provider in self._providers.values():
                    reusables = provider.reusables()
                    if reusables:
                        for reusable_impl_cls in reusables:
                            self._object_store[reusable_impl_cls] = None

    def disable_object_store(self):
        """Disables the object store of this mapping.

        If the object store is disabled, no instances will be reused.
        """
        with self._lock:
            self._object_store = None

    def is_object_store_enabled(self) -> bool:
        """Indicates whether the object store is enabled.

        Returns:
            bool: `True` if the object store is enabled, `False` if
                it is disabled.
        """
        return self._object_store is not None

    def flush_object_store(self, obj_type: Optional[Type[Interface]] = None):
        """Flushes the object store of this mapping.

        If the object store is enabled, this method will remove all reusable
        instances of interface implementations, or if `obj_type` is specified,
        only the instance of that type will be removed.

        Args:
            obj_type: The specific type of object to flush.
                If left `None`, all objects will be flushed.
        """
        with self._lock:
            if self._object_store is not None:
                if obj_type is not None:
                    if obj_type in self._object_store:
                        self._object_store[obj_type] = None
                else:
                    for key in self._object_store:
                        self._object_store[key] = None

    def find_provider(self, context: Context) -> Provider:
        """Searches for an available provider implementation.

        The given context must indicate the purview of the provider
        to search for.

        Args:
            context (Context): The context for which a provider
                should be obtained.

        Returns:
            Provider: A `Provider` implementation instance.

        Raises:
            ProviderNotFoundException: If no suitable provider implementation
                is currently available or if no provider can be found
                for the given context.
        """
        with self._lock:
            if len(self._providers) == 0:
                raise ProviderNotFoundException(
                    "No providers have been registered yet"
                )

            ctx = context.purview_namespace()
            if not ctx:
                raise ProviderNotFoundException(
                    "Invalid context specified: No purview namespace"
                )

            provider = self._providers.get(ctx)
            if provider is None:
                raise ProviderNotFoundException(
                    f"No provider serving purview '{ctx}' available"
                )

            return provider

    def register(self, provider: Provider, context: Optional[Context] = None):
        """Registers the given `Provider` implementation.

        An additional `Context` object is optional. In any case, a namespace
        defined by the `Provider` object itself by means of the `namespace()`
        method takes precedence over the information potentially
        supplied by the context.

        Args:
            provider (Provider): The provider implementation
                instance to register.
            context (Context): An optional context for which the specified
                provider should be registered for. May be `None`.

        Raises:
            ProviderRegistrationException: If the specified provider cannot be
                registered due to insufficient available information.
            ProviderContextAlreadyBoundException: If a provider is already
                registered for the determined namespace context.
        """
        TypeCheck.require_arg(provider, Provider)
        with self._lock:
            self._register_provider(provider, context, override=False)

    def register_override(self, provider: Provider):
        """Registers the given `Provider` implementation as an override.

        The `Provider` object itself must define the namespace for which an
        override should be registered via the `namespace()` method.

        Args:
            provider (Provider): The provider implementation
                instance for which to register an override.

        Raises:
            ProviderRegistrationException: If the specified provider does not
                specify the namespace to override.
        """
        TypeCheck.require_arg(provider, Provider)
        with self._lock:
            self._register_provider(provider, context=None, override=True)

    def find_implementation_instance(
        self,
        target: Type[I],
        context: Context,
        *args,
        **kwargs
    ) -> I:
        """Searches for a mapping of the target interface to an implementation.

        If a mapping exists, an instance of the class implementing the given
        target interface is created.
        The values in `*args` and `**kwargs` are the arguments passed to the
        `provide()` method of the `VariableImplementation` object which is
        queried for an implementation class.

        Args:
            target: The target interface for which an implementation
                should be instantiated.
            context: The calling context.

        Returns:
            An initialized instance implementing the target interface `I`.

        Raises:
            NotImplementedError: If the given target interface has no
                implementation available, i.e. no mapping exists.
        """
        with self._lock:
            if not self.needs_implementation_lookup(target):
                return cast(
                    I, self._instantiate_concrete(target, *args, **kwargs)
                )

            provider, impl = self._lookup_calling_scope(
                target,
                context,
                *args,
                **kwargs
            )
            if provider is not None:
                return cast(
                    I,
                    self._instantiate(provider, target, impl, *args, **kwargs)
                )

            provider, impl = self._lookup_purview_scope(
                target,
                context,
                *args,
                **kwargs
            )
            if provider is not None:
                return cast(
                    I,
                    self._instantiate(provider, target, impl, *args, **kwargs)
                )

            raise NotImplementedError(
                f"No implementation available for {target}"
            )

    def clear(self):
        """Removes all registered providers from this mapping."""
        with self._lock:
            self._providers.clear()
            self._object_store = None

    def needs_implementation_lookup(self, target: Type[Interface]) -> bool:
        """Checks if the specified target class requires an implementation
        class lookup or whether it can be instantiated directly.

        Args:
            target: The target class to check.

        Returns:
            bool: `True` if the given class object cannot be instantiated
                directly, `False` if it can be directly instantiated.
        """
        return inspect.isabstract(target)

    def _register_provider(self, provider, context, override):
        ctx = provider.namespace()
        if not ctx and context is not None:
            ctx = context.purview_namespace()

        if not ctx:
            raise ProviderRegistrationException(
                "Cannot determine dependency provider registration purview"
            )

        TypeCheck.require(
            ctx, Namespace,
            "Failed to register dependency provider: "
            f"Expected Namespace object as context but found {type(ctx)}"
        )
        if not override and ctx in self._providers:
            raise ProviderContextAlreadyBoundException(
                f"A dependency provider for purview '{ctx}' "
                "is already registered"
            )

        provider.initialize_bindings()
        self._providers[ctx] = provider
        if self.is_object_store_enabled():
            reusable_classes = provider.reusables()
            if reusable_classes:
                for reusable_cls in reusable_classes:
                    if not issubclass(reusable_cls, Interface):
                        raise TypeError(
                            f"Reusable class '{reusable_cls.__name__}' "
                            "must implement an interface"
                        )

                    if inspect.isabstract(reusable_cls):
                        raise TypeError(
                            f"Reusable class '{reusable_cls.__name__}' "
                            "must not be an abstract class"
                        )

                    assert self._object_store is not None
                    self._object_store[reusable_cls] = None

    def _lookup_purview_scope(self, target, context, *args, **kwargs):
        export_required = self._check_export_required(
            context.calling_namespace(),
            context.purview_namespace()
        )
        provider, impl_cls = self._lookup_traversal(
            context.purview_namespace(),
            target,
            export_required,
            *args, **kwargs
        )
        return provider,impl_cls

    def _lookup_calling_scope(self, target, context, *args, **kwargs):
        calling_namespace = context.calling_namespace()
        export_required = False
        provider, impl_cls = self._lookup_traversal(
            calling_namespace, target, export_required, *args, **kwargs
        )

        return provider, impl_cls

    def _lookup_traversal(
        self,
        namespace,
        interface,
        exported,
        *args,
        **kwargs
    ):
        ctx = namespace
        while ctx is not None:
            provider = self._providers.get(ctx)
            if provider is not None:
                impl_cls = provider.get_implementation_class(
                    interface, exported, *args, **kwargs
                )
                if impl_cls is not None:
                    return provider, impl_cls

            ctx = ctx.parent()

        return None, None

    def _instantiate_concrete(self, target, *args, **kwargs):
        is_object_store_enabled = self.is_object_store_enabled()
        if is_object_store_enabled:
            stored_instance = self._get_from_object_store(target)
            if stored_instance is not None:
                return stored_instance

        new_instance = _new(target, target, *args, **kwargs)
        if is_object_store_enabled:
            if target in self._object_store:
                self._store_object(target, new_instance)

        return new_instance

    def _instantiate(self, provider, interface, target,  *args, **kwargs):
        is_object_store_enabled = self.is_object_store_enabled()
        if is_object_store_enabled:
            stored_instance = self._get_from_object_store(target)
            if stored_instance is not None:
                return stored_instance

        new_instance = provider.instantiate_class(
            interface,
            target,
            *args,
            **kwargs
        )
        if is_object_store_enabled:
            if target in self._object_store:
                self._store_object(target, new_instance)

        return new_instance

    def _store_object(self, target, instance):
        assert self._object_store is not None
        self._object_store[target] = instance

    def _get_from_object_store(self, target):
        assert self._object_store is not None
        if target in self._object_store:
            return self._object_store.get(target)

        return None

    def _check_export_required(self, calling_namespace, purview_namespace):
        return (
            calling_namespace != purview_namespace
            and calling_namespace is not None
            and not calling_namespace.is_enclosed_by(purview_namespace)
        )


class Dependencies:
    """Primary API to interact with dependency providers.

    This class handles global mappings. Application packages should use
    this API to register the dependency provider responsible for the
    application code residing in that namespace.
    """

    _IMPL = ProviderMapping()

    @classmethod
    def get_provider(cls, namespace: Namespace) -> Provider:
        """Obtains the provider implementation for the given namespace.

        The provider must have already been registered

        Args:
            namespace (Namespace): The namespace for which a provider
                implementation should be obtained.

        Returns:
            Provider: A `Provider` implementation instance.

        Raises:
            ProviderNotFoundException: If no suitable provider implementation
                is currently available.
        """
        return cls._IMPL.find_provider(Context(purview=namespace))

    @classmethod
    def register(cls, provider: Provider):
        """Registers the given `Provider` implementation.

        Args:
            provider (Provider): The provider implementation
                instance to register.

        Raises:
            ProviderRegistrationException: If the provider registration fails.
            ProviderContextAlreadyBoundException: If a provider is already
                registered for the determined namespace.
        """
        cls._IMPL.register(provider, Context.get_purview_context(provider))

    @classmethod
    def register_override(cls, provider: Provider):
        """Registers the given `Provider` implementation as an override.

        Args:
            provider (Provider): The provider implementation
                instance for which to register an override.

        Raises:
            ProviderRegistrationException: If the specified provider does not
                specify the namespace to override.
        """
        cls._IMPL.register_override(provider)

    @classmethod
    def get_implementation_instance(
        cls,
        target: Type[I],
        *args,
        **kwargs
    ) -> I:
        """Creates an instance of a class implementing the given interface `I`.

        The values in `*args` and `**kwargs` are the arguments that would be
        passed to the implementation class initializer if it were to be
        instantiated directly. These arguments are only passed to
        the `provide()` method of the `VariableImplementation` object which
        is queried for an implementation class and they are not forwarded to
        the concrete initializer of the implementation class.

        Args:
            target: The target interface for which an implementation
                class should be instantiated.

        Returns:
            An initialized instance implementing the target interface `I`.

        Raises:
            NotImplementedError: If the given target has no implementation
                available.
        """
        return cls._IMPL.find_implementation_instance(
            target,
            Context(
                Context.get_purview_context(target).purview_namespace(),
                Context.get_calling_context().calling_namespace()),
            *args,
            **kwargs
        )

    @classmethod
    def inject_class_instance(
        cls,
        target: Type[I],
        context: Context,
        *args,
        **kwargs
    ) -> I:
        """Returns an instance of a class implementing the interface `I`.

        Searches the available provider mappings to find a usable
        implementation class and instantiates the found class, effectively
        creating an instance of a class implementing the given
        target interface `I`.

        The values in `*args` and `**kwargs` are the arguments supplied by the
        code which has requested an implementation instance for an interface.

        Args:
            target: The target interface for which an implementation
                class should be instantiated.
            context (Context): The calling context.

        Returns:
            An initialized instance implementing the target interface `I`.

        Raises:
            NotImplementedError: If no implementation is available for the
                given target interface.
        """
        ns = Context.get_purview_context(target).purview_namespace()
        if ns is not None:
            context.set_purview_namespace(ns)

        return cls._IMPL.find_implementation_instance(
            target, context, *args, **kwargs
        )

    @classmethod
    def enable_object_store(cls):
        """Enables the object store for concrete dependency instances."""
        cls._IMPL.enable_object_store()

    @classmethod
    def disable_object_store(cls):
        """Disables the object store for concrete dependency instances."""
        cls._IMPL.disable_object_store()

    @classmethod
    def is_object_store_enabled(cls) -> bool:
        """Indicates whether the object store is enabled.

        Returns:
            bool: `True` if the object store is enabled, `False` if
                it is disabled.
        """
        return cls._IMPL.is_object_store_enabled()

    @classmethod
    def flush_object_store(cls):
        """Flushes the object store for concrete dependency instances."""
        cls._IMPL.flush_object_store()

    @classmethod
    def flush_object_store_type(cls, obj_type: Type[Interface]):
        """Flushes the object store for a dependency instance
        of the concrete implementation type.

        Args:
            obj_type: The type of the object to flush.
        """
        cls._IMPL.flush_object_store(obj_type)

    @classmethod
    def reset(cls):
        """Unregisters and clears all currently available
        provider implementations.
        """
        cls._IMPL.clear()
