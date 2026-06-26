import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, SmallInteger, DateTime, Numeric, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False)
    # Role codes (Rule 1.2): 1 = admin, 2 = employee, 3 = shopkeeper, 4 = user
    role = Column(SmallInteger, nullable=False, default=4)
    points = Column(Integer, nullable=False, default=0)
    # Subscription Tiers: 0 = None, 1 = Student, 2 = Premium, 3 = Enterprise
    subscription_tier = Column(SmallInteger, nullable=False, default=0)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

# RFID Card model for one-to-one mapping with User
class RFIDCard(Base):
    __tablename__ = "rfid_cards"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.users.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True)
    rfid_uid = Column(String(255), unique=True, nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("ecommerce.users.id"), nullable=True)

class OTPRecord(Base):
    __tablename__ = "otps"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column("otp_code", String(255), nullable=False)  # HMAC‑SHA256 hash stored in otp_code column
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    attempts = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    resend_count = Column(Integer, default=1)

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    badge = Column(String(50), nullable=True)
    image_url = Column(Text, nullable=True)
    out_of_stock = Column(Boolean, default=False)
    mrp = Column(Numeric(10, 2), nullable=True)
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, default=0)
    images = Column(JSON, nullable=True)
    features = Column(JSON, nullable=True)
    specs = Column(JSON, nullable=True)
    reviews = Column(JSON, nullable=True)
    style_id = Column(String(50), nullable=True)
    hex = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.users.id", ondelete="SET NULL"), nullable=True, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    # Status codes (Rule 1.2): 1 = Pending, 2 = Processing, 3 = Shipped, 4 = Delivered, 5 = Cancelled
    status = Column(SmallInteger, nullable=False, default=1, index=True)
    delivery_type = Column(String(100), nullable=False)
    delivery_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    payment_screenshot_url = Column(Text, nullable=True)
    full_name = Column(String(255), nullable=False)
    street_address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    pin_code = Column(String(20), nullable=False)
    phone_number = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    subtitle = Column(String(255), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    uploaded_file_url = Column(Text, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="items")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.orders.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.users.id", ondelete="SET NULL"), nullable=False, index=True)
    sender_role = Column(SmallInteger, nullable=False)  # 1=admin,2=employee,3=shopkeeper,4=customer
    text = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    order = relationship("Order", backref="chat_messages")
    sender = relationship("User", backref="sent_chat_messages")

# Audit Log model for tracking admin actions
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(255), nullable=False)
    performed_by = Column("user_id", UUID(as_uuid=True), ForeignKey("ecommerce.users.id", ondelete="SET NULL"), nullable=True)
    performed_at = Column("created_at", DateTime(timezone=True), default=datetime.utcnow)
    details = Column(JSON, nullable=True)



class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.orders.id", ondelete="SET NULL"), nullable=True, index=True)
    object_key = Column(String(500), unique=True, nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    category = Column(String(50), nullable=False, index=True) # e.g. 'products', 'tasks', 'print-orders', 'book-prints', 'receipts'
    delete_after = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.users.id", ondelete="CASCADE"), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = {"schema": "ecommerce"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("ecommerce.carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("ecommerce.products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

