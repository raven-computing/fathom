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
"""Provides an implementation of the `EntropySource` interface."""

import random

from raven.fathom.base.entropy import EntropySource


class SystemRandomEntropySource(EntropySource):
    """Implementation of `EntropySource` which queries the operating system.

    This implementation uses a strong random number generator provided by the
    underlying system and is thus suitable to be used for
    cryptographic purposes. Implements a high-entropy source.
    """

    def __init__(self):
        self._random = random.SystemRandom()

    def get_bytes(self, count):
        return self._random.randbytes(count)

    def get_next_int32(self):
        return self._random.getrandbits(32)

    def choose_one(self, sequence):
        return self._random.choice(sequence)

    def is_random(self):
        return True
