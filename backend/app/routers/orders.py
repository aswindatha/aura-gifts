from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Order, OrderItem, User, ChatMessage, Cart, CartItem
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate, StandardResponse
from app.constants import OrderStatus
from sqlalchemy import delete
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

import hmac
import hashlib

WEBHOOK_SECRET = "your_webhook_secret_key"

async def verify_webhook_signature(request: Request):
    """Verifies HMAC signature from local NAS backend"""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        print("Webhook Error: Missing X-Webhook-Signature header")
        raise HTTPException(status_code=401, detail="Missing signature")
    
    body = await request.body()
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    print(f"DEBUG Webhook: Received signature={signature}")
    print(f"DEBUG Webhook: Received body={body}")
    print(f"DEBUG Webhook: Expected signature={expected_signature}")

    if not hmac.compare_digest(signature, expected_signature):
        print("Webhook Error: Signature mismatch")
        raise HTTPException(status_code=401, detail="Invalid signature")

from app.webhook_schemas import WebhookOrderStatusUpdate
@router.post("/webhook/status", response_model=dict)
async def update_order_status_from_nas(
    payload: WebhookOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_webhook_signature)
):
    """
    Receive order/pipeline status updates from the local NAS workflow backend.
    """
    # Basic logic to just update the overall order status if a step changes.
    # In a real system, you might want to sync the entire pipeline back or just specific fields.
    query = select(Order).where(Order.id == payload.order_id)
    result = await db.execute(query)
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # If a pipeline step is completed, maybe update the whole order if all are completed,
    # or just update the pipeline JSON. For this demo, let's just log it.
    print(f"Received NAS webhook for Order {payload.order_id}: step {payload.step_id} is now {payload.status}")

    # Update pipeline steps inside JSONB if the step is not "final"
    if order.pipeline_steps and payload.step_id != "final":
        try:
            target_step_id = int(payload.step_id)
            updated_steps = []
            for step in order.pipeline_steps:
                if step.get("id") == target_step_id:
                    updated_step = {**step, "status": payload.status}
                    if payload.proof_url:
                        updated_step["proof_url"] = payload.proof_url
                    updated_steps.append(updated_step)
                else:
                    updated_steps.append(step)
            order.pipeline_steps = updated_steps
        except (ValueError, TypeError) as e:
            print(f"Error parsing step_id in webhook: {e}")
    
    # Example logic: if any step is completed, we could move order to processing
    if payload.status == 'Completed' and order.status < 3:
        order.status = 2 # Processing
    elif payload.status == 'Shipped':
        order.status = 3 # Shipped
        
    db.add(order)
    await db.commit()

    return {"status": "ok"}

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
    if new_status_code == 4: # 4 = Delivered (from ORDER_STATUS_MAP)
        await db.execute(delete(ChatMessage).where(ChatMessage.order_id == order.id))
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

from pydantic import BaseModel

class PipelineStepsUpdate(BaseModel):
    steps: list

@router.put("/{order_id}/pipeline", response_model=OrderResponse)
async def update_order_pipeline(
    order_id: UUID,
    payload: PipelineStepsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the pipeline steps for a specific order (Admin/Shopkeeper/Staff only).
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
        
    order.pipeline_steps = payload.steps
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Trigger webhook to NAS
    from app.webhook_client import send_webhook
    import asyncio
    asyncio.create_task(
        send_webhook(
            "/tasks/sync",
            {
                "id": str(order.id),
                "order_details": {
                    "full_name": order.full_name,
                    "city": order.city,
                    "total_amount": float(order.total_amount),
                    "delivery_type": order.delivery_type
                },
                "steps": payload.steps
            }
        )
    )
    
    return OrderResponse.from_orm_model(order)



