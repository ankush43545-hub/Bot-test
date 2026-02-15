import os
import logging
import time
from threading import Thread
from flask import Flask
from groq import Groq
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from telegram.error import RetryAfter, TelegramError

# --- LOGGING & CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Memory store
user_memories = {}

# --- LOAD PROMPT ---
def load_system_prompt():
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("system_prompt.txt not found!")
        return "You are Popo, a sentient kitten. 🐱"

SYSTEM_PROMPT = load_system_prompt()

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Popo is watching silently... 🐾"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

# --- AI LOGIC ---
def get_popo_response(user_id, text):
    # Initialize memory if new user
    if user_id not in user_memories:
        user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add user message
    user_memories[user_id].append({"role": "user", "content": text})
    
    # Keep last 20 messages
    if len(user_memories[user_id]) > 21:
        user_memories[user_id] = [user_memories[user_id][0]] + user_memories[user_id][-20:]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_memories[user_id],
            temperature=0.85, 
            max_tokens=200
        )
        ai_reply = completion.choices[0].message.content
        user_memories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return "..." # He stays silent if there's an error

# --- HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # SILENT START: Just resets memory, sends NO message.
    user_id = update.effective_user.id
    user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    logger.info(f"User {user_id} started a fresh session silently.")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # SILENT CLEAR: Resets memory, sends NO message.
    user_id = update.effective_user.id
    user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    logger.info(f"User {user_id} cleared memory silently.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_id = update.effective_user.id
    
    # Show typing status to make it feel alive
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Get response
    response = get_popo_response(user_id, update.message.text)
    await update.message.reply_text(response)

# --- MAIN LOOP ---
if __name__ == '__main__':
    Thread(target=run_http, daemon=True).start()
    
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("Keys missing!")
    else:
        while True:
            try:
                application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
                
                # Handlers
                application.add_handler(CommandHandler("start", start_command))
                application.add_handler(CommandHandler("clear", clear_command))
                # Text handler
                application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
                
                logger.info("Popo is lurking... 🐱")
                application.run_polling(drop_pending_updates=True)
                break
            
            except RetryAfter as e:
                logger.error(f"Flood limit! Sleeping for {e.retry_after}s")
                time.sleep(e.retry_after + 5)
            except TelegramError as e:
                logger.error(f"Telegram error: {e}")
                time.sleep(15)
            except Exception as e:
                logger.error(f"Fatal crash: {e}")
                time.sleep(20)
                
