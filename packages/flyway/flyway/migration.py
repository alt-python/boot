"""
flyway.migration — value types for versioned migration records.

Inspired by Flyway OSS (https://flywaydb.org, Apache 2.0).
"""


class MigrationState:
    """Migration state constants (mirrors Flyway OSS state names)."""
    PENDING = 'PENDING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    BASELINE = 'BASELINE'


class MigrationVersion:
    """Parsed migration version — wraps a dot-separated version string.

    Flyway convention: V{major}[.{minor}[.{patch}...]}__{description}.sql
    Versions are compared numerically segment by segment: 1 < 1.1 < 2 < 10.
    """

    def __init__(self, raw):
        self.raw = str(raw)
        self._segments = [int(s) for s in str(raw).split('.')]

    def compare_to(self, other):
        """Return negative if self < other, positive if self > other, 0 if equal."""
        a = self._segments
        b = other._segments
        length = max(len(a), len(b))
        for i in range(length):
            diff = (a[i] if i < len(a) else 0) - (b[i] if i < len(b) else 0)
            if diff != 0:
                return diff
        return 0

    def __lt__(self, other):
        return self.compare_to(other) < 0

    def __eq__(self, other):
        return self.compare_to(other) == 0

    def __str__(self):
        return self.raw

    def __repr__(self):
        return f'MigrationVersion({self.raw!r})'

    @staticmethod
    def parse(raw):
        return MigrationVersion(raw)
