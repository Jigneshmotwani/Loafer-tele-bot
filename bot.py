import os
import re
import openai
import asyncio
from langdetect import detect
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Load API keys from environment variables
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
RENDER_URL = "https://loafer-tele-bot.onrender.com"  # same as your deployed URL

openai.api_key = OPENAI_API_KEY
LATIN_PATTERN = re.compile(r'^[A-Za-z0-9\s,.\'?!-]+$')


def needs_translation(text: str) -> bool:
    if not LATIN_PATTERN.match(text):
        return False
    try:
        return detect(text) != "en"
    except Exception:
        return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text or update.message.from_user.is_bot:
        return

    if not needs_translation(text):
        return

    prompt = f"Translate the following text into natural English, keeping the meaning intact:\n\n{text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        translation = response.choices[0].message.content.strip()
        await update.message.reply_text(
            f"🔹 {update.message.from_user.first_name} said:\n{text}\n\n➡️ {translation}"
        )
    except Exception as e:
        print(f"Translation error: {e}")
        await update.message.reply_text("⚠️ Translation failed.")


async def main():
    print("Starting Telegram bot...")

    # Set webhook asynchronously
    bot = Bot(token=TELEGRAM_TOKEN)
    webhook_url = f"{RENDER_URL}/{TELEGRAM_TOKEN}"
    try:
        await bot.set_webhook(webhook_url)
        print(f"Webhook successfully set to {webhook_url}")
    except Exception as e:
        print(f"Failed to set webhook: {e}")

    # Build the bot application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run webhook for Render
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    asyncio.run(main())