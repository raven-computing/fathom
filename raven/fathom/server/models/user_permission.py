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
"""Data model to represent the permissions of users."""

from raven.fathom.server.datastore.orm import Model
from raven.fathom.server.datastore.orm import (
    BooleanField, ForeignKeyField
)
from raven.fathom.server.models.user import User


class UserPermission(Model):
    """Models a Fathom user permission."""

    user = ForeignKeyField(
        model=User,
        unique=True,
    )

    allow_overwrite = BooleanField(
        default=False,
        null=False,
    )
