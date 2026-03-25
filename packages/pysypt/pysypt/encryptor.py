"""
pysypt.encryptor — Jasypt-compatible PBE encryption.

Supports the same algorithm table as the JS alt-javascript/jasypt Encryptor:

PBE1 (EVP_BytesToKey-style KDF + DES / 3DES):
  PBEWITHMD5ANDDES, PBEWITHMD5ANDTRIPLEDES, PBEWITHSHA1ANDDESEDE

PBE2 (PBKDF2 + AES-CBC):
  PBEWITHHMACSHA{1,224,256,384,512}ANDAES_{128,256}

Wire format (base64-encoded):
  PBE1 / PBE1N:  salt(8) + ciphertext
  PBE2:          salt(16) + iv(16) + ciphertext

All algorithms operate in CBC mode.  RC2 / RC4 variants from the JS version
are intentionally omitted — they are removed from modern OpenSSL and have no
safe analogue in the cryptography package.
"""

from __future__ import annotations

import os
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers import algorithms as std_algorithms
from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# TripleDES moved to decrepit in cryptography 44+; fall back gracefully
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES as _TripleDES
except ImportError:
    _TripleDES = std_algorithms.TripleDES  # type: ignore[attr-defined]
import hashlib
import base64

from common import is_empty

# ---------------------------------------------------------------------------
# Algorithm table
# ---------------------------------------------------------------------------

_PBE1_SALT_LEN = 8
_PBE2_SALT_LEN = 16
_PBE2_IV_LEN = 16

_HASH_MAP = {
    "md5": hashes.MD5,
    "sha1": hashes.SHA1,
    "sha224": hashes.SHA224,
    "sha256": hashes.SHA256,
    "sha384": hashes.SHA384,
    "sha512": hashes.SHA512,
}

# Each entry:  type, hash/hmac name, key_len (bytes), iv_len (bytes)
# PBE1 uses DES/3DES; PBE2 uses AES-CBC via PBKDF2
_ALGO_CONFIG: dict[str, dict[str, Any]] = {
    # PBE1 — EVP_BytesToKey KDF + DES
    "PBEWITHMD5ANDDES": {
        "type": "pbe1",
        "hash": "md5",
        "cipher": "des-cbc",
        "key_len": 8,
        "iv_len": 8,
    },
    # PBE1 — EVP_BytesToKey KDF + 3DES
    "PBEWITHMD5ANDTRIPLEDES": {
        "type": "pbe1",
        "hash": "md5",
        "cipher": "3des-cbc",
        "key_len": 24,
        "iv_len": 8,
    },
    "PBEWITHSHA1ANDDESEDE": {
        "type": "pbe1",
        "hash": "sha1",
        "cipher": "3des-cbc",
        "key_len": 24,
        "iv_len": 8,
    },
    # PBE2 — PBKDF2 + AES-CBC
    "PBEWITHHMACSHA1ANDAES_128": {"type": "pbe2", "hmac": "sha1", "key_len": 16},
    "PBEWITHHMACSHA1ANDAES_256": {"type": "pbe2", "hmac": "sha1", "key_len": 32},
    "PBEWITHHMACSHA224ANDAES_128": {"type": "pbe2", "hmac": "sha224", "key_len": 16},
    "PBEWITHHMACSHA224ANDAES_256": {"type": "pbe2", "hmac": "sha224", "key_len": 32},
    "PBEWITHHMACSHA256ANDAES_128": {"type": "pbe2", "hmac": "sha256", "key_len": 16},
    "PBEWITHHMACSHA256ANDAES_256": {"type": "pbe2", "hmac": "sha256", "key_len": 32},
    "PBEWITHHMACSHA384ANDAES_128": {"type": "pbe2", "hmac": "sha384", "key_len": 16},
    "PBEWITHHMACSHA384ANDAES_256": {"type": "pbe2", "hmac": "sha384", "key_len": 32},
    "PBEWITHHMACSHA512ANDAES_128": {"type": "pbe2", "hmac": "sha512", "key_len": 16},
    "PBEWITHHMACSHA512ANDAES_256": {"type": "pbe2", "hmac": "sha512", "key_len": 32},
}

SUPPORTED_ALGORITHMS = list(_ALGO_CONFIG.keys())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pkcs7_pad(data: bytes, block_size: int) -> bytes:
    padder = sym_padding.PKCS7(block_size * 8).padder()
    return padder.update(data) + padder.finalize()


