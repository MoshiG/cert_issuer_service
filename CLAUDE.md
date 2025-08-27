# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Start Development Server:**
```bash
poetry run uvicorn cert_issuer_service.app:app --host 0.0.0.0 --port 8080 --reload
```

**Install Dependencies:**
```bash
poetry install
```

**Run Application:**
```bash
poetry run python -m cert_issuer_service.app
```

## Architecture Overview

This is a **FastAPI-based blockchain certificate issuer service** that creates and manages ERC-721 NFT certificates with IPFS storage and cryptographic security.

### Core Components

**FastAPI Application (`app.py`)**
- REST API with 4 endpoints: health, wallet creation, wallet export, certificate preparation
- API key authentication via `X-API-Key` header
- Uses dependency injection for settings, database sessions, and auth

**Certificate Preparation Flow (`service.py`)**
- Generates ULID-based unique token IDs
- Creates PDF → IPFS CID mapping with SHA256 verification
- Builds canonicalized manifest (JCS) with cryptographic hash
- Generates ERC-721 metadata with IPFS references
- Stores complete certificate audit trail in database

**Wallet Management**
- Creates custodial Ethereum wallets using eth-account
- Encrypts private keys with envelope encryption (AES-GCM + KMS)
- Supports both local KMS (master key) and AWS KMS modes
- Exports wallets as encrypted keystores with user-specified passwords

**Database Models (`models_db.py`)**
- `Wallet`: Encrypted private key storage with KMS metadata
- `Certificate`: Complete certificate metadata and IPFS references
- `Binding`: Links certificates to blockchain tokens with status tracking

**Key Management (`kms.py`)**
- Protocol-based design supporting multiple KMS providers
- Local mode: Uses base64 master key for envelope encryption
- AWS mode: Integrates with AWS KMS for enterprise security
- All private keys encrypted at rest, never stored in plaintext

**IPFS Integration (`ipfs.py`)**
- Uploads PDFs, manifests, and metadata to IPFS with pinning
- Uses CIDv1 with SHA2-256 for content addressing
- Configurable IPFS API endpoint

### Security Architecture

- **Envelope Encryption**: Private keys encrypted with per-key data keys, data keys encrypted by KMS
- **Memory Safety**: Best-effort wiping of sensitive data from memory
- **Content Verification**: SHA256 checksums for PDF integrity
- **Canonical Hashing**: JCS canonicalization for deterministic manifest hashes
- **API Authentication**: Header-based API key validation

### Configuration

Environment variables prefixed with `CERT_`:
- `CERT_API_KEY`: API authentication key
- `CERT_DATABASE_URL`: SQLite/PostgreSQL connection string
- `CERT_IPFS_API_URL`: IPFS node API endpoint
- `CERT_KMS_MODE`: "local" or "aws"
- `CERT_LOCAL_MASTER_KEY_BASE64`: Base64 master key for local KMS
- `CERT_AWS_KMS_KEY_ID` / `CERT_AWS_REGION`: AWS KMS configuration

### Data Flow

1. **Wallet Creation**: Generate ETH keypair → Envelope encrypt private key → Store in database
2. **Certificate Preparation**: PDF upload → IPFS storage → Manifest generation → Metadata creation → Database persistence
3. **Token Binding**: Links certificate ULIDs to blockchain token IDs for minting

The service acts as a secure bridge between traditional certificate documents and blockchain-based verification systems.