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
"""Formatters for tabular data."""

from typing import Any, Optional


class TableFormatter:
    """Formats tabular data as text.

    Provides a simple API to build a table with headers and rows, then format
    it as text. Columns are auto-sized based on content.

    Attributes:
        headers (List[str]): Column headers for the table.
        rows (List[List[str]]): Data rows, each a list of column values.
    """

    def __init__(self, title: Optional[str] = None):
        """Initializes a new `TableFormatter` instance.

        Args:
            title (str): Optional title to include at the top
                of formatted output.
        """
        self._title = title
        self._headers = []
        self._rows = []

    @property
    def title(self) -> Optional[str]:
        """The title of the table, if any, as a `str`."""
        return self._title

    def set_headers(self, *headers: str) -> "TableFormatter":
        """Sets the column headers for the table.

        Args:
            *headers: Column header names.

        Returns:
            TableFormatter: This `TableFormatter` instance.
        """
        self._headers = list(headers)
        return self

    def add_row(self, *values: Any) -> "TableFormatter":
        """Adds a row of data to the table.

        Args:
            *values: Column values for this row. Will be converted to strings.

        Returns:
            TableFormatter: This `TableFormatter` instance.
        """
        row = [str(value) for value in values]
        self._rows.append(row)
        return self

    def size(self) -> int:
        """Indicates the number of rows.

        Returns:
            int: The total number of rows that this table
                formatter currently has.
        """
        return len(self._rows)

    def get_formatted_text(self) -> str:
        """Formats the the row data as a single table.

        Returns:
            str: Formatted table as a multi-line string.
        """
        lines = []

        if self._title:
            lines.append(self._title)

        if not self._headers and not self._rows:
            return "\n".join(lines)

        if self._headers and self._rows:
            lines.extend(self._format_table())
        elif self._rows:
            lines.extend(self._format_rows())

        return "\n".join(lines)

    def _get_column_widths(self) -> list[int]:
        """Calculates the width needed for each column."""
        widths = [
            len(header) for header in self._headers
        ] if self._headers else []

        for row in self._rows:
            for i, value in enumerate(row):
                if i >= len(widths):
                    widths.append(0)

                widths[i] = max(widths[i], len(value))

        return widths

    def _format_table(self) -> list[str]:
        """Formats a table with headers and data rows as lines."""
        lines = []
        widths = self._get_column_widths()

        if self._headers:
            header_row = " | ".join(
                header.ljust(width)
                for header, width in zip(self._headers, widths)
            )
            lines.append(" | " + header_row)

            separator = "-+-".join("-" * width for width in widths)
            lines.append("-+-" + separator)

        for row in self._rows:
            data_row = " | ".join(
                value.ljust(width)
                for value, width in zip(row, widths)
            )
            lines.append(" | " + data_row)

        return lines

    def _format_rows(self) -> list[str]:
        """Formats rows without headers as lines using tab-separated format."""
        lines = []
        for row in self._rows:
            lines.append(" | " + "\t".join(row))

        return lines
