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
"""Unit tests for the file resource filters."""

import os

from raven.fathom.base import File
from raven.fathom.client import FileFilter
from raven.fathom.client import FileSizeRange, UNBOUND_FILE_SIZE
from raven.fathom.client import FileSize, FileSizeUnit
from raven.fathom.client import DocsFile

from tests.unit import TestCase


class TestFileFilter(TestCase):
    """Tests the `FileFilter` class."""

    def setUp(self):
        base_dir = "/testing/res/filter"
        self.basedir = File(base_dir)
        self.basedir.create_directory_tree()
        self.index_html = DocsFile(self.basedir / "non_empty_dir/index.html")
        self.testfile_1_html = DocsFile(self.basedir / "page_32b.html")
        self.testfile_2_html = DocsFile(self.basedir / "page_64b.html")
        self.testfile_3_html = DocsFile(self.basedir / "page_96b.html")
        self.testfiles_html = {
            self.index_html,
            self.testfile_1_html,
            self.testfile_2_html,
            self.testfile_3_html,
        }
        self.testfile_1_js = DocsFile(self.basedir / "script_32b.js")
        self.testfile_2_js = DocsFile(self.basedir / "script_64b.js")
        self.testfile_3_js = DocsFile(self.basedir / "script_96b.js")
        self.testfiles_js = {
            self.testfile_1_js,
            self.testfile_2_js,
            self.testfile_3_js,
        }
        self.testfile_1_css = DocsFile(self.basedir / "styles_32b.css")
        self.testfile_2_css = DocsFile(self.basedir / "styles_64b.css")
        self.testfile_3_css = DocsFile(self.basedir / "styles_96b.css")
        self.testfiles_css = {
            self.testfile_1_css,
            self.testfile_2_css,
            self.testfile_3_css,
        }
        self.testdir_empty = DocsFile(self.basedir / "empty_dir")
        self.testdir_1 = DocsFile(self.basedir / "non_empty_dir")

        self.all_testfiles = (
            self.testfiles_html
            | self.testfiles_js
            | self.testfiles_css
            | {self.index_html}
        )
        self.all_testdirs = {self.testdir_1, self.testdir_empty}
        self.all_any = self.all_testfiles | self.all_testdirs
        for directory in self.all_testdirs:
            File(directory.path).create_directory() # type: ignore

        for file in self.all_testfiles:
            File(file.path).create() # type: ignore

        File(self.index_html.path).write_all("non-empty") # type: ignore
        File(self.testfile_1_html.path).write_all("A" * 32) # type: ignore
        File(self.testfile_2_html.path).write_all("A" * 64) # type: ignore
        File(self.testfile_3_html.path).write_all("A" * 96) # type: ignore
        File(self.testfile_1_js.path).write_all("B" * 32) # type: ignore
        File(self.testfile_2_js.path).write_all("B" * 64) # type: ignore
        File(self.testfile_3_js.path).write_all("B" * 96) # type: ignore
        File(self.testfile_1_css.path).write_all("C" * 32) # type: ignore
        File(self.testfile_2_css.path).write_all("C" * 64) # type: ignore
        File(self.testfile_3_css.path).write_all("C" * 96) # type: ignore

    def test_apply_on_any_type(self):
        fltr = FileFilter(
            apply_on=FileFilter.FileType.ANY,
            file_names={"index.html", "non_empty_dir", "page_64b.html"},
        )
        expected = self.all_any ^ {
            self.index_html, self.testdir_1, self.testfile_2_html
        }
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_apply_on_regular_files_match(self):
        fltr = FileFilter(
            apply_on=FileFilter.FileType.REGULAR_FILE,
            file_extensions={".html"},
        )
        expected = self.all_any ^ self.testfiles_html
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_apply_on_regular_files_no_match(self):
        fltr = FileFilter(
            apply_on=FileFilter.FileType.REGULAR_FILE,
            file_names={"non_empty_dir", "empty_dir"},
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_apply_on_directories_match(self):
        fltr = FileFilter(
            apply_on=FileFilter.FileType.DIRECTORY,
            file_names={"non_empty_dir", "empty_dir"},
        )
        expected = self.all_any ^ {self.testdir_1, self.testdir_empty}
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_apply_on_directories_no_match(self):
        fltr = FileFilter(
            apply_on=FileFilter.FileType.DIRECTORY,
            file_extensions={".html", ".js", ".css"},
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_mode_exclusive_match(self):
        fltr = FileFilter(
            mode=FileFilter.Mode.EXCLUSIVE,
            file_extensions={".html", ".css"},
        )
        expected = self.all_any ^ (self.testfiles_html | self.testfiles_css)
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_mode_exclusive_no_match(self):
        fltr = FileFilter(
            mode=FileFilter.Mode.EXCLUSIVE,
            file_extensions={".xml", ".java"},
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_mode_inclusive_match(self):
        fltr = FileFilter(
            mode=FileFilter.Mode.INCLUSIVE,
            file_extensions={".html", ".css"},
        )
        expected = self.testfiles_html | self.testfiles_css
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_mode_inclusive_no_match(self):
        fltr = FileFilter(
            mode=FileFilter.Mode.INCLUSIVE,
            file_extensions={".xml", ".java"},
        )
        expected = set()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_file_names(self):
        fltr = FileFilter(
            file_names={"index.html", "non_empty_dir"},
        )
        expected = self.all_any ^ {
            self.index_html, self.testdir_1
        }
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_no_match_file_names(self):
        fltr = FileFilter(
            file_names={"should_not_exist", "non-existent.xml"},
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_file_extensions(self):
        fltr = FileFilter(
            file_extensions={".js", ".java"},
        )
        expected = self.all_any ^ self.testfiles_js
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_no_match_file_extensions(self):
        fltr = FileFilter(
            file_extensions={".xml", ".h"},
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_size_range_lower(self):
        fltr = FileFilter(
            size_range=FileSizeRange(lower=FileSize(96, FileSizeUnit.BYTE)),
        )
        expected = self.all_any ^ {
            self.testfile_3_html,
            self.testfile_3_js,
            self.testfile_3_css,
        }
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_size_range_upper(self):
        fltr = FileFilter(
            mode=FileFilter.Mode.INCLUSIVE,
            size_range=FileSizeRange(upper=FileSize(32, FileSizeUnit.BYTE)),
        )
        expected = self.all_any ^ {
            self.testfile_2_html,
            self.testfile_2_js,
            self.testfile_2_css,
            self.testfile_3_html,
            self.testfile_3_js,
            self.testfile_3_css,
        }
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_size_range_lower_and_upper(self):
        fltr = FileFilter(
            mode=FileFilter.Mode.INCLUSIVE,
            size_range=FileSizeRange(
                lower=FileSize(1, FileSizeUnit.BYTE),
                upper=FileSize(64, FileSizeUnit.BYTE)
            ),
        )
        expected = self.all_any ^ {
            self.testdir_empty,
            self.testfile_3_html,
            self.testfile_3_js,
            self.testfile_3_css,
        }
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_size_range_unbounded_excl(self):
        unbounded_range = FileSizeRange(
            lower=UNBOUND_FILE_SIZE,
            upper=UNBOUND_FILE_SIZE
        )
        fltr = FileFilter(
            mode=FileFilter.Mode.EXCLUSIVE,
            size_range=unbounded_range,
        )
        result = fltr.apply(self.all_any)
        self.assertEqual(result, set())

    def test_match_size_range_unbounded_incl(self):
        unbounded_range = FileSizeRange(
            lower=UNBOUND_FILE_SIZE,
            upper=UNBOUND_FILE_SIZE
        )
        fltr = FileFilter(
            mode=FileFilter.Mode.INCLUSIVE,
            size_range=unbounded_range
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_match_file_path_prefixes(self):
        fltr = FileFilter(
            path_prefixes={
                os.path.join(self.basedir.path, "page"),
                os.path.join(self.basedir.path, "non_empty_dir"),
            },
        )
        expected = self.all_any ^ (self.testfiles_html | {self.testdir_1})
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_no_match_file_path_prefixes(self):
        fltr = FileFilter(
            path_prefixes={
                "/this/path/should/not/exist",
                "/this/path/should/also/not/exist",
            },
        )
        expected = self.all_any.copy()
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_ignore_nonexistent_flag_inclusive_by_file_names(self):
        nonexistent_1 = DocsFile(
            self.basedir.path / "this_does_not_exist.html"
        )
        nonexistent_2 = DocsFile(self.basedir.path / "page_1234b.html")
        self.all_any.add(nonexistent_1)
        self.all_any.add(nonexistent_2)
        fltr = FileFilter(
            mode=FileFilter.Mode.INCLUSIVE,
            file_names={
                "index.html",
                "this_does_not_exist.html",
                "page_1234b.html",
            },
            ignore_nonexistent=True,
        )
        expected = {self.index_html, nonexistent_1, nonexistent_2}
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)

    def test_ignore_nonexistent_flag_exclusive_by_file_names(self):
        nonexistent_1 = DocsFile(
            self.basedir.path / "this_does_not_exist.html"
        )
        nonexistent_2 = DocsFile(self.basedir.path / "page_1234b.html")
        self.all_any.add(nonexistent_1)
        self.all_any.add(nonexistent_2)
        fltr = FileFilter(
            mode=FileFilter.Mode.EXCLUSIVE,
            file_names={
                "index.html",
                "this_does_not_exist.html",
                "page_1234b.html",
            },
            ignore_nonexistent=True,
        )
        expected = self.all_any ^ {self.index_html}
        result = fltr.apply(self.all_any)
        self.assertEqual(result, expected)


class TestFileSizeRange(TestCase):
    """Tests for the `FileSizeRange` class."""

    def test_file_size_range_is_unbound(self):
        size_range = FileSizeRange()
        self.assertTrue(size_range.is_unbound())

    def test_file_size_range_is_bound(self):
        size_range = FileSizeRange(lower=FileSize(32, FileSizeUnit.BYTE))
        self.assertFalse(size_range.is_unbound())

    def test_file_size_range_invalid_arguments_raises_type_error(self):
        with self.assertRaises(TypeError):
            FileSizeRange(lower="not-a-file-size") # type: ignore

        with self.assertRaises(TypeError):
            FileSizeRange(upper="not-a-file-size") # type: ignore


if __name__ == "__main__":
    TestCase.run_tests()
