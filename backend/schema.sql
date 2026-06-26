-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create Isolated Schemas (Rule 3.1)
CREATE SCHEMA IF NOT EXISTS ecommerce;
CREATE SCHEMA IF NOT EXISTS maintenance;

-- 3. Ecommerce Domain Tables
-- Users Table (Rule 1.2)
-- Role mapping: 1=admin, 2=employee, 3=shopkeeper, 4=user (customer)
-- Subscription Tier mapping: 0=None, 1=Student, 2=Premium, 3=Enterprise
CREATE TABLE IF NOT EXISTS ecommerce.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    role SMALLINT NOT NULL DEFAULT 4,
    points INTEGER NOT NULL DEFAULT 0,
    subscription_tier SMALLINT NOT NULL DEFAULT 0,
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- B-Tree Indexes on frequently filtered/joined fields (Rule 2.1)
CREATE INDEX IF NOT EXISTS idx_users_email ON ecommerce.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON ecommerce.users(role);

-- OTP Verification Table
CREATE TABLE IF NOT EXISTS ecommerce.otps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_otps_email ON ecommerce.otps(email);

-- Products Table
CREATE TABLE IF NOT EXISTS ecommerce.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    category VARCHAR(100),
    badge VARCHAR(50),
    image_url TEXT, -- Store media URLs instead of binaries (Rule 1.1)
    out_of_stock BOOLEAN DEFAULT FALSE,
    mrp NUMERIC(10, 2),
    rating NUMERIC(3, 2),
    review_count INTEGER DEFAULT 0,
    images JSONB,
    features JSONB,
    specs JSONB,
    reviews JSONB,
    style_id VARCHAR(50),
    hex VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category ON ecommerce.products(category);

-- Orders Table
-- Status mapping: 1=Pending, 2=Processing, 3=Shipped, 4=Delivered, 5=Cancelled
CREATE TABLE IF NOT EXISTS ecommerce.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    delivery_type VARCHAR(100) NOT NULL,
    delivery_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    payment_screenshot_url TEXT, -- Store public media URL (Rule 1.1)
    full_name VARCHAR(255) NOT NULL,
    street_address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    pin_code VARCHAR(20) NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON ecommerce.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON ecommerce.orders(status);

