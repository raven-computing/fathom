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
"""Provides `SystemEnvironment` implementations for functionality tests.

These thin subclasses of `FunctionalityTestEnvironment` allow the
client and server to each get their own independently configurable
environment instance via the dependency injection framework.
"""

from raven.fathom.base.testing import FunctionalityTestEnvironment


class ClientEnvironment(FunctionalityTestEnvironment):
    """The `SystemEnvironment` implementation for the Fathom client
    in functionality tests.

    This environment can be configured with a custom home directory,
    current working directory, and environment variables to simulate
    the client running in an isolated filesystem location under
    the ``build/testing`` tree.
    """

    def __repr__(self):
        return (
            f"ClientEnvironment(cwd={self.cwd!r}, home={self.home!r})"
        )


class ServerEnvironment(FunctionalityTestEnvironment):
    """The `SystemEnvironment` implementation for the Fathom server
    in functionality tests.

    This environment can be configured with a custom working directory
    and environment variables to simulate the server operating in an
    isolated filesystem location under the ``build/testing`` tree.
    """

    def __repr__(self):
        return (
            f"ServerEnvironment(cwd={self.cwd!r})"
        )
