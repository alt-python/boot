"""
pysypt — Jasypt-compatible PBE encryption and digest for Python.

Mirrors the JS @alt-javascript/jasypt package.

Quick start::

    from pysypt import Jasypt, Encryptor, Digester

    jasypt = Jasypt()
    ciphertext = jasypt.encrypt("admin", "mypassword")
    plaintext  = jasypt.decrypt(ciphertext, "mypassword")

    stored = jasypt.digest("admin")
    assert jasypt.matches("admin", stored) is True
"""

from pysypt.jasypt import Jasypt
from pysypt.encryptor import Encryptor, SUPPORTED_ALGORITHMS
from pysypt.digester import Digester, SUPPORTED_ALGORITHMS as SUPPORTED_DIGEST_ALGORITHMS

__all__ = [
    "Jasypt",
    "Encryptor",
    "Digester",
    "SUPPORTED_ALGORITHMS",
    "SUPPORTED_DIGEST_ALGORITHMS",
]
