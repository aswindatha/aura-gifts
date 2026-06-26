import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import RFIDCard, User, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/rfid", tags=["RFID Management"])

# Helper to create audit log
async def log_audit(action: str, performed_by_id: str, details: dict, db: AsyncSession):
    audit = AuditLog(action=action, performed_by=performed_by_id, details=details)
    db.add(audit)
    await db.commit()

@router.post("/{user_id}", response_model=dict)
async def assign_rfid(
    user_id: str,
    rfid_uid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Only admin or employee can assign
    if current_user.role not in [1, 2]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Verify target user exists
    user_q = select(User).where(User.id == user_id)
    user_res = await db.execute(user_q)
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if user already has a card
    existing_user_q = select(RFIDCard).where(RFIDCard.user_id == user_id)
    existing_user_res = await db.execute(existing_user_q)
    if existing_user_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has an RFID card")

    # Check if RFID UID already assigned
    existing_uid_q = select(RFIDCard).where(RFIDCard.rfid_uid == rfid_uid)
    existing_uid_res = await db.execute(existing_uid_q)
    if existing_uid_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RFID UID already assigned to another user")

    rfid = RFIDCard(user_id=user_id, rfid_uid=rfid_uid, assigned_by=current_user.id)
    db.add(rfid)
    await db.commit()
    await db.refresh(rfid)
    await log_audit("rfid_assigned", str(current_user.id), {"user_id": user_id, "rfid_uid": rfid_uid}, db)
    return {
        "id": str(rfid.id),
        "user_id": str(rfid.user_id),
        "rfid_uid": rfid.rfid_uid,
        "assigned_at": rfid.assigned_at.isoformat()
    }

@router.get("/{user_id}", response_model=dict)
async def get_rfid(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Users can view their own card; admin/employee can view any
    if current_user.role not in [1, 2] and str(current_user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    q = select(RFIDCard).where(RFIDCard.user_id == user_id)
    res = await db.execute(q)
    card = res.scalars().first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFID card not found for user")
    return {
        "id": str(card.id),
        "user_id": str(card.user_id),
        "rfid_uid": card.rfid_uid,
        "assigned_at": card.assigned_at.isoformat(),
        "assigned_by": str(card.assigned_by) if card.assigned_by else None
    }

@router.delete("/{user_id}", response_model=dict)
async def delete_rfid(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Only admin or employee can delete
    if current_user.role not in [1, 2]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    q = select(RFIDCard).where(RFIDCard.user_id == user_id)
    res = await db.execute(q)
    card = res.scalars().first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFID card not found for user")

    await db.delete(card)
    await db.commit()
    await log_audit("rfid_unassigned", str(current_user.id), {"user_id": user_id}, db)
    return {"detail": "RFID card unassigned successfully"}
