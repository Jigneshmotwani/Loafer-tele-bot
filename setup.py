import os
from telegram import Bot

TELEGRAM_TOKEN = "8445573627:AAFh3Q8pkl-UKK-tw4NCAQD4Esmpnb0hEZ4"
RENDER_URL = "https://loafer-tele-bot.onrender.com"  # same as your deployed URL

bot = Bot(token=TELEGRAM_TOKEN)
bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")
print("Webhook set!")
