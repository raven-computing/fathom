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
"""Database schema handling.

Provides an implementation of the `DatabaseSchema` ABC.
"""

import inspect
import importlib
import pkgutil

from raven.fathom.server import models
from raven.fathom.server.datastore.orm import Model
from raven.fathom.server.datastore.database import DatabaseSchema
from raven.fathom.server.datastore._schema_updates import DatabaseSchemaUpdate


class DatabaseSchemaImpl(DatabaseSchema):
    """Implementation of `DatabaseSchema`."""

    def get_models(self):
        model_classes = []
        package_path = models.__path__
        package_name = models.__name__

        mods = pkgutil.iter_modules(package_path)
        for _, module_name, is_pkg in mods:
            if is_pkg:
                continue

            module = importlib.import_module(f"{package_name}.{module_name}")
            members = [
                (name, obj)
                for name, obj in inspect.getmembers(module, inspect.isclass)
                if obj.__module__ == module.__name__
            ]
            for _, obj in members:
                if issubclass(obj, Model) and obj is not Model:
                    if obj not in model_classes:
                        model_classes.append(obj)

        return model_classes

    def get_update_procedures(self):
        return DatabaseSchemaUpdate.get_all_procedures()
