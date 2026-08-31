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
"""Implementation of `Provider` to be used in unit tests."""

from raven.fathom.base.provider import Namespace
from raven.fathom.base._provider import BaseProvider
from raven.fathom.base.system import SystemEnvironment, FileSystem, InputPrompt
from raven.fathom.base.entropy import EntropySource
from raven.fathom.base.http import ConnectionHTTP
from raven.fathom.base.archive import ArchiveFileIO
from raven.fathom.base.testing._vfs import VirtualFileSystem
from raven.fathom.base.testing._input import SystemInputPromptMock
from raven.fathom.base.testing._http import ConnectionHTTPMock
from raven.fathom.base.testing._entropy import EntropySourceMock
from raven.fathom.base.testing._env import TestEnvironment
from raven.fathom.base.testing._varchive import JsonArchiveFileIO


class UnitTestProvider(BaseProvider):
    """A `Provider` implementation to be used in unit tests."""

    def namespace(self):
        return Namespace("raven.fathom.base")

    def reusables(self):
        return [
            TestEnvironment,
            SystemInputPromptMock,
            ConnectionHTTPMock,
            EntropySourceMock,
        ]

    def initialize_bindings(self):
        super().initialize_bindings()
        self.bind_override(SystemEnvironment, TestEnvironment)
        self.bind_override(FileSystem, VirtualFileSystem)
        self.bind_override(InputPrompt, SystemInputPromptMock)
        self.bind_override(ConnectionHTTP, ConnectionHTTPMock)
        self.bind_override(EntropySource, EntropySourceMock)
        self.bind_override(ArchiveFileIO, JsonArchiveFileIO)
