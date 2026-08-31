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
"""Unit tests for ORM customisations."""

from raven.fathom.server.datastore.orm.model import Model
from raven.fathom.server.datastore.orm.field import (
    FieldChecker, CharField, BooleanField, IntegerField
)

from tests.unit import TestCase


class ModelWithNonNullFields(Model):
    """An ORM model with required fields for testing purposes."""

    field_a = CharField(
        null=False,
    )

    field_b = CharField()

    field_c = BooleanField(
        null=False,
    )

    field_d = IntegerField(
        null=False,
        default=42,
    )


class TestRequiredFieldChecker(TestCase):
    """Tests the `RequiredFieldChecker` class."""

    def test_can_instantiate_model_with_all_required_fields_set(self):
        obj = ModelWithNonNullFields(
            field_a="AAA", field_b="CCC", field_c=True, field_d=10,
        )
        self.assertIsInstance(obj, ModelWithNonNullFields)

    def test_instantiating_model_with_missing_required_field_raises_ex(self):
        with self.assertRaises(TypeError) as ctx:
            ModelWithNonNullFields(
                field_a="AAA", field_b="CCC", field_c=None, field_d=10
            )

        self.assertIn("cannot be None", str(ctx.exception))
        self.assertIn("field_c", str(ctx.exception))

    def test_instantiating_model_with_required_field_as_none_raises_ex(self):
        with self.assertRaises(TypeError) as ctx:
            ModelWithNonNullFields(
                field_a="AAA", field_b="CCC", field_d=10
            )

        self.assertIn("Missing", str(ctx.exception))
        self.assertIn("field_c", str(ctx.exception))

    def test_can_instantiate_model_with_default_missing_required_field(self):
        obj = ModelWithNonNullFields(
            field_a="AAA", field_b="CCC", field_c=True
        )
        self.assertIsInstance(obj, ModelWithNonNullFields)

    def test_instantiating_model_reuses_field_checker_instance(self):
        obj_1 = ModelWithNonNullFields(
            field_a="AAA", field_b="CCC", field_c=True, field_d=10,
        )
        checker_1 = FieldChecker.get_checker(obj_1)
        obj_2 = ModelWithNonNullFields(
            field_a="AAA", field_b="CCC", field_c=False, field_d=11,
        )
        checker_2 = FieldChecker.get_checker(obj_2)
        obj_3 = ModelWithNonNullFields(
            field_a="AAA", field_b="CCC", field_c=True, field_d=12,
        )
        checker_3 = FieldChecker.get_checker(obj_3)
        self.assertTrue(
            checker_1 is checker_2 is checker_3,
            "Instances of RequiredFieldChecker should be reused per model"
        )


if __name__ == "__main__":
    TestCase.run_tests()
