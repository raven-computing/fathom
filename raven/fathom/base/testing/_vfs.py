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
"""Interactions with an in-memory virtual filesystem.

This can be used during testing.
Implements the `FileSystem` interface.
"""

import datetime
import platform

from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import Optional, Final, Union

from raven.fathom.base.system import FileSystem
from raven.fathom.base.file import FileMode, FileType
from raven.fathom.base.file import FilePermission, FileAccess
from raven.fathom.base.file import (
    InvalidFileModeException, CannotOpenFileException,
    CannotCloseFileException, FileNotFoundException, FilePermissionException,
    FilePositioningException, FileLockAcquisitionException, FileReadException,
    SymbolicLinkResolutionException, DirectoryListingException,
    FileModificationException, FileWriteException, FileRelocationException,
    FileCopyException, FileRemovalException, FileCreationException,
    TemporaryFileCreationException
)

# Some of the code in this module is intentionally similar to
# the implementation for host system interaction, for example to have
# consistent error handling behaviour and error messages.
# pylint: disable=duplicate-code


_IS_OS_WINDOWS: Final[bool] = platform.system() == "Windows"

_INTERNAL_ROOT_POSIX: Final[str] = "/"

_INTERNAL_ROOT_WINDOWS: Final[str] = "/C:"

_INTERNAL_PATH_SEPARATOR: Final[str] = "/"

_HOST_ROOT_WINDOWS: Final[str] = "C:\\"

_DRIVE_SEPARATOR: Final[str] = ":"

_INTERNAL_TEMP_DIR_POSIX: Final[str] = "/tmp"

_INTERNAL_TEMP_DIR_WINDOWS: Final[str] = _INTERNAL_ROOT_WINDOWS + "/tmp"


def _has_win32_drive(posix_path_str: str) -> bool:
    return (
        len(posix_path_str) >= 3
        and posix_path_str[0] == _INTERNAL_ROOT_POSIX
        and posix_path_str[1].isalpha()
        and posix_path_str[2] == ":"
    )


def _to_posix(path) -> PurePosixPath:
    """Converts a path to internal POSIX format.

    On Windows, converts paths like 'C:\\Users\\Me\\example.txt'
    to '/C:/Users/Me/example.txt'. On other systems, returns the
    path unchanged.

    Special case on Windows: POSIX-style absolute paths without drive
    letters (e.g. '/this/is/an/absolute/path') are treated as paths under
    the 'C:' drive to allow users to write platform-independent test code
    when using a virtual filesystem. Otherwise, given the previous example,
    a test case that required absolute paths would not work both on POSIX
    as well as Windows systems because on Windows the example path would
    be treated as a relative path. Windows allows the use of forward slashes
    as path separators, but a path starting with '/' is still a relative path
    since it does not specify a drive. Therefore, in the given example, the
    path will be converted internally to '/C:/this/is/an/absolute/path'.
    """
    if isinstance(path, PurePosixPath):
        return path

    path = PurePath(path)
    posix_str = path.as_posix()
    if not _IS_OS_WINDOWS:
        return PurePosixPath(posix_str)

    if posix_str == _INTERNAL_ROOT_POSIX:
        return PurePosixPath(_INTERNAL_ROOT_POSIX)

    if _has_win32_drive(posix_str):
        return PurePosixPath(posix_str)

    if not path.drive and posix_str.startswith(_INTERNAL_ROOT_POSIX):
        return PurePosixPath(f"{_INTERNAL_ROOT_WINDOWS}{posix_str}")

    if path.drive:
        drive = path.drive.rstrip(_DRIVE_SEPARATOR)
        subpath = posix_str[len(path.drive):]
        return PurePosixPath(
            f"{_INTERNAL_ROOT_POSIX}{drive}{_DRIVE_SEPARATOR}{subpath}"
        )

    return PurePosixPath(posix_str)


def _from_posix(posix_path: PurePosixPath) -> PurePath:
    """Converts an internal POSIX path back to the platform format.

    On Windows, converts paths like '/C:/Users/Me/example.txt' back
    to 'C:\\Users\\Me\\example.txt'. On other systems, returns the
    path unchanged.
    """
    if not _IS_OS_WINDOWS:
        return PurePath(posix_path)

    posix_str = str(posix_path)
    if posix_str in (_INTERNAL_ROOT_POSIX, _INTERNAL_ROOT_WINDOWS):
        return PureWindowsPath(_HOST_ROOT_WINDOWS)

    if _has_win32_drive(posix_str):
        drive = posix_str[1]
        subpath = posix_str[3:]
        return PureWindowsPath(f"{drive}{_DRIVE_SEPARATOR}{subpath}")

    return PureWindowsPath(posix_str)


