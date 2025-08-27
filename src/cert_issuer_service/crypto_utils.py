# cert_issuer_service/crypto_utils.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def aesgcm_encrypt(plaintext_key: bytes, data: bytes) -> tuple[bytes, bytes, bytes]:
    aes = AESGCM(plaintext_key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, data, None)  # ct = ciphertext + tag
    return nonce, ct[:-16], ct[-16:]     # nonce, ciphertext, tag

def aesgcm_decrypt(plaintext_key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    aes = AESGCM(plaintext_key)
    return aes.decrypt(nonce, ciphertext + tag, None)
