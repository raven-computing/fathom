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
"""Contains interface classes used for host system interactions and queries."""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from pathlib import PurePath
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union, Any
from collections.abc import Generator

from raven.fathom.base.typing import Interface
from raven.fathom.base.exceptions import FathomIOException
from raven.fathom.base.decorators import inject

if TYPE_CHECKING:
    from raven.fathom.base.file import (
        FileType, FileMode, FileAccess, FilePermission
    )


class InputReadException(FathomIOException):
    """An attempt to read from an `InputPrompt` has failed."""


class OperatingSystem(Enum):
    """Enumeration of known operating systems."""

    GNU_LINUX = "GNU/Linux"

    MS_WINDOWS = "Windows"

    ANDROID = "Android"

    MAC_OS = "MacOS"

    I_OS = "iOS"

    I_PAD_OS = "iPadOS"

    OTHER = "Other"

    def is_supported(self):
        """Indicates whether this operating system is supported.

        Returns:
            bool: `True` if the application supports this OS,
                `False` otherwise.
        """
        return self in (OperatingSystem.GNU_LINUX, OperatingSystem.MS_WINDOWS)

    def __str__(self):
        return self.value


@inject
class SystemEnvironment(Interface):
    """An interface to query the system environment of the application.

    Gives access to information that is usually provided by the operating
    system, for example the name or UID of the system user that is used in
    the process of the underlying running application.
    """

    @abstractmethod
    def get_user_id(self) -> Optional[int]:
        """Gets the user identifier string of the underlying system user.

        Returns:
            int: The system ID of the host user, or `None` if such a
                numerical ID does not exist on the underlying system.
        """

    @abstractmethod
    def get_user_name(self) -> Optional[str]:
        """Gets the ordinary user name of the underlying system user,
        if a such a name is available.

        Returns:
            str: The ordinary name of the host user, or `None` if no such
                name can be found.
        """

    @abstractmethod
    def get_home_path(self) -> Optional[PurePath]:
        """Gets the path to the home directory of the underlying system user.

        Returns:
            PurePath: The path to the host user's home directory, or `None` if
                the user does not have a home directory or it cannot be found.
        """

    @abstractmethod
    def get_current_working_directory(self) -> PurePath:
        """Gets the current working directory of the underlying system user.

        It may be different from the home directory of the user.

        Returns:
            PurePath: The path to the current working directory.
        """

    @abstractmethod
    def get_operating_system(self) -> OperatingSystem:
        """Determines the underlying operating system platform.

        Returns:
            OperatingSystem: The operating system platform in use.
        """

    @abstractmethod
    def get_line_separator(self) -> str:
        """Indicates the line separator used by default for all text
        files by the underlying system.

        Returns:
            str: The character string that represent the default
                line separator in text files. May be a multi-character string.
        """

    @abstractmethod
    def get_text_encoding(self) -> str:
        """Indicates the name of the encoding used by the underlying system by
        default when reading and writing text files.

        Returns:
            str: The name of the default text encoding.
        """

    @abstractmethod
    def get_file_system_encoding(self) -> str:
        """Indicates the encoding used by the underlying filesystem.

        This is used when converting file names and paths to and from bytes in
        the native representation of the system.

        Returns:
            str: The name of the used filesystem encoding.
        """

    @abstractmethod
    def get_variable(
        self,
        name: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """Gets the value of the environment variable with the specified name.

        If the variable is not set, then the `default` value is returned.

        Args:
            name (str): The name of the environment variable to get.
            default (str): The default value to return if the variable is
                not set. Defaults to `None`.

        Returns:
            str: The value of the specified environment variable or
                the `default` value if it is not set.
        """


@inject
class InputPrompt(Interface):
    """An interface to prompt the user for input.

    Declares a method to prompt the program user for input and to read a
    text line, usually from the standard input stream.
    """

    @abstractmethod
    def read(
        self,
        prompt: Optional[str] = None,
        default_value: str = "",
        secret: bool = False
    ) -> str:
        """Prompts the user and reads his entered input.

        This method may block until the user provides input.

        Args:
            prompt (str): The message to display to the user as the prompt.
                If left as `None`, then no prompt is displayed and only the
                input is read.
            default_value (str): The default value to return if the user
                does not provide any input.
            secret (bool): If `True`, the input will be hidden, i.e. it will
                not be echoed. This is useful for sensitive input, e.g. for
                password prompts. Defaults to `False`.

        Returns:
            str: The input provided by the user. May be an empty string.
                Must never include any trailing newline character.

        Raises:
            InputReadException: If the input cannot be read.
        """


@inject
class FileSystem(Interface):
    """An interface for interactions with a filesystem.

    All methods declared by this class can, unless noted otherwise,
    handle only `pathlib.PurePath` objects as file path arguments.
    """

    @abstractmethod
    def init_path(self, path) -> PurePath:
        """Initializes a path from the given object.

        The returned `PurePath` corresponds to the representation of the
        given path within this filesystem, which may or may not be exactly
        the same as the textual representation of the given object.
        Higher-level APIs should use this initialization method to obtain
        a ground truth representation of used paths.
        This method does not convert relative to absolute paths or vice versa.

        Args:
            path: An object that can be converted by the filesystem
                to a `PurePath`.

        Raises:
            TypeError: If the type of the given object
                is not supported by this filesystem.
        """

    @abstractmethod
    def check_exists(self, path: PurePath, check_symlink=True) -> bool:
        """Checks whether the specified file exists.

        Symbolic links anywhere in the given path shall always be followed
        to their respective targets. The `check_symlink` argument specifies
        how to handle cases where the given path as a whole points to
        a symbolic link. If `check_symlink` is `True` and the given path points
        to a broken symlink, then this method shall return `False` because the
        target of the symlink does not exist. If `check_symlink` is `False` and
        the given path points to a broken symlink, then this method shall
        return `True` because the link itself exists and it is not checked
        whether the target of the link exists. Therefore, if the given path
        points to a valid symlink, then this method always returns `True`.

        Args:
            path (PurePath): The path of the file to check.
            check_symlink (bool): Indicates whether to check the existence of a
                symbolic link target if `path` points to a symlink.

        Returns:
            bool: `True` if the file denoted by the specified path exists
                in this filesystem. `False` if the file does not exist.

        Raises:
            FileIOException: If an I/O error occurs.
        """

    @abstractmethod
    def check_is_hidden(self, path: PurePath) -> bool:
        """Checks whether the specified file is hidden in the filesystem.

        The way that a file is marked as hidden is platform-dependent.
        This method shall handle all supported platforms. It may or may not
        do filesystem I/O to determine the hidden-state.

        Args:
            path (PurePath): The file path to check.

        Returns:
            bool: `True` if the file is hidden.
                `False` if the file is visible.

        Raises:
            FileNotFoundException: If the file at the specified path does not
                exist.
            FileQueryException: If an I/O error occurs or the query can
                otherwise not be fulfilled.
        """

    @abstractmethod
    def set_hidden(self, path: PurePath, hidden: bool) -> PurePath:
        """Sets the specified file as hidden.

        If a change in the hidden-state of the underlying file wihin the file
        system occurs, then this method may change the file itself depending on
        how hidden file states are implemented on the underlying platform.
        Thus, callers should ensure to use the file path returned by this
        method as a reference to the given input file in the case of
        such a change. The file denoted by the given input path is allowed
        to be moved by this method. Symbolic links are not followed.

        If the underlying file is already in the desired target state, this
        method shall have no effect.

        Args:
            path (PurePath): The path of the file to potentially change.
            hidden (bool): Whether to hide or unhide the specified file.

        Returns:
            PurePath: The path to the hidden or unhidden file, depending on the
                target state defined by the `hidden` argument. May or may not
                be the same as the input path.

        Raises:
            FileNotFoundException: If the file at the specified path does not
                exist but the hidden-state is determined by querying the actual
                filesystem file.
            FileQueryException: If the file hidden-state cannot
                be queried.
            FileModificationException: If the hidden-state of the file at the
                specified path cannot be modified.
        """

    @abstractmethod
    def get_parent_path(self, path: PurePath) -> PurePath:
        """Gets the parent directory of the specified path.

        The returned path represents the logical parent of the given path.
        For paths representing non-directory files, the returned path
        represents the enclosing directory of that file.
        In the case of root directory paths ('/'), which do not have parents,
        the same path is returned instead.

        This method shall only consider the path itself, not the underlying
        filesystem file that the path refers to.

        Returns:
            PurePath: The path of the parent of the specified path.

        Raises:
            FileIOException: In case any error occurs.
        """

    @abstractmethod
    def get_size(self, path: PurePath) -> int:
        """Checks the size of the specified file.

        This method measures the number of bytes of the file data content.
        For directories, this method returns the sum of the bytes of all
        children files in the corresponding directory, including
        subdirectories and the content thereof.

        This method will follow symbolic links.

        Args:
            path (PurePath): The file path to check.

        Returns:
            int: The size in bytes of the file content in this filesystem.

        Raises:
            FileNotFoundException: If the specified path does not exist in
                the filesystem.
            FileQueryException: If the file size cannot be obtained.
            SymbolicLinkResolutionException: If the specified path is a
                symbolic link and cannot be resolved.
        """

    @abstractmethod
    def check_is_empty(self, path: PurePath) -> bool:
        """Checks whether the specified regular file or directory is empty.

        This method must only return `True` for regular files and directories.
        For any other file type this method must always return `False`.
        A regular file is considered empty if its size is exactly zero.
        The size is determined with respect to the data content.
        A directory is considered empty if it contains no files of any type.

        This method will follow symbolic links.

        Args:
            path (PurePath): The file path to check.

        Returns:
            bool: `True` if the specified path points to a regular file or
                directory and it has no content, `False` otherwise.

        Raises:
            FileNotFoundException: If the specified path does not exist in
                the filesystem.
            FileQueryException: If the file size or type cannot be determined.
            SymbolicLinkResolutionException: If any symbolic link within the
                given path cannot be resolved or a broken symbolic link
                is encountered.
        """

    @abstractmethod
    def get_type(self, path: PurePath, follow_symlinks=True) -> FileType:
        """Determines the type of the specified file.

        Args:
            path (PurePath): The file path to check.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            FileType: The type of the specified file.

        Raises:
            FileNotFoundException: If the specified path does not exist
                in the filesystem.
            SymbolicLinkResolutionException: If the specified path is a
                symbolic link and cannot be resolved.
        """

    @abstractmethod
    def open_file_object(self, path: PurePath, mode: FileMode) -> Any:
        """Opens the file denoted by the specified path.

        The file is opened in the given file mode. It must not be already open.
        This method must return a file handle which can be subsequently passed
        to various other methods of this interface to perform file-related
        operations. A file handle is a completely transparent object, i.e. it
        does not declare any public attributes and is only used to refer to a
        previously opened file by means of this method. A file handle is not
        reusable across different implementations of this interface.

        This method will follow symbolic links.

        Args:
            path (PurePath): The path of the file to open.
            mode (FileMode): The file mode to use when opening.

        Returns:
            A file handle object which can be used for I/O operations
            in the specified mode.

        Raises:
            InvalidFileModeException: If the file mode is invalid
                or unsupported.
            FileNotFoundException: If the file does not exist.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
        """

    @abstractmethod
    def close_file_object(self, handle: Any):
        """Closes the file represented by the given handle.

        Args:
            handle: The filesystem handle to close.

        Raises:
            CannotCloseFileException: If the file from the handle
                cannot be closed.
        """

    @abstractmethod
    def read_from_file_object(self, handle: Any, n_bytes=-1) -> bytes:
        """Reads from the specified file.

        It must already be open in a mode which permits reading.

        Args:
            handle: The file handle to read from.
            n_bytes (int): How many bytes should be read by this operation.
                When specifying a negative `int` (the default), then the entire
                file content is read.

        Returns:
            bytes: The read data from the specified file.

        Raises:
            FileReadException: If an I/O error occurs while reading data.
        """

    @abstractmethod
    def write_to_file_object(
        self,
        handle: Any,
        data: Union[bytes, bytearray]
    ) -> int:
        """Writes the specified data to the specified file.

        It must already be open in a mode which permits either writing
        or appending.

        Args:
            handle: The handle object to write to.
            data (bytes): The data to write to the file.

        Returns:
            int: The number of bytes written to the specified file.

        Raises:
            FileWriteException: If an I/O error occurs while writing data.
        """

    @abstractmethod
    def flush_file_object(self, handle: Any):
        """Flushes the data buffer of the specified file.

        It must already be open.

        Args:
            handle: The file handle object to flush.

        Raises:
            FileWriteException: If an I/O error occurs while flushing data.
        """

    @abstractmethod
    def get_file_object_position(self, handle: Any) -> int:
        """Gets the current file position indicator value.

        The specified file must already be open and support random access.

        Args:
            handle: The file handle object to get
                the file position indicator for.

        Returns:
            int: The current numerical value of the position indicator
                of the specified file.

        Raises:
            FilePositioningException: If the file position cannot be obtained.
        """

    @abstractmethod
    def set_file_object_position(self, handle: Any, new_pos: int):
        """Sets the current file position indicator to the specified value.

        Repositions the file position indicator of the specified file to
        have the specified position. It must already be open and it must
        support random access.

        Args:
            handle: The file handle object to set the file position
                indicator for.
            new_pos (int): The new value to set the position indicator
                of the specified file to. Must be equal to or greater
                than zero.

        Raises:
            FilePositioningException: If the file position cannot be set,
                is invalid or the underlying filesystem file does not
                support random access.
        """

    @abstractmethod
    def rewind_file_object_position(self, handle: Any):
        """Rewinds the file position indicator.

        Rewinding the file position indicator will reset the position
        to the start of the file. The specified file must already be open
        and it must support random access.

        Args:
            handle: The file handle object to rewind the
                file position indicator for.

        Raises:
            FilePositioningException: If the file cannot be rewinded, or the
                underlying filesystem file does not support rewinding.
        """

    @abstractmethod
    def resize_file_object(self, handle: Any, size: Optional[int] = None):
        """Resizes the file to the specified size.

        The specified file must already be open in a mode which
        permits writing.

        Args:
            handle: The file handle object to do a resize operation for.
            size (int): The new size that the file should have, in bytes.
                Must be equal to or greater than zero. May be `None` to
                indicate that the file should be resized to the current
                file position indicator.

        Raises:
            FileWriteException: If the specified size is invalid or
                an I/O error occurs during resizing.
        """

    @abstractmethod
    def check_file_access(
        self,
        path: PurePath,
        follow_symlinks=True
    ) -> FileAccess:
        """Checks and returns the access capabilities for the specified file.

        The access capabilities represented by the returned `FileAccess` object
        are determined based on the underlying operating system user.

        Args:
            path (PurePath): The path of the file to check.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            FileAccess: A `FileAccess` object representing the access
                capabilities of the underlying system user for the
                specified file.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the specified path cannot be
                resolved or is a broken symbolic link.
            FileQueryException: If the file access capabilities
                cannot be queried.
        """

    @abstractmethod
    def get_file_permissions(
        self,
        path: PurePath,
        follow_symlinks=True
    ) -> FilePermission:
        """Gets the file mode permissions of a file.

        Args:
            path (PurePath): The path of the file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            FilePermission: A `FilePermission` object representing the
                permissions effective for the specified file.

        Raises:
            FileNotFoundException: If the file at the specified path does
                not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileQueryException: If the file permissions cannot be queried.
        """

    @abstractmethod
    def set_file_permissions(
        self,
        path: PurePath,
        permissions: FilePermission,
        follow_symlinks=True
    ):
        """Sets the file mode permissions for a file.

        Args:
            path (PurePath): The path of the file.
            permissions (FilePermission): The permissions to set
                for the specified file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileModificationException: If the file permissions cannot
                be modified or the operation is not permitted.
        """

    @abstractmethod
    def get_file_owner_uid(self, path: PurePath, follow_symlinks=True) -> int:
        """Gets the owner UID of the specified file.

        Args:
            path (PurePath): The path of the file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            int: The operating system UID of the file owner.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileQueryException: If the file owner cannot be queried.
        """

    @abstractmethod
    def get_file_owner_name(self, path: PurePath, follow_symlinks=True) -> str:
        """Gets the name of the owner of the specified file.

        Args:
            path (PurePath): The path of the file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            str: The operating system user name of the file owner.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileQueryException: If the file owner cannot be queried.
        """

    @abstractmethod
    def get_file_group_gid(self, path: PurePath, follow_symlinks=True) -> int:
        """Gets the group GID of the specified file.

        Args:
            path (PurePath): The path of the file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            int: The operating system GID of the file group.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileQueryException: If the file group cannot be queried.
        """

    @abstractmethod
    def get_file_group_name(self, path: PurePath, follow_symlinks=True) -> str:
        """Gets the name of the group of the specified file.

        Args:
            path (PurePath): The path of the file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            int: The operating system group name of the file group.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileQueryException: If the file group cannot be queried.
        """

    @abstractmethod
    def get_file_last_modification_time(
        self,
        path: PurePath,
        follow_symlinks=True
    ) -> datetime:
        """Gets the time of the last modification made to the specified file.

        The returned datetime shall represent a point in time
        on the UTC time scale.

        Args:
            path (PurePath): The path of the file.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            datetime: The time of the last modification made
                to the specified file.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            SymbolicLinkResolutionException: If the file at the specified path
                is a symbolic link and cannot be resolved.
            FileQueryException: If the file modification time cannot
                be queried.
        """

    @abstractmethod
    def create_regular_file(self, path: PurePath):
        """Creates the regular file denoted by the specified path.

        If the file already exists in this filesystem, then this method shall
        have no effect, unless it is not a regular file, in which case an
        exception is raised.

        Args:
            path (PurePath): The regular file to create.

        Raises:
            FilePermissionException: If the file creation is denied.
            FileCreationException: If the file cannot be created or it already
                exists but is not a regular file.
        """

    @abstractmethod
    def create_directory(self, path: PurePath):
        """Creates the directory denoted by the specified path.

        If the directory already exists in this filesystem, then this method
        shall have no effect, unless it is not a directory, in which case an
        exception is raised. The parent directory must already exist and is not
        automatically created by this method.

        Args:
            path (PurePath): The directory to create.

        Raises:
            FileNotFoundException: If the parent directory at the
                specified path does not exist.
            FilePermissionException: If the directory creation is denied.
            FileCreationException: If the directory cannot be created or a file
                at the same location already exists.
        """

    @abstractmethod
    def create_directories(self, path: PurePath):
        """Creates the directory structure denoted by the specified path.

        This method will also create all parent directories in the given path
        as needed. If one or more parent or all directories already exist, then
        this method has no effect on the existent directories and no error is
        raised due to that. If an error occurs because one out of many
        directories could not be created, then the state of the filesystem in
        the affected locations is left unspecified.

        Args:
            path (PurePath): The directory path to create.

        Raises:
            FilePermissionException: If the creation of any directory in
                the tree is denied.
            FileCreationException: If the directory or any of the parent
                directories cannot be created.
        """

    @abstractmethod
    def create_symbolic_link(self, path: PurePath, target: PurePath):
        """Creates a symbolic link denoted by the specified path, linking to
        the specified target file.

        Symbolic links must not be followed with respect to the
        specified target path. If the target is a symbolic link itself, then
        the created link will simply point to another link.
        The target may be specified as a relative or absolute path. A relative
        path is interpreted as being relative to the symlink path.
        A file may or may not exist at the specified target path.

        Args:
            path (PurePath): The path of the symbolic link to create.
            target (PurePath): The path of the target file to link to.

        Raises:
            FilePermissionException: If the symbolic link creation is denied.
            FileCreationException: If the symbolic link cannot be created or
                a file at the same location already exists.
        """

    @abstractmethod
    def get_symbolic_link_target(
        self,
        path: PurePath,
        absolute=False
    ) -> PurePath:
        """Returns the target path that the symbolic link denoted by the
        specified path points to.

        If the given path is not a symbolic link or if no file exists at
        that path, then this method shall have no effect and the given path
        must be returned unaltered.
        This method must not check for broken symbolic links, i.e. for any
        symbolic link only the target path is returned without checking
        whether the file that link points to actually exists.

        Args:
            path (PurePath): The path of the symbolic link to follow.
            absolute (bool): A flag indicating whether in the case of a
                symbolic link the returned target path should always be
                absolute, even when the link target is a relative path.

        Returns:
            PurePath: The target path of the symbolic link, or the specified
                path if it is not a symbolic link.

        Raises:
            SymbolicLinkResolutionException: If the specified path is a
                symbolic link but cannot be resolved.
        """

    @abstractmethod
    def resolve_symbolic_links(self, path: PurePath) -> PurePath:
        """Follows and resolves all symbolic links within the specified path.

        The given path does not necessarily have to represent a symbolic link
        itself. Symbolic links are resolved anywhere within the given path,
        including multiple layers of links (a link pointing to another
        link, etc.), such that the returned path does not contain any
        symbolic links.
        If the given path does not contain any symbolic links, then the same
        path must be returned unaltered. If at least one symbolic link is
        encountered and resolved, then this method might return a normalized
        version of the given input path.
        This method shall check whether any resolved symbolic link is broken
        and raise an exception if it is, i.e. if the file that a resolved link
        points to does not exist.
        A file at the specified path may or may not exist.

        Args:
            path (PurePath): The path for which to follow and resolve
                symbolic links.

        Returns:
            PurePath: The resolved target path.

        Raises:
            SymbolicLinkResolutionException: If any symbolic link within the
                given path cannot be resolved or a broken symbolic link
                is encountered.
        """

    @abstractmethod
    def touch_file(self, path: PurePath):
        """Touches the file denoted by the specified path.

        Touching a file causes the access and modification timestamps recorded
        by the underlying filesystem to be updated to the current time.
        This operation will create the file if it does not exist.

        Args:
            path (PurePath): The file to touch.

        Raises:
            FilePermissionException: If the file modification or
                creation is denied.
            FileCreationException: If the file cannot be created or a file
                at the same location already exists.
        """

    @abstractmethod
    def move(self, source: PurePath, target: PurePath, follow_symlinks=True):
        """Moves the file from the source location to the target location.

        An existent file of the same type at the specified target location
        is replaced by the source file. If the `follow_symlinks` argument is
        `True` and the specified `source` file is a symbolic link, then the
        target of the link is used as the source and the symbolic link itself
        is removed. If the `follow_symlinks` argument is `False` and the
        specified `source` file is a symbolic link, then the link is moved to
        the new location (potentially by first removing and recreating it at
        the target location) while keeping the same link target it originally
        pointed to.

        Args:
            source (PurePath): The location of the file to move.
            target (PurePath): The new location where to move the
                source file to.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            FilePermissionException: If the file move operation is denied.
            SymbolicLinkResolutionException: If the specified path cannot be
                resolved or is a broken symbolic link.
            FileRelocationException: If the file cannot be moved
                to the destination.
        """

    @abstractmethod
    def copy(self, source: PurePath, target: PurePath, follow_symlinks=True):
        """Copies the source file to the target location.

        Implementations are only obligated to be able to copy regular files and
        directories. The capability to copy files of any other type shall
        remain optional. Implementations can, but are not obligated to, copy
        filesystem metadata to the target file.

        If the argument `follow_symlinks` is `True`, then the provided source
        path should be followed with regards to symbolic links. Irrespective of
        that, when copying a directory that contains symbolic links, all
        symbolic links are replaced at the target directory with the
        corresponding resolved regular file or directory that the link
        points to. Symbolic links should never be copied as symbolic links when
        part of a directory that is being copied.

        If the specified target path already exists, the corresponding file
        must be of the same type as the file referred to by the source path.
        For regular files, the target file is replaced by the source file in
        case it already exists. For directories, the content of the source
        directory is recursively copied into the target directory, replacing
        any regular files already present in it. All files present in the
        target directory which do not exist in the source directory are left
        in place and are not overwritten.

        Args:
            source (PurePath): The location of the file to copy.
            target (PurePath): The location where to copy the source file to.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Raises:
            FileNotFoundException: If the file at the specified source path
                does not exist.
            FilePermissionException: If the file copy operation is denied.
            SymbolicLinkResolutionException: If the specified source path
                cannot be resolved or is a broken symbolic link.
            FileCopyException: If the file cannot be copied to the destination.
        """

    @abstractmethod
    def remove(self, path: PurePath, follow_symlinks=True):
        """Removes the specified file.

        This method follows symbolic links depending on the value of
        the `follow_symlinks` argument. If the file at the specified path is a
        symbolic link and `follow_symlinks` is `True`, then the file the link
        refers to and the symbolic link itself are both removed. If the file is
        a symbolic link and `follow_symlinks` is `False`, then only the link
        is removed, but not the target file it points to. Removing a directory
        will also remove all of its content.

        Args:
            path (PurePath): The file to remove.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Raises:
            FileNotFoundException: If the file at the specified path
                does not exist.
            FilePermissionException: If the file remove operation is denied.
            SymbolicLinkResolutionException: If the specified path cannot be
                resolved or is a broken symbolic link.
            FileRemovalException: If the file at the specified path cannot
                be removed.
        """

    @abstractmethod
    def list_files_of_directory(
        self,
        path: PurePath,
        recursive=False
    ) -> Generator[PurePath, None, None]:
        """Lists all files in a directory.

        If `recursive` is `True`, then all subdirectories are traversed
        recursively.

        Args:
            path (PurePath): The path to check.
            recursive (bool): A flag indicating whether to traverse
                all subdirectories recursively to yield their subdirectories
                as well.

        Yields:
            The `PurePath` objects representing the content of the directory.

        Raises:
            FileNotFoundException: If no directory or file exists at
                the specified path.
            FilePermissionException: If the listing operation is denied.
            DirectoryListingException: If the directory listing cannot
                be created or if the file at the specified path is
                not a directory.
        """

    @abstractmethod
    def flush_system(self):
        """Flushes the state of the filesystem.

        This may cause intermediate buffers to be written to disk
        or internal states to be reset. During normal operations there is
        usually no need to use this method.

        Raises:
            FileIOException: If an I/O error occurs.
        """

    @abstractmethod
    def get_lock_file_path(
        self,
        path: PurePath,
        follow_symlinks=True
    ) -> PurePath:
        """Gets the path to the lock file used by the `lock_file()`
        and `unlock_file()` methods.

        Args:
            path (PurePath): The path of the file to get the lock file for.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Returns:
            PurePath: The path to the lock file.

        Raises:
            FileIOException: If an I/O error occurs.
        """

    @abstractmethod
    def lock_file(self, path: PurePath, follow_symlinks=True):
        """Attempts to acquire an exclusive advisory lock on the specified file.

        If the argument `follow_symlinks` is `True`, then in case `path` refers
        to a symbolic link, the lock is acquired on the file of the final link
        target. Otherwise the lock is always acquired on the file of the
        specified path itself, and in case it is a symbolic link, the lock is
        acquired on the symbolic link. It is advised that callers are cautious
        about this distinctiveness because when relying on a lock which is
        established based on a symbolic link, exclusive access to the actual
        file the link refers to cannot be guaranteed since another process
        might access that file directly or via a different symbolic link
        elsewhere in the filesystem.

        The acquired lock is an advisory lock, i.e. exclusive access can only be
        guaranteed if all involved actors check for the lock state via this
        method before attempting to gain access to the underlying resource.
        Advisory locks are not enforced and rely on the cooperation of the
        involved processes. The acquired lock shall be system-global.

        Implementations are not obligated to perform deadlock detection. It is
        the responsibility of the calling code to ensure a deadlock
        cannot occur. Any file lock acquired with `lock_file()` must be later
        released again with exactly one call to `unlock_file()`. In case
        application code fails to do so, including due to a program crash, no
        attempt has to be made by this method to detect abandoned locks and
        subsequent calls to this method may result in a deadlock.
        The file lock does not have to be reentrant.

        This method must be non-blocking. If a lock cannot be acquired because
        the underlying file is already locked, this method must raise
        an exception of type `FileLockAcquisitionException`.
        Implementations are not obligated to detect lost locks.

        Args:
            path (PurePath): The path of the file to try to lock.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Raises:
            FileLockAcquisitionException: If a lock for the specified file
                could not be acquired because it is already locked.
            FileNotFoundException: If the parent directory at the specified
                path does not exist.
            FilePermissionException: If a file lock cannot be placed in the
                filesystem due to insufficient permission.
            SymbolicLinkResolutionException: If the specified path cannot be
                resolved or is a broken symbolic link.
            FileIOException: If an I/O error occurs.
        """

    @abstractmethod
    def unlock_file(self, path: PurePath, follow_symlinks=True):
        """Releases the exclusive advisory lock held on the specified file.

        If the file denoted by the specified path does not have a lock
        associated with it, then this method has no effect. However, please
        note that it is generally not safe for a lock holder to call this
        method multiple times because it is not obligated to check that the
        calling code is in fact the holder of the lock it might release. Thus,
        it is possible for a caller to release a lock he does not own.

        If the argument `follow_symlinks` is `True`, then in case `path` refers
        to a symbolic link, it is attempted to release the lock on the file of
        the final link target. Otherwise the lock is always attempted to be
        released on the file of the specified path itself, and in case it is a
        symbolic link, the lock is attempted to be released on the symbolic
        link.

        Args:
            path (PurePath): The path of the file to release the lock for.
            follow_symlinks (bool): Indicates whether to follow symbolic
                links to their respective targets.

        Raises:
            FilePermissionException: If a file lock cannot be released in
                the filesystem due to insufficient permission.
            SymbolicLinkResolutionException: If the specified path cannot be
                resolved or is a broken symbolic link.
            FileIOException: If an I/O error occurs.
        """

    @abstractmethod
    def create_temp_file(
        self,
        directory: Optional[Union[PurePath, str]] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None
    ) -> PurePath:
        """Creates a temporary file in a temporary filesystem location.

        Args:
            directory (PurePath | str): The path to the directory where the
                temporary file should be created. This could also be a
                non-temporary directory. If specified, the directory must
                already exist. Otherwise, if left `None`, it is automatically
                created in a temporary location.
            prefix (str): An optional prefix for the created file name.
            suffix (str): An optional suffix for the created file name.

        Returns:
            PurePath: A `PurePath` denoting the created temporary file.

        Raises:
            FileNotFoundException: If the specified directory does not exist.
            FilePermissionException: If the temporary file creation is denied.
            TemporaryFileCreationException: If the temporary file could
                not be created.
        """

    @abstractmethod
    def create_temp_dir(
        self,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None
    ) -> PurePath:
        """Creates a temporary directory.

        Args:
            prefix (str): An optional prefix for the created directory name.
            suffix (str): An optional suffix for the created directory name.

        Returns:
            PurePath: A `PurePath` denoting the created temporary directory.

        Raises:
            FilePermissionException: If the temporary directory
                creation is denied.
            TemporaryFileCreationException: If the temporary directory could
                not be created.
        """
