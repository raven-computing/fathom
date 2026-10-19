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
"""Implementation of the `InputPrompt` interface providing mock
inputs and prompts.
"""

from collections import deque
from typing import Optional, Sequence

from raven.fathom.base.system import InputPrompt, InputPromptValidator


class SystemInputPromptMock(InputPrompt):
    """Mock implementation of `InputPrompt`."""

    def __init__(self):
        super().__init__()
        self.prompts = deque()
        self.inputs = deque()
        self.secret_reads: int = 0

    def read(
        self,
        prompt: Optional[str] = None,
        default_value: str = "",
        secret: bool = False,
        validator: Optional[InputPromptValidator] = None
    ) -> str:
        while True:
            if prompt is not None:
                self.prompts.append(prompt)

            if secret:
                self.secret_reads += 1

            if len(self.inputs) == 0:
                result = default_value
            else:
                result = self.inputs.popleft() or default_value

            if validator is not None:
                if validator(result):
                    return result
            else:
                return result

    def select(
        self,
        options: Sequence[str],
        prompt: Optional[str] = None,
        default_value: Optional[str] = None
    ) -> str:
        if len(options) == 0:
            raise ValueError("The options sequence must not be empty")

        while True:
            if prompt is not None:
                self.prompts.append(prompt)

            if len(self.inputs) == 0 and default_value is not None:
                return default_value

            result = self.inputs.popleft()
            try:
                item_index = int(result)
                if 1 <= item_index <= len(options):
                    return options[item_index - 1]

            except ValueError:
                pass

            if result in options:
                return result
