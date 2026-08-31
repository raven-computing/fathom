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
"""Interactions with the host filesystem.

Implements the `FileSystem` interface.
"""

import os
import io
import stat
import errno
import ctypes
import tempfile
import shutil
import datetime
import threading

from pathlib import PurePath, Path
from typing import IO, Any, Optional

from raven.fathom.base.system import FileSystem, OperatingSystem
from raven.fathom.base.file import FileType, FileMode
from raven.fathom.base.file import FilePermission, FileAccess
from raven.fathom.base.file import (
    FileIOException, InvalidFileModeException, CannotOpenFileException,
    CannotCloseFileException, FileNotFoundException, FilePermissionException,
    FilePositioningException, FileLockAcquisitionException, FileQueryException,
    FileReadException, SymbolicLinkResolutionException,
    DirectoryListingException, FileModificationException, FileWriteException,
    FileRelocationException, FileCopyException, FileRemovalException,
    FileCreationException, TemporaryFileCreationException
)
from raven.fathom.base._env import HostSystemEnvironment


# Lazy loaded, use _host_os() function to access
_HOST_OS = None
_G_LOCK = threading.Lock()

# Windows file attribute constants
_FILE_ATTRIBUTE_HIDDEN = 0x2
_INVALID_FILE_ATTRIBUTES = -1
_OWNER_SECURITY_INFORMATION = 0x00000001
_GROUP_SECURITY_INFORMATION = 0x00000002

# The file access mode names as understood by the runtime.
_PYRT_FILE_MODES = {
    FileMode.CREATE: "xb",
    FileMode.READ: "rb",
    FileMode.WRITE: "wb",
    FileMode.APPEND: "ab",
    FileMode.READ_WRITE: "rb+",
    FileMode.READ_APPEND: "ab+",
    FileMode.CREATE_WRITE: "xb",
    FileMode.CREATE_READ_WRITE: "wb+",
}

# Text encodings are not used as files are always opened in binary mode.
# pylint: disable=unspecified-encoding


def _get_account_name_win32(path: str, security_info: int) -> Optional[str]:
    """Gets the owner or group account name for a file on Windows.

    Uses the Win32 security API via ctypes.

    Args:
        path_str (str): The file path as a string.
        security_info (int): Either `_OWNER_SECURITY_INFORMATION` or
            `_GROUP_SECURITY_INFORMATION`.

    Returns:
        str: The account name, or `None` if it could not be determined.
    """
    advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]
    sd_needed = ctypes.c_ulong(0)
    advapi32.GetFileSecurityW(
        path, security_info, None, 0, ctypes.byref(sd_needed)
    )
    if sd_needed.value == 0:
        return None

    sd_buffer = ctypes.create_string_buffer(sd_needed.value)
    if not advapi32.GetFileSecurityW(
        path, security_info,
        sd_buffer, sd_needed.value, ctypes.byref(sd_needed)
    ):
        return None

    sid_ptr = ctypes.c_void_p()
    defaulted = ctypes.c_long(0)
    if security_info == _OWNER_SECURITY_INFORMATION:
        if not advapi32.GetSecurityDescriptorOwner(
            sd_buffer, ctypes.byref(sid_ptr), ctypes.byref(defaulted)
        ):
            return None
    else:
        if not advapi32.GetSecurityDescriptorGroup(
            sd_buffer, ctypes.byref(sid_ptr), ctypes.byref(defaulted)
        ):
            return None

    if not sid_ptr.value:
        return None

    name_size = ctypes.c_ulong(0)
    domain_size = ctypes.c_ulong(0)
    sid_type = ctypes.c_ulong(0)
    advapi32.LookupAccountSidW(
        None, sid_ptr, None, ctypes.byref(name_size),
        None, ctypes.byref(domain_size), ctypes.byref(sid_type)
    )
    if name_size.value == 0:
        return None

    name_buf = ctypes.create_unicode_buffer(name_size.value)
    domain_buf = ctypes.create_unicode_buffer(domain_size.value)
    if not advapi32.LookupAccountSidW(
        None, sid_ptr, name_buf, ctypes.byref(name_size),
        domain_buf, ctypes.byref(domain_size), ctypes.byref(sid_type)
    ):
        return None

    return name_buf.value

