import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pydbc_sqlite  # noqa: F401 — registers SQLiteDriver
from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration
from boot_flyway import flyway_starter

from services import NoteRepository, Application

Boot.boot({
    'contexts': [
        Context(pydbc_auto_configuration() + flyway_starter()),
        Context([Singleton(NoteRepository), Singleton(Application)]),
    ]
})
