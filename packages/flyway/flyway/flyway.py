"""
flyway.flyway — database migration engine.

Inspired by Flyway (https://flywaydb.org) by Redgate Software Ltd,
Apache License 2.0.  Implements the open-source feature set only:

  migrate()   — apply all pending versioned migrations
  info()      — return migration status report
  validate()  — detect checksum drift between files and history
  baseline()  — mark current database state as a known baseline
  repair()    — remove failed migration records from history table
  clean()     — drop the schema history table (destructive)

NOT implemented (premium/proprietary): undo, dry-run, batched execution,
cherry-pick, teams/enterprise features.

Conventions (Flyway OSS naming):
  V{version}__{description}.sql   — versioned migration
  flyway_schema_history            — default history table name
"""
import time

from flyway.migration import MigrationState, MigrationVersion
from flyway.migration_loader import MigrationLoader
from flyway.migration_executor import MigrationExecutor
from flyway.schema_history_table import SchemaHistoryTable


class Flyway:
    """Database migration engine.

    :param data_source: pydbc DataSource instance (required).
    :param template: PydbcTemplate to use (constructed from data_source if not provided).
    :param locations: List of migration file paths (default: ['db/migration']).
    :param table: History table name (default: 'flyway_schema_history').
    :param baseline_version: Version for baseline() (default: '1').
    :param baseline_description: Baseline description.
    :param out_of_order: Allow out-of-order migrations (default: False).
    :param validate_on_migrate: Validate checksums before migrating (default: True).
    :param installed_by: User recorded in history (default: 'flyway').
    """

    def __init__(self, data_source, template=None, locations=None, table=None,
                 baseline_version='1', baseline_description='Flyway Baseline',
                 out_of_order=False, validate_on_migrate=True, installed_by='flyway'):
        if data_source is None:
            raise FlywayError('Flyway requires a data_source')
        self._data_source = data_source
        if template is None:
            from boot_pydbc import PydbcTemplate
            template = PydbcTemplate(data_source)
        self._template = template
        self._locations = ['db/migration'] if locations is None else (
            [locations] if isinstance(locations, str) else list(locations)
        )
        self._table = table or 'flyway_schema_history'
        self._baseline_version = baseline_version
        self._baseline_description = baseline_description
        self._out_of_order = out_of_order
        self._validate_on_migrate = validate_on_migrate
        self._installed_by = installed_by

        self._loader = MigrationLoader(self._locations)
        self._executor = MigrationExecutor()
        self._history = SchemaHistoryTable(self._template, self._table)

    # ── Public API ────────────────────────────────────────────────────────

    def migrate(self):
        """Apply all pending migrations in version order.

        :returns: dict with keys migrationsExecuted (int) and appliedMigrations (list).
        :raises FlywayValidationError: if validate_on_migrate=True and checksums differ.
        :raises FlywayMigrationError: if a migration SQL fails.
        """
        self._history.provision()
        available = self._loader.load()
        applied = self._history.find_all()

        if self._validate_on_migrate:
            self._validate(available, applied)

        pending = self._get_pending(available, applied)
        applied_migrations = []

        for migration in pending:
            start = time.monotonic()
            rank = self._history.insert({
                'version': str(migration['version']),
                'description': migration['description'],
                'script': migration['script'],
                'checksum': migration['checksum'],
                'installed_by': self._installed_by,
                'success': False,
            })

            try:
                self._executor.execute_with_template(self._template, migration['sql'])
                elapsed_ms = int((time.monotonic() - start) * 1000)
                self._history.update_success(rank, True, elapsed_ms)
                applied_migrations.append({
                    'version': str(migration['version']),
                    'description': migration['description'],
                    'script': migration['script'],
                    'execution_time': elapsed_ms,
                    'state': MigrationState.SUCCESS,
                })
            except Exception as err:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                self._history.update_success(rank, False, elapsed_ms)
                raise FlywayMigrationError(migration, err) from err

        return {
            'migrations_executed': len(applied_migrations),
            'applied_migrations': applied_migrations,
        }

    def info(self):
        """Return a status report for all migrations (applied + pending).

        :returns: list of dicts with keys version, description, script,
                  checksum, state, installed_on, execution_time.
        """
        self._history.provision()
        available = self._loader.load()
        applied = self._history.find_all()

        applied_by_version = {
            r['version']: r for r in applied if r.get('version')
        }

        result = []
        for m in available:
            rec = applied_by_version.get(str(m['version']))
            if rec is None:
                state = MigrationState.PENDING
            elif rec['success']:
                state = MigrationState.SUCCESS
            else:
                state = MigrationState.FAILED
            result.append({
                'version': str(m['version']),
                'description': m['description'],
                'script': m['script'],
                'checksum': m['checksum'],
                'state': state,
                'installed_on': rec.get('installed_on') if rec else None,
                'execution_time': rec.get('execution_time') if rec else None,
            })
        return result

    def validate(self):
        """Validate applied migration checksums match the files on disk.

        :raises FlywayValidationError: on checksum mismatch.
        """
        self._history.provision()
        available = self._loader.load()
        applied = self._history.find_all()
        self._validate(available, applied)

    def baseline(self):
        """Mark the current database state as a baseline.

        :raises FlywayError: if the history table is not empty.
        """
        self._history.provision()
        existing = self._history.find_all()
        if existing:
            raise FlywayError(
                'Cannot baseline a non-empty schema history. '
                'Use repair() to clear failed entries first.'
            )
        self._history.insert_baseline(self._baseline_version, self._baseline_description)

    def repair(self):
        """Remove failed migration entries from the history table.

        :returns: dict with key removed_entries (int).
        """
        self._history.provision()
        before = self._history.find_all()
        failed_count = sum(1 for r in before if not r['success'])
        self._history.remove_failed_entries()
        return {'removed_entries': failed_count}

    def clean(self):
        """Drop the flyway schema history table.

        DESTRUCTIVE — does not drop application tables.
        Intended for development/test environments only.
        """
        self._history.drop()

    # ── Private helpers ───────────────────────────────────────────────────

    def _get_pending(self, available, applied):
        """Return migrations not yet successfully applied."""
        applied_versions = {
            r['version'] for r in applied if r['success'] and r.get('version')
        }
        pending = [m for m in available if str(m['version']) not in applied_versions]

        if not self._out_of_order:
            successful_versions = [
                r['version'] for r in applied if r['success'] and r.get('version')
            ]
            if successful_versions:
                max_applied = max(
                    (MigrationVersion.parse(v) for v in successful_versions)
                )
                pending = [m for m in pending if m['version'].compare_to(max_applied) > 0]

        return pending

    def _validate(self, available, applied):
        """Check applied migrations have matching checksums on disk.

        :raises FlywayValidationError: on mismatch.
        """
        available_by_version = {str(m['version']): m for m in available}
        for rec in applied:
            if not rec.get('version') or rec.get('type') == 'BASELINE':
                continue
            if not rec['success']:
                continue
            file_migration = available_by_version.get(rec['version'])
            if file_migration is None:
                continue  # file deleted — warn-only in OSS Flyway
            if file_migration['checksum'] != rec.get('checksum'):
                raise FlywayValidationError(
                    f"Migration checksum mismatch for version {rec['version']} "
                    f"({rec['script']}). "
                    f"Expected {rec.get('checksum')}, got {file_migration['checksum']}. "
                    'The migration file was modified after it was applied.'
                )


# ── Error types ───────────────────────────────────────────────────────────

class FlywayError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.name = 'FlywayError'


class FlywayValidationError(FlywayError):
    def __init__(self, message):
        super().__init__(message)
        self.name = 'FlywayValidationError'


class FlywayMigrationError(FlywayError):
    def __init__(self, migration, cause):
        super().__init__(f"Migration {migration['script']} failed: {cause}")
        self.name = 'FlywayMigrationError'
        self.migration = migration
        self.cause = cause
