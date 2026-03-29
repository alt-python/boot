# Getting Started

This tutorial walks you through building a working application with `alt-python/boot`. By the end, you'll have a service with dependency injection, configuration, logging, and lifecycle hooks — all wired in one call.

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) (or pip)

## Install

```bash
mkdir my-app && cd my-app
uv init --no-package
uv add alt-python-boot-lib alt-python-cdi alt-python-config alt-python-logger
```

Create `config/application.yaml`:

```yaml
logging:
  level:
    /:   info
app:
  name: My First App
```

## Step 1: Define your components

Create `services.py`:

```python
class GreetingRepository:
    def __init__(self):
        self._greetings = ["Hello", "Hi", "Hey"]

    def get_random(self):
        import random
        return random.choice(self._greetings)


class GreetingService:
    def __init__(self):
        self.greeting_repository = None  # CDI-autowired by name

    def greet(self, name: str) -> str:
        return f"{self.greeting_repository.get_random()}, {name}!"
```

The key pattern: `GreetingService` declares `greeting_repository = None`. CDI
matches this property name to the registered `GreetingRepository` singleton and
injects the instance automatically.

## Step 2: Wire and run with Boot

Create `main.py`:

```python
from boot import Boot
from cdi import Context, Singleton
from services import GreetingRepository, GreetingService


class Application:
    def __init__(self):
        self.greeting_service = None  # CDI-autowired

    def run(self):
        print(self.greeting_service.greet("World"))


Boot.boot({
    'contexts': [
        Context([
            Singleton(GreetingRepository),
            Singleton(GreetingService),
            Singleton(Application),
        ])
    ]
})
```

Run it:

```bash
uv run python main.py
# Output: Hello, World!  (or Hi, World! or Hey, World!)
```

`Boot.boot()` loads `config/application.yaml`, prints the startup banner, wires
all CDI beans, and calls `application.run()`.

## Step 3: Add lifecycle hooks

Beans can implement `init()` for startup logic and `destroy()` for cleanup:

```python
class GreetingService:
    def __init__(self):
        self.greeting_repository = None
        self._call_count = 0

    def init(self):
        print("GreetingService ready")

    def greet(self, name: str) -> str:
        self._call_count += 1
        return f"{self.greeting_repository.get_random()}, {name}!"

    def destroy(self):
        print(f"GreetingService stopping. Total greetings: {self._call_count}")
```

CDI calls `init()` after wiring all beans. `destroy()` is called on SIGINT or
when the context stops.

## Step 4: Read config values

Inject config values using placeholder strings in `__init__`:

```python
class GreetingService:
    def __init__(self):
        self.greeting_repository = None  # CDI-autowired
        self.app_name = '${app.name:My App}'  # resolved from config
```

CDI resolves `${app.name:My App}` against the live config bean before calling
`init()`. The `:My App` suffix is the default if the key is absent.

## Step 5: Use the config and logger singletons directly

For code outside a CDI bean, use the module-level singletons directly:

```python
from config import config
from logger import logger_factory

log = logger_factory.get_logger("my.app.main")

port = config.get("server.port", 8080)
log.info(f"Starting on port {port}")
```

## What's next

- [Configuration](configuration.md) — file formats, profiles, environment variables, encrypted values
- [Dependency Injection](dependency-injection.md) — scopes, profiles, explicit wiring, lifecycle
- [Lifecycle](lifecycle.md) — full lifecycle sequence, events, BeanPostProcessor
- [Database Access](database.md) — PydbcTemplate, Flyway migrations, secondary datasources
- [Spring Comparison](spring-comparison.md) — mapping Spring concepts to alt-python equivalents
