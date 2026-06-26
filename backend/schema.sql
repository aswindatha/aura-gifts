-- =============================================================================
-- 1. Enable Extensions & Isolated Schemas
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS auth;

CREATE OR REPLACE FUNCTION auth.uid()
RETURNS uuid
LANGUAGE sql STABLE
AS $$
  select nullif(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid;
$$;

CREATE SCHEMA IF NOT EXISTS ecommerce;
CREATE SCHEMA IF NOT EXISTS maintenance;

-- =============================================================================
-- 2. ECOSYSTEM TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 2.1 Users Table (ecommerce.users)
-- -----------------------------------------------------------------------------
-- Stores all user accounts. Role mapping: 1=admin, 2=employee, 3=shopkeeper, 4=customer.
-- Subscription tier: 0=None, 1=Student, 2=Premium, 3=Enterprise.
-- Passwords are hashed (never stored in plain text).
-- Points accumulate for loyalty (can be used for discounts).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,                          -- Full name
    email VARCHAR(255) UNIQUE NOT NULL,                  -- Unique email (used for login)
    phone VARCHAR(50),                                  -- Contact number
    password_hash VARCHAR(255) NOT NULL,                -- bcrypt/argon2 hash
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,      -- Must be true before registration complete
    role SMALLINT NOT NULL DEFAULT 4,                   -- 1=admin,2=employee,3=shopkeeper,4=customer
    points INTEGER NOT NULL DEFAULT 0,                  -- Loyalty points balance
    subscription_tier SMALLINT NOT NULL DEFAULT 0,      -- 0=None,1=Student,2=Premium,3=Enterprise
    subscription_expires_at TIMESTAMP WITH TIME ZONE,   -- Expiry timestamp for subscriptions
    address TEXT,                                       -- Shipping address (can be updated)
    photo_url VARCHAR(500),                             -- Profile/Subscriber photo URL
    id_proof_type VARCHAR(100),                         -- Aadhaar, PAN, etc.
    id_proof_number VARCHAR(100),                       -- ID document number
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for frequent lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON ecommerce.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON ecommerce.users(role);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION ecommerce.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON ecommerce.users
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

-- Constraint for valid subscription tier values
ALTER TABLE ecommerce.users ADD CONSTRAINT chk_subscription_tier
    CHECK (subscription_tier BETWEEN 0 AND 4);

-- -----------------------------------------------------------------------------
-- 2.1b Site Configuration Table (ecommerce.site_config)
-- -----------------------------------------------------------------------------
-- Stores JSON config blobs for dynamic site content: banners, plans, etc.
-- Each config is identified by a unique string key.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.site_config (
    key TEXT PRIMARY KEY,                               -- Config key, e.g. 'banners', 'subscription_plans'
    value JSONB NOT NULL DEFAULT '{}',                  -- JSON blob value
    updated_by UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2.2 OTP Verification Table (ecommerce.otps)
-- -----------------------------------------------------------------------------
-- Stores OTP codes for email verification. Expires after a short time.
-- Used in the registration flow (send‑otp, verify‑otp).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.otps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,                        -- Email address to verify
    otp_code VARCHAR(6) NOT NULL,                       -- 6‑digit numeric code
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,       -- Expiry timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_otps_email ON ecommerce.otps(email);
CREATE INDEX IF NOT EXISTS idx_otps_expires_at ON ecommerce.otps(expires_at); -- for cleanup

-- -----------------------------------------------------------------------------
-- 2.3 Products Table (ecommerce.products)
-- -----------------------------------------------------------------------------
-- Product catalogue. All media (images) are stored in Supabase Storage / S3;
-- only URLs are saved in the database.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.products (
    id SERIAL PRIMARY KEY,                              -- Auto‑increment (or UUID if preferred)
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,                     -- Selling price
    category VARCHAR(100),                             -- e.g., 'Electronics', 'Gifts'
    badge VARCHAR(50),                                 -- e.g., 'New', 'Sale'
    image_url TEXT,                                   -- Main image URL
    out_of_stock BOOLEAN DEFAULT FALSE,
    mrp NUMERIC(10, 2),                               -- Maximum Retail Price (for discount display)
    rating NUMERIC(3, 2),                             -- Average rating (0‑5)
    review_count INTEGER DEFAULT 0,
    images JSONB,                                     -- Array of additional image URLs
    features JSONB,                                   -- Key‑value list of features
    specs JSONB,                                      -- Detailed specifications
    reviews JSONB,                                    -- Denormalised reviews for quick display
    style_id VARCHAR(50),                             -- e.g., SKU style identifier
    hex VARCHAR(10),                                  -- Colour hex code (if applicable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category ON ecommerce.products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON ecommerce.products(price);
CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON ecommerce.products
    USING gin (name gin_trgm_ops);                    -- For full‑text search (requires pg_trgm)

-- -----------------------------------------------------------------------------
-- 2.4 Shopping Cart (ecommerce.carts & ecommerce.cart_items)
-- -----------------------------------------------------------------------------
-- Each user has exactly one active cart. Cart items reference the product
-- and store a snapshot of the price at the time of addition.
-- -----------------------------------------------------------------------------

-- Cart (one per user)
CREATE TABLE IF NOT EXISTS ecommerce.carts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES ecommerce.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_carts_updated_at
    BEFORE UPDATE ON ecommerce.carts
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

-- Cart items
CREATE TABLE IF NOT EXISTS ecommerce.cart_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cart_id UUID NOT NULL REFERENCES ecommerce.carts(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES ecommerce.products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL,                -- Price at the time of addition
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cart_items_cart_id ON ecommerce.cart_items(cart_id);
CREATE INDEX idx_cart_items_product_id ON ecommerce.cart_items(product_id);

-- -----------------------------------------------------------------------------
-- 2.5 Orders Table (ecommerce.orders)
-- -----------------------------------------------------------------------------
-- Contains order header information. Status mapping:
--   1 = Pending Payment
--   2 = Processing
--   3 = Shipped
--   4 = Delivered
--   5 = Cancelled
--   6 = Refunded (optional)
--   7 = On Hold (optional)
-- Payment screenshot and payment_intent_id are stored for reconciliation.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    delivery_type VARCHAR(100) NOT NULL,               -- e.g., 'standard', 'express'
    delivery_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(50),                       -- e.g., 'card', 'upi', 'cod'
    payment_intent_id VARCHAR(255),                   -- Stripe/PayPal intent ID
    payment_screenshot_url TEXT,                      -- Uploaded payment proof (optional)
    full_name VARCHAR(255) NOT NULL,
    street_address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    pin_code VARCHAR(20) NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_id ON ecommerce.orders(user_id);
CREATE INDEX idx_orders_status ON ecommerce.orders(status);

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON ecommerce.orders
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

ALTER TABLE ecommerce.orders ADD CONSTRAINT chk_order_status
    CHECK (status BETWEEN 1 AND 7);

-- -----------------------------------------------------------------------------
-- 2.6 Order Items Table (ecommerce.order_items)
-- -----------------------------------------------------------------------------
-- Line items for each order. Denormalises product name and price at order time.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES ecommerce.products(id) ON DELETE SET NULL,
    product_name VARCHAR(255) NOT NULL,                -- Snapshot of product name
    subtitle VARCHAR(255),                             -- Optional variant info
    price NUMERIC(10, 2) NOT NULL,                     -- Snapshot of unit price
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    uploaded_file_url TEXT                             -- If customer uploaded a file for customisation
);

CREATE INDEX idx_order_items_order_id ON ecommerce.order_items(order_id);

-- -----------------------------------------------------------------------------
-- 2.7 Chat Messages Table (ecommerce.chat_messages)
-- -----------------------------------------------------------------------------
-- Order‑specific communication between customer and staff.
-- sender_role: 1=admin,2=employee,3=shopkeeper,4=customer
-- read_at marks when a staff member has read a customer message.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    sender_user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    sender_role SMALLINT NOT NULL,                     -- Role of the sender
    text TEXT,                                         -- Message content (plain text)
    image_url TEXT,                                    -- Optional image attachment
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE                   -- Null until read by support
);

CREATE INDEX idx_chat_messages_order_id ON ecommerce.chat_messages(order_id);
CREATE INDEX idx_chat_messages_created_at ON ecommerce.chat_messages(created_at);

-- -----------------------------------------------------------------------------
-- 2.8 RFID Loyalty Cards (ecommerce.rfid_cards)
-- -----------------------------------------------------------------------------
-- Assigns a unique RFID UID to a user. One‑to‑one mapping (user ↔ card).
-- assigned_by tracks who performed the assignment (admin/employee/shopkeeper).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.rfid_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES ecommerce.users(id) ON DELETE RESTRICT,
    rfid_uid VARCHAR(255) UNIQUE NOT NULL,            -- Physical card UID
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL
);

CREATE INDEX idx_rfid_user_id ON ecommerce.rfid_cards(user_id);
CREATE INDEX idx_rfid_uid ON ecommerce.rfid_cards(rfid_uid);

-- -----------------------------------------------------------------------------
-- 2.9 Audit Logs (ecommerce.audit_logs)
-- -----------------------------------------------------------------------------
-- Records critical actions (user updates, product changes, order status changes, etc.)
-- for compliance and troubleshooting.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL, -- Who performed the action
    action VARCHAR(255) NOT NULL,                       -- e.g., 'ORDER_STATUS_CHANGE', 'PRODUCT_CREATE'
    details JSONB,                                     -- Additional context (old/new values, IP, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_id ON ecommerce.audit_logs(user_id);
CREATE INDEX idx_audit_created_at ON ecommerce.audit_logs(created_at);

-- =============================================================================
-- 3. MAINTENANCE DOMAIN TABLES (for internal staff)
-- =============================================================================
-- These tables are for tracking machinery and repairs; only accessible to admin
-- and employee roles (via RLS).
-- -----------------------------------------------------------------------------
-- 3.1 Machinery (maintenance.machinery)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance.machinery (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    model_number VARCHAR(100),
    status SMALLINT NOT NULL DEFAULT 1,                -- 1=Operational,2=Requires Service,3=Down
    last_service_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_machinery_status ON maintenance.machinery(status);

-- 3.2 Repair Logs (maintenance.repair_logs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance.repair_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    machinery_id UUID REFERENCES maintenance.machinery(id) ON DELETE CASCADE,
    issue_description TEXT NOT NULL,
    action_taken TEXT,
    technician_name VARCHAR(255),
    cost NUMERIC(10, 2) DEFAULT 0.00,
    document_url TEXT,                                 -- URL to uploaded checklist / PDF
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_repair_logs_machinery ON maintenance.repair_logs(machinery_id);

-- =============================================================================
-- 4. ROW‑LEVEL SECURITY (RLS) – ZERO‑TRUST PRINCIPLE
-- =============================================================================
-- Enable RLS on all tables; policies enforce that users can only access data
-- they are authorised for. For simplicity, policies are defined for the
-- `ecommerce` schema; similar policies can be applied to `maintenance`.
-- -----------------------------------------------------------------------------
ALTER TABLE ecommerce.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.otps ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.cart_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.rfid_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance.machinery ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance.repair_logs ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 4.1 Policies for ecommerce.users
-- Users can see and update their own profile; admins can do everything.
-- -----------------------------------------------------------------------------
CREATE POLICY select_own_profile ON ecommerce.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY update_own_profile ON ecommerce.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY admin_manage_users ON ecommerce.users
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role = 1)
    );

-- 4.2 Policies for ecommerce.otps (allow insert and read for all)
CREATE POLICY insert_otps ON ecommerce.otps FOR INSERT WITH CHECK (true);
CREATE POLICY select_otps ON ecommerce.otps FOR SELECT USING (true);

-- 4.3 Policies for ecommerce.products (public read, admin write)
CREATE POLICY select_products ON ecommerce.products FOR SELECT USING (true);
CREATE POLICY admin_manage_products ON ecommerce.products
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role = 1)
    );

-- 4.4 Policies for ecommerce.carts (user can manage own cart)
CREATE POLICY select_own_cart ON ecommerce.carts
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY insert_own_cart ON ecommerce.carts
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY update_own_cart ON ecommerce.carts
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY delete_own_cart ON ecommerce.carts
    FOR DELETE USING (auth.uid() = user_id);

-- 4.5 Policies for ecommerce.cart_items (user can manage own cart items)
CREATE POLICY select_own_cart_items ON ecommerce.cart_items
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM ecommerce.carts WHERE carts.id = cart_items.cart_id AND carts.user_id = auth.uid())
    );
