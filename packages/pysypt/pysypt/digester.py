"""
pysypt.digester — Jasypt-compatible iterated-hash digest.

Output format: base64(salt_bytes + hash_bytes)
  - Random salt is prepended when no fixed salt is provided.
  - matches() extracts the salt from the stored digest for verification.

Algorithm map mirrors the JS Digester ALGO_MAP.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import hashlib
import hmac as _hmac
import os
import base64
from typing import Optional

from common import is_empty

# ---------------------------------------------------------------------------
# Algorithm table
# ---------------------------------------------------------------------------

_ALGO_MAP: dict[str, str] = {
    "MD2": "md2",       # may not be available
    "MD5": "md5",
    "SHA-1": "sha1",
    "SHA-224": "sha224",
    "SHA-256": "sha256",
    "SHA-384": "sha384",
    "SHA-512": "sha512",
    "SHA-512/224": "sha512_224",
    "SHA-512/256": "sha512_256",
    "SHA3-224": "sha3_224",
    "SHA3-256": "sha3_256",
    "SHA3-384": "sha3_384",
    "SHA3-512": "sha3_512",
}

_AVAILABLE = set(hashlib.algorithms_available)

# Normalise hashlib naming differences (sha512_224 vs sha512-224)
def _normalise_algo(name: str) -> Optional[str]:
    """Return the hashlib name if available, else None."""
    if name in _AVAILABLE:
        return name
    # Try underscored variant
    alt = name.replace("-", "_")
    if alt in _AVAILABLE:
        return alt
    # Try dashed variant
    alt2 = name.replace("_", "-")
    if alt2 in _AVAILABLE:
        return alt2
    return None


def _resolve(algo_key: str) -> Optional[str]:
    raw = _ALGO_MAP.get(algo_key)
    if raw is None:
        return None
    return _normalise_algo(raw)


SUPPORTED_ALGORITHMS: list[str] = [k for k in _ALGO_MAP if _resolve(k) is not None]


# ---------------------------------------------------------------------------
# Digester
# ---------------------------------------------------------------------------

class Digester:
    """
    Jasypt-compatible iterated-hash digester.

    Default: SHA-256, 1000 iterations, random 8-byte salt.
    """

    DEFAULT_SALT_SIZE = 8

    def __init__(
        self,
        algorithm: str = "SHA-256",
        salt: Optional[str] = None,
        iterations: int = 1000,
    ) -> None:
        self.set_algorithm(algorithm)
        self.salt: Optional[str] = salt
        self.salt_size = self.DEFAULT_SALT_SIZE
        self.iterations = iterations

    def set_algorithm(self, algorithm: str) -> None:
        resolved = _resolve(algorithm)
        if resolved is None:
            raise ValueError(f"Unsupported digest algorithm: {algorithm}")
        self.algorithm = algorithm
        self._hashlib_algo = resolved

    def set_salt(self, salt: Optional[str]) -> None:
        self.salt = salt

    def set_iterations(self, iterations: int) -> None:
        self.iterations = iterations

    # ------------------------------------------------------------------
    # Core compute
    # ------------------------------------------------------------------

    def _compute(self, salt_bytes: bytes, message: str, iterations: int) -> bytes:
        """
        Iterated hash: first = Hash(salt + message), subsequent = Hash(digest).
        Mirrors the JS Digester._compute().
        """
        msg = message.encode("utf-8")
        digest = hashlib.new(self._hashlib_algo, salt_bytes + msg).digest()
        for _ in range(1, iterations):
            digest = hashlib.new(self._hashlib_algo, digest).digest()
        return digest

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def digest(
        self,
        message: str,
        salt: Optional[str] = None,
        iterations: Optional[int] = None,
    ) -> str:
        """
        Digest a message.  Returns base64(salt_bytes + hash_bytes).
        """
        if not is_empty(salt):
            salt_bytes = salt.encode("utf-8")  # type: ignore[union-attr]
        elif not is_empty(self.salt):
            salt_bytes = self.salt.encode("utf-8")  # type: ignore[union-attr]
        else:
            salt_bytes = os.urandom(self.salt_size)

        _iters = iterations if iterations is not None else self.iterations
        digest_bytes = self._compute(salt_bytes, message, _iters)
        return base64.b64encode(salt_bytes + digest_bytes).decode("ascii")

    def matches(
        self,
        message: str,
        stored_digest: str,
        salt: Optional[str] = None,
        iterations: Optional[int] = None,
    ) -> bool:
        """
        Verify message against a stored digest.

        For random-salt digests, the salt is extracted from the first salt_size
        bytes of the decoded stored value.  For fixed-salt digests, that salt is
        used directly.
        """
        stored_bytes = base64.b64decode(stored_digest)

        if not is_empty(salt):
            salt_bytes = salt.encode("utf-8")  # type: ignore[union-attr]
        elif not is_empty(self.salt):
            salt_bytes = self.salt.encode("utf-8")  # type: ignore[union-attr]
        else:
            salt_bytes = stored_bytes[: self.salt_size]

        expected = stored_bytes[len(salt_bytes) :]
        _iters = iterations if iterations is not None else self.iterations
        computed = self._compute(salt_bytes, message, _iters)

        # Constant-time comparison
        return _hmac.compare_digest(computed, expected)
