#!/usr/bin/env python3
"""
Facebook Follow-Back Checker Bot  —  Professional Edition
@illumoria_1 channel member gate  |  aiogram 3.x

Features:
  Security  : Channel gate, rate limiting (3 uploads/day), 20MB file size limit, admin panel
  UX        : Inline button menu, Myanmar/English language toggle, progress bar animation
  Data      : SQLite storage, 2hr cache expiry, usage logging
  Export    : .txt, .csv, PNG summary card
"""

import asyncio
import csv
import io
import json
import logging
import os
import sqlite3
import time
import zipfile
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.fsm.storage.memory import MemoryStorage

from card_generator import generate_summary_card

# ── Config ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot_usage.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BOT_TOKEN    = os.getenv("BOT_TOKEN", "8908867218:AAHOxEujRxyfDskdWv2HairpqJGPoAZvs0g")
CHANNEL_ID   = "@illumoria_1"
ADMIN_IDS    = {int(x) for x in os.getenv("ADMIN_IDS", "1683995608").split(",") if x.strip()}
MAX_ZIP_MB   = 20
MAX_UPLOADS  = 3          # per day
CACHE_TTL    = 7200       # 2 hours in seconds
PAGE_SIZE    = 20
SEP          = "=" * 40
DB_PATH      = "bot_data.db"

