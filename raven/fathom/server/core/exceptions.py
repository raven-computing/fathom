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
"""Fathom server exceptions."""

from raven.fathom.base import FathomException


class FathomServerException(FathomException):
    """Base exception class to be used only by the **server** component
    of Fathom.
    """


class InternalException(FathomServerException):
    """Base exception class for internal infrastructure-related errors.

    Unhandled exceptions of this type will cause an active transaction that
    is bound to an underlying request context to be rolled back.
    """


class DomainException(FathomServerException):
    """Base exception class to be used by code in the domain layer."""
