"""
offer_service.py — Service layer for Discount & Offer management
================================================================
Pure business-logic functions separated from route handlers so they
can be unit-tested without going through the FastAPI layer.

All functions accept an ``AsyncSession`` and raise domain exceptions
(``ValidationError``, ``NotFoundError``, ``OfferConflictError``) which
the router translates into the consistent ``APIError`` HTTP responses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CustomerInfo,
    Offer,
    OfferQualifyingProduct,
    OfferRedemption,
    Order,
    OrderItem,
    Product,
)


# ─── Domain exceptions ────────────────────────────────────────────────────────

class OfferServiceError(Exception):
    """Base exception for offer-service errors."""

    def __init__(self, detail: str, field: Optional[str] = None):
        self.detail = detail
        self.field = field
        super().__init__(detail)


class ValidationError(OfferServiceError):
    """Raised for 400-style validation failures."""


class NotFoundError(OfferServiceError):
    """Raised when an entity (offer/product/customer) is missing."""


class OfferConflictError(OfferServiceError):
    """Raised when an active offer overlaps on the same product(s)/dates."""

    def __init__(self, detail: str, conflicting_offer_ids: List[UUID],
                 conflicts: Optional[List[Dict[str, Any]]] = None):
        self.conflicting_offer_ids = conflicting_offer_ids
        self.conflicts = conflicts or []
        super().__init__(detail)


# ─── Helpers ──────────────────────────────────────────────────────────────────

VALID_CRITERIA = {"PURCHASE_COUNT", "PURCHASE_VALUE"}
VALID_SCOPE = {"SINGLE_PRODUCT", "MULTIPLE_PRODUCT", "ALL_PRODUCTS"}
VALID_REWARD = {"FREE_PRODUCT", "PRICE_DISCOUNT"}
VALID_STATUS = {"ACTIVE", "INACTIVE"}


def _to_float(v: Optional[Decimal]) -> Optional[float]:
    return float(v) if v is not None else None


def offer_to_dict(offer: Offer) -> Dict[str, Any]:
    """Serialise an Offer ORM instance to a response dict (with qualifying ids)."""
    return {
        "offer_id": offer.offer_id,
        "offer_name": offer.offer_name,
        "criteria_type": offer.criteria_type,
        "product_scope": offer.product_scope,
        "product_id": offer.product_id,
        "qualifying_product_ids": [qp.product_id for qp in offer.qualifying_products],
        "required_count": offer.required_count,
        "required_value": _to_float(offer.required_value),
        "reward_type": offer.reward_type,
        "free_product_id": offer.free_product_id,
        "free_product_qty": offer.free_product_qty,
        "discount_percentage": _to_float(offer.discount_percentage),
        "start_datetime": offer.start_datetime,
        "end_datetime": offer.end_datetime,
        "status": offer.status,
        "promotion_group": offer.promotion_group,
        "created_at": offer.created_at,
        "updated_at": offer.updated_at,
    }


def _offer_product_ids(offer: Offer) -> Set[int]:
    if offer.product_scope == "ALL_PRODUCTS":
        return set()  # empty set = all products qualify
    if offer.product_scope == "SINGLE_PRODUCT":
        return {offer.product_id} if offer.product_id is not None else set()
    return {qp.product_id for qp in offer.qualifying_products}


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_offer_fields(
    *,
    offer_name: str,
    criteria_type: str,
    product_scope: str,
    product_id: Optional[int],
    qualifying_product_ids: Optional[List[int]],
    required_count: Optional[int],
    required_value: Optional[float],
    reward_type: str,
    free_product_id: Optional[int],
    free_product_qty: Optional[int],
    discount_percentage: Optional[float],
    start_datetime: datetime,
    end_datetime: datetime,
    status: str,
) -> None:
    """Enforce all cross-field validation rules from the spec."""
    if not offer_name or not offer_name.strip():
        raise ValidationError("offer_name is required", field="offer_name")

    if criteria_type not in VALID_CRITERIA:
        raise ValidationError(f"criteria_type must be one of {VALID_CRITERIA}", field="criteria_type")
    if product_scope not in VALID_SCOPE:
        raise ValidationError(f"product_scope must be one of {VALID_SCOPE}", field="product_scope")
    if reward_type not in VALID_REWARD:
        raise ValidationError(f"reward_type must be one of {VALID_REWARD}", field="reward_type")
    if status not in VALID_STATUS:
        raise ValidationError(f"status must be one of {VALID_STATUS}", field="status")

    # end must be strictly after start
    if end_datetime <= start_datetime:
        raise ValidationError("end_datetime must be strictly after start_datetime", field="end_datetime")

    # criteria rules
    if criteria_type == "PURCHASE_COUNT":
        if required_count is None or required_count < 1:
            raise ValidationError("required_count is required and must be >= 1 when criteria_type = PURCHASE_COUNT", field="required_count")
        if required_value is not None:
            raise ValidationError("required_value must be null when criteria_type = PURCHASE_COUNT", field="required_value")
    else:  # PURCHASE_VALUE
        if required_value is None or required_value <= 0:
            raise ValidationError("required_value is required and must be > 0 when criteria_type = PURCHASE_VALUE", field="required_value")
        if required_count is not None:
            raise ValidationError("required_count must be null when criteria_type = PURCHASE_VALUE", field="required_count")

    # product scope rules
    qids = qualifying_product_ids or []
    if product_scope == "SINGLE_PRODUCT":
        if product_id is None:
            raise ValidationError("product_id is required when product_scope = SINGLE_PRODUCT", field="product_id")
        if qids:
            raise ValidationError("qualifying_product_ids must be empty when product_scope = SINGLE_PRODUCT", field="qualifying_product_ids")
    elif product_scope == "MULTIPLE_PRODUCT":
        if product_id is not None:
            raise ValidationError("product_id must be null when product_scope = MULTIPLE_PRODUCT", field="product_id")
        if len(qids) < 2:
            raise ValidationError("qualifying_product_ids must contain at least 2 entries when product_scope = MULTIPLE_PRODUCT", field="qualifying_product_ids")
    else:  # ALL_PRODUCTS
        if product_id is not None:
            raise ValidationError("product_id must be null when product_scope = ALL_PRODUCTS", field="product_id")
        if qids:
            raise ValidationError("qualifying_product_ids must be empty when product_scope = ALL_PRODUCTS", field="qualifying_product_ids")

    # reward rules
    if reward_type == "FREE_PRODUCT":
        if free_product_id is None:
            raise ValidationError("free_product_id is required when reward_type = FREE_PRODUCT", field="free_product_id")
        if discount_percentage is not None:
            raise ValidationError("discount_percentage must be null when reward_type = FREE_PRODUCT", field="discount_percentage")
    else:  # PRICE_DISCOUNT
        if discount_percentage is None or not (Decimal("0.01") <= Decimal(str(discount_percentage)) <= Decimal("100")):
            raise ValidationError("discount_percentage must be between 0.01 and 100 when reward_type = PRICE_DISCOUNT", field="discount_percentage")
        if free_product_id is not None:
            raise ValidationError("free_product_id must be null when reward_type = PRICE_DISCOUNT", field="free_product_id")


# ─── Conflict detection ───────────────────────────────────────────────────────

async def find_conflicts(
    db: AsyncSession,
    *,
    product_scope: str,
    product_id: Optional[int],
    qualifying_product_ids: Optional[List[int]],
    start_datetime: datetime,
    end_datetime: datetime,
    exclude_offer_id: Optional[UUID] = None,
    promotion_group: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return a list of conflict dicts for ACTIVE offers overlapping on the
    same product(s) and date range. Each dict:
        { offer_id, offer_name, overlapping_products: [int, ...] }

    Carve-out: offers sharing the same promotion_group (tiered promotions)
    are allowed to coexist and do NOT count as conflicts.
    """
    if product_scope == "SINGLE_PRODUCT":
        target_ids: Set[int] = {product_id} if product_id is not None else set()
    else:
        target_ids = set(qualifying_product_ids or [])

    if not target_ids:
        return []

    q = select(Offer).options(selectinload(Offer.qualifying_products)).where(
        Offer.status == "ACTIVE",
        or_(
            and_(Offer.start_datetime <= end_datetime, Offer.end_datetime >= start_datetime),
        ),
    )
    if exclude_offer_id is not None:
        q = q.where(Offer.offer_id != exclude_offer_id)

    result = await db.execute(q)
    existing = result.scalars().unique().all()

    conflicts: List[Dict[str, Any]] = []
    for ex in existing:
        # Carve-out: skip offers in the same promotion_group (tiered promotions)
        if promotion_group is not None and ex.promotion_group == promotion_group:
            continue
        ex_ids = _offer_product_ids(ex)
        overlap = target_ids & ex_ids
        if overlap:
            conflicts.append({
                "offer_id": str(ex.offer_id),
                "offer_name": ex.offer_name,
                "overlapping_products": sorted(overlap),
            })
    return conflicts


