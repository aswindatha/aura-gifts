"""
Seed promotional offers from AURA flyer images.

Combo offers: 2026-07-16 00:00:00 to 2026-07-19 23:59:59 IST
Grand Opening offers: 2026-07-16 00:00:00 to 2026-07-31 23:59:59 IST

Each tiered promotion uses promotion_group so tiers can coexist without
triggering the conflict check.

Free product rule: first qualifying SKU alphabetically (deterministic).
"""
import psycopg2
import json
import uuid
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

# ─── Date ranges ─────────────────────────────────────────────────────────────
COMBO_START = datetime(2026, 7, 16, 0, 0, 0, tzinfo=IST)
COMBO_END = datetime(2026, 7, 19, 23, 59, 59, tzinfo=IST)
GRAND_OPENING_START = datetime(2026, 7, 16, 0, 0, 0, tzinfo=IST)
GRAND_OPENING_END = datetime(2026, 7, 31, 23, 59, 59, tzinfo=IST)


# ─── Helper: get product IDs by SKU list ─────────────────────────────────────
def get_product_ids_by_sku(skus):
    """Return list of product IDs matching the given SKUs, sorted by SKU alphabetically."""
    if not skus:
        return []
    placeholders = ",".join(["%s"] * len(skus))
    cur.execute(f"""
        SELECT id, sku FROM ecommerce.products
        WHERE sku IN ({placeholders})
        ORDER BY sku ASC
    """, skus)
    return [row[0] for row in cur.fetchall()]


def get_product_id_by_sku(sku):
    """Return product ID for a single SKU."""
    cur.execute("SELECT id FROM ecommerce.products WHERE sku = %s", (sku,))
    row = cur.fetchone()
    return row[0] if row else None


def get_product_ids_by_category(category):
    """Return all product IDs in a category, sorted by name."""
    cur.execute("""
        SELECT id FROM ecommerce.products WHERE category = %s ORDER BY name ASC
    """, (category,))
    return [row[0] for row in cur.fetchall()]


# ─── Helper: create offer with tiers ─────────────────────────────────────────
created_offers = []

def create_offer(offer_name, criteria_type, product_scope, required_count=None,
                 required_value=None, reward_type="FREE_PRODUCT",
                 free_product_id=None, free_product_qty=1,
                 start_datetime=COMBO_START, end_datetime=COMBO_END,
                 qualifying_product_ids=None, promotion_group=None):
    """Insert an offer row + qualifying products."""
    offer_id = uuid.uuid4()
    cur.execute("""
        INSERT INTO ecommerce.offers
            (offer_id, offer_name, criteria_type, product_scope, product_id,
             required_count, required_value, reward_type, free_product_id,
             free_product_qty, start_datetime, end_datetime, status, promotion_group,
             created_at, updated_at)
        VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, NOW(), NOW())
        RETURNING offer_id
    """, (str(offer_id), offer_name, criteria_type, product_scope,
          required_count, required_value, reward_type, free_product_id,
          free_product_qty, start_datetime, end_datetime, promotion_group))
    inserted_id = cur.fetchone()[0]

    if qualifying_product_ids:
        for pid in qualifying_product_ids:
            cur.execute("""
                INSERT INTO ecommerce.offer_qualifying_products (id, offer_id, product_id)
                VALUES (%s, %s, %s)
            """, (str(uuid.uuid4()), str(inserted_id), pid))

    created_offers.append({
        "offer_name": offer_name,
        "promotion_group": promotion_group,
        "criteria_type": criteria_type,
        "required_count": required_count,
        "required_value": required_value,
        "free_product_id": free_product_id,
        "free_product_qty": free_product_qty,
        "qualifying_count": len(qualifying_product_ids or []),
    })
    return inserted_id


# ─── METAL MAGNETS (Pre-Designed) ────────────────────────────────────────────
# Qualifying: AMM-C-44, AMM-C-58, AMM-C-75, AMM-S-50 (all metal magnets)
metal_magnet_skus = ["AMM-C-44", "AMM-C-58", "AMM-C-75", "AMM-S-50"]
metal_magnet_ids = get_product_ids_by_sku(metal_magnet_skus)
# Free product = first qualifying SKU alphabetically = AMM-C-44
free_metal_magnet = get_product_id_by_sku("AMM-C-44")

