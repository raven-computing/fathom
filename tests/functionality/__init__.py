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
"""Fathom functionality tests.

Contains end-to-end tests that exercise the Fathom client and server
working together. All filesystem operations are confined to the
``build/testing`` directory within the project root directory.

Provider overrides are registered at import time so that both the client
and server receive their own test-specific `SystemEnvironment` instances.
"""

from raven.fathom.base import Dependencies

from .common import TestCase
from .common import clean_testing_directory
from ._provider import ClientFunctionalityTestProvider
from ._provider import ServerFunctionalityTestProvider

Dependencies.register_override(ClientFunctionalityTestProvider())
Dependencies.register_override(ServerFunctionalityTestProvider())

del Dependencies
del ClientFunctionalityTestProvider
del ServerFunctionalityTestProvider
