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
"""Unit tests for the url module."""

from pathlib import PurePath

from raven.fathom.base import URL, InvalidURLException
from raven.fathom.base import URLAuthority, URLQuery, URLUserAuthentication
from raven.fathom.base import File

from tests.unit import TestCase


class TestURL(TestCase):
    """Unit tests for the `URL` class."""

    def test_empty_url(self):
        url = URL()
        self.assertEqual(url.scheme, "")
        self.assertTrue(url.authority.is_empty())
        self.assertEqual(url.path, "")
        self.assertEqual(len(url.query), 0)
        self.assertEqual(url.fragment, "")
        self.assertIsNone(url.get_user_authentication())
        self.assertEqual(str(url), "")

    def test_url_parsing(self):
        url_string = (
            "https://user:passwd@example.com:8080"
            "/test/path?foo=bar&baz=data#frag"
        )
        url = URL(url_string)
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.authority.userinfo, "user:passwd")
        self.assertEqual(url.authority.hostname, "example.com")
        self.assertEqual(url.authority.port, 8080)
        self.assertEqual(url.path, "/test/path")
        self.assertEqual(url.query["foo"], "bar")
        self.assertEqual(url.query["baz"], "data")
        self.assertEqual(url.fragment, "frag")
        self.assertEqual(str(url), url_string)

    def test_url_query_str(self):
        query = URLQuery()
        query["a"] = "1"
        query["b"] = "2"
        self.assertIn(str(query), ["a=1&b=2", "b=2&a=1"])

    def test_url_authority_str(self):
        auth = URLAuthority(userinfo="user:pw", hostname="myhost", port=123)
        self.assertEqual(str(auth), "user:pw@myhost:123")
        auth = URLAuthority(hostname="myhost")
        self.assertEqual(str(auth), "myhost")
        auth = URLAuthority()
        self.assertEqual(str(auth), "")

    def test_properties(self):
        url = URL()
        url.scheme = "ftp"
        url.authority = URLAuthority(userinfo="u:p", hostname="host", port=21)
        url.path = "myfile"
        url.query = URLQuery()
        url.query["k"] = "v"
        url.fragment = "frag"
        self.assertEqual(url.scheme, "ftp")
        self.assertEqual(url.authority.hostname, "host")
        self.assertEqual(url.path, "/myfile")
        self.assertEqual(url.query["k"], "v")
        self.assertEqual(url.fragment, "frag")

    def test_user_authentication(self):
        url = URL("http://user:pw@host")
        auth = url.get_user_authentication()
        self.assertIsNotNone(auth)
        assert auth is not None
        self.assertEqual(auth.username, "user")
        self.assertEqual(auth.password, "pw")
        url.set_user_authentication(
            URLUserAuthentication("myuser", "mypasswd")
        )
        self.assertEqual(url.authority.userinfo, "myuser:mypasswd")
        auth2 = url.get_user_authentication()
        assert auth2 is not None
        self.assertEqual(auth2.username, "myuser")
        self.assertEqual(auth2.password, "mypasswd")

    def test_user_authentication_no_password(self):
        url = URL("http://user@host")
        auth = url.get_user_authentication()
        self.assertIsNotNone(auth)
        assert auth is not None
        self.assertEqual(auth.username, "user")
        self.assertEqual(auth.password, "")

    def test_from_path_object(self):
        path = PurePath("/tmp/dir/file.txt")
        url = URL(path)
        self.assertEqual(url.scheme, "file")
        self.assertEqual(url.path, "/tmp/dir/file.txt")
        self.assertEqual(str(url), "file:///tmp/dir/file.txt")

    def test_from_file_object(self):
        path = File("/C:/some/testing/dir/file.bin")
        url = URL(path)
        self.assertEqual(url.scheme, "file")
        self.assertEqual(File(url.path), path)
        expected_str = f"file://{path.path.as_posix()}"
        actual_str = str(url)
        self.assertEqual(expected_str, actual_str)

    def test_invalid_query_raises_exception(self):
        with self.assertRaises(InvalidURLException):
            URL("http://host/path?badquery")

        with self.assertRaises(InvalidURLException):
            URL("http://host/path?foo=bar=baz")

    def test_invalid_type_raises_exception(self):
        with self.assertRaises(TypeError):
            URL(123) # type: ignore

    def test_setters_type_check(self):
        url = URL()
        with self.assertRaises(TypeError):
            url.scheme = 123 # type: ignore
        with self.assertRaises(TypeError):
            url.authority = "not_authority" # type: ignore
        with self.assertRaises(TypeError):
            url.path = None # type: ignore
        with self.assertRaises(TypeError):
            url.query = {} # type: ignore
        with self.assertRaises(TypeError):
            url.fragment = None # type: ignore
        with self.assertRaises(TypeError):
            url.set_user_authentication(("user", "pw")) # type: ignore


if __name__ == "__main__":
    TestCase.run_tests()
