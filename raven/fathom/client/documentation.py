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
"""Documentation resources and files.

This module provides an API to structure documentation files of a built project
into a single object. The primary touch point for a client is
the `DocumentationResource` class. It represents a collection of files that
clients may wish to deploy, irrespective of how those files are laid out in
the filesystem. Each individual documentation file is represented
as a `DocsFile` instance. Since most often build tools write documentation
files under a single directory within the build tree of a project,
the `DocsDir` class can be used in such a case for greater convenience.
"""

from os import PathLike
from pathlib import Path
from typing import Union, Optional, TypeAlias

from raven.fathom.base import File
from raven.fathom.base import TypeCheck
from raven.fathom.client.filter import FileFilter


PathType: TypeAlias = Union[str, PathLike]


class DocsFile(PathLike):
    """An individual documentation resource file.

    For the most part, a `DocsFile` object is associated with a file in the
    filesystem by its set path. The content of that file on the host of the
    client is the data that will be incorporated into the deployed
    documentation resource. A `DocsFile` object can have a different name than
    the real file it is associated with. This allows a client to create a
    deployable documentation resource with a file tree that looks different
    than what is actually stored in the filesystem.

    Attributes:
        name (str): The name of the documentation resource file. Read-only.
        path (Path): The path to the file in the filesystem that the `DocsFile`
            is associated with. May be `None` for pathless instances created
            via `DocsFile.with_name()`.
    """

    def __init__(
        self,
        path: Optional[PathType] = None,
        name: Optional[str] = None
    ):
        """Initializes a new `DocsFile` instance.

        At least either path or name must be specified.

        Args:
            path (PathLike): The path to the file in the filesystem.
                May be `None` if `name` is provided. May be specified
                as a `str`.
            name (str): The name of the documentation resource file.

        Raises:
            ValueError: If neither path nor name is specified.
        """
        if path is None:
            if not name:
                raise ValueError("Either 'path' or 'name' must be provided")

            self._path = None
            self._name = name
        else:
            self._path = Path(path)
            self._name = name or self._path.name

    @staticmethod
    def with_name(name: str) -> "DocsFile":
        """Creates a `DocsFile` instance with the specified name.

        This method is intended to be used in places where only the
        name of a documentation file is known, but otherwise it is
        not backed by a real file in the filesystem and thus it does
        not have a real path.

        Args:
            name (str): The name of the created documentation file.

        Returns:
            DocsFile: A new documentation file with the given name
                and an unset path.
        """
        return DocsFile(path=None, name=name)

    @property
    def name(self) -> str:
        """The name of the file, as a `str`."""
        return self._name

    @property
    def path(self) -> Optional[Path]:
        """The path of the file, as a `Path` object.

        May be `None` for pathless instances created
        via `DocsFile.with_name()`.
        """
        if self._path is None:
            return None

        return Path(self._path)

    def __fspath__(self):
        if self._path is None:
            raise TypeError(
                f"DocsFile '{self._name}' has no associated filesystem path"
            )

        return str(self._path)

    def __eq__(self, value):
        if not isinstance(value, DocsFile):
            raise TypeError(
                f"Cannot compare instance of {type(self)} "
                f"to instance of {type(value)}"
            )

        return self.name == value.name

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"{DocsFile.__qualname__}[{self.name}]"


