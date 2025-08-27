import os
import re
import openai
import asyncio
from langdetect import detect
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Load API keys from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not OPENAI_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("OPENAI_API_KEY or TELEGRAM_TOKEN not set in environment")

openai.api_key = OPENAI_API_KEY

# Regex to check if text is Latin letters only (ignores emojis, numbers, etc.)
LATIN_PATTERN = re.compile(r'^[A-Za-z0-9\s,.\'?!-]+$')

def needs_translation(text: str) -> bool:
    """Return True if text is non-English and written in Latin letters."""
    if not LATIN_PATTERN.match(text):
        return False
    try:
        lang = detect(text)
        return lang != "en"
    except Exception as e:
        print(f"Language detection error: {e}")
        return False

async def translate_text(text: str, retries: int = 2) -> str:
    """Call OpenAI API to translate text, with retries on failure."""
    prompt = f"Translate the following text into natural English, keeping the meaning intact:\n\n{text}"
    for attempt in range(retries + 1):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            translation = response.choices[0].message.content

            return translation
        except Exception as e:
            print(f"OpenAI API error on attempt {attempt + 1}: {e}")
            await asyncio.sleep(1)  # wait before retry
    return None  # all attempts failed

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user.first_name
    print(f"Received message from {user}: {text}")

    if not text or update.message.from_user.is_bot:
        return

    if not needs_translation(text):
        print("No translation needed.")
        return

    translation = await translate_text(text)
    if translation:
        await update.message.reply_text(f"🔹 {user} said:\n{text}\n\n➡️ {translation}")
    else:
        await update.message.reply_text("⚠️ Translation failed. Check logs for details.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    PORT = int(os.environ.get("PORT", 5000))
    print(f"Starting bot. Listening on port {PORT}...")

    # Using polling for simplicity; switch to run_webhook in production
    app.run_polling()
