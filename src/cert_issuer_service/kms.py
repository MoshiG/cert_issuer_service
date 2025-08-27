# cert_issuer_service/kms.py
import base64, os
from typing import Tuple, Protocol
from .settings import get_settings
from .crypto_utils import aesgcm_encrypt, aesgcm_decrypt

class KmsProvider(Protocol):
    def generate_data_key(self) -> Tuple[bytes, bytes]: ...
    def decrypt_data_key(self, enc_datakey: bytes) -> bytes: ...

class LocalEnvelopeKMS:
    """
    Simulates KMS using a master key from env. Only for dev/self-hosted KMS.
    """
    def __init__(self, master_key_b64: str):
        mk = base64.b64decode(master_key_b64)
        if len(mk) not in (16, 24, 32):
            raise ValueError("Local master key must be 16/24/32 bytes (base64)")
        self.master_key = mk

    def generate_data_key(self) -> Tuple[bytes, bytes]:
        plaintext = os.urandom(32)  # AES-256 data key
        nonce, ciphertext, tag = aesgcm_encrypt(self.master_key, plaintext)
        return plaintext, nonce + ciphertext + tag

    def decrypt_data_key(self, enc_datakey: bytes) -> bytes:
        nonce, rest = enc_datakey[:12], enc_datakey[12:]
        ciphertext, tag = rest[:-16], rest[-16:]
        return aesgcm_decrypt(self.master_key, nonce, ciphertext, tag)

# OPTIONAL AWS implementation
class AwsKMS:
    def __init__(self, key_id: str, region: str):
        import boto3  # only if installed
        self.kms = boto3.client("kms", region_name=region)
        self.key_id = key_id

    def generate_data_key(self) -> Tuple[bytes, bytes]:
        resp = self.kms.generate_data_key(KeyId=self.key_id, KeySpec="AES_256")
        return resp["Plaintext"], resp["CiphertextBlob"]

    def decrypt_data_key(self, enc_datakey: bytes) -> bytes:
        resp = self.kms.decrypt(CiphertextBlob=enc_datakey)
        return resp["Plaintext"]

def get_kms() -> KmsProvider:
    s = get_settings()
    if s.kms_mode == "aws":
        if not (s.aws_kms_key_id and s.aws_region):
            raise RuntimeError("AWS KMS selected but CERT_AWS_KMS_KEY_ID/REGION not set")
        return AwsKMS(s.aws_kms_key_id, s.aws_region)
    # default local
    if not s.local_master_key_base64:
        raise RuntimeError("Local KMS selected but CERT_LOCAL_MASTER_KEY_BASE64 not set")
    return LocalEnvelopeKMS(s.local_master_key_base64)
