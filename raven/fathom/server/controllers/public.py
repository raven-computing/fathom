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
"""HTTP-server public content controller.

Content served by this controller is publicly accessible
and does not require authentication.
"""

import cherrypy

from raven.fathom.base import MethodHTTP
from raven.fathom.server.logging import Logger
from raven.fathom.server.http_tools import expose, output_json
from raven.fathom.server.version import Version


LOG = Logger.get()


class PublicController:
    """Controller for the public endpoints which require no authentication."""

    @expose(MethodHTTP.GET)
    @output_json()
    def server_version(self):
        """Controller method to query the server version."""

        version = Version.current()
        if version is None:
            LOG.e("Failed to determine server version")
            cherrypy.response.status = 500
            return {
                "status": "Failure",
            }

        return {
            "status": "OK",
            "serverVersion": {
                "identifier": str(version),
                "major": version.major,
                "minor": version.minor,
                "patch": version.patch,
            },
            "isDevelopmentVersion": version.is_development_version(),
        }
