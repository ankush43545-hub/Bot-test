import os
import logging
from threading import Thread
from flask import Flask
from duckduckgo_search import DDGS
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- THE PERSONA ---
# Since DDG doesn't have a 'system_instruction' parameter, 
# we prompt the model at the start of every message.
POPO_PROMPT = (
    "You are Popo, a casual, human-like friend. Use slang and emojis. "
    "Be witty and supportive. Keep it brief. Talk to the user as a peer. "
    "User says: "
)

# --- WEB SERVER (For Koyeb) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Popo is Ducking Awesome!"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

# --- AI LOGIC (DuckDuckGo) ---
def get_ai_response(user_text):
    try:
        with DDGS() as ddgs:
            # We use gpt-4o-mini via DDG - it's fast and smart!
            results = ddgs.chat(f"{POPO_PROMPT} {user_text}", model='gpt-4o-mini')
            return results
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "My brain just did a duck-dive. 🦆 Try again?"

# --- TELEGRAM BOT ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    response = get_ai_response(user_text)
    await update.message.reply_text(response)

if __name__ == '__main__':
    # Start Web Server
    Thread(target=run_http, daemon=True).start()
    
    # Start Telegram
    if not TELEGRAM_TOKEN:
        print("Missing TELEGRAM_TOKEN!")
    else:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        logger.info("Popo (DDG Edition) is starting...")
        app_bot.run_polling()
        
