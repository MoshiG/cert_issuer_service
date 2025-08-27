# cert_issuer_service/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyUrl
from typing import Optional

class Settings(BaseSettings):
    api_key: Optional[str] = Field(default=None)

    database_url: str = Field(default="sqlite:///./service.db")
    ipfs_api_url: AnyUrl = "http://127.0.0.1:5001"

    kms_mode: str = Field(default="local")              # local | aws
    local_master_key_base64: Optional[str] = None       # for local KMS

    aws_region: Optional[str] = None
    aws_kms_key_id: Optional[str] = None

    firefly_api_base: Optional[AnyUrl] = None
    firefly_api_name: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="CERT_", env_file=".env", extra="ignore")

def get_settings() -> "Settings":
    return Settings()
