"""
pysypt.jasypt — Thin facade matching the JS Jasypt class API.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Optional

from common import is_empty
from pysypt.encryptor import Encryptor
from pysypt.digester import Digester


class Jasypt:
    """
    Facade providing encrypt / decrypt / digest / matches — mirrors the JS Jasypt class.

    Each call constructs a fresh Encryptor or Digester with the provided options
    so this class is stateless and thread-safe.
    """

    def encrypt(
        self,
        message: str,
        password: str,
        algorithm: str = "PBEWITHMD5ANDDES",
        iterations: int = 1000,
        salt: Optional[bytes] = None,
    ) -> Optional[str]:
        """Encrypt a plaintext message.  Returns None for empty input."""
        if is_empty(message):
            return None
        enc = Encryptor(algorithm=algorithm, salt=salt, iterations=iterations)
        return enc.encrypt(message, password)

    def decrypt(
        self,
        encrypted_message: Optional[str],
        password: str = "",
        algorithm: str = "PBEWITHMD5ANDDES",
        iterations: int = 1000,
        salt: Optional[bytes] = None,
    ) -> Optional[str]:
        """Decrypt an encrypted message.  Returns None for empty input."""
        if is_empty(encrypted_message):
            return None
        enc = Encryptor(algorithm=algorithm, salt=salt, iterations=iterations)
        return enc.decrypt(encrypted_message, password)  # type: ignore[arg-type]

    def digest(
        self,
        message: str,
        salt: Optional[str] = None,
        iterations: int = 1000,
        algorithm: str = "SHA-256",
    ) -> Optional[str]:
        """One-way digest a message.  Returns None for empty input."""
        if is_empty(message):
            return None
        digester = Digester(algorithm=algorithm, iterations=iterations)
        return digester.digest(message, salt=salt)

    def matches(
        self,
        message: str,
        stored_digest: str,
        salt: Optional[str] = None,
        iterations: int = 1000,
        algorithm: str = "SHA-256",
    ) -> Optional[bool]:
        """Verify plaintext against a stored digest.  Returns None for empty message."""
        if is_empty(message):
            return None
        return Digester(algorithm=algorithm, iterations=iterations).matches(
            message, stored_digest, salt=salt
        )
