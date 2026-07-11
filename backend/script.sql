-- =============================================================================
-- script.sql — Sample Subscriber Seed Data for "Manage Subscribers" Tab
-- =============================================================================
-- This script inserts sample subscriber customers (role=4) with varied
-- subscription tiers and expiry states so the shopkeeper UI row colours can
-- be tested:
--   Pale green  → active (expires_at > NOW())
--   Pale yellow → expiring soon (expires_at BETWEEN NOW() AND NOW() + 15 days)
--   Red         → expired (expires_at <= NOW() or NULL with tier > 0)
-- =============================================================================
-- Passwords are bcrypt hash of "Welcome123"
-- $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW
-- =============================================================================

BEGIN;

-- Active Gold subscriber (valid ~90 days from now)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Ravi Kumar',
    'ravi.kumar@example.com',
    '+91 98765 43210',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 200,
    3, NOW() + INTERVAL '87 days',
    'No. 12, MG Road, Bengaluru, KA 560001',
    NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;

-- Active Premium subscriber (valid ~365 days from now)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Priya Patel',
    'priya.patel@example.com',
    '+91 95551 23456',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 500,
    4, NOW() + INTERVAL '340 days',
    'Flat 4B, Andheri West, Mumbai, MH 400058',
    NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;

-- Active Silver subscriber (valid ~30 days from now)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Arjun Mehta',
    'arjun.mehta@example.com',
    '+91 91234 56789',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 80,
    2, NOW() + INTERVAL '22 days',
    '77, Park Street, Kolkata, WB 700016',
    NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;

-- EXPIRING SOON — Student subscriber (expires in 10 days → pale yellow)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Sneha Nair',
    'sneha.nair@example.com',
    '+91 88887 76655',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 30,
    1, NOW() + INTERVAL '10 days',
    'Hostel Block C, NIT Calicut, KL 673601',
    NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;

-- EXPIRING SOON — Gold subscriber (expires in 7 days → pale yellow)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Karan Singh',
    'karan.singh@example.com',
    '+91 77776 54321',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 150,
    3, NOW() + INTERVAL '7 days',
    'C-21, Sector 18, Noida, UP 201301',
    NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;

-- EXPIRED — Silver subscriber (expired 15 days ago → red)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Divya Reddy',
    'divya.reddy@example.com',
    '+91 99887 11223',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 60,
    2, NOW() - INTERVAL '15 days',
    '8-2-293, Road No. 82, Banjara Hills, Hyderabad, TS 500034',
    NOW() - INTERVAL '45 days', NOW()
) ON CONFLICT (email) DO NOTHING;

-- EXPIRED — Premium subscriber (expired 2 days ago → red)
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Amit Verma',
    'amit.verma@example.com',
    '+91 70001 23456',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 420,
    4, NOW() - INTERVAL '2 days',
    'A-4, Defence Colony, New Delhi, DL 110024',
    NOW() - INTERVAL '367 days', NOW()
) ON CONFLICT (email) DO NOTHING;

-- NO PLAN — Registered user with no subscription
INSERT INTO ecommerce.users (
    id, name, email, phone, password_hash,
    email_verified, role, points,
    subscription_tier, subscription_expires_at,
    address, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'Meena Krishnan',
    'meena.krishnan@example.com',
    '+91 80001 99887',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE, 4, 0,
    0, NULL,
    'No 3, Anna Salai, Chennai, TN 600002',
    NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;
-- Link sample RFID cards to seeded subscribers
INSERT INTO ecommerce.rfid_cards (id, user_id, rfid_uid, is_active, assigned_by)
SELECT gen_random_uuid(), id, '12AB34CD', TRUE, 'c0000000-0000-0000-0000-000000000003'::uuid
FROM ecommerce.users WHERE email = 'ravi.kumar@example.com'
ON CONFLICT DO NOTHING;

INSERT INTO ecommerce.rfid_cards (id, user_id, rfid_uid, is_active, assigned_by)
SELECT gen_random_uuid(), id, '56EF78GH', TRUE, 'c0000000-0000-0000-0000-000000000003'::uuid
FROM ecommerce.users WHERE email = 'priya.patel@example.com'
ON CONFLICT DO NOTHING;

INSERT INTO ecommerce.rfid_cards (id, user_id, rfid_uid, is_active, assigned_by)
SELECT gen_random_uuid(), id, '90IJ12KL', TRUE, 'c0000000-0000-0000-0000-000000000003'::uuid
FROM ecommerce.users WHERE email = 'arjun.mehta@example.com'
ON CONFLICT DO NOTHING;

INSERT INTO ecommerce.rfid_cards (id, user_id, rfid_uid, is_active, assigned_by)
SELECT gen_random_uuid(), id, '34MN56OP', TRUE, 'c0000000-0000-0000-0000-000000000003'::uuid
FROM ecommerce.users WHERE email = 'sneha.nair@example.com'
ON CONFLICT DO NOTHING;

INSERT INTO ecommerce.rfid_cards (id, user_id, rfid_uid, is_active, assigned_by)
SELECT gen_random_uuid(), id, '78QR90ST', TRUE, 'c0000000-0000-0000-0000-000000000003'::uuid
FROM ecommerce.users WHERE email = 'amit.verma@example.com'
ON CONFLICT DO NOTHING;

COMMIT;

-- =============================================================================
-- Row Colour Logic (computed in frontend, not DB):
--   subscription_tier = 0 OR expires_at IS NULL → no plan (grey, filtered out
--     unless "Show All" is toggled)
--   expires_at > NOW() + 15 days   → active    → pale green (#f0fdf4)
--   expires_at BETWEEN NOW() AND NOW()+15 days → expiring → pale yellow (#fefce8)
--   expires_at <= NOW()            → expired   → pale red  (#fff5f5)
-- =============================================================================
