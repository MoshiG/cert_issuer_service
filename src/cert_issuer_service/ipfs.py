# cert_issuer_service/ipfs.py
import json, requests
from typing import Tuple

def _root(url: str) -> str:
    u = url.rstrip("/")
    return u if u.endswith("/api/v0") else u + "/api/v0"

def add_bytes(name: str, data: bytes, ipfs_api_url: str, pin=True) -> str:
    params = {"pin": "true" if pin else "false", "cid-version": "1", "hash": "sha2-256"}
    files = {"file": (name, data)}
    r = requests.post(f"{_root(ipfs_api_url)}/add", params=params, files=files, timeout=60)
    r.raise_for_status()
    last = [json.loads(line) for line in r.text.strip().splitlines()][-1]
    return last["Hash"]