CREATE POLICY insert_own_cart_items ON ecommerce.cart_items
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM ecommerce.carts WHERE carts.id = cart_items.cart_id AND carts.user_id = auth.uid())
    );
CREATE POLICY update_own_cart_items ON ecommerce.cart_items
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM ecommerce.carts WHERE carts.id = cart_items.cart_id AND carts.user_id = auth.uid())
    );
CREATE POLICY delete_own_cart_items ON ecommerce.cart_items
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM ecommerce.carts WHERE carts.id = cart_items.cart_id AND carts.user_id = auth.uid())
    );

-- 4.6 Policies for ecommerce.orders (customer sees own, admin sees all)
CREATE POLICY select_own_orders ON ecommerce.orders
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY insert_own_orders ON ecommerce.orders
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY admin_manage_orders ON ecommerce.orders
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role = 1)
    );

-- 4.7 Policies for ecommerce.order_items (customer sees own order items)
CREATE POLICY select_own_order_items ON ecommerce.order_items
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM ecommerce.orders WHERE orders.id = order_items.order_id AND orders.user_id = auth.uid())
    );
CREATE POLICY admin_manage_order_items ON ecommerce.order_items
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role = 1)
    );

-- 4.8 Policies for ecommerce.chat_messages
-- Customer can see/send messages for their own orders;
-- Staff (admin,employee,shopkeeper) can see/send for any order.
CREATE POLICY select_chat_messages ON ecommerce.chat_messages
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM ecommerce.orders WHERE orders.id = chat_messages.order_id AND orders.user_id = auth.uid())
        OR
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role IN (1,2,3))
    );
