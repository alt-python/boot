import asyncio
import pytest
import boot.boot as _boot_module
import pynosqlc.memory  # noqa: F401 — registers MemoryDriver on import
from pynosqlc.core import DriverManager, Filter
from pynosqlc.memory.memory_driver import _driver
from config.ephemeral_config import EphemeralConfig
from cdi import ApplicationContext
from boot import Boot
from boot_pynosqlc import (
    ConfiguredClientDataSource, ManagedNosqlClient, NoSqlClientBuilder,
    pynosqlc_auto_configuration, pynosqlc_starter, pynosqlc_boot,
    DEFAULT_NOSQL_PREFIX,
)

URL = 'pynosqlc:memory:'


@pytest.fixture(autouse=True)
def reset_state():
    _boot_module._root.clear()
    DriverManager.clear()
    DriverManager.register_driver(_driver)  # _driver is a module-level singleton — idempotent
    yield
    _boot_module._root.clear()
    DriverManager.clear()


def _boot_with_url(url=URL, prefix=DEFAULT_NOSQL_PREFIX):
    cfg = EphemeralConfig({f'{prefix}.url': url})
    return Boot.boot({
        'config': cfg,
        'contexts': pynosqlc_auto_configuration(prefix=prefix),
        'run': False,
    })


# ---------------------------------------------------------------------------
# 1. Import symbols
# ---------------------------------------------------------------------------

def test_import_symbols():
    assert ConfiguredClientDataSource is not None
    assert ManagedNosqlClient is not None
    assert NoSqlClientBuilder is not None
    assert pynosqlc_auto_configuration is not None
    assert pynosqlc_starter is not None
    assert pynosqlc_boot is not None
    assert DEFAULT_NOSQL_PREFIX is not None


# ---------------------------------------------------------------------------
# 2. Default prefix
# ---------------------------------------------------------------------------

def test_default_prefix_is_boot_nosql():
    assert DEFAULT_NOSQL_PREFIX == 'boot.nosql'


# ---------------------------------------------------------------------------
# 3. pynosqlc_auto_configuration returns two components
# ---------------------------------------------------------------------------

def test_pynosqlc_auto_configuration_returns_two_components():
    components = pynosqlc_auto_configuration()
    assert len(components) == 2
    names = {c.name for c in components}
    assert 'nosql_client_data_source' in names
    assert 'nosql_client' in names


# ---------------------------------------------------------------------------
# 4. Beans registered in context
# ---------------------------------------------------------------------------

def test_registered_in_context():
    app_ctx = _boot_with_url()
    assert isinstance(app_ctx.get('nosql_client_data_source'), ConfiguredClientDataSource)
    assert isinstance(app_ctx.get('nosql_client'), ManagedNosqlClient)


# ---------------------------------------------------------------------------
# 5. ManagedNosqlClient is ready after boot with URL
# ---------------------------------------------------------------------------

def test_managed_nosql_client_ready():
    app_ctx = _boot_with_url()
    client = app_ctx.get('nosql_client')
    col = client.get_collection('test')
    assert col is not None


# ---------------------------------------------------------------------------
# 6. Collection store/get round-trip
# ---------------------------------------------------------------------------

def test_collection_store_get_round_trip():
    app_ctx = _boot_with_url()
    col = app_ctx.get('nosql_client').get_collection('items')
    asyncio.run(col.store('k1', {'val': 1}))
    doc = asyncio.run(col.get('k1'))
    assert doc['val'] == 1


# ---------------------------------------------------------------------------
# 7. Collection.get returns None for missing key
# ---------------------------------------------------------------------------

def test_collection_get_returns_none_for_missing_key():
    app_ctx = _boot_with_url()
    col = app_ctx.get('nosql_client').get_collection('items')
    result = asyncio.run(col.get('nonexistent'))
    assert result is None


# ---------------------------------------------------------------------------
# 8. Collection.insert assigns a string ID
# ---------------------------------------------------------------------------

def test_collection_insert_assigns_id():
    app_ctx = _boot_with_url()
    col = app_ctx.get('nosql_client').get_collection('items')
    _id = asyncio.run(col.insert({'name': 'test'}))
    assert isinstance(_id, str)
    assert _id != ''


