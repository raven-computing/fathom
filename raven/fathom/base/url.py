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
"""Uniform Resource Locator (URL) objects."""

from io import StringIO
from os import PathLike, fspath
from dataclasses import dataclass, field
from urllib.parse import urlparse
from pathlib import PurePath
from typing import Optional, Union, NamedTuple, Final

from raven.fathom.base.typing import TypeCheck
from raven.fathom.base.system import SystemEnvironment
from raven.fathom.base.file import File

# pylint: disable=consider-using-f-string


class InvalidURLException(Exception):
    """Raised when an invalid URL is encountered."""


class URLUserAuthentication(NamedTuple):
    """A named tuple representing user authentication information for a URL.

    This type of data is commonly used in the userinfo component part of URLs.
    Please note that the usage of the userinfo URL field for user
    authentication is officially deprecated and discouraged. Refer to RFC 3986
    for more information.
    """

    username: str

    password: str


@dataclass
class URLAuthority:
    """The authority component part of a URL."""

    userinfo: str = field(default="")

    hostname: str = field(default="")

    port: Optional[int] = field(default=None)

    def is_empty(self) -> bool:
        """Indicates whether this URL authority object is empty.

        An authority object is empty if it has no userinfo, hostname, and port.

        Returns:
            bool: `True` if this authority object is empty, `False` otherwise.
        """
        return not (self.userinfo or self.hostname or self.port)

    def __str__(self):
        hostname = (
            "{sep}{hostname}".format(
                sep="@" if self.userinfo else "",
                hostname=self.hostname or "",
            )
        )
        port = (
            "{sep}{port}".format(
                sep=":" if (hostname and self.port) else "",
                port=self.port or "",
            )
        )
        return "{userinfo}{hostname}{port}".format(
            userinfo=self.userinfo,
            hostname=hostname,
            port=port,
        )


class URLQuery(dict):
    """The query component part of a URL."""

    def __str__(self):
        buffer = StringIO()
        for key, value in self.items():
            if buffer.tell() > 0:
                buffer.write("&")

            buffer.write(key)
            buffer.write("=")
            buffer.write(value)

        return buffer.getvalue()


