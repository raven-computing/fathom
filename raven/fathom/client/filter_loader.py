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
"""Provides a function to load resource filters from configurations."""

from ast import literal_eval
from collections.abc import Sequence
from typing import Optional

from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.base import MalformedConfigurationValueException
from raven.fathom.client.config import ProjectConfiguration
from raven.fathom.client.config import FileFilterConfigurationSection
from raven.fathom.client.filter import FileFilter
from raven.fathom.client.filter import FileSizeRange


def _map_file_type(file_type: Optional[str]) -> FileFilter.FileType:
    if file_type is None or file_type == "any":
        return FileFilter.FileType.ANY

    if file_type == "regular_file":
        return FileFilter.FileType.REGULAR_FILE
    if file_type == "directory":
        return FileFilter.FileType.DIRECTORY
    if file_type == "symlink":
        return FileFilter.FileType.SYMLINK
    if file_type == "nonexistent":
        return FileFilter.FileType.NONEXISTENT

    raise MalformedConfigurationValueException(
        f"Invalid file type '{file_type}' specified in configuration"
    )


def _load_file_filter_with_mode(
    config: ConfigurationSection,
    file_mode: FileFilter.Mode
) -> Optional[FileFilter]:

    if config.is_empty():
        return None

    file_type = _map_file_type(
        config.value_of(FileFilterConfigurationSection.FILE_TYPE)
    )

    file_names = config.raw_value_of(FileFilterConfigurationSection.FILE_NAMES)
    if file_names is not None:
        file_names = set(literal_eval(file_names))

    file_extensions = config.raw_value_of(
        FileFilterConfigurationSection.FILE_EXTENSIONS
    )
    if file_extensions is not None:
        file_extensions = set(literal_eval(file_extensions))

    file_prefixes = config.raw_value_of(
        FileFilterConfigurationSection.FILE_PREFIXES
    )
    if file_prefixes is not None:
        file_prefixes = set(literal_eval(file_prefixes))

    size_range = None
    size_min = config.value_of(FileFilterConfigurationSection.FILE_SIZE_MIN)
    size_max = config.value_of(FileFilterConfigurationSection.FILE_SIZE_MAX)
    if size_min is not None or size_max is not None:
        size_range = FileSizeRange()
        if size_min is not None:
            size_range.lower = size_min

        if size_max is not None:
            size_range.upper = size_max

    ignore_nonexistent = config.value_of(
        FileFilterConfigurationSection.FILE_IGNORE_NONEXISTENT
    ) or False

    return FileFilter(
        apply_on=file_type,
        mode=file_mode,
        file_names=file_names,
        file_extensions=file_extensions,
        path_prefixes=file_prefixes,
        size_range=size_range,
        ignore_nonexistent=ignore_nonexistent,
    )


def load_filters(
    config: Configuration
) -> Sequence[FileFilter]:
    """Retrieves file filters from a configuration.

    The filters in the returned iterable are guaranteed to be ordered such that
    filters with inclusive mode come before filters with exclusive mode.

    Args:
        config (Configuration): The configuration object to load from.

    Returns:
        Sequence: A loaded sequence of `FileFilter` objects with all parameters
            found in the specified configuration.

    Raises:
        MalformedConfigurationValueException: If the specified configuration
            is malformed or missing required values.
    """
    file_filters = []
    include_filter = _load_file_filter_with_mode(
        config.get_section(ProjectConfiguration.FILE_FILTER_INCLUDE),
        FileFilter.Mode.INCLUSIVE
    )
    if include_filter is not None:
        file_filters.append(include_filter)

    exclude_filter = _load_file_filter_with_mode(
        config.get_section(ProjectConfiguration.FILE_FILTER_EXCLUDE),
        FileFilter.Mode.EXCLUSIVE
    )
    if exclude_filter is not None:
        file_filters.append(exclude_filter)

    return file_filters
