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
"""Unit tests for the base provider module."""

from raven.fathom.base import Provider, Namespace, Context
from raven.fathom.base import ProviderNotFoundException
from raven.fathom.base import ProviderRegistrationException
from raven.fathom.base import ProviderContextAlreadyBoundException
from raven.fathom.base.provider import ProviderMapping

from tests.unit import TestCase
from tests.unit.base.mocks import FakeInterface
from tests.unit.base.mocks import FakeInterfaceImplementation
from tests.unit.base.mocks import FakeInterfaceImplementation2
from tests.unit.base.mocks import MockProvider


class TestNamespace(TestCase):
    """Unit tests for the `Namespace` class."""

    def test_namespace_initialization(self):
        ns = Namespace("parent.child")
        self.assertEqual(ns.value, "parent.child")

    def test_namespace_invalid_initialization(self):
        with self.assertRaises(ValueError):
            Namespace(".invalid")

        with self.assertRaises(ValueError):
            Namespace("invalid.")

        with self.assertRaises(ValueError):
            Namespace("invalid@namespace")

    def test_namespace_parent(self):
        ns = Namespace("parent.child")
        parent = ns.parent()
        self.assertIsNotNone(parent)
        self.assertEqual(parent.value, "parent") # type: ignore

    def test_namespace_parent_parent_of_parent(self):
        ns = Namespace("main-parent.child-a.child_b")
        parent = ns.parent().parent() # type: ignore
        self.assertIsNotNone(parent)
        self.assertEqual(parent.value, "main-parent") # type: ignore

    def test_namespace_top_has_no_parent(self):
        ns = Namespace("parent.child")
        parent = ns.parent().parent() # type: ignore
        self.assertIsNone(parent)

    def test_namespace_is_top_level(self):
        ns = Namespace("the-root_level")
        self.assertTrue(ns.is_top_level())

    def test_namespace_is_not_top_level(self):
        child_ns = Namespace("parent.child")
        self.assertFalse(child_ns.is_top_level())

    def test_namespace_is_enclosed_by(self):
        parent = Namespace("parent")
        child = Namespace("parent.child")
        self.assertTrue(child.is_enclosed_by(parent))
        self.assertFalse(parent.is_enclosed_by(child))

    def test_namespace_is_not_enclosed_by_unrelated(self):
        ns_1 = Namespace("parent.child.leaf1")
        ns_2 = Namespace("parent.child.leaf2")
        self.assertFalse(ns_1.is_enclosed_by(ns_2))
        self.assertFalse(ns_2.is_enclosed_by(ns_1))


class TestContext(TestCase):
    """Unit tests for the `Context` class."""

    def test_context_initialization(self):
        purview = Namespace("purview.namespace")
        calling_ctx = Namespace("calling.namespace")
        context = Context(purview, calling_ctx)
        self.assertEqual(str(context.purview_namespace()), "purview.namespace")
        self.assertEqual(str(context.calling_namespace()), "calling.namespace")

    def test_context_get_calling_context(self):
        context = Context.get_calling_context()
        self.assertIsInstance(context, Context)
        self.assertIsNotNone(context.calling_namespace())


