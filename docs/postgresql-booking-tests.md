# PostgreSQL booking contention test

The ordinary test suite uses isolated SQLite databases and needs no local
PostgreSQL server:

```sh
uv run pytest
```

The row-locking integration test must use PostgreSQL. Start a local server (for
example, with Docker) and create a test database, then run from `web_backend`:

```sh
LETSGOSA_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/letsgosa_test' \
  uv run alembic upgrade head
TEST_POSTGRESQL_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/letsgosa_test' \
  uv run pytest -m postgresql tests/integration/test_public_booking_postgresql.py
```

The migration command prepares the PostgreSQL schema. The test opens two
separate application instances, so each request has its own SQLAlchemy engine
and connection pool. Both requests wait at a bounded barrier before posting;
each requests two places from a three place departure. The test requires one
`201` and one `409`, then checks the final inventory and persisted booking rows.
The ordinary suite skips this test when the PostgreSQL URL is not set. The
dedicated CI step sets the URL explicitly and runs the test in addition to the
regular backend suite using its PostgreSQL 16 service.
