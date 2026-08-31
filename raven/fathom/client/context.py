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
"""Fathom client application context."""

from raven.fathom.base import SystemEnvironment, ApplicationMode
from raven.fathom.base import File
from raven.fathom.base.decorators import noexcept
from raven.fathom.base.context import determine_application_mode
from raven.fathom.base.context import determine_working_directory


@noexcept
def determine_client_application_mode() -> ApplicationMode:
    """Determines the client application mode based on the environment.

    Returns:
        ApplicationMode: The determined application mode of the Fathom client.
    """
    return determine_application_mode(SystemEnvironment.instance())


@noexcept
def determine_client_working_directory(app_mode: ApplicationMode) -> File:
    """Determines the client working directory for the application.

    Args:
        app_mode (ApplicationMode): The application mode.

    Returns:
        File: The working directory of the Fathom client.
    """
    return determine_working_directory(SystemEnvironment.instance(), app_mode)
