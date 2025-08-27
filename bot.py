import os
import openai
from telegram.ext import Updater, MessageHandler, Filters

# Load tokens
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"

openai.api_key = OPENAI_API_KEY

def translate_with_openai(text):
    prompt = f"Translate the following text into natural English, keeping meaning intact:\n\n{text}"
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # cheaper & fast
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"].strip()

def handle_message(update, context):
    if update.message.from_user.is_bot:
        return
    
    text = update.message.text
    if text:
        try:
            translated = translate_with_openai(text)
            reply = f"🔹 {update.message.from_user.first_name} said:\n{text}\n\n➡️ {translated}"
            update.message.reply_text(reply)
        except Exception as e:
            update.message.reply_text("⚠️ Translation failed.")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