def _pkcs7_unpad(data: bytes, block_size: int) -> bytes:
    unpadder = sym_padding.PKCS7(block_size * 8).unpadder()
    return unpadder.update(data) + unpadder.finalize()


def _evp_bytes_to_key(
    hash_name: str, password: bytes, salt: bytes, iterations: int, key_len: int, iv_len: int
) -> tuple[bytes, bytes]:
    """
    OpenSSL EVP_BytesToKey-compatible KDF.

    Produces successive hash blocks: H_i = Hash^n(H_{i-1} || password || salt)
    Returns (key[:key_len], key[key_len:key_len+iv_len])
    """
    total = key_len + iv_len
    result = b""
    prev = b""
    while len(result) < total:
        block = prev + password + salt
        for _ in range(iterations):
            block = hashlib.new(hash_name, block).digest()
        result += block
        prev = block
    key = result[:key_len]
    iv = result[key_len : key_len + iv_len]
    return key, iv


def _pbkdf2_key(
    hmac_name: str, password: bytes, salt: bytes, iterations: int, key_len: int
) -> bytes:
    """PBKDF2 key derivation using the cryptography library."""
    hash_cls = _HASH_MAP[hmac_name]
    kdf = PBKDF2HMAC(
        algorithm=hash_cls(),
        length=key_len,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(password)


# ---------------------------------------------------------------------------
# Encryptor
# ---------------------------------------------------------------------------

class Encryptor:
    """
    Jasypt-compatible PBE encryptor.

    Default algorithm: PBEWITHMD5ANDDES (same as Java jasypt default).
    """

    def __init__(
        self,
        algorithm: str = "PBEWITHMD5ANDDES",
        salt: bytes | None = None,
        iterations: int = 1000,
    ) -> None:
        self.set_algorithm(algorithm)
        cfg = _ALGO_CONFIG[self.algorithm]
        salt_len = _PBE2_SALT_LEN if cfg["type"] == "pbe2" else _PBE1_SALT_LEN
        self.salt: bytes = salt if salt is not None else os.urandom(salt_len)
        self.iterations = iterations

    def set_algorithm(self, algorithm: str) -> None:
        norm = algorithm.upper()
        if norm not in _ALGO_CONFIG:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        self.algorithm = norm

    def set_salt(self, salt: bytes | str | None) -> None:
        cfg = _ALGO_CONFIG[self.algorithm]
        salt_len = _PBE2_SALT_LEN if cfg["type"] == "pbe2" else _PBE1_SALT_LEN
        if salt is None:
            self.salt = os.urandom(salt_len)
            return
        if isinstance(salt, str):
            b = salt.encode("utf-8")
        else:
            b = bytes(salt)
        # Empty → random; short → zero-pad to required length; long → truncate
        if len(b) == 0:
            self.salt = os.urandom(salt_len)
        elif len(b) < salt_len:
            self.salt = b.ljust(salt_len, b"\x00")
        else:
            self.salt = b[:salt_len]

    def set_iterations(self, iterations: int) -> None:
        self.iterations = iterations or 1000

    # ------------------------------------------------------------------
    # Encrypt
    # ------------------------------------------------------------------

    def encrypt(
        self,
        payload: str,
        password: str,
        salt: bytes | None = None,
        iterations: int | None = None,
    ) -> str:
        cfg = _ALGO_CONFIG[self.algorithm]
        _salt = salt if salt is not None else self.salt
        _iters = iterations if iterations is not None else self.iterations
        pwd_bytes = (password or "").encode("utf-8")
        data = payload.encode("utf-8")

        if cfg["type"] == "pbe1":
            return self._encrypt_pbe1(cfg, _salt, _iters, pwd_bytes, data)
        # pbe2
        return self._encrypt_pbe2(cfg, _salt, _iters, pwd_bytes, data)

    def _encrypt_pbe1(
        self,
        cfg: dict,
        salt: bytes,
        iterations: int,
        password: bytes,
        data: bytes,
    ) -> str:
        key, iv = _evp_bytes_to_key(cfg["hash"], password, salt, iterations, cfg["key_len"], cfg["iv_len"])
        ciphertext = self._pbe1_cipher_encrypt(cfg["cipher"], key, iv, data)
        return base64.b64encode(salt + ciphertext).decode("ascii")

    def _encrypt_pbe2(
        self,
        cfg: dict,
        salt: bytes,
        iterations: int,
        password: bytes,
        data: bytes,
    ) -> str:
        iv = os.urandom(_PBE2_IV_LEN)
        key = _pbkdf2_key(cfg["hmac"], password, salt, iterations, cfg["key_len"])
        padded = _pkcs7_pad(data, 16)
        cipher = Cipher(std_algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        enc = cipher.encryptor()
        ciphertext = enc.update(padded) + enc.finalize()
        return base64.b64encode(salt + iv + ciphertext).decode("ascii")

    # ------------------------------------------------------------------
    # Decrypt
    # ------------------------------------------------------------------

    def decrypt(
        self,
        payload: str,
        password: str,
        iterations: int | None = None,
    ) -> str:
        cfg = _ALGO_CONFIG[self.algorithm]
        _iters = iterations if iterations is not None else self.iterations
        pwd_bytes = (password or "").encode("utf-8")
        buf = base64.b64decode(payload)

        if cfg["type"] == "pbe1":
            return self._decrypt_pbe1(cfg, buf, _iters, pwd_bytes)
        return self._decrypt_pbe2(cfg, buf, _iters, pwd_bytes)

    def _decrypt_pbe1(
        self,
        cfg: dict,
        buf: bytes,
        iterations: int,
        password: bytes,
    ) -> str:
        salt = buf[:_PBE1_SALT_LEN]
        ciphertext = buf[_PBE1_SALT_LEN:]
        key, iv = _evp_bytes_to_key(cfg["hash"], password, salt, iterations, cfg["key_len"], cfg["iv_len"])
        plaintext = self._pbe1_cipher_decrypt(cfg["cipher"], key, iv, ciphertext)
        return plaintext.decode("utf-8")

    def _decrypt_pbe2(
        self,
        cfg: dict,
        buf: bytes,
        iterations: int,
        password: bytes,
    ) -> str:
        salt = buf[:_PBE2_SALT_LEN]
        iv = buf[_PBE2_SALT_LEN : _PBE2_SALT_LEN + _PBE2_IV_LEN]
        ciphertext = buf[_PBE2_SALT_LEN + _PBE2_IV_LEN :]
        key = _pbkdf2_key(cfg["hmac"], password, salt, iterations, cfg["key_len"])
        cipher = Cipher(std_algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        dec = cipher.decryptor()
        padded = dec.update(ciphertext) + dec.finalize()
        return _pkcs7_unpad(padded, 16).decode("utf-8")

    # ------------------------------------------------------------------
    # Internal cipher wrappers
    # ------------------------------------------------------------------

    def _pbe1_cipher_encrypt(self, cipher_name: str, key: bytes, iv: bytes, data: bytes) -> bytes:
        if cipher_name == "des-cbc":
            # Single DES: cryptography library has no DES primitive; emulate using
            # TripleDES-EDE with k1=k2=k3 (same 8-byte key repeated 3 times).
            padded = _pkcs7_pad(data, 8)
            c = Cipher(_TripleDES(key * 3), modes.CBC(iv), backend=default_backend())
            enc = c.encryptor()
            return enc.update(padded) + enc.finalize()
        elif cipher_name == "3des-cbc":
            padded = _pkcs7_pad(data, 8)
            c = Cipher(_TripleDES(key), modes.CBC(iv), backend=default_backend())
            enc = c.encryptor()
            return enc.update(padded) + enc.finalize()
        else:
            raise ValueError(f"Unknown PBE1 cipher: {cipher_name}")

    def _pbe1_cipher_decrypt(self, cipher_name: str, key: bytes, iv: bytes, data: bytes) -> bytes:
        if cipher_name == "des-cbc":
            c = Cipher(_TripleDES(key * 3), modes.CBC(iv), backend=default_backend())
            dec = c.decryptor()
            padded = dec.update(data) + dec.finalize()
            return _pkcs7_unpad(padded, 8)
        elif cipher_name == "3des-cbc":
            c = Cipher(_TripleDES(key), modes.CBC(iv), backend=default_backend())
            dec = c.decryptor()
            padded = dec.update(data) + dec.finalize()
            return _pkcs7_unpad(padded, 8)
        else:
            raise ValueError(f"Unknown PBE1 cipher: {cipher_name}")
