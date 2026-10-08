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
"""Implementations for parcel validators."""

import json

from typing import Any, TypeVar, cast

import jsonschema.exceptions
import jsonschema.validators

from raven.fathom.base import ParcelValidator, ParcelValidationException
from raven.fathom.base import FileIOException
from raven.fathom.server.schemas import SchemaLoaderJSON


T = TypeVar("T")


class ParcelValidatorJSON(ParcelValidator):
    """Implementation of `ParcelValidator` for JSON-encoded parcels."""

    def __init__(self, schema_loader: SchemaLoaderJSON):
        """Initializes a new `ParcelValidatorJSON` instance.
        
        Args:
            schema_loader (SchemaLoaderJSON): The schema loader to use
                for loading the JSON schema.
        """
        self._schema_loader = schema_loader

    def validate(self, parcel: T) -> T:
        schema = self._load_schema()
        schema_validator = jsonschema.validators.validator_for(schema)
        try:
            schema_validator(schema).validate(cast(Any, parcel))
        except jsonschema.exceptions.ValidationError as error:
            raise ParcelValidationException(
               "JSON schema validation failed for parcel"
            ) from error

        return parcel

    def _load_schema(self):
        try:
            return self._schema_loader.load()
        except FileIOException as ex:
            raise ParcelValidationException(
                "Failed to load JSON schema from file"
            ) from ex
        except json.JSONDecodeError as error:
            raise ParcelValidationException(
                "Loaded JSON schema from file but failed to decode"
            ) from error
