class NoteRepository:
    def __init__(self):
        self.pydbc_template = None  # CDI autowired

    def _map(self, row, _):
        return {k.lower(): v for k, v in row.items()}

    def find_all(self):
        """Return all notes ordered by priority desc, then id."""
        return self.pydbc_template.query_for_list(
            'SELECT id, title, body, done, priority FROM notes ORDER BY priority DESC, id',
            row_mapper=self._map,
        )

    def find_by_id(self, note_id):
        results = self.pydbc_template.query_for_list(
            'SELECT id, title, body, done, priority FROM notes WHERE id = ?',
            (note_id,),
            row_mapper=self._map,
        )
        return results[0] if results else None

    def save(self, title, body='', priority=0):
        """Insert a new note and return its generated id."""
        self.pydbc_template.update(
            'INSERT INTO notes (title, body, priority) VALUES (?, ?, ?)',
            (title, body, priority),
        )
        row = self.pydbc_template.query_for_map('SELECT MAX(id) AS id FROM notes')
        return row.get('ID') or row.get('id')

    def mark_done(self, note_id):
        self.pydbc_template.update(
            'UPDATE notes SET done = 1 WHERE id = ?',
            (note_id,),
        )

    def remove(self, note_id):
        return self.pydbc_template.update(
            'DELETE FROM notes WHERE id = ?',
            (note_id,),
        )


class Application:
    def __init__(self):
        self.note_repository = None   # CDI autowired
        self.managed_flyway = None    # CDI autowired

    def run(self):
        flyway = self.managed_flyway.get_flyway()
        info = flyway.info()

        print('\n── Migration history ──────────────────────────────')
        for m in info:
            print(f"  V{m['version']} {m['description']:<35} [{m['state']}]")

        notes = self.note_repository.find_all()
        print('\n── Notes (seeded by V3 migration) ────────────────')
        for n in notes:
            print(f"  [{n['id']}] P{n['priority']} {n['title']}")

        new_id = self.note_repository.save('Runtime note', 'Added after migration.', 0)
        self.note_repository.mark_done(notes[0]['id'])

        updated = self.note_repository.find_all()
        print('\n── After update ───────────────────────────────────')
        for n in updated:
            status = '✓' if n['done'] else '○'
            print(f"  [{n['id']}] {status} {n['title']}")

        self.note_repository.remove(new_id)
        print('\n── After remove ───────────────────────────────────')
        for n in self.note_repository.find_all():
            status = '✓' if n['done'] else '○'
            print(f"  [{n['id']}] {status} {n['title']}")
        print()
