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

from raven.fathom.base.system import InputPrompt


class SystemInputPromptMock(InputPrompt):
    """Mock implementation of `InputPrompt`."""

    def __init__(self):
        super().__init__()
        self.prompts = deque()
        self.inputs = deque()
        self.secret_reads: int = 0

    def read(self, prompt=None, default_value="", secret=False):
        if prompt is not None:
            self.prompts.append(prompt)

        if secret:
            self.secret_reads += 1

        if len(self.inputs) == 0:
            return default_value

        return self.inputs.popleft() or default_value
