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
"""The Fathom application. This setup.py handles all components."""

import os
import sys

from setuptools import setup, find_namespace_packages


COMPONENT_ROOT = os.path.abspath(os.path.dirname(__file__))


with open(os.path.join(COMPONENT_ROOT, "pypi.md"), encoding="UTF-8") as f:
    README = f.read()

with open(os.path.join(COMPONENT_ROOT, "VERSION"), encoding="UTF-8") as f:
    VERSION = f.read()


build_target = os.environ.get("FATHOM_BUILD_TARGET")
if build_target is None:
    print("Error: Missing build target argument")
    sys.exit(1)

PACKAGE_NAME = f"raven-fathom-{build_target}"

install_requires = []  # Dependencies common to all packages
entry_points = {}
exclude_namespaces = []

if build_target == "base":
    exclude_namespaces.extend([
        "raven.fathom.client", "raven.fathom.client.*",
        "raven.fathom.server", "raven.fathom.server.*",
    ])
elif build_target == "client":
    exclude_namespaces.extend([
        "raven.fathom.base", "raven.fathom.base.*",
        "raven.fathom.server", "raven.fathom.server.*",
    ])
    install_requires.extend([
        "raven-fathom-base>=0.0.1",
    ])
    entry_points["console_scripts"] = [
        "fathom=raven.fathom.client.cli.application:main",
    ]
elif build_target == "server":
    exclude_namespaces.extend([
        "raven.fathom.base", "raven.fathom.base.*",
        "raven.fathom.client", "raven.fathom.client.*",
    ])
    install_requires.extend([
        "raven-fathom-base>=0.0.1",
        "CherryPy>=18.0.0",
        "jsonschema==4.26.0",
        "peewee==4.4.0",
    ])
    entry_points["console_scripts"] = [
        "fathom-server=raven.fathom.server:main"
    ]
else:
    print(f"Error: Unknown build target argument: '{build_target}'")
    sys.exit(1)

namespace_packages = find_namespace_packages(
    include=("raven.*",),
    exclude=exclude_namespaces
)

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description="Manage the Release of Documentation",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://raven-computing.com",
    author="Phil Gaiser",
    author_email="phil.gaiser@raven-computing.com",
    license="Apache-2.0",
    packages=namespace_packages,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    entry_points=entry_points,
    python_requires=">=3.11",
    install_requires=install_requires,
)