async def _assert_no_conflict(
    db: AsyncSession,
    *,
    product_scope: str,
    product_id: Optional[int],
    qualifying_product_ids: Optional[List[int]],
    start_datetime: datetime,
    end_datetime: datetime,
    exclude_offer_id: Optional[UUID] = None,
    promotion_group: Optional[str] = None,
) -> None:
    conflicts = await find_conflicts(
        db,
        product_scope=product_scope,
        product_id=product_id,
        qualifying_product_ids=qualifying_product_ids,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        exclude_offer_id=exclude_offer_id,
        promotion_group=promotion_group,
    )
    if conflicts:
        ids = [c["offer_id"] for c in conflicts]
        names = ", ".join(f"'{c['offer_name']}'" for c in conflicts)
        raise OfferConflictError(
            f"Conflict: active offer(s) {names} overlap on the same product(s) and date range.",
            conflicting_offer_ids=ids,
            conflicts=conflicts,
        )


# ─── Product existence helper ─────────────────────────────────────────────────

async def _assert_products_exist(db: AsyncSession, product_ids: List[int]) -> None:
    if not product_ids:
        return
    res = await db.execute(select(Product.id).where(Product.id.in_(set(product_ids))))
    found = {r[0] for r in res.all()}
    missing = set(product_ids) - found
    if missing:
        raise NotFoundError(f"Product(s) not found: {sorted(missing)}", field="product_id")


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def list_offers(
    db: AsyncSession,
    *,
    status_filter: Optional[str] = None,
    active_only: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List offers with optional status / active / search filters."""
    q = select(Offer).options(selectinload(Offer.qualifying_products))

    if status_filter:
        if status_filter not in VALID_STATUS:
            raise ValidationError("status_filter must be ACTIVE or INACTIVE", field="status_filter")
        q = q.where(Offer.status == status_filter)

    if active_only is True:
        now = datetime.now(timezone.utc)
        q = q.where(
            Offer.status == "ACTIVE",
            Offer.start_datetime <= now,
            Offer.end_datetime >= now,
        )
    elif active_only is False:
        now = datetime.now(timezone.utc)
        q = q.where(or_(Offer.end_datetime < now, Offer.status != "ACTIVE"))

    if search:
        term = f"%{search.strip()}%"
        q = q.where(Offer.offer_name.ilike(term))

    q = q.order_by(Offer.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(q)
    offers = res.scalars().unique().all()
    return [offer_to_dict(o) for o in offers]


async def get_offer(db: AsyncSession, offer_id: UUID) -> Dict[str, Any]:
    res = await db.execute(
        select(Offer).options(selectinload(Offer.qualifying_products)).where(Offer.offer_id == offer_id)
    )
    offer = res.scalars().unique().first()
    if not offer:
        raise NotFoundError("Offer not found", field="offer_id")
    return offer_to_dict(offer)


async def _get_offer_orm(db: AsyncSession, offer_id: UUID) -> Offer:
    res = await db.execute(
        select(Offer).options(selectinload(Offer.qualifying_products)).where(Offer.offer_id == offer_id)
    )
    offer = res.scalars().unique().first()
    if not offer:
        raise NotFoundError("Offer not found", field="offer_id")
    return offer


async def create_offer(db: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create an offer from a dict-like payload (already parsed by Pydantic)."""
    validate_offer_fields(**payload)

    # Validate referenced products exist
    product_refs: List[int] = []
    if payload["product_scope"] == "SINGLE_PRODUCT" and payload["product_id"] is not None:
        product_refs.append(payload["product_id"])
    if payload["product_scope"] == "MULTIPLE_PRODUCT":
        product_refs.extend(payload.get("qualifying_product_ids") or [])
    if payload["reward_type"] == "FREE_PRODUCT" and payload["free_product_id"] is not None:
        product_refs.append(payload["free_product_id"])
    await _assert_products_exist(db, product_refs)

    offer = Offer(
        offer_name=payload["offer_name"].strip(),
        criteria_type=payload["criteria_type"],
        product_scope=payload["product_scope"],
        product_id=payload["product_id"] if payload["product_scope"] == "SINGLE_PRODUCT" else None,
        required_count=payload["required_count"],
        required_value=payload["required_value"],
        reward_type=payload["reward_type"],
        free_product_id=payload["free_product_id"],
        free_product_qty=payload["free_product_qty"] if payload["reward_type"] == "FREE_PRODUCT" else None,
        discount_percentage=payload["discount_percentage"],
        start_datetime=payload["start_datetime"],
        end_datetime=payload["end_datetime"],
        status=payload["status"],
        promotion_group=payload.get("promotion_group"),
    )
    db.add(offer)
    await db.flush()

    if payload["product_scope"] == "MULTIPLE_PRODUCT":
        for pid in payload.get("qualifying_product_ids") or []:
            db.add(OfferQualifyingProduct(offer_id=offer.offer_id, product_id=pid))

    if offer.status == "ACTIVE":
        # Use the payload IDs directly instead of accessing offer.qualifying_products
        # (lazy-loading a relationship in an async session raises MissingGreenlet)
        conflict_qids = (
            payload.get("qualifying_product_ids") or []
            if payload["product_scope"] == "MULTIPLE_PRODUCT"
            else []
        )
        await _assert_no_conflict(
            db,
            product_scope=offer.product_scope,
            product_id=offer.product_id,
            qualifying_product_ids=conflict_qids,
            start_datetime=offer.start_datetime,
            end_datetime=offer.end_datetime,
            exclude_offer_id=offer.offer_id,
            promotion_group=offer.promotion_group,
        )

    await db.commit()
    # refresh with qualifying products loaded
    res = await db.execute(
        select(Offer).options(selectinload(Offer.qualifying_products)).where(Offer.offer_id == offer.offer_id)
    )
    offer = res.scalars().unique().first()
    return offer_to_dict(offer)


def _apply_updates(offer: Offer, payload: Dict[str, Any]) -> None:
    """Apply fields from the effective dict onto the ORM instance, including None values."""
    simple_fields = (
        "offer_name", "criteria_type", "product_scope", "product_id",
        "required_count", "required_value", "reward_type",
        "free_product_id", "free_product_qty", "discount_percentage",
        "start_datetime", "end_datetime", "status", "promotion_group",
    )
    for f in simple_fields:
        if f in payload:
            setattr(offer, f, payload[f])


async def update_offer(
    db: AsyncSession,
    offer_id: UUID,
    payload: Dict[str, Any],
    *,
    full: bool = False,
) -> Dict[str, Any]:
    """
    Update an offer. When ``full`` is True (PUT), missing fields are treated
    as a full replacement; otherwise (PATCH) only provided fields are merged.
    """
    offer = await _get_offer_orm(db, offer_id)

    # Build the effective post-update field set for validation
    current = offer_to_dict(offer)
    effective: Dict[str, Any] = {}
    all_fields = (
        "offer_name", "criteria_type", "product_scope", "product_id",
        "qualifying_product_ids", "required_count", "required_value",
        "reward_type", "free_product_id", "free_product_qty",
        "discount_percentage", "start_datetime", "end_datetime", "status",
        "promotion_group",
    )
    for f in all_fields:
        if f in payload and payload[f] is not None:
            effective[f] = payload[f]
        elif full:
            # For PUT, fall back to current value (we don't reset to defaults)
            effective[f] = current.get(f)
        else:
            effective[f] = current.get(f)

    # qualifying_product_ids handling
    if "qualifying_product_ids" in payload and payload["qualifying_product_ids"] is not None:
        effective["qualifying_product_ids"] = payload["qualifying_product_ids"]
    elif full and payload.get("qualifying_product_ids") is not None:
        effective["qualifying_product_ids"] = payload["qualifying_product_ids"]
    else:
        effective["qualifying_product_ids"] = current.get("qualifying_product_ids") or []

    # Coerce None product_id for MULTIPLE/ALL scope so validation passes
    if effective.get("product_scope") == "MULTIPLE_PRODUCT":
        effective["product_id"] = None
    elif effective.get("product_scope") == "ALL_PRODUCTS":
        effective["product_id"] = None
        effective["qualifying_product_ids"] = []
    elif effective.get("product_scope") == "SINGLE_PRODUCT":
        effective["qualifying_product_ids"] = []

    # Null out irrelevant criteria fields
    if effective.get("criteria_type") == "PURCHASE_COUNT":
        effective["required_value"] = None
    else:
        effective["required_count"] = None

    # Null out irrelevant reward fields
    if effective.get("reward_type") == "FREE_PRODUCT":
        effective["discount_percentage"] = None
    else:
        effective["free_product_id"] = None
        effective["free_product_qty"] = None

    validate_offer_fields(**effective)

    # Validate referenced products
    product_refs: List[int] = []
    if effective["product_scope"] == "SINGLE_PRODUCT" and effective["product_id"] is not None:
        product_refs.append(effective["product_id"])
    if effective["product_scope"] == "MULTIPLE_PRODUCT":
        product_refs.extend(effective.get("qualifying_product_ids") or [])
    if effective["reward_type"] == "FREE_PRODUCT" and effective["free_product_id"] is not None:
        product_refs.append(effective["free_product_id"])
    await _assert_products_exist(db, product_refs)

    # Apply scalar updates
    _apply_updates(offer, effective)

    # Replace qualifying products if provided
    if "qualifying_product_ids" in payload and payload["qualifying_product_ids"] is not None:
        for qp in list(offer.qualifying_products):
            await db.delete(qp)
        await db.flush()
        for pid in payload["qualifying_product_ids"]:
            db.add(OfferQualifyingProduct(offer_id=offer.offer_id, product_id=pid))

    if offer.status == "ACTIVE":
        # Use the effective merged IDs instead of accessing offer.qualifying_products
        # (lazy-loading a relationship in an async session raises MissingGreenlet)
        conflict_qids = (
            effective.get("qualifying_product_ids") or []
            if effective.get("product_scope") == "MULTIPLE_PRODUCT"
            else []
        )
        await _assert_no_conflict(
            db,
            product_scope=offer.product_scope,
            product_id=offer.product_id,
            qualifying_product_ids=conflict_qids,
            start_datetime=offer.start_datetime,
            end_datetime=offer.end_datetime,
            exclude_offer_id=offer.offer_id,
            promotion_group=offer.promotion_group,
        )

    await db.commit()
    res = await db.execute(
        select(Offer).options(selectinload(Offer.qualifying_products)).where(Offer.offer_id == offer.offer_id)
    )
    offer = res.scalars().unique().first()
    return offer_to_dict(offer)


async def set_offer_status(db: AsyncSession, offer_id: UUID, new_status: str) -> Dict[str, Any]:
    if new_status not in VALID_STATUS:
        raise ValidationError("status must be ACTIVE or INACTIVE", field="status")
    offer = await _get_offer_orm(db, offer_id)
    if offer.status == new_status:
        return offer_to_dict(offer)

    offer.status = new_status

    # If activating, ensure no conflicts now appear
    if new_status == "ACTIVE":
        await _assert_no_conflict(
            db,
            product_scope=offer.product_scope,
            product_id=offer.product_id,
            qualifying_product_ids=[qp.product_id for qp in offer.qualifying_products],
            start_datetime=offer.start_datetime,
            end_datetime=offer.end_datetime,
            exclude_offer_id=offer.offer_id,
            promotion_group=offer.promotion_group,
        )

    await db.commit()
    res = await db.execute(
        select(Offer).options(selectinload(Offer.qualifying_products)).where(Offer.offer_id == offer_id)
    )
    offer = res.scalars().unique().first()
    return offer_to_dict(offer)


async def delete_offer(db: AsyncSession, offer_id: UUID) -> None:
    offer = await _get_offer_orm(db, offer_id)
    await db.delete(offer)
    await db.commit()


# ─── Evaluation logic ─────────────────────────────────────────────────────────

@dataclass
class _CartAggregate:
    count: int = 0
    value: float = 0.0
    relevant_product_ids: Set[int] = field(default_factory=set)


async def _customer_history_aggregate(
    db: AsyncSession,
    customer_id: UUID,
    product_ids: Set[int],
) -> _CartAggregate:
    """
    Sum historical purchased qty & value for the given products across the
    customer's completed orders. Uses OrderItem joined to Order.
    Empty product_ids means ALL_PRODUCTS — sum across all products.
    """
    agg = _CartAggregate(relevant_product_ids=product_ids)
    if customer_id is None:
        return agg

    all_products_mode = len(product_ids) == 0

    # Order.user_id is the customer link in this codebase
    if all_products_mode:
        res = await db.execute(
            select(OrderItem.product_id, OrderItem.quantity, OrderItem.price)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.user_id == customer_id)
        )
    else:
        res = await db.execute(
            select(OrderItem.product_id, OrderItem.quantity, OrderItem.price)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == customer_id,
                OrderItem.product_id.in_(product_ids),
            )
        )
    for pid, qty, price in res.all():
        agg.count += int(qty or 0)
        agg.value += float((qty or 0) * (price or 0))
    return agg


