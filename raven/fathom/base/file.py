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
"""Provides an API for working with files.

This module provides a primary API for interacting with the filesystem
through file objects. Instances of the `File` class encapsulate a path to a
file within a filesystem and provide methods to manipulate that file.

#### Enumerations:

* `FileType`
* `FileMode`
* `FileSizeUnit`

#### Classes:

* `FileSize`
* `FilePermission`
* `FileAccess`
* `File`
* `TemporaryFile`

#### Constants:

* `FILE_READ_ALL`
* `FILE_POSITION_BEGIN`
* `FILE_RESIZE_TO_CURRENT_POSITION`

#### Exceptions:

The following diagram illustrates the exception hierarchy:

```

FileIOException
      |
      |-- InvalidFileModeException
      |
      |-- InvalidFileStateException
      |
      |-- CannotOpenFileException
      |
      |-- CannotCloseFileException
      |
      |-- FileNotFoundException
      |
      |-- FilePermissionException
      |
      |-- FilePositioningException
      |
      |-- FileLockAcquisitionException
      |
      |-- FileInputException
      |         |
      |         |-- FileQueryException
      |         |
      |         |-- SymbolicLinkResolutionException
      |         |
      |         |-- DirectoryListingException
      |         |
      |         |-- FileReadException
      |                   |
      |                   |-- FileTextDecodeException
      |
      |-- FileOutputException
                |
                |-- FileModificationException
                |
                |-- FileRelocationException
                |
                |-- FileCopyException
                |
                |-- FileRemovalException
                |
                |-- FileWriteException
                |         |
                |         |-- FileTextEncodeException
                |
                |-- FileCreationException
                          |
                          |-- TemporaryFileCreationException

```

All classes in this module may only raise a `FileIOException` or subclasses
thereof to indicate failure and errors of any kind related to file operations,
even when the cause of the underlying error is not directly related to file
system I/O. Problems caused by programming errors, like type errors, may still
be indicated by the appropriate standard library error type. For the sake of
brevity, individual methods may not document this conjuncture separately,
however, all methods cite the most concrete applicable exception type that can
be raised when called.

Author: Phil Gaiser
"""

import math
import re
import threading
import warnings
import weakref

from collections.abc import Generator
from enum import Enum, IntEnum
from os import PathLike
from pathlib import PurePath
from datetime import datetime
from typing import Optional, TypeAlias, Final, Union

from raven.fathom.base.typing import TypeCheck
from raven.fathom.base.system import FileSystem, SystemEnvironment
from raven.fathom.base.exceptions import FathomIOException


class FileIOException(FathomIOException):
    """Base exception used for all file-related I/O errors and general errors
    when doing file operations.

    Attributes:
        file_path (str): The path of the corresponding file for which
            the exception was raised, as a `str` path. May be `None`.
    """

    def __init__(self, file_path: Optional[str], message: str, *args):
        """Initializes a new `FileIOException` with the given path and message.

        Args:
            file_path (str): The path of the file associated with this error.
                May be `None`.
            message (str): The exception message.
        """
        super().__init__(message, *args)
        self.file_path: Optional[str] = file_path


class InvalidFileModeException(FileIOException):
    """An attempt was made to perform a file-related operation which
    the used file mode does not permit, or the file mode itself
    is invalid/unknown.
    """


class InvalidFileStateException(FileIOException):
    """A requested file operation cannot be carried out due to the presence of
    an invalid or incoherent state, or such a state was reached or would be
    reached as part of a requested operation which would violate the
    stated API contract.
    """


class CannotOpenFileException(FileIOException):
    """An attempt to open a file (with a valid file mode) failed."""


class CannotCloseFileException(FileIOException):
    """An attempt to close a file failed."""


class FileNotFoundException(FileIOException):
    """An operation was requested on a file which does not actually exist
    in the filesystem.
    """


class FilePermissionException(FileIOException):
    """A file operation was denied by the underlying operating system
    due to missing or insufficient permissions.
    """


class FilePositioningException(FileIOException):
    """An operation related to querying or mutating the position
    indicator of a file failed.
    """


class FileLockAcquisitionException(FileIOException):
    """The lock for a file resource could not be acquired."""


class FileInputException(FileIOException):
    """Base exception for all file input errors.

    This includes both reading file meta data, such as file attributes,
    as well as the reading of the actual file content.
    """


class FileQueryException(FileInputException):
    """Could not query an attribute or filesystem meta data of a file."""


class FileReadException(FileInputException):
    """A data read operation on a file failed."""


class FileTextDecodeException(FileReadException):
    """A text read operation on a file has failed due to a decoding error
    or the specified text encoding is invalid or unsupported.
    """


class SymbolicLinkResolutionException(FileInputException):
    """An attempt to resolve the target a symbolic link refers
    to has failed.

    This exception type is also used during file operations to indicate
    the detection of a broken link.
    """


class DirectoryListingException(FileInputException):
    """The generation of a directory listing has failed."""


class FileOutputException(FileIOException):
    """Base exception for all file output errors.

    This includes both mutating file meta data, such as file attributes,
    as well as the writing of the actual file content.
    """


class FileModificationException(FileOutputException):
    """Could not modify an attribute or filesystem meta data of a file."""


class FileWriteException(FileOutputException):
    """A data write operation on a file failed."""


class FileTextEncodeException(FileWriteException):
    """A text write operation on a file has failed due to an encoding
    error or the specified text encoding is invalid or unsupported.
    """


class FileRelocationException(FileOutputException):
    """The relocation (move operation) of a file has failed."""


class FileCopyException(FileOutputException):
    """The copy operation of a file has failed."""


class FileRemovalException(FileOutputException):
    """The deletion (remove operation) of a file has failed."""


class FileCreationException(FileOutputException):
    """The creation of a file (of any type) in the filesystem has failed."""


class TemporaryFileCreationException(FileCreationException):
    """The creation of a temporary file, either a regular file or
    a directory, has failed.
    """


class FileSizeUnit(Enum):
    """Enumerates supported measurement units of file sizes
    in digital storage.

    Both units with power of ten and power of two are supported.
    The base unit with factor `1` is the byte, which is the smallest
    addressable unit in digital storage.
    """

    BYTE = "B", 1

    KILOBYTE = "KB", 10**3

    KIBIBYTE = "KiB", 2**10

    MEGABYTE = "MB", 10**6

    MEBIBYTE = "MiB", 2**20

    GIGABYTE = "GB", 10**9

    GIBIBYTE = "GiB", 2**30

    @property
    def symbol(self) -> str:
        """The data unit symbol, as a `str`."""
        return self.value[0]

    @property
    def factor(self) -> int:
        """The data unit numeric factor, as an `int`."""
        return self.value[1]

    def has_base_two(self) -> bool:
        """Indicates whether this unit has a base of two.

        For `FileSizeUnit.BYTE` this method returns `True`.

        Returns:
            bool: `True` if this unit has a base of 2, `False` otherwise.
        """
        return math.log2(self.factor).is_integer()

    def has_base_ten(self) -> bool:
        """Indicates whether this unit has a base of ten.

        For `FileSizeUnit.BYTE` this method returns `True`.

        Returns:
            bool: `True` if this unit has a base of 10, `False` otherwise.
        """
        return math.log10(self.factor).is_integer()

    def __str__(self):
        return self.symbol

    @staticmethod
    def with_symbol(symbol: str) -> "FileSizeUnit":
        """Returns the `FileSizeUnit` that has the given symbol.

        Args:
            symbol (str): The symbol of the unit to return.

        Returns:
            FileSizeUnit: The unit with the specified symbol.

        Raises:
            ValueError: If the specified symbol string cannot
                be mapped to a file size unit.
        """
        symbol_lower = symbol.lower()
        for unit in FileSizeUnit:
            if unit.symbol.lower() == symbol_lower:
                return unit

        raise ValueError(f"'{symbol}' is not a valid file size unit")


class FileSize:
    """The size of a file in digital storage.

    Instances of this class are immutable. Use the `with_unit()` method
    on an instance to convert between file size units.

    Attributes:
        value (float): The size value expressed in the corresponding unit.
        unit (FileSizeUnit): The size unit of measure.
    """

    def __init__(self, value: Union[int, float], unit: FileSizeUnit):
        """Initializes a new `FileSize` instance.

        Args:
            value (int | float): The value of the file size, expressed in
                the specified unit.
            unit (FileSizeUnit): The unit of the specified value.
        """
        TypeCheck.require_arg(unit, FileSizeUnit)
        if not isinstance(value, float):
            value = float(value)

        if value < 0.0:
            raise ValueError(
                "Invalid argument 'value' for FileSize: "
                "File size must not be negative"
            )

        self._value = value
        self._unit = unit

    @property
    def value(self) -> float:
        """The size value, as a `float`."""
        return self._value

    @property
    def unit(self) -> FileSizeUnit:
        """The unit of the size value, as a `FileSizeUnit`."""
        return self._unit

    def with_unit(self, unit: FileSizeUnit, rounding: Optional[int] = None):
        """Converts this file size to the specified unit.

        Args:
            unit (FileSizeUnit): The unit to convert to.
            rounding (int): To how many decimal digits of precision to round
                the result of the conversion to. Must be a positive `int`.
                May be `None` to not round at all.

        Returns:
            FileSize: A `FileSize` with the value converted to the given unit.
        """
        if self._unit == unit:
            converted_value = self._value
        else:
            converted_value = (self._value * self._unit.factor) / unit.factor

        if rounding is not None:
            converted_value = round(converted_value, rounding)

        return FileSize(converted_value, unit)

    def in_bytes(self) -> int:
        """Returns this file size in bytes.

        Returns:
            int: This file size expressed in number of bytes, with the
                size value converted to an `int`.
        """
        return int(self.with_unit(FileSizeUnit.BYTE).value)

    def as_human_readable(self) -> "FileSize":
        """Returns this file size in a unit that is best readable by a human.

        This method may perform appropriate unit conversions to represent this
        file size value in a preferably concise, to humans easy-to-understand
        scale. Rounding may be applied as deemed appropriate.

        Returns:
            FileSize: This file size in an appropriate unit.
        """
        for unit in reversed(FileSizeUnit):
            if not unit.has_base_ten():
                continue

            converted_size = self.with_unit(unit, rounding=2)
            if converted_size.value >= 1.0:
                return converted_size

        return self.with_unit(FileSizeUnit.BYTE)  # == 0B

    def __str__(self):
        value = int(self._value) if self._value.is_integer() else self._value
        return f"{value}{self._unit}"

    def __repr__(self):
        return f"FileSize(value={self._value}, unit={self._unit})"

    def __eq__(self, other):
        if not isinstance(other, FileSize):
            raise TypeError(
                "Cannot compare FileSize instance "
                f"with object of type {type(other)}"
            )

        return self.in_bytes() == other.in_bytes()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.in_bytes())

    @staticmethod
    def from_string_value(value: str) -> "FileSize":
        """Parses a string representation of a file size.

        The given string value must contain a number, followed by an optional
        size unit specifier. If no size unit is specified, the number is
        assumed to be in bytes (`FileSizeUnit.BYTE`).
        Valid string-formatted file sizes include, for example:
        - "24"
        - "1KB"
        - "2MB"
        - "3 GB"
        - "  4.59KiB  "

        Args:
            value (str): The string representation of the file size.

        Returns:
            FileSize: A `FileSize` object equivalent to the
                given string representation.

        Raises:
            ValueError: If the string does not match a valid file size format.
        """
        match = re.match(
            r"^\s*(\d+(\.\d+)?)\s*([a-zA-Z]*)\s*$", value, re.IGNORECASE
        )
        if not match:
            raise ValueError(f"Invalid file size format: '{value}'")

        size_value = float(match.group(1))
        size_unit = match.group(3)
        if not size_unit:
            size_unit = "B"

        return FileSize(size_value, FileSizeUnit.with_symbol(size_unit))


class _FileModeCap(IntEnum):
    """Enumeration of raw/individual file mode capabilities.

    Meaning when a file is opened in a mode which possesses
    the capability (can be combined):

    Create: The file can be created if it does not already exist.
    Read: The file content can be read.
    Write: The file can be written to.
    Append: The file content can be appended to.
    """

    X = 0b1000  # Create

    R = 0b0100  # Read

    W = 0b0010  # Write

    A = 0b0001  # Append


class _FM:
    """Wrapper class for values of `FileMode` enum.

    This is used to wrap combinations of `_FileModeCap` into distinct objects
    to guarantee unique identities of all `FileMode` enum values.
    """

    def __init__(self, cap_bits: int):
        self.cap_bits: int = cap_bits


class FileMode(Enum):
    """Enumeration of possible modes when opening files.

    The declared file modes do not distinguish between text and binary modes.
    This behaviour deviates from the standard Python file operation functions
    and the underlying system C-API likewise
    (see [fopen()](https://cplusplus.com/reference/cstdio/fopen)
    for more information).

    Files are always opened in binary mode. Provided implementations for file
    operations perform proper platform-dependent encoding/decoding where
    necessary.
    """

    # Create.
    # Only allows the creation of the file. If the file is opened
    # in this mode and already exists, an error is raised.
    # Implementation Note:
    # This is effectively using the same mode as CREATE_WRITE ('xb') which
    # means the file is actually writable from the perspective of the OS,
    # however, attempting to write to a file that only has the create-bit
    # set in its mode will result in an error as a matter of API consistency.
    CREATE = _FM(_FileModeCap.X)

    # Read binary.
    # Allows reading of the file. If the file does not exist,
    # an error is raised. The opening position is 0 (zero).
    READ = _FM(_FileModeCap.R)

    # Write binary.
    # Allows writing to the file. If the file does already exist,
    # its content is overwritten. If it does not already exist, it is created.
    # The opening position is 0 (zero).
    WRITE = _FM(_FileModeCap.X | _FileModeCap.W)

    # Append binary.
    # Allows appending to the file. If the file does already exist,
    # all content that is written to it will be appended to the end
    # of the file. If it does not already exist, it is created. The opening
    # position is the end of the file.
    APPEND = _FM(_FileModeCap.X | _FileModeCap.A)

    # Read and Write.
    # Allows both reading and writing of the file. If the file does
    # not exist, an error is raised. The opening position is 0 (zero).
    READ_WRITE = _FM(_FileModeCap.R | _FileModeCap.W)

    # Read and Append.
    # Allows both reading and appending of the file. If the file does already
    # exist, all content that is written to it will be appended to the end
    # of the file. If it does not already exist, it is created. The opening
    # position is the end of the file.
    READ_APPEND = _FM(_FileModeCap.X | _FileModeCap.R | _FileModeCap.A)

    # Create and Write.
    # Creates the file and allows writing to it. If the file already exists,
    # an error is raised.
    CREATE_WRITE = _FM(_FileModeCap.X | _FileModeCap.W)

    # Create, Read and Write.
    # Creates the file and allows both reading from and writing to it.
    # If the file already exists, its content is overwritten.
    CREATE_READ_WRITE = _FM(_FileModeCap.X | _FileModeCap.R | _FileModeCap.W)

    def bits(self) -> int:
        """The file mode bits.

        Returns:
            int: The mode number representing the mode bits.
        """
        return self.value.cap_bits

    def can_create(self) -> bool:
        """Indicates whether this mode allows creating.

        Returns:
            bool: `True` if this file mode has the create bit set,
                `False` otherwise.
        """
        return bool(self.bits() & _FileModeCap.X)

    def can_read(self) -> bool:
        """Indicates whether this mode allows reading.

        Returns:
            bool: `True` if this file mode has the read bit set,
                `False` otherwise.
        """
        return bool(self.bits() & _FileModeCap.R)

    def can_write(self) -> bool:
        """Indicates whether this mode allows writing.

        Returns:
            bool: `True` if this file mode has the write bit set,
                `False` otherwise.
        """
        return bool(self.bits() & _FileModeCap.W)

    def can_append(self) -> bool:
        """Indicates whether this mode allows appending.

        Returns:
            bool: `True` if this file mode has the append bit set,
                `False` otherwise.
        """
        return bool(self.bits() & _FileModeCap.A)

    def __str__(self):
        return self.name


class FileType(Enum):
    """Enumeration of possible file types.

    The file type describes the kind of file a `File` object
    corresponds to in a real filesystem.
    """

    UNKNOWN = "?"

    REGULAR_FILE = "-"

    DIRECTORY = "d"

    SYMBOLIC_LINK = "l"

    NAMED_PIPE = "p"

    CHARACTER_DEVICE = "c"

    BLOCK_DEVICE = "b"

    SOCKET = "s"

    @property
    def symbol(self) -> str:
        """The filesystem symbol of this `FileType`,
        as a 1-character `str`.
        """
        return self.value[0]

    def __str__(self):
        return self.name


class FileAccess:
    """Access permission of a file.

    There are three access capabilities, which determine whether an entity can:
    (1) read, (2) write, (3) execute a file. Instances of this class represent
    access capabilities for a single file, although the meaning of such
    instance is contextual. For example, a `FileAccess` object can represent
    the individual access permissions that apply to a specific entity
    category (owner / group / other) of a file. It can also represent the
    access permissions which apply for a specific system user on
    a specific file.

    Instances of this class are mutable but do not conduct any
    filesystem I/O as this class is merely used as a data container.

    Attributes:
        can_read (bool): Whether reading of the file is allowed. Can be set.
        can_write (bool): Whether writing to the file is allowed. Can be set.
        can_execute (bool): Whether executing the file is allowed. Can be set.
    """

    def __init__(self, bits: tuple):
        """Initializes a new `FileAccess` instance.

        Args:
            bits (tuple): A 3-tuple of `bool` values representing the
                access permission bits.
        """
        TypeCheck.require_arg(
            bits, tuple, f"Expected tuple of bools but found {type(bits)}"
        )

        if len(bits) != 3:
            raise ValueError(
                "Tuple of protection bits must have length 3 "
                f"but found length {len(bits)}"
            )

        self._read = bool(bits[0])
        self._write = bool(bits[1])
        self._exec = bool(bits[2])

    @property
    def can_read(self) -> bool:
        """Indicates whether the READ permission bit is set, as a `bool`."""
        return self._read

    @can_read.setter
    def can_read(self, value: bool):
        TypeCheck.require_prop(value, bool, "FileAccess.can_read")
        self._read = value

    @property
    def can_write(self) -> bool:
        """Indicates whether the WRITE permission bit is set, as a `bool`."""
        return self._write

    @can_write.setter
    def can_write(self, value: bool):
        TypeCheck.require_prop(value, bool, "FileAccess.can_write")
        self._write = value

    @property
    def can_execute(self) -> bool:
        """Indicates whether the EXECUTE permission bit is set, as a `bool`."""
        return self._exec

    @can_execute.setter
    def can_execute(self, value: bool):
        TypeCheck.require_prop(value, bool, "FileAccess.can_execute")
        self._exec = value

    def __str__(self):
        """Returns this `FileAccess` object in the format 'rwx'.

        A zero-bit is represented as a '-' character, e.g. 'r-x' means:
        read- and execute permissions but no write permission.

        Returns:
            str: The permission bits as a formatted string.
        """
        r = "r" if self._read else "-"
        w = "w" if self._write else "-"
        x = "x" if self._exec else "-"
        return f"{r}{w}{x}"

    def __eq__(self, other):
        if not isinstance(other, FileAccess):
            raise TypeError(
                "Cannot compare FileAccess instance "
                f"with object of type {type(other)}"
            )

        return (
            self._read == other._read
            and self._write == other._write
            and self._exec == other._exec
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._read, self._write, self._exec))

    @staticmethod
    def of(readable=False, writable=False, executable=False):
        """Creates a `FileAccess` object with the specified bits set.

        By default all bits are off.

        Args:
            readable (bool): Whether the file is readable.
            writable (bool): Whether the file is writable.
            executable (bool): Whether the file is executable.

        Returns:
            FileAccess: The created `FileAccess` object.
        """
        return FileAccess((readable, writable, executable))

    @staticmethod
    def no_access():
        """Creates a `FileAccess` object with all bits set to zero (off).

        Returns:
            FileAccess: A `FileAccess` object with zero bits,
                effectively granting no permissions.
        """
        return FileAccess.of(
            readable=False, writable=False, executable=False
        )

    @staticmethod
    def all_access():
        """Creates a `FileAccess` object with all bits set to one (on).

        Returns:
            FileAccess: A `FileAccess` object with one bits,
                effectively granting all permissions.
        """
        return FileAccess.of(
            readable=True, writable=True, executable=True
        )


class FilePermission:
    """Permission attributes of a file.

    This class bundles all three permission attributes into a single type, each
    of which represents the category of entity that might access a file.
    The 'owner' permission attribute applies to the user who actually owns
    the file. The 'group' permission attribute applies to all users who are
    part of that user group, excluding the user who owns the file. The 'other'
    permission attribute applies to all other users in the system who are
    neither the owner nor part of the aforementioned group.

    Instances of this class are mutable but only carry the permission data of
    a file. To obtain and set the file permissions via filesystem I/O use the
    methods provided by the `File` class.

    Attributes:
        owner (FileAccess): The access permission bits of OWNER. Can be set.
        group (FileAccess): The access permission bits of GROUP. Can be set.
        other (FileAccess): The access permission bits of OTHER. Can be set.
    """

    def __init__(self, protection_bits: tuple):
        """Initializes a new `FilePermission` instance.

        Args:
            protection_bits (tuple): A 3-tuple of either 3-tuples of `bool`
                values or `FileAccess` objects representing the
                permission bits for owner/group/other.
        """
        TypeCheck.require_arg(
            protection_bits, tuple,
            f"Expected tuple but found {type(protection_bits)}"
        )

        if len(protection_bits) != 3:
            raise ValueError(
                "Protection bits tuple must have length 3 (owner/group/other) "
                f"but found length {len(protection_bits)}"
            )

        self._owner = self._as_acc_obj(protection_bits[0])
        self._group = self._as_acc_obj(protection_bits[1])
        self._other = self._as_acc_obj(protection_bits[2])

    @property
    def owner(self) -> FileAccess:
        """Permission bits for the OWNER of the file, as `FileAccess`."""
        return self._owner

    @owner.setter
    def owner(self, value: FileAccess):
        TypeCheck.require_prop(
            value, FileAccess, "FilePermission.owner"
        )
        self._owner = value

    @property
    def group(self) -> FileAccess:
        """Permission bits for the GROUP of the file, as `FileAccess`."""
        return self._group

    @group.setter
    def group(self, value: FileAccess):
        TypeCheck.require_prop(
            value, FileAccess, "FilePermission.group"
        )
        self._group = value

    @property
    def other(self) -> FileAccess:
        """Permission bits for OTHER of the file, as `FileAccess`."""
        return self._other

    @other.setter
    def other(self, value: FileAccess):
        TypeCheck.require_prop(
            value, FileAccess, "FilePermission.other"
        )
        self._other = value

    def _as_acc_obj(self, bits):
        return (
            bits if isinstance(bits, FileAccess)
            else FileAccess(bits)
        )

    def __str__(self):
        """Returns this `FilePermission` object as a formatted string.

        Each division (owner/group/other) is represented as
        a string-formatted `FileAccess` object, e.g.: 'rwxrw-r--'.

        Returns:
            str: The file permissions as a formatted string.
        """
        return f"{self._owner}{self._group}{self._other}"

    def __eq__(self, other):
        if not isinstance(other, FilePermission):
            raise TypeError(
                "Cannot compare FilePermission instance "
                f"with object of type {type(other)}"
            )

        return (
            self._owner == other._owner
            and self._group == other._group
            and self._other == other._other
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._owner, self._group, self._other))

    @staticmethod
    def of(
        owner: Optional[FileAccess] = None,
        group: Optional[FileAccess] = None,
        other: Optional[FileAccess] = None,
    ):
        """Creates a `FilePermission` object with the specified
        file permissions set.

        By default no permissions are granted for anyone.

        Args:
            owner (FileAccess): The file permissions for OWNER.
            group (FileAccess): The file permissions for GROUP.
            other (FileAccess): The file permissions for OTHER.

        Returns:
            FilePermission: The created `FilePermission` object.
        """
        return FilePermission((
            owner or FileAccess.no_access(),
            group or FileAccess.no_access(),
            other or FileAccess.no_access())
        )


