import secrets

from fastapi import Header, HTTPException, status

from .config import get_settings


async def require_api_key(x_api_key: str = Header(...)) -> None:
    configured = get_settings().ingest_api_key
    if not secrets.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
