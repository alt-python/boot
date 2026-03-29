class NoteRepository:
    def __init__(self):
        self.pydbc_template = None  # CDI autowired — primary template

    def _map(self, row, _):
        return {k.lower(): v for k, v in row.items()}

    def find_all(self):
        return self.pydbc_template.query_for_list(
            'SELECT id, title, body, done FROM notes ORDER BY id',
            row_mapper=self._map,
        )

    def save(self, title, body=''):
        self.pydbc_template.update(
            'INSERT INTO notes (title, body) VALUES (?, ?)',
            (title, body),
        )
        row = self.pydbc_template.query_for_map('SELECT MAX(id) AS id FROM notes')
        return row.get('ID') or row.get('id')


class TagRepository:
    def __init__(self):
        self.tags_pydbc_template = None  # CDI autowired — secondary template

    def _map(self, row, _):
        return {k.lower(): v for k, v in row.items()}

    def find_all_tags(self):
        return self.tags_pydbc_template.query_for_list(
            'SELECT id, name FROM tags ORDER BY name',
            row_mapper=self._map,
        )

    def save_tag(self, name):
        self.tags_pydbc_template.update(
            'INSERT OR IGNORE INTO tags (name) VALUES (?)',
            (name,),
        )
        row = self.tags_pydbc_template.query_for_map(
            'SELECT id FROM tags WHERE name = ?', (name,)
        )
        return row.get('ID') or row.get('id')

    def tag_note(self, note_id, tag_id):
        self.tags_pydbc_template.update(
            'INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)',
            (note_id, tag_id),
        )

    def tags_for_note(self, note_id):
        return self.tags_pydbc_template.query_for_list(
            """SELECT t.id, t.name FROM tags t
               JOIN note_tags nt ON nt.tag_id = t.id
               WHERE nt.note_id = ?
               ORDER BY t.name""",
            (note_id,),
            row_mapper=self._map,
        )


class Application:
    def __init__(self):
        self.note_repository = None       # CDI autowired
        self.tag_repository = None        # CDI autowired
        self.managed_flyway = None        # CDI autowired — notes runner
        self.managed_flyway_tags = None   # CDI autowired — tags runner

    def run(self):
        # Both migrations ran during CDI init — show their histories
        notes_info = self.managed_flyway.get_flyway().info()
        print('\n── Notes DB migration history ─────────────────────')
        for m in notes_info:
            print(f"  V{m['version']} {m['description']:<30} [{m['state']}]")

        tags_info = self.managed_flyway_tags.get_flyway().info()
        print('\n── Tags DB migration history ──────────────────────')
        for m in tags_info:
            print(f"  V{m['version']} {m['description']:<30} [{m['state']}]")

        notes = self.note_repository.find_all()
        print('\n── Notes ──────────────────────────────────────────')
        for n in notes:
            print(f"  [{n['id']}] {n['title']}")

        tags = self.tag_repository.find_all_tags()
        print('\n── Tags ───────────────────────────────────────────')
        for t in tags:
            print(f"  [{t['id']}] {t['name']}")

        # Tag the first note as 'important' and 'work'
        important = next(t for t in tags if t['name'] == 'important')
        work = next(t for t in tags if t['name'] == 'work')
        self.tag_repository.tag_note(notes[0]['id'], important['id'])
        self.tag_repository.tag_note(notes[0]['id'], work['id'])

        note_tags = self.tag_repository.tags_for_note(notes[0]['id'])
        print(f"\n── Tags on note [{notes[0]['id']}] ──────────────────────────")
        for t in note_tags:
            print(f"  {t['name']}")
        print()
