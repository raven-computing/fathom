--
-- Baseline datastore fixture for functionality tests.
-- This file contains both the DDL statements and some example data to set up a database
-- that represents a state from the initial stable released version. This is used to test
-- database schema migrations to a later version to ensure that the initial state can
-- always safely be migrated.
--

CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "identifier" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "password" VARCHAR(255),
    "role" VARCHAR(255) NOT NULL,
    "state" VARCHAR(255) NOT NULL
);

CREATE UNIQUE INDEX "user_identifier" ON "user" ("identifier");

CREATE TABLE IF NOT EXISTS "project" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "identifier" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "latest_version" VARCHAR(255) NOT NULL,
    "is_published" INTEGER NOT NULL
);

CREATE UNIQUE INDEX "project_identifier" ON "project" ("identifier");

CREATE TABLE IF NOT EXISTS "auth_deployment" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "token" VARCHAR(255) NOT NULL,
    "expiration_time" DATETIME NOT NULL,
    "is_revoked" INTEGER NOT NULL,
    "user_id" INTEGER NOT NULL,
    "project_id" INTEGER NOT NULL,
    "project_version" VARCHAR(255) NOT NULL,
    "allow_overwrite" INTEGER NOT NULL,
    FOREIGN KEY ("user_id") REFERENCES "user" ("id"),
    FOREIGN KEY ("project_id") REFERENCES "project" ("id")
);

CREATE UNIQUE INDEX "auth_deployment_token" ON "auth_deployment" ("token");

CREATE INDEX "auth_deployment_user_id" ON "auth_deployment" ("user_id");

CREATE INDEX "auth_deployment_project_id" ON "auth_deployment" ("project_id");

CREATE TABLE IF NOT EXISTS "project_version" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "project_id" INTEGER NOT NULL,
    "version_sequence" INTEGER NOT NULL,
    "version_identifier" VARCHAR(255) NOT NULL,
    "is_published" INTEGER NOT NULL,
    FOREIGN KEY ("project_id") REFERENCES "project" ("id")
);

CREATE INDEX "project_version_project_id" ON "project_version" ("project_id");

CREATE TABLE IF NOT EXISTS "settings" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "organisation_name" VARCHAR(255) NOT NULL,
    "shared_secret" VARCHAR(255) NOT NULL,
    "active" INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS "staging_allocation" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "project_version_id" INTEGER NOT NULL,
    "path" VARCHAR(255) NOT NULL,
    FOREIGN KEY ("project_version_id") REFERENCES "project_version" ("id")
);

CREATE UNIQUE INDEX "staging_allocation_project_version_id" ON "staging_allocation" ("project_version_id");

CREATE UNIQUE INDEX "staging_allocation_path" ON "staging_allocation" ("path");

CREATE TABLE IF NOT EXISTS "user_permission" (
    "id" INTEGER NOT NULL PRIMARY KEY,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "user_id" INTEGER NOT NULL,
    "allow_overwrite" INTEGER NOT NULL,
    FOREIGN KEY ("user_id") REFERENCES "user" ("id")
);

CREATE UNIQUE INDEX "user_permission_user_id" ON "user_permission" ("user_id");

CREATE TABLE IF NOT EXISTS "user_project_rel" (
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "user_id" INTEGER NOT NULL,
    "project_id" INTEGER NOT NULL,
    PRIMARY KEY ("user_id", "project_id"),
    FOREIGN KEY ("user_id") REFERENCES "user" ("id"),
    FOREIGN KEY ("project_id") REFERENCES "project" ("id")
);

CREATE INDEX "user_project_rel_user_id" ON "user_project_rel" ("user_id");

CREATE INDEX "user_project_rel_project_id" ON "user_project_rel" ("project_id");


--
-- Datastore data.
--


INSERT INTO "settings" (organisation_name, shared_secret, active, created_at, updated_at) VALUES
    ("Test Org 1", "secret", 1, datetime('now'), datetime('now'));

INSERT INTO "user" (identifier, name, password, role, state, created_at, updated_at) VALUES
    ('fathom', 'Fathom System User', 'fathom', 'system', 'active', datetime('now'), datetime('now')),
    ('alpha', 'Alphanet Administrator', 'alpha', 'admin', 'active', datetime('now'), datetime('now')),
    ('test-user-1', 'Test User 1', '123456', 'user', 'active', datetime('now'), datetime('now'));

INSERT INTO "project" (identifier, name, description, latest_version, is_published, created_at, updated_at) VALUES
    ('test-project-1', 'Test Project 1', 'A Project for Testing Purposes (1).', '1.0.0', 0, datetime('now'), datetime('now'));

INSERT INTO "project_version" (project_id, version_sequence, version_identifier, is_published, created_at, updated_at) VALUES
    (1, 1, '1.0.0', 1, datetime('now'), datetime('now'));

INSERT INTO "user_project_rel" (user_id, project_id, created_at, updated_at) VALUES
    (1, 1, datetime('now'), datetime('now')),
    (2, 1, datetime('now'), datetime('now'));

INSERT INTO "user_permission" (user_id, allow_overwrite, created_at, updated_at) VALUES
    (1, 1, datetime('now'), datetime('now')),
    (2, 1, datetime('now'), datetime('now')),
    (3, 0, datetime('now'), datetime('now'));
