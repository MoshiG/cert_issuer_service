# cert_issuer_service/schemas.py
from pydantic import BaseModel, Field, HttpUrl, constr
from typing import Optional, Literal

WalletMode = Literal["generate", "provided"]

class CreateWalletRequest(BaseModel):
    student_ref: Optional[str] = None

class CreateWalletResponse(BaseModel):
    address: constr(pattern=r"^0x[a-fA-F0-9]{40}$")

class ExportWalletRequest(BaseModel):
    new_password: str = Field(min_length=6)

class PrepareIssueRequest(BaseModel):
    holder_name: str
    degree_name: str
    issued_date: str
    issuer_id: str
    pdf_b64: Optional[str] = None
    pdf_path: Optional[str] = None
    ipfs_api_url: Optional[HttpUrl] = None
    wallet_mode: WalletMode = "provided"
    holder_address: Optional[constr(pattern=r"^0x[a-fA-F0-9]{40}$")] = None
    keystore_password: Optional[str] = None
    external_url_base: Optional[HttpUrl] = None

class PrepareIssueResponse(BaseModel):
    holder: str
    tokenId: str
    manifestHash: str
    tokenURI: str
    ulid: str
    pdf_cid: str
    manifest_cid: str
    metadata_cid: str
    holder_keystore_json: Optional[str] = None