def _host_os() -> OperatingSystem:
    global _HOST_OS  # pylint: disable=global-statement
    if _HOST_OS is None:
        with _G_LOCK:
            if _HOST_OS is None:
                _HOST_OS = HostSystemEnvironment().get_operating_system()

    return _HOST_OS

def _oserr_msg(os_error: OSError) -> str:
    if os_error.strerror:
        errno_str = f" (Errno {hex(os_error.errno)})" if os_error.errno else ""
        return f": {os_error.strerror}{errno_str}"

    if os_error.errno:
        return f": Errno {hex(os_error.errno)}"

    if isinstance(os_error, io.UnsupportedOperation):
        return f": Unsupported operation '{os_error}'"

    return ""


class _FileHandle:
    """An opaque file handle.

    Used internally by the FS implementation to manage access
    to file-like objects, readers, writers.
    """

    def __init__(self, obj: IO[Any], mode: FileMode, path: Path):
        self.file: IO[Any] = obj
        self.mode: FileMode = mode
        self.path: Path = path
        self.is_open: bool = False


class HostFileSystem(FileSystem):
    """Implementation of `FileSystem` which interoperates with
    the actual host's FS.
    """

    def init_path(self, path):
        return PurePath(path)

    def check_exists(self, path, check_symlink=True):
        path = Path(path)
        try:
            return path.exists(follow_symlinks=check_symlink)
        except OSError as error:
            raise FileIOException(
                str(path),
                f"Failed to check existence of "
                f"file '{path}'{_oserr_msg(error)}"
            ) from None

    def check_is_hidden(self, path):
        path = Path(path)
        if _host_os() == OperatingSystem.MS_WINDOWS:
            return self._check_is_hidden_win32(path)

        return self._check_is_hidden_linux(path)

    def set_hidden(self, path, hidden):
        path = Path(path)
        if _host_os() == OperatingSystem.MS_WINDOWS:
            return self._set_hidden_win32(path, hidden)

        is_hidden = self.check_is_hidden(path)
        adjusted_path = path
        action = "act on"
        if hidden and not is_hidden:  # Do hide
            action = "hide"
            adjusted_path = path.with_name("." + path.name)
        elif not hidden and is_hidden:  # Do unhide
            action = "unhide"
            adjusted_path = path.with_name(path.name[1:])

        if adjusted_path != path:
            try:
                self.move(path, adjusted_path, follow_symlinks=False)
            except FileIOException:
                raise FileModificationException(
                    str(path),
                    f"Failed to {action} file by moving '{path}'"
                )

        return adjusted_path

    def get_parent_path(self, path):
        return path.parent

    def get_size(self, path):
        path = Path(self.resolve_symbolic_links(path))
        try:
            if path.is_dir():
                return self._get_dir_size(path)

            return path.lstat().st_size
        except OSError as error:
            msg = f"Failed to query size of file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def check_is_empty(self, path):
        path = Path(self.resolve_symbolic_links(path))
        try:
            stat_res = path.stat()
            if stat.S_ISREG(stat_res.st_mode):
                return stat_res.st_size == 0
            if stat.S_ISDIR(stat_res.st_mode):
                return self._check_dir_is_empty(path)

            return False
        except OSError as error:
            msg = f"Failed to query size of file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_type(self, path, follow_symlinks=True):
        path = Path(path)
        file_type = 0
        try:
            st_mode = 0
            if follow_symlinks:
                path = Path(self.resolve_symbolic_links(path))

            st_mode = path.lstat().st_mode

            file_type = stat.S_IFMT(st_mode)
        except OSError as error:
            self._checked_io_err(
                path, error,
                f"Failed to obtain type of file '{path}'"
            )
            return FileType.UNKNOWN

        if file_type == stat.S_IFREG:
            return FileType.REGULAR_FILE
        if file_type == stat.S_IFDIR:
            return FileType.DIRECTORY
        if file_type == stat.S_IFLNK:
            return FileType.SYMBOLIC_LINK
        if file_type == stat.S_IFSOCK:
            return FileType.SOCKET
        if file_type == stat.S_IFIFO:
            return FileType.NAMED_PIPE
        if file_type == stat.S_IFCHR:
            return FileType.CHARACTER_DEVICE
        if file_type == stat.S_IFBLK:
            return FileType.BLOCK_DEVICE
        return FileType.UNKNOWN

    def open_file_object(self, path, mode):
        path = Path(self.resolve_symbolic_links(path))
        try:
            # pylint: disable=consider-using-with
            handle = _FileHandle(
                open(path, _PYRT_FILE_MODES[mode]),
                mode,
                path
            )
            handle.is_open = True
            return handle
        except (ValueError, KeyError) as error:
            raise InvalidFileModeException(
                str(path),
                f"Failed to open file '{path}' with "
                f"given mode '{mode}': {error}"
            ) from None
        except OSError as error:
            msg = (
                f"Failed to open file '{path}' in "
                f"mode '{mode}'"
            )
            self._checked_io_err(path, error, msg)
            raise CannotOpenFileException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def close_file_object(self, handle):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        try:
            if handle.is_open:
                handle.file.close()
                handle.is_open = False
        except OSError as error:
            raise CannotCloseFileException(
                str(handle.path),
                f"Failed to close file{_oserr_msg(error)}"
            ) from None

    def read_from_file_object(self, handle, n_bytes=-1):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        try:
            return handle.file.read(n_bytes)
        except OSError as error:
            hint_amount = "all" if n_bytes < 0 else str(n_bytes)
            hint_unit = "bytes" if n_bytes != 1 else "byte"
            raise FileReadException(
                str(handle.path),
                f"Failed to read {hint_amount} {hint_unit} from "
                f"file '{handle.path}'{_oserr_msg(error)}"
            ) from None

    def write_to_file_object(self, handle, data):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        try:
            return handle.file.write(data)
        except OSError as error:
            n_bytes = len(data)
            hint_amount = str(n_bytes)
            hint_unit = "bytes" if n_bytes != 1 else "byte"
            raise FileWriteException(
                str(handle.path),
                f"Failed to write {hint_amount} {hint_unit} to "
                f"file '{handle.path}'{_oserr_msg(error)}"
            ) from None

    def flush_file_object(self, handle):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        try:
            handle.file.flush()
        except OSError as error:
            raise FileWriteException(
                str(handle.path),
                f"Failed to flush file{_oserr_msg(error)}"
            ) from None

    def get_file_object_position(self, handle):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        try:
            return handle.file.tell()
        except OSError as error:
            raise FilePositioningException(
                str(handle.path),
                f"Failed to get position of file "
                f"at '{handle.path}'{_oserr_msg(error)}"
            ) from None

    def set_file_object_position(self, handle, new_pos):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        if new_pos < 0:
            raise FilePositioningException(
                str(handle.path),
                f"Cannot set position of file at '{handle.path}': "
                f"Invalid file position {new_pos}"
            )

        try:
            handle.file.seek(new_pos, os.SEEK_SET)
        except OSError as error:
            raise FilePositioningException(
                str(handle.path),
                f"Failed to set position of file "
                f"at '{handle.path}'{_oserr_msg(error)}"
            ) from None

    def rewind_file_object_position(self, handle):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        try:
            handle.file.seek(0, os.SEEK_SET)
        except OSError as error:
            raise FilePositioningException(
                str(handle.path),
                f"Failed to rewind position of file "
                f"at '{handle.path}'{_oserr_msg(error)}"
            ) from None

    def resize_file_object(self, handle, size=None):
        assert isinstance(handle, _FileHandle), "Invalid file handle type"
        if size is not None and size < 0:
            raise FileWriteException(
                str(handle.path),
                f"Cannot resize file at '{handle.path}'. "
                f"Invalid file size: {size}"
            )

        try:
            handle.file.truncate(size)
        except OSError as error:
            hint_trunc = (
                "current position indicator"
                if size is None
                else f"{size} bytes" if size != 1 else "1 byte"
            )
            raise FileWriteException(
                str(handle.path),
                f"Failed to resize file to size of {hint_trunc} "
                f"at '{handle.path}'{_oserr_msg(error)}"
            ) from None

    def check_file_access(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = self.resolve_symbolic_links(path)

        if _host_os() == OperatingSystem.MS_WINDOWS:
            return self._check_file_access_win32(path)

        return self._check_file_access_linux(path)

    def get_file_permissions(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        # Get the 9 file perm bits (owner/group/other) as strings
        try:
            mode_bits = bin(path.lstat().st_mode)[-9:]
        except OSError as error:
            msg = f"Failed to read file permission for file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

        # Split into suitable chunks and convert to ints (0s and 1s):
        # e.g.:  Owner,     Group,     Other
        #    [ [1, 1, 1], [1, 0, 0], [1, 0, 0] ]
        stat_bits = [
            [int(bit) for bit in list(mode_bits[i:i+3])]
            for i in range(0, len(mode_bits), 3)
        ]

        # pylint: disable=consider-using-generator
        prot_bits = tuple([
            FileAccess(tuple(perm_group))
            for perm_group in stat_bits
        ])

        return FilePermission(prot_bits)

    def set_file_permissions(self, path, permissions, follow_symlinks=True):
        # pylint: disable=too-many-locals
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        user = permissions.owner
        u_r = stat.S_IRUSR if user.can_read else 0
        u_w = stat.S_IWUSR if user.can_write else 0
        u_x = stat.S_IXUSR if user.can_execute else 0
        user = u_r | u_w | u_x
        group = permissions.group
        g_r = stat.S_IRGRP if group.can_read else 0
        g_w = stat.S_IWGRP if group.can_write else 0
        g_x = stat.S_IXGRP if group.can_execute else 0
        group = g_r | g_w | g_x
        other = permissions.other
        o_r = stat.S_IROTH if other.can_read else 0
        o_w = stat.S_IWOTH if other.can_write else 0
        o_x = stat.S_IXOTH if other.can_execute else 0
        other = o_r | o_w | o_x
        try:
            path.chmod(
                user | group | other,
                follow_symlinks=False
            )
        except OSError as error:
            msg = (
                f"Failed to set file permission to {permissions} "
                f"for file '{path}'"
            )
            self._checked_io_err(path, error, msg)
            raise FileModificationException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_file_owner_uid(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        try:
            return path.lstat().st_uid
        except OSError as error:
            msg = f"Failed to get file owner UID for file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_file_owner_name(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        if _host_os() == OperatingSystem.MS_WINDOWS:
            msg = f"Failed to get file owner name for file '{path}'"
            try:
                name = _get_account_name_win32(
                    str(path), _OWNER_SECURITY_INFORMATION
                )
            except OSError as error:
                self._checked_io_err(path, error, msg)
                raise FileQueryException(
                    str(path),
                    f"{msg}{_oserr_msg(error)}"
                ) from None

            if name is None:
                raise FileQueryException(
                    str(path),
                    f"{msg}: Could not determine owner name"
                )
            return name

        try:
            return path.owner() # pyright: ignore[reportAttributeAccessIssue]
        except OSError as error:
            msg = f"Failed to get file owner name for file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_file_group_gid(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        try:
            return path.lstat().st_gid
        except OSError as error:
            msg = f"Failed to get file group GID for file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_file_group_name(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        if _host_os() == OperatingSystem.MS_WINDOWS:
            msg = f"Failed to get file group name for file '{path}'"
            try:
                name = _get_account_name_win32(
                    str(path), _GROUP_SECURITY_INFORMATION
                )
            except OSError as error:
                self._checked_io_err(path, error, msg)
                raise FileQueryException(
                    str(path),
                    f"{msg}{_oserr_msg(error)}"
                ) from None
            if name is None:
                raise FileQueryException(
                    str(path),
                    f"{msg}: Could not determine group name"
                )
            return name

        try:
            return path.group() # pyright: ignore[reportAttributeAccessIssue]
        except OSError as error:
            msg = f"Failed to get file group name for file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_file_last_modification_time(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = Path(self.resolve_symbolic_links(path))

        try:
            return datetime.datetime.fromtimestamp(
                path.lstat().st_mtime,
                datetime.UTC
            )
        except OSError as error:
            msg = (
                "Failed to get last modification time "
                f"for file '{path}'"
            )
            self._checked_io_err(path, error, msg)
            raise FileQueryException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def create_regular_file(self, path):
        path = Path(path)
        try:
            if path.exists(follow_symlinks=False):
                f_type = self.get_type(path, follow_symlinks=False)
                if f_type != FileType.REGULAR_FILE:
                    f_type = str(f_type).lower().replace("_", " ")
                    raise FileCreationException(
                        str(path),
                        f"Failed to create regular file '{path}': "
                        f"File already exists but is {f_type}"
                    )

            else:
                self._create_empty_file_atomic(path)
        except OSError as error:
            msg = f"Failed to create regular file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileCreationException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def create_directory(self, path):
        path = Path(path)
        try:
            path.mkdir(parents=False, exist_ok=True)
        except FileNotFoundError as error:
            raise FileNotFoundException(
                str(path),
                f"Failed to create directory '{path}' because its "
                f"parent does not exist{_oserr_msg(error)}"
            ) from None
        except NotADirectoryError as error:
            raise FileCreationException(
                str(path),
                f"Failed to create directory '{path}' because parent file "
                f"already exists but is not a directory{_oserr_msg(error)}"
            ) from None
        except OSError as error:
            msg = f"Failed to create directory '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileCreationException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def create_directories(self, path):
        path = Path(path)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except NotADirectoryError as error:
            raise FileCreationException(
                str(path),
                f"Failed to create directory '{path}': Parent file already "
                f"exists but is not a directory{_oserr_msg(error)}"
            ) from None
        except OSError as error:
            msg = (
                f"Failed to create directory '{path}' "
                f"or one of its parents"
            )
            self._checked_io_err(path, error, msg)
            raise FileCreationException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def create_symbolic_link(self, path, target):
        path = Path(path)
        try:
            path.symlink_to(target)
        except OSError as error:
            msg = (
                f"Failed to create symbolic link '{path}' to "
                f"target '{target}'"
            )
            self._checked_io_err(path, error, msg)
            raise FileCreationException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def get_symbolic_link_target(self, path, absolute=False):
        path_to_check = Path(path)
        try:
            if path_to_check.is_symlink():
                path = Path(os.readlink(path_to_check))
                if _host_os() == OperatingSystem.MS_WINDOWS:
                    if str(path).startswith("\\\\?\\"):
                        path = Path(str(path)[4:])

                if absolute and not path.is_absolute():
                    path = path_to_check.absolute().parent / path

        except OSError as error:
            raise SymbolicLinkResolutionException(
                str(path),
                f"Failed to resolve symbolic link '{path}'{_oserr_msg(error)}"
            ) from None

        return path

    def resolve_symbolic_links(self, path):
        source_path = Path(path)
        try:
            resolved_path = source_path.resolve(strict=False)
            normalized_path = Path(os.path.normpath(source_path)).absolute()
            no_symlinks = (
                normalized_path == resolved_path
                and not source_path.is_symlink()
            )
            if no_symlinks:
                return path  # Does not contain any symlinks

            if not resolved_path.exists(follow_symlinks=True):
                # Broken symlink detection
                parts = normalized_path.parts
                span = Path(parts[0])
                for part in parts[1:]:
                    span = span.joinpath(part)
                    seen_link_targets = {span}
                    while span.is_symlink():
                        link_target = Path(
                            self.get_symbolic_link_target(
                                span, absolute=True
                            )
                        )
                        if span == link_target:
                            break

                        # Symlink loop detection
                        if link_target in seen_link_targets:
                            raise SymbolicLinkResolutionException(
                                str(source_path),
                                "Failed to resolve symbolic links "
                                f"in path '{source_path}'. "
                                f"Symlink loop detected for path '{span}' "
                                f"which points to '{link_target}' "
                                "(symlink loop)"
                            ) from None

                        seen_link_targets.add(link_target)

                        if not link_target.exists(follow_symlinks=False):
                            raise SymbolicLinkResolutionException(
                                str(source_path),
                                "Failed to resolve symbolic links "
                                f"in path '{source_path}'. "
                                f"Cannot follow symbolic link '{span}'. "
                                f"Target does not exist: '{link_target}' "
                                "(broken link)"
                            ) from None

                        span = link_target

            return resolved_path
        except (OSError, RuntimeError) as error:
            # Py < 3.13 can raise RuntimeError for symlink loops
            if isinstance(error, OSError):
                msg = _oserr_msg(error)
            else:
                msg = f": Runtime error: {error}"

            raise SymbolicLinkResolutionException(
                str(source_path),
                "Failed to resolve symbolic links in path "
                f"'{source_path}'{msg}"
            ) from None

    def touch_file(self, path):
        path = Path(path)
        try:
            path.touch()
        except OSError as error:
            msg = f"Failed to touch file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileModificationException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def move(self, source, target, follow_symlinks=True):
        source = Path(source)
        target = Path(target)
        symlink_to_be_removed = None
        if follow_symlinks:
            resolved = Path(self.resolve_symbolic_links(source))
            if resolved != source and source.is_symlink():
                symlink_to_be_removed = source

            source = resolved

        try:
            if _host_os() == OperatingSystem.MS_WINDOWS:
                self._try_move_file_win32(source, target, follow_symlinks)
            else:
                self._try_move_file_linux(source, target)
        except OSError as error:
            msg = (
                f"Failed to move file '{source}' to "
                f"destination at '{target}'"
            )
            self._checked_io_err(source, error, msg)
            raise FileRelocationException(
                str(source),
                f"{msg}{_oserr_msg(error)}"
            ) from None

        if symlink_to_be_removed:
            try:
                symlink_to_be_removed.unlink()
            except OSError as error:
                msg = (
                    "Failed to remove source symbolic link "
                    f"'{symlink_to_be_removed}' "
                    f"after move operation of link target '{source}' to "
                    f"destination at '{target}'"
                )
                self._checked_io_err(source, error, msg)
                raise FileRelocationException(
                    str(source),
                    f"{msg}{_oserr_msg(error)}"
                ) from None

    def copy(self, source, target, follow_symlinks=True):
        source = Path(source)
        target = Path(target)
        if follow_symlinks:
            source = self.resolve_symbolic_links(source)

        source_type = FileType.UNKNOWN
        try:
            source_type = self.get_type(source, follow_symlinks=False)
            if source_type not in (FileType.REGULAR_FILE, FileType.DIRECTORY):
                raise FileCopyException(
                    str(source),
                    f"Cannot copy file '{source}' of type {source_type}. "
                    "Only regular files and directories can be copied"
                )

            if self.check_exists(target, check_symlink=False):
                target_type = self.get_type(target, follow_symlinks=False)
                if source_type != target_type:
                    raise FileCopyException(
                        str(source),
                        f"Cannot copy file '{source}' of type {source_type} "
                        f"to destination at '{target}'. File at destination "
                        f"already exists but is of type {target_type}"
                    )
        except FileNotFoundException:
            # The source file does not exist. This exception here is ignored
            # such that the actual copy attempt below fails and we give
            # the correct/expected error message to the caller.
            pass

        ftype_hint = "file"
        try:
            if source_type == FileType.DIRECTORY:
                ftype_hint = "directory"
                shutil.copytree(
                    source,
                    target,
                    symlinks=False,
                    dirs_exist_ok=True
                )
            else:
                shutil.copy2(source, target)
        except OSError as error:
            msg = (
                f"Failed to copy {ftype_hint} '{source}' to "
                f"destination at '{target}'"
            )
            self._checked_io_err(source, error, msg)
            raise FileCopyException(
                str(source),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def remove(self, path, follow_symlinks=True):
        path = Path(path)
        is_directory = is_symlink = False
        try:
            is_directory = path.is_dir()
            is_symlink = path.is_symlink()
            if is_directory and not is_symlink:
                for child in self.list_files_of_directory(path):
                    self.remove(child, follow_symlinks)

                path.rmdir()
            else:
                if is_symlink and follow_symlinks:
                    target = self.resolve_symbolic_links(path)
                    self.remove(target, follow_symlinks=False)

                path.unlink()
        except DirectoryListingException:
            raise FileRemovalException(
                str(path),
                f"Failed to remove directory '{path}': "
                "Could not list content of directory"
            )
        except OSError as error:
            ftype = (
                "directory" if is_directory
                else "symbolic link" if is_symlink else "file"
            )
            msg = f"Failed to remove {ftype} '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileRemovalException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def list_files_of_directory(self, path, recursive=False):
        path = Path(path)
        try:
            yield from HostFileSystem._generate_dir_listing(path, recursive)
        except NotADirectoryError:
            raise DirectoryListingException(
                str(path),
                "Cannot generate directory listing for "
                f"non-directory file: '{path}'"
            ) from None
        except OSError as error:
            msg = f"Failed to generate listing for directory '{path}'"
            self._checked_io_err(path, error, msg)
            raise DirectoryListingException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def flush_system(self):
        pass  # NO-OP

    def get_lock_file_path(self, path, follow_symlinks=True):
        if follow_symlinks:
            path = self.resolve_symbolic_links(path)

        return path.with_name(f".{path.name}.lck")

    def lock_file(self, path, follow_symlinks=True):
        if follow_symlinks:
            path = self.resolve_symbolic_links(path)

        lock_file = self.get_lock_file_path(path, follow_symlinks=False)
        try:
            self._create_empty_file_atomic(lock_file)
        except FileExistsError:
            raise FileLockAcquisitionException(
                str(path),
                f"File is already locked: '{path}'"
            ) from None
        except OSError as error:
            msg = (
                f"Failed to acquire lock for file '{path}'. "
                "It is required that the parent directory of the file exists "
                "and is writable in order to acquire a lock"
            )
            self._checked_io_err(path, error, msg)
            raise FileIOException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def unlock_file(self, path, follow_symlinks=True):
        path = Path(path)
        if follow_symlinks:
            path = self.resolve_symbolic_links(path)

        lock_file = Path(self.get_lock_file_path(path, follow_symlinks=False))
        try:
            lock_file.unlink()
        except FileNotFoundError:
            # Lock file does not exist. Ignore.
            pass
        except OSError as error:
            msg = f"Failed to release lock for file '{path}'"
            self._checked_io_err(path, error, msg)
            raise FileIOException(
                str(path),
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def create_temp_file(self, directory=None, prefix=None, suffix=None):
        try:
            # Arguments to mkstemp() must all be of the same type.
            # Accept a PurePath object as a directory path but implicitly
            # always convert to a string.
            if isinstance(directory, PurePath):
                directory = str(directory)

            # mkstemp() opens the file already
            fd, name = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=directory,
            )
            os.close(fd)
            return Path(name)
        except FileNotFoundError as error:
            raise FileNotFoundException(
                directory, # type: ignore
                f"Failed to create temporary file because "
                f"the specified parent directory '{directory}' does "
                f"not exist{_oserr_msg(error)}"
            ) from None
        except OSError as error:
            hint = "" if directory is None else f" in directory '{directory}'"
            msg = f"Failed to create temporary file{hint}"
            self._checked_io_err(None, error, msg)
            raise TemporaryFileCreationException(
                None,
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def create_temp_dir(self, prefix=None, suffix=None):
        try:
            return Path(tempfile.mkdtemp(suffix=suffix, prefix=prefix))
        except OSError as error:
            msg = "Failed to create temporary directory"
            self._checked_io_err(None, error, msg)
            raise TemporaryFileCreationException(
                None,
                f"{msg}{_oserr_msg(error)}"
            ) from None

    def _create_empty_file_atomic(self, path):
        with open(path, _PYRT_FILE_MODES[FileMode.CREATE]):
            pass

    def _get_dir_size(self, dir_path):
        return sum(
            self.get_size(file)
            for file in dir_path.glob("*")
        )

    def _check_dir_is_empty(self, dir_path):
        for _ in dir_path.glob("*"):
            return False

        return True

    def _check_is_hidden_linux(self, path):
        if not path.exists(follow_symlinks=True):
            raise FileNotFoundException(
                str(path),
                "Failed to check if file is hidden. "
                f"No such file or directory: '{path}'"
            )

        return path.name.startswith(".")

    def _check_is_hidden_win32(self, path):
        try:
            st = path.stat()
            return bool(st.st_file_attributes & _FILE_ATTRIBUTE_HIDDEN)
        except OSError:
            raise FileNotFoundException(
                str(path),
                "Failed to check if file is hidden. "
                f"No such file or directory: '{path}'"
            ) from None

    def _set_hidden_win32(self, path, hidden):
        action = "hide" if hidden else "unhide"
        path_str = str(path)
        win32_sys = ctypes.windll.kernel32 # type: ignore
        current_attrs = win32_sys.GetFileAttributesW(path_str)
        if current_attrs == _INVALID_FILE_ATTRIBUTES:
            raise FileNotFoundException(
                path_str,
                f"Failed to {action} file. "
                f"No such file or directory: '{path}'"
            )

        new_attrs = (
            current_attrs | _FILE_ATTRIBUTE_HIDDEN
            if hidden
            else current_attrs & ~_FILE_ATTRIBUTE_HIDDEN
        )
        if not win32_sys.SetFileAttributesW(path_str, new_attrs):
            raise FileModificationException(
                path_str,
                f"Failed to {action} file '{path}'"
            )

        return path

    def _check_file_access_linux(self, path):
        try:
            mode_bits = path.lstat().st_mode
            readable = bool(mode_bits & stat.S_IRUSR)
            writable = bool(mode_bits & stat.S_IWUSR)
            executable = bool(mode_bits & stat.S_IXUSR)
            return FileAccess((readable, writable, executable))
        except FileNotFoundError:
            raise FileNotFoundException(
                str(path),
                f"Failed to obtain access capabilities for file '{path}': "
                "No such file or directory"
            ) from None
        except OSError as error:
            raise FileQueryException(
                str(path),
                "Failed to obtain access capabilities "
                f"for file '{path}'{_oserr_msg(error)}"
            ) from None

    def _check_file_access_win32(self, path):
        readable = False
        writable = False
        executable = False
        try:
            if path.is_dir():
                mode_bits = path.lstat().st_mode
                readable = bool(mode_bits & stat.S_IRUSR)
                writable = bool(mode_bits & stat.S_IWUSR)
                executable = bool(mode_bits & stat.S_IXUSR)
                return FileAccess((readable, writable, executable))

            readable = self._try_access_rw_win32(path, "r")
            writable = self._try_access_rw_win32(path, "w")
            executable = readable and self._try_access_x_win32(path)
        except FileNotFoundError:
            raise FileNotFoundException(
                str(path),
                f"Failed to obtain access capabilities for file '{path}': "
                "No such file or directory"
            ) from None
        except OSError as error:
            raise FileQueryException(
                str(path),
                "Failed to obtain access capabilities "
                f"for file '{path}'{_oserr_msg(error)}"
            ) from None

        return FileAccess((readable, writable, executable))

    def _try_access_rw_win32(self, path, mode):
        try:
            with open(path, mode):
                return True
        except PermissionError:
            return False

    def _try_access_x_win32(self, path):
        try:
            return os.access(path, os.X_OK)
        except PermissionError:
            return False

    def _try_move_file_linux(self, source, target):
        source.rename(target)

    def _try_move_file_win32(self, source, target, follow_symlinks):
        try:
            source.rename(target)
        except FileExistsError as fe_error:
            try:
                self.remove(target, follow_symlinks)
                source.rename(target)
            except FileIOException:
                raise fe_error

    def _checked_io_err(self, path, error, message):
        if error.errno:
            path = str(path) if path is not None else None
            if error.errno == errno.ENOENT:
                raise FileNotFoundException(
                    path,
                    f"{message}{_oserr_msg(error)}"
                ) from None

            if error.errno == errno.EACCES:
                raise FilePermissionException(
                    path,
                    f"{message}{_oserr_msg(error)}"
                ) from None

    @staticmethod
    def _generate_dir_listing(path, recursive=False):
        for child in path.iterdir():
            recurse = recursive and child.is_dir()
            yield child
            if recurse:
                yield from HostFileSystem._generate_dir_listing(
                    child,
                    recursive=True
                )
