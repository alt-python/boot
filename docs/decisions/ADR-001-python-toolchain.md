# ADR-001: Python 3.12 + uv via Homebrew

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Craig Parravicini, Agent

## Context

The system Python on macOS 14 is Python 3.9.6 linked against LibreSSL 2.8.3.
LibreSSL 2.8.3 exposes no AES or DES ciphers via its OpenSSL compatibility
layer, making it impossible to implement any PBE encryption algorithm. A newer
Python linked against a real OpenSSL build is required.

The project is a monorepo with three interdependent packages. A workspace-aware
package manager that can install local packages as editable dependencies and
resolve the full dependency graph in a single lock file simplifies development
and CI.

## Decision

Install Python 3.12 and uv via Homebrew:

```bash
brew install python@3.12 uv
```

Use uv workspace mode (`[tool.uv.workspace]` in the root `pyproject.toml`) with
per-package `pyproject.toml` files using `{ workspace = true }` source
references. All packages are also listed as root dependencies so `uv sync`
installs them into the shared virtual environment.

Python 3.12 is selected over 3.11 or 3.13 because it is the current stable LTS
release with full OpenSSL 3.x support via Homebrew's `openssl@3` formula.

## Consequences

**Positive:**
- OpenSSL 3.x is available; all PBE algorithms in the test suite pass.
- `uv sync` resolves and installs all workspace packages in one step.
- `uv run pytest` runs tests in the correct environment without manual venv activation.
- Lock file (`uv.lock`) ensures reproducible installs.

**Negative:**
- Requires Homebrew — not available in all CI environments by default.
- System Python (`/usr/bin/python3`) is not used; PATH must resolve to the Homebrew binary.

**Risks:**
- Homebrew's `openssl@3` could change the cipher set in a future version. Mitigated by pinning Python version in `.python-version`.
