# pysypt

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Jasypt-compatible password-based encryption (PBE) and iterated-hash digest for
Python. Interoperable with Spring Boot applications that use `ENC(...)` encrypted
configuration values.

Port of [`@alt-javascript/jasypt`](https://github.com/alt-javascript/jasypt) to
Python.

## Install

```bash
uv add alt-python-pysypt        # or: pip install alt-python-pysypt
```

Requires Python 3.12+ and `cryptography` >= 42.

## Quick Start

```python
from pysypt import Jasypt

jasypt = Jasypt()

# Encrypt and decrypt
ciphertext = jasypt.encrypt("admin", "mySecretKey")
plaintext  = jasypt.decrypt(ciphertext, "mySecretKey")
# plaintext == "admin"

# One-way digest
stored = jasypt.digest("admin")
jasypt.matches("admin", stored)  # True
jasypt.matches("wrong", stored)  # False
```

## API

### `Jasypt`

High-level facade. Each method constructs a fresh `Encryptor` or `Digester`
internally — the `Jasypt` class is stateless and thread-safe.

#### `jasypt.encrypt(message, password, algorithm="PBEWITHMD5ANDDES", iterations=1000, salt=None)`

Encrypts a plaintext string. Returns a base64-encoded ciphertext with the salt
prepended.

Returns `None` if `message` is empty or `None`.

```python
jasypt.encrypt("admin", "secret")
# => "nsbC5r0ymz740/aURtuRWw=="

jasypt.encrypt("admin", "secret", algorithm="PBEWITHHMACSHA256ANDAES_256")
# => "K3q8z..."  (AES-256-CBC, PBKDF2-SHA256)
```

#### `jasypt.decrypt(encrypted_message, password="", algorithm="PBEWITHMD5ANDDES", iterations=1000, salt=None)`

Decrypts a base64-encoded ciphertext. The salt is extracted from the ciphertext
automatically.

Returns `None` if `encrypted_message` is empty or `None`.

```python
jasypt.decrypt("nsbC5r0ymz740/aURtuRWw==", "secret")
# => "admin"
```

#### `jasypt.digest(message, salt=None, iterations=1000, algorithm="SHA-256")`

Produces a one-way hash. Returns `base64(salt_bytes + hash_bytes)`.

Returns `None` if `message` is empty or `None`.

```python
stored = jasypt.digest("admin")
```

#### `jasypt.matches(message, stored_digest, salt=None, iterations=1000, algorithm="SHA-256")`

Verifies a plaintext message against a stored digest. Uses constant-time
comparison.

Returns `None` if `message` is empty or `None`.

```python
stored = jasypt.digest("admin")
jasypt.matches("admin", stored)  # True
jasypt.matches("wrong", stored)  # False
```

---

### `Encryptor`

Low-level class for direct control over encryption parameters.

```python
from pysypt import Encryptor

enc = Encryptor(
    algorithm="PBEWITHHMACSHA256ANDAES_256",
    iterations=10000,
)

ciphertext = enc.encrypt("admin", "secret")
plaintext  = enc.decrypt(ciphertext, "secret")
```

#### Constructor

```python
Encryptor(algorithm="PBEWITHMD5ANDDES", salt=None, iterations=1000)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `algorithm` | `str` | `PBEWITHMD5ANDDES` | PBE algorithm name (see table below) |
| `salt` | `bytes \| None` | random | Salt bytes. `None` generates a random salt of the correct length. |
| `iterations` | `int` | `1000` | KDF iteration count |

#### Methods

| Method | Description |
|---|---|
| `set_algorithm(algorithm)` | Change the algorithm. Raises `ValueError` for unsupported names. |
| `set_salt(salt)` | Set the salt. Accepts `bytes`, `str` (UTF-8 encoded), or `None` (random). Short salts are zero-padded; long salts are truncated to the required length. |
| `set_iterations(iterations)` | Set the iteration count. |
| `encrypt(payload, password, salt=None, iterations=None)` | Encrypt. Returns base64 string. |
| `decrypt(payload, password, iterations=None)` | Decrypt. Returns plaintext string. |

---

### `Digester`

Low-level class for direct control over digest parameters.

```python
from pysypt import Digester

d = Digester(algorithm="SHA-512", iterations=5000)
d.set_salt("fixedsalt")

stored   = d.digest("admin")
is_match = d.matches("admin", stored)  # True
```

#### Constructor

```python
Digester(algorithm="SHA-256", salt=None, iterations=1000)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `algorithm` | `str` | `SHA-256` | Digest algorithm name (see table below) |
| `salt` | `str \| None` | random per digest | Fixed salt string. If `None`, a random 8-byte salt is generated per call. |
| `iterations` | `int` | `1000` | Hash iteration count |

#### Methods

| Method | Description |
|---|---|
| `set_algorithm(algorithm)` | Change the algorithm. Raises `ValueError` for unsupported names. |
| `set_salt(salt)` | Set a fixed salt. |
| `set_iterations(iterations)` | Set the iteration count. |
| `digest(message, salt=None, iterations=None)` | Produce `base64(salt + hash)`. |
| `matches(message, stored_digest, salt=None, iterations=None)` | Constant-time verification. |

---

## Supported Algorithms

### Encryption

| Algorithm | Type | Notes |
|---|---|---|
| `PBEWITHMD5ANDDES` | PBE1 | Default. EVP_BytesToKey KDF + DES-CBC. See [ADR-005](../../docs/decisions/ADR-005-pbe1-des-emulation.md). |
| `PBEWITHMD5ANDTRIPLEDES` | PBE1 | EVP_BytesToKey KDF + 3DES-CBC |
| `PBEWITHSHA1ANDDESEDE` | PBE1 | EVP_BytesToKey KDF (SHA-1) + 3DES-CBC |
| `PBEWITHHMACSHA1ANDAES_128` | PBE2 | PBKDF2-SHA1 + AES-128-CBC |
| `PBEWITHHMACSHA1ANDAES_256` | PBE2 | PBKDF2-SHA1 + AES-256-CBC |
| `PBEWITHHMACSHA224ANDAES_128` | PBE2 | PBKDF2-SHA224 + AES-128-CBC |
| `PBEWITHHMACSHA224ANDAES_256` | PBE2 | PBKDF2-SHA224 + AES-256-CBC |
| `PBEWITHHMACSHA256ANDAES_128` | PBE2 | PBKDF2-SHA256 + AES-128-CBC |
| `PBEWITHHMACSHA256ANDAES_256` | PBE2 | PBKDF2-SHA256 + AES-256-CBC (**recommended**) |
| `PBEWITHHMACSHA384ANDAES_128` | PBE2 | PBKDF2-SHA384 + AES-128-CBC |
| `PBEWITHHMACSHA384ANDAES_256` | PBE2 | PBKDF2-SHA384 + AES-256-CBC |
| `PBEWITHHMACSHA512ANDAES_128` | PBE2 | PBKDF2-SHA512 + AES-128-CBC |
| `PBEWITHHMACSHA512ANDAES_256` | PBE2 | PBKDF2-SHA512 + AES-256-CBC |

**PBE1** uses an iterative MD5/SHA-1 KDF (EVP_BytesToKey-style) with an 8-byte
salt prepended to the ciphertext.

**PBE2** uses PBKDF2 with a 16-byte salt and a random 16-byte IV, both prepended
to the ciphertext.

RC2 and RC4 variants are not supported — see
[ADR-006](../../docs/decisions/ADR-006-rc2-rc4-omitted.md).

### Digest

| Algorithm | Available by default |
|---|---|
| `MD5` | ✅ |
| `SHA-1` | ✅ |
| `SHA-224` | ✅ |
| `SHA-256` | ✅ (default) |
| `SHA-384` | ✅ |
| `SHA-512` | ✅ |
| `SHA-512/224` | ✅ |
| `SHA-512/256` | ✅ |
| `SHA3-224` | ✅ |
| `SHA3-256` | ✅ |
| `SHA3-384` | ✅ |
| `SHA3-512` | ✅ |
| `MD2` | Rarely available |

`Digester.SUPPORTED_ALGORITHMS` reflects only algorithms available in the current
OpenSSL build. `Digester.set_algorithm("MD2")` raises `ValueError` if MD2 is
unavailable.

## Wire Format

Both classes produce self-describing base64 ciphertext — the salt (and IV for
PBE2) is stored inline so decryption requires only the password:

```
PBE1:  base64( salt[8]  + ciphertext )
PBE2:  base64( salt[16] + iv[16]     + ciphertext )
Digest: base64( salt[8]  + hash_bytes )
```

## Java Interoperability

PBE2 algorithms (`PBEWITHHMACSHA*ANDAES_*`) are fully interoperable with Java
jasypt. If you encrypt a value in Java using `PBEWITHHMACSHA256ANDAES_256` and
the same password, `pysypt` will decrypt it correctly.

PBE1 DES (`PBEWITHMD5ANDDES`) is **not** byte-for-byte compatible with Java due
to the TripleDES-EDE emulation (ADR-005). Use a PBE2 algorithm for cross-language
scenarios.

## Troubleshooting

**`ValueError: Unsupported algorithm: MYALGO`**
The algorithm name is not in the supported list. Check spelling and case — names
must match exactly (e.g. `PBEWITHHMACSHA256ANDAES_256`).

**Decryption produces garbled text**
The password or algorithm does not match what was used to encrypt. Both the
encryptor and decryptor must use the same algorithm and password.

**`ValueError: Invalid padding bytes`**
The ciphertext is corrupt, truncated, or was encrypted with a different algorithm.
This can also occur if the base64 string was URL-encoded and not decoded first.
