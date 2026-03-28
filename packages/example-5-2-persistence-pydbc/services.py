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

    def mark_done(self, note_id):
        self.pydbc_template.update(
            'UPDATE notes SET done = 1 WHERE id = ?',
            (note_id,),
        )


class Application:
    def __init__(self):
        self.note_repository = None  # CDI autowires by name

    def run(self):
        print()
        print('--- All Notes ---')
        for note in self.note_repository.find_all():
            status = '✓' if note['done'] else '○'
            print(f"  [{status}] {note['id']}. {note['title']}")

        self.note_repository.mark_done(1)

        print()
        print('--- Updated Notes ---')
        for note in self.note_repository.find_all():
            status = '✓' if note['done'] else '○'
            print(f"  [{status}] {note['id']}. {note['title']}")
        print()