# ---------------------------------------------------------------------------
# 9. Collection.update patches document
# ---------------------------------------------------------------------------

def test_collection_update_patches():
    app_ctx = _boot_with_url()
    col = app_ctx.get('nosql_client').get_collection('items')
    asyncio.run(col.store('k2', {'val': 2, 'extra': 'keep'}))
    asyncio.run(col.update('k2', {'val': 99}))
    doc = asyncio.run(col.get('k2'))
    assert doc['val'] == 99


# ---------------------------------------------------------------------------
# 10. Collection.delete removes document
# ---------------------------------------------------------------------------

def test_collection_delete_removes():
    app_ctx = _boot_with_url()
    col = app_ctx.get('nosql_client').get_collection('items')
    asyncio.run(col.store('k3', {'val': 3}))
    asyncio.run(col.delete('k3'))
    result = asyncio.run(col.get('k3'))
    assert result is None


# ---------------------------------------------------------------------------
# 11. Collection.find with filter
# ---------------------------------------------------------------------------

def test_collection_find_with_filter():
    app_ctx = _boot_with_url()
    col = app_ctx.get('nosql_client').get_collection('typed')

    async def _setup():
        await col.store('a1', {'type': 'a', 'name': 'alpha'})
        await col.store('b1', {'type': 'b', 'name': 'beta'})
        f = Filter.where('type').eq('a').build()
        cursor = await col.find(f)
        return cursor.get_documents()

    docs = asyncio.run(_setup())
    assert len(docs) == 1
    assert docs[0]['type'] == 'a'


# ---------------------------------------------------------------------------
# 12. Beans absent / client not ready when URL not set
# ---------------------------------------------------------------------------

def test_beans_absent_when_url_not_set():
    cfg = EphemeralConfig({})
    app_ctx = Boot.boot({
        'config': cfg,
        'contexts': pynosqlc_auto_configuration(),
        'run': False,
    })
    ds = app_ctx.get('nosql_client_data_source')
    assert ds._delegate is None
    client = app_ctx.get('nosql_client')
    with pytest.raises(RuntimeError):
        client.get_collection('x')


# ---------------------------------------------------------------------------
# 13. NoSqlClientBuilder default bean names
# ---------------------------------------------------------------------------

def test_nosql_client_builder_default_names():
    components = NoSqlClientBuilder.create().build()
    assert len(components) == 2
    names = {c.name for c in components}
    assert 'nosql_client_data_source' in names
    assert 'nosql_client' in names


# ---------------------------------------------------------------------------
# 14. NoSqlClientBuilder custom bean names
# ---------------------------------------------------------------------------

def test_nosql_client_builder_custom_names():
    components = (
        NoSqlClientBuilder.create()
        .bean_names({'nosql_client_data_source': 'my_ds', 'nosql_client': 'my_client'})
        .build()
    )
    names = {c.name for c in components}
    assert 'my_ds' in names
    assert 'my_client' in names
    assert 'nosql_client_data_source' not in names
    assert 'nosql_client' not in names


# ---------------------------------------------------------------------------
# 15. Secondary NoSQL client with different prefix
# ---------------------------------------------------------------------------

def test_secondary_nosql_client():
    primary = NoSqlClientBuilder.create().prefix('boot.nosql').build()
    secondary = (
        NoSqlClientBuilder.create()
        .prefix('boot.nosql.secondary')
        .bean_names({'nosql_client_data_source': 'secondary_ds',
                     'nosql_client': 'secondary_client'})
        .build()
    )
    cfg = EphemeralConfig({
        'boot.nosql.url': URL,
        'boot.nosql.secondary.url': URL,
    })
    app_ctx = Boot.boot({
        'config': cfg,
        'contexts': [*primary, *secondary],
        'run': False,
    })
    primary_ds = app_ctx.get('nosql_client_data_source')
    secondary_ds = app_ctx.get('secondary_ds')
    assert primary_ds._delegate is not None
    assert secondary_ds._delegate is not None
    # both clients should be independently ready
    primary_col = app_ctx.get('nosql_client').get_collection('p')
    secondary_col = app_ctx.get('secondary_client').get_collection('s')
    assert primary_col is not None
    assert secondary_col is not None
