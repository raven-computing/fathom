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
"""Common command abstractions for client and server components."""

from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract base class for CLI command implementations.

    Attributes:
        name (str): The name of the command, as a str.
    """

    def __init__(self, name: str):
        """Initializes the command with the given name.

        Args:
            name (str): The name of the command.
        """
        self.name = name

    @abstractmethod
    def execute(self) -> int:
        """Executes this command and returns its operation exit status.

        Returns:
            int: The exit status code of the command execution.
        """

    def cancel(self):
        """Lifecycle hook for command cancellation.

        This method is called when the command execution is interrupted,
        for example, by a user pressing Ctrl+C. Concrete commands may override
        this method to implement custom cancellation logic. It is not called in
        case of an encountered exception during command execution.
        An implementation must not raise any exceptions.
        The default implementation does nothing.
        """
