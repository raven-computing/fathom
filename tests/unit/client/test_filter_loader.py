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
"""Unit tests for the filter_loader module."""

from collections.abc import Sequence

from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.base import MalformedConfigurationValueException
from raven.fathom.client import FileFilter
from raven.fathom.client import FileSizeRange, UNBOUND_FILE_SIZE
from raven.fathom.client import FileSize, FileSizeUnit
from raven.fathom.client.config import ProjectConfiguration
from raven.fathom.client.filter_loader import load_filters

from tests.unit import TestCase


class TestFileFilterLoading(TestCase):
    """Tests the `load_filters()` function."""

    def setUp(self):
        self.config = Configuration()
        self.config_section_incl = ConfigurationSection(
            ProjectConfiguration.FILE_FILTER_INCLUDE
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_TYPE, "any"
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_NAMES,
            {"index.html", "about.html"}
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_EXTENSIONS,
            {".html", "xml"}
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_PREFIXES,
            {"search", "data/bin"}
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_SIZE_MIN, "8B"
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_SIZE_MAX, "10MB"
        )
        self.config_section_incl.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_IGNORE_NONEXISTENT,
            False
        )
        self.config.add_section(self.config_section_incl)
        self.config_section_excl = ConfigurationSection(
            ProjectConfiguration.FILE_FILTER_EXCLUDE
        )
        self.config_section_excl.set_value(
            ProjectConfiguration.FILE_FILTER_EXCLUDE.FILE_TYPE, "any"
        )
        self.config_section_excl.set_value(
            ProjectConfiguration.FILE_FILTER_EXCLUDE.FILE_NAMES, {"bad.html"}
        )
        self.config_section_excl.set_value(
            ProjectConfiguration.FILE_FILTER_EXCLUDE.FILE_EXTENSIONS, {".txt"}
        )
        self.config_section_excl.set_value(
            ProjectConfiguration.FILE_FILTER_EXCLUDE.FILE_PREFIXES,
            {"data/bin"}
        )
        self.config_section_excl.set_value(
            ProjectConfiguration.FILE_FILTER_EXCLUDE.FILE_SIZE_MAX, "50MB"
        )
        self.config_section_excl.set_value(
            ProjectConfiguration.FILE_FILTER_EXCLUDE.FILE_IGNORE_NONEXISTENT,
            True
        )
        self.config.add_section(self.config_section_excl)

    def test_load_filters_returns_all_declared_filters(self):
        filters = load_filters(self.config)
        self.assertIsInstance(filters, Sequence)
        self.assertEqual(len(filters), 2)
        include_filter = filters[0]
        self.assertIsInstance(include_filter, FileFilter)
        self.assertEqual(include_filter.mode, FileFilter.Mode.INCLUSIVE)
        self.assertEqual(include_filter.file_type, FileFilter.FileType.ANY)
        self.assertEqual(
            include_filter.file_names,
            {"index.html", "about.html"}
        )
        self.assertEqual(include_filter.file_extensions, {".html", ".xml"})
        self.assertEqual(include_filter.path_prefixes, {"search", "data/bin"})
        self.assertEqual(
            str(include_filter.size_range),
            str(
                FileSizeRange(
                    lower=FileSize(8, FileSizeUnit.BYTE),
                    upper=FileSize(10, FileSizeUnit.MEGABYTE)
                )
            )
        )
        self.assertEqual(include_filter.ignore_nonexistent, False)
        exclude_filter = filters[1]
        self.assertIsInstance(exclude_filter, FileFilter)
        self.assertEqual(exclude_filter.mode, FileFilter.Mode.EXCLUSIVE)
        self.assertEqual(exclude_filter.file_type, FileFilter.FileType.ANY)
        self.assertEqual(exclude_filter.file_names, {"bad.html"})
        self.assertEqual(exclude_filter.file_extensions, {".txt"})
        self.assertEqual(exclude_filter.path_prefixes, {"data/bin"})
        self.assertEqual(
            str(exclude_filter.size_range),
            str(
                FileSizeRange(
                    lower=UNBOUND_FILE_SIZE,
                    upper=FileSize(50, FileSizeUnit.MEGABYTE)
                )
            )
        )
        self.assertEqual(exclude_filter.ignore_nonexistent, True)

    def test_load_filters_with_empty_config_returns_empty_list(self):
        filters = load_filters(Configuration())
        self.assertIsInstance(filters, Sequence)
        self.assertEqual(len(filters), 0)

    def test_load_filters_with_only_include_filter(self):
        self.config.remove_section(ProjectConfiguration.FILE_FILTER_EXCLUDE)
        filters = load_filters(self.config)
        self.assertIsInstance(filters, Sequence)
        self.assertEqual(len(filters), 1)
        include_filter = filters[0]
        self.assertIsInstance(include_filter, FileFilter)
        self.assertEqual(include_filter.mode, FileFilter.Mode.INCLUSIVE)
        self.assertEqual(include_filter.file_type, FileFilter.FileType.ANY)
        self.assertEqual(
            include_filter.file_names,
            {"index.html", "about.html"}
        )
        self.assertEqual(include_filter.file_extensions, {".html", ".xml"})
        self.assertEqual(include_filter.path_prefixes, {"search", "data/bin"})
        self.assertEqual(
            str(include_filter.size_range),
            str(
                FileSizeRange(
                    lower=FileSize(8, FileSizeUnit.BYTE),
                    upper=FileSize(10, FileSizeUnit.MEGABYTE)
                )
            )
        )
        self.assertEqual(include_filter.ignore_nonexistent, False)

    def test_load_filters_with_only_exclude_filter(self):
        self.config.remove_section(ProjectConfiguration.FILE_FILTER_INCLUDE)
        filters = load_filters(self.config)
        self.assertIsInstance(filters, Sequence)
        self.assertEqual(len(filters), 1)
        exclude_filter = filters[0]
        self.assertIsInstance(exclude_filter, FileFilter)
        self.assertEqual(exclude_filter.mode, FileFilter.Mode.EXCLUSIVE)
        self.assertEqual(exclude_filter.file_type, FileFilter.FileType.ANY)
        self.assertEqual(exclude_filter.file_names, {"bad.html"})
        self.assertEqual(exclude_filter.file_extensions, {".txt"})
        self.assertEqual(exclude_filter.path_prefixes, {"data/bin"})
        self.assertEqual(
            str(exclude_filter.size_range),
            str(
                FileSizeRange(
                    lower=UNBOUND_FILE_SIZE,
                    upper=FileSize(50, FileSizeUnit.MEGABYTE)
                )
            )
        )
        self.assertEqual(exclude_filter.ignore_nonexistent, True)

    def test_load_filters_with_various_file_types(self):
        types_map = {
            "regular_file": FileFilter.FileType.REGULAR_FILE,
            "directory": FileFilter.FileType.DIRECTORY,
            "symlink": FileFilter.FileType.SYMLINK,
            "nonexistent": FileFilter.FileType.NONEXISTENT,
        }
        for type_str in types_map:
            config = Configuration()
            config_section = ConfigurationSection(
                ProjectConfiguration.FILE_FILTER_INCLUDE
            )
            config_section.set_value(
                ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_TYPE,
                type_str
            )
            config_section.set_value(
                ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_NAMES,
                {"index.html"}
            )
            config.add_section(config_section)
            filters = load_filters(config)
            self.assertEqual(len(filters), 1)

    def test_load_filters_invalid_file_type_raises_exception(self):
        config = Configuration()
        config_section = ConfigurationSection(
            ProjectConfiguration.FILE_FILTER_INCLUDE
        )
        config_section.set_value(
            ProjectConfiguration.FILE_FILTER_INCLUDE.FILE_TYPE,
            "invalid_type"
        )
        config.add_section(config_section)

        with self.assertRaises(MalformedConfigurationValueException):
            load_filters(config)


if __name__ == "__main__":
    TestCase.run_tests()
