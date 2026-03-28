import pytest
import boot.boot as _boot_module
import pydbc_sqlite  # noqa: F401 — self-registers the SQLite driver
from pydbc_core import SingleConnectionDataSource, PooledDataSource, DriverManager
from config.ephemeral_config import EphemeralConfig
from cdi import ApplicationContext
from boot_pydbc import (
    PydbcTemplate, NamedParameterPydbcTemplate, ConfiguredDataSource,
    SchemaInitializer, DataSourceBuilder, pydbc_auto_configuration, DEFAULT_PREFIX,
)

URL = 'pydbc:sqlite::memory:'


@pytest.fixture(autouse=True)
def reset_state():
    """Reset boot _root and re-register the SQLite driver before each test."""
    _boot_module._root.clear()
    DriverManager.register_driver(pydbc_sqlite.SqliteDriver())
    yield
    _boot_module._root.clear()
    DriverManager.clear()


# ---------------------------------------------------------------------------
# T02 tests (5, 6) — preserved
# ---------------------------------------------------------------------------

def test_pydbc_template_executes_sql():
    # PooledDataSource with max=1 reuses the same underlying SQLite connection,
    # so conn.close() (which returns to pool) does not destroy the in-memory DB.
    ds = PooledDataSource(URL, pool={'max': 1})
    try:
        template = PydbcTemplate(ds)
        template.execute('CREATE TABLE notes (id INTEGER, body TEXT)')
        template.update('INSERT INTO notes (id, body) VALUES (?, ?)', (1, 'hello'))
        template.update('INSERT INTO notes (id, body) VALUES (?, ?)', (2, 'world'))
        rows = template.query_for_list('SELECT id, body FROM notes ORDER BY id')
        assert len(rows) == 2
        row = template.query_for_object('SELECT id, body FROM notes WHERE id = ?', (1,))
        normalized = {k.lower(): v for k, v in row.items()}
        assert normalized['body'] == 'hello'
    finally:
        ds.destroy()


def test_named_parameter_pydbc_template_executes_sql():
    ds = PooledDataSource(URL, pool={'max': 1})
    try:
        template = NamedParameterPydbcTemplate(ds)
        template.execute('CREATE TABLE notes2 (id INTEGER, body TEXT)')
        template.update('INSERT INTO notes2 (id, body) VALUES (:id, :body)', {'id': 1, 'body': 'named'})
        rows = template.query_for_list('SELECT id, body FROM notes2 WHERE id = :id', {'id': 1})
        assert len(rows) == 1
        normalized = {k.lower(): v for k, v in rows[0].items()}
        assert normalized['body'] == 'named'
    finally:
        ds.destroy()


# ---------------------------------------------------------------------------
# T03 tests (1–4, 7–15)
# ---------------------------------------------------------------------------

def test_import_symbols():
    """All public symbols are importable and not None."""
    from boot_pydbc import (
        PydbcTemplate, NamedParameterPydbcTemplate,
        ConfiguredDataSource, SchemaInitializer, DataSourceBuilder,
        pydbc_auto_configuration, pydbc_starter, pydbc_template_starter,
        DEFAULT_PREFIX,
    )
    assert PydbcTemplate is not None
    assert NamedParameterPydbcTemplate is not None
    assert ConfiguredDataSource is not None
    assert SchemaInitializer is not None
    assert DataSourceBuilder is not None
    assert pydbc_auto_configuration is not None
    assert pydbc_starter is not None
    assert pydbc_template_starter is not None
    assert DEFAULT_PREFIX is not None


def test_default_prefix_is_boot_datasource():
    assert DEFAULT_PREFIX == 'boot.datasource'


def test_pydbc_auto_configuration_returns_four_singletons():
    components = pydbc_auto_configuration()
    assert len(components) == 4
    names = [c.name for c in components]
    assert 'data_source' in names
    assert 'pydbc_template' in names
    assert 'named_parameter_pydbc_template' in names
    assert 'schema_initializer' in names


def test_registered_in_context():
    """Boot with URL config → app_ctx contains ConfiguredDataSource and PydbcTemplate."""
    from boot import Boot
    config = EphemeralConfig({'boot': {'datasource': {'url': URL}}})
    app_ctx = Boot.boot({
        'config': config,
        'contexts': pydbc_auto_configuration(),
        'run': False,
    })
    assert app_ctx is not None
    ds = app_ctx.get('data_source')
    assert isinstance(ds, ConfiguredDataSource)
    jt = app_ctx.get('pydbc_template')
    assert isinstance(jt, PydbcTemplate)


