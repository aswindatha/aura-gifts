# Database Architecture Rules & Constraints

## Project: E-commerce & Shop Maintenance Application

### Target Environment: Supabase Free Tier

This document outlines the strict engineering rules and schema constraints required to keep our combined e-commerce and shop maintenance application operating safely, performantly, and **100% free** within the Supabase Free Tier boundaries.

---

## 1. Storage & Size Rules (Max 500 MB)

PostgreSQL text and numeric types are incredibly lightweight, but poor handling of media or large blocks of text will exhaust the 500 MB limit.

### Rule 1.1: Complete Binary Ban (`BYTEA`)

* **Prohibited:** Storing images, product photos, invoice PDFs, or repair receipts directly in database tables using `BYTEA` or binary large object formats.
* **Enforced Alternative:** Upload all media files to **Supabase Storage** (utilizing the 1 GB free bucket limit). Store *only* the resulting public asset URL string (`VARCHAR` or `TEXT`) in the database column.

### Rule 1.2: Strict Schema Data-Typing

Avoid using generic `TEXT` fields for fixed values. Use highly efficient numeric approximations:

* **Statuses & Roles:** Use `SMALLINT` or specialized Postgres `ENUM` types for statuses.
  Example: Order Status → `1 = Pending`, `2 = Shipped`
  Avoid repetitive strings like `"pending_verification"`.

* **Primary/Foreign Keys:** Use the native `UUID` data type for uniquely identifying users and records instead of arbitrarily long hashed strings.

### Rule 1.3: Maintenance Log Truncation

Shop maintenance tracking (machinery repair history, utility metrics) can generate extensive row counts over time.

* Compress detail entries.
* Store comprehensive technician descriptions or multi-page checklists as `.txt` or `.json` files in Supabase Storage.
* Reference them using a single file link in the database table.

---

## 2. Memory & RAM Rules (Max 500 MB Shared RAM)

Because the infrastructure shares a restricted 500 MB memory pool, unoptimized queries that trigger full-table sequential scans will exhaust container memory.

### Rule 2.1: Defensive Indexing Strategy

* **Mandatory:** Create B-Tree indexes on columns frequently used in:

  * `WHERE`
  * `JOIN`
  * `ORDER BY`

Examples:

* `user_id`
* `sku`
* `created_at`
* `status`

**Restriction:** Do not over-index.

Every additional index consumes persistent memory and disk space. Avoid indexing:

* Long text descriptions
* Low-cardinality columns (e.g., boolean active/inactive flags)

### Rule 2.2: Mandatory API Pagination

The Python backend API **must never** execute unrestricted `SELECT *` commands.

All endpoints exposing:

* Product directories
* Maintenance histories
* Order lists

Must enforce pagination:

```sql
LIMIT 20 OFFSET 0;
```

Recommended approaches:

* Limit-offset pagination
* Cursor-based pagination

This prevents large row arrays from saturating database buffer pools.

---

## 3. Structural Isolation (Hybrid Domain Architecture)

To manage both user-facing retail data and private internal workshop operations within a single free database allotment (limit of 2 active free projects total), database objects must be isolated using PostgreSQL schemas.

### Architecture Diagram

```text
                [ Supabase Database Instance ]
                              │
     ┌────────────────────────┴────────────────────────┐
     ▼                                                 ▼

        [ ecommerce schema ]               [ maintenance schema ]
        ├── users                          ├── equipment
        ├── products                       ├── repair_logs
        └── orders                         └── store_expenses
```

### Rule 3.1: Namespace Separation

Do **not** combine internal management assets and customer shop inventories in the default `public` schema.

Segment data logically:

#### `ecommerce` schema

Contains:

* `users`
* `products`
* `orders`
* `cart_items`
* Transaction tables

#### `maintenance` schema

Contains:

* `machinery`
* `repair_logs`
* `tasks`
* Shop overhead metrics

---

## 4. Security & Network Egress Rules (Max 5 GB Egress)

[Supabase](https://supabase.com?utm_source=chatgpt.com) auto-generates REST endpoints directly over PostgreSQL structures. Access must be managed strictly at the database layer to optimize data transmission sizes.

### Rule 4.1: Explicit Column Selection

To respect the **5 GB network egress bandwidth constraint**, backend queries must selectively pull only required fields.

Avoid:

```sql
SELECT * FROM orders;
```

Prefer:

```sql
SELECT SUM(order_total) FROM orders;
```

Guideline:

* Compute aggregates directly in PostgreSQL
* Transmit only primitive results
* Minimize payload size

### Rule 4.2: Zero-Trust Row Level Security (RLS)

**Enforcement:** RLS must be activated on **every table** across all custom schemas.

#### E-commerce Policies

Customers are restricted via:

```sql
auth.uid()
```

This ensures they can only:

* Query their own rows
* Update their own checkout data
* Access personal transactions

#### Maintenance Policies

Prevent standard user interaction entirely.

Access to `maintenance` schema requires:

* `admin` role
  or
* `staff` privilege flag

---

## 5. Free-Tier Lifecycle Management

### Rule 5.1: Keep-Alive Activity Trigger

Supabase automatically pauses inactive free projects after **7 consecutive days of zero traffic**.

**Enforcement:** During:

* Non-production phases
* Local testing gaps
* Development downtime

The system must receive at least **one automated ping or manual query every 5 days** to prevent suspension.

Example keep-alive query:

```sql
SELECT NOW();
```

---

## Final Engineering Constraints Summary

| Resource           | Free Tier Limit | Required Strategy          |
| ------------------ | --------------: | -------------------------- |
| Database Storage   |          500 MB | Store only structured data |
| Storage Bucket     |            1 GB | Store media/files only     |
| RAM                |          500 MB | Index carefully + paginate |
| Network Egress     |            5 GB | Select minimal columns     |
| Inactivity Timeout |          7 days | Ping every 5 days          |

---

**Primary Goal:** Maintain a scalable hybrid e-commerce + maintenance platform while remaining entirely inside Supabase free-tier limits without service suspension or performance degradation.
