import os
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import string

# Load tokens from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Filler words to ignore
FILLER_WORDS = {"hi", "hello", "ok", "yes", "no", "lol", "hmm", "hey", "thanks", "thank", "bye"}

def is_latin(text: str) -> bool:
    """Check if all characters are ASCII (Latin letters, numbers, punctuation)."""
    return all(ord(c) < 128 for c in text)

async def detect_and_translate(text: str) -> str:
    """
    Single OpenAI call:
    - Detect if text is non-English (Latin letters)
    - Translate to English if non-English
    - Return empty string if text is already English
    """
    prompt = (
        "Detect if this text is non-English. "
        "If it is non-English, translate it to natural English keeping meaning intact. "
        "If it is English, return nothing.\n\n"
        f"Text: \"{text}\""
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        result = response["choices"][0]["message"]["content"].strip()
        return result  # empty if English
    except:
        return ""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.is_bot:
        return

    text = update.message.text
    if not text or not is_latin(text):
        return

    # Skip messages that are only filler words
    clean_text = text.translate(str.maketrans('', '', string.punctuation)).lower()
    words_in_text = clean_text.split()
    if all(w in FILLER_WORDS for w in words_in_text):
        return

    translated = await detect_and_translate(text)
    if translated:
        reply = f"🔹 {update.message.from_user.first_name} said:\n{text}\n\n➡️ {translated}"
        await update.message.reply_text(reply)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
