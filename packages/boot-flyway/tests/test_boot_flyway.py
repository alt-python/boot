"""
alt-python-boot-flyway — CDI integration tests.

Verifies ManagedFlyway wires to the data_source bean and runs migrate()
during CDI context start.
"""
import os
import pytest
import boot.boot as _boot_module
import pydbc_sqlite  # noqa: F401
from pydbc_core import PooledDataSource, DriverManager
from config.ephemeral_config import EphemeralConfig
from cdi import ApplicationContext
from boot import Boot
from boot_pydbc import PydbcTemplate, pydbc_auto_configuration
from boot_flyway import (
    ManagedFlyway,
    flyway_starter,
    flyway_auto_configuration,
    DEFAULT_FLYWAY_PREFIX,
)

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')
MIGRATIONS = os.path.join(FIXTURES, 'db', 'migration')
URL = 'pydbc:sqlite::memory:'


def base_config(extra_flyway=None):
    flyway_cfg = {'locations': MIGRATIONS}
    if extra_flyway:
        flyway_cfg.update(extra_flyway)
    return EphemeralConfig({
        'boot': {
            'datasource': {'url': URL, 'pool': {'enabled': True, 'max': 2}},
            'flyway': flyway_cfg,
        },
    })


@pytest.fixture(autouse=True)
def reset_state():
    _boot_module._root.clear()
    DriverManager.register_driver(pydbc_sqlite.SqliteDriver())
    yield
    _boot_module._root.clear()
    DriverManager.clear()


# ── Constants ─────────────────────────────────────────────────────────────

def test_default_flyway_prefix():
    assert DEFAULT_FLYWAY_PREFIX == 'boot.flyway'


# ── flyway_starter() ──────────────────────────────────────────────────────

def test_flyway_starter_returns_component_list():
    components = flyway_starter()
    assert isinstance(components, list)
    assert len(components) > 0


def test_flyway_starter_contains_managed_flyway():
    names = [c.name for c in flyway_starter()]
    assert 'managed_flyway' in names


def test_flyway_auto_configuration_alias():
    assert flyway_auto_configuration() is not None


# ── CDI integration — migrate() on start ─────────────────────────────────

def test_runs_all_migrations_on_context_start():
    app_ctx = Boot.boot({
        'config': base_config(),
        'contexts': pydbc_auto_configuration() + flyway_starter(),
        'run': False,
    })
    mf = app_ctx.get('managed_flyway')
    assert isinstance(mf, ManagedFlyway)
    flyway = mf.get_flyway()
    assert flyway is not None
    info = flyway.info()
    assert all(m['state'] == 'SUCCESS' for m in info)


def test_schema_applied_users_seeded():
    app_ctx = Boot.boot({
        'config': base_config(),
        'contexts': pydbc_auto_configuration() + flyway_starter(),
        'run': False,
    })
    template = app_ctx.get('pydbc_template')
    users = template.query_for_list('SELECT * FROM users ORDER BY id')
    assert len(users) == 2
    assert {k.lower(): v for k, v in users[0].items()}['username'] == 'alice'
    assert {k.lower(): v for k, v in users[1].items()}['username'] == 'bob'


def test_history_table_populated():
    app_ctx = Boot.boot({
        'config': base_config(),
        'contexts': pydbc_auto_configuration() + flyway_starter(),
        'run': False,
    })
    template = app_ctx.get('pydbc_template')
    rows = template.query_for_list(
        'SELECT * FROM flyway_schema_history ORDER BY installed_rank'
    )
    assert len(rows) == 2
    assert all({k.lower(): v for k, v in r.items()}['success'] == 1 for r in rows)


def test_second_migrate_is_idempotent():
    app_ctx = Boot.boot({
        'config': base_config(),
        'contexts': pydbc_auto_configuration() + flyway_starter(),
        'run': False,
    })
    mf = app_ctx.get('managed_flyway')
    result = mf.get_flyway().migrate()
    assert result['migrations_executed'] == 0


def test_enabled_false_suppresses_migration():
    app_ctx = Boot.boot({
        'config': base_config({'enabled': False}),
        'contexts': pydbc_auto_configuration() + flyway_starter(),
        'run': False,
    })
    mf = app_ctx.get('managed_flyway')
    # init() returned early — flyway was not created
    assert mf.get_flyway() is None


def test_custom_table_name_respected():
    app_ctx = Boot.boot({
        'config': base_config({'table': 'my_migrations'}),
        'contexts': pydbc_auto_configuration() + flyway_starter(),
        'run': False,
    })
    template = app_ctx.get('pydbc_template')
    rows = template.query_for_list(
        'SELECT * FROM my_migrations ORDER BY installed_rank'
    )
    assert len(rows) == 2


def test_custom_datasource_bean_wired():
    """flyway_starter with datasource_bean='data_source' wires to the correct bean."""
    app_ctx = Boot.boot({
        'config': base_config(),
        'contexts': pydbc_auto_configuration() + flyway_starter(datasource_bean='data_source'),
        'run': False,
    })
    mf = app_ctx.get('managed_flyway')
    assert mf.get_flyway() is not None
