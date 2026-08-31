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
"""ZIP archive files.

Provides an implementation of the `ArchiveFileIO` interface for reading
and writing of ZIP archive files.
"""

import zipfile

from pathlib import Path

from raven.fathom.base.archive import ArchiveFileIO, ArchiveFileIOException
from raven.fathom.base.archive import ArchiveFileMember


class ZipArchiveFileIO(ArchiveFileIO):
    """ZIP file I/O implementation."""

    def extract(self, archive, dest):
        try:
            self._extract_packed_zip(archive, dest)
        except IOError as error:
            raise ArchiveFileIOException(
                str(archive.path),
                f"Failed to extract ZIP archive file '{archive}' to '{dest}'"
            ) from error

    def compress(self, members, archive):
        try:
            self._compress_to_zip_archive(members, archive)
        except IOError as error:
            raise ArchiveFileIOException(
                str(archive.path),
                f"Failed to compress ZIP archive to file '{archive.path}'"
            ) from error

    def read_packed_members(self, archive):
        try:
            return self._read_members_from_packed_zip(archive)
        except IOError as error:
            raise ArchiveFileIOException(
                str(archive.path),
                "Failed to read member list from packed ZIP archive "
                f"'{archive.path}'"
            ) from error

    def _extract_packed_zip(self, archive, dest):
        dest_resolved = Path(dest.path).resolve()
        with zipfile.ZipFile(archive.path, "r") as zip_file:
            for member in zip_file.namelist():
                member_resolved = (dest_resolved / member).resolve()
                if not member_resolved.is_relative_to(dest_resolved):
                    raise ArchiveFileIOException(
                        str(archive.path),
                        f"Archive member path would escape destination "
                        f"directory: '{member}'"
                    )

            zip_file.extractall(path=dest.path)

    def _compress_to_zip_archive(self, members, archive):
        compression_mode = (
            zipfile.ZIP_DEFLATED
            if self._has_zlib_compression()
            else zipfile.ZIP_STORED
        )

        members_dirs = [member for member in members if member.is_directory]
        members_files = [
            member for member in members if not member.is_directory
        ]
        added_dirs = set()
        with zipfile.ZipFile(archive.path, "w", compression_mode) as zip_file:
            for member in members_files:
                file_dirs = member.name_parts[:-1]
                if file_dirs:
                    for i, _ in enumerate(file_dirs, 1):
                        dir_part = "/".join(file_dirs[:i])
                        if dir_part not in added_dirs:
                            zip_file.writestr(dir_part + "/", "")
                            added_dirs.add(dir_part)

                if member.file is not None:
                    zip_file.write(member.file.path, member.name)
                elif member.is_transient:
                    zip_file.writestr(member.name, member.data())
                else:
                    raise IOError("Invalid ArchiveFileMember")

            for member in members_dirs:
                if member.name not in added_dirs:
                    if member.file is not None:
                        zip_file.write(member.file.path, member.name)
                    elif member.is_transient:
                        zip_file.writestr(member.name + "/", "")
                    else:
                        raise IOError("Invalid ArchiveFileMember")

    def _has_zlib_compression(self):
        try:
            # pylint: disable=unused-import,import-outside-toplevel
            import zlib
            return True
        except ImportError:
            return False

    def _read_members_from_packed_zip(self, archive):
        with zipfile.ZipFile(archive.path, "r") as zip_file:
            members = []
            for file_info in zip_file.infolist():
                name = file_info.filename
                is_dir = file_info.is_dir()
                member_name = name[:-1] if is_dir else name
                member_data = None if is_dir else bytes()
                members.append(ArchiveFileMember(member_name, member_data))

            return members
