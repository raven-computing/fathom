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
"""Contains a declaration of a base class for interface types."""

from abc import ABC


class InjectableInterfaceType(ABC):
    """An abstract base class for injectable types.

    Is meant to be used with interface classes whose implementations
    are provided via dependency injection.

    Implementation note:  
    This class is used so that the `instance()` method resides in a module
    that can be tracked safely and unambiguously by the injection machinery.
    This is necessary to make the introspection work when determining the
    calling context of an injection.
    """

    @classmethod
    def instance(cls, *args, **kwargs):
        """Obtains an instance of a class implementing the interface.

        Returns:
            A concrete instance of the injectable interface class.
        """
        return cls(*args, **kwargs)