class _VirtualFile:

    def __init__(
        self,
        path: PurePosixPath,
        file_type: FileType,
        data: Optional[Union[bytearray, PurePosixPath]]
    ):
        self.path = path
        self.file_type = file_type
        self.data = data
        self.perm = FilePermission.of(
            owner=FileAccess.all_access(),
            group=FileAccess.all_access(),
            other=FileAccess.of(readable=True, executable=True)
        ) if file_type == FileType.DIRECTORY else FilePermission.of(
            owner=FileAccess.of(readable=True, writable=True),
            group=FileAccess.of(readable=True, writable=True),
            other=FileAccess.of(readable=True)
        )
        self.uid = 1000
        self.owner = "user"
        self.gid = 1000
        self.group = "user"
        self.t_last_mod = datetime.datetime(
            year=2022, month=5, day=25,
            hour=14, minute=15, second=16,
            tzinfo=datetime.UTC,
        )


class _VirtualFileHandle:

    def __init__(self, file: _VirtualFile, mode: FileMode):
        self.file = file
        self.buffer = None
        self.mode = mode
        self.is_open = True
        self.pos = 0
        if file.file_type == FileType.REGULAR_FILE:
            assert isinstance(file.data, bytearray)
            self.buffer = file.data.copy()

        if mode.can_append():
            assert isinstance(file.data, bytearray)
            self.pos = len(file.data)


