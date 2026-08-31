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
"""A Fathom documentation package."""

from raven.fathom.base import File
from raven.fathom.base import Package
from raven.fathom.base import PackageableResource
from raven.fathom.base import PackageableResourceCollection
from raven.fathom.client.documentation import DocsFile, DocumentationResource


class PackageableDocsFile(PackageableResource):
    """A `DocsFile` object as a `PackageableResource`."""

    def __init__(self, docs_file: DocsFile):
        """Initializes a new `PackageableDocsFile` instance.

        Args:
            docs_file (DocsFile): The `DocsFile` object to be wrapped
                as a `PackageableResource`.
        """
        super().__init__()
        self._docs_file = docs_file

    def get_name(self):
        return self._docs_file.name

    def get_data(self):
        return (
            bytes()
            if self._docs_file.path is None
            else File(self._docs_file.path)
        )


class DocumentationPackage(PackageableResourceCollection):
    """A `DocumentationResource` object as a `PackageableResourceCollection`.

    Adaptable to a `Package`.
    """

    def __init__(self, docs_resource: DocumentationResource):
        """Initializes a new `DocumentationPackage` instance.

        Args:
            docs_resource (DocumentationResource): The documentation resources
                to be wrapped as a `PackageableResourceCollection`.
        """
        super().__init__()
        self._docs_resource = docs_resource

    def get_resources(self):
        for resource in self._docs_resource:
            yield PackageableDocsFile(resource)

    def adapt(self) -> Package:
        """Adapts this `DocumentationPackage` to a generic `Package` object.

        Returns:
            Package: This documentation package as a `Package` object.
        """
        return Package(self)