metal_magnet_tiers = [
    (7, 2, "Metal Magnet Pre-Designed — Buy 7 Get 2 Free"),
    (12, 3, "Metal Magnet Pre-Designed — Buy 12 Get 3 Free"),
    (15, 4, "Metal Magnet Pre-Designed — Buy 15 Get 4 Free"),
]
for req, free_qty, name in metal_magnet_tiers:
    create_offer(name, "PURCHASE_COUNT", "MULTIPLE_PRODUCT",
                 required_count=req, free_product_id=free_metal_magnet,
                 free_product_qty=free_qty, qualifying_product_ids=metal_magnet_ids,
                 promotion_group="METAL_MAGNET_PREDESIGNED")

# ─── METAL MAGNETS (Customized) ──────────────────────────────────────────────
# Same SKUs but customized variant — task says "all customized metal magnet SKUs"
# The xlsx doesn't distinguish pre-designed vs customized for metal magnets.
# We use the same SKUs but a different promotion_group.
free_metal_magnet_custom = get_product_id_by_sku("AMM-C-44")

metal_magnet_custom_tiers = [
    (5, 1, "Metal Magnet Customized — Buy 5 Get 1 Free"),
    (10, 3, "Metal Magnet Customized — Buy 10 Get 3 Free"),
    (12, 4, "Metal Magnet Customized — Buy 12 Get 4 Free"),
]
for req, free_qty, name in metal_magnet_custom_tiers:
    create_offer(name, "PURCHASE_COUNT", "MULTIPLE_PRODUCT",
                 required_count=req, free_product_id=free_metal_magnet_custom,
                 free_product_qty=free_qty, qualifying_product_ids=metal_magnet_ids,
                 promotion_group="METAL_MAGNET_CUSTOMIZED")

# ─── ACRYLIC MAGNETS (Customized only) ───────────────────────────────────────
acrylic_magnet_skus = ["AAM-2.5", "AAM-4x3", "AAM-2.5x6", "AAM-SL", "AAM-H", "AAM-C", "AAM-P"]
acrylic_magnet_ids = get_product_ids_by_sku(acrylic_magnet_skus)
# Free product = first SKU alphabetically = AAM-2.5
free_acrylic_magnet = get_product_id_by_sku("AAM-2.5")

acrylic_magnet_tiers = [
    (3, 1, "Acrylic Magnet Customized — Buy 3 Get 1 Free"),
    (6, 2, "Acrylic Magnet Customized — Buy 6 Get 2 Free"),
    (10, 3, "Acrylic Magnet Customized — Buy 10 Get 3 Free"),
    (15, 4, "Acrylic Magnet Customized — Buy 15 Get 4 Free"),
]
for req, free_qty, name in acrylic_magnet_tiers:
    create_offer(name, "PURCHASE_COUNT", "MULTIPLE_PRODUCT",
                 required_count=req, free_product_id=free_acrylic_magnet,
                 free_product_qty=free_qty, qualifying_product_ids=acrylic_magnet_ids,
                 promotion_group="ACRYLIC_MAGNET_CUSTOMIZED")

# ─── POSTERS (A5, A4, A3, A3+ only — exclude split) ──────────────────────────
poster_skus = ["APR-A5", "APR-A4", "APR-A3", "APR-A3+"]
poster_ids = get_product_ids_by_sku(poster_skus)
# Free product = first SKU alphabetically = APR-A3 (A3 < A3+ < A4 < A5)
free_poster = get_product_id_by_sku("APR-A3")