class VirtualFileSystem(FileSystem):
    """A virtual filesystem.

    An implementation of `FileSystem` that does not interoperate with the
    actual host filesystem but rather creates its own file tree purely
    in memory. Some methods and behaviours might slightly deviate from the
    expected behaviour of an actual filesystem, For instance, when creating
    a file of any type, any missing parent directories might automatically be
    created. This is so that entire file trees can be created more easily for
    testing purposes. A virtual filesystem does not implement any file access
    control. All methods declared by the `FileSystem` interface are
    implemented, but it is not checked whether the user making a method call is
    allowed to interact with a specific file. For example, file permissions may
    be changed by anyone.
    """

    def __init__(self):
        self._files: dict[str, _VirtualFile] = dict()
        self._temp_file_counter = 0
        self._cwd = PurePosixPath(_INTERNAL_ROOT_POSIX)
        self.flush_system()

    def init_path(self, path):
        return _from_posix(_to_posix(path))

    def check_exists(self, path, check_symlink=True):
        fs_path = _to_posix(path)
        try:
            fs_path = self._resolve_symlinks_in_path(fs_path, head=False)
        except SymbolicLinkResolutionException:
            return False

        try:
            return self._get_node(fs_path) is not None
        except SymbolicLinkResolutionException:
            return not check_symlink

    def check_is_hidden(self, path):
        fs_path = _to_posix(path)
        if not self.check_exists(fs_path, check_symlink=False):
            raise FileNotFoundException(
                str(path),
                f"Failed to check if file is hidden. "
                f"No such file or directory: '{path}'"
            )

        return str(fs_path.name).startswith(".")

    def set_hidden(self, path, hidden):
        fs_path = _to_posix(path)
        if self.check_exists(fs_path, check_symlink=False):
            is_hidden = self.check_is_hidden(fs_path)
            if hidden and not is_hidden:
                hidden_name = PurePath("." + fs_path.name)
                hidden_file = self.get_parent_path(fs_path) / hidden_name
                self.move(fs_path, hidden_file, follow_symlinks=False)
                return _from_posix(_to_posix(hidden_file))

            if not hidden and is_hidden:
                hidden_name = fs_path.name
                unhidden_file = self.get_parent_path(fs_path) / hidden_name[1:]
                self.move(fs_path, unhidden_file, follow_symlinks=False)
                return _from_posix(_to_posix(unhidden_file))

        return _from_posix(fs_path)

    def get_parent_path(self, path):
        fs_path = _to_posix(path)
        return _from_posix(fs_path.parent)

    def get_size(self, path):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks=True)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to query size of file '{path}': "
                "File does not exist"
            )

        if vf.file_type == FileType.REGULAR_FILE:
            assert isinstance(vf.data, bytearray)
            return len(vf.data)

        if vf.file_type == FileType.DIRECTORY:
            return sum(
                self.get_size(file.path)
                for file in self._get_adjacent_child_nodes(fs_path)
            )

        return 4096  # For other file types

    def check_is_empty(self, path):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks=True)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to query size of file '{path}': "
                "File does not exist"
            )

        if vf.file_type == FileType.REGULAR_FILE:
            assert isinstance(vf.data, bytearray)
            return len(vf.data) == 0

        if vf.file_type == FileType.DIRECTORY:
            return len(self._get_adjacent_child_nodes(fs_path)) == 0

        return False  # For other file types

    def get_type(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to obtain type of file '{path}': "
                "No such file or directory"
            )

        return (vf and vf.file_type) or FileType.UNKNOWN

    def open_file_object(self, path, mode):
        fs_path = _to_posix(path)
        if not isinstance(mode, FileMode):
            raise InvalidFileModeException(
                str(path),
                f"Failed to open file '{path}' with "
                f"given mode '{mode}': "
                f"Expected FileMode but found {type(mode)}"
            )

        vf = self._get_node(
            self.resolve_symbolic_links(fs_path),
            follow_symlinks=False
        )
        if vf is None and mode.can_create():
            self.create_regular_file(fs_path)
            vf = self._get_node(fs_path, follow_symlinks=False)
        elif mode in (FileMode.CREATE, FileMode.CREATE_WRITE):
            raise CannotOpenFileException(
                str(path),
                f"Failed to open file '{path}' in mode '{mode}': "
                "File exists"
            )

        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to open file '{path}' in "
                f"mode '{mode}': File does not exist"
            )

        if vf.file_type != FileType.REGULAR_FILE:
            f_type = self._vf_file_type_to_str(vf)
            raise CannotOpenFileException(
                str(path),
                f"Cannot open file '{vf.path}' of type {f_type}"
            )

        if mode.can_read() and not vf.perm.owner.can_read:
            raise FilePermissionException(
                str(path),
                f"Failed to read file '{path}': "
                "Permission denied"
            )

        write_requested = mode.can_write() or mode.can_append()
        if write_requested and not vf.perm.owner.can_write:
            raise FilePermissionException(
                str(path),
                f"Failed to write file '{path}': "
                "Permission denied"
            )

        if mode in (FileMode.WRITE, FileMode.CREATE_READ_WRITE):
            # Overwrite file content
            vf.data = bytearray()

        return _VirtualFileHandle(vf, mode)

    def close_file_object(self, handle):
        try:
            self.flush_file_object(handle)
        except FileWriteException as ex:
            raise CannotCloseFileException(
                str(handle.file.path),
                f"Failed to flush data buffer to file. {ex}"
            )

        handle.is_open = False

    def read_from_file_object(self, handle, n_bytes=-1):
        if not handle.is_open:
            raise FileReadException(
                str(handle.file.path),
                f"Failed to read file '{handle.file.path}': "
                "File is not open"
            )

        vf = handle.file
        if vf is None:
            raise FileReadException(
                str(handle.file.path),
                f"Failed to read file '{handle.file.path}' in "
                f"mode '{handle.mode}': File does not exist"
            )

        if vf.file_type == FileType.DIRECTORY:
            raise FileReadException(
                str(handle.file.path),
                f"Failed to read file '{handle.file.path}' in "
                f"mode '{handle.mode}': File is a directory"
            )

        read_data = bytes()
        file_buffer = handle.buffer
        if n_bytes < 0:
            read_data = bytes(file_buffer[handle.pos:])
            n_bytes = len(file_buffer) - handle.pos
            handle.pos += n_bytes
        elif handle.pos < len(file_buffer):
            upper_bound = min(handle.pos + n_bytes, len(file_buffer))
            n_bytes = upper_bound - handle.pos
            read_data = bytes(file_buffer[handle.pos:upper_bound])
            handle.pos += n_bytes

        return read_data

    def write_to_file_object(self, handle, data):
        if not handle.is_open:
            raise FileWriteException(
                str(handle.file.path),
                f"Failed to write to file '{handle.file.path}': "
                "File is not open"
            )

        if not (handle.mode.can_write() or handle.mode.can_append()):
            raise FileWriteException(
                str(handle.file.path),
                f"Failed to write to file '{handle.file.path}' in "
                f"mode '{handle.mode}': Unsupported operation"
            )

        vf = handle.file
        if vf.file_type != FileType.REGULAR_FILE:
            raise FileWriteException(
                str(handle.file.path),
                f"Failed to write to file '{handle.file.path}' in "
                f"mode '{handle.mode}': "
                f"Cannot write to file of type {vf.file_type}"
            )

        n_bytes = len(data)
        file_buffer = handle.buffer
        if handle.mode.can_write():
            file_buffer[handle.pos:(handle.pos + n_bytes)] = data
        else:  # Append
            file_buffer.extend(data)

        handle.pos += n_bytes
        return n_bytes

    def flush_file_object(self, handle):
        if not handle.is_open:
            raise FileWriteException(
                str(handle.file.path),
                f"Cannot flush file '{handle.file.path}': "
                "File is not open"
            )

        handle.file.data = handle.buffer.copy()

    def get_file_object_position(self, handle):
        if not handle.is_open:
            raise FilePositioningException(
                str(handle.file.path),
                f"Failed to obtain position of file '{handle.file.path}': "
                "File is not open"
            )

        return handle.pos

    def set_file_object_position(self, handle, new_pos):
        if not handle.is_open:
            raise FilePositioningException(
                str(handle.file.path),
                f"Failed to set position of file at '{handle.file.path}': "
                "File is not open"
            )

        if new_pos < 0:
            raise FilePositioningException(
                str(handle.file.path),
                f"Cannot set position of file at '{handle.file.path}': "
                f"Invalid file position {new_pos}"
            )

        handle.pos = new_pos

    def rewind_file_object_position(self, handle):
        if not handle.is_open:
            raise FilePositioningException(
                str(handle.file.path),
                f"Failed to rewind position of file at '{handle.file.path}': "
                "File is not open"
            )

        handle.pos = 0

    def resize_file_object(self, handle, size=None):
        if not handle.is_open:
            raise FileWriteException(
                str(handle.file.path),
                f"Failed to resize file '{handle.file.path}': "
                "File is not open"
            )

        if size is not None and size < 0:
            raise FileWriteException(
                str(handle.file.path),
                f"Cannot resize file '{handle.file.path}'. "
                f"Invalid file size: {size}"
            )

        if not handle.mode.can_write():
            raise FileWriteException(
                str(handle.file.path),
                f"Failed to resize file '{handle.file.path}' in "
                f"mode '{handle.mode}': Unsupported operation"
            )

        resize_pos = handle.pos if size is None else size
        file_buffer = handle.buffer
        data_size = len(file_buffer)
        if resize_pos > data_size:
            file_buffer.extend(b"\x00" * (resize_pos - data_size))
        else:
            handle.buffer = file_buffer[:resize_pos]

        self.flush_file_object(handle)

    def check_file_access(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to obtain access capabilities for file '{path}': "
                "No such file or directory"
            )

        # Assume user == owner
        user_perms = vf.perm.owner
        return FileAccess.of(
            readable=user_perms.can_read,
            writable=user_perms.can_write,
            executable=user_perms.can_execute
        )

    def get_file_permissions(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to read file permission for file '{path}': "
                "File does not exist"
            )

        ow = vf.perm.owner
        gr = vf.perm.group
        ot = vf.perm.other
        return FilePermission.of(
            owner=FileAccess.of(ow.can_read, ow.can_write, ow.can_execute),
            group=FileAccess.of(gr.can_read, gr.can_write, gr.can_execute),
            other=FileAccess.of(ot.can_read, ot.can_write, ot.can_execute)
        )

    def set_file_permissions(self, path, permissions, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to set file permission to {permissions} "
                f"for file '{path}': "
                "File does not exist"
            )

        vf.perm = FilePermission.of(
            owner=FileAccess.of(
                permissions.owner.can_read,
                permissions.owner.can_write,
                permissions.owner.can_execute
            ),
            group=FileAccess.of(
                permissions.group.can_read,
                permissions.group.can_write,
                permissions.group.can_execute
            ),
            other=FileAccess.of(
                permissions.other.can_read,
                permissions.other.can_write,
                permissions.other.can_execute
            )
        )

    def get_file_owner_uid(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to get file owner UID for file '{path}': "
                "File does not exist"
            )

        return vf.uid

    def get_file_owner_name(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to get file owner name for file '{path}': "
                "File does not exist"
            )

        return vf.owner

    def get_file_group_gid(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to get file group GID for file '{path}': "
                "File does not exist"
            )

        return vf.gid

    def get_file_group_name(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to get file group name for file '{path}': "
                "File does not exist"
            )

        return vf.group

    def get_file_last_modification_time(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to get last modification time for file '{path}': "
                "File does not exist"
            )

        return vf.t_last_mod

    def create_regular_file(self, path):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks=False)
        if vf is not None and vf.file_type != FileType.REGULAR_FILE:
            f_type = self._vf_file_type_to_str(vf)
            raise FileCreationException(
                str(path),
                f"Failed to create regular file at '{path}': "
                f"File already exists but is {f_type}"
            )

        self._add_node(fs_path, FileType.REGULAR_FILE, data=bytearray())

    def create_directory(self, path):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path)
        if vf is not None and vf.file_type != FileType.DIRECTORY:
            f_type = self._vf_file_type_to_str(vf)
            raise FileCreationException(
                str(path),
                f"Failed to create directory '{path}': "
                f"File already exists but is {f_type}"
            )

        if (fs_path.as_posix() != _INTERNAL_ROOT_POSIX
            and self._get_node(fs_path.parent) is None):
            raise FileNotFoundException(
                str(path),
                f"Failed to create directory '{path}' "
                "because its parent does not exist"
            )

        try:
            self._add_node(fs_path, FileType.DIRECTORY, data=None)
        except FileCreationException:
            raise FileCreationException(
                str(path),
                f"Failed to create directory '{path}': "
                "Parent file already exists but is not a directory"
            ) from None

    def create_directories(self, path):
        fs_path = _to_posix(path)
        parts = fs_path.parts
        if len(parts) > 0 and parts[0] == _INTERNAL_ROOT_POSIX:
            parts = parts[1:]

        for i, _ in enumerate(parts, 1):
            part = _INTERNAL_ROOT_POSIX + _INTERNAL_PATH_SEPARATOR.join(
                parts[:i]
            )
            vf = self._files.get(part)
            if vf is None:
                try:
                    self._create_vf_directory(part)
                except FilePermissionException as ex:
                    raise FilePermissionException(
                        str(path),
                        f"Failed to create directory '{path}' "
                        f"or one of its parents: {ex}"
                    ) from None
            elif vf.file_type != FileType.DIRECTORY:
                raise FileCreationException(
                    str(path),
                    f"Failed to create directory '{vf.path}': "
                    "File already exists but is not a directory"
                )

    def create_symbolic_link(self, path, target):
        fs_path = _to_posix(path)
        posix_target = _to_posix(target)
        if self._get_node(fs_path, follow_symlinks=False) is not None:
            raise FileCreationException(
                str(path),
                f"Failed to create symbolic link at '{path}': "
                "File already exists"
            )

        self._add_node(fs_path, FileType.SYMBOLIC_LINK, data=posix_target)

    def get_symbolic_link_target(self, path, absolute=False):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks=False)
        if self._is_virtual_symlink(vf):
            assert vf is not None
            target_path = vf.data
            assert isinstance(target_path, PurePosixPath)
            if absolute and not _to_posix(target_path).is_absolute():
                target_path = vf.path.parent / target_path

            return _from_posix(_to_posix(target_path))

        return path

    def resolve_symbolic_links(self, path):
        resolved = self._resolve_symlinks_in_path(path)
        return _from_posix(_to_posix(resolved))

    def touch_file(self, path):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path)
        if vf is None:
            self.create_regular_file(fs_path)
        else:
            try:
                vf.t_last_mod = datetime.datetime.now(datetime.UTC)
            except Exception as ex:
                raise FileModificationException(
                    str(path),
                    f"Failed to touch file '{path}': {ex}"
                ) from None

    def move(self, source, target, follow_symlinks=True):
        fs_source = _to_posix(source)
        fs_target = _to_posix(target)
        vf = self._get_node(fs_source, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(source),
                f"Failed to move file '{source}' "
                f"to destination at '{target}': "
                "File does not exist"
            )

        vf_children = list(self._get_child_nodes(fs_source))
        try:
            self.remove(fs_source, follow_symlinks)
        except FileRemovalException:
            raise FileRelocationException(
                str(source),
                f"Failed to move file '{source}' to "
                f"destination at '{target}'"
            )

        vf.path = fs_target
        len_src = len(str(fs_source))
        target_base = str(fs_target)
        self._link_vf(vf)
        for vf_child in vf_children:
            child_relative = str(vf_child.path)[len_src:]
            vf_child.path = PurePosixPath(target_base + child_relative)
            self._link_vf(vf_child)

    def copy(self, source, target, follow_symlinks=True):
        fs_source = _to_posix(source)
        fs_target = _to_posix(target)
        vf_source = self._get_node(fs_source, follow_symlinks)
        if vf_source is None:
            raise FileNotFoundException(
                str(source),
                f"Failed to copy file '{source}' to "
                f"destination at '{target}': File does not exist"
            )

        source_type = vf_source.file_type
        if source_type not in (FileType.REGULAR_FILE, FileType.DIRECTORY):
            raise FileCopyException(
                str(source),
                f"Cannot copy file '{source}' of type {source_type}. "
                "Only regular files and directories can be copied"
            )

        vf_target = self._get_node(fs_target)
        if vf_target is not None:
            target_type = vf_target.file_type
            if source_type != target_type:
                raise FileCopyException(
                    str(source),
                    f"Cannot copy file '{source}' of type {source_type} "
                    f"to destination at '{target}'. File at destination "
                    f"already exists but is of type {target_type}"
                )

        if source_type == FileType.DIRECTORY:
            if vf_target is None:
                self._add_node(
                    fs_target,
                    FileType.DIRECTORY,
                    data=None
                )

            base_src = str(vf_source.path) + _INTERNAL_PATH_SEPARATOR
            for vf_child in self._get_child_nodes(vf_source.path):
                subpath_child = str(vf_child.path)[len(base_src):]
                if vf_child.file_type == FileType.SYMBOLIC_LINK:
                    try:
                        vf_child = self._get_node(vf_child.path)
                    except SymbolicLinkResolutionException as ex:
                        raise FileCopyException(
                            str(source),
                            f"Failed to copy file '{source}' "
                            f"to destination at '{target}'. {ex}"
                        ) from None

                assert vf_child is not None
                self._add_node(
                    PurePosixPath(f"{fs_target.as_posix()}/{subpath_child}"),
                    vf_child.file_type,
                    data=(
                        vf_child.data.copy() # type: ignore
                        if vf_child.file_type == FileType.REGULAR_FILE
                        else vf_child.data
                    )
                )
        else:
            if vf_target is None:
                self._add_node(
                    fs_target,
                    vf_source.file_type,
                    data=vf_source.data
                )
            else:
                assert isinstance(vf_source.data, bytearray)
                vf_target.data = vf_source.data.copy()

    def remove(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        vf = self._get_node(fs_path, follow_symlinks)
        if vf is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to remove file '{path}': "
                "File does not exist"
            )

        vf_symlink = self._get_node(fs_path, follow_symlinks=False)
        assert vf_symlink is not None
        remove_vf_symlink = vf_symlink.file_type == FileType.SYMBOLIC_LINK
        for child_vf in list(self._get_child_nodes(vf.path)):
            self._delete_node(child_vf)

        self._delete_node(vf)
        if follow_symlinks and remove_vf_symlink:
            self._delete_node(vf_symlink)

    def list_files_of_directory(self, path, recursive=False):
        fs_path = _to_posix(path)
        vf_dir = self._get_node(fs_path)
        if vf_dir is None:
            raise FileNotFoundException(
                str(path),
                f"Failed to generate listing for directory '{path}': "
                "Directory does not exist"
            )

        if vf_dir.file_type != FileType.DIRECTORY:
            raise DirectoryListingException(
                str(path),
                "Cannot generate directory listing for "
                f"non-directory file: '{path}'"
            )

        if recursive:
            return (
                _from_posix(vf.path)
                for vf in self._get_child_nodes(vf_dir.path)
            )

        return (
            _from_posix(vf.path)
            for vf in self._get_adjacent_child_nodes(vf_dir.path)
        )

    def flush_system(self):
        self._files.clear()
        self._temp_file_counter = 0
        self.create_directory(PurePosixPath(_INTERNAL_ROOT_POSIX))
        if _IS_OS_WINDOWS:
            self.create_directory(PurePosixPath(_INTERNAL_ROOT_WINDOWS))

    def get_lock_file_path(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        if follow_symlinks:
            fs_path = _to_posix(self.resolve_symbolic_links(fs_path))

        lock_path = fs_path.with_name(
            self._get_lock_file_name_for(fs_path.name)
        )
        return _from_posix(lock_path)

    def lock_file(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        if follow_symlinks:
            fs_path = _to_posix(self.resolve_symbolic_links(fs_path))

        lock_file_path = fs_path.with_name(
            self._get_lock_file_name_for(fs_path.name)
        )
        vf_lock = self._get_node(lock_file_path, follow_symlinks=False)
        if vf_lock is not None:
            raise FileLockAcquisitionException(
                str(path),
                f"File is already locked: '{path}'"
            )

        vf_parent = self._get_node(fs_path.parent, follow_symlinks=False)
        if vf_parent is None :
            raise FileNotFoundException(
                str(path),
                f"Failed to acquire lock for file '{path}'. "
                "It is required that the parent directory of the file exists "
                "and is writable in order to acquire a lock: "
                "Parent directory does not exist"
            )

        if not vf_parent.perm.owner.can_write:
            raise FilePermissionException(
                str(path),
                f"Failed to acquire lock for file '{path}'. "
                "It is required that the parent directory of the file exists "
                "and is writable in order to acquire a lock: Permission denied"
            )

        self._add_node(lock_file_path, FileType.REGULAR_FILE, data=bytearray())

    def unlock_file(self, path, follow_symlinks=True):
        fs_path = _to_posix(path)
        if follow_symlinks:
            fs_path = _to_posix(self.resolve_symbolic_links(fs_path))

        lock_file_path = fs_path.with_name(
            self._get_lock_file_name_for(fs_path.name)
        )
        vf_lock = self._get_node(lock_file_path, follow_symlinks=False)
        if vf_lock is not None:
            self._delete_node(vf_lock)

    def create_temp_file(self, directory=None, prefix=None, suffix=None):
        prefix = prefix or ""
        suffix = suffix or ""
        if directory is None:
            directory = self.create_temp_dir()

        fs_directory = _to_posix(directory)
        if self._get_node(directory) is None:
            raise FileNotFoundException(
                str(directory),
                "Failed to create temporary file because "
                f"the specified parent directory '{directory}' does not exist"
            )

        tmpvf_name = prefix + str(self._temp_file_counter) + suffix
        tmpvf_path = fs_directory / PurePosixPath(tmpvf_name)
        try:
            self._add_node(tmpvf_path, FileType.REGULAR_FILE, data=bytearray())
        except FileCreationException as ex:
            hint = "" if directory is None else f" in directory '{directory}'"
            msg = f"Failed to create temporary file{hint}"
            raise TemporaryFileCreationException(
                file_path=None,
                message=f"{msg}: {ex}"
            )

        self._temp_file_counter += 1
        return _from_posix(tmpvf_path)

    def create_temp_dir(self, prefix=None, suffix=None):
        prefix = prefix or ""
        suffix = suffix or ""
        tmpvf_name = prefix + str(self._temp_file_counter) + suffix
        tmpvf_base = (
            PurePosixPath(_INTERNAL_TEMP_DIR_WINDOWS)
            if _IS_OS_WINDOWS
            else PurePosixPath(_INTERNAL_TEMP_DIR_POSIX)
        )
        tmpvf_path = tmpvf_base / PurePosixPath(tmpvf_name)
        try:
            self._add_node(tmpvf_path, FileType.DIRECTORY, data=None)
        except FileCreationException as ex:
            raise TemporaryFileCreationException(
                file_path=None,
                message=f"Failed to create temporary directory: {ex}"
            ) from None

        self._temp_file_counter += 1
        return _from_posix(tmpvf_path)

    def __str__(self):
        return super().__str__() + "\n" + "\n".join(
            self._vf_to_str(vf)
            for vf in self._files.values()
        )

    def _vf_to_str(self, vf):
        string = f"{vf.file_type.symbol} {vf.path.as_posix()}"
        if vf.file_type == FileType.SYMBOLIC_LINK:
            string += f" -> {vf.data.as_posix()}"

        return string

    def _vf_file_type_to_str(self, vf):
        return str(vf.file_type).lower().replace("_", " ")

    def _get_node(self, path, follow_symlinks=True) -> Optional[_VirtualFile]:
        if follow_symlinks:
            path = self._resolve_symlinks_in_path(path)

        fs_path = _to_posix(path)
        if not fs_path.is_absolute():
            fs_path = self._cwd / fs_path

        return self._files.get(fs_path.as_posix())

    def _add_node(self, path, file_type, data):
        fs_path = _to_posix(path)
        self.create_directories(fs_path.parent)
        if not fs_path.is_absolute():
            fs_path = self._cwd / fs_path

        self._files[str(fs_path)] = _VirtualFile(fs_path, file_type, data)

    def _delete_node(self, vf):
        del self._files[str(vf.path)]

    def _link_vf(self, virtual_file):
        self._files[str(virtual_file.path)] = virtual_file

    def _get_child_nodes(self, path):
        path = (
            PurePosixPath(path)
            if not isinstance(path, PurePosixPath)
            else path
        )
        path_begin = str(path) + _INTERNAL_PATH_SEPARATOR
        return [
            vf for path_str, vf in self._files.items()
            if path_str.startswith(path_begin)
        ]

    def _get_adjacent_child_nodes(self, path):
        path = (
            PurePosixPath(path)
            if not isinstance(path, PurePosixPath)
            else path
        )
        path_str = str(path)
        path_begin = path_str + _INTERNAL_PATH_SEPARATOR
        return [
            vf for file_path_str, vf in self._files.items()
            if (
                file_path_str.startswith(path_begin)
                and PurePosixPath(file_path_str).parent.as_posix() == path_str
            )
        ]

    def _get_lock_file_name_for(self, file_name):
        return f".{file_name}.lck"

    def _create_vf_directory(self, path):
        path_obj = PurePosixPath(path)
        path_str = path_obj.as_posix()
        self._ensure_is_writable(path_obj.parent)
        self._files[path_str] = _VirtualFile(
            path_obj, FileType.DIRECTORY, data=None
        )

    def _ensure_is_writable(self, path):
        path = (
            PurePosixPath(path)
            if not isinstance(path, PurePosixPath)
            else path
        )
        vf = self._get_node(path, follow_symlinks=False)
        if vf is not None and not vf.perm.owner.can_write:
            f_type = self._vf_file_type_to_str(vf)
            platform_path = _from_posix(path)
            raise FilePermissionException(
                str(platform_path),
                f"File '{platform_path}' of type {f_type} is not writable: "
                "Permission denied"
            )

    def _resolve_symlinks_in_path(self, path, head=True) -> PurePath:
        fs_path = _to_posix(path)
        parts = fs_path.parts
        resolved_path = PurePosixPath(parts[0])
        head_idx = len(parts) - 1
        for i, item in enumerate(parts[1:], 1):
            is_head = i == head_idx
            resolved_path = resolved_path / PurePosixPath(item)
            if not head and is_head:
                continue

            vf = self._follow_symlink(
                self._get_node(resolved_path, follow_symlinks=False)
            )
            if vf is not None:
                resolved_path = PurePosixPath(vf.path)

        return resolved_path

    def _follow_symlink(self, vf):
        if vf is None:
            return None

        src_path = vf.path
        seen_paths = set()
        while self._is_virtual_symlink(vf):
            if vf.path in seen_paths:
                platform_src_path = _from_posix(src_path)
                raise SymbolicLinkResolutionException(
                    str(platform_src_path),
                    "Failed to resolve symbolic links in path "
                    f"'{platform_src_path}': Symlink loop detected"
                )

            seen_paths.add(vf.path)
            symlink_target_path = vf.data
            assert isinstance(symlink_target_path, PurePosixPath)
            if not symlink_target_path.is_absolute():
                symlink_target_path = vf.path.parent / symlink_target_path

            symlink_target = self._files.get(str(symlink_target_path))
            if symlink_target is None:
                platform_src_path = _from_posix(src_path)
                platform_vf_path = _from_posix(vf.path)
                platform_target_path = _from_posix(symlink_target_path)
                raise SymbolicLinkResolutionException(
                    str(platform_src_path),
                    "Failed to resolve symbolic links "
                    f"in path '{platform_src_path}'. "
                    f"Cannot follow symbolic link '{platform_vf_path}'. "
                    f"Target does not exist: '{platform_target_path}' "
                    "(broken link)"
                )

            vf = symlink_target

        return vf

    def _is_virtual_symlink(self, vf):
        return (
            vf is not None
            and vf.file_type == FileType.SYMBOLIC_LINK
            and isinstance(vf.data, PurePath)
        )
