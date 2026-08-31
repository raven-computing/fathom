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
"""Schema loaders."""

import json

from typing import Any

from raven.fathom.base import File


class SchemaLoaderJSON:
    """A loader for JSON schemas."""

    def __init__(self, schema_file: File):
        """Initializes a new `SchemaLoaderJSON` instance.

        Args:
            schema_file (File): The file that contains
                the JSON schema definition.
        """
        self._schema_file = schema_file

    def load(self) -> Any:
        """Loads the JSON schema.

        Returns:
            Any: An object that represents the deserialized JSON schema.

        Raises:
            FileIOException: If the schema file cannot be read.
            JSONDecodeError: If the JSON schema cannot be decoded.
        """
        schema = self._schema_file.read_all_text()
        return json.loads(schema)

    @staticmethod
    def for_request_schema() -> "SchemaLoaderJSON":
        """Returns a `SchemaLoaderJSON` object for loading the request schema.

        Returns:
            SchemaLoaderJSON: A schema loader for loading the
                client request schema used in a client-server-interaction.
        """
        base = File(__file__).get_parent_directory()
        schema_path = base / File("request-parcel-v1.schema.json")
        return SchemaLoaderJSON(schema_path)

    @staticmethod
    def for_response_schema() -> "SchemaLoaderJSON":
        """Returns a `SchemaLoaderJSON` object for loading the response schema.

        Returns:
            SchemaLoaderJSON: A schema loader for loading the
                server response schema used in a client-server-interaction.
        """
        base = File(__file__).get_parent_directory()
        schema_path = base / File("response-parcel-v1.schema.json")
        return SchemaLoaderJSON(schema_path)
