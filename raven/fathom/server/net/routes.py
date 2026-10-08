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
"""Definition of the Fathom `ServerApplication` with its exposed routes."""

from raven.fathom.server.net.http import ServerApplication
from raven.fathom.server.net.defaults import SERVER_ROOT_PATH_V1
from raven.fathom.server.controllers import InteractionController
from raven.fathom.server.controllers import PublicController
from raven.fathom.server.controllers import SignupController


class FathomServer(ServerApplication):
    """The Fathom server application."""

    def __init__(self):
        super().__init__()
        self.public = PublicController()
        self.user = SignupController()
        self.interact = InteractionController()

    def root_path(self):
        return SERVER_ROOT_PATH_V1
