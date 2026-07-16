"""
Seed product catalogue from AURA_Catalogue_Order_Price_Details_With_Invitations.xlsx
and AURA frames catalogue PDF.

- All non-frame products with prices from xlsx: one row per SKU variant
- Frame products: inserted with price=0 and badge='PRICE_CONFIRMATION_NEEDED'
  (shopkeeper must fill in real prices later)
- Products without prices in xlsx (Corporate, some Stickers, Invitations):
  inserted with price=0 and badge='PRICE_CONFIRMATION_NEEDED'
- Frame specs.frame_sizes populated from PDF size data (price=0 placeholder)

Idempotent: uses SKU as unique key — re-running updates existing rows.
"""
import psycopg2
import json
from datetime import datetime, timezone

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

# ─── Helper ──────────────────────────────────────────────────────────────────
def upsert_product(sku, name, description, price, category, specs=None, badge=None,
                   style_id=None, available_count=100):
    """Insert or update a product by SKU."""
    if sku:
        cur.execute("SELECT id FROM ecommerce.products WHERE sku = %s", (sku,))
        existing = cur.fetchone()
    else:
        cur.execute("SELECT id FROM ecommerce.products WHERE name = %s AND category = %s", (name, category))
        existing = cur.fetchone()

    specs_json = json.dumps(specs) if specs else None
    now = datetime.now(timezone.utc)

    if existing:
        product_id = existing[0]
        cur.execute("""
            UPDATE ecommerce.products SET
                name=%s, description=%s, price=%s, category=%s, badge=%s,
                specs=%s, style_id=%s, available_count=%s, updated_at=%s
            WHERE id=%s
        """, (name, description, price, category, badge, specs_json, style_id,
              available_count, now, product_id))
        return product_id, False
    else:
        cur.execute("""
            INSERT INTO ecommerce.products
                (name, description, price, category, badge, specs, style_id,
                 available_count, sku, created_at, rating, review_count, out_of_stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 4.5, 0, false)
            RETURNING id
        """, (name, description, price, category, badge, specs_json, style_id,
              available_count, sku, now))
        product_id = cur.fetchone()[0]
        return product_id, True


# ─── Frame size data from PDF ────────────────────────────────────────────────
# All sizes in inches, format "WxH"
FRAME_SIZES_NORMAL = ["4x4","6x4","6x8","7x5","10x8","12x8","12x10","12x15",
                      "15x10","18x12","24x16","12x12","24x12","24x18","20x30","24x30"]
FRAME_SIZES_FAREWELL = ["4x4","12x10","15x10","18x12"]
FRAME_SIZES_STORY = ["4x4","12x10","15x10","18x12"]
FRAME_SIZES_MINI = ["4x4","5x5"]
FRAME_SIZES_CERTIFICATE = ["6x4","12x10"]
FRAME_SIZES_WEDDING = ["12x12","18x12"]
FRAME_SIZES_COLLAGE = ["12x15","24x12"]
FRAME_SIZES_3D_MINIATURE = ["8x8","10x15"]
FRAME_SIZES_3D_ELEMENT = ["8x8","12x8","15x10"]
FRAME_SIZES_LED = ["7x5","12x10","12x8"]
FRAME_SIZES_COLLAGE_POPUP = ["12x12","15x10","12x10"]
FRAME_SIZES_CANVAS = ["12x15","12x12"]
FRAME_SIZES_EMBROIDERY = ["7x8","12x8","12x10"]
FRAME_SIZES_SPLIT = ["12x12","6x8"]
FRAME_SIZES_PLASTIC_BEADING = ["12x12","12x15"]

def make_frame_specs(sizes):
    """Build specs.frame_sizes with price=0 (shopkeeper must fill in)."""
    return {
        "frame_sizes": [{"size": s, "price": 0} for s in sizes]
    }


# ─── Track stats ─────────────────────────────────────────────────────────────
created_count = 0
updated_count = 0
unpriced_items = []
products_by_category = {}

