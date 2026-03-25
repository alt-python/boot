"""
tests/test_jasypt.py — pysypt test suite.

Mirrors the JS test/jasypt.test.js coverage:
  - empty input handling
  - encrypt/decrypt round-trips for all supported PBE algorithms
  - digest / matches for all supported hash algorithms
  - custom salt and iterations
  - unsupported algorithm errors
"""

from __future__ import annotations

import pytest

from pysypt import Jasypt, Encryptor, Digester, SUPPORTED_ALGORITHMS, SUPPORTED_DIGEST_ALGORITHMS

PASSWORD = "G0CvDz7oJn60"
MESSAGE = "admin"

# ---------------------------------------------------------------------------
# Empty-input guards
# ---------------------------------------------------------------------------

def test_encrypt_empty_returns_none():
    j = Jasypt()
    assert j.encrypt("", PASSWORD) is None


def test_decrypt_none_returns_none():
    j = Jasypt()
    assert j.decrypt(None) is None  # type: ignore[arg-type]


def test_decrypt_empty_string_returns_none():
    j = Jasypt()
    assert j.decrypt("") is None


def test_digest_empty_returns_none():
    j = Jasypt()
    assert j.digest("") is None


def test_matches_empty_returns_none():
    j = Jasypt()
    stored = Jasypt().digest(MESSAGE)
    assert j.matches("", stored) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Basic encrypt / decrypt round-trip (default PBEWITHMD5ANDDES)
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_default():
    j = Jasypt()
    encrypted = j.encrypt(MESSAGE, PASSWORD)
    assert encrypted is not None
    assert j.decrypt(encrypted, PASSWORD) == MESSAGE


# ---------------------------------------------------------------------------
# Encryptor class direct usage
# ---------------------------------------------------------------------------

def test_encryptor_set_salt_and_iterations():
    enc = Encryptor()
    enc.set_salt(b"")
    enc.set_iterations(100)
    ciphertext = enc.encrypt(MESSAGE, PASSWORD)
    assert enc.decrypt(ciphertext, PASSWORD) == MESSAGE


def test_encryptor_unsupported_algorithm_raises():
    enc = Encryptor()
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        enc.set_algorithm("INVALID")


# ---------------------------------------------------------------------------
# PBE1 DES / 3DES
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algorithm", [
    "PBEWITHMD5ANDDES",
    "PBEWITHMD5ANDTRIPLEDES",
    "PBEWITHSHA1ANDDESEDE",
])
def test_pbe1_round_trip(algorithm: str):
    j = Jasypt()
    encrypted = j.encrypt(MESSAGE, PASSWORD, algorithm=algorithm)
    assert j.decrypt(encrypted, PASSWORD, algorithm=algorithm) == MESSAGE


# ---------------------------------------------------------------------------
# PBE2 AES-CBC (PBKDF2)
# ---------------------------------------------------------------------------

_AES_ALGORITHMS = [
    "PBEWITHHMACSHA1ANDAES_128",
    "PBEWITHHMACSHA1ANDAES_256",
    "PBEWITHHMACSHA224ANDAES_128",
    "PBEWITHHMACSHA224ANDAES_256",
    "PBEWITHHMACSHA256ANDAES_128",
    "PBEWITHHMACSHA256ANDAES_256",
    "PBEWITHHMACSHA384ANDAES_128",
    "PBEWITHHMACSHA384ANDAES_256",
    "PBEWITHHMACSHA512ANDAES_128",
    "PBEWITHHMACSHA512ANDAES_256",
]


@pytest.mark.parametrize("algorithm", _AES_ALGORITHMS)
def test_pbe2_aes_round_trip(algorithm: str):
    j = Jasypt()
    encrypted = j.encrypt(MESSAGE, PASSWORD, algorithm=algorithm)
    assert j.decrypt(encrypted, PASSWORD, algorithm=algorithm) == MESSAGE


# ---------------------------------------------------------------------------
# SUPPORTED_ALGORITHMS list coverage
# ---------------------------------------------------------------------------

def test_all_supported_algorithms_round_trip():
    j = Jasypt()
    for algo in SUPPORTED_ALGORITHMS:
        encrypted = j.encrypt(MESSAGE, PASSWORD, algorithm=algo)
        assert j.decrypt(encrypted, PASSWORD, algorithm=algo) == MESSAGE, algo


# ---------------------------------------------------------------------------
# Digester
# ---------------------------------------------------------------------------

def test_digester_default_sha256():
    d = Digester()
    stored = d.digest(MESSAGE)
    assert d.matches(MESSAGE, stored) is True
    assert d.matches("wrong", stored) is False


def test_jasypt_digest_and_matches():
    j = Jasypt()
    stored = j.digest(MESSAGE)
    assert j.matches(MESSAGE, stored) is True
    assert j.matches("wrong", stored) is False


@pytest.mark.parametrize("algorithm", SUPPORTED_DIGEST_ALGORITHMS)
def test_digester_all_algorithms(algorithm: str):
    d = Digester()
    d.set_algorithm(algorithm)
    stored = d.digest(MESSAGE)
    assert d.matches(MESSAGE, stored) is True
    assert d.matches("wrong", stored) is False


def test_digester_custom_salt_and_iterations():
    d = Digester()
    d.set_algorithm("SHA-512")
    d.set_salt("123456789012345")
    d.set_iterations(500)
    stored = d.digest(MESSAGE)
    assert d.matches(MESSAGE, stored) is True
    assert d.matches("other", stored) is False


def test_digester_unsupported_algorithm_raises():
    d = Digester()
    with pytest.raises(ValueError, match="Unsupported digest algorithm"):
        d.set_algorithm("AES")


# ---------------------------------------------------------------------------
# Encryptor salt handling
# ---------------------------------------------------------------------------

def test_encryptor_string_salt():
    """set_salt accepts a string and encodes it as UTF-8."""
    enc = Encryptor()
    enc.set_salt("myfix")
    # Encrypt twice with same string salt — same ciphertext
    c1 = enc.encrypt(MESSAGE, PASSWORD)
    enc2 = Encryptor()
    enc2.set_salt("myfix")
    c2 = enc2.encrypt(MESSAGE, PASSWORD)
    assert enc.decrypt(c1, PASSWORD) == MESSAGE
    assert enc2.decrypt(c2, PASSWORD) == MESSAGE


def test_encryptor_none_salt_generates_random():
    enc = Encryptor()
    enc.set_salt(None)
    c1 = enc.encrypt(MESSAGE, PASSWORD)
    enc2 = Encryptor()
    enc2.set_salt(None)
    c2 = enc2.encrypt(MESSAGE, PASSWORD)
    # Each encrypt uses a fresh random salt — ciphertexts differ
    assert c1 != c2
    assert enc.decrypt(c1, PASSWORD) == MESSAGE
    assert enc2.decrypt(c2, PASSWORD) == MESSAGE


# ---------------------------------------------------------------------------
# Different messages and passwords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg,pw", [
    ("hello world", "secret"),
    ("", "anything"),          # empty message → encrypt returns None
    ("unicode: \u00e9\u00e0\u00fc", "p@ss"),
    ("admin", ""),             # empty password
])
def test_encrypt_decrypt_various(msg: str, pw: str):
    j = Jasypt()
    if msg == "":
        assert j.encrypt(msg, pw) is None
    else:
        encrypted = j.encrypt(msg, pw)
        assert j.decrypt(encrypted, pw) == msg
