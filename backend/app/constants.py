# Centralized enumerations and constants for Aura Prints backend

# Order status mapping (1-7)
class OrderStatus:
    PENDING = 1
    PROCESSING = 2
    SHIPPED = 3
    IN_TRANSIT = 4
    OUT_FOR_DELIVERY = 5
    DELIVERED = 6
    CANCELLED = 7

# Subscription tier mapping (0-4)
class SubscriptionTier:
    NONE = 0
    STUDENT = 1
    BASIC = 2
    PREMIUM = 3
    ENTERPRISE = 4

# User role mapping (1=admin, 2=employee, 3=shopkeeper, 4=user)
class UserRole:
    ADMIN = 1
    EMPLOYEE = 2
    SHOPKEEPER = 3
    CUSTOMER = 4

# OTP request limits
MAX_OTP_PER_EMAIL_PER_DAY = 3
OTP_EXPIRATION_MINUTES = 10

# Resend email configuration (API key loaded from environment)
import os
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

# Rate limit configuration (requests per minute)
RATE_LIMITS = {
    "send_otp": "5/minute",
    "login": "10/minute",
    "assign_rfid": "5/minute",
}

# Audit action types
class AuditAction:
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    RFID_ASSIGNED = "rfid_assigned"
    RFID_UNASSIGNED = "rfid_unassigned"
    ORDER_STATUS_CHANGED = "order_status_changed"
    OTP_SENT = "otp_sent"
    EMAIL_SENT = "email_sent"
