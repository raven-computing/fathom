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
"""ORM model declarations."""

from datetime import datetime
from typing import TypeVar

import peewee as orm_impl

from raven.fathom.base import SystemClock
from raven.fathom.server.datastore._proxy import get_orm_proxy
from raven.fathom.server.datastore.orm.field import RecordId, OrmRecordId
from raven.fathom.server.datastore.orm.field import FieldChecker


def _apply_private_field_mapping(fields: set[str], kwargs: dict):
    """Maps public to private model fields in kwargs."""
    for field_name in fields:
        if field_name.startswith("_"):
            private_name = field_name
            public_name = field_name[1:]
            if public_name in kwargs and private_name not in kwargs:
                kwargs[private_name] = kwargs.pop(public_name)


def _timestamp_field_current_time() -> datetime:
    return SystemClock().current_time()


class _BaseModel(orm_impl.Model):
    # pylint: disable=missing-class-docstring
    class Meta:
        database = get_orm_proxy()
        legacy_table_names = False


class _DataModelORM(_BaseModel):

    def __init__(self, *args, **kwargs):
        if not FieldChecker.has_checker(self):
            FieldChecker.assign_checker(self)

        field_checker = FieldChecker.get_checker(self)
        _apply_private_field_mapping(field_checker.get_all_fields(), kwargs)
        field_checker.check_known(**kwargs)
        field_checker.check_required(**kwargs)

        super().__init__(*args, **kwargs)

    _created_at = orm_impl.DateTimeField(
        column_name="created_at",
        default=_timestamp_field_current_time,
    )

    _updated_at = orm_impl.DateTimeField(
        column_name="updated_at",
        default=_timestamp_field_current_time,
    )

    @property
    def created_at(self) -> datetime:
        """The time when this record was created, as a `datetime` object."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """The time when this record was last updated,
        as a `datetime` object.
        """
        return self._updated_at

    @property
    def datastore_id(self) -> RecordId:
        """The internal datastore ID of this record."""
        # pylint: disable=no-member
        raw_id = self.id # pyright: ignore[reportAttributeAccessIssue]
        return OrmRecordId(raw_id)

    def touch(self):
        """Updates the modification time of this record to the current time."""
        self._updated_at = _timestamp_field_current_time()


class Model(_DataModelORM):
    """An ORM data model for persistence.

    Concrete data models should inherit from this class and define their
    fields as class attributes.
    """

M = TypeVar("M", bound=Model)