poster_tiers = [
    (5, 1, "Poster Combo — Buy 5 Get 1 Free"),
    (10, 2, "Poster Combo — Buy 10 Get 2 Free"),
    (18, 4, "Poster Combo — Buy 18 Get 4 Free"),
    (23, 5, "Poster Combo — Buy 23 Get 5 Free"),
    (30, 7, "Poster Combo — Buy 30 Get 7 Free"),
]
for req, free_qty, name in poster_tiers:
    create_offer(name, "PURCHASE_COUNT", "MULTIPLE_PRODUCT",
                 required_count=req, free_product_id=free_poster,
                 free_product_qty=free_qty, qualifying_product_ids=poster_ids,
                 promotion_group="POSTER_COMBO")

# ─── POLAROIDS (Pre-Designed) ────────────────────────────────────────────────
# Pre-designed: Mini | Normal | Border | Borderless
# SKUs: APD-M-bl, APD-M-b, APD-M-r, APD-M-3/4, APD-N-bl, APD-N-b, APD-N-r, APD-N-3/4, APD-N-fs
polaroid_predesigned_skus = [
    "APD-M-bl", "APD-M-b", "APD-M-r", "APD-M-3/4",
    "APD-N-bl", "APD-N-b", "APD-N-r", "APD-N-3/4", "APD-N-fs"
]
polaroid_predesigned_ids = get_product_ids_by_sku(polaroid_predesigned_skus)
# Free product = first SKU alphabetically = APD-M-3/4
free_polaroid_predesigned = get_product_id_by_sku("APD-M-3/4")

polaroid_predesigned_tiers = [
    (10, 3, "Polaroid Pre-Designed — Buy 10 Get 3 Free"),
    (16, 5, "Polaroid Pre-Designed — Buy 16 Get 5 Free"),
    (22, 7, "Polaroid Pre-Designed — Buy 22 Get 7 Free"),
    (33, 12, "Polaroid Pre-Designed — Buy 33 Get 12 Free"),
    (40, 15, "Polaroid Pre-Designed — Buy 40 Get 15 Free"),
]
for req, free_qty, name in polaroid_predesigned_tiers:
    create_offer(name, "PURCHASE_COUNT", "MULTIPLE_PRODUCT",
                 required_count=req, free_product_id=free_polaroid_predesigned,
                 free_product_qty=free_qty, qualifying_product_ids=polaroid_predesigned_ids,
                 promotion_group="POLAROID_PREDESIGNED")

# ─── POLAROIDS (Customized) ──────────────────────────────────────────────────
# Customized: includes color variants
polaroid_custom_skus = [
    "APD-M-bl", "APD-M-b", "APD-M-r", "APD-M-3/4",
    "APD-N-bl", "APD-N-b", "APD-N-r", "APD-N-3/4", "APD-N-fs",
    "APD-M-b-color", "APD-N-b-color"
]
polaroid_custom_ids = get_product_ids_by_sku(polaroid_custom_skus)
free_polaroid_custom = get_product_id_by_sku("APD-M-3/4")

polaroid_custom_tiers = [
    (10, 2, "Polaroid Customized — Buy 10 Get 2 Free"),
    (16, 4, "Polaroid Customized — Buy 16 Get 4 Free"),
    (22, 7, "Polaroid Customized — Buy 22 Get 7 Free"),
    (33, 10, "Polaroid Customized — Buy 33 Get 10 Free"),
    (40, 12, "Polaroid Customized — Buy 40 Get 12 Free"),
]
for req, free_qty, name in polaroid_custom_tiers:
    create_offer(name, "PURCHASE_COUNT", "MULTIPLE_PRODUCT",
                 required_count=req, free_product_id=free_polaroid_custom,
                 free_product_qty=free_qty, qualifying_product_ids=polaroid_custom_ids,
                 promotion_group="POLAROID_CUSTOMIZED")

# ─── GRAND OPENING OFFERS (spend-based, storewide) ───────────────────────────
# These use PURCHASE_VALUE + ALL_PRODUCTS
# Free products are specific frame products

# Offer 1: Spend 1299 → 4x4 Mini Frame
mini_frame_id = get_product_id_by_sku("AFRM-MINI")
create_offer("Grand Opening — Spend ₹1299 Get 4x4 Mini Frame Free",
             "PURCHASE_VALUE", "ALL_PRODUCTS",
             required_value=1299, free_product_id=mini_frame_id,
             free_product_qty=1,
             start_datetime=GRAND_OPENING_START, end_datetime=GRAND_OPENING_END,
             promotion_group="GRAND_OPENING")

