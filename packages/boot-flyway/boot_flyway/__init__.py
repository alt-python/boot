"""
alt-python-boot-flyway — Flyway-inspired migration starter for alt-python/boot.

Registers a ManagedFlyway CDI bean that calls migrate() synchronously during
CDI init(), reading all settings from boot.flyway.* config.

Usage:
    import pydbc_sqlite
    from boot import Boot
    from cdi import Context, Singleton
    from boot_pydbc import pydbc_auto_configuration
    from boot_flyway import flyway_starter

    Boot.boot({
        'contexts': [
            Context(pydbc_auto_configuration() + flyway_starter()),
            Context([Singleton(MyRepository), Singleton(MyApp)]),
        ]
    })

Config keys (prefix: boot.flyway):
  boot.flyway.enabled              — enable on start (default: true)
  boot.flyway.locations            — comma-separated paths (default: db/migration)
  boot.flyway.table                — history table name (default: flyway_schema_history)
  boot.flyway.baseline-on-migrate  — baseline if history empty (default: false)
  boot.flyway.baseline-version     — baseline version (default: '1')
  boot.flyway.out-of-order         — allow out-of-order (default: false)
  boot.flyway.validate-on-migrate  — checksum validation (default: true)
  boot.flyway.installed-by         — user in history (default: 'flyway')
"""

from boot_flyway.flyway_auto_configuration import (
    ManagedFlyway,
    flyway_auto_configuration,
    flyway_starter,
    DEFAULT_FLYWAY_PREFIX,
)

__all__ = [
    'ManagedFlyway',
    'flyway_auto_configuration',
    'flyway_starter',
    'DEFAULT_FLYWAY_PREFIX',
]
