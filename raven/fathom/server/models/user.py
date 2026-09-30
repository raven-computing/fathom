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
"""Data model to represent a user within the Fathom server."""

from enum import StrEnum

from raven.fathom.base import UserState

from raven.fathom.server.datastore.orm import Model
from raven.fathom.server.datastore.orm import (
    CharField, ForeignKeyField, CompositeKey
)
from raven.fathom.server.models.project import Project

# pylint: disable=missing-class-docstring


class UserRole(StrEnum):
    """Enumeration of available user roles."""

    SYSTEM = "system"

    ADMINISTRATOR = "admin"

    USER = "user"

    def has_administrative_privileges(self) -> bool:
        """Indicates whether this user role has admin privileges.
        
        Returns:
            bool: `True` if this user role can access data and perform actions
                that are reserved for administrators. `False` if this role does
                not grand such privileges.
        """
        return self in (UserRole.SYSTEM, UserRole.ADMINISTRATOR)


class User(Model):
    """Models a Fathom user."""

    identifier = CharField(
        unique=True,
        null=False,
    )

    name = CharField(
        null=False,
    )

    password = CharField(
        null=True,
    )

    role = CharField(
        null=False,
        default=UserRole.USER,
    )

    state = CharField(
        null=False,
        default=UserState.INACTIVE,
    )


class UserProjectRel(Model):
    """Models a user and project relation."""

    # Peewee does some metaclass magic, which confuses the type checker.
    class Meta: # type: ignore[reportIncompatibleVariableOverride]
        primary_key = CompositeKey("user", "project")

    user = ForeignKeyField(User)

    project = ForeignKeyField(Project)
