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
"""Documentation resource filters.

Provides the `FileFilter` class that lets you filter a set of documentation
source files based on various criteria, such as file type, file name,
file extension, etc. The filter can operate in either inclusive
or exclusive mode, allowing you to specify whether to include or exclude files
that match the specified criteria.
"""

from enum import Enum
from dataclasses import dataclass, field
from collections.abc import Collection
from os import PathLike
from typing import TypeVar, Optional, Final

from raven.fathom.base import File, FileSize, FileSizeUnit
from raven.fathom.base import TypeCheck


def _filter_is_regular_file(file: File):
    return file.is_regular_file()

def _filter_is_directory(file: File):
    return file.is_directory()

def _filter_is_symlink(file: File):
    return file.is_symbolic_link()

# pylint: disable=W0613
def _filter_is_any_file_type(file: File):
    return True

def _filter_is_nonexistent(file: File):
    return not file.exists()


# The constant value for marking a file size within
# a `FileSizeRange` as unbounded.
UNBOUND_FILE_SIZE: Final = None

# File-like
F = TypeVar("F", bound=PathLike)


@dataclass
class FileSizeRange:
    """Dataclass encapsulating a range for file sizes in file filters.

    A range is composed of two bounds, lower and upper. The lower bound marks
    the minimum file size in the corresponding unit of digital storage for
    which a match is produced by a file filter. The upper bound marks the
    maximum file size for a match. Both bounds are inclusive, i.e. a file
    in the filesystem of exactly the size of such a bound will still produce
    a match by a file filter.

    Attributes:
        lower (FileSize): The lower bound (inclusive) of the range.
            Defaults to `UNBOUND_FILE_SIZE`.
        upper (FileSize): The upper bound (inclusive) of the range.
            Defaults to `UNBOUND_FILE_SIZE`.
    """

    lower: Optional[FileSize] = field(default=UNBOUND_FILE_SIZE)

    upper: Optional[FileSize] = field(default=UNBOUND_FILE_SIZE)

    def is_unbound(self):
        """Indicates whether this file size range is completely unbound.

        Returns:
            bool: `True` if both `lower` and `upper` is unbound,
                `False` otherwise.
        """
        return (
            self.lower is UNBOUND_FILE_SIZE
            and self.upper is UNBOUND_FILE_SIZE
        )

    def __post_init__(self):
        if self.lower is not UNBOUND_FILE_SIZE:
            if not isinstance(self.lower, FileSize):
                raise TypeError(
                    "Invalid argument 'lower' for FileSizeRange: "
                    f"Expected FileSize but found {type(self.lower)}"
                )

        if self.upper is not UNBOUND_FILE_SIZE:
            if not isinstance(self.upper, FileSize):
                raise TypeError(
                    "Invalid argument 'upper' for FileSizeRange: "
                    f"Expected FileSize but found {type(self.upper)}"
                )


