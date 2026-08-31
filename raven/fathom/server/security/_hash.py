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
"""Hashing-related facilities used in a security context."""

import hashlib
import hmac
import re

from abc import ABC, abstractmethod
from typing import Final

if "blake2b" not in hashlib.algorithms_guaranteed:
    raise ImportError("Fatal: Required hash algorithm 'blake2b' not available")


PASSWORD_ENCODING: Final = "UTF-8"

PBKDF2_HASH_FUNCTION: Final = "sha512"

PBKDF2_ROUNDS: Final = 2048

REGEX_STORED_HASH_REPR: Final = re.compile(
    r"^([a-z0-9\-_]+):([a-f0-9]+):([a-f0-9]+)$"
)


class PasswordHasher(ABC):
    """Abstract base class for password hashers."""

    @abstractmethod
    def specification(self) -> str:
        """Returns the specification of hash algorithm."""

    @abstractmethod
    def digest(self, password: bytes, salt: bytes) -> bytes:
        """Performs a hash digest."""

    @staticmethod
    def by_spec(hash_function_spec: str) -> "PasswordHasher":
        """Returns a password hasher instance for the
        given hash function specification.
        """
        if hash_function_spec.startswith(HashPBKDF2.NAME):
            if not HashPBKDF2.is_available():
                raise ValueError(
                    f"Password hash function '{hash_function_spec}' is "
                    "not available on this system."
                )
            return HashPBKDF2(PBKDF2_HASH_FUNCTION, PBKDF2_ROUNDS)

        if hash_function_spec.startswith(HashBLAKE2b.NAME):
            return HashBLAKE2b()

        raise ValueError(
            f"Unsupported hash function spec: '{hash_function_spec}'"
        )

    @staticmethod
    def get_default() -> "PasswordHasher":
        """Returns the default password hasher for this system."""
        if HashPBKDF2.is_available():
            return HashPBKDF2(PBKDF2_HASH_FUNCTION, PBKDF2_ROUNDS)

        return HashBLAKE2b()


class HashBLAKE2b(PasswordHasher):
    """Password hasher using the BLAKE2b hash function."""

    NAME: Final = "blake2b"

    def specification(self):
        return HashBLAKE2b.NAME

    def digest(self, password, salt):
        return hashlib.blake2b(password, salt=salt).digest()


class HashPBKDF2(PasswordHasher):
    """Password hasher using the PBKDF2 password hashing algorithm."""

    NAME: Final = "pbkdf2-hmac"

    _IS_AVAILABLE = None

    def __init__(self, hmac_hash: str, rounds: int):
        self.hmac_hash: str = hmac_hash
        self.rounds: int = rounds

    def specification(self):
        return f"{HashPBKDF2.NAME}-{self.hmac_hash}-{self.rounds}"

    def digest(self, password, salt):
        return hashlib.pbkdf2_hmac(self.hmac_hash, password, salt, self.rounds)

    @staticmethod
    def is_available() -> bool:
        """Indicates whether the PBKDF2 password hasher
        is available on this system.
        """
        if HashPBKDF2._IS_AVAILABLE is None:
            HashPBKDF2._IS_AVAILABLE = (
                hasattr(hashlib, "pbkdf2_hmac")
                and callable(getattr(hashlib, "pbkdf2_hmac"))
            )

        return HashPBKDF2._IS_AVAILABLE


class StoredPasswordHash:
    """Represents a password hash as stored in persistent storage, including
    the hash function name, the salt, and the hash value.
    """

    DELIMITER: Final = ":"

    NUMBER_OF_PARTS: Final = 3

    def __init__(self, hash_function_name: str, salt: str, hash_value: str):
        self.hash_function_name: str = hash_function_name
        self.hash_value: str = hash_value
        self.salt: str = salt

    def __str__(self):
        return (
            f"{self.hash_function_name}{StoredPasswordHash.DELIMITER}"
            f"{self.salt}{StoredPasswordHash.DELIMITER}{self.hash_value}"
        )

    @staticmethod
    def is_stored_representation(string: str) -> bool:
        """Checks whether the given string is a valid stored password
        hash representation.
        """
        if isinstance(string, str):
            match = REGEX_STORED_HASH_REPR.match(string)
            return bool(match)

        return False

    @staticmethod
    def from_compact_string(string: str) -> "StoredPasswordHash":
        """Creates a StoredPasswordHash instance from
        a compact string representation.
        """
        parts = string.split(StoredPasswordHash.DELIMITER)
        if len(parts) != StoredPasswordHash.NUMBER_OF_PARTS:
            raise ValueError(
                f"Invalid stored hash item '{string}': Invalid format"
            )

        return StoredPasswordHash(parts[0], parts[1], parts[2])


def _compare_password_hashes(
    hashed_password: bytes,
    known_password_hash: bytes
) -> bool:

    return hmac.compare_digest(hashed_password, known_password_hash)


class PasswordValidation:
    """Internal API to securely validate a password
    against a stored password hash.
    """

    @staticmethod
    def validate_equality(
        password: str,
        stored_password: StoredPasswordHash
    ) -> bool:
        """Validates whether the given plain-text password matches
        the expected stored password hash.
        """
        hasher = PasswordHasher.by_spec(stored_password.hash_function_name)
        salt = bytes.fromhex(stored_password.salt)
        hash_bytes = hasher.digest(password.encode(PASSWORD_ENCODING), salt)
        stored_hash_bytes = bytes.fromhex(stored_password.hash_value)
        return _compare_password_hashes(hash_bytes, stored_hash_bytes)