def _cart_aggregate(cart: List[Dict[str, Any]], product_ids: Set[int]) -> _CartAggregate:
    agg = _CartAggregate(relevant_product_ids=product_ids)
    # Empty product_ids means ALL_PRODUCTS — every cart item qualifies
    all_products_mode = len(product_ids) == 0
    for item in cart:
        pid = item["product_id"]
        if all_products_mode or pid in product_ids:
            qty = int(item.get("qty", 0))
            price = float(item.get("price", 0))
            agg.count += qty
            agg.value += qty * price
    return agg


async def evaluate_offers(
    db: AsyncSession,
    *,
    customer_id: Optional[UUID],
    cart: List[Dict[str, Any]],
    include_history: bool = False,
) -> Dict[str, Any]:
    """
    Core evaluation: for every ACTIVE offer whose date window contains now(),
    compute the customer's cumulative qualifying count/value (cart only, or
    cart + history) and determine whether the offer is qualified and what
    benefit applies.
    """
    now = datetime.now(timezone.utc)
    q = select(Offer).options(selectinload(Offer.qualifying_products)).where(
        Offer.status == "ACTIVE",
        Offer.start_datetime <= now,
        Offer.end_datetime >= now,
    )
    res = await db.execute(q)
    offers = res.scalars().unique().all()

    results: List[Dict[str, Any]] = []
    for offer in offers:
        target_ids = _offer_product_ids(offer)
        cart_agg = _cart_aggregate(cart, target_ids)

        if include_history and customer_id is not None:
            hist_agg = await _customer_history_aggregate(db, customer_id, target_ids)
            cum_count = cart_agg.count + hist_agg.count
            cum_value = round(cart_agg.value + hist_agg.value, 2)
        else:
            cum_count = cart_agg.count
            cum_value = round(cart_agg.value, 2)

        if offer.criteria_type == "PURCHASE_COUNT":
            required = offer.required_count
            qualified = cum_count >= (required or 0)
            cum_value_out: Optional[float] = None
            required_value_out: Optional[float] = None
        else:
            required = offer.required_value
            required_value_out = _to_float(offer.required_value)
            qualified = cum_value >= float(required or 0)
            cum_count = None  # not relevant for value criteria
            required = None

        benefit = _compute_benefit(offer, cart, target_ids, qualified)

        results.append({
            "offer_id": offer.offer_id,
            "offer_name": offer.offer_name,
            "criteria_type": offer.criteria_type,
            "product_scope": offer.product_scope,
            "cumulative_count": cum_count if offer.criteria_type == "PURCHASE_COUNT" else None,
            "cumulative_value": cum_value if offer.criteria_type == "PURCHASE_VALUE" else None,
            "required_count": offer.required_count if offer.criteria_type == "PURCHASE_COUNT" else None,
            "required_value": required_value_out,
            "qualified": qualified,
            "benefit": benefit,
        })

    return {
        "customer_id": customer_id,
        "qualified_offers": [r for r in results if r["qualified"]],
        "evaluated_at": now,
    }


