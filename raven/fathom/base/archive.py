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
"""Handling of archive files in the filesystem.

Provides an API for dealing with archive files in a consistent, unified,
format-independent way.

An `ArchiveFile` intance has a state and a format and consists of a
collection of `ArchiveFileMember` instances. The members represent the
content of the archive. Users may use those classes to create and edit
an archive file, and then use `ArchiveFile.pack()`
and `ArchiveFile.extract()` to perform archiving operations
in the filesystem.

All operations related to classes of this module may raise
an `ArchiveFileIOException`, even when the underlying operation does
not directly involve filesystem I/O, e.g. attempting to change an object
in a way that would result in an invalid state.

#### Classes:

* `ArchiveFileMember`
* `ArchiveFile`
* `ArchiveFileIO`

#### Exceptions:

* `ArchiveFileIOException`


Author: Phil Gaiser
"""

from abc import abstractmethod
from typing import Union, Optional, TypeAlias
from collections.abc import Sequence
from enum import Enum
from pathlib import PurePath

from raven.fathom.base.typing import Interface, TypeCheck
from raven.fathom.base.decorators import inject
from raven.fathom.base.file import File, FileSize, FileSizeUnit
from raven.fathom.base.file import FileIOException, FileNotFoundException


# Type aliases
FileOrPath: TypeAlias = Union[File, PurePath, str]
BytesOrFileRef: TypeAlias = Union[bytes, bytearray, FileOrPath]


class ArchiveFileIOException(FileIOException):
    """Indicates an illegal or failed operation regarding `ArchiveFile`
    and `ArchiveFileMember` instances.

    Is a subclass of `FileIOException`.
    """


