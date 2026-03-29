"""
boot_flyway.flyway_auto_configuration — CDI auto-configuration for Flyway migrations.

Registers a ManagedFlyway bean that runs migrate() synchronously during CDI init().
Reads all configuration from boot.flyway.* (configurable prefix).

Config keys (prefix: boot.flyway):
  {prefix}.enabled              — enable migration on start (default: true)
  {prefix}.locations            — comma-separated migration paths (default: db/migration)
  {prefix}.table                — history table name (default: flyway_schema_history)
  {prefix}.baseline-on-migrate  — baseline() if history is empty (default: false)
  {prefix}.baseline-version     — version for baseline (default: '1')
  {prefix}.baseline-description — baseline description
  {prefix}.out-of-order         — allow out-of-order migrations (default: false)
  {prefix}.validate-on-migrate  — checksum validation (default: true)
  {prefix}.installed-by         — user recorded in history (default: 'flyway')
  {prefix}.datasource           — name of the data_source CDI bean (default: 'data_source')
"""
from cdi import Singleton
from flyway import Flyway
from boot_pydbc import PydbcTemplate

DEFAULT_FLYWAY_PREFIX = 'boot.flyway'


class ManagedFlyway:
    """CDI-managed Flyway migration runner.

    Reads configuration from the application context and calls migrate()
    during the synchronous CDI init() lifecycle phase.
    """

    def __init__(self):
        self.data_source = None          # CDI-wired via properties
        self._application_context = None
        self._prefix = DEFAULT_FLYWAY_PREFIX
        self._flyway = None

    def set_application_context(self, ctx):
        self._application_context = ctx

    def init(self):
        """Run Flyway migrate() synchronously.

        CDI calls init() synchronously — migrations are complete before
        any downstream bean's init() runs.
        """
        config = self._application_context.get('config')
        p = self._prefix

        if config.has(f'{p}.enabled') and not config.get(f'{p}.enabled'):
            return

        locations_raw = config.get(f'{p}.locations') if config.has(f'{p}.locations') else 'db/migration'
        locations = [loc.strip() for loc in str(locations_raw).split(',')]

        kwargs = {
            'locations': locations,
        }
        if config.has(f'{p}.table'):
            kwargs['table'] = config.get(f'{p}.table')
        if config.has(f'{p}.baseline-version'):
            kwargs['baseline_version'] = config.get(f'{p}.baseline-version')
        if config.has(f'{p}.baseline-description'):
            kwargs['baseline_description'] = config.get(f'{p}.baseline-description')
        if config.has(f'{p}.out-of-order'):
            kwargs['out_of_order'] = config.get(f'{p}.out-of-order')
        if config.has(f'{p}.validate-on-migrate'):
            kwargs['validate_on_migrate'] = config.get(f'{p}.validate-on-migrate')
        if config.has(f'{p}.installed-by'):
            kwargs['installed_by'] = config.get(f'{p}.installed-by')

        template = PydbcTemplate(self.data_source)
        self._flyway = Flyway(data_source=self.data_source, template=template, **kwargs)

        baseline_on_migrate = (
            config.has(f'{p}.baseline-on-migrate')
            and config.get(f'{p}.baseline-on-migrate')
        )
        if baseline_on_migrate:
            self._flyway._history.provision()
            existing = self._flyway._history.find_all()
            if not existing:
                self._flyway.baseline()

        self._flyway.migrate()

    def get_flyway(self):
        """Return the underlying Flyway instance (for info/validate/repair in app code)."""
        return self._flyway

    def destroy(self):
        pass


def flyway_auto_configuration(prefix=DEFAULT_FLYWAY_PREFIX, datasource_bean='data_source'):
    """Return CDI Singleton beans that auto-configure Flyway migration.

    :param prefix: Config key prefix (default: 'boot.flyway').
    :param datasource_bean: CDI bean name of the DataSource to wire (default: 'data_source').
    :returns: List containing one Singleton for ManagedFlyway.
    """
    class _BoundManagedFlyway(ManagedFlyway):
        def __init__(self_):
            super().__init__()
            self_._prefix = prefix
    _BoundManagedFlyway.__name__ = 'managedFlyway'
    _BoundManagedFlyway.__qualname__ = 'managedFlyway'

    return [
        Singleton({
            'reference': _BoundManagedFlyway,
            'name': 'managed_flyway',
            'depends_on': datasource_bean,
            'properties': [{'name': 'data_source', 'reference': datasource_bean}],
        }),
    ]


def flyway_starter(prefix=DEFAULT_FLYWAY_PREFIX, datasource_bean='data_source'):
    """Alias for flyway_auto_configuration()."""
    return flyway_auto_configuration(prefix=prefix, datasource_bean=datasource_bean)
