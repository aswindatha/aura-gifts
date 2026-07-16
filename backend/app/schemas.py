from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.storage_helpers import sign_r2_url

# Role & Subscription Mapping helper to convert database SMALLINT representation to frontend strings
ROLE_MAP = {1: "admin", 2: "employee", 3: "shopkeeper", 4: "user"}
SUB_MAP = {0: "None", 1: "Student", 2: "Silver", 3: "Gold", 4: "Premium"}

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    role: str
    points: int
    subscriptionTier: str
    subscriptionTierCode: int = 0          # raw int 0-4 for edit forms
    subscriptionExpiresAt: Optional[datetime] = None  # UTC, for row colouring
    photo_url: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number: Optional[str] = None
    created_at: datetime
    upi_id: Optional[str] = None
    upi_qr_url: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, user_obj):
        return cls(
            id=user_obj.id,
            name=user_obj.name,
            email=user_obj.email,
            phone=user_obj.phone,
            address=getattr(user_obj, "address", None),
            role=ROLE_MAP.get(user_obj.role, "user"),
            points=user_obj.points,
            subscriptionTier=SUB_MAP.get(user_obj.subscription_tier, "None"),
            subscriptionTierCode=user_obj.subscription_tier,
            subscriptionExpiresAt=getattr(user_obj, "subscription_expires_at", None),
            photo_url=getattr(user_obj, "photo_url", None),
            id_proof_type=getattr(user_obj, "id_proof_type", None),
            id_proof_number=getattr(user_obj, "id_proof_number", None),
            created_at=user_obj.created_at,
            upi_id=getattr(user_obj, "upi_id", None),
            upi_qr_url=getattr(user_obj, "upi_qr_url", None)
        )

class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    subscriptionTier: Optional[str] = None
    photo_url: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number: Optional[str] = None
    points: Optional[int] = None

class AdminUserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    subscriptionTier: Optional[str] = "None"
    photo_url: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number: Optional[str] = None

class AdminEmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    job_title: Optional[str] = "Employee"   # typable role/designation
    password: Optional[str] = "Welcome123"  # custom password, defaults to Welcome123

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class SendOTPRequest(BaseModel):
    email: str
    is_email: bool = True

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
    is_email: bool = True

class SubscribeRequest(BaseModel):
    tier: str

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StandardResponse(BaseModel):
    success: bool
    message: Optional[str] = None

# Product Schemas
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    badge: Optional[str] = None
    image_url: Optional[str] = None
    out_of_stock: Optional[bool] = False
    available_count: Optional[int] = 0
    mrp: Optional[float] = None
    rating: Optional[float] = 4.5
    images: list[str] = []
    features: list[str] = []
    specs: dict = {}
    style_id: Optional[str] = None
    hex: Optional[str] = None
    sku: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    badge: Optional[str] = None
    image_url: Optional[str] = None
    out_of_stock: Optional[bool] = None
    available_count: Optional[int] = None
    mrp: Optional[float] = None
    rating: Optional[float] = None
    images: Optional[list[str]] = None
    features: Optional[list[str]] = None
    specs: Optional[dict] = None
    style_id: Optional[str] = None
    hex: Optional[str] = None
    sku: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    badge: Optional[str] = None
    image_url: Optional[str] = None
    out_of_stock: bool
    available_count: int = 0
    mrp: Optional[float] = None
    rating: Optional[float] = None
    review_count: int = 0
    images: list[str] = []
    features: list[str] = []
    specs: dict = {}
    reviews: list[dict] = []
    style_id: Optional[str] = None
    hex: Optional[str] = None
    sku: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Order Item Schemas
class OrderItemCreate(BaseModel):
    product_name: str
    subtitle: Optional[str] = None
    price: float
    quantity: int
    uploaded_file_url: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: UUID
    product_id: Optional[int] = None
    product_name: str
    subtitle: Optional[str] = None
    price: float
    quantity: int
    uploaded_file_url: Optional[str] = None

    class Config:
        from_attributes = True

# Order Schemas
class OrderCreate(BaseModel):
    total_amount: float
    delivery_type: str
    delivery_cost: float
    payment_screenshot_url: Optional[str] = None
    full_name: str
    street_address: str
    city: str
    pin_code: str
    phone_number: str
    items: list[OrderItemCreate]

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1)

ORDER_STATUS_MAP = {
    1: "Awaiting Payment Verification",
    2: "Paid & Processing",
    3: "Shipped",
    4: "Delivered",
    5: "Cancelled",
    6: "Cancel Requested"
}
REV_ORDER_STATUS_MAP = {v.lower(): k for k, v in ORDER_STATUS_MAP.items()}

class OrderResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    total_amount: float
    status: str
    delivery_type: str
    delivery_cost: float
    payment_screenshot_url: Optional[str] = None
    full_name: str
    street_address: str
    city: str
    pin_code: str
    phone_number: str
    pipeline_steps: Optional[list] = None
    created_at: datetime
    items: list[OrderItemResponse]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, order_obj):
        return cls(
            id=order_obj.id,
            user_id=order_obj.user_id,
            total_amount=float(order_obj.total_amount),
            status=ORDER_STATUS_MAP.get(order_obj.status, "Awaiting Payment Verification"),
            delivery_type=order_obj.delivery_type,
            delivery_cost=float(order_obj.delivery_cost),
            payment_screenshot_url=sign_r2_url(order_obj.payment_screenshot_url),
            full_name=order_obj.full_name,
            street_address=order_obj.street_address,
            city=order_obj.city,
            pin_code=order_obj.pin_code,
            phone_number=order_obj.phone_number,
            pipeline_steps=order_obj.pipeline_steps or [],
            created_at=order_obj.created_at,
            items=[
                OrderItemResponse(
                    id=item.id,
                    product_name=item.product_name,
                    subtitle=item.subtitle,
                    price=float(item.price),
                    quantity=item.quantity,
                    uploaded_file_url=sign_r2_url(item.uploaded_file_url)
                ) for item in order_obj.items
            ]
        )



class ChatMessageCreate(BaseModel):
    text: Optional[str] = None
    image_url: Optional[str] = None

class ChatMessageResponse(BaseModel):
    id: UUID
    order_id: UUID
    sender_user_id: UUID
    sender_role: int
    text: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, chat_obj):
        return cls(
            id=chat_obj.id,
            order_id=chat_obj.order_id,
            sender_user_id=chat_obj.sender_user_id,
            sender_role=chat_obj.sender_role,
            text=chat_obj.text,
            image_url=chat_obj.image_url,
            created_at=chat_obj.created_at,
            read_at=chat_obj.read_at,
        )


# Cart Schemas
class CartItemResponse(BaseModel):
    id: UUID
    product_id: int
    name: str
    price: float
    quantity: int
    unit_price: float
    image_url: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    subtotal: float
    tax: float
    total: float


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


# Razorpay Integration Schemas
class CheckoutRequest(BaseModel):
    payment_method: str = "razorpay"
    delivery_type: str
    delivery_cost: float
    full_name: str
    street_address: str
    city: str
    pin_code: str
    phone_number: str


class CheckoutResponse(BaseModel):
    order_id: UUID
    razorpay_order_id: str
    amount: float
    currency: str = "INR"
    status: str = "pending_payment"


class PaymentVerifyRequest(BaseModel):
    order_id: UUID
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class PaymentVerifyResponse(BaseModel):
    success: bool
    message: str
    order_status: str


class PaymentStatusResponse(BaseModel):
    order_id: UUID
    payment_status: str
    razorpay_payment_id: Optional[str] = None
    amount: float
    updated_at: datetime


class RefundRequest(BaseModel):
    order_id: UUID
    amount: float
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    refund_id: str
    status: str


# ── Workflow Templates ───────────────────────────────────────────────────────

class WorkflowStep(BaseModel):
    id: int
    name: str
    desc: str = ""
    assignee: str = "Unassigned"
    status: str = "Pending"

class WorkflowTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    steps: List[WorkflowStep]

class WorkflowTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    steps: Optional[List[WorkflowStep]] = None
    is_active: Optional[bool] = None

