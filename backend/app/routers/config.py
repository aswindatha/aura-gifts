from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Any
import json

from app.database import get_db
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/config", tags=["SiteConfig"])


class ConfigUpdate(BaseModel):
    value: Any  # Any JSON-serializable value


@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint. Returns the JSON value for a site config key.
    Returns 404 if the key does not exist.
    """
    result = await db.execute(
        text("SELECT value FROM ecommerce.site_config WHERE key = :k"),
        {"k": key}
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Config key '{key}' not found")
    return {"key": key, "value": row.value}


@router.put("/{key}")
async def set_config(
    key: str,
    payload: ConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin-only endpoint. Upserts a JSON blob for a site config key.
    Only role==1 (admin) may write config.
    """
    if current_user.role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may modify site configuration"
        )

    value_json = json.dumps(payload.value)

    await db.execute(
        text("""
            INSERT INTO ecommerce.site_config (key, value, updated_by, updated_at)
            VALUES (:k, :v::jsonb, :uid, NOW())
            ON CONFLICT (key) DO UPDATE
              SET value = EXCLUDED.value,
                  updated_by = EXCLUDED.updated_by,
                  updated_at = NOW()
        """),
        {"k": key, "v": value_json, "uid": str(current_user.id)}
    )
    await db.commit()

    result = await db.execute(
        text("SELECT value, updated_at FROM ecommerce.site_config WHERE key = :k"),
        {"k": key}
    )
    row = result.first()
    return {"key": key, "value": row.value, "updated_at": row.updated_at}
