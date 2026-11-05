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

from typing import Optional, Sequence, Final

from raven.fathom.base.system import InputPrompt, InputPromptValidator
from raven.fathom.base.system import InputReadException
from raven.fathom.base.logging import LogFormatterCLI


_MAX_READ_ATTEMPTS: Final[int] = 1024


class SystemInputPromptStdIn(InputPrompt):
    """Implements the `InputPrompt` interface via the standard input stream."""

    def __init__(self):
        super().__init__()
        self.stream_in = sys.stdin
        self.stream_out = sys.stdout

    def read(
        self,
        prompt: Optional[str] = None,
        default_value: str = "",
        secret: bool = False,
        validator: Optional[InputPromptValidator] = None
    ) -> str:
        attempts = 0
        while attempts <= _MAX_READ_ATTEMPTS:
            if prompt is not None:
                print(
                    LogFormatterCLI.format_message_info(prompt),
                    file=self.stream_out,
                    end="",
                    flush=True,
                )

            try:
                if secret and self._can_read_secret():
                    user_input = getpass.getpass("", stream=self.stream_out)
                else:
                    user_input = self.stream_in.readline()
                attempts += 1
            except KeyboardInterrupt:
                if prompt is not None:
                    print("", file=self.stream_out, flush=True)
                raise
            except EOFError as error:
                raise InputReadException(f"Failed to read input: {error}")

            if not user_input:
                result = default_value
            else:
                result = user_input.rstrip("\n") or default_value

            if validator is not None:
                if validator(result):
                    return result
            else:
                return result

        raise InputReadException("Maximum read attempts exceeded")

    def select(
        self,
        options: Sequence[str],
        prompt: Optional[str] = None,
        default_value: Optional[str] = None
    ) -> str:
        if len(options) == 0:
            raise ValueError("The options sequence must not be empty")

        print("", file=self.stream_out)
        for item_number, option in enumerate(options, 1):
            print(f"[{item_number}] {option}", file=self.stream_out)

        print("", file=self.stream_out)

        attempts = 0
        user_input = ""
        while not user_input:
            if attempts > _MAX_READ_ATTEMPTS:
                raise InputReadException("Maximum read attempts exceeded")

            print(
                LogFormatterCLI.format_message_info(prompt or ""),
                file=self.stream_out,
                end="",
                flush=True,
            )
            try:
                user_input = self.stream_in.readline()
            except KeyboardInterrupt:
                if prompt is not None:
                    print("", file=self.stream_out, flush=True)
                raise
            except EOFError as error:
                raise InputReadException(
                    f"Failed to read selection input: {error}"
                )

            attempts += 1
            user_input = user_input.rstrip("\n")

            if not user_input and default_value is not None:
                return default_value

            try:
                item_index = int(user_input)
                if 1 <= item_index <= len(options):
                    return options[item_index - 1]
            except ValueError:
                pass

            if user_input not in options:
                user_input = ""

        return user_input

    def _can_read_secret(self):
        if self.stream_in is not sys.stdin:
            return False

        is_tty = getattr(self.stream_in, "isatty", None)
        if is_tty is None or callable(is_tty) is False:
            return False

        return bool(is_tty())
