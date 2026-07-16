"""
offers.py — Discount & Offer management router
================================================
Thin HTTP layer that delegates business logic to ``app.services.offer_service``
and translates domain exceptions into the consistent ``APIError`` envelope:

    { "error": str, "detail": str, "field": str | null }

Status codes:
    400 — validation failure
    404 — offer / product / customer not found
    409 — date/product conflict on create or update
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.schemas import (
    APIError,
    OfferCreate,
    OfferUpdate,
    OfferResponse,
    OfferRedemptionResponse,
    OfferEvaluateRequest,
    OfferEvaluateResponse,
    OfferRedeemRequest,
    OfferRedeemResponse,
    OfferConflictCheckRequest,
    OfferConflictResponse,
    OfferStatusUpdate,
)
from app.services import offer_service
from app.services.offer_service import (
    NotFoundError,
    OfferConflictError,
    OfferServiceError,
    ValidationError,
)

router = APIRouter(prefix="/api/offers", tags=["Offers & Discounts"])


# ─── Auth helper ──────────────────────────────────────────────────────────────

async def _require_staff(current_user: User = Depends(get_current_user)):
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff members can manage offers",
        )
    return current_user


# ─── Exception → HTTPException translation ────────────────────────────────────

def _err(exc: OfferServiceError, code: int) -> HTTPException:
    body = APIError(error=type(exc).__name__, detail=exc.detail, field=exc.field)
    return HTTPException(status_code=code, detail=body.model_dump())


def _conflict_err(exc: OfferConflictError) -> HTTPException:
    body = {
        "error": "OfferConflictError",
        "detail": exc.detail,
        "field": exc.field,
        "conflicting_offer_ids": [str(i) for i in exc.conflicting_offer_ids],
        "conflicts": exc.conflicts,
    }
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=body)


# ─── Offer CRUD ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[OfferResponse])
async def list_offers(
    status_filter: Optional[str] = Query(None, alias="status"),
    active: Optional[bool] = Query(None, description="true=currently active, false=expired/inactive"),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List offers for the shop, optionally filtered by status / active / name search."""
    try:
        return await offer_service.list_offers(
            db,
            status_filter=status_filter,
            active_only=active,
            search=search,
            limit=limit,
            offset=offset,
        )
    except ValidationError as e:
        raise _err(e, 400) from e


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: OfferCreate,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new offer/discount."""
    try:
        return await offer_service.create_offer(db, payload.model_dump())
    except ValidationError as e:
        raise _err(e, 400) from e
    except NotFoundError as e:
        raise _err(e, 404) from e
    except OfferConflictError as e:
        raise _conflict_err(e) from e


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: UUID,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a single offer detail (includes qualifying products list)."""
    try:
        return await offer_service.get_offer(db, offer_id)
    except NotFoundError as e:
        raise _err(e, 404) from e


@router.put("/{offer_id}", response_model=OfferResponse)
async def replace_offer(
    offer_id: UUID,
    payload: OfferCreate,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Full replacement update of an offer (PUT)."""
    try:
        return await offer_service.update_offer(db, offer_id, payload.model_dump(), full=True)
    except ValidationError as e:
        raise _err(e, 400) from e
    except NotFoundError as e:
        raise _err(e, 404) from e
    except OfferConflictError as e:
        raise _conflict_err(e) from e


@router.patch("/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: UUID,
    payload: OfferUpdate,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Partial update of an offer (PATCH). Kept for backwards compatibility with the existing UI."""
    try:
        return await offer_service.update_offer(db, offer_id, payload.model_dump(exclude_unset=True), full=False)
    except ValidationError as e:
        raise _err(e, 400) from e
    except NotFoundError as e:
        raise _err(e, 404) from e
    except OfferConflictError as e:
        raise _conflict_err(e) from e


@router.patch("/{offer_id}/status", response_model=OfferResponse)
async def toggle_offer_status(
    offer_id: UUID,
    payload: OfferStatusUpdate,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Toggle an offer's status between ACTIVE and INACTIVE only."""
    try:
        return await offer_service.set_offer_status(db, offer_id, payload.status)
    except ValidationError as e:
        raise _err(e, 400) from e
    except NotFoundError as e:
        raise _err(e, 404) from e
    except OfferConflictError as e:
        raise _conflict_err(e) from e


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offer(
    offer_id: UUID,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete/archive an offer."""
    try:
        await offer_service.delete_offer(db, offer_id)
    except NotFoundError as e:
        raise _err(e, 404) from e
    return None


# ─── Offer Evaluation (core business logic) ───────────────────────────────────

@router.post("/evaluate", response_model=OfferEvaluateResponse)
async def evaluate_offers(
    payload: OfferEvaluateRequest,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Given a customer_id + cart contents, return which offers the customer
    qualifies for and what benefit applies. Does NOT auto-apply.
    """
    cart = [item.model_dump() for item in payload.cart]
    return await offer_service.evaluate_offers(
        db,
        customer_id=payload.customer_id,
        cart=cart,
        include_history=payload.include_history,
    )


@router.post("/suggestions")
async def get_offer_suggestions(
    payload: OfferEvaluateRequest,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Live offer suggestions for the billing page. Returns qualified and
    in-progress offers based on the current cart contents (no history).
    """
    cart = [item.model_dump() for item in payload.cart]
    return await offer_service.get_offer_suggestions(db, cart=cart)


@router.post("/redeem", response_model=OfferRedeemResponse)
async def redeem_offer(
    payload: OfferRedeemRequest,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a redemption for a qualified offer and return the snapshotted
    benefit that was applied.
    """
    cart = [item.model_dump() for item in payload.cart]
    try:
        return await offer_service.redeem_offer(
            db,
            offer_id=payload.offer_id,
            customer_id=payload.customer_id,
            order_id=payload.order_id,
            cart=cart,
            include_history=payload.include_history,
        )
    except ValidationError as e:
        raise _err(e, 400) from e
    except NotFoundError as e:
        raise _err(e, 404) from e


# ─── Supporting ───────────────────────────────────────────────────────────────

@router.get("/{offer_id}/conflicts", response_model=OfferConflictResponse)
async def check_offer_conflicts(
    offer_id: UUID,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Check whether an existing offer (by id) conflicts with other active offers
    on the same product(s) + date range. Used by the UI's inline conflict warning.
    """
    try:
        return await offer_service.check_existing_offer_conflicts(db, offer_id)
    except NotFoundError as e:
        raise _err(e, 404) from e


@router.post("/conflicts", response_model=OfferConflictResponse)
async def check_conflicts(
    payload: OfferConflictCheckRequest,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Pre-save conflict check: given a candidate product scope + product id(s) +
    date range, return any conflicting active offers. Used by the UI before save.
    """
    return await offer_service.check_candidate_conflicts(
        db,
        product_scope=payload.product_scope,
        product_id=payload.product_id,
        qualifying_product_ids=payload.qualifying_product_ids,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        exclude_offer_id=payload.exclude_offer_id,
    )


@router.get("/{offer_id}/redemptions", response_model=List[OfferRedemptionResponse])
async def list_offer_redemptions(
    offer_id: UUID,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all redemptions recorded for an offer."""
    try:
        return await offer_service.list_redemptions(db, offer_id)
    except NotFoundError as e:
        raise _err(e, 404) from e