# ── Languages ──────────────────────────────────────────────────────────────────
LANG = {
    "mm": {
        "welcome": (
            "မင်္ဂလာပါ! 👋\n\n"
            "Facebook followers/following data စစ်ဆေးဖို့\n"
            "Facebook ZIP ဖိုင်ကို ဤနေရာတွင် ပေးပို့ပါ။\n\n"
            "📌 Commands:\n"
            "/help  — အသုံးပြုနည်း\n"
            "/stats — ရလဒ် summary\n"
            "/check — follow ပြန်မလုပ်သူ စာရင်း\n"
            "/top10 — အသစ်ဆုံး 10 ဦး\n"
            "/export — full list (.txt + .csv)\n"
            "/lang  — ဘာသာ ပြောင်းရန်"
        ),
        "help": (
            "📖 Bot အသုံးပြုနည်း\n" + SEP + "\n\n"
            "Facebook ၏ \"Download Your Information\"\n"
            "မှ download လုပ်ထားသော ZIP ဖိုင်ကို\n"
            "ဤ bot သို့ တိုက်ရိုက် upload လုပ်ပါ။\n\n"
            "ZIP ထဲတွင် ပါဝင်ရမည့် ဖိုင်:\n"
            "• people_who_followed_you.json\n"
            "• who_you've_followed.json\n\n"
            "ကန့်သတ်ချက်:\n"
            "• ဖိုင် အများဆုံး 20MB\n"
            "• တစ်ရက် upload 3 ကြိမ်\n\n"
            "/lang — မြန်မာ / English ပြောင်းရန်"
        ),
        "gate": (
            "🔒 ဤ bot ကို @illumoria_1 channel\n"
            "member များသာ အသုံးပြုနိုင်ပါသည်။\n\n"
            "Channel join ပြီးပါက အောက်ပါ ခလုတ်ကို နှိပ်ပါ။"
        ),
        "join_btn":    "📢 @illumoria_1 Channel Join ရန်",
        "recheck_btn": "✅ Join ပြီးပါပြီ — စစ်ဆေးမည်",
        "recheck_ok":  "✅ Channel member အဖြစ် အတည်ပြုပြီးပါပြီ!\n\nFacebook ZIP ဖိုင်ကို ယခု ပေးပို့နိုင်ပါပြီ။",
        "recheck_fail":"❌ Channel member မဟုတ်သေးပါ။ Join ပြီးမှ ထပ်နှိပ်ပါ။",
        "processing":  "⏳ စစ်ဆေးနေပါသည်…",
        "invalid_zip": "❌ မှန်ကန်သော ZIP ဖိုင် မဟုတ်ပါ။",
        "too_big":     f"❌ ဖိုင် {MAX_ZIP_MB}MB ကျော်သောကြောင့် လက်မခံနိုင်ပါ။",
        "json_miss":   "❌ လိုအပ်သော JSON ဖိုင်များ မတွေ့ပါ။",
        "proc_err":    "❌ ဒေတာ စစ်ဆေးရာတွင် အမှားအယွင်း ရှိပါသည်။",
        "rate_limit":  f"⚠️ တစ်ရက်တွင် {MAX_UPLOADS} ကြိမ်သာ upload ပြုလုပ်နိုင်ပါသည်။\nမနက်ဖြန် ထပ်မံ ကြိုးစားပါ။",
        "no_cache":    "⚠️ ဦးစွာ Facebook ZIP ဖိုင်ကို upload လုပ်ပါ။\n(ရလဒ် 2 နာရီ သာ သိမ်းဆည်းပါသည်)",
        "all_follow":  "🎉 သင် follow လုပ်ထားသူ အားလုံး သင့်ကို ပြန် follow လုပ်ထားပါသည်!",
        "lang_changed":"✅ ဘာသာ မြန်မာ သို့ ပြောင်းပြီးပါပြီ။",
        "lang_btn":    "🌐 English သို့ ပြောင်းရန်",
        "export_cap":  "📄 Follow ပြန်မလုပ်သူ full list",
        "csv_cap":     "📊 CSV ဖိုင် (Excel/Sheets တွင် ဖွင့်နိုင်)",
        "card_cap":    "📊 Facebook Analysis Summary Card",
        "not_back_hdr":"❌ Not Following Back",
        "top10_hdr":   "🔟 လတ်တလော Follow လုပ်ထားသော်လည်း\n   Follow ပြန်မလုပ်သူ Top 10",
        "followed_on": "Followed on",
        "page_label":  "စာမျက်နှာ",
        "prev":        "⬅️ နောက်",
        "next":        "ရှေ့ ➡️",
    },
    "en": {
        "welcome": (
            "Hello! 👋\n\n"
            "Send your Facebook data export ZIP file\n"
            "to check who doesn't follow you back.\n\n"
            "📌 Commands:\n"
            "/help  — How to use\n"
            "/stats — Result summary\n"
            "/check — Not-following-back list\n"
            "/top10 — Latest 10 people\n"
            "/export — Full list (.txt + .csv)\n"
            "/lang  — Change language"
        ),
        "help": (
            "📖 How to Use\n" + SEP + "\n\n"
            "Upload your Facebook \"Download Your\n"
            "Information\" ZIP file directly here.\n\n"
            "Required files inside ZIP:\n"
            "• people_who_followed_you.json\n"
            "• who_you've_followed.json\n\n"
            "Limits:\n"
            f"• Max file size: {MAX_ZIP_MB}MB\n"
            f"• Max {MAX_UPLOADS} uploads per day\n\n"
            "/lang — Switch to Myanmar"
        ),
        "gate": (
            "🔒 This bot is exclusive to\n"
            "@illumoria_1 channel members.\n\n"
            "Join the channel then tap the button below."
        ),
        "join_btn":    "📢 Join @illumoria_1 Channel",
        "recheck_btn": "✅ I've Joined — Verify Now",
        "recheck_ok":  "✅ Membership verified!\n\nYou can now upload your Facebook ZIP file.",
        "recheck_fail":"❌ You're not a member yet. Join first, then tap again.",
        "processing":  "⏳ Processing your file…",
        "invalid_zip": "❌ The file you sent is not a valid ZIP.",
        "too_big":     f"❌ File exceeds {MAX_ZIP_MB}MB limit.",
        "json_miss":   "❌ Required JSON files not found in ZIP.",
        "proc_err":    "❌ An error occurred while processing.",
        "rate_limit":  f"⚠️ You can only upload {MAX_UPLOADS} times per day.\nPlease try again tomorrow.",
        "no_cache":    "⚠️ Please upload your Facebook ZIP file first.\n(Results are cached for 2 hours)",
        "all_follow":  "🎉 Everyone you follow also follows you back!",
        "lang_changed":"✅ Language changed to English.",
        "lang_btn":    "🌐 မြန်မာ သို့ ပြောင်းရန်",
        "export_cap":  "📄 Not-following-back full list",
        "csv_cap":     "📊 CSV file (open in Excel/Sheets)",
        "card_cap":    "📊 Facebook Analysis Summary Card",
        "not_back_hdr":"❌ Not Following Back",
        "top10_hdr":   "🔟 Latest 10 People Not Following Back",
        "followed_on": "Followed on",
        "page_label":  "Page",
        "prev":        "⬅️ Prev",
        "next":        "Next ➡️",
    },
}

