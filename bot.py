#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Store / Access Bot (aiogram 3.x + SQLite)
Render-ready version (Flask health server + callback middleware fixed)
"""
import asyncio
import html
import logging
import math
import os
import re
from contextlib import asynccontextmanager
import threading

from flask import Flask

import aiosqlite
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============ কনফিগ ============
# ⚠️ পুরানো টোকেন প্রকাশ হয়ে গেছে — BotFather-এ /revoke করে নতুন টোকেন নিন,
# তারপর Render-এর Environment Variables-এ TELEGRAM_TOKEN দিন।
BOT_TOKEN = os.environ.get("8697620225:AAFkpPMkvaoPE7MaxmxXecKb3aoXAiYQf54", "8697620225:AAFkpPMkvaoPE7MaxmxXecKb3aoXAiYQf54")
ADMIN_IDS = {8569375013}
DB_PATH = "store.db"
CURRENCY = "৳"
MIN_DEPOSIT = 50.0
MIN_USD = 1.0

DEFAULT_SUPPORT = "@afmbdff"
DEFAULT_RATE_BUY = 120.0
DEFAULT_RATE_SELL = 115.0

DEFAULT_BKASH = "01949638507"
DEFAULT_NAGAD = "01650242703"
DEFAULT_ROCKET = "01XXXXXXXXX"
DEFAULT_BINANCE = "YourBinanceUIDHere"
DEFAULT_USDT = "T-XXXXXXXXXXXXXXXXXXXXXXXX"
DEFAULT_LTC = "L-XXXXXXXXXXXXXXXXXXXXXXXX"

DOLLAR_CRYPTO_KEYS = ["binance", "usdt", "ltc"]
DOLLAR_CRYPTO_NAMES = {"binance": "Binance UID", "usdt": "USDT (BEP20)", "ltc": "LTC (LiteCoin)"}
FIAT_PAYMENT_METHODS = ["bKash", "Nagad", "Rocket"]

BOT_USERNAME = ""
log = logging.getLogger("store-bot")

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))

def fmt(x: float) -> str:
    return f"{x:,.2f}"

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
        "back": "⬅️ ফিরে যান",
        "choose_category": "📂 <b>ক্যাটাগরি নির্বাচন করুন:</b>",
        "no_categories": "😔 এই মুহূর্তে কোনো প্রোডাক্ট বা ক্যাটাগরি নেই।",
        "choose_product": "🛍 <b>{cat}</b>\nপ্রোডাক্ট নির্বাচন করুন:",
        "no_products": "😔 এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই।",
        "product_detail": "📦 <b>{name}</b>\n\n{desc}\n\n💰 প্রতি পিস মূল্য: <b>{price} {cur}</b>\n📊 স্টক: <b>{stock}</b>",
        "buy_ok": "✅ <b>কেনা সফল!</b>\n\n📦 {name} (পরিমাণ: {qty})\n💰 মোট কাটা হয়েছে: {total} {cur}\n💼 বর্তমান ব্যালেন্স: {balance} {cur}\n\n🔑 <b>আপনার প্রোডাক্ট/সার্ভিস:</b>\n<code>{content}</code>",
        "buy_nobalance": "❌ আপনার ব্যালেন্স অপর্যাপ্ত।\n💼 ব্যালেন্স: {balance} {cur}\n💰 প্রয়োজন: {total} {cur}",
        "buy_nostock": "❌ দুঃখিত, পর্যাপ্ত স্টক নেই।",
        "buy_notfound": "❌ প্রোডাক্টটি পাওয়া যায়নি।",
        "profile": "👤 <b>আপনার প্রোফাইল</b>\n\n🆔 ID: <code>{uid}</code>\n📛 নাম: {name}\n💼 ব্যালেন্স: <b>{balance} {cur}</b>\n👥 মোট রেফার: {refs}\n🎁 রেফার আয়: {earn} {cur}\n📅 জয়েন: {joined}",
        "history_btn": "📜 ট্রানজেকশন হিস্ট্রি",
        "history_title": "📜 <b>সর্বশেষ ১০টি ট্রানজেকশন:</b>\n\n",
        "history_empty": "কোনো ট্রানজেকশন নেই।",
        "dep_choose": "💳 <b>ডিপোজিট মেথড নির্বাচন করুন:</b>",
        "dep_instr": "💳 <b>{method}</b>\n\nনিচের ঠিকানায় টাকা পাঠান:\n<code>{address}</code>\n\n⚠️ সর্বনিম্ন ডিপোজিট: {min} {cur}\n\n💰 কত টাকা পাঠিয়েছেন লিখুন:\n(বাতিল করতে /cancel)",
        "dep_ask_trx": "🧾 এখন <b>Transaction ID (TrxID)</b> লিখুন:\n(বাতিল করতে /cancel)",
        "dep_submitted": "✅ ডিপোজিট রিকোয়েস্ট জমা হয়েছে! ID: #{id}",
        "support_text": "🎧 <b>সাপোর্ট</b>\n\nযেকোনো সমস্যায় যোগাযোগ করুন: @{admin}",
        "help_text": "🙋‍♂️ <b>গাইড:</b> 💳 ডিপোজিট করুন -> 🛒 প্রোডাক্ট কিনুন।",
        "usd_menu": "💵 <b>ডলার বাই/সেল জোন</b>\n\n🟢 ডলার কেনার রেট: <b>1 USD = {sell} {cur}</b>\n🔴 ডলার বিক্রির রেট: <b>1 USD = {buy} {cur}</b>\n\n💼 ব্যালেন্স: {balance} {cur}",
        "usd_buy_btn": "🟢 ডলার কিনুন",
        "usd_sell_btn": "🔴 ডলার বিক্রি করুন",
        "usd_submitted": "✅ অর্ডার #{id} জমা হয়েছে।",
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
    product_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
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

        defaults = {
            "rate_buy": str(DEFAULT_RATE_BUY),
            "rate_sell": str(DEFAULT_RATE_SELL),
            "support_username": DEFAULT_SUPPORT,
            "pay_bkash": DEFAULT_BKASH,
            "pay_nagad": DEFAULT_NAGAD,
            "pay_rocket": DEFAULT_ROCKET,
            "pay_binance": DEFAULT_BINANCE,
            "pay_usdt": DEFAULT_USDT,
            "pay_ltc": DEFAULT_LTC,
        }
        for k, v in defaults.items():
            await self.conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
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

    async def all_user_ids(self):
        rows = await self.many("SELECT user_id FROM users WHERE banned=0")
        return [r["user_id"] for r in rows]

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
        except Exception:
            pass

async def notify_user(bot: Bot, uid: int, text: str):
    try:
        await bot.send_message(uid, text)
        return True
    except Exception:
        return False

def user_link(uid, name):
    return f'<a href="tg://user?id={uid}">{esc(name)}</a>'

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
        if user is None:
            await db.create_user(tg.id, tg.username, tg.full_name)
            user = await db.get_user(tg.id)
        elif user["username"] != tg.username or user["full_name"] != tg.full_name:
            await db.update_profile(tg.id, tg.username, tg.full_name)
        data["user"] = user
        data["lang"] = user["lang"] if user else "bn"
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
    price_set = State()
    stock_add = State()
    setting_edit = State()

user_router = Router(name="user")

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer(WELCOME_MULTI.format(name=esc(message.from_user.full_name)), reply_markup=lang_kb())

@user_router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery):
    lang = call.data.split(":", 1)[1]
    await db.set_lang(call.from_user.id, lang)
    await call.answer()
    await safe_edit(call.message, t(lang, "lang_saved"))
    await call.message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

@user_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(t(lang, "cancelled"), reply_markup=main_menu_kb(lang))

async def categories_view(lang):
    cats = await db.categories(only_available=True)
    if not cats:
        return t(lang, "no_categories"), None
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"📁 {c['name']}", callback_data=f"cat:{c['id']}")
    b.adjust(1)
    return t(lang, "choose_category"), b.as_markup()

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
async def cb_category(call: CallbackQuery, lang: str):
    cid = int(call.data.split(":")[1])
    cat = await db.get_category(cid)
    prods = await db.products(cid)
    await call.answer()
    if not cat or not prods:
        return await safe_edit(call.message, t(lang, "no_products"))
    b = InlineKeyboardBuilder()
    for p in prods:
        mark = "" if p["stock"] > 0 else " ❌"
        b.button(text=f"{p['name']} — {fmt(p['price'])} {CURRENCY} ({p['stock']}){mark}", callback_data=f"prod:{p['id']}")
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

    qty = 1
    b = InlineKeyboardBuilder()
    if p["stock"] > 0:
        b.button(text="➖", callback_data=f"qty:{pid}:{qty-1}")
        b.button(text=f"📦 Qty: {qty}", callback_data="noop")
        b.button(text="➕", callback_data=f"qty:{pid}:{qty+1}")
        b.button(text="✏️ Custom Qty", callback_data=f"custqty:{pid}")
        total_p = p["price"] * qty
        b.button(text=f"✅ Confirm Buy ({fmt(total_p)} {CURRENCY})", callback_data=f"buyfin:{pid}:{qty}")
    b.button(text=t(lang, "back"), callback_data=f"cat:{p['category_id']}")
    b.adjust(3, 1, 1, 1)

    await safe_edit(call.message, t(
        lang, "product_detail", name=esc(p["name"]), desc=esc(p["description"] or "—"),
        price=fmt(p["price"]), cur=CURRENCY, stock=p["stock"]), b.as_markup())

@user_router.callback_query(F.data.startswith("qty:"))
async def cb_change_qty(call: CallbackQuery, lang: str):
    _, pid_s, qty_s = call.data.split(":")
    pid, qty = int(pid_s), int(qty_s)
    p = await db.get_product(pid)
    if not p:
        return await call.answer("Not found", show_alert=True)
    qty = max(1, min(qty, p["stock"]))

    b = InlineKeyboardBuilder()
    if p["stock"] > 0:
        b.button(text="➖", callback_data=f"qty:{pid}:{qty-1}")
        b.button(text=f"📦 Qty: {qty}", callback_data="noop")
        b.button(text="➕", callback_data=f"qty:{pid}:{qty+1}")
        b.button(text="✏️ Custom Qty", callback_data=f"custqty:{pid}")
        total_p = p["price"] * qty
        b.button(text=f"✅ Confirm Buy ({fmt(total_p)} {CURRENCY})", callback_data=f"buyfin:{pid}:{qty}")
    b.button(text=t(lang, "back"), callback_data=f"cat:{p['category_id']}")
    b.adjust(3, 1, 1, 1)

    await call.answer()
    await safe_edit(call.message, t(
        lang, "product_detail", name=esc(p["name"]), desc=esc(p["description"] or "—"),
        price=fmt(p["price"]), cur=CURRENCY, stock=p["stock"]), b.as_markup())

@user_router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()

@user_router.callback_query(F.data.startswith("custqty:"))
async def cb_cust_qty(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(BuyQtySt.custom_qty)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("✏️ কাঙ্ক্ষিত পরিমাণ (Quantity) লিখুন:")

@user_router.message(BuyQtySt.custom_qty, F.text, ~F.text.startswith("/"))
async def msg_custom_qty(message: Message, state: FSMContext, lang: str):
    if not message.text.isdigit():
        return await message.answer("⚠️ দয়া করে সঠিক সংখ্যা লিখুন।")
    qty = int(message.text)
    data = await state.get_data()
    pid = data.get("pid")
    await state.clear()

    p = await db.get_product(pid)
    if not p or p["stock"] <= 0:
        return await message.answer("❌ স্টক নেই।")
    qty = max(1, min(qty, p["stock"]))

    res = await db.purchase_multi(message.from_user.id, pid, qty)
    if res["status"] != "ok":
        return await message.answer(t(lang, "buy_nobalance" if res["status"]=="nobalance" else "buy_nostock"))

    await message.answer(t(
        lang, "buy_ok", name=esc(p["name"]), qty=qty, total=fmt(res["total"]), cur=CURRENCY,
        balance=fmt(res["balance"]), content="\n".join(res["contents"])), reply_markup=main_menu_kb(lang))

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
        return await call.message.answer(t(lang, "buy_nobalance", balance=fmt(res["balance"]), total=fmt(res["total"]), cur=CURRENCY))

    p = res["product"]
    await call.answer("✅")
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await call.message.answer(t(
        lang, "buy_ok", name=esc(p["name"]), qty=qty, total=fmt(res["total"]), cur=CURRENCY,
        balance=fmt(res["balance"]), content="\n".join(res["contents"])))

@user_router.message(F.text.in_(all_texts("btn_profile")))
async def m_profile(message: Message, state: FSMContext, lang: str):
    await state.clear()
    u = await db.get_user(message.from_user.id)
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "history_btn"), callback_data="hist")
    await message.answer(t(
        lang, "profile", uid=u["user_id"], name=esc(u["full_name"]), balance=fmt(u["balance"]),
        cur=CURRENCY, refs=u["ref_count"], earn=fmt(u["ref_earnings"]), joined=esc(u["created_at"][:10])),
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

@user_router.message(F.text.in_(all_texts("btn_deposit")))
async def m_deposit(message: Message, state: FSMContext, lang: str):
    await state.clear()
    b = InlineKeyboardBuilder()
    b.button(text="bKash 🟣", callback_data="dep:bkash")
    b.button(text="Nagad 🟠", callback_data="dep:nagad")
    b.button(text="Rocket 🟪", callback_data="dep:rocket")
    b.button(text="USDT 💎", callback_data="dep:usdt")
    b.adjust(2)
    await message.answer(t(lang, "dep_choose"), reply_markup=b.as_markup())

@user_router.callback_query(F.data.startswith("dep:"))
async def cb_dep_method(call: CallbackQuery, state: FSMContext, lang: str):
    key = call.data.split(":")[1]
    address = await db.get_setting(f"pay_{key}", "নট সেট")
    await state.clear()
    await state.set_state(DepositSt.amount)
    await state.update_data(method=key)
    await call.answer()
    await call.message.answer(t(lang, "dep_instr", method=key.upper(), address=esc(address), min=fmt(MIN_DEPOSIT), cur=CURRENCY))

@user_router.message(DepositSt.amount, F.text, ~F.text.startswith("/"))
async def dep_amount(message: Message, state: FSMContext, lang: str):
    amount = parse_amount(message.text)
    if amount is None or amount < MIN_DEPOSIT:
        return await message.answer("⚠️ সঠিক পরিমাণ বা সর্বনিম্ন ডিপোজিট দিন।")
    await state.update_data(amount=amount)
    await state.set_state(DepositSt.trx)
    await message.answer(t(lang, "dep_ask_trx"))

@user_router.message(DepositSt.trx, F.text, ~F.text.startswith("/"))
async def dep_trx(message: Message, state: FSMContext, bot: Bot):
    trx = message.text.strip()
    data = await state.get_data()
    dep_id = await db.create_deposit(message.from_user.id, data["method"], data["amount"], trx)
    if dep_id is None:
        return await message.answer("⚠️ এই Transaction ID আগে ব্যবহার করা হয়েছে।")
    await state.clear()
    await message.answer(f"✅ ডিপোজিট রিকোয়েস্ট জমা হয়েছে! (ID: #{dep_id})", reply_markup=main_menu_kb("bn"))

    b = InlineKeyboardBuilder()
    b.button(text="✅ Approve", callback_data=f"admindep_ok:{dep_id}")
    b.button(text="❌ Reject", callback_data=f"admindep_no:{dep_id}")
    await notify_admins(bot, f"💳 Deposit #{dep_id}\nUser: {message.from_user.id}\nAmount: {data['amount']}\nTrxID: {trx}", b.as_markup())

@user_router.message(F.text.in_(all_texts("btn_support")))
async def m_support(message: Message, state: FSMContext, lang: str):
    await state.clear()
    sup = await db.get_setting("support_username", DEFAULT_SUPPORT)
    await message.answer(t(lang, "support_text", admin=esc(sup)))

@user_router.message(F.text.in_(all_texts("btn_help")))
async def m_help(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(t(lang, "help_text"))

@user_router.message(F.text.in_(all_texts("btn_dollar")))
async def m_dollar(message: Message, state: FSMContext, lang: str):
    await state.clear()
    buy, sell = await db.rates()
    u = await db.get_user(message.from_user.id)
    b = InlineKeyboardBuilder()
    b.button(text="🟢 ডলার কিনুন", callback_data="usd:buy")
    b.button(text="🔴 ডলার বিক্রি করুন", callback_data="usd:sell")
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
    await call.message.answer(f"💵 <b>ডলার {direction.upper()}</b>\n\nকত USD করতে চান? (সর্বনিম্ন {fmt(MIN_USD)} USD)\n💱 রেট: 1 USD = <b>{fmt(rate)} {CURRENCY}</b>\n(বাতিল করতে /cancel)")

@user_router.message(UsdOrderSt.amount, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_TEXTS))
async def usd_order_amount(message: Message, state: FSMContext):
    usd = parse_amount(message.text)
    if usd is None or usd < MIN_USD:
        return await message.answer("⚠️ সঠিক পরিমাণ দিন।")

    buy_rate, sell_rate = await db.rates()
    data = await state.get_data()
    direction = data.get("direction")
    rate = sell_rate if direction == "buy" else buy_rate
    bdt = round(usd * rate, 2)

    if direction == "buy":
        u = await db.get_user(message.from_user.id)
        if u["balance"] + 1e-9 < bdt:
            await state.clear()
            return await message.answer(f"❌ ব্যালেন্স অপর্যাপ্ত। প্রয়োজন: {fmt(bdt)} {CURRENCY}")

    await state.update_data(usd=usd, bdt=bdt)
    await state.set_state(UsdOrderSt.method)
    b = InlineKeyboardBuilder()
    for key in DOLLAR_CRYPTO_KEYS:
        b.button(text=DOLLAR_CRYPTO_NAMES[key], callback_data=f"usdcrypto:{key}")
    b.adjust(1)
    await message.answer(f"💵 {fmt(usd)} USD = <b>{fmt(bdt)} {CURRENCY}</b>\n\nমেথড সিলেক্ট করুন:", reply_markup=b.as_markup())

@user_router.callback_query(F.data.startswith("usdcrypto:"))
async def cb_usd_crypto(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    key = call.data.split(":")[1]
    cm = DOLLAR_CRYPTO_NAMES.get(key, key)
    await state.update_data(crypto_meth=cm)
    await call.answer()

    if data.get("direction") == "buy":
        await state.set_state(UsdOrderSt.details)
        await call.message.answer(f"📬 আপনার <b>{esc(cm)}</b> ওয়ালেট অ্যাড্রেস / UID দিন:")
    else:
        addr = await db.get_setting(f"pay_{key}", "নট সেট")
        await state.set_state(UsdOrderSt.trx)
        await call.message.answer(f"📤 নিচের <b>{esc(cm)}</b> ঠিকানায় <b>{fmt(data['usd'])} USD</b> পাঠান:\n<code>{esc(addr)}</code>\n\nপাঠানোর পর Transaction ID (TXID) দিন:")

@user_router.message(UsdOrderSt.trx, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_TEXTS))
async def usd_sell_trx(message: Message, state: FSMContext):
    await state.update_data(trx=message.text.strip())
    await state.set_state(UsdOrderSt.fiat)
    b = InlineKeyboardBuilder()
    for fm in FIAT_PAYMENT_METHODS:
        b.button(text=fm, callback_data=f"usdfiat:{fm}")
    b.adjust(3)
    await message.answer("💳 কোন মাধ্যমে টাকা রিসিভ করতে চান?", reply_markup=b.as_markup())

@user_router.callback_query(F.data.startswith("usdfiat:"))
async def cb_usd_fiat(call: CallbackQuery, state: FSMContext):
    fm = call.data.split(":", 1)[1]
    await state.update_data(fiat_meth=fm)
    await state.set_state(UsdOrderSt.number)
    await call.answer()
    await call.message.answer(f"📱 আপনার <b>{esc(fm)}</b> নাম্বার দিন:")

@user_router.message(UsdOrderSt.number, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_TEXTS))
async def usd_sell_number(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    details = f"TXID: {data.get('trx', '-')}\n{data.get('fiat_meth', '')} Number: {message.text.strip()}"
    await usd_finalize(message, state, bot, details)

@user_router.message(UsdOrderSt.details, F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_TEXTS))
async def usd_buy_details(message: Message, state: FSMContext, bot: Bot):
    await usd_finalize(message, state, bot, f"Wallet/UID: {message.text.strip()}")

async def usd_finalize(message: Message, state: FSMContext, bot: Bot, details: str):
    data = await state.get_data()
    oid = await db.create_usd_order(message.from_user.id, data["direction"], data["crypto_meth"], data.get("fiat_meth", "Auto"), data["usd"], data["bdt"], details)
    await state.clear()
    if oid is None:
        return await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই।")

    await message.answer(f"✅ ডলার অর্ডার #{oid} জমা হয়েছে।", reply_markup=main_menu_kb("bn"))
    b = InlineKeyboardBuilder()
    b.button(text="✅ Complete", callback_data=f"adminusd_ok:{oid}")
    b.button(text="❌ Reject", callback_data=f"adminusd_no:{oid}")
    await notify_admins(bot, f"💵 Dollar Order #{oid} ({data['direction'].upper()})\nUser: {message.from_user.id}\nUSD: {data['usd']} | BDT: {data['bdt']}\nDetails: <code>{esc(details)}</code>", b.as_markup())

# ==================== ADMIN ROUTER ====================
admin_router = Router(name="admin")
admin_router.message.filter(lambda m: m.from_user is not None and is_admin_id(m.from_user.id))
admin_router.callback_query.filter(lambda c: c.from_user is not None and is_admin_id(c.from_user.id))

AT = (F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_TEXTS))

def admin_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📊 Stats", callback_data="apanel:stats")
    b.button(text="⏳ Deposits", callback_data="apanel:deposits")
    b.button(text="💵 Dollar Orders", callback_data="apanel:usds")
    b.button(text="📦 Products", callback_data="apanel:products")
    b.button(text="⚙️ Payment & Settings", callback_data="apanel:settings")
    b.button(text="👥 Users", callback_data="apanel:users")
    b.adjust(2, 2, 2)
    return b.as_markup()

def cancel_kb():
    b = InlineKeyboardBuilder()
    b.button(text="❌ Cancel", callback_data="acancel")
    return b.as_markup()

def back_kb(cb="apanel:main"):
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Back", callback_data=cb)
    return b.as_markup()

@admin_router.message(Command("admin", "panel"))
async def a_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🛠 <b>Admin Control Panel</b>", reply_markup=admin_menu_kb())

@admin_router.callback_query(F.data == "apanel:main")
async def cb_apanel_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, "🛠 <b>Admin Control Panel</b>", admin_menu_kb())

@admin_router.callback_query(F.data == "acancel")
async def cb_acancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Cancelled ❎")
    await safe_edit(call.message, "🛠 <b>Admin Control Panel</b>", admin_menu_kb())

@admin_router.callback_query(F.data == "apanel:settings")
async def cb_admin_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    buy, sell = await db.rates()
    sup = await db.get_setting("support_username")
    txt = f"⚙️ <b>Settings & Rates</b>\n\n🟢 Buy: {fmt(sell)} | 🔴 Sell: {fmt(buy)}\n🎧 Support: @{esc(sup)}"
    b = InlineKeyboardBuilder()
    b.button(text="🟢 Buy Rate", callback_data="aset:rate_sell")
    b.button(text="🔴 Sell Rate", callback_data="aset:rate_buy")
    b.button(text="🎧 Support", callback_data="aset:support_username")
    b.button(text="⬅️ Back", callback_data="apanel:main")
    b.adjust(2, 1, 1)
    await safe_edit(call.message, txt, b.as_markup())

@admin_router.callback_query(F.data.startswith("aset:"))
async def cb_aset_field(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    await state.set_state(AdminSt.setting_edit)
    await state.update_data(key=key)
    await call.answer()
    await call.message.answer(f"✏️ <b>{key}</b> এর নতুন ভ্যালু দিন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.setting_edit, *AT)
async def st_setting_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.set_setting(data["key"], message.text.strip().lstrip("@"))
    await state.clear()
    await message.answer("✅ সফলভাবে আপডেট হয়েছে!")

@admin_router.callback_query(F.data == "apanel:products")
async def cb_apanel_products(call: CallbackQuery, state: FSMContext):
    await state.clear()
    cats = await db.categories()
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"📁 {c['name']}", callback_data=f"acat:{c['id']}")
    b.button(text="➕ Add Category", callback_data="acat_add")
    b.button(text="⬅️ Back", callback_data="apanel:main")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, "📦 <b>Categories</b>", b.as_markup())

@admin_router.callback_query(F.data.startswith("acat:"))
async def cb_acat(call: CallbackQuery):
    cid = int(call.data.split(":")[1])
    cat = await db.get_category(cid)
    prods = await db.products(cid, only_active=False)
    b = InlineKeyboardBuilder()
    for p in prods:
        b.button(text=f"{p['name']} • {p['price']}৳ ({p['stock']})", callback_data=f"aprod:{p['id']}")
    b.button(text="➕ Add Product", callback_data=f"aprodadd:{cid}")
    b.button(text="⬅️ Back", callback_data="apanel:products")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, f"📁 <b>{esc(cat['name'])}</b>", b.as_markup())

@admin_router.callback_query(F.data == "acat_add")
async def cb_acat_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSt.cat_name)
    await call.answer()
    await call.message.answer("📁 ক্যাটাগরির নাম দিন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.cat_name, *AT)
async def st_cat_name(message: Message, state: FSMContext):
    await db.add_category(message.text.strip())
    await state.clear()
    await message.answer("✅ ক্যাটাগরি যোগ হয়েছে!")

@admin_router.callback_query(F.data.startswith("aprodadd:"))
async def cb_aprodadd(call: CallbackQuery, state: FSMContext):
    cid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.prod_name)
    await state.update_data(cid=cid)
    await call.answer()
    await call.message.answer("📦 প্রোডাক্টের নাম দিন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.prod_name, *AT)
async def st_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminSt.prod_price)
    await message.answer("💰 দাম দিন (সংখ্যায়):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.prod_price, *AT)
async def st_prod_price(message: Message, state: FSMContext):
    price = parse_amount(message.text)
    if price is None:
        return await message.answer("⚠️ সঠিক দাম দিন।")
    data = await state.get_data()
    pid = await db.add_product(data["cid"], data["name"], price, "")
    await state.clear()
    await message.answer(f"✅ প্রোডাক্ট যোগ হয়েছে! (ID: #{pid})")

@admin_router.callback_query(F.data.startswith("aprod:"))
async def cb_aprod_detail(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    p = await db.get_product(pid)
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Change Price", callback_data=f"apset:{pid}")
    b.button(text="📥 Add Stock", callback_data=f"astock:{pid}")
    b.button(text="⬅️ Back", callback_data=f"acat:{p['category_id']}")
    b.adjust(1)
    await call.answer()
    await safe_edit(call.message, f"📦 <b>{esc(p['name'])}</b>\n💰 Price: {p['price']}৳\n📊 Stock: {p['stock']}", b.as_markup())

@admin_router.callback_query(F.data.startswith("apset:"))
async def cb_apset(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.price_set)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("✏️ নতুন দাম দিন:", reply_markup=cancel_kb())

@admin_router.message(AdminSt.price_set, *AT)
async def st_price_set(message: Message, state: FSMContext):
    p = parse_amount(message.text)
    if p is None:
        return await message.answer("⚠️ সঠিক দাম দিন।")
    pid = (await state.get_data())["pid"]
    await db.adjust_price(pid, "s", p)
    await state.clear()
    await message.answer("✅ দাম আপডেট হয়েছে!")

@admin_router.callback_query(F.data.startswith("astock:"))
async def cb_astock(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.set_state(AdminSt.stock_add)
    await state.update_data(pid=pid)
    await call.answer()
    await call.message.answer("📥 স্টক আইটেম দিন (প্রতি লাইনে ১টি):", reply_markup=cancel_kb())

@admin_router.message(AdminSt.stock_add, *AT)
async def st_stock_add(message: Message, state: FSMContext):
    pid = (await state.get_data())["pid"]
    items = [ln.strip() for ln in message.text.splitlines() if ln.strip()]
    n = await db.add_stock(pid, items)
    await state.clear()
    await message.answer(f"✅ {n} টি স্টক যোগ হয়েছে!")

@admin_router.callback_query(F.data == "apanel:stats")
async def cb_apanel_stats(call: CallbackQuery):
    s = await db.stats()
    await call.answer()
    await safe_edit(call.message, f"👥 Users: {s['users']}\n💼 Balance: {fmt(s['balance'])}৳\n📦 Products: {s['products']}", back_kb())

@admin_router.callback_query(F.data == "apanel:deposits")
async def cb_apanel_deposits(call: CallbackQuery):
    rows = await db.pending_deposits()
    await call.answer()
    if not rows:
        return await safe_edit(call.message, "🎉 কোনো পেন্ডিং ডিপোজিট নেই।", back_kb())
    for d in rows[:5]:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Approve", callback_data=f"admindep_ok:{d['id']}")
        b.button(text="❌ Reject", callback_data=f"admindep_no:{d['id']}")
        await call.message.answer(f"💳 Deposit #{d['id']}\nUser: {d['user_id']}\nAmount: {d['amount']}\nTrxID: {d['trx_id']}", reply_markup=b.as_markup())

@admin_router.callback_query(F.data.startswith("admindep_ok:"))
async def cb_admindep_ok(call: CallbackQuery, bot: Bot):
    res = await db.approve_deposit(int(call.data.split(":")[1]), call.from_user.id)
    if res:
        await notify_user(bot, res["user_id"], "✅ ডিপোজিট অ্যাপ্রুভ হয়েছে!")
        await call.answer("Approved ✅")
        await safe_edit(call.message, "✅ Approved")

@admin_router.callback_query(F.data.startswith("admindep_no:"))
async def cb_admindep_no(call: CallbackQuery, bot: Bot):
    d = await db.reject_deposit(int(call.data.split(":")[1]), call.from_user.id)
    if d:
        await notify_user(bot, d["user_id"], "❌ ডিপোজিট বাতিল হয়েছে।")
        await call.answer("Rejected ❌")
        await safe_edit(call.message, "❌ Rejected")

@admin_router.callback_query(F.data == "apanel:usds")
async def cb_apanel_usds(call: CallbackQuery):
    rows = await db.pending_usd_orders()
    await call.answer()
    if not rows:
        return await safe_edit(call.message, "🎉 কোনো পেন্ডিং ডলার অর্ডার নেই।", back_kb())
    for o in rows[:5]:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Complete", callback_data=f"adminusd_ok:{o['id']}")
        b.button(text="❌ Reject", callback_data=f"adminusd_no:{o['id']}")
        await call.message.answer(f"💵 Dollar Order #{o['id']}\nUSD: {o['usd_amount']} | BDT: {o['bdt_amount']}", reply_markup=b.as_markup())

@admin_router.callback_query(F.data.startswith("adminusd_ok:"))
async def cb_adminusd_ok(call: CallbackQuery, bot: Bot):
    res = await db.resolve_usd_order(int(call.data.split(":")[1]), True)
    if res:
        await notify_user(bot, res["order"]["user_id"], "✅ ডলার অর্ডার সম্পন্ন হয়েছে!")
        await call.answer("Done ✅")
        await safe_edit(call.message, "✅ Done")

@admin_router.callback_query(F.data.startswith("adminusd_no:"))
async def cb_adminusd_no(call: CallbackQuery, bot: Bot):
    res = await db.resolve_usd_order(int(call.data.split(":")[1]), False)
    if res:
        await notify_user(bot, res["order"]["user_id"], "❌ ডলার অর্ডার বাতিল হয়েছে!")
        await call.answer("Rejected ❌")
        await safe_edit(call.message, "❌ Rejected")

# ==================== Render health server ====================
def run_flask():
    app = Flask(__name__)

    @app.route("/")
    def health():
        return "Bot is running"

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==================== Main ====================
async def main():
    global BOT_USERNAME
    logging.basicConfig(level=logging.INFO)
    await db.connect()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    BOT_USERNAME = (await bot.get_me()).username

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.message.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(UserMiddleware())  # ✅ বাটনের জন্য জরুরি

    # Render-এর জন্য পোর্ট সার্ভার চালু (background thread)
    threading.Thread(target=run_flask, daemon=True).start()

    log.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped!")
