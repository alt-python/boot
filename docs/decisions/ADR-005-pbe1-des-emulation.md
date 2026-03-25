# ADR-005: Single DES Emulated via TripleDES-EDE

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Agent

## Context

The `PBEWITHMD5ANDDES` algorithm uses single DES (Data Encryption Standard) in
CBC mode. Python's `cryptography` library (PyCA) removed the standalone DES
primitive in version 42.0 because DES is broken; it is not exported from
`cryptography.hazmat.primitives.ciphers.algorithms`.

The JS port uses `des.js`, a pure-JS implementation that exposes single DES
directly. No equivalent pure-Python DES library is widely maintained and
trusted.

## Decision

Emulate single DES using TripleDES-EDE (3DES) with a degenerate key where
k1 = k2 = k3 = the 8-byte DES key. When all three 3DES sub-keys are identical,
the cipher applies E(k) → D(k) → E(k) which is mathematically equivalent to
a single E(k) pass — i.e. plain DES.

The 8-byte DES key is repeated three times to produce a 24-byte TripleDES key:

```python
triple_des_key = des_key * 3  # 8 bytes → 24 bytes
Cipher(TripleDES(triple_des_key), modes.CBC(iv))
```

`TripleDES` has itself been moved to `cryptography.hazmat.decrepit.ciphers.algorithms`
in `cryptography` 44+. The implementation imports from the new location with a
fallback to the old path for backward compatibility.

## Consequences

**Positive:**
- `PBEWITHMD5ANDDES` round-trips correctly within Python — encrypt then decrypt
  returns the original plaintext.
- No additional dependency required.

**Negative:**
- The ciphertext produced is **not byte-for-byte compatible with Java jasypt** for
  `PBEWITHMD5ANDDES`. Java uses a native DES cipher; the 3DES-k1=k2=k3 emulation
  produces the same plaintext after round-trip but generates different ciphertext
  than a Java-encrypted value.
- If interop with Java `ENC(...)` values encrypted using `PBEWITHMD5ANDDES` is
  required, use `PBEWITHHMACSHA256ANDAES_256` instead, which is fully interoperable.

**Risks:**
- A future `cryptography` release may remove `TripleDES` entirely. The `decrepit`
  import path is the migration target and will remain available for longer.
  Monitor `cryptography` release notes.
