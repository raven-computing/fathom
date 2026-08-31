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
"""Provides a very simple implementation of `ArchiveFileIO` which is intended
to be used for testing purposes.
"""

import json

from raven.fathom.base.file import FileIOException
from raven.fathom.base.archive import ArchiveFileIO
from raven.fathom.base.archive import ArchiveFileMember, ArchiveFileIOException


class JsonArchiveFileIO(ArchiveFileIO):
    """Implementation of the `ArchiveFileIO` interface.

    Used for testing purposes. Even though this implementation interacts with
    the File API and not any concrete `FileSystem` implementation directly,
    it is flexible and could be used in any environment. However, it is not
    intended to be used in production. This implementation is not performant.
    """

    def extract(self, archive, dest):
        archive_files = self._read_archive(archive).get("files")
        try:
            dest.create_directory_tree()
        except FileIOException as ex:
            raise ArchiveFileIOException(
                str(archive.path),
                "Failed to extract archive: "
                "Failed to create destination directory"
            ) from ex

        for member_name, member_data in archive_files.items():
            if not isinstance(member_name, str):
                raise ArchiveFileIOException(
                    str(archive.path),
                    "Failed to extract archive: "
                    "Invalid payload member name format"
                )

            if member_data is None:
                (dest / member_name).create_directory_tree()
            elif not isinstance(member_data, str):
                raise ArchiveFileIOException(
                    str(archive.path),
                    "Failed to extract archive: "
                    "Invalid payload member data format"
                )
            else:
                member_file = dest / member_name
                member_file.get_parent_directory().create_directory_tree()
                member_file.write_all(bytes.fromhex(member_data))

    def compress(self, members, archive):
        archive_files = dict()
        archive_file_data = {
            "format": "JSON",
            "files": archive_files,
        }
        for member in members:
            if member.is_directory:
                archive_files[member.name] = None
            else:
                archive_files[member.name] = member.data().hex()

        archive.write_all(json.dumps(archive_file_data))

    def read_packed_members(self, archive):
        return [
            ArchiveFileMember(member_name)
            for member_name in self._read_archive(archive).get("files").keys()
        ]

    def _read_archive(self, archive):
        archive_data = json.loads(archive.read_all_text())
        if archive_data.get("format", "?") != "JSON":
            raise ArchiveFileIOException(
                str(archive.path),
                "Cannot extract archive with non-JSON format"
            )

        archive_files = archive_data.get("files")
        if archive_files is None:
            raise ArchiveFileIOException(
                str(archive.path),
                "Cannot extract archive: Missing files payload object"
            )

        return archive_data
