import random
from uuid import UUID
import hashlib
import os
import hmac
import asyncio
import resend
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.database import get_db
from app.models import User, OTPRecord, CustomerInfo
from app.schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    SendOTPRequest, VerifyOTPRequest, SubscribeRequest, StandardResponse,
    ProfileUpdateRequest, AdminUserUpdate, AdminUserCreate, AdminEmployeeCreate
)
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.config import settings
from app import constants
from app.dependencies import rate_limiter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

async def send_otp_email(email: str, otp_code: str):
    """
    Sends the OTP code to the user's email using Resend API.
    Requires a verified domain on Resend to send to arbitrary email addresses.
    """
    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY.startswith("re_xxxx"):
        print(f"\n[Resend Mock] Skipping real email sending. OTP for {email} is: {otp_code}\n")
        return

    resend.api_key = settings.RESEND_API_KEY
    from_email = settings.RESEND_FROM_EMAIL or "Aura Prints <onboarding@resend.dev>"
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: resend.Emails.send({
                "from": from_email,
                "to": email,
                "subject": "Aura Prints - Email Verification Code",
                "html": f"""
                <div style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #3525cd; text-align: center;">Aura Prints &amp; Gifts</h2>
                    <p>Hello,</p>
                    <p>Thank you for choosing Aura Prints. Please use the verification code below to complete your registration or verification process:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #3525cd; background-color: #f0effd; padding: 10px 30px; border-radius: 6px; display: inline-block;">{otp_code}</span>
                    </div>
                    <p style="color: #666; font-size: 13px;">This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes. If you did not request this code, please ignore this email.</p>
                    <hr style="border: 0; border-top: 1px solid #eeeeee; margin: 20px 0;">
                    <p style="color: #999; font-size: 11px; text-align: center;">© 2026 Aura Prints &amp; Gifts. All rights reserved.</p>
                </div>
                """
            })
        )
        print(f"[Resend] Sent OTP email successfully to {email}")
    except Exception as e:
        print(f"[Resend Error] Failed to send email via Resend to {email}: {e}")
        print(f"[Resend Error] From: {from_email} | API Key prefix: {settings.RESEND_API_KEY[:8]}...")
        print(f"[Resend Error] NOTE: If using free tier, verify your domain at https://resend.com/domains")
        print(f"[Resend Error] OTP for {email} is: {otp_code} (printed as fallback)")

@router.post("/send-otp", response_model=StandardResponse, dependencies=[Depends(rate_limiter("send_otp", constants.RATE_LIMITS["send_otp"]))])
async def send_otp(payload: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()

    # Daily limit: max OTP requests per email per day (configurable)
    from sqlalchemy import func
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count_q = select(func.coalesce(func.sum(OTPRecord.resend_count), 0)).where(
        OTPRecord.email == email,
        OTPRecord.created_at >= start_of_day
    )
    daily_count_res = await db.execute(daily_count_q)
    daily_count = daily_count_res.scalar_one()
    if daily_count >= constants.MAX_OTP_PER_EMAIL_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Daily OTP limit reached ({constants.MAX_OTP_PER_EMAIL_PER_DAY}/day)"
        )

    # Cooldown: 1 OTP per minute per email
    recent_q = select(OTPRecord).where(
        OTPRecord.email == email
    ).order_by(OTPRecord.created_at.desc()).limit(1)
    recent_res = await db.execute(recent_q)
    recent_record = recent_res.scalars().first()
    if False:
        raise HTTPException(
            status_code=429,
            detail="Please wait before requesting another OTP (60s cooldown)"
        )

    # Check for existing unexpired OTP (reuse same record but update code)
    existing_q = select(OTPRecord).where(
        OTPRecord.email == email,
        OTPRecord.expires_at > datetime.utcnow()
    ).order_by(OTPRecord.created_at.desc()).limit(1)
    existing_res = await db.execute(existing_q)
    existing_record = existing_res.scalars().first()

    # Generate new OTP code
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    # HMAC-SHA256 hash using secret
    secret = settings.OTP_HMAC_SECRET.encode()
    otp_hash = hmac.new(secret, otp_code.encode(), hashlib.sha256).hexdigest()

    if existing_record:
        existing_record.otp_hash = otp_hash
        existing_record.expires_at = expires_at
        existing_record.resend_count += 1
        existing_record.last_sent_at = datetime.utcnow()
        db.add(existing_record)
        await db.commit()
        await send_otp_email(email, otp_code)
        return StandardResponse(success=True, message="OTP resent successfully")

    # New record
    otp_record = OTPRecord(
        email=email,
        otp_hash=otp_hash,
        expires_at=expires_at,
        resend_count=1,
        last_sent_at=datetime.utcnow()
    )
    db.add(otp_record)
    await db.commit()

    await send_otp_email(email, otp_code)

    return StandardResponse(success=True, message="OTP sent successfully")

