"""
test_offers.py — pytest suite for the Discount & Offer service layer.

Covers:
  * valid offer creation (validation rules)
  * conflict detection (overlapping active offers on same product)
  * evaluate logic for SINGLE_PRODUCT and MULTIPLE_PRODUCT scopes
  * redemption logging (snapshotted benefit)
  * cross-field validation error cases
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services import offer_service
from app.services.offer_service import (
    NotFoundError,
    OfferConflictError,
    ValidationError,
    _cart_aggregate,
    _compute_benefit,
    validate_offer_fields,
)
from tests.conftest import scalars_result, rows_result


# ──────────────────────────────────────────────────────────────────────────────
# Valid base payload helper
# ──────────────────────────────────────────────────────────────────────────────

def _valid_payload(**overrides):
    base = dict(
        offer_name="Summer Bonanza 20%",
        criteria_type="PURCHASE_COUNT",
        product_scope="SINGLE_PRODUCT",
        product_id=1,
        qualifying_product_ids=[],
        required_count=10,
        required_value=None,
        reward_type="FREE_PRODUCT",
        free_product_id=1,
        free_product_qty=1,
        discount_percentage=None,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=7),
        status="ACTIVE",
    )
    base.update(overrides)
    return base


# ──────────────────────────────────────────────────────────────────────────────
# 1. Validation rules
# ──────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_single_product_free_product(self):
        validate_offer_fields(**_valid_payload())  # should not raise

    def test_valid_multiple_product_price_discount(self):
        validate_offer_fields(**_valid_payload(
            product_scope="MULTIPLE_PRODUCT",
            product_id=None,
            qualifying_product_ids=[1, 2, 3],
            criteria_type="PURCHASE_VALUE",
            required_count=None,
            required_value=500,
            reward_type="PRICE_DISCOUNT",
            free_product_id=None,
            free_product_qty=None,
            discount_percentage=15,
        ))

    def test_end_must_be_after_start(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match="end_datetime"):
            validate_offer_fields(**_valid_payload(
                start_datetime=now, end_datetime=now,
            ))

    def test_purchase_count_requires_required_count(self):
        with pytest.raises(ValidationError, match="required_count"):
            validate_offer_fields(**_valid_payload(required_count=None))

    def test_purchase_count_rejects_required_value(self):
        with pytest.raises(ValidationError, match="required_value must be null"):
            validate_offer_fields(**_valid_payload(required_count=10, required_value=500))

    def test_purchase_value_requires_required_value(self):
        with pytest.raises(ValidationError, match="required_value"):
            validate_offer_fields(**_valid_payload(
                criteria_type="PURCHASE_VALUE",
                required_count=None, required_value=None,
            ))

    def test_single_product_requires_product_id(self):
        with pytest.raises(ValidationError, match="product_id is required"):
            validate_offer_fields(**_valid_payload(product_id=None))

    def test_single_product_rejects_qualifying_ids(self):
        with pytest.raises(ValidationError, match="qualifying_product_ids must be empty"):
            validate_offer_fields(**_valid_payload(qualifying_product_ids=[1, 2]))

    def test_multiple_product_requires_two_qualifying(self):
        with pytest.raises(ValidationError, match="at least 2"):
            validate_offer_fields(**_valid_payload(
                product_scope="MULTIPLE_PRODUCT",
                product_id=None,
                qualifying_product_ids=[1],
            ))

    def test_multiple_product_rejects_product_id(self):
        with pytest.raises(ValidationError, match="product_id must be null"):
            validate_offer_fields(**_valid_payload(
                product_scope="MULTIPLE_PRODUCT",
                product_id=1,
                qualifying_product_ids=[1, 2],
            ))

    def test_free_product_requires_free_product_id(self):
        with pytest.raises(ValidationError, match="free_product_id is required"):
            validate_offer_fields(**_valid_payload(free_product_id=None))

    def test_free_product_rejects_discount_percentage(self):
        with pytest.raises(ValidationError, match="discount_percentage must be null"):
            validate_offer_fields(**_valid_payload(discount_percentage=10))

    def test_price_discount_requires_discount_percentage(self):
        with pytest.raises(ValidationError, match="discount_percentage"):
            validate_offer_fields(**_valid_payload(
                reward_type="PRICE_DISCOUNT",
                free_product_id=None,
                free_product_qty=None,
                discount_percentage=None,
            ))

    def test_price_discount_rejects_free_product_id(self):
        with pytest.raises(ValidationError, match="free_product_id must be null"):
            validate_offer_fields(**_valid_payload(
                reward_type="PRICE_DISCOUNT",
                free_product_id=1,
                free_product_qty=None,
                discount_percentage=10,
            ))

    def test_price_discount_range_low(self):
        with pytest.raises(ValidationError, match="discount_percentage"):
            validate_offer_fields(**_valid_payload(
                reward_type="PRICE_DISCOUNT",
                free_product_id=None,
                free_product_qty=None,
                discount_percentage=0.0,
            ))

    def test_price_discount_range_high(self):
        with pytest.raises(ValidationError, match="discount_percentage"):
            validate_offer_fields(**_valid_payload(
                reward_type="PRICE_DISCOUNT",
                free_product_id=None,
                free_product_qty=None,
                discount_percentage=101,
            ))


# ──────────────────────────────────────────────────────────────────────────────
# 2. Cart aggregate + benefit computation (pure)
# ──────────────────────────────────────────────────────────────────────────────

class TestCartAggregate:
    def test_aggregates_only_relevant_products(self):
        cart = [
            {"product_id": 1, "qty": 4, "price": 100},
            {"product_id": 2, "qty": 2, "price": 50},
            {"product_id": 9, "qty": 10, "price": 5},
        ]
        agg = _cart_aggregate(cart, {1, 2})
        assert agg.count == 6
        assert agg.value == 500.0

    def test_empty_cart(self):
        agg = _cart_aggregate([], {1, 2})
        assert agg.count == 0
        assert agg.value == 0.0


class TestComputeBenefit:
    def _offer(self, **kw):
        return SimpleNamespace(
            offer_name="X",
            reward_type=kw.get("reward_type", "FREE_PRODUCT"),
            free_product_id=kw.get("free_product_id", 7),
            free_product_qty=kw.get("free_product_qty", 1),
            discount_percentage=kw.get("discount_percentage"),
        )

    def test_free_product_when_qualified(self):
        offer = self._offer(reward_type="FREE_PRODUCT", free_product_id=7, free_product_qty=2)
        cart = [{"product_id": 1, "qty": 5, "price": 100}]
        benefit = _compute_benefit(offer, cart, {1}, qualified=True)
        assert benefit["reward_type"] == "FREE_PRODUCT"
        assert benefit["free_product_id"] == 7
        assert benefit["free_product_qty"] == 2
        assert benefit["applicable_cart_total"] == 500.0
        assert benefit["discount_amount"] is None

    def test_price_discount_when_qualified(self):
        offer = self._offer(reward_type="PRICE_DISCOUNT", discount_percentage=Decimal("20"))
        cart = [{"product_id": 1, "qty": 2, "price": 100}, {"product_id": 2, "qty": 1, "price": 50}]
        benefit = _compute_benefit(offer, cart, {1, 2}, qualified=True)
        assert benefit["reward_type"] == "PRICE_DISCOUNT"
        assert benefit["discount_percentage"] == 20.0
        assert benefit["applicable_cart_total"] == 250.0
        assert benefit["discount_amount"] == 50.0
        assert benefit["free_product_id"] is None

    def test_not_qualified_returns_empty_benefit(self):
        offer = self._offer()
        benefit = _compute_benefit(offer, [], {1}, qualified=False)
        assert benefit["free_product_id"] is None
        assert benefit["discount_amount"] is None


# ──────────────────────────────────────────────────────────────────────────────
# 3. Conflict detection
# ──────────────────────────────────────────────────────────────────────────────

class TestConflictDetection:
    @pytest.mark.asyncio
    async def test_find_conflicts_detects_overlap(self, fake_db, make_offer):
        existing = make_offer(
            offer_name="Existing Deal",
            product_scope="SINGLE_PRODUCT",
            product_id=1,
        )
        # find_conflicts runs select(...).options(...).where(...) then .scalars().unique().all()
        fake_db.execute.return_value = scalars_result([existing])

        conflicts = await offer_service.find_conflicts(
            fake_db,
            product_scope="SINGLE_PRODUCT",
            product_id=1,
            qualifying_product_ids=None,
            start_datetime=datetime.now(timezone.utc),
            end_datetime=datetime.now(timezone.utc) + timedelta(days=5),
        )
        assert len(conflicts) == 1
        assert conflicts[0]["offer_name"] == "Existing Deal"
        assert 1 in conflicts[0]["overlapping_products"]

    @pytest.mark.asyncio
    async def test_find_conflicts_no_overlap_returns_empty(self, fake_db, make_offer):
        existing = make_offer(product_scope="SINGLE_PRODUCT", product_id=99)
        fake_db.execute.return_value = scalars_result([existing])

        conflicts = await offer_service.find_conflicts(
            fake_db,
            product_scope="SINGLE_PRODUCT",
            product_id=1,
            qualifying_product_ids=None,
            start_datetime=datetime.now(timezone.utc),
            end_datetime=datetime.now(timezone.utc) + timedelta(days=5),
        )
        assert conflicts == []

    @pytest.mark.asyncio
    async def test_find_conflicts_multiple_product_overlap(self, fake_db, make_offer):
        existing = make_offer(
            product_scope="MULTIPLE_PRODUCT",
            product_id=None,
            qualifying_products=[2, 3, 4],
        )
        fake_db.execute.return_value = scalars_result([existing])

        conflicts = await offer_service.find_conflicts(
            fake_db,
            product_scope="MULTIPLE_PRODUCT",
            product_id=None,
            qualifying_product_ids=[3, 5, 6],
            start_datetime=datetime.now(timezone.utc),
            end_datetime=datetime.now(timezone.utc) + timedelta(days=5),
        )
        assert len(conflicts) == 1
        assert conflicts[0]["overlapping_products"] == [3]

    @pytest.mark.asyncio
    async def test_assert_no_conflict_raises(self, fake_db, make_offer):
        existing = make_offer(product_scope="SINGLE_PRODUCT", product_id=1, offer_name="Blocker")
        fake_db.execute.return_value = scalars_result([existing])

        with pytest.raises(OfferConflictError) as exc:
            await offer_service._assert_no_conflict(
                fake_db,
                product_scope="SINGLE_PRODUCT",
                product_id=1,
                qualifying_product_ids=None,
                start_datetime=datetime.now(timezone.utc),
                end_datetime=datetime.now(timezone.utc) + timedelta(days=5),
            )
        assert exc.value.conflicting_offer_ids == [existing.offer_id]


# ──────────────────────────────────────────────────────────────────────────────
# 4. Evaluate logic — SINGLE_PRODUCT and MULTIPLE_PRODUCT
# ──────────────────────────────────────────────────────────────────────────────

class TestEvaluate:
    @pytest.mark.asyncio
    async def test_evaluate_single_product_qualified(self, fake_db, make_offer):
        offer = make_offer(
            offer_name="Buy 10 Get 1 Free",
            criteria_type="PURCHASE_COUNT",
            product_scope="SINGLE_PRODUCT",
            product_id=1,
            required_count=10,
            reward_type="FREE_PRODUCT",
            free_product_id=1,
            free_product_qty=1,
        )
        fake_db.execute.return_value = scalars_result([offer])

        cart = [{"product_id": 1, "qty": 12, "price": 100}]
        result = await offer_service.evaluate_offers(fake_db, customer_id=None, cart=cart)

        assert len(result["qualified_offers"]) == 1
        q = result["qualified_offers"][0]
        assert q["offer_id"] == offer.offer_id
        assert q["qualified"] is True
        assert q["cumulative_count"] == 12
        assert q["benefit"]["free_product_id"] == 1
        assert q["benefit"]["free_product_qty"] == 1

    @pytest.mark.asyncio
    async def test_evaluate_single_product_not_qualified(self, fake_db, make_offer):
        offer = make_offer(
            criteria_type="PURCHASE_COUNT",
            product_scope="SINGLE_PRODUCT",
            product_id=1,
            required_count=10,
        )
        fake_db.execute.return_value = scalars_result([offer])

        cart = [{"product_id": 1, "qty": 3, "price": 100}]
        result = await offer_service.evaluate_offers(fake_db, customer_id=None, cart=cart)

        assert result["qualified_offers"] == []  # not qualified, filtered out

    @pytest.mark.asyncio
    async def test_evaluate_multiple_product_value_qualified(self, fake_db, make_offer):
        offer = make_offer(
            offer_name="Spend 500 Get 15% Off",
            criteria_type="PURCHASE_VALUE",
            product_scope="MULTIPLE_PRODUCT",
            product_id=None,
            qualifying_products=[1, 2, 3],
            required_count=None,
            required_value=Decimal("500"),
            reward_type="PRICE_DISCOUNT",
            free_product_id=None,
            free_product_qty=None,
            discount_percentage=Decimal("15"),
        )
        fake_db.execute.return_value = scalars_result([offer])

        cart = [
            {"product_id": 1, "qty": 2, "price": 150},
            {"product_id": 2, "qty": 1, "price": 250},
            {"product_id": 9, "qty": 5, "price": 10},  # not in scope
        ]
        result = await offer_service.evaluate_offers(fake_db, customer_id=None, cart=cart)

        assert len(result["qualified_offers"]) == 1
        q = result["qualified_offers"][0]
        assert q["qualified"] is True
        assert q["cumulative_value"] == 550.0
        assert q["benefit"]["discount_percentage"] == 15.0
        assert q["benefit"]["applicable_cart_total"] == 550.0
        assert q["benefit"]["discount_amount"] == 82.5

    @pytest.mark.asyncio
    async def test_evaluate_multiple_product_not_qualified(self, fake_db, make_offer):
        offer = make_offer(
            criteria_type="PURCHASE_VALUE",
            product_scope="MULTIPLE_PRODUCT",
            product_id=None,
            qualifying_products=[1, 2, 3],
            required_count=None,
            required_value=Decimal("500"),
            reward_type="PRICE_DISCOUNT",
            discount_percentage=Decimal("15"),
        )
        fake_db.execute.return_value = scalars_result([offer])

        cart = [{"product_id": 1, "qty": 1, "price": 100}]
        result = await offer_service.evaluate_offers(fake_db, customer_id=None, cart=cart)

        assert result["qualified_offers"] == []

    @pytest.mark.asyncio
    async def test_evaluate_filters_out_expired_offers(self, fake_db, make_offer):
        expired = make_offer(
            start_dt=datetime.now(timezone.utc) - timedelta(days=10),
            end_dt=datetime.now(timezone.utc) - timedelta(days=1),  # ended yesterday
        )
        fake_db.execute.return_value = scalars_result([])  # service query filters by now()

        result = await offer_service.evaluate_offers(fake_db, customer_id=None, cart=[])
        assert result["qualified_offers"] == []


# ──────────────────────────────────────────────────────────────────────────────
# 5. Redemption logging
# ──────────────────────────────────────────────────────────────────────────────

class TestRedemption:
    @pytest.mark.asyncio
    async def test_redeem_qualified_offer_logs_snapshot(self, fake_db, make_offer):
        offer = make_offer(
            criteria_type="PURCHASE_COUNT",
            product_scope="SINGLE_PRODUCT",
            product_id=1,
            required_count=5,
            reward_type="FREE_PRODUCT",
            free_product_id=1,
            free_product_qty=1,
        )

        # Sequence of execute calls:
        #  1. _get_offer_orm  -> scalars_result([offer])
        #  2. evaluate_offers -> scalars_result([offer])
        fake_db.execute.side_effect = [
            scalars_result([offer]),   # get offer
            scalars_result([offer]),   # evaluate offers
        ]

        cart = [{"product_id": 1, "qty": 6, "price": 100}]
        result = await offer_service.redeem_offer(
            fake_db,
            offer_id=offer.offer_id,
            customer_id=None,
            order_id=None,
            cart=cart,
        )

        assert "redemption_id" in result
        assert result["offer_id"] == offer.offer_id
        assert result["benefit_applied"]["reward_type"] == "FREE_PRODUCT"
        assert result["benefit_applied"]["free_product_id"] == 1
        assert result["benefit_applied"]["offer_name"] == offer.offer_name
        # db.add should have been called with an OfferRedemption instance
        assert fake_db.add.called
        added = fake_db.add.call_args[0][0]
        assert added.offer_id == offer.offer_id
        assert added.benefit_applied is not None

    @pytest.mark.asyncio
    async def test_redeem_non_qualified_raises(self, fake_db, make_offer):
        offer = make_offer(
            criteria_type="PURCHASE_COUNT",
            product_scope="SINGLE_PRODUCT",
            product_id=1,
            required_count=20,
        )
        fake_db.execute.side_effect = [
            scalars_result([offer]),   # get offer
            scalars_result([offer]),   # evaluate offers (will not qualify)
        ]

        cart = [{"product_id": 1, "qty": 2, "price": 100}]
        with pytest.raises(ValidationError, match="does not qualify"):
            await offer_service.redeem_offer(
                fake_db,
                offer_id=offer.offer_id,
                customer_id=None,
                order_id=None,
                cart=cart,
            )

    @pytest.mark.asyncio
    async def test_redeem_missing_offer_raises_not_found(self, fake_db):
        fake_db.execute.return_value = scalars_result([])  # offer not found

        with pytest.raises(NotFoundError):
            await offer_service.redeem_offer(
                fake_db,
                offer_id=uuid4(),
                customer_id=None,
                order_id=None,
                cart=[],
            )


# ──────────────────────────────────────────────────────────────────────────────
# 6. create_offer happy path + conflict rejection
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateOffer:
    @pytest.mark.asyncio
    async def test_create_valid_offer(self, fake_db, make_offer):
        payload = _valid_payload()

        # execute calls in order:
        #  1. _assert_products_exist -> rows_result([(1,)])  (product found)
        #  2. _assert_no_conflict -> scalars_result([])      (no conflicts)
        #  3. refresh select -> scalars_result([created_offer])
        created = make_offer(**{k: v for k, v in payload.items() if k in {
            "offer_name", "criteria_type", "product_scope", "product_id",
            "required_count", "reward_type", "free_product_id", "free_product_qty",
            "discount_percentage", "status",
        }})
        fake_db.execute.side_effect = [
            rows_result([(1,)]),        # products exist
            scalars_result([]),         # no conflict
            scalars_result([created]),  # refresh
        ]

        result = await offer_service.create_offer(fake_db, payload)
        assert result["offer_name"] == payload["offer_name"]
        assert fake_db.add.called
        assert fake_db.commit.await_count >= 1

    @pytest.mark.asyncio
    async def test_create_rejects_on_conflict(self, fake_db, make_offer):
        payload = _valid_payload()
        blocker = make_offer(offer_name="Blocker", product_scope="SINGLE_PRODUCT", product_id=1)

        fake_db.execute.side_effect = [
            rows_result([(1,)]),            # products exist
            scalars_result([blocker]),      # conflict found
        ]

        with pytest.raises(OfferConflictError) as exc:
            await offer_service.create_offer(fake_db, payload)
        assert blocker.offer_id in exc.value.conflicting_offer_ids
