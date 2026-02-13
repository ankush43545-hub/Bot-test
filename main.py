import os
import logging
from threading import Thread
from flask import Flask
from groq import Groq
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- AI CLIENT ---
client = Groq(api_key=GROQ_API_KEY)

# --- THE PERSONA ---
SYSTEM_PROMPT = (
    "You are Popo, an authentic, adaptive AI collaborator with a touch of wit. "
    "Your tone is casual, human-like, and supportive. Use frequent emojis. "
    "Keep responses concise and scannable. You are like a grounded, helpful peer."
)

# --- WEB SERVER (For Koyeb Health) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Popo is running on Groq! 🚀"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

# --- AI LOGIC ---
def get_popo_response(user_text):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.8,
            max_tokens=500
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return "My internal circuits just did a backflip. 🙃 Try again in a sec!"

# --- TELEGRAM HANDLERS ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # Show typing status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Get AI response
    user_text = update.message.text
    response = get_popo_response(user_text)
    
    # Send reply
    await update.message.reply_text(response)

if __name__ == '__main__':
    # Start Web Server for Koyeb
    Thread(target=run_http, daemon=True).start()
    
    # Start Telegram Bot
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("Missing Environment Variables!")
    else:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        logger.info("Popo is officially online...")
        application.run_polling()
        
