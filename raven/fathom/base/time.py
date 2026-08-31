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
"""Common time-related utilities."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class Clock(ABC):
    """A source of time measurement.

    This class is used to abstract away the retrieval of the current time.
    Primarily useful for testing purposes.
    """

    @abstractmethod
    def current_time(self) -> datetime:
        """Returns the current time as measured by this clock at
        the time this method is called.

        The `datetime` object returned by this method
        uses the UTC+00:00 timezone.

        Returns:
            datetime: The current time in UTC.
        """


class SystemClock(Clock):
    """Implementation of `Clock` using the underlying system clock."""

    def current_time(self):
        return datetime.now(timezone.utc)


class ConstantClock(Clock):
    """Implementation of `Clock` which always returns the
    same constant time."""

    def __init__(self, const_time: datetime):
        """Initializes a new `ConstantClock` for the specified time.

        Ensure the provided time is in UTC.

        Args:
            const_time (datetime): The constant time that the clock
                should always measure.
        """
        super().__init__()
        self._const_time = const_time.replace(tzinfo=timezone.utc)

    def current_time(self):
        return self._const_time
