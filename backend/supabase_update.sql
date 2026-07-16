-- ============================================================================
-- AURA Prints & Gifts — Targeted Supabase Update (MISSING TABLES ONLY)
-- Generated: 2026-07-16 09:55:50
-- ============================================================================

-- This script ONLY adds what's missing in Supabase:
--   1. ALTER TABLE products: ADD COLUMN sku
--   2. CREATE TABLE: offers, offer_qualifying_products, offer_redemptions, customer_info
--   3. INSERT data for the new tables only
--   4. UPDATE products with SKU values
--   5. CREATE indexes for new tables

-- Existing tables (users, orders, products, etc.) are NOT recreated or truncated.

-- ============================================================================
-- SECTION 1: ADD MISSING COLUMNS
-- ============================================================================

-- Add sku column to products (if not already present)
ALTER TABLE "ecommerce"."products" ADD COLUMN IF NOT EXISTS "sku" VARCHAR(100);
-- Add unique constraint on sku (if not already present)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'products_sku_key' AND conrelid = '"ecommerce"."products"'::regclass) THEN
    ALTER TABLE "ecommerce"."products" ADD CONSTRAINT "products_sku_key" UNIQUE ("sku");
  END IF;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- ============================================================================
-- SECTION 2: CREATE MISSING TABLES
-- ============================================================================

-- Table: ecommerce.customer_info
CREATE TABLE IF NOT EXISTS "ecommerce"."customer_info" (
  "id" UUID NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "phone" VARCHAR(50) NOT NULL,
  "email" VARCHAR(255),
  "address" TEXT,
  "is_sub_user" BOOLEAN NOT NULL,
  "created_at" TIMESTAMPTZ,
  "updated_at" TIMESTAMPTZ,
  PRIMARY KEY ("id")
);

CREATE INDEX ix_ecommerce_customer_info_email ON ecommerce.customer_info USING btree (email);
CREATE INDEX ix_ecommerce_customer_info_phone ON ecommerce.customer_info USING btree (phone);

-- Table: ecommerce.offers
CREATE TABLE IF NOT EXISTS "ecommerce"."offers" (
  "offer_id" UUID NOT NULL,
  "offer_name" VARCHAR(100) NOT NULL,
  "criteria_type" VARCHAR(20) NOT NULL,
  "product_scope" VARCHAR(20) NOT NULL,
  "product_id" INTEGER,
  "required_count" INTEGER,
  "required_value" NUMERIC(10,2),
  "reward_type" VARCHAR(20) NOT NULL,
  "free_product_id" INTEGER,
  "free_product_qty" INTEGER,
  "discount_percentage" NUMERIC(5,2),
  "start_datetime" TIMESTAMPTZ NOT NULL,
  "end_datetime" TIMESTAMPTZ NOT NULL,
  "status" VARCHAR(10) NOT NULL,
  "created_at" TIMESTAMPTZ,
  "updated_at" TIMESTAMPTZ,
  "promotion_group" VARCHAR(100),
  PRIMARY KEY ("offer_id")
);

CREATE INDEX idx_offers_promo_group ON ecommerce.offers USING btree (promotion_group) WHERE (promotion_group IS NOT NULL);

-- Table: ecommerce.offer_qualifying_products
CREATE TABLE IF NOT EXISTS "ecommerce"."offer_qualifying_products" (
  "id" UUID NOT NULL,
  "offer_id" UUID NOT NULL,
  "product_id" INTEGER NOT NULL,
  PRIMARY KEY ("id"),
  CONSTRAINT "offer_qualifying_products_offer_id_fkey" FOREIGN KEY ("offer_id") REFERENCES "ecommerce"."offers" ("offer_id") ON DELETE CASCADE
);

CREATE INDEX ix_ecommerce_offer_qualifying_products_offer_id ON ecommerce.offer_qualifying_products USING btree (offer_id);

-- Table: ecommerce.offer_redemptions
CREATE TABLE IF NOT EXISTS "ecommerce"."offer_redemptions" (
  "redemption_id" UUID NOT NULL,
  "offer_id" UUID NOT NULL,
  "customer_id" UUID,
  "order_id" UUID,
  "redeemed_at" TIMESTAMPTZ,
  "benefit_applied" JSON,
  PRIMARY KEY ("redemption_id"),
  CONSTRAINT "offer_redemptions_offer_id_fkey" FOREIGN KEY ("offer_id") REFERENCES "ecommerce"."offers" ("offer_id") ON DELETE CASCADE,
  CONSTRAINT "offer_redemptions_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "ecommerce"."customer_info" ("id") ON DELETE SET NULL,
  CONSTRAINT "offer_redemptions_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "ecommerce"."orders" ("id") ON DELETE SET NULL
);

CREATE INDEX ix_ecommerce_offer_redemptions_offer_id ON ecommerce.offer_redemptions USING btree (offer_id);

-- ============================================================================
-- SECTION 3: INSERT DATA FOR NEW TABLES
-- ============================================================================

