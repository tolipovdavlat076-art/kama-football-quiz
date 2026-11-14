
import os
import json
import hmac
import hashlib
import sqlite3
import threading
import time
from urllib.parse import parse_qsl

from flask import Flask, request, jsonify, send_from_directory
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN sozlanmagan!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DB_PATH = "kama_quiz.db"


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                first_name TEXT,
                score INTEGER NOT NULL,
                played_at INTEGER NOT NULL
            )
        """)


def verify_telegram_data(init_data):
    if not init_data:
        return None

    try:
        data = dict(parse_qsl(init_data))
        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        auth_date = int(data.get("auth_date", "0"))
        if time.time() - auth_date > 86400:
            return None

        check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(data.items())
        )

        secret = hmac.new(
            b"WebAppData",
            TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret,
            check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        return json.loads(data["user"])

    except Exception:
        return None


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "KAMA Football Quiz ishlayapti!"})


@app.route("/api/score", methods=["POST"])
def save_score():
    data = request.get_json(silent=True) or {}
    user = verify_telegram_data(data.get("initData", ""))

    if not user:
        return jsonify({"error": "Telegram tekshiruvi muvaffaqiyatsiz"}), 401

    try:
        score = int(data.get("score", 0))
        if score < 0 or score > 1000:
            return jsonify({"error": "Ball noto‘g‘ri"}), 400

        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                """INSERT INTO results
                (user_id, username, first_name, score, played_at)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    str(user["id"]),
                    user.get("username", ""),
                    user.get("first_name", "O‘yinchi"),
                    score,
                    int(time.time())
                )
            )

        return jsonify({"saved": True})

    except Exception:
        return jsonify({"error": "Natijani saqlab bo‘lmadi"}), 500


@app.route("/api/leaderboard")
def leaderboard():
    period = request.args.get("period", "all")

    now = int(time.time())
    if period == "day":
        since = now - 86400
    elif period == "week":
        since = now - 7 * 86400
    else:
        since = 0

    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute("""
            SELECT user_id,
                   MAX(username),
                   MAX(first_name),
                   SUM(score) AS points
            FROM results
            WHERE played_at >= ?
            GROUP BY user_id
            ORDER BY points DESC
            LIMIT 10
        """, (since,)).fetchall()

    players = []
    for i, row in enumerate(rows, 1):
        name = row[1] or row[2] or "O‘yinchi"
        players.append({
            "rank": i,
            "name": name,
            "score": row[3]
        })

    return jsonify({"players": players})


@bot.message_handler(commands=["start"])
def start(message):
    if not WEBAPP_URL:
        bot.send_message(message.chat.id, "Mini App manzili sozlanmagan.")
        return

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            "⚽ O‘YINNI BOSHLASH",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )

    bot.send_message(
        message.chat.id,
        "🏆 KAMA FOOTBALL QUIZ\n\n"
        "Futbol bilimingizni sinab ko‘ring!",
        reply_markup=keyboard
    )


def run_bot():
    bot.infinity_polling(skip_pending=True)


init_db()
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )

