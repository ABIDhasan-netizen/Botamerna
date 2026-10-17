#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Store / Access Bot (aiogram 3.x + SQLite)
v9 Render-Ready: Full admin panel + Flask Health Server
"""
import asyncio
import html
import logging
import math
import os
import re
import threading
from contextlib import asynccontextmanager
from urllib.parse import quote

from flask import Flask
import aiosqlite
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ============ কনফিগ ============
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8734494535:AAHylmP-S4hPTk1fpBib02quT2uqwr_ibec")
ADMIN_IDS = {7307860847}
DB_PATH = "store.db"
CURRENCY = "💎"
MIN_DEPOSIT = 50.0
MIN_USD = 1.0
REFERRAL_BONUS = 0.0

DEFAULT_SUPPORT = "AMAccessSupport_bot"
DEFAULT_RATE_BUY = 120.0
DEFAULT_RATE_SELL = 115.0

DEFAULT_BKASH = "01949638507"
DEFAULT_NAGAD = "01650242703"
DEFAULT_ROCKET = "01XXXXXXXXX"
DEFAULT_BINANCE = "YourBinanceUIDHere"
DEFAULT_USDT = "T-XXXXXXXXXXXXXXXXXXXXXXXX"
DEFAULT_LTC = "L-XXXXXXXXXXXXXXXXXXXXXXXX"
DEFAULT_BITGET = "YourBitgetUIDHere"

FIAT_PAYMENT_METHODS = ["bKash", "Nagad", "Rocket"]

BOT_USERNAME = ""
log = logging.getLogger("store-bot")

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))

def fmt(x: float) -> str:
    return f"{x:,.2f}"

def sgn(v) -> str:
    return f"+{v:g}" if v > 0 else f"{v:g}"

def is_admin_id(uid: int) -> bool:
    return uid in ADMIN_IDS

WELCOME_MULTI = (
    "👋 <b>স্বাগতম, {name}!</b>\n"
    "অনুগ্রহ করে আপনার ভাষা নির্বাচন করুন।"
)

T = {
    "bn": {
        "lang_saved": "✅ ভাষা সেট হয়েছে: বাংলা 🇧🇩",
        "main_menu": "🏠 প্রধান মেনু — নিচের বাটন থেকে বেছে নিন।",
        "btn_buy": "🛒 প্রোডাক্ট কিনুন",
        "btn_dollar": "💵 ডলার বাই/সেল",
        "btn_profile": "👤 প্রোফাইল",
        "btn_deposit": "💳 ডিপোজিট",
        "btn_ref": "🔗 রেফার",
        "btn_support": "🎧 সাপোর্ট",
        "btn_help": "🙋‍♂️ আমি নতুন",
        "back": "⬅️ ব্যাক",
        "choose_category": "কোন প্রোডাক্ট কিনতে চান?",
        "no_categories": "😔 এই মুহূর্তে কোনো প্রোডাক্ট বা ক্যাটাগরি নেই।",
        "choose_product": "সাব-প্রোডাক্ট সিলেক্ট করুন:\n\n📦 <b>{cat}</b>",
        "no_products": "😔 এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই।",
        "product_detail": "কোন প্রোডাক্ট কিনতে চান?\n\n📦 <b>{name}</b>{desc}\n💎 প্রাইস: <b>{price} {cur}</b>\n📊 স্টক: <b>{stock}</b>\n\n🛒 পরিমাণ: <b>{qty}</b>\n💰 মোট দাম: <b>{total} {cur}</b>",
        "buy_ok": "✅ <b>কেনা সফল!</b>\n\n📦 {name} (পরিমাণ: {qty})\n💎 মোট কাটা হয়েছে: {total} {cur}\n💼 বর্তমান ব্যালেন্স: {balance} {cur}",
        "buy_nobalance": "❌ <b>Insufficient Balance!</b>\n\n💎 Total: {total} {cur}\n💼 Balance: {balance} {cur}\n💰 Need: {need} {cur}\n\n👉 Deposit funds first!",
        "buy_nostock": "❌ দুঃখিত, পর্যাপ্ত স্টক নেই।",
        "buy_notfound": "❌ প্রোডাক্টটি পাওয়া যায়নি।",
        "profile": "👤 <b>আপনার প্রোফাইল</b>\n\n🆔 Telegram ID: <code>{uid}</code>\n📛 নাম: {name}\n\n💼 ব্যালেন্স: <b>{balance} {cur}</b>\n🛒 কেনা প্রোডাক্ট: <b>{items} টি</b>\n💸 মোট খরচ: <b>{spent} {cur}</b>\n💳 মোট ডিপোজিট: <b>{dep} {cur}</b>\n\n👥 মোট রেফার: {refs}\n🎁 রেফার আয়: {earn} {cur}\n📅 জয়েন: {joined}",
        "history_btn": "📜 ট্রানজেকশন হিস্ট্রি",
        "history_title": "📜 <b>সর্বশেষ ১০টি ট্রানজেকশন:</b>\n\n",
        "history_empty": "কোনো ট্রানজেকশন নেই।",
        "dep_choose": "💎 <b>ডিপোজিট মেথড সিলেক্ট করুন:</b>",
        "dep_instr": "💎 <b>{method} Selected</b>\n\n📱 {method} Number: <code>{address}</code>\n\n1 TK = 1 💎\n🟢 Minimum deposit: {min} {cur}\n\n🎯 Send money to this number, then submit the Transaction ID.\n\n💰 আপনি কত {cur} ডিপোজিট করতে চান লিখুন (সর্বনিম্ন {min}):\n(বাতিল করতে /cancel বা /start)",
        "dep_ask_trx": "🧾 এখন আপনার <b>Transaction ID / Order ID / Pay ID</b> টি লিখে পাঠান:\nঅথবা বাতিল করতে /cancel লিখুন",
        "support_text": "🎧 <b>সাপোর্ট</b>\n\nযেকোনো সমস্যার জন্য এডমিনের সাথে যোগাযোগ করুন।\n\n🔗 পেমেন্ট সংক্রান্ত যেকোনো সমস্যার জন্য আমাদের সাথে যোগাযোগ করুন: @{admin}",
        "help_text": "🙋‍♂️ <b>টিউটোরিয়াল ও গাইড:</b>\nনিচের অপশন থেকে যে ভিডিওটি দেখতে চান সিলেক্ট করুন:",
        "usd_menu": "💵 <b>ডলার বাই/সেল জোন</b>\n\n🟢 ডলার কেনার রেট: <b>1 USD = {sell} {cur}</b>\n🔴 ডলার বিক্রির রেট: <b>1 USD = {buy} {cur}</b>\n\n💼 ব্যালেন্স: {balance} {cur}",
        "usd_buy_btn": "🟢 ডলার কিনুন",
        "usd_sell_btn": "🔴 ডলার বিক্রি করুন",
        "cancelled": "❎ বাতিল করা হয়েছে।",
        "banned": "🚫 আপনাকে ব্যান করা হয়েছে।",
    }
}

MENU_KEYS = ["btn_buy", "btn_dollar", "btn_profile", "btn_deposit", "btn_ref", "btn_support", "btn_help"]

def t(lang: str, key: str, **kw) -> str:
    text = T.get(lang, T["bn"]).get(key) or T["bn"].get(key, key)
    return text.format(**kw) if kw else text

def all_texts(key: str) -> set:
    return {T[l][key] for l in T if key in T[l]}

MENU_TEXTS = set()
for _k in MENU_KEYS:
    MENU_TEXTS |= all_texts(_k)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    user_id      INTEGER PRIMARY KEY,
    username     TEXT,
    full_name    TEXT,
    lang         TEXT    NOT NULL DEFAULT 'bn',
    balance      REAL    NOT NULL DEFAULT 0,
    referred_by  INTEGER,
    ref_count    INTEGER NOT NULL DEFAULT 0,
    ref_earnings REAL    NOT NULL DEFAULT 0,
    ref_paid     INTEGER NOT NULL DEFAULT 0,
    banned       INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS categories(
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS products(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price       REAL NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS stock(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    sold       INTEGER NOT NULL DEFAULT 0,
    sold_to    INTEGER,
    sold_at    TEXT
);
CREATE TABLE IF NOT EXISTS transactions(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    type          TEXT NOT NULL,
    amount        REAL NOT NULL,
    balance_after REAL NOT NULL,
    note          TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS deposits(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    method      TEXT NOT NULL,
    amount      REAL NOT NULL,
    trx_id      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    resolved_by INTEGER
);
CREATE TABLE IF NOT EXISTS dollar_orders(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    direction  TEXT NOT NULL,
    crypto_meth TEXT NOT NULL DEFAULT '',
    fiat_meth  TEXT NOT NULL DEFAULT '',
    usd_amount REAL NOT NULL,
    bdt_amount REAL NOT NULL,
    details    TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS settings(
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_methods(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    kind    TEXT NOT NULL DEFAULT 'fiat',
    active  INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS help_videos(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    kind       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

async def q1(c, sql, params=()):
    cur = await c.execute(sql, params)
    return await cur.fetchone()

async def qa(c, sql, params=()):
    cur = await c.execute(sql, params)
    return await cur.fetchall()

def calc_price(cur: float, mode: str, value: float) -> float:
    if mode == "p":
        new = cur * (1 + value / 100.0)
    elif mode == "f":
        new = cur + value
    else:
        new = value
    if not math.isfinite(new):
        return cur
    return max(round(new, 2), 0.01)

class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self.lock = asyncio.Lock()

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()
        await self._migrate_stock_fk()
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_avail ON stock(product_id, sold)")
        await self.conn.commit()

        defaults = {
            "rate_buy": str(DEFAULT_RATE_BUY),
            "rate_sell": str(DEFAULT_RATE_SELL),
            "support_username": DEFAULT_SUPPORT,
            "channel_link": "",
            "min_deposit": str(MIN_DEPOSIT),
        }
        for k, v in defaults.items():
            await self.conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        await self.conn.commit()
        await self._seed_payment_methods()

    async def _migrate_stock_fk(self):
        rows = await qa(self.conn, "PRAGMA foreign_key_list(stock)")
        if not any(r["table"] == "categories" for r in rows):
            return
        log.warning("Migrating stock table (fixing wrong foreign key)...")
        await self.conn.commit()
        await self.conn.execute("PRAGMA foreign_keys=OFF")
        await self.conn.executescript("""
        BEGIN;
        ALTER TABLE stock RENAME TO stock_old;
        CREATE TABLE stock(
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            content    TEXT NOT NULL,
            sold       INTEGER NOT NULL DEFAULT 0,
            sold_to    INTEGER,
            sold_at    TEXT
        );
        INSERT INTO stock(id,product_id,content,sold,sold_to,sold_at)
            SELECT id,product_id,content,sold,sold_to,sold_at FROM stock_old;
        DROP TABLE stock_old;
        COMMIT;
        """)
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.commit()

    async def _seed_payment_methods(self):
        row = await q1(self.conn, "SELECT COUNT(*) n FROM payment_methods")
        if row["n"]:
            return
        defaults = [
            ("bkash", "bKash", DEFAULT_BKASH, "fiat"),
            ("rocket", "Rocket", DEFAULT_ROCKET, "fiat"),
            ("nagad", "Nagad", DEFAULT_NAGAD, "fiat"),
            ("binance", "Binance UID", DEFAULT_BINANCE, "crypto"),
            ("usdt", "USDT (BEP20)", DEFAULT_USDT, "crypto"),
            ("ltc", "LTC (LiteCoin)", DEFAULT_LTC, "crypto"),
            ("bitget", "Bitget UID", DEFAULT_BITGET, "crypto"),
        ]
        for code, name, addr, kind in defaults:
            old = await q1(self.conn, "SELECT value FROM settings WHERE key=?", (f"pay_{code}",))
            if old and old["value"] and not (code == "bitget" and old["value"] == DEFAULT_BKASH):
                addr = old["value"]
            await self.conn.execute(
                "INSERT INTO payment_methods(name,address,kind,active) VALUES(?,?,?,1)", (name, addr, kind)
            )
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    @asynccontextmanager
    async def txn(self):
        async with self.lock:
            try:
                yield self.conn
                await self.conn.commit()
            except BaseException:
                await self.conn.rollback()
                raise

    async def one(self, sql, params=()):
        async with self.lock:
            return await q1(self.conn, sql, params)

    async def many(self, sql, params=()):
        async with self.lock:
            return await qa(self.conn, sql, params)

    async def get_setting(self, key, default=""):
        row = await self.one("SELECT value FROM settings WHERE key=?", (key,))
        return row["value"] if row else default

    async def set_setting(self, key, value):
        async with self.txn() as c:
            await c.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value))
            )

    async def rates(self):
        buy = float(await self.get_setting("rate_buy", DEFAULT_RATE_BUY))
        sell = float(await self.get_setting("rate_sell", DEFAULT_RATE_SELL))
        return buy, sell

    async def get_user(self, uid):
        return await self.one("SELECT * FROM users WHERE user_id=?", (uid,))

    async def find_user_by_username(self, username):
        return await self.one("SELECT * FROM users WHERE lower(username)=lower(?)", (username.lstrip("@"),))

    async def create_user(self, uid, username, full_name):
        async with self.txn() as c:
            await c.execute(
                "INSERT OR IGNORE INTO users(user_id,username,full_name) VALUES(?,?,?)",
                (uid, username, full_name)
            )

    async def update_profile(self, uid, username, full_name):
        async with self.txn() as c:
            await c.execute("UPDATE users SET username=?, full_name=? WHERE user_id=?", (username, full_name, uid))

    async def set_lang(self, uid, lang):
        async with self.txn() as c:
            await c.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))

    async def set_banned(self, uid, flag):
        async with self.txn() as c:
            cur = await c.execute("UPDATE users SET banned=? WHERE user_id=?", (int(flag), uid))
            return cur.rowcount > 0

    async def user_stats(self, uid):
        a = await self.one("SELECT COUNT(*) n FROM stock WHERE sold=1 AND sold_to=?", (uid,))
        b = await self.one("SELECT COALESCE(SUM(-amount),0) n FROM transactions WHERE user_id=? AND type='purchase'", (uid,))
        c = await self.one("SELECT COALESCE(SUM(amount),0) n FROM deposits WHERE user_id=? AND status='approved'", (uid,))
        return a["n"], b["n"], c["n"]

    @staticmethod
    async def _tx(c, uid, type_, amount, balance_after, note=""):
        await c.execute(
            "INSERT INTO transactions(user_id,type,amount,balance_after,note) VALUES(?,?,?,?,?)",
            (uid, type_, amount, balance_after, note)
        )

    async def change_balance(self, uid, delta, type_, note=""):
        async with self.txn() as c:
            u = await q1(c, "SELECT balance FROM users WHERE user_id=?", (uid,))
            if u is None:
                return None
            new = round(u["balance"] + delta, 2)
            if new < 0:
                return None
            await c.execute("UPDATE users SET balance=? WHERE user_id=?", (new, uid))
            await self._tx(c, uid, type_, delta, new, note)
            return new

    async def history(self, uid, limit=10):
        return await self.many("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit))

    async def set_referrer(self, new_id, ref_id):
        if new_id == ref_id:
            return False
        async with self.txn() as c:
            u = await q1(c, "SELECT referred_by FROM users WHERE user_id=?", (new_id,))
            r = await q1(c, "SELECT user_id FROM users WHERE user_id=?", (ref_id,))
            if u is None or r is None or u["referred_by"] is not None:
                return False
            await c.execute("UPDATE users SET referred_by=? WHERE user_id=?", (ref_id, new_id))
            await c.execute("UPDATE users SET ref_count=ref_count+1 WHERE user_id=?", (ref_id,))
            return True

    async def pay_referral(self, uid):
        async with self.txn() as c:
            u = await q1(c, "SELECT referred_by, ref_paid FROM users WHERE user_id=?", (uid,))
            if not u or not u["referred_by"] or u["ref_paid"] or REFERRAL_BONUS <= 0:
                return None
            ref_id = u["referred_by"]
            r = await q1(c, "SELECT balance FROM users WHERE user_id=?", (ref_id,))
            if not r:
                return None
            new = round(r["balance"] + REFERRAL_BONUS, 2)
            await c.execute("UPDATE users SET ref_paid=1 WHERE user_id=?", (uid,))
            await c.execute("UPDATE users SET balance=?, ref_earnings=ref_earnings+? WHERE user_id=?", (new, REFERRAL_BONUS, ref_id))
            await self._tx(c, ref_id, "referral", REFERRAL_BONUS, new, f"referred user {uid}")
            return {"referrer_id": ref_id, "bonus": REFERRAL_BONUS, "balance": new}

    async def categories(self, only_available=False):
        if only_available:
            return await self.many(
                "SELECT DISTINCT c.* FROM categories c JOIN products p ON p.category_id=c.id AND p.active=1 ORDER BY c.id"
            )
        return await self.many("SELECT * FROM categories ORDER BY id")

    async def get_category(self, cid):
        return await self.one("SELECT * FROM categories WHERE id=?", (cid,))

    async def add_category(self, name):
        try:
            async with self.txn() as c:
                cur = await c.execute("INSERT INTO categories(name) VALUES(?)", (name,))
                return cur.lastrowid
        except aiosqlite.IntegrityError:
            return None

    async def delete_category(self, cid):
        async with self.txn() as c:
            cur = await c.execute("DELETE FROM categories WHERE id=?", (cid,))
            return cur.rowcount > 0

    async def add_product(self, cid, name, price, desc=""):
        async with self.txn() as c:
            if not await q1(c, "SELECT id FROM categories WHERE id=?", (cid,)):
                return None
            cur = await c.execute(
                "INSERT INTO products(category_id,name,description,price) VALUES(?,?,?,?)",
                (cid, name, desc, price)
            )
            return cur.lastrowid

    async def delete_product(self, pid):
        async with self.txn() as c:
            cur = await c.execute("DELETE FROM products WHERE id=?", (pid,))
            return cur.rowcount > 0

    async def adjust_price(self, pid, mode, value):
        async with self.txn() as c:
            p = await q1(c, "SELECT price FROM products WHERE id=?", (pid,))
            if not p:
                return None
            new = calc_price(p["price"], mode, value)
            await c.execute("UPDATE products SET price=? WHERE id=?", (new, pid))
            return p["price"], new

    async def products(self, cid=None, only_active=True):
        sql = "SELECT p.*, (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.sold=0) AS stock FROM products p WHERE 1=1"
        params = []
        if cid is not None:
            sql += " AND p.category_id=?"
            params.append(cid)
        if only_active:
            sql += " AND p.active=1"
        return await self.many(sql + " ORDER BY p.id", tuple(params))

    async def get_product(self, pid):
        return await self.one(
            "SELECT p.*, (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.sold=0) AS stock FROM products p WHERE p.id=?",
            (pid,)
        )

    async def add_stock(self, pid, items):
        async with self.txn() as c:
            if not await q1(c, "SELECT id FROM products WHERE id=?", (pid,)):
                return None
            await c.executemany("INSERT INTO stock(product_id,content) VALUES(?,?)", [(pid, i) for i in items])
            return len(items)

    async def purchase_multi(self, uid, pid, qty: int):
        async with self.txn() as c:
            p = await q1(c, "SELECT * FROM products WHERE id=? AND active=1", (pid,))
            if not p:
                return {"status": "notfound"}
            u = await q1(c, "SELECT balance FROM users WHERE user_id=?", (uid,))
            stock_items = await qa(
                c, "SELECT id, content FROM stock WHERE product_id=? AND sold=0 ORDER BY id LIMIT ?", (pid, qty)
            )
            if len(stock_items) < qty:
                return {"status": "nostock", "product": p, "available": len(stock_items)}

            total_price = round(p["price"] * qty, 2)
            if u["balance"] + 1e-9 < total_price:
                return {"status": "nobalance", "product": p, "balance": u["balance"], "total": total_price}

            new_bal = round(u["balance"] - total_price, 2)
            contents = []
            for item in stock_items:
                await c.execute("UPDATE stock SET sold=1, sold_to=?, sold_at=datetime('now') WHERE id=?", (uid, item["id"]))
                contents.append(item["content"])

            await c.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, uid))
            await self._tx(c, uid, "purchase", -total_price, new_bal, f"{qty}x {p['name']} (#{p['id']})")
            return {"status": "ok", "product": p, "contents": contents, "balance": new_bal, "total": total_price, "qty": qty}

    async def payment_methods(self, active_only=False, kind=None):
        sql = "SELECT * FROM payment_methods WHERE 1=1"
        params = []
        if active_only:
            sql += " AND active=1"
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        return await self.many(sql + " ORDER BY id", tuple(params))

    async def get_pm(self, pid):
        return await self.one("SELECT * FROM payment_methods WHERE id=?", (pid,))

    async def add_pm(self, name, address, kind):
        async with self.txn() as c:
            cur = await c.execute(
                "INSERT INTO payment_methods(name,address,kind,active) VALUES(?,?,?,1)", (name, address, kind)
            )
            return cur.lastrowid

    async def set_pm_address(self, pid, address):
        async with self.txn() as c:
            cur = await c.execute("UPDATE payment_methods SET address=? WHERE id=?", (address, pid))
            return cur.rowcount > 0

    async def toggle_pm(self, pid):
        async with self.txn() as c:
            p = await q1(c, "SELECT active FROM payment_methods WHERE id=?", (pid,))
            if not p:
                return None
            new = 0 if p["active"] else 1
            await c.execute("UPDATE payment_methods SET active=? WHERE id=?", (new, pid))
            return new

    async def delete_pm(self, pid):
        async with self.txn() as c:
            cur = await c.execute("DELETE FROM payment_methods WHERE id=?", (pid,))
            return cur.rowcount > 0

    async def videos(self):
        return await self.many("SELECT * FROM help_videos ORDER BY id")

    async def get_video(self, vid):
        return await self.one("SELECT * FROM help_videos WHERE id=?", (vid,))

    async def add_video(self, title, kind, content):
        async with self.txn() as c:
            cur = await c.execute("INSERT INTO help_videos(title,kind,content) VALUES(?,?,?)", (title, kind, content))
            return cur.lastrowid

    async def delete_video(self, vid):
        async with self.txn() as c:
            cur = await c.execute("DELETE FROM help_videos WHERE id=?", (vid,))
            return cur.rowcount > 0

    async def create_deposit(self, uid, method, amount, trx_id):
        async with self.txn() as c:
            dup = await q1(c, "SELECT id FROM deposits WHERE method=? AND lower(trx_id)=lower(?) AND status!='rejected'", (method, trx_id))
            if dup:
                return None
            cur = await c.execute("INSERT INTO deposits(user_id,method,amount,trx_id) VALUES(?,?,?,?)", (uid, method, amount, trx_id))
            return cur.lastrowid

    async def pending_deposits(self):
        return await self.many("SELECT * FROM deposits WHERE status='pending' ORDER BY id")

    async def approve_deposit(self, dep_id, admin_id):
        async with self.txn() as c:
            d = await q1(c, "SELECT * FROM deposits WHERE id=?", (dep_id,))
            if not d or d["status"] != "pending":
                return None
            amt = round(float(d["amount"]), 2)
            await c.execute("UPDATE deposits SET status='approved', resolved_at=datetime('now'), resolved_by=? WHERE id=?", (admin_id, dep_id))
            u = await q1(c, "SELECT balance FROM users WHERE user_id=?", (d["user_id"],))
            new = round(u["balance"] + amt, 2)
            await c.execute("UPDATE users SET balance=? WHERE user_id=?", (new, d["user_id"]))
            await self._tx(c, d["user_id"], "deposit", amt, new, f"deposit #{dep_id} {d['method']}")
            return {"user_id": d["user_id"], "amount": amt, "balance": new}

    async def reject_deposit(self, dep_id, admin_id):
        async with self.txn() as c:
            d = await q1(c, "SELECT * FROM deposits WHERE id=?", (dep_id,))
            if not d or d["status"] != "pending":
                return None
            await c.execute("UPDATE deposits SET status='rejected', resolved_at=datetime('now'), resolved_by=? WHERE id=?", (admin_id, dep_id))
            return dict(d)

    async def create_usd_order(self, uid, direction, crypto_meth, fiat_meth, usd, bdt, details):
        async with self.txn() as c:
            if direction == "buy":
                u = await q1(c, "SELECT balance FROM users WHERE user_id=?", (uid,))
                if u is None or u["balance"] + 1e-9 < bdt:
                    return None
                new = round(u["balance"] - bdt, 2)
                await c.execute("UPDATE users SET balance=? WHERE user_id=?", (new, uid))
                cur = await c.execute(
                    "INSERT INTO dollar_orders(user_id,direction,crypto_meth,fiat_meth,usd_amount,bdt_amount,details) VALUES(?,?,?,?,?,?,?)",
                    (uid, direction, crypto_meth, fiat_meth, usd, bdt, details)
                )
                await self._tx(c, uid, "usd_buy", -bdt, new, f"dollar buy order #{cur.lastrowid}")
                return cur.lastrowid
            else:
                cur = await c.execute(
                    "INSERT INTO dollar_orders(user_id,direction,crypto_meth,fiat_meth,usd_amount,bdt_amount,details) VALUES(?,?,?,?,?,?,?)",
                    (uid, direction, crypto_meth, fiat_meth, usd, bdt, details)
                )
                return cur.lastrowid

    async def pending_usd_orders(self):
        return await self.many("SELECT * FROM dollar_orders WHERE status='pending' ORDER BY id")

    async def resolve_usd_order(self, oid, approve: bool):
        async with self.txn() as c:
            o = await q1(c, "SELECT * FROM dollar_orders WHERE id=?", (oid,))
            if not o or o["status"] != "pending":
                return None
            balance = None
            if approve:
                await c.execute("UPDATE dollar_orders SET status='done' WHERE id=?", (oid,))
                if o["direction"] == "sell":
                    u = await q1(c, "SELECT balance FROM users WHERE user_id=?", (o["user_id"],))
                    balance = round(u["balance"] + o["bdt_amount"], 2)
                    await c.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, o["user_id"]))
                    await self._tx(c, o["user_id"], "usd_sell", o["bdt_amount"], balance, f"dollar order #{oid}")
            else:
                await c.execute("UPDATE dollar_orders SET status='rejected' WHERE id=?", (oid,))
                if o["direction"] == "buy":
                    u = await q1(c, "SELECT balance FROM users WHERE user_id=?", (o["user_id"],))
                    balance = round(u["balance"] + o["bdt_amount"], 2)
                    await c.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, o["user_id"]))
                    await self._tx(c, o["user_id"], "refund", o["bdt_amount"], balance, f"dollar order #{oid} rejected")
            return {"order": dict(o), "balance": balance}

    async def stats(self):
        async with self.lock:
            c = self.conn
            return {
                "users": (await q1(c, "SELECT COUNT(*) n FROM users"))["n"],
                "banned": (await q1(c, "SELECT COUNT(*) n FROM users WHERE banned=1"))["n"],
                "balance": (await q1(c, "SELECT COALESCE(SUM(balance),0) n FROM users"))["n"],
                "deposited": (await q1(c, "SELECT COALESCE(SUM(amount),0) n FROM deposits WHERE status='approved'"))["n"],
                "pending_dep": (await q1(c, "SELECT COUNT(*) n FROM deposits WHERE status='pending'"))["n"],
                "pending_usd": (await q1(c, "SELECT COUNT(*) n FROM dollar_orders WHERE status='pending'"))["n"],
                "products": (await q1(c, "SELECT COUNT(*) n FROM products"))["n"],
                "stock": (await q1(c, "SELECT COUNT(*) n FROM stock WHERE sold=0"))["n"],
                "sales": (await q1(c, "SELECT COUNT(*) n FROM stock WHERE sold=1"))["n"],
                "revenue": (await q1(c, "SELECT COALESCE(SUM(-amount),0) n FROM transactions WHERE type='purchase'"))["n"],
            }

db = Database(DB_PATH)

def parse_amount(text: str):
    try:
        v = float(text.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
    if not math.isfinite(v) or v <= 0 or v > 10_000_000:
        return None
    return round(v, 2)

async def min_deposit() -> float:
    try:
        return float(await db.get_setting("min_deposit", MIN_DEPOSIT))
    except ValueError:
        return MIN_DEPOSIT

def norm_link(s: str):
    s = (s or "").strip()
    if s.startswith("@"):
        s = "https://t.me/" + s[1:]
    elif s.startswith("t.me/"):
        s = "https://" + s
    return s if re.match(r"^https?://\S+$", s) else None

def norm_phone(text: str):
    s = re.sub(r"[\s\-+]", "", text or "")
    return s if s.isdigit() and 10 <= len(s) <= 15 else None

SUP_RE = re.compile(r"^[A-Za-z0-9_]{3,64}$")

async def safe_edit(msg: Message, text: str, kb=None):
    try:
        await msg.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "not modified" not in str(e).lower():
            log.warning("edit failed: %s", e)

async def notify_admins(bot: Bot, text: str, kb=None):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text, reply_markup=kb)
        except Exception as e:
            log.warning("cannot notify admin %s: %s", aid, e)

async def notify_user(bot: Bot, uid: int, text: str):
    try:
        await bot.send_message(uid, text)
        return True
    except Exception as e:
        log.info("cannot notify user %s: %s", uid, e)
        return False

def user_link(uid, name):
    return f'<a href="tg://user?id={uid}">{esc(name)}</a>'

async def animate(message: Message, frames, final_text, kb=None, delay=0.45):
    sent = await message.answer(frames[0])
    for f in frames[1:]:
        await asyncio.sleep(delay)
        await safe_edit(sent, f)
    await asyncio.sleep(delay)
    await safe_edit(sent, final_text, kb)
    return sent

def lang_kb():
    b = InlineKeyboardBuilder()
    b.button(text="বাংলা 🇧🇩", callback_data="lang:bn")
    b.adjust(1)
    return b.as_markup()

def main_menu_kb(lang):
    b = ReplyKeyboardBuilder()
    for k in MENU_KEYS:
        b.button(text=t(lang, k))
    b.adjust(2, 2, 2, 1)
    return b.as_markup(resize_keyboard=True)

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        tg = data.get("event_from_user")
        if tg is None or tg.is_bot:
            return await handler(event, data)
        user = await db.get_user(tg.id)
        is_new = False
        if user is None:
            await db.create_user(tg.id, tg.username, tg.full_name)
            user = await db.get_user(tg.id)
            is_new = True
        elif user["username"] != tg.username or user["full_name"] != tg.full_name:
            await db.update_profile(tg.id, tg.username, tg.full_name)
        if user["banned"] and not is_admin_id(tg.id):
            if isinstance(event, Message):
                await event.answer(t(user["lang"], "banned"))
            elif isinstance(event, CallbackQuery):
                await event.answer(t(user["lang"], "banned"), show_alert=True)
            return
        data["user"] = user
        data["is_new"] = is_new
        data["lang"] = user["lang"] or "bn"
        return await handler(event, data)

class DepositSt(StatesGroup):
    amount = State()
    trx = State()

class BuyQtySt(StatesGroup):
    custom_qty = State()

class UsdOrderSt(StatesGroup):
    amount = State()
    method = State()
    trx = State()
    fiat = State()
    number = State()
    details = State()

class AdminSt(StatesGroup):
    cat_name = State()
    prod_name = State()
    prod_price = State()
    prod_desc = State()
    price_set = State()
    stock_add = State()
    setting_edit = State()
    pm_new_name = State()
    pm_new_kind = State()
    pm_new_addr = State()
    pm_edit_addr = State()
    vid_title = State()
    vid_content = State()
    user_find = State()
    bal_amount = State()
    user_msg = State()

UT = (F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_TEXTS))

user_router = Router(name="user")

@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, is_new: bool, bot: Bot):
    await state.clear()
    if is_new and command.args and command.args.startswith("ref_"):
        try:
            ref_id = int(command.args[4:])
        except ValueError:
            ref_id = None
        if ref_id and await db.set_referrer(message.from_user.id, ref_id):
            res = await db.pay_referral(message.from_user.id)
            if res:
                await notify_user(bot, res["referrer_id"], f"🎁 রেফার বোনাস! আপনি {fmt(res['bonus'])} {CURRENCY} পেয়েছেন।\n💼 নতুন ব্যালেন্স: {fmt(res['balance'])} {CURRENCY}")
    await message.answer(WELCOME_MULTI.format(name=esc(message.from_user.full_name)), reply_markup=lang_kb())

@user_router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery):
    lang = call.data.split(":", 1)[1]
    if lang not in T:
        return await call.answer()
    await db.set_lang(call.from_user.id, lang)
    await call.answer()
    await safe_edit(call.message, t(lang, "lang_saved"))
    await call.message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

@user_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(t(lang, "cancelled"), reply_markup=main_menu_kb(lang))

@user_router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

@user_router.callback_query(F.data == "main_menu_back")
async def cb_main_menu_back(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, t(lang, "main_menu"))

@user_router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()

async def categories_view(lang):
    cats = await db.categories(only_available=True)
    if not cats:
        return t(lang, "no_categories"), None
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"{c['name']}", callback_data=f"cat:{c['id']}")
    b.button(text=t(lang, "back"), callback_data="main_menu_back")
    b.adjust(1)
    return t(lang, "choose_category"), b.as_markup()

async def product_view(p, qty: int, lang: str):
    stock = p["stock"]
    qty = max(1, min(qty, stock)) if stock > 0 else 1
    total = round(p["price"] * qty, 2)
    desc = f"\n📝 {esc(p['description'])}\n" if p["description"] else "\n"
    text = t(lang, "product_detail", name=esc(p["name"]), desc=desc, price=fmt(p["price"]),
             cur=CURRENCY, stock=stock, qty=qty, total=fmt(total))
    if stock <= 0:
        text += "\n\n❌ <b>স্টক শেষ</b>"
    b = InlineKeyboardBuilder()
    if stock > 0:
        pid = p["id"]
        b.button(text="➖", callback_data=f"qty:{pid}:{qty - 1}")
        b.button(text=f"📦 {qty}", callback_data="noop")
        b.button(text="➕", callback_data=f"qty:{pid}:{qty + 1}")
        b.button(text="Custom Quantity", callback_data=f"custqty:{pid}")
        b.button(text=f"✅ কনফার্ম ({fmt(total)} {CURRENCY})", callback_data=f"buyfin:{pid}:{qty}")
        b.button(text=t(lang, "back"), callback_data=f"cat:{p['category_id']}")
        b.adjust(3, 1, 1, 1)
    else:
        b.button(text=t(lang, "back"), callback_data=f"cat:{p['category_id']}")
        b.adjust(1)
    return text, b.as_markup()

@user_router.message(F.text.in_(all_texts("btn_buy")))
async def m_buy(message: Message, state: FSMContext, lang: str):
    await state.clear()
    text, kb = await categories_view(lang)
    await message.answer(text, reply_markup=kb)

@user_router.callback_query(F.data == "cats")
async def cb_cats(call: CallbackQuery, lang: str):
    text, kb = await categories_view(lang)
    await call.answer()
    await safe_edit(call.message, text, kb)

@user_router.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    cid = int(call.data.split(":")[1])
    cat = await db.get_category(cid)
    prods = await db.products(cid)
    await call.answer()
    if not cat or not prods:
        b = InlineKeyboardBuilder()
        b.button(text=t(lang, "back"), callback_data="cats")
        return await safe_edit(call.message, t(lang, "no_products"), b.as_markup())
    b = InlineKeyboardBuilder()
    for p in prods:
        mark = "" if p["stock"] > 0 else " ❌"
        b.button(text=f"{p['name']} | {fmt(p['price'])} {CURRENCY} | {p['stock']}{mark}", callback_data=f"prod:{p['id']}")
    b.button(text=t(lang, "back"), callback_data="cats")
    b.adjust(1)
    await safe_edit(call.message, t(lang, "choose_product", cat=esc(cat["name"])), b.as_markup())

@user_router.callback_query(F.data.startswith("prod:"))
async def cb_product(call: CallbackQuery, lang: str):
    pid = int(call.data.split(":")[1])
    p = await db.get_product(pid)
    await call.answer()
    if not p or not p["active"]:
        return await safe_edit(call.message, t(lang, "buy_notfound"))
    text, kb = await product_view(p, 1, lang)
    await safe_edit(call.message, text, kb)

@user_router.callback_query(F.data.startswith("qty:"))
async def cb_change_qty(call: CallbackQuery, lang: str):
    _, pid_s, qty_s = call.data.split(":")
    pid, qty = int(pid_s), int(qty_s)
    p = await db.get_product(pid)
    if not p or not p["active"]:
        return await call.answer(t(lang, "buy_notfound"), show_alert=True)
    if p["stock"] > 0 and qty > p["stock"]:
        await call.answer("⚠️ সর্বোচ্চ স্টক পর্যন্ত কিনতে পারবেন।")
    else:
        await call.answer()
    text, kb = await product_view(p, qty, lang)
    await safe_edit(call.message, text, kb)

@user_router.callback_query(F.data.startswith("custqty:"))
async def cb_cust_qty(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(BuyQtySt.custom_qty)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("✏️ কাঙ্ক্ষিত পরিমাণ (Quantity) লিখুন:\n(বাতিল করতে /cancel)")

@user_router.message(BuyQtySt.custom_qty, *UT)
async def msg_custom_qty(message: Message, state: FSMContext, lang: str):
    if not message.text.strip().isdigit() or int(message.text.strip()) < 1:
        return await message.answer("⚠️ দয়া করে সঠিক সংখ্যা লিখুন।")
    qty = int(message.text.strip())
    pid = (await state.get_data()).get("pid")
    await state.clear()
    p = await db.get_product(pid)
    if not p or not p["active"]:
        return await message.answer(t(lang, "buy_notfound"))
    if p["stock"] <= 0:
        return await message.answer(t(lang, "buy_nostock"))
    if qty > p["stock"]:
        await message.answer(f"⚠️ স্টকে মাত্র {p['stock']} টি আছে, তাই সর্বোচ্চ পরিমাণ সেট করা হয়েছে।")
    text, kb = await product_view(p, qty, lang)
    await message.answer(text, reply_markup=kb)

async def send_purchase(target: Message, lang: str, p, qty: int, res: dict):
    head = t(lang, "buy_ok", name=esc(p["name"]), qty=qty, total=fmt(res["total"]), cur=CURRENCY, balance=fmt(res["balance"]))
    head += "\n\n🔑 <b>আপনার প্রোডাক্ট/সার্ভিস:</b>\n"
    chunks, cur_chunk = [], ""
    for c in res["contents"]:
        item = f"<code>{esc(c)}</code>\n"
        if cur_chunk and len(cur_chunk) + len(item) > 3500:
            chunks.append(cur_chunk)
            cur_chunk = ""
        cur_chunk += item
    if cur_chunk:
        chunks.append(cur_chunk)
    for i, ch in enumerate(chunks):
        await target.answer((head + ch) if i == 0 else ch)

@user_router.callback_query(F.data.startswith("buyfin:"))
async def cb_buy_final(call: CallbackQuery, lang: str):
    _, pid_s, qty_s = call.data.split(":")
    pid, qty = int(pid_s), int(qty_s)
    res = await db.purchase_multi(call.from_user.id, pid, qty)
    st = res["status"]
    if st == "notfound":
        return await call.answer(t(lang, "buy_notfound"), show_alert=True)
    if st == "nostock":
        return await call.answer(t(lang, "buy_nostock"), show_alert=True)
    if st == "nobalance":
        await call.answer()
        b = InlineKeyboardBuilder()
        b.button(text="Deposit", callback_data="m_dep_menu")
        b.button(text="Back", callback_data=f"cat:{res['product']['category_id']}")
        b.adjust(2)
        return await safe_edit(call.message, t(
            lang, "buy_nobalance", balance=fmt(res["balance"]), total=fmt(res["total"]),
            need=fmt(res["total"] - res["balance"]), cur=CURRENCY), b.as_markup())

    p = res["product"]
    await call.answer("✅")
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await send_purchase(call.message, lang, p, qty, res)

@user_router.message(F.text.in_(all_texts("btn_profile")))
async def m_profile(message: Message, state: FSMContext, lang: str):
    await state.clear()
    u = await db.get_user(message.from_user.id)
    items, spent, dep = await db.user_stats(u["user_id"])
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "history_btn"), callback_data="hist")
    await message.answer(t(
        lang, "profile", uid=u["user_id"], name=esc(u["full_name"]), balance=fmt(u["balance"]),
        cur=CURRENCY, items=items, spent=fmt(spent), dep=fmt(dep), refs=u["ref_count"],
        earn=fmt(u["ref_earnings"]), joined=esc(u["created_at"][:10])),
        reply_markup=b.as_markup())

@user_router.callback_query(F.data == "hist")
async def cb_history(call: CallbackQuery, lang: str):
    rows = await db.history(call.from_user.id, 10)
    await call.answer()
    if not rows:
        return await call.message.answer(t(lang, "history_empty"))
    lines = []
    for r in rows:
        sign = "➕" if r["amount"] >= 0 else "➖"
        lines.append(f"{sign} <b>{fmt(abs(r['amount']))} {CURRENCY}</b> • {esc(r['type'])}\n    {esc(r['note'])}")
    await call.message.answer(t(lang, "history_title") + "\n".join(lines))

async def deposit_menu_view(lang):
    methods = await db.payment_methods(active_only=True)
    b = InlineKeyboardBuilder()
    if not methods:
        b.button(text=t(lang, "back"), callback_data="main_menu_back")
        b.adjust(1)
        return "😔 এই মুহূর্তে কোনো পেমেন্ট মেথড চালু নেই। সাপোর্টে যোগাযোগ করুন।", b.as_markup()
    for m in methods:
        b.button(text=m["name"], callback_data=f"dep:{m['id']}")
    b.button(text=t(lang, "back"), callback_data="main_menu_back")
    sizes = [2] * (len(methods) // 2) + ([1] if len(methods) % 2 else []) + [1]
    b.adjust(*sizes)
    return t(lang, "dep_choose"), b.as_markup()

@user_router.message(F.text.in_(all_texts("btn_deposit")))
async def m_deposit(message: Message, state: FSMContext, lang: str):
    await state.clear()
    text, kb = await deposit_menu_view(lang)
    await message.answer(text, reply_markup=kb)

@user_router.callback_query(F.data == "m_dep_menu")
async def cb_m_dep_menu(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await call.answer()
    text, kb = await deposit_menu_view(lang)
    await safe_edit(call.message, text, kb)

@user_router.callback_query(F.data.startswith("dep:"))
async def cb_dep_method(call: CallbackQuery, state: FSMContext, lang: str):
    m = await db.get_pm(int(call.data.split(":")[1]))
    if not m or not m["active"]:
        return await call.answer("⛔ এই মেথডটি এখন বন্ধ আছে।", show_alert=True)
    await state.clear()
    await state.set_state(DepositSt.amount)
    await state.update_data(method_id=m["id"], method_name=m["name"])
    await call.answer()
    await call.message.answer(t(lang, "dep_instr", method=esc(m["name"]), address=esc(m["address"]),
                                min=fmt(await min_deposit()), cur=CURRENCY))

@user_router.message(DepositSt.amount, *UT)
async def dep_amount(message: Message, state: FSMContext, lang: str):
    amount = parse_amount(message.text)
    mind = await min_deposit()
    if amount is None:
        return await message.answer("⚠️ সঠিক পরিমাণ লিখুন (সংখ্যায়)।")
    if amount < mind:
        return await message.answer(f"⚠️ সর্বনিম্ন ডিপোজিট {fmt(mind)} {CURRENCY}।")
    await state.update_data(amount=amount)
    await state.set_state(DepositSt.trx)
    await message.answer(t(lang, "dep_ask_trx"))

@user_router.message(DepositSt.trx, *UT)
async def dep_trx(message: Message, state: FSMContext, lang: str, bot: Bot):
    trx = message.text.strip()
    if not (3 <= len(trx) <= 120):
        return await message.answer("⚠️ সঠিক Transaction ID লিখুন।")
    data = await state.get_data()
    dep_id = await db.create_deposit(message.from_user.id, data["method_name"], data["amount"], trx)
    if dep_id is None:
        return await message.answer("⚠️ এই Transaction ID আগে ব্যবহার করা হয়েছে।")
    await state.clear()
    await message.answer(
        f"✅ ডিপোজিট রিকোয়েস্ট জমা হয়েছে!\n\n🆔 রিকোয়েস্ট: #{dep_id}\n💎 পরিমাণ: {fmt(data['amount'])} {CURRENCY}\n\nঅ্যাডমিন যাচাই করে ব্যালেন্সে যোগ করবেন।",
        reply_markup=main_menu_kb(lang))

    b = InlineKeyboardBuilder()
    b.button(text="✅ Approve", callback_data=f"admindep_ok:{dep_id}")
    b.button(text="❌ Reject", callback_data=f"admindep_no:{dep_id}")
    b.adjust(2)
    await notify_admins(bot, (
        f"💳 <b>New Deposit #{dep_id}</b>\n"
        f"👤 {user_link(message.from_user.id, message.from_user.full_name)} (<code>{message.from_user.id}</code>)\n"
        f"🏦 {esc(data['method_name'])}\n💎 {fmt(data['amount'])} {CURRENCY}\n🧾 TrxID: <code>{esc(trx)}</code>"), b.as_markup())

@user_router.message(F.text.in_(all_texts("btn_ref")))
async def m_ref(message: Message, state: FSMContext, lang: str):
    await state.clear()
    u = await db.get_user(message.from_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{u['user_id']}"
    final = (
        "✨ <b>আপনার রেফারেল লিংক তৈরি!</b>\n\n"
        f"🔗 <code>{esc(link)}</code>\n\n"
        f"👥 মোট রেফার: <b>{u['ref_count']}</b>\n"
        f"🎁 রেফার আয়: <b>{fmt(u['ref_earnings'])} {CURRENCY}</b>\n\n"
        "📤 নিচের বাটনে চাপ দিয়ে বন্ধুদের শেয়ার করুন!"
    )
    share = "https://t.me/share/url?url=" + quote(link, safe="") + "&text=" + quote("🎁 এই বটে জয়েন করুন!", safe="")
    b = InlineKeyboardBuilder()
    b.button(text="📤 শেয়ার করুন", url=share)
    b.adjust(1)
    frames = [
        "🔗 লিংক তৈরি হচ্ছে...\n▱▱▱▱▱",
        "🔗 লিংক তৈরি হচ্ছে...\n▰▱▱▱▱",
        "🔗 লিংক তৈরি হচ্ছে...\n▰▰▱▱▱",
        "🔗 লিংক তৈরি হচ্ছে...\n▰▰▰▱▱",
        "🔗 লিংক তৈরি হচ্ছে...\n▰▰▰▰▱",
        "🔗 লিংক তৈরি হচ্ছে...\n▰▰▰▰▰ ✅",
    ]
    await animate(message, frames, final, b.as_markup(), delay=0.35)

@user_router.message(F.text.in_(all_texts("btn_support")))
async def m_support(message: Message, state: FSMContext, lang: str):
    await state.clear()
    sup = await db.get_setting("support_username", DEFAULT_SUPPORT)
    channel = await db.get_setting("channel_link", "")
    b = InlineKeyboardBuilder()
    if SUP_RE.match(sup or ""):
        b.button(text="💬 সাপোর্টে মেসেজ করুন", url=f"https://t.me/{sup}")
    if channel and norm_link(channel):
        b.button(text="📢 আমাদের চ্যানেল", url=channel)
    b.adjust(1)
    final = t(lang, "support_text", admin=esc(sup))
    frames = [
        "🎧 সাপোর্ট টিমের সাথে কানেক্ট হচ্ছে\n🟢⚪⚪",
        "🎧 সাপোর্ট টিমের সাথে কানেক্ট হচ্ছে\n🟢🟢⚪",
        "🎧 সাপোর্ট টিমের সাথে কানেক্ট হচ্ছে\n🟢🟢🟢",
        "✅ কানেক্টেড!",
    ]
    await animate(message, frames, final, b.as_markup() if (SUP_RE.match(sup or "") or channel) else None, delay=0.45)

async def send_help_video(target: Message, v):
    title = f"🎬 <b>{esc(v['title'])}</b>"
    try:
        if v["kind"] == "video":
            await target.answer_video(v["content"], caption=title)
        elif v["kind"] == "animation":
            await target.answer_animation(v["content"], caption=title)
        elif v["kind"] == "document":
            await target.answer_document(v["content"], caption=title)
        else:
            await target.answer(f"{title}\n\n🔗 {esc(v['content'])}")
    except Exception as e:
        log.warning("send help video failed: %s", e)
        await target.answer("⚠️ ভিডিওটি পাঠানো যায়নি। সাপোর্টে যোগাযোগ করুন।")

@user_router.message(F.text.in_(all_texts("btn_help")))
async def m_help(message: Message, state: FSMContext, lang: str):
    await state.clear()
    vids = await db.videos()
    if not vids:
        return await message.answer("🙋‍♂️ এখনো কোনো টিউটোরিয়াল ভিডিও যোগ করা হয়নি। কোনো সমস্যা হলে সাপোর্টে যোগাযোগ করুন।")
    if len(vids) == 1:
        return await send_help_video(message, vids[0])
    b = InlineKeyboardBuilder()
    for v in vids:
        b.button(text=f"🎬 {v['title']}", callback_data=f"help:{v['id']}")
    b.adjust(1)
    await message.answer(t(lang, "help_text"), reply_markup=b.as_markup())

@user_router.callback_query(F.data.startswith("help:"))
async def cb_help(call: CallbackQuery):
    v = await db.get_video(int(call.data.split(":")[1]))
    if not v:
        return await call.answer("ভিডিওটি পাওয়া যায়নি।", show_alert=True)
    await call.answer()
    await send_help_video(call.message, v)

@user_router.message(F.text.in_(all_texts("btn_dollar")))
async def m_dollar(message: Message, state: FSMContext, lang: str):
    await state.clear()
    buy, sell = await db.rates()
    u = await db.get_user(message.from_user.id)
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "usd_buy_btn"), callback_data="usd:buy")
    b.button(text=t(lang, "usd_sell_btn"), callback_data="usd:sell")
    b.adjust(2)
    await message.answer(t(lang, "usd_menu", buy=fmt(buy), sell=fmt(sell), cur=CURRENCY, balance=fmt(u["balance"])), reply_markup=b.as_markup())

@user_router.callback_query(F.data.in_({"usd:buy", "usd:sell"}))
async def cb_usd_dir(call: CallbackQuery, state: FSMContext):
    direction = "buy" if call.data == "usd:buy" else "sell"
    buy_rate, sell_rate = await db.rates()
    rate = sell_rate if direction == "buy" else buy_rate
    await state.clear()
    await state.update_data(direction=direction)
    await state.set_state(UsdOrderSt.amount)
    await call.answer()
    title = "🟢 ডলার কিনুন" if direction == "buy" else "🔴 ডলার বিক্রি করুন"
    await call.message.answer(f"<b>{title}</b>\n\nকত USD করতে চান? (সর্বনিম্ন {fmt(MIN_USD)} USD)\n💱 রেট: 1 USD = <b>{fmt(rate)} {CURRENCY}</b>\n(বাতিল করতে /cancel)")

@user_router.message(UsdOrderSt.amount, *UT)
async def usd_order_amount(message: Message, state: FSMContext):
    usd = parse_amount(message.text)
    if usd is None or usd < MIN_USD:
        return await message.answer(f"⚠️ সঠিক পরিমাণ দিন (সর্বনিম্ন {fmt(MIN_USD)} USD)।")

    buy_rate, sell_rate = await db.rates()
    data = await state.get_data()
    direction = data.get("direction")
    rate = sell_rate if direction == "buy" else buy_rate
    bdt = round(usd * rate, 2)

    if direction == "buy":
        u = await db.get_user(message.from_user.id)
        if u["balance"] + 1e-9 < bdt:
            await state.clear()
            return await message.answer(f"❌ ব্যালেন্স অপর্যাপ্ত। প্রয়োজন: {fmt(bdt)} {CURRENCY}\n💼 আপনার ব্যালেন্স: {fmt(u['balance'])} {CURRENCY}")

    methods = await db.payment_methods(active_only=True, kind="crypto")
    if not methods:
        await state.clear()
        return await message.answer("😔 এই মুহূর্তে কোনো ক্রিপ্টো মেথড চালু নেই।")
    await state.update_data(usd=usd, bdt=bdt)
    await state.set_state(UsdOrderSt.method)
    b = InlineKeyboardBuilder()
    for m in methods:
        b.button(text=m["name"], callback_data=f"usdcrypto:{m['id']}")
    b.adjust(1)
    await message.answer(f"💵 {fmt(usd)} USD = <b>{fmt(bdt)} {CURRENCY}</b>\n\nমেথড সিলেক্ট করুন:", reply_markup=b.as_markup())

@user_router.callback_query(F.data.startswith("usdcrypto:"))
async def cb_usd_crypto(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "usd" not in data or "direction" not in data:
        return await call.answer("⏳ সেশন শেষ। আবার শুরু করুন।", show_alert=True)
    m = await db.get_pm(int(call.data.split(":")[1]))
    if not m or not m["active"]:
        return await call.answer("⛔ এই মেথডটি এখন বন্ধ আছে।", show_alert=True)
    cm = m["name"]
    await state.update_data(crypto_meth=cm)
    await call.answer()

    if data.get("direction") == "buy":
        await state.set_state(UsdOrderSt.details)
        await call.message.answer(f"📬 আপনার <b>{esc(cm)}</b> ওয়ালেট অ্যাড্রেস / UID দিন:\n(বাতিল করতে /cancel)")
    else:
        await state.set_state(UsdOrderSt.trx)
        await call.message.answer(
            f"📤 নিচের <b>{esc(cm)}</b> ঠিকানায় <b>{fmt(data['usd'])} USD</b> পাঠান:\n"
            f"<code>{esc(m['address'])}</code>\n\n"
            f"💰 আপনি পাবেন: <b>{fmt(data['bdt'])} {CURRENCY}</b>\n\n"
            f"পাঠানোর পর Transaction ID (TXID) দিন:\n(বাতিল করতে /cancel)")

@user_router.message(UsdOrderSt.trx, *UT)
async def usd_sell_trx(message: Message, state: FSMContext):
    trx = message.text.strip()
    if not (4 <= len(trx) <= 200):
        return await message.answer("⚠️ সঠিক Transaction ID লিখুন।")
    await state.update_data(trx=trx)
    await state.set_state(UsdOrderSt.fiat)
    b = InlineKeyboardBuilder()
    for fm in FIAT_PAYMENT_METHODS:
        b.button(text=fm, callback_data=f"usdfiat:{fm}")
    b.adjust(3)
    await message.answer("💳 কোন মাধ্যমে টাকা রিসিভ করতে চান?", reply_markup=b.as_markup())

@user_router.callback_query(F.data.startswith("usdfiat:"))
async def cb_usd_fiat(call: CallbackQuery, state: FSMContext):
    fm = call.data.split(":", 1)[1]
    data = await state.get_data()
    if fm not in FIAT_PAYMENT_METHODS or "trx" not in data:
        return await call.answer("⏳ সেশন শেষ। আবার শুরু করুন।", show_alert=True)
    await state.update_data(fiat_meth=fm)
    await state.set_state(UsdOrderSt.number)
    await call.answer()
    await call.message.answer(f"📱 আপনার <b>{esc(fm)}</b> নাম্বার দিন:\n(বাতিল করতে /cancel)")

async def usd_finalize(message: Message, state: FSMContext, lang: str, bot: Bot, details: str):
    data = await state.get_data()
    oid = await db.create_usd_order(message.from_user.id, data["direction"], data["crypto_meth"],
                                    data.get("fiat_meth", "Auto"), data["usd"], data["bdt"], details)
    await state.clear()
    if oid is None:
        return await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই।", reply_markup=main_menu_kb(lang))

    await message.answer(f"✅ ডলার অর্ডার #{oid} জমা হয়েছে। অ্যাডমিন যাচাই করে প্রসেস করবেন।", reply_markup=main_menu_kb(lang))
    b = InlineKeyboardBuilder()
    b.button(text="✅ Complete", callback_data=f"adminusd_ok:{oid}")
    b.button(text="❌ Reject", callback_data=f"adminusd_no:{oid}")
    b.adjust(2)
    await notify_admins(bot, (
        f"💵 <b>Dollar {data['direction'].upper()} Order #{oid}</b>\n"
        f"👤 {user_link(message.from_user.id, message.from_user.full_name)} (<code>{message.from_user.id}</code>)\n"
        f"🔹 {esc(data['crypto_meth'])} / {esc(data.get('fiat_meth', 'Auto'))}\n"
        f"💵 USD: <b>{fmt(data['usd'])}</b> | {CURRENCY}: <b>{fmt(data['bdt'])}</b>\n"
        f"📬 Details:\n<code>{esc(details)}</code>"), b.as_markup())

@user_router.message(UsdOrderSt.number, *UT)
async def usd_sell_number(message: Message, state: FSMContext, lang: str, bot: Bot):
    num = norm_phone(message.text)
    if num is None:
        return await message.answer("⚠️ সঠিক মোবাইল নাম্বার দিন।")
    data = await state.get_data()
    details = f"TXID: {data.get('trx', '-')}\n{data.get('fiat_meth', '')} Number: {num}"
    await usd_finalize(message, state, lang, bot, details)

@user_router.message(UsdOrderSt.details, *UT)
async def usd_buy_details(message: Message, state: FSMContext, lang: str, bot: Bot):
    d = message.text.strip()[:500]
    if len(d) < 3:
        return await message.answer("⚠️ সঠিক ওয়ালেট অ্যাড্রেস / UID দিন।")
    await usd_finalize(message, state, lang, bot, f"Wallet/UID: {d}")

admin_router = Router(name="admin")
admin_router.message.filter(lambda m: m.from_user is not None and is_admin_id(m.from_user.id))
admin_router.callback_query.filter(lambda c: c.from_user is not None and is_admin_id(c.from_user.id))

AT = UT
ADMIN_TITLE = "🛠 <b>Admin Control Panel</b>"

def admin_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📊 Stats", callback_data="apanel:stats")
    b.button(text="⏳ Deposits", callback_data="apanel:deposits")
    b.button(text="💵 Dollar Orders", callback_data="apanel:usds")
    b.button(text="📦 Products", callback_data="apanel:products")
    b.button(text="💳 Payment Methods", callback_data="apanel:pay_methods")
    b.button(text="💲 Rates & Support", callback_data="apanel:rates_supp")
    b.button(text="👥 Users", callback_data="apanel:users")
    b.button(text="🎬 আমি নতুন (ভিডিও)", callback_data="apanel:help")
    b.adjust(2, 2, 2, 2)
    return b.as_markup()

def cancel_kb():
    b = InlineKeyboardBuilder()
    b.button(text="❌ Cancel", callback_data="acancel")
    return b.as_markup()

def back_kb(cb="apanel:main", text="⬅️ Back"):
    b = InlineKeyboardBuilder()
    b.button(text=text, callback_data=cb)
    return b.as_markup()

@admin_router.message(Command("admin", "panel"))
async def a_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(ADMIN_TITLE, reply_markup=admin_menu_kb())

@admin_router.callback_query(F.data == "apanel:main")
async def cb_apanel_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, ADMIN_TITLE, admin_menu_kb())

@admin_router.callback_query(F.data == "acancel")
async def cb_acancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Cancelled ❎")
    await safe_edit(call.message, ADMIN_TITLE, admin_menu_kb())

@admin_router.callback_query(F.data == "apanel:stats")
async def cb_apanel_stats(call: CallbackQuery):
    s = await db.stats()
    buy, sell = await db.rates()
    text = (
        "📊 <b>Statistics</b>\n\n"
        f"👥 Users: {s['users']} (Banned: {s['banned']})\n"
        f"💼 Total Balance: {fmt(s['balance'])} {CURRENCY}\n"
        f"💳 Total Deposited: {fmt(s['deposited'])} {CURRENCY}\n"
        f"🛒 Sales: {s['sales']} • Revenue: {fmt(s['revenue'])} {CURRENCY}\n"
        f"📦 Products: {s['products']} • Stock: {s['stock']}\n"
        f"⏳ Pending Deposits: {s['pending_dep']} • Dollar Orders: {s['pending_usd']}\n"
        f"💵 Rates: Buy {fmt(sell)} / Sell {fmt(buy)}"
    )
    await call.answer()
    await safe_edit(call.message, text, back_kb())

@admin_router.callback_query(F.data == "apanel:deposits")
async def cb_apanel_deposits(call: CallbackQuery):
    rows = await db.pending_deposits()
    await call.answer()
    if not rows:
        return await safe_edit(call.message, "🎉 কোনো পেন্ডিং ডিপোজিট নেই।", back_kb())
    for d in rows[:10]:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Approve", callback_data=f"admindep_ok:{d['id']}")
        b.button(text="❌ Reject", callback_data=f"admindep_no:{d['id']}")
        b.adjust(2)
        await call.message.answer(
            f"💳 <b>Deposit #{d['id']}</b>\nUser: <code>{d['user_id']}</code>\nMethod: {esc(d['method'])}\n"
            f"Amount: {fmt(d['amount'])} {CURRENCY}\nTrxID: <code>{esc(d['trx_id'])}</code>",
            reply_markup=b.as_markup())

@admin_router.callback_query(F.data.startswith("admindep_ok:"))
async def cb_admindep_ok(call: CallbackQuery, bot: Bot):
    res = await db.approve_deposit(int(call.data.split(":")[1]), call.from_user.id)
    if res is None:
        return await call.answer("Already processed / not found.", show_alert=True)
    await notify_user(bot, res["user_id"], f"✅ আপনার ডিপোজিট অ্যাপ্রুভ হয়েছে!\n💎 যোগ হয়েছে: {fmt(res['amount'])} {CURRENCY}\n💼 নতুন ব্যালেন্স: {fmt(res['balance'])} {CURRENCY}")
    await call.answer("Approved ✅")
    await safe_edit(call.message, call.message.html_text + "\n\n✅ <b>Approved</b>")

@admin_router.callback_query(F.data.startswith("admindep_no:"))
async def cb_admindep_no(call: CallbackQuery, bot: Bot):
    d = await db.reject_deposit(int(call.data.split(":")[1]), call.from_user.id)
    if d is None:
        return await call.answer("Already processed / not found.", show_alert=True)
    await notify_user(bot, d["user_id"], "❌ আপনার ডিপোজিট বাতিল হয়েছে। সমস্যা হলে সাপোর্টে যোগাযোগ করুন।")
    await call.answer("Rejected ❌")
    await safe_edit(call.message, call.message.html_text + "\n\n❌ <b>Rejected</b>")

@admin_router.callback_query(F.data == "apanel:usds")
async def cb_apanel_usds(call: CallbackQuery):
    rows = await db.pending_usd_orders()
    await call.answer()
    if not rows:
        return await safe_edit(call.message, "🎉 কোনো পেন্ডিং ডলার অর্ডার নেই।", back_kb())
    for o in rows[:10]:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Complete", callback_data=f"adminusd_ok:{o['id']}")
        b.button(text="❌ Reject", callback_data=f"adminusd_no:{o['id']}")
        b.adjust(2)
        await call.message.answer(
            f"💵 <b>Dollar Order #{o['id']} ({o['direction'].upper()})</b>\n"
            f"User: <code>{o['user_id']}</code>\nUSD: {fmt(o['usd_amount'])} | {CURRENCY}: {fmt(o['bdt_amount'])}\n"
            f"Method: {esc(o['crypto_meth'])} / {esc(o['fiat_meth'])}\nDetails:\n<code>{esc(o['details'])}</code>",
            reply_markup=b.as_markup())

@admin_router.callback_query(F.data.startswith("adminusd_ok:"))
async def cb_adminusd_ok(call: CallbackQuery, bot: Bot):
    oid = int(call.data.split(":")[1])
    res = await db.resolve_usd_order(oid, True)
    if res is None:
        return await call.answer("Already processed.", show_alert=True)
    o = res["order"]
    if o["direction"] == "sell":
        msg = f"✅ ডলার অর্ডার #{oid} সম্পন্ন! {fmt(o['bdt_amount'])} {CURRENCY} আপনার ব্যালেন্সে যোগ হয়েছে।\n💼 নতুন ব্যালেন্স: {fmt(res['balance'])} {CURRENCY}"
    else:
        msg = f"✅ ডলার অর্ডার #{oid} সম্পন্ন হয়েছে!"
    await notify_user(bot, o["user_id"], msg)
    await call.answer("Done ✅")
    await safe_edit(call.message, call.message.html_text + "\n\n✅ <b>Completed</b>")

@admin_router.callback_query(F.data.startswith("adminusd_no:"))
async def cb_adminusd_no(call: CallbackQuery, bot: Bot):
    oid = int(call.data.split(":")[1])
    res = await db.resolve_usd_order(oid, False)
    if res is None:
        return await call.answer("Already processed.", show_alert=True)
    await notify_user(bot, res["order"]["user_id"], f"❌ ডলার অর্ডার #{oid} বাতিল হয়েছে।")
    await call.answer("Rejected ❌")
    await safe_edit(call.message, call.message.html_text + "\n\n❌ <b>Rejected</b>")

async def a_products_root():
    cats = await db.categories()
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"📁 {c['name']}", callback_data=f"acat:{c['id']}")
    b.button(text="➕ Add Category", callback_data="acat_add")
    b.button(text="⬅️ Back", callback_data="apanel:main")
    b.adjust(1)
    return "📦 <b>Categories</b>", b.as_markup()

async def a_cat_view(cid):
    cat = await db.get_category(cid)
    if not cat:
        return None
    prods = await db.products(cid, only_active=False)
    b = InlineKeyboardBuilder()
    for p in prods:
        b.button(text=f"{p['name']} • {fmt(p['price'])}{CURRENCY} ({p['stock']})", callback_data=f"aprod:{p['id']}")
    b.button(text="➕ Add Product", callback_data=f"aprodadd:{cid}")
    b.button(text="🗑 Delete Category", callback_data=f"acatdel:{cid}")
    b.button(text="⬅️ Back", callback_data="apanel:products")
    b.adjust(1)
    return f"📁 <b>{esc(cat['name'])}</b>\nপ্রোডাক্ট: {len(prods)} টি", b.as_markup()

async def a_prod_view(pid):
    p = await db.get_product(pid)
    if not p:
        return None
    b = InlineKeyboardBuilder()
    b.button(text="✏️ দাম সেট", callback_data=f"apset:{pid}")
    for v in (-50, -10, 10, 50):
        b.button(text=f"{sgn(v)} {CURRENCY}", callback_data=f"apadj:{pid}:f:{v}")
    for v in (-10, -5, 5, 10):
        b.button(text=f"{sgn(v)}%", callback_data=f"apadj:{pid}:p:{v}")
    b.button(text="📥 স্টক যোগ", callback_data=f"astock:{pid}")
    b.button(text="🗑 ডিলিট", callback_data=f"aprod_del:{pid}")
    b.button(text="⬅️ Back", callback_data=f"acat:{p['category_id']}")
    b.adjust(1, 4, 4, 2, 1)
    text = (
        f"📦 <b>{esc(p['name'])}</b> (#{pid})\n"
        f"📝 {esc(p['description'] or '—')}\n\n"
        f"💎 Price: <b>{fmt(p['price'])} {CURRENCY}</b>\n"
        f"📊 Stock: <b>{p['stock']}</b>"
    )
    return text, b.as_markup()

@admin_router.callback_query(F.data == "apanel:products")
async def cb_apanel_products(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, *(await a_products_root()))

@admin_router.callback_query(F.data.startswith("acat:"))
async def cb_acat(call: CallbackQuery, state: FSMContext):
    await state.clear()
    v = await a_cat_view(int(call.data.split(":")[1]))
    await call.answer()
    if not v:
        return await safe_edit(call.message, "❌ ক্যাটাগরি পাওয়া যায়নি।", back_kb("apanel:products"))
    await safe_edit(call.message, *v)

@admin_router.callback_query(F.data == "acat_add")
async def cb_acat_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSt.cat_name)
    await call.answer()
    await call.message.answer("📁 ক্যাটাগরির নাম দিন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.cat_name, *AT)
async def st_cat_name(message: Message, state: FSMContext):
    cid = await db.add_category(message.text.strip()[:60])
    await state.clear()
    if cid is None:
        return await message.answer("⚠️ এই নামে ক্যাটাগরি আগেই আছে।", reply_markup=back_kb("apanel:products"))
    await message.answer("✅ ক্যাটাগরি যোগ হয়েছে!")
    await message.answer(*(await a_cat_view(cid)))

@admin_router.callback_query(F.data.startswith("acatdel:"))
async def cb_acatdel(call: CallbackQuery):
    cid = int(call.data.split(":")[1])
    b = InlineKeyboardBuilder()
    b.button(text="⚠️ হ্যাঁ, ডিলিট করুন", callback_data=f"acatdelok:{cid}")
    b.button(text="❌ না", callback_data=f"acat:{cid}")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, "⚠️ ক্যাটাগরি ডিলিট করলে এর <b>সব প্রোডাক্ট ও স্টক</b> মুছে যাবে। নিশ্চিত?", b.as_markup())

@admin_router.callback_query(F.data.startswith("acatdelok:"))
async def cb_acatdelok(call: CallbackQuery):
    await db.delete_category(int(call.data.split(":")[1]))
    await call.answer("Deleted 🗑️", show_alert=True)
    await safe_edit(call.message, *(await a_products_root()))

@admin_router.callback_query(F.data.startswith("aprodadd:"))
async def cb_aprodadd(call: CallbackQuery, state: FSMContext):
    cid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.prod_name)
    await state.update_data(cid=cid)
    await call.answer()
    await call.message.answer("📦 প্রোডাক্টের নাম দিন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.prod_name, *AT)
async def st_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip()[:100])
    await state.set_state(AdminSt.prod_price)
    await message.answer(f"{CURRENCY} প্রতি পিসের দাম দিন (সংখ্যায়):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.prod_price, *AT)
async def st_prod_price(message: Message, state: FSMContext):
    price = parse_amount(message.text)
    if price is None:
        return await message.answer("⚠️ সঠিক দাম দিন।", reply_markup=cancel_kb())
    await state.update_data(price=price)
    await state.set_state(AdminSt.prod_desc)
    await message.answer("📝 প্রোডাক্টের বিবরণ লিখুন (স্কিপ করতে <code>-</code> লিখুন):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.prod_desc, *AT)
async def st_prod_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    desc = "" if message.text.strip() == "-" else message.text.strip()[:500]
    pid = await db.add_product(data["cid"], data["name"], data["price"], desc)
    await state.clear()
    if pid is None:
        return await message.answer("❌ ক্যাটাগরি পাওয়া যায়নি।")
    await message.answer("✅ প্রোডাক্ট যোগ হয়েছে! এখন স্টক যোগ করুন 👇")
    await message.answer(*(await a_prod_view(pid)))

@admin_router.callback_query(F.data.startswith("aprod:"))
async def cb_aprod_detail(call: CallbackQuery, state: FSMContext):
    await state.clear()
    v = await a_prod_view(int(call.data.split(":")[1]))
    await call.answer()
    if not v:
        return await safe_edit(call.message, "❌ প্রোডাক্ট পাওয়া যায়নি।", back_kb("apanel:products"))
    await safe_edit(call.message, *v)

@admin_router.callback_query(F.data.startswith("apadj:"))
async def cb_apadj(call: CallbackQuery):
    _, pid_s, mode, val_s = call.data.split(":")
    res = await db.adjust_price(int(pid_s), mode, float(val_s))
    if res is None:
        return await call.answer("Not found", show_alert=True)
    await call.answer(f"{fmt(res[0])} → {fmt(res[1])}")
    v = await a_prod_view(int(pid_s))
    if v:
        await safe_edit(call.message, *v)

@admin_router.callback_query(F.data.startswith("apset:"))
async def cb_apset(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.price_set)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("✏️ নতুন দাম দিন (সংখ্যায়):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.price_set, *AT)
async def st_price_set(message: Message, state: FSMContext):
    p = parse_amount(message.text)
    if p is None:
        return await message.answer("⚠️ সঠিক দাম দিন।", reply_markup=cancel_kb())
    pid = (await state.get_data())["pid"]
    res = await db.adjust_price(pid, "s", p)
    await state.clear()
    if res is None:
        return await message.answer("❌ প্রোডাক্ট পাওয়া যায়নি।")
    await message.answer(f"✅ দাম আপডেট: {fmt(res[0])} → <b>{fmt(res[1])} {CURRENCY}</b>")
    await message.answer(*(await a_prod_view(pid)))

@admin_router.callback_query(F.data.startswith("astock:"))
async def cb_astock(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.stock_add)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("📥 স্টক আইটেম দিন — <b>প্রতি লাইনে ১টি</b>:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.stock_add, *AT)
async def st_stock_add(message: Message, state: FSMContext):
    pid = (await state.get_data())["pid"]
    items = [ln.strip() for ln in message.text.splitlines() if ln.strip()]
    if not items:
        return await message.answer("⚠️ কোনো আইটেম পাওয়া যায়নি।", reply_markup=cancel_kb())
    n = await db.add_stock(pid, items)
    await state.clear()
    if n is None:
        return await message.answer("❌ প্রোডাক্ট পাওয়া যায়নি।")
    await message.answer(f"✅ {n} টি স্টক যোগ হয়েছে!")
    await message.answer(*(await a_prod_view(pid)))

@admin_router.callback_query(F.data.startswith("aprod_del:"))
async def cb_aprod_del(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    b = InlineKeyboardBuilder()
    b.button(text="⚠️ হ্যাঁ, ডিলিট করুন", callback_data=f"aprod_delok:{pid}")
    b.button(text="❌ না", callback_data=f"aprod:{pid}")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, "⚠️ এই প্রোডাক্ট ও এর সব স্টক ডিলিট হবে। নিশ্চিত?", b.as_markup())

@admin_router.callback_query(F.data.startswith("aprod_delok:"))
async def cb_aprod_delok(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    p = await db.get_product(pid)
    cid = p["category_id"] if p else None
    await db.delete_product(pid)
    await call.answer("Deleted 🗑️", show_alert=True)
    v = await a_cat_view(cid) if cid else None
    await safe_edit(call.message, *(v if v else await a_products_root()))

async def pm_list_view():
    methods = await db.payment_methods()
    mind = await min_deposit()
    lines = []
    for m in methods:
        icon = "✅" if m["active"] else "⛔"
        kind = "ক্রিপ্টো" if m["kind"] == "crypto" else "মোবাইল"
        lines.append(f"{icon} <b>{esc(m['name'])}</b> ({kind})\n    <code>{esc(m['address'])}</code>")
    text = "💳 <b>Payment Methods</b>\n\n" + ("\n".join(lines) if lines else "কোনো মেথড নেই।") + \
           f"\n\n📉 সর্বনিম্ন ডিপোজিট: <b>{fmt(mind)} {CURRENCY}</b>\n\n✅ = চালু • ⛔ = বন্ধ (ক্লিক করে ম্যানেজ করুন)"
    b = InlineKeyboardBuilder()
    for m in methods:
        b.button(text=f"{'✅' if m['active'] else '⛔'} {m['name']}", callback_data=f"apm:{m['id']}")
    b.button(text="➕ নতুন মেথড অ্যাড", callback_data="apmadd")
    b.button(text="📉 সর্বনিম্ন ডিপোজিট সেট", callback_data="aset:min_deposit")
    b.button(text="⬅️ Back to Admin Menu", callback_data="apanel:main")
    sizes = [2] * (len(methods) // 2) + ([1] if len(methods) % 2 else []) + [1, 1, 1]
    b.adjust(*sizes)
    return text, b.as_markup()

async def pm_view(pid):
    m = await db.get_pm(pid)
    if not m:
        return None
    kind = "💎 ক্রিপ্টো (ডিপোজিট + ডলার জোন)" if m["kind"] == "crypto" else "📱 মোবাইল ব্যাংকিং (ডিপোজিট)"
    text = (
        f"💳 <b>{esc(m['name'])}</b>\n\n"
        f"📍 নাম্বার/অ্যাড্রেস: <code>{esc(m['address'])}</code>\n"
        f"🏷 টাইপ: {kind}\n"
        f"🔘 স্ট্যাটাস: {'✅ চালু' if m['active'] else '⛔ বন্ধ'}"
    )
    b = InlineKeyboardBuilder()
    b.button(text="✏️ নাম্বার/অ্যাড্রেস পরিবর্তন", callback_data=f"apmaddr:{pid}")
    b.button(text=("⛔ বন্ধ করুন (OFF)" if m["active"] else "✅ চালু করুন (ON)"), callback_data=f"apmtog:{pid}")
    b.button(text="🗑 ডিলিট", callback_data=f"apmdel:{pid}")
    b.button(text="⬅️ Back", callback_data="apanel:pay_methods")
    b.adjust(1)
    return text, b.as_markup()

@admin_router.callback_query(F.data == "apanel:pay_methods")
async def cb_admin_pay_methods(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, *(await pm_list_view()))

@admin_router.callback_query(F.data.startswith("apm:"))
async def cb_apm(call: CallbackQuery, state: FSMContext):
    await state.clear()
    v = await pm_view(int(call.data.split(":")[1]))
    await call.answer()
    if not v:
        return await safe_edit(call.message, "❌ মেথড পাওয়া যায়নি।", back_kb("apanel:pay_methods"))
    await safe_edit(call.message, *v)

@admin_router.callback_query(F.data.startswith("apmtog:"))
async def cb_apmtog(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    new = await db.toggle_pm(pid)
    if new is None:
        return await call.answer("Not found", show_alert=True)
    await call.answer("✅ চালু হয়েছে" if new else "⛔ বন্ধ হয়েছে")
    await safe_edit(call.message, *(await pm_view(pid)))

@admin_router.callback_query(F.data.startswith("apmaddr:"))
async def cb_apmaddr(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.pm_edit_addr)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("✏️ নতুন নাম্বার/অ্যাড্রেস/UID লিখুন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.pm_edit_addr, *AT)
async def st_pm_edit_addr(message: Message, state: FSMContext):
    pid = (await state.get_data())["pid"]
    ok = await db.set_pm_address(pid, message.text.strip()[:300])
    await state.clear()
    if not ok:
        return await message.answer("❌ মেথড পাওয়া যায়নি।")
    await message.answer("✅ আপডেট হয়েছে!")
    await message.answer(*(await pm_view(pid)))

@admin_router.callback_query(F.data.startswith("apmdel:"))
async def cb_apmdel(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    b = InlineKeyboardBuilder()
    b.button(text="⚠️ হ্যাঁ, ডিলিট করুন", callback_data=f"apmdelok:{pid}")
    b.button(text="❌ না", callback_data=f"apm:{pid}")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, "⚠️ এই পেমেন্ট মেথড ডিলিট করবেন? (শুধু বন্ধ করতে চাইলে OFF ব্যবহার করুন)", b.as_markup())

@admin_router.callback_query(F.data.startswith("apmdelok:"))
async def cb_apmdelok(call: CallbackQuery):
    await db.delete_pm(int(call.data.split(":")[1]))
    await call.answer("Deleted 🗑️", show_alert=True)
    await safe_edit(call.message, *(await pm_list_view()))

@admin_router.callback_query(F.data == "apmadd")
async def cb_apmadd(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSt.pm_new_name)
    await call.answer()
    await call.message.answer("➕ নতুন পেমেন্ট মেথডের <b>নাম</b> লিখুন (যেমন: Upay, Binance Pay):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.pm_new_name, *AT)
async def st_pm_new_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip()[:30])
    await state.set_state(AdminSt.pm_new_kind)
    b = InlineKeyboardBuilder()
    b.button(text="📱 মোবাইল ব্যাংকিং", callback_data="apmkind:fiat")
    b.button(text="💎 ক্রিপ্টো (ডলার জোনেও দেখাবে)", callback_data="apmkind:crypto")
    b.button(text="❌ Cancel", callback_data="acancel")
    b.adjust(1)
    await message.answer("🏷 মেথডের টাইপ সিলেক্ট করুন:", reply_markup=b.as_markup())

@admin_router.callback_query(F.data.startswith("apmkind:"))
async def cb_apmkind(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "name" not in data:
        return await call.answer("⏳ সেশন শেষ। আবার শুরু করুন।", show_alert=True)
    await state.update_data(kind=call.data.split(":")[1])
    await state.set_state(AdminSt.pm_new_addr)
    await call.answer()
    await call.message.answer("📍 এখন নাম্বার/অ্যাড্রেস/UID লিখুন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.pm_new_addr, *AT)
async def st_pm_new_addr(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = await db.add_pm(data["name"], message.text.strip()[:300], data.get("kind", "fiat"))
    await state.clear()
    await message.answer("✅ নতুন পেমেন্ট মেথড যোগ হয়েছে!")
    await message.answer(*(await pm_view(pid)))

SETTING_LABELS = {
    "rate_sell": "🟢 Dollar Buy Rate (ইউজার কিনলে 1 USD = ? 💎)",
    "rate_buy": "🔴 Dollar Sell Rate (ইউজার বিক্রি করলে 1 USD = ? 💎)",
    "support_username": "🎧 সাপোর্ট ইউজারনেম (@ ছাড়া/সহ)",
    "channel_link": "📢 চ্যানেল লিংক (যেমন https://t.me/xxx বা @xxx) — মুছতে <code>-</code> লিখুন",
    "min_deposit": "📉 সর্বনিম্ন ডিপোজিট (💎)",
}
NUMERIC_SETTINGS = {"rate_buy", "rate_sell", "min_deposit"}

async def rates_supp_view():
    buy, sell = await db.rates()
    sup = await db.get_setting("support_username", DEFAULT_SUPPORT)
    ch = await db.get_setting("channel_link", "")
    mind = await min_deposit()
    text = (
        "💲 <b>Rates & Support Settings</b>\n\n"
        f"🟢 Dollar Buy Rate: <b>{fmt(sell)}</b>\n"
        f"🔴 Dollar Sell Rate: <b>{fmt(buy)}</b>\n"
        f"📉 Min Deposit: <b>{fmt(mind)} {CURRENCY}</b>\n"
        f"🎧 Support: <b>@{esc(sup)}</b>\n"
        f"📢 Channel: {esc(ch) if ch else '—'}"
    )
    b = InlineKeyboardBuilder()
    for v in (-5, -1, 1, 5):
        b.button(text=f"🟢 {sgn(v)}", callback_data=f"arate:rate_sell:{v}")
    b.button(text="🟢 Buy Rate সেট করুন", callback_data="aset:rate_sell")
    for v in (-5, -1, 1, 5):
        b.button(text=f"🔴 {sgn(v)}", callback_data=f"arate:rate_buy:{v}")
    b.button(text="🔴 Sell Rate সেট করুন", callback_data="aset:rate_buy")
    b.button(text="🎧 সাপোর্ট আইডি", callback_data="aset:support_username")
    b.button(text="📢 চ্যানেল লিংক", callback_data="aset:channel_link")
    b.button(text="📉 Min Deposit", callback_data="aset:min_deposit")
    b.button(text="⬅️ Back to Admin Menu", callback_data="apanel:main")
    b.adjust(4, 1, 4, 1, 1, 1, 1, 1)
    return text, b.as_markup()

@admin_router.callback_query(F.data == "apanel:rates_supp")
async def cb_admin_rates_supp(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, *(await rates_supp_view()))

@admin_router.callback_query(F.data.startswith("arate:"))
async def cb_arate(call: CallbackQuery):
    _, key, val_s = call.data.split(":")
    if key not in ("rate_buy", "rate_sell"):
        return await call.answer()
    try:
        cur = float(await db.get_setting(key, "0") or 0)
    except ValueError:
        cur = 0.0
    new = max(round(cur + float(val_s), 2), 0.01)
    await db.set_setting(key, new)
    await call.answer(f"✅ {fmt(new)}")
    await safe_edit(call.message, *(await rates_supp_view()))

@admin_router.callback_query(F.data.startswith("aset:"))
async def cb_aset_field(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    if key not in SETTING_LABELS:
        return await call.answer()
    await state.set_state(AdminSt.setting_edit)
    await state.update_data(key=key)
    await call.answer()
    await call.message.answer(f"✏️ <b>{SETTING_LABELS[key]}</b>\n\nনতুন ভ্যালু লিখুন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.setting_edit, *AT)
async def st_setting_edit(message: Message, state: FSMContext):
    key = (await state.get_data())["key"]
    raw = message.text.strip()
    if key in NUMERIC_SETTINGS:
        v = parse_amount(raw)
        if v is None:
            return await message.answer("⚠️ সঠিক সংখ্যা লিখুন।", reply_markup=cancel_kb())
        val = v
    elif key == "support_username":
        val = raw.lstrip("@")
        if val.startswith("https://t.me/"):
            val = val[len("https://t.me/"):]
        if not SUP_RE.match(val):
            return await message.answer("⚠️ সঠিক ইউজারনেম লিখুন (ইংরেজি অক্ষর/সংখ্যা/_ , কমপক্ষে ৩ অক্ষর)।", reply_markup=cancel_kb())
    elif key == "channel_link":
        if raw == "-":
            val = ""
        else:
            val = norm_link(raw)
            if val is None:
                return await message.answer("⚠️ সঠিক লিংক দিন (https://t.me/... বা @name)।", reply_markup=cancel_kb())
    else:
        val = raw
    await db.set_setting(key, val)
    await state.clear()
    await message.answer("✅ সফলভাবে আপডেট হয়েছে!")
    if key == "min_deposit":
        await message.answer(*(await pm_list_view()))
    else:
        await message.answer(*(await rates_supp_view()))

async def a_user_view(u):
    items, spent, dep = await db.user_stats(u["user_id"])
    b = InlineKeyboardBuilder()
    b.button(text="➕ ব্যালেন্স যোগ", callback_data=f"abal:{u['user_id']}:add")
    b.button(text="➖ ব্যালেন্স কমান", callback_data=f"abal:{u['user_id']}:sub")
    b.button(text="✉️ মেসেজ পাঠান", callback_data=f"amsg:{u['user_id']}")
    b.button(text=("✅ আনব্যান" if u["banned"] else "🚫 ব্যান"), callback_data=f"aban:{u['user_id']}")
    b.button(text="⬅️ Back", callback_data="apanel:users")
    b.adjust(2, 2, 1)
    text = (
        f"👤 <b>{esc(u['full_name'])}</b> (@{esc(u['username'] or '-')})\n"
        f"🆔 <code>{u['user_id']}</code>\n"
        f"💼 ব্যালেন্স: <b>{fmt(u['balance'])} {CURRENCY}</b>\n"
        f"🛒 কেনা: {items} টি • 💸 খরচ: {fmt(spent)} • 💳 ডিপোজিট: {fmt(dep)}\n"
        f"👥 রেফার: {u['ref_count']}\n"
        f"📅 জয়েন: {esc(u['created_at'][:10])}\n"
        f"🔘 স্ট্যাটাস: {'🚫 Banned' if u['banned'] else '✅ Active'}"
    )
    return text, b.as_markup()

@admin_router.callback_query(F.data == "apanel:users")
async def cb_apanel_users(call: CallbackQuery, state: FSMContext):
    await state.clear()
    b = InlineKeyboardBuilder()
    b.button(text="🔍 ইউজার খুঁজুন (ID / @username)", callback_data="ausearch")
    b.button(text="✉️ ইউজারকে মেসেজ", callback_data="aumsg")
    b.button(text="⬅️ Back to Admin Menu", callback_data="apanel:main")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, "👥 <b>User Management</b>\nইউজারের ব্যালেন্স যোগ/কমানো, মেসেজ, ব্যান — সবকিছু এখান থেকে:", b.as_markup())

@admin_router.callback_query(F.data.in_({"ausearch", "aumsg"}))
async def cb_ausearch(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSt.user_find)
    await state.update_data(purpose="msg" if call.data == "aumsg" else "view")
    await call.answer()
    await call.message.answer("🔍 ইউজারের <b>Telegram ID</b> বা <b>@username</b> লিখুন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.user_find, *AT)
async def st_user_find(message: Message, state: FSMContext):
    q = message.text.strip()
    u = await db.get_user(int(q)) if q.isdigit() else await db.find_user_by_username(q)
    if not u:
        return await message.answer("❌ ইউজার পাওয়া যায়নি। আবার চেষ্টা করুন।", reply_markup=cancel_kb())
    purpose = (await state.get_data()).get("purpose", "view")
    if purpose == "msg":
        await state.set_state(AdminSt.user_msg)
        await state.update_data(uid=u["user_id"])
        return await message.answer(
            f"✉️ <b>{esc(u['full_name'])}</b> (<code>{u['user_id']}</code>) কে পাঠানোর মেসেজ লিখুন:", reply_markup=cancel_kb())
    await state.clear()
    await message.answer(*(await a_user_view(u)))

@admin_router.callback_query(F.data.startswith("ause:"))
async def cb_ause(call: CallbackQuery, state: FSMContext):
    await state.clear()
    u = await db.get_user(int(call.data.split(":")[1]))
    await call.answer()
    if not u:
        return await safe_edit(call.message, "❌ ইউজার পাওয়া যায়নি।", back_kb("apanel:users"))
    await safe_edit(call.message, *(await a_user_view(u)))

@admin_router.callback_query(F.data.startswith("amsg:"))
async def cb_amsg(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.user_msg)
    await state.update_data(uid=uid)
    await call.answer()
    await call.message.answer(f"✉️ <code>{uid}</code> কে পাঠানোর মেসেজ লিখুন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.user_msg, *AT)
async def st_user_msg(message: Message, state: FSMContext, bot: Bot):
    uid = (await state.get_data())["uid"]
    await state.clear()
    ok = await notify_user(bot, uid, f"📩 <b>অ্যাডমিন থেকে বার্তা:</b>\n\n{message.html_text}")
    await message.answer("✅ মেসেজ পাঠানো হয়েছে।" if ok else "❌ মেসেজ পাঠানো যায়নি (ইউজার বট ব্লক করেছে হতে পারে)।",
                         reply_markup=back_kb("apanel:users"))

@admin_router.callback_query(F.data.startswith("abal:"))
async def cb_abal(call: CallbackQuery, state: FSMContext):
    _, uid_s, mode = call.data.split(":")
    await state.set_state(AdminSt.bal_amount)
    await state.update_data(uid=int(uid_s), mode=mode)
    await call.answer()
    word = "যোগ করার" if mode == "add" else "কমানোর"
    await call.message.answer(f"{CURRENCY} <code>{uid_s}</code> এর ব্যালেন্স {word} পরিমাণ লিখুন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.bal_amount, *AT)
async def st_bal_amount(message: Message, state: FSMContext, bot: Bot):
    amount = parse_amount(message.text)
    if amount is None:
        return await message.answer("⚠️ সঠিক পরিমাণ লিখুন।", reply_markup=cancel_kb())
    data = await state.get_data()
    uid, mode = data["uid"], data["mode"]
    sign = 1 if mode == "add" else -1
    new = await db.change_balance(uid, sign * amount, "admin_add" if sign > 0 else "admin_sub", "admin panel")
    await state.clear()
    if new is None:
        return await message.answer("❌ ব্যর্থ (ইউজার নেই বা ব্যালেন্স কম)।", reply_markup=back_kb("apanel:users"))
    verb = "যোগ" if sign > 0 else "কাটা"
    await notify_user(bot, uid, f"💼 আপনার ব্যালেন্সে {fmt(amount)} {CURRENCY} {verb} হয়েছে।\nনতুন ব্যালেন্স: <b>{fmt(new)} {CURRENCY}</b>")
    await message.answer(f"✅ সম্পন্ন। নতুন ব্যালেন্স: <b>{fmt(new)} {CURRENCY}</b>")
    u = await db.get_user(uid)
    await message.answer(*(await a_user_view(u)))

@admin_router.callback_query(F.data.startswith("aban:"))
async def cb_aban(call: CallbackQuery):
    uid = int(call.data.split(":")[1])
    u = await db.get_user(uid)
    if not u:
        return await call.answer("Not found", show_alert=True)
    await db.set_banned(uid, not u["banned"])
    u = await db.get_user(uid)
    await call.answer("🚫 Banned" if u["banned"] else "✅ Unbanned")
    await safe_edit(call.message, *(await a_user_view(u)))

async def help_admin_view():
    vids = await db.videos()
    lines = [f"{i}. 🎬 {esc(v['title'])} ({'লিংক' if v['kind'] == 'link' else 'ভিডিও'})" for i, v in enumerate(vids, 1)]
    text = "🎬 <b>আমি নতুন — ভিডিও ম্যানেজমেন্ট</b>\n\n" + ("\n".join(lines) if lines else "এখনো কোনো ভিডিও নেই।") + \
           "\n\n🗑 ডিলিট করতে নিচের বাটনে ক্লিক করুন।"
    b = InlineKeyboardBuilder()
    for v in vids:
        b.button(text=f"🗑 {v['title']}", callback_data=f"avdel:{v['id']}")
    b.button(text="➕ ভিডিও / লিংক অ্যাড", callback_data="avadd")
    b.button(text="⬅️ Back to Admin Menu", callback_data="apanel:main")
    b.adjust(1)
    return text, b.as_markup()

@admin_router.callback_query(F.data == "apanel:help")
async def cb_apanel_help(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, *(await help_admin_view()))

@admin_router.callback_query(F.data == "avadd")
async def cb_avadd(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSt.vid_title)
    await call.answer()
    await call.message.answer("🎬 ভিডিওর <b>টাইটেল</b> লিখুন (বাটনে এই নাম দেখাবে):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.vid_title, *AT)
async def st_vid_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip()[:40])
    await state.set_state(AdminSt.vid_content)
    await message.answer("📹 এখন <b>ভিডিও ফাইল</b> পাঠান (অথবা ভিডিওর লিংক লিখুন):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.vid_content, lambda m: not (m.text or "").startswith("/"))
async def st_vid_content(message: Message, state: FSMContext):
    title = (await state.get_data()).get("title", "Tutorial")
    kind = content = None
    if message.video:
        kind, content = "video", message.video.file_id
    elif message.animation:
        kind, content = "animation", message.animation.file_id
    elif message.document and (message.document.mime_type or "").startswith("video/"):
        kind, content = "document", message.document.file_id
    elif message.text and norm_link(message.text):
        kind, content = "link", norm_link(message.text)
    if kind is None:
        return await message.answer("⚠️ ভিডিও ফাইল পাঠান অথবা সঠিক লিংক (https://...) দিন।", reply_markup=cancel_kb())
    await db.add_video(title, kind, content)
    await state.clear()
    await message.answer("✅ ভিডিও যোগ হয়েছে!")
    await message.answer(*(await help_admin_view()))

@admin_router.callback_query(F.data.startswith("avdel:"))
async def cb_avdel(call: CallbackQuery):
    vid = int(call.data.split(":")[1])
    b = InlineKeyboardBuilder()
    b.button(text="⚠️ হ্যাঁ, ডিলিট করুন", callback_data=f"avdelok:{vid}")
    b.button(text="❌ না", callback_data="apanel:help")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, "⚠️ এই ভিডিওটি ডিলিট করবেন?", b.as_markup())

@admin_router.callback_query(F.data.startswith("avdelok:"))
async def cb_avdelok(call: CallbackQuery):
    await db.delete_video(int(call.data.split(":")[1]))
    await call.answer("Deleted 🗑️")
    await safe_edit(call.message, *(await help_admin_view()))

# ============ Render-এর জন্য Web Port (Flask) ============
def run_flask():
    app = Flask(__name__)
    @app.route('/')
    def health():
        return "Bot is running"
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ============ Entrypoint ============
async def main():
    global BOT_USERNAME
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await db.connect()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    BOT_USERNAME = (await bot.get_me()).username

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(UserMiddleware())
    dp.include_router(admin_router)
    dp.include_router(user_router)

    @dp.errors()
    async def on_error(event):
        log.exception("Unhandled error: %s", event.exception)
        return True

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot @%s started.", BOT_USERNAME)
    
    # Render Port এর জন্য থ্রেড চালু করা হলো
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped!")
