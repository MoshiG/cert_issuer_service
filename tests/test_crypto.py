import os
from cert_issuer_service.crypto_utils import aesgcm_encrypt, aesgcm_decrypt
from cert_issuer_service.kms import get_kms
from cert_issuer_service.service import canonicalize_and_hash_manifest, build_ulid_token


def test_aesgcm_round_trip():
    key, data = os.urandom(32), b"secret private key"
    nonce, ct, tag = aesgcm_encrypt(key, data)
    assert ct != data
    assert aesgcm_decrypt(key, nonce, ct, tag) == data


def test_envelope_data_key_round_trip():
    kms = get_kms()
    plain, enc = kms.generate_data_key()
    assert len(plain) == 32 and enc != plain
    assert kms.decrypt_data_key(enc) == plain


def test_manifest_hash_ignores_key_order():
    a = {"name": "Jane", "degree": "BSc", "issued": "2025-11-30"}
    b = {"issued": "2025-11-30", "degree": "BSc", "name": "Jane"}
    assert canonicalize_and_hash_manifest(a)[1] == canonicalize_and_hash_manifest(b)[1]


def test_manifest_hash_detects_tampering():
    a = {"name": "Jane", "degree": "BSc"}
    b = {"name": "Jane", "degree": "MSc"}
    assert canonicalize_and_hash_manifest(a)[1] != canonicalize_and_hash_manifest(b)[1]


def test_token_ids_are_unique_128_bit():
    ids = {build_ulid_token()[1] for _ in range(1000)}
    assert len(ids) == 1000 and all(i < 2**128 for i in ids)
