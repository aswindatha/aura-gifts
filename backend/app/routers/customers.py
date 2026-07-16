from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import CustomerInfo, User
from app.schemas import (
    CustomerInfoCreate,
    CustomerInfoUpdate,
    CustomerInfoResponse,
)

router = APIRouter(prefix="/api/customers", tags=["Customer Info"])


async def _require_staff(
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff members can manage customer info"
        )
    return current_user


@router.get("", response_model=List[CustomerInfoResponse])
async def list_customers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db)
):
    """List all customers with optional search filter."""
    query = select(CustomerInfo)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            CustomerInfo.name.ilike(search_term) |
            CustomerInfo.phone.ilike(search_term) |
            CustomerInfo.email.ilike(search_term)
        )

    query = query.order_by(CustomerInfo.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=CustomerInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerInfoCreate,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Create a new customer record. If a customer with the same phone already exists, update it instead."""
    # Check if a customer with this phone already exists
    existing_q = select(CustomerInfo).where(CustomerInfo.phone == payload.phone.strip())
    existing_res = await db.execute(existing_q)
    existing = existing_res.scalars().first()

    if existing:
        # Update existing record with any new info
        existing.name = payload.name.strip()
        if payload.email:
            existing.email = payload.email.strip().lower()
        if payload.address:
            existing.address = payload.address.strip()
        existing.is_sub_user = payload.is_sub_user
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing

    customer = CustomerInfo(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        email=payload.email.strip().lower() if payload.email else None,
        address=payload.address.strip() if payload.address else None,
        is_sub_user=payload.is_sub_user
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerInfoResponse)
async def get_customer(
    customer_id: UUID,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Get a single customer by ID."""
    result = await db.execute(
        select(CustomerInfo).where(CustomerInfo.id == customer_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerInfoResponse)
async def update_customer(
    customer_id: UUID,
    payload: CustomerInfoUpdate,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Update a customer record."""
    result = await db.execute(
        select(CustomerInfo).where(CustomerInfo.id == customer_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.name is not None:
        customer.name = payload.name.strip()
    if payload.phone is not None:
        customer.phone = payload.phone.strip()
    if payload.email is not None:
        customer.email = payload.email.strip().lower() if payload.email else None
    if payload.address is not None:
        customer.address = payload.address.strip() if payload.address else None
    if payload.is_sub_user is not None:
        customer.is_sub_user = payload.is_sub_user

    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    current_user: User = Depends(_require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Delete a customer record."""
    result = await db.execute(
        select(CustomerInfo).where(CustomerInfo.id == customer_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    await db.delete(customer)
    await db.commit()
    return None
