# cert_issuer_service/models_db.py
from datetime import datetime
from sqlmodel import SQLModel, Field

class Wallet(SQLModel, table=True):
    address: str = Field(primary_key=True)     # 0x…
    student_ref: str | None = None

    kms_key_id: str
    enc_datakey: bytes                         # KMS-encrypted data key
    ciphertext_privkey: bytes                  # AES-GCM ciphertext of 32B privkey
    nonce: bytes
    tag: bytes

    exported_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Certificate(SQLModel, table=True):
    ulid: str = Field(primary_key=True)
    short_code: str | None = Field(default=None, index=True, unique=True)
    issuer_id: str
    holder_name: str
    degree_name: str
    issued_date: str

    pdf_cid: str
    pdf_sha256: str
    manifest_cid: str
    manifest_hash: str
    metadata_cid: str
    contract_address: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Binding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    certificate_ulid: str = Field(foreign_key="certificate.ulid")
    holder_address: str = Field(index=True)
    token_id: str = Field(unique=True, index=True)   # decimal string
    status: str = Field(default="pending")           # pending|bound|revoked
    firefly_tx_id: str | None = None
    firefly_op_id: str | None = None
    bound_at: datetime | None = None
    revoked_at: datetime | None = None
