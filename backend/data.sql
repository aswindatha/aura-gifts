-- data.sql – sample data for aura‑prints
-- This file resides alongside schema.sql and can be loaded with:
--   psql -f data.sql -U postgres -d aura_prints

-- Clean existing data and reset auto-incrementing IDs to make the script re-runnable
TRUNCATE TABLE ecommerce.users RESTART IDENTITY CASCADE;
TRUNCATE TABLE ecommerce.products RESTART IDENTITY CASCADE;
TRUNCATE TABLE maintenance.machinery RESTART IDENTITY CASCADE;
TRUNCATE TABLE ecommerce.otps RESTART IDENTITY CASCADE;
TRUNCATE TABLE ecommerce.media_files RESTART IDENTITY CASCADE;
TRUNCATE TABLE ecommerce.payments RESTART IDENTITY CASCADE;
TRUNCATE TABLE ecommerce.webhook_events RESTART IDENTITY CASCADE;
TRUNCATE TABLE ecommerce.refunds RESTART IDENTITY CASCADE;

-- 1. Users (admin, employee, shopkeeper, customer)
INSERT INTO ecommerce.users (id, name, email, phone, password_hash, role, points, subscription_tier, address, photo_url, id_proof_type, id_proof_number, email_verified)
VALUES
    ('c0000000-0000-0000-0000-000000000001', 'Site Admin', 'admin@auraprints.com', NULL,            '$2b$12$Lql1vCWG8bJ2UUgIzrZH6u.K1adpKUbWkW43EjJxTfpIofAA4VTSq', 1, 0, 0, 'Admin HQ, Creative City', NULL, NULL, NULL, TRUE),
    ('c0000000-0000-0000-0000-000000000002', 'Dave Operator', 'dave@auraprints.com', NULL,          '$2b$12$ix0FsyNJFMDR.PFvBrtU9OfH2QblZO3Ib5epSdYFQO/1IOvH6srrS', 2, 0, 0, 'Staff Room, Shop Floor', NULL, NULL, NULL, TRUE),
    ('c0000000-0000-0000-0000-000000000006', 'Deva', 'deva@auraprints.com', NULL,          '$2b$12$examplehashplaceholder', 2, 0, 0, 'Employee Desk, Shop Floor', NULL, NULL, NULL, TRUE),
    ('c0000000-0000-0000-0000-000000000003', 'Pushpavel', 'pushpa@auraprints.com', NULL,             '$2b$12$gD84lRPpU1MR1oU5CbV3o.1/X9S0doRgMiXCd0ptSF2Oly06C7qci', 3, 0, 0, 'Billing Desk, Shop Floor', NULL, NULL, NULL, TRUE),
    ('c0000000-0000-0000-0000-000000000004', 'Jane Doe', 'customer@auraprints.com', '9876543210',    '$2b$12$uxUUjBVqtXXH8UJTmPD7ouKPLX.u5maUASfzMvhqpSZ7JZ5t2p8Mm', 4, 450, 2, '123 Artisan Way, Apt 4B, Mumbai, MH - 400001', NULL, NULL, NULL, TRUE),
    ('c0000000-0000-0000-0000-000000000005', 'Alex Patel', 'student@auraprints.com', '9876543211',    '$2b$12$QV1q7efTpKOXcdVFb/dqH.GtSDxsZIIvZqYbPOOYncaINJmPEhFOq', 4, 150, 1, '456 Academy Road, Pune, MH - 411001', NULL, NULL, NULL, TRUE);

-- Capture the generated UUIDs for later reference (optional – you can replace with concrete UUIDs if needed)
-- For illustration purposes we will use sub‑queries to fetch the IDs by email.

