import os
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from langdetect import detect, DetectorFactory

# Fix randomness in langdetect
DetectorFactory.seed = 0

# Load tokens from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def is_latin_non_english(text: str) -> bool:
    """
    Returns True if text is written in Latin letters but is not English.
    """
    try:
        lang = detect(text)
        if lang != "en":
            # Check if all characters are ASCII letters, spaces, or punctuation
            if all(ord(c) < 128 for c in text):
                return True
    except:
        pass
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
