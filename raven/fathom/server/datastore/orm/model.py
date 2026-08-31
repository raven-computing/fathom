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

import peewee as orm_impl

from raven.fathom.server.datastore._proxy import get_orm_proxy
from raven.fathom.server.datastore.orm.field import FieldChecker

# pylint: disable=C0115


class _BaseModel(orm_impl.Model):
    class Meta:
        database = get_orm_proxy()
        legacy_table_names = False


class _DataModelORM(_BaseModel):

    def __init__(self, *args, **kwargs):
        if not FieldChecker.has_checker(self):
            FieldChecker.assign_checker(self)

        field_checker = FieldChecker.get_checker(self)
        field_checker.check_known(**kwargs)
        field_checker.check_required(**kwargs)

        super().__init__(*args, **kwargs)


class Model(_DataModelORM):
    """An ORM data model for persistence.

    Concrete data models should inherit from this class and define their
    fields as class attributes.
    """