# Offer 2: Spend 1999 → 7x5 Frame (Normal Frame Type A has 7x5 size)
normal_frame_a_id = get_product_id_by_sku("AFRM1")
create_offer("Grand Opening — Spend ₹1999 Get 7x5 Frame Free",
             "PURCHASE_VALUE", "ALL_PRODUCTS",
             required_value=1999, free_product_id=normal_frame_a_id,
             free_product_qty=1,
             start_datetime=GRAND_OPENING_START, end_datetime=GRAND_OPENING_END,
             promotion_group="GRAND_OPENING")

# Offer 3: Spend 2399 → 8x6 Frame (Normal Frame Type A has 6x8 size)
create_offer("Grand Opening — Spend ₹2399 Get 8x6 Frame Free",
             "PURCHASE_VALUE", "ALL_PRODUCTS",
             required_value=2399, free_product_id=normal_frame_a_id,
             free_product_qty=1,
             start_datetime=GRAND_OPENING_START, end_datetime=GRAND_OPENING_END,
             promotion_group="GRAND_OPENING")

# Offer 4: Spend 3499 → 12x8 Frame (Normal Frame Type A has 12x8 size)
create_offer("Grand Opening — Spend ₹3499 Get 12x8 Frame Free",
             "PURCHASE_VALUE", "ALL_PRODUCTS",
             required_value=3499, free_product_id=normal_frame_a_id,
             free_product_qty=1,
             start_datetime=GRAND_OPENING_START, end_datetime=GRAND_OPENING_END,
             promotion_group="GRAND_OPENING")

# Offer 5: Spend 4499 → Customized Gift Package
gift_bundle_id = get_product_id_by_sku("AGB-GIFT-PKG")
create_offer("Grand Opening — Spend ₹4499 Get Customized Gift Package Free",
             "PURCHASE_VALUE", "ALL_PRODUCTS",
             required_value=4499, free_product_id=gift_bundle_id,
             free_product_qty=1,
             start_datetime=GRAND_OPENING_START, end_datetime=GRAND_OPENING_END,
             promotion_group="GRAND_OPENING")

conn.commit()

# ─── Summary Report ──────────────────────────────────────────────────────────
print("=" * 70)
print("  AURA PRINTS — PROMOTIONAL OFFERS SEED REPORT")
print("=" * 70)
print(f"\n  Total offer rows created: {len(created_offers)}")

# Group by promotion_group
groups = {}
for o in created_offers:
    g = o["promotion_group"] or "(no group)"
    groups.setdefault(g, []).append(o)

print(f"\n  {'PROMOTION GROUP':<35} {'TIERS':>5}  {'TYPE':<15}")
print(f"  {'-'*35} {'-'*5}  {'-'*15}")
for g in sorted(groups.keys()):
    offers = groups[g]
    ctype = offers[0]["criteria_type"]
    print(f"  {g:<35} {len(offers):>5}  {ctype:<15}")

print(f"\n  DETAILED OFFER LIST:")
print(f"  {'-'*70}")
for g in sorted(groups.keys()):
    print(f"\n  ── {g} ──")
    for o in groups[g]:
        if o["criteria_type"] == "PURCHASE_COUNT":
            threshold = f"Buy {o['required_count']}"
        else:
            threshold = f"Spend ₹{o['required_value']}"
        reward = f"Get {o['free_product_qty']} Free (product_id={o['free_product_id']})"
        print(f"    {o['offer_name']}")
        print(f"      {threshold} → {reward} | qualifying={o['qualifying_count']} products")

# Write report to file
report = {
    "total_offers": len(created_offers),
    "groups": {g: len(v) for g, v in sorted(groups.items())},
    "offers": created_offers,
}
with open("seed_report_offers.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
print(f"\n  Report saved to seed_report_offers.json")

cur.close()
conn.close()