def track(pid, is_new, category, name, sku, price):
    global created_count, updated_count
    if is_new:
        created_count += 1
    else:
        updated_count += 1
    products_by_category.setdefault(category, []).append({"id": pid, "sku": sku, "name": name, "price": price})
    if price == 0:
        unpriced_items.append({"sku": sku, "name": name, "category": category, "reason": "No price in xlsx"})


# ─── 1. PHOTO MAGNETS (category = 'magnet') ─────────────────────────────────
magnets = [
    # Metal Magnets
    ("AMM-C-44", "Circle Fridge Magnet — 44mm", "Metal magnet, 44mm circle", 45, "magnet"),
    ("AMM-C-58", "Circle Fridge Magnet — 58mm", "Metal magnet, 58mm circle", 45, "magnet"),
    ("AMM-C-75", "Circle Fridge Magnet — 75mm", "Metal magnet, 75mm circle", 89, "magnet"),
    ("AMM-S-50", "Square Fridge Magnet — 50x50mm", "Metal magnet, 50x50mm square", 50, "magnet"),
    # Acrylic Magnets
    ("AAM-2.5", "Square Acrylic Photo Magnet — 2.5x2.5in", "Acrylic magnet, 2.5x2.5in square", 40, "magnet"),
    ("AAM-4x3", "Square Acrylic Photo Magnet — 4x3in", "Acrylic magnet, 4x3in square", 60, "magnet"),
    ("AAM-2.5x6", "Square Acrylic Photo Magnet — 2.5x6in", "Acrylic magnet, 2.5x6in square", 99, "magnet"),
    ("AAM-SL", "Square Acrylic Photo Magnet — 4x6in", "Acrylic magnet, 4x6in square", 199, "magnet"),
    ("AAM-H", "Heart Shaped Acrylic Photo Magnet", "Acrylic magnet, heart shaped", 129, "magnet"),
    ("AAM-C", "Circle Shaped Acrylic Photo Magnet", "Acrylic magnet, circle shaped", 129, "magnet"),
    ("AAM-P", "Pentagon Shaped Acrylic Photo Magnet", "Acrylic magnet, pentagon shaped", 129, "magnet"),
    # Sheet Magnets
    ("ACM-2.5", "Customised Sheet Photo Magnet — 2.5x2.5in", "Sheet magnet, 2.5x2.5in", 30, "magnet"),
    ("ACM-5", "Customised Sheet Photo Magnet — 5x5in", "Sheet magnet, 5x5in", 50, "magnet"),
    ("ACM-4x3", "Customised Sheet Photo Magnet — 4x3in", "Sheet magnet, 4x3in", 45, "magnet"),
    ("ACM-2.5x6", "Customised Sheet Photo Magnet — 2.5x6in", "Sheet magnet, 2.5x6in", 60, "magnet"),
]
for sku, name, desc, price, cat in magnets:
    pid, is_new = upsert_product(sku, name, desc, price, cat, badge=None)
    track(pid, is_new, cat, name, sku, price)

