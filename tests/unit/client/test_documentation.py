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
"""Unit tests for the documentation resource classes."""

from pathlib import PurePath

from raven.fathom.base import File
from raven.fathom.client import DocsFile, DocsDir, DocumentationResource
from raven.fathom.client import FileFilter

from tests.unit import TestCase


class TestDocsFile(TestCase):
    """Tests the `DocsFile` class."""

    def test_can_create(self):
        path = PurePath("/home/user/project/build/some_file.html")
        file = DocsFile(path)
        self.assertEqual(file.path, path)
        self.assertEqual(file.name, path.name)

    def test_can_create_with_specific_name(self):
        path = PurePath("/home/user/project/build/some_file.html")
        other_name = "the_new_name.ext"
        file = DocsFile(path, other_name)
        self.assertEqual(file.path, path)
        self.assertEqual(file.name, other_name)

    def test_can_create_pathless(self):
        name = "some_name.html"
        file = DocsFile.with_name(name)
        self.assertIsNone(file.path)
        self.assertEqual(file.name, name)

    def test_equals_operator(self):
        path = PurePath("/home/user/project/build/some_file.html")
        file_1 = DocsFile(path)
        file_2 = DocsFile(path)
        self.assertEqual(file_1, file_2)
        file_3 = DocsFile(str(path))
        self.assertEqual(file_2, file_3)

    def test_not_equals_operator(self):
        file_1 = DocsFile(PurePath("/home/user/project/build/some_file.html"))
        file_2 = DocsFile(
            PurePath("/home/user/project/build/some_other_file.html")
        )
        self.assertNotEqual(file_1, file_2)
        file_3 = DocsFile("TEST.ext")
        self.assertNotEqual(file_2, file_3)

    def test_equal_objects_result_in_same_hash(self):
        path = PurePath("/home/user/project/build/some_file.html")
        file_1 = DocsFile(path)
        file_2 = DocsFile(path)
        self.assertEqual(hash(file_1), hash(file_2))
        file_3 = DocsFile("some_file.html")
        self.assertEqual(hash(file_2), hash(file_3))


class TestDocsDir(TestCase):
    """Tests the `DocsDir` class."""

    def setUp(self):
        self.testdir = PurePath("/testing/res/docsdir")
        self.testdir_subdir = PurePath("/testing/res/docsdir/subdir")
        File(self.testdir).create_directory_tree()
        File(self.testdir_subdir).create_directory()
        self.testfiles = {
            DocsFile(self.testdir / PurePath("index.html")),
            DocsFile(self.testdir / PurePath("script.js")),
            DocsFile(self.testdir / PurePath("styles.css")),
            DocsFile(self.testdir / PurePath("subdir")),
            DocsFile(
                path=self.testdir / PurePath("subdir/index.html"),
                name="subdir/index.html"
            ),
        }
        for file in self.testfiles:
            file = File(file.path) # type: ignore
            if not file.is_directory():
                file.create()

    def test_can_create(self):
        docs = DocsDir(self.testdir)
        self.assertEqual(docs.path, self.testdir)
        actual_files = set(file for file in docs)
        self.assertEqual(actual_files, self.testfiles)

    def test_anchor_files(self):
        docs = DocsDir(self.testdir)
        anchor = "aaa/bbb/ccc"
        docs.anchor_files(anchor)
        testfiles = {
            DocsFile(
                path=testfile.path,
                name=f"{anchor}/{testfile.name}"
            )
            for testfile in self.testfiles
        }
        actual_files = set(file for file in docs)
        self.assertEqual(actual_files, testfiles)

    def test_can_apply_filter(self):
        docs = DocsDir(self.testdir)
        docs.apply_filter(FileFilter(file_names={"index.html"}))
        testfiles = self.testfiles ^ {
            DocsFile(self.testdir / PurePath("index.html")),
            DocsFile(
                path=self.testdir / PurePath("subdir/index.html"),
                name="subdir/index.html"
            )
        }
        actual_files = set(file for file in docs)
        self.assertEqual(actual_files, testfiles)


class TestDocumentationResource(TestCase):
    """Tests the `DocumentationResource` class."""

    def test_can_create(self):
        docs = DocumentationResource()
        self.assertEqual(docs.size(), 0)
        self.assertTrue(docs.is_empty())
        actual_files = set(file for file in docs)
        self.assertEqual(actual_files, set())
        self.assertFalse(docs.ignore_name_collisions)

    def test_can_add_files(self):
        docs = DocumentationResource()
        docs.add_file(DocsFile("file_a.html"))
        self.assertEqual(docs.size(), 1)
        self.assertFalse(docs.is_empty())
        docs.add_file(DocsFile("file_b.html"))
        self.assertEqual(docs.size(), 2)
        docs.add_file(DocsFile("file_c.html"))
        self.assertEqual(docs.size(), 3)
        testfiles = {
            DocsFile("file_a.html"),
            DocsFile("file_b.html"),
            DocsFile("file_c.html"),
        }
        actual_files = set(file for file in docs)
        self.assertEqual(actual_files, testfiles)

    def test_contains_added_file(self):
        docs = DocumentationResource()
        docs.add_file(DocsFile("file_a.html"))
        self.assertTrue(docs.contains(DocsFile("file_a.html")))

    def test_not_contains_file_that_is_not_part_of_resource(self):
        docs = DocumentationResource()
        docs.add_file(DocsFile("file_a.html"))
        self.assertFalse(docs.contains(DocsFile("file_b.html")))


if __name__ == "__main__":
    TestCase.run_tests()