CREATE POLICY insert_chat_messages ON ecommerce.chat_messages
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM ecommerce.orders WHERE orders.id = chat_messages.order_id AND orders.user_id = auth.uid())
        OR
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role IN (1,2,3))
    );

-- 4.9 Policies for ecommerce.rfid_cards (only staff can manage)
CREATE POLICY staff_manage_rfid ON ecommerce.rfid_cards
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role IN (1,2,3))
    );

-- 4.10 Policies for ecommerce.audit_logs (only admin can read)
CREATE POLICY admin_read_audit ON ecommerce.audit_logs
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role = 1)
    );
-- Insert is allowed by system (e.g., triggers) – we can allow insert from any authenticated user
-- but typically only backend code inserts; we can allow all authenticated to insert.
CREATE POLICY insert_audit ON ecommerce.audit_logs
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- 4.11 Policies for maintenance schema (only admin and employee)
CREATE POLICY staff_manage_machinery ON maintenance.machinery
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role IN (1,2))
    );
CREATE POLICY staff_manage_repair_logs ON maintenance.repair_logs
    FOR ALL USING (
        EXISTS (SELECT 1 FROM ecommerce.users WHERE id = auth.uid() AND role IN (1,2))
    );

-- =============================================================================
-- 5. ADDITIONAL UTILITY FUNCTIONS & TRIGGERS (optional)
-- =============================================================================
-- Example: function to automatically create a cart when a user is registered
CREATE OR REPLACE FUNCTION ecommerce.create_cart_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO ecommerce.carts (user_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_create_cart_after_user_insert
    AFTER INSERT ON ecommerce.users
    FOR EACH ROW
    EXECUTE FUNCTION ecommerce.create_cart_for_new_user();

-- Example: function to log order status changes
CREATE OR REPLACE FUNCTION ecommerce.log_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO ecommerce.audit_logs (user_id, action, details)
        VALUES (
            auth.uid(),  -- assumes the JWT user ID is available in a session variable
            'ORDER_STATUS_CHANGE',
            jsonb_build_object('order_id', NEW.id, 'old_status', OLD.status, 'new_status', NEW.status)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_status_audit
    AFTER UPDATE OF status ON ecommerce.orders
    FOR EACH ROW
    EXECUTE FUNCTION ecommerce.log_order_status_change();

-- =============================================================================
-- 6. RAZORPAY INTEGRATION TABLES
-- =============================================================================

-- Payments table
CREATE TABLE IF NOT EXISTS ecommerce.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    razorpay_order_id VARCHAR(255) NOT NULL,
    razorpay_payment_id VARCHAR(255),
    razorpay_signature VARCHAR(255),
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    payment_method VARCHAR(50),
    payment_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_order_id ON ecommerce.payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_razorpay_order_id ON ecommerce.payments(razorpay_order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON ecommerce.payments(status);

DROP TRIGGER IF EXISTS trg_payments_updated_at ON ecommerce.payments;
CREATE TRIGGER trg_payments_updated_at
    BEFORE UPDATE ON ecommerce.payments
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

-- Webhook events table
CREATE TABLE IF NOT EXISTS ecommerce.webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webhook_event_id ON ecommerce.webhook_events(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_processed ON ecommerce.webhook_events(processed);

-- Refunds table
CREATE TABLE IF NOT EXISTS ecommerce.refunds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id UUID NOT NULL REFERENCES ecommerce.payments(id) ON DELETE CASCADE,
    razorpay_refund_id VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2.12 RFID Cards Table (ecommerce.rfid_cards)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.rfid_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES ecommerce.users(id) ON DELETE RESTRICT,
    rfid_uid VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deactivated_at TIMESTAMP WITH TIME ZONE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_rfid_cards_user_id ON ecommerce.rfid_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_rfid_cards_rfid_uid ON ecommerce.rfid_cards(rfid_uid);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rfid_cards_active_uid ON ecommerce.rfid_cards(rfid_uid) WHERE (is_active = TRUE);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rfid_cards_active_user ON ecommerce.rfid_cards(user_id) WHERE (is_active = TRUE);

-- -----------------------------------------------------------------------------
-- 2.13 RFID Scan Logs Table (ecommerce.rfid_scan_logs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecommerce.rfid_scan_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfid_uid VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    scan_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    scanner_id VARCHAR(100) DEFAULT 'admin_console'
);

CREATE INDEX IF NOT EXISTS idx_rfid_scan_logs_uid ON ecommerce.rfid_scan_logs(rfid_uid);
CREATE INDEX IF NOT EXISTS idx_rfid_scan_logs_user_id ON ecommerce.rfid_scan_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_rfid_scan_logs_time ON ecommerce.rfid_scan_logs(scan_time);