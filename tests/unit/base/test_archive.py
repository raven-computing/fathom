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
"""Unit tests for the base archive module."""

from raven.fathom.base import ArchiveFile, ArchiveFileMember, ArchiveFileIO
from raven.fathom.base import ArchiveFileIOException
from raven.fathom.base import File, FileSize, FileSizeUnit

from tests.unit import TestCase


class TestArchiveFileMember(TestCase):
    """Unit tests for the `ArchiveFileMember` class."""

    def setUp(self):
        self.fs = File.get_file_system()
        self.fs.flush_system()

    def test_initialize_transient_directory(self):
        member = ArchiveFileMember("member_A")
        self.assertEqual(member.name, "member_A")
        self.assertIsNone(member.file)
        self.assertTrue(member.is_transient)
        self.assertTrue(member.is_directory)

    def test_initialize_transient_data(self):
        data = b"somedata"
        member = ArchiveFileMember("member_A", content=data)
        self.assertEqual(member.name, "member_A")
        self.assertIsNone(member.file)
        self.assertTrue(member.is_transient)
        self.assertFalse(member.is_directory)
        self.assertIsInstance(member.data(), bytearray)
        self.assertEqual(member.data(), data)

    def test_name_parts_list(self):
        nodes = ["member_A", "member_B", "member_C"]
        member = ArchiveFileMember(name="/".join(nodes))
        self.assertEqual(member.name, "member_A/member_B/member_C")
        self.assertEqual(member.name_parts, nodes)

    def test_node_name(self):
        nodes = ["member_A", "member_B", "member_C"]
        member = ArchiveFileMember(name="/".join(nodes))
        self.assertEqual(member.name, "member_A/member_B/member_C")
        self.assertEqual(member.node_name, "member_C")

    def test_initialize_transient_nested_directory(self):
        member = ArchiveFileMember("member_A/member_B/member_C")
        self.assertEqual(member.name, "member_A/member_B/member_C")
        self.assertIsNone(member.file)
        self.assertTrue(member.is_transient)
        self.assertTrue(member.is_directory)

    def test_initialize_transient_data_nested_name(self):
        member = ArchiveFileMember(
            name="member_A/member_B/member_C",
            content=b"somedata"
        )
        self.assertEqual(member.name, "member_A/member_B/member_C")
        self.assertIsNone(member.file)
        self.assertTrue(member.is_transient)
        self.assertFalse(member.is_directory)

    def test_initialize_transient_data_bytearray(self):
        data = bytearray(b"somedata")
        member = ArchiveFileMember("member_A", content=data)
        self.assertEqual(member.name, "member_A")
        self.assertIsNone(member.file)
        self.assertTrue(member.is_transient)
        self.assertFalse(member.is_directory)
        self.assertIsInstance(member.data(), bytearray)
        self.assertEqual(member.data(), data)

    def test_initializing_member_without_name_raises_exception(self):
        with self.assertRaises(ArchiveFileIOException) as raised:
            ArchiveFileMember("")

        self.assertIn(
            "Archive file member name must not be empty",
            str(raised.exception)
        )

    def test_initialize_nontransient_file_str(self):
        file_path = "/testing/data.txt"
        file = File(file_path)
        member = ArchiveFileMember("member_A", content=file_path)
        self.assertEqual(member.name, "member_A")
        self.assertEqual(member.file, file)
        self.assertFalse(member.is_transient)
        self.assertFalse(member.is_directory)

    def test_initialize_nontransient_file_obj(self):
        file = File("/testing/data.txt")
        member = ArchiveFileMember("member_A", content=file)
        self.assertEqual(member.name, "member_A")
        self.assertEqual(member.file, file)
        self.assertFalse(member.is_transient)
        self.assertFalse(member.is_directory)

    def test_initialize_nontransient_directory_str(self):
        dir_path = "/testing/data-dir"
        dir_file = File(dir_path)
        dir_file.create_directory_tree()
        member = ArchiveFileMember("member_A", content=dir_path)
        self.assertEqual(member.name, "member_A")
        self.assertEqual(member.file, dir_file)
        self.assertFalse(member.is_transient)
        self.assertTrue(member.is_directory)

    def test_initialize_nontransient_directory_obj(self):
        dir_file = File("/testing/data-dir")
        dir_file.create_directory_tree()
        member = ArchiveFileMember("member_A", content=dir_file)
        self.assertEqual(member.name, "member_A")
        self.assertEqual(member.file, dir_file)
        self.assertFalse(member.is_transient)
        self.assertTrue(member.is_directory)

    def test_initializing_transient_with_wrong_type_raises_exception(self):
        with self.assertRaises(TypeError):
            ArchiveFileMember(
                name="member_A",
                content=ArchiveFileMember("wrong") # type: ignore
            )

    def test_str_name(self):
        member = ArchiveFileMember("member_A", content=b"somedata")
        self.assertEqual(str(member), "ArchiveFileMember[member_A]")
        member = ArchiveFileMember("A/B/C")
        self.assertEqual(str(member), "ArchiveFileMember[A/B/C]")

    def test_get_transient_data(self):
        data = b"somedata"
        member = ArchiveFileMember("member_A", content=data)
        self.assertIsInstance(member.data(), bytearray)
        self.assertEqual(member.data(), data)

    def test_getting_data_from_directory_member_raises_exception(self):
        member = ArchiveFileMember("member_A")
        with self.assertRaises(ArchiveFileIOException) as raised:
            member.data()

        self.assertIn(
            "Cannot get data of ArchiveFileMember instance "
            "that represents a directory",
            str(raised.exception)
        )

    def test_get_nontransient_data(self):
        file = File("/testing/data.txt")
        file_content = b"Some test data text"
        file.write_all(file_content)
        member = ArchiveFileMember("member_A", content=file.path)
        data = member.data()
        self.assertIsInstance(data, bytearray)
        self.assertEqual(data, file_content)

    def test_getting_data_from_nonexistent_file_raises_exception(self):
        file_path = "/testing/this_should_not_exist"
        member = ArchiveFileMember("member_A", file_path)
        with self.assertRaises(ArchiveFileIOException) as raised:
            member.data()

        self.assertIn(
            "Failed to read ArchiveFileMember from the filesystem",
            str(raised.exception)
        )

    def test_can_mutate_transient_data(self):
        member = ArchiveFileMember("member_A", content=b"ABCDEFG")
        data = member.data()
        data[1] = ord("1".encode("ASCII"))
        data[3] = ord("3".encode("ASCII"))
        data[5] = ord("5".encode("ASCII"))
        data = member.data()
        self.assertEqual(data, bytearray(b"A1C3E5G"))


