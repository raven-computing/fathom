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
"""Fathom: Manage the Release of Documentation.

This is the client API.
"""

from raven.fathom.base import FileSize
from raven.fathom.base import FileSizeUnit
from raven.fathom.base import Project, ProjectVersion
from raven.fathom.base import Dependencies as _Dependencies

from .deployment import DeploymentResult
from .deployment import FathomDeployment
from .documentation import DocumentationResource
from .documentation import DocsFile
from .documentation import DocsDir
from .locator import ServerLocator
from .exceptions import FathomClientException
from .filter import FileFilter
from .filter import FileSizeRange, UNBOUND_FILE_SIZE
from .version import Version

from ._provider import ClientProvider as _ProviderImpl

_Dependencies.register(_ProviderImpl())
del _ProviderImpl
del _Dependencies
