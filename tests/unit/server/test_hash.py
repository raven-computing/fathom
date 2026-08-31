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
"""Unit tests for _hash module in the security package."""

from raven.fathom.server.security._hash import PasswordHasher
from raven.fathom.server.security._hash import HashBLAKE2b, HashPBKDF2
from raven.fathom.server.security._hash import StoredPasswordHash
from raven.fathom.server.security._hash import PasswordValidation
from raven.fathom.server.security._hash import (
    PASSWORD_ENCODING,
    PBKDF2_HASH_FUNCTION,
    PBKDF2_ROUNDS,
)

from tests.unit import TestCase


class TestPasswordHasher(TestCase):
    """Unit tests for the `PasswordHasher` class."""

    def test_get_hasher_by_spec_name(self):
        hasher = PasswordHasher.by_spec(HashBLAKE2b.NAME)
        self.assertIsInstance(hasher, HashBLAKE2b)
        hasher = PasswordHasher.by_spec(HashPBKDF2.NAME)
        self.assertIsInstance(hasher, HashPBKDF2)

    def test_requesting_hasher_with_invalid_spec_name_raises_exception(self):
        with self.assertRaises(ValueError) as raised:
            PasswordHasher.by_spec("An-Invalid-Hasher-Spec")

        self.assertIn("Unsupported hash function spec", str(raised.exception))

    def test_get_default_hasher(self):
        hasher = PasswordHasher.get_default()
        self.assertIsInstance(hasher, PasswordHasher)


class TestHashBLAKE2b(TestCase):
    """Unit tests for the `HashBLAKE2b` class."""

    def test_generate_blake2b_hash_value(self):
        hasher = HashBLAKE2b()
        salt = b"A" * 16
        password = "My_Great_Password".encode(PASSWORD_ENCODING)
        hash_value = hasher.digest(password, salt)
        self.assertEqual(
            hash_value.hex(),
            "1d1a6a56e262d3c9da777b3968bf1d6ba79a21f254201fdfc42301e84fad5c86"
            "4ed1b78bb9127b16512d2e0b65e9d4db5fae329025fd0d130d1dba2c59860c76"
        )


class TestHashPBKDF2(TestCase):
    """Unit tests for the `HashPBKDF2` class."""

    def test_generate_pbkdf2_hash_value(self):
        hasher = HashPBKDF2(PBKDF2_HASH_FUNCTION, PBKDF2_ROUNDS)
        salt = b"A" * 16
        password = "My_Great_Password".encode(PASSWORD_ENCODING)
        hash_value = hasher.digest(password, salt)
        self.assertEqual(
            hash_value.hex(),
            "d71200452829738dff7f99b90a223a33c8008d71a9dea43d5b538eeb86d38735"
            "fe68022d763e5fd8a6ef0908f49f66cb12e24ca670e0bce7861119c8db58b98d"
        )


class TestStoredPasswordHash(TestCase):
    """Unit tests for the `StoredPasswordHash` class."""

    def test_generate_string_value_from_parameters(self):
        stored_hash = StoredPasswordHash(
            "pbkdf2-hmac", "fedcba9876543210", "0123456789abcdef",
        )
        self.assertEqual(
            str(stored_hash), "pbkdf2-hmac:fedcba9876543210:0123456789abcdef"
        )

    def test_creating_object_from_compact_string(self):
        stored = StoredPasswordHash.from_compact_string(
            "blake2b:fedcba9876543210:0123456789abcdef"
        )
        self.assertIsInstance(stored, StoredPasswordHash)
        self.assertEqual(stored.hash_function_name, "blake2b")
        self.assertEqual(stored.hash_value, "0123456789abcdef")
        self.assertEqual(stored.salt, "fedcba9876543210")

    def test_creating_obj_from_invalid_compact_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            StoredPasswordHash.from_compact_string("invalid_format_string")

    def test_is_stored_representation(self):
        self.assertTrue(
            StoredPasswordHash.is_stored_representation(
                "blake2b:fedcba9876543210:0123456789abcdef"
            )
        )
        self.assertFalse(
            StoredPasswordHash.is_stored_representation("invalid_format")
        )
        self.assertFalse(
            StoredPasswordHash.is_stored_representation(12345) # type: ignore
        )


class TestPasswordValidation(TestCase):
    """Unit tests for the `PasswordValidation` class."""

    def test_validate_same_passwords_correct(self):
        password = "My_Great_Password"
        stored_hash = StoredPasswordHash(
            PasswordHasher.by_spec(HashPBKDF2.NAME).specification(),
            "fedcba9876543210",
            "bb1df9c306b75fb2bec119f29269b5c38b26876415ca2bb5e24d9517d41f68ce8"
            "8e1b20154479eb31fe356a996c10d0eb834b82716488ecc970e7b1aeeb3df8d",
        )
        self.assertTrue(
            PasswordValidation.validate_equality(password, stored_hash)
        )

    def test_validate_different_passwords_are_not_equal(self):
        password = "My_Great_Password0"
        stored_hash = StoredPasswordHash(
            PasswordHasher.by_spec(HashPBKDF2.NAME).specification(),
            "fedcba9876543210",
            "bb1df9c306b75fb2bec119f29269b5c38b26876415ca2bb5e24d9517d41f68ce8"
            "8e1b20154479eb31fe356a996c10d0eb834b82716488ecc970e7b1aeeb3df8d",
        )
        self.assertFalse(
            PasswordValidation.validate_equality(password, stored_hash)
        )


if __name__ == "__main__":
    TestCase.run_tests()
