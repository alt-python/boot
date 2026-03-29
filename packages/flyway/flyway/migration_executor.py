"""
flyway.migration_executor — applies a single migration SQL against a pydbc Connection.

Each SQL file may contain multiple statements separated by semicolons.
Statements are executed sequentially; the first failure aborts and rethrows.

Flyway-inspired (https://flywaydb.org, Apache 2.0).
"""


class MigrationExecutor:
    """Execute all SQL statements in a migration against an open pydbc Connection."""

    def execute(self, conn, sql: str) -> None:
        """Execute all statements in *sql* using *conn*.

        :param conn: Open pydbc Connection.
        :param sql: Full SQL file content, may contain multiple statements.
        """
        for stmt_sql in self._split(sql):
            stmt = conn.create_statement()
            stmt.execute(stmt_sql)
        conn.commit()

    def execute_with_template(self, template, sql: str) -> None:
        """Execute all statements in *sql* via *template*.

        Uses template.execute() per statement so each call acquires and
        releases its own connection — safe with PooledDataSource(max=1).
        """
        for stmt_sql in self._split(sql):
            template.execute(stmt_sql)

    @staticmethod
    def _split(sql: str):
        """Split SQL content into individual non-empty statements.

        Strips SQL line comments (-- ...) and blank lines, splits on ';'.
        """
        statements = []
        for chunk in sql.split(';'):
            lines = [
                line for line in chunk.split('\n')
                if not line.strip().startswith('--')
            ]
            stripped = '\n'.join(lines).strip()
            if stripped:
                statements.append(stripped)
        return statements
