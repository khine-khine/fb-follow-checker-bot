"""
Summary Card Image Generator  —  v5  (Large & Bold)
1200 x 620 px  |  Big numbers  |  Channel promo  |  No username in header
"""

from PIL import Image, ImageDraw, ImageFont
import io

FONT_BOLD = "/usr/local/lib/python3.11/dist-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/local/lib/python3.11/dist-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"

W, H = 1200, 860

BG    = (11,  14,  35)
PANEL = (20,  26,  58)
BORD  = (38,  46,  90)
BLUE  = (80,  160, 255)
GOLD  = (255, 200,  50)
GREEN = (40,  220, 110)
RED   = (255,  75,  75)
WHITE = (255, 255, 255)
LGRAY = (160, 170, 210)
DGRAY = ( 50,  60, 100)
HBG   = ( 26,  34,  80)
PROMO = ( 18,  24,  60)


def _f(size: int, bold=True):
    path = FONT_BOLD if bold else FONT_REG
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _rrect(d, xy, r=12, fill=None, outline=None, width=2):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def _cx(d, cx, y, text, font, fill, shadow=True):
    bb = d.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    x  = cx - tw // 2
    if shadow:
        d.text((x+3, y+3), text, font=font, fill=(0, 0, 0))
    d.text((x, y), text, font=font, fill=fill)


def _grad(img):
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(
            int(11 + (7  - 11) * t),
            int(14 + (10 - 14) * t),
            int(35 + (28 - 35) * t),
        ))


