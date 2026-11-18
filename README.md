# cert_issuer_service

A FastAPI service that prepares **tamper-evident academic certificates** for issuance as ERC-721 tokens. It stores the certificate PDF and a canonical manifest on IPFS, records a deterministic hash of the manifest, and manages custodial Ethereum wallets for certificate holders with envelope encryption.

The goal: let anyone verify that a certificate is genuine and unchanged, without calling the issuing institution, and make forgery detectable.

> **Status:** prototype. The service prepares everything needed to mint (token ID, token URI, manifest hash, holder address). On-chain minting and the `Binding` lifecycle (bound / revoked) are designed in the data model — via Hyperledger FireFly — but not yet wired up.

## How it works

```
PDF certificate ──► IPFS (pinned, CIDv1, sha2-256) ──► pdf_cid + SHA-256
                                   │
manifest {id, pdfCID, sha256, issuer, name, degree, issued}
        ──► JCS canonical JSON ──► SHA-256 = manifestHash ──► IPFS ──► manifest_cid
                                   │
ERC-721 metadata {name, attributes, manifest_cid, manifest_hash, pdf_cid}
        ──► IPFS ──► metadata_cid ──► tokenURI = ipfs://<metadata_cid>
                                   │
ULID ──► 128-bit integer ──► tokenId          holder wallet ──► holder address
```

1. **Content addressing.** The PDF is pinned to IPFS and its SHA-256 recorded, so any change to the file changes its CID.
2. **Deterministic manifest hash.** The manifest is canonicalised with [JCS (RFC 8785)](https://www.rfc-editor.org/rfc/rfc8785) before hashing, so the same certificate data always produces the same `manifestHash`, whatever the key order or whitespace.
3. **Collision-free token IDs.** Each certificate gets a ULID, converted to a 128-bit integer for the ERC-721 `tokenId`, so IDs are unique and time-sortable without a central counter.
4. **Custodial wallets with envelope encryption.** Holders without a wallet get one generated for them. Each private key is encrypted with its own AES-256-GCM data key; the data key is itself encrypted by a KMS (AWS KMS, or a local master key for development). Plaintext keys are never stored. Holders can export their wallet as a standard password-protected Ethereum keystore to take custody themselves.
5. **Audit trail.** Every prepared certificate is stored with all its CIDs and hashes for retries and audits.

## API

All endpoints except `/health` require the `X-API-Key` header.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness check |
| `POST` | `/wallets` | Create a custodial wallet (optional `student_ref`); returns the address |
| `POST` | `/wallets/{address}/export` | Export the wallet as an encrypted keystore JSON under a new password |
| `POST` | `/prepare-issue` | Upload the certificate, build manifest and metadata, return `tokenId`, `tokenURI`, `manifestHash` and the CIDs |

Example:

```bash
curl -X POST http://localhost:8080/prepare-issue \
  -H "X-API-Key: $CERT_API_KEY" -H "Content-Type: application/json" \
  -d '{
        "holder_name": "Jane Doe",
        "degree_name": "BSc Computer Science",
        "issued_date": "2025-11-30",
        "issuer_id": "did:example:university",
        "pdf_b64": "<base64-encoded PDF>",
        "wallet_mode": "generate"
      }'
```

## Run it

Requires Python 3.13, [Poetry](https://python-poetry.org/) and an IPFS node (e.g. Kubo) with its API on port 5001.

```bash
poetry install
export CERT_API_KEY=change-me
export CERT_LOCAL_MASTER_KEY_BASE64=$(python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())")
poetry run uvicorn cert_issuer_service.app:app --port 8080 --reload
```

| Variable | Meaning |
| --- | --- |
| `CERT_API_KEY` | API key clients must send |
| `CERT_DATABASE_URL` | SQLAlchemy URL (default SQLite `./service.db`; PostgreSQL in production) |
| `CERT_IPFS_API_URL` | IPFS API endpoint (default `http://127.0.0.1:5001`) |
| `CERT_KMS_MODE` | `local` or `aws` |
| `CERT_LOCAL_MASTER_KEY_BASE64` | 16/24/32-byte master key, base64 (local mode, development only) |
| `CERT_AWS_KMS_KEY_ID`, `CERT_AWS_REGION` | AWS KMS key (aws mode) |

## Project layout

```
src/cert_issuer_service/
  app.py           FastAPI routes and API-key dependency
  service.py       certificate preparation and wallet logic
  kms.py           KMS providers (local envelope, AWS)
  crypto_utils.py  AES-256-GCM helpers
  ipfs.py          IPFS add + pin
  models_db.py     Wallet, Certificate, Binding (SQLModel)
  schemas.py       request/response models
  settings.py      environment configuration
```

## Tests

```bash
poetry install --with dev
poetry run pytest
```

The suite covers AES-GCM and envelope-key round trips, manifest-hash stability and tamper detection, token-ID uniqueness, API-key enforcement, and the full `/prepare-issue` flow (IPFS is mocked).

## Security design

- **Fail-closed authentication.** If the server has no API key configured, every protected endpoint refuses requests (503) rather than running open. Keys are compared in constant time.
- **No server-side file reads.** Certificates arrive only as base64 in the request body and must be real PDFs; the API never opens a path supplied by a caller.
- **No caller-chosen outbound URLs.** The IPFS endpoint comes from server configuration only, which closes off server-side request forgery.
- **Keys encrypted at rest** with per-key data keys under KMS (see above); plaintext keys are overwritten after use on a best-effort basis.
- **Bad input returns 400**, not a stack trace.

## Roadmap

- [ ] Wire minting and revocation through Hyperledger FireFly (`Binding` table).
- [ ] Keep personal data off public IPFS: store a salted hash of the holder's name in the manifest, and keep the full PDF in access-controlled storage, so certificates stay verifiable without publishing personal data permanently.
- [ ] Rate limiting and per-issuer API keys.
- [ ] Move the `on_event` startup hook to FastAPI's lifespan API.

## Author

Goodiel Moshi — [LinkedIn](https://www.linkedin.com/in/dr-goodiel-moshi/)
