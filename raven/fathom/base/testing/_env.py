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
"""Provides an implementation of the `SystemEnvironment` interface which is
intended to be used for testing purposes.
"""

from pathlib import PurePath
from typing import Optional

from raven.fathom.base.system import SystemEnvironment, OperatingSystem
from raven.fathom.base._env import HostSystemEnvironment


class TestEnvironment(SystemEnvironment):
    """Implementation of `SystemEnvironment` which provides a test environment.

    Simulates a basic system environment for testing purposes, with a system
    user named 'User' and a UID of 1000.
    """

    def __init__(self):
        self.env_vars: dict[str, str] = {
            "HOME": "/home/user",
            "CWD": "/home/user",
        }
        self.operating_system: Optional[OperatingSystem] = None
        self.line_separator: Optional[str] = None
        self.text_encoding: str = "UTF-8"
        self.file_system_encoding: str = "UTF-8"

    def get_user_id(self):
        return 1000

    def get_user_name(self):
        return "User"

    def get_home_path(self):
        return PurePath(self.env_vars.get("HOME", "."))

    def get_current_working_directory(self):
        return PurePath(self.env_vars.get("CWD", "/"))

    def get_operating_system(self):
        if self.operating_system is not None:
            return self.operating_system

        return HostSystemEnvironment().get_operating_system()

    def get_line_separator(self):
        if self.line_separator is not None:
            return self.line_separator

        return HostSystemEnvironment().get_line_separator()

    def get_text_encoding(self):
        return self.text_encoding

    def get_file_system_encoding(self):
        return self.file_system_encoding

    def get_variable(self, name, default=None):
        return self.env_vars.get(name, default)


_UNSET = object()


class FunctionalityTestEnvironment(HostSystemEnvironment):
    """Implementation of `SystemEnvironment` which provides
    a test environment.

    This is intended to be used for functionality (end-to-end) testing, where
    the actual host system environment is utilized. However, it allows
    overriding certain aspects of the environment, such as the home directory,
    current working directory, and environment variables, to facilitate testing
    in real but more controlled conditions.
    """

    def __init__(self):
        self.home: PurePath = _UNSET # type: ignore
        self.cwd: PurePath = _UNSET # type: ignore
        self.env_vars: dict[str, str] = dict()

    def get_home_path(self):
        if self.home is _UNSET:
            return super().get_home_path()

        return self.home

    def get_current_working_directory(self):
        if self.cwd is _UNSET:
            return super().get_current_working_directory()

        return self.cwd

    def get_variable(self, name, default=None):
        if name == "HOME" and self.home is not _UNSET:
            return str(self.home)

        if name == "CWD" and self.cwd is not _UNSET:
            return str(self.cwd)

        value = self.env_vars.get(name)
        if value is not None:
            return value

        return super().get_variable(name, default)
