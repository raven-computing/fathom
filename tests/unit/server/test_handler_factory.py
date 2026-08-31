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
"""Unit tests for the HandlerFactory class."""

from raven.fathom.base import ClientRequest, Interaction

from raven.fathom.server.handlers.factory import HandlerFactory
from raven.fathom.server.handlers.server_info import ServerInfoHandler
from raven.fathom.server.handlers.deployment_intent import (
    DeploymentIntentHandler,
)
from raven.fathom.server.handlers.deployment_transaction import (
    DeploymentTransactionHandler,
)

from tests.unit import TestCase, TestFixture


class TestHandlerFactory(TestCase, TestFixture):
    """Unit tests for the `HandlerFactory` class."""

    def test_creates_server_info_handler_for_server_info_query(self):
        request = ClientRequest(Interaction.QUERY_SERVER_INFO)
        handler = HandlerFactory().create_action_handler_for(request)
        self.assertIsInstance(handler, ServerInfoHandler)

    def test_creates_deployment_intent_handler_for_request_deployment(self):
        request = ClientRequest(Interaction.REQUEST_DEPLOYMENT)
        handler = HandlerFactory().create_action_handler_for(request)
        self.assertIsInstance(handler, DeploymentIntentHandler)

    def test_creates_deployment_transaction_handler_for_deployment(self):
        request = ClientRequest(Interaction.TRANSACT_DEPLOYMENT)
        handler = HandlerFactory().create_action_handler_for(request)
        self.assertIsInstance(handler, DeploymentTransactionHandler)

    def test_returns_none_for_unrecognized_action(self):
        request = ClientRequest("unknown-action") # type: ignore
        handler = HandlerFactory().create_action_handler_for(request)
        self.assertIsNone(handler)


if __name__ == "__main__":
    TestCase.run_tests()
