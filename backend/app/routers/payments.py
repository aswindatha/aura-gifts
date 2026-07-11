import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import razorpay
from pydantic import BaseModel

from app.database import get_db
from app.models import Order, OrderItem, User, Cart, CartItem, Payment, WebhookEvent, Refund, UPIDetails
from app.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PaymentStatusResponse,
    RefundRequest,
    RefundResponse,
    ORDER_STATUS_MAP
)
from app.auth import get_current_user
from app.config import settings

router = APIRouter(tags=["Payments"])

def get_razorpay_client():
    is_dummy = (
        not settings.RAZORPAY_KEY_ID 
        or "xxxx" in settings.RAZORPAY_KEY_ID 
        or settings.RAZORPAY_KEY_ID == "rzp_test_xxxxxx"
    )
    if is_dummy:
        return None
    try:
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except Exception as e:
        print(f"[Razorpay Client Init Warning]: {e}", flush=True)
        return None

@router.post("/api/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Checkout the current user's cart, create an order record, and initialize a Razorpay Order.
    """
    # 1. Fetch active cart
    cart_q = select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == current_user.id)
    cart_res = await db.execute(cart_q)
    cart = cart_res.scalars().first()
    
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty."
        )

    # 2. Calculate totals
    subtotal = sum(float(item.unit_price) * item.quantity for item in cart.items)
    final_total = subtotal + payload.delivery_cost

    # 3. Create the Order model
    new_order = Order(
        user_id=current_user.id,
        total_amount=final_total,
        status=1, # 1 = Awaiting Payment Verification / Pending Payment
        delivery_type=payload.delivery_type,
        delivery_cost=payload.delivery_cost,
        payment_method=payload.payment_method,
        payment_intent_id=None, # will be populated with Razorpay Order ID
        full_name=payload.full_name,
        street_address=payload.street_address,
        city=payload.city,
        pin_code=payload.pin_code,
        phone_number=payload.phone_number
    )
    db.add(new_order)
    await db.flush() # Generate order.id UUID

    # 4. Copy CartItems to OrderItems
    for item in cart.items:
        # Fetch product to copy name
        product_q = select(CartItem).options(selectinload(CartItem.product)).where(CartItem.id == item.id)
        prod_res = await db.execute(product_q)
        cart_item_loaded = prod_res.scalars().first()
        product_name = cart_item_loaded.product.name if cart_item_loaded and cart_item_loaded.product else "Unknown Product"
        
        new_item = OrderItem(
            order_id=new_order.id,
            product_name=product_name,
            subtitle=None,
            price=item.unit_price,
            quantity=item.quantity,
            uploaded_file_url=None
        )
        db.add(new_item)

    # 5. Call Razorpay API to create an order
    client = get_razorpay_client()
    amount_paise = int(final_total * 100)
    
    if client is None:
        # Dummy fallback in development
        razorpay_order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
    else:
        try:
            rzp_order = client.order.create({
                "amount": amount_paise,
                "currency": settings.RAZORPAY_CURRENCY,
                "receipt": str(new_order.id),
                "notes": {
                    "order_id": str(new_order.id),
                    "user_id": str(current_user.id)
                }
            })
            razorpay_order_id = rzp_order["id"]
        except Exception as e:
            if not settings.IS_PRODUCTION:
                razorpay_order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
                print(f"[Razorpay Dev Warning] Failed to create order: {e}. Falling back to mock order ID.", flush=True)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to initiate Razorpay transaction: {str(e)}"
                )

    new_order.payment_intent_id = razorpay_order_id
    db.add(new_order)

    # 6. Create initial Payment entry
    new_payment = Payment(
        order_id=new_order.id,
        razorpay_order_id=razorpay_order_id,
        amount=final_total,
        currency=settings.RAZORPAY_CURRENCY,
        status="created",
        payment_method=payload.payment_method
    )
    db.add(new_payment)

    # 7. Clear database cart items
    clear_q = delete(CartItem).where(CartItem.cart_id == cart.id)
    await db.execute(clear_q)

    await db.commit()

    return CheckoutResponse(
        order_id=new_order.id,
        razorpay_order_id=razorpay_order_id,
        amount=final_total,
        currency=settings.RAZORPAY_CURRENCY,
        status="pending_payment"
    )

@router.post("/api/payment/verify", response_model=PaymentVerifyResponse)
async def verify_payment(
    payload: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify payment signature after frontend checkout completion.
    """
    # 1. Verify owner of the order
    order_q = select(Order).where(Order.id == payload.order_id)
    order_res = await db.execute(order_q)
    order = order_res.scalars().first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this order."
        )

    # 2. Verify signature
    client = get_razorpay_client()
    is_mock = payload.razorpay_order_id.startswith("order_mock_")
    
    verified = False
    if client is None or is_mock:
        verified = True
    else:
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': payload.razorpay_order_id,
                'razorpay_payment_id': payload.razorpay_payment_id,
                'razorpay_signature': payload.razorpay_signature
            })
            verified = True
        except Exception as e:
            verified = False
            print(f"[Razorpay Signature Verify Error]: {e}", flush=True)

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed."
        )

    # 3. Update payment and order records
    pay_q = select(Payment).where(Payment.razorpay_order_id == payload.razorpay_order_id)
    pay_res = await db.execute(pay_q)
    payment = pay_res.scalars().first()

    if payment:
        payment.razorpay_payment_id = payload.razorpay_payment_id
        payment.razorpay_signature = payload.razorpay_signature
        payment.status = "captured"
        db.add(payment)

    # Update order status to 2 (Paid & Processing)
    order.status = 2
    db.add(order)

    await db.commit()

    return PaymentVerifyResponse(
        success=True,
        message="Payment verified successfully",
        order_status="Paid & Processing"
    )

