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
"""Contains shared classes to represent application user entities."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


# This should be defined by the org record on the server.
USER_ONBOARDING_SHARED_SECRET: Final[str] = "whatever"


class UserState(StrEnum):
    """The lifecycle state of a dedicated application user."""

    ONBOARDING = "onboarding"

    INITIALIZED = "initialized"


@dataclass
class User:
    """A Fathom application user."""

    identifier: str

    name: str = ""

    password: str = ""

    is_admin: bool = False

    state: UserState = UserState.INITIALIZED
