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
"""Fathom server main entry point."""

from typing import TYPE_CHECKING

from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.base import Configuration
from raven.fathom.base import User, UserState
from raven.fathom.server.logging import Logger, LogLevel
from raven.fathom.server.http import ServerApplication, assign
from raven.fathom.server.http import ServerHTTP, HTTPServerStartException
from raven.fathom.server.defaults import SERVER_ROOT_PATH_V1
from raven.fathom.server.controllers import PublicController
from raven.fathom.server.controllers import InteractionController
from raven.fathom.server.staging import StagingArea
from raven.fathom.server.deployment import DeploymentSite
from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.config import ConfigurationManager
from raven.fathom.server.user_management import UserManager
from raven.fathom.server.updates import UpdateManager
from raven.fathom.server.updates import FailedApplicationUpdateException

if TYPE_CHECKING:
    from raven.fathom.server.cli.arguments import AppArgs


LOG = Logger.get()


class FathomServer(ServerApplication):
    """The Fathom server application."""

    def __init__(self):
        super().__init__()
        self.public = PublicController()
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
                current_version
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

    LOG.d("Disconnecting from database after setup procedures")
    db.disconnect()


def _apply_args_to_config(args: "AppArgs", config: Configuration):
    if args.port is not None:
        config[ServerConfiguration.SERVER.PORT_LISTEN] = args.port


def _setup_application(args: "AppArgs", config: Configuration):
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


def _run_fathom_server_application(args: "AppArgs", config: Configuration):
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


def _run_user_command(args: "AppArgs") -> int:
    db = DatabaseManager().get_database()
    should_disconnect = not db.is_connected()
    if should_disconnect:
        db.connect()

    try:
        manager = UserManager()
        if args.user_command == "create":
            user = User(
                identifier=args.user_identifier,
                name=args.user_name,
                is_admin=args.user_is_admin,
                state=UserState.ONBOARDING,
            )
            manager.create_user(user)
            role = "admin" if user.is_admin else "regular"
            LOG.i(
                "Created user '%s' (%s, %s).",
                user.identifier, role, user.state
            )
            return 0

        if args.user_command == "list":
            for user in manager.list_users():
                role = "admin" if user.is_admin else "regular"
                LOG.i(
                    "User: '%s'\tName: '%s'\tRole: '%s'\tState: '%s'",
                    user.identifier, user.name, role, user.state
                )
            return 0

        if args.user_command == "delete":
            manager.delete_user(
                User(identifier=args.user_identifier)
            )
            LOG.i("Deleted user '%s'.", args.user_identifier)
            return 0

        raise ValueError(f"Invalid user command '{args.user_command}'")
    finally:
        if should_disconnect and db.is_connected():
            db.disconnect()


def run(args: "AppArgs") -> int:
    """Runs the Fathom server application.

    Args:
        args (AppArgs): The application arguments to be used.

    Returns:
        int: The exit status code of the server.
    """
    app_mode = ApplicationContext.instance().get_application_mode()
    if app_mode == ApplicationMode.DEVELOPMENT:
        LOG.i("Running in a development environment")

    try:
        cm = ConfigurationManager()
        cm.load_configs(args)
        config = cm.get_server_config()
        _setup_application(args, config)
        if args.command == "user":
            return _run_user_command(args)

        return _run_fathom_server_application(args, config)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        LOG.e("Failed to run Fathom server")
        LOG.e(str(ex))
        LOG.d(str(ex), exc_info=True)
        return 1