class ArchiveFileMember:
    """A member of an archive file.

    `ArchiveFileMember` objects can be created independently of `ArchiveFile`
    objects, however, to be useful a member is typically
    associated at some point with a specific archive.
    Each member must have a name, which is always the same regardless of the
    state of an archive. A member may contain data directly or may point to a
    file within the filesystem.

    All attributes of members are immutable, that is, once instantiated, a
    member cannot change its name, file path etc. To apply changes in an
    archive, members need to be replaced. A notable exception to this rule is
    the data content of regular file archive members. As long as a member is
    transient, its data content as returned by `ArchiveFileMember.data()`
    can be mutated. However, this does not apply to member data which is
    backed by actual files in the filesystem, in which case changing the data
    of the member will not overwrite the content of the file.

    Archive members can be children of other members. This may be indicated by
    separating members by '/' characters within the name. For example,
    the member with the name 'hello/stuff' has node name 'stuff',
    a (canonical) name 'hello/stuff', and is a child of the 'hello' member.

    Two `ArchiveFileMember` objects are considered equal if they have the
    same canonical name. Other properties as well as the data content are not
    considered to determine equality.

    Attributes:
        name (str): The immutable canonical name of the archive member.
        name_parts (list): A list of `str` node names that form
            the archive member.
        node_name (str): The name of the final archive member node. This is
            the last part of the canonical name path.
        file (File): The filesystem file that the member represents.
            May be `None` if the member is not directly backed by a file,
            or when the underlying archive is in a packed state.
        is_transient (bool): Indicates whether the data content of the member
            is backed by a file in the filesystem (`False`), or the data only
            resides in memory (`True`).
        is_directory (bool): Indicates whether the member is a
            directory (`True`), or a regular file with content (`False`).
    """

    def __init__(self, name: str, content: Optional[BytesOrFileRef] = None):
        """Initalizes a new `ArchiveFileMember` instance.

        A member must have a non-empty name.
        If the content is left `None`, then a transient directory member
        is initialized. If the content is specified as a `bytes` or `bytearray`
        object, then the member is initialized as a transient regular file with
        the content of those bytes. If the content is specified as a `File`,
        `PurePath` or `str`, then that is interpreted as a file path to an
        existing file in the filesystem, which may be a directory
        or regular file.

        Args:
            name (str): The name of the member. Must not be empty.
            content (bytes | File): The data of the member.
                May be in-memory data (`bytes` or `bytearray`), or data located
                in a filesystem file (`File`, `PurePath` or `str`).
                May be `None`.
        """
        if not name:
            raise ArchiveFileIOException(
                None,
                "Archive file member name must not be empty"
            )

        fs_file = data = is_transient = is_dir = None
        if content is not None:
            if isinstance(content, (PurePath, str)):
                content = File(content)

            if isinstance(content, File):
                fs_file = content
                is_transient = False
                is_dir = fs_file.is_directory()
            elif isinstance(content, (bytes, bytearray)):
                data = bytearray(content)
                is_transient = True
                is_dir = False
            else:
                raise TypeError(
                    "Invalid type for archive file member content: "
                    "Expected File, PurePath, str, bytes or bytearray, "
                    f"found {type(content)}"
                )
        else:
            is_transient = True
            is_dir = True

        self._name = name
        self._fs_file = fs_file
        self._data = data
        self._is_transient = is_transient
        self._is_dir = is_dir

    @property
    def name(self) -> str:
        """The full canonical name of this member."""
        return self._name

    @property
    def name_parts(self) -> list:
        """The list of node name parts of this member,
        as a `list` of `str`.
        """
        return self._name.split("/")

    @property
    def node_name(self) -> str:
        """The name of the node of this member."""
        return self.name_parts[-1]

    @property
    def file(self) -> Optional[File]:
        """The file in the filesystem which this member represents.

        May be `None` if this member is not backed by a file.
        """
        return self._fs_file

    @property
    def is_transient(self) -> bool:
        """Indicates whether the data of this member is only stored in memory.

        A non-transient member has its data content stored
        in persistent storage.
        """
        return self._is_transient

    @property
    def is_directory(self) -> bool:
        """Indicates whether this member represents a directory."""
        return self._is_dir

    def data(self) -> bytearray:
        """Retrieves the data content of this member.

        May perform filesystem I/O if the content of this member is stored in
        the filesystem. If this member is transient, then all changes to its
        data are reflected by the returned `bytearray`, and all changes made to
        the returned `bytearray` will change the data of this member.

        If this method is used on a member that is a directory,
        an `ArchiveFileIOException` will be raised.

        Returns:
            bytearray: The raw data of this member.

        Raises:
            ArchiveFileIOException: If the data content of this member cannot
                be read. This may indicate an underlying filesystem I/O error.
                Or if this member is a directory.
        """
        if self.is_directory:
            raise ArchiveFileIOException(
                None,
                "Cannot get data of ArchiveFileMember instance "
                "that represents a directory"
            )

        if self.is_transient:
            assert self._data is not None
            return self._data

        try:
            assert self._fs_file is not None
            return bytearray(self._fs_file.read_all_bytes())
        except FileIOException as ex:
            raise ArchiveFileIOException(
                ex.file_path,
                "Failed to read ArchiveFileMember from the filesystem"
            ) from ex

    def __str__(self):
        return f"{ArchiveFileMember.__name__}[{self._name}]"

    def __eq__(self, value):
        TypeCheck.require_arg(value, ArchiveFileMember)
        return self.name == value.name

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self.name)


@inject
class ArchiveFileIO(Interface):
    """Interface for archive I/O operations.

    Implementations of this class are responsible to handle file
    system I/O related to operations of `ArchiveFile` instances.
    Since archive files on disk can have different formats, compression
    levels etc., various implementations may be provided to
    handle those differences.

    All methods declared by this interface may raise
    an `ArchiveFileIOException` to indicate a failed operation.
    """

    @abstractmethod
    def extract(self, archive: File, dest: File):
        """Extracts the packed archive file.

        The `archive` argument must be a packed archive on disk. It is
        extracted to the directory denoted by `dest`. If the `dest` directory
        does not exist, this method must attempt to create it.

        Args:
            archive (File): The file of the packed archive on disk.
            dest (File): The file of the destination directory where to extract
                the archive to.

        Raises:
            ArchiveFileIOException: If an I/O errors occurs.
        """

    @abstractmethod
    def compress(self, members: list[ArchiveFileMember], archive: File):
        """Writes the archive file to the filesystem.

        The given archive members are compressed into a single packed archive
        file on disk. If a file denoted by `archive` already exists in the file
        system, then that file may or may not be overwritten.

        Args:
            members (list): The `list` of `ArchiveFileMember` objects to
                write to the archive file on disk.
            archive (File): The compressed archive file to write to disk.

        Raises:
            ArchiveFileIOException: If an I/O errors occurs.
        """

    @abstractmethod
    def read_packed_members(self, archive: File) -> list[ArchiveFileMember]:
        """Determines the member list of the packed archive file.

        The list of archive members must be extracted from the compressed
        archive without extracting it first.

        Args:
            archive (File): The file representing the packed archive file
                on disk.

        Returns:
            list: A `list` of `ArchiveFileMember` objects.

        Raises:
            ArchiveFileIOException: If an I/O errors occurs.
            NotImplementedError: If the operation is not supported by the
                underlying archive file format.
        """


