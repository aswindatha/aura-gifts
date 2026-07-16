import psycopg2, json

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM ecommerce.offers")
print("Total offers in DB:", cur.fetchone()[0])

cur.execute("""SELECT offer_name, promotion_group, criteria_type, required_count, required_value, status
    FROM ecommerce.offers WHERE promotion_group IS NOT NULL
    ORDER BY promotion_group, required_count, required_value""")
rows = cur.fetchall()

groups = {}
for r in rows:
    g = r[1]
    groups.setdefault(g, []).append({"name": r[0], "type": r[2], "req_count": r[3], "req_value": r[4], "status": r[5]})

print()
for g in sorted(groups.keys()):
    print(f"  {g} ({len(groups[g])} tiers):")
    for o in groups[g]:
        if o["req_count"]:
            threshold = f"Buy {o['req_count']}"
        else:
            threshold = f"Spend Rs {o['req_value']}"
        print(f"    {o['name']}  [{threshold}]  {o['status']}")

# Also check qualifying products count per offer
cur.execute("""
    SELECT o.offer_name, o.promotion_group, COUNT(oqp.product_id) as qcount
    FROM ecommerce.offers o
    LEFT JOIN ecommerce.offer_qualifying_products oqp ON o.offer_id = oqp.offer_id
    WHERE o.promotion_group IS NOT NULL
    GROUP BY o.offer_name, o.promotion_group
    ORDER BY o.promotion_group, o.offer_name
""")
print("\nQualifying products per offer:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[2]} qualifying products")

# Write report
report = {"total_offers": len(rows), "groups": {g: len(v) for g, v in sorted(groups.items())}}
with open("seed_report_offers.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=True)
print("\nReport saved to seed_report_offers.json")

cur.close()
conn.close()
