-- Migration: Create chat_messages table for order chat feature
-- This migration is compatible with Supabase free tier (PostgreSQL)
CREATE SCHEMA IF NOT EXISTS ecommerce;

CREATE TABLE IF NOT EXISTS ecommerce.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    sender_user_id UUID NOT NULL REFERENCES ecommerce.users(id) ON DELETE SET NULL,
    sender_role SMALLINT NOT NULL, -- 1=admin,2=employee,3=shopkeeper,4=customer
    text TEXT,
    image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at TIMESTAMPTZ NULL
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_chat_order ON ecommerce.chat_messages(order_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON ecommerce.chat_messages(created_at);

-- Optional: partial unique index to prevent duplicate timestamps per order (not needed)
