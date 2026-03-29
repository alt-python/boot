class NoteRepository:
    def __init__(self):
        self.pydbc_template = None  # CDI autowires by name

    def _row_mapper(self, row, _):
        return {k.lower(): v for k, v in row.items()}

    def find_all(self):
        return self.pydbc_template.query_for_list(
            'SELECT id, title, body, done FROM notes ORDER BY id',
            row_mapper=self._row_mapper,
        )

    def find_by_id(self, note_id):
        results = self.pydbc_template.query_for_list(
            'SELECT id, title, body, done FROM notes WHERE id = ?',
            (note_id,),
            row_mapper=self._row_mapper,
        )
        return results[0] if results else None

    def save(self, title, body=''):
        """Insert a new note and return its generated id."""
        self.pydbc_template.update(
            'INSERT INTO notes (title, body) VALUES (?, ?)',
            (title, body),
        )
        row = self.pydbc_template.query_for_map(
            'SELECT MAX(id) AS id FROM notes',
        )
        return row['ID'] if 'ID' in row else row['id']

    def mark_done(self, note_id):
        self.pydbc_template.update(
            'UPDATE notes SET done = 1 WHERE id = ?',
            (note_id,),
        )

    def remove(self, note_id):
        """Delete a note by id. Returns affected row count."""
        return self.pydbc_template.update(
            'DELETE FROM notes WHERE id = ?',
            (note_id,),
        )


class Application:
    def __init__(self):
        self.note_repository = None  # CDI autowires by name

    def run(self):
        print()
        print('── All notes (seeded by SchemaInitializer) ────────')
        for note in self.note_repository.find_all():
            status = '✓' if note['done'] else '○'
            print(f"  [{status}] {note['id']}. {note['title']}")

        # Add a new note
        new_id = self.note_repository.save(
            'Created at runtime',
            'Added after SchemaInitializer seeded the table.',
        )
        print(f"\n── Created note id={new_id} ─────────────────────────")

        # Mark the first note done
        self.note_repository.mark_done(1)

        # Batch-insert two more notes
        self.note_repository.pydbc_template.batch_update(
            'INSERT INTO notes (title, body) VALUES (?, ?)',
            [
                ('Batch note A', 'inserted in a batch'),
                ('Batch note B', 'also in the batch'),
            ],
        )
        print()
        print('── After batch insert ─────────────────────────────')
        for note in self.note_repository.find_all():
            status = '✓' if note['done'] else '○'
            print(f"  [{status}] {note['id']}. {note['title']}")

        # Remove the runtime note
        self.note_repository.remove(new_id)
        print()
        print('── After remove ───────────────────────────────────')
        for note in self.note_repository.find_all():
            status = '✓' if note['done'] else '○'
            print(f"  [{status}] {note['id']}. {note['title']}")
        print()
