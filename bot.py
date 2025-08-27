import os
import re
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # Fix langdetect randomness

# Load tokens
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Regex pattern to detect typical non-English Latin words (Hindi/Urdu transliteration)
NON_ENGLISH_LATIN_PATTERN = re.compile(
    r"\b(ka|ke|ki|ho|hai|tum|kya|main|hum|aap|rahe|rahi|tha|thi|hai|hoon|ho)\b", re.IGNORECASE
)

def is_latin_non_english(text: str) -> bool:
    """
    Returns True if text is in Latin letters but likely not English.
    """
    try:
        lang = detect(text)
    except:
        return False

    # ASCII check: only Latin letters, numbers, spaces, punctuation
    if not all(ord(c) < 128 for c in text):
        return False

    # Only translate if detected language is not English OR matches our non-English Latin regex
    if lang != "en" or NON_ENGLISH_LATIN_PATTERN.search(text):
        return True

    return False

async def translate_with_openai(text: str) -> str:
    prompt = f"Translate the following text into natural English, keeping meaning intact:\n\n{text}"
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"].strip()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.is_bot:
        return

    text = update.message.text
    if text and is_latin_non_english(text):
        try:
            translated = await translate_with_openai(text)
            reply = f"🔹 {update.message.from_user.first_name} said:\n{text}\n\n➡️ {translated}"
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Translation failed: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