class ArchiveFile:
    """An archive of files.

    An archive file is a collection of files and directories which
    are represented as `ArchiveFileMember` instances. Each archive file
    has a state. An archive in the `ArchiveFile.State.PACKED` state is
    represented in the filesystem by a single regular file which contains
    all the archive members in a compressed format. If that archive is
    extracted, then its state changes to `ArchiveFile.State.EXTRACTED` and
    the archive is represented in the filesystem by a directory which
    contains all the archive members as regular files and folders in
    a directory tree. Lastly, an archive can also be in
    a `ArchiveFile.State.TRANSIENT` state, which means that the archive
    itself is not backed by any files in the filesystem but merely exists
    as an object in memory. This is useful to dynamically create archives
    in memory, add members to it which can be scattered across the file
    system, and then pack all those individual files and directories into
    a single compressed archive at a specific location.

    Attributes:
        state (ArchiveFile.State): The current state of this archive file.
            Readonly.
        file (File): The file of this archive in the filesystem. Readonly.
        destination (File): The destination where to write the files in the
            filesystem when packing or extracting. Can be set.
        file_format (ArchiveFile.Format): The archive file format. Readonly.
        auto_remove (bool): Configuration value specifying whether files should
            get automatically removed after processing. Can be set.
    """

    class State(Enum):
        """The state of an archive file object."""

        TRANSIENT = "transient"

        EXTRACTED = "extracted"

        PACKED = "packed"

        def __str__(self):
            return self.value

    class Format(Enum):
        """The format of a packed archive file when saved in the filesystem.

        An archive file format is associated with a corresponding file
        extension, which is used to identify such archives within
        the filesystem.
        """

        ZIP = "zip"

        TAR = "tar"

        TAR_GZ = "tar.gz"

        TAR_BZIP2 = "tar.bz2"

        TAR_XZ = "tar.xz"

        def file_extension(self):
            """Returns the file extension used by this archive file format."""
            return "." + self.value

        def __str__(self):
            return self.name

    def __init__(self, file: FileOrPath, file_format: Format = Format.ZIP):
        """Initializes a new `ArchiveFile` instance.

        The state of the created `ArchiveFile` object will be determined based
        on whether the specified file exists. If the file exists in the file
        system and is a regular file, then it is treated as an existing
        compressed archive file. The format may be determined by the file
        extension. If the file exists in the filesystem and is a directory,
        then it is treated as an existing extracted archive file. Otherwise,
        if the file does not exist, then `ArchiveFile` object is treated as a
        transient archive.

        The archive file format used by default is `ArchiveFile.Format.ZIP`.

        Args:
            file (File): The filesystem file of the archive on disk.
                May also be specified as a `PurePath` object or `str` path.
            file_format (ArchiveFile.Format): The format of the archive
                file when writing to disk.

        Raises:
            ArchiveFileIOException: If the state of the archive in the
                filesystem as indicated by the given file cannot
                be determined.
        """
        TypeCheck.require_arg(file_format, ArchiveFile.Format)
        self._file = File(file)
        self._format: ArchiveFile.Format = file_format
        self._file_dest: Optional[File] = None
        self._io = ArchiveFileIO.instance(file_format)
        self._state: ArchiveFile.State = self._determine_state()
        self._member_list: Optional[list[ArchiveFileMember]] = None
        self._auto_remove: bool = False

    @property
    def state(self) -> State:
        """The state of this archive file, as an `ArchiveFile.State`."""
        return self._state

    @property
    def file(self) -> File:
        """The filesystem file of this archive file, as a `File`."""
        return self._file

    @property
    def destination(self) -> Optional[File]:
        """The destination file in the filesystem where files are written
        when the archive is packed or extracted, as a `File`.

        Can be set by a caller. May be `None` if no destination path has
        been set.
        """
        return self._file_dest

    @destination.setter
    def destination(self, value):
        self._file_dest = File(value)

    @property
    def file_format(self) -> Format:
        """The archive file format, as an `ArchiveFile.Format`."""
        return self._format

    @property
    def auto_remove(self) -> bool:
        """Whether to automatically remove processed files.

        This property is a configuration value specifying whether files should
        get automatically removed when processed by `pack()` and `extract()`.
        Can be set.
        """
        return self._auto_remove

    @auto_remove.setter
    def auto_remove(self, value: bool):
        TypeCheck.require_prop(value, bool, "ArchiveFile.auto_remove")
        self._auto_remove = value

    def get_members(self) -> Sequence[ArchiveFileMember]:
        """Gets all members of this archive.

        Returns:
            Sequence: A `Sequence` of `ArchiveFileMember` objects.

        Raises:
            ArchiveFileIOException: If the archive members in the
                underlying state cannot be determined or if an I/O error
                is encountered.
        """
        return list(self._get_members()) # Return a copy

    def set_members(self, members: Sequence[ArchiveFileMember]):
        """Sets all members of this archive.

        Any previously set members are potentially replaced.
        Members cannot be set when an archive file is in
        state `ArchiveFile.State.PACKED`.
        This archive file will take ownership of the specified
        members objects.

        Args:
            members (Sequence): The `Sequence` of `ArchiveFileMember`
                objects to set.

        Raises:
            ArchiveFileIOException: If this archive file is in a packed state.
        """
        TypeCheck.require_arg(members, Sequence)
        if self.state == ArchiveFile.State.PACKED:
            raise ArchiveFileIOException(
                str(self._file.path),
                "Cannot set members of a packed archive file"
            )

        self._member_list = list(members)

    def get_member_by_name(self, name: str) -> Optional[ArchiveFileMember]:
        """Gets the member with the specified name.

        Args:
            name (str): The name of the archive file member to get.

        Returns:
            ArchiveFileMember: The `ArchiveFileMember` object that is part of
                this archive and has the specified name. May be `None` if this
                archive has no member with the specified name.

        Raises:
            ArchiveFileIOException: If the archive members cannot be
                determined or an I/O error occurs.
        """
        TypeCheck.require_arg(name, str)
        for member in self._get_members():
            if member.name == name:
                return member

        return None

    def pack(self):
        """Compresses all files of this archive into a single archive file.

        All members of this archive will be packed into the file specified by
        the `destination` attribute of this instance, or, if not set, an
        automatically generated file path. The `file` attribute will be
        adjusted accordingly by this method to point to the compressed archive.

        If the `auto_remove` attribute is set to `True`, then successfully
        packing this archive will result in all copies of member files outside
        of the created packed archive to be automatically deleted.

        Raises:
            ArchiveFileIOException: If this archive file is not in
                a packable state, cannot be packed, or the clean up
                operation fails.
        """
        if not self._is_in_packable_state():
            raise ArchiveFileIOException(
                str(self._file.path),
                f"Cannot pack archive in {self._state} state"
            )

        target_file = self._get_io_file_obj()
        self._compress_archive_file(target_file)
        if self.auto_remove:
            self._clean_up_after_packing()

        self._change_state(target_file, ArchiveFile.State.PACKED)

    def extract(self):
        """Extracts all files of this archive.

        All members of this archive will be extracted to individual files and
        directories under a single extracted archive directory specified by
        the `destination` attribute of this instance, or, if not set, an
        automatically generated directory. The `file` attribute will be
        adjusted accordingly by this method to point to the extracted archive
        directory. If the destination directory does not already exist, it will
        be automatically created.

        If the `auto_remove` attribute is set to `True`, then successfully
        extracting this archive will result in the packed archive file to be
        automatically deleted.

        Raises:
            ArchiveFileIOException: If this archive file is not in
                an extractable state, cannot be extracted, or the clean up
                operation fails.
        """
        if not self._is_in_extractable_state():
            raise ArchiveFileIOException(
                str(self._file.path),
                f"Cannot extract archive in {self._state} state"
            )

        target_file = self._get_io_file_obj()
        self._extract_archive_file(target_file)
        if self.auto_remove:
            self._clean_up_after_extracting()

        self._change_state(target_file, ArchiveFile.State.EXTRACTED)

    def add(self, member: ArchiveFileMember):
        """Adds the specified member to this archive.

        This archive must not be in a packed state.

        Args:
            member (ArchiveFileMember): The archive file member to add.

        Raises:
            ArchiveFileIOException: If this archive file is in a packed state.
        """
        TypeCheck.require_arg(member, ArchiveFileMember)
        if self.state == ArchiveFile.State.PACKED:
            raise ArchiveFileIOException(
                str(self._file.path),
                "Cannot add member to archive in packed state"
            )

        if self.contains(member):
            if member.is_directory:
                existing_member = self.get_member_by_name(member.name)
                assert existing_member is not None
                if existing_member.is_directory:
                    return

            raise ArchiveFileIOException(
                str(self._file.path),
                f"Archive file member '{member.name}' is already present"
            )

        members = self._get_members()
        for sub_member in self._split_member(member):
            if not self.contains(sub_member):
                members.append(sub_member)

        members.append(member)

    def remove(self, member: ArchiveFileMember) -> bool:
        """Removes the specified member from this archive.

        This archive must not be in a packed state.

        Args:
            member (ArchiveFileMember): The archive file member to remove.

        Returns:
            bool: `True` if removed, `False` if specified member
                does not exist in this archive.

        Raises:
            ArchiveFileIOException: If this archive file is in a packed state.
        """
        TypeCheck.require_arg(member, ArchiveFileMember)
        if self.state == ArchiveFile.State.PACKED:
            raise ArchiveFileIOException(
                str(self._file.path),
                "Cannot remove member from archive in packed state"
            )

        member_name = member.name
        self._ensure_members_initialized()

        members = self._get_members()
        to_rem = None
        for item in members:
            if item.name == member_name:
                to_rem = item
                break

        if to_rem is not None:
            members.remove(to_rem)
            if to_rem.is_directory:
                to_rem_children = []
                member_name_parts = member_name.split("/")
                parts_size = len(member_name_parts)
                for item in members:
                    if item.name_parts[:parts_size] == member_name_parts:
                        to_rem_children.append(item)

                for child in to_rem_children:
                    members.remove(child)

            return True

        return False

    def contains(self, member: ArchiveFileMember) -> bool:
        """Indicates whether this ArchiveFile contains the specified member.

        Args:
            member (ArchiveFileMember): The archive file member to check.

        Returns:
            bool: `True` if this archive file contains the specified member
                file, `False` if it does not contain the member.

        Raises:
            ArchiveFileIOException: If the members have to be retrieved from a
                packed archive file and an I/O errors occurs.
        """
        TypeCheck.require_arg(member, ArchiveFileMember)
        member_name = member.name
        return any(m.name == member_name for m in self._get_members())

    def member_count(self) -> int:
        """Indicates the amount of members in this archive.

        Returns:
            int: How many members this archive file has.
        """
        return len(self._get_members())

    def size(self) -> FileSize:
        """The size of the archive.

        The size of a packed archive is simply the size of the underlying file
        in the filesystem. Please note that the content of a packed archive
        file might be compressed. The size of an extracted archive is the sum
        of all filesystem files that are part of the archive. The size of a
        transient archive is the sum of all members as they reside in memory,
        where directory members themselves have a size of zero bytes.

        Returns:
            FileSize: The size of this archive, as a `FileSize` object with
                unit `FileSizeUnit.BYTE`.
        """
        try:
            return self._read_size()
        except FileIOException as ex:
            raise ArchiveFileIOException(
                str(self._file.path),
                f"Failed to read size of {self._state} archive file"
            ) from ex

    def _get_members(self):
        self._ensure_members_initialized()
        assert self._member_list is not None
        return self._member_list

    def _read_size(self):
        if self._state == ArchiveFile.State.PACKED:
            return self._file.size()

        return FileSize(
            sum(
                len(member.data())
                if member.is_transient
                else member.file.size().in_bytes() # type: ignore
                for member in filter(
                    lambda m: not m.is_directory,
                    self._get_members()
                )
            ),
            FileSizeUnit.BYTE
        )

    def _get_io_file_obj(self):
        """Gets the target destination file for pack and extract operations."""
        if self._file_dest is not None:
            return self._file_dest

        if self._is_in_packable_state():
            return self._file.with_suffix(self._format.file_extension())

        if self._is_in_extractable_state():
            if self._file.get_suffix() == self._format.file_extension():
                return self._file.without_suffix()

            return self._file.with_suffix("_")

        raise ArchiveFileIOException(
            str(self._file.path),
            "Could not determine target file for requested I/O operation of "
            f"{self._state} archive file '{self._file}'"
        )

    def _change_state(self, target_file, target_state):
        self._member_list = None  # Reset
        self._file_dest = None
        self._file = target_file
        self._state = target_state

    def _determine_state(self):
        if self._file.is_regular_file():
            if self._file.size().in_bytes() == 0:
                return ArchiveFile.State.TRANSIENT

            return ArchiveFile.State.PACKED

        if self._file.is_directory():
            return ArchiveFile.State.EXTRACTED

        if not self._file.exists():
            return ArchiveFile.State.TRANSIENT

        raise ArchiveFileIOException(
            str(self._file.path),
            f"Could not determine archive state for file '{self._file}'"
        )

    def _extract_archive_file(self, dest):
        if self._file == dest:
            raise ArchiveFileIOException(
                str(self._file.path),
                f"Cannot extract archive file to same location: '{dest}'"
            )

        self._io.extract(self._file, dest)

    def _compress_archive_file(self, dest):
        if self._state == ArchiveFile.State.EXTRACTED and self._file == dest:
            raise ArchiveFileIOException(
                str(self._file.path),
                f"Cannot compress archive file to same path: '{dest}'"
            )

        self._io.compress(self._get_members(), dest)

    def _clean_up_after_packing(self):
        try:
            for member in self._get_members():
                if member.file is not None:
                    self._try_clean_up(member.file)

            self._try_clean_up(self._file)
        except FileIOException as ex:
            raise ArchiveFileIOException(
                str(self._file.path),
                "Failed to clean up remnant files after pack operation"
            ) from ex

    def _clean_up_after_extracting(self):
        try:
            self._try_clean_up(self._file)
        except FileIOException as ex:
            raise ArchiveFileIOException(
                str(self._file.path),
                "Failed to clean up remnant files after extract operation"
            ) from ex

    def _try_clean_up(self, file):
        try:
            file.remove()
        except FileNotFoundException:
            pass

    def _is_in_packable_state(self):
        return self._state in (
            ArchiveFile.State.TRANSIENT,
            ArchiveFile.State.EXTRACTED
        )

    def _is_in_extractable_state(self):
        return self._state == ArchiveFile.State.PACKED

    def _split_member(self, member):
        dir_members = member.name.split("/")[:-1]
        split = []
        for i, _ in enumerate(dir_members):
            dm_name = "/".join(dir_members[:i+1])
            split.append(ArchiveFileMember(dm_name))

        return split

    def _ensure_members_initialized(self):
        if self._member_list is None:
            try:
                self._member_list = self._determine_members()
            except FileIOException as ex:
                raise ArchiveFileIOException(
                    str(self._file.path),
                    "Failed to initialize archive members "
                    f"for file '{self._file}'"
                ) from ex

    def _determine_members(self):
        if self._state == ArchiveFile.State.PACKED:
            return self._io.read_packed_members(self._file)

        member_list = []
        if self._state == ArchiveFile.State.TRANSIENT:
            return member_list

        if self._state == ArchiveFile.State.EXTRACTED:
            extracted_dir = self._file
            for file in extracted_dir.list_all_files():
                member_name = file.path.relative_to(extracted_dir).as_posix()
                member_list.append(ArchiveFileMember(member_name, file))

            return member_list

        raise ArchiveFileIOException(
            str(self._file.path),
            "Could not determine archive members "
            f"in state {self._state} for file '{self._file}'"
        )

    def __str__(self):
        return "\n".join([member.name for member in self._get_members()])

    def __iter__(self):
        """Returns an iterator over all archive members."""
        return iter(self._get_members())

    def __len__(self):
        """Returns the number of members in this archive."""
        return self.member_count()

    def __getitem__(self, member_name: str):
        """Returns the `ArchiveFileMember` object in this archive
        that has the specified name.
        """
        return self.get_member_by_name(member_name)

    def __iadd__(self, member):
        """Same as `lhs.add(rhs)`."""
        if isinstance(member, str):
            member = ArchiveFileMember(member)

        self.add(member)
        return self

    def __isub__(self, member):
        """Same as `lhs.remove(rhs)`."""
        if isinstance(member, str):
            member = ArchiveFileMember(member)

        self.remove(member)
        return self

    def __contains__(self, member):
        """Same as `rhs.contains(lhs)`."""
        if isinstance(member, str):
            member = ArchiveFileMember(member)

        return self.contains(member)
