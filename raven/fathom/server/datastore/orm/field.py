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
"""ORM field declarations and related internal utilities."""

import threading

from typing import Final

import peewee as orm_impl


_INIT_LOCK = threading.Lock()


class FieldChecker:
    """A checker for known and required fields of model instances.

    Instances of this class are assigned to class objects of ORM models.
    When a model is instantiated by application code, to create a record of
    such model, a checker ensures that all required fields are provided
    directly in the initializer and that all set attributes correspond to
    defined fields in the underlying model. This is done so that not specifying
    a required field or typos in initializer arguments attributes fails early
    when a record is instantiated in memory, as opposed to having only the
    actual datastore detect that error condition when that record is inserted
    and the not-null constraint is violated because of the missing field value.
    """

    # The name of the class attribute where checker instances live
    ORM_CHECKER: Final[str] = "_fathom_orm_field_checker"

    def __init__(self, model_instance):
        self._model_name = model_instance.__class__.__name__
        fields = self._get_fields_list(model_instance)
        self._all_fields = self._compute_all(fields)
        self._req_fields = self._compute_required(fields)

    def check_required(self, **kwargs):
        """Checks that all required fields have a value specified.

        Args:
            kwargs: The field name-value pairs.

        Raises:
            TypeError: If a required field is not set.
        """
        for required_field in self._req_fields:
            if required_field not in kwargs:
                raise TypeError(
                    "Missing value for required field "
                    f"'{self._model_name}.{required_field}'"
                )

            if kwargs.get(required_field) is None:
                raise TypeError(
                    "Value cannot be None for required field "
                    f"'{self._model_name}.{required_field}'"
                )

    def check_known(self, **kwargs):
        """Checks that all specified fields are known to the model.

        Args:
            kwargs: The field name-value pairs.

        Raises:
            TypeError: If at least one field is not known.
        """
        for field_name in kwargs:
            if (not field_name.startswith("_")
                and field_name not in self._all_fields):

                raise TypeError(
                    "Unknown model field "
                    f"'{self._model_name}.{field_name}'"
                )

    @staticmethod
    def has_checker(model_instance) -> bool:
        """Checks that the model class has a checker set.

        Args:
            model_instance: The instance of the model to check.

        Returns:
            bool: `True` if a checker is present, `False` otherwise.
        """
        return hasattr(
            model_instance.__class__,
            FieldChecker.ORM_CHECKER
        )

    @staticmethod
    def get_checker(model_instance) -> "FieldChecker":
        """Gets the checker instance for the model.

        Args:
            model_instance: The instance of the model to get a checker for.

        Returns:
            FieldChecker: The checker instance for the given model.
        """
        return getattr(
            model_instance.__class__,
            FieldChecker.ORM_CHECKER
        )

    @staticmethod
    def assign_checker(model_instance):
        """Assigns a new checker to the given model.

        Args:
            model_instance: The instance of the model to assign a checker for.
        """
        with _INIT_LOCK:
            setattr(
                model_instance.__class__,
                FieldChecker.ORM_CHECKER,
                FieldChecker(model_instance)
            )

    def _get_fields_list(self, model_instance):
        model_class = model_instance.__class__

        # Positions:        [0]              [1]
        #           [(attribute_name, attribute_value)]

        attributes = [
            (attribute, getattr(model_class, attribute))
            for attribute in dir(model_instance)
        ]
        return [
            attribute for attribute in attributes
            if isinstance(attribute[1], orm_impl.Field)
            and not isinstance(attribute[1], orm_impl.MetaField)
            and attribute[0] != "id"
            and not attribute[0].endswith("_id")
            and not attribute[0].startswith("_")
        ]

    def _compute_all(self, fields):
        return set(map(lambda field: field[0], fields)) | {"id"}

    def _compute_required(self, fields):
        return set(
            map(lambda required_field: required_field[0],
                filter(
                    lambda field: (
                        not field[1].null
                        and field[1].default is None
                    ),
                    fields
                )
            )
        )


IntegerField = orm_impl.IntegerField

BigIntegerField = orm_impl.BigIntegerField

BooleanField = orm_impl.BooleanField

FloatField = orm_impl.FloatField

DoubleField = orm_impl.DoubleField

DecimalField = orm_impl.DecimalField

CharField = orm_impl.CharField

FixedCharField = orm_impl.FixedCharField

TextField = orm_impl.TextField

BlobField = orm_impl.BlobField

TimeField = orm_impl.TimeField

DateField = orm_impl.DateField

DateTimeField = orm_impl.DateTimeField

TimestampField = orm_impl.TimestampField

UUIDField = orm_impl.UUIDField

ForeignKeyField = orm_impl.ForeignKeyField

ManyToManyField = orm_impl.ManyToManyField

CompositeKey = orm_impl.CompositeKey
