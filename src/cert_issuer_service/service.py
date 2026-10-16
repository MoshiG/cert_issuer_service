# cert_issuer_service/service.py
import base64, hashlib, json, ulid, jcs
from typing import Dict, Tuple
from eth_account import Account
from eth_keyfile import create_keyfile_json
from sqlmodel import Session, select
from .kms import get_kms
from .crypto_utils import aesgcm_encrypt, aesgcm_decrypt
from .ipfs import add_bytes
from .models_db import Wallet, Certificate
from .settings import get_settings

def _decode_pdf(pdf_b64: str) -> tuple[bytes, str]:
    # PDFs arrive only as base64 in the request body; the API never reads server-side paths.
    data = base64.b64decode(pdf_b64, validate=True)
    if not data.startswith(b"%PDF-"):
        raise ValueError("pdf_b64 is not a PDF")
    return data, "certificate.pdf"

def create_custodial_wallet(session: Session, student_ref: str | None = None) -> str:
    kms = get_kms()
    acct = Account.create()  # os.urandom
    priv = bytes(acct.key)   # 32 bytes

    # Envelope: generate data key, encrypt privkey with it; store ciphertext + enc_datakey
    data_key, enc_datakey = kms.generate_data_key()
    nonce, ciphertext, tag = aesgcm_encrypt(data_key, priv)
    # wipe data_key from memory by shadowing (best-effort in Python)
    data_key = b"\x00" * len(data_key)

    w = Wallet(
        address=acct.address,
        student_ref=student_ref,
        kms_key_id=(get_settings().aws_kms_key_id or "local"),
        enc_datakey=enc_datakey,
        ciphertext_privkey=ciphertext,
        nonce=nonce,
        tag=tag,
    )
    session.add(w)
    session.commit()
    return acct.address

def export_wallet_keystore(session: Session, address: str, new_password: str) -> str:
    kms = get_kms()
    w = session.get(Wallet, address)
    if not w:
        raise ValueError("Wallet not found")

    data_key = kms.decrypt_data_key(w.enc_datakey)
    priv = aesgcm_decrypt(data_key, w.nonce, w.ciphertext_privkey, w.tag)
    ks = create_keyfile_json(priv, new_password.encode("utf-8"))
    # best-effort wipe
    priv = b"\x00"*32
    return json.dumps(ks)

def build_ulid_token() -> tuple[str, int, str]:
    u = ulid.new()
    token_int = int.from_bytes(u.bytes, "big")
    return u.str, token_int, str(token_int)

def canonicalize_and_hash_manifest(manifest: Dict) -> tuple[bytes, str]:
    canon = jcs.canonicalize(manifest)
    return canon, "0x" + hashlib.sha256(canon).hexdigest()

def prepare_issue(session: Session, *,
                  holder_name: str, degree_name: str, issued_date: str, issuer_id: str,
                  pdf_b64: str,
                  ipfs_api_url: str, wallet_mode: str,
                  holder_address: str | None, keystore_password: str | None,
                  external_url_base: str | None) -> Dict:

    # 1) Holder address
    if wallet_mode == "provided":
        if not holder_address:
            raise ValueError("holder_address is required for wallet_mode='provided'")
        holder = holder_address
        holder_keystore_json = None
    else:
        # custodial generation
        holder = create_custodial_wallet(session)
        holder_keystore_json = None
        if keystore_password:
            holder_keystore_json = export_wallet_keystore(session, holder, keystore_password)

    # 2) ULID → tokenId
    ulid_str, _token_int, token_id_str = build_ulid_token()

    # 3) PDF → CID + sha256
    pdf_bytes, pdf_name = _decode_pdf(pdf_b64)
    pdf_cid = add_bytes(pdf_name, pdf_bytes, ipfs_api_url, pin=True)
    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # 4) Manifest → JCS → hash → CID
    manifest = {
        "id": ulid_str,
        "pdfCID": pdf_cid,
        "sha256": pdf_sha256,
        "issuer": issuer_id,
        "name": holder_name,
        "degree": degree_name,
        "issued": issued_date
    }
    canon_bytes, manifest_hash_hex = canonicalize_and_hash_manifest(manifest)
    manifest_cid = add_bytes(f"{ulid_str}.manifest.canon.json", canon_bytes, ipfs_api_url, pin=True)

    # 5) ERC-721 metadata → CID
    md = {
        "name": f"Certificate: {holder_name}",
        "description": f"Official certificate issued by {issuer_id}",
        "attributes": [
            {"trait_type": "Degree", "value": degree_name},
            {"trait_type": "Issued", "value": issued_date},
            {"trait_type": "Issuer", "value": issuer_id},
        ],
        "manifest_cid": manifest_cid,
        "manifest_hash": manifest_hash_hex,
        "content": {"mediaType": "application/pdf", "pdf_cid": pdf_cid},
    }
    if external_url_base:
        md["external_url"] = f"{external_url_base}?id={ulid_str}"

    md_bytes = json.dumps(md, separators=(",", ":"), ensure_ascii=False).encode()
    metadata_cid = add_bytes(f"{ulid_str}.metadata.json", md_bytes, ipfs_api_url, pin=True)
    token_uri = f"ipfs://{metadata_cid}"

    # 6) Persist certificate row (for audits & retries)
    cert = Certificate(
        ulid=ulid_str,
        short_code=None,  # add later if you generate a short alias
        issuer_id=issuer_id,
        holder_name=holder_name,
        degree_name=degree_name,
        issued_date=issued_date,
        pdf_cid=pdf_cid,
        pdf_sha256=pdf_sha256,
        manifest_cid=manifest_cid,
        manifest_hash=manifest_hash_hex,
        metadata_cid=metadata_cid,
    )
    session.add(cert)
    session.commit()

    out = {
        "holder": holder,
        "tokenId": token_id_str,
        "manifestHash": manifest_hash_hex,
        "tokenURI": token_uri,
        "ulid": ulid_str,
        "pdf_cid": pdf_cid,
        "manifest_cid": manifest_cid,
        "metadata_cid": metadata_cid
    }
    if holder_keystore_json:
        out["holder_keystore_json"] = holder_keystore_json
    return out
