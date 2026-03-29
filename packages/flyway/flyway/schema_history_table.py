"""
flyway.schema_history_table — manages the flyway_schema_history tracking table.

Flyway-inspired (https://flywaydb.org, Apache 2.0).
Mirrors the open-source Flyway schema history table structure:
  installed_rank, version, description, type, script, checksum,
  installed_by, installed_on, execution_time, success

Table name is configurable (default: flyway_schema_history).
Uses PydbcTemplate for all parameterized queries.
"""
from datetime import datetime, timezone


class SchemaHistoryTable:
    """Manage the Flyway schema history table via PydbcTemplate."""

    def __init__(self, template, table_name='flyway_schema_history'):
        """
        :param template: PydbcTemplate instance.
        :param table_name: History table name (default: flyway_schema_history).
        """
        self._template = template
        self._table_name = table_name

    @property
    def table_name(self):
        return self._table_name

    def provision(self):
        """Create the history table if it does not exist."""
        self._template.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                installed_rank  INTEGER NOT NULL,
                version         TEXT,
                description     TEXT    NOT NULL,
                type            TEXT    NOT NULL DEFAULT 'SQL',
                script          TEXT    NOT NULL,
                checksum        INTEGER,
                installed_by    TEXT    NOT NULL DEFAULT 'flyway',
                installed_on    TEXT    NOT NULL,
                execution_time  INTEGER NOT NULL DEFAULT 0,
                success         INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (installed_rank)
            )
        """)

    def find_all(self):
        """Return all migration records ordered by installed_rank."""
        rows = self._template.query_for_list(
            f'SELECT * FROM {self._table_name} ORDER BY installed_rank'
        )
        result = []
        for r in rows:
            row = {k.lower(): v for k, v in r.items()}
            row['success'] = bool(row['success'])
            result.append(row)
        return result

    def max_rank(self):
        """Return the maximum installed_rank, or 0 if the table is empty."""
        row = self._template.query_for_map(
            f'SELECT COALESCE(MAX(installed_rank), 0) AS max_rank FROM {self._table_name}'
        )
        normalized = {k.lower(): v for k, v in row.items()}
        return normalized.get('max_rank') or 0

    def insert(self, entry):
        """Record a migration entry. Returns the new installed_rank."""
        rank = self.max_rank() + 1
        self._template.update(
            f"""INSERT INTO {self._table_name}
                 (installed_rank, version, description, type, script, checksum,
                  installed_by, installed_on, execution_time, success)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rank,
                entry.get('version'),
                entry['description'],
                entry.get('type', 'SQL'),
                entry['script'],
                entry.get('checksum'),
                entry.get('installed_by', 'flyway'),
                datetime.now(timezone.utc).isoformat(),
                entry.get('execution_time', 0),
                1 if entry.get('success') else 0,
            ),
        )
        return rank

    def update_success(self, rank, success, execution_time):
        """Update success flag and execution_time for a row."""
        self._template.update(
            f'UPDATE {self._table_name} SET success = ?, execution_time = ? WHERE installed_rank = ?',
            (1 if success else 0, execution_time, rank),
        )

    def remove_failed_entries(self):
        """Delete all failed (success=0) rows. Used by repair()."""
        self._template.update(
            f'DELETE FROM {self._table_name} WHERE success = 0',
            (),
        )

    def drop(self):
        """Drop the history table. Used by clean()."""
        self._template.execute(f'DROP TABLE IF EXISTS {self._table_name}')

    def insert_baseline(self, version, description='Flyway Baseline'):
        """Insert a BASELINE record."""
        return self.insert({
            'version': version,
            'description': description,
            'type': 'BASELINE',
            'script': f'<< {description} >>',
            'checksum': None,
            'success': True,
        })
