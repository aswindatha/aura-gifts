-- Migration: Add CHECK constraints, RFID table, audit logs, OTP cleanup

-- 1. Add CHECK constraint for orders.status (1-7)
ALTER TABLE ecommerce.orders
    ADD CONSTRAINT chk_orders_status CHECK (status BETWEEN 1 AND 7);

-- 2. Add CHECK constraint for users.subscription_tier (0-4)
ALTER TABLE ecommerce.users
    ADD CONSTRAINT chk_users_subscription_tier CHECK (subscription_tier BETWEEN 0 AND 4);

-- 3. RFID table (one-to-one with users)
CREATE TABLE IF NOT EXISTS ecommerce.rfid_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES ecommerce.users(id) ON DELETE RESTRICT,
    rfid_uid VARCHAR(255) UNIQUE NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES ecommerce.users(id)
);

-- 4. Audit logs table
CREATE TABLE IF NOT EXISTS ecommerce.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(100) NOT NULL,
    performed_by UUID NOT NULL REFERENCES ecommerce.users(id),
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- 5. OTP cleanup: Delete expired OTP records older than 1 day (can be run as scheduled job)
CREATE OR REPLACE FUNCTION ecommerce.cleanup_expired_otps() RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM ecommerce.otps WHERE expires_at < NOW() - INTERVAL '1 day';
END;
$$;

-- Schedule this function via pg_cron or your application scheduler.