@router.post("/api/webhooks/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Public webhook receiver for Razorpay payment captured/failed events.
    """
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    signature = request.headers.get("x-razorpay-signature")

    client = get_razorpay_client()
    
    # Verify signature
    is_dummy_webhook = not signature or not settings.RAZORPAY_WEBHOOK_SECRET or "xxxx" in settings.RAZORPAY_WEBHOOK_SECRET
    
    if not is_dummy_webhook and client is not None:
        try:
            client.utility.verify_webhook_signature(body_str, signature, settings.RAZORPAY_WEBHOOK_SECRET)
        except Exception as e:
            if settings.IS_PRODUCTION:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")
            else:
                print(f"[Razorpay Webhook Signature Dev Warning] Verification failed: {e}. Proceeding in dev mode.", flush=True)

    # Parse payload
    import json
    try:
        payload = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_id = payload.get("id")
    event_type = payload.get("event")

    if not event_id or not event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event metadata")

    # Idempotent check
    dup_q = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    dup_res = await db.execute(dup_q)
    dup = dup_res.scalars().first()

    if dup:
        return {"status": "duplicate", "message": "Event already processed"}

    # Log webhook event
    new_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        processed=False
    )
    db.add(new_event)
    await db.flush()

    # Process events
    if event_type in ["payment.captured", "order.paid"]:
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rzp_order_id = payment_entity.get("order_id")
        rzp_payment_id = payment_entity.get("id")
        method = payment_entity.get("method")
        
        if rzp_order_id:
            # Find Payment
            pay_q = select(Payment).where(Payment.razorpay_order_id == rzp_order_id)
            pay_res = await db.execute(pay_q)
            payment = pay_res.scalars().first()

            if payment:
                payment.status = "captured"
                payment.razorpay_payment_id = rzp_payment_id
                payment.payment_method = method
                payment.payment_details = payment_entity
                db.add(payment)

                # Update Order status
                order_q = select(Order).where(Order.id == payment.order_id)
                order_res = await db.execute(order_q)
                order = order_res.scalars().first()
                if order:
                    order.status = 2 # Paid & Processing
                    db.add(order)
    elif event_type == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rzp_order_id = payment_entity.get("order_id")
        rzp_payment_id = payment_entity.get("id")

        if rzp_order_id:
            pay_q = select(Payment).where(Payment.razorpay_order_id == rzp_order_id)
            pay_res = await db.execute(pay_q)
            payment = pay_res.scalars().first()
            if payment:
                payment.status = "failed"
                payment.razorpay_payment_id = rzp_payment_id
                payment.payment_details = payment_entity
                db.add(payment)

    new_event.processed = True
    new_event.processed_at = datetime.utcnow()
    db.add(new_event)
    
    await db.commit()

    return {"status": "received"}

@router.get("/api/payment/status/{order_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment status for a specific order.
    """
    # 1. Fetch order to verify ownership
    order_q = select(Order).where(Order.id == order_id)
    order_res = await db.execute(order_q)
    order = order_res.scalars().first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role == 4 and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view the payment status for this order."
        )

    # 2. Fetch latest payment details
    pay_q = select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc())
    pay_res = await db.execute(pay_q)
    payment = pay_res.scalars().first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payments found for this order."
        )

    return PaymentStatusResponse(
        order_id=order.id,
        payment_status=payment.status,
        razorpay_payment_id=payment.razorpay_payment_id,
        amount=float(payment.amount),
        updated_at=payment.updated_at
    )