class DocsDir:
    """A documentation resource directory.

    Represents a collection of documentation resource files which are all
    located under a given filesystem directory path. Often, the built
    documentation files of a project are all located under a specific directory
    within the build tree. In that case it is more convenient to specify the
    files of the documentation resource a client may wants to deploy as that
    directory, instead of listing all documentation files separately.
    A `DocsDir` instance will collect and handle all individual files
    as `DocsFile` instances automatically. Besides the greater convenience,
    a `DocsDir` instance can be filtered by a `FileFilter` in order to only
    include or exclude specific files.

    Clients should use `DocsDir` instances and apply all operations **before**
    they are added to a `DocumentationResource` object, because latter may
    create copies of the collected `DocsFile` instances or otherwise perform
    operations which result in the usage of different object references.

    Attributes:
        path (Path): The path to the directory in the filesystem that
            the `DocsDir` is associated with. Is never `None`.
    """

    def __init__(self, path: PathType):
        """Initializes a new `DocsDir` instance.

        Args:
            path (PathLike): The path to the directory in the filesystem that
                the `DocsDir` is associated with.

        Raises:
            ValueError: If the specified path does not denote a directory.
        """
        self._directory = Path(path)
        directory_file = File(self._directory)
        if not directory_file.is_directory():
            raise ValueError(
                f"Invalid argument 'path'. "
                f"Path must denote an existing directory: '{directory_file}'"
            )

        self._files: set[DocsFile] = set()
        for file in directory_file.list_all_files():
            self._files.add(
                DocsFile(
                    path=file.path,
                    name=file.path.relative_to(directory_file.path).as_posix()
                )
            )

    @property
    def path(self) -> Path:
        """The path of the filesystem directory, as a `Path`."""
        return Path(self._directory)

    def anchor_files(self, anchor: PathType):
        """Changes the file path anchor for all individual files.

        Args:
            anchor (PathLike): The path anchor to apply to all documentation
                files of this directory.
        """
        if not isinstance(anchor, Path):
            anchor = Path(anchor)

        anchored_files = set()
        for file in self._files:
            anchored_files.add(
                DocsFile(
                    path=file.path,
                    name=(anchor / Path(file.name)).as_posix()
                )
            )

        self._files = anchored_files

    def apply_filter(self, file_filter: FileFilter):
        """Applies the specified file filter to the files of this
        documentation directory.

        Args:
            file_filter (FileFilter): The `FileFilter` to apply to all files.
        """
        filtered_files = file_filter.apply(self._files)
        if isinstance(filtered_files, set):
            self._files = filtered_files
        else:
            fileset = set()
            for file in filtered_files:
                fileset.add(file)

            self._files = fileset

    def _get_fileset(self) -> set[DocsFile]:
        """Returns the set of `DocsFile` objects.

        Returns:
            set: The `set` of collected `DocsFile` objects.
        """
        return self._files

    def __repr__(self):
        return f"{DocsDir.__qualname__}[{self.path}]"

    def __iter__(self):
        """Returns an iterator over all documentation files."""
        return iter(self._files.copy())