# ── SQLite DB ──────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            lang        TEXT DEFAULT 'mm',
            created_at  REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            uploaded_at REAL DEFAULT (strftime('%s','now')),
            followers   INTEGER,
            following   INTEGER,
            not_back    INTEGER
        );
        CREATE TABLE IF NOT EXISTS cache (
            user_id         INTEGER PRIMARY KEY,
            followers_json  TEXT,
            following_json  TEXT,
            not_back_json   TEXT,
            cached_at       REAL
        );
    """)
    con.commit()
    con.close()

def db_get_lang(user_id: int) -> str:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return row[0] if row else "mm"

def db_set_lang(user_id: int, lang: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    con.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
    con.commit(); con.close()

def db_upsert_user(user_id: int, username: str, first_name: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO users(user_id,username,first_name) VALUES(?,?,?)",
        (user_id, username, first_name)
    )
    con.execute(
        "UPDATE users SET username=?,first_name=? WHERE user_id=?",
        (username, first_name, user_id)
    )
    con.commit(); con.close()

def db_count_today_uploads(user_id: int) -> int:
    since = time.time() - 86400
    con   = sqlite3.connect(DB_PATH)
    cnt   = con.execute(
        "SELECT COUNT(*) FROM uploads WHERE user_id=? AND uploaded_at>?",
        (user_id, since)
    ).fetchone()[0]
    con.close()
    return cnt

def db_log_upload(user_id: int, followers: int, following: int, not_back: int):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO uploads(user_id,followers,following,not_back) VALUES(?,?,?,?)",
        (user_id, followers, following, not_back)
    )
    con.commit(); con.close()

def db_save_cache(user_id: int, followers_names, following_list, not_following_back):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)",
        (
            user_id,
            json.dumps(list(followers_names), ensure_ascii=False),
            json.dumps(following_list,        ensure_ascii=False),
            json.dumps(not_following_back,    ensure_ascii=False),
            time.time(),
        )
    )
    con.commit(); con.close()

def db_load_cache(user_id: int):
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT followers_json,following_json,not_back_json,cached_at FROM cache WHERE user_id=?",
        (user_id,)
    ).fetchone()
    con.close()
    if not row:
        return None
    cached_at = row[3]
    if time.time() - cached_at > CACHE_TTL:
        return None   # expired
    return {
        "followers_names":    set(json.loads(row[0])),
        "following_list":     json.loads(row[1]),
        "not_following_back": json.loads(row[2]),
    }

def db_admin_stats():
    con = sqlite3.connect(DB_PATH)
    total_users   = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_uploads = con.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
    today_since   = time.time() - 86400
    today_uploads = con.execute(
        "SELECT COUNT(*) FROM uploads WHERE uploaded_at>?", (today_since,)
    ).fetchone()[0]
    active_cache  = con.execute(
        "SELECT COUNT(*) FROM cache WHERE cached_at>?", (time.time() - CACHE_TTL,)
    ).fetchone()[0]
    con.close()
    return total_users, total_uploads, today_uploads, active_cache

# ── Rate Limit (in-memory fast check) ─────────────────────────────────────────
_rate: dict = defaultdict(list)

def rate_check(user_id: int) -> bool:
    now    = time.time()
    times  = [t for t in _rate[user_id] if now - t < 86400]
    _rate[user_id] = times
    if len(times) >= MAX_UPLOADS:
        return False
    _rate[user_id].append(now)
    return True

# ── Encoding Fix ───────────────────────────────────────────────────────────────
def fix_encoding(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text

# ── ZIP Parser ─────────────────────────────────────────────────────────────────
def parse_zip(zip_bytes: bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        fp = next((n for n in names if "people_who_followed_you.json" in n), None)
        fw = next((n for n in names if "who_you" in n and "followed.json" in n), None)
        if not fp or not fw:
            return None, None, None
        with zf.open(fp) as f:
            followers_raw = json.load(f).get("followers_v3", [])
        with zf.open(fw) as f:
            following_raw = json.load(f).get("following_v3", [])

    followers_names = {fix_encoding(x["name"]) for x in followers_raw}
    following_list  = [
        {"name": fix_encoding(x["name"]), "timestamp": x.get("timestamp", 0)}
        for x in following_raw
    ]
    not_following_back = sorted(
        [p for p in following_list if p["name"] not in followers_names],
        key=lambda x: x["timestamp"], reverse=True
    )
    return followers_names, following_list, not_following_back

# ── Formatters ─────────────────────────────────────────────────────────────────
def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A"

def format_stats(d: dict, L: dict) -> str:
    fn = d["followers_names"]
    fl = d["following_list"]
    nb = d["not_following_back"]
    mutual = len({p["name"] for p in fl} & fn)
    return (
        f"📊 Facebook Analysis Result\n{SEP}\n\n"
        f"👥 Followers Count:    {len(fn)}\n"
        f"➡️ Following Count:    {len(fl)}\n"
        f"🤝 Mutual Follow:      {mutual}\n"
        f"❌ Not Following Back: {len(nb)}\n\n"
        f"{SEP}\n\n"
        f"/check — {L['not_back_hdr']} (20 ဦးစီ)\n"
        f"/top10 — {L['top10_hdr'].split(chr(10))[0]}\n"
        f"/export — .txt + .csv"
    )

def format_page(nfb: list, page: int, L: dict) -> str:
    total = len(nfb)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start = page * PAGE_SIZE
    chunk = nfb[start: start + PAGE_SIZE]
    lines = [
        f"{L['not_back_hdr']} ({total})",
        f"📄 {L['page_label']} {page+1} / {total_pages}",
        SEP, "",
    ]
    for i, p in enumerate(chunk, start=start+1):
        lines.append(f"{i}. {p['name']}")
        lines.append(f"    {L['followed_on']}: {fmt_ts(p['timestamp'])}")
        lines.append("")
    return "\n".join(lines).rstrip()

def format_full_txt(d: dict, L: dict) -> str:
    fn = d["followers_names"]
    fl = d["following_list"]
    nb = d["not_following_back"]
    mutual = len({p["name"] for p in fl} & fn)
    lines = [
        "📊 Facebook Analysis Result", SEP, "",
        f"👥 Followers Count:    {len(fn)}",
        f"➡️ Following Count:    {len(fl)}",
        f"🤝 Mutual Follow:      {mutual}",
        f"❌ Not Following Back: {len(nb)}",
        "", SEP, "",
    ]
    for i, p in enumerate(nb, 1):
        lines.append(f"{i}. {p['name']}")
        lines.append(f"    {L['followed_on']}: {fmt_ts(p['timestamp'])}")
        lines.append("")
    return "\n".join(lines).rstrip()

def format_csv(d: dict) -> bytes:
    nb = d["not_following_back"]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Name", "Followed On"])
    for i, p in enumerate(nb, 1):
        writer.writerow([i, p["name"], fmt_ts(p["timestamp"])])
    return buf.getvalue().encode("utf-8-sig")  # utf-8-sig for Excel compatibility

def page_kb(page: int, total: int, L: dict) -> InlineKeyboardMarkup:
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    btns = []
    if page > 0:
        btns.append(InlineKeyboardButton(text=L["prev"], callback_data=f"page:{page-1}"))
    if page < total_pages - 1:
        btns.append(InlineKeyboardButton(text=L["next"], callback_data=f"page:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[btns]) if btns else InlineKeyboardMarkup(inline_keyboard=[])

def gate_kb(L: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["join_btn"],    url="https://t.me/illumoria_1")],
        [InlineKeyboardButton(text=L["recheck_btn"], callback_data="recheck_membership")],
    ])

# ── Channel Check ──────────────────────────────────────────────────────────────
async def is_member(bot: Bot, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def require_member(message: Message, bot: Bot) -> bool:
    L = LANG[db_get_lang(message.from_user.id)]
    if not await is_member(bot, message.from_user.id):
        await message.reply(L["gate"], reply_markup=gate_kb(L))
        return False
    return True

# ── Progress bar helper ────────────────────────────────────────────────────────
async def progress_edit(msg: Message, step: int, total: int = 5, label: str = ""):
    filled = int(step / total * 10)
    bar    = "█" * filled + "░" * (10 - filled)
    pct    = int(step / total * 100)
    await msg.edit_text(f"⏳ [{bar}] {pct}%  {label}")

# ── Handlers ───────────────────────────────────────────────────────────────────
async def cmd_start(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    u = message.from_user
    db_upsert_user(u.id, u.username or "", u.first_name or "")
    L = LANG[db_get_lang(u.id)]
    log.info(f"/start user_id={u.id} username={u.username}")
    await message.reply(L["welcome"])

async def cmd_help(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    L = LANG[db_get_lang(message.from_user.id)]
    await message.reply(L["help"])

async def cmd_lang(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    uid  = message.from_user.id
    cur  = db_get_lang(uid)
    new  = "en" if cur == "mm" else "mm"
    db_set_lang(uid, new)
    L    = LANG[new]
    await message.reply(L["lang_changed"])

async def handle_zip(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return

    uid = message.from_user.id
    L   = LANG[db_get_lang(uid)]
    log.info(f"ZIP upload user_id={uid} file={message.document.file_name if message.document else 'N/A'}")

    if not message.document or not message.document.file_name.lower().endswith(".zip"):
        await message.reply(L["invalid_zip"])
        return

    # File size check
    if message.document.file_size > MAX_ZIP_MB * 1024 * 1024:
        await message.reply(L["too_big"])
        return

    # Rate limit check
    if not rate_check(uid):
        await message.reply(L["rate_limit"])
        return

    status = await message.reply(L["processing"])

    try:
        await progress_edit(status, 1, label="Downloading…")
        file_info = await bot.get_file(message.document.file_id)
        buf = io.BytesIO()
        await bot.download_file(file_info.file_path, buf)

        await progress_edit(status, 2, label="Extracting ZIP…")
        followers_names, following_list, not_following_back = parse_zip(buf.getvalue())

        if followers_names is None:
            await status.edit_text(L["json_miss"])
            return

        await progress_edit(status, 3, label="Analysing data…")
        db_save_cache(uid, followers_names, following_list, not_following_back)
        db_log_upload(uid, len(followers_names), len(following_list), len(not_following_back))

        await progress_edit(status, 4, label="Generating card…")
        mutual = len({p["name"] for p in following_list} & followers_names)
        card_bytes = generate_summary_card(
            len(followers_names), len(following_list), mutual,
            len(not_following_back),
            username=message.from_user.username or "",
        )

        await progress_edit(status, 5, label="Done!")
        await status.delete()

        if not not_following_back:
            await message.reply(L["all_follow"])
            return

        cache = {"followers_names": followers_names, "following_list": following_list,
                 "not_following_back": not_following_back}

        # 1. Summary card image
        await bot.send_photo(
            message.chat.id,
            BufferedInputFile(card_bytes, filename="summary.png"),
            caption=L["card_cap"],
        )

        # 2. Stats text
        await message.reply(format_stats(cache, L))

        # 3. Full .txt file
        txt = format_full_txt(cache, L).encode("utf-8")
        await bot.send_document(
            message.chat.id,
            BufferedInputFile(txt, filename="not_following_back.txt"),
            caption=L["export_cap"],
        )

        # 4. CSV file
        csv_bytes = format_csv(cache)
        await bot.send_document(
            message.chat.id,
            BufferedInputFile(csv_bytes, filename="not_following_back.csv"),
            caption=L["csv_cap"],
        )

    except zipfile.BadZipFile:
        await status.edit_text(L["invalid_zip"])
    except Exception as e:
        log.error(f"Error processing ZIP for user {uid}: {e}", exc_info=True)
        await status.edit_text(L["proc_err"])

async def cmd_stats(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    uid   = message.from_user.id
    L     = LANG[db_get_lang(uid)]
    cache = db_load_cache(uid)
    if not cache:
        await message.reply(L["no_cache"])
        return
    await message.reply(format_stats(cache, L))

async def cmd_check(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    uid   = message.from_user.id
    L     = LANG[db_get_lang(uid)]
    cache = db_load_cache(uid)
    if not cache:
        await message.reply(L["no_cache"])
        return
    nfb = cache["not_following_back"]
    await message.reply(format_page(nfb, 0, L), reply_markup=page_kb(0, len(nfb), L))

async def cmd_top10(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    uid   = message.from_user.id
    L     = LANG[db_get_lang(uid)]
    cache = db_load_cache(uid)
    if not cache:
        await message.reply(L["no_cache"])
        return
    nfb   = cache["not_following_back"][:10]
    lines = [L["top10_hdr"], SEP, ""]
    for i, p in enumerate(nfb, 1):
        lines.append(f"{i}. {p['name']}")
        lines.append(f"    {L['followed_on']}: {fmt_ts(p['timestamp'])}")
        lines.append("")
    await message.reply("\n".join(lines).rstrip())

async def cmd_export(message: Message, bot: Bot):
    if not await require_member(message, bot):
        return
    uid   = message.from_user.id
    L     = LANG[db_get_lang(uid)]
    cache = db_load_cache(uid)
    if not cache:
        await message.reply(L["no_cache"])
        return
    txt = format_full_txt(cache, L).encode("utf-8")
    await bot.send_document(
        message.chat.id,
        BufferedInputFile(txt, filename="not_following_back.txt"),
        caption=L["export_cap"],
    )
    csv_bytes = format_csv(cache)
    await bot.send_document(
        message.chat.id,
        BufferedInputFile(csv_bytes, filename="not_following_back.csv"),
        caption=L["csv_cap"],
    )

async def cmd_admin(message: Message, bot: Bot):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        return
    total_users, total_uploads, today_uploads, active_cache = db_admin_stats()
    await message.reply(
        f"🛡️ Admin Panel\n{SEP}\n\n"
        f"👤 Total Users:        {total_users}\n"
        f"📤 Total Uploads:      {total_uploads}\n"
        f"📅 Today's Uploads:    {today_uploads}\n"
        f"💾 Active Cache:       {active_cache} users\n\n"
        f"⏱️ Cache TTL:          2 hours\n"
        f"📁 DB:                 {DB_PATH}\n"
        f"📋 Log:                bot_usage.log"
    )

# ── Callbacks ──────────────────────────────────────────────────────────────────
async def recheck_callback(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    L   = LANG[db_get_lang(uid)]
    if await is_member(bot, uid):
        await callback.message.edit_text(L["recheck_ok"])
        await callback.answer("✅", show_alert=False)
    else:
        await callback.answer(L["recheck_fail"], show_alert=True)

async def page_callback(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    if not await is_member(bot, uid):
        await callback.answer("Channel join ပါ!", show_alert=True)
        return
    L     = LANG[db_get_lang(uid)]
    cache = db_load_cache(uid)
    if not cache:
        await callback.answer(L["no_cache"], show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    nfb  = cache["not_following_back"]
    await callback.message.edit_text(
        format_page(nfb, page, L),
        reply_markup=page_kb(page, len(nfb), L),
    )
    await callback.answer()

# ── Main ───────────────────────────────────────────────────────────────────────
async def main():
    init_db()
    log.info("DB initialized")

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start,  CommandStart())
    dp.message.register(cmd_help,   Command("help"))
    dp.message.register(cmd_lang,   Command("lang"))
    dp.message.register(cmd_stats,  Command("stats"))
    dp.message.register(cmd_check,  Command("check"))
    dp.message.register(cmd_top10,  Command("top10"))
    dp.message.register(cmd_export, Command("export"))
    dp.message.register(cmd_admin,  Command("admin"))
    dp.message.register(handle_zip, F.document)

    dp.callback_query.register(recheck_callback, F.data == "recheck_membership")
    dp.callback_query.register(page_callback,    F.data.startswith("page:"))

    log.info(f"Bot started | Channel gate: {CHANNEL_ID} | Admin IDs: {ADMIN_IDS}")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
