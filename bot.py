import os
import re
import openai
import asyncio
from langdetect import detect
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from dotenv import load_dotenv

load_dotenv()

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

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
    """Call OpenAI API to translate text or return None if no translation needed."""
    prompt = f"""Analyze this text and decide if it needs translation to English.

If the text is already in English or doesn't need translation, respond with exactly: "NO_TRANSLATION_NEEDED"

If the text is in another language and needs translation, translate it to natural English.

Text: {text}

Respond with either:
- "NO_TRANSLATION_NEEDED" if no translation is needed
- The English translation if translation is needed"""

    for attempt in range(retries + 1):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            
            if result == "NO_TRANSLATION_NEEDED":
                print("OpenAI determined no translation needed")
                return None
            else:
                print(f"Translation successful: {result[:50]}...")
                return result
                
        except Exception as e:
            print(f"OpenAI API error on attempt {attempt + 1}: {e}")
            if attempt < retries:
                await asyncio.sleep(1)  # wait before retry
            else:
                print("All translation attempts failed")
    return None  # all attempts failed

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user.first_name
    chat_type = update.message.chat.type
    print(f"Received message from {user} in {chat_type}: {text}")

    if not text or update.message.from_user.is_bot:
        return

    # Let OpenAI decide if translation is needed
    translation = await translate_text(text)
    if translation:
        await update.message.reply_text(f"{user}: {text} ➡️ {translation}")
    else:
        print("No translation needed or translation failed")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """
🤖 Welcome to the Auto-Translator Bot!

I automatically detect and translate messages from other languages to English.

Simply send me any message in a foreign language, and I'll translate it for you!

Supported features:
• Automatic language detection
• Translation to English
• Works with Latin alphabet languages
• Preserves original message context

Start chatting in any language! 🌍
    """
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 How to use this bot:

1. Send any message in a foreign language
2. I'll automatically detect if it needs translation
3. If it does, I'll reply with both the original and English translation

Examples of supported languages:
• Spanish: "Hola, ¿cómo estás?"
• French: "Bonjour, comment allez-vous?"
• German: "Guten Tag, wie geht es Ihnen?"
• Italian: "Ciao, come stai?"
• Portuguese: "Olá, como você está?"

Commands:
/start - Welcome message
/help - This help message

Note: I work best with Latin alphabet languages.
    """
    await update.message.reply_text(help_text)

def main():
    """Start the bot"""
    print("Starting Auto-Translator Bot...")
    
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot handlers configured:")
    print("- /start command")
    print("- /help command") 
    print("- Text message handler (works in private chats and groups)")
    
    # Get webhook configuration
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 5000))
    
    print(f"Starting bot on port {PORT}")
    print(f"WEBHOOK_URL: {WEBHOOK_URL}")
    
    # For Render deployment, always use webhook mode
    if not WEBHOOK_URL:
        # Auto-generate webhook URL for Render
        WEBHOOK_URL = f"https://loafer-tele-bot.onrender.com"
        print(f"Auto-generated webhook URL: {WEBHOOK_URL}")
    
    # Use webhooks for production
    print(f"Using webhook at {WEBHOOK_URL}")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="",
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()


