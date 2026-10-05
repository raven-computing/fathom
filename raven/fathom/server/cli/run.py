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
"""CLI command handling for server runtime actions."""

from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.runtime import run_server_application


class RunServerCommand(ServerCommand):
    """Implementation of the default command that starts the HTTP server."""

    def execute(self) -> int:
        return run_server_application(self.args)