class TestArchiveFile(TestCase):
    """Unit tests for the `ArchiveFile` class."""

    def setUp(self):
        self.fs = File.get_file_system()
        self.fs.flush_system()
        # Create base directory tree
        File("/testing/state").create_directory_tree()
        self.file_transient = File("/testing/state/transient")
        # Create EXTRACTED archive file tree
        self.file_extracted = File("/testing/state/extracted")
        self.file_extracted.create_directory()
        f_a = File("/testing/state/extracted/a.txt")
        f_a.write_all("AAA")
        f_b = File("/testing/state/extracted/b.txt")
        f_b.write_all("BBB")
        File("/testing/state/extracted/c").create_directory()
        File("/testing/state/extracted/c/d").create_directory()
        f_c = File("/testing/state/extracted/c/c.txt")
        f_c.write_all("CCC")
        # All members of the test archive file
        self.file_members = [
            ArchiveFileMember("a.txt", f_a), ArchiveFileMember("b.txt", f_b),
            ArchiveFileMember("c"), ArchiveFileMember("c/d"),
            ArchiveFileMember("c/c.txt", f_c)
        ]
        # Create PACKED archive file
        self.file_packed = File("/testing/state/packed")
        ArchiveFileIO.instance().compress(self.file_members, self.file_packed)

    def test_archive_is_created_with_zip_format_by_default(self):
        archive = ArchiveFile(self.file_transient)
        self.assertEqual(archive.file_format, ArchiveFile.Format.ZIP)

    def test_states_based_on_files(self):
        transient = ArchiveFile(self.file_transient)
        extracted = ArchiveFile(self.file_extracted)
        packed = ArchiveFile(self.file_packed)
        self.assertEqual(transient.state, ArchiveFile.State.TRANSIENT)
        self.assertEqual(extracted.state, ArchiveFile.State.EXTRACTED)
        self.assertEqual(packed.state, ArchiveFile.State.PACKED)

    def test_auto_remove_is_disabled_by_default(self):
        archive = ArchiveFile(self.file_transient)
        self.assertFalse(archive.auto_remove)

    def test_path_property_is_set(self):
        path = self.file_transient
        archive = ArchiveFile(path)
        self.assertEqual(archive.file, File(path))

    def test_path_property_is_readonly(self):
        archive = ArchiveFile(self.file_transient)
        with self.assertRaises(AttributeError):
            archive.file = File("/other/file/state/transient") # type: ignore

    def test_file_format_property_is_set(self):
        archive = ArchiveFile(self.file_packed)
        self.assertEqual(archive.file_format, ArchiveFile.Format.ZIP)

    def test_file_format_property_is_readonly(self):
        archive = ArchiveFile(self.file_packed)
        with self.assertRaises(AttributeError):
            archive.file_format = ArchiveFile.Format.ZIP # type: ignore

    def test_auto_remove_property_is_set(self):
        archive = ArchiveFile(self.file_packed)
        self.assertFalse(archive.auto_remove)

    def test_auto_remove_property_can_be_set(self):
        archive = ArchiveFile(self.file_packed)
        archive.auto_remove = True
        self.assertTrue(archive.auto_remove)

    def test_get_members_returns_list(self):
        archive = ArchiveFile(self.file_transient)
        self.assertIsInstance(archive.get_members(), list)
        self.assertEqual(archive.get_members(), [])
        archive = ArchiveFile(self.file_extracted)
        self.assertIsInstance(archive.get_members(), list)

    def test_created_in_transient_state_has_no_members(self):
        archive = ArchiveFile(self.file_transient)
        self.assertEqual(archive.get_members(), [])

    def test_get_members_from_packed_archive(self):
        archive = ArchiveFile(self.file_packed)
        self.assertEqual(archive.get_members(), self.file_members)

    def test_get_members_from_extracted_archive(self):
        archive = ArchiveFile(self.file_extracted)
        self.assertEqual(archive.get_members(), self.file_members)

    def test_set_members_in_transient_state(self):
        archive = ArchiveFile(self.file_transient)
        members = [
            ArchiveFileMember("myfile_a"),
            ArchiveFileMember("myfile_b"),
            ArchiveFileMember("myfile_c"),
        ]
        archive.set_members(members)
        self.assertEqual(archive.get_members(), members)

    def test_set_members_in_extracted_state(self):
        archive = ArchiveFile(self.file_extracted)
        members = [
            ArchiveFileMember("myfile_a"),
            ArchiveFileMember("myfile_b"),
            ArchiveFileMember("myfile_c"),
        ]
        archive.set_members(members)
        self.assertEqual(archive.get_members(), members)

    def test_set_members_in_packed_state_raises_exception(self):
        archive = ArchiveFile(self.file_packed)
        members = [ArchiveFileMember("myfile_a")]
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.set_members(members)

        self.assertIn(
            "Cannot set members of a packed archive file",
            str(raised.exception)
        )

    def test_can_extract(self):
        self.file_packed.move(self.file_packed.with_suffix(".zip"))
        archive = ArchiveFile("/testing/state/packed.zip")
        archive.extract()
        self.assertEqual(archive.file, File("/testing/state/packed"))
        self.assertEqual(archive.state, ArchiveFile.State.EXTRACTED)
        self.assertEqual(archive.get_members(), self.file_members)

    def test_extract_does_not_auto_remove_by_default(self):
        archive = ArchiveFile(self.file_packed)
        archive.extract()
        self.assertTrue(self.file_packed.is_regular_file())
        self.assertTrue(archive.file.is_directory())

    def test_can_extract_with_auto_remove_enabled(self):
        archive = ArchiveFile(self.file_packed)
        archive.auto_remove = True
        archive.extract()
        self.assertFalse(self.file_packed.is_regular_file())
        self.assertTrue(archive.file.is_directory())

    def test_extract_while_not_in_extractable_state_raises_exception(self):
        archive = ArchiveFile(self.file_extracted)
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.extract()

        self.assertIn(
            "Cannot extract archive in extracted state",
            str(raised.exception)
        )

        archive = ArchiveFile(self.file_transient)
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.extract()

        self.assertIn(
            "Cannot extract archive in transient state",
            str(raised.exception)
        )

    def test_extract_to_specific_destination(self):
        archive = ArchiveFile(self.file_packed)
        dest = File("/the/path/to/dest")
        dest.create_directory_tree()
        archive.destination = dest
        archive.extract()
        self.assertEqual(archive.file, dest)
        self.assertTrue(archive.file.is_directory())
        self.assertFalse((self.file_packed / "_").exists())
        self.assertEqual(archive.state, ArchiveFile.State.EXTRACTED)
        self.assertEqual(archive.get_members(), self.file_members)
        self.assertEqual(ArchiveFile(dest).get_members(), self.file_members)

    def test_extract_destination_path_same_as_archive_raises_exception(self):
        archive = ArchiveFile("/testing/state/packed")
        archive.destination = "/testing/state/packed"
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.extract()

        self.assertIn(
            "Cannot extract archive file to same location",
            str(raised.exception)
        )
        self.assertIn(str(archive.destination), str(raised.exception))

    def test_can_pack(self):
        archive = ArchiveFile(self.file_extracted)
        packed_path = File("/testing/state/extracted.zip")
        archive.pack()
        self.assertEqual(archive.file, packed_path)
        self.assertEqual(archive.state, ArchiveFile.State.PACKED)
        self.assertEqual(archive.get_members(), self.file_members)
        self.assertEqual(
            ArchiveFile(packed_path).get_members(),
            self.file_members
        )

    def test_pack_does_not_auto_remove_by_default(self):
        archive = ArchiveFile(self.file_extracted)
        archive.pack()
        self.assertTrue(self.file_extracted.is_directory())

    def test_can_pack_with_auto_remove_enabled(self):
        archive = ArchiveFile(self.file_extracted)
        archive.auto_remove = True
        packed_file = File("/testing/state/extracted.zip")
        archive.pack()
        self.assertFalse(self.file_extracted.exists())
        self.assertTrue(packed_file.is_regular_file())
        self.assertEqual(archive.file, packed_file)
        self.assertEqual(
            ArchiveFile(packed_file).get_members(),
            self.file_members
        )

    def test_pack_while_not_in_packable_state_raises_exception(self):
        archive = ArchiveFile(self.file_packed)
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.pack()

        self.assertIn(
            "Cannot pack archive in packed state",
            str(raised.exception)
        )

    def test_pack_to_specific_destination(self):
        archive = ArchiveFile(self.file_extracted)
        packed_file = File("/the/path/to/dest")
        packed_file.get_parent_directory().create_directory_tree()
        archive.destination = packed_file
        archive.pack()
        self.assertEqual(archive.file, packed_file)
        self.assertTrue(packed_file.is_regular_file())
        self.assertEqual(archive.state, ArchiveFile.State.PACKED)
        self.assertEqual(archive.get_members(), self.file_members)
        self.assertEqual(
            ArchiveFile(packed_file).get_members(),
            self.file_members
        )

    def test_pack_destination_path_same_as_archive_raises_exception(self):
        archive = ArchiveFile(self.file_extracted)
        archive.destination = self.file_extracted
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.pack()

        self.assertIn(
            "Cannot compress archive file to same path",
            str(raised.exception)
        )
        self.assertIn(str(self.file_extracted), str(raised.exception))

    def test_add_member_to_transient_archive(self):
        archive = ArchiveFile(self.file_transient)
        len_before = len(archive.get_members())
        new_member_a = ArchiveFileMember("other_file_A")
        new_member_b = ArchiveFileMember("other_dir/other_file_A")
        archive.add(new_member_a)
        archive.add(new_member_b)
        self.assertEqual(len(archive.get_members()), len_before + 3)
        self.assertTrue(archive.contains(new_member_a))
        self.assertTrue(archive.contains(new_member_b))
        self.assertTrue(archive.contains(ArchiveFileMember("other_dir")))

    def test_add_member_to_extracted_archive(self):
        archive = ArchiveFile(self.file_extracted)
        len_before = len(archive.get_members())
        new_member_a = ArchiveFileMember("other_file_A")
        new_member_b = ArchiveFileMember("other_dir_a/other_dir_b/B")
        archive.add(new_member_a)
        self.assertEqual(len(archive.get_members()), len_before + 1)
        archive.add(new_member_b)
        self.assertEqual(len(archive.get_members()), len_before + 4)
        self.assertTrue(archive.contains(new_member_a))
        self.assertTrue(archive.contains(new_member_b))
        self.assertTrue(archive.contains(ArchiveFileMember("other_dir_a")))

    def test_add_member_with_add_operator(self):
        archive = ArchiveFile(self.file_extracted)
        len_before = len(archive.get_members())
        new_member_a = ArchiveFileMember("other_file_A")
        new_member_b = ArchiveFileMember("other_dir_a/other_dir_b/B")
        archive += new_member_a
        self.assertEqual(len(archive.get_members()), len_before + 1)
        archive += new_member_b
        self.assertEqual(len(archive.get_members()), len_before + 4)
        self.assertTrue(archive.contains(new_member_a))
        self.assertTrue(archive.contains(new_member_b))
        self.assertTrue(archive.contains(ArchiveFileMember("other_dir_a")))

    def test_add_already_existing_member_raises_exception(self):
        archive = ArchiveFile(self.file_transient)
        archive.add(ArchiveFileMember("file1", content=bytes()))
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.add(ArchiveFileMember("file1", content=bytes()))

        self.assertIn(
            "Archive file member 'file1' is already present",
            str(raised.exception)
        )

        archive = ArchiveFile(self.file_extracted)
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.add(ArchiveFileMember("a.txt"))

        self.assertIn(
            "Archive file member 'a.txt' is already present",
            str(raised.exception)
        )

    def test_adding_already_existing_directory_member_succeeds(self):
        archive = ArchiveFile(self.file_transient)
        archive.add(ArchiveFileMember("dir1"))
        archive.add(ArchiveFileMember("dir1"))
        self.assertEqual(len(archive.get_members()), 1)
        self.assertEqual(
            archive.get_member_by_name("dir1"), ArchiveFileMember("dir1")
        )

    def test_add_member_in_packed_state_raises_exception(self):
        archive = ArchiveFile(self.file_packed)
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.add(ArchiveFileMember("other_file_A"))

        self.assertIn(
            "Cannot add member to archive in packed state",
            str(raised.exception)
        )

    def test_remove_member_from_transient_archive(self):
        archive = ArchiveFile(self.file_transient)
        archive.add(ArchiveFileMember("file_A"))
        archive.add(ArchiveFileMember("dir_A/file_A"))
        self.assertTrue(archive.remove(ArchiveFileMember("file_A")))
        self.assertEqual(len(archive.get_members()), 2)
        self.assertFalse(archive.contains(ArchiveFileMember("file_A")))
        self.assertTrue(archive.remove(ArchiveFileMember("dir_A/file_A")))
        self.assertEqual(len(archive.get_members()), 1)
        self.assertFalse(archive.contains(ArchiveFileMember("dir_A/file_A")))
        self.assertTrue(archive.remove(ArchiveFileMember("dir_A")))
        self.assertEqual(len(archive.get_members()), 0)
        self.assertFalse(archive.contains(ArchiveFileMember("dir_A")))

    def test_remove_member_from_extracted_archive(self):
        archive = ArchiveFile(self.file_extracted)
        archive.add(ArchiveFileMember("file_A"))
        archive.add(ArchiveFileMember("dir_A/dir_B/file_C"))
        len_before = len(archive.get_members())
        self.assertTrue(archive.remove(ArchiveFileMember("file_A")))
        self.assertEqual(len(archive.get_members()), len_before - 1)
        self.assertFalse(archive.contains(ArchiveFileMember("file_A")))
        self.assertTrue(
            archive.remove(ArchiveFileMember("dir_A/dir_B/file_C"))
        )
        self.assertEqual(len(archive.get_members()), len_before - 2)
        self.assertFalse(
            archive.contains(ArchiveFileMember("dir_A/dir_B/file_C"))
        )

    def test_remove_member_from_extracted_archive_does_not_remove_file(self):
        archive = ArchiveFile(self.file_extracted)
        member_to_remove = self.file_members[0]
        archive.remove(member_to_remove)
        self.assertEqual(archive.get_members(), self.file_members[1:])
        self.assertTrue((self.file_extracted / member_to_remove.name).exists())

    def test_remove_member_in_packed_state_raises_exception(self):
        archive = ArchiveFile(self.file_packed)
        with self.assertRaises(ArchiveFileIOException) as raised:
            archive.remove(ArchiveFileMember("file1"))

        self.assertIn(
            "Cannot remove member from archive in packed state",
            str(raised.exception)
        )

    def test_remove_nonexistent_member(self):
        archive = ArchiveFile(self.file_extracted)
        len_before = len(archive.get_members())
        self.assertFalse(archive.remove(ArchiveFileMember("extfile4")))
        self.assertEqual(len(archive.get_members()), len_before)
        self.assertFalse(archive.remove(ArchiveFileMember("extfile0")))
        self.assertEqual(len(archive.get_members()), len_before)
        self.assertEqual(archive.get_members(), self.file_members)

    def test_get_size_of_empty_transient_archive(self):
        archive = ArchiveFile(self.file_transient)
        size = archive.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)
        self.assertEqual(size.in_bytes(), 0)

    def test_get_size_of_transient_archive(self):
        archive = ArchiveFile(self.file_transient)
        archive.set_members(self.file_members)
        size = archive.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)
        self.assertEqual(size.in_bytes(), 9)

    def test_get_size_of_extracted_archive(self):
        archive = ArchiveFile(self.file_extracted)
        size = archive.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)
        self.assertEqual(size.in_bytes(), 9)

    def test_get_size_of_packed_archive(self):
        archive = ArchiveFile(self.file_packed)
        size = archive.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)
        self.assertEqual(size.in_bytes(), self.file_packed.size().in_bytes())

    def test_member_count(self):
        archive = ArchiveFile(self.file_transient)
        archive.set_members(self.file_members)
        self.assertIsInstance(archive.member_count(), int)
        self.assertEqual(archive.member_count(), len(self.file_members))
        archive = ArchiveFile(self.file_extracted)
        archive.remove(self.file_members[0])
        archive.remove(self.file_members[1])
        self.assertIsInstance(archive.member_count(), int)
        self.assertEqual(archive.member_count(), len(self.file_members) - 2)
        archive = ArchiveFile(self.file_packed)
        self.assertIsInstance(archive.member_count(), int)
        self.assertEqual(archive.member_count(), len(self.file_members))

    def test_get_member_by_name(self):
        archive = ArchiveFile(self.file_transient)
        archive.set_members(self.file_members)
        self.assertEqual(
            archive.get_member_by_name("a.txt"), ArchiveFileMember("a.txt")
        )
        archive = ArchiveFile(self.file_extracted)
        self.assertEqual(
            archive.get_member_by_name("b.txt"), ArchiveFileMember("b.txt")
        )
        archive = ArchiveFile(self.file_packed)
        self.assertEqual(
            archive.get_member_by_name("c/c.txt"), ArchiveFileMember("c/c.txt")
        )

    def test_contains_member_in_transient_archive(self):
        archive = ArchiveFile(self.file_transient)
        member_a = ArchiveFileMember("file_A")
        member_b = ArchiveFileMember("dir_A/file_B")
        archive.add(member_a)
        archive.add(member_b)
        self.assertTrue(archive.contains(ArchiveFileMember("file_A")))
        self.assertTrue(archive.contains(ArchiveFileMember("dir_A/file_B")))
        self.assertTrue(archive.contains(ArchiveFileMember("dir_A")))
        self.assertEqual(len(archive.get_members()), 3)
        self.assertFalse(archive.contains(ArchiveFileMember("dir_B")))
        self.assertFalse(archive.contains(ArchiveFileMember("file_B")))

    def test_contains_member_in_extracted_archive(self):
        archive = ArchiveFile(self.file_extracted)
        self.assertTrue(archive.contains(ArchiveFileMember("a.txt")))
        self.assertTrue(archive.contains(ArchiveFileMember("c/d")))
        self.assertFalse(archive.contains(ArchiveFileMember("file_A")))

    def test_contains_member_in_packed_archive(self):
        archive = ArchiveFile(self.file_packed)
        self.assertTrue(archive.contains(ArchiveFileMember("a.txt")))
        self.assertTrue(archive.contains(ArchiveFileMember("c/d")))
        self.assertFalse(archive.contains(ArchiveFileMember("dir2/file5")))

    def test_contains_member_with_in_operator(self):
        archive = ArchiveFile(self.file_packed)
        self.assertTrue("a.txt" in archive)
        self.assertTrue(ArchiveFileMember("c/d") in archive)
        self.assertFalse("dir2/file5" in archive)
        self.assertTrue("dir2/file5" not in archive)

    def test_get_member_with_subscription_operator(self):
        archive = ArchiveFile(self.file_extracted)
        self.assertEqual(archive["a.txt"], ArchiveFileMember("a.txt"))
        self.assertEqual(archive["c/d"], ArchiveFileMember("c/d"))
        archive = ArchiveFile(self.file_packed)
        self.assertEqual(archive["c/c.txt"], ArchiveFileMember("c/c.txt"))

    def test_archive_member_iterator(self):
        archive = ArchiveFile(self.file_extracted)
        n = 0
        for member in archive:
            n += 1
            self.assertIn(member, self.file_members)

        self.assertEqual(n, len(self.file_members))

    def test_remove_directory_member_also_removes_children(self):
        archive = ArchiveFile(self.file_transient)
        archive.add(ArchiveFileMember("file_A", content=bytes()))
        archive.add(ArchiveFileMember(
            "dir_A_donotremove/file_A", content=bytes())
        )
        archive.add(ArchiveFileMember("dir_A/file_A", content=bytes()))
        archive.add(ArchiveFileMember("dir_A/dir_B"))
        archive.add(ArchiveFileMember("dir_A/dir_B/file_B", content=bytes()))
        self.assertTrue(archive.remove(ArchiveFileMember("dir_A")))
        self.assertEqual(len(archive.get_members()), 3)
        self.assertFalse(
            archive.contains(ArchiveFileMember("dir_A/dir_B/file_B"))
        )
        self.assertFalse(archive.contains(ArchiveFileMember("dir_A/dir_B")))
        self.assertFalse(archive.contains(ArchiveFileMember("dir_A/file_A")))
        self.assertFalse(archive.contains(ArchiveFileMember("dir_A")))
        self.assertTrue(archive.contains(ArchiveFileMember("file_A")))
        self.assertTrue(
            archive.contains(ArchiveFileMember("dir_A_donotremove/file_A"))
        )
        self.assertTrue(
            archive.contains(ArchiveFileMember("dir_A_donotremove"))
        )

    def test_remove_directory_member_in_subdir_also_removes_children(self):
        archive = ArchiveFile(self.file_transient)
        archive.add(ArchiveFileMember("file_A", content=bytes()))
        archive.add(ArchiveFileMember("dir_A/file_A", content=bytes()))
        archive.add(ArchiveFileMember("dir_A/dir_B"))
        archive.add(ArchiveFileMember("dir_A/dir_B/file_A", content=bytes()))
        archive.add(ArchiveFileMember("dir_A/dir_B/file_B", content=bytes()))
        self.assertTrue(archive.remove(ArchiveFileMember("dir_A/dir_B")))
        self.assertEqual(len(archive.get_members()), 3)
        self.assertFalse(
            archive.contains(ArchiveFileMember("dir_A/dir_B/file_A"))
        )
        self.assertFalse(
            archive.contains(ArchiveFileMember("dir_A/dir_B/file_B"))
        )
        self.assertFalse(archive.contains(ArchiveFileMember("dir_A/dir_B")))
        self.assertTrue(archive.contains(ArchiveFileMember("dir_A/file_A")))
        self.assertTrue(archive.contains(ArchiveFileMember("dir_A")))
        self.assertTrue(archive.contains(ArchiveFileMember("file_A")))


if __name__ == "__main__":
    TestCase.run_tests()
