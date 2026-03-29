"""
flyway.migration_loader — discovers and parses versioned SQL migration files.

Flyway-inspired (https://flywaydb.org, Apache 2.0).
Naming convention: V{version}__{description}.sql
  e.g. V1__create_notes_table.sql
       V1.1__add_index.sql
       V2__seed_data.sql

Files are sorted by version (numeric, segment-aware) before return.
Repeatable migrations (R__description.sql) are not supported.
"""
import os
import re
import binascii

from flyway.migration import MigrationVersion

# Matches: V{version}__{description}.sql (case-insensitive)
_VERSIONED_PATTERN = re.compile(r'^V([0-9]+(?:\.[0-9]+)*)__(.+)\.sql$', re.IGNORECASE)


def checksum(content: str) -> int:
    """Compute a CRC32 checksum of *content* (UTF-8 encoded).

    Returns a signed 32-bit integer.  Used only for migration drift detection —
    not a cryptographic hash.  Matches Flyway's intent (not its exact impl).
    """
    raw = binascii.crc32(content.encode('utf-8'))
    # Convert to signed 32-bit int (same range as JS's (crc ^ 0xFFFFFFFF) | 0)
    if raw > 0x7FFFFFFF:
        raw -= 0x100000000
    return raw


class MigrationLoader:
    """Discover and parse versioned SQL migration files from filesystem paths."""

    def __init__(self, locations=None):
        if locations is None:
            locations = ['db/migration']
        self.locations = [locations] if isinstance(locations, str) else list(locations)

    def load(self):
        """Load all versioned migrations from all configured locations.

        Files are sorted by version ascending across all locations.
        Non-existent locations are silently skipped.

        Returns a list of migration dicts with keys:
            version (MigrationVersion), description (str), script (str),
            sql (str), checksum (int), type (str)
        """
        migrations = []

        for loc in self.locations:
            if not os.path.isdir(loc):
                continue
            for filename in os.listdir(loc):
                match = _VERSIONED_PATTERN.match(filename)
                if not match:
                    continue
                version_raw = match.group(1)
                description = match.group(2).replace('_', ' ')
                file_path = os.path.join(loc, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    sql = f.read()
                migrations.append({
                    'version': MigrationVersion.parse(version_raw),
                    'description': description,
                    'script': filename,
                    'sql': sql,
                    'checksum': checksum(sql),
                    'type': 'SQL',
                })

        migrations.sort(key=lambda m: m['version'])
        return migrations
