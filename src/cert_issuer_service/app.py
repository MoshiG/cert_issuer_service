# cert_issuer_service/app.py
from fastapi import FastAPI, Depends, Header, HTTPException 
from fastapi.responses import JSONResponse
from sqlmodel import Session
from .settings import get_settings, Settings
from .database import init_db, get_session
from .schemas import (CreateWalletRequest, CreateWalletResponse, ExportWalletRequest,
                      PrepareIssueRequest, PrepareIssueResponse)
from .service import create_custodial_wallet, export_wallet_keystore, prepare_issue


app = FastAPI(title="Certificate Issuer Service", version="2.0.0")

@app.on_event("startup")
def startup():
    init_db()

def require_api_key(x_api_key: str | None = Header(default=None),
                    settings: Settings = Depends(get_settings)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/wallets", response_model=CreateWalletResponse)
def create_wallet(req: CreateWalletRequest,
                  _=Depends(require_api_key),
                  session: Session = Depends(get_session)):
    addr = create_custodial_wallet(session, req.student_ref)
    return JSONResponse(content={"address": addr})

@app.post("/wallets/{address}/export")
def export_wallet(address: str,
                  req: ExportWalletRequest,
                  _=Depends(require_api_key),
                  session: Session = Depends(get_session)):
    ks = export_wallet_keystore(session, address, req.new_password)
    return JSONResponse(content={"keystore_json": ks})

@app.post("/prepare-issue", response_model=PrepareIssueResponse)
def prepare_issue_route(req: PrepareIssueRequest,
                        _=Depends(require_api_key),
                        session: Session = Depends(get_session),
                        settings: Settings = Depends(get_settings)):
    ipfs_url = str(req.ipfs_api_url or settings.ipfs_api_url)
    out = prepare_issue(
        session,
        holder_name=req.holder_name,
        degree_name=req.degree_name,
        issued_date=req.issued_date,
        issuer_id=req.issuer_id,
        pdf_path=req.pdf_path,
        pdf_b64=req.pdf_b64,
        ipfs_api_url=ipfs_url,
        wallet_mode=req.wallet_mode,
        holder_address=req.holder_address,
        keystore_password=req.keystore_password,
        external_url_base=str(req.external_url_base) if req.external_url_base else None,
    )
    return JSONResponse(content=out)
