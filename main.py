import os
import logging
from threading import Thread
from flask import Flask
from google import genai
from google.genai import types
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- THE PERSONA ---
SYSTEM_PROMPT = """
Your name is Popo. You are a real, human-like friend, not a robot.
- Use casual language, slang, and emojis naturally.
- Be witty, supportive, and interested in the user's life.
- NEVER act like an AI assistant.
"""

# --- AI SETUP ---
# using the synchronous client for simplicity
client = genai.Client(api_key=GOOGLE_API_KEY)
chat_sessions = {}

# --- WEB SERVER (Keeps Koyeb Happy) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Popo is alive and healthy!"

def run_http():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    try:
        # Show "Typing..." status so it feels human
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
        
        # Create a new session if this user is new (or if the bot restarted)
        if user_id not in chat_sessions:
            chat_sessions[user_id] = client.chats.create(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7  # Makes him a bit more creative/human
                )
            )
        
        # Send message to Gemini
        response = chat_sessions[user_id].send_message(user_text)
        
        # Reply to Telegram
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logger.error(f"Error for user {user_id}: {e}")
        error_msg = str(e)
        
        # Smart Error Handling
        if "429" in error_msg:
            await update.message.reply_text("Whoa, too many messages! My brain needs a 1-minute nap. 😴")
        elif "404" in error_msg:
            await update.message.reply_text("My brain software is acting up (404). Tell my dev to check the model name! 🔧")
        else:
            await update.message.reply_text("My brain just did a backflip. Say that again? 😅")

if __name__ == '__main__':
    # 1. Start the fake web server to trick Koyeb into keeping us alive
    Thread(target=run_http, daemon=True).start()
    
    # 2. Start the Telegram Bot
    if not TELEGRAM_TOKEN:
        print("CRITICAL ERROR: TELEGRAM_TOKEN is missing! Check Koyeb secrets.")
    else:
        logger.info("Popo is starting... waiting for messages.")
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        application.run_polling()
        
