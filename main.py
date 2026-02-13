import os
import logging
import asyncio
from google import genai
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION (Loading from Environment) ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- THE PERSONA ---
SYSTEM_PROMPT = """
Your name is Popo. You are a real, human-like friend, not a robot.
- Use casual language and emojis.
- Be witty, supportive, and ask the user questions to get to know them.
- NEVER act like an AI assistant. 
"""

# --- AI SETUP ---
client = genai.Client(api_key=GOOGLE_API_KEY)
chat_sessions = {}

# --- WEB SERVER (For Health Checks) ---
app = Flask('')
@app.route('/')
def home(): return "Popo is alive!"

def run_http():
    # Koyeb/Cloud hosts provide a 'PORT' variable automatically
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
        
        if user_id not in chat_sessions:
            chat_sessions[user_id] = client.chats.create(
                model="models/gemini-1.5-flash", 
                config={'system_instruction': SYSTEM_PROMPT}
            )
        
        response = chat_sessions[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("My brain just did a backflip. Say that again? 😅")

if __name__ == '__main__':
    # Start Web Server
    Thread(target=run_http, daemon=True).start()
    
    # Build and Run Bot
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Popo is starting...")
    application.run_polling()
    