-- 2. Products (a subset of the seed data)
INSERT INTO ecommerce.products (name, description, price, category, badge, image_url, out_of_stock, mrp, rating, review_count, images, features, specs, reviews, style_id, hex)
VALUES
    (
        'Teakwood Gallery Frame',
        'Handcrafted genuine teakwood with rich natural grain patterns. A warm, timeless classic designed to elevate your photographic prints, sketches, and professional documents.',
        1250.00,
        'Frames',
        'Featured',
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame1.jpeg',
        FALSE,
        1800.00,
        4.80,
        124,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame1.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame2.jpeg"
]'::jsonb,
        '[
            "Hand-selected natural teakwood borders for premium durability and organic aesthetic appeal.",
            "Supplied with standard high-transmission float glass offering 90%+ optical clarity.",
            "Includes pre-installed metal hanging brackets for portrait or landscape wall mounting.",
            "Archival-grade acid-free composition prevents artwork yellowing or discoloration over time."
        ]'::jsonb,
        '{
            "Frame Material": "Genuine Premium Teakwood",
            "Profile Width": "0.75 inches",
            "Mount Type": "Wall Hanging / Tabletop convertible",
            "Hanging Hardware": "Pre-attached D-rings and wiring",
            "Origin": "Handmade in India"
        }'::jsonb,
        '[
            {"author": "Rahul K.", "rating": 5, "date": "14 May 2026", "text": "Stunning organic grain. It makes my gallery print stand out beautifully on the wall!"},
            {"author": "Elena S.", "rating": 4, "date": "01 June 2026", "text": "Beautiful wood frame, sturdy mountings. Extremely clean corners."}
        ]'::jsonb,
        'oak',
        '#dcd1be'
    ),
    (
        'Charcoal Walnut Frame',
        'Deep charcoal-stained premium walnut wood. Offers an elegant, modern dark accent that fits high-contrast photography, sketch designs, and monochrome art prints.',
        1650.00,
        'Frames',
        NULL,
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame2.jpeg',
        FALSE,
        2200.00,
        4.90,
        86,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame2.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame3.jpeg"
]'::jsonb,
        '[
            "Stained dark walnut borders with subtle charcoal gray undertones.",
            "Sleek and heavy profile, providing a grand museum presence for your home.",
            "Can be displayed vertically or horizontally.",
            "Easy-to-open flexible turn tabs on the back make swapping prints a breeze."
        ]'::jsonb,
        '{
            "Frame Material": "Stained Walnut Wood",
            "Profile Width": "0.85 inches",
            "Mount Type": "Wall Mount Only",
            "Finish": "Satin Wax Matte",
            "Origin": "Made in India"
        }'::jsonb,
        '[
            {"author": "Anya V.", "rating": 5, "date": "08 June 2026", "text": "Extremely rich dark color. Fits my prints perfectly! Heavy and premium feel."}
        ]'::jsonb,
        'black',
        '#2e2528'
    ),
    (
        'Classic Oak Frame',
        'Solid light oak frame with raw matte wax coating. Ideal for minimalist interior designs, landscape photography, watercolors, and charcoal sketches.',
        1450.00,
        'Frames',
        'Hot Seller',
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame3.jpeg',
        FALSE,
        1950.00,
        4.70,
        94,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame3.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame4.jpeg"
]'::jsonb,
        '[
            "Made from 100% genuine sustainable Northern White Oak wood.",
            "Natural raw finish preserved with light protective organic wax coat.",
            "Includes scratch-resistant acrylic sheet with high light transmission.",
            "Double-sealed backing board keeps dust out completely."
        ]'::jsonb,
        '{
            "Frame Material": "Genuine White Oak",
            "Profile Width": "0.70 inches",
            "Mount Type": "Wall / Tabletop convertible",
            "Finish": "Raw Organic Matte",
            "Origin": "Made in India"
        }'::jsonb,
        '[
            {"author": "Karan G.", "rating": 5, "date": "10 May 2026", "text": "Excellent frame. It matches my scandinavian home decor perfectly. Very organic."}
        ]'::jsonb,
        'oak',
        '#dcd1be'
    ),
    (
        'Modern Gold Frame',
        'Luxury anodized golden aluminum frame. Brushed finish perfect for executive offices, certificates, achievement degrees, and modern fine art statement pieces.',
        2400.00,
        'Frames',
        'Trending',
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame4.jpeg',
        FALSE,
        3200.00,
        4.80,
        73,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame4.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame5.jpeg"
]'::jsonb,
        '[
            "Aerospace-grade anodized aluminum alloy, lightweight yet highly durable.",
            "Brushed metallic gold finish with polished protective clear lacquer coating.",
            "Supplied with high-transparency tempered scratch-resistant sheet.",
            "Sturdy corner joint hardware for perfect alignment."
        ]'::jsonb,
        '{
            "Frame Material": "Anodized Aluminum Alloy",
            "Profile Width": "0.50 inches (ultra-slim)",
            "Mount Type": "Wall Mounting Only",
            "Color": "Brushed Luxury Gold",
            "Origin": "Imported"
        }'::jsonb,
        '[
            {"author": "Megha D.", "rating": 5, "date": "29 May 2026", "text": "Perfect for framing my university degree. Looks so grand and professional on my office wall."}
        ]'::jsonb,
        'gold',
        '#dfba7c'
    ),
    (
        'Minimalist White Frame',
        'Matte white wooden frame with smooth wrap finish. Beautifully highlights drawings, high-contrast sketching, watercolor paintings, and modern artwork.',
        1250.00,
        'Frames',
        'New Release',
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame5.jpeg',
        FALSE,
        1600.00,
        4.60,
        42,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame5.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame6.jpeg"
]'::jsonb,
        '[
            "Medium-density fiberwood core with premium matte white wrap coating.",
            "Clean corners and edges with no visible joint lines.",
            "Lightweight and safe for plasterboard or drywalls.",
            "Includes white backing mat and dust cover sheets."
        ]'::jsonb,
        '{
            "Frame Material": "Engineered Pine Wood",
            "Profile Width": "0.75 inches",
            "Mount Type": "Wall / Tabletop convertible",
            "Color": "Matte Studio White",
            "Origin": "Made in India"
        }'::jsonb,
        '[
            {"author": "Siddharth M.", "rating": 4, "date": "12 June 2026", "text": "Matte studio white frame looks extremely neat and elegant. Clean corners."}
        ]'::jsonb,
        'white',
        '#ffffff'
    ),
    (
        'Gallery Black Frame',
        'Professional matte black wooden finish, perfect for high-contrast statements, gallery exhibitions, and modern black-and-white portraits.',
        1300.00,
        'Frames',
        NULL,
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame6.jpeg',
        FALSE,
        1750.00,
        4.80,
        110,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame6.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame7.jpeg"
]'::jsonb,
        '[
            "Solid wood core with satin black protective matte coating.",
            "Deep frame profile for a dimensional gallery shadowbox appearance.",
            "High-impact tempered sheet glass protects prints from dust.",
            "Premium metal suspension bracket pre-attached on the rear."
        ]'::jsonb,
        '{
            "Frame Material": "Solid Pine Wood",
            "Profile Width": "0.80 inches",
            "Mount Type": "Wall Mount",
            "Color": "Satin Gallery Black",
            "Origin": "Made in India"
        }'::jsonb,
        '[
            {"author": "Tanvi R.", "rating": 5, "date": "04 June 2026", "text": "Standard exhibition black frame. Very clean and high quality wood. Looks great in my dining room."}
        ]'::jsonb,
        'black',
        '#1b1b24'
    ),
    (
        'Lustre Fine Art Photo Print',
        'Premium grade photo prints on heavy 260gsm lustre-finish photographic paper. Delivering vibrant colors, deep blacks, and a gorgeous semi-matte finish that resists fingerprints and reflections.',
        350.00,
        'Frames',
        NULL,
        'file:///C:/Users/aswin/Music/AURA/images/frame/frame7.jpeg',
        FALSE,
        500.00,
        4.90,
        148,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame7.jpeg"
]'::jsonb,
        '[
            "Printed on professional archival-grade 260gsm lustre photographic paper.",
            "High-fidelity 12-ink printing process ensures stunning detail and color accuracy.",
            "Ideal for landscapes, wedding portraits, and gallery-style display.",
            "Archival inks guaranteed not to fade for 100+ years."
        ]'::jsonb,
        '{
            "Paper Type": "Lustre Archival Photo Paper",
            "Paper Weight": "260 gsm",
            "Print Finish": "Semi-matte / Lustre",
            "Ink Tech": "12-color archival pigment inks",
            "Origin": "Printed in India"
        }'::jsonb,
        '[
            {"author": "Meera P.", "rating": 5, "date": "10 June 2026", "text": "Absolutely stellar printing quality. Colors are incredibly rich and the semi-matte finish is perfect."},
            {"author": "Aditya S.", "rating": 5, "date": "04 June 2026", "text": "Printed a few high-res landscapes. The details are razor sharp and the paper weight feels solid."}
        ]'::jsonb,
        'print',
        '#ffffff'
    ),
    (
        'Elegance 9-Photo Collage Frame',
        'A premium large-profile gallery collage frame designed to group nine square family portraits in a beautiful 3x3 layout. Supplied with archival-grade precision bevel-cut matting.',
        2850.00,
        'Frames',
        NULL,
        'file:///C:/Users/aswin/Music/AURA/images/frame/farme11.jpeg',
        FALSE,
        3900.00,
        4.80,
        92,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/frame/farme11.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame12.jpeg",
    "file:///C:/Users/aswin/Music/AURA/images/frame/frame13.jpeg"
]'::jsonb,
        '[
            "Heavy-duty gallery black frame profile for structural durability.",
            "Pristine white multi-aperture mat board holds 9 square photos.",
            "Tempered anti-scratch float glass protects photos from light fading.",
            "Supplied with heavy wire mounting kit."
        ]'::jsonb,
        '{
            "Frame Material": "Satin Black Engineered Wood",
            "Layout style": "9-Photo 3x3 Grid Matrix",
            "Mat Board": "Archival acid-free bevel-cut matting",
            "Photo Size": "Fits 4\" x 4\" square prints",
            "Origin": "Imported"
        }'::jsonb,
        '[
            {"author": "Priyanka K.", "rating": 5, "date": "02 June 2026", "text": "Best way to frame vacation memories. The matting looks so professional!"}
        ]'::jsonb,
        'black',
        '#1b1b24'
    ),
    (
        'Modern Gold Floating Canvas',
        'Modern gold metallic float-mount frame designed to give your canvas prints a beautiful border shadowbox look, suspended 0.25 inches off the frame edges.',
        2200.00,
        'Frames',
        NULL,
        'file:///C:/Users/aswin/Music/AURA/images/gifts/canvas.jpeg',
        FALSE,
        3000.00,
        4.70,
        46,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/canvas.jpeg"
]'::jsonb,
        '[
            "Gold anodized floating profile creates a deep shadow gap effect.",
            "Designed specifically for stretched canvas paintings or prints.",
            "Pre-attached tension brackets suspend canvas inside securely.",
            "Lightweight aluminum design prevents warping."
        ]'::jsonb,
        '{
            "Frame Material": "Anodized Aluminum Alloy",
            "Finish style": "Brushed Luxury Gold",
            "Mount style": "Internal float clamp mounts",
            "Shadow Gap": "0.25 inches around canvas",
            "Origin": "Made in India"
        }'::jsonb,
        '[
            {"author": "Rahul V.", "rating": 4, "date": "12 June 2026", "text": "Modern looking. The canvas floating look is exactly like art museums."}
        ]'::jsonb,
        'gold',
        '#dfba7c'
    ),
    (
        'Executive Indigo Rollerball',
        'Smooth flow premium rollerball pen with weighted brass body and luxury indigo finish.',
        3500.00,
        'Stationery',
        'Bestseller',
        'file:///C:/Users/aswin/Music/AURA/images/gifts/pens.jpeg',
        FALSE,
        4200.00,
        4.90,
        92,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/pens.jpeg"
]'::jsonb,
        '[
            "Ergonomically weighted brass body for fatigue-free signature writing.",
            "Schmidt liquid ink system for consistent skip-free flow.",
            "Sleek indigo lacquer finish with polished chrome accents.",
            "Presented in a premium leatherette gift box."
        ]'::jsonb,
        '{
            "Material": "Lacquered Brass",
            "Nib Size": "0.7mm Medium Rollerball",
            "Ink Type": "German Liquid Gel Ink",
            "Weight": "42 grams",
            "Refill": "Standard Schmidt P8126 refill"
        }'::jsonb,
        '[
            {"author": "Arjun K.", "rating": 5, "date": "01 June 2026", "text": "This is the best rollerball I have ever used. Weight distribution is perfect for signatures."}
        ]'::jsonb,
        NULL,
        NULL
    ),
    (
        'Midnight Resin Fountain Pen',
        'Polished midnight resin body with gold nib styling. A collector grade fountain pen.',
        6500.00,
        'Stationery',
        'Out of Stock',
        'file:///C:/Users/aswin/Music/AURA/images/gifts/pens.jpeg',
        TRUE,
        7500.00,
        4.70,
        34,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/pens.jpeg"
]'::jsonb,
        '[
            "Hand-polished precious resin cap and barrel.",
            "24k gold-plated accents and customized medium steel nib.",
            "Dual filling system (cartridge and piston converter included).",
            "Threaded cap prevents ink dehydration."
        ]'::jsonb,
        '{
            "Material": "Polished Resin & Gold Accents",
            "Nib": "Medium Gold-Plated Steel",
            "Filling": "Cartridge / Converter",
            "Weight": "28 grams",
            "Origin": "Imported"
        }'::jsonb,
        '[
            {"author": "Rohan M.", "rating": 5, "date": "28 May 2026", "text": "Writes incredibly wet and smooth. The resin catches light beautifully."}
        ]'::jsonb,
        NULL,
        NULL
    ),
    (
        'Handcrafted Leather Journal',
        'Hand-tailored rich brown leather cover with a vintage brass key wrap lock. Ideal for daily logging, sketches, and professional notes.',
        1850.00,
        'Stationery',
        'Artisanal',
        'file:///C:/Users/aswin/Music/AURA/images/gifts/lanyard.jpeg',
        FALSE,
        2500.00,
        4.90,
        142,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/lanyard.jpeg"
]'::jsonb,
        '[
            "Full-grain genuine leather cover that develops a beautiful unique patina over time.",
            "120 sheets (240 pages) of handmade, acid-free recycled cotton paper.",
            "Includes built-in leather pen loop and secure brass key strap wrap closure.",
            "Sturdy hand-stitched binding prevents loose pages."
        ]'::jsonb,
        '{
            "Cover Material": "Genuine Full-Grain Leather",
            "Paper Type": "125 GSM Recycled Cotton Paper",
            "Page Layout": "Unlined / Plain",
            "Dimensions": "8.3\" x 5.8\" (A5 Size)",
            "Origin": "Handcrafted in Rajasthan"
        }'::jsonb,
        '[
            {"author": "Vikram A.", "rating": 5, "date": "12 May 2026", "text": "Stunning craftsmanship. The leather smells genuine and the paper is thick enough for calligraphy."},
            {"author": "Sophia T.", "rating": 4, "date": "01 June 2026", "text": "Beautiful vintage design. Paper texture is amazing, although ink bleeds slightly with heavy fountain pens."}
        ]'::jsonb,
        NULL,
        NULL
    ),
    (
        'Vintage Brass Desk Clock',
        'Heavy weighted retro circular desk clock forged in brushed solid brass. Features quiet sweep mechanism and pristine glass pane.',
        2900.00,
        'Office & Gifts',
        'Popular',
        'file:///C:/Users/aswin/Music/AURA/images/gifts/hat.jpeg',
        FALSE,
        3800.00,
        4.80,
        88,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/hat.jpeg"
]'::jsonb,
        '[
            "Forged with 100% solid brass for heavy tabletop stability and vintage appeal.",
            "Noiseless sweep quartz movement provides an absolutely silent work environment.",
            "Minimalist cream clock face with elegant black markers and gold metal hands.",
            "Runs on a single standard AA battery."
        ]'::jsonb,
        '{
            "Body Material": "Solid Forged Brass",
            "Movement": "Silent Sweep Quartz",
            "Dial Window": "Flat Mineral Glass",
            "Dimensions": "4.5\" Diameter x 2.2\" Depth",
            "Weight": "480 grams"
        }'::jsonb,
        '[
            {"author": "Megha S.", "rating": 5, "date": "18 May 2026", "text": "A gorgeous statement piece for my office desk. Silent and has a solid weight!"}
        ]'::jsonb,
        NULL,
        NULL
    ),
    (
        'Solid Walnut Desk Organizer',
        'Multi-functional desktop storage slot handcrafted from premium walnut hardwood. Features dedicated smartphone dock, pen slots, and accessory tray.',
        1650.00,
        'Office & Gifts',
        'Best Seller',
        'file:///C:/Users/aswin/Music/AURA/images/gifts/socks.jpeg',
        FALSE,
        2100.00,
        4.70,
        76,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/socks.jpeg"
]'::jsonb,
        '[
            "Carved from a single piece of premium sustainable American Walnut wood.",
            "Non-slip silicone pads on bottom protect your desk surfaces from scratches.",
            "Includes dedicated smartphone display slot with charging cable route.",
            "Features satin wax matte coat to highlight organic wood grain."
        ]'::jsonb,
        '{
            "Material": "Solid American Walnut Wood",
            "Finish": "Satin Wax Matte Coating",
            "Slots": "1 Phone stand, 3 Pen holes, 1 Letter slot, 1 Tray",
            "Dimensions": "10.2\" L x 4.0\" W x 1.8\" H",
            "Origin": "Made in India"
        }'::jsonb,
        '[
            {"author": "Amit P.", "rating": 5, "date": "29 May 2026", "text": "Very neat organization. Fits my iPhone 15 Pro Max perfectly. Wood grain is gorgeous."}
        ]'::jsonb,
        NULL,
        NULL
    ),
    (
        'Royal Brass Wax Seal Kit',
        'Complete ceremonial letter sealing set containing an ornate carved brass stamp, wax beads, melting spoon, and candles in a leatherette gift box.',
        1450.00,
        'Stationery',
        'Collector',
        'file:///C:/Users/aswin/Music/AURA/images/gifts/plush.jpeg',
        FALSE,
        1950.00,
        4.90,
        54,
        '[
    "file:///C:/Users/aswin/Music/AURA/images/gifts/plush.jpeg"
]'::jsonb,
        '[
            "Includes 1 wooden handle stamp with 3 interchangeable engraved brass dies (Tree of Life, Rose, Crown).",
            "Comes with 2 bottles of premium wax seal beads (Deep Gold & Royal Crimson).",
            "Supplied with solid brass melting spoon and 2 unscented tealight candles.",
            "Neatly packaged in a vintage leatherette presentation box, perfect for gifting."
        ]'::jsonb,
        '{
            "Stamp Material": "Polished Brass & Rosewood Handle",
            "Die Designs": "Tree of Life, Rose, Royal Crown",
            "Wax Quantity": "Approx. 120 beads per bottle",
            "Melting Spoon": "Brass with insulated wooden handle",
            "Box Dimensions": "7.8\" x 5.6\" x 1.6\""
        }'::jsonb,
        '[
            {"author": "Tanvi J.", "rating": 5, "date": "08 June 2026", "text": "Absolutely spectacular. The wax melts cleanly and seals are crisp. Packaging is beautiful!"}
        ]'::jsonb,
        NULL,
        NULL
    );
