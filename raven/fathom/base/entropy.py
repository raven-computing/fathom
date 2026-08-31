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
"""Declares an interface to obtain data points based on a source of entropy."""

from abc import abstractmethod
from typing import TypeVar, Sequence

from raven.fathom.base.typing import Interface
from raven.fathom.base.decorators import inject


T = TypeVar("T")


@inject
class EntropySource(Interface):
    """A source of entropy.

    This interface establishes a contract for entropy sources, which are used
    to generate data of a certain pattern. The pattern does not necessarily
    have to be strictly defined, it can be a vague generalised description.
    Most notably, a prominent implementation would be to provide access to
    random data, that is, the specific data that such an entropy source
    generates may not be predictable by a user as it does not follow any
    specific recognizable pattern, it is random, where the actual randomness is
    provided by the entropy source. In general terms, an entropy source that
    produces random data points is said to have high entropy, while a source
    that always produces perfectly predictable data points is said to have
    zero entropy.

    Implementations must indicate whether the source is suitable for
    cryptographic use via the `is_random()` method.
    """

    @abstractmethod
    def get_bytes(self, count: int) -> bytes:
        """Obtains a sequence of bytes from this entropy source.

        Args:
            count (int): The quantity of bytes to return.

        Returns:
            bytes: A `bytes` object of length `count` containing bytes obtained
                from this entropy source.
        """

    @abstractmethod
    def get_next_int32(self) -> int:
        """Obtains the next 32-bit integer number from this entropy source.

        The returned number is composed of 32 bits obtained from this source.

        Returns:
            int: The next 32-bit integer number of this source.
        """

    @abstractmethod
    def choose_one(self, sequence: Sequence[T]) -> T:
        """Picks one element out of the given non-empty sequence.

        Args:
            sequence (Sequence): The sequence of elements to choose from.

        Returns:
            T: One element from the given sequence.
        """

    @abstractmethod
    def is_random(self) -> bool:
        """Indicates whether this entropy source produces truly random data.

        The specification of true randomness refers to the possible safe
        application of an entropy source for cryptographic purposes, where
        pseudo-random outcomes are inappropriate. Thus, if this entropy source
        prodcues pseudo-random outcomes, this method must return `False`.

        Returns:
            bool: `True` if this entropy source can be safely used in places
                where cryptographically strong randomness is required,
                `False` otherwise.
        """
