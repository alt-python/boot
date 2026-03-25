# ADR-006: RC2 and RC4 Algorithms Not Ported

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Agent

## Context

The JavaScript jasypt implementation supports four RC2/RC4 PBE algorithms:

- `PBEWITHSHA1ANDRC2_128`
- `PBEWITHSHA1ANDRC2_40`
- `PBEWITHSHA1ANDRC4_128`
- `PBEWITHSHA1ANDRC4_40`

These use the `rc2-cbc`, `rc2-40-cbc`, `rc4`, and `rc4-40` OpenSSL ciphers.
In OpenSSL 3.x these ciphers are in the legacy provider and are disabled by
default. The JS port already skips them conditionally in its test suite when
the cipher is unavailable.

Python's `cryptography` library (PyCA) does not expose RC2 or RC4 in its hazmat
layer at all — they are considered broken and have been intentionally excluded.

## Decision

Do not implement RC2 or RC4 PBE algorithms in `pysypt`. The `SUPPORTED_ALGORITHMS`
list contains only the algorithms that actually work on a standard OpenSSL 3.x
installation:

- PBE1: `PBEWITHMD5ANDDES`, `PBEWITHMD5ANDTRIPLEDES`, `PBEWITHSHA1ANDDESEDE`
- PBE2: all `PBEWITHHMACSHA*ANDAES_*` variants

## Consequences

**Positive:**
- No dependency on an OpenSSL legacy provider.
- `pysypt` works on any standard Python 3.12 + Homebrew OpenSSL 3.x installation.

**Negative:**
- RC2/RC4-encrypted values from legacy Java jasypt deployments cannot be decrypted by `pysypt`. Callers must re-encrypt using a supported algorithm before migrating.

**Risks:**
- None. RC2 and RC4 are cryptographically broken and should not be used in new deployments. The JS monorepo itself marks them as "skip if unavailable".