# ─── 2. KEYCHAINS (category = 'keychain') ───────────────────────────────────
keychains = [
    ("AMK-C-44", "Circle Metal Keychain — 44mm", "Metal keychain, 44mm circle", 50, "keychain"),
    ("AMK-C-58", "Circle Metal Keychain — 58mm", "Metal keychain, 58mm circle", 60, "keychain"),
    ("AMK-C-75", "Circle Metal Keychain — 75mm", "Metal keychain, 75mm circle", 95, "keychain"),
    ("AMiKe", "Mirror Keychain", "Mirror keychain", 70, "keychain"),
    ("ABO", "Bottle Opener", "Bottle opener keychain", 100, "keychain"),
]
for sku, name, desc, price, cat in keychains:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 3. POSTERS (category = 'poster') ───────────────────────────────────────
posters = [
    ("APR-A5", "A5 Size Poster", "A5 size poster", 20, "poster"),
    ("APR-A4", "A4 Size Poster", "A4 size poster", 30, "poster"),
    ("APR-A3", "A3 Size Poster", "A3 size poster", 60, "poster"),
    ("APR-A3+", "A3+ Size Poster", "A3+ size poster", 70, "poster"),
    ("APR-MAXI", "4x6 Size Poster (Maxi)", "4x6 size poster", 15, "poster"),
    ("APR-A4-2", "A4 2-Split Poster", "A4 sized 2 split poster", 79, "poster"),
    ("APR-A4-3", "A4 3-Split Poster", "A4 sized 3 split poster", 119, "poster"),
    ("APR-A4-4", "A4 4-Split Poster", "A4 sized 4 split poster", 149, "poster"),
    ("APR-A3-2", "A3 2-Split Poster", "A3 sized 2 split poster", 129, "poster"),
    ("APR-A3-3", "A3 3-Split Poster", "A3 sized 3 split poster", 199, "poster"),
    ("APR-A3-4", "A3 4-Split Poster", "A3 sized 4 split poster", 269, "poster"),
    ("APR-A3+2", "A3+ 2-Split Poster", "A3+ sized 2 split poster", 159, "poster"),
    ("APR-A3+3", "A3+ 3-Split Poster", "A3+ sized 3 split poster", 229, "poster"),
    ("APR-A3+4", "A3+ 4-Split Poster", "A3+ sized 4 split poster", 339, "poster"),
]
for sku, name, desc, price, cat in posters:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 4. POLAROIDS (category = 'polaroid') ───────────────────────────────────
polaroids = [
    ("APD-M-bl", "Borderless Mini Polaroid", "Borderless mini polaroid", 5, "polaroid"),
    ("APD-M-b", "Bordered Mini Polaroid", "Bordered mini polaroid", 5, "polaroid"),
    ("APD-M-r", "Retro Type Mini Polaroid", "Retro type mini polaroid", 5, "polaroid"),
    ("APD-M-3/4", "3/4 Polaroid Mini", "3/4 polaroid mini", 5, "polaroid"),
    ("APD-N-bl", "Borderless Normal Polaroid", "Borderless normal polaroid", 15, "polaroid"),
    ("APD-N-b", "Bordered Normal Polaroid", "Bordered normal polaroid", 15, "polaroid"),
    ("APD-N-r", "Retro Type Normal Polaroid", "Retro type normal polaroid", 15, "polaroid"),
    ("APD-N-3/4", "3/4 Polaroid Normal", "3/4 polaroid normal", 15, "polaroid"),
    ("APD-N-fs", "Film Strip Polaroid", "Film strip polaroid", 75, "polaroid"),
    ("APD-M-b-color", "Bordered Custom Color Mini Polaroid", "Bordered with custom color mini", 7, "polaroid"),
    ("APD-N-b-color", "Bordered Custom Color Normal Polaroid", "Bordered with custom color normal", 18, "polaroid"),
]
for sku, name, desc, price, cat in polaroids:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 5. PHOTO BOOKS (category = 'photobook') ────────────────────────────────
photobooks = [
    ("APB-S-4", "Small Photo Book — 4 Pages", "Small size with 4 pages", 70, "photobook"),
    ("APB-A5-4", "A5 Photo Book — 4 Pages", "A5 size with 4 pages", 99, "photobook"),
    ("APB-A4-4", "A4 Photo Book — 4 Pages", "A4 size with 4 pages", 249, "photobook"),
    ("APB-A3-4", "A3 Photo Book — 4 Pages", "A3 size with 4 pages", 349, "photobook"),
    ("APB-S-8", "Small Photo Book — 8 Pages", "Small size with 8 pages", 149, "photobook"),
    ("APB-A5-8", "A5 Photo Book — 8 Pages", "A5 size with 8 pages", 199, "photobook"),
    ("APB-A4-8", "A4 Photo Book — 8 Pages", "A4 size with 8 pages", 399, "photobook"),
    ("APB-A3-8", "A3 Photo Book — 8 Pages", "A3 size with 8 pages", 499, "photobook"),
    ("APB-S-12", "Small Photo Book — 12 Pages", "Small size with 12 pages", 199, "photobook"),
    ("APB-A5-12", "A5 Photo Book — 12 Pages", "A5 size with 12 pages", 299, "photobook"),
    ("APB-A4-12", "A4 Photo Book — 12 Pages", "A4 size with 12 pages", 599, "photobook"),
    ("APB-A3-12", "A3 Photo Book — 12 Pages", "A3 size with 12 pages", 699, "photobook"),
]
for sku, name, desc, price, cat in photobooks:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 6. PHOTO MAGAZINES (category = 'magazine') ─────────────────────────────
magazines = [
    ("APM-S", "Small Photo Magazine — 4 Pages", "Small size with 4 pages", 70, "magazine"),
    ("APM-A5", "A5 Photo Magazine — 4 Pages", "A5 size with 4 pages", 99, "magazine"),
    ("APM-A4", "A4 Photo Magazine — 4 Pages", "A4 size with 4 pages", 249, "magazine"),
    ("APM-A3", "A3 Photo Magazine — 4 Pages", "A3 size with 4 pages", 349, "magazine"),
    ("APM-S-8", "Small Photo Magazine — 8 Pages", "Small size with 8 pages", 149, "magazine"),
    ("APM-A5-8", "A5 Photo Magazine — 8 Pages", "A5 size with 8 pages", 199, "magazine"),
    ("APM-A4-8", "A4 Photo Magazine — 8 Pages", "A4 size with 8 pages", 399, "magazine"),
    ("APM-A3-8", "A3 Photo Magazine — 8 Pages", "A3 size with 8 pages", 499, "magazine"),
    ("APM-S-12", "Small Photo Magazine — 12 Pages", "Small size with 12 pages", 199, "magazine"),
    ("APM-A5-12", "A5 Photo Magazine — 12 Pages", "A5 size with 12 pages", 299, "magazine"),
    ("APM-A4-12", "A4 Photo Magazine — 12 Pages", "A4 size with 12 pages", 599, "magazine"),
    ("APM-A3-12", "A3 Photo Magazine — 12 Pages", "A3 size with 12 pages", 699, "magazine"),
]
for sku, name, desc, price, cat in magazines:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 7. CALENDARS (category = 'calendar') ───────────────────────────────────
calendars = [
    ("ACAL-12-T", "12-Page Tabletop Calendar", "12 pages tabletop calendar", 450, "calendar"),
    ("ACAL-6-T", "6-Page Tabletop Calendar", "6 pages tabletop calendar", 250, "calendar"),
    ("ACAL-12-H", "12-Page Hanging Calendar", "12 pages hanging calendar", 700, "calendar"),
    ("ACAL-6-H", "6-Page Hanging Calendar", "6 pages hanging calendar", 550, "calendar"),
]
for sku, name, desc, price, cat in calendars:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 8. BOUQUETS (category = 'bouquet') ─────────────────────────────────────
bouquets = [
    ("ABQ-CHOCOLATE", "Chocolate Bouquet", "Chocolate bouquet", 350, "bouquet"),
    ("ABQ-FLOWER", "Flower Bouquet", "Flower bouquet", 350, "bouquet"),
    ("ABQ-PHOTO", "Photo Bouquet", "Photo bouquet", 350, "bouquet"),
]
for sku, name, desc, price, cat in bouquets:
    pid, is_new = upsert_product(sku, name, desc, price, cat)
    track(pid, is_new, cat, name, sku, price)