class WorkflowTemplateResponse(BaseModel):
    id: UUID
    name: str
    created_by: UUID
    steps: List[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Customer Info ─────────────────────────────────────────────────────────────

class CustomerInfoCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_sub_user: bool = False

class CustomerInfoUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_sub_user: Optional[bool] = None

class CustomerInfoResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    is_sub_user: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Offer / Discount Management ────────────────────────────────────────────────

class OfferCreate(BaseModel):
    offer_name: str = Field(..., min_length=1, max_length=100)
    criteria_type: str = Field(..., pattern="^(PURCHASE_COUNT|PURCHASE_VALUE)$")
    product_scope: str = Field(..., pattern="^(SINGLE_PRODUCT|MULTIPLE_PRODUCT|ALL_PRODUCTS)$")
    product_id: Optional[int] = None
    qualifying_product_ids: Optional[List[int]] = None
    required_count: Optional[int] = None
    required_value: Optional[float] = None
    reward_type: str = Field(..., pattern="^(FREE_PRODUCT|PRICE_DISCOUNT)$")
    free_product_id: Optional[int] = None
    free_product_qty: Optional[int] = Field(1, ge=1)
    discount_percentage: Optional[float] = Field(None, ge=0.01, le=100)
    start_datetime: datetime
    end_datetime: datetime
    status: str = Field("ACTIVE", pattern="^(ACTIVE|INACTIVE)$")
    promotion_group: Optional[str] = None

class OfferUpdate(BaseModel):
    offer_name: Optional[str] = Field(None, min_length=1, max_length=100)
    criteria_type: Optional[str] = Field(None, pattern="^(PURCHASE_COUNT|PURCHASE_VALUE)$")
    product_scope: Optional[str] = Field(None, pattern="^(SINGLE_PRODUCT|MULTIPLE_PRODUCT|ALL_PRODUCTS)$")
    product_id: Optional[int] = None
    qualifying_product_ids: Optional[List[int]] = None
    required_count: Optional[int] = None
    required_value: Optional[float] = None
    reward_type: Optional[str] = Field(None, pattern="^(FREE_PRODUCT|PRICE_DISCOUNT)$")
    free_product_id: Optional[int] = None
    free_product_qty: Optional[int] = Field(None, ge=1)
    discount_percentage: Optional[float] = Field(None, ge=0.01, le=100)
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(ACTIVE|INACTIVE)$")
    promotion_group: Optional[str] = None

class OfferResponse(BaseModel):
    offer_id: UUID
    offer_name: str
    criteria_type: str
    product_scope: str
    product_id: Optional[int] = None
    qualifying_product_ids: List[int] = []
    required_count: Optional[int] = None
    required_value: Optional[float] = None
    reward_type: str
    free_product_id: Optional[int] = None
    free_product_qty: Optional[int] = None
    discount_percentage: Optional[float] = None
    start_datetime: datetime
    end_datetime: datetime
    status: str
    promotion_group: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OfferRedemptionResponse(BaseModel):
    redemption_id: UUID
    offer_id: UUID
    customer_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    redeemed_at: datetime
    benefit_applied: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ── Offer evaluation & redemption ─────────────────────────────────────────────

class EvaluateCartItem(BaseModel):
    product_id: int
    qty: int = Field(..., ge=1)
    price: float = Field(..., ge=0)


class OfferEvaluateRequest(BaseModel):
    customer_id: Optional[UUID] = None
    cart: List[EvaluateCartItem] = Field(default_factory=list)
    # When True, only the current cart counts toward the threshold.
    # When False, lifetime purchase history (orders) is also summed.
    include_history: bool = Field(False)


class OfferBenefit(BaseModel):
    reward_type: str
    free_product_id: Optional[int] = None
    free_product_qty: Optional[int] = None
    discount_percentage: Optional[float] = None
    discount_amount: Optional[float] = None
    applicable_cart_total: Optional[float] = None


class OfferEvaluateResult(BaseModel):
    offer_id: UUID
    offer_name: str
    criteria_type: str
    product_scope: str
    cumulative_count: Optional[int] = None
    cumulative_value: Optional[float] = None
    required_count: Optional[int] = None
    required_value: Optional[float] = None
    qualified: bool
    benefit: OfferBenefit


class OfferEvaluateResponse(BaseModel):
    customer_id: Optional[UUID] = None
    qualified_offers: List[OfferEvaluateResult]
    evaluated_at: datetime


class OfferRedeemRequest(BaseModel):
    offer_id: UUID
    customer_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    cart: List[EvaluateCartItem] = Field(default_factory=list)
    include_history: bool = Field(False)


class OfferRedeemResponse(BaseModel):
    redemption_id: UUID
    offer_id: UUID
    customer_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    redeemed_at: datetime
    benefit_applied: Dict[str, Any]


class OfferConflictCheckRequest(BaseModel):
    product_id: Optional[int] = None
    qualifying_product_ids: Optional[List[int]] = None
    product_scope: str = Field(..., pattern="^(SINGLE_PRODUCT|MULTIPLE_PRODUCT|ALL_PRODUCTS)$")
    start_datetime: datetime
    end_datetime: datetime
    exclude_offer_id: Optional[UUID] = None


class OfferConflictInfo(BaseModel):
    offer_id: UUID
    offer_name: str
    overlapping_products: List[int]


class OfferConflictResponse(BaseModel):
    has_conflict: bool
    conflicts: List[OfferConflictInfo]


class OfferStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|INACTIVE)$")


# ── Consistent error envelope ─────────────────────────────────────────────────

class APIError(BaseModel):
    error: str
    detail: str
    field: Optional[str] = None