class URL:
    r"""A Uniform Resource Locator (URL).

    Represents the location of a physical or abstract resource.

    The following is an example URL and its component parts:

    ```text

         foo://example.com:1234/some/test/path?name=hello#my-fragment
         \_/   \______________/\_____________/ \________/ \_________/
          |           |               |             |          |
       scheme     authority          path         query     fragment

    ```

    The authority component part is further divided into:

    ```text
         userinfo@hostname:port
         \_______/\______/\___/
            |        |      |
         userinfo hostname port
    ```

    URL objects are mutable.
    """

    # Shortcut for URLAuthority type
    Authority: Final = URLAuthority  # pylint: disable=invalid-name

    def __init__(self, specifier: Optional[Union[str, PathLike]] = None):
        """Initializes a new URL instance.

        If the specifier is `None`, then the created URL object will be empty.
        If the specifier is used, it must represent a valid URL string,
        which is then parsed by this initializer.

        Args:
            specifier (str): An optional URL specifier, as a str.
                May be `None`.

        Raises:
            InvalidURLException: If the specified URL is invalid.
        """
        self._scheme = ""
        self._authority = URLAuthority()
        self._path = ""
        self._query = URLQuery()
        self._fragment = ""
        if specifier is not None:
            if isinstance(specifier, str):
                self._parse_and_fill(specifier)
            elif isinstance(specifier, PathLike):
                self._from_path(specifier)
            else:
                raise TypeError(
                    "Invalid argument: Expected None, str or PathLike "
                    f"but found {type(specifier)}"
                )

    @property
    def scheme(self) -> str:
        """The scheme component part of this URL.

        A returned string does not include the delimiting '://' characters.
        Is an empty `str` if no scheme is present in this URL.
        """
        return self._scheme

    @scheme.setter
    def scheme(self, value: str):
        TypeCheck.require_prop(value, str, "scheme")
        self._scheme = value

    @property
    def authority(self) -> URLAuthority:
        """The authority component part of this URL.

        Is an empty `Authority` object if no authority is present.
        """
        return self._authority

    @authority.setter
    def authority(self, value: URLAuthority):
        TypeCheck.require_prop(value, URLAuthority, "authority")
        self._authority = value

    @property
    def path(self) -> str:
        """The path component part of this URL.

        Is an empty `str` if no path is present.
        """
        return self._path

    @path.setter
    def path(self, value: str):
        TypeCheck.require_prop(value, str, "path")
        if not value.startswith("/"):
            value = "/" + value

        self._path = value

    @property
    def query(self) -> URLQuery:
        """The query component part of this URL.

        Is an empty `Query` object if no query is present.
        """
        return self._query

    @query.setter
    def query(self, value: URLQuery):
        TypeCheck.require_prop(value, URLQuery, "query")
        self._query = value

    @property
    def fragment(self) -> str:
        """The fragment component part of this URL.

        Is an empty `str` if no fragment is present.
        """
        return self._fragment

    @fragment.setter
    def fragment(self, value: str):
        TypeCheck.require_prop(value, str, "fragment")
        self._fragment = value

    def get_user_authentication(self) -> Optional[URLUserAuthentication]:
        """The user authentication information of this URL.

        Can be used when the userinfo component part denotes a
        username-password combination. The returned named tuple is mutable but
        changes to it are not reflected by this URL object.
        Use `set_user_authentication()` to set those credentials to
        this object.

        Please note that the usage of the userinfo URL field for user
        authentication is discouraged.

        Returns:
            URLUserAuthentication: A named tuple with the username and
                password, or `None` if no user authentication is present.
        """
        if not self.authority.userinfo:
            return None

        userinfo = self.authority.userinfo.split(":", maxsplit=1)
        if len(userinfo) == 1:
            return URLUserAuthentication(username=userinfo[0], password="")

        if len(userinfo) == 2:
            return URLUserAuthentication(
                username=userinfo[0], password=userinfo[1]
            )

        return None

    def set_user_authentication(self, authentication: URLUserAuthentication):
        """Sets the user authentication information of this URL.

        This will override any previously set userinfo component part data.

        Please note that the usage of the userinfo URL field for
        user authentication is discouraged.

        Args:
            authentication (URLUserAuthentication): A named tuple with
                username and password.
        """
        TypeCheck.require_arg(authentication, URLUserAuthentication)
        self.authority.userinfo = (
            f"{authentication.username}:{authentication.password}"
        )

    def __str__(self):
        return (
            "{scheme}{scheme_sep}{authority}{path}"
            "{query_sep}{query}{frag_sep}{fragment}"
        ).format(
            scheme=self.scheme or "",
            scheme_sep="://" if self.scheme else "",
            authority=self.authority or "",
            path=self.path or "",
            query_sep="?" if self.query else "",
            query=self.query or "",
            frag_sep="#" if self.fragment else "",
            fragment=self.fragment or "",
        )

    def _parse_and_fill(self, specifier):
        url = urlparse(specifier)
        self._scheme = url.scheme
        self._fill_authority_obj(url)
        self._path = url.path
        self._fill_query_obj(url.query)
        self._fragment = url.fragment

    def _from_path(self, path):
        if isinstance(path, PurePath):
            path = path.as_posix()
        elif isinstance(path, File):
            path = path.path.as_posix()
        else:
            path = fspath(path)
            if isinstance(path, bytes):
                path = path.decode(
                    SystemEnvironment.instance().get_file_system_encoding()
                )

        self._scheme = "file"
        self._path = str(path)

    def _fill_authority_obj(self, url):
        userinfo, found, _ = url.netloc.rpartition('@')
        self._authority.userinfo = userinfo if found else ""
        self._authority.hostname = url.hostname
        self._authority.port = url.port

    def _fill_query_obj(self, query):
        if not query:
            return

        pairs = query.split("&")
        for pair in pairs:
            if "=" not in pair:
                raise InvalidURLException(
                    f"Malformed URL query component: '{query}'"
                )

            components = pair.split("=")
            if len(components) != 2:
                raise InvalidURLException(
                    f"Malformed URL query component: '{query}'"
                )

            key = components[0]
            value = components[1]
            self._query[key] = value
