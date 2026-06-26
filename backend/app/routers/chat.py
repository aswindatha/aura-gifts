import bleach
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import List, Optional

from app.database import get_db
from app.models import ChatMessage, Order, User
from app.schemas import ChatMessageResponse, ChatMessageCreate, StandardResponse
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/orders", tags=["Order Chat"])

# Helper: check order status visibility
def is_chat_allowed(status_code: int) -> bool:
    return status_code in settings.CHAT_ALLOWED_STATUSES

@router.get("/{order_id}/chat", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    order_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify order belongs to user (or admin/employee/shopkeeper)
    order_q = select(Order).where(Order.id == order_id)
    order_res = await db.execute(order_q)
    order = order_res.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == 4 and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Check chat visibility based on order status
    if not is_chat_allowed(order.status):
        raise HTTPException(status_code=403, detail="Chat not available for this order status")
    # Fetch messages with pagination, newest last
    msgs_q = (
        select(ChatMessage)
        .where(ChatMessage.order_id == order_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
        .offset(offset)
    )
    msgs_res = await db.execute(msgs_q)
    msgs = msgs_res.scalars().all()
    # Return in chronological order (oldest first)
    msgs.reverse()
    return [ChatMessageResponse.from_orm_model(m) for m in msgs]

@router.post("/{order_id}/chat", response_model=StandardResponse)
async def post_chat_message(
    order_id: str,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify order ownership / role
    order_q = select(Order).where(Order.id == order_id)
    order_res = await db.execute(order_q)
    order = order_res.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == 4 and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Visibility check
    if not is_chat_allowed(order.status):
        raise HTTPException(status_code=403, detail="Chat not available for this order status")
    # Rate limiting: max one message per CHAT_RATE_LIMIT_SECONDS per user per order
    rl_q = (
        select(ChatMessage.created_at)
        .where(
            and_(
                ChatMessage.order_id == order_id,
                ChatMessage.sender_user_id == current_user.id,
            )
        )
        .order_by(desc(ChatMessage.created_at))
        .limit(1)
    )
    rl_res = await db.execute(rl_q)
    last_ts = rl_res.scalar_one_or_none()
    if last_ts:
        now_val = datetime.now(timezone.utc) if last_ts.tzinfo else datetime.utcnow()
        if (now_val - last_ts).total_seconds() < settings.CHAT_RATE_LIMIT_SECONDS:
            raise HTTPException(status_code=429, detail="You are sending messages too quickly. Please wait.")
    # Message length validation
    if payload.text and len(payload.text) > settings.CHAT_MAX_LENGTH:
        raise HTTPException(status_code=400, detail="Message exceeds maximum length")
    # Sanitize HTML to prevent XSS
    clean_text = None
    if payload.text:
        clean_text = bleach.clean(payload.text, tags=[], attributes={}, protocols=[], strip=True)
    # Create chat message
    chat_msg = ChatMessage(
        order_id=order_id,
        sender_user_id=current_user.id,
        sender_role=current_user.role,
        text=clean_text,
        image_url=payload.image_url,
        created_at=datetime.utcnow(),
    )
    db.add(chat_msg)
    await db.commit()
    return StandardResponse(success=True, message="Message sent")

@router.patch("/{order_id}/chat/{message_id}/read", response_model=StandardResponse)
async def mark_message_read(
    order_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only admin/employee/shopkeeper can mark as read
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    msg_q = select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.order_id == order_id)
    msg_res = await db.execute(msg_q)
    msg = msg_res.scalars().first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.read_at = datetime.utcnow()
    db.add(msg)
    await db.commit()
    return StandardResponse(success=True, message="Message marked as read")
