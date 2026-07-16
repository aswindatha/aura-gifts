"""Generate a product list markdown file from the database."""
import psycopg2
import json
from datetime import datetime

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

cur.execute("""
    SELECT id, sku, name, category, price, mrp, badge, available_count,
           out_of_stock, style_id, description, specs, created_at
    FROM ecommerce.products
    ORDER BY category, sku, name
""")
rows = cur.fetchall()

lines = []
lines.append("# AURA Prints & Gifts — Product Catalogue")
lines.append("")
lines.append(f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
lines.append(f"> **Total Products:** {len(rows)}")
lines.append("")
lines.append("---")
lines.append("")

# Group by category
by_cat = {}
for r in rows:
    cat = r[3] or "(uncategorized)"
    by_cat.setdefault(cat, []).append(r)

# Category summary table
lines.append("## Category Summary")
lines.append("")
lines.append("| Category | Total | Priced | Unpriced |")
lines.append("|---|---:|---:|---:|")
unpriced_total = 0
for cat in sorted(by_cat.keys()):
    items = by_cat[cat]
    p = sum(1 for i in items if i[4] and float(i[4]) > 0)
    u = len(items) - p
    unpriced_total += u
    lines.append(f"| {cat} | {len(items)} | {p} | {u} |")
lines.append(f"| **TOTAL** | **{len(rows)}** | **{len(rows)-unpriced_total}** | **{unpriced_total}** |")
lines.append("")
lines.append("---")
lines.append("")

# Detailed listing per category
for cat in sorted(by_cat.keys()):
    items = by_cat[cat]
    priced = sum(1 for i in items if i[4] and float(i[4]) > 0)
    unpriced = len(items) - priced
    lines.append(f"## {cat} ({len(items)} products — {priced} priced, {unpriced} unpriced)")
    lines.append("")
    lines.append("| ID | SKU | Name | Price | MRP | Badge | Stock | Status |")
    lines.append("|---:|---|---|---:|---:|---|---:|---|")
    for i in items:
        pid, sku, name, _, price, mrp, badge, stock, oos, style_id, desc, specs, _ = i
        sku_str = sku or "—"
        price_str = f"Rs {float(price):,.2f}" if price and float(price) > 0 else "Rs 0.00 ⚠️"
        mrp_str = f"Rs {float(mrp):,.2f}" if mrp else "—"
        badge_str = badge or "—"
        stock_str = str(stock) if stock is not None else "0"
        status_str = "OUT OF STOCK" if oos else "In Stock"
        lines.append(f"| {pid} | `{sku_str}` | {name} | {price_str} | {mrp_str} | {badge_str} | {stock_str} | {status_str} |")
    lines.append("")

    # Show specs details for products that have them
    has_specs = [i for i in items if i[11] and isinstance(i[11], dict) and (i[11].get("frame_sizes") or i[11].get("min_qty") or i[11].get("components"))]
    if has_specs:
        lines.append("### Specs Details")
        lines.append("")
        for i in has_specs:
            pid, sku, name, _, _, _, _, _, _, _, _, specs, _ = i
            sku_str = sku or "—"
            lines.append(f"**{name}** (`{sku_str}`, ID={pid})")
            lines.append("")
            if "frame_sizes" in specs:
                lines.append("- **Frame sizes:**")
                for s in specs["frame_sizes"]:
                    sprice = f"Rs {float(s['price']):,.2f}" if s.get("price") and float(s.get("price", 0)) > 0 else "Rs 0.00 ⚠️"
                    lines.append(f"  - {s['size']} — {sprice}")
            if "min_qty" in specs:
                lines.append(f"- **Order quantity range:** {specs['min_qty']}–{specs['max_qty']} copies")
            if "components" in specs:
                lines.append(f"- **Components:** {', '.join(specs['components'])}")
            lines.append("")
    lines.append("---")
    lines.append("")

# Unpriced items section
lines.append("## Unpriced Items (price=0 — shopkeeper must confirm pricing)")
lines.append("")
unpriced = [r for r in rows if not r[4] or float(r[4]) == 0]
if unpriced:
    lines.append("| SKU | Category | Name | Reason |")
    lines.append("|---|---|---|---|")
    for r in unpriced:
        pid, sku, name, cat, _, _, badge, _, _, _, _, _, _ = r
        sku_str = sku or "—"
        reason = "No price in xlsx" if badge == "PRICE_CONFIRMATION_NEEDED" else "—"
        lines.append(f"| `{sku_str}` | {cat} | {name} | {reason} |")
else:
    lines.append("*(none)*")
lines.append("")
lines.append("---")
lines.append("")

# Legend
lines.append("## Legend")
lines.append("")
lines.append("- ⚠️ = Price is Rs 0.00, needs shopkeeper confirmation (badge: `PRICE_CONFIRMATION_NEEDED`)")
lines.append("- `SKU` = Product code from the xlsx catalogue (blank for items without a SKU)")
lines.append("- Frame products have `specs.frame_sizes` with per-size pricing (currently all Rs 0.00)")
lines.append("- Invitation products have `specs.min_qty` / `specs.max_qty` for order quantity range")
lines.append("")

output = "\n".join(lines)
print(output[:200] + "...\n")
print(f"Total lines: {len(lines)}")

with open("PRODUCT_LIST.md", "w", encoding="utf-8") as f:
    f.write(output)
print(">> Saved to PRODUCT_LIST.md")

cur.close()
conn.close()
