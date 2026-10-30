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
"""HTTP response and status code types."""

from typing import Annotated, TypeAlias, TypeVar
from dataclasses import dataclass


StatusCodeHTTP = Annotated[int, "must be in range [100, 599]"]


@dataclass
class ResponseStatusHTTP:
    """An HTTP response status that can be returned by web controllers."""

    code: StatusCodeHTTP

    message: str

    def __post_init__(self):
        if self.code < 100 or self.code > 599:
            raise ValueError(
                "ResponseStatusHTTP.code must be in range [100, 599] but "
                f"got {self.code!r}"
            )


T = TypeVar("T")

# pylint: disable=invalid-name
ResponseHTTP: TypeAlias = ResponseStatusHTTP | T
