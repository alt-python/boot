import os
import pydbc_sqlite  # self-registers SQLite driver with DriverManager
from boot import Boot
from boot_pydbc import pydbc_auto_configuration
from cdi import Context, Singleton
from services import NoteRepository, Application

# Change to this file's directory so config/ and schema.sql are found correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

Boot.boot({
    'contexts': [
        Context([Singleton(NoteRepository), Singleton(Application)]),
        Context(pydbc_auto_configuration()),
    ],
})
