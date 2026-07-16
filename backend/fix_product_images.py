"""Fix product image_url and images columns that contain broken file:/// paths.

The database was manually populated with local filesystem paths like
    file:///C:/Users/aswin/Music/AURA/images/frame/frame1.jpeg
which browsers refuse to load from an http:// origin.  This script
replaces them with proper URLs that resolve to the Vite-served
frontend/public assets (e.g. /classic_oak_frame.png) or the original
Google CDN URLs used in the seed data.
"""
import asyncio
from sqlalchemy import text
from app.database import engine


# id -> (image_url, [images])
CORRECT_IMAGES = {
    1: ("/classic_oak_frame.png", ["/classic_oak_frame.png", "/charcoal_walnut_frame.png"]),
    2: ("/charcoal_walnut_frame.png", ["/charcoal_walnut_frame.png", "/gallery_black_frame.png"]),
    3: ("/classic_oak_frame.png", ["/classic_oak_frame.png", "/charcoal_walnut_frame.png"]),
    4: ("/modern_gold_frame.png", ["/modern_gold_frame.png", "/gallery_black_frame.png"]),
    5: ("/minimalist_white_frame.png", ["/minimalist_white_frame.png", "/classic_oak_frame.png"]),
    6: ("/gallery_black_frame.png", ["/gallery_black_frame.png", "/charcoal_walnut_frame.png"]),
    7: ("/fine_art_print.png", ["/fine_art_print.png", "/fine_art_print.png"]),
    8: ("/collage_frame.png", ["/collage_frame.png", "/gallery_black_frame.png"]),
    9: ("/floating_canvas.png", ["/floating_canvas.png", "/modern_gold_frame.png"]),
    10: (
        "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
        [
            "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
            "https://lh3.googleusercontent.com/aida-public/AB6AXuCl1EvgR54j_YwzfA7phtTKN04lR-bS4i1obDgD361m44Sz6oPsGI389fbBjSN8dH5PQtzrBxeoBSl5l-TaKAodUW2pAz0A7GRyhJAI-ij9s84Q7ZOZ3nN0DmrSNeUatQgYhAwRNJaGWRIZzM5qhu-0MNxHDGF9w15CMYu9gPKGgATFsT678xc3UzXjI5dkVg0mtvXJi7dnOkrngJSpG8UQZaTiWXMcfIu9hQe0kvN7o3fMqkLlr4LhyfWG3hyRigIeSAmUjuZzBjs",
        ],
    ),
    11: (
        "https://lh3.googleusercontent.com/aida-public/AB6AXuCl1EvgR54j_YwzfA7phtTKN04lR-bS4i1obDgD361m44Sz6oPsGI389fbBjSN8dH5PQtzrBxeoBSl5l-TaKAodUW2pAz0A7GRyhJAI-ij9s84Q7ZOZ3nN0DmrSNeUatQgYhAwRNJaGWRIZzM5qhu-0MNxHDGF9w15CMYu9gPKGgATFsT678xc3UzXjI5dkVg0mtvXJi7dnOkrngJSpG8UQZaTiWXMcfIu9hQe0kvN7o3fMqkLlr4LhyfWG3hyRigIeSAmUjuZzBjs",
        [
            "https://lh3.googleusercontent.com/aida-public/AB6AXuCl1EvgR54j_YwzfA7phtTKN04lR-bS4i1obDgD361m44Sz6oPsGI389fbBjSN8dH5PQtzrBxeoBSl5l-TaKAodUW2pAz0A7GRyhJAI-ij9s84Q7ZOZ3nN0DmrSNeUatQgYhAwRNJaGWRIZzM5qhu-0MNxHDGF9w15CMYu9gPKGgATFsT678xc3UzXjI5dkVg0mtvXJi7dnOkrngJSpG8UQZaTiWXMcfIu9hQe0kvN7o3fMqkLlr4LhyfWG3hyRigIeSAmUjuZzBjs",
            "https://lh3.googleusercontent.com/aida-public/AB6AXuAldfb-X5l64uc9iwFf5wEuOofZsHwlLQXar37AnwoNcYDufiBkYYSHa8MyQheWhiCnr5Ql2z2y-mVSWPp-Wuav4JbSi2foa8NZ45wRF0j1EUN0llWudxN1w-ADMgMv4v5PkZX7aw2rxCMppK5SpVbNRqNjGE0rCr89050F4xL-2X9_d4f2Gt2pQUcavHoisSr6-iVyGv1kq3F_9RS6PAfKve5wYcB2JxcXaLrE2V7YD4zwKJmWA_H93wIUn-t_jkyymM3i_5YxLPg",
        ],
    ),
    12: ("/leather_journal.png", ["/leather_journal.png"]),
    13: ("/brass_clock.png", ["/brass_clock.png"]),
    14: ("/walnut_organizer.png", ["/walnut_organizer.png"]),
    15: ("/wax_seal_kit.png", ["/wax_seal_kit.png"]),
}


async def fix():
    async with engine.begin() as conn:
        for pid, (image_url, images) in CORRECT_IMAGES.items():
            await conn.execute(
                text(
                    "UPDATE ecommerce.products "
                    "SET image_url = :url, images = CAST(:imgs AS JSONB) "
                    "WHERE id = :pid"
                ),
                {"url": image_url, "imgs": __import__("json").dumps(images), "pid": pid},
            )
            print(f"  product {pid:>2}  ->  {image_url}")

    print("\nDone. Product images updated.")


if __name__ == "__main__":
    asyncio.run(fix())
