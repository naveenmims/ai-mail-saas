import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(tags=["demo"])

def _require_demo(x_demo_token: Optional[str] = None) -> None:
    # Demo endpoints only available when DEMO_MODE=1
    if os.getenv("DEMO_MODE", "0") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    # Optional token gate: if DEMO_TOKEN is set, require header X-Demo-Token
    expected = os.getenv("DEMO_TOKEN", "").strip()
    if expected:
        if not x_demo_token or x_demo_token != expected:
            raise HTTPException(status_code=404, detail="Not found")

@router.get("/demo/info")
def demo_info(x_demo_token: Optional[str] = Header(default=None, alias="X-Demo-Token")):
    _require_demo(x_demo_token)
    return {
        "demo_mode": True,
        "demo_org_name": os.getenv("DEMO_ORG_NAME", "BookURL Demo"),
        "demo_owner_email": os.getenv("DEMO_OWNER_EMAIL", "demo@bookurl.info"),
    }