def _compute_benefit(
    offer: Offer,
    cart: List[Dict[str, Any]],
    target_ids: Set[int],
    qualified: bool,
) -> Dict[str, Any]:
    """Build the benefit payload for an offer (only populated when qualified)."""
    base: Dict[str, Any] = {
        "reward_type": offer.reward_type,
        "free_product_id": None,
        "free_product_qty": None,
        "discount_percentage": None,
        "discount_amount": None,
        "applicable_cart_total": None,
    }
    if not qualified:
        return base

    # Applicable cart total = sum of (qty*price) for relevant products
    applicable_total = 0.0
    for item in cart:
        if item["product_id"] in target_ids:
            applicable_total += int(item.get("qty", 0)) * float(item.get("price", 0))

    if offer.reward_type == "FREE_PRODUCT":
        base["free_product_id"] = offer.free_product_id
        base["free_product_qty"] = offer.free_product_qty or 1
        base["applicable_cart_total"] = round(applicable_total, 2)
    else:  # PRICE_DISCOUNT
        pct = float(offer.discount_percentage or 0)
        base["discount_percentage"] = pct
        base["applicable_cart_total"] = round(applicable_total, 2)
        base["discount_amount"] = round(applicable_total * pct / 100.0, 2)
    return base


# ─── Live Offer Suggestions (billing page) ────────────────────────────────────