def test_configured_datasource_uses_single_connection_for_in_memory():
    """Two get_connection() calls on an in-memory URL return the same connection object."""
    from boot import Boot
    config = EphemeralConfig({'boot': {'datasource': {'url': URL}}})
    app_ctx = Boot.boot({
        'config': config,
        'contexts': pydbc_auto_configuration(),
        'run': False,
    })
    ds = app_ctx.get('data_source')
    conn1 = ds.get_connection()
    conn2 = ds.get_connection()
    assert conn1 is conn2


def test_configured_datasource_skips_when_url_not_set():
    """No URL in config → ConfiguredDataSource._delegate stays None."""
    from boot import Boot
    config = EphemeralConfig({})
    app_ctx = Boot.boot({
        'config': config,
        'contexts': pydbc_auto_configuration(),
        'run': False,
    })
    ds = app_ctx.get('data_source')
    assert isinstance(ds, ConfiguredDataSource)
    assert ds._delegate is None


def test_custom_prefix_accepted():
    """pydbc_auto_configuration with a custom prefix reads from matching config keys."""
    from boot import Boot
    config = EphemeralConfig({'myapp': {'db': {'url': URL}}})
    app_ctx = Boot.boot({
        'config': config,
        'contexts': pydbc_auto_configuration(prefix='myapp.db'),
        'run': False,
    })
    ds = app_ctx.get('data_source')
    assert isinstance(ds, ConfiguredDataSource)
    assert ds._delegate is not None


def test_schema_initializer_skips_when_initialize_false():
    """boot.datasource.initialize = False → SchemaInitializer.init() is a no-op."""
    from boot import Boot
    config = EphemeralConfig({
        'boot': {'datasource': {'url': URL, 'initialize': False}}
    })
    # Should not raise even though config/schema.sql does not exist
    app_ctx = Boot.boot({
        'config': config,
        'contexts': pydbc_auto_configuration(),
        'run': False,
    })
    assert app_ctx is not None


def test_schema_initializer_skips_missing_files():
    """URL set but no config/schema.sql on disk → SchemaInitializer.init() is a no-op."""
    from boot import Boot
    import os
    config = EphemeralConfig({'boot': {'datasource': {'url': URL}}})
    # Ensure the schema file definitely does not exist in the working directory
    assert not os.path.exists('config/schema.sql')
    app_ctx = Boot.boot({
        'config': config,
        'contexts': pydbc_auto_configuration(),
        'run': False,
    })
    assert app_ctx is not None


def test_datasource_builder_default_names():
    """DataSourceBuilder.create().build() produces 4 components with default names."""
    components = DataSourceBuilder.create().build()
    assert len(components) == 4
    names = [c.name for c in components]
    assert 'data_source' in names
    assert 'pydbc_template' in names
    assert 'named_parameter_pydbc_template' in names
    assert 'schema_initializer' in names


def test_datasource_builder_custom_names():
    """Custom bean_names override default names."""
    components = (
        DataSourceBuilder.create()
        .bean_names({'data_source': 'reporting_ds', 'pydbc_template': 'reporting_template'})
        .build()
    )
    names = [c.name for c in components]
    assert 'reporting_ds' in names
    assert 'reporting_template' in names
    assert 'data_source' not in names
    assert 'pydbc_template' not in names


def test_datasource_builder_without_schema_initializer():
    """without_schema_initializer() produces 3 components (no schema_initializer)."""
    components = DataSourceBuilder.create().without_schema_initializer().build()
    assert len(components) == 3
    names = [c.name for c in components]
    assert 'schema_initializer' not in names


def test_datasource_builder_secondary_datasource():
    """Two DataSourceBuilders with different prefixes and names both wire correctly."""
    from boot import Boot
    config = EphemeralConfig({
        'primary': {'url': URL},
        'secondary': {'url': URL},
    })
    primary_components = (
        DataSourceBuilder.create()
        .prefix('primary')
        .bean_names({
            'data_source': 'primary_ds',
            'pydbc_template': 'primary_template',
            'named_parameter_pydbc_template': 'primary_named_template',
            'schema_initializer': 'primary_schema_initializer',
        })
        .build()
    )
    secondary_components = (
        DataSourceBuilder.create()
        .prefix('secondary')
        .bean_names({
            'data_source': 'secondary_ds',
            'pydbc_template': 'secondary_template',
            'named_parameter_pydbc_template': 'secondary_named_template',
            'schema_initializer': 'secondary_schema_initializer',
        })
        .build()
    )
    app_ctx = Boot.boot({
        'config': config,
        'contexts': primary_components + secondary_components,
        'run': False,
    })
    primary_ds = app_ctx.get('primary_ds')
    secondary_ds = app_ctx.get('secondary_ds')
    assert isinstance(primary_ds, ConfiguredDataSource)
    assert isinstance(secondary_ds, ConfiguredDataSource)
    assert primary_ds._delegate is not None
    assert secondary_ds._delegate is not None
