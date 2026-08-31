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
"""Unit tests for the time module."""

from datetime import datetime, timezone

from raven.fathom.base import ConstantClock

from tests.unit import TestCase


class TestConstantClock(TestCase):
    """Tests for the `ConstantClock` class."""

    def test_constant_clock_always_returns_the_same_time(self):
        constant_time = datetime(
            year=2024, month=4, day=5,
            hour=13, minute=14, second=15, microsecond=16,
            tzinfo=timezone.utc
        )
        clock = ConstantClock(constant_time)
        for _ in range(50):
            self.assertEqual(clock.current_time(), constant_time)


if __name__ == "__main__":
    TestCase.run_tests()
