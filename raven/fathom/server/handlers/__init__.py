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
"""Server interaction handlers.

An `ActionHandler` is used to handle a specific `Interaction` that is requested
by a client and produce the corresponding server response. A handler
communicates with the domain layer of the application and delegates individual
domain-specific tasks to the appropriate domain objects.

The `HandlerFactory` should be used to create the appropriate `ActionHandler`
for a given client request.
"""

from .handler import ActionHandler
from .factory import HandlerFactory
