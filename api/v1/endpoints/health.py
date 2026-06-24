from fastapi import APIRouter, Depends

from core.auth import verify_api_key

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return {"status": "ok"}


@router.get("/protected")
async def health_protected(_: str = Depends(verify_api_key)):
    return {"authenticated": True}