-- 3. Orders & Order Items (linked to Jane Customer)
-- Order 1: Awaiting Payment Verification, Total: ₹1,350
INSERT INTO ecommerce.orders (
    id, user_id, total_amount, status, delivery_type, delivery_cost,
    payment_screenshot_url, full_name, street_address, city, pin_code, phone_number, created_at
) VALUES (
    'de305d54-75b4-431b-adb2-eb6b9e546013',
    'c0000000-0000-0000-0000-000000000004',
    1350.00,
    1,
    'Standard Delivery',
    150.00,
    'https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg',
    'Jane Customer',
    '123 Artisan Way, Apt 4B',
    'Mumbai',
    '400001',
    '+91 98765 43210',
    CURRENT_TIMESTAMP - INTERVAL '7 days'
);

INSERT INTO ecommerce.order_items (
    id, order_id, product_name, subtitle, price, quantity, uploaded_file_url
) VALUES
    ('de305d54-75b4-431b-adb2-eb6b9e546023', 'de305d54-75b4-431b-adb2-eb6b9e546013', 'Seasonal Wood Frame', 'Premium Hand-crafted Wood Frame', 1250.00, 1, NULL),
    ('de305d54-75b4-431b-adb2-eb6b9e546025', 'de305d54-75b4-431b-adb2-eb6b9e546013', 'A4 Documents Color', 'Color Printing', 10.00, 10, NULL);