# ─── 9. CORPORATE & BRANDING (category = 'corporate') — NO PRICES ───────────
corporate = [
    (None, "ID Cards", "Custom ID cards for corporate use"),
    (None, "Badges", "Custom badges for corporate use"),
    (None, "Pamphlets", "Custom pamphlets for branding"),
    (None, "Logo Stickers", "Custom logo stickers"),
    (None, "Backlit Prints", "Backlit prints for signage"),
]
for sku, name, desc in corporate:
    pid, is_new = upsert_product(sku, name, desc, 0, "corporate", badge="PRICE_CONFIRMATION_NEEDED")
    track(pid, is_new, "corporate", name, sku, 0)

# ─── 10. STICKERS, LABELS & GIFTS (category = 'sticker_gift') ───────────────
sticker_gifts_priced = [
    ("Custom Name Label", "Custom Name Label", "Personalised name labels", 50),
    ("Ready-Made Label", "Ready-Made Label", "Pre-designed labels", 35),
]
for name, label, desc, price in sticker_gifts_priced:
    pid, is_new = upsert_product(None, name, desc, price, "sticker_gift")
    track(pid, is_new, "sticker_gift", name, None, price)

sticker_gifts_unpriced = [
    "Customised Chocolates", "Photo Clock", "Customised Playing Cards", "Customised Uno Cards",
]
for name in sticker_gifts_unpriced:
    pid, is_new = upsert_product(None, name, name, 0, "sticker_gift", badge="PRICE_CONFIRMATION_NEEDED")
    track(pid, is_new, "sticker_gift", name, None, 0)

