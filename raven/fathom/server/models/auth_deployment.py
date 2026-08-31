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
"""Data model to represent deployment authorization grants."""

from raven.fathom.server.datastore.orm import Model
from raven.fathom.server.datastore.orm import (
    BooleanField, CharField, DateTimeField, ForeignKeyField
)
from raven.fathom.server.models.project import Project
from raven.fathom.server.models.user import User


class AuthDeployment(Model):
    """Models a deployment authorization grant."""

    token = CharField(
        null=False,
        unique=True,
    )

    expiration_time = DateTimeField(
        null=False,
    )

    is_revoked = BooleanField(
        default=False,
        null=False,
    )

    user = ForeignKeyField(
        model=User,
        null=False,
    )

    project = ForeignKeyField(
        model=Project,
        null=False,
    )

    project_version = CharField(
        null=False,
    )

    allow_overwrite = BooleanField(
        default=False,
        null=False,
    )
