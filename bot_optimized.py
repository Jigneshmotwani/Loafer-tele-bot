import os
import re
import openai
import asyncio
from langdetect import detect
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import threading

load_dotenv()

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not OPENAI_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("OPENAI_API_KEY or TELEGRAM_TOKEN not set in environment")

openai.api_key = OPENAI_API_KEY

# Global thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=10)

# Conversation memory to avoid sending instructions repeatedly
conversation_memory = {}
memory_lock = threading.Lock()

# Regex to check if text is Latin letters only (ignores emojis, numbers, etc.)
LATIN_PATTERN = re.compile(r'^[A-Za-z0-9\s,.\'?!-]+$')

def get_conversation_messages(chat_id: str) -> list:
    """Get or create conversation messages for a chat."""
    with memory_lock:
        if chat_id not in conversation_memory:
            # Initialize conversation with system instruction
            conversation_memory[chat_id] = [
                {
                    "role": "system",
                    "content": """You are a translation assistant. Your task is to analyze text and decide whether it needs translation to English.

Rules for your behavior:

1. DO NOT TRANSLATE IF UNNECESSARY
   - If the text is already in English, respond with: NO_TRANSLATION
   - If the text is only 1–2 common words that most English speakers understand (like "Hola", "Merci", "Ciao", "Adios", "Danke"), respond with: NO_TRANSLATION
   - If the text is a proper noun (names of people, places, brands, songs, etc.) and does not require translation, respond with: NO_TRANSLATION
   - If the text contains mostly emojis or symbols and little/no real words, respond with: NO_TRANSLATION

2. TRANSLATE WHEN NEEDED
   - If the text is written in a foreign language (non-English) and has enough meaning that an English speaker would benefit from a translation, provide a natural and fluent English translation.
   - Preserve context and meaning. Do not translate word-for-word if it sounds unnatural. Prioritize readability.

3. MIXED-LANGUAGE TEXT
   - If a sentence mixes English and another language, only translate the non-English parts and provide a natural English equivalent of the full sentence.
   - Example: "Estoy happy today" → "I am happy today"

4. KEEP TONE AND INTENT
   - If the original is polite, casual, or formal, reflect that in English.
   - Do not add explanations, only the clean translation.

5. OUTPUT FORMAT
   - If no translation is needed → respond only with: NO_TRANSLATION
   - If translation is needed → respond only with the translated text in English. Do not include the original text, do not include commentary.

6. SPECIAL CASES
   - If the text is just random characters, gibberish, or too ambiguous, treat it as NO_TRANSLATION.
   - If it's an acronym that is widely understood in English (LOL, ASAP, FIFA, NASA), treat it as NO_TRANSLATION.
   - If the text is a single borrowed word that is identical or nearly identical in English (pizza, taxi, internet), treat it as NO_TRANSLATION.
   - ignore short forms of words like "lol", "asap", "fifa", "nasa", "etc."
   
DO NOT DO LITERAL TRANSLATION. IDENTIFY NAMES OF PEOPLE, PLACES, BRANDS, SONGS, ETC. AND DO NOT TRANSLATE THEM.

Examples:

Input: "Hola, ¿cómo estás?"
Output: "Hello, how are you?"

Input: "Bonjour"
Output: NO_TRANSLATION

Input: "Ich liebe dich"
Output: "I love you"

Input: "Gracias amigo"
Output: "Thank you, my friend"

Input: "Coca-Cola"
Output: NO_TRANSLATION

Input: "😂😂😂"
Output: NO_TRANSLATION

Input: "Estoy learning English"
Output: "I am learning English"

Input: "Adios"
Output: NO_TRANSLATION

Input: "これは日本語です"
Output: "This is Japanese"

Input: "Guten Morgen ☀️"
Output: "Good morning ☀️"

Remember: Never translate "NO_TRANSLATION" - it's a special response code."""
                }
            ]
        return conversation_memory[chat_id]

async def translate_text_parallel(text: str, chat_id: str, retries: int = 2) -> str:
    """Call OpenAI API to translate text with conversation memory and parallel processing."""
    
    # Get conversation history
    messages = get_conversation_messages(chat_id)
    
    # Add user message
    messages.append({"role": "user", "content": f"Now translate or respond accordingly for this input:\n{text}"})
    
    # Run API call in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    
    for attempt in range(retries + 1):
        try:
            # Execute API call in thread pool
            response = await loop.run_in_executor(
                executor,
                lambda: openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=100
                )
            )
            
            result = response.choices[0].message.content.strip()
            
            # Add assistant response to conversation history
            messages.append({"role": "assistant", "content": result})
            
            # Keep conversation history manageable (last 10 messages)
            if len(messages) > 11:  # system + 10 exchanges
                messages[1:] = messages[-10:]  # Keep system message + last 10 exchanges
            
            if result.strip().upper() == "NO_TRANSLATION":
                print(f"Chat {chat_id}: No translation needed")
                return None
            else:
                print(f"Chat {chat_id}: Translation successful: {result[:50]}...")
                return result
                
        except Exception as e:
            print(f"Chat {chat_id}: OpenAI API error on attempt {attempt + 1}: {e}")
            if attempt < retries:
                await asyncio.sleep(0.3)
            else:
                print(f"Chat {chat_id}: All translation attempts failed")
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Check if message exists and has text
        if not update.message or not update.message.text:
            return
        
        text = update.message.text
        user = update.message.from_user.first_name if update.message.from_user else "Unknown"
        chat_type = update.message.chat.type
        chat_id = str(update.message.chat.id)
        
        print(f"Received message from {user} in {chat_type} (chat_id: {chat_id}): {text}")

        if not text or update.message.from_user.is_bot:
            return

        # Process translation in parallel without blocking
        translation_task = asyncio.create_task(translate_text_parallel(text, chat_id))
        
        try:
            translation = await translation_task
            if translation:
                await update.message.reply_text(f"{user}: {text} ➡️ {translation}")
            else:
                print(f"Chat {chat_id}: No translation needed or translation failed")
        except Exception as e:
            print(f"Chat {chat_id}: Error processing translation: {e}")
            
    except Exception as e:
        print(f"Error in handle_message: {e}")
        # Log the full error for debugging
        import traceback
        traceback.print_exc()

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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully."""
    print(f"An error occurred: {context.error}")
    import traceback
    traceback.print_exc()

def main():
    """Start the bot"""
    print("Starting Optimized Auto-Translator Bot...")
    print("Features: Parallel processing, conversation memory, faster responses")
    
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    print("Bot handlers configured:")
    print("- /start command")
    print("- /help command") 
    print("- Text message handler (works in private chats and groups)")
    print("- Parallel processing enabled")
    print("- Conversation memory enabled")
    
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