class FileFilter:
    """A filter to be applied on a set of documentation source files.

    A file filter is used to trim a set of source files based on various
    criteria, such as file type, file name, file extension, etc. A filter can
    operate in either inclusive or exclusive mode, allowing you to specify
    whether the filter removes or only includes files that match the
    specified criteria.

    Attributes:
        file_type (FileFilter.FileType): The type of file this filter
            applies to. Read-only.
        mode (FileFilter.Mode): The mode of this filter, either inclusive
            or exclusive. Read-only.
        file_names (set): The set of file names this filter applies to.
            Read-only.
        file_extensions (set): The set of file extensions this filter
            applies to. Read-only.
        path_prefixes (set): The set of path prefixes this filter applies to.
            Read-only.
        size_range (FileSizeRange): The range of file sizes this filter
            applies to. Read-only.
        ignore_nonexistent (bool): Indicates whether this filter ignores files
            which do not exist, meaning that if a file does not actually exist
            in the filesystem and this property is `True`, then the file
            matches the filter (assuming other criteria are met). Read-only.
    """

    class FileType(Enum):
        """The file type to be considered by a `FileFilter` object."""

        REGULAR_FILE = "f"

        DIRECTORY = "d"

        SYMLINK = "s"

        ANY = "any"

        NONEXISTENT = "nonexistent"

    class Mode(Enum):
        """The filter mode a `FileFilter` object operates on."""

        INCLUSIVE = "inclusive"

        EXCLUSIVE = "exclusive"

    def __init__(
        self,
        apply_on: FileType = FileType.ANY,
        mode: Mode = Mode.EXCLUSIVE,
        file_names: Optional[set[str]] = None,
        file_extensions: Optional[set[str]] = None,
        path_prefixes: Optional[set[str]] = None,
        size_range: Optional[FileSizeRange] = None,
        ignore_nonexistent: bool = False,
    ):
        """Initializes a new `FileFilter` instance.

        Args:
            apply_on (FileFilter.FileType): The type of file which should
                be filtered. Defaults to `FileFilter.FileType.ANY`.
            mode (FileFilter.Mode): The mode of operation for the filter.
                Defaults to `FileFilter.Mode.EXCLUSIVE`.
            file_names (set): A `set` of `str` file names which should
                be filtered. May be `None` (Default) to not filter by
                any file names.
            file_extensions (set): A `set` of `str` file extensions which
                should be filtered. May be `None` (Default) to not filter by
                any file extensions.
            path_prefixes (set): A `set` of `str` file path prefixes which
                should be filtered. A prefix is simply the beginning of the
                file path. May be `None` (Default) to not filter by any file
                path prefixes.
            size_range (FileSizeRange): A `FileSizeRange` denoting an open or
                closed range for file sizes for which files and directories
                should be filtered. Please note that for directories the entire
                content, including subdirectories, is considered when computing
                the size. May be `None` (Default) to not filter
                by any file sizes.
            ignore_nonexistent (bool): A flag indicating whether to ignore
                files which do not actually exist in the filesystem.
                This applies to all modes of operation. Defaults to `False`.
        """
        self._file_type = apply_on
        self._mode = mode
        self._file_names = file_names
        if file_extensions is not None:
            file_extensions = set(
                map(
                    lambda ext: ext if ext.startswith(".") else "." + ext,
                    file_extensions
                )
            )

        self._file_extensions = file_extensions
        self._prefixes = path_prefixes
        if size_range is not None:
            TypeCheck.require_arg(size_range, FileSizeRange)

        self._size_range = size_range
        self._ignore_nonexistent = ignore_nonexistent

    @property
    def file_type(self) -> FileType:
        """The type of file this filter applies to,
        as a `FileFilter.FileType`.
        """
        return self._file_type

    @property
    def mode(self) -> Mode:
        """The mode of this filter, as a `FileFilter.Mode`."""
        return self._mode

    @property
    def file_names(self) -> set[str]:
        """The set of file names this filter applies to,
        as a `set` of `str`."""
        return self._file_names or set()

    @property
    def file_extensions(self) -> set[str]:
        """The set of file extensions this filter applies to,
        as a `set` of `str`.
        """
        return self._file_extensions or set()

    @property
    def path_prefixes(self) -> set[str]:
        """The set of path prefixes this filter applies to,
        as a `set` of `str`.
        """
        return self._prefixes or set()

    @property
    def size_range(self) -> FileSizeRange:
        """The file size range this filter applies to,
        as a `FileSizeRange` object.
        """
        return self._size_range or FileSizeRange()

    @property
    def ignore_nonexistent(self) -> bool:
        """Indicates whether this filter ignores files which do not exist.

        If set to `True`, files which do not exist in the filesystem are
        ignored by this filter. If set to `False`, such files are not
        ignored and will be filtered out if they do not match the other
        criteria of this filter.
        """
        return self._ignore_nonexistent

    def apply(self, files: Collection[F]) -> Collection[F]:
        """Applies this file filter on the specified set of files.

        Args:
            files (Collection): A `Collection` of `PathLike` objects
                to filter. Is not mutated by this filter.

        Returns:
            Collection: A new `Collection` of `PathLike` objects
                which match the criteria of this filter.
        """
        TypeCheck.require_arg(files, Collection)
        filtered_files = set()
        incl = self._mode == FileFilter.Mode.INCLUSIVE
        func_is_applicable_type = _FILE_TYPE_CHECK_MAP[self._file_type]
        for file_item in files:
            file = self._get_file(file_item)
            exists = file.exists()
            if self._ignore_nonexistent and not exists:
                filtered_files.add(file_item)
                continue

            if exists and not func_is_applicable_type(file):
                filtered_files.add(file_item)
                continue

            if self._file_names is not None:
                is_match = self._match_file_names(file)
                if is_match ^ incl:
                    continue

            if self._file_extensions is not None:
                is_match = self._match_file_extensions(file)
                if is_match ^ incl:
                    continue

            if self._size_range is not None:
                is_match = (
                    self._match_file_size_range(file)
                    if exists
                    else self._match_nonexistent_file_size_range()
                )
                if is_match ^ incl:
                    continue

            if self._prefixes is not None:
                is_match = self._match_file_prefixes(file)
                if is_match ^ incl:
                    continue

            filtered_files.add(file_item)

        return filtered_files

    def _get_file(self, file_item):
        return File(file_item)

    def _normalize_size_range(self):
        assert self._size_range is not None
        lower_bound = upper_bound = UNBOUND_FILE_SIZE
        if self._size_range.lower is not UNBOUND_FILE_SIZE:
            lower_bound = self._size_range.lower.with_unit( # type: ignore
                FileSizeUnit.BYTE
            )

        if self._size_range.upper is not UNBOUND_FILE_SIZE:
            upper_bound = self._size_range.upper.with_unit( # type: ignore
                FileSizeUnit.BYTE
            )

        return FileSizeRange(
            lower=lower_bound,
            upper=upper_bound
        )

    def _match_file_names(self, file):
        return file.name in self._file_names

    def _match_file_extensions(self, file):
        return file.get_suffix() in self._file_extensions

    def _match_file_size_range(self, file):
        size_range = self._normalize_size_range()
        if size_range.is_unbound():
            return True

        file_size = file.size()
        if size_range.lower is UNBOUND_FILE_SIZE:
            assert size_range.upper is not UNBOUND_FILE_SIZE
            return file_size.value <= size_range.upper.value # type: ignore

        if size_range.upper is UNBOUND_FILE_SIZE:
            assert size_range.lower is not UNBOUND_FILE_SIZE
            return size_range.lower.value <= file_size.value # type: ignore

        lower_bound = size_range.lower.value # type: ignore
        upper_bound = size_range.upper.value # type: ignore
        return lower_bound <= file_size.value <= upper_bound

    def _match_nonexistent_file_size_range(self):
        size_range = self._normalize_size_range()
        return size_range.lower in (0, UNBOUND_FILE_SIZE)

    def _match_file_prefixes(self, file):
        assert self._prefixes is not None
        for prefix in self._prefixes:
            path_begin = str(file)[:len(prefix)]
            if path_begin == prefix:
                return True

        return False


_FILE_TYPE_CHECK_MAP = {
    FileFilter.FileType.REGULAR_FILE: _filter_is_regular_file,
    FileFilter.FileType.DIRECTORY: _filter_is_directory,
    FileFilter.FileType.SYMLINK: _filter_is_symlink,
    FileFilter.FileType.ANY: _filter_is_any_file_type,
    FileFilter.FileType.NONEXISTENT: _filter_is_nonexistent
}