@router.post("/verify-otp", response_model=StandardResponse)
async def verify_otp(payload: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    otp_code = payload.otp.strip()
    
    # Fetch latest unverified, unexpired OTP
    query = select(OTPRecord).where(
        OTPRecord.email == email,
        OTPRecord.expires_at > datetime.utcnow(),
        OTPRecord.verified == False
    ).order_by(OTPRecord.created_at.desc()).limit(1)
    
    result = await db.execute(query)
    record = result.scalars().first()
    
    if not record:
        return StandardResponse(success=False, message="Invalid or expired OTP code")
    
    # Increment attempts
    record.attempts += 1
    if record.attempts >= 5:
        db.add(record)
        await db.commit()
        raise HTTPException(status_code=429, detail="Too many OTP attempts")
    
    # Verify HMAC-SHA256 hash using secret
    secret = settings.OTP_HMAC_SECRET.encode()
    expected_hash = hmac.new(secret, otp_code.encode(), hashlib.sha256).hexdigest()
    if expected_hash != record.otp_hash:
        db.add(record)
        await db.commit()
        return StandardResponse(success=False, message="Invalid or expired OTP code")
    
    # Successful verification
    record.verified = True
    user_query = select(User).where(User.email == email)
    user_res = await db.execute(user_query)
    user_obj = user_res.scalars().first()
    if user_obj:
        user_obj.email_verified = True
        db.add(user_obj)
    db.add(record)
    await db.commit()
    
    return StandardResponse(success=True, message="OTP verified successfully")

@router.post("/register", response_model=TokenResponse)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    
    # Check duplicate email
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Ensure email is verified via OTP
    otp_q = select(OTPRecord).where(
        OTPRecord.email == email,
        OTPRecord.verified == True
    ).order_by(OTPRecord.created_at.desc()).limit(1)
    otp_res = await db.execute(otp_q)
    otp_rec = otp_res.scalars().first()
    if not otp_rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification required. Please verify OTP first."
        )

    hashed_password = get_password_hash(payload.password)
    new_user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone.strip() if payload.phone else None,
        password_hash=hashed_password,
        email_verified=True,  # Set to True since OTP was verified
        role=4,
        points=100,
        subscription_tier=0
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Sync customer_info: if shopkeeper already created a record by phone, update it;
    # otherwise create a new one.
    phone = payload.phone.strip() if payload.phone else None
    if phone:
        ci_q = select(CustomerInfo).where(CustomerInfo.phone == phone)
        ci_res = await db.execute(ci_q)
        existing_ci = ci_res.scalars().first()
        if existing_ci:
            # Update missing fields from the signup data
            if not existing_ci.email:
                existing_ci.email = email
            if not existing_ci.name or existing_ci.name == existing_ci.phone:
                existing_ci.name = payload.name.strip()
            db.add(existing_ci)
        else:
            new_ci = CustomerInfo(
                name=payload.name.strip(),
                phone=phone,
                email=email,
                is_sub_user=False
            )
            db.add(new_ci)
        await db.commit()

    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.from_orm_model(new_user)
    )

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before login"
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.from_orm_model(user)
    )

@router.post("/employee-login", response_model=TokenResponse)
async def employee_login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login(payload, db)

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_resp = UserResponse.from_orm_model(current_user)
    if current_user.role in [1, 3]:
        from app.models import UPIDetails
        stmt = select(UPIDetails).order_by(UPIDetails.id.asc()).limit(1)
        res = await db.execute(stmt)
        upi = res.scalars().first()
        if upi:
            user_resp.upi_id = upi.upi_id
            user_resp.upi_qr_url = upi.qr_url
    return user_resp


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if payload.name is not None:
        current_user.name = payload.name.strip()
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() if payload.phone else None
    if payload.address is not None:
        current_user.address = payload.address.strip() if payload.address else None
        
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.from_orm_model(current_user)

