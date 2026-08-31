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
"""Fathom server CLI exit status code definitions."""

import enum


class ExitStatus(enum.IntEnum):
    """Enumeration of the Fathom server CLI exit status codes."""

    SUCCESS = 0

    FAILURE = 1

    INTERNAL_ERROR = 3

    UNKNOWN_ERROR = 126
