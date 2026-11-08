--
-- Default datastore fixture for functionality tests.
--

INSERT INTO "settings" (organisation_name, shared_secret, active, created_at, updated_at) VALUES
    ("Test Org 1", "secret", 1, datetime('now'), datetime('now'));

INSERT INTO "user" (identifier, name, password, role, state, created_at, updated_at) VALUES
    ('fathom', 'Fathom System User', 'fathom', 'system', 'active', datetime('now'), datetime('now')),
    ('alpha', 'Alphanet Administrator', 'alpha', 'admin', 'active', datetime('now'), datetime('now')),
    ('test-user-1', 'Test User 1', '123456', 'user', 'active', datetime('now'), datetime('now'));

INSERT INTO "project" (identifier, name, description, latest_version, time_created, is_published, created_at, updated_at) VALUES
    ('test-project-1', 'Test Project 1', 'A Project for Testing Purposes (1).', '1.0.0', datetime('now'), 0, datetime('now'), datetime('now'));

INSERT INTO "project_version" (project_id, version_sequence, version_identifier, time_created, is_published, created_at, updated_at) VALUES
    (1, 1, '1.0.0', datetime('now'), 1, datetime('now'), datetime('now'));

INSERT INTO "user_project_rel" (user_id, project_id, created_at, updated_at) VALUES
    (1, 1, datetime('now'), datetime('now')),
    (2, 1, datetime('now'), datetime('now'));

INSERT INTO "user_permission" (user_id, allow_overwrite, created_at, updated_at) VALUES
    (1, 1, datetime('now'), datetime('now')),
    (2, 1, datetime('now'), datetime('now')),
    (3, 0, datetime('now'), datetime('now'));