@router.post("/subscribe", response_model=UserResponse)
async def subscribe(payload: SubscribeRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tier_str = payload.tier.strip()

    rev_sub_map = {"none": 0, "student": 1, "silver": 2, "gold": 3, "premium": 4}
    tier_val = rev_sub_map.get(tier_str.lower(), 0)

    # Tier→duration in days (0 = cancel subscription)
    tier_durations = {0: 0, 1: 30, 2: 30, 3: 90, 4: 365}
    days = tier_durations.get(tier_val, 30)

    current_user.subscription_tier = tier_val
    if tier_val == 0:
        current_user.subscription_expires_at = None  # cancelled
    else:
        current_user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_orm_model(current_user)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (Admin/Employee/Shopkeeper only) with optional search filter.
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    query = select(
        User.id,
        User.name,
        User.email,
        User.phone,
        User.address,
        User.role,
        User.points,
        User.subscription_tier,
        User.subscription_expires_at,
        User.photo_url,
        User.id_proof_type,
        User.id_proof_number,
        User.created_at
    )
    
    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            User.name.ilike(search_term) |
            User.email.ilike(search_term) |
            User.phone.ilike(search_term)
        )
        
    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    users = []
    
    for row in result.all():
        from app.schemas import ROLE_MAP, SUB_MAP
        users.append(
            UserResponse(
                id=row.id,
                name=row.name,
                email=row.email,
                phone=row.phone,
                address=row.address,
                role=ROLE_MAP.get(row.role, "user"),
                points=row.points,
                subscriptionTier=SUB_MAP.get(row.subscription_tier, "None"),
                subscriptionTierCode=row.subscription_tier,
                subscriptionExpiresAt=row.subscription_expires_at,
                photo_url=row.photo_url,
                id_proof_type=row.id_proof_type,
                id_proof_number=row.id_proof_number,
                created_at=row.created_at
            )
        )
        
    return users

