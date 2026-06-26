from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Order, OrderItem, User, ChatMessage, Cart, CartItem
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate, StandardResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.post("", response_model=OrderResponse)
async def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order for the authenticated user.
    """
    new_order = Order(
        user_id=current_user.id,
        total_amount=payload.total_amount,
        status=1, # 1 = Awaiting Payment Verification
        delivery_type=payload.delivery_type,
        delivery_cost=payload.delivery_cost,
        payment_screenshot_url=payload.payment_screenshot_url,
        full_name=payload.full_name,
        street_address=payload.street_address,
        city=payload.city,
        pin_code=payload.pin_code,
        phone_number=payload.phone_number
    )
    db.add(new_order)
    await db.flush() # Flush to generate UUID primary key
    
    for item in payload.items:
        new_item = OrderItem(
            order_id=new_order.id,
            product_name=item.product_name,
            subtitle=item.subtitle,
            price=item.price,
            quantity=item.quantity,
            uploaded_file_url=item.uploaded_file_url
        )
        db.add(new_item)

    # Auto-create welcome chat message from Shopkeeper/Admin
    sender_q = select(User).where(User.role == 3).limit(1)
    sender_res = await db.execute(sender_q)
    welcome_sender = sender_res.scalars().first()
    if not welcome_sender:
        sender_q = select(User).where(User.role == 1).limit(1)
        sender_res = await db.execute(sender_q)
        welcome_sender = sender_res.scalars().first()

    if welcome_sender:
        from datetime import datetime
        welcome_msg = ChatMessage(
            order_id=new_order.id,
            sender_user_id=welcome_sender.id,
            sender_role=welcome_sender.role,
            text=f"Hi there! Thank you for ordering with Aura Prints. We have received your screenshot and are verifying your payment of ₹{new_order.total_amount:,.2f}. Feel free to drop any customization notes or reference photos below.",
            created_at=datetime.utcnow()
        )
        db.add(welcome_msg)
        
    # Clear database cart items for the user if a cart exists
    try:
        cart_q = select(Cart).where(Cart.user_id == current_user.id)
        cart_res = await db.execute(cart_q)
        cart_obj = cart_res.scalars().first()
        if cart_obj:
            clear_q = delete(CartItem).where(CartItem.cart_id == cart_obj.id)
            await db.execute(clear_q)
    except Exception as e:
        print(f"[Checkout Error] Failed to clear database cart: {e}", flush=True)

    await db.commit()
    
    # Retrieve order with items loaded
    query = select(Order).options(selectinload(Order.items)).where(Order.id == new_order.id)
    result = await db.execute(query)
    order_db = result.scalars().first()
    
    return OrderResponse.from_orm_model(order_db)

@router.get("", response_model=List[OrderResponse])
async def list_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List orders. Customers see only their own. Admin/Shopkeeper/Staff see all.
    Enforces Rule 2.2 (Pagination) and Role Policies.
    """
    query = select(Order).options(selectinload(Order.items))
    
    # Role filtering: Regular customers (role=4) only see their own orders.
    if current_user.role == 4:
        query = query.where(Order.user_id == current_user.id)
        
    query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return [OrderResponse.from_orm_model(o) for o in orders]

@router.post("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update order status (Simulator or Staff action).
    """
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
        
    new_status_str = payload.status.strip()
    
    from app.schemas import REV_ORDER_STATUS_MAP
    new_status_code = REV_ORDER_STATUS_MAP.get(new_status_str.lower())
    if new_status_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed values: {list(REV_ORDER_STATUS_MAP.keys())}"
        )
        
    # Check permissions
    if current_user.role == 4:
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this order"
            )
        # Regular customer can only request cancellation (status 6)
        if new_status_code != 6:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers can only request cancellation"
            )
            
    order.status = new_status_code
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    return OrderResponse.from_orm_model(order)

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific order.
    Customers can only view their own; staff (admin, employee, shopkeeper) can view any.
    """
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
        
    # Check permissions
    if current_user.role == 4 and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
        
    return OrderResponse.from_orm_model(order)

@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an order (customer owner action).
    Can only cancel if still in pending_payment or processing status.
    """
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
        
    # Check ownership
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )
        
    # Can only cancel if status is 1 (Awaiting Payment) or 2 (Processing)
    if order.status not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled at this stage"
        )
        
    # Update status to 5 (Cancelled)
    order.status = 5
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    return OrderResponse.from_orm_model(order)
