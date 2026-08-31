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
"""Application update management API."""

from typing import TYPE_CHECKING, Optional
from collections.abc import Generator

from raven.fathom.base import ApplicationContext, FileIOException
from raven.fathom.base import write_version_file
from raven.fathom.server.logging import Logger
from raven.fathom.server.version import Version
from raven.fathom.server.exceptions import FathomServerException
from raven.fathom.server.datastore.database import Database, DatabaseException
from raven.fathom.server.updates.procedure import (
    FailedUpdateProcedureException
)

if TYPE_CHECKING:
    from raven.fathom.server.datastore._schema_updates import (
        DatabaseSchemaUpdate
    )


LOG = Logger.get()


class FailedApplicationUpdateException(FathomServerException):
    """Raised by an `UpdateManager` object when an application update has
    failed or otherwise cannot be performed properly.
    """


class FailedDatabaseSchemaUpdateException(FailedApplicationUpdateException):
    """Raised by an `UpdateManager` object when an application update requires
    that the underlying database schema must be updated, but that update failed
    or otherwise cannot be performed properly.
    """


class UpdateManager:
    """Server application update manager.

    An `UpdateManager` object can be used to check the server application
    update state, i.e. whether the application was previously updated, and
    apply potential post-update procedures.

    This class is not MT-safe.
    """

    def __init__(self, database: Optional["Database"] = None):
        """Initializes a new `UpdateManager` instance.

        Args:
            database (Database): A database to check for applicable post-update
                procedures. May be `None` to not check any database.
        """
        self._database: Optional[Database] = database
        self._previous_version: Optional[Version] = None
        self._current_version: Optional[Version] = None

    def application_update_detected(self) -> bool:
        """Checks whether the application was previously updated.

        This method returns `True` only if the application version in the last
        known run was older than than the currently running detected version.

        Returns:
            bool: `True` if an application update was detected, `False` if
                no update was detected.
        """
        previous = self.determine_previous_version()
        if previous is None:
            return False

        current = self.determine_current_version()
        if previous > current:
            LOG.w(
                "The previously running application version (%s) is greater "
                "than the currently running version (%s). "
                "Downgrades are not supported.",
                previous, current
            )
            return False

        return previous < current

    def application_first_start_detected(self) -> bool:
        """Checks whether the application is being run for the first time.

        This method returns `True` if the application was never started
        before and was thus freshly installed, and `False` otherwise.

        Returns:
            bool: `True` if the application is being started for the
                first time, `False` if it has been started before.
        """
        return self.determine_previous_version() is None

    def determine_current_version(self) -> Version:
        """Determines the version of the currently running application.

        Returns:
            Version: The version object of the running application.
        """
        if self._current_version is None:
            self._current_version = Version.current()
            if self._current_version is None:
                LOG.w("Cannot determine current application version")
                raise FailedApplicationUpdateException(
                    "Failed to determine current version"
                )

        return self._current_version

    def determine_previous_version(self) -> Optional[Version]:
        """Determines the version of the previously run application.

        Returns:
            Version: The version object of the detected
                previous application version. May return `None` if
                the previous version cannot be determined, for example when the
                application was never started before.
        """
        if self._previous_version is None:
            self._previous_version = Version.previous()

        return self._previous_version

    def apply_post_installation_procedures(self):
        """Applies post-installation procedures after a fresh installation.

        This method should be called when the application is being run for the
        first time and is used to perform any necessary setup tasks.

        Raises:
            FailedApplicationUpdateException: If the post-installation
                procedures fail.
        """
        LOG.i("Applying post-installation procedures")
        self._update_version_file()
        LOG.i("Post-installation procedures completed successfully")

    def apply_post_update_procedures(
        self,
        previous_version: Version,
        current_version: Version
    ):
        """Applies post-update procedures after an application update.

        Args:
            previous_version (Version): The previously installed version.
            current_version (Version): The current version, which was just
                installed as part of the underlying occurred update.

        Raises:
            FailedApplicationUpdateException: If the post-update
                procedures fail.
        """
        LOG.i(
            "Applying post-update procedures from version %s to %s",
            previous_version, current_version
        )
        if self._database is not None:
            LOG.i("Updating database schema")
            self._try_update_database_schema(previous_version, current_version)

        self._update_version_file()
        LOG.i("Post-update procedures completed successfully")

    def _update_version_file(self):
        try:
            write_version_file(
                ApplicationContext.instance().get_working_directory(),
                self.determine_current_version()
            )
            self._previous_version = None # Invalidate
        except FileIOException as ex:
            raise FailedApplicationUpdateException(
                "Failed to update version file"
            ) from ex

    def _try_update_database_schema(
        self,
        previous_version: Version,
        current_version: Version
    ):
        assert self._database is not None
        try:
            self._update_database_schema(previous_version, current_version)
        except FailedUpdateProcedureException as ex:
            raise FailedDatabaseSchemaUpdateException(
                "Failed to update database schema"
            ) from ex

    def _update_database_schema(
        self,
        previous_version: Version,
        current_version: Version
    ):
        assert self._database is not None
        db_schema_updates = self._filter_applicable(
            self._database.get_schema().get_update_procedures(),
            previous_version,
            current_version
        )
        self._apply_database_schema_update(db_schema_updates)

    def _apply_database_schema_update(
        self,
        update_procedures: Generator["DatabaseSchemaUpdate"]
    ):
        assert self._database is not None
        try:
            with self._database:
                for schema_update in update_procedures:
                    schema_update.use_database(self._database)
                    schema_update.apply()
        except DatabaseException as ex:
            raise FailedUpdateProcedureException(
                "Failed to apply database schema update"
            ) from ex

    def _filter_applicable(
        self,
        procedures: Generator["DatabaseSchemaUpdate"],
        previous_version: Version,
        current_version: Version
    ) -> Generator["DatabaseSchemaUpdate"]:
        return (
            update for update in procedures
            if previous_version < update.target_version <= current_version
        )
