-- ⬇ ctfile-downloader schema
CREATE TABLE tasks(id INTEGER PRIMARY KEY, status TEXT DEFAULT 'queued', parallel INTEGER DEFAULT 4, created_at DATETIME);
CREATE TABLE files(id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES tasks(id), url TEXT, name TEXT, size INTEGER DEFAULT 0, downloaded INTEGER DEFAULT 0, status TEXT DEFAULT 'queued', retries INTEGER DEFAULT 0);
