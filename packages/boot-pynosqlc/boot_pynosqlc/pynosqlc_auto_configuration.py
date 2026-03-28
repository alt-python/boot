from pynosqlc.core import ClientDataSource, DriverManager  # noqa: F401
from cdi import Singleton

DEFAULT_NOSQL_PREFIX = 'boot.nosql'


class ConfiguredClientDataSource:
    def __init__(self):
        self._delegate = None
        self._application_context = None
        self._prefix = DEFAULT_NOSQL_PREFIX

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
        self._delegate = ClientDataSource({'url': url, 'username': username, 'password': password})

    async def get_client(self):
        return await self._delegate.get_client()

    def get_url(self):
        return self._delegate.get_url() if self._delegate else None

    def destroy(self):
        pass  # ManagedNosqlClient owns the client lifecycle


class ManagedNosqlClient:
    def __init__(self):
        self.nosql_client_data_source = None  # CDI-autowired via properties
        self._client = None
        self._application_context = None

    def set_application_context(self, ctx):
        self._application_context = ctx

    def init(self):
        if self.nosql_client_data_source._delegate is None:
            return  # no URL configured — skip silently
        import asyncio
        asyncio.run(self._connect())

    async def _connect(self):
        self._client = await self.nosql_client_data_source.get_client()

    async def ready(self):
        pass  # kept for API parity with JS, no-op

    def get_collection(self, name):
        if self._client is None:
            raise RuntimeError('NoSQL client not ready')
        return self._client.get_collection(name)

    def destroy(self):
        if self._client is not None:
            import asyncio
            asyncio.run(self._client.close())


class NoSqlClientBuilder:
    def __init__(self):
        self._prefix = DEFAULT_NOSQL_PREFIX
        self._bean_names = {}

    @staticmethod
    def create():
        return NoSqlClientBuilder()

    def prefix(self, prefix):
        self._prefix = prefix
        return self

    def bean_names(self, names):
        self._bean_names.update(names)
        return self

    def build(self):
        prefix = self._prefix
        names = self._bean_names
        ds_name = names.get('nosql_client_data_source', 'nosql_client_data_source')
        client_name = names.get('nosql_client', 'nosql_client')

        class _BoundCDS(ConfiguredClientDataSource):
            def __init__(self_):
                super().__init__()
                self_._prefix = prefix
        _BoundCDS.__name__ = ds_name
        _BoundCDS.__qualname__ = ds_name

        class _BoundMC(ManagedNosqlClient):
            pass
        _BoundMC.__name__ = client_name
        _BoundMC.__qualname__ = client_name

        return [
            Singleton({'reference': _BoundCDS, 'name': ds_name}),
            Singleton({'reference': _BoundMC, 'name': client_name,
                       'depends_on': ds_name,
                       'properties': [{'name': 'nosql_client_data_source', 'reference': ds_name}]}),
        ]


def pynosqlc_auto_configuration(prefix=DEFAULT_NOSQL_PREFIX):
    return NoSqlClientBuilder.create().prefix(prefix).build()


def pynosqlc_starter(prefix=DEFAULT_NOSQL_PREFIX):
    return pynosqlc_auto_configuration(prefix=prefix)


def pynosqlc_boot(options=None):
    options = options or {}
    from boot import Boot
    contexts = options.get('contexts', [])
    config = options.get('config')
    prefix = options.get('prefix', DEFAULT_NOSQL_PREFIX)
    return Boot.boot({
        'config': config,
        'contexts': [*contexts, *pynosqlc_auto_configuration(prefix=prefix)],
        'run': False,
    })
