"""
example-1-1-intro-config

Introduces alt-python/config in isolation.

Key concepts:
  - ``from config import config`` gives you a ProfileConfigLoader-backed config instance,
    ready to use with no setup. Reads config files from the current directory.
  - .has(path) / .get(path, default) interface
  - PY_ACTIVE_PROFILES selects overlay files (application-{profile}.yaml, .json, .properties)
  - application.properties (top-level) + config/application.json can coexist
  - ENC(...) values are decrypted transparently (jasypt-compatible)

Config files in this example:
  application.properties       — top-level; shows .properties format + ENC() encryption
  config/application.json      — JSON format; provides greeting, port, retries
  config/application-dev.yaml  — YAML format dev overlay; overrides greeting + port

Run:
  python main.py                          # uses application.json + application.properties (default)
  PY_ACTIVE_PROFILES=dev python main.py   # overlays application-dev.yaml (G'day, port 9090)
"""

from config import config

app_name = config.get("app.name")
greeting = config.get("app.greeting")
port = config.get("server.port")
max_retries = config.get("app.max_retries", 5)  # default used if not in config
secret = config.get("app.secret", "not-set")    # ENC(...) decrypted transparently

print(f"App:       {app_name}")
print(f"Greeting:  {greeting}")
print(f"Port:      {port}")
print(f"Retries:   {max_retries}")
print(f"Secret:    {secret}")
print(f"Has theme: {config.has('app.theme')}")  # False — not in config

print("\nProfile-sensitive values (change with PY_ACTIVE_PROFILES=dev):")
print(f"  app.greeting = {config.get('app.greeting')}")
print(f"  server.port  = {config.get('server.port')}")
