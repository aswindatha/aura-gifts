"""
conftest.py — shared pytest fixtures for the offer-service test suite.

The service layer is tested with an ``AsyncMock``-backed fake session so the
tests run without a live PostgreSQL instance. Pure functions (validation,
benefit computation, cart aggregation) are tested directly with no DB at all.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure the backend package is importable when running pytest from the
# backend directory (or from the repo root).
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


@pytest.fixture
def make_offer():
    """Factory for lightweight Offer-like objects used in service tests."""
    from uuid import uuid4

    def _make(
        *,
        offer_id=None,
        offer_name="Test Offer",
        criteria_type="PURCHASE_COUNT",
        product_scope="SINGLE_PRODUCT",
        product_id=1,
        qualifying_products=None,
        required_count=10,
        required_value=None,
        reward_type="FREE_PRODUCT",
        free_product_id=1,
        free_product_qty=1,
        discount_percentage=None,
        status="ACTIVE",
        start_dt=None,
        end_dt=None,
    ):
        from datetime import datetime, timezone, timedelta
        start = start_dt or datetime.now(timezone.utc)
        end = end_dt or (datetime.now(timezone.utc) + timedelta(days=30))
        qps = qualifying_products if qualifying_products is not None else []
        return SimpleNamespace(
            offer_id=offer_id or uuid4(),
            offer_name=offer_name,
            criteria_type=criteria_type,
            product_scope=product_scope,
            product_id=product_id,
            qualifying_products=[SimpleNamespace(product_id=p) for p in qps],
            required_count=required_count,
            required_value=required_value,
            reward_type=reward_type,
            free_product_id=free_product_id,
            free_product_qty=free_product_qty,
            discount_percentage=discount_percentage,
            start_datetime=start,
            end_datetime=end,
            status=status,
            created_at=start,
            updated_at=start,
        )

    return _make


class _ScalarsProxy:
    """Mimics sqlalchemy Result.scalars().unique().all() / .first() chains."""
    def __init__(self, items):
        self._items = list(items)

    def unique(self):
        return self

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class _ScalarsOnly:
    """Mimics Result.scalars() without .unique() (for simple id selects)."""
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class _ResultProxy:
    """Mimics sqlalchemy Result: .scalars() -> chain, .all() -> rows."""
    def __init__(self, scalars=None, rows=None):
        self._scalars = scalars or []
        self._rows = rows or []

    def scalars(self):
        return _ScalarsProxy(self._scalars)

    def all(self):
        return list(self._rows)


@pytest.fixture
def fake_db():
    """
    An AsyncMock standing in for AsyncSession. Individual tests configure the
    return value of ``execute`` via ``fake_db.execute.return_value`` or by
    assigning a side-effect function.
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


def scalars_result(items):
    return _ResultProxy(scalars=items)


def rows_result(rows):
    return _ResultProxy(rows=rows)
