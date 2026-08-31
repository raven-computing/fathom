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
"""Input gathering from the user.

Implements the `InputPrompt` interface.
"""

import sys
import getpass

from raven.fathom.base.system import InputPrompt, InputReadException
from raven.fathom.base.logging import LogFormatterCLI


class SystemInputPromptStdIn(InputPrompt):
    """Implements the `InputPrompt` interface via the standard input stream."""

    def __init__(self):
        super().__init__()
        self.stream_in = sys.stdin
        self.stream_out = sys.stdout

    def read(self, prompt=None, default_value="", secret=False):
        if prompt is not None:
            print(
                LogFormatterCLI.format_message_info(prompt),
                file=self.stream_out,
                end="",
                flush=True,
            )

        try:
            if secret:
                user_input = getpass.getpass("")
            else:
                user_input = self.stream_in.readline()
        except KeyboardInterrupt:
            if prompt is not None:
                print("", file=self.stream_out, flush=True)

            raise
        except EOFError as error:
            raise InputReadException(f"Failed to read input: {error}")

        if not user_input:
            return default_value

        return user_input.rstrip("\n") or default_value