-- Order 2: Delivered, Total: ₹3,500
INSERT INTO ecommerce.orders (
    id, user_id, total_amount, status, delivery_type, delivery_cost,
    payment_screenshot_url, full_name, street_address, city, pin_code, phone_number, created_at
) VALUES (
    'de305d54-75b4-431b-adb2-eb6b9e546014',
    'c0000000-0000-0000-0000-000000000004',
    3500.00,
    4,
    'In-store Pickup',
    0.00,
    'https://www.gstatic.com/labs-code/stitch/stitch-placeholder-300x300.svg',
    'Jane Customer',
    '123 Artisan Way, Apt 4B',
    'Mumbai',
    '400001',
    '+91 98765 43210',
    CURRENT_TIMESTAMP - INTERVAL '19 days'
);

INSERT INTO ecommerce.order_items (
    id, order_id, product_name, subtitle, price, quantity, uploaded_file_url
) VALUES
    ('de305d54-75b4-431b-adb2-eb6b9e546024', 'de305d54-75b4-431b-adb2-eb6b9e546014', 'Executive Indigo Rollerball', 'Stationery • High Quality', 3500.00, 1, NULL);

-- Chat messages for Order 1
INSERT INTO ecommerce.chat_messages (
    id, order_id, sender_user_id, sender_role, text, image_url, created_at
) VALUES
    (
        'de305d54-75b4-431b-adb2-eb6b9e546031',
        'de305d54-75b4-431b-adb2-eb6b9e546013',
        'c0000000-0000-0000-0000-000000000003',
        3,
        'Hi Jane, we have received your order details and payment submission! We are verifying the transaction. Please upload any layout preferences or image references here.',
        NULL,
        CURRENT_TIMESTAMP - INTERVAL '15 minutes'
    ),
    (
        'de305d54-75b4-431b-adb2-eb6b9e546032',
        'de305d54-75b4-431b-adb2-eb6b9e546013',
        'c0000000-0000-0000-0000-000000000004',
        4,
        'Thanks! I want to make sure the border has a matte finish. I will upload a photo showing what I mean.',
        NULL,
        CURRENT_TIMESTAMP - INTERVAL '10 minutes'
    );

