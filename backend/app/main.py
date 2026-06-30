import asyncio
import json
import logging
import time
import os
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.future import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import engine, SessionLocal
from app.models import Base, User, Product

from app.routers import auth, products, orders, chat, storage, rfid, cart, payments, config


# ─── Logging Setup ─────────────────────────────────────────────────────────────
LOG_FILE = "/tmp/api_responses.log" if os.getenv("PRODUCTION", "0") == "1" else os.path.join(os.path.dirname(__file__), "..", "api_responses.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("aura_api")

# File handler for persistent log
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)


def _log(message: str):
    """Print to terminal and write to api_responses.log"""
    print(message, flush=True)
    logger.info(message)


class APILoggingMiddleware(BaseHTTPMiddleware):
    """Logs every API request & response: method, path, status, duration, payload summary."""

    async def dispatch(self, request: Request, call_next):
        # Skip health-check noise
        if request.url.path == "/api/health":
            return await call_next(request)

        start = time.perf_counter()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Capture request body for logging (skip large/binary file uploads)
        content_type = request.headers.get("content-type", "")
        content_length = request.headers.get("content-length")
        
        should_read_body = False
        if "application/json" in content_type:
            should_read_body = True
            if content_length:
                try:
                    if int(content_length) > 1 * 1024 * 1024:  # 1MB limit
                        should_read_body = False
                except ValueError:
                    pass
                    
        req_body_pretty = ""
        if should_read_body:
            req_body_bytes = await request.body()
            try:
                req_json = json.loads(req_body_bytes.decode())
                # Mask secrets
                for secret in ["password", "access_token", "refresh_token", "otp"]:
                    if secret in req_json:
                        req_json[secret] = "***"
                req_body_pretty = json.dumps(req_json, indent=2)
            except Exception:
                req_body_pretty = req_body_bytes.decode(errors="ignore")[:5000]
        else:
            req_body_pretty = f"<Payload omitted: content_type={content_type}, size={content_length}>"

        # Capture response body for product endpoints
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Build log entry
        path = request.url.path
        status = response.status_code
        method = request.method

        # For product list endpoint, stream body and parse product count
        body_summary = ""
        if "/api/products" in path and method == "GET":
            # Collect body chunks
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk

            try:
                data = json.loads(body_bytes.decode("utf-8"))
                if isinstance(data, list):
                    body_summary = f"  -> {len(data)} product(s) returned"
                    if data:
                        names = [p.get("name", "?") for p in data[:3]]
                        body_summary += f": [{', '.join(names)}{', ...' if len(data) > 3 else ''}]"
                elif isinstance(data, dict) and "name" in data:
                    body_summary = f"  -> Product: {data.get('name')} (id={data.get('id')})"
            except Exception:
                body_summary = f"  -> {len(body_bytes)} bytes"

            # Rebuild response with same body
            from starlette.responses import Response as StarletteResponse
            new_response = StarletteResponse(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
            log_line = (
                f"[{ts}] {method} {path} -> {status} ({duration_ms:.1f}ms)\n"
                f"{body_summary}"
            )
            _log(log_line)
            return new_response

        log_line = f"[{ts}] {method} {path} -> {status} ({duration_ms:.1f}ms)\nRequest Body:\n{req_body_pretty}\nResponse Summary:\n{body_summary}"
        _log(log_line)
        return response


app = FastAPI(title="Aura Prints API", description="FastAPI Backend for Aura Prints & Gifts Shop")

# Register API logging middleware FIRST (before CORS)
app.add_middleware(APILoggingMiddleware)

# CORS middleware config to allow React client communication
CORS_ORIGINS = (
    [
        "https://auraprintsandgifts.in",
        "https://www.auraprintsandgifts.in",
    ]
    if os.getenv("PRODUCTION", "0") == "1"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(chat.router)  # Register chat router
app.include_router(storage.router) # Register storage router
app.include_router(rfid.router)    # Register rfid router
app.include_router(cart.router)     # Register cart router
app.include_router(payments.router)   # Register payments router
app.include_router(config.router)     # Register site config router

# Create uploads directory if not exists
os.makedirs("uploads", exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")



async def keep_alive_loop():
    """
    Rule 5.1: Keep-Alive Activity Trigger
    To prevent Supabase from pausing the free project after 7 days of inactivity,
    this background loop pings the database with a lightweight SELECT NOW() query every 24 hours.
    """
    while True:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT NOW();"))
                print("[Keep-Alive] Pinged Supabase database successfully.")
        except Exception as e:
            print(f"[Keep-Alive] Failed to ping database: {e}")
        # Sleep for 24 hours (86400 seconds)
        await asyncio.sleep(86400)

async def seed_database(db):
    """
    Populate database with default users and products if tables are empty.
    Hashed passwords correspond to client credentials.
    """
    # Seed Users
    result = await db.execute(select(User).limit(1))
    if not result.scalars().first():
        from app.auth import get_password_hash
        default_users = [
            User(
                name="Site Manager",
                email="admin@auraprints.com",
                password_hash=get_password_hash("aura@2024"),
                email_verified=True,
                role=1,
                points=9999,
                subscription_tier=4,
                address="Admin HQ, Creative City"
            ),
            User(
                name="Jane Doe",
                email="customer@auraprints.com",
                password_hash=get_password_hash("customer123"),
                email_verified=True,
                role=4,
                points=450,
                subscription_tier=4,
                address="123 Artisan Way, Apt 4B, Mumbai, MH - 400001"
            ),
            User(
                name="Alex Patel",
                email="student@auraprints.com",
                password_hash=get_password_hash("student123"),
                email_verified=True,
                role=4,
                points=150,
                subscription_tier=1,
                address="Hostel 4, IIT Bombay, Powai, Mumbai - 400076"
            ),
            User(
                name="Dave Operator",
                email="dave@auraprints.com",
                password_hash=get_password_hash("dave123"),
                email_verified=True,
                role=2,
                points=0,
                subscription_tier=0,
                address="Staff Room, Shop Floor"
            ),
            User(
                name="PUSHPAVEL",
                email="pushpa@auraprints.com",
                password_hash=get_password_hash("shopkeeper123"),
                email_verified=True,
                role=3,
                points=0,
                subscription_tier=0,
                address="Billing Desk, Shop Floor"
            )
        ]
        db.add_all(default_users)
        await db.commit()
        print("[Seed] Users seed data successfully populated.")


    # Seed Products
    prod_result = await db.execute(select(Product).limit(1))
    if not prod_result.scalars().first():
        default_products = [
            Product(
                id=1,
                name="Teakwood Gallery Frame",
                price=1250.00,
                category="Frames",
                badge="Featured",
                image_url="https://lh3.googleusercontent.com/aida-public/AB6AXuBehfvhJuTMiXtWFQe2pWlkrsR8gXJXSo2dx0miac6CbTrsrNlBsUYj267ST_bYnG1SFOFQ1nL_59kxAVZ2bCO70omCeToLv3qhbzb9jlbO0opg7OW1FQATnlVYo6sjKOkbCaoV9mMBnuqC9-3ZFAsU2Fuu-YuKBs1V3IY-mkNJe0bEEYSdN9I62AeKgciKnxvKeHPMoDIFPqLECldyLjp9XziksDk3CxsbGDV8r8EMtdyMyKnV-ziRB4SNi0vHJiNFFGWcHOjJqCs",
                description="Handcrafted genuine teakwood with rich natural grain patterns. A warm, timeless classic designed to elevate your photographic prints, sketches, and professional documents.",
                out_of_stock=False,
                mrp=1800.00,
                rating=4.80,
                review_count=124,
                images=[
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuBehfvhJuTMiXtWFQe2pWlkrsR8gXJXSo2dx0miac6CbTrsrNlBsUYj267ST_bYnG1SFOFQ1nL_59kxAVZ2bCO70omCeToLv3qhbzb9jlbO0opg7OW1FQATnlVYo6sjKOkbCaoV9mMBnuqC9-3ZFAsU2Fuu-YuKBs1V3IY-mkNJe0bEEYSdN9I62AeKgciKnxvKeHPMoDIFPqLECldyLjp9XziksDk3CxsbGDV8r8EMtdyMyKnV-ziRB4SNi0vHJiNFFGWcHOjJqCs",
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuDTvXYHmtnxtTPr3cp9eXMQWBs-X7SxdsN74Fsi8cQcGV1_jukaC8BJoVwBwmxhsdrglf513-nigeMmK0hMCHRp7n-eot_J7D0jkjA4YOCMam-xxKNfEgVayhCoN4qxlbDFBnjpe3jAh7DFq98gEaf_ED3DBoXcszF0vzAP2V5Y0Wsebo1euRgKMav_oGqk3e_KoyAMLQMlLmNAdJYwADrYgxKesL3SWrLnENA3FpztGtTMRNgFCIwObR9SLm44dnsNsPofrj67dFM",
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuBehfvhJuTMiXtWFQe2pWlkrsR8gXJXSo2dx0miac6CbTrsrNlBsUYj267ST_bYnG1SFOFQ1nL_59kxAVZ2bCO70omCeToLv3qhbzb9jlbO0opg7OW1FQATnlVYo6sjKOkbCaoV9mMBnuqC9-3ZFAsU2Fuu-YuKBs1V3IY-mkNJe0bEEYSdN9I62AeKgciKnxvKeHPMoDIFPqLECldyLjp9XziksDk3CxsbGDV8r8EMtdyMyKnV-ziRB4SNi0vHJiNFFGWcHOjJqCs"
                ],
                features=[
                    "Hand-selected natural teakwood borders for premium durability and organic aesthetic appeal.",
                    "Supplied with standard high-transmission float glass offering 90%+ optical clarity.",
                    "Includes pre-installed metal hanging brackets for portrait or landscape wall mounting.",
                    "Archival-grade acid-free composition prevents artwork yellowing or discoloration over time."
                ],
                specs={
                    "Frame Material": "Genuine Premium Teakwood",
                    "Profile Width": "0.75 inches",
                    "Mount Type": "Wall Hanging / Tabletop convertible",
                    "Hanging Hardware": "Pre-attached D-rings and wiring",
                    "Origin": "Handmade in India"
                },
                reviews=[
                    {"author": "Rahul K.", "rating": 5, "date": "14 May 2026", "text": "Stunning organic grain. It makes my gallery print stand out beautifully on the wall!"},
                    {"author": "Elena S.", "rating": 4, "date": "01 June 2026", "text": "Beautiful wood frame, sturdy mountings. Extremely clean corners."}
                ],
                style_id="oak",
                hex="#dcd1be"
            ),
            Product(
                id=2,
                name="Charcoal Walnut Frame",
                price=1650.00,
                category="Frames",
                badge=None,
                image_url="/charcoal_walnut_frame.png",
                description="Deep charcoal-stained premium walnut wood. Offers an elegant, modern dark accent that fits high-contrast photography, sketch designs, and monochrome art prints.",
                out_of_stock=False,
                mrp=2200.00,
                rating=4.90,
                review_count=86,
                images=[
                    "/charcoal_walnut_frame.png",
                    "/gallery_black_frame.png"
                ],
                features=[
                    "Stained dark walnut borders with subtle charcoal gray undertones.",
                    "Sleek and heavy profile, providing a grand museum presence for your home.",
                    "Can be displayed vertically or horizontally.",
                    "Easy-to-open flexible turn tabs on the back make swapping prints a breeze."
                ],
                specs={
                    "Frame Material": "Stained Walnut Wood",
                    "Profile Width": "0.85 inches",
                    "Mount Type": "Wall Mount Only",
                    "Finish": "Satin Wax Matte",
                    "Origin": "Made in India"
                },
                reviews=[
                    {"author": "Anya V.", "rating": 5, "date": "08 June 2026", "text": "Extremely rich dark color. Fits my prints perfectly! Heavy and premium feel."}
                ],
                style_id="black",
                hex="#2e2528"
            ),
            Product(
                id=3,
                name="Classic Oak Frame",
                price=1450.00,
                category="Frames",
                badge="Hot Seller",
                image_url="/classic_oak_frame.png",
                description="Solid light oak frame with raw matte wax coating. Ideal for minimalist interior designs, landscape photography, watercolors, and charcoal sketches.",
                out_of_stock=False,
                mrp=1950.00,
                rating=4.70,
                review_count=94,
                images=[
                    "/classic_oak_frame.png",
                    "/charcoal_walnut_frame.png"
                ],
                features=[
                    "Made from 100% genuine sustainable Northern White Oak wood.",
                    "Natural raw finish preserved with light protective organic wax coat.",
                    "Includes scratch-resistant acrylic sheet with high light transmission.",
                    "Double-sealed backing board keeps dust out completely."
                ],
                specs={
                    "Frame Material": "Genuine White Oak",
                    "Profile Width": "0.70 inches",
                    "Mount Type": "Wall / Tabletop convertible",
                    "Finish": "Raw Organic Matte",
                    "Origin": "Made in India"
                },
                reviews=[
                    {"author": "Karan G.", "rating": 5, "date": "10 May 2026", "text": "Excellent frame. It matches my scandinavian home decor perfectly. Very organic."}
                ],
                style_id="oak",
                hex="#dcd1be"
            ),
            Product(
                id=4,
                name="Modern Gold Frame",
                price=2400.00,
                category="Frames",
                badge="Trending",
                image_url="/modern_gold_frame.png",
                description="Luxury anodized golden aluminum frame. Brushed finish perfect for executive offices, certificates, achievement degrees, and modern fine art statement pieces.",
                out_of_stock=False,
                mrp=3200.00,
                rating=4.80,
                review_count=73,
                images=[
                    "/modern_gold_frame.png",
                    "/gallery_black_frame.png"
                ],
                features=[
                    "Aerospace-grade anodized aluminum alloy, lightweight yet highly durable.",
                    "Brushed metallic gold finish with polished protective clear lacquer coating.",
                    "Supplied with high-transparency tempered scratch-resistant sheet.",
                    "Sturdy corner joint hardware for perfect alignment."
                ],
                specs={
                    "Frame Material": "Anodized Aluminum Alloy",
                    "Profile Width": "0.50 inches (ultra-slim)",
                    "Mount Type": "Wall Mounting Only",
                    "Color": "Brushed Luxury Gold",
                    "Origin": "Imported"
                },
                reviews=[
                    {"author": "Megha D.", "rating": 5, "date": "29 May 2026", "text": "Perfect for framing my university degree. Looks so grand and professional on my office wall."}
                ],
                style_id="gold",
                hex="#dfba7c"
            ),
            Product(
                id=5,
                name="Minimalist White Frame",
                price=1250.00,
                category="Frames",
                badge="New Release",
                image_url="/minimalist_white_frame.png",
                description="Matte white wooden frame with smooth wrap finish. Beautifully highlights drawings, high-contrast sketching, watercolor paintings, and modern artwork.",
                out_of_stock=False,
                mrp=1600.00,
                rating=4.60,
                review_count=42,
                images=[
                    "/minimalist_white_frame.png",
                    "/classic_oak_frame.png"
                ],
                features=[
                    "Medium-density fiberwood core with premium matte white wrap coating.",
                    "Clean corners and edges with no visible joint lines.",
                    "Lightweight and safe for plasterboard or drywalls.",
                    "Includes white backing mat and dust cover sheets."
                ],
                specs={
                    "Frame Material": "Engineered Pine Wood",
                    "Profile Width": "0.75 inches",
                    "Mount Type": "Wall / Tabletop convertible",
                    "Color": "Matte Studio White",
                    "Origin": "Made in India"
                },
                reviews=[
                    {"author": "Siddharth M.", "rating": 4, "date": "12 June 2026", "text": "Extremely neat, clean finish. Excellent packaging and quick delivery."}
                ],
                style_id="white",
                hex="#ffffff"
            ),
            Product(
                id=6,
                name="Gallery Black Frame",
                price=1300.00,
                category="Frames",
                badge=None,
                image_url="/gallery_black_frame.png",
                description="Professional matte black wooden finish, perfect for high-contrast statements, gallery exhibitions, and modern black-and-white portraits.",
                out_of_stock=False,
                mrp=1750.00,
                rating=4.80,
                review_count=110,
                images=[
                    "/gallery_black_frame.png",
                    "/charcoal_walnut_frame.png"
                ],
                features=[
                    "Solid wood core with satin black protective matte coating.",
                    "Deep frame profile for a dimensional gallery shadowbox appearance.",
                    "High-impact tempered sheet glass protects prints from dust.",
                    "Premium metal suspension bracket pre-attached on the rear."
                ],
                specs={
                    "Frame Material": "Solid Pine Wood",
                    "Profile Width": "0.80 inches",
                    "Mount Type": "Wall Mount",
                    "Color": "Satin Gallery Black",
                    "Origin": "Made in India"
                },
                reviews=[
                    {"author": "Tanvi R.", "rating": 5, "date": "04 June 2026", "text": "Standard exhibition black frame. Very clean and high quality wood. Looks great in my dining room."}
                ],
                style_id="black",
                hex="#1b1b24"
            ),
            Product(
                id=7,
                name="Lustre Fine Art Photo Print",
                price=350.00,
                category="Frames",
                badge=None,
                image_url="/fine_art_print.png",
                description="Premium grade photo prints on heavy 260gsm lustre-finish photographic paper. Delivering vibrant colors, deep blacks, and a gorgeous semi-matte finish that resists fingerprints and reflections.",
                out_of_stock=False,
                mrp=500.00,
                rating=4.90,
                review_count=148,
                images=[
                    "/fine_art_print.png",
                    "/fine_art_print.png"
                ],
                features=[
                    "Printed on professional archival-grade 260gsm lustre photographic paper.",
                    "High-fidelity 12-ink printing process ensures stunning detail and color accuracy.",
                    "Ideal for landscapes, wedding portraits, and gallery-style display.",
                    "Archival inks guaranteed not to fade for 100+ years."
                ],
                specs={
                    "Paper Type": "Lustre Archival Photo Paper",
                    "Paper Weight": "260 gsm",
                    "Print Finish": "Semi-matte / Lustre",
                    "Ink Tech": "12-color archival pigment inks",
                    "Origin": "Printed in India"
                },
                reviews=[
                    {"author": "Meera P.", "rating": 5, "date": "10 June 2026", "text": "Absolutely stellar printing quality. Colors are incredibly rich and the semi-matte finish is perfect."},
                    {"author": "Aditya S.", "rating": 5, "date": "04 June 2026", "text": "Printed a few high-res landscapes. The details are razor sharp and the paper weight feels solid."}
                ],
                style_id="print",
                hex="#ffffff"
            ),
            Product(
                id=8,
                name="Elegance 9-Photo Collage Frame",
                price=2850.00,
                category="Frames",
                badge=None,
                image_url="/collage_frame.png",
                description="A premium large-profile gallery collage frame designed to group nine square family portraits in a beautiful 3x3 layout. Supplied with archival-grade precision bevel-cut matting.",
                out_of_stock=False,
                mrp=3900.00,
                rating=4.80,
                review_count=92,
                images=[
                    "/collage_frame.png",
                    "/gallery_black_frame.png"
                ],
                features=[
                    "Heavy-duty gallery black frame profile for structural durability.",
                    "Pristine white multi-aperture mat board holds 9 square photos.",
                    "Tempered anti-scratch float glass protects photos from light fading.",
                    "Supplied with heavy wire mounting kit."
                ],
                specs={
                    "Frame Material": "Satin Black Engineered Wood",
                    "Layout style": "9-Photo 3x3 Grid Matrix",
                    "Mat Board": "Archival acid-free bevel-cut matting",
                    "Photo Size": "Fits 4\" x 4\" square prints",
                    "Origin": "Imported"
                },
                reviews=[
                    {"author": "Priyanka K.", "rating": 5, "date": "02 June 2026", "text": "Best way to frame vacation memories. The matting looks so professional!"}
                ],
                style_id="black",
                hex="#1b1b24"
            ),
            Product(
                id=9,
                name="Modern Gold Floating Canvas",
                price=2200.00,
                category="Frames",
                badge=None,
                image_url="/floating_canvas.png",
                description="Modern gold metallic float-mount frame designed to give your canvas prints a beautiful border shadowbox look, suspended 0.25 inches off the frame edges.",
                out_of_stock=False,
                mrp=3000.00,
                rating=4.70,
                review_count=46,
                images=[
                    "/floating_canvas.png",
                    "/modern_gold_frame.png"
                ],
                features=[
                    "Gold anodized floating profile creates a deep shadow gap effect.",
                    "Designed specifically for stretched canvas paintings or prints.",
                    "Pre-attached tension brackets suspend canvas inside securely.",
                    "Lightweight aluminum design prevents warping."
                ],
                specs={
                    "Frame Material": "Anodized Aluminum Alloy",
                    "Finish style": "Brushed Luxury Gold",
                    "Mount style": "Internal float clamp mounts",
                    "Shadow Gap": "0.25 inches around canvas",
                    "Origin": "Made in India"
                },
                reviews=[
                    {"author": "Rahul V.", "rating": 4, "date": "12 June 2026", "text": "Modern looking. The canvas floating look is exactly like art museums."}
                ],
                style_id="gold",
                hex="#dfba7c"
            ),
            Product(
                id=10,
                name="Executive Indigo Rollerball",
                price=3500.00,
                category="Stationery",
                badge="Bestseller",
                image_url="https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
                description="Smooth flow premium rollerball pen with weighted brass body and luxury indigo finish.",
                out_of_stock=False,
                mrp=4200.00,
                rating=4.90,
                review_count=92,
                images=[
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuCl1EvgR54j_YwzfA7phtTKN04lR-bS4i1obDgD361m44Sz6oPsGI389fbBjSN8dH5PQtzrBxeoBSl5l-TaKAodUW2pAz0A7GRyhJAI-ij9s84Q7ZOZ3nN0DmrSNeUatQgYhAwRNJaGWRIZzM5qhu-0MNxHDGF9w15CMYu9gPKGgATFsT678xc3UzXjI5dkVg0mtvXJi7dnOkrngJSpG8UQZaTiWXMcfIu9hQe0kvN7o3fMqkLlr4LhyfWG3hyRigIeSAmUjuZzBjs"
                ],
                features=[
                    "Ergonomically weighted brass body for fatigue-free signature writing.",
                    "Schmidt liquid ink system for consistent skip-free flow.",
                    "Sleek indigo lacquer finish with polished chrome accents.",
                    "Presented in a premium leatherette gift box."
                ],
                specs={
                    "Material": "Lacquered Brass",
                    "Nib Size": "0.7mm Medium Rollerball",
                    "Ink Type": "German Liquid Gel Ink",
                    "Weight": "42 grams",
                    "Refill": "Standard Schmidt P8126 refill"
                },
                reviews=[
                    {"author": "Arjun K.", "rating": 5, "date": "01 June 2026", "text": "This is the best rollerball I have ever used. Weight distribution is perfect for signatures."}
                ]
            ),
            Product(
                id=11,
                name="Midnight Resin Fountain Pen",
                price=6500.00,
                category="Stationery",
                badge="Out of Stock",
                image_url="https://lh3.googleusercontent.com/aida-public/AB6AXuCl1EvgR54j_YwzfA7phtTKN04lR-bS4i1obDgD361m44Sz6oPsGI389fbBjSN8dH5PQtzrBxeoBSl5l-TaKAodUW2pAz0A7GRyhJAI-ij9s84Q7ZOZ3nN0DmrSNeUatQgYhAwRNJaGWRIZzM5qhu-0MNxHDGF9w15CMYu9gPKGgATFsT678xc3UzXjI5dkVg0mtvXJi7dnOkrngJSpG8UQZaTiWXMcfIu9hQe0kvN7o3fMqkLlr4LhyfWG3hyRigIeSAmUjuZzBjs",
                description="Polished midnight resin body with gold nib styling. A collector grade fountain pen.",
                out_of_stock=True,
                mrp=7500.00,
                rating=4.70,
                review_count=34,
                images=[
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuCl1EvgR54j_YwzfA7phtTKN04lR-bS4i1obDgD361m44Sz6oPsGI389fbBjSN8dH5PQtzrBxeoBSl5l-TaKAodUW2pAz0A7GRyhJAI-ij9s84Q7ZOZ3nN0DmrSNeUatQgYhAwRNJaGWRIZzM5qhu-0MNxHDGF9w15CMYu9gPKGgATFsT678xc3UzXjI5dkVg0mtvXJi7dnOkrngJSpG8UQZaTiWXMcfIu9hQe0kvN7o3fMqkLlr4LhyfWG3hyRigIeSAmUjuZzBjs",
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg"
                ],
                features=[
                    "Hand-polished precious resin cap and barrel.",
                    "24k gold-plated accents and customized medium steel nib.",
                    "Dual filling system (cartridge and piston converter included).",
                    "Threaded cap prevents ink dehydration."
                ],
                specs={
                    "Material": "Polished Resin & Gold Accents",
                    "Nib": "Medium Gold-Plated Steel",
                    "Filling": "Cartridge / Converter",
                    "Weight": "28 grams",
                    "Origin": "Imported"
                },
                reviews=[
                    {"author": "Rohan M.", "rating": 5, "date": "28 May 2026", "text": "Writes incredibly wet and smooth. The resin catches light beautifully."}
                ]
            ),
            Product(
                id=12,
                name="Handcrafted Leather Journal",
                price=1850.00,
                category="Stationery",
                badge="Artisanal",
                image_url="https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
                description="Hand-tailored rich brown leather cover with a vintage brass key wrap lock. Ideal for daily logging, sketches, and professional notes.",
                out_of_stock=False,
                mrp=2500.00,
                rating=4.90,
                review_count=142,
                images=[
                    "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg"
                ],
                features=[
                    "Full-grain genuine leather cover that develops a beautiful unique patina over time.",
                    "120 sheets (240 pages) of handmade, acid-free recycled cotton paper.",
                    "Includes built-in leather pen loop and secure brass key strap wrap closure.",
                    "Sturdy hand-stitched binding prevents loose pages."
                ],
                specs={
                    "Cover Material": "Genuine Full-Grain Leather",
                    "Paper Type": "125 GSM Recycled Cotton Paper",
                    "Page Layout": "Unlined / Plain",
                    "Dimensions": "8.3\" x 5.8\" (A5 Size)",
                    "Origin": "Handcrafted in Rajasthan"
                },
                reviews=[
                    {"author": "Vikram A.", "rating": 5, "date": "12 May 2026", "text": "Stunning craftsmanship. The leather smells genuine and the paper is thick enough for calligraphy."},
                    {"author": "Sophia T.", "rating": 4, "date": "01 June 2026", "text": "Beautiful vintage design. Paper texture is amazing, although ink bleeds slightly with heavy fountain pens."}
                ]
            ),
            Product(
                id=13,
                name="Vintage Brass Desk Clock",
                price=2900.00,
                category="Office & Gifts",
                badge="Popular",
                image_url="https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg",
                description="Heavy weighted retro circular desk clock forged in brushed solid brass. Features quiet sweep mechanism and pristine glass pane.",
                out_of_stock=False,
                mrp=3800.00,
                rating=4.80,
                review_count=88,
                images=[
                    "https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg"
                ],
                features=[
                    "Forged with 100% solid brass for heavy tabletop stability and vintage appeal.",
                    "Noiseless sweep quartz movement provides an absolutely silent work environment.",
                    "Minimalist cream clock face with elegant black markers and gold metal hands.",
                    "Runs on a single standard AA battery."
                ],
                specs={
                    "Body Material": "Solid Forged Brass",
                    "Movement": "Silent Sweep Quartz",
                    "Dial Window": "Flat Mineral Glass",
                    "Dimensions": "4.5\" Diameter x 2.2\" Depth",
                    "Weight": "480 grams"
                },
                reviews=[
                    {"author": "Megha S.", "rating": 5, "date": "18 May 2026", "text": "A gorgeous statement piece for my office desk. Silent and has a solid weight!"}
                ]
            ),
            Product(
                id=14,
                name="Solid Walnut Desk Organizer",
                price=1650.00,
                category="Office & Gifts",
                badge="Best Seller",
                image_url="https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg",
                description="Multi-functional desktop storage slot handcrafted from premium walnut hardwood. Features dedicated smartphone dock, pen slots, and accessory tray.",
                out_of_stock=False,
                mrp=2100.00,
                rating=4.70,
                review_count=76,
                images=[
                    "https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg"
                ],
                features=[
                    "Carved from a single piece of premium sustainable American Walnut wood.",
                    "Non-slip silicone pads on bottom protect your desk surfaces from scratches.",
                    "Includes dedicated smartphone display slot with charging cable route.",
                    "Features satin wax matte coat to highlight organic wood grain."
                ],
                specs={
                    "Material": "Solid American Walnut Wood",
                    "Finish": "Satin Wax Matte Coating",
                    "Slots": "1 Phone stand, 3 Pen holes, 1 Letter slot, 1 Tray",
                    "Dimensions": "10.2\" L x 4.0\" W x 1.8\" H",
                    "Origin": "Made in India"
                },
                reviews=[
                    {"author": "Amit P.", "rating": 5, "date": "29 May 2026", "text": "Very neat organization. Fits my iPhone 15 Pro Max perfectly. Wood grain is gorgeous."}
                ]
            ),
            Product(
                id=15,
                name="Royal Brass Wax Seal Kit",
                price=1450.00,
                category="Stationery",
                badge="Collector",
                image_url="https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg",
                description="Complete ceremonial letter sealing set containing an ornate carved brass stamp, wax beads, melting spoon, and candles in a leatherette gift box.",
                out_of_stock=False,
                mrp=1950.00,
                rating=4.90,
                review_count=54,
                images=[
                    "https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg"
                ],
                features=[
                    "Includes 1 wooden handle stamp with 3 interchangeable engraved brass dies (Tree of Life, Rose, Crown).",
                    "Comes with 2 bottles of premium wax seal beads (Deep Gold & Royal Crimson).",
                    "Supplied with solid brass melting spoon and 2 unscented tealight candles.",
                    "Neatly packaged in a vintage leatherette presentation box, perfect for gifting."
                ],
                specs={
                    "Stamp Material": "Polished Brass & Rosewood Handle",
                    "Die Designs": "Tree of Life, Rose, Royal Crown",
                    "Wax Quantity": "Approx. 120 beads per bottle",
                    "Melting Spoon": "Brass with insulated wooden handle",
                    "Box Dimensions": "7.8\" x 5.6\" x 1.6\""
                },
                reviews=[
                    {"author": "Tanvi J.", "rating": 5, "date": "08 June 2026", "text": "Absolutely spectacular. The wax melts cleanly and seals are crisp. Packaging is beautiful!"}
                ]
            )
        ]
        db.add_all(default_products)
        await db.commit()
        print("[Seed] Products seed data successfully populated.")

    # Seed Config (Banners)
    config_result = await db.execute(text("SELECT key FROM ecommerce.site_config WHERE key = 'banners'"))
    if not config_result.first():
        default_banners = [
            {
                "id": "b1",
                "title": "Premium Document Quick Print",
                "titleHtml": "Premium Document <span>Quick Print</span>",
                "desc": "High-fidelity quick prints on select quality paper weights for all your needs.",
                "badge": "Hot Offer",
                "image": "https://lh3.googleusercontent.com/aida-public/AB6AXuDTvXYHmtnxtTPr3cp9eXMQWBs-X7SxdsN74Fsi8cQcGV1_jukaC8BJoVwBwmxhsdrglf513-nigeMmK0hMCHRp7n-eot_J7D0jkjA4YOCMam-xxKNfEgVayhCoN4qxlbDFBnjpe3jAh7DFq98gEaf_ED3DBoXcszF0vzAP2V5Y0Wsebo1euRgKMav_oGqk3e_KoyAMLQMlLmNAdJYwADrYgxKesL3SWrLnENA3FpztGtTMRNgFCIwObR9SLm44dnsNsPofrj67dFM",
                "actionPath": "/quick-prints",
                "actionText": "Upload & Quick Print",
                "emoji": "📄",
                "bgClass": "s2"
            },
            {
                "id": "b2",
                "title": "Executive Stationery",
                "titleHtml": "Executive <span>Stationery</span>",
                "desc": "Elegant writing tools crafted with brass and solid resin, perfect for gifts.",
                "badge": "Best Seller",
                "image": "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
                "actionPath": "/product/2",
                "actionText": "Buy Now",
                "emoji": "✒️",
                "bgClass": "s3"
            },
            {
                "id": "b3",
                "title": "Curated RFID Subscription",
                "titleHtml": "Aura Premium <span>RFID Plans</span>",
                "desc": "Unlock free museum-grade quick prints, custom matting, and automatic loyalty benefits.",
                "badge": "Club Member",
                "image": "/logo.jpeg",
                "actionPath": "/subscriptions",
                "actionText": "Browse Plans",
                "emoji": "💎",
                "bgClass": "s4"
            }
        ]
        await db.execute(
            text("INSERT INTO ecommerce.site_config (key, value) VALUES ('banners', :v::jsonb)"),
            {"v": json.dumps(default_banners)}
        )
        await db.commit()
        print("[Seed] Default site config banners successfully populated.")

@app.on_event("startup")
async def on_startup():
    from app.config import settings as _settings
    try:
        async with engine.begin() as conn:
            if not _settings.IS_PRODUCTION:
                # Dev only: auto-create schemas and tables via SQLAlchemy models.
                # In production, schema.sql handles table creation with RLS policies.
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ecommerce;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS maintenance;"))
                await conn.run_sync(Base.metadata.create_all)
                # Ensure the pipeline_steps column exists on the orders table
                await conn.execute(text("ALTER TABLE ecommerce.orders ADD COLUMN IF NOT EXISTS pipeline_steps JSONB;"))
                # Create site_config if not exists (raw SQL table since no SQLAlchemy model is mapped)
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ecommerce.site_config (
                        key TEXT PRIMARY KEY,
                        value JSONB NOT NULL DEFAULT '{}',
                        updated_by UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """))
            else:
                # Production: schemas & tables already exist from schema.sql upload.
                # Just verify the connection is alive.
                await conn.execute(text("SELECT 1;"))

        async with SessionLocal() as session:
            await seed_database(session)

        # Start keep-alive daemon loop
        asyncio.create_task(keep_alive_loop())
    except Exception as e:
        print(f"[Startup Error] Failed to initialize database: {e}")

@app.get("/api/health")
async def health_check():
    """Manual health check endpoint that pings the database (Rule 5.1/2)"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT NOW();"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database_error": str(e)}