async def get_offer_suggestions(
    db: AsyncSession,
    cart: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate all ACTIVE offers against the current cart and return two groups:
      - qualified: cart meets the threshold
      - in_progress: cart has partial progress but hasn't qualified yet

    Only offers with > 0 progress are returned (no irrelevant offers).
    Qualified offers are listed first; in_progress are sorted by
    closest-to-completion (highest progress fraction).
    """
    now = datetime.now(timezone.utc)
    q = select(Offer).options(selectinload(Offer.qualifying_products)).where(
        Offer.status == "ACTIVE",
        Offer.start_datetime <= now,
        Offer.end_datetime >= now,
    )
    res = await db.execute(q)
    offers = res.scalars().unique().all()

    # Fetch product names + prices for the qualifying products (for messages + click-to-add)
    all_product_ids: Set[int] = set()
    for offer in offers:
        all_product_ids |= _offer_product_ids(offer)
    product_names: Dict[int, str] = {}
    product_prices: Dict[int, float] = {}
    if all_product_ids:
        pnames_res = await db.execute(
            select(Product.id, Product.name, Product.price).where(Product.id.in_(all_product_ids))
        )
        for pid, name, price in pnames_res.all():
            product_names[pid] = name
            product_prices[pid] = float(price or 0)

    qualified: List[Dict[str, Any]] = []
    in_progress: List[Dict[str, Any]] = []

    cart_is_empty = len(cart) == 0

    for offer in offers:
        target_ids = _offer_product_ids(offer)
        is_all_products = offer.product_scope == "ALL_PRODUCTS"
        cart_agg = _cart_aggregate(cart, target_ids)

        # Skip offers with zero progress only when cart is non-empty
        # AND the offer is product-specific (ALL_PRODUCTS always shows since any product counts)
        if not cart_is_empty and not is_all_products and cart_agg.count == 0 and cart_agg.value == 0:
            continue

        if offer.criteria_type == "PURCHASE_COUNT":
            required = offer.required_count or 0
            current = cart_agg.count
            qualified_flag = current >= required
            progress_frac = current / required if required > 0 else 1.0
            remaining_count = max(0, required - current)
            remaining_value = None
            current_value = None
            required_value = None
        else:
            required = float(offer.required_value or 0)
            current = round(cart_agg.value, 2)
            qualified_flag = current >= required
            progress_frac = current / required if required > 0 else 1.0
            remaining_value = round(max(0, required - current), 2)
            remaining_count = None
            current_value = current
            required_value = required

        # Build reward description
        if offer.reward_type == "FREE_PRODUCT":
            free_name = product_names.get(offer.free_product_id, f"Product #{offer.free_product_id}")
            reward_desc = f"{offer.free_product_qty or 1}x {free_name} free"
        else:
            pct = float(offer.discount_percentage or 0)
            reward_desc = f"{pct}% off qualifying items"

        # Build "what's still needed" message for in_progress
        remaining_msg = None
        if not qualified_flag:
            if offer.criteria_type == "PURCHASE_COUNT":
                if is_all_products:
                    remaining_msg = f"Add {remaining_count} more unit(s) of any product"
                else:
                    # Find which products from target_ids are in cart vs not
                    cart_pids = {item["product_id"] for item in cart if item["product_id"] in target_ids}
                    missing_pids = target_ids - cart_pids
                    if missing_pids and offer.product_scope == "MULTIPLE_PRODUCT":
                        missing_names = [product_names.get(pid, f"Product #{pid}") for pid in list(missing_pids)[:2]]
                        remaining_msg = f"Add {remaining_count} more unit(s) from: {', '.join(missing_names)}"
                    elif offer.product_scope == "SINGLE_PRODUCT":
                        pname = product_names.get(offer.product_id, f"Product #{offer.product_id}")
                        remaining_msg = f"Add {remaining_count} more {pname}(s)"
                    else:
                        remaining_msg = f"Add {remaining_count} more qualifying unit(s)"
            else:
                if is_all_products:
                    remaining_msg = f"Spend ₹{remaining_value} more on any products to qualify"
                else:
                    remaining_msg = f"Spend ₹{remaining_value} more to qualify"

        # Build progress description
        if offer.criteria_type == "PURCHASE_COUNT":
            progress_desc = f"{current} / {required} units"
        else:
            progress_desc = f"₹{current} / ₹{required_value}"

        # Benefit amount (only for qualified)
        benefit_amount = None
        if qualified_flag:
            if offer.reward_type == "FREE_PRODUCT":
                # Look up free product price for benefit value
                free_p = await db.execute(select(Product.price).where(Product.id == offer.free_product_id))
                free_price = free_p.scalar()
                benefit_amount = round(float(free_price or 0) * (offer.free_product_qty or 1), 2)
            else:
                benefit_amount = round(cart_agg.value * float(offer.discount_percentage or 0) / 100.0, 2)

        # Build qualifying products list (for click-to-add on frontend)
        qualifying_products_list = []
        for pid in sorted(target_ids):
            qualifying_products_list.append({
                "product_id": pid,
                "name": product_names.get(pid, f"Product #{pid}"),
                "price": product_prices.get(pid, 0),
            })

        entry = {
            "offer_id": str(offer.offer_id),
            "offer_name": offer.offer_name,
            "criteria_type": offer.criteria_type,
            "reward_type": offer.reward_type,
            "reward_description": reward_desc,
            "progress_description": progress_desc,
            "progress_fraction": round(progress_frac, 4),
            "remaining_message": remaining_msg,
            "benefit_amount": benefit_amount,
            "current_count": current if offer.criteria_type == "PURCHASE_COUNT" else None,
            "required_count": required if offer.criteria_type == "PURCHASE_COUNT" else None,
            "current_value": current_value,
            "required_value": required_value,
            "free_product_id": offer.free_product_id,
            "free_product_qty": offer.free_product_qty,
            "discount_percentage": _to_float(offer.discount_percentage),
            "product_scope": offer.product_scope,
            "qualifying_products": qualifying_products_list,
        }

        if qualified_flag:
            qualified.append(entry)
        else:
            in_progress.append(entry)

    # Sort in_progress by closest to completion (highest fraction first)
    in_progress.sort(key=lambda e: e["progress_fraction"], reverse=True)

    return {
        "qualified": qualified,
        "in_progress": in_progress,
        "evaluated_at": now,
    }


# ─── Redemption ───────────────────────────────────────────────────────────────

async def redeem_offer(
    db: AsyncSession,
    *,
    offer_id: UUID,
    customer_id: Optional[UUID],
    order_id: Optional[UUID],
    cart: List[Dict[str, Any]],
    include_history: bool = False,
) -> Dict[str, Any]:
    """
    Record a redemption for a qualified offer and snapshot the benefit.
    Returns the redemption dict.
    """
    # Validate referenced entities
    offer = await _get_offer_orm(db, offer_id)

    if customer_id is not None:
        cust = (await db.execute(select(CustomerInfo).where(CustomerInfo.id == customer_id))).scalars().first()
        if not cust:
            raise NotFoundError("Customer not found", field="customer_id")

    if order_id is not None:
        ord_obj = (await db.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not ord_obj:
            raise NotFoundError("Order not found", field="order_id")

    # Must be active & within date window
    now = datetime.now(timezone.utc)
    if offer.status != "ACTIVE" or not (offer.start_datetime <= now <= offer.end_datetime):
        raise ValidationError("Offer is not currently active", field="offer_id")

    # Evaluate to confirm qualification + compute benefit snapshot
    eval_result = await evaluate_offers(
        db,
        customer_id=customer_id,
        cart=cart,
        include_history=include_history,
    )
    matched = next((r for r in eval_result["qualified_offers"] if r["offer_id"] == offer_id), None)
    if not matched:
        raise ValidationError("Customer does not qualify for this offer", field="offer_id")

    benefit_snapshot: Dict[str, Any] = {
        "offer_id": str(offer_id),
        "offer_name": offer.offer_name,
        **matched["benefit"],
        "cumulative_count": matched.get("cumulative_count"),
        "cumulative_value": matched.get("cumulative_value"),
        "redeemed_at": now.isoformat(),
    }

    redemption = OfferRedemption(
        offer_id=offer_id,
        customer_id=customer_id,
        order_id=order_id,
        redeemed_at=now,
        benefit_applied=benefit_snapshot,
    )
    db.add(redemption)
    await db.commit()
    await db.refresh(redemption)

    return {
        "redemption_id": redemption.redemption_id,
        "offer_id": redemption.offer_id,
        "customer_id": redemption.customer_id,
        "order_id": redemption.order_id,
        "redeemed_at": redemption.redeemed_at,
        "benefit_applied": redemption.benefit_applied or {},
    }


async def check_existing_offer_conflicts(
    db: AsyncSession,
    offer_id: UUID,
) -> Dict[str, Any]:
    """Check whether an existing offer conflicts with other active offers."""
    offer = await _get_offer_orm(db, offer_id)
    conflicts = await find_conflicts(
        db,
        product_scope=offer.product_scope,
        product_id=offer.product_id,
        qualifying_product_ids=[qp.product_id for qp in offer.qualifying_products],
        start_datetime=offer.start_datetime,
        end_datetime=offer.end_datetime,
        exclude_offer_id=offer.offer_id,
        promotion_group=offer.promotion_group,
    )
    return {"has_conflict": bool(conflicts), "conflicts": conflicts}


async def check_candidate_conflicts(
    db: AsyncSession,
    *,
    product_scope: str,
    product_id: Optional[int],
    qualifying_product_ids: Optional[List[int]],
    start_datetime: datetime,
    end_datetime: datetime,
    exclude_offer_id: Optional[UUID] = None,
    promotion_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Pre-save conflict check for a candidate offer (not yet persisted)."""
    conflicts = await find_conflicts(
        db,
        product_scope=product_scope,
        product_id=product_id,
        qualifying_product_ids=qualifying_product_ids,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        exclude_offer_id=exclude_offer_id,
        promotion_group=promotion_group,
    )
    return {"has_conflict": bool(conflicts), "conflicts": conflicts}


async def list_redemptions(db: AsyncSession, offer_id: UUID) -> List[Dict[str, Any]]:
    await _get_offer_orm(db, offer_id)  # 404 if missing
    res = await db.execute(
        select(OfferRedemption).where(OfferRedemption.offer_id == offer_id).order_by(OfferRedemption.redeemed_at.desc())
    )
    items = res.scalars().all()
    return [
        {
            "redemption_id": r.redemption_id,
            "offer_id": r.offer_id,
            "customer_id": r.customer_id,
            "order_id": r.order_id,
            "redeemed_at": r.redeemed_at,
            "benefit_applied": r.benefit_applied,
        }
        for r in items
    ]