def generate_summary_card(
    followers_count: int,
    following_count: int,
    mutual_count: int,
    not_back_count: int,
    username: str = "",
) -> bytes:

    img = Image.new("RGB", (W, H))
    _grad(img)
    d = ImageDraw.Draw(img)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    fHdr  = _f(30)
    fNum  = _f(90)          # 3-digit
    fNumM = _f(78)          # 4-digit (1,xxx)
    fLbl  = _f(20)
    fBar  = _f(20)
    fPrT  = _f(22)
    fPrS  = _f(17, False)

    # ── Header ────────────────────────────────────────────────────────────────
    _rrect(d, [28, 18, W-28, 78], r=14, fill=HBG, outline=BLUE, width=2)
    d.rounded_rectangle([28, 18, 52, 78], radius=14, fill=BLUE)
    d.rectangle([44, 18, 52, 78], fill=BLUE)
    d.text((66, 30), "Facebook Followers Analysis Result", font=fHdr, fill=WHITE)

    # ── 4 Tiles ───────────────────────────────────────────────────────────────
    tiles = [
        (followers_count, "FOLLOWERS",         BLUE),
        (following_count, "FOLLOWING",          GOLD),
        (mutual_count,    "MUTUAL FOLLOW",      GREEN),
        (not_back_count,  "NOT FOLLOWING BACK", RED),
    ]

    tw   = 252
    th   = 340
    gap  = 22
    tot  = tw * 4 + gap * 3
    tx0  = (W - tot) // 2
    ty0  = 92

    for i, (val, lbl, col) in enumerate(tiles):
        x0 = tx0 + i * (tw + gap)
        x1 = x0 + tw
        y0 = ty0
        y1 = ty0 + th

        # shadow
        _rrect(d, [x0+5, y0+5, x1+5, y1+5], r=16, fill=(5, 7, 20))
        # panel
        _rrect(d, [x0, y0, x1, y1], r=16, fill=PANEL, outline=BORD, width=1)
        # top stripe
        d.rounded_rectangle([x0, y0, x1, y0+12], radius=16, fill=col)
        d.rectangle([x0, y0+12, x1, y0+20], fill=col)

        # glow — will be drawn after we know ny, so approximate center
        gcx = x0 + tw // 2
        # approximate number center: midpoint between top stripe and label
        gcy = y0 + 20 + (th - 78) // 2
        for rr in range(70, 0, -7):
            a = int(18 * (1 - rr/70))
            cr, cg, cb = col
            d.ellipse([gcx-rr, gcy-rr, gcx+rr, gcy+rr], fill=(
                min(255, PANEL[0] + cr * a // 255),
                min(255, PANEL[1] + cg * a // 255),
                min(255, PANEL[2] + cb * a // 255),
            ))

        # number — center in zone between stripe and label
        num_str = f"{val:,}"
        fn  = fNumM if val >= 1000 else fNum
        bb  = d.textbbox((0, 0), num_str, font=fn)
        nw  = bb[2] - bb[0]
        nh  = bb[3] - bb[1]
        top_off = bb[1]   # Pillow includes ascender space above glyphs
        # zone: between bottom of top stripe and top of label pill
        # label pill top = y1 - lh_approx - 24, approx lh = 26
        zone_top = y0 + 20
        zone_bot = y1 - 60   # ~top of label pill
        zone_h   = zone_bot - zone_top
        # visual center: subtract top_off so glyph sits in center, not bbox
        ny  = zone_top + (zone_h - (nh - top_off)) // 2 - top_off
        nx  = x0 + (tw - nw) // 2
        d.text((nx+3, ny+3), num_str, font=fn, fill=(0, 0, 0))
        d.text((nx,   ny),   num_str, font=fn, fill=col)

        # label pill — always inside tile, 14px from bottom
        bb2 = d.textbbox((0, 0), lbl, font=fLbl)
        lw2 = bb2[2] - bb2[0]
        lh2 = bb2[3] - bb2[1]
        lx  = x0 + (tw - lw2) // 2 - 14
        ly  = y1 - lh2 - 46   # well inside tile bottom
        _rrect(d, [lx, ly, lx+lw2+28, ly+lh2+12], r=8,
               fill=(col[0]//5, col[1]//5, col[2]//5))
        d.text((x0 + (tw - lw2)//2, ly+6), lbl, font=fLbl, fill=col)

    # ── Progress Bar ──────────────────────────────────────────────────────────
    rate = (mutual_count / following_count * 100) if following_count else 0
    bx   = 40
    by   = ty0 + th + 30
    bw   = W - 80
    bh   = 32
    fw   = max(0, int(bw * rate / 100))

    d.text((bx, by - 32), "FOLLOW-BACK RATE", font=fBar, fill=LGRAY)
    rs   = f"{rate:.1f}%"
    bb_r = d.textbbox((0, 0), rs, font=fBar)
    d.text((W - 40 - (bb_r[2]-bb_r[0]), by - 32), rs, font=fBar, fill=GREEN)

    _rrect(d, [bx, by, bx+bw, by+bh], r=bh//2, fill=DGRAY)
    if fw > bh:
        _rrect(d, [bx, by, bx+fw, by+bh], r=bh//2, fill=GREEN)
        d.rectangle([bx+bh//2, by+6, bx+fw-10, by+10],
                    fill=(min(255, GREEN[0]+70), min(255, GREEN[1]+70), min(255, GREEN[2]+70)))

    for pct in (25, 50, 75):
        tx = bx + int(bw * pct / 100)
        d.line([(tx, by-5), (tx, by)], fill=(80, 90, 130), width=2)

    # ── Channel Promo ─────────────────────────────────────────────────────────
    py   = by + bh + 28
    tx0p = 64

    ch_name = "illumoria"
    ch_user = "@illumoria_1"
    promo_lines = [
        ("Join our Telegram channel for more —",  LGRAY, fPrS),
        ("Welcome to Illumoria",                        GOLD,  fPrT),
        ('"Laughter, tears, and a whole lot of binge-watching."', (200, 200, 230), fPrS),
        ("►  Latest K-Series & Films",              (120, 200, 255), fPrS),
        ("►  Variety & Survival Shows",             (120, 200, 255), fPrS),
        ("►  Experience the best of Korea here.",   (120, 200, 255), fPrS),
    ]

    # calculate total content height to size the box
    bb_n  = d.textbbox((0, 0), ch_name, font=fPrT)
    row1h = bb_n[3] - bb_n[1]
    lines_h = sum((d.textbbox((0,0), t, font=f)[3]-d.textbbox((0,0), t, font=f)[1])+7
                  for t, _, f in promo_lines)
    ph = row1h + 10 + lines_h + 28   # 18 top + 10 gap + lines + 18 bottom

    # draw box
    _rrect(d, [28, py, W-28, py+ph], r=14, fill=PROMO,
           outline=(50, 65, 140), width=1)
    d.rounded_rectangle([28, py, 48, py+ph], radius=14, fill=GOLD)
    d.rectangle([42, py, 48, py+ph], fill=GOLD)

    cy = py + 18

    # Row 1: channel name + username
    bb_u = d.textbbox((0, 0), ch_user, font=fPrS)
    d.text((tx0p, cy), ch_name, font=fPrT, fill=GOLD)
    d.text((tx0p + (bb_n[2]-bb_n[0]) + 14, cy + 4), ch_user, font=fPrS, fill=BLUE)
    cy += row1h + 10

    # Row 2+: description lines
    for line_txt, line_col, line_font in promo_lines:
        d.text((tx0p, cy), line_txt, font=line_font, fill=line_col)
        bb_l = d.textbbox((0, 0), line_txt, font=line_font)
        cy += (bb_l[3]-bb_l[1]) + 7

    # Telegram badge (right) — vertically centered in promo box
    badge = "Telegram"
    bb_b  = d.textbbox((0, 0), badge, font=fPrT)
    bw2   = bb_b[2] - bb_b[0]
    bh2   = bb_b[3] - bb_b[1]
    bx2   = W - 46 - bw2 - 24
    promo_mid = py + ph // 2
    by2   = promo_mid - bh2 // 2 - 8
    _rrect(d, [bx2-12, by2-6, bx2+bw2+12, by2+bh2+10], r=10,
           fill=(30, 100, 200), outline=(80, 160, 255), width=1)
    d.text((bx2, by2), badge, font=fPrT, fill=WHITE)

    # crop to content
    final_h = py + ph + 18
    img = img.crop((0, 0, W, final_h))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
