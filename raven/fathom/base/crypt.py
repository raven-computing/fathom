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
"""Cryptographic utilities."""

from typing import Final

import string

from raven.fathom.base.entropy import EntropySource


class SecretToken:
    """A cryptographically strong secret token.

    A token consists of printable characters and can be converted to a string.
    """

    ALPHABET_ASCII: Final = string.ascii_letters + string.digits

    ALPHABET_HEX: Final = string.digits + "abcdef"

    ALPHABET_OCTAL: Final = string.octdigits

    ALPHABET_BINARY: Final = "01"

    ALPHABET_DEFAULT: Final = ALPHABET_ASCII

    DEFAULT_SIZE: Final = 32

    DEFAULT_BLOCK_SIZE: Final = 1

    DEFAULT_BLOCK_DELIMITER: Final = "-"

    def __init__(
        self,
        alphabet: str = ALPHABET_DEFAULT,
        size: int = DEFAULT_SIZE,
        blocks: int = DEFAULT_BLOCK_SIZE,
        block_delimiter: str = DEFAULT_BLOCK_DELIMITER
    ):
        """Initializes a new `SecretToken` instance.

        Args:
            alphabet (str): The character alphabet to be used. Every individual
                character within the string is part of the alphabet.
            size (int): The number of alphabet characters in the created token.
            blocks (int): How many separate blocks the token string should
                be divided by. Keep as 1 to not have any blocks. The size
                must be divisible without remainder by the block size.
            block_delimiter (str): The delimiter string to be used to
                separate token blocks.

        Raises:
            ValueError: If the specified size cannot be evenly divided into
                the specified number of blocks.
        """
        if size % blocks != 0:
            raise ValueError(
                "The token's size must be divisible by its block size"
            )

        randomness = EntropySource.instance()
        self._token = block_delimiter.join(
            "".join(
                randomness.choose_one(alphabet) for _ in range(size // blocks)
            ) for _ in range(blocks)
        )

    def to_string(self) -> str:
        """Returns this token as a string.

        Returns:
            str: The string representation of this token.
        """
        return self._token

    def __repr__(self):
        return self.to_string()

    def __eq__(self, value):
        return self.to_string() == value.to_string()

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self.to_string())
