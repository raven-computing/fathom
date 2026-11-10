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
"""Unit tests for database schema verification."""

from raven.fathom.server.datastore._schema_verification import _Result

from tests.unit import TestCase


class TestSchemaVerification(TestCase):
    """Tests for schema verification results."""

    def test_to_string_describes_schema_mismatches(self):
        result = _Result(
            ok=False,
            missing_tables=["users"],
            missing_columns=["users.email"],
            extra_columns=["users.old_field"],
        )

        string = result.to_string()

        self.assertIn("missing tables", string.lower())
        self.assertIn("users", string)
        self.assertIn("missing columns", string.lower())
        self.assertIn("email", string)
        self.assertIn("extra columns", string.lower())
        self.assertIn("old_field", string)


if __name__ == "__main__":
    TestCase.run_tests()
