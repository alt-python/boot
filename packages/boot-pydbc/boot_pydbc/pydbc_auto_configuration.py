from pydbc_core import DataSource, SingleConnectionDataSource, PooledDataSource
from cdi import Singleton
from boot_pydbc.pydbc_template import PydbcTemplate
from boot_pydbc.named_parameter_pydbc_template import NamedParameterPydbcTemplate

DEFAULT_PREFIX = 'boot.datasource'


class ConfiguredDataSource:
    def __init__(self):
        self._delegate = None
        self._application_context = None
        self._prefix = DEFAULT_PREFIX

    def set_application_context(self, ctx):
        self._application_context = ctx

    def init(self):
        config = self._application_context.get('config')
        p = self._prefix
        if not config.has(f'{p}.url'):
            return  # silently skip — bean exists but _delegate stays None
        url = config.get(f'{p}.url')
        username = config.get(f'{p}.username') if config.has(f'{p}.username') else None
        password = config.get(f'{p}.password') if config.has(f'{p}.password') else None
        pool_enabled = config.has(f'{p}.pool.enabled') and config.get(f'{p}.pool.enabled')
        if pool_enabled:
            pool = {}
            for key in ('min', 'max'):
                if config.has(f'{p}.pool.{key}'):
                    pool[key] = config.get(f'{p}.pool.{key}')
            self._delegate = PooledDataSource(url, pool=pool)
        elif self._is_in_memory_url(url):
            self._delegate = SingleConnectionDataSource(url, username, password)
        else:
            self._delegate = DataSource(url, username, password)

    def get_connection(self):
        if self._delegate is None:
            raise RuntimeError('ConfiguredDataSource: no datasource configured')
        return self._delegate.get_connection()

    def get_url(self):
        return self._delegate.get_url() if self._delegate else None

    def destroy(self):
        if self._delegate and hasattr(self._delegate, 'destroy'):
            self._delegate.destroy()

    def _is_in_memory_url(self, url):
        return ':memory' in url


class SchemaInitializer:
    def __init__(self):
        self.data_source = None  # injected via CDI properties
        self._application_context = None
        self._prefix = DEFAULT_PREFIX

    def set_application_context(self, ctx):
        self._application_context = ctx

    def init(self):
        config = self._application_context.get('config')
        p = self._prefix
        if config.has(f'{p}.initialize') and not config.get(f'{p}.initialize'):
            return
        # If no datasource is configured, skip schema init silently
        if self.data_source is None or self.data_source._delegate is None:
            return
        schema_path = config.get(f'{p}.schema') if config.has(f'{p}.schema') else 'config/schema.sql'
        data_path = config.get(f'{p}.data') if config.has(f'{p}.data') else 'config/data.sql'
        conn = self.data_source.get_connection()
        self._run_file(conn, schema_path)
        self._run_file(conn, data_path)
        conn.close()  # Return connection to pool (no-op for SingleConnectionDataSource)

    def _run_file(self, conn, file_path):
        import os
        if not os.path.exists(file_path):
            return
        with open(file_path, 'r') as f:
            sql = f.read()
        statements = []
        for chunk in sql.split(';'):
            stripped = '\n'.join(
                line for line in chunk.split('\n')
                if not line.strip().startswith('--')
            ).strip()
            if stripped:
                statements.append(stripped)
        for stmt_sql in statements:
            stmt = conn.create_statement()
            stmt.execute(stmt_sql)
        conn.commit()


class DataSourceBuilder:
    def __init__(self):
        self._prefix = DEFAULT_PREFIX
        self._bean_names = {}
        self._include_schema_initializer = True

    @staticmethod
    def create():
        return DataSourceBuilder()

    def prefix(self, prefix):
        self._prefix = prefix
        return self

    def bean_names(self, names):
        self._bean_names.update(names)
        return self

    def without_schema_initializer(self):
        self._include_schema_initializer = False
        return self

    def build(self):
        prefix = self._prefix
        names = self._bean_names
        ds_name = names.get('data_source', 'data_source')
        jt_name = names.get('pydbc_template', 'pydbc_template')
        njt_name = names.get('named_parameter_pydbc_template', 'named_parameter_pydbc_template')
        si_name = names.get('schema_initializer', 'schema_initializer')

        class _BoundDS(ConfiguredDataSource):
            def __init__(self_):
                super().__init__()
                self_._prefix = prefix
        _BoundDS.__name__ = ds_name
        _BoundDS.__qualname__ = ds_name

        components = [
            Singleton({'reference': _BoundDS, 'name': ds_name}),
            Singleton({'reference': PydbcTemplate, 'name': jt_name,
                       'constructor_args': [ds_name], 'depends_on': ds_name}),
            Singleton({'reference': NamedParameterPydbcTemplate, 'name': njt_name,
                       'constructor_args': [ds_name], 'depends_on': ds_name}),
        ]
        if self._include_schema_initializer:
            class _BoundSI(SchemaInitializer):
                def __init__(self_):
                    super().__init__()
                    self_._prefix = prefix
            _BoundSI.__name__ = si_name
            _BoundSI.__qualname__ = si_name
            components.append(
                Singleton({'reference': _BoundSI, 'name': si_name,
                           'depends_on': ds_name,
                           'properties': [{'name': 'data_source', 'reference': ds_name}]})
            )
        return components


def pydbc_auto_configuration(prefix=DEFAULT_PREFIX):
    return DataSourceBuilder.create().prefix(prefix).build()


def pydbc_starter(prefix=DEFAULT_PREFIX):
    return pydbc_auto_configuration(prefix=prefix)


def pydbc_template_starter(options=None):
    options = options or {}
    from boot import Boot
    contexts = options.get('contexts', [])
    config = options.get('config')
    prefix = options.get('prefix', DEFAULT_PREFIX)
    return Boot.boot({
        'config': config,
        'contexts': [*contexts, pydbc_auto_configuration(prefix=prefix)],
        'run': False,
    })
