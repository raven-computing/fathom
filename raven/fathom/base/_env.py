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
"""Provides an implementation of the `SystemEnvironment` interface."""

import os
import sys
import platform
import locale
import pathlib

try:
    import pwd
except ImportError:
    pwd = None

from raven.fathom.base.system import SystemEnvironment, OperatingSystem


class HostSystemEnvironment(SystemEnvironment):
    """Implementation of `SystemEnvironment` which queries the actual host."""

    def get_user_id(self):
        return os.getuid() if hasattr(os, "getuid") else None # type: ignore

    def get_user_name(self):
        try:
            return os.getlogin() or None
        except OSError:
            if pwd is not None:
                if hasattr(pwd, "getpwuid") and hasattr(os, "getuid"):
                    # pylint: disable=no-member
                    entry = pwd.getpwuid(os.getuid()) # type: ignore
                    return entry.pw_name or None

            return os.environ.get("USER") or os.environ.get("LOGNAME") or None

    def get_home_path(self):
        home = os.environ.get("HOME")
        if home:
            return pathlib.PurePath(home)

        return None

    def get_current_working_directory(self):
        return pathlib.PurePath(os.getcwd())

    def get_operating_system(self):
        operating_system = platform.system()
        if operating_system == "Linux":
            return OperatingSystem.GNU_LINUX
        if operating_system == "Windows":
            return OperatingSystem.MS_WINDOWS
        if operating_system == "Android":
            return OperatingSystem.ANDROID
        if operating_system == "Darwin":
            return OperatingSystem.MAC_OS
        if operating_system == "iOS":
            return OperatingSystem.I_OS
        if operating_system == "iPadOS":
            return OperatingSystem.I_PAD_OS

        return OperatingSystem.OTHER

    def get_line_separator(self):
        return os.linesep

    def get_text_encoding(self):
        return locale.getpreferredencoding(False)

    def get_file_system_encoding(self):
        return sys.getfilesystemencoding()

    def get_variable(self, name, default=None):
        return os.environ.get(name, default)