-- ────────────────────────────────────────────────────────────
-- Data for table: ecommerce.customer_info
-- ────────────────────────────────────────────────────────────
-- 10 row(s) in ecommerce.customer_info
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('a62223ca-1a8e-438b-b5e9-9579abae2577', 'Jane Doe', '9876543210', 'customer@auraprints.com', '123 Artisan Way, Apt 4B, Mumbai, MH - 400001', TRUE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('9963f085-52fa-4ff2-ad0d-88c0b835ed54', 'Alex Patel', '9123456789', 'student@auraprints.com', 'Hostel 4, IIT Bombay, Powai, Mumbai - 400076', FALSE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('0a523bd7-9616-41ac-8b4a-dec4b96787fb', 'Rajesh Sharma', '9812345678', NULL, NULL, FALSE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('b2286bc2-8eb8-489c-b026-4c9803b01c99', 'Priya Patel', '95551234567', 'priya.patel@gmail.com', '45 Marine Drive, Mumbai - 400020', TRUE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('679b39a5-0b72-475e-a430-d4b0773a0afa', 'Amit Verma', '9988776655', NULL, NULL, FALSE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('5fb533e7-1119-44f7-9ef0-e19e5c2aa07d', 'Sneha Reddy', '9001122334', 'sneha.reddy@outlook.com', '12 Jubilee Hills, Hyderabad - 500033', FALSE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('82525d32-7086-40d3-8dce-beb5e7061a28', 'Karthik Iyer', '9445566778', NULL, NULL, TRUE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('f0ec3769-332a-4907-9c20-13e3eb4a9580', 'Neha Gupta', '9708564412', 'neha.gupta@yahoo.com', '78 CG Road, Ahmedabad - 380009', FALSE, '2026-07-15T08:38:36.306092+05:30', '2026-07-15T08:38:36.306092+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('28e22796-859f-4dd4-9387-ecf079b83ac1', 'deepak', '9940077848', NULL, NULL, FALSE, '2026-07-15T08:51:21.425320+05:30', '2026-07-15T08:51:21.425320+05:30') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."customer_info" ("id", "name", "phone", "email", "address", "is_sub_user", "created_at", "updated_at") VALUES ('9657e8df-88cb-41ad-83d0-e333c5848ed3', 'mehull', '1122334455', NULL, NULL, FALSE, '2026-07-15T08:51:55.775407+05:30', '2026-07-15T08:51:55.775407+05:30') ON CONFLICT DO NOTHING;

-- ────────────────────────────────────────────────────────────
-- Data for table: ecommerce.offers
-- ────────────────────────────────────────────────────────────
-- 29 row(s) in ecommerce.offers
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('7a30340a-4ca9-4703-930d-cc08be51d109', 'Poster Combo — Buy 5 Get 1 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 5, NULL, 'FREE_PRODUCT', 38, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POSTER_COMBO') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('aaefd39f-be96-4129-a7e3-c55dcfe485ad', 'Poster Combo — Buy 10 Get 2 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 10, NULL, 'FREE_PRODUCT', 38, 2, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POSTER_COMBO') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('dbd5ab4a-c282-4571-9edd-2c6d280536fb', 'Poster Combo — Buy 18 Get 4 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 18, NULL, 'FREE_PRODUCT', 38, 4, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POSTER_COMBO') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('d04dc93b-c21a-4497-8665-7e93ab72875c', 'Metal Magnet Pre-Designed — Buy 7 Get 2 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 7, NULL, 'FREE_PRODUCT', 16, 2, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'METAL_MAGNET_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('bbda832c-3ac2-48a3-b3e8-1ac2807e948f', 'Metal Magnet Pre-Designed — Buy 12 Get 3 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 12, NULL, 'FREE_PRODUCT', 16, 3, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'METAL_MAGNET_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('14759b4d-e541-4625-a99d-9ef91b9a98cd', 'Metal Magnet Pre-Designed — Buy 15 Get 4 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 15, NULL, 'FREE_PRODUCT', 16, 4, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'METAL_MAGNET_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('1f620da7-405d-49bb-855b-1e7a56e9463e', 'Metal Magnet Customized — Buy 5 Get 1 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 5, NULL, 'FREE_PRODUCT', 16, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'METAL_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('47157e5b-53ed-4182-8f98-77633b562fad', 'Metal Magnet Customized — Buy 10 Get 3 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 10, NULL, 'FREE_PRODUCT', 16, 3, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'METAL_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('dcde6c87-178f-451f-843c-0d498c40faf0', 'Metal Magnet Customized — Buy 12 Get 4 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 12, NULL, 'FREE_PRODUCT', 16, 4, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'METAL_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('e40c1b17-4ca1-4bc6-b937-d774c1836340', 'Acrylic Magnet Customized — Buy 3 Get 1 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 3, NULL, 'FREE_PRODUCT', 20, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'ACRYLIC_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('d58a1602-0253-4c8c-8cee-8fd885d53897', 'Acrylic Magnet Customized — Buy 6 Get 2 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 6, NULL, 'FREE_PRODUCT', 20, 2, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'ACRYLIC_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('4c71fc5a-713b-4cce-ba03-d8f172c927fc', 'Acrylic Magnet Customized — Buy 10 Get 3 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 10, NULL, 'FREE_PRODUCT', 20, 3, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'ACRYLIC_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('7245191d-0deb-475e-951d-bcd8e705f875', 'Acrylic Magnet Customized — Buy 15 Get 4 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 15, NULL, 'FREE_PRODUCT', 20, 4, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'ACRYLIC_MAGNET_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('c817eebd-725a-4fa1-9dda-3013ee4a63ff', 'Poster Combo — Buy 23 Get 5 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 23, NULL, 'FREE_PRODUCT', 38, 5, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POSTER_COMBO') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('69498e2e-05d7-4c5d-953f-9abb7b36eeff', 'Poster Combo — Buy 30 Get 7 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 30, NULL, 'FREE_PRODUCT', 38, 7, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POSTER_COMBO') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('324bb927-21e0-4fc1-8666-3af4fd48d6ae', 'Polaroid Pre-Designed — Buy 10 Get 3 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 10, NULL, 'FREE_PRODUCT', 53, 3, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('8dbb0ffb-3223-4cb8-920f-db998325fc10', 'Polaroid Pre-Designed — Buy 16 Get 5 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 16, NULL, 'FREE_PRODUCT', 53, 5, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('48180cd4-294c-4e42-8170-bfb5a7ed7c99', 'Polaroid Pre-Designed — Buy 22 Get 7 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 22, NULL, 'FREE_PRODUCT', 53, 7, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 'Polaroid Pre-Designed — Buy 33 Get 12 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 33, NULL, 'FREE_PRODUCT', 53, 12, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('041cc0f4-0ce7-4884-856b-6f5649653b72', 'Polaroid Pre-Designed — Buy 40 Get 15 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 40, NULL, 'FREE_PRODUCT', 53, 15, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_PREDESIGNED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('24cba658-fc34-4aa7-94c5-4cb399b4d87f', 'Polaroid Customized — Buy 10 Get 2 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 10, NULL, 'FREE_PRODUCT', 53, 2, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('05714570-6233-466e-93b4-d4f701eb1c5c', 'Polaroid Customized — Buy 16 Get 4 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 16, NULL, 'FREE_PRODUCT', 53, 4, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('a708ab62-46b7-4079-8d85-9ac468a483af', 'Polaroid Customized — Buy 22 Get 7 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 22, NULL, 'FREE_PRODUCT', 53, 7, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('3b4c929e-1397-495a-a989-a03d84d9ca83', 'Polaroid Customized — Buy 33 Get 10 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 33, NULL, 'FREE_PRODUCT', 53, 10, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('cfb64206-9d67-4b81-8d9b-4021f85ac440', 'Polaroid Customized — Buy 40 Get 12 Free', 'PURCHASE_COUNT', 'MULTIPLE_PRODUCT', NULL, 40, NULL, 'FREE_PRODUCT', 53, 12, NULL, '2026-07-16T00:00:00+05:30', '2026-07-19T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'POLAROID_CUSTOMIZED') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('a1676dd7-1411-4fd2-b7aa-7556d2b55fbd', 'Grand Opening — Spend ₹1299 Get 4x4 Mini Frame Free', 'PURCHASE_VALUE', 'ALL_PRODUCTS', NULL, NULL, 1299.00, 'FREE_PRODUCT', 118, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-31T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'GRAND_OPENING') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('097bd225-3e5c-4199-8f17-006046d01b66', 'Grand Opening — Spend ₹1999 Get 7x5 Frame Free', 'PURCHASE_VALUE', 'ALL_PRODUCTS', NULL, NULL, 1999.00, 'FREE_PRODUCT', 105, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-31T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'GRAND_OPENING') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('986d35be-b0cf-454b-acf2-b4ef25e219fd', 'Grand Opening — Spend ₹2399 Get 8x6 Frame Free', 'PURCHASE_VALUE', 'ALL_PRODUCTS', NULL, NULL, 2399.00, 'FREE_PRODUCT', 105, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-31T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'GRAND_OPENING') ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offers" ("offer_id", "offer_name", "criteria_type", "product_scope", "product_id", "required_count", "required_value", "reward_type", "free_product_id", "free_product_qty", "discount_percentage", "start_datetime", "end_datetime", "status", "created_at", "updated_at", "promotion_group") VALUES ('31e31907-fc1b-4365-ad97-8b00feee21a9', 'Grand Opening — Spend ₹3499 Get 12x8 Frame Free', 'PURCHASE_VALUE', 'ALL_PRODUCTS', NULL, NULL, 3499.00, 'FREE_PRODUCT', 105, 1, NULL, '2026-07-16T00:00:00+05:30', '2026-07-31T23:59:59+05:30', 'ACTIVE', '2026-07-16T07:44:23.932637+05:30', '2026-07-16T07:44:23.932637+05:30', 'GRAND_OPENING') ON CONFLICT DO NOTHING;

-- ────────────────────────────────────────────────────────────
-- Data for table: ecommerce.offer_qualifying_products
-- ────────────────────────────────────────────────────────────
-- 172 row(s) in ecommerce.offer_qualifying_products
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('59903540-8a1f-4482-aee1-8975da2642bd', 'd04dc93b-c21a-4497-8665-7e93ab72875c', 16) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('159d86c0-8895-48df-8679-faa5a067bc30', 'd04dc93b-c21a-4497-8665-7e93ab72875c', 17) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('888cb781-7710-4b6e-940a-535f08e514e3', 'd04dc93b-c21a-4497-8665-7e93ab72875c', 18) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('16a81053-21c2-4473-a986-25a0668069ac', 'd04dc93b-c21a-4497-8665-7e93ab72875c', 19) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3b0e77ce-cb51-4d60-bc9e-ebcb9ba7c791', 'bbda832c-3ac2-48a3-b3e8-1ac2807e948f', 16) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('c03e1f0f-2c8c-4d81-b8fe-03317c075074', 'bbda832c-3ac2-48a3-b3e8-1ac2807e948f', 17) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('1139def9-9ea0-4c9c-a375-8d94e8ccda85', 'bbda832c-3ac2-48a3-b3e8-1ac2807e948f', 18) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('27def654-c3c9-4e45-b4f6-7d0f5f812f7a', 'bbda832c-3ac2-48a3-b3e8-1ac2807e948f', 19) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('61b77936-4f94-4abc-ac1a-86786fcfa226', '14759b4d-e541-4625-a99d-9ef91b9a98cd', 16) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('12ba4104-3be7-4bf3-9a76-7d30732b33d6', '14759b4d-e541-4625-a99d-9ef91b9a98cd', 17) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('70101d1d-5b39-4f5b-afdc-3ab6037e8862', '14759b4d-e541-4625-a99d-9ef91b9a98cd', 18) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('35676839-7598-489b-917f-9d8472676652', '14759b4d-e541-4625-a99d-9ef91b9a98cd', 19) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('0318c420-a302-4fcd-8039-466d3d3842bf', '1f620da7-405d-49bb-855b-1e7a56e9463e', 16) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('66b957a1-a0e4-4498-a0bd-6581d1bfad56', '1f620da7-405d-49bb-855b-1e7a56e9463e', 17) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('fffd3263-52f1-471a-8bd7-560437a55731', '1f620da7-405d-49bb-855b-1e7a56e9463e', 18) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6c517b5e-be7c-4266-8e89-48267a9437c8', '1f620da7-405d-49bb-855b-1e7a56e9463e', 19) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6ac71408-8a60-4f1e-a81d-cd4f6d2ef4e8', '47157e5b-53ed-4182-8f98-77633b562fad', 16) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ce7a2841-3bda-4338-b1d2-36f27734d63a', '47157e5b-53ed-4182-8f98-77633b562fad', 17) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('1027977c-f10e-4da2-9bb4-cdf6d71a537a', '47157e5b-53ed-4182-8f98-77633b562fad', 18) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('42892209-e4f1-454a-a35c-62d87b7cff03', '47157e5b-53ed-4182-8f98-77633b562fad', 19) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('c63b7ea3-9347-42eb-81be-6b09a41b7ab2', 'dcde6c87-178f-451f-843c-0d498c40faf0', 16) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4b4592d6-cbb2-41fe-9345-4f8dec83d19f', 'dcde6c87-178f-451f-843c-0d498c40faf0', 17) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('73a6741b-0462-429d-802d-b41d59144d08', 'dcde6c87-178f-451f-843c-0d498c40faf0', 18) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('1c374c16-1250-46d1-b775-0d039479d921', 'dcde6c87-178f-451f-843c-0d498c40faf0', 19) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('42599e65-7dea-44d8-aa43-4423cfc85849', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 20) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('bf37aca3-4227-4577-bcaf-848d9259585e', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 22) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9d4e4983-ce08-47b1-bae7-e591572081a3', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 21) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('03089edc-903a-4331-85d6-791d82807843', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 25) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('a819ad69-19e8-47fa-81f5-2d89ead9c36a', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 24) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('92a40012-4622-40a3-b3b6-58abc88eaaf9', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 26) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('c67aa96a-9fb1-4322-9e11-aaed9d0813c8', 'e40c1b17-4ca1-4bc6-b937-d774c1836340', 23) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('bd5225ea-d710-47e1-8b3a-decf73561e6a', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 20) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9a96213c-1627-4d39-ad46-152eca51ecdb', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 22) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('44b1e06e-1a14-4b44-94ec-2645926b4a34', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 21) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('8ea51045-242f-48ac-aa19-decd7a8446d8', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 25) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3a2a300b-0214-436f-9e7f-11d896bfc799', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 24) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6be7aa5c-e158-48da-b48b-b32f1136478b', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 26) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('659a259d-5006-4ad8-be98-e849699a431b', 'd58a1602-0253-4c8c-8cee-8fd885d53897', 23) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('2dc934d0-747f-412d-8918-d48c060bfd02', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 20) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ada88f9f-defb-4967-a081-24d9917f429d', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 22) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('688c5c7d-a12c-4776-bdd0-551a65801303', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 21) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f8f40cf9-a177-4e2e-a7d9-9d89beb30c13', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 25) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('bb7c1287-3dd3-4c3b-a692-2486869512b9', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 24) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f31fd41a-4cac-45fc-92a4-9e8c48b73deb', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 26) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('dcfb2bdc-89b2-4e07-aa0c-ea3200a59ddd', '4c71fc5a-713b-4cce-ba03-d8f172c927fc', 23) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f0edca1b-92b7-4446-aa3e-a7b5e5fbbb32', '7245191d-0deb-475e-951d-bcd8e705f875', 20) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('94984aeb-b3c5-4868-b656-549b201fa3b6', '7245191d-0deb-475e-951d-bcd8e705f875', 22) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('89683e12-2b6e-4545-9b21-5b2f118d09d0', '7245191d-0deb-475e-951d-bcd8e705f875', 21) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('1f925256-e43a-4c4e-a1a4-58b404ce557e', '7245191d-0deb-475e-951d-bcd8e705f875', 25) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('5158c7cb-d13b-407d-8e5a-e1d1ec64400b', '7245191d-0deb-475e-951d-bcd8e705f875', 24) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b8ddfe89-cf30-4e12-ad25-c9e303e7b7f7', '7245191d-0deb-475e-951d-bcd8e705f875', 26) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3834f42a-d956-4891-b7ad-35afbc59743d', '7245191d-0deb-475e-951d-bcd8e705f875', 23) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('d1122ec9-2b28-4079-9bcd-57343a4e586e', '7a30340a-4ca9-4703-930d-cc08be51d109', 38) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('db6e5598-5242-4ff7-952d-9ebd3195ab9b', '7a30340a-4ca9-4703-930d-cc08be51d109', 39) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('655f7dcc-055f-4619-8975-09fda8a494bc', '7a30340a-4ca9-4703-930d-cc08be51d109', 37) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('45869b27-e77f-4b78-b7a4-68eb847f8624', '7a30340a-4ca9-4703-930d-cc08be51d109', 36) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4078e9ce-2c02-4762-b697-5bc4648fcbac', 'aaefd39f-be96-4129-a7e3-c55dcfe485ad', 38) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('718d36f1-e754-4982-9261-bbbd412adb31', 'aaefd39f-be96-4129-a7e3-c55dcfe485ad', 39) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f030d2b8-a19e-4f72-bb8a-3d39517f08c6', 'aaefd39f-be96-4129-a7e3-c55dcfe485ad', 37) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('562ebb54-bd0e-414c-939f-3d51c1757f99', 'aaefd39f-be96-4129-a7e3-c55dcfe485ad', 36) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('30928a3c-66fe-40cc-aa8b-dcf3804af2e5', 'dbd5ab4a-c282-4571-9edd-2c6d280536fb', 38) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4a111d3d-29b9-4078-8685-ce6facb588f3', 'dbd5ab4a-c282-4571-9edd-2c6d280536fb', 39) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9cb58985-e2dc-485f-8fbd-efe8cd4201af', 'dbd5ab4a-c282-4571-9edd-2c6d280536fb', 37) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('93f3d391-cb78-4284-9384-e3b4f2261f14', 'dbd5ab4a-c282-4571-9edd-2c6d280536fb', 36) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('0f0f8946-3cc4-475d-90ef-1c0f900d2aff', 'c817eebd-725a-4fa1-9dda-3013ee4a63ff', 38) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ebc79a4c-e2f1-453e-8d17-a1f7b03d74fb', 'c817eebd-725a-4fa1-9dda-3013ee4a63ff', 39) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('d56bb8fd-81a6-4298-8b57-a141ac597bdb', 'c817eebd-725a-4fa1-9dda-3013ee4a63ff', 37) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('bb13aff3-93c1-485b-a7c9-53e509df5295', 'c817eebd-725a-4fa1-9dda-3013ee4a63ff', 36) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('e3b88038-f040-46fc-8578-91a5ba565fe8', '69498e2e-05d7-4c5d-953f-9abb7b36eeff', 38) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('277848fd-0964-41a4-bc3d-d29454acbef4', '69498e2e-05d7-4c5d-953f-9abb7b36eeff', 39) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('2983431a-0e14-425c-844a-98481ef02310', '69498e2e-05d7-4c5d-953f-9abb7b36eeff', 37) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9ed8e27c-e17a-48d9-bede-902da258b736', '69498e2e-05d7-4c5d-953f-9abb7b36eeff', 36) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ed34263e-b1ef-4aca-b884-2facfc92e293', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b6b36188-4a90-46d7-bfa4-4a3288e91839', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('98861545-6456-4a67-9359-49b446cfd4f8', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4bb0dd49-3ab2-4a5a-a30a-0a4b7ebd0a7e', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('137ccaa1-31f4-4d11-ab0c-9a455c917629', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b1c2d11e-fe41-4e65-a704-f3656d500f06', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('7fd509ba-a24f-4ba5-ae84-5edaeb3da5e7', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ed08e9b9-e3e9-413d-ad7d-2a6a13400f69', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('a24066da-d4b8-4905-b162-7e4b85820b64', '324bb927-21e0-4fc1-8666-3af4fd48d6ae', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b344df9e-e8b2-4120-bff9-dca5d5209f03', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('35569a3f-8959-4877-af03-0027c88ef64e', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('841f244c-7199-4593-966b-86689fed489e', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('8b5dafba-a482-49f4-8ea9-645052ba6acb', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ffaee3d6-00a8-44a5-9df1-eb51858802f4', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('5601945d-db8e-4bb4-a330-aa6ebba2ac26', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('8dff38e8-c246-44e2-9e4c-fe7614f01594', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('a8b49fec-5b50-484f-8c3d-3d54ff02d4c3', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('cc7855d4-04a6-49c8-8b43-e2e155247d7e', '8dbb0ffb-3223-4cb8-920f-db998325fc10', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('0470e690-25bb-42d8-9a2f-86c73241e56d', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('0308b317-2044-454d-bb05-5405d560cf40', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('56f2cdb3-c66c-47ff-abc4-1aaa61d39f1c', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('d5c0ac5d-ba65-4c71-a55f-e2fab7d05d97', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('934847ea-de6b-4459-ae9e-44efede27937', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('fbe5c553-a613-4fab-a43c-411066e61663', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('99a0469f-f90f-4619-8e09-7a571711bae1', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('16b75ed4-bdf6-43b2-b4ef-5b186947b370', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9470c017-475a-4302-ab93-ee558f223450', '48180cd4-294c-4e42-8170-bfb5a7ed7c99', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3620c1db-faad-4cb5-91e0-3cc00873d0a7', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('8710b942-23f7-48a6-ac69-904ffe602a26', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('1be46040-ce10-438e-9c9d-45d95fab7c6a', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3b5393d5-724e-4fa1-96ae-54f6462cbf6d', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('05e4def4-a6b5-44dd-9cf8-4b93cfcca285', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f2bbd449-4001-47bb-b426-2bb3013a8b26', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('dd23ecea-1791-4a1d-9cd8-1a9a2b8aa11f', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6993aa5e-b76e-4bb8-af7f-98d5d3ad7a26', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f95fb14c-a958-4b9c-9fb3-16fabbc16030', 'fd44cab4-b6c5-4a2d-9e57-1bfb75a1bcb8', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3ac29fc7-57ce-4ab6-8ae0-181d825b3bac', '041cc0f4-0ce7-4884-856b-6f5649653b72', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('7f1b5ac5-95cf-433b-935d-922700d0d8e2', '041cc0f4-0ce7-4884-856b-6f5649653b72', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('51393c87-2983-4494-a3c0-c6d11e76fe22', '041cc0f4-0ce7-4884-856b-6f5649653b72', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('098a751c-86e6-4347-8c97-8c602ba03a7a', '041cc0f4-0ce7-4884-856b-6f5649653b72', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('c90c62b6-56f5-4cf2-ba28-b2dc1415c1c5', '041cc0f4-0ce7-4884-856b-6f5649653b72', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('c74c632a-b45c-4fa9-a5f9-3eab5214cd80', '041cc0f4-0ce7-4884-856b-6f5649653b72', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('59642d34-30c3-41fe-aee1-b4e13826704b', '041cc0f4-0ce7-4884-856b-6f5649653b72', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('e73baa19-5915-4620-988f-23b20c1d2cd6', '041cc0f4-0ce7-4884-856b-6f5649653b72', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b3659932-4503-499c-bdb3-dcb5c853cd8c', '041cc0f4-0ce7-4884-856b-6f5649653b72', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('5bdbf8a8-28fb-4e41-92c9-26be5ec41c37', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('fcabdfe3-c428-4a09-8395-111d5242a374', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('2e2bbcd2-7eee-4d3c-9921-ca39a55b6e15', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 59) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('cca5479a-3ea6-40f6-8859-4e0ea40af102', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f42a0833-1aa7-44c5-bd92-08026a900f43', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4026d02f-1bd5-4573-9f26-80c716268424', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('cf188857-cf5d-4c23-92ee-68de32556b9e', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9cff81e4-de98-4cd7-af84-6d7c784fabce', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 60) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('04773e1d-60a0-4821-81ef-7c7447027a53', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6efd006a-0daa-42af-8a16-c110f6b72bf7', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('aba571f9-34a5-46c1-a5a0-78997b83dff7', '24cba658-fc34-4aa7-94c5-4cb399b4d87f', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('7df7d4b0-b5ba-4982-a824-7c58133cb200', '05714570-6233-466e-93b4-d4f701eb1c5c', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('58f92bb7-8354-4bc9-b324-c01c30eb427a', '05714570-6233-466e-93b4-d4f701eb1c5c', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('7ba846c0-ff4f-4774-96da-11f101292625', '05714570-6233-466e-93b4-d4f701eb1c5c', 59) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('857ace3a-2482-4399-b2dc-00552c983649', '05714570-6233-466e-93b4-d4f701eb1c5c', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b7793fc8-7a0a-421f-be91-3eb63417bf57', '05714570-6233-466e-93b4-d4f701eb1c5c', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f3d34101-e42b-419f-9407-e2f5d9841db8', '05714570-6233-466e-93b4-d4f701eb1c5c', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('ba0506b3-ddb5-4d77-bdf4-42710131527e', '05714570-6233-466e-93b4-d4f701eb1c5c', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('9b9275c4-6953-4844-a554-fb8a2931266f', '05714570-6233-466e-93b4-d4f701eb1c5c', 60) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4a9851ac-af0b-4667-b01e-cb143d38ebb0', '05714570-6233-466e-93b4-d4f701eb1c5c', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3e6c801d-b09e-4e2a-aad6-6b70eda2d37c', '05714570-6233-466e-93b4-d4f701eb1c5c', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('d9559bdc-e5e8-4e6d-8206-d17a76b8071d', '05714570-6233-466e-93b4-d4f701eb1c5c', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('abbe4d80-1231-4b83-b263-638ac7ae9b26', 'a708ab62-46b7-4079-8d85-9ac468a483af', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('10b9fba4-a586-4b4d-8843-0048fc0e3f60', 'a708ab62-46b7-4079-8d85-9ac468a483af', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('871ff17b-46de-438d-96ad-4e366992efee', 'a708ab62-46b7-4079-8d85-9ac468a483af', 59) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('dbb90966-b572-4495-a42c-457fd2cc5c47', 'a708ab62-46b7-4079-8d85-9ac468a483af', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('83f947c2-a424-415d-b9a9-34e47d956273', 'a708ab62-46b7-4079-8d85-9ac468a483af', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('1e57291f-b917-449d-8ed2-6d040e9b43b0', 'a708ab62-46b7-4079-8d85-9ac468a483af', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('3a8e3cbc-14d2-44c7-8e9f-f046c2384c31', 'a708ab62-46b7-4079-8d85-9ac468a483af', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('92658c54-bbe8-4ebd-b75f-86f189714135', 'a708ab62-46b7-4079-8d85-9ac468a483af', 60) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('483b44ff-48a0-4cbf-99bf-5711c45e3a89', 'a708ab62-46b7-4079-8d85-9ac468a483af', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('35b21738-2e0c-444d-8176-857dfb533c4e', 'a708ab62-46b7-4079-8d85-9ac468a483af', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('c596e1af-6b8a-43b5-a3f2-0ea8fd2ec51a', 'a708ab62-46b7-4079-8d85-9ac468a483af', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('16a1ebe3-8bc3-4294-9235-030305c30f4f', '3b4c929e-1397-495a-a989-a03d84d9ca83', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('79c53ad1-dd0a-4294-a7c4-f2014c59ce21', '3b4c929e-1397-495a-a989-a03d84d9ca83', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('b818b2d8-31d7-4a32-8938-3ef90ae708da', '3b4c929e-1397-495a-a989-a03d84d9ca83', 59) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('22d009b1-e64b-42c4-9296-d4e8e299eaf0', '3b4c929e-1397-495a-a989-a03d84d9ca83', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('91746d68-68ef-4363-8ed3-ad22c13c9e79', '3b4c929e-1397-495a-a989-a03d84d9ca83', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f99101aa-3148-45be-b777-9d25b61eb37e', '3b4c929e-1397-495a-a989-a03d84d9ca83', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('74459300-9c7f-4aa0-8683-88bbbac38c38', '3b4c929e-1397-495a-a989-a03d84d9ca83', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('06f26b41-7073-4bbd-b77f-8728da89bf48', '3b4c929e-1397-495a-a989-a03d84d9ca83', 60) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6e0f60f2-20eb-4f4c-b932-dc2c4223ed22', '3b4c929e-1397-495a-a989-a03d84d9ca83', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('aaf39d5e-67d3-42d7-9c42-80f6a34dd5ec', '3b4c929e-1397-495a-a989-a03d84d9ca83', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('4a0767b6-d0a8-414d-a140-9d8ba5973df7', '3b4c929e-1397-495a-a989-a03d84d9ca83', 56) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('70f342a9-c735-4287-8403-ece3450b205d', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 53) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('7c1d812c-d06d-456b-8b6b-530035e330bd', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 51) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('34ed7ab4-c589-48ec-8963-0f1c78ee7a16', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 59) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('6d53d226-31a1-474b-b128-a46bf0ca5fd5', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 50) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('a61d4ce9-5f88-4827-ab44-4f3408c9ee1e', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 52) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f3df2a2a-42ec-4e1a-bff1-eb890c95bc93', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 57) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('f94f870e-1010-484d-8120-54d3f164d4f1', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 55) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('bba5b608-dc6a-4d02-96d5-50ed42f598fc', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 60) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('cc370847-1192-4294-af42-b237865aa9b3', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 54) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('aee77e91-5ed3-475a-8b08-6e3a45e2276a', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 58) ON CONFLICT DO NOTHING;
INSERT INTO "ecommerce"."offer_qualifying_products" ("id", "offer_id", "product_id") VALUES ('449d20f6-6096-46d8-99fe-4ff787c1eb3c', 'cfb64206-9d67-4b81-8d9b-4021f85ac440', 56) ON CONFLICT DO NOTHING;

-- ============================================================================
-- SECTION 4: UPDATE PRODUCTS WITH SKU VALUES
-- ============================================================================

-- Updating 94 products with SKU values
UPDATE "ecommerce"."products" SET "sku" = 'AMM-C-44' WHERE "id" = 16;
UPDATE "ecommerce"."products" SET "sku" = 'AMM-C-58' WHERE "id" = 17;
UPDATE "ecommerce"."products" SET "sku" = 'AMM-C-75' WHERE "id" = 18;
UPDATE "ecommerce"."products" SET "sku" = 'AMM-S-50' WHERE "id" = 19;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-2.5' WHERE "id" = 20;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-4x3' WHERE "id" = 21;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-2.5x6' WHERE "id" = 22;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-SL' WHERE "id" = 23;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-H' WHERE "id" = 24;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-C' WHERE "id" = 25;
UPDATE "ecommerce"."products" SET "sku" = 'AAM-P' WHERE "id" = 26;
UPDATE "ecommerce"."products" SET "sku" = 'ACM-2.5' WHERE "id" = 27;
UPDATE "ecommerce"."products" SET "sku" = 'ACM-5' WHERE "id" = 28;
UPDATE "ecommerce"."products" SET "sku" = 'ACM-4x3' WHERE "id" = 29;
UPDATE "ecommerce"."products" SET "sku" = 'ACM-2.5x6' WHERE "id" = 30;
UPDATE "ecommerce"."products" SET "sku" = 'AMK-C-44' WHERE "id" = 31;
UPDATE "ecommerce"."products" SET "sku" = 'AMK-C-58' WHERE "id" = 32;
UPDATE "ecommerce"."products" SET "sku" = 'AMK-C-75' WHERE "id" = 33;
UPDATE "ecommerce"."products" SET "sku" = 'AMiKe' WHERE "id" = 34;
UPDATE "ecommerce"."products" SET "sku" = 'ABO' WHERE "id" = 35;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A5' WHERE "id" = 36;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A4' WHERE "id" = 37;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3' WHERE "id" = 38;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3+' WHERE "id" = 39;
UPDATE "ecommerce"."products" SET "sku" = 'APR-MAXI' WHERE "id" = 40;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A4-2' WHERE "id" = 41;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A4-3' WHERE "id" = 42;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A4-4' WHERE "id" = 43;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3-2' WHERE "id" = 44;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3-3' WHERE "id" = 45;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3-4' WHERE "id" = 46;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3+2' WHERE "id" = 47;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3+3' WHERE "id" = 48;
UPDATE "ecommerce"."products" SET "sku" = 'APR-A3+4' WHERE "id" = 49;
UPDATE "ecommerce"."products" SET "sku" = 'APD-M-bl' WHERE "id" = 50;
UPDATE "ecommerce"."products" SET "sku" = 'APD-M-b' WHERE "id" = 51;
UPDATE "ecommerce"."products" SET "sku" = 'APD-M-r' WHERE "id" = 52;
UPDATE "ecommerce"."products" SET "sku" = 'APD-M-3/4' WHERE "id" = 53;
UPDATE "ecommerce"."products" SET "sku" = 'APD-N-bl' WHERE "id" = 54;
UPDATE "ecommerce"."products" SET "sku" = 'APD-N-b' WHERE "id" = 55;
UPDATE "ecommerce"."products" SET "sku" = 'APD-N-r' WHERE "id" = 56;
UPDATE "ecommerce"."products" SET "sku" = 'APD-N-3/4' WHERE "id" = 57;
UPDATE "ecommerce"."products" SET "sku" = 'APD-N-fs' WHERE "id" = 58;
UPDATE "ecommerce"."products" SET "sku" = 'APD-M-b-color' WHERE "id" = 59;
UPDATE "ecommerce"."products" SET "sku" = 'APD-N-b-color' WHERE "id" = 60;
UPDATE "ecommerce"."products" SET "sku" = 'APB-S-4' WHERE "id" = 61;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A5-4' WHERE "id" = 62;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A4-4' WHERE "id" = 63;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A3-4' WHERE "id" = 64;
UPDATE "ecommerce"."products" SET "sku" = 'APB-S-8' WHERE "id" = 65;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A5-8' WHERE "id" = 66;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A4-8' WHERE "id" = 67;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A3-8' WHERE "id" = 68;
UPDATE "ecommerce"."products" SET "sku" = 'APB-S-12' WHERE "id" = 69;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A5-12' WHERE "id" = 70;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A4-12' WHERE "id" = 71;
UPDATE "ecommerce"."products" SET "sku" = 'APB-A3-12' WHERE "id" = 72;
UPDATE "ecommerce"."products" SET "sku" = 'APM-S' WHERE "id" = 73;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A5' WHERE "id" = 74;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A4' WHERE "id" = 75;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A3' WHERE "id" = 76;
UPDATE "ecommerce"."products" SET "sku" = 'APM-S-8' WHERE "id" = 77;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A5-8' WHERE "id" = 78;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A4-8' WHERE "id" = 79;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A3-8' WHERE "id" = 80;
UPDATE "ecommerce"."products" SET "sku" = 'APM-S-12' WHERE "id" = 81;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A5-12' WHERE "id" = 82;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A4-12' WHERE "id" = 83;
UPDATE "ecommerce"."products" SET "sku" = 'APM-A3-12' WHERE "id" = 84;
UPDATE "ecommerce"."products" SET "sku" = 'ACAL-12-T' WHERE "id" = 85;
UPDATE "ecommerce"."products" SET "sku" = 'ACAL-6-T' WHERE "id" = 86;
UPDATE "ecommerce"."products" SET "sku" = 'ACAL-12-H' WHERE "id" = 87;
UPDATE "ecommerce"."products" SET "sku" = 'ACAL-6-H' WHERE "id" = 88;
UPDATE "ecommerce"."products" SET "sku" = 'ABQ-CHOCOLATE' WHERE "id" = 89;
UPDATE "ecommerce"."products" SET "sku" = 'ABQ-FLOWER' WHERE "id" = 90;
UPDATE "ecommerce"."products" SET "sku" = 'ABQ-PHOTO' WHERE "id" = 91;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM1' WHERE "id" = 105;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM2' WHERE "id" = 106;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM9' WHERE "id" = 107;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM15' WHERE "id" = 108;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM14' WHERE "id" = 109;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM3' WHERE "id" = 110;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM4' WHERE "id" = 111;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM11' WHERE "id" = 112;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM17' WHERE "id" = 113;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM7' WHERE "id" = 114;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM12' WHERE "id" = 115;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM8' WHERE "id" = 116;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM-FAREWELL' WHERE "id" = 117;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM-MINI' WHERE "id" = 118;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM-WEDDING' WHERE "id" = 119;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM-PHOTO-COLLAGE' WHERE "id" = 120;
UPDATE "ecommerce"."products" SET "sku" = 'AFRM-PLASTIC-BEADING' WHERE "id" = 121;
UPDATE "ecommerce"."products" SET "sku" = 'AGB-GIFT-PKG' WHERE "id" = 122;

-- ============================================================================
-- END OF UPDATE — 211 rows in new tables, 94 SKU updates
-- ============================================================================