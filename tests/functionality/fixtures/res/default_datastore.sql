--
-- Default datastore fixture for functionality tests.
--

INSERT INTO "user" (identifier, name, password, state) VALUES
    ('alpha', 'Alphanet Administrator', 'alpha', 'active'),
    ('test-user-1', 'Test User 1', '123456', 'active');

INSERT INTO "project" (identifier, name, description, latest_version, time_created, is_published) VALUES
    ('test-project-1', 'Test Project 1', 'A Project for Testing Purposes (1).', '1.0.0', datetime('now'), 0);

INSERT INTO "project_version" (project_id, version_sequence, version_identifier, time_created, is_published) VALUES
    (1, 1, '1.0.0', datetime('now'), 1);

INSERT INTO "user_project_rel" (user_id, project_id) VALUES
    (1, 1);

INSERT INTO "user_permission" (user_id, allow_overwrite, is_admin) VALUES
    (1, 1, 1),
    (2, 0, 0);