# ─── 11. INVITATIONS (category = 'invitation') — NO PRICES ──────────────────
invitations = [
    ("A5 Invitations", "A5 Invitations", "A5 invitation cards", {"min_qty": 100, "max_qty": 500}),
    ("A4 Invitations", "A4 Invitations", "A4 invitation cards", {"min_qty": 50, "max_qty": 250}),
]
for name, label, desc, qty_range in invitations:
    specs = {"min_qty": qty_range["min_qty"], "max_qty": qty_range["max_qty"]}
    pid, is_new = upsert_product(None, name, desc, 0, "invitation", specs=specs, badge="PRICE_CONFIRMATION_NEEDED")
    track(pid, is_new, "invitation", name, None, 0)

# ─── 12. FRAMES (category = 'frame') — ALL PRICE=0, FLAGGED ─────────────────
# From xlsx + PDF. Each frame type is one product with specs.frame_sizes.
frames_data = [
    # (sku, name, description, sizes, style_id)
    ("AFRM1", "Normal Frame (Type A — Matte/Glossy/Glitter)", "Normal frame 8mm MDF. Types: Matte paper, Glossy sheet, Glitter sheet. Custom sizes available.", FRAME_SIZES_NORMAL, "frame_a"),
    ("AFRM2", "Normal Frame (Type B — 2mm Acrylic)", "Normal frame 2mm MDF with 2mm acrylic sheet. Types: Fiber sheet, MDF, Cardboard. Custom sizes available.", FRAME_SIZES_NORMAL, "frame_b"),
    ("AFRM9", "Story Frame", "Story frame. All customised frame sizes available.", FRAME_SIZES_STORY, "story"),
    ("AFRM15", "Certificate Frame", "Certificate frame. All customised frame sizes available.", FRAME_SIZES_CERTIFICATE, "certificate"),
    ("AFRM14", "Collage Frame", "Collage frame. All customised frame sizes available.", FRAME_SIZES_COLLAGE, "collage"),
    ("AFRM3", "3D Miniature Frame", "3D miniature frame. All customised frame sizes available.", FRAME_SIZES_3D_MINIATURE, "3d_mini"),
    ("AFRM4", "3D Element Frame", "3D element frame. All customised frame sizes available.", FRAME_SIZES_3D_ELEMENT, "3d_element"),
    ("AFRM11", "LED Frame", "LED frame. All customised frame sizes available.", FRAME_SIZES_LED, "led"),
    ("AFRM17", "Collage Popup Frame", "Collage popup frame. Editing applies extra charges per page.", FRAME_SIZES_COLLAGE_POPUP, "collage_popup"),
    ("AFRM7", "Canvas Frame", "Canvas frame. All customised frame sizes available.", FRAME_SIZES_CANVAS, "canvas"),
    ("AFRM12", "Embroidery Frame", "Embroidery frame. All customised frame sizes available.", FRAME_SIZES_EMBROIDERY, "embroidery"),
    ("AFRM8", "Split Frame", "Split frame. All customised frame sizes available.", FRAME_SIZES_SPLIT, "split"),
    # Additional frame types from PDF (not in xlsx)
    ("AFRM-FAREWELL", "Farewell Frame", "Farewell frame. All customised frame sizes available.", FRAME_SIZES_FAREWELL, "farewell"),
    ("AFRM-MINI", "Mini Frame", "Mini frame. All customised frame sizes available.", FRAME_SIZES_MINI, "mini"),
    ("AFRM-WEDDING", "Wedding Frame", "Wedding frame. All customised frame sizes available.", FRAME_SIZES_WEDDING, "wedding"),
    ("AFRM-PHOTO-COLLAGE", "Photo Collage Frame", "Photo collage frame with two layout options.", ["6x4-2/4x4-2/3x3-2/5x5-2", "6x4-2/4x4-2/3x3-2/6x6-2"], "photo_collage"),
    ("AFRM-PLASTIC-BEADING", "Plastic Beading Frame", "Plastic beading frame. All customised frame sizes available.", FRAME_SIZES_PLASTIC_BEADING, "plastic_beading"),
]
for sku, name, desc, sizes, sid in frames_data:
    specs = make_frame_specs(sizes)
    pid, is_new = upsert_product(sku, name, desc, 0, "frame", specs=specs, badge="PRICE_CONFIRMATION_NEEDED", style_id=sid)
    track(pid, is_new, "frame", name, sku, 0)

