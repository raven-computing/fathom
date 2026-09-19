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
"""Data model to represent organisational settings within the Fathom server."""

from raven.fathom.server.datastore.orm import Model
from raven.fathom.server.datastore.orm import CharField, BooleanField


class Settings(Model):
    """Models Fathom server settings."""

    organisation_name = CharField()

    shared_secret = CharField()

    active = BooleanField()