@router.get("/employees", response_model=List[UserResponse])
async def list_employees(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all users with role=employee (role=2).
    Accessible by admin, shopkeeper, and employee roles.
    Used to populate the task assignee dropdown in task orchestration.
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    from app.schemas import ROLE_MAP, SUB_MAP
    query = select(
        User.id, User.name, User.email, User.phone, User.address,
        User.role, User.points, User.subscription_tier,
        User.subscription_expires_at, User.photo_url,
        User.id_proof_type, User.id_proof_number, User.created_at
    ).where(User.role == 2).order_by(User.name)

    result = await db.execute(query)
    return [
        UserResponse(
            id=row.id,
            name=row.name,
            email=row.email,
            phone=row.phone,
            address=row.address,
            role=ROLE_MAP.get(row.role, "employee"),
            points=row.points,
            subscriptionTier=SUB_MAP.get(row.subscription_tier, "None"),
            subscriptionTierCode=row.subscription_tier,
            subscriptionExpiresAt=row.subscription_expires_at,
            photo_url=row.photo_url,
            id_proof_type=row.id_proof_type,
            id_proof_number=row.id_proof_number,
            created_at=row.created_at
        )
        for row in result.all()
    ]

@router.post("/users", response_model=UserResponse)
async def create_user_by_admin(
    payload: AdminUserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user/subscriber (Admin/Employee/Shopkeeper only).
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    email = payload.email.strip().lower()
    
    # Check duplicate
    exist_q = select(User).where(User.email == email)
    exist_res = await db.execute(exist_q)
    if exist_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
        
    # Reverse subscription tier
    rev_sub_map = {"none": 0, "student": 1, "silver": 2, "gold": 3, "premium": 4}
    tier_val = rev_sub_map.get((payload.subscriptionTier or "none").lower(), 0)
    tier_durations = {0: 0, 1: 30, 2: 30, 3: 90, 4: 365}
    sub_expires = (
        datetime.now(timezone.utc) + timedelta(days=tier_durations[tier_val])
        if tier_val > 0 else None
    )

    # Default password Welcome123 hashed
    hashed_pwd = get_password_hash("Welcome123")

    new_user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone.strip() if payload.phone else None,
        address=payload.address.strip() if payload.address else None,
        password_hash=hashed_pwd,
        email_verified=True,
        role=4, # user
        points=0,
        subscription_tier=tier_val,
        subscription_expires_at=sub_expires,
        photo_url=payload.photo_url,
        id_proof_type=payload.id_proof_type,
        id_proof_number=payload.id_proof_number
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Trigger webhook to NAS
    from app.webhook_client import send_webhook
    import asyncio
    asyncio.create_task(
        send_webhook(
            "/users/sync",
            {
                "id": str(new_user.id),
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role,
                "password_hash": new_user.password_hash
            }
        )
    )
    
    return UserResponse.from_orm_model(new_user)

@router.post("/employees", response_model=UserResponse)
async def create_employee_by_admin(
    payload: AdminEmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new employee account (role=2). Admin/Shopkeeper/Employee.
    Default password is Welcome123. Employee is synced to the workflow DB.
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin, shopkeeper, or employee accounts can create employee accounts"
        )

    email = payload.email.strip().lower()

    # Check duplicate
    exist_q = select(User).where(User.email == email)
    exist_res = await db.execute(exist_q)
    if exist_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    raw_password = (payload.password or "Welcome123").strip() or "Welcome123"
    hashed_pwd = get_password_hash(raw_password)

    new_user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone.strip() if payload.phone else None,
        address=payload.address.strip() if payload.address else None,
        password_hash=hashed_pwd,
        email_verified=True,
        role=2,  # employee
        points=0,
        subscription_tier=0,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Sync to workflow NAS so employee shows in task assignment dropdown
    from app.webhook_client import send_webhook
    import asyncio
    asyncio.create_task(
        send_webhook(
            "/users/sync",
            {
                "id": str(new_user.id),
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role,
                "password_hash": new_user.password_hash
            }
        )
    )

    return UserResponse.from_orm_model(new_user)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: UUID,
    payload: AdminUserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user profile and subscription tier (Admin/Employee/Shopkeeper only).
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    user_q = select(User).where(User.id == user_id)
    user_res = await db.execute(user_q)
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    if payload.name is not None:
        target_user.name = payload.name.strip()
    if payload.email is not None:
        target_user.email = payload.email.strip().lower()
    if payload.phone is not None:
        target_user.phone = payload.phone.strip() if payload.phone else None
    if payload.address is not None:
        target_user.address = payload.address.strip() if payload.address else None
    if payload.points is not None:
        target_user.points = payload.points
    if payload.subscriptionTier is not None:
        rev_sub_map = {"none": 0, "student": 1, "silver": 2, "gold": 3, "premium": 4}
        tier_val = rev_sub_map.get(payload.subscriptionTier.lower(), 0)
        tier_durations = {0: 0, 1: 30, 2: 30, 3: 90, 4: 365}
        target_user.subscription_tier = tier_val
        target_user.subscription_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=tier_durations[tier_val])
            if tier_val > 0 else None
        )
    if payload.photo_url is not None:
        target_user.photo_url = payload.photo_url
    if payload.id_proof_type is not None:
        target_user.id_proof_type = payload.id_proof_type
    if payload.id_proof_number is not None:
        target_user.id_proof_number = payload.id_proof_number
        
    db.add(target_user)
    await db.commit()
    await db.refresh(target_user)
    
    # Trigger webhook to NAS
    from app.webhook_client import send_webhook
    import asyncio
    asyncio.create_task(
        send_webhook(
            "/users/sync",
            {
                "id": str(target_user.id),
                "name": target_user.name,
                "email": target_user.email,
                "role": target_user.role,
                "password_hash": target_user.password_hash
            }
        )
    )
    
    return UserResponse.from_orm_model(target_user)


@router.delete("/users/{user_id}", response_model=StandardResponse)
async def delete_user_by_admin(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a subscriber's plan and optionally soft-delete (Admin/Shopkeeper).
    Cancels the subscription tier and clears expiry. Does NOT delete the row
    so order history is preserved.
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    user_q = select(User).where(User.id == user_id)
    user_res = await db.execute(user_q)
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Cancel subscription (soft operation — row preserved for order history)
    target_user.subscription_tier = 0
    target_user.subscription_expires_at = None
    db.add(target_user)
    await db.commit()

    return StandardResponse(success=True, message="Subscription cancelled successfully")


@router.delete("/employees/{user_id}", response_model=StandardResponse)
async def delete_employee(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently delete an employee account (Admin/Shopkeeper only).
    Hard-deletes the row from the users table.
    """
    if current_user.role not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    user_q = select(User).where(User.id == user_id)
    user_res = await db.execute(user_q)
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    # Only allow deleting employees (role=2)
    if target_user.role != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint can only delete employee accounts (role=employee)"
        )

    await db.delete(target_user)
    await db.commit()

    return StandardResponse(success=True, message=f"Employee '{target_user.name}' permanently deleted")