-- Order Items Table
CREATE TABLE IF NOT EXISTS ecommerce.order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255),
    price NUMERIC(10, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    uploaded_file_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON ecommerce.order_items(order_id);

-- Chat Messages Table
CREATE TABLE IF NOT EXISTS ecommerce.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    sender_user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    sender_role SMALLINT NOT NULL,
    text TEXT,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_order_id ON ecommerce.chat_messages(order_id);


-- 4. Maintenance Domain Tables
-- Machinery Table
CREATE TABLE IF NOT EXISTS maintenance.machinery (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    model_number VARCHAR(100),
    status SMALLINT NOT NULL DEFAULT 1, -- 1=Operational, 2=Requires Service, 3=Down
    last_service_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_machinery_status ON maintenance.machinery(status);

-- Repair Logs Table
CREATE TABLE IF NOT EXISTS maintenance.repair_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    machinery_id UUID REFERENCES maintenance.machinery(id) ON DELETE CASCADE,
    issue_description TEXT NOT NULL,
    action_taken TEXT,
    technician_name VARCHAR(255),
    cost NUMERIC(10, 2) DEFAULT 0.00,
    document_url TEXT, -- Checklist/details file URL stored in Supabase Storage (Rule 1.3)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_repair_logs_machinery ON maintenance.repair_logs(machinery_id);


/*
-- 5. Enable Row Level Security (RLS) on all tables (Rule 4.2)
ALTER TABLE ecommerce.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.otps ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE ecommerce.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance.machinery ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance.repair_logs ENABLE ROW LEVEL SECURITY;


-- 6. Define Zero-Trust RLS Policies (Rule 4.2)
-- Users Policies: Users can read/update their own profile
CREATE POLICY select_own_profile ON ecommerce.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY update_own_profile ON ecommerce.users
    FOR UPDATE USING (auth.uid() = id);

-- Admin Policy for Users: Admin can manage all users
CREATE POLICY admin_manage_users ON ecommerce.users
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM ecommerce.users 
            WHERE id = auth.uid() AND role = 1
        )
    );

-- OTP Table Policy: Internal usage or basic insert
CREATE POLICY insert_otps ON ecommerce.otps FOR INSERT WITH CHECK (true);
CREATE POLICY select_otps ON ecommerce.otps FOR SELECT USING (true);

-- Products Policies: Public read-only, Admin write
CREATE POLICY select_all_products ON ecommerce.products
    FOR SELECT USING (true);

CREATE POLICY admin_manage_products ON ecommerce.products
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM ecommerce.users 
            WHERE id = auth.uid() AND role = 1
        )
    );

-- Orders Policies: Customer read/insert their own, admin read all
CREATE POLICY select_own_orders ON ecommerce.orders
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY insert_own_orders ON ecommerce.orders
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY admin_manage_orders ON ecommerce.orders
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM ecommerce.users 
            WHERE id = auth.uid() AND role = 1
        )
    );

-- Order Items Policies
CREATE POLICY select_own_order_items ON ecommerce.order_items
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM ecommerce.orders
            WHERE orders.id = order_items.order_id AND orders.user_id = auth.uid()
        )
    );

CREATE POLICY insert_own_order_items ON ecommerce.order_items
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM ecommerce.orders
            WHERE orders.id = order_items.order_id AND orders.user_id = auth.uid()
        )
    );

CREATE POLICY admin_manage_order_items ON ecommerce.order_items
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM ecommerce.users 
            WHERE id = auth.uid() AND role = 1
        )
    );

-- Chat Messages Policies
CREATE POLICY select_own_chat_messages ON ecommerce.chat_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM ecommerce.orders
            WHERE orders.id = chat_messages.order_id AND orders.user_id = auth.uid()
        ) OR EXISTS (
            SELECT 1 FROM ecommerce.users
            WHERE id = auth.uid() AND (role = 1 OR role = 2 OR role = 3)
        )
    );

CREATE POLICY insert_own_chat_messages ON ecommerce.chat_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM ecommerce.orders
            WHERE orders.id = chat_messages.order_id AND orders.user_id = auth.uid()
        ) OR EXISTS (
            SELECT 1 FROM ecommerce.users
            WHERE id = auth.uid() AND (role = 1 OR role = 2 OR role = 3)
        )
    );

-- Maintenance Domain Policies: Hides maintenance details from standard customers
-- Only admin (role=1) and staff (role=2) can access maintenance details
CREATE POLICY staff_manage_machinery ON maintenance.machinery
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM ecommerce.users 
            WHERE id = auth.uid() AND (role = 1 OR role = 2)
        )
    );

CREATE POLICY staff_manage_repair_logs ON maintenance.repair_logs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM ecommerce.users 
            WHERE id = auth.uid() AND (role = 1 OR role = 2)
        )
    );
*/


-- Add CHECK constraints for order status and subscription tier
ALTER TABLE ecommerce.orders ADD CONSTRAINT chk_order_status CHECK (status BETWEEN 1 AND 7);
ALTER TABLE ecommerce.users ADD CONSTRAINT chk_subscription_tier CHECK (subscription_tier BETWEEN 0 AND 4);

-- RFID cards table with one-to-one mapping and tracking
CREATE TABLE IF NOT EXISTS ecommerce.rfid_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL,
    rfid_uid VARCHAR(255) UNIQUE NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES ecommerce.users(id) ON DELETE RESTRICT
);

-- Audit logs for critical admin actions
CREATE TABLE IF NOT EXISTS ecommerce.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    action VARCHAR(255) NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_rfid_user_id ON ecommerce.rfid_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_rfid_uid ON ecommerce.rfid_cards(rfid_uid);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON ecommerce.audit_logs(user_id);
