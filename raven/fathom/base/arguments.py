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
"""Provides a subclass of `argparse.ArgumentParser` for custom command line
argument handling in both the Fathom client and server.
"""

import argparse


_HELP_OUTPUT_WIDTH = 100


class _HelpFormatter(argparse.HelpFormatter):

    def __init__(self, prog):
        super().__init__(prog, width=_HELP_OUTPUT_WIDTH)

    def _format_action(self, action):
        return super()._format_action(action) + "\n"

    def add_arguments(self, actions):
        regular_actions = []
        help_actions = []
        for action in actions:
            options = action.option_strings
            if "-?" in options or "--help" in options:
                help_actions.append(action)
            else:
                regular_actions.append(action)

        super().add_arguments(regular_actions + help_actions)


class _VersionOptAction(argparse.Action):

    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        namespace.version = True
        namespace.version_short = option_string == "-#"


class ArgumentParser(argparse.ArgumentParser):
    """Subclass of `argparse.ArgumentParser` that
    adds Fathom-specific behaviour.
    """

    def __init__(self, *args, **kwargs):
        add_custom_help = kwargs.pop("add_help", True)
        kwargs["add_help"] = False # Disable builtin help
        if "formatter_class" not in kwargs:
            kwargs["formatter_class"] = _HelpFormatter

        super().__init__(*args, **kwargs)

        if add_custom_help:
            self.add_argument(
                "-?",
                "--help",
                action="help",
                help="Show this help message and then exit.",
            )

    def add_version_argument(self):
        """Adds handling for the '-#|--version' option."""
        self.add_argument(
            "-#",
            "--version",
            action=_VersionOptAction,
            default=False,
            help="Show program version information and then exit.",
        )
