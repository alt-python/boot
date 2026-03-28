import os
import pynosqlc.memory  # self-registers MemoryDriver with DriverManager
from boot import Boot
from boot_pynosqlc import pynosqlc_auto_configuration
from cdi import Context, Singleton
from services import NoteRepository, Application

# Change to this file's directory so config/ is found correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

Boot.boot({
    'contexts': [
        Context([Singleton(NoteRepository), Singleton(Application)]),
        Context(pynosqlc_auto_configuration()),
    ],
})
