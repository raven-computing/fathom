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
"""Contains shared classes representing concepts related to software projects
for which documentation artifacts can be built and published.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectVersion:
    """Represents the concept of versioning within a software project.

    Attributes:
        identifier (str): The version identifier.
        is_latest (bool): Whether the version is the latest
            published version of the project.
    """

    identifier: str

    is_latest: bool = field(default=False)

    def __str__(self):
        return f"v{self.identifier}"


@dataclass
class Project:
    """Represents a software project for which a Fathom deployment
    can be carried out.

    Attributes:
        identifier (str): A unique project identifier.
        name (str): The name of the project.
        description (str): A short human-readable description of the project.
        version (ProjectVersion): The version applicable to
            the project instance.
        domain (str): The domain under which the project is deployed.
        assets (str): The path to the project assets.
    """

    identifier: str

    name: str = ""

    description: str = ""

    version: Optional[ProjectVersion] = None

    domain: str = ""

    assets: str = ""

    def __str__(self):
        return f"{self.identifier} {self.version}"
