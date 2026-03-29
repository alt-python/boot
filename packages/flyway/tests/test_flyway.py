"""
alt-python-flyway — test suite.

Uses pydbc-sqlite (in-memory, zero native deps).
Migration fixtures in tests/fixtures/db/migration/.
"""
import os
import pytest
import pydbc_sqlite  # noqa: F401 — self-registers the SQLite driver
from pydbc_core import PooledDataSource, DriverManager
from boot_pydbc import PydbcTemplate

from flyway import (
    Flyway,
    FlywayError,
    FlywayValidationError,
    FlywayMigrationError,
    MigrationLoader,
    MigrationExecutor,
    SchemaHistoryTable,
    MigrationState,
    MigrationVersion,
    checksum,
)

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')
MIGRATIONS = os.path.join(FIXTURES, 'db', 'migration')
MIGRATIONS2 = os.path.join(FIXTURES, 'db', 'migration2')

URL = 'pydbc:sqlite::memory:'


@pytest.fixture(autouse=True)
def reset_drivers():
    DriverManager.register_driver(pydbc_sqlite.SqliteDriver())
    yield
    DriverManager.clear()


def new_ds():
    return PooledDataSource(URL, pool={'max': 1})


def new_template(ds=None):
    if ds is None:
        ds = new_ds()
    return PydbcTemplate(ds), ds


# ── MigrationVersion ──────────────────────────────────────────────────────

class TestMigrationVersion:

    def test_parses_single_segment(self):
        assert str(MigrationVersion.parse('1')) == '1'
        assert str(MigrationVersion.parse('10')) == '10'

    def test_parses_multi_segment(self):
        assert str(MigrationVersion.parse('1.1')) == '1.1'
        assert str(MigrationVersion.parse('2.0.0')) == '2.0.0'

    def test_compare_to_less_than(self):
        assert MigrationVersion.parse('1').compare_to(MigrationVersion.parse('2')) < 0

    def test_compare_to_greater_than(self):
        assert MigrationVersion.parse('2').compare_to(MigrationVersion.parse('1')) > 0

    def test_compare_to_equal(self):
        assert MigrationVersion.parse('1').compare_to(MigrationVersion.parse('1')) == 0

    def test_sort_order_numeric(self):
        """1 < 1.1 < 2 < 10 (not lexicographic)."""
        versions = [MigrationVersion.parse(v) for v in ['10', '2', '1.1', '1']]
        versions.sort()
        assert [str(v) for v in versions] == ['1', '1.1', '2', '10']

    def test_lt_operator(self):
        assert MigrationVersion.parse('1') < MigrationVersion.parse('2')

    def test_eq_operator(self):
        assert MigrationVersion.parse('1.0') == MigrationVersion.parse('1.0')


# ── checksum ──────────────────────────────────────────────────────────────

class TestChecksum:

    def test_same_content_same_value(self):
        assert checksum('SELECT 1') == checksum('SELECT 1')

    def test_different_content_different_value(self):
        assert checksum('SELECT 1') != checksum('SELECT 2')

    def test_returns_signed_32bit_int(self):
        c = checksum('hello world')
        assert isinstance(c, int)
        assert -2147483648 <= c <= 2147483647


# ── MigrationLoader ───────────────────────────────────────────────────────

class TestMigrationLoader:

    def test_loads_versioned_migrations(self):
        loader = MigrationLoader([MIGRATIONS])
        migrations = loader.load()
        assert len(migrations) == 3

    def test_sorted_by_version_ascending(self):
        loader = MigrationLoader([MIGRATIONS])
        migrations = loader.load()
        assert [str(m['version']) for m in migrations] == ['1', '2', '3']

    def test_description_parsed_from_filename(self):
        loader = MigrationLoader([MIGRATIONS])
        first = loader.load()[0]
        assert first['description'] == 'create notes table'

    def test_multi_location_merge_sorted(self):
        loader = MigrationLoader([MIGRATIONS, MIGRATIONS2])
        migrations = loader.load()
        assert len(migrations) == 4
        assert [str(m['version']) for m in migrations] == ['1', '1.1', '2', '3']

    def test_nonexistent_location_silently_empty(self):
        loader = MigrationLoader(['/does/not/exist'])
        assert loader.load() == []

    def test_checksum_attached(self):
        loader = MigrationLoader([MIGRATIONS])
        for m in loader.load():
            assert isinstance(m['checksum'], int)

    def test_type_is_sql(self):
        loader = MigrationLoader([MIGRATIONS])
        for m in loader.load():
            assert m['type'] == 'SQL'