# ─── 13. GIFT BUNDLE for Grand Opening Offer 5 ──────────────────────────────
gift_bundle_specs = {
    "components": ["Wall Hanging", "Customized Polaroids", "LED Lights", "Decorative Leaves"],
    "description": "Customized gift package for Grand Opening offer"
}
pid, is_new = upsert_product("AGB-GIFT-PKG", "Customized Gift Package (Wall Hanging + Polaroids + LED + Decor)",
                             "Customized gift package: Wall Hanging + Customized Polaroids + LED Lights + Decorative Leaves",
                             0, "gift_bundle", specs=gift_bundle_specs, badge="PRICE_CONFIRMATION_NEEDED")
track(pid, is_new, "gift_bundle", "Customized Gift Package", "AGB-GIFT-PKG", 0)

conn.commit()

# ─── Summary Report ──────────────────────────────────────────────────────────
print("=" * 70)
print("  AURA PRINTS — PRODUCT CATALOGUE SEED REPORT")
print("=" * 70)
print(f"\n  Total products created: {created_count}")
print(f"  Total products updated: {updated_count}")
print(f"  Total products in DB now: {created_count + updated_count + 15}")  # +15 existing

print(f"\n  {'CATEGORY':<20} {'COUNT':>6}  {'PRICED':>6}  {'UNPRICED':>8}")
print(f"  {'-'*20} {'-'*6}  {'-'*6}  {'-'*8}")
for cat in sorted(products_by_category.keys()):
    items = products_by_category[cat]
    priced = sum(1 for i in items if i["price"] > 0)
    unpriced = len(items) - priced
    print(f"  {cat:<20} {len(items):>6}  {priced:>6}  {unpriced:>8}")

print(f"\n  UNPRICED ITEMS (price=0, badge=PRICE_CONFIRMATION_NEEDED):")
print(f"  {'-'*60}")
if unpriced_items:
    for item in unpriced_items:
        print(f"  {item['sku'] or '(no sku)':<20} {item['category']:<15} {item['name']}")
else:
    print("  (none)")

# Write report to file
report = {
    "total_created": created_count,
    "total_updated": updated_count,
    "products_by_category": {k: len(v) for k, v in sorted(products_by_category.items())},
    "unpriced_items": unpriced_items,
}
with open("seed_report_products.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"\n  Report saved to seed_report_products.json")

cur.close()
conn.close()