# Constant to be used with the File.read() method to
# indicate that all bytes should be read from a file
FILE_READ_ALL: Final = -1

# Constant indicating the start position of a file position
# indicator, which may be returned by the File.position() method
FILE_POSITION_BEGIN: Final = 0

# Constant to be used with the File.resize() method to indicate that the
# target size should be the current position of the file position indicator.
FILE_RESIZE_TO_CURRENT_POSITION: Final = None

# A single Linefeed (LF) character
_LF: Final = "\n"

# A compiled regular expression matching CR-LF and CR chars.
# Used when decoding text data.
_REGEX_NL_TRANSLATION: Final = re.compile("(\r\n|\r)")

# Type aliases
FileOrPath: TypeAlias = Union["File", PathLike, str]


class File(PathLike):
    """A file object in a filesystem.

    A `File` object represents a specific file within an underlying file
    system, identified by a concrete filesystem path. Such a path may be
    absolute or relative. Using the former makes the specific file
    identification unambiguous, while using the latter may introduce a
    contextual dependency on the current working directory of the application
    process.

    A file object essentially encapsulates a path within a filesystem and
    provides additional properties and methods to interact with the actual
    individual file in the filesystem. The specific path of any `File` must be
    set during initialization and is immutable thereafter. Any method that
    accepts a `File` object as an argument is guaranteed to also work
    with `PurePath` objects and plain `str` objects representing the
    corresponding paths, automatically applying conversions where necessary.

    The actual interactions with the underlying filesystem are carried out
    through the `FileSystem` interface. That is, this class does not directly
    implement any operations related to filesystem I/O, but instead delegates
    all such operations to a `FileSystem` implementation. Upon first
    instantiation of any file object, an implementation of that interface is
    obtained and used in all subsequent operations. Thus, this class is
    suitable to be used anywhere in the codebase as for testing purposes the
    usage of an implementation can be set up which does not actually interact
    with the underlying filesystem of the host.

    For processing of text files, each instance can use an individual
    text encoding. If not explicitly specified, a default text encoding is
    used, which can also be adjusted globally. If not changed, the default
    text encoding used when processing text files is defined to be UTF-8.
    Please note that this might deviate from the default encoding used by
    the underlying operating system, and thus also from the behaviour of the
    standard Python library functions. However, this can be adjusted globally.
    The following code can be used to align with the underlying operating
    system and Python standard library behaviour:
    ```
    File.set_default_text_encoding(
        SystemEnvironment.instance().get_text_encoding()
    )
    ```

    Furthermore, the line separator used in text files can also be
    adjusted globally. The default line separator is platform-dependent but
    can be changed by using the `File.set_default_line_separator()` method.
    When reading and writing text files, the approach used by the File API is
    the same as universal newlines in the Python standard library. That is,
    both '\\r' and '\\r\\n' are converted into '\\n' for the `str` returned
    by API methods. Users should only use '\\n' characters in strings to
    terminate lines. When writing a `str` to a file, the `line_separator`
    property determines how lines are actually written to the filesystem file.

    Certain file operations require that the file must first be opened via
    the `open()` method. An open file must be closed after usage
    via the `close()` method. Failing to do so might result in the creation
    of a resource leak. A `File` instance can be used with a context manager,
    which takes care of properly closing the file when the corresponding
    context is exited. The generally recommended approach for opening and
    closing files is to use a context manager. For example, to write to a file
    you could do the following:
    ```
    with File("my_data.txt").open(FileMode.WRITE) as file:
        file.write("Some text data")
    ```

    By default, when interacting with a filesystem, all symbolic links are
    automatically resolved and followed to their respective targets. This also
    works for symbolic links pointing to symbolic links, etc. If the behaviour
    of a method deviates from the mentioned default, it is explicitly
    documented so. In any case, to instruct a `File` instance to not follow any
    symbolic links, the `follow_symlinks` property of that instance can be
    set to `False`.

    To ensure exclusive access to a particular file within the filesystem,
    a `File` instance provides the capability to lock a file. See the `lock()`
    method for details. The generally recommended approach is to use a context
    manager like in the following example:
    ```
    with File("global.txt").lock().open(FileMode.WRITE) as file:
        file.write("Some text data")
    ```

    This class implements the filesystem path protocol as specified by
    the `PathLike` abstract base class. Equality of `File` objects is
    determined by their paths (use the `==` operator). File objects can be
    combined to create new composite paths via the `/` operator.

    Attributes:
        name (str): The name of the file. Is read-only.
        path (PurePath): The path of the file. Is read-only.
        follow_symlinks (bool): Indicates whether to follow symbolic links to
            their respective targets when doing various file operations.
            Defaults to `True`. Can be set.
        text_encoding (str): The encoding to be used when reading/writing text.
            Defaults to `File.get_default_text_encoding()` for all new File
            instances. May be set to a different encoding.
        line_separator (str): The separator to use when writing text files.
            Defaults to `File.get_default_line_separator()` for all new
            File instances. May be set to a different separator.
    """

    _DEFAULT_TEXT_ENCODING: str = "UTF-8"

    # Deferred init
    _DEFAULT_LINE_SEPARATOR: str = None  # type: ignore

    # Deferred init
    _FS: FileSystem = None  # type: ignore

    _INIT_LOCK = threading.Lock()

    def __init__(self, path: FileOrPath):
        """Initializes a new `File` instance.

        Args:
            path (FileOrPath): The path of the file to initialize, either
                absolute or relative, as a `PurePath`, `File` or `str`.
        """
        if File._FS is None:
            File._init_internals()

        self._path = File._FS.init_path(path)
        self._handle = None
        self._is_open = False
        self._open_mode = None
        self._follow_symlinks = True
        self._text_encoding = File._DEFAULT_TEXT_ENCODING
        self._line_separator = File._DEFAULT_LINE_SEPARATOR
        self._is_locked = False
        weakref.finalize(self, File._finalize, self)

    @property
    def name(self) -> str:
        """The name of the file, as a `str`."""
        return self._path.name

    @property
    def path(self) -> PurePath:
        """The path of the file in the filesystem, as a `PurePath` object."""
        return self._path

    @property
    def follow_symlinks(self) -> bool:
        """Indicates whether to follow symbolic links to their respective
        targets when doing various file operations. Can be set.
        """
        return self._follow_symlinks

    @follow_symlinks.setter
    def follow_symlinks(self, value: bool):
        TypeCheck.require_prop(value, bool, "follow_symlinks")
        self._follow_symlinks = value

    @property
    def text_encoding(self) -> str:
        """Indicates the text encoding used by this file when reading and
        writing text data. Can be set to a different encoding.
        """
        return self._text_encoding

    @text_encoding.setter
    def text_encoding(self, value: str):
        TypeCheck.require_prop(value, str, "File.text_encoding")
        self._text_encoding = value

    @property
    def line_separator(self) -> str:
        """The separator to use when writing text files, as a `str` object.

        A line separator may be comprised of multiple characters. Those
        are the character bytes that are actually written to the underlying
        filesystem file. Can be set to a different string.
        """
        return self._line_separator

    @line_separator.setter
    def line_separator(self, value: str):
        TypeCheck.require_prop(value, str, "File.line_separator")
        self._line_separator = value

    def is_open(self) -> bool:
        """Indicates whether this file is open.

        Returns:
            bool: `True` if this file is open, `False` if it is closed.
        """
        return self._is_open

    def is_locked(self) -> bool:
        """Indicates whether this file is currently locked.

        This method only indicates whether this `File` instance has been locked
        by a previous call to the `lock()` method. It does not check for the
        presence of a lock file within the filesystem. This means that it
        cannot be used to check for lost or abandoned locks.

        Returns:
            bool: `True` if this file is locked, `False` if it is not locked.
        """
        return self._is_locked

    def size(self) -> FileSize:
        """Gets the size of this file.

        Measures the size of the file with respect to its data content.
        That is, it returns the number of bytes that the actual
        data associated with the file content requires, disregarding any
        file-system-specific overhead. Thus, for a regular file, this method
        returns the number of bytes in that file. For a directory, this
        method returns the total number of bytes of all files in that
        directory, including any subdirectories and the content thereof.
        Therefore, for an empty directory, this method returns zero bytes, not
        the 4096 bytes that the directory special file itself occupies in
        an ext4 filesystem with a block size of 4096 bytes, for example.

        Symbolic links are always followed, regardless of the value
        of the `follow_symlinks` property.

        Returns:
            FileSize: The size of the file content in the filesystem,
                as a `FileSize` with unit `FileSizeUnit.BYTE`.

        Raises:
            FileNotFoundException: If the file does not exist.
            FileQueryException: If the file size cannot be obtained.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
        """
        return FileSize(File._FS.get_size(self._path), FileSizeUnit.BYTE)

    def is_empty(self) -> bool:
        """Indicates whether this regular file or directory is empty.

        Returns `True` if and only if this file is either a regular file or
        directory and is considered empty. A regular file is considered empty
        if its size is exactly zero. The size of the file is measured similar
        to the `size()` method.
        A directory is considered empty if it contains no files of any type,
        which also implies that its size as measured by the `size()` method
        is zero. The reverse, however, is not necessarily true as a directory
        containing a regular empty file has a size of zero bytes but is not
        considered empty.

        Always returns `False` if this file is neither a regular file
        nor a directory.

        Symbolic links are always followed, regardless of the value
        of the `follow_symlinks` property.

        Returns:
            bool: `True` if this regular file or directory is considered empty,
                `False` if it is not empty or if this file is not a regular
                file or directory.

        Raises:
            FileNotFoundException: If the file does not exist.
            FileQueryException: If the file size or type cannot be determined.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
        """
        return File._FS.check_is_empty(self._path)

    def get_type(self) -> FileType:
        """Indicates the type of this file.

        If it should be checked whether the file could be a symbolic link,
        then the `follow_symlinks` property should be set to `False` prior
        to calling this method.

        Returns:
            FileType: The type of this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
        """
        return File._FS.get_type(self._path, self._follow_symlinks)

    def is_regular_file(self) -> bool:
        """Indicates whether this file is a regular file.

        Returns:
            bool: `True` if this file is a regular file.
                `False` otherwise.
        """
        return self._check_is_type(
            FileType.REGULAR_FILE,
            self._follow_symlinks
        )

    def is_directory(self) -> bool:
        """Indicates whether this file is a directory.

        Returns:
            bool: `True` if this file is a directory.
                `False` otherwise.
        """
        return self._check_is_type(FileType.DIRECTORY, self._follow_symlinks)

    def is_symbolic_link(self) -> bool:
        """Indicates whether this file is a symbolic link.

        Returns:
            bool: `True` if this file is a symbolic link.
                `False` otherwise.
        """
        return self._check_is_type(
            FileType.SYMBOLIC_LINK,
            follow_symlinks=False
        )

    def is_socket(self) -> bool:
        """Indicates whether this file is a socket.

        Returns:
            bool: `True` if this file is a socket.
                `False` otherwise.
        """
        return self._check_is_type(FileType.SOCKET, self._follow_symlinks)

    def is_named_pipe(self) -> bool:
        """Indicates whether this file is a named pipe.

        Returns:
            bool: `True` if this file is a named pipe.
                `False` otherwise.
        """
        return self._check_is_type(FileType.NAMED_PIPE, self._follow_symlinks)

    def is_character_device(self) -> bool:
        """Indicates whether this file is a character device.

        Returns:
            bool: `True` if this file is a character device.
                `False` otherwise.
        """
        return self._check_is_type(
            FileType.CHARACTER_DEVICE,
            self._follow_symlinks
        )

    def is_block_device(self) -> bool:
        """Indicates whether this file is a block device.

        Returns:
            bool: `True` if this file is a block device.
                `False` otherwise.
        """
        return self._check_is_type(
            FileType.BLOCK_DEVICE,
            self._follow_symlinks
        )

    def get_parent_directory(self) -> "File":
        """Gets the parent directory of this file.

        For directory paths which do not have a logical parent,
        e.g. '/' or drives, the parent is defined to be the same path as
        the path itself.

        This method does not follow symbolic links, as it operates on the
        path itself, not the underlying filesystem file that the path
        refers to.

        Returns:
            File: The enclosing parent directory of this file.
        """
        return File(File._FS.get_parent_path(self._path))

    def open(self, mode=FileMode.READ) -> "File":
        """Opens this file in the specified file mode.

        If this file is already open, then an `InvalidFileStateException`
        is raised. If this file is locked and calling `open()` raises any
        exception, then this file automatically releases the held lock.

        This method will always follow symbolic links regardless of the value
        of the `follow_symlinks` property.

        Args:
            mode (FileMode): The file mode to use when opening this file.

        Returns:
            File: This `File` instance.

        Raises:
            InvalidFileStateException: If the file is already open.
            InvalidFileModeException: If the file mode is invalid
                or unsupported.
            FileNotFoundException: If the file does not exist.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
        """
        TypeCheck.require_arg(mode, FileMode)
        try:
            self._checked_open(mode)
        except FileIOException:
            self._try_release_lock()
            raise

        return self

    def close(self):
        """Closes this file.

        If this file is already closed, then this method has no effect.

        Raises:
            CannotCloseFileException: If the file cannot be closed.
        """
        if self._is_open:
            File._FS.close_file_object(self._handle)
            self._handle = None
            self._open_mode: Optional[FileMode] = None
            self._is_open = False

    def read(self, n_bytes: int = FILE_READ_ALL) -> bytes:
        """Reads data from this file.

        If this file is not open, an `InvalidFileStateException` is raised.

        Args:
            n_bytes (int): How many bytes should be read by this operation.
                When specifying a negative `int` or `FILE_READ_ALL`, then the
                entire file content is read.

        Returns:
            bytes: The read data from the specified file.

        Raises:
            InvalidFileStateException: If the file is not open.
            InvalidFileModeException: If the open mode does not permit reading.
            FileReadException: If an I/O error occurs while reading data.
        """
        self._ensure_is_open(
            f"Cannot read from file '{self._path}': "
            "File must be opened before read operation"
        )

        assert isinstance(self._open_mode, FileMode)
        if not self._open_mode.can_read():
            raise InvalidFileModeException(
                str(self._path),
                f"Cannot read from file '{self._path}': "
                f"File is open in {self._open_mode} mode which does "
                "not allow reading"
            )

        return File._FS.read_from_file_object(self._handle, n_bytes)

    def read_text(self, n_bytes: int = FILE_READ_ALL) -> str:
        """Reads text data from this file.

        If this file is not open, an `InvalidFileStateException` is raised.

        The text data read from the underlying file is decoded according to
        the `text_encoding` property of this object. If this method is
        instructed to read a specific number of bytes via the `n_bytes`
        argument, and the encoding uses multiple bytes to encode a character,
        then when the last character in the sequence of bytes read happens to
        be truncated, this method might attempt to read more bytes than
        instructed such that the last character in the sequence can be properly
        decoded. Therefore, the actual number of bytes read by this method
        might be slightly larger than `n_bytes` if it is specified as
        a positive int.
        The returned string will contain Linefeed (LF) characters as a line
        separator, regardless of the value of the `line_separator` property
        which is only used when writing text.

        Args:
            n_bytes (int): How many bytes should be read by this operation.
                Please note that the number of bytes is not necessarily equal
                to the number of characters, depending on the underlying
                encoding. When specifying a negative `int` or `FILE_READ_ALL`,
                then the entire file content is read.

        Returns:
            str: The read text data from the specified file.

        Raises:
            InvalidFileStateException: If the file is not open.
            InvalidFileModeException: If the open mode does not permit reading.
            FileTextDecodeException: If the file text data cannot be decoded
                or the underlying set text encoding is invalid or unsupported.
            FileReadException: If an I/O error occurs while reading data.
        """
        return self._read_text_chunk(n_bytes)

    def write(self, data: Union[bytes, bytearray, str]) -> int:
        """Writes the given data to this file.

        If this file is not open, a `InvalidFileStateException` is raised.

        If the given data is of type `str`, then before it is written to the
        underlying file, it is first encoded according to the `text_encoding`
        property of this object. The given string should only contain
        Linefeed (LF) characters as line separators. The actual line separator
        used during writing of the filesystem file depends on the value of
        the `line_separator` property.

        Args:
            data (bytes): The data to write to this file,
                as a `bytes`, `bytearray` or `str` object.

        Returns:
            int: The number of bytes written to this file.

        Raises:
            InvalidFileStateException: If the file is not open.
            InvalidFileModeException: If the open mode does not permit writing
                or appending.
            FileTextEncodeException: If the specified data is text but cannot
                be encoded with the underlying set text encoding, or an
                encoding error occurs.
            FileWriteException: If an I/O error occurs while writing data to
                the file.
        """
        self._ensure_is_open(
            f"Cannot write to file '{self._path}': "
            "File must be opened before write operation"
        )

        operation = self._open_mode
        assert isinstance(operation, FileMode)
        if not operation.can_write() and not operation.can_append():
            raise InvalidFileModeException(
                str(self._path),
                f"Cannot write to file '{self._path}': "
                f"File is open in {operation} mode which does "
                "not allow writing"
            )

        if isinstance(data, str):
            data = self._encode_text(data)

        return File._FS.write_to_file_object(self._handle, data)

    def flush(self):
        """Flushes the data buffer to the file.

        If this file is not open, a `InvalidFileStateException` is raised.

        Raises:
            InvalidFileStateException: If the file is not open.
            FileWriteException: If an I/O error occurs while flushing data
                to the file.
        """
        self._ensure_is_open(
            f"Cannot flush file '{self._path}': "
            "File must be opened before flush operation"
        )

        File._FS.flush_file_object(self._handle)

    def position(self) -> int:
        """Gets the current file position indicator.

        The position indicator points to the numerical position within the
        file at which the next read and write operation will be carried out
        when the corresponding method is called. For example, if a file already
        contains 16 bytes of data and the position indicator is 0 (zero), a
        subsequent write operation writing 4 bytes will overwrite the first
        4 bytes in that file and advance the position indicator by the value 4.
        As another example, if a file already contains 16 bytes of data and the
        position indicator is 16 (i.e. at the end of the file), a subsequent
        write operation writing 4 bytes will append that data to the end of
        the file and advance the position indicator by 4 bytes.

        The file must be open to get its position.

        Returns:
            int: The current numerical value of the position indicator
                of this file.

        Raises:
            InvalidFileStateException: If the file is not open.
            FilePositioningException: If the file position cannot be queried.
        """
        self._ensure_is_open(
            f"Cannot get position of file '{self._path}': "
            "File must be opened before position can be queried."
        )

        return File._FS.get_file_object_position(self._handle)

    def set_position(self, offset: int):
        """Repositions the current file position indicator.

        The position indicator will point to the new specified offset position
        within this file. It must be open to set a new position.
        The file must support random access otherwise this method
        will raise an exception.

        Args:
            offset (int): The new value to set the position indicator
                of this file to. Must be equal to or greater than zero.

        Raises:
            InvalidFileStateException: If the file is not open.
            FilePositioningException: If the file position cannot be set,
                is invalid or the underlying filesystem file does not
                support random access.
        """
        self._ensure_is_open(
            f"Cannot set position of file '{self._path}': "
            "File must be opened before position can be set."
        )

        File._FS.set_file_object_position(self._handle, offset)

    def rewind_position(self) -> "File":
        """Rewinds the current file position indicator.

        Rewinding the file position indicator will reset the position to the
        start of the file. The file must be open to rewind its position.

        Returns:
            File: This `File` instance.

        Raises:
            InvalidFileStateException: If the file is not open.
            FilePositioningException: If the file cannot be rewinded, or the
                underlying filesystem file does not support rewinding.
        """
        self._ensure_is_open(
            f"Cannot rewind position of file '{self._path}': "
            "File must be opened before position can be rewinded."
        )

        File._FS.rewind_file_object_position(self._handle)
        return self

    def resize(
        self,
        size: Optional[FileSize] = FILE_RESIZE_TO_CURRENT_POSITION
    ):
        """Resizes this file such that it has the specified size.

        A resize operation either shrinks or extends a file to the
        specified size. If this file has a size which is larger than
        the specified size, then it is truncated and the excess data is lost.
        If this file has a size which is smaller than the specified size, then
        the extended part is filled with zero-bytes. The file must be open and
        the mode must allow writing. The file position indicator is not changed
        by this operation.

        If the size argument is specified
        to be `FILE_RESIZE_TO_CURRENT_POSITION`, then the new size is
        determined by the current file position indicator as returned by
        the `position()` method.

        Args:
            size (FileSize): The new size that this file should have. May
                be `FILE_RESIZE_TO_CURRENT_POSITION` to indicate that this file
                should be resized to the current file position indicator.

        Raises:
            InvalidFileStateException: If the file is not open.
            InvalidFileModeException: If the open mode does not permit writing.
            FileWriteException: If an I/O error occurs during resizing.
        """
        self._ensure_is_open(
            f"Cannot resize file '{self._path}': "
            "File must be opened before resize operation"
        )

        assert isinstance(self._open_mode, FileMode)
        if not self._open_mode.can_write():
            raise InvalidFileModeException(
                str(self._path),
                f"Cannot resize file '{self._path}': File is open "
                f"in {self._open_mode} mode which does not allow writing"
            )

        new_size = size
        if size is not None:
            TypeCheck.require_arg(size, FileSize)
            new_size = size.in_bytes()

        assert new_size is None or isinstance(new_size, int)
        File._FS.resize_file_object(self._handle, new_size)

    def access(self) -> FileAccess:
        """Indicates the user access capabilities for this file.

        The returned `FileAccess` object represents the access capabilities of
        what the underlying operating system user is allowed to do with the
        file on the level of the filesystem.

        The returned object is mutable but any changes made to it have no
        effect on the file within the filesystem. In order to make changes
        effective, the file permission bits must be adjusted by using
        the `set_permission()` method.

        Returns:
            FileAccess: A `FileAccess` object representing the access
                capabilities effective for the underlying invoking system user
                on this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file access capabilities
                cannot be queried.
        """
        return File._FS.check_file_access(self._path, self._follow_symlinks)

    def is_readable(self) -> bool:
        """Indicates whether this file is readable.

        The access capability of reading this file is indicated with respect
        to the underlying operating system user. This method does not raise any
        exceptions but only returns `True` if this file exists and the system
        user is in fact allowed to read this file.

        Returns:
            bool: `True` if this file is readable by the underlying invoking
                system user, `False` if this file is not readable for
                whatever reason.
        """
        try:
            return File._FS.check_file_access(
                self._path,
                self._follow_symlinks
            ).can_read
        except FileIOException:
            return False

    def is_writable(self) -> bool:
        """Indicates whether this file is writable.

        The access capability of writing to this file is indicated with respect
        to the underlying operating system user. This method does not raise any
        exceptions but only returns `True` if this file exists and the system
        user is in fact allowed to write to this file.

        Returns:
            bool: `True` if this file is writable by the underlying
                invoking system user, `False` if this file is not writable
                for whatever reason.
        """
        try:
            return File._FS.check_file_access(
                self._path,
                self._follow_symlinks
            ).can_write
        except FileIOException:
            return False

    def is_executable(self) -> bool:
        """Indicates whether this file is executable.

        The access capability of executing this file is indicated with respect
        to the underlying operating system user. This method does not raise any
        exceptions but only returns `True` if this file exists and the system
        user is in fact allowed to execute this file. Please note that this
        only relates to the execute-permission bit applicable to the underlying
        system user. A file marked as executable might still not be actually
        executable based on its data content. This method does not attempt
        to execute any files to perform the check.

        Returns:
            bool: `True` if the underlying invoking system user is allowed to
                execute this file, `False` otherwise or if any errors occur.
        """
        try:
            return File._FS.check_file_access(
                self._path,
                self._follow_symlinks
            ).can_execute
        except FileIOException:
            return False

    def permission(self) -> FilePermission:
        """Gets the file mode permission for this file.

        The returned object is mutable and permission bits can be set by
        the caller but in order to make changes effective within the file
        system, the caller must also call the `set_permission()` method.

        Returns:
            FilePermission: A `FilePermission` object representing the
                permissions effective for this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file permissions cannot be queried.
        """
        return File._FS.get_file_permissions(self._path, self._follow_symlinks)

    def set_permission(self, permission: FilePermission):
        """Sets the file mode permission for this file.

        Args:
            permission (FilePermission): The permission mode to set
                for this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileModificationException: If the file permissions cannot
                be modified or the operation is not permitted.
        """
        File._FS.set_file_permissions(
            self._path,
            permission,
            self._follow_symlinks
        )

    def owner(self) -> int:
        """Indicates the owner of this file.

        The owner corresponds to a user within the underlying operating system.

        Returns:
            int: The system user ID (UID) of the owner of this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file owner cannot be queried.
        """
        return File._FS.get_file_owner_uid(self._path, self._follow_symlinks)

    def owner_name(self) -> str:
        """Indicates the name of the owner of this file.

        The owner corresponds to a user within the underlying operating system.

        Returns:
            str: The name of the system user who owns this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file owner cannot be queried.
        """
        return File._FS.get_file_owner_name(self._path, self._follow_symlinks)

    def group(self) -> int:
        """Indicates the group of this file.

        The group corresponds to a user group within the underlying
        operating system.

        Returns:
            int: The system group ID (GID) of the group of this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file group cannot be queried.
        """
        return File._FS.get_file_group_gid(self._path, self._follow_symlinks)

    def group_name(self) -> str:
        """Indicates the name of the group of this file.

        The group corresponds to a user group within the underlying
        operating system.

        Returns:
            str: The name of the system group of this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file group cannot be queried.
        """
        return File._FS.get_file_group_name(self._path, self._follow_symlinks)

    def modification_time(self) -> datetime:
        """Indicates the time of the last modification made to this file.

        The time of modification as returned by this method corresponds to the
        time as tracked by the underlying filesystem. It is independent of any
        modification made to this `File` instance. This means that two
        subsequent calls made to this method can return two different values
        even if no other action has been otherwise imposed on this file
        instance, because a different program might have changed the underlying
        filesystem file in between the two method calls.

        The returned `datetime` is in UTC (offset +00:00). The resolution is
        intentionally left unspecified but on most platforms and filesystems
        at least a resolution of seconds can be expected.

        Returns:
            datetime: The last modification time.

        Raises:
            FileNotFoundException: If the file does not exist.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If the file modification time cannot
                be queried.
        """
        return File._FS.get_file_last_modification_time(
            self._path,
            self._follow_symlinks
        )

    def info(self) -> str:
        """Creates a string with descriptive information about this file.

        The returned string is formatted similar to the output of
        the `ls -lh` command on a GNU/Linux system. For example, an info string
        might look like the following:

        ```
          (1)   (2)    (3)   (4)    (5)           (6)            (7)    
           |     |      |     |      |             |              |     
          |v|    v   |  v  |  v  |   v   |         v         |    v    |
          '-rw-rw-r-- owner group 12.34MB 2022-05-25T14:15:16 afile.txt'
        ```

        (1): File type symbol as a single character (`FileType`)  
        (2): File permission (`FilePermission`)  
        (3): Owner name of the file owner  
        (4): Group name of the file group  
        (5): File size in a human-readable unit (`FileSize`)  
        (6): Last modification time as an ISO-8601 formatted timestamp (UTC)  
        (7): File name  

        Besides the first and the second element, all elements are separated
        by a single space character. If the file does not actually exist in
        the filesystem, then this method returns an empty string.
        The specified format may be considered by a caller as part
        of the API contract.

        Returns:
            str: A string representing essential information about this file,
                or an empty string if the file does not exist.

        Raises:
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileQueryException: If some file information cannot be queried.
        """
        try:
            file_type = File._FS.get_type(self._path, follow_symlinks=False)
            file_name = self.name
            if file_type == FileType.SYMBOLIC_LINK:
                link_target = File._FS.get_symbolic_link_target(self._path)
                file_name += f" -> {link_target}"

            return " ".join([
                file_type.symbol + str(self.permission()),
                self.owner_name(),
                self.group_name(),
                str(self.size().as_human_readable()),
                # Remove the '+00:00' UTC offset from formatted str,
                # as is implicit
                self.modification_time().replace(tzinfo=None).isoformat(
                    timespec="seconds"
                ),
                file_name,
            ])
        except FileNotFoundException:
            return ""

    def exists(self) -> bool:
        """Checks whether this file exists.

        This method follows symbolic links depending on the value of
        the `follow_symlinks` property. If symbolic links are followed, then
        this method returns `False` if this file is a symbolic link which
        points to a non-existent file (i.e. it is a broken symlink). Likewise,
        if symbolic links are not followed and this file is a symbolic link
        which points to a non-existent file, then this method still
        returns `True` because the link itself still exists.
        Symbolic links anywhere else in the path of this file are always
        followed. Callers may also explicitly follow symbolic links by using
        the file returned by the `resolve_symbolic_links()` method instead.

        Returns:
            bool: `True` if this file exists in the local filesystem.
                `False` if it does not exist.
        """
        return File._FS.check_exists(self._path, self._follow_symlinks)

    def list_files(self) -> Generator["File", None, None]:
        """Lists all files in this directory.

        This generator function only yields files which are immediate members
        of this directory. That is, files contained in any subdirectories are
        not yielded by the generator, but are rather just implicit in
        the item of the included subdirectory itself. This method does not
        guarantee any particular ordering of the yielded files.

        If all files should be considered recursively, including all files
        in subdirectories, then the `list_all_files()` method should be
        used instead.

        If this `File` instance does not represent a directory,
        a `DirectoryListingException` is raised.

        Yields:
            File: The next `File` object that is part of the content
                of this directory.

        Raises:
            FileNotFoundException: If this file does not exist.
            FilePermissionException: If the listing operation is denied.
            DirectoryListingException: If the directory listing cannot
                be created or if this file is not a directory.
        """
        for path in File._FS.list_files_of_directory(
            self._path, recursive=False
        ):

            yield File(path)

    def list_all_files(self) -> Generator["File", None, None]:
        """Lists all files in this directory including any
        subdirectories recursively.

        This generator function yields all files which are immediate members of
        this directory, subdirectories and all children thereof. That is, files
        contained in any subdirectories are yielded as separate items by
        the generator. This method does not guarantee any particular ordering
        of the yielded files.

        If only the direct children files should be considered, then
        the `list_files()` method should be used instead.

        If this `File` instance does not represent a directory,
        a `DirectoryListingException` is raised.

        Yields:
            File: The next `File` object that is part of the content
                of this directory or any subdirectory.

        Raises:
            FileNotFoundException: If this file does not exist.
            FilePermissionException: If the listing operation is denied.
            DirectoryListingException: If the directory listing cannot
                be created or if this file is not a directory.
        """
        for path in File._FS.list_files_of_directory(
            self._path, recursive=True
        ):

            yield File(path)

    def create(self):
        """Creates this file in the filesystem.

        The underlying filesystem file is created as a regular file.
        If the regular file already exists, then this method has no effect.
        If a file of any type other than a regular file already exists at the
        underlying filesystem path, then an exception is raised instead.

        Raises:
            FilePermissionException: If the file creation is denied.
            FileCreationException: If the file cannot be created or it already
                exists but is not a regular file.
        """
        File._FS.create_regular_file(self._path)

    def create_directory(self):
        """Creates this file in the filesystem as a directory.

        If the directory already exists, then this method has no effect.
        If a file of any type other than a directory already exists at the
        underlying filesystem path, then an exception is raised instead.

        Any parent directories must already exist. If an entire tree of
        directories should be created at once, use
        the `create_directory_tree()` method instead.

        Raises:
            FileNotFoundException: If the parent directory of this file does
                not exist.
            FilePermissionException: If the directory creation is denied.
            FileCreationException: If the directory cannot be created or a file
                at the same location already exists.
        """
        File._FS.create_directory(self._path)

    def create_directory_tree(self):
        """Creates this file in the filesystem as a directory, and any missing
        parent directories if needed.

        If the directory already exists, then this method has no effect.
        Please note that an error can potentially occur at any point when
        creating a directory tree, which might lead to the situation that an
        exception is raised after any number of parent directories were already
        created in the filesystem. This method does not attempt to clean up a
        halfway created directory tree.

        Raises:
            FilePermissionException: If the creation of any directory in
                the tree is denied.
            FileCreationException: If the directory or any of the parent
                directories cannot be created.
        """
        File._FS.create_directories(self._path)

    def create_symbolic_link(self, target: FileOrPath):
        """Creates this file as a symbolic link pointing to the specified file.

        The target of a symbolic link may either be specified as a relative or
        absolute path. If the path is relative, it is interpreted as being
        relative to the symlink itself. The target file may or may not exist.

        Args:
            target (File): The target file that this file should link to.

        Raises:
            FilePermissionException: If the symbolic link creation is denied.
            FileCreationException: If the symbolic link cannot be created or
                a file at the same location already exists.
        """
        File._FS.create_symbolic_link(self._path, self._ensure_path(target))

    def resolve_symbolic_links(self) -> "File":
        """Follows and resolves all symbolic links.

        Symbolic links are resolved anywhere within the path of this file.
        The resolved target path is returned as a new `File` instance.
        If the path of this file does not contain any symbolic links, then the
        returned `File` instance is equal to this file. If a symbolic link has
        to be resolved, then path normalization may be applied.
        If any resolved symbolic link is broken, then an exception is raised.

        The result of this method is independent from the value of
        the `follow_symlinks` property.

        Returns:
            File: The resolved target file of this symbolic link.

        Raises:
            SymbolicLinkResolutionException: If any symbolic link within the
                path of this file cannot be resolved or is a broken symlink.
        """
        return File(File._FS.resolve_symbolic_links(self._path))

    def move(self, destination: FileOrPath):
        """Moves this file to the specified destination.

        If a file of the same type already exists at the specified destination,
        then it is effectively replaced by this file.

        If the `follow_symlinks` property is `True` (the default) and this file
        is a symbolic link, then the target of the link is effectively moved
        and the original symbolic link is removed. If the `follow_symlinks`
        property is `False` and this file is a symbolic link, then the link is
        moved to the destination while keeping the same link target it
        originally pointed to.
        This method must not be called on an open file.

        Args:
            destination (File): The destination where to move this file to.

        Raises:
            InvalidFileStateException: If the file is open.
            FileNotFoundException: If the file does not exist.
            FilePermissionException: If the file move operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileRelocationException: If the file cannot be moved
                to the destination.
        """
        self._ensure_is_not_open(
            f"Cannot move file '{self._path}': File is open and must "
            "first be closed before it can be moved"
        )
        File._FS.move(
            self._path,
            self._ensure_path(destination),
            self._follow_symlinks
        )

    def copy(self, destination: FileOrPath):
        """Copies this file to the specified destination.

        Only regular files and directories can be copied. If a file of the same
        type already exists at the specified destination, then it is
        effectively replaced by this file.

        If the `follow_symlinks` property is `True` (the default), then if this
        file is a symbolic link, the file it refers to will be used as the
        source for the copy operation, otherwise the symbolic link will be
        copied instead which may or may not be supported by the underlying
        filesystem. To explicitly copy a symbolic link, it is recommended to
        use the `create_symbolic_link()` method.
        When copying a directory that contains symbolic links, all
        symbolic links are replaced at the target directory with the
        corresponding resolved regular file or directory that the link
        points to.
        This method must not be called on an open file.

        Args:
            destination (File): The destination where to copy this file to.

        Raises:
            InvalidFileStateException: If the file is open.
            FileNotFoundException: If the file does not exist.
            FilePermissionException: If the file copy operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileCopyException: If the file cannot be copied to the destination,
                including the case in which this file is a directory containing
                a broken symlink.
        """
        self._ensure_is_not_open(
            f"Cannot copy file '{self._path}': File is open and must "
            "first be closed before it can be copied"
        )
        File._FS.copy(
            self._path,
            self._ensure_path(destination),
            self._follow_symlinks
        )

    def remove(self):
        """Removes this file from the filesystem.

        This method can be used on files of all types, including non-empty
        directories. If a directory is removed, all content within that
        directory is also removed automatically.
        This method must not be called on an open file.

        If the `follow_symlinks` property is `True` (the default) and this file
        is a symbolic link, then the file the link refers to and the symbolic
        link itself are both removed. If the file is a symbolic link and
        the `follow_symlinks` property is `False`, then only the link itself
        is removed, but not the target file it points to.

        Raises:
            InvalidFileStateException: If the file is open.
            FileNotFoundException: If the file does not exist.
            FilePermissionException: If the file remove operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            FileRemovalException: If the file cannot be removed.
        """
        self._ensure_is_not_open(
            f"Cannot remove file '{self._path}': File is open and must "
            "first be closed before it can be removed"
        )
        File._FS.remove(self._path, self._follow_symlinks)

    def is_hidden(self) -> bool:
        """Indicates whether this file is hidden in the filesystem.

        A hidden file might not be shown by default in a file explorer
        application or when printing directory listings.

        Returns:
            bool: `True` if this file is hidden. `False` if this file
                is not hidden.

        Raises:
            FileNotFoundException: If the file does not exist.
            FileQueryException: If the file hidden-state cannot be queried.
        """
        return File._FS.check_is_hidden(self._path)

    def make_hidden(self) -> "File":
        """Makes this file hidden in the filesystem.

        This method potentially moves the underlying file in the filesystem
        if the hidden-attribute is determined by the concrete path within such
        a filesystem. To avoid complications, callers should ensure they
        continue to work with the `File` object returned by this method if
        subsequent operations might be applied. In any case, the returned file
        will have the same properties as this file but might have a different
        path. This method must not be called on an open or locked file.

        If this file is already hidden, then this method has no effect.

        Returns:
            File: A `File` which represents this file in a hidden state.

        Raises:
            InvalidFileStateException: If this file is open or locked.
            FileNotFoundException: If the file does not exist but the
                hidden-state is determined with the actual filesystem file.
            FileQueryException: If the file hidden-state cannot
                be queried.
            FileModificationException: If the hidden-state of the file
                cannot be changed.
        """
        if self._is_locked:
            raise InvalidFileStateException(
                str(self._path),
                f"Cannot hide file '{self._path}': "
                "File must not be locked when making hidden"
            )

        self._ensure_is_not_open(
            f"Cannot hide file '{self._path}': "
            "File must not be open when making hidden"
        )

        hidden_file = File(File._FS.set_hidden(self._path, hidden=True))
        self._copy_attributes_to(hidden_file)
        return hidden_file

    def make_visible(self) -> "File":
        """Makes this file visible, i.e. unhidden, in the filesystem.

        This method potentially moves the underlying file in the filesystem
        if the hidden-attribute is determined by the concrete path within such
        a filesystem. To avoid complications, callers should ensure they
        continue to work with the `File` object returned by this method if
        subsequent operations might be applied. In any case, the returned file
        will have the same properties as this file but might have a different
        path. This method must not be called on an open or locked file.

        If this file is already visible, then this method has no effect.

        Returns:
            File: A `File` which represents this file in a visible state.

        Raises:
            InvalidFileStateException: If this file is open or locked.
            FileNotFoundException: If the file does not exist but the
                hidden-state is determined with the actual filesystem file.
            FileQueryException: If the file hidden-state cannot
                be queried.
            FileModificationException: If the hidden-state of the file
                cannot be changed.
        """
        if self._is_locked:
            raise InvalidFileStateException(
                str(self._path),
                f"Cannot unhide file '{self._path}': "
                "File must not be locked when making visible"
            )

        self._ensure_is_not_open(
            f"Cannot unhide file '{self._path}': "
            "File must not be open when making visible"
        )

        visible_file = File(File._FS.set_hidden(self._path, hidden=False))
        self._copy_attributes_to(visible_file)
        return visible_file

    def get_suffix(self) -> str:
        """Returns the file name suffix of this file.

        The suffix of a file name, also known as a file extension, is the last
        part of the path of the file that is separated by a dot ('.')
        character. The returned string includes the dot separator of the
        suffix. For example, the file with path `/home/user/my_file1.txt` has a
        suffix of `.txt`.
        Composite suffixes are returned as one string. For example, the file
        `/home/user/my_archive.tar.gz` has a suffix of `.tar.gz`.

        Returns:
            str: The file name suffix of this `File`. Returns an empty string
                if this file does not have a suffix.
        """
        return "".join(self._path.suffixes)

    def with_suffix(self, suffix: str) -> "File":
        """Returns this file with the last suffix replaced by the
        specified suffix.

        If this file has no suffix, the specified suffix is appended.
        If the specified suffix does not start with a dot, a dot is
        automatically prepended. If the file has a composite suffix
        (e.g. `.tar.gz`), only the last suffix (`.gz`) is replaced.

        To append a suffix without replacing, use the `append_suffix()` method.
        This method does not do filesystem I/O.

        Args:
            suffix (str): The file name suffix to apply. A leading dot is
                assumed if not present.

        Returns:
            File: A `File` which has the same path as this file with the
                last suffix replaced by the specified suffix.
        """
        if not suffix.startswith("."):
            suffix = "." + suffix

        current_suffix = self._path.suffix
        if current_suffix == suffix:
            return self

        if current_suffix:
            new_name = self._path.name[:-len(current_suffix)] + suffix
        else:
            new_name = self._path.name + suffix

        return File(self._path.with_name(new_name))

    def append_suffix(self, suffix: str) -> "File":
        """Returns this file with the specified suffix appended.

        This method may or may not return this `File` instance if this
        file already has the specified suffix.
        This method does not do filesystem I/O.

        Args:
            suffix (str): The file name suffix to append.

        Returns:
            File: A `File` which has the same path as this file with the
                specified suffix appended.
        """
        if not self._path.name.endswith(suffix):
            return File(PurePath(str(self._path) + suffix))

        return self

    def without_suffix(self, suffix: Optional[str] = None) -> "File":
        """Returns this file without a suffix.

        If the specified suffix is `None` or an empty string, then any suffix
        is removed from the returned file. Otherwise, if a non-empty string
        suffix is specified, then only that suffix is potentially removed from
        the returned file.

        This method may or may not return this `File` instance if this
        file already does not have the specified non-empty suffix.

        This method does not do filesystem I/O.

        Args:
            suffix (str): The file name suffix to potentially remove.
                May be `None` or an empty string.

        Returns:
            File: A `File` which has the same path as this file but without
                a suffix.
        """
        if not suffix:
            combined_suffixes = "".join(self._path.suffixes)
            if combined_suffixes:
                suffix_length = len(combined_suffixes)
                return File(
                    self._path.with_name(self._path.name[:-suffix_length])
                )

        else:
            if not suffix.startswith("."):
                suffix = "." + suffix

            if self._path.name.endswith(suffix):
                suffix_length = len(suffix)
                return File(
                    self._path.with_name(self._path.name[:-suffix_length])
                )

        return self

    def read_all_bytes(self) -> bytes:
        """Reads the entire content of this file.

        This is a convenience method for opening this file, reading the
        entire content into memory and then closing this file.
        This file can already be open when calling this method but the
        underlying file mode must allow for reading.
        If this method has to open the file, it guarantees that it will be
        closed again before this method returns. Otherwise, if the file is
        already open, this method will not automatically close it.

        Returns:
            bytes: The content of this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            InvalidFileModeException: If the file is already open but the used
                file mode is invalid or unsupported.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
            FileReadException: If an I/O error occurs while reading data.
            CannotCloseFileException: If the file was opened by this method
                call but cannot be closed again.
        """
        was_opened = False
        if not self._is_open:
            self.open(FileMode.READ)
            was_opened = True
        elif not self._open_mode.can_read(): # type: ignore
            raise InvalidFileModeException(
                str(self._path),
                f"Cannot read all bytes from file '{self._path}': "
                f"File is already open in {self._open_mode} mode which does "
                "not allow reading"
            )

        try:
            data = File._FS.read_from_file_object(self._handle)
        finally:
            if was_opened:
                self.close()

        return data

    def read_all_text(self) -> str:
        """Reads the entire content of this file as text.

        This is a convenience method for opening this file, reading the
        entire text content into memory and then closing this file.
        The text data is decoded according to the `text_encoding` property
        of this object.
        This file can already be open when calling this method but the
        underlying file mode must allow for reading.
        If this method has to open the file, it is guaranteed that it will be
        closed again before this method returns. Otherwise, if the file is
        already open, this method will not automatically close it.

        Returns:
            str: The text content of this file.

        Raises:
            FileNotFoundException: If the file does not exist.
            InvalidFileModeException: If the file is already open but the used
                file mode is invalid or unsupported.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
            FileTextDecodeException: If a text decoding error occurs or the
                underlying set text encoding is invalid.
            FileReadException: If an I/O error occurs while reading data.
            CannotCloseFileException: If the file was opened by this method
                call but cannot be closed again.
        """
        return self._decode_text(self.read_all_bytes())

    def read_all_text_lines(self, include_empty: bool = True) -> list[str]:
        """Reads the entire content of this file and returns it
        as a list of text lines.

        This is a convenience method for opening this file, reading the
        entire text content into memory, separating lines into distinct
        items, and then closing this file.

        The lines in the returned list do not include a trailing
        new line character.

        The text data read from the underlying file is decoded according to
        the `text_encoding` property of this object.

        This file can already be open when calling this method but the
        underlying file mode must allow for reading. If this method has to
        open the file, it is guaranteed that it will be closed again before
        this method returns. Otherwise, if the file is already open, this
        method will not automatically close it.

        Args:
            include_empty (bool): Indicates whether to include empty lines in
                the returned list, or whether they should be excluded.

        Returns:
            list[str]: The text lines of this file, as a `list` of `str`.

        Raises:
            FileNotFoundException: If the file does not exist.
            InvalidFileModeException: If the file is already open but the used
                file mode is invalid or unsupported.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
            FileTextDecodeException: If a text decoding error occurs or the
                underlying set text encoding is invalid.
            FileReadException: If an I/O error occurs while reading data.
            CannotCloseFileException: If the file was opened by this method
                call but cannot be closed again.
        """
        lines = self.read_all_text().splitlines()
        if not include_empty:
            lines = list(filter(bool, lines))

        return lines

    def write_all(self, data) -> int:
        """Writes the specified data to this file.

        This is a convenience method for opening this file in write mode,
        writing the specified data, and then closing this file.
        This file can already be open when calling this method but the
        underlying file mode must allow for writing.
        If the file has to be opened by this method and it does not
        already exist, it will be created as a result of this operation.
        This method will automatically close the file again, unless it is
        already open when calling this method, in which case this method
        will flush the file buffer but not automatically close it.

        Args:
            data: The data to write to this file,
                as a `bytes`, `bytearray` or `str` object.

        Returns:
            int: The number of bytes written to this file.

        Raises:
            InvalidFileModeException: If the file mode is invalid
                or unsupported.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
            FileTextEncodeException: If a text encoding error occurs or the
                underlying set text encoding is invalid or unsupported.
            FileWriteException: If an I/O error occurs while writing data to
                the file.
            CannotCloseFileException: If the file was opened by this method
                call but cannot be closed again.
        """
        return self._write_all_in_mode(FileMode.WRITE, data)

    def append_all(self, data) -> int:
        """Appends the specified data to the end of this file.

        If the file does not aleady exist in the filesystem, it is
        first created. If it already exists and is non-empty, then the
        already existing content of the file is not overwritten, but the
        the specified data is appended after the existing content.
        This file can already be open when calling this method but the
        underlying file mode must be append-enabled, for any other mode
        calling this method will raise an exception.
        This method will automatically close the file again, unless it is
        already open when calling this method, in which case this method
        will flush the file buffer but not automatically close it.

        Args:
            data: The data to append to this file,
                as a `bytes`, `bytearray` or `str` object.

        Returns:
            int: The number of bytes appended to this file.

        Raises:
            InvalidFileModeException: If the file mode is invalid
                or unsupported.
            FilePermissionException: If the open operation is denied.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
            CannotOpenFileException: If the file cannot be opened due to
                an I/O error.
            FileTextEncodeException: If a text encoding error occurs or the
                underlying set text encoding is invalid or unsupported.
            FileWriteException: If an I/O error occurs while writing data to
                the file.
            CannotCloseFileException: If the file was opened by this method
                call but cannot be closed again.
        """
        return self._write_all_in_mode(FileMode.APPEND, data)

    def lock(self) -> "File":
        """Attempts to acquire an exclusive advisory lock on this file.

        The file lock is either successfully acquired or
        a `FileLockAcquisitionException` is raised to indicate that the file
        system file is already locked by another `File` instance, a different
        application process or a different program entirely. If the underlying
        file has already been locked by this `File` instance, then subsequently
        calling this method has no effect and no exception is raised.
        Therefore, an acquired lock is reentrant only with respect to the
        same `File` instance but not otherwise.
        A file must not be open when attempting to acquire a lock and it should
        first be closed before attempting to release the previously
        acquired lock.

        This file does not necessarily have to exist in order to acquire a lock
        on it. The parent directory of this file, however, must exist and must
        be writable to perform lock operations.

        This method does never block.

        The acquired lock is an advisory lock, i.e. exclusive access can only be
        guaranteed if all involved actors check for the lock state via this
        method before attempting to gain access to the underlying resource.
        Advisory locks are not enforced and rely on the cooperation of the
        involved processes. The acquired lock is guaranteed to be global with
        respect to the entire underlying filesystem.

        If the `follow_symlinks` property is `True`, then in case this file is
        a symbolic link, the lock is acquired on the file of the final link
        target. Otherwise, if the `follow_symlinks` property is `False`, the
        lock is always acquired for this file and in case it is a symbolic link,
        the lock is acquired on the symbolic link itself. It is advised that
        callers are cautious about this distinctiveness because when relying
        on a lock which is established based on a symbolic link, exclusive
        access to the actual file the link refers to cannot be guaranteed since
        another process might access that file directly or via a different
        symbolic link elsewhere in the filesystem.

        No deadlock detection or detection for lost locks is performed. It is
        the responsibility of the calling code to ensure a deadlock
        cannot occur. An acquired lock must be released again via a direct or
        indirect call to the `unlock()` method. A lock acquired by one
        particular `File` instance cannot be released by any other `File`
        instance with the same path. The instance which originally acquired the
        lock also has to take care of releasing it again when appropriate.
        If application code fails to call `unlock()` for a previously acquired
        lock, including but not limited due to a program crash, no attempt is
        made to detect abandoned locks and subsequent attempts to acquire that
        lock may result in a deadlock-like scenario.

        Returns:
            File: This `File` instance.

        Raises:
            FileLockAcquisitionException: If a lock for this file could not be
                acquired because it is already locked.
            InvalidFileStateException: If this file is open.
            FileNotFoundException: If the parent directory of this file does
                not exist.
            FilePermissionException: If the file lock cannot be placed in the
                filesystem due to insufficient permission.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
        """
        if not self._is_locked:
            self._ensure_is_not_open(
                f"Attempt to lock already open file '{self._path}': "
                "Files must first be locked and then opened"
            )

            File._FS.lock_file(self._path, self._follow_symlinks)
            self._is_locked = True

        return self

    def unlock(self) -> "File":
        """Releases the exclusive advisory lock held on this file.

        If this file has not been previously locked by the `lock()` method,
        then calling this method has no effect. A file should first be closed
        before attempting to release any previously acquired lock.

        If the `follow_symlinks` property is `True`, then in case this file is
        a symbolic link, it is attempted to release the lock on the file of
        the final link target. Otherwise the lock is always attempted to be
        released on this file directly, and in case it is a symbolic link, the
        lock is attempted to be released on the symbolic link itself.

        Returns:
            File: This `File` instance.

        Raises:
            FilePermissionException: If the file lock cannot be released in
                the filesystem due to insufficient permission.
            SymbolicLinkResolutionException: If a symbolic link in the path of
                this file cannot be resolved or is a broken symbolic link.
        """
        if self._is_locked:
            if self._is_open:
                warnings.warn(
                    f"Attempt to release lock on file '{self._path}' which is "
                    "still open. Files should first be closed and "
                    "then unlocked.",
                    UserWarning,
                    stacklevel=2
                )

            File._FS.unlock_file(self._path, self._follow_symlinks)
            self._is_locked = False

        return self

    def __eq__(self, value):
        """Indicates whether this file is equal to the specified file.

        Two `File` objects are considered to be equal if and only if they
        encapsulate the same filesystem path.

        Args:
            value (File): The file to compare this file to,
                as a `File` or `PathLike` object.

        Returns:
            bool: `True` if both files are equal, `False` otherwise.
        """
        if isinstance(value, File):
            return self._path == value._path

        if isinstance(value, (PathLike, str)):
            return self._path == PurePath(value)

        raise TypeError(
            "Cannot compare File instance "
            f"with object of type {type(value)}"
        )

    def __ne__(self, value):
        """Indicates whether this file is not equal to the specified file.

        Two `File` objects are considered to be not equal if and only if the
        filesystem path they each encapsulate is different.

        Args:
            value (File): The file to compare this file to,
                as a `File` or `PathLike` object.

        Returns:
            bool: `True` if both files are not equal, `False` otherwise.
        """
        return not self.__eq__(value)

    def __hash__(self):
        """Returns the hash value of this file.
        
        The general contract of `__eq__()` and `__hash__()` applies.
        The hash returned by this method is related to the path of the file,
        not the actual data content in the filesystem.

        Returns:
            int: The hash value of this `File` instance.
        """
        return hash(self._path)

    def __truediv__(self, rhs):
        """Combines this file's path with the path of the specified file.
        
        This operator is equivalent to `File(lhs.path / rhs.path)`
        """
        return File(self.path / self._ensure_path(rhs))

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_trace):
        try:
            self.close()
        except FileIOException as close_exception:
            if ex_type is None:
                raise close_exception
        finally:
            self._try_release_lock()

    def __str__(self):
        return str(self._path)

    def __repr__(self):
        return f"File('{self._path}')"

    def __del__(self):
        # Deprecated: Dependency on __del__() should be removed.
        try:
            self.close()
        except CannotCloseFileException:
            pass

    def __fspath__(self):
        return str(self._path)

    def _ensure_path(self, obj):
        if isinstance(obj, File):
            return obj.path
        if isinstance(obj, str):
            return PurePath(obj)
        if isinstance(obj, PurePath):
            return obj

        raise TypeError(
            "Invalid argument type. "
            f"Expected File, PurePath or str but found {type(obj)}"
        )

    def _ensure_is_open(self, message):
        if not self._is_open:
            raise InvalidFileStateException(str(self._path), message)

    def _ensure_is_not_open(self, message):
        if self._is_open:
            raise InvalidFileStateException(str(self._path), message)

    def _checked_open(self, mode):
        self._ensure_is_not_open(
            f"Cannot open file '{self._path}': Is already open"
        )

        self._handle = File._FS.open_file_object(self._path, mode)
        self._open_mode = mode
        self._is_open = True

    def _try_release_lock(self):
        try:
            self.unlock()
        except FileIOException:
            pass

    def _copy_attributes_to(self, target_file):
        target_file.follow_symlinks = self._follow_symlinks
        target_file.text_encoding = self._text_encoding
        target_file.line_separator = self._line_separator

    def _check_is_type(self, file_type, follow_symlinks):
        try:
            return File._FS.get_type(self._path, follow_symlinks) == file_type
        except FileIOException:
            return False

    def _write_all_in_mode(self, mode, data):
        was_opened = False
        try:
            if not self._is_open:
                self.open(mode)
                was_opened = True
            else:
                assert isinstance(self._open_mode, FileMode)
                if mode.can_write() and not self._open_mode.can_write():
                    raise InvalidFileModeException(
                        str(self._path),
                        f"Cannot write to file '{self._path}': "
                        f"File is already open in {self._open_mode} mode "
                        "which does not allow writing"
                    )

                if mode.can_append() and not self._open_mode.can_append():
                    raise InvalidFileModeException(
                        str(self._path),
                        f"Cannot append to file '{self._path}': "
                        f"File is already open in {self._open_mode} mode "
                        "which does not allow appending to it"
                    )

            if isinstance(data, str):
                data = self._encode_text(data)

            n_bytes_written = File._FS.write_to_file_object(self._handle, data)
            if not was_opened:
                File._FS.flush_file_object(self._handle)

            return n_bytes_written
        finally:
            if was_opened:
                self.close()

    def _read_text_chunk(self, n_bytes):
        read_attempts = 4  # Assume encoding has max 4 bytes per char
        data = None
        while read_attempts > 0:
            try:
                read_data = self.read(n_bytes)
                if data is None:
                    data = read_data
                else:
                    data += read_data

                return self._decode_text(data)
            except FileTextDecodeException as ex:
                if n_bytes > 0 and read_attempts > 1 and any(
                    msg in str(ex) for msg in (
                        "unexpected end of data",
                        "truncated data",
                    )
                ):
                    n_bytes = 1
                    read_attempts -= 1
                else:
                    raise ex

        # Should never reach here
        assert False, "Internal error: Unexpected code path"

    def _encode_text(self, text):
        try:
            if self._line_separator != _LF:
                text = text.replace(_LF, self._line_separator)

            return text.encode(self._text_encoding)
        except LookupError:
            raise FileTextEncodeException(
                str(self._path),
                "Failed to encode text while trying to write "
                f"to file '{self._path}': "
                f"Invalid encoding '{self._text_encoding}'"
            ) from None
        except UnicodeEncodeError as error:
            raise FileTextEncodeException(
                str(self._path),
                f"Failed to {self._text_encoding} encode text "
                f"while trying to write to file '{self._path}': {error}"
        ) from None

    def _decode_text(self, data):
        try:
            return re.sub(
                _REGEX_NL_TRANSLATION, _LF, data.decode(self._text_encoding)
            )
        except LookupError:
            raise FileTextDecodeException(
                str(self._path),
                f"Failed to decode text while reading file '{self._path}': "
                f"Invalid encoding '{self._text_encoding}'"
            ) from None
        except UnicodeDecodeError as error:
            raise FileTextDecodeException(
                str(self._path),
                f"Failed to decode {self._text_encoding} text "
                f"while reading file '{self._path}': {error}"
            ) from None

    @staticmethod
    def get_default_text_encoding() -> str:
        """Gets the text encoding used by default for all new `File` instances.

        Returns:
            str: The default file text encoding, as an identifying name
                of the encoding, e.g. 'UTF-8'.
        """
        return File._DEFAULT_TEXT_ENCODING

    @staticmethod
    def set_default_text_encoding(encoding: str):
        """Sets the text encoding used by default for all new `File` instances.

        Args:
            encoding (str): The identifying name of the text encoding to be
                used by default, e.g. 'UTF-8'.
        """
        TypeCheck.require_arg(encoding, str)
        File._DEFAULT_TEXT_ENCODING = encoding

    @staticmethod
    def get_default_line_separator() -> str:
        """Gets the string used as line separators by default when
        writing text files.

        Returns:
            str: The default line separator.
        """
        return File._DEFAULT_LINE_SEPARATOR

    @staticmethod
    def set_default_line_separator(separator: str):
        """Sets the default line separator to be used when writing text files.

        Args:
            separator (str): The character string to be used as a
                line separator by default for all text files.
        """
        TypeCheck.require_arg(separator, str)
        File._DEFAULT_LINE_SEPARATOR = separator

    @staticmethod
    def get_file_system() -> FileSystem:
        """Obtains the `FileSystem` instance used by all file objects
        to interoperate with the underlying filesystem.

        Returns:
            FileSystem: The `FileSystem` instance used by `File` objects.
        """
        if File._FS is None:
            File._init_internals()

        return File._FS

    @staticmethod
    def _finalize(instance):
        """Finalizer for `File` objects."""
        try:
            instance.close()
        except CannotCloseFileException:
            pass

    @staticmethod
    def _init_internals():
        with File._INIT_LOCK:
            if File._FS is not None:
                return

            File._FS = FileSystem.instance()
            File._DEFAULT_LINE_SEPARATOR = (
                SystemEnvironment.instance().get_line_separator()
        )


