import asyncio


class NoteRepository:
    def __init__(self):
        self.nosql_client = None  # CDI autowired

    async def find_all(self):
        col = self.nosql_client.get_collection('notes')  # sync
        cursor = await col.find({'type': 'and', 'conditions': []})
        return cursor.get_documents()  # sync — do NOT await

    async def store(self, key, note):
        col = self.nosql_client.get_collection('notes')
        await col.store(key, note)


class Application:
    def __init__(self):
        self.note_repository = None  # CDI autowired

    def run(self):
        asyncio.run(self._run_async())

    async def _run_async(self):
        # Seed notes
        await self.note_repository.store('1', {'id': 1, 'title': 'Learn alt-python/boot', 'done': False})
        await self.note_repository.store('2', {'id': 2, 'title': 'Try persistence with pynosqlc', 'done': False})
        await self.note_repository.store('3', {'id': 3, 'title': 'Explore NoSQL patterns', 'done': True})

        notes = await self.note_repository.find_all()
        print('\n--- All Notes ---')
        for note in notes:
            status = '\u2713' if note.get('done') else '\u25cb'
            print(f"  [{status}] {note.get('id', '?')}. {note.get('title', '')}")
