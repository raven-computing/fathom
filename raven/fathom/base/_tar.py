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
"""TAR archive files.

Provides various implementations of the `ArchiveFileIO` interface for reading
and writing of TAR archive files, with and without compression.
"""

import io
import tarfile

from pathlib import Path

from raven.fathom.base.archive import ArchiveFileIO, ArchiveFileIOException
from raven.fathom.base.archive import ArchiveFileMember
from raven.fathom.base.file import File
from raven.fathom.base.time import SystemClock
from raven.fathom.base._env import HostSystemEnvironment


class TarArchiveFileIO(ArchiveFileIO):
    """TAR file I/O implementation.

    Base class for creating and extracting TAR archives.
    Compression capabilities is provided by specific subclasses.
    """

    def __init__(self):
        super().__init__()
        self._environment = HostSystemEnvironment()
        self._clock = SystemClock()

    def extract(self, archive, dest):
        try:
            self._extract_packed_tar(archive, dest)
        except tarfile.TarError as error:
            raise ArchiveFileIOException(
                str(archive.path),
                f"Failed to extract TAR archive file '{archive}' to '{dest}'"
            ) from error

    def compress(self, members, archive):
        try:
            self._compress_to_tar_archive(members, archive)
        except tarfile.TarError as error:
            raise ArchiveFileIOException(
                str(archive.path),
                f"Failed to compress TAR archive to file '{archive.path}'"
            ) from error

    def read_packed_members(self, archive):
        try:
            return self._read_members_from_packed_tar(archive)
        except tarfile.TarError as error:
            raise ArchiveFileIOException(
                str(archive.path),
                "Failed to read member list from packed TAR archive "
                f"'{archive.path}'"
            ) from error

    def _read_mode(self) -> str:
        return "r"

    def _write_mode(self) -> str:
        return "w"

    def _extract_packed_tar(self, archive: File, dest: File):
        dest_resolved = Path(dest.path).resolve()
        path = str(archive.path)
        mode = self._read_mode()
        with tarfile.TarFile.open(path, mode) as tar_file: # type: ignore
            for member in tar_file.getmembers():
                member_resolved = (dest_resolved / member.name).resolve()
                if not member_resolved.is_relative_to(dest_resolved):
                    raise ArchiveFileIOException(
                        str(archive.path),
                        f"Archive member path would escape destination "
                        f"directory: '{member.name}'"
                    )

            tar_file.extractall(path=dest.path, filter=tarfile.data_filter)

    def _compress_to_tar_archive(
        self,
        members: list[ArchiveFileMember],
        archive: File
    ):
        # This needs to be refactored!
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements,duplicate-code
        members_dirs = [member for member in members if member.is_directory]
        members_files = [
            member for member in members if not member.is_directory
        ]
        added_dirs = set()
        user_id = self._environment.get_user_id()
        user_name = self._environment.get_user_name()
        archiving_time = int(self._clock.current_time().timestamp())
        path = str(archive.path)
        mode = self._write_mode()
        with tarfile.TarFile.open(path, mode) as tar_file: # type: ignore
            for member in members_files:
                file_dirs = member.name_parts[:-1]
                if file_dirs:
                    for i, _ in enumerate(file_dirs, 1):
                        dir_part = "/".join(file_dirs[:i])
                        if dir_part not in added_dirs:
                            dir_info = tarfile.TarInfo(name=dir_part + "/")
                            dir_info.type = tarfile.DIRTYPE
                            dir_info.mode = 0o775
                            if user_id is not None:
                                dir_info.uid = user_id
                            if user_name is not None:
                                dir_info.uname = user_name
                            dir_info.mtime = archiving_time
                            tar_file.addfile(dir_info)
                            added_dirs.add(dir_part)

                if member.file is not None:
                    tar_file.add(member.file.path, arcname=member.name)
                elif member.is_transient:
                    file_data = member.data()
                    file_info = tarfile.TarInfo(name=member.name)
                    file_info.size = len(file_data)
                    file_info.type = tarfile.REGTYPE
                    file_info.mode = 0o664
                    if user_id is not None:
                        file_info.uid = user_id
                    if user_name is not None:
                        file_info.uname = user_name
                    file_info.mtime = archiving_time
                    tar_file.addfile(file_info, io.BytesIO(file_data))
                else:
                    raise ArchiveFileIOException(
                        str(archive.path),
                        "Invalid ArchiveFileMember"
                    )

            for member in members_dirs:
                if member.name not in added_dirs:
                    if member.file is not None:
                        tar_file.add(member.file.path, arcname=member.name)
                    elif member.is_transient:
                        dir_info = tarfile.TarInfo(name=member.name + "/")
                        dir_info.type = tarfile.DIRTYPE
                        dir_info.mode = 0o775
                        if user_id is not None:
                            dir_info.uid = user_id
                        if user_name is not None:
                            dir_info.uname = user_name
                        dir_info.mtime = archiving_time
                        tar_file.addfile(dir_info)
                    else:
                        raise ArchiveFileIOException(
                            str(archive.path),
                            "Invalid ArchiveFileMember"
                        )

    def _read_members_from_packed_tar(
        self,
        archive: File
    ) -> list[ArchiveFileMember]:
        path = str(archive.path)
        mode = self._read_mode()
        with tarfile.TarFile.open(path, mode) as tar_file: # type: ignore
            members = []
            for file_info in tar_file.getmembers():
                name = file_info.name
                is_dir = file_info.isdir()
                member_name = (
                    name[:-1]
                    if is_dir and name.endswith("/")
                    else name
                )
                member_data = None if is_dir else bytes()
                members.append(ArchiveFileMember(member_name, member_data))

            return members


class TarGzArchiveFileIO(TarArchiveFileIO):
    """GZIP-compressed TAR file I/O implementation."""

    def _read_mode(self):
        return "r:gz"

    def _write_mode(self):
        return "w:gz"


class TarBzip2ArchiveFileIO(TarArchiveFileIO):
    """BZIP2-compressed TAR file I/O implementation."""

    def _read_mode(self):
        return "r:bz2"

    def _write_mode(self):
        return "w:bz2"


class TarXzArchiveFileIO(TarArchiveFileIO):
    """XZ-compressed (LZMA) TAR file I/O implementation."""

    def _read_mode(self):
        return "r:xz"

    def _write_mode(self):
        return "w:xz"
