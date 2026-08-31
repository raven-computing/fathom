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
"""Integration tests for the crypt module."""

from raven.fathom.base import SecretToken

from tests.integration import TestCase


class TestSecretToken(TestCase):
    """Integration tests for the `SecretToken` class.

    This integration test case utilizes a real entropy source
    (the system default that should be injected when using the interface) as
    opposed to a mock object which may get used in unit tests.
    """

    def test_random_secret_tokens_are_not_equal(self):
        token_1 = SecretToken().to_string()
        token_2 = SecretToken().to_string()
        token_3 = SecretToken().to_string()
        token_4 = SecretToken().to_string()
        self.assertRegex(token_1, "^[a-zA-Z0-9]{32}$")
        self.assertRegex(token_2, "^[a-zA-Z0-9]{32}$")
        self.assertRegex(token_3, "^[a-zA-Z0-9]{32}$")
        self.assertRegex(token_4, "^[a-zA-Z0-9]{32}$")
        token_list = sorted(list(set([token_1, token_2, token_3, token_4])))
        self.assertEqual(
            token_list, sorted([token_1, token_2, token_3, token_4]),
            "Expected that four generated secret tokens have unequal value. "
            "This failure is likely a programming error but might indicate a "
            "problem with the underlying system's entropy source."
        )


if __name__ == "__main__":
    TestCase.run_tests()