-- 4. Maintenance – Machinery
INSERT INTO maintenance.machinery (name, model_number, status, last_service_date)
VALUES
    ('Laser Cutter', 'LC-2000', 1, CURRENT_DATE - INTERVAL '30 days'),
    ('3D Printer',   'PR-500', 2, CURRENT_DATE - INTERVAL '90 days');

-- 5. Maintenance – Repair Logs (related to machinery above)
WITH mach AS (
    SELECT id FROM maintenance.machinery WHERE name = '3D Printer'
)
INSERT INTO maintenance.repair_logs (
    machinery_id, issue_description, action_taken, technician_name, cost, document_url
) SELECT
    (SELECT id FROM mach), 'Nozzle clog', 'Replaced nozzle and cleaned extrusion path', 'Tech Raj', 150.00, 'https://example.com/repair_log_3dprinter.pdf';

-- 6. OTPs – Example verified OTP record for Jane Customer
-- NOTE: otp_code stores an HMAC-SHA256 hex digest, NOT the raw 6-digit code.
-- The hash below corresponds to OTP "123456" signed with the secret "test-secret".
-- In production, the backend generates this hash automatically via routers/auth.py.
-- To generate a valid hash for testing:
--   python3 -c "import hmac, hashlib; print(hmac.new(b'otp-hmac-secret-hfbvqihrv-rqeg4rv-reqf34fveqb-h45bwteqg5', b'123456', hashlib.sha256).hexdigest())"
INSERT INTO ecommerce.otps (email, otp_code, expires_at, last_sent_at, attempts, verified, resend_count)
VALUES (
    'customer@auraprints.com',
    'a8c9e5b2f1d3a4b6c7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0',  -- placeholder hash
    NOW() + INTERVAL '10 minutes',
    NOW(),
    0,
    FALSE,
    1
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Site Config – Banners & Subscription Plans
-- These rows feed /api/config/banners and /api/config/subscription_plans.
-- Without them every GET returns 404, which triggers the admin toast loop.
-- ON CONFLICT DO NOTHING makes this re-runnable without overwriting edits.
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO ecommerce.site_config (key, value, updated_by, updated_at)
VALUES
(
  'banners',
  '[
    {
      "id": "b1",
      "title": "Premium Frames",
      "titleHtml": "Premium <span>Frames</span>",
      "desc": "Elevate your space with handcrafted teakwood, walnut, and gold frames.",
      "badge": "New Collection",
      "image": "",
      "actionText": "Shop Frames",
      "actionPath": "/shop",
      "emoji": "\ud83d\uddbc\ufe0f",
      "bgClass": "s1"
    },
    {
      "id": "b2",
      "title": "Fine Art Prints",
      "titleHtml": "Fine Art <span>Prints</span>",
      "desc": "Professional 260 gsm lustre prints with archival pigment inks. Colours that last 100+ years.",
      "badge": "Bestseller",
      "image": "",
      "actionText": "Order Prints",
      "actionPath": "/shop",
      "emoji": "\ud83c\udfa8",
      "bgClass": "s2"
    },
    {
      "id": "b3",
      "title": "Gifting Essentials",
      "titleHtml": "Gifting <span>Essentials</span>",
      "desc": "From brass desk clocks to leather journals — gifts that make lasting impressions.",
      "badge": "Hot Picks",
      "image": "",
      "actionText": "Explore Gifts",
      "actionPath": "/shop",
      "emoji": "\ud83c\udf81",
      "bgClass": "s3"
    }
  ]'::jsonb,
  (SELECT id FROM ecommerce.users WHERE role = 1 LIMIT 1),
  NOW()
),
(
  'subscription_plans',
  '[
    {
      "id": "plan_student",
      "tier": "Student",
      "badge": "Starter",
      "price": 199,
      "duration": "per month",
      "color": "#4648d4",
      "tierCode": 1,
      "features": [
        "5% discount on all orders",
        "Priority email support",
        "Access to student exclusive designs",
        "Early access to new products"
      ]
    },
    {
      "id": "plan_premium",
      "tier": "Premium",
      "badge": "Most Popular",
      "price": 499,
      "duration": "per month",
      "color": "#7c3aed",
      "tierCode": 2,
      "features": [
        "15% discount on all orders",
        "Free standard delivery on every order",
        "Priority customer support (chat + email)",
        "Exclusive premium design collection",
        "Early access to new arrivals"
      ]
    },
    {
      "id": "plan_enterprise",
      "tier": "Enterprise",
      "badge": "Best Value",
      "price": 1299,
      "duration": "per month",
      "color": "#d97706",
      "tierCode": 3,
      "features": [
        "25% discount on bulk orders",
        "Dedicated account manager",
        "Custom branding on prints",
        "Free express delivery on all orders",
        "White-label invoicing support",
        "API access for order automation"
      ]
    }
  ]'::jsonb,
  (SELECT id FROM ecommerce.users WHERE role = 1 LIMIT 1),
  NOW()
)
ON CONFLICT (key) DO NOTHING;