class TemporaryFile(File):
    """A temporary file object in a filesystem.

    A `TemporaryFile` is a `File` with special behaviour and properties.
    Semantically, a temporary file usually is only used for a short period of
    time and then manually deleted by its owner. This class extends the
    functionality of `File` to provide a mechanism to ensure the lifetime of
    the `File` object in code is coupled with the existence of the
    corresponding file within the underlying filesystem. That is, if not
    manually removed earlier, when a `TemporaryFile` instance gets deleted,
    then the actual filesystem file will be automatically removed. However,
    this is an opt-in feature and must be explicitly enabled during
    initialization or by setting the `auto_remove` property.
    Please note that due to implementation details of the Python runtime and
    garbage collector, there is no strict guarantee that a `TemporaryFile`
    object that is out of scope and no longer reachable will be destroyed and
    thus the temporary file in the filesystem will get removed. For example,
    this is the case when the program is interrupted by a shutdown. There is no
    strict guarantee that the temporary filesystem file is cleaned up before
    the runtime exits. If you need to make sure that a the temporary file is
    deleted, you can call the `remove()` method manually.

    To create temporary files in temporary filesystem locations, use the
    `TemporaryFile.create_temporary_file()` and
    `TemporaryFile.create_temporary_directory()` methods.

    You can use a context manager to ensure a temporary file is automatically
    deleted after the context is left.

    Attributes:
        auto_remove (bool): Indicates whether the filesystem file will be
            automatically removed once the `TemporaryFile` instance
            is deleted.
    """

    def __init__(self, path: FileOrPath, auto_remove: bool):
        """Initializes a new `TemporaryFile`.

        Args:
            path (PurePath): The path of the file to initialize, either
                absolute or relative, as a `PurePath`, `File` or `str`.
            auto_remove (bool): A `bool` indicating whether to automatically
                remove the temporary file as soon as it becomes unused.
        """
        super().__init__(path)
        self._auto_remove = auto_remove
        self._is_destroyed = False
        weakref.finalize(self, TemporaryFile._finalize_temp, self)

    @property
    def auto_remove(self) -> bool:
        """Indicates whether the filesystem file will be automatically
        removed when this `TemporaryFile` object is destroyed, as a `bool`.
        Can be set.
        """
        return self._auto_remove

    @auto_remove.setter
    def auto_remove(self, value: bool):
        TypeCheck.require_prop(value, bool, "TemporaryFile.auto_remove")
        self._auto_remove = value

    def __enter__(self):
        super().__enter__()  # Discard return value
        self.auto_remove = True
        return self

    def __exit__(self, ex_type, ex_value, ex_trace):
        try:
            super().__exit__(ex_type, ex_value, ex_trace)
        finally:
            try:
                self._destroy()
            except FileIOException as destroy_exception:
                if ex_type is None:
                    raise destroy_exception

    def __del__(self):
        super().__del__()
        # Deprecated: Dependency on __del__() should be removed.
        try:
            self._destroy()
        except FileIOException:
            pass

    def _try_close(self):
        try:
            self.close()
        except FileIOException:
            self._is_open = False

    def _destroy(self):
        if not self._is_destroyed:
            self._try_close()
            if self._auto_remove:
                try:
                    self.remove()
                except FileNotFoundException:
                    # Assume someone else has already removed the temp file
                    pass

            self._is_destroyed = True

    @staticmethod
    def _finalize_temp(instance):
        """Finalizer for `TemporaryFile` objects."""
        try:
            # pylint: disable=W0212
            instance._destroy()
        except FileIOException:
            pass

    @staticmethod
    def create_temporary_file(
        in_directory: Optional[FileOrPath] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None
    ) -> "TemporaryFile":
        """Creates a file in a temporary filesystem location.

        Args:
            in_directory (File): The directory where the temporary file should
                be created. This could also be a non-temporary directory.
                If specified, the directory must already exist. Otherwise, if
                left `None`, it is automatically created in a temporary
                location. May also be specified as a `PurePath` or `str`.
            prefix (str): An optional prefix for the created file name.
            suffix (str): An optional suffix for the created file name.

        Returns:
            TemporaryFile: A `TemporaryFile` object denoting the created
                temporary file.

        Raises:
            FileNotFoundException: If `in_directory` was specified but that
                directory does not exist.
            FilePermissionException: If the temporary file creation is denied.
            TemporaryFileCreationException: If the temporary file could
                not be created.
        """
        if in_directory is not None:
            if isinstance(in_directory, File):
                in_directory = in_directory.path
            elif isinstance(in_directory, str):
                in_directory = PurePath(in_directory)
            elif not isinstance(in_directory, PurePath):
                raise TypeError(
                    "Invalid type for argument 'in_directory'. Expected "
                    f"File, PurePath or str but found {type(in_directory)}"
                )

        return TemporaryFile(
            File.get_file_system().create_temp_file(
                in_directory, prefix, suffix
            ),
            auto_remove=False
        )

    @staticmethod
    def create_temporary_directory(
        prefix: Optional[str] = None,
        suffix: Optional[str] = None
    ) -> "TemporaryFile":
        """Creates a temporary directory.

        Args:
            prefix (str): An optional prefix for the created directory name.
            suffix (str): An optional suffix for the created directory name.

        Returns:
            TemporaryFile: A `TemporaryFile` object denoting the created
                temporary directory.

        Raises:
            FilePermissionException: If the temporary directory
                creation is denied.
            TemporaryFileCreationException: If the temporary directory could
                not be created.
        """
        return TemporaryFile(
            File.get_file_system().create_temp_dir(prefix, suffix),
            auto_remove=False
        )