# ── SchemaHistoryTable ────────────────────────────────────────────────────

class TestSchemaHistoryTable:

    def test_provision_creates_table(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        assert h.find_all() == []

    def test_provision_idempotent(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        h.provision()  # must not raise
        assert h.find_all() == []

    def test_insert_and_find_all_round_trip(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        h.insert({
            'version': '1',
            'description': 'create notes',
            'script': 'V1__create_notes.sql',
            'checksum': 42,
            'success': True,
        })
        rows = h.find_all()
        assert len(rows) == 1
        assert rows[0]['version'] == '1'
        assert rows[0]['description'] == 'create notes'
        assert rows[0]['success'] is True

    def test_max_rank_empty_returns_zero(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        assert h.max_rank() == 0

    def test_max_rank_increments(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        h.insert({'version': '1', 'description': 'a', 'script': 'V1.sql', 'success': True})
        h.insert({'version': '2', 'description': 'b', 'script': 'V2.sql', 'success': True})
        assert h.max_rank() == 2

    def test_remove_failed_entries(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        h.insert({'version': '1', 'description': 'ok', 'script': 'V1.sql', 'success': True})
        h.insert({'version': '2', 'description': 'fail', 'script': 'V2.sql', 'success': False})
        h.remove_failed_entries()
        rows = h.find_all()
        assert len(rows) == 1
        assert rows[0]['version'] == '1'

    def test_insert_baseline(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t)
        h.provision()
        h.insert_baseline('1', 'Test Baseline')
        rows = h.find_all()
        assert len(rows) == 1
        assert rows[0]['type'] == 'BASELINE'
        assert rows[0]['version'] == '1'
        assert rows[0]['success'] is True

    def test_custom_table_name(self):
        t, ds = new_template()
        h = SchemaHistoryTable(t, 'my_migrations')
        h.provision()
        assert h.table_name == 'my_migrations'
        assert h.find_all() == []


# ── MigrationExecutor ─────────────────────────────────────────────────────

class TestMigrationExecutor:

    def test_executes_multi_statement_sql(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        executor = MigrationExecutor()
        # Use execute_with_template so we don't hold a connection across calls
        executor.execute_with_template(t, """
            CREATE TABLE ex_test (id INTEGER PRIMARY KEY, val TEXT);
            INSERT INTO ex_test VALUES (1, 'hello');
        """)
        rows = t.query_for_list('SELECT id, val FROM ex_test')
        assert len(rows) == 1
        normalized = {k.lower(): v for k, v in rows[0].items()}
        assert normalized['val'] == 'hello'

    def test_execute_with_connection_executes_sql(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        executor = MigrationExecutor()
        conn = ds.get_connection()
        try:
            executor.execute(conn, 'CREATE TABLE ex_conn_test (id INTEGER PRIMARY KEY);')
        finally:
            conn.close()  # return to pool before querying
        rows = t.query_for_list('SELECT COUNT(*) AS cnt FROM ex_conn_test')
        cnt = {k.lower(): v for k, v in rows[0].items()}['cnt']
        assert cnt == 0

    def test_strips_line_comments(self):
        ds = new_ds()
        executor = MigrationExecutor()
        conn = ds.get_connection()
        executor.execute(conn, """
            -- this is a comment
            CREATE TABLE ex_test2 (id INTEGER PRIMARY KEY);
            -- another comment
        """)
        # No error = pass

    def test_split_removes_blank_statements(self):
        parts = MigrationExecutor._split('SELECT 1;; SELECT 2;')
        assert len(parts) == 2


# ── Flyway.migrate() ─────────────────────────────────────────────────────

class TestFlywayMigrate:

    def test_applies_all_pending_and_returns_count(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        result = flyway.migrate()
        assert result['migrations_executed'] == 3
        assert len(result['applied_migrations']) == 3

    def test_applied_migrations_have_state_success(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        result = flyway.migrate()
        for m in result['applied_migrations']:
            assert m['state'] == MigrationState.SUCCESS

    def test_history_table_populated(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        flyway = Flyway(data_source=ds, template=t, locations=[MIGRATIONS])
        flyway.migrate()
        history = SchemaHistoryTable(t)
        rows = history.find_all()
        assert len(rows) == 3
        assert all(r['success'] for r in rows)

    def test_idempotent_second_migrate_returns_zero(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        flyway.migrate()
        second = flyway.migrate()
        assert second['migrations_executed'] == 0

    def test_schema_created_after_migrate(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        flyway = Flyway(data_source=ds, template=t, locations=[MIGRATIONS])
        flyway.migrate()
        rows = t.query_for_list('SELECT COUNT(*) AS cnt FROM notes')
        cnt = {k.lower(): v for k, v in rows[0].items()}['cnt']
        assert cnt == 2  # V3 seeded 2 rows

    def test_multi_location_merge(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS, MIGRATIONS2])
        result = flyway.migrate()
        assert result['migrations_executed'] == 4

    def test_raises_flyway_migration_error_on_bad_sql(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        # Replace loader with one that returns bad SQL
        flyway._loader = type('L', (), {'load': lambda self: [{
            'version': MigrationVersion.parse('99'),
            'description': 'bad migration',
            'script': 'V99__bad.sql',
            'sql': 'THIS IS NOT VALID SQL !!!',
            'checksum': 0,
            'type': 'SQL',
        }]})()
        with pytest.raises(FlywayMigrationError):
            flyway.migrate()


# ── Flyway.info() ────────────────────────────────────────────────────────

class TestFlywayInfo:

    def test_all_pending_before_migrate(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        info = flyway.info()
        assert len(info) == 3
        for m in info:
            assert m['state'] == MigrationState.PENDING

    def test_success_and_pending_mix(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        flyway = Flyway(data_source=ds, template=t, locations=[MIGRATIONS])
        # Apply only V1 by temporarily restricting the loader
        original_loader = flyway._loader
        flyway._loader = type('L', (), {'load': lambda self: original_loader.load()[:1]})()
        flyway.migrate()
        # Restore full loader for info()
        flyway._loader = original_loader
        info = flyway.info()
        assert info[0]['state'] == MigrationState.SUCCESS
        assert info[1]['state'] == MigrationState.PENDING
        assert info[2]['state'] == MigrationState.PENDING


# ── Flyway.validate() ────────────────────────────────────────────────────

class TestFlywayValidate:

    def test_passes_when_checksums_match(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        flyway.migrate()
        flyway.validate()  # must not raise

    def test_raises_on_checksum_drift(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        flyway.migrate()
        # Tamper: bump the checksum of the first migration in the loader
        original_loader = flyway._loader
        class TamperedLoader:
            def load(self_):
                migrations = original_loader.load()
                tampered = dict(migrations[0])
                tampered['checksum'] = tampered['checksum'] + 1
                return [tampered] + migrations[1:]
        flyway._loader = TamperedLoader()
        with pytest.raises(FlywayValidationError, match='checksum mismatch'):
            flyway.validate()


# ── Flyway.baseline() ────────────────────────────────────────────────────

class TestFlywayBaseline:

    def test_inserts_baseline_entry(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        flyway = Flyway(data_source=ds, template=t, locations=[MIGRATIONS], baseline_version='0')
        flyway.baseline()
        history = SchemaHistoryTable(t)
        rows = history.find_all()
        assert len(rows) == 1
        assert rows[0]['type'] == 'BASELINE'

    def test_raises_if_history_not_empty(self):
        ds = new_ds()
        flyway = Flyway(data_source=ds, locations=[MIGRATIONS])
        flyway.migrate()
        with pytest.raises(FlywayError):
            flyway.baseline()


# ── Flyway.repair() ───────────────────────────────────────────────────────

class TestFlywayRepair:

    def test_removes_failed_entries_and_reports_count(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        history = SchemaHistoryTable(t)
        history.provision()
        history.insert({'version': '1', 'description': 'ok', 'script': 'V1.sql', 'success': True})
        history.insert({'version': '2', 'description': 'fail', 'script': 'V2.sql', 'success': False})

        flyway = Flyway(data_source=ds, template=t, locations=[MIGRATIONS])
        result = flyway.repair()
        assert result['removed_entries'] == 1
        assert len(history.find_all()) == 1


# ── Flyway.clean() ────────────────────────────────────────────────────────

class TestFlywayClean:

    def test_drops_history_table(self):
        ds = new_ds()
        t = PydbcTemplate(ds)
        flyway = Flyway(data_source=ds, template=t, locations=[MIGRATIONS])
        flyway.migrate()
        flyway.clean()
        # Reprovision — should be empty after clean
        history = SchemaHistoryTable(t)
        history.provision()
        assert history.find_all() == []
