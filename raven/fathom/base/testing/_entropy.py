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
"""Implementation of the `EntropySource` interface providing
a mock for testing.
"""

from raven.fathom.base.entropy import EntropySource


class EntropySourceMock(EntropySource):
    """Completely deterministic implementation of `EntropySource` .

    This mock implementation always produces predictable outcomes.
    It implements a zero-entropy source.

    Attributes:
        next_int32 (int): The mock value returned by `get_next_int32()`.
        choose_sequence_index (int): The index of the sequence element to
            be chosen by `choose_one()`.
    """

    def __init__(self):
        self.next_byte: bytes = b"\x41"
        self.next_int32: int = 1
        self.choose_sequence_index: int = 0

    def get_bytes(self, count):
        return self.next_byte * count

    def get_next_int32(self):
        return self.next_int32

    def choose_one(self, sequence):
        return sequence[self.choose_sequence_index]

    def is_random(self):
        return False