@router.post("/api/payment/refund", response_model=RefundResponse)
async def refund_payment(
    payload: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Refund a captured payment (Admin only).
    """
    # 1. Check roles: Admin role is 1
    if current_user.role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can initiate refunds."
        )

    # 2. Fetch order and captured payment
    pay_q = select(Payment).where(Payment.order_id == payload.order_id, Payment.status == "captured")
    pay_res = await db.execute(pay_q)
    payment = pay_res.scalars().first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No captured payment exists for this order to refund."
        )

    # 3. Call Razorpay API to refund
    client = get_razorpay_client()
    amount_paise = int(payload.amount * 100)

    if client is None or payment.razorpay_order_id.startswith("order_mock_"):
        refund_id = f"rfnd_mock_{uuid.uuid4().hex[:14]}"
        refund_status = "processed"
    else:
        try:
            rzp_refund = client.refund.create({
                "payment_id": payment.razorpay_payment_id,
                "amount": amount_paise,
                "notes": {
                    "reason": payload.reason or "Admin initiated refund"
                }
            })
            refund_id = rzp_refund["id"]
            refund_status = rzp_refund["status"]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Razorpay refund request failed: {str(e)}"
            )

    # 4. Save Refund log
    new_refund = Refund(
        payment_id=payment.id,
        razorpay_refund_id=refund_id,
        amount=payload.amount,
        reason=payload.reason,
        status=refund_status
    )
    db.add(new_refund)

    # Update Payment status
    if refund_status == "processed":
        payment.status = "refunded"
        db.add(payment)

        # Optionally update Order status to 5 (Cancelled)
        order_q = select(Order).where(Order.id == payload.order_id)
        order_res = await db.execute(order_q)
        order = order_res.scalars().first()
        if order:
            order.status = 5
            db.add(order)

    await db.commit()

    return RefundResponse(
        refund_id=refund_id,
        status=refund_status
    )


class UPIUpdateRequest(BaseModel):
    upi_id: str
    account_holder_name: str = "AURA PRINTS"

@router.get("/api/payment/upi")
async def get_upi_details(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch the configured UPI ID and QR code URL (Admin/Shopkeeper only).
    """
    if current_user.role not in [1, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    stmt = select(UPIDetails).order_by(UPIDetails.id.asc()).limit(1)
    res = await db.execute(stmt)
    upi = res.scalars().first()
    if not upi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UPI details not configured."
        )
    return {
        "upi_id": upi.upi_id,
        "account_holder_name": getattr(upi, "account_holder_name", "AURA PRINTS"),
        "upi_url": upi.upi_url,
        "qr_url": upi.qr_url,
        "updated_at": upi.updated_at
    }

@router.put("/api/payment/upi")
async def update_upi_details(
    payload: UPIUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the system UPI ID, generate the corresponding QR code for Rs.1,
    upload it to R2 (or local mock folder), and save it in the database.
    (Admin only).
    """
    if current_user.role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can modify UPI settings."
        )

    new_upi_id = payload.upi_id.strip()
    new_holder_name = (payload.account_holder_name or "AURA PRINTS").strip()
    if not new_upi_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UPI ID cannot be empty."
        )
    if not new_holder_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account holder name cannot be empty."
        )

    # 1. Construct the UPI URL for Rs.1 (admin test payment)
    import urllib.parse as _urlparse
    pn_encoded = _urlparse.quote(new_holder_name, safe='')
    upi_url = f"upi://pay?pa={new_upi_id}&pn={pn_encoded}&am=1.00&cu=INR&tn=test_payment_from_admin"

    # 2. Generate QR code bytes from external API
    import urllib.parse
    import requests
    encoded_upi_url = urllib.parse.quote(upi_url, safe='')
    qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_upi_url}"

    try:
        response = requests.get(qr_api_url)
        if response.status_code != 200:
            raise Exception("External QR generation service failed.")
        qr_image_bytes = response.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate QR code: {str(e)}"
        )

    # 3. Determine if using local dev mock mode
    is_mock = (
        not settings.R2_ACCESS_KEY_ID or 
        not settings.R2_SECRET_ACCESS_KEY or
        not settings.R2_ACCOUNT_ID or
        settings.R2_ACCESS_KEY_ID == "your_r2_access_key_id" or
        "your_r2" in settings.R2_ACCESS_KEY_ID
    )

    import os
    public_url = ""
    if is_mock:
        # Save locally
        local_key = "banners/upi_qr.png"
        local_path = os.path.join("uploads", local_key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            with open(local_path, "wb") as f:
                f.write(qr_image_bytes)
            public_url = f"{settings.BACKEND_URL}/static/uploads/{local_key}"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save QR code locally: {str(e)}"
            )
    else:
        # Upload to Cloudflare R2
        import boto3
        from botocore.config import Config
        r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url=r2_endpoint,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
            s3_client.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key="banners/upi_qr.png",
                Body=qr_image_bytes,
                ContentType="image/png"
            )
            if settings.R2_PUBLIC_CUSTOM_DOMAIN:
                domain = settings.R2_PUBLIC_CUSTOM_DOMAIN.rstrip("/")
                public_url = f"{domain}/banners/upi_qr.png"
            else:
                public_url = f"{r2_endpoint}/{settings.R2_BUCKET_NAME}/banners/upi_qr.png"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload QR code to R2: {str(e)}"
            )

    # 4. Update the DB table
    stmt = select(UPIDetails).order_by(UPIDetails.id.asc()).limit(1)
    res = await db.execute(stmt)
    upi = res.scalars().first()

    if upi:
        upi.upi_id = new_upi_id
        upi.account_holder_name = new_holder_name
        upi.upi_url = upi_url
        upi.qr_url = public_url
        db.add(upi)
    else:
        upi = UPIDetails(
            upi_id=new_upi_id,
            account_holder_name=new_holder_name,
            upi_url=upi_url,
            qr_url=public_url
        )
        db.add(upi)

    await db.commit()
    await db.refresh(upi)

    return {
        "success": True,
        "upi_id": upi.upi_id,
        "account_holder_name": upi.account_holder_name,
        "upi_url": upi.upi_url,
        "qr_url": upi.qr_url,
        "updated_at": upi.updated_at
    }


class CheckoutQRRequest(BaseModel):
    order_id: str
    amount: float

@router.post("/api/payment/qr")
async def generate_checkout_qr(
    payload: CheckoutQRRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a UPI QR code for a specific order.
    Fetches the admin-configured UPI ID, builds the UPI URL with order_id as
    message and the order amount, generates a QR via api.qrserver.com, uploads
    to R2 (or saves locally in dev), and returns the public QR URL.
    """
    # 1. Fetch configured UPI ID from DB
    stmt = select(UPIDetails).order_by(UPIDetails.id.asc()).limit(1)
    res = await db.execute(stmt)
    upi = res.scalars().first()
    if not upi or not upi.upi_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UPI payment is not configured. Please contact the store."
        )

    upi_id = upi.upi_id.strip()
    holder_name = getattr(upi, "account_holder_name", "AURA PRINTS").strip() or "AURA PRINTS"
    amount = round(float(payload.amount), 2)
    order_id = payload.order_id.strip()

    # 2. Build the UPI URL with order_id as message and real holder name
    import urllib.parse
    import requests as req_lib
    import os

    tn_raw = f"AURA Order {order_id}"
    upi_url = (
        f"upi://pay?pa={upi_id}"
        f"&pn={urllib.parse.quote(holder_name, safe='')}"
        f"&am={amount:.2f}"
        f"&cu=INR"
        f"&tn={urllib.parse.quote(tn_raw, safe='')}"
    )

    # 3. Generate QR image from external service
    encoded_upi = urllib.parse.quote(upi_url, safe='')
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_upi}"
    try:
        r = req_lib.get(qr_api, timeout=10)
        if r.status_code != 200:
            raise Exception(f"QR server returned {r.status_code}")
        qr_bytes = r.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate QR code: {str(e)}"
        )

    # 4. Store the QR (R2 in prod, local disk in dev)
    safe_id = "".join(c for c in order_id if c.isalnum() or c in "-_")
    r2_key = f"receipts/qr_{safe_id}.png"

    is_mock = (
        not settings.R2_ACCESS_KEY_ID
        or not settings.R2_SECRET_ACCESS_KEY
        or not settings.R2_ACCOUNT_ID
        or "your_r2" in settings.R2_ACCESS_KEY_ID
    )

    public_url = ""
    if is_mock:
        local_path = os.path.join("uploads", r2_key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(qr_bytes)
        public_url = f"{settings.BACKEND_URL}/static/uploads/{r2_key}"
    else:
        import boto3
        from botocore.config import Config as BotoConfig
        r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=r2_endpoint,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
                config=BotoConfig(signature_version="s3v4"),
            )
            s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=r2_key,
                Body=qr_bytes,
                ContentType="image/png",
            )
            if settings.R2_PUBLIC_CUSTOM_DOMAIN:
                domain = settings.R2_PUBLIC_CUSTOM_DOMAIN.rstrip("/")
                public_url = f"{domain}/{r2_key}"
            else:
                public_url = f"{r2_endpoint}/{settings.R2_BUCKET_NAME}/{r2_key}"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store QR in R2: {str(e)}"
            )

    return {
        "qr_url": public_url,
        "upi_url": upi_url,
        "upi_id": upi_id,
        "amount": amount,
        "order_id": order_id,
    }