class TestProviderMapping(TestCase):
    """Unit tests for the `ProviderMapping` class."""

    def test_register_and_get_provider(self):
        namespace_1 = "my.testing"
        namespace_2 = "my.testing.namespace"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(namespace_1)
        mock_provider_2 = MockProvider(namespace_2)
        mapping.register(mock_provider_1)
        mapping.register(mock_provider_2)
        found_provider_1 = mapping.find_provider(
            Context(Namespace(namespace_1))
        )
        found_provider_2 = mapping.find_provider(
            Context(Namespace(namespace_2))
        )
        self.assertIsInstance(found_provider_1, Provider)
        self.assertIsInstance(found_provider_2, Provider)
        self.assertIs(found_provider_1, mock_provider_1)
        self.assertIs(found_provider_2, mock_provider_2)

    def test_searching_for_unregistered_provider_raises_exception(self):
        mapping = ProviderMapping()
        mock_provider = MockProvider("my.testing.some-namespace")
        mapping.register(mock_provider)
        ns = "my.testing.other-namespace"
        with self.assertRaises(ProviderNotFoundException) as raised:
            mapping.find_provider(Context(Namespace(ns)))

        self.assertIn(
            f"No provider serving purview '{ns}' available",
            str(raised.exception)
        )

    def test_searching_for_provider_with_insufficient_context_raises_ex(self):
        mapping = ProviderMapping()
        mock_provider = MockProvider("my.testing.some-namespace")
        mapping.register(mock_provider)
        with self.assertRaises(ProviderNotFoundException) as raised:
            mapping.find_provider(Context())

        self.assertIn(
            "Invalid context specified: No purview namespace",
            str(raised.exception)
        )

    def test_clear_providers(self):
        namespace = "my.testing.namespace"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace)
        mapping.register(mock_provider)
        mapping.clear()
        with self.assertRaises(ProviderNotFoundException):
            mapping.find_provider(Context(Namespace(namespace)))

    def test_register_provider_in_custom_context(self):
        namespace = Namespace("my.testing.namespace")
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace=None)
        mapping.register(mock_provider, Context(namespace))
        found_provider = mapping.find_provider(
            Context(namespace)
        )
        self.assertIsInstance(found_provider, Provider)
        self.assertIs(found_provider, mock_provider)

    def test_registering_provider_with_insufficient_context_raises_ex(self):
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace=None)
        with self.assertRaises(ProviderRegistrationException) as raised:
            mapping.register(mock_provider)

        self.assertIn(
            "Cannot determine dependency provider registration purview",
            str(raised.exception)
        )

    def test_registering_provider_in_already_bound_namespace_raises_ex(self):
        namespace = "my.testing.some-namespace"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(namespace)
        mapping.register(mock_provider_1)
        mock_provider_2 = MockProvider(namespace)
        with self.assertRaises(ProviderContextAlreadyBoundException) as raised:
            mapping.register(mock_provider_2)

        self.assertIn(
            f"A dependency provider for purview '{namespace}' "
            "is already registered",
            str(raised.exception)
        )

    def test_register_provider_override(self):
        namespace = "my.testing.namespace"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(namespace)
        mock_provider_2 = MockProvider(
            namespace, impl_class=FakeInterfaceImplementation2
        )
        mapping.register(mock_provider_1)
        mapping.register_override(mock_provider_2)
        found_provider = mapping.find_provider(
            Context(Namespace(namespace))
        )
        created_object = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace),
                caller=Namespace(namespace)
            ),
        )
        self.assertIsInstance(found_provider, Provider)
        self.assertIs(found_provider, mock_provider_2)
        self.assertIsInstance(created_object, FakeInterfaceImplementation2)

    def test_needs_implementation_lookup_for_interface_target(self):
        mapping = ProviderMapping()
        needs_lookup = mapping.needs_implementation_lookup(FakeInterface)
        self.assertTrue(needs_lookup)

    def test_needs_implementation_lookup_for_concrete_class_target(self):
        mapping = ProviderMapping()
        needs_lookup = mapping.needs_implementation_lookup(
            FakeInterfaceImplementation
        )
        self.assertFalse(needs_lookup)

    def test_impl_lookup_when_calling_ctx_does_not_have_provider(self):
        namespace = "raven.project.package"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace, binding="export")
        mapping.register(mock_provider)
        created_object = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace),
                caller=Namespace("raven.different.namespace")
            ),
        )
        self.assertIsInstance(created_object, FakeInterfaceImplementation)
        self.assertTrue(mock_provider.get_implementation_class_called)

    def test_impl_lookup_when_calling_ctx_has_provider_without_impl(self):
        namespace_1 = "raven"
        namespace_2 = "raven.project.package"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(namespace_1)
        mock_provider_2 = MockProvider(namespace_2, impl_class=None)
        mapping.register(mock_provider_1)
        mapping.register(mock_provider_2)
        created_object = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace_1),
                caller=Namespace(namespace_2)
            ),
        )
        self.assertIsInstance(created_object, FakeInterfaceImplementation)
        self.assertTrue(mock_provider_1.get_implementation_class_called)
        self.assertTrue(mock_provider_2.get_implementation_class_called)

    def test_impl_lookup_when_calling_ctx_has_provider_with_impl_class(self):
        namespace_1 = "raven.project.package"
        namespace_2 = "raven.different.namespace"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(namespace_1)
        mock_provider_2 = MockProvider(
            namespace_2, impl_class=FakeInterfaceImplementation2
        )
        mapping.register(mock_provider_1)
        mapping.register(mock_provider_2)
        created_object = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace_1),
                caller=Namespace(namespace_2)
            ),
        )
        self.assertIsInstance(created_object, FakeInterfaceImplementation2)
        self.assertFalse(mock_provider_1.get_implementation_class_called)
        self.assertTrue(mock_provider_2.get_implementation_class_called)

    def test_standard_binding_can_be_accessed_from_lower_namespaces(self):
        namespace_1 = "raven"
        namespace_2 = "raven.project.namespace.child"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace_1)
        mapping.register(mock_provider)
        created_object = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace_1),
                caller=Namespace(namespace_2)
            ),
        )

        self.assertIsInstance(created_object, FakeInterfaceImplementation)
        self.assertEqual(created_object.something(), "FakeReturnValue")

    def test_standard_binding_cannot_be_accessed_from_other_namespaces(self):
        namespace_1 = "raven.project.namespace-a"
        namespace_2 = "raven.project.namespace-b"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace_1)
        mapping.register(mock_provider)
        with self.assertRaises(NotImplementedError) as raised:
            mapping.find_implementation_instance(
                FakeInterface,
                Context(
                    purview=Namespace(namespace_1),
                    caller=Namespace(namespace_2)
                ),
            )

        self.assertIn("No implementation available", str(raised.exception))

    def test_exported_binding_can_be_accessed_from_other_namespaces(self):
        namespace_1 = "raven.project.namespace-a"
        namespace_2 = "something.else.namespace-b"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace_1, binding="export")
        mapping.register(mock_provider)
        created_object = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace_1),
                caller=Namespace(namespace_2)
            ),
        )

        self.assertIsInstance(created_object, FakeInterfaceImplementation)
        self.assertEqual(created_object.something(), "FakeReturnValue")

    def test_override_binding_replaces_existing_impl_class_in_namespace(self):
        namespace_1 = "raven.project.namespace"
        namespace_2 = "something.else.namespace"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(namespace_1, binding="export")
        mock_provider_2 = MockProvider(
            namespace=namespace_1,
            binding=("export", "override")
        )
        mapping.register(mock_provider_1)
        mapping.register_override(mock_provider_2)
        created_object_1 = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace_1),
                caller=Namespace(namespace_1)
            ),
        )
        self.assertIsInstance(created_object_1, FakeInterfaceImplementation2)
        self.assertEqual(created_object_1.something(), "FakeReturnValue2")
        self.assertFalse(mock_provider_1.get_implementation_class_called)
        self.assertTrue(mock_provider_2.get_implementation_class_called)
        created_object_2 = mapping.find_implementation_instance(
            FakeInterface,
            Context(
                purview=Namespace(namespace_1),
                caller=Namespace(namespace_2)
            ),
        )
        self.assertIsInstance(created_object_2, FakeInterfaceImplementation2)
        self.assertEqual(created_object_2.something(), "FakeReturnValue2")
        self.assertFalse(mock_provider_1.get_implementation_class_called)
        self.assertTrue(mock_provider_2.get_implementation_class_called)

    def test_overriding_default_binding_does_not_export_impl_class(self):
        namespace_1 = "raven.project.namespace"
        namespace_2 = "something.else.namespace"
        mapping = ProviderMapping()
        mock_provider_1 = MockProvider(
            namespace_1,
            binding="default"
        )
        mock_provider_2 = MockProvider(
            namespace=namespace_1,
            binding=("default", "override")
        )
        mapping.register(mock_provider_1)
        mapping.register_override(mock_provider_2)
        with self.assertRaises(NotImplementedError) as raised:
            mapping.find_implementation_instance(
                FakeInterface,
                Context(
                    purview=Namespace(namespace_1),
                    caller=Namespace(namespace_2)
                ),
            )

        self.assertIn("No implementation available", str(raised.exception))
        self.assertFalse(mock_provider_1.get_implementation_class_called)
        self.assertTrue(mock_provider_2.get_implementation_class_called)

    def test_non_reusable_impl_class_is_instantiated_every_time(self):
        namespace = "raven.project.namespace"
        mapping = ProviderMapping()
        mapping.enable_object_store()
        mock_provider = MockProvider(namespace)
        mapping.register(mock_provider)
        ctx = Context(
            purview=Namespace(namespace),
            caller=Namespace(namespace)
        )
        created_object_1 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_2 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        self.assertIsNot(created_object_1, created_object_2)

    def test_reusable_impl_class_instance_is_reused(self):
        namespace = "raven.project.namespace"
        mapping = ProviderMapping()
        mapping.enable_object_store()
        mock_provider = MockProvider(namespace)
        mock_provider.reusable_classes = [FakeInterfaceImplementation]
        mapping.register(mock_provider)
        ctx = Context(
            purview=Namespace(namespace),
            caller=Namespace(namespace)
        )
        created_object_1 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_2 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_3 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        self.assertIs(created_object_1, created_object_2)
        self.assertIs(created_object_2, created_object_3)

    def test_impl_class_is_not_reused_when_object_store_not_enabled(self):
        namespace = "raven.project.namespace"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace)
        mock_provider.reusable_classes = [FakeInterfaceImplementation]
        mapping.register(mock_provider)
        ctx = Context(
            purview=Namespace(namespace),
            caller=Namespace(namespace)
        )
        created_object_1 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_2 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_3 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        self.assertIsNot(created_object_1, created_object_2)
        self.assertIsNot(created_object_2, created_object_3)

    def test_flushing_object_store_clears_reused_impl_class_instance(self):
        namespace = "raven.project.namespace"
        mapping = ProviderMapping()
        mapping.enable_object_store()
        mock_provider = MockProvider(namespace)
        mock_provider.reusable_classes = [FakeInterfaceImplementation]
        mapping.register(mock_provider)
        ctx = Context(
            purview=Namespace(namespace),
            caller=Namespace(namespace)
        )
        created_object_1 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_2 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        mapping.flush_object_store()
        created_object_3 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        self.assertIs(created_object_1, created_object_2)
        self.assertIsNot(created_object_2, created_object_3)

    def test_object_store_can_be_enabled_anytime(self):
        namespace = "raven.project.namespace"
        mapping = ProviderMapping()
        mock_provider = MockProvider(namespace)
        mock_provider.reusable_classes = [FakeInterfaceImplementation]
        mapping.register(mock_provider)
        ctx = Context(
            purview=Namespace(namespace),
            caller=Namespace(namespace)
        )
        mapping.enable_object_store()
        created_object_1 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        created_object_2 = mapping.find_implementation_instance(
            FakeInterface,
            ctx,
        )
        self.assertIs(created_object_1, created_object_2)

    def test_reusable_impl_cls_is_instantiated_when_directly_initialized(self):
        namespace = "raven.project.namespace"
        mapping = ProviderMapping()
        mapping.enable_object_store()
        mock_provider = MockProvider(namespace)
        mock_provider.reusable_classes = [FakeInterfaceImplementation]
        mapping.register(mock_provider)
        created_object_1 = FakeInterfaceImplementation()
        created_object_2 = FakeInterfaceImplementation()
        created_object_3 = FakeInterfaceImplementation()
        self.assertIsNot(created_object_1, created_object_2)
        self.assertIsNot(created_object_2, created_object_3)


if __name__ == "__main__":
    TestCase.run_tests()
