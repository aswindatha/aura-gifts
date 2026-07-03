import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import RFIDCard, User, AuditLog, RFIDScanLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/rfid", tags=["RFID Management"])

# ─── Helper ───────────────────────────────────────────────────────────────────
async def log_audit(action: str, performed_by_id: str, details: dict, db: AsyncSession):
    audit = AuditLog(action=action, performed_by=performed_by_id, details=details)
    db.add(audit)
    await db.commit()


# ─── Lookup by UID (must be BEFORE /{user_id} routes) ────────────────────────

@router.get("/lookup")
async def lookup_rfid_by_uid(
    uid: str = Query(..., description="RFID UID emitted by the card reader"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin/employee endpoint. Given a raw UID (from the keyboard-emulation reader),
    return the linked user + subscription status. Joins user and rfid_cards in a single query.
    Logs every tap event to the rfid_scan_logs table.
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Normalise UID: strip whitespace, uppercase
    uid_normalised = uid.strip().upper()

    # Join query to fetch active card and user details in one SQL query
    stmt = select(User, RFIDCard).join(
        RFIDCard, User.id == RFIDCard.user_id
    ).where(
        RFIDCard.rfid_uid == uid_normalised,
        RFIDCard.is_active == True
    )
    res = await db.execute(stmt)
    row = res.first()

    user = None
    card = None
    sub_status = "not_found"

    if row:
        user, card = row
        now = datetime.now(timezone.utc)
        expires = user.subscription_expires_at

        if expires is None:
            sub_status = "no_plan"
        elif expires > now:
            sub_status = "valid"
        else:
            sub_status = "expired"
    else:
        # Check if the card is registered but deactivated (historically)
        deact_stmt = select(RFIDCard).where(
            RFIDCard.rfid_uid == uid_normalised,
            RFIDCard.is_active == False
        )
        deact_res = await db.execute(deact_stmt)
        deact_card = deact_res.scalars().first()
        if deact_card:
            sub_status = "deactivated"
        else:
            sub_status = "not_found"

    # Write log to rfid_scan_logs
    scan_log = RFIDScanLog(
        rfid_uid=uid_normalised,
        user_id=user.id if user else None,
        status=sub_status,
        scanner_id="admin_console"
    )
    db.add(scan_log)
    await db.commit()

    if sub_status in ["not_found", "deactivated"]:
        return {"status": "not_found", "uid": uid_normalised, "user": None, "card": None}

    # Map tier code → name
    TIER_NAMES = {0: "None", 1: "Student", 2: "Silver", 3: "Gold", 4: "Premium"}

    return {
        "status": sub_status,
        "uid": uid_normalised,
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "photo_url": user.photo_url,
            "subscription_tier": user.subscription_tier,
            "subscription_tier_name": TIER_NAMES.get(user.subscription_tier, "Unknown"),
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
        },
        "card": {
            "id": str(card.id),
            "rfid_uid": card.rfid_uid,
            "assigned_at": card.assigned_at.isoformat(),
        },
    }


# ─── Assign RFID to a user ────────────────────────────────────────────────────

@router.post("/{user_id}", response_model=dict)
async def assign_rfid(
    user_id: str,
    rfid_uid: str,
    replace: bool = Query(False, description="If true, replaces an existing active card for this user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign an RFID card to a user. If replace=true, the previous card is
    deactivated first (used during the Add Card flow for existing subscribers).
    """
    if current_user.role not in [1, 2]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Verify target user exists
    user_q = select(User).where(User.id == user_id)
    user_res = await db.execute(user_q)
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Normalise UID
    rfid_uid = rfid_uid.strip().upper()

    # Check if RFID UID already assigned and active for someone else
    existing_uid_q = select(RFIDCard).where(
        RFIDCard.rfid_uid == rfid_uid,
        RFIDCard.is_active == True
    )
    existing_uid_res = await db.execute(existing_uid_q)
    existing_uid_card = existing_uid_res.scalars().first()
    if existing_uid_card and str(existing_uid_card.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RFID UID already assigned and active for another user"
        )

    # Check if user already has an active card
    existing_user_q = select(RFIDCard).where(
        RFIDCard.user_id == user_id,
        RFIDCard.is_active == True
    )
    existing_user_res = await db.execute(existing_user_q)
    existing_user_card = existing_user_res.scalars().first()

    if existing_user_card:
        # If user already has the exact same card active, just return it
        if existing_user_card.rfid_uid == rfid_uid:
            return {
                "id": str(existing_user_card.id),
                "user_id": str(existing_user_card.user_id),
                "rfid_uid": existing_user_card.rfid_uid,
                "assigned_at": existing_user_card.assigned_at.isoformat(),
            }
            
        if not replace:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has an active RFID card. Use replace=true to re-issue."
            )
        # Replace mode: deactivate old card
        existing_user_card.is_active = False
        existing_user_card.deactivated_at = datetime.now(timezone.utc)
        db.add(existing_user_card)
        await db.flush()
        await log_audit(
            "rfid_deactivated",
            str(current_user.id),
            {"user_id": user_id, "old_rfid_uid": existing_user_card.rfid_uid, "reason": "re-issue"},
            db,
        )

    # Create new active card mapping
    rfid = RFIDCard(user_id=user_id, rfid_uid=rfid_uid, assigned_by=current_user.id, is_active=True)
    db.add(rfid)
    await db.commit()
    await db.refresh(rfid)
    await log_audit(
        "rfid_assigned",
        str(current_user.id),
        {"user_id": user_id, "rfid_uid": rfid_uid, "replaced": replace},
        db,
    )
    return {
        "id": str(rfid.id),
        "user_id": str(rfid.user_id),
        "rfid_uid": rfid.rfid_uid,
        "assigned_at": rfid.assigned_at.isoformat(),
    }


# ─── Get RFID for a user ──────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=dict)
async def get_rfid(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get active RFID card details for a user.
    """
    if current_user.role not in [1, 2] and str(current_user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    q = select(RFIDCard).where(
        RFIDCard.user_id == user_id,
        RFIDCard.is_active == True
    )
    res = await db.execute(q)
    card = res.scalars().first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active RFID card not found for user")
    return {
        "id": str(card.id),
        "user_id": str(card.user_id),
        "rfid_uid": card.rfid_uid,
        "assigned_at": card.assigned_at.isoformat(),
        "assigned_by": str(card.assigned_by) if card.assigned_by else None,
    }


# ─── Unassign (Deactivate) RFID from a user ──────────────────────────────────

@router.delete("/{user_id}", response_model=dict)
async def delete_rfid(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate active RFID card for a user.
    """
    if current_user.role not in [1, 2]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    q = select(RFIDCard).where(
        RFIDCard.user_id == user_id,
        RFIDCard.is_active == True
    )
    res = await db.execute(q)
    card = res.scalars().first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active RFID card not found for user")

    # Instead of deleting card row, deactivate it
    card.is_active = False
    card.deactivated_at = datetime.now(timezone.utc)
    db.add(card)
    await db.commit()
    await log_audit("rfid_deactivated", str(current_user.id), {"user_id": user_id, "reason": "admin_unassigned"}, db)
    return {"detail": "RFID card deactivated successfully"}
