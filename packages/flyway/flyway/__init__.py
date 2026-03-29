"""
alt-python-flyway — database migration engine.

Flyway-inspired versioned SQL migration engine for Python.
Port of @alt-javascript/flyway (Apache 2.0).

Usage:
    import pydbc_sqlite  # register driver
    from pydbc_core import PooledDataSource
    from flyway import Flyway

    ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 1})
    flyway = Flyway(data_source=ds, locations=['db/migration'])
    result = flyway.migrate()
    # result: {'migrations_executed': 3, 'applied_migrations': [...]}
"""

from flyway.flyway import Flyway, FlywayError, FlywayValidationError, FlywayMigrationError
from flyway.migration import MigrationState, MigrationVersion
from flyway.migration_loader import MigrationLoader, checksum
from flyway.migration_executor import MigrationExecutor
from flyway.schema_history_table import SchemaHistoryTable

__all__ = [
    'Flyway',
    'FlywayError',
    'FlywayValidationError',
    'FlywayMigrationError',
    'MigrationState',
    'MigrationVersion',
    'MigrationLoader',
    'MigrationExecutor',
    'SchemaHistoryTable',
    'checksum',
]
