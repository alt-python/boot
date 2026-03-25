# ADR-003: Dot-Separated Logger Category Hierarchy

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Craig Parravicini, Agent

## Context

The JavaScript logger uses slash-separated category names (`com/example/MyService`)
matching Spring's Java package path convention expressed as a URL path. Category
levels are stored in config at keys like `logging.level./com/example`.

Python's stdlib `logging` module uses dot-separated logger names
(`com.example.MyService`) as the canonical hierarchy separator. A logger named
`com.example.MyService` is automatically a child of `com.example`, which is a
child of `com` — this is enforced by the stdlib logger registry.

## Decision

Use dot-separated category names throughout the Python logger:

- Logger names: `com.example.MyService`
- Config level keys: `logging.level.com.example.MyService`
- Root level stored at: `logging.level./` (the slash root marker is preserved for config-file compatibility across runtimes)

`ConfigurableLogger.get_logger_level()` walks dot-split segments of the category
string and queries `config.has("logging.level.{segment_path}")` at each step,
taking the most-specific match found.

## Consequences

**Positive:**
- Idiomatic Python — every Python developer expects dot-separated logger names.
- Direct integration with `logging.getLogger("com.example.MyService")` — the stdlib hierarchy works naturally.
- Config file format is familiar to anyone who has used Python logging configuration.

**Negative:**
- Config files are not directly portable from the JS monorepo — category separator in keys must change from `/` to `.`.
- The root marker (`/`) is an exception to the otherwise pure dot convention; this is a deliberate compatibility artefact.

**Risks:**
- Config keys containing dots are ambiguous with EphemeralConfig's dot-path traversal. `ConfigurableLogger` avoids this by building the key incrementally from segments, which traverses nested dicts correctly.
