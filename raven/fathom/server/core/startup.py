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
"""Server runtime setup and execution helpers."""

from typing import TYPE_CHECKING

from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.base import ClientAuthentication
from raven.fathom.base import Configuration
from raven.fathom.base import InputPrompt
from raven.fathom.server.core.config import ServerConfiguration
from raven.fathom.server.core.config import ConfigurationManager
from raven.fathom.server.controllers import InteractionController
from raven.fathom.server.controllers import PublicController
from raven.fathom.server.controllers import SignupController
from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.net.defaults import SERVER_ROOT_PATH_V1
from raven.fathom.server.deployment import DeploymentSite
from raven.fathom.server.net.http import assign
from raven.fathom.server.net.http import HTTPServerStartException
from raven.fathom.server.net.http import ServerApplication
from raven.fathom.server.net.http import ServerHTTP
from raven.fathom.server.core.logging import LogLevel, Logger
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.staging import StagingArea
from raven.fathom.server.updates import FailedApplicationUpdateException
from raven.fathom.server.updates import UpdateManager
from raven.fathom.server.user_management import SYSTEM_USER_IDENTIFIER
from raven.fathom.server.user_management import UserManager

if TYPE_CHECKING:
    from raven.fathom.server.cli.arguments import AppArgs


LOG = Logger.get()


class FathomServer(ServerApplication):
    """The Fathom server application."""

    def __init__(self):
        super().__init__()
        self.public = PublicController()
        self.user = SignupController()
        self.interact = InteractionController()

    def root_path(self):
        return SERVER_ROOT_PATH_V1


def _setup_database():
    db_manager = DatabaseManager()
    if not db_manager.locate_application_database():
        raise ValueError("Cannot locate DB")

    db_exists = db_manager.check_database_exists()
    db = db_manager.get_database()
    if LOG.level == LogLevel.DEBUG:
        db_manager.set_debug_loggging_enabled(True)

    LOG.i("Connecting to %s database", db.type_name())
    db.connect()
    if not db_exists:
        LOG.i("Creating database schema")
        db_manager.initialize_empty_database()


def _setup_filesystem(config: Configuration):
    staging_area = StagingArea(config)
    staging_area.create()

    deployment_area = DeploymentSite(config)
    deployment_area.create()


def _setup_post_update():
    db = DatabaseManager().get_database()
    update_manager = UpdateManager(db)
    if update_manager.application_update_detected():
        previous_version = update_manager.determine_previous_version()
        current_version = update_manager.determine_current_version()
        try:
            assert previous_version is not None
            update_manager.apply_post_update_procedures(
                previous_version,
                current_version,
            )
        except FailedApplicationUpdateException as ex:
            LOG.e("Failed to update application:")
            LOG.e(str(ex))
            raise

    elif update_manager.application_first_start_detected():
        try:
            update_manager.apply_post_installation_procedures()
        except FailedApplicationUpdateException as ex:
            LOG.e("Failed to apply post-installation procedures:")
            LOG.e(str(ex), exc_info=ex)
            raise


def _apply_args_to_config(args: "AppArgs", config: Configuration):
    if args.port is not None:
        config[ServerConfiguration.SERVER.PORT_LISTEN] = args.port


def setup_application(args: "AppArgs", config: Configuration):
    """Runs startup setup steps required before command execution."""
    try:
        _setup_database()
        _setup_filesystem(config)
        _setup_post_update()
        _apply_args_to_config(args, config)
    except Exception:
        LOG.e("An error occurred during application startup")
        raise


def _start_server(server: ServerHTTP):
    try:
        server.start()
    except HTTPServerStartException:
        LOG.e("Failed to start Fathom server")
        raise


def run_server_application(args: "AppArgs") -> int:
    """Starts and runs the HTTP server application."""
    config = ConfigurationManager().get_server_config()
    port = config[ServerConfiguration.SERVER.PORT_LISTEN]
    LOG.i("Starting Fathom server on port %d", port)
    server = assign(ServerHTTP(FathomServer(), config, args.ready_event))
    _start_server(server)
    app_mode = ApplicationContext.instance().get_application_mode()
    debug_mode_enabled = config[ServerConfiguration.SERVER.DEBUG_MODE_ENABLED]
    if app_mode == ApplicationMode.PRODUCTION and debug_mode_enabled:
        LOG.w(
            "The debug mode of the server is enabled. "
            "This is not suitable for a production environment."
        )

    server.run()
    LOG.i("Fathom server has been stopped")
    return server.status_code()


def confirm_system_privileges():
    """Asks for user credentials and validates system user privileges."""
    prompt = InputPrompt.instance()
    LOG.i("Authentication is required to perform this action")
    authentication = ClientAuthentication(
        username=prompt.read("User: "),
        password=prompt.read("Password: ", secret=True),
    )
    auth_result = UserAuthenticator().authenticate_system_user(authentication)
    if not auth_result.is_authenticated():
        raise ValueError("Incorrect username or password.")

    user_record = auth_result.user_record
    if user_record is None:
        raise ValueError("Authentication failed.")

    if str(user_record.identifier) != SYSTEM_USER_IDENTIFIER:
        raise ValueError(
            "Fathom system user authentication is required."
        )


def ensure_connected_to_database():
    """Ensures an active database connection for command operations."""
    db = DatabaseManager().get_database()
    if not db.is_connected():
        db.connect()


def require_server_setup():
    """Raises if server setup has not been completed yet."""
    ensure_connected_to_database()

    if UserManager(UserAuthenticator()).is_setup_complete():
        return

    raise ValueError(
        "The server has not been set up yet. Run 'fathom-server setup' first."
    )
