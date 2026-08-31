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
"""Implementation of `Provider` for the base package."""

from raven.fathom.base.provider import AbstractProvider, VariableImplementation
from raven.fathom.base.system import SystemEnvironment, FileSystem, InputPrompt
from raven.fathom.base._env import HostSystemEnvironment
from raven.fathom.base._fs import HostFileSystem
from raven.fathom.base._input import SystemInputPromptStdIn
from raven.fathom.base.archive import ArchiveFile, ArchiveFileIO
from raven.fathom.base._zip import ZipArchiveFileIO
from raven.fathom.base._tar import TarArchiveFileIO, TarGzArchiveFileIO
from raven.fathom.base._tar import TarBzip2ArchiveFileIO, TarXzArchiveFileIO
from raven.fathom.base.http import ConnectionHTTP
from raven.fathom.base._net_http import ConnectionHTTPImpl
from raven.fathom.base.entropy import EntropySource
from raven.fathom.base._random import SystemRandomEntropySource


class VariableImplementationArchiveFileIO(VariableImplementation):
    """Decides what `ArchiveFileIO` implementation to use based
    on a given `ArchiveFile.Format`.
    """

    def provide(self, *args, **kwargs):
        file_format = args[0]
        if file_format == ArchiveFile.Format.ZIP:
            return ZipArchiveFileIO
        if file_format == ArchiveFile.Format.TAR:
            return TarArchiveFileIO
        if file_format == ArchiveFile.Format.TAR_GZ:
            return TarGzArchiveFileIO
        if file_format == ArchiveFile.Format.TAR_BZIP2:
            return TarBzip2ArchiveFileIO
        if file_format == ArchiveFile.Format.TAR_XZ:
            return TarXzArchiveFileIO

        raise NotImplementedError(
            "No implementation available for ArchiveFileIO "
            f"with file format '{file_format}'"
        )


class BaseProvider(AbstractProvider):
    """The `Provider` implementation for the base package."""

    def initialize_bindings(self):
        self.bind_export(SystemEnvironment, HostSystemEnvironment)
        self.bind_export(FileSystem, HostFileSystem)
        self.bind_export(InputPrompt, SystemInputPromptStdIn)
        self.bind_export(ConnectionHTTP, ConnectionHTTPImpl)
        self.bind_export(EntropySource, SystemRandomEntropySource)
        self.bind_export(ArchiveFileIO, VariableImplementationArchiveFileIO())
