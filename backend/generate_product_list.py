"""Generate a product list file from the database."""
import psycopg2
import json
from datetime import datetime

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

cur.execute("""
    SELECT id, sku, name, category, price, mrp, badge, available_count,
           out_of_stock, style_id, specs, created_at
    FROM ecommerce.products
    ORDER BY category, sku, name
""")
rows = cur.fetchall()

lines = []
lines.append("=" * 100)
lines.append("  AURA PRINTS & GIFTS — PRODUCT CATALOGUE (DB SNAPSHOT)")
lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"  Total Products: {len(rows)}")
lines.append("=" * 100)
lines.append("")

# Group by category
by_cat = {}
for r in rows:
    cat = r[3] or "(uncategorized)"
    by_cat.setdefault(cat, []).append(r)

for cat in sorted(by_cat.keys()):
    items = by_cat[cat]
    priced = sum(1 for i in items if i[4] and float(i[4]) > 0)
    unpriced = len(items) - priced
    lines.append(f"  ┌─ {cat.upper()} ({len(items)} products — {priced} priced, {unpriced} unpriced)")
    lines.append(f"  │")
    for i in items:
        pid, sku, name, _, price, mrp, badge, stock, oos, style_id, specs, _ = i
        sku_str = sku or "(no sku)"
        price_str = f"Rs {float(price):,.2f}" if price and float(price) > 0 else "Rs 0.00 (NEEDS PRICING)"
        badge_str = f" [{badge}]" if badge else ""
        stock_str = str(stock) if stock is not None else "0"
        oos_str = " | OUT OF STOCK" if oos else ""
        lines.append(f"  │  ID={pid:<4} | {sku_str:<22} | {name[:55]:<55} | {price_str:<28}{badge_str}{oos_str}")
        # Show frame sizes if present
        if specs and isinstance(specs, dict) and "frame_sizes" in specs:
            sizes = specs["frame_sizes"]
            size_list = ", ".join(f'{s["size"]}' for s in sizes)
            lines.append(f"  │         Frame sizes: {size_list}")
        if specs and isinstance(specs, dict) and "min_qty" in specs:
            lines.append(f"  │         Qty range: {specs['min_qty']}-{specs['max_qty']} copies")
    lines.append("  │")
    lines.append("")

lines.append("=" * 100)
lines.append("  UNPRICED ITEMS (price=0 — shopkeeper must confirm pricing)")
lines.append("=" * 100)
unpriced = [r for r in rows if not r[4] or float(r[4]) == 0]
if unpriced:
    for r in unpriced:
        pid, sku, name, cat, _, _, badge, _, _, _, _, _ = r
        sku_str = sku or "(no sku)"
        lines.append(f"  {sku_str:<22} | {cat:<15} | {name}")
else:
    lines.append("  (none)")
lines.append("")

lines.append("=" * 100)
lines.append("  CATEGORY SUMMARY")
lines.append("=" * 100)
lines.append(f"  {'Category':<20} {'Total':>6} {'Priced':>7} {'Unpriced':>9}")
lines.append(f"  {'-'*20} {'-'*6} {'-'*7} {'-'*9}")
for cat in sorted(by_cat.keys()):
    items = by_cat[cat]
    p = sum(1 for i in items if i[4] and float(i[4]) > 0)
    u = len(items) - p
    lines.append(f"  {cat:<20} {len(items):>6} {p:>7} {u:>9}")
lines.append(f"  {'-'*20} {'-'*6} {'-'*7} {'-'*9}")
lines.append(f"  {'TOTAL':<20} {len(rows):>6} {len(rows)-len(unpriced):>7} {len(unpriced):>9}")
lines.append("")

output = "\n".join(lines)
print(output)

with open("PRODUCT_LIST.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("\n  >> Saved to PRODUCT_LIST.txt")

# Also save as JSON
products_json = []
for r in rows:
    pid, sku, name, cat, price, mrp, badge, stock, oos, style_id, specs, created = r
    products_json.append({
        "id": pid, "sku": sku, "name": name, "category": cat,
        "price": float(price) if price else 0,
        "mrp": float(mrp) if mrp else None,
        "badge": badge, "available_count": stock,
        "out_of_stock": oos, "style_id": style_id,
        "specs": specs,
    })
with open("PRODUCT_LIST.json", "w", encoding="utf-8") as f:
    json.dump(products_json, f, indent=2, ensure_ascii=False, default=str)
print("  >> Saved to PRODUCT_LIST.json")

cur.close()
conn.close()