class DocumentationResource:
    """A deployable documentation resource.

    A `DocumentationResource` object represents a set of individual
    documentation resources, usually individual files and directories in
    the filesystem, to be deployed by a Fathom client as a software
    project's built documentation.

    Attributes:
        ignore_name_collisions (bool): Whether to ignore collisions on the name
            of doc files. If `True`, then adding a file with the same name as
            an existing file will not raise an exception, but the new file will
            replace the existing file in the resource. If `False`, then adding
            a file with the same name as an existing file will raise a
            `ValueError`. Defaults to `False`. Can be set.
    """

    def __init__(self):
        """Initializes a new `DocumentationResource` instance.

        The initialized instance will be empty, that is, it does not contain
        any documentation files.
        """
        self._files: set[DocsFile] = set()
        self._ignore_name_collisions = False

    @property
    def ignore_name_collisions(self) -> bool:
        """Whether to ignore collisions on the name of doc files."""
        return self._ignore_name_collisions

    @ignore_name_collisions.setter
    def ignore_name_collisions(self, value: bool):
        TypeCheck.require_prop(value, bool, "ignore_name_collisions")
        self._ignore_name_collisions = value

    def size(self) -> int:
        """Indicates the number of documentation files that are part of
        this documentation resource.

        Returns:
            int: The number of documentation files in this resource.
        """
        return len(self._files)

    def is_empty(self) -> bool:
        """Indicates whether this documentation resource contains
        no documentation files.

        Returns:
            bool: `True` if this documentation resource is empty,
                `False` if it contains at least one file.
        """
        return self.size() == 0

    def get_file_by_name(
        self,
        name: Union[str, DocsFile]
    ) -> Optional[DocsFile]:
        """Gets the specified file by name.

        Args:
            name (str): The name of the file to get, or a `DocsFile` instance
                whose name will be used.

        Returns:
            DocsFile: The `DocsFile` instance with the specified name, or
                `None` if no such file exists in this resource.
        """
        if isinstance(name, DocsFile):
            name = name.name

        if not isinstance(name, str):
            raise TypeError(
                "Invalid argument 'name': "
                f"Expected str or DocsFile but found {type(name)}"
            )

        for file in self._files:
            if file.name == name:
                return file

        return None

    def add_directory(self, directory: DocsDir):
        """Adds a resource directory to this documentation resource.

        Args:
            directory (DocsDir): The directory to add.
        """
        TypeCheck.require_arg(directory, DocsDir)
        # pylint: disable=W0212
        fileset = directory._get_fileset()
        if not self.ignore_name_collisions:
            collisions = self._files & fileset
            if len(collisions) != 0:
                raise ValueError(
                    "File name collision detected for files: "
                    f"{collisions}"
                )

        self._files |= fileset

    def add_file(self, file: DocsFile):
        """Adds a single resource file to this documentation resource.

        Args:
            file (DocsFile): The file to add.
        
        Raises:
            ValueError: If the specified `file` has the same name as an
                existing file in this resource and `ignore_name_collisions`
                is set to `False`.
        """
        TypeCheck.require_arg(file, DocsFile)
        if not self.ignore_name_collisions:
            if file in self._files:
                raise ValueError(
                    f"File name collision for file: '{file}'"
                )

        self._files.add(file)

    def remove_file(self, file: DocsFile):
        """Removes a single resource file from this documentation resource.

        Args:
            file (DocsFile): The file to remove.
        """
        TypeCheck.require_arg(file, DocsFile)
        self._files.remove(file)

    def contains(self, file: DocsFile) -> bool:
        """Indicates whether the given file exists in this
        documentation resource.

        Args:
            file (DocsFile): The file to check.

        Returns:
            bool: `True` if the specified file is part of this
                documentation resource, `False` otherwise.
        """
        TypeCheck.require_arg(file, DocsFile)
        return file in self._files

    def apply_filter(self, file_filter: FileFilter):
        """Applies the specified file filter to the files of this
        documentation resource.

        Args:
            file_filter (FileFilter): The `FileFilter` to apply to the
                files of this resource.
        """
        filtered_files = file_filter.apply(self._files)
        if isinstance(filtered_files, set):
            self._files = filtered_files
        else:
            fileset = set()
            for file in filtered_files:
                fileset.add(file)

            self._files = fileset

    def __getitem__(self, key: Union[str, DocsFile]):
        """Same as `lhs.get_file_by_name(rhs)`."""
        return self.get_file_by_name(key)

    def __iadd__(self, docs: Union[DocsFile, DocsDir]):
        """Same as `lhs.add_*(rhs)`, depending on the argument type.

        If `docs` is an instance of `DocsDir`, then it is the same
        as `lhs.add_directory(rhs)`.
        Otherwise will be treated the same as `lhs.add_file(rhs)`.
        """
        if isinstance(docs, DocsDir):
            self.add_directory(docs)
        else:
            self.add_file(docs)

        return self

    def __isub__(self, docs: DocsFile):
        """Same as `lhs.remove_file(rhs)`."""
        self.remove_file(docs)
        return self

    def __contains__(self, docs: DocsFile):
        """Same as `rhs.contains(lhs)`."""
        return self.contains(docs)

    def __iter__(self):
        """Returns an iterator over all documentation files."""
        return iter(self._files.copy())
