
import os
import threading
from flask import Flask, send_from_directory
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL")

if not TOKEN or not WEBAPP_URL:
    raise RuntimeError("BOT_TOKEN va WEBAPP_URL sozlanmagan!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return {"status": "KAMA Football Quiz ishlayapti!"}

@bot.message_handler(commands=["start"])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            "⚽ O'YINNI BOSHLASH",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )
    bot.send_message(
        message.chat.id,
        "🏆 KAMA FOOTBALL QUIZ\n\n"
        "Futbol bilimingizni sinab ko'ring!\n"
        "Reytingda birinchi o'rinni egallang! 🥇",
        reply_markup=keyboard
    )

def run_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